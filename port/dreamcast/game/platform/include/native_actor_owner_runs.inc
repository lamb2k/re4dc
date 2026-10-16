// Included after re4dc_actor_submit_chunks; synchronous kernels, no deferral.
#if defined(RE4DC_PS2_WORLD_DRAW) && RE4DC_PS2_WORLD_DRAW
extern "C" int re4dc_ps2_world_before_owned_tr(const Re4dcModelPart*);
#endif
namespace {
void owned_run_load(Re4dcModelPart& p,const Re4dcActorDrawRun& r,const Re4dcActorOwnedMaterial& m) {
    const auto& c=r.chunk;p.info=c.info;p.part=c.info;p.stream=c.stream;p.stream_bytes=c.stream_bytes;
    p.uv=c.uv;p.position_count=c.position_count;p.normal_count=c.normal_count;
    std::memcpy(p.modelview,c.modelview,sizeof(p.modelview));
    p.image=m.image;p.mask=m.mask;p.material_flags=m.material_flags;p.blend=m.blend;p.depth_mode=m.depth_mode;
    p.mask_ref=m.mask_ref;p.mask_same_uv=m.mask_same_uv;p.wrap_s=m.wrap_s;p.wrap_t=m.wrap_t;
}
bool owned_all_textures(const Re4dcActorTextureLease* t,unsigned n) {
    if(!t || !n || n>kRe4dcActorMaterials)return false;
    for(unsigned i=0;i<n;++i)if(!re4dc_actor_texture_validate(&t[i]))return false;
    return true;
}
}
extern "C" int re4dc_actor_preflight_owned_runs(Re4dcModelPart* part,const Re4dcActorDrawRun* runs,unsigned n,
    const Re4dcActorOwnedMaterial* materials,unsigned nm,const Re4dcActorWorkspaceLease* workspace_lease,
    const Re4dcActorSkinLease* skin_lease,const Re4dcActorTextureLease* textures) {
    if(!part || !runs || !materials || !n || n>kRe4dcActorRuns || owned_submission ||
       !re4dc_actor_workspace_validate(workspace_lease) || !re4dc_actor_skin_validate(skin_lease) || !owned_all_textures(textures,nm))return 0;
    Re4dcActorStreamState before{};if(!re4dc_actor_stream_state(&before))return 0;
    for(float f:part->projection)if(!re4dc::render::is_finite(f))return 0;
    for(float f:part->viewport)if(!re4dc::render::is_finite(f))return 0;
    const float near=part->projection[6]/(part->projection[5]-1.0f),far=part->projection[6]/part->projection[5];
    if(!re4dc::render::is_finite(near) || !re4dc::render::is_finite(far) || !(near>0) || !(far>near))return 0;
    // Every run in BOTH original OT groups qualifies before the first header.
    // Validate the actual texture entry selected by packet_begin, not just any
    // pinned entry. This performs no upload, packet emission or SQ ownership.
    for(unsigned i=0;i<n;++i) {
        if(runs[i].material>=nm)return 0;
        owned_run_load(*part,runs[i],materials[runs[i].material]);
        const SkinEntry* skin=nullptr;Re4dcActorSource source{};
        if(!one_qualifies(*part,skin,source) || !blob_of(*part) ||
           !re4dc_actor_texture_material_validate(part,&textures[runs[i].material]))return 0;
        for(float f:part->modelview)if(!re4dc::render::is_finite(f))return 0;
        Re4dcModelPacket packet{};
        if(!re4dc_model_packet_reserve(part,&packet) || packet.capacity<kCacheSlots+64u)return 0;
    }
    return 1;
}
#if RE4DC_ACTOR_PLAN
static int owned_submit_runs(Re4dcModelPart* part,const Re4dcActorDrawRun* runs,unsigned n,
    const Re4dcActorOwnedMaterial* materials,unsigned nm,const Re4dcActorWorkspaceLease* workspace_lease,
    const Re4dcActorSkinLease* skin_lease,const Re4dcActorTextureLease* textures,bool prepared) {
    // The caller already checked every run (including the other OT group)
    // before publishing the actor. Keep current resource checks, pin commits,
    // world barriers, kernel qualification and the post-submit checks below.
    if(prepared && (!part || !runs || !materials || !n || n>kRe4dcActorRuns || owned_submission ||
       !re4dc_actor_workspace_validate(workspace_lease) || !re4dc_actor_skin_validate(skin_lease) ||
       !owned_all_textures(textures,nm)))return 0;
#if RE4DC_ACTOR_PLAN == 2
    const int full=re4dc_actor_preflight_owned_runs(part,runs,n,materials,nm,workspace_lease,skin_lease,textures);
    static unsigned checks,bad;
    if(prepared){++checks;if(!full)++bad;
        if(checks%600==0)re4dc_log("APREP checks=%u bad=%u\n",checks,bad);}
    if(!full)return 0;
#else
    if(!prepared && !re4dc_actor_preflight_owned_runs(part,runs,n,materials,nm,workspace_lease,skin_lease,textures))return 0;
#endif
#else
extern "C" int re4dc_actor_submit_owned_runs(Re4dcModelPart* part,const Re4dcActorDrawRun* runs,unsigned n,
    const Re4dcActorOwnedMaterial* materials,unsigned nm,const Re4dcActorWorkspaceLease* workspace_lease,
    const Re4dcActorSkinLease* skin_lease,const Re4dcActorTextureLease* textures) {
    if(!re4dc_actor_preflight_owned_runs(part,runs,n,materials,nm,workspace_lease,skin_lease,textures))return 0;
#endif
    Re4dcActorStreamState before{};if(!re4dc_actor_stream_state(&before))return 0;
    // Commit ALL texture scene pins before any first-pass emission. Release of
    // an actor lease later cannot evict an already-submitted GPU texture.
    for(unsigned i=0;i<nm;++i)if(!re4dc_actor_texture_commit(&textures[i]))return 0;
    OneWindow window;owned_submission=true;bool okay=true;unsigned previous=~0u;
    for(unsigned i=0;i<n && okay;++i) {
        const unsigned material=runs[i].material;
        // A header is never reused across a different texture/blend/depth run.
        // The same-info skin lease/palette remains shared across all14 hair runs.
        const bool changed=material!=previous;
        if(changed)one_close(window);
        owned_run_load(*part,runs[i],materials[material]);previous=material;
#if defined(RE4DC_PS2_WORLD_DRAW) && RE4DC_PS2_WORLD_DRAW
        // No live SQ window, packet reserve or resolved texture handle here.
        // Every actor material already has a scene pin from the commit above.
        if(changed && !re4dc_ps2_world_before_owned_tr(part)){okay=false;break;}
#endif
        okay=one_chunk(*part,window)==1;
        Re4dcActorStreamState after{};
        okay=okay && re4dc_actor_stream_state(&after) && after.frame==before.frame &&
            after.invalid==before.invalid && after.resource==before.resource && after.overflow==before.overflow;
    }
    one_close(window);owned_submission=false;
    Re4dcActorStreamState closed{};
    if(!okay || !re4dc_actor_stream_state(&closed) || closed.frame!=before.frame ||
       closed.invalid!=before.invalid || closed.resource!=before.resource || closed.overflow!=before.overflow ||
       !re4dc_actor_workspace_validate(workspace_lease) || !re4dc_actor_skin_validate(skin_lease) || !owned_all_textures(textures,nm)) {
        re4dc_model_packet_abort();return -1;
    }
    return 1;
}
#if RE4DC_ACTOR_PLAN
extern "C" int re4dc_actor_submit_owned_runs(Re4dcModelPart* p,const Re4dcActorDrawRun* r,unsigned n,
    const Re4dcActorOwnedMaterial* m,unsigned nm,const Re4dcActorWorkspaceLease* w,
    const Re4dcActorSkinLease* s,const Re4dcActorTextureLease* t) {
    return owned_submit_runs(p,r,n,m,nm,w,s,t,false);
}
extern "C" int re4dc_actor_submit_preflighted_runs(Re4dcModelPart* p,const Re4dcActorDrawRun* r,unsigned n,
    const Re4dcActorOwnedMaterial* m,unsigned nm,const Re4dcActorWorkspaceLease* w,
    const Re4dcActorSkinLease* s,const Re4dcActorTextureLease* t) {
    return owned_submit_runs(p,r,n,m,nm,w,s,t,true);
}
#endif
// Retain the former one-material API for other isolated callers. Its current
// material fields are copied explicitly; no new rendering policy is inferred.
namespace {
Re4dcActorOwnedMaterial owned_old_material(const Re4dcModelPart& p) {
    Re4dcActorOwnedMaterial m{};m.image=p.image;m.mask=p.mask;m.material_flags=p.material_flags;m.blend=p.blend;
    m.depth_mode=p.depth_mode;m.mask_ref=p.mask_ref;m.mask_same_uv=p.mask_same_uv;m.wrap_s=p.wrap_s;m.wrap_t=p.wrap_t;return m;
}
}
extern "C" int re4dc_actor_preflight_owned(Re4dcModelPart* p,const Re4dcActorChunk* c,unsigned n,
    const Re4dcActorWorkspaceLease* w,const Re4dcActorSkinLease* s,const Re4dcActorTextureLease* t) {
    if(!p || !c || !n || n>8)return 0;
    Re4dcActorDrawRun r[8];for(unsigned i=0;i<n;++i)r[i]={c[i],0};const auto m=owned_old_material(*p);
    return re4dc_actor_preflight_owned_runs(p,r,n,&m,1,w,s,t);
}
extern "C" int re4dc_actor_submit_owned(Re4dcModelPart* p,const Re4dcActorChunk* c,unsigned n,
    const Re4dcActorWorkspaceLease* w,const Re4dcActorSkinLease* s,const Re4dcActorTextureLease* t) {
    if(!p || !c || !n || n>8)return 0;
    Re4dcActorDrawRun r[8];for(unsigned i=0;i<n;++i)r[i]={c[i],0};const auto m=owned_old_material(*p);
    return re4dc_actor_submit_owned_runs(p,r,n,&m,1,w,s,t);
}
