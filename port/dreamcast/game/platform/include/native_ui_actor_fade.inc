// Included once by native_ui.cpp, after the existing source deferral API.
// Uses its FIFO, frame storage, spill and retirement; there is no second queue.
namespace {
DeferredLighting* const kActorFadeTag=reinterpret_cast<DeferredLighting*>(5);
constexpr unsigned kActorFadeNode=(sizeof(DeferredPart)+31u)&~31u;
constexpr unsigned kActorFadeBytes=kActorFadeNode+((sizeof(Re4dcActorFadeTicket)+31u)&~31u);
unsigned actor_fade_queue_epoch=1,actor_fade_queue_pending;
#if RE4DC_ACTOR_TRANSACTION_DIAG
bool actor_fade_queue_seen;
unsigned actor_fade_queue_walk;
#endif
Re4dcActorFadeReservation actor_fade_reserved{};
unsigned* actor_fade_reserved_top;
unsigned actor_fade_old_top;
DeferredPart* actor_fade_reserved_tail;

void actor_fade_queue_reset() {
    // A lost admitted node is an explicit failed candidate frame. Do not walk
    // payloads here: source retirement can already have revoked their owner.
    if(actor_fade_queue_pending)re4dc_model_packet_abort();
    actor_fade_queue_pending=0;actor_fade_reserved={};actor_fade_reserved_top=nullptr;
#if RE4DC_ACTOR_TRANSACTION_DIAG
    if(actor_fade_queue_seen)re4dc_log("AFD_FIFO reset ep=%u walked=%u\n",actor_fade_queue_epoch,actor_fade_queue_walk);
    actor_fade_queue_seen=false;actor_fade_queue_walk=0;
#endif
    if(actor_fade_queue_epoch)++actor_fade_queue_epoch; // exhausted 0 never admits
}
bool actor_fade_reservation_current(const Re4dcActorFadeReservation& r) {
    return r.node && r.epoch && r.epoch==actor_fade_queue_epoch &&
        r.node==actor_fade_reserved.node && r.epoch==actor_fade_reserved.epoch &&
        actor_fade_reserved_top && *actor_fade_reserved_top==actor_fade_old_top-kActorFadeBytes &&
        deferred_last==actor_fade_reserved_tail;
}
int actor_fade_queue_failure() {re4dc_model_packet_abort();return -1;}
// The production drain calls this before ordinary model restoration. The node
// is popped and its value copied before a callback can yield/retire storage.
bool actor_fade_drain_head() {
    if(!deferred_first || deferred_first->lighting!=kActorFadeTag)return false;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    // Include dying-actor ticket restore, acquisition and palette/list setup,
    // not just the nested native part emission, in the model-list interval.
    const re4dc::dsa24::Scope dsa_model(re4dc::dsa24::ModelList);
#endif
    const auto* node=deferred_first;
    Re4dcActorFadeTicket ticket{};
    std::memcpy(&ticket,reinterpret_cast<const unsigned char*>(node)+kActorFadeNode,sizeof(ticket));
    const bool valid=node->changed[0]==sizeof(ticket) && ticket.queue_epoch==actor_fade_queue_epoch &&
        actor_fade_queue_pending && frame_ready && !stream_aborted && draining_parts &&
        draining_list==PVR_LIST_TR_POLY && !actor_fade_reserved.node;
#if RE4DC_ACTOR_TRANSACTION_DIAG
    re4dc_log("AFD_FIFO actor ep=%u q=%u s=%u node=%p next=%p valid=%u\n",actor_fade_queue_epoch,ticket.sequence,ticket.model.serial,node,node->next,unsigned(valid));
#endif
    deferred_first=node->next;
    if(!valid){actor_fade_queue_failure();return true;}
    --actor_fade_queue_pending;
    const unsigned epoch=actor_fade_queue_epoch;
    const int result=re4dc_actor_death_fade_drain(ticket);
    if(result!=1 || epoch!=actor_fade_queue_epoch || !frame_ready || stream_aborted)actor_fade_queue_failure();
    return true;
}
}
extern "C" int re4dc_model_actor_fade_reserve(Re4dcActorFadeReservation* out) {
    if(!out || out->node || out->epoch || actor_fade_reserved.node)return actor_fade_queue_failure();
    if(!frame_ready || stream_aborted || !actor_fade_queue_epoch)return actor_fade_queue_failure();
    if(draining_parts || source_draws_finished || direct_open)return 0;
    unsigned char* storage=frame_storage;unsigned* top=&deferred_top;
    const unsigned keep=std::max(8192u,nquad*unsigned(sizeof(Re4dcUiQuad)));
    if(kActorFadeBytes>deferred_top || deferred_top-kActorFadeBytes<keep) {
        if(!deferred_spill) {
            deferred_spill=static_cast<unsigned char*>(re4dc_model_deferred_storage(&deferred_spill_capacity));
            deferred_spill_top=deferred_spill_capacity;
        }
        if(!deferred_spill || kActorFadeBytes>deferred_spill_top)return 0;
        storage=deferred_spill;top=&deferred_spill_top;
    }
    actor_fade_old_top=*top;*top-=kActorFadeBytes;
    actor_fade_reserved_top=top;actor_fade_reserved_tail=deferred_last;
    actor_fade_reserved={storage+*top,actor_fade_queue_epoch};*out=actor_fade_reserved;
    return 1;
}
extern "C" int re4dc_model_actor_fade_cancel(Re4dcActorFadeReservation* r) {
    if(!r || !actor_fade_reservation_current(*r))return actor_fade_queue_failure();
    *actor_fade_reserved_top=actor_fade_old_top;
    actor_fade_reserved={};actor_fade_reserved_top=nullptr;*r={};return 1;
}
extern "C" int re4dc_model_actor_fade_commit(Re4dcActorFadeReservation* r,const Re4dcActorFadeTicket* ticket) {
    if(!r || !ticket || !actor_fade_reservation_current(*r) ||
       ticket->queue_epoch!=r->epoch || !ticket->sequence || !frame_ready || stream_aborted ||
       draining_parts || source_draws_finished || direct_open)return actor_fade_queue_failure();
    auto* node=new(r->node) DeferredPart{};node->lighting=kActorFadeTag;node->changed[0]=sizeof(*ticket);
    std::memcpy(reinterpret_cast<unsigned char*>(node)+kActorFadeNode,ticket,sizeof(*ticket));
#if RE4DC_ACTOR_TRANSACTION_DIAG
    actor_fade_queue_seen=true;
    re4dc_log("AFD_FIFO enqueue ep=%u q=%u s=%u node=%p prev=%p\n",actor_fade_queue_epoch,ticket->sequence,ticket->model.serial,node,deferred_last);
#endif
    if(deferred_last)deferred_last->next=node;else deferred_first=node;
    deferred_last=node;++deferred_count;++actor_fade_queue_pending;
    actor_fade_reserved={};actor_fade_reserved_top=nullptr;*r={};
    deferred_peak=std::max(deferred_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    frame_queue_peak=std::max(frame_queue_peak,unsigned(sizeof(frame_storage))-deferred_top+deferred_spill_capacity-deferred_spill_top);
    return 1;
}
