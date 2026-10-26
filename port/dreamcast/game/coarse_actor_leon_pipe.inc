// Included once by coarse_actor_transaction.inc under LEON_NATIVE_PIPE (native_model_registry.mk; default 0; render
// only, exact). Leon (pl00, appearance 0x100) through the owner transaction with the work it repeats done once:
//  - the binding: owner_leon_bind once per pass-1 call (the plan and owner_leon_palettes each ran it), with its finite
//    test of the 119 parts' mat / lt_inv_mat as one exponent sweep (coarse_finite is that exponent test per float);
//  - the plan: re4dc_actor_plan_leon's result kept per binding (it is a function of the role infos and fixed data),
//    with the record's fixed parts (sources, chunks, the source-order runs, the base part);
//  - actor_semantics: its fixed terms (counts, the immutable chunk proofs, palette / workspace bytes, run order and
//    triangle totals) proved by one full actor_semantics for the plan; every per-frame term and the live material
//    certificate run in every pass;
//  - the palettes: owner_leon_palettes' bones and groups unchanged; its per-float finite scan of the 7,980 palette
//    floats is replaced by a sufficient test of the bone matrices T they are weighted sums of (exponent < 228, i.e.
//    |T| < 2^101, and the plan's largest entry weight sum below 2^20 keep every sum and FTRV partial finite); a T
//    outside it runs the scan, which decides;
//  - the preflight: one full re4dc_actor_preflight_owned_runs per plan proves the runs' fixed terms, then the lite
//    one (native_actor_leon_pipe.inc) in acquisition and pass 2; pass 1's submission does not repeat acquisition's;
//  - the submission: re4dc_leon_pipe_submit (no one_qualifies per run, pass 2's hair in one store-queue window).
// The leases, prim-tail allocations, ledger choices, release order, ATD codes and kernels are actor_acquire's and the
// transaction's, in their order; anything this path does not accept goes to the unchanged transaction in the same
// call before any lease (a binding or plan it does not take), or declines / fails exactly where actor_acquire and the
// transaction decline / fail. Lane fm (game-logic maths): this reads parts[b]->mat and lt_inv_mat (row-major 3x4),
// pParts->mat, info->mat and pG->Cam.v_mat as owner_leon_palettes and actor_acquire do; no layout of its own.
#if RE4DC_ACTOR_TRANSACTION_DIAG || RE4DC_NATIVE_MODEL_REGISTRY_CENSUS || (defined(RE4DC_NATIVE_MODEL_REGISTRY_TX) && RE4DC_NATIVE_MODEL_REGISTRY_TX == 2) || RE4DC_ACTOR_PROOF_LEAN == 2
#error LEON_NATIVE_PIPE: not with the transaction diagnostic / census / compare builds
#endif
#include "leon_native_pipe.h"
namespace {
typedef unsigned __attribute__((may_alias)) LeonWord;
struct LeonPipe {
    bool planned, semantics_proved, preflight_proved, bound_ok, live;
    cModelInfo* key[8];      // the plan's role infos (the binding's)
    unsigned lean_serial;    // ACTOR_PROOF_LEAN: the lifetime serial after the admitting call's semantics
    ActorOwnedRecord r;      // plan, base part, parts and runs fixed per plan; leases, flags, modelviews per frame
} leon_pipe;

// owner_leon_bind with the finite test as one sweep.
bool leon_bind(cModel* m) {
    if(!m || m->id || m->nParts!=119 || !m->pList || !m->pParts || (m->be_flag&0x4000))return false;
    if(!re4dc_actor_role_bindings(m,0x100,infos,8) || !re4dc_actor::exact_infos(m->pModelInfo,infos,8))return false;
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    if(owner!=m || owner_serial!=m->serial || owner_parts!=m->pList || owner_root_parts!=m->pParts || owner_binding_revision!=revision) {
        cParts* part=m->pList;
        for(unsigned i=0;i<119;++i) {
            if(!part)return false;parts[i]=part;
            for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
                (!RE4DC_LEON_RIG_SIM(i) && __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f))return false;
            part=part->pList;
        }
        if(part)return false;
        owner=m;owner_serial=m->serial;owner_parts=m->pList;owner_root_parts=m->pParts;owner_binding_revision=revision;
    }
    // (exponent field + one unit: bit 31 set exactly for an all-ones exponent, a NaN or an infinity)
    unsigned bad=0;
    for(unsigned i=0;i<119;++i) {
        const LeonWord* a=reinterpret_cast<const LeonWord*>(&parts[i]->lt_inv_mat[0][0]);
        const LeonWord* b=reinterpret_cast<const LeonWord*>(&parts[i]->mat[0][0]);
        for(unsigned j=0;j<12;++j)bad|=((a[j]&0x7f800000u)+0x00800000u)|((b[j]&0x7f800000u)+0x00800000u);
    }
    return !(bad&0x80000000u);
}

// The plan of this binding (re4dc_actor_plan_leon's, kept while the role infos are the same) and the record's fixed
// parts as actor_acquire lays them out. nullptr: no plan here (the transaction's own plans decide).
const Re4dcActorPlan* leon_plan(cModel* m) {
    auto& L=leon_pipe;
    if(L.planned && !std::memcmp(L.key,infos,sizeof(L.key)))return &L.r.plan;
    L.planned=L.semantics_proved=L.preflight_proved=L.bound_ok=false;
    Re4dcActorPlan p{};
    if(!re4dc_actor_plan_leon(m,&p) || !actor_plan_layout(p) || p.count!=8 || std::memcmp(p.info,infos,sizeof(L.key)) ||
       !p.palette_bytes || p.palette_bytes>kActorPaletteCap)return nullptr;
    auto& r=*::new(static_cast<void*>(&L.r)) ActorOwnedRecord{};  // value-initialised as actor_acquire's record
    r.plan=p;r.count=p.count;
    unsigned order=0;
    for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
        unsigned i=0;for(;i<p.count && p.info[i]!=info;++i){}
        if(i==p.count || order==p.count)return nullptr;
        const auto& c=p.input[i];auto& part=r.part[order];
        part.info=info;part.role=i;
        part.source={c.positions.data,c.normals.data,c.position_count,c.normal_count,c.palette_count,0};
        part.chunk={info,c.stream.data,c.uv.data,part.mv,unsigned(c.stream.size),c.position_count,c.normal_count};
        for(unsigned j=0;j<p.run_count;++j)if(p.runs[j].role==i) {
            const auto& run=p.runs[j];auto& draw=r.runs[r.run_count++];
            draw.chunk={info,run.stream.data,run.uv.data,part.mv,unsigned(run.stream.size),c.position_count,c.normal_count};
            draw.material=run.material;
        }
        ++order;
    }
    if(order!=p.count || r.run_count!=p.run_count)return nullptr;
    auto& b=r.base;b.position_stride=6;b.normal_stride=6;b.normal_shift=14;b.shift=4;
    b.lighting=&light;b.image=p.image;b.source_key[2]=1;b.cull=0;b.alpha_state=255;
    // The largest entry weight sum (the palette bound's W).
    float w_max=0.0f;
    for(unsigned i=0;i<8;++i) {
        const auto& c=leon4k::chunks[i];
        for(unsigned j=0;j<c.palette_count;++j) {
            float s=0.0f;
            for(unsigned k=0;k<c.weights[j].count && k<3;++k)s+=__builtin_fabsf(c.weights[j].value[k]);
            if(!(s<=w_max))w_max=s;
        }
    }
    L.bound_ok=w_max<1048576.0f;
    std::memcpy(L.key,infos,sizeof(L.key));L.planned=true;
    return &r.plan;
}

// actor_semantics with its fixed terms (proved for this plan by a full call): the per-frame terms, its order.
bool leon_semantics(cModel* m,const Re4dcActorPlan& p) {
    if(!m->pParts || m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f || m->alpha_omit!=255 ||
       m->z_mode!=0 || m->CullMode || m->Shader_type || m->AddAmb_r || m->AddAmb_g || m->AddAmb_b ||
       (m->be_flag&(0x4000u|0x00020000u)) || !re4dc_actor::exact_infos(m->pModelInfo,p.info,p.count))return false;
    if(pG->Status_flg[1]&0x100)return false;
    if((pG->Status_flg[2]&0x00100000) && (m->be_flag&0x02000000) &&
       !(pG->Disp_flg&0x00040000) && (pG->Status_flg[1]&0x200))return false;
    for(unsigned i=0;i<p.count;++i) {
        auto* info=p.info[i];
        if(!info || !info->pData || info->invisible_factor!=1.0f || info->blend_mode ||
           info->colorWord!=0xffffffffu || info->flagsDC || info->pAddTpl || info->nAddTex ||
           info->texBlendTbl || info->pTexAnim || info->uvU || info->uvV || info->uvScrollU || info->uvScrollV ||
           ((info->be_flag&2) && !RE4DC_LEON_FACE_ROLE(p,i)))return false;
    }
    return re4dc_actor_material_certificate(m,&p)!=0;
}
bool leon_semantics_any(cModel* m,const Re4dcActorPlan& p) {
    auto& L=leon_pipe;
    if(L.semantics_proved)return leon_semantics(m,p);
    if(!actor_semantics(m,p))return false;
    L.semantics_proved=true;return true;
}

// owner_leon_palettes after this call's leon_bind (only native code ran since: its second bind has this answer).
int leon_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
    if(!skin_init())return 0;
    for(unsigned i=0;i<8;++i)if(p.info[i]!=infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&parts[b]->mat[0][0],RE4DC_LEON_BIND_ROW(b,parts[b]),bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    unsigned big=0;
    for(unsigned u=0;u<skin_used;++u) {
        const LeonWord* t=reinterpret_cast<const LeonWord*>(bone_T[skin_bone[u]]);
        for(unsigned j=0;j<12;++j)big|=(t[j]&0x7f800000u)+(28u<<23);  // bit 31: exponent >= 228 (or not finite)
    }
    const bool bounded=leon_pipe.bound_ok && !(big&0x80000000u);
    for(unsigned i=0;i<8;++i) {
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],leon4k::chunks[i].palette_count);
        if(!bounded)for(unsigned j=0;j<leon4k::chunks[i].palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
    }
    return 1;
}

ActorOwnedRecord* leon_decline(ActorOwnedRecord& r,bool& failed) {
    leon_pipe.live=false;
    return actor_decline(r,failed);
}

// actor_acquire for the plan in leon_pipe.r: the same leases in the same order, the same prim-tail allocations (the
// record's own bytes are taken and left unused: the record is leon_pipe.r), the same palettes, modelviews, skin lease
// and base part; the lite preflight once the plan's fixed run terms were proved by a full one.
ActorOwnedRecord* leon_acquire(cModel* m,const FrameIdentity& frame,const ModelIdentity& model,bool& failed) {
    auto& L=leon_pipe;auto& r=L.r;const auto& p=r.plan;
    failed=false;L.live=false;
    re4dc_bind_actor_frame();
    Re4dcActorTextureLease textures[kRe4dcActorMaterials]{};
    Re4dcActorWorkspaceLease workspace{};
    unsigned acquired=0;
    auto release_textures=[&]{while(acquired)re4dc_actor_texture_release(&textures[--acquired]);};
    for(;acquired<p.material_count;++acquired) {
        const auto& mat=p.materials[acquired];
        if(!re4dc_actor_texture_acquire(&mat.image,mat.crc,mat.fnv,&textures[acquired])) {ATD(m,8,acquired,p.material_count);release_textures();return nullptr;}
    }
    if(!re4dc_actor_workspace_acquire(p.workspace_bytes,&workspace)) {ATD(m,9,p.workspace_bytes,0);release_textures();return nullptr;}
    const unsigned header=(sizeof(ActorOwnedRecord)+31u)&~31u;
    if(!actor_palette_arena.bound()) {
        void* bank=re4dc_prim_tail(kActorPaletteCap,kActorOwnerReserve+header);
        if(!bank || !actor_palette_arena.bind(bank,kActorPaletteCap)) {
            ATD(m,10,kActorPaletteCap,header);
            re4dc_actor_workspace_release(&workspace);release_textures();return nullptr;
        }
    }
    re4dc_actor::PaletteLease palette_lease{};
    if(!actor_palette_arena.acquire(p.palette_bytes,palette_lease)) {
        ATD(m,11,p.palette_bytes,0);
        re4dc_actor_workspace_release(&workspace);release_textures();return nullptr;
    }
    void* palette_memory=actor_palette_arena.data(palette_lease,p.palette_bytes);
    void* memory=palette_memory?re4dc_prim_tail(header,kActorOwnerReserve):nullptr;
    if(!memory) {
        ATD(m,12,header,p.palette_bytes);
        if(!actor_palette_arena.release(palette_lease))failed=true;
        re4dc_actor_workspace_release(&workspace);release_textures();return nullptr;
    }
    r.parts_owner=m->pParts;r.frame=frame;r.model=model;r.workspace=workspace;r.palette=palette_lease;r.skin={};
    r.done=r.passes=r.submitted=r.released=0;
    for(unsigned i=0;i<p.material_count;++i)r.textures[i]=textures[i];
    float* palettes[kRe4dcActorRoles]{};unsigned at=0;
    for(unsigned i=0;i<p.count;++i) {
        palettes[i]=reinterpret_cast<float*>(static_cast<unsigned char*>(palette_memory)+at);
        at+=(p.input[i].palette_count*48u+31u)&~31u;
    }
    if(!leon_palettes(m,p,palettes)){ATD(m,13,p.appearance,0);return leon_decline(r,failed);}
    Re4dcActorSkinBinding bindings[kRe4dcActorRoles]{};
    unsigned order=0;
    for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
        // (the binding fixed this source order: the plan's record laid its parts out in it)
        if(order==r.count || r.part[order].info!=info)return leon_decline(r,failed);
        auto& part=r.part[order];part.flags=info->be_flag;
        Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
        std::memcpy(part.mv,mv,sizeof(mv));
        for(float f:part.mv)if(!coarse_finite(f))return leon_decline(r,failed);
        bindings[order]={info,part.source,palettes[part.role],p.input[part.role].palette_count};
        ++order;
    }
    if(!re4dc_actor_skin_acquire(frame.frame,bindings,order,&r.skin)){ATD(m,14,order,0);return leon_decline(r,failed);}
    auto& b=r.base;b.model=m;b.depth_mode=m->z_mode;
    GXGetProjectionv(b.projection);GXGetViewportv(b.viewport);
    r.passes=m->ot_type==7?3u:1u;
    if(!(L.preflight_proved && re4dc_leon_pipe_preflight(&b,r.runs,r.run_count,p.materials,p.material_count,&r.workspace,
                                                          &r.skin,r.textures,unsigned(pG->Frame_cnt)))) {
        if(!re4dc_actor_preflight_owned_runs(&b,r.runs,r.run_count,p.materials,p.material_count,&r.workspace,&r.skin,r.textures)) {
            ATD(m,15,r.run_count,p.run_count);return leon_decline(r,failed);
        }
        L.preflight_proved=true;
    }
    L.live=true;
    return &r;
}

// The transaction's per-pass part for the lean record. admitting: the pass-1 call that acquired it.
int leon_pass(cModel* m,ActorOwnedRecord& r,bool admitting) {
    auto& L=leon_pipe;
    const unsigned pass=m->ot_type==7 && (m->be_flag&0x08000000)?2u:1u;
    if((r.done&pass) || r.released){actor_fail();return -1;}
#if RE4DC_ACTOR_PROOF_LEAN == 1
    const bool lean_held=admitting && L.lean_serial && !re4dc_material::life::exhausted && re4dc_material::life::serial==L.lean_serial;
#else
    const bool lean_held=false;
#endif
    if(!actor_palette_arena.data(r.palette,r.plan.palette_bytes) || m->pParts!=r.parts_owner ||
       (!lean_held && !leon_semantics(m,r.plan))){actor_release(r);actor_fail();return -1;}
    float projection[7],viewport[6];GXGetProjectionv(projection);GXGetViewportv(viewport);
    if(std::memcmp(projection,r.base.projection,sizeof(projection)) || std::memcmp(viewport,r.base.viewport,sizeof(viewport))) {
        actor_release(r);actor_fail();return -1;
    }
    unsigned order=0;
    for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
        if(order==r.count || r.part[order].info!=info || r.part[order].flags!=info->be_flag) {
            actor_release(r);actor_fail();return -1;
        }
        if(!lean_held) {
            Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
            if(std::memcmp(r.part[order].mv,mv,sizeof(mv))){actor_release(r);actor_fail();return -1;}
        }
        ++order;
    }
    if(order!=r.count){actor_release(r);actor_fail();return -1;}
    Re4dcActorDrawRun runs[kRe4dcActorRuns];unsigned n=0;
    for(unsigned i=0;i<r.count;++i) {
        const auto& p=r.part[i];
        if(!(p.flags&8))continue;
        if(m->ot_type==7 && ((p.flags&0x40)?2u:1u)!=pass)continue;
        for(unsigned j=0;j<r.run_count;++j)if(r.runs[j].chunk.info==p.info)runs[n++]=r.runs[j];
    }
    const int result=n?re4dc_leon_pipe_submit(&r.base,runs,n,r.plan.materials,r.plan.material_count,&r.workspace,&r.skin,
                                              r.textures,unsigned(pG->Frame_cnt),admitting?0:1):1;
    if(result!=1){actor_release(r);actor_fail();return -1;}
    ATD(m,n?(pass==1?18u:19u):17u,n,r.plan.appearance);
    r.submitted|=n!=0;r.done|=pass;
    if(r.done==r.passes && !actor_release(r))return -1;
    return 1;
}

// The pass-1 call (choice 0, the source mark already taken): 2 = not this path (the transaction's plans continue in
// this call), else the transaction's result.
int leon_pipe_first(cModel* m,const FrameIdentity& frame,const ModelIdentity& model) {
    auto& L=leon_pipe;
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if(RE4DC_WARP_LATE(RE4DC_LATE_LEON_SOURCE))return 2;  // the plan's test-only old-path arm
#endif
    if(!m || m->id || m->ot_type!=7 || !leon_bind(m))return 2;
    const Re4dcActorPlan* p=leon_plan(m);
    if(!p)return 2;
    if(!leon_semantics_any(m,*p)){ATD(m,6,p->appearance,p->count);return 0;}
#if RE4DC_ACTOR_PROOF_LEAN
    L.lean_serial=re4dc_material::life::exhausted?0u:re4dc_material::life::serial;
#endif
    bool failed=false;ActorOwnedRecord* r=leon_acquire(m,frame,model,failed);
    if(failed){actor_fail();return -1;}
    if(!r){ATD(m,31,p->appearance,0);return 0;}
    if(!re4dc_actor_transaction_choose(m,2)){actor_release(*r);actor_fail();return -1;}
    ATD(m,16,p->appearance,p->run_count);
    return leon_pass(m,*r,true);
}
}
