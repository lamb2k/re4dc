// Build32 current-image presentation, initially the existing cabin Luis class.
// Only copied identities survive a callback. Pose, infos and palettes are
// reproved/rebuilt by the ordinary registry transaction on every new image.
#if !RE4DC_ACTOR_TRANSACTION || !RE4DC_COARSE_SOURCE_ACTORS || !RE4DC_ACTOR_SKIN_RESERVE || \
    RE4DC_NATIVE_MODEL_REGISTRY != 1 || !RE4DC_NATIVE_MODEL_REGISTRY_PACK || !RE4DC_ROUTE_CH22 || \
    RE4DC_ACTOR_SKIN_OWNER_POOL
#error ACTOR_PRESENTATION32 requires the shared-table cabin registry transaction profile
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
#error ACTOR_PRESENTATION32 and SKIN_RECIPE32 require a separate joint source-credit qualification
#endif
extern "C" int re4dc_registry_presentation32_class(const cModel*);
namespace {
bool sourceActorPresentation32Active;
struct SourceActorPresentation32Scope {
    bool previous;unsigned epoch;
    SourceActorPresentation32Scope():previous(sourceActorPresentation32Active),epoch(sourceActorEpoch) {
        sourceActorPresentation32Active=true;
    }
    ~SourceActorPresentation32Scope() {
        sourceActorPresentation32Active=previous && epoch==sourceActorEpoch;
    }
};
struct SourceActorPresentation32 {
    FrameIdentity frame{};ModelIdentity model{};
    std::uintptr_t primitive=0;
    unsigned bytes=0,buffer=0,choice=0;
};
SourceActorPresentation32 partnerPresentation32;
void sourceActorPresentation32Retire(){sourceActorPresentation32Active=false;}
bool partnerPresentation32Address(const cModel* m) {
    return m && partnerPresentation32.model.address==reinterpret_cast<std::uintptr_t>(m) &&
        partnerPresentation32.frame.frame==unsigned(pG->Frame_cnt) &&
        partnerPresentation32.frame.primitive_epoch==sourceActorEpoch;
}
}
extern "C" int re4dc_actor_presentation32_required(const cModel* m) {
    if(!sourceActorPresentation32Active)return 0;
    // A recorded address cannot become a source fallback after replacement or
    // a mid-image change of ledger domain, even if it is no longer pSUB.
    if(partnerPresentation32Address(m))return 1;
    return !sourceActorActive && m && m==(const cModel*)pSUB && sourceActorRam(m) && m->id==4u;
}
namespace {
int partnerPresentation32Identity(cModel* m,FrameIdentity* frame,ModelIdentity* model) {
    if(!re4dc_actor_presentation32_required(m))return 0;
    if(sourceActorActive || m!=(cModel*)pSUB || !sourceActorRam(m) ||
       !(m->be_flag&1u) || !re4dc_registry_presentation32_class(m))return -1;
    FrameIdentity now{};
    if(!sourceActorIdentity(now) || !pG->prim_cnt || !pG->nPrim || unsigned(pG->vtx_buf_no)>1u)return -1;
    const ModelIdentity id=sourceActorModel(m);
    const auto primitive=reinterpret_cast<std::uintptr_t>(pG->prim_cnt);
    auto& e=partnerPresentation32;
    if(e.model.address && e.frame.frame==now.frame && e.frame.primitive_epoch==now.primitive_epoch) {
        // Same image: a room/manager/model/primitive change is a refusal, not
        // permission to reset a sticky choice and draw a recycled address.
        if(!(e.frame==now && e.model==id) || e.primitive!=primitive ||
           e.bytes!=unsigned(pG->nPrim) || e.buffer!=unsigned(pG->vtx_buf_no))return -1;
    } else {
        e={now,id,primitive,unsigned(pG->nPrim),unsigned(pG->vtx_buf_no),0};
    }
    if(frame)*frame=now;
    if(model)*model=id;
    return 1;
}
}
