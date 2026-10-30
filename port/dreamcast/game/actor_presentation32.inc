// Included after actor_semantics, before actor_acquire. No pose/palette cache.
// Each texture acquisition may yield; reprove before the next material read,
// palette/primitive allocation or any old plan pointer dereference.
#if RE4DC_NMR_BONES < 90
#error ACTOR_PRESENTATION32 requires the existing Luis-capable registry skeleton capacity
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
#error ACTOR_PRESENTATION32 and SKIN_RECIPE32 require a separate joint source-credit qualification
#endif
extern "C" int re4dc_actor_presentation32_required(const cModel*);
struct ActorPresentation32Ticket {
    bool direct;
    unsigned generation,revision;
};
ActorPresentation32Ticket actor_presentation32_capture(cModel* m) {
    if(!re4dc_actor_presentation32_required(m))return {};
    return {true,registry.generation,re4dc_actor_binding_revision(m)};
}
bool actor_presentation32_current(cModel* m,const Re4dcActorPlan& p,
        const FrameIdentity& frame,const ModelIdentity& model,const ActorPresentation32Ticket& t) {
    if(!t.direct)return true;
    // Registry retirement can invalidate descriptor storage used even by the
    // source identity nomination. Check its out-of-band generation first.
    if(!t.generation || registry.generation!=t.generation || !t.revision)return false;
    FrameIdentity now{};ModelIdentity current{};
    if(re4dc_actor_transaction_identity(m,&now,&current)!=1 || !(now==frame && current==model) ||
       re4dc_actor_binding_revision(m)!=t.revision || !re4dc_registry_presentation32_class(m) ||
       !registry_bind(m) || !registry_bound ||
       p.appearance!=nmr::appearance_first+registry_bound->descriptor || p.count!=6u)return false;
    for(unsigned i=0;i<p.count;++i)if(p.info[i]!=registry_bound->infos[i])return false;
    // Preserve all ordinary static-material, coverage, owner and role proofs.
    // Animated/scrolling/morphed source state is not added to this first class.
    return actor_semantics(m,p);
}
bool actor_presentation32_reserve(const Re4dcActorPlan& p,unsigned frame) {
    if(p.count!=6u)return false;
    const void* infos[kRe4dcActorRoles];
    for(unsigned i=0;i<p.count;++i)infos[i]=p.info[i];
    return re4dc_actor_skin_presentation32_frame(frame,infos,p.count)!=0;
}
bool actor_presentation32_forget_source(Re4dcActorSkinLease& lease) {
    if(!re4dc_actor_skin_validate(&lease))return false;
    // There was no source-preparation promise for this image. Never restore a
    // prior primitive owner's source palette when this fresh native lease ends.
    for(unsigned i=0;i<lease.count;++i) {
        const unsigned index=lease.old[i].index;
        lease.old[i]={index,nullptr,nullptr,nullptr,0,0};
    }
    return true;
}
