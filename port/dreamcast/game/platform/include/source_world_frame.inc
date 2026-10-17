// Current accepted registrations, not a visibility/lifetime replacement.
// All borrowed objects are revisited synchronously before the first native draw.
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" int re4dc_ui_movie_texture();
extern "C" int re4dc_ss_ui_order();
extern "C" unsigned re4dc_ui_frame();
#include "re4dc_platform.h"
#include "source_world_memory.inc"
namespace {
constexpr unsigned kSourceWorldCallbacks=90;
struct SourceWorldEntry { cModel* model;unsigned serial,work;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    const void* node=nullptr;const void* next=nullptr;unsigned table=0,kind=0;bool consumed=false;
#endif
};
struct SourceWorldFrame {
    unsigned native=0,source=0,room_generation=0,package_generation=0,objects=0,pools=0;
    unsigned long prim=0,begin=0,end=0;
    unsigned bytes=0,buffer=0,prim_generation=0,ot_epoch=0,count=0;
    bool active=false,ready=false,started=false,failed=false;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    unsigned role=0,system=0,stop=0,disp=0,used=0,consumed=0,member_reason=0;
    bool coarse=false,withheld=false,committed=false,guarded=false,sealed=false;
    unsigned proven=0; // TRANSITION_OWNER: native frame whose first owned callback passed the full revalidation
    unsigned sample=~0U,anchor=~0U;bool uv_valid[2]{};float uv[2][2]{};
    cModel* group[kSourceWorldCallbacks]{};
#endif
    SourceWorldEntry entries[kSourceWorldCallbacks]{};
} sourceWorldFrame;
bool sourceWorldRenderActive;
unsigned sourceWorldPrimGeneration;
unsigned sourceWorldReports,sourceWorldFailures;
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
// Scalar observers only. CardMainTask owns System_flg 0x1000 until its objects
// and layouts are retired. Observe in r200, then record four native frames once.
struct SourceWorldDiagnostic {
    bool armed=false,used=false,active=false,done=false,draw_observed=false;
    unsigned first=0,native=0,field=0,reason=0,memory=0;
    const char* stage="idle";
    const void* model=nullptr;unsigned serial=0,work=~0U,table=~0U;int probe=0;
    void begin(unsigned frame,bool in_room,bool card) {
        active=false;native=frame;field=reason=memory=0;stage="prepare";draw_observed=false;
        model=nullptr;serial=0;work=table=~0U;probe=0;
        if(done)return;
        if(!in_room){armed=false;if(used)done=true;return;}
        if(!used){
            if(card){armed=true;return;}
            if(!armed)return;
            used=true;first=frame;
        }
        // Unsigned subtraction handles frame wrap; the window never re-arms.
        active=unsigned(frame-first)<4U;if(!active)done=true;
    }
} sourceWorldDiagnostic;
bool sourceWorldDiagTest(bool ok,unsigned field) {
    if(!ok && sourceWorldDiagnostic.active)sourceWorldDiagnostic.field=field;
    return ok;
}
void sourceWorldDiagStage(const char* stage) {
    if(sourceWorldDiagnostic.active)sourceWorldDiagnostic.stage=stage;
}
#define RE4DC_SOURCE_DIAG_TEST(test,field) sourceWorldDiagTest((test),(field))
#define RE4DC_SOURCE_DIAG_STAGE(stage) sourceWorldDiagStage(stage)
#else
#define RE4DC_SOURCE_DIAG_TEST(test,field) (test)
#define RE4DC_SOURCE_DIAG_STAGE(stage) ((void)0)
#endif
#if RE4DC_PS2_WORLD_TRANSITION_PIN
// gameDoordemo (Rno0 4) still presents the old room while fading. Its source
// callback set is not a play-frame ticket. Retaining an existing native texture
// is separately qualified and never admits that callback set.
bool sourceWorldTransitionContext(unsigned native,unsigned generation) {
    unsigned rg=0,c=0,b=0,s=0,retired=0,pg=0;
    return pG && pG->Rno0==4 && G_ROOM_ID==0x200 &&
        !(pG->System_flg&(0x100000U|0x1000U)) &&
        !(pG->Status_flg[2]&0x04000000U) && !(pG->Status_flg[1]&0x100U) &&
        !re4dc_coarse_image && !re4dc_pace_skipping &&
        !re4dc_ui_movie_texture() && !re4dc_ss_ui_order() &&
        native==re4dc_ui_frame() && generation &&
        re4dc_room4_state(&rg,&c,&b,&s,&retired) && rg &&
        re4dc_ps2_source_package(&pg) && pg==generation;
}
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
unsigned sourceWorldTransitionReports,sourceWorldTransitionFailures;
unsigned sourceWorldTransitionRole(unsigned* reason=nullptr) {
    if(reason)*reason=0;
#define RE4DC_TRANSITION_CONTEXT(test,code) if(!(test)){if(reason)*reason=code;return 0;}
    RE4DC_TRANSITION_CONTEXT(pG && pG->Rno0==4 && G_ROOM_ID==0x200,1)
    RE4DC_TRANSITION_CONTEXT(!(pG->System_flg&(0x100000U|0x1000U)),2)
    RE4DC_TRANSITION_CONTEXT(!(pG->Status_flg[2]&0x04000000U),3)
    RE4DC_TRANSITION_CONTEXT(!(pG->Status_flg[1]&0x100U),4)
    RE4DC_TRANSITION_CONTEXT(!re4dc_coarse_image,5)
    RE4DC_TRANSITION_CONTEXT(!re4dc_pace_skipping,6)
    RE4DC_TRANSITION_CONTEXT(!re4dc_ui_movie_texture(),7)
    RE4DC_TRANSITION_CONTEXT(!re4dc_ss_ui_order(),8)
#undef RE4DC_TRANSITION_CONTEXT
    return pG->System_flg&0x01000000U?2U:1U;
}
unsigned sourceWorldScheduledTables() {
#if defined(RE4DC_OT_MASK) && RE4DC_OT_MASK == 1
    return g_OtUsed&((1U<<0x0b)|(1U<<0x0d)|(1U<<0x10)|(1U<<0x11));
#else
    // OT_MASK=2 is diagnostic: it still executes the observed table.
    return (1U<<0x0b)|(1U<<0x0d)|(1U<<0x10)|(1U<<0x11);
#endif
}
bool sourceWorldTransitionPhasesCurrent() {
    const auto& f=sourceWorldFrame;
    const unsigned indices[2]={f.anchor,f.sample};
    for(unsigned which=0;which<2;++which)if(f.uv_valid[which]){
        if(indices[which]>=f.count)return false;
        const auto& e=f.entries[indices[which]];float phase[2]{};
        if(!re4dc_r200_scroll_member(e.model,e.serial,e.work,phase) ||
           phase[0]!=f.uv[which][0] || phase[1]!=f.uv[which][1])return false;
    }
    return true;
}
bool sourceWorldTransitionIdentity() {
    const auto& f=sourceWorldFrame;
    return f.role && f.native==re4dc_ui_frame() && !f.coarse && sourceWorldTransitionRole()==f.role &&
        unsigned(pG->System_flg)==f.system && unsigned(pG->Stop_flg)==f.stop &&
        unsigned(pG->Disp_flg)==f.disp && sourceWorldScheduledTables()==f.used;
}
#endif
bool sourceWorldContext() {
    return RE4DC_SOURCE_DIAG_TEST(pG,1) && RE4DC_SOURCE_DIAG_TEST(pG->Rno0==3,2) &&
        RE4DC_SOURCE_DIAG_TEST(G_ROOM_ID==0x200,3) && RE4DC_SOURCE_DIAG_TEST(pG->System_flg&0x400,4) &&
        // SceEventStart's 0x800 is not a movie exclusion; source OTs still run.
        RE4DC_SOURCE_DIAG_TEST(!(pG->System_flg&0x100000),5) &&
        RE4DC_SOURCE_DIAG_TEST(!(pG->Status_flg[2]&0x04000000),6) &&
        RE4DC_SOURCE_DIAG_TEST(!(pG->Status_flg[1]&0x100),7) &&
        RE4DC_SOURCE_DIAG_TEST(!re4dc_coarse_image,8) && RE4DC_SOURCE_DIAG_TEST(!re4dc_pace_skipping,9) &&
        RE4DC_SOURCE_DIAG_TEST(!re4dc_ui_movie_texture(),10) && RE4DC_SOURCE_DIAG_TEST(!re4dc_ss_ui_order(),11);
}
void sourceWorldFail(unsigned reason) {
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    if(sourceWorldDiagnostic.active)sourceWorldDiagnostic.reason=reason;
#endif
    ++sourceWorldFailures;
    if(sourceWorldFailures<=16 || !(re4dc_ui_frame()%120))
        re4dc_log("PS2SOURCE_DECLINE f=%u reason=%u count=%u\n",re4dc_ui_frame(),reason,sourceWorldFailures);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    const auto& f=sourceWorldFrame;
    if(f.role && (++sourceWorldTransitionFailures<=16 || !(re4dc_ui_frame()%120)))
        re4dc_log("PS2TRANSITION_DECLINE f=%u role=%u reason=%u member=%u callbacks=%u consumed=%u started=%u withheld=%u\n",
            re4dc_ui_frame(),f.role,reason,f.member_reason,f.count,f.consumed,unsigned(f.started),unsigned(f.withheld));
#endif
    sourceWorldFrame.active=false;sourceWorldFrame.ready=false;
}
// reason12 subcodes: 1 primitive metadata, 2 primitive owner, 3 cursor,
// 4 OT metadata, 5 OT owner, 6 node bounds, 7 walk limit, 8 OT epoch.
void sourceWorldMemoryFail(unsigned sub,unsigned table,unsigned long address,unsigned bytes) {
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    if(sourceWorldDiagnostic.active)sourceWorldDiagnostic.memory=sub;
#endif
    if(sourceWorldFailures<16 || !(re4dc_ui_frame()%120)) {
        Re4dcSourceWorldOtMemory memory{};re4dc_source_world_ot_memory(&memory);
        re4dc_log("PS2SOURCE_MEMORY f=%u sub=%u table=%x addr=%08lx bytes=%u retained=%u:%08lx-%08lx epoch=%u/%u\n",
            re4dc_ui_frame(),sub,table,address,bytes,memory.live,memory.begin,memory.end,sourceWorldFrame.ot_epoch,memory.epoch);
    }
    sourceWorldFail(12);
}
void sourceWorldAbort(unsigned reason) {
    if(sourceWorldFrame.failed)return;
    sourceWorldFrame.failed=true;sourceWorldFail(reason);re4dc_model_packet_abort();
}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
bool sourceWorldCapturedStorageCurrentFull();
// After the frame's first owned callback passed the full proof (f.proven), the captured storage is proven by its
// epochs plus the light (walk-free) member storage check; TRANSITION_XCHECK compares it with the full check.
bool sourceWorldCapturedStorageCurrent() {
#if RE4DC_ATCHK_LIST
    const auto& f=sourceWorldFrame;unsigned rg=0,c,b,stale,refused,pg=0;
    if(f.guarded && f.proven==f.native){
        const bool light=sourceWorldPrimGeneration==f.prim_generation && re4dc_source_world_ot_epoch()==f.ot_epoch &&
            re4dc_alive_gen[2]==f.objects && re4dc_alive_gen[0]==f.pools &&
            re4dc_room4_state(&rg,&c,&b,&stale,&refused) && rg==f.room_generation &&
            re4dc_ps2_source_group_package(&pg,0) && pg==f.package_generation && re4dc_r200_scroll_storage_current_light();
#if RE4DC_TRANSITION_GATE_DIAG
        if(!light){static unsigned ll;if(ll<6){++ll;unsigned g2=0,pg2=0,c2,b2,s2,r2;
            re4dc_log("TGD light f=%u prim=%d ot=%d obj=%d pools=%d room=%d pkg=%d storage=%d consumed=%u\n",f.native,
              int(sourceWorldPrimGeneration==f.prim_generation),int(re4dc_source_world_ot_epoch()==f.ot_epoch),
              int(re4dc_alive_gen[2]==f.objects),int(re4dc_alive_gen[0]==f.pools),
              int(re4dc_room4_state(&g2,&c2,&b2,&s2,&r2) && g2==f.room_generation),
              int(re4dc_ps2_source_group_package(&pg2,0) && pg2==f.package_generation),re4dc_r200_scroll_storage_current_light(),f.consumed);}}
#endif
#if RE4DC_TRANSITION_XCHECK
        static unsigned xs,xsbad;++xs;
        auto& fm=sourceWorldFrame;const unsigned pv=fm.proven;fm.proven=0;re4dc_r200_set_light(0);
        const bool full=sourceWorldCapturedStorageCurrentFull();
        fm.proven=pv;re4dc_r200_set_light(1);
        if(full!=light){++xsbad;re4dc_log("XCHK storage bad f=%u light=%d full=%d\n",f.native,int(light),int(full));}
        if(!(xs%64))re4dc_log("XCHK storage f=%u checks=%u bad=%u\n",f.native,xs,xsbad);
        return light && full;
#else
        return light;
#endif
    }
#endif
    return sourceWorldCapturedStorageCurrentFull();
}
bool sourceWorldCapturedStorageCurrentFull() {
    const auto& f=sourceWorldFrame;unsigned rg=0,c,b,stale,refused,pg=0;
    if(!f.guarded)return true;
    if(sourceWorldPrimGeneration!=f.prim_generation || re4dc_source_world_ot_epoch()!=f.ot_epoch ||
       re4dc_alive_gen[2]!=f.objects || re4dc_alive_gen[0]!=f.pools ||
       !sourceWorldAllocated(reinterpret_cast<const void*>(f.prim),f.bytes*RE4DC_PRIMITIVE_BUFFERS,true) ||
       !re4dc_room4_state(&rg,&c,&b,&stale,&refused) || rg!=f.room_generation ||
       !re4dc_ps2_source_group_package(&pg,0) || pg!=f.package_generation ||
       !re4dc_r200_scroll_storage_current())return false;
    // Check bucket ownership without following any captured node links.
    for(const auto& ot:g_OtWork){
        if(!ot.list && !ot.max)continue;
        if(!ot.list || !ot.max || ot.max>4096)return false;
        const unsigned bytes=unsigned(ot.max)*sizeof(OtData);
        if(!sourceWorldAllocated(ot.list,bytes,true) && !re4dc_source_world_ot_retained(ot.list,bytes))return false;
    }
    return true;
}
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
bool sourceWorldIdentity(unsigned native,unsigned generation,bool deep=true) {
#if RE4DC_ATCHK_LIST
    if(sourceWorldFrame.proven==sourceWorldFrame.native && sourceWorldFrame.proven)deep=false;
#endif
#else
bool sourceWorldIdentity(unsigned native,unsigned generation) {
#endif
    const auto& f=sourceWorldFrame;unsigned rg=0,c,b,s,r,pg=0;
    return RE4DC_SOURCE_DIAG_TEST(f.active,20) &&
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        (f.role?sourceWorldTransitionIdentity():sourceWorldContext()) &&
#else
        sourceWorldContext() &&
#endif
        RE4DC_SOURCE_DIAG_TEST(native==f.native,21) && RE4DC_SOURCE_DIAG_TEST(generation==f.package_generation,22) &&
        RE4DC_SOURCE_DIAG_TEST(unsigned(pG->Frame_cnt)==f.source,23) &&
        RE4DC_SOURCE_DIAG_TEST(static_cast<unsigned long>(pG->prim_cnt)==f.prim,24) &&
        RE4DC_SOURCE_DIAG_TEST(unsigned(pG->nPrim)==f.bytes,25) && RE4DC_SOURCE_DIAG_TEST(unsigned(pG->vtx_buf_no)==f.buffer,26) &&
        RE4DC_SOURCE_DIAG_TEST(sourceWorldPrimGeneration==f.prim_generation,27) &&
        RE4DC_SOURCE_DIAG_TEST(re4dc_source_world_ot_epoch()==f.ot_epoch,28) &&
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        (!f.role || (f.proven==f.native && f.proven) || sourceWorldAllocated(reinterpret_cast<const void*>(f.prim),f.bytes*RE4DC_PRIMITIVE_BUFFERS,true)) &&
#endif
        RE4DC_SOURCE_DIAG_TEST(reinterpret_cast<unsigned long>(GXWORK()->prim)>=f.end,29) &&
        RE4DC_SOURCE_DIAG_TEST(reinterpret_cast<unsigned long>(GXWORK()->prim)-f.begin<=f.bytes,30) &&
        RE4DC_SOURCE_DIAG_TEST(re4dc_alive_gen[2]==f.objects,31) && RE4DC_SOURCE_DIAG_TEST(re4dc_alive_gen[0]==f.pools,32) &&
        RE4DC_SOURCE_DIAG_TEST(re4dc_room4_state(&rg,&c,&b,&s,&r),33) && RE4DC_SOURCE_DIAG_TEST(rg==f.room_generation,34) &&
        RE4DC_SOURCE_DIAG_TEST(
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        f.role?re4dc_ps2_source_group_package(&pg,deep):
#endif
        re4dc_ps2_source_package(&pg),35) && RE4DC_SOURCE_DIAG_TEST(pg==f.package_generation,36)
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        && (!f.role || (re4dc_ps2_source_group_package(&pg,deep) && pg==f.package_generation &&
            (!deep || (re4dc_r200_scroll_group() && sourceWorldTransitionPhasesCurrent()))))
#endif
        ;
}
bool sourceWorldWalk(bool publish) {
    auto& f=sourceWorldFrame;unsigned count=0;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    unsigned sample=~0U,anchor=~0U;
#endif
    if(re4dc_source_world_ot_epoch()!=f.ot_epoch){sourceWorldMemoryFail(8,~0U,0,0);return false;}
    // ModelTrans registers the current source callbacks into raw tables
    // 0x0b (direct), 0x0d (model depth), 0x10 (after render), 0x11 (world depth).
    // Keep this order identical to Render's scopes. The descriptive
    // OT_TYPE_SCROLL/MODEL aliases name different tables in trans_ot.h.
    const unsigned tables[4]={0x0b,0x0d,0x10,0x11};
    for(unsigned table:tables){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(f.role && !(f.used&(1U<<table)))continue;
#endif
        const auto& ot=g_OtWork[table];if(!ot.list && !ot.max)continue;
        const auto buckets=reinterpret_cast<unsigned long>(ot.list);
        if(!ot.list || !ot.max || ot.max>4096 || buckets%alignof(OtData)) {
            sourceWorldMemoryFail(4,table,buckets,0);return false;
        }
        const unsigned bytes=unsigned(ot.max)*sizeof(OtData);
        if(!sourceWorldAllocated(ot.list,bytes,true) && !re4dc_source_world_ot_retained(ot.list,bytes)) {
            sourceWorldMemoryFail(5,table,buckets,bytes);return false;
        }
        unsigned visited=0;
        for(auto* node=&ot.list[ot.max-1];node;node=node->next){
            const auto address=reinterpret_cast<unsigned long>(node);
            const bool bucket=address>=buckets && address-buckets<unsigned(ot.max)*sizeof(OtData) &&
                (address-buckets)%sizeof(OtData)==0;
            const bool primitive=address>=f.begin && address<=f.end &&
                !(address&31UL) && sizeof(OtPrim)<=f.end-address;
            // next is read only after this iteration proved the complete node.
            if(++visited>4096){sourceWorldMemoryFail(7,table,address,sizeof(OtPrim));return false;}
            if(!bucket && !primitive){sourceWorldMemoryFail(6,table,address,sizeof(OtPrim));return false;}
            if(!node->data || node->func!=(void (*)(void*))ModelRender){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
                // Before the two samples, only known source-world callbacks
                // may run: an unknown callback can close OP or alter the group.
                if(f.role && anchor==~0U && node->func){sourceWorldFail(20);return false;}
#endif
                continue;
            }
            auto* model=static_cast<cModel*>(node->data);
            unsigned serial=0,work=~0U;
            const int accepted=
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
                f.role?re4dc_r200_scroll_probe(model,&serial,&work):
#endif
                re4dc_scroll_source_probe(model,&serial,&work);
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
            if(sourceWorldDiagnostic.active){auto& d=sourceWorldDiagnostic;d.model=model;d.serial=serial;d.work=work;d.table=table;d.probe=accepted;}
#endif
            if(accepted<0){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
                if(f.role)f.member_reason=re4dc_scroll_source_member_field();
#endif
                sourceWorldFail(4);return false;
            }
            if(!accepted){
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
                if(f.role && anchor==~0U){sourceWorldFail(20);return false;}
#endif
                continue;
            }
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            if(f.role){
                if(node->kind!=2 || (table!=0x0b && table!=0x10)){
                    sourceWorldFail(14);return false;
                }
                if(work==16){
                    if(sample!=~0U || table!=0x0b || model->ot_type!=2){sourceWorldFail(20);return false;}
                    sample=count;
                }
                if(work==10){
                    if(anchor!=~0U || sample==~0U || table!=0x0b || model->ot_type!=3){sourceWorldFail(20);return false;}
                    anchor=count;
                }
            }
#endif
            if(count>=kSourceWorldCallbacks){sourceWorldFail(2);return false;}
            for(unsigned i=0;i<count;++i)if(f.entries[i].model==model){sourceWorldFail(3);return false;}
            if(publish)f.entries[count]={model,serial,work};
            else if(count>=f.count || f.entries[count].model!=model || f.entries[count].serial!=serial ||
                    f.entries[count].work!=work){sourceWorldFail(9);return false;}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
            if(f.role){
                auto& entry=f.entries[count];
                if(publish){entry.node=node;entry.next=node->next;entry.table=table;entry.kind=node->kind;entry.consumed=false;}
                else if(entry.node!=node || entry.table!=table || entry.kind!=node->kind){sourceWorldFail(15);return false;}
            }
#endif
            ++count;
        }
    }
    if(publish)f.count=count;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role){
        if(publish){f.sample=sample;f.anchor=anchor;}
        if(sample==~0U || anchor==~0U || sample>=anchor || sample!=f.sample || anchor!=f.anchor){sourceWorldFail(20);return false;}
    }
#endif
    return RE4DC_SOURCE_DIAG_TEST(count!=0,40) && RE4DC_SOURCE_DIAG_TEST(count==f.count,41);
}
struct SourceWorldRenderScope {
    bool previous;
    explicit SourceWorldRenderScope():previous(sourceWorldRenderActive){sourceWorldRenderActive=true;}
    ~SourceWorldRenderScope(){
        auto& f=sourceWorldFrame;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(!f.failed && (
            f.withheld ||
            f.started) && (!sourceWorldIdentity(f.native,f.package_generation) || !sourceWorldWalk(false)))sourceWorldAbort(11);
#else
        if(f.started && !f.failed && f.native==re4dc_ui_frame() &&
           (!sourceWorldIdentity(f.native,f.package_generation) || !sourceWorldWalk(false)))sourceWorldAbort(11);
#endif
        sourceWorldRenderActive=previous;
    }
};
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
bool sourceWorldGroupPointer(const cModel* model){
    for(auto* pointer:sourceWorldFrame.group)if(pointer==model)return true;
    return false;
}
SourceWorldEntry* sourceWorldCaptured(cModel* model) {
    auto& f=sourceWorldFrame;
    for(unsigned i=0;i<f.count;++i)if(f.entries[i].model==model)return &f.entries[i];
    return nullptr;
}
bool sourceWorldCallbackMatches(const SourceWorldEntry& entry) {
    Re4dcSourceWorldCallback current{};
    return re4dc_source_world_callback_current(&current) && current.callback_depth==1 &&
        current.model_depth==1 && current.table==entry.table && current.node==entry.node &&
        current.func==reinterpret_cast<void(*)(void*)>(ModelRender) &&
        current.data==entry.model && current.kind==entry.kind;
}
bool sourceWorldModelAborted(const cModel* model) {
    const auto& f=sourceWorldFrame;
    return f.role && f.failed && sourceWorldGroupPointer(model);
}
bool sourceWorldModelBlocked(cModel* model) {
    auto& f=sourceWorldFrame;
    if(!f.role)return false;
    if(f.guarded && !sourceWorldCapturedStorageCurrent()){f.withheld=true;sourceWorldAbort(16);return true;}
    Re4dcSourceWorldCallback call{};
    if((f.active || f.guarded || f.withheld || f.started || f.failed) && re4dc_source_world_callback_current(&call) &&
       sourceWorldGroupPointer(static_cast<cModel*>(call.data)) &&
       (call.data!=model || call.callback_depth!=1 || call.model_depth!=1)){
        if(f.withheld || f.started){sourceWorldAbort(16);return true;}
        sourceWorldFail(16);return true;
    }
    if(!sourceWorldGroupPointer(model))return false;
    if(f.active && !(f.proven==f.native && f.proven) && (!re4dc_source_world_pool(model,0) ||
       !re4dc_source_world_pool(model->pModelInfo,2) || !re4dc_source_world_pool(model->pList,3))){
        // A captured source payload whose owner retired is unsafe even before
        // the first native draw. Refusing the ticket cannot dereference it via GC.
        f.withheld=true;sourceWorldAbort(16);return true;
    }
    if(f.native!=re4dc_ui_frame()){
        if(f.started || f.withheld || f.failed){sourceWorldAbort(16);return true;}
        return false;
    }
    if(f.failed)return true;
    if(!f.active)return false;
    const auto* entry=sourceWorldCaptured(model);unsigned work=~0U;
    if(!entry){
        if(f.started || f.withheld){sourceWorldAbort(16);return true;}
        sourceWorldFail(16);return false;
    }
    if(!sourceWorldRenderActive || !sourceWorldIdentity(f.native,f.package_generation) ||
       !sourceWorldCallbackMatches(*entry) || entry->consumed ||
       !re4dc_scroll_source_transition_member(model,entry->serial,&work,&f.member_reason) || work!=entry->work){
        if(f.started || f.withheld){sourceWorldAbort(16);return true;}
        sourceWorldFail(16);return false;
    }
    return false;
}
#endif
bool sourceWorldCandidate(cModel* model) {
    const auto& f=sourceWorldFrame;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role && f.native!=re4dc_ui_frame() && (f.started || f.withheld || f.failed)){
        sourceWorldAbort(16);return sourceWorldCaptured(model)!=nullptr;
    }
#endif
    if(!sourceWorldRenderActive || f.native!=re4dc_ui_frame())return false;
    if(f.started && !f.failed && !sourceWorldIdentity(f.native,f.package_generation))sourceWorldAbort(11);
    if(f.failed) {
        // Once this image was suppressed, captured pointer values suffice to
        // keep refusing it. A retired pointer must never be read to do that.
        for(unsigned i=0;i<f.count;++i)if(f.entries[i].model==model)return true;
        return false;
    }
    if(!f.ready || !sourceWorldIdentity(f.native,f.package_generation))return false;
    for(unsigned i=0;i<f.count;++i)if(f.entries[i].model==model) {
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        if(f.role && (!sourceWorldCallbackMatches(f.entries[i]) || f.entries[i].consumed)){
            if(f.started || f.withheld){sourceWorldAbort(16);return true;}
            sourceWorldFail(16);return false;
        }
#endif
        unsigned work=~0U;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        unsigned reason=0;
        const bool member=f.role?re4dc_scroll_source_transition_member(model,f.entries[i].serial,&work,&reason):
            re4dc_scroll_source_member(model,f.entries[i].serial,&work);
        if(member && work==f.entries[i].work)return true;
        sourceWorldFrame.member_reason=reason;
#else
        if(re4dc_scroll_source_member(model,f.entries[i].serial,&work) && work==f.entries[i].work)return true;
#endif
        if(f.started){sourceWorldAbort(5);return true;}
        sourceWorldFail(5);return false;
    }
    return false;
}
int sourceWorldDraw(cModel* model) {
    if(!sourceWorldCandidate(model))return 0;
    auto& f=sourceWorldFrame;
    if(f.failed)return -1;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role){
        auto* entry=sourceWorldCaptured(model);float uv[2]{};
        // Full revalidation (identity incl. the deep package hashes, the whole OT walk, this member) on the frame's
        // first owned callback only. Later callbacks prove their own entry (OT node + next link, member fingerprint)
        // and that nothing frame-wide moved: the O(1) epochs in identity (alive_gen[0]/[2], OT epoch, prim
        // generation and cursor, room4 / package generation; GAME_ATCHK_LIST bumps alive_gen). The full walk per
        // callback cost ~78 x 78 pool walks and stalled the 2-3 -> 3-1 frame past the 30 s watchdog.
        // TRANSITION_XCHECK=1 (test only) also runs the full check on every callback and logs disagreements.
        const auto fullCheck=[&]()->bool{
            return entry && !entry->consumed && sourceWorldIdentity(f.native,f.package_generation) &&
                sourceWorldWalk(false) && re4dc_r200_scroll_member(model,entry->serial,entry->work,uv);
        };
#if RE4DC_ATCHK_LIST
        const auto fastCheck=[&]()->bool{
            const auto* node=entry?static_cast<const OtData*>(entry->node):nullptr;
            return entry && !entry->consumed && node && node->data==model && node->next==entry->next &&
                node->func==(void (*)(void*))ModelRender && sourceWorldIdentity(f.native,f.package_generation,false) &&
                re4dc_r200_scroll_member_light(model,entry->serial,entry->work,uv);
        };
        const bool fast=f.proven==f.native;
        bool valid=fast?fastCheck():fullCheck();
#if RE4DC_TRANSITION_XCHECK
        if(fast){
            static unsigned xchecks,xbad;++xchecks;
            auto& fm=sourceWorldFrame;const unsigned pv=fm.proven;fm.proven=0;re4dc_r200_set_light(0);
            const bool full=fullCheck();
            fm.proven=pv;re4dc_r200_set_light(1);
            if(full!=valid){++xbad;re4dc_log("XCHK bad f=%u work=%u fast=%d full=%d\n",f.native,entry?entry->work:~0U,int(valid),int(full));}
            if(!(xchecks%64))re4dc_log("XCHK f=%u checks=%u bad=%u\n",f.native,xchecks,xbad);
            valid=valid && full;
        }
#endif
        if(valid && !fast){f.proven=f.native;re4dc_r200_set_light(1);}
#else
        const bool valid=fullCheck();
#endif
        if(!valid || (!f.started && !re4dc_source_world_op_window())){
            if(f.withheld || f.started){sourceWorldAbort(21);return -1;}
            sourceWorldFail(21);return 0;
        }
        // The first withheld callback claims the whole source group. Any later
        // invalidity aborts the image; no source/dyn fallback may resume.
        f.withheld=true;entry->consumed=true;++f.consumed;
#if RE4DC_TRANSITION_GATE_DIAG
        {static unsigned dl;if(dl<200){++dl;re4dc_log("TGD own f=%u work=%u consumed=%u\n",f.native,entry->work,f.consumed);}}
#endif
        if(entry->work==16){f.uv[1][0]=uv[0];f.uv[1][1]=uv[1];f.uv_valid[1]=true;}
        if(entry->work==10){
            if(!f.uv_valid[1] || f.started){sourceWorldAbort(21);return -1;}
            f.uv[0][0]=uv[0];f.uv[0][1]=uv[1];f.uv_valid[0]=true;
            // Mark started before the yielding draw so its claim remains
            // latched even if the native/source identity changes inside bind.
            f.started=true;
#if RE4DC_TRANSITION_GATE_DIAG
            re4dc_log("TGD draw begin f=%u\n",f.native);
            {const int dr=re4dc_ps2_source_draw(f.package_generation);re4dc_log("TGD draw end f=%u result=%d\n",f.native,dr);
             if(dr!=1){sourceWorldAbort(6);return -1;}}
#else
            if(re4dc_ps2_source_draw(f.package_generation)!=1){sourceWorldAbort(6);return -1;}
#endif
        }
        return 1;
    }
#endif
    // Revalidate the complete accepted set before any PS2 header; a changed
    // sibling is a whole-frame refusal, never a silent per-object omission.
    if(!f.started && !sourceWorldWalk(false))return 0;
    unsigned work=~0U;
    unsigned serial=0;
    for(unsigned i=0;i<f.count;++i)if(f.entries[i].model==model){serial=f.entries[i].serial;break;}
    if(!re4dc_scroll_source_member(model,serial,&work)) {
        const bool started=f.started;sourceWorldFail(5);
        if(started){sourceWorldAbort(5);return -1;}return 0;
    }
#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
    if(sourceWorldDiagnostic.active && !sourceWorldDiagnostic.draw_observed){
        sourceWorldDiagnostic.draw_observed=true;
        re4dc_log("PS2PF owned f=%u model=%p serial=%u work=%u\n",re4dc_ui_frame(),static_cast<void*>(model),serial,work);
    }
#endif
    const int result=re4dc_ps2_source_draw(f.package_generation);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role && result){
        f.withheld=true;
        auto* entry=sourceWorldCaptured(model);
        if(entry && !entry->consumed){entry->consumed=true;++f.consumed;}
    }
#endif
    if(result){f.started=true;if(result<0){f.failed=true;sourceWorldFail(6);}return result;}
    sourceWorldFail(7);return 0;
}
}
#if RE4DC_PS2_WORLD_TRANSITION_PIN
extern "C" int re4dc_source_world_transition(unsigned native,unsigned generation) {
    return sourceWorldTransitionContext(native,generation);
}
#endif
extern "C" int re4dc_source_world_prepare(unsigned native,unsigned* generation) {
    auto& f=sourceWorldFrame;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // Never revive or replace a provisional same-image transaction.
    if(f.role && f.native==native && (f.guarded || f.started || f.withheld || f.failed))return 0;
    f.guarded=false;f.role=0;f.consumed=0;f.member_reason=0;f.withheld=false;f.committed=false;f.sealed=false;f.proven=0;re4dc_r200_set_light(0);
    f.sample=f.anchor=~0U;f.uv_valid[0]=f.uv_valid[1]=false;
    for(auto& pair:f.uv)for(auto& value:pair)value=0.f;
    for(auto& pointer:f.group)pointer=nullptr;
#endif
    f.active=false;f.ready=false;f.started=false;f.failed=false;f.count=0;
    RE4DC_SOURCE_DIAG_STAGE("context");
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!RE4DC_SOURCE_DIAG_TEST(generation,12))return 0;
    f.role=sourceWorldTransitionRole(&f.member_reason);
    if(f.role){
        f.coarse=re4dc_coarse_image!=0;f.system=pG->System_flg;f.stop=pG->Stop_flg;f.disp=pG->Disp_flg;
        f.used=sourceWorldScheduledTables();
    }else if(!sourceWorldContext()){
        if(pG && pG->Rno0==4 && G_ROOM_ID==0x200 &&
           (++sourceWorldTransitionFailures<=16 || !(native%120)))
            re4dc_log("PS2TRANSITION_CONTEXT f=%u field=%u sys=%08x coarse=%u\n",native,f.member_reason,unsigned(pG->System_flg),unsigned(re4dc_coarse_image));
        return 0;
    }
#else
    if(!RE4DC_SOURCE_DIAG_TEST(generation,12) || !sourceWorldContext())return 0;
#endif
    RE4DC_SOURCE_DIAG_STAGE("room-package");
    unsigned rg=0,c,b,s,r,pg=0;
    if(!RE4DC_SOURCE_DIAG_TEST(re4dc_room4_state(&rg,&c,&b,&s,&r),13) ||
       !RE4DC_SOURCE_DIAG_TEST(rg,14) || !RE4DC_SOURCE_DIAG_TEST(
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
       f.role?re4dc_ps2_source_group_package(&pg,1):
#endif
       re4dc_ps2_source_package(&pg),15)){sourceWorldFail(1);return 0;}
    f.native=native;f.source=pG->Frame_cnt;f.room_generation=rg;f.package_generation=pg;
    f.objects=re4dc_alive_gen[2];f.pools=re4dc_alive_gen[0];
    f.prim=pG->prim_cnt;f.bytes=pG->nPrim;f.buffer=pG->vtx_buf_no;
    f.prim_generation=sourceWorldPrimGeneration;f.ot_epoch=re4dc_source_world_ot_epoch();
    RE4DC_SOURCE_DIAG_STAGE("primitive-meta");
    if(!f.bytes || f.buffer>=RE4DC_PRIMITIVE_BUFFERS || f.bytes>~0U/RE4DC_PRIMITIVE_BUFFERS) {
        sourceWorldMemoryFail(1,~0U,f.prim,f.bytes);return 0;
    }
    RE4DC_SOURCE_DIAG_STAGE("primitive-owner");
    if(!sourceWorldAllocated(reinterpret_cast<const void*>(f.prim),f.bytes*RE4DC_PRIMITIVE_BUFFERS,true)) {
        sourceWorldMemoryFail(2,~0U,f.prim,f.bytes*RE4DC_PRIMITIVE_BUFFERS);return 0;
    }
    f.begin=f.prim+static_cast<unsigned long>(f.bytes)*f.buffer;
    f.end=reinterpret_cast<unsigned long>(GXWORK()->prim);
    RE4DC_SOURCE_DIAG_STAGE("primitive-cursor");
    if(f.end<f.begin || f.end-f.begin>f.bytes){sourceWorldMemoryFail(3,~0U,f.end,f.bytes);return 0;}
    RE4DC_SOURCE_DIAG_STAGE("walk");
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role && (!re4dc_ps2_source_legacy_clean(native) || !re4dc_source_world_op_window() || !re4dc_ps2_source_group_package(&pg,1) ||
       !re4dc_r200_scroll_group() || !re4dc_r200_scroll_pointers(f.group,kSourceWorldCallbacks))){
#if RE4DC_TRANSITION_GATE_DIAG
        // TRANSITION_GATE_DIAG (test only): which of the five pre-walk checks refused (reason 14), with the r200 package
        // and scroll pins against the live data (tools/d367/srcworld/r200_profile.py regenerates the pins).
        static unsigned tgd_lines;
        if(tgd_lines<6){
            ++tgd_lines;unsigned pg2=0;
            re4dc_log("TGD f=%u legacy=%d opwin=%d package=%d scroll_group=%d scroll_ptrs=%d\n",re4dc_ui_frame(),
                re4dc_ps2_source_legacy_clean(native),re4dc_source_world_op_window(),re4dc_ps2_source_group_package(&pg2,1),
                re4dc_r200_scroll_group(),re4dc_r200_scroll_pointers(f.group,kSourceWorldCallbacks));
            re4dc_ps2_source_group_package_diag();re4dc_r200_scroll_diag();
        }
#endif
        sourceWorldFail(14);return 0;}
#endif
    if(!sourceWorldWalk(true))return 0;
    f.active=f.count!=0;
    RE4DC_SOURCE_DIAG_STAGE("identity");
    if(!sourceWorldIdentity(native,pg)){f.active=false;return 0;}
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // Admission can later decline; captured storage remains guarded until a
    // new image prepare replaces this ticket, never during the same image.
    if(f.role)f.guarded=true;
#endif
    RE4DC_SOURCE_DIAG_STAGE("accepted");
    *generation=pg;
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(f.role && (++sourceWorldTransitionReports<=16 || !(native%120))){
        const auto& first=f.entries[0];
        re4dc_log("PS2TRANSITION_PLAN f=%u role=%u sys=%08x stop=%08x disp=%08x callbacks=%u table=%x node=%p model=%p serial=%u work=%u\n",
            native,f.role,f.system,f.stop,f.disp,f.count,first.table,first.node,static_cast<void*>(first.model),first.serial,first.work);
    }
#endif
#if !RE4DC_PS2_WORLD_SOURCE_TEX_PREP
    f.ready=true;
#endif
    if(++sourceWorldReports<=16 || !(native%120))
        re4dc_log("PS2SOURCE_PLAN f=%u t=%u room=200 gen=%u package=%u callbacks=%u\n",native,f.source,rg,pg,f.count);
    return 1;
}
extern "C" int re4dc_source_world_current(unsigned native,unsigned generation) {
    return sourceWorldFrame.ready && sourceWorldIdentity(native,generation);
}
extern "C" void re4dc_source_world_prepared(unsigned native,unsigned generation,int ready) {
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(sourceWorldFrame.guarded && !sourceWorldCapturedStorageCurrent()){
#if RE4DC_TRANSITION_GATE_DIAG
        {const auto& f=sourceWorldFrame;unsigned rg=0,c,b,st,rf,pg=0;const int r4=re4dc_room4_state(&rg,&c,&b,&st,&rf);
         re4dc_log("TGD storage f=%u prim=%d ot=%d objects=%d pools=%d primalloc=%d room4=%d/%d pkg=%d scroll=%d\n",native,
            int(sourceWorldPrimGeneration==f.prim_generation),int(re4dc_source_world_ot_epoch()==f.ot_epoch),
            int(re4dc_alive_gen[2]==f.objects),int(re4dc_alive_gen[0]==f.pools),
            int(sourceWorldAllocated(reinterpret_cast<const void*>(f.prim),f.bytes*RE4DC_PRIMITIVE_BUFFERS,true)),
            r4,int(rg==f.room_generation),int(re4dc_ps2_source_group_package(&pg,0) && pg==f.package_generation),
            re4dc_r200_scroll_storage_current());}
#endif
        sourceWorldFrame.withheld=true;sourceWorldAbort(8);return;
    }
#endif
    if(!ready || !sourceWorldIdentity(native,generation)){sourceWorldFail(8);return;}
    sourceWorldFrame.ready=true;
}
extern "C" void re4dc_source_world_flush_result(unsigned native,int complete) {
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    const auto& f=sourceWorldFrame;
    if(f.role && f.native==native && (f.started || f.withheld)){
        if(!complete || !sourceWorldIdentity(native,f.package_generation) ||
           !re4dc_ps2_source_receipt_complete(native,f.package_generation))sourceWorldAbort(10);
        return;
    }
#endif
    if(sourceWorldFrame.native==native && sourceWorldFrame.started && !complete){
        sourceWorldAbort(10);
    }
}

#if RE4DC_PS2_WORLD_TRANSITION_OWNER
extern "C" int re4dc_source_world_native_cell(const void* data,unsigned bytes,unsigned generation){
    unsigned current=0,c,b,stale,refused;
    const auto address=reinterpret_cast<unsigned long>(data);
    if(!generation || !re4dc_room4_state(&current,&c,&b,&stale,&refused) || current!=generation ||
       address<32 || !bytes || bytes>~0U-32U ||
       !sourceWorldAllocated(reinterpret_cast<const void*>(address-32),bytes+32,true,4))return 0;
    // room_alloc4's exact 32-byte Room4Cell, after allocated-cell proof.
    const auto* header=reinterpret_cast<const unsigned*>(address-32);
    return header[0]==0x57364834U && header[1]==generation && header[2]==bytes;
}
extern "C" int re4dc_source_world_group_claimed(){
    const auto& f=sourceWorldFrame;
    return f.role && (f.withheld || f.started || f.failed);
}
extern "C" int re4dc_source_world_preflight_current(unsigned native,unsigned generation){
    const auto& f=sourceWorldFrame;
    return !f.role || sourceWorldIdentity(native,generation);
}
extern "C" int re4dc_source_world_sealed(){return sourceWorldFrame.role && sourceWorldFrame.sealed;}
extern "C" int re4dc_source_world_binding_valid(){
    if(!re4dc_source_world_group_claimed())return 1;
    const auto& f=sourceWorldFrame;
    return !f.failed && f.ready &&
        sourceWorldIdentity(f.native,f.package_generation) && sourceWorldWalk(false);
}
extern "C" void re4dc_source_world_binding_failed(){
    if(re4dc_source_world_group_claimed())sourceWorldAbort(22);
}
extern "C" int re4dc_source_world_uv(unsigned placement,unsigned mesh,unsigned part,unsigned pass,float* uv){
    if(!uv)return 0;uv[0]=uv[1]=0.f;
    if(!re4dc_source_world_group_claimed())return 1;
    if(!re4dc_source_world_binding_valid())return 0;
    const auto& f=sourceWorldFrame;
    if(!f.started || !f.uv_valid[0] || !f.uv_valid[1])return 0;
    if(!pass && placement==13 && mesh==13 && part==32){uv[0]=f.uv[0][0];uv[1]=f.uv[0][1];}
    if(!pass && placement==19 && mesh==19 && part>=47 && part<=52){uv[0]=f.uv[1][0];uv[1]=f.uv[1][1];}
    return 1;
}
extern "C" int re4dc_source_world_transition_owner(unsigned native,unsigned generation) {
    const auto& f=sourceWorldFrame;
    return f.role && f.ready && sourceWorldIdentity(native,generation);
}
extern "C" int re4dc_source_world_legacy_allowed(unsigned native) {
    auto& f=sourceWorldFrame;
    if(!f.role)return 1;
    if(f.native!=native){
        if(f.started || f.withheld || f.failed){sourceWorldAbort(17);return 0;}
        return 1;
    }
    if((f.started || f.withheld) && !f.failed && !f.sealed && !sourceWorldIdentity(native,f.package_generation))sourceWorldAbort(17);
    return !(f.active || f.started || f.withheld || f.failed);
}
extern "C" int re4dc_source_world_callback_continue() {
    auto& f=sourceWorldFrame;
    if(!f.role)return 1;
    // Sealed: every owned callback drew under a valid proof and the checks passed after the last one.
    // Later epoch changes (e.g. SetPrimBuffPtr at DOORDEMO START) cannot invalidate draws already made.
    if(f.sealed)return 1;
    if(f.guarded && !sourceWorldCapturedStorageCurrent()){
        re4dc_log("PS2TRANSITION_ABORT19 f=%u case=%s consumed=%u callbacks=%u\n",f.native,
            f.consumed==f.count?"during-last":(f.consumed?"between":"before"),f.consumed,f.count);
        // Admission failure must not disable traversal safety. This runs before
        // the first node and again before reading the current node's next link.
        f.withheld=true;sourceWorldAbort(19);return 0;
    }
    if(!f.started && !f.withheld)return 1;
    // After revocation, even the next OT link may point into retired memory.
    if(f.failed)return 0;
    if(!sourceWorldIdentity(f.native,f.package_generation) || !sourceWorldWalk(false)){
#if RE4DC_TRANSITION_GATE_DIAG
        {static unsigned cl;if(cl<6){++cl;const bool id=sourceWorldIdentity(f.native,f.package_generation);
         re4dc_log("TGD continue19 f=%u identity=%d walk=%d consumed=%u prim=%lx begin=%lx end=%lx bytes=%u\n",f.native,int(id),
            int(id && sourceWorldWalk(false)),f.consumed,reinterpret_cast<unsigned long>(GXWORK()->prim),f.begin,f.end,f.bytes);}}
#endif
        re4dc_log("PS2TRANSITION_ABORT19 f=%u case=%s consumed=%u callbacks=%u\n",f.native,
            f.consumed==f.count?"during-last":(f.consumed?"between":"before"),f.consumed,f.count);
        sourceWorldAbort(19);return 0;
    }
    if(f.started && f.count && f.consumed==f.count){
        f.sealed=true;
        re4dc_log("PS2TRANSITION_SEALED f=%u callbacks=%u\n",f.native,f.count);
    }
    return 1;
}
extern "C" int re4dc_source_world_present(unsigned native,int source_finished,int stream_aborted) {
    auto& f=sourceWorldFrame;
    if(!f.role)return 1;
    if(f.native!=native){
        if(f.started || f.withheld || f.failed){sourceWorldAbort(18);return 0;}
        return 1;
    }
    if(f.failed)return 0;
    if(!f.started && !f.withheld)return 1;
    if(stream_aborted || !source_finished || f.consumed!=f.count ||
       (!f.sealed && (!sourceWorldIdentity(native,f.package_generation) || !sourceWorldWalk(false))) ||
       !re4dc_ps2_source_receipt_complete(native,f.package_generation)){
        sourceWorldAbort(18);return 0;
    }
    if(!f.committed){
        f.committed=true;
        if(sourceWorldTransitionReports<=16 || !(native%120))
            re4dc_log("PS2TRANSITION_COMMIT f=%u role=%u callbacks=%u consumed=%u passes=111\n",native,f.role,f.count,f.consumed);
    }
    return 1;
}
#endif

#if RE4DC_PS2_WORLD_PREFLIGHT_DIAG
extern "C" void re4dc_source_world_diag_begin(unsigned native) {
    sourceWorldDiagnostic.begin(native,pG && G_ROOM_ID==0x200,pG && (pG->System_flg&0x1000));
}
extern "C" int re4dc_source_world_diag_active(unsigned native) {
    return sourceWorldDiagnostic.active && sourceWorldDiagnostic.native==native;
}
extern "C" void re4dc_source_world_diag_report(unsigned native,const char* where) {
    if(!re4dc_source_world_diag_active(native))return;
    const auto& d=sourceWorldDiagnostic;const auto& f=sourceWorldFrame;
    re4dc_log("PS2PF source f=%u where=%s stage=%s field=%u reason=%u memory=%u callbacks=%u ticket=%u/%u/%u/%u source=%u/%u sys=%08x status=%08x/%08x mode=%u coarse=%u pace=%u epochs=%u/%u package=%u\n",
        native,where,d.stage,d.field,d.reason,d.memory,f.count,unsigned(f.active),unsigned(f.ready),unsigned(f.started),unsigned(f.failed),
        pG?unsigned(pG->Frame_cnt):0U,f.source,pG?unsigned(pG->System_flg):0U,
        pG?unsigned(pG->Status_flg[1]):0U,pG?unsigned(pG->Status_flg[2]):0U,pG?unsigned(pG->Rno0):0U,
        unsigned(re4dc_coarse_image),unsigned(re4dc_pace_skipping),sourceWorldPrimGeneration,f.prim_generation,f.package_generation);
    if(d.model)re4dc_log("PS2PF walk-last f=%u where=%s table=%x model=%p serial=%u work=%u accepted=%d\n",
        native,where,d.table,d.model,d.serial,d.work,d.probe);
}
#endif
#undef RE4DC_SOURCE_DIAG_TEST
#undef RE4DC_SOURCE_DIAG_STAGE
