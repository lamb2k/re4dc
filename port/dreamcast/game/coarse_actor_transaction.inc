// Included once by coarse_actor.cpp under RE4DC_ACTOR_TRANSACTION.
// Owners are acquired only from commonModelTrans, after re4dc_ui_begin.
// The original emTrans/commonScreenMatSub has already run once for ALL actors.
#include "actor_palette_arena.h"
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#include "actor_death_fade.h"
#include "em.h"
#endif
#include "actor_transaction_diag.h"
#include "actor_prof.h"  // ACTOR_PROF (actorplan.mk, diagnostic): empty macros otherwise
#include "actor_plan.h"  // ACTOR_PLAN (actorplan.mk): RE4DC_PLAN_ON is 0 otherwise
#include "actor_transaction_diag_impl.inc"
#include "actor_visibility_diag_impl.inc"
// NATIVE_MODEL_REGISTRY_SOURCE_LIGHT (native_model_registry.mk): registry plans of the selected enemy ids (bit 0: El
// Gigante, 0x2B, set by PS2_GIGANTE; bit 1: Del Lago, 0x2F, set by PS2_DELLAGO) take the source GX lighting record
// (actor_source_lighting below) instead of the constant colour, as ACTOR_GANADO_SOURCE_LIGHT does for every non-Leon
// plan; the lit kernel then folds the lights as it does on the source path (GIGANTE_LIGHTS reads base.model's id).
// Bit 2: the female Ganado (0x17 / 0x16, PS2_GANADO_F); bit 3: the crow (0x23, PS2_CROW, Phase 2 A3); bit 4: the
// parasite dog (0x22, PS2_WOLF, lane ps2cast-4); bit 5: the merchant (0x18, PS2_CAST_MERCHANT_LIT).
// PS2_GANADO_LIT (game30.mk): the cast Ganados (owner appearances below 0x100, the PS2 bundle with real normals) take
// the same source lighting record; the kernel keeps the 3 strongest lights + ambient (RE4DC_GANADO_LIGHT_FOLD).
#ifndef RE4DC_LEON_SOURCE_LIGHT
#define RE4DC_LEON_SOURCE_LIGHT 0
#endif
#if RE4DC_ACTOR_GANADO_SOURCE_LIGHT || RE4DC_NMR_SOURCE_LIGHT || RE4DC_PS2_GANADO_LIT || RE4DC_LEON_SOURCE_LIGHT
#define RE4DC_ACTOR_SOURCE_LIT 1
#else
#define RE4DC_ACTOR_SOURCE_LIT 0
#endif
#if RE4DC_ACTOR_SOURCE_LIT
extern u8 gxCsScale[];  // trans.cpp: the room's TEV colour scale per group (shaderSetup)
#endif
#if RE4DC_ACTOR_PROOF_LEAN
#if defined(RE4DC_NATIVE_MODEL_REGISTRY_TX) && RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
#error ACTOR_PROOF_LEAN and NATIVE_MODEL_REGISTRY_TX=2 are separate compare builds
#endif
// ACTOR_PROOF_LEAN (game/native_model_registry.mk): every lifetime change (adopt, retire, revoke, forget, stream
// pending, binding refresh) takes life::next(); an unchanged serial with no exhaustion means no lifetime record moved.
namespace re4dc_material { namespace life { extern unsigned serial; extern bool exhausted; } }  // actor_lifetime.inc
#if RE4DC_ACTOR_PROOF_LEAN == 2
// Compare build counters ("APL" lines): uses of each reuse and how often the =0 result differed (every *_bad must be 0).
struct ActorLeanCount { unsigned semantics,held,semantics_bad,mv,mv_bad,owner,owner_bad,rows,rows_bad,materials,materials_bad,last; };
ActorLeanCount actor_lean_c;
void actor_lean_report(const char* why) {
    const auto& c=actor_lean_c;
    re4dc_log("APL %s t=%u semantics=%u held=%u semantics_bad=%u mv=%u mv_bad=%u owner=%u owner_bad=%u rows=%u rows_bad=%u "
              "materials=%u materials_bad=%u\n",why,unsigned(pG->Frame_cnt),c.semantics,c.held,c.semantics_bad,c.mv,c.mv_bad,
              c.owner,c.owner_bad,c.rows,c.rows_bad,c.materials,c.materials_bad);
}
#endif
#endif
#if RE4DC_ACTOR_BIND_REUSE
extern "C" { unsigned re4dc_actor_tx_serial; }  // re4dc_actor_transaction_draw calls (ACTOR_BIND_REUSE, crowd.mk)
#endif
namespace {
using re4dc_source::FrameIdentity;
using re4dc_source::ModelIdentity;
struct ActorOwnedPart {
    cModelInfo* info;
    Re4dcActorSource source;
    Re4dcActorChunk chunk;
    float mv[12];
    unsigned flags,role;
};
struct ActorOwnedRecord {
    ActorOwnedRecord* next;
    const void* parts_owner;
    FrameIdentity frame;
    ModelIdentity model;
    Re4dcActorTextureLease textures[kRe4dcActorMaterials];
    Re4dcActorWorkspaceLease workspace;
    re4dc_actor::PaletteLease palette;
    Re4dcActorSkinLease skin;
    Re4dcModelPart base;
    Re4dcActorPlan plan;
    unsigned count,run_count,done,passes,submitted,released;
#if RE4DC_CROWD
    unsigned crowd_ganado,crowd_would,crowd_emit;  // lane crowd: a Ganado; its policy reason (=2 check); triangles emitted
    unsigned crowd_why;float crowd_depth,crowd_fog;  // =2 check: which cull test (1 fog, 2 off-screen), root depth, fog far
#endif
    ActorOwnedPart part[kRe4dcActorRoles];
    Re4dcActorDrawRun runs[kRe4dcActorRuns];
#if RE4DC_ACTOR_SOURCE_LIT
    re4dc::render::SourceLighting lit;  // the source's GX lighting for this Ganado (both pass groups)
#endif
};
ActorOwnedRecord* actor_owned_head;
FrameIdentity actor_owned_frame{};
bool actor_owned_live;
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
bool actor_certificate_reached;
#endif
re4dc_actor::PaletteArena actor_palette_arena;
#ifndef RE4DC_ACTOR_PALETTE_BANK
#define RE4DC_ACTOR_PALETTE_BANK 64
#endif
// ACTOR_PALETTE_BANK (KiB, native_model_registry.mk): the per-frame palette bank funded from the primitive tail.
constexpr unsigned kActorPaletteCap=RE4DC_ACTOR_PALETTE_BANK*1024;
static_assert(RE4DC_ACTOR_PALETTE_BANK>=16 && RE4DC_ACTOR_PALETTE_BANK<=64,"ACTOR_PALETTE_BANK 16..64 KiB");
constexpr unsigned kActorOwnerReserve=16*1024;
extern "C" void* re4dc_prim_tail(unsigned,unsigned);
extern "C" void re4dc_model_packet_abort();
extern "C" void re4dc_actor_model_frame_retire();

void actor_fail() { ATD(nullptr,20,0,0);re4dc_model_packet_abort(); }
bool actor_release(ActorOwnedRecord& r) {
    if(r.released)return true;
    // Revoke every borrowed skin/cache pointer BEFORE matrix space is reused.
    // A failed revocation keeps that space occupied until frame retirement.
    const bool skin_ok=re4dc_actor_skin_release(&r.skin)!=0;
    const bool okay=skin_ok && actor_palette_arena.release(r.palette);
    re4dc_actor_workspace_release(&r.workspace);
    for(unsigned i=r.plan.material_count;i>0;--i)re4dc_actor_texture_release(&r.textures[i-1]);
    r.released=1;
    if(!okay)actor_fail();
    return okay;
}
bool actor_plan_layout(Re4dcActorPlan& p) {
    if(!p.count || p.count>kRe4dcActorRoles)return false;
    // Legacy Ganado factories retain their one-atlas representation.
    if(!p.material_count && !p.run_count) {
        p.material_count=1;p.materials[0].image=p.image;p.materials[0].crc=p.crc;p.materials[0].fnv=p.fnv;
        for(unsigned i=0;i<p.count;++i) {
            const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
            r.role=i;r.immutable_asset_id=p.immutable_asset_id[i];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
        }
    }
    return p.material_count && p.material_count<=kRe4dcActorMaterials && p.run_count && p.run_count<=kRe4dcActorRuns;
}
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#include "coarse_actor_death_fade_context.inc"
#endif
#if RE4DC_NMR_BLENDTBL
// NATIVE_MODEL_REGISTRY_BLENDTBL (native_model_registry.mk): a registry actor's info with a texture blend table installed
// but idle (cModelInfo::setTexBlendTbl sets flagsDC 4; blendRatio 0 and blendType 0: trans.cpp TextureBlend adds no
// stage, the base textures show) draws as the base: the Novistador (em2d) keeps its table for the whole fight and
// blends only while its camouflage changes (em2dCamouflageMove).
#define RE4DC_NMR_BLEND_IDLE0(info,app) ((app)>=nmr::appearance_first && (info)->flagsDC==4u && (info)->texBlendTbl &&     !(info)->blendRatio && !(info)->blendType)
#else
#define RE4DC_NMR_BLEND_IDLE0(info,app) false
#endif
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
// PVR_RTT (pvr_rtt.mk): a registry info showing a render target through TexRenderModSet's table ({1, 0, ?, ?, 0xF7,
// 0xF8 + slot}) with blend type 2 and ratio 0xFF (em2cSetFreeze: the frozen Verdugo's ice) keeps its plan; the draw
// adds the target as a second pass (re4dc_nmr_ice_pass below).
extern "C" void re4dc_rtt_want(int slot);
extern "C" int re4dc_rtt_ready(int slot);
extern "C" void re4dc_rtt_override(int slot);
inline int re4dc_nmr_ice_slot(const cModelInfo* info) {
    if(!info || info->flagsDC!=4u || !info->texBlendTbl || info->blendType!=2 || info->blendRatio!=0xFFu)return -1;
    const unsigned char* t=static_cast<const unsigned char*>(info->texBlendTbl);
    return t[0]==1 && t[4]==0xF7 && t[5]>=0xF8?int(t[5])-0xF8:-1;
}
#define RE4DC_NMR_BLEND_ICE(info,app) ((app)>=nmr::appearance_first && re4dc_nmr_ice_slot(info)>=0)
#define RE4DC_NMR_BLEND_IDLE(info,app) (RE4DC_NMR_BLEND_IDLE0(info,app) || RE4DC_NMR_BLEND_ICE(info,app))
#else
#define RE4DC_NMR_BLEND_ICE(info,app) false
#define RE4DC_NMR_BLEND_IDLE(info,app) RE4DC_NMR_BLEND_IDLE0(info,app)
#endif
bool actor_semantics(cModel* m,const Re4dcActorPlan& p) {
    if(!m->pParts || !p.count || p.count>kRe4dcActorRoles || !p.palettes ||
#if RE4DC_ACTOR_GANADO_DEATH_FADE
       ((!actor_fade_eligible(m,p)) && (m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f)) || m->alpha_omit!=255 ||
#else
       m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f || m->alpha_omit!=255 ||
#endif
       m->z_mode!=0 || m->CullMode || m->Shader_type || m->AddAmb_r || m->AddAmb_g || m->AddAmb_b ||
       (m->be_flag&(0x4000u|0x00020000u)) ||
       !re4dc_actor::exact_infos(m->pModelInfo,p.info,p.count) ||
       !p.material_count || p.material_count>kRe4dcActorMaterials || !p.run_count || p.run_count>kRe4dcActorRuns)return false;
    // Shadow/depth, special rendering and texture modifications remain source.
    if(pG->Status_flg[1]&0x100)return false;
    if((pG->Status_flg[2]&0x00100000) && (m->be_flag&0x02000000) &&
       !(pG->Disp_flg&0x00040000) && (pG->Status_flg[1]&0x200))return false;
    unsigned palette_bytes=0,workspace_bytes=0;
    for(unsigned i=0;i<p.count;++i) {
        auto* info=p.info[i];
        // Hidden infos were still prepared and animated by the source callback.
        // They participate in the certificate and lease proof too.
        if(!info || !info->pData || info->invisible_factor!=1.0f || info->blend_mode ||
           info->colorWord!=0xffffffffu || (info->flagsDC && !RE4DC_NMR_BLEND_IDLE(info,p.appearance)) || info->pAddTpl || info->nAddTex ||
           (info->texBlendTbl && !RE4DC_NMR_BLEND_IDLE(info,p.appearance)) || info->pTexAnim || info->uvU || info->uvV || info->uvScrollU || info->uvScrollV ||
           ((info->be_flag&2) && !RE4DC_ACTOR_SHAPE_ROLE(p,i)))return false;
        re4dc_source::ChunkProof proof{};
        if(re4dc_actor_immutable_chunk_proof(p.immutable_asset_id[i],p.input[i],proof)!=re4dc_source::BlobError::None)return false;
        palette_bytes+=proof.palette_bytes;
        if(proof.skin_table_bytes>workspace_bytes)workspace_bytes=proof.skin_table_bytes;
    }
    if(palette_bytes!=p.palette_bytes || workspace_bytes!=p.workspace_bytes)return false;
    unsigned triangles[kRe4dcActorRoles]{},seen=0,materials=0,previous_role=0;
    for(unsigned j=0;j<p.run_count;++j) {
        const auto& r=p.runs[j];
        if(r.role>=p.count || r.material>=p.material_count || (j && r.role<previous_role))return false;
        previous_role=r.role;seen|=1u<<r.role;materials|=1u<<r.material;
        auto c=p.input[r.role];c.uv=r.uv;c.stream=r.stream;c.triangles=r.triangles;
        re4dc_source::ChunkProof proof{};
        // Compiled const run bytes have separate IDs29..42. Their shared role7
        // palette is accounted once above, never once per material run.
        if(re4dc_actor_immutable_chunk_proof(r.immutable_asset_id,c,proof)!=re4dc_source::BlobError::None)return false;
        if(r.triangles>p.input[r.role].triangles-triangles[r.role])return false;
        triangles[r.role]+=r.triangles;
    }
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
    unsigned covered=0;
    if(!re4dc_registry_covered_roles(m,&p,&covered) ||
       (seen|covered)!=(1u<<p.count)-1 || (seen&covered) || materials!=(1u<<p.material_count)-1)return false;
    for(unsigned i=0;i<p.count;++i)if(triangles[i]!=((covered&(1u<<i))?0u:p.input[i].triangles))return false;
#else
    if(seen!=(1u<<p.count)-1 || materials!=(1u<<p.material_count)-1)return false;
    for(unsigned i=0;i<p.count;++i)if(triangles[i]!=p.input[i].triangles)return false;
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    actor_certificate_reached=true;  // the registry census: a decline from here on is the material certificate's
#endif
    // Geometry signatures do not prove unchanged materials, costumes or TPLs.
    return re4dc_actor_material_certificate(m,&p)!=0;
}
#if RE4DC_ACTOR_TRANSACTION_DIAG
// WP2 census (diagnostic): actor_semantics' first failing clause, in its order (a read-only twin; the admission
// decision is still actor_semantics'). detail: the info index, run index or flag word involved.
extern "C" void re4dc_actor_txdiag_why(const cModel*,const char*,unsigned,unsigned);
unsigned actor_semantics_why(cModel* m,const Re4dcActorPlan& p,unsigned* detail) {
    *detail=0;
    if(!m->pParts)return 1;
    if(!p.count || p.count>kRe4dcActorRoles || !p.palettes){*detail=p.count;return 2;}
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    if(!actor_fade_eligible(m,p) && (m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f))return 3;
#else
    if(m->invisible_factor!=1.0f || m->invisible_factor2!=1.0f)return 3;
#endif
    if(m->alpha_omit!=255){*detail=m->alpha_omit;return 4;}
    if(m->z_mode!=0 || m->CullMode || m->Shader_type){*detail=(unsigned(m->z_mode)<<16)|(unsigned(m->CullMode)<<8)|unsigned(m->Shader_type);return 5;}
    if(m->AddAmb_r || m->AddAmb_g || m->AddAmb_b){*detail=(unsigned(m->AddAmb_r)<<16)|(unsigned(m->AddAmb_g)<<8)|unsigned(m->AddAmb_b);return 6;}
    if(m->be_flag&(0x4000u|0x00020000u)){*detail=m->be_flag;return 7;}
    if(!re4dc_actor::exact_infos(m->pModelInfo,p.info,p.count)){
        for(const cModelInfo* f=m->pModelInfo;f && *detail<999;f=f->pList)++*detail;
        return 8;
    }
    if(!p.material_count || p.material_count>kRe4dcActorMaterials || !p.run_count || p.run_count>kRe4dcActorRuns)return 9;
    if(pG->Status_flg[1]&0x100)return 10;
    if((pG->Status_flg[2]&0x00100000) && (m->be_flag&0x02000000) &&
       !(pG->Disp_flg&0x00040000) && (pG->Status_flg[1]&0x200))return 11;
    unsigned palette_bytes=0,workspace_bytes=0;
    for(unsigned i=0;i<p.count;++i) {
        auto* info=p.info[i];*detail=i;
        if(!info || !info->pData)return 12;
        if(info->invisible_factor!=1.0f)return 13;
        if(info->blend_mode){*detail=i<<16|info->blend_mode;return 14;}
        if(info->colorWord!=0xffffffffu){*detail=info->colorWord;return 15;}
        if(info->flagsDC && !RE4DC_NMR_BLEND_IDLE(info,p.appearance)){*detail=i<<16|info->flagsDC;return 16;}
        if(info->pAddTpl || info->nAddTex)return 17;
        if((info->texBlendTbl && !RE4DC_NMR_BLEND_IDLE(info,p.appearance)) || info->pTexAnim)return 18;
        if(info->uvU || info->uvV || info->uvScrollU || info->uvScrollV)return 19;
        if((info->be_flag&2) && !RE4DC_ACTOR_SHAPE_ROLE(p,i))return 20;
        re4dc_source::ChunkProof proof{};
        if(re4dc_actor_immutable_chunk_proof(p.immutable_asset_id[i],p.input[i],proof)!=re4dc_source::BlobError::None)return 21;
        palette_bytes+=proof.palette_bytes;
        if(proof.skin_table_bytes>workspace_bytes)workspace_bytes=proof.skin_table_bytes;
    }
    *detail=0;
    if(palette_bytes!=p.palette_bytes || workspace_bytes!=p.workspace_bytes)return 22;
    unsigned triangles[kRe4dcActorRoles]{},seen=0,materials=0,previous_role=0;
    for(unsigned j=0;j<p.run_count;++j) {
        const auto& r=p.runs[j];*detail=j;
        if(r.role>=p.count || r.material>=p.material_count || (j && r.role<previous_role))return 23;
        previous_role=r.role;seen|=1u<<r.role;materials|=1u<<r.material;
        auto c=p.input[r.role];c.uv=r.uv;c.stream=r.stream;c.triangles=r.triangles;
        re4dc_source::ChunkProof proof{};
        if(re4dc_actor_immutable_chunk_proof(r.immutable_asset_id,c,proof)!=re4dc_source::BlobError::None)return 24;
        if(r.triangles>p.input[r.role].triangles-triangles[r.role])return 25;
        triangles[r.role]+=r.triangles;
    }
    *detail=0;
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
    unsigned covered=0;
    if(!re4dc_registry_covered_roles(m,&p,&covered) ||
       (seen|covered)!=(1u<<p.count)-1 || (seen&covered) || materials!=(1u<<p.material_count)-1)return 26;
    for(unsigned i=0;i<p.count;++i)if(triangles[i]!=((covered&(1u<<i))?0u:p.input[i].triangles)){*detail=i;return 27;}
#else
    if(seen!=(1u<<p.count)-1 || materials!=(1u<<p.material_count)-1)return 26;
    for(unsigned i=0;i<p.count;++i)if(triangles[i]!=p.input[i].triangles){*detail=i;return 27;}
#endif
    if(!re4dc_actor_material_certificate(m,&p))return 28;
    return 0;
}
#endif
ActorOwnedRecord* actor_decline(ActorOwnedRecord& r,bool& failed) {
    const bool released=actor_release(r);Re4dcActorStreamState state{};
    if(!released || !re4dc_actor_stream_state(&state))failed=true;
    return nullptr;
}
#if RE4DC_ACTOR_SOURCE_LIT
// ACTOR_GANADO_SOURCE_LIGHT (default 0): a Ganado's owned draw is lit as the source lights it instead of the
// constant (flat) record. ModelTrans ran LightSetModel(m) just before commonModelTrans reached this owner, so the
// GX state already holds this model's selected light objects, channel control, ambient and material colour
// (re4dc_gx_model_lighting). commonModelTrans then loads per info nrm = (view * root * info)^-T (= part.mv^-T) and
// shaderSetup multiplies the rasterised colour by the TEV scale of gxCsScale[TevScaleGroup]; both are applied here.
// Returns the first failing clause (0 = lit record ready): 1 per-vertex colour source, 2 diffuse function other
// than clamp, 3 an info's material colour differs from the captured one (commonModelTrans would switch it per
// info), 4 role matrices differ (one record lights every role), 5 singular matrix, 6 TEV scale group/value.
// Any nonzero result declines the whole actor to the source path.
unsigned actor_source_lighting(cModel* m,ActorOwnedRecord& r) {
    auto& L=r.lit;re4dc_gx_model_lighting(&L);
    if(L.ambient_vertex || L.material_vertex)return 1;
    if(L.enable && L.diffuse!=2)return 2;
    const u8* base=static_cast<const u8*>(m->pModelInfo->color);
    for(unsigned i=0;i<r.count;++i) {
        const cModelInfo* info=r.part[i].info;
        const u8* c=(info->be_flag&0x20)?static_cast<const u8*>(info->color):base;
        if(std::memcmp(c,L.material,4))return 3;
        if(std::memcmp(r.part[i].mv,r.part[0].mv,sizeof(r.part[0].mv)))return 4;
    }
    Mtx mv,inv,nrm;std::memcpy(mv,r.part[0].mv,sizeof(mv));
    if(!PSMTXInverse(mv,inv))return 5;
    PSMTXTranspose(inv,nrm);std::memcpy(L.normal_matrix,nrm,sizeof(L.normal_matrix));
    if(m->TevScaleGroup>1 || gxCsScale[m->TevScaleGroup]>2)return 6;
    static const float scales[3]={1,2,4};
    L.tev_scale=scales[gxCsScale[m->TevScaleGroup]];
    return 0;
}
#endif
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
#include "actor_presentation32.inc"
#endif
ActorOwnedRecord* actor_acquire(cModel* m,const Re4dcActorPlan& p,
    const FrameIdentity& frame,const ModelIdentity& model,bool& failed
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    ,bool publish=true,const ActorFadeContext* captured=nullptr,unsigned fade_revision=0,const void* fade_parts=nullptr
#endif
    ) {
    failed=false;
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
    const ActorPresentation32Ticket presentation=actor_presentation32_capture(m);
#endif
    if(!p.palette_bytes || p.palette_bytes>kActorPaletteCap){ATD(m,7,p.palette_bytes,kActorPaletteCap);return nullptr;}
    re4dc_bind_actor_frame(); // existing single frame owner, before its lease
    Re4dcActorTextureLease textures[kRe4dcActorMaterials]{};
    Re4dcActorWorkspaceLease workspace{};
    unsigned acquired=0;
    auto release_textures=[&]{while(acquired)re4dc_actor_texture_release(&textures[--acquired]);};
    for(;acquired<p.material_count;++acquired) {
        const auto& mat=p.materials[acquired];
        if(!re4dc_actor_texture_acquire(&mat.image,mat.crc,mat.fnv,&textures[acquired])) {ATD(m,8,acquired,p.material_count);release_textures();return nullptr;}
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
        // Every acquisition may yield. Reprove before even reading the next
        // material's source image; include this newly acquired lease in unwind.
        if(presentation.direct && !actor_presentation32_current(m,p,frame,model,presentation)) {
            ++acquired;release_textures();failed=true;return nullptr;
        }
#endif
    }
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
    if(presentation.direct) {
        if(!actor_presentation32_reserve(p,frame.frame)){release_textures();return nullptr;}
    }
#endif
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    // All resource I/O is above this guard. The record allocation and every
    // operation after it are synchronous/non-yielding native proof routines.
    // G1 always supplies a stack-owned plan, never a pending-header reference.
    if(!publish && (!actor_fade_current({frame,model,0,0},captured?2u:1u) ||
       !fade_revision || m->pParts!=fade_parts || re4dc_actor_binding_revision(m)!=fade_revision)) {
        release_textures();failed=true;return nullptr;
    }
#endif
    if(!re4dc_actor_workspace_acquire(p.workspace_bytes,&workspace)) {
        ATD(m,9,p.workspace_bytes,0);
        release_textures();return nullptr;
    }
    const unsigned header=(sizeof(ActorOwnedRecord)+31u)&~31u;
    if(!actor_palette_arena.bound()) {
        // Fund the whole reusable bank, this record and the existing reserve.
        // The bank survives until primitive retirement, even after a decline.
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
#if RE4DC_ACTOR_TRANSACTION_DIAG
    {static const unsigned char* pal_first;static unsigned pal_peak,pal_logs;
        static unsigned pal_frame,pal_low;const auto* pm=static_cast<const unsigned char*>(palette_memory);
        if(pal_frame!=pG->Frame_cnt){pal_frame=pG->Frame_cnt;pal_low=~0u;}
        if(pm){const unsigned lo=unsigned(uintptr_t(pm));if(lo<pal_low){pal_low=lo;pal_first=pm;}
            const unsigned hw=unsigned(pm+p.palette_bytes-pal_first);
            if(hw>pal_peak && pal_logs++<60){pal_peak=hw;re4dc_log("APAL f=%u peak=%u id=%02x bytes=%u\n",unsigned(pG->Frame_cnt),hw,unsigned(m->id),p.palette_bytes);}}}
#endif
    void* memory=palette_memory?re4dc_prim_tail(header,kActorOwnerReserve):nullptr;
    if(!memory) {
        ATD(m,12,header,p.palette_bytes);
        if(!actor_palette_arena.release(palette_lease))failed=true;
        re4dc_actor_workspace_release(&workspace);release_textures();return nullptr;
    }
    auto* r=::new(memory) ActorOwnedRecord{};
    r->parts_owner=m->pParts;r->frame=frame;r->model=model;r->workspace=workspace;r->count=p.count;r->plan=p;
    r->palette=palette_lease;
    for(unsigned i=0;i<p.material_count;++i)r->textures[i]=textures[i];
    // All roles of this actor share one allocation. Material runs only borrow
    // their role's palette, including all fourteen ordered hair draws.
    float* palettes[kRe4dcActorRoles]{};unsigned at=0;
    for(unsigned i=0;i<p.count;++i) {
        palettes[i]=reinterpret_cast<float*>(static_cast<unsigned char*>(palette_memory)+at);
        at+=(p.input[i].palette_count*48u+31u)&~31u;
    }
    APROF_SPAN(aprof_pal,APROF_PAL);
    if(!p.palettes(m,p,palettes)){ATD(m,13,p.appearance,0);return actor_decline(*r,failed);}
    APROF_STOP(aprof_pal);
    Re4dcActorSkinBinding bindings[kRe4dcActorRoles]{};
    unsigned order=0;
    for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
        unsigned i=0;for(;i<p.count && p.info[i]!=info;++i){}
        if(i==p.count || order==p.count)return actor_decline(*r,failed);
        const auto& c=p.input[i];auto& part=r->part[order];
        part.info=info;part.flags=info->be_flag;part.role=i;
        part.source={c.positions.data,c.normals.data,c.position_count,c.normal_count,c.palette_count,0};
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        if(captured) {
            if(order>=captured->count || captured->info[order]!=info || captured->role[order]!=i)return actor_decline(*r,failed);
            part.flags=captured->flags[order];std::memcpy(part.mv,captured->mv[order],sizeof(part.mv));
        } else {
#endif
        Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
        std::memcpy(part.mv,mv,sizeof(mv));
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        }
#endif
        for(float f:part.mv)if(!coarse_finite(f))return actor_decline(*r,failed);
        part.chunk={info,c.stream.data,c.uv.data,part.mv,unsigned(c.stream.size),c.position_count,c.normal_count};
#if RE4DC_ACTOR_SOURCE_SPAN
        if(!re4dc_actor::source_span(c,part.chunk.source_span))return actor_decline(*r,failed);
#endif
        bindings[order]={info,part.source,palettes[i],c.palette_count};
        // Expand materials in this role's source order, not texture-key order.
        for(unsigned j=0;j<p.run_count;++j)if(p.runs[j].role==i) {
            const auto& run=p.runs[j];auto& draw=r->runs[r->run_count++];
            draw.chunk={info,run.stream.data,run.uv.data,part.mv,unsigned(run.stream.size),c.position_count,c.normal_count};
#if RE4DC_ACTOR_SOURCE_SPAN
            auto run_input=c;run_input.uv=run.uv;run_input.stream=run.stream;
            if(!re4dc_actor::source_span(run_input,draw.chunk.source_span))return actor_decline(*r,failed);
#endif
            draw.material=run.material;
        }
        ++order;
    }
    if(!re4dc_actor_skin_acquire(frame.frame,bindings,order,&r->skin)){ATD(m,14,order,0);return actor_decline(*r,failed);}
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
    if(presentation.direct && !actor_presentation32_forget_source(r->skin))return actor_decline(*r,failed);
#endif
#if RE4DC_ACTOR_SOURCE_SPAN
    // Every refresh/mutation/re-LOD retires owned records first. Each new skin
    // lease gets a never-reused serial, even on same-address/same-frame reuse.
    for(unsigned i=0;i<r->count;++i) {
        auto& a=r->part[i].chunk.source_span;a.owner_serial=r->skin.serial;a.owner_frame=r->skin.frame;
    }
    for(unsigned j=0;j<r->run_count;++j) {
        auto& a=r->runs[j].chunk.source_span;a.owner_serial=r->skin.serial;a.owner_frame=r->skin.frame;
    }
#endif
    auto& b=r->base;b.model=m;b.position_stride=6;b.normal_stride=6;b.normal_shift=14;b.shift=4;
#if RE4DC_NMR_SHIFT
    b.shift=registry_position_shift(p.appearance);
#endif
    b.lighting=&light;b.image=p.image;b.source_key[2]=1;b.depth_mode=m->z_mode;b.cull=0;b.alpha_state=255;
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
    if(RE4DC_LEON_LIKE(p.appearance))b.lighting=RE4DC_LEON_FLAT_LIGHT;  // LEON_LIGHT_HEADROOM: 128 on the 2x textures
#endif
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    if(captured) {
        b.alpha_state=captured->alpha;b.source_key[2]=captured->fog;
#if RE4DC_NMR_DYING
        if(captured->own_lit)
#endif
        {r->lit=captured->lit;b.lighting=&r->lit;}
    } else if(actor_fade_eligible(m,p)) {
        b.alpha_state=re4dc_fade::alpha(m->invisible_factor,m->invisible_factor2,1.0f,255);
        b.source_key[2]=re4dc_fog_enabled();
    }
#endif
#if RE4DC_NMR_SOURCE_CULL
    // NATIVE_MODEL_REGISTRY: the selected registry bosses (bit 1 em2f) cull as the source path does (model_bridge.cpp;
    // the plan admits CullMode 0 only), not cull none: from inside Del Lago's body the source shows no inner faces.
    if(p.appearance>=nmr::appearance_first && (((RE4DC_NMR_SOURCE_CULL&2) && m->id==0x2F) ||
                                               ((RE4DC_NMR_SOURCE_CULL&16) && m->id==0x22) ||
                                               ((RE4DC_NMR_SOURCE_CULL&8) && m->id==0x23)))
        b.cull=(unsigned char)re4dc_model_cull(m->CullMode,(pG->Debug_flg[0]&0x20000000)!=0);
#endif
#if defined(RE4DC_ACTOR_BACKFACE) && RE4DC_ACTOR_BACKFACE
    // ACTOR_BACKFACE (backface.mk, needs CPU_BACKFACE): Leon (id 0), the Ganados (0x10..0x20) and El Gigante (0x2B) take the source model's
    // cull mode (as model_bridge.cpp's source path and the NMR_SOURCE_CULL bosses do) instead of cull none; per material,
    // native_actor_owner_runs.inc keeps alpha-mask and no-depth-write materials double-sided.
#if defined(RE4DC_ACTOR_BACKFACE_CONE) && RE4DC_ACTOR_BACKFACE_CONE
    // ACTOR_BACKFACE_CONE (backface.mk): the same classes plus Ashley (id 3); the converter splits these models' opaque
    // parts by palette entry and facing (native_actor_fast.cpp re4dc_abc_mark).
    {
        const unsigned abc=m->id==0?1u:(m->id>=0x10 && m->id<=0x20)?2u:m->id==0x2B?3u:m->id==3?4u:0u;
        if(abc)b.cull=(unsigned char)re4dc_model_cull(m->CullMode,(pG->Debug_flg[0]&0x20000000)!=0);
        if(abc)re4dc_abc_mark(m,abc);
    }
#else
    if(m->id==0 || (m->id>=0x10 && m->id<=0x20) || m->id==0x2B)  // + El Gigante (em2b)
        b.cull=(unsigned char)re4dc_model_cull(m->CullMode,(pG->Debug_flg[0]&0x20000000)!=0);
#endif
#endif
#if RE4DC_ACTOR_GANADO_SOURCE_LIGHT
    if(!RE4DC_LEON_LIKE(p.appearance)) {
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        if(!captured)
#endif
        if(const unsigned why=actor_source_lighting(m,*r)){ATD(m,26,why,p.appearance);return actor_decline(*r,failed);}
        b.lighting=&r->lit;
    }
#elif RE4DC_NMR_SOURCE_LIGHT
    if(p.appearance>=nmr::appearance_first &&
       (((RE4DC_NMR_SOURCE_LIGHT&1) && m->id==0x2B) || ((RE4DC_NMR_SOURCE_LIGHT&2) && m->id==0x2F) ||
        ((RE4DC_NMR_SOURCE_LIGHT&4) && (m->id==0x17 || m->id==0x16)) || ((RE4DC_NMR_SOURCE_LIGHT&16) && m->id==0x22) ||
        ((RE4DC_NMR_SOURCE_LIGHT&8) && m->id==0x23) || ((RE4DC_NMR_SOURCE_LIGHT&32) && m->id==0x18)
#if RE4DC_NMR_POOL
        || ((RE4DC_NMR_SOURCE_LIGHT&64) && p.pool)
#endif
        )) {
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        if(!captured)
#endif
        if(const unsigned why=actor_source_lighting(m,*r)){ATD(m,26,why,p.appearance);return actor_decline(*r,failed);}
        b.lighting=&r->lit;
    }
#endif
#if RE4DC_PS2_GANADO_LIT && !RE4DC_ACTOR_GANADO_SOURCE_LIGHT
    if(p.appearance<0x100u) {
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        if(!captured)
#endif
        if(const unsigned why=actor_source_lighting(m,*r)){ATD(m,26,why,p.appearance);return actor_decline(*r,failed);}
        b.lighting=&r->lit;
    }
#endif
#if RE4DC_LEON_SOURCE_LIGHT
    // LEON_SOURCE_LIGHT (crowd.mk; render only): Leon takes the source GX light set LightSetModel loaded for him
    // (as PS2_GANADO_LIT does for the cast Ganados) instead of the constant record. His roles differ in rotation, so
    // the record is marked per part (normal_matrix[3]) and the kernel builds each part's normal matrix
    // (native_actor_fast.cpp build_lights). Never a decline: a record the kernel cannot take keeps the constant
    // colour, so Leon stays on the PS2 owner path.
    if(RE4DC_LEON_LIKE(p.appearance)) {
        auto& L=r->lit;re4dc_gx_model_lighting(&L);
        const bool ok=L.enable && !L.ambient_vertex && !L.material_vertex && L.diffuse==2 &&
                      m->TevScaleGroup<=1 && gxCsScale[m->TevScaleGroup]<=2;
        if(ok) {
            static const float scales[3]={1,2,4};
            L.tev_scale=scales[gxCsScale[m->TevScaleGroup]];L.normal_matrix[3]=1.0e30f;b.lighting=&L;
        }
        static unsigned leon_lit_n,leon_lit_fail;++leon_lit_n;if(!ok)++leon_lit_fail;
        if(leon_lit_n<=3 || leon_lit_n%600==0) {
            unsigned lights=0;for(unsigned i=0;i<8;++i)lights+=(L.mask>>i)&1u;
            re4dc_log("LEON_LIGHT t=%u n=%u fail=%u enable=%u lights=%u amb=%u,%u,%u mat=%u,%u,%u tev=%u\n",
                unsigned(pG->Frame_cnt),leon_lit_n,leon_lit_fail,L.enable,lights,L.ambient[0],L.ambient[1],L.ambient[2],
                L.material[0],L.material[1],L.material[2],unsigned(L.tev_scale));
        }
    }
#endif
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    if(captured) {
        std::memcpy(b.projection,captured->projection,sizeof(b.projection));
        std::memcpy(b.viewport,captured->viewport,sizeof(b.viewport));
    } else {
#endif
    GXGetProjectionv(b.projection);GXGetViewportv(b.viewport);
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    }
#endif
    r->passes=m->ot_type==7?3u:1u;
    // The whole actor, BOTH pass groups, qualifies before its first TA header.
    APROF_SPAN(aprof_pre1,APROF_PRE1);
    if(r->run_count!=p.run_count || !re4dc_actor_preflight_owned_runs(&b,r->runs,r->run_count,p.materials,p.material_count,&r->workspace,&r->skin,r->textures)) {
        ATD(m,15,r->run_count,p.run_count);return actor_decline(*r,failed);
    }
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    if(!publish)return r;
#endif
    r->next=actor_owned_head;actor_owned_head=r;return r;
}
}
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#include "coarse_actor_death_fade.inc"
#endif

#if RE4DC_CROWD
// Lane crowd (crowd.mk; render only): after the owner path admitted a Ganado (plan + semantics), decide whether its
// cast mesh is acquired and submitted at all. A Ganado that is not drawn takes presentation choice 2 (native, so the
// source callback never draws it) with no record: both of its OT passes return "handled" without a submission. Its
// simulation, skeleton and collision ran before and are untouched.
//   reason 1: CROWD_CULL, every visible chunk provably off-screen (re4dc_crowd_offscreen, the cast pregate balls)
//   reason 2: CROWD_DRAW_M, farther than D metres; reason 3: CROWD_DRAW_MAX, beyond the N nearest;
//   reason 4: CROWD_FOGSKIP, root beyond the fogged View far + 2.5 m.
extern "C" int re4dc_crowd_offscreen(cModel*);  // coarse_actor_owner_ganado.inc
#if RE4DC_CROWD_OUTPUT
extern "C" unsigned re4dc_model_output_count();  // native_ui.cpp, census / cull-check builds only
#endif
extern "C" unsigned re4dc_ui_frame();
#if RE4DC_CROWD_FREEZE_AT
#include <arch/timer.h>
#endif
#if RE4DC_CROWD_CENSUS
extern "C" void re4dc_crowd_life_report(unsigned);  // actor_lifetime.inc
#endif
namespace {
constexpr unsigned kCrowdSkips=64;
ModelIdentity crowd_skip[kCrowdSkips];
unsigned crowd_skips;
bool crowd_ganado(cModel* m) { return m && m->id>=0x10 && m->id<=0x20; }  // owner_ganado_bind's class
// The root's camera distance and view depth (-z; source units: millimetres).
float crowd_distance(cModel* m,float* depth) {
    const float (*r)[4]=m->pParts->mat;const float (*v)[4]=pG->Cam.v_mat;
    float t[3];
    for(unsigned i=0;i<3;++i)t[i]=v[i][0]*r[0][3]+v[i][1]*r[1][3]+v[i][2]*r[2][3]+v[i][3];
    *depth=-t[2];
    return __builtin_sqrtf(t[0]*t[0]+t[1]*t[1]+t[2]*t[2]);
}
// CROWD_CULL's fog test is the pregate balls' far plane at the fog-gate cull depth (re4dc_crowd_offscreen). The
// first version (root depth > fog far + 2.5 m) was not exact: the =2 check found 16 actor-frames at view l whose
// root lay 27.5..28.3 m deep and that still emitted 396..617 triangles (cw-ck-l, cw-ck2-l).
extern "C" float re4dc_fog_gate_far();
#if RE4DC_CROWD_DRAW_MAX >= 0 || RE4DC_CROWD_NEAR_MAX >= 0
// Distances of the previous frame's drawable Ganados (kept by the cull and the distance limit), and this frame's.
struct CrowdSeen { std::uintptr_t address; float d; };
CrowdSeen crowd_prev[kCrowdSkips],crowd_cur[kCrowdSkips];
unsigned crowd_prev_n,crowd_cur_n;
#endif
#if RE4DC_CROWD_CENSUS
struct CrowdCensus { unsigned frame,game,seen,admitted,skip[5],drawn,empty,band[4],tris,cullcheck; } crowd_cc;
#endif
#if RE4DC_CROWD_CULL == 2
unsigned crowd_chk_would,crowd_chk_violations,crowd_chk_tris,crowd_chk_log;
#endif
unsigned crowd_why;float crowd_depth,crowd_fog;  // the last crowd_policy's cull test, for the =2 check's log
void crowd_frame_begin() {
#if RE4DC_CROWD_FREEZE_AT
    // Look sheets only (CROWD_FREEZE_AT=N): stop in game frame N's first owner draw; frame N-1, already presented,
    // stays on screen, so every later capture of two arms shows the same game frame.
    // CROWD_FREEZE_AT2 / CROWD_FREEZE_HOLD (seconds, 0 = forever): hold at each of the two frames for HOLD s, so
    // one run gives a sheet frame per fixture view.
    {
        static unsigned crowd_frozen;
        const unsigned at[2]={unsigned(RE4DC_CROWD_FREEZE_AT),unsigned(RE4DC_CROWD_FREEZE_AT2)};
        for(unsigned k=0;k<2;++k) {
            if(!at[k] || (crowd_frozen>>k&1u) || unsigned(pG->Frame_cnt)<at[k])continue;
            crowd_frozen|=1u<<k;
            re4dc_log("CROWD_FREEZE t=%u: the screen holds frame %u\n",unsigned(pG->Frame_cnt),unsigned(pG->Frame_cnt)-1);
            if(!RE4DC_CROWD_FREEZE_HOLD)for(;;)__asm__ volatile("nop");
            const unsigned long long until=timer_ms_gettime64()+1000ull*RE4DC_CROWD_FREEZE_HOLD;
            while(timer_ms_gettime64()<until)__asm__ volatile("nop");
            re4dc_log("CROWD_FREEZE t=%u released\n",unsigned(pG->Frame_cnt));
        }
    }
#endif
#if RE4DC_CROWD_CENSUS
    const CrowdCensus& c=crowd_cc;
    if(c.seen && c.frame>=RE4DC_CROWD_CENSUS_FROM && c.frame<=RE4DC_CROWD_CENSUS_TO)
        re4dc_log("CROWDC f=%u t=%u seen=%u admitted=%u off=%u far=%u cap=%u drawn=%u empty=%u band=%u/%u/%u/%u tris=%u\n",
            c.frame,c.game,c.seen,c.admitted,c.skip[1],c.skip[2],c.skip[3],c.drawn,c.empty,c.band[0],c.band[1],c.band[2],
            c.band[3],c.tris);
    crowd_cc=CrowdCensus{};crowd_cc.frame=re4dc_ui_frame();crowd_cc.game=unsigned(pG->Frame_cnt);
    if(!(crowd_cc.frame%120))re4dc_crowd_life_report(crowd_cc.frame);
#endif
#if RE4DC_CROWD_CULL == 2
    if(!(pG->Frame_cnt%120))
        re4dc_log("CROWDCULL t=%u would_cull=%u violations=%u violation_tris=%u\n",unsigned(pG->Frame_cnt),crowd_chk_would,
            crowd_chk_violations,crowd_chk_tris);
#endif
#if RE4DC_CROWD_DRAW_MAX >= 0 || RE4DC_CROWD_NEAR_MAX >= 0
    std::memcpy(crowd_prev,crowd_cur,sizeof(crowd_cur));crowd_prev_n=crowd_cur_n;crowd_cur_n=0;
#endif
}
// 0: draw; 1..3: the reason it is not drawn (above).
unsigned crowd_policy(cModel* m) {
    float depth;
    const float d=crowd_distance(m,&depth);
    (void)d;(void)depth;
#if RE4DC_CROWD_CENSUS
    ++crowd_cc.admitted;++crowd_cc.band[d<5000.0f?0:d<12000.0f?1:d<25000.0f?2:3];
#endif
#if RE4DC_CROWD_CULL
    crowd_depth=depth;crowd_fog=re4dc_fog_gate_far();crowd_why=2;
    if(re4dc_crowd_offscreen(m))return 1;
    crowd_why=0;
#endif
#if RE4DC_CROWD_FOGSKIP
    // Reason 4, CROWD_FOGSKIP (look change, the user's call): the root lies more than 2.5 m beyond the fogged View far
    // (the GC clips there; the actor path's own gate bound still emits some of these Ganados fully fogged).
    {
        const float fog=re4dc_fog_gate_far();
        if(fog>0.0f && depth-2500.0f>fog)return 4;
    }
#endif
#if RE4DC_CROWD_DRAW_M > 0
    if(d>float(RE4DC_CROWD_DRAW_M)*1000.0f)return 2;
#endif
#if RE4DC_CROWD_DRAW_MAX >= 0 || RE4DC_CROWD_NEAR_MAX >= 0
    const std::uintptr_t a=reinterpret_cast<std::uintptr_t>(m);
    if(crowd_cur_n<kCrowdSkips)crowd_cur[crowd_cur_n++]={a,d};
    unsigned rank=0;
    for(unsigned k=0;k<crowd_prev_n;++k)if(crowd_prev[k].address!=a && crowd_prev[k].d<d)++rank;
    (void)rank;
#if RE4DC_CROWD_DRAW_MAX >= 0
    if(rank>=unsigned(RE4DC_CROWD_DRAW_MAX))return 3;
#endif
#endif
    return 0;
}
bool crowd_skipped(const ModelIdentity& model) {
    for(unsigned k=0;k<crowd_skips;++k)if(crowd_skip[k]==model)return true;
    return false;
}
}
#if RE4DC_CROWD_FAR
// The far tier (crowd.mk CROWD_FAR_M / CROWD_NEAR_MAX; a look change): 1 when re4dc_actor_plan_ganado should plan m
// with the far bundle's chunks. Called by the plan, before crowd_policy; the rank is against the previous frame's
// drawn Ganados (crowd_prev), as CROWD_DRAW_MAX's.
extern "C" int re4dc_crowd_far(cModel* m) {
    float depth;
    const float d=crowd_distance(m,&depth);
    (void)d;(void)depth;
#if RE4DC_CROWD_FAR_M > 0
    if(d>float(RE4DC_CROWD_FAR_M)*1000.0f)return 1;
#endif
#if RE4DC_CROWD_NEAR_MAX >= 0
    const std::uintptr_t a=reinterpret_cast<std::uintptr_t>(m);
    unsigned rank=0;
    for(unsigned k=0;k<crowd_prev_n;++k)if(crowd_prev[k].address!=a && crowd_prev[k].d<d)++rank;
    if(rank>=unsigned(RE4DC_CROWD_NEAR_MAX))return 1;
#endif
    return 0;
}
#endif
#endif
#if RE4DC_LEON_NATIVE_PIPE
#include "coarse_actor_leon_pipe.inc"  // LEON_NATIVE_PIPE (native_model_registry.mk): Leon's lean owner passes
#endif
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
extern "C" void re4dc_ganado_lod_retired();  // coarse_ganado_lod.inc (coarse_ganado_cast.cpp)
#endif
#if RE4DC_ACTOR_GANADO_PS2_STUMP
// ACTOR_GANADO_PS2_STUMP: the variant cell (coarse_actor_owner_ganado.inc, another unit) revokes owned records before
// it frees the bytes they may name.
extern "C" int re4dc_actor_owned_live() {return actor_owned_live?1:0;}
#endif
extern "C" void re4dc_actor_transaction_retire() {
    // Revoke exported owners without traversing old primitive storage. This is
    // called BEFORE FrameLedger retirement and SetPrimBuffPtr storage reuse.
#if RE4DC_ACTOR_GANADO_DEATH_FADE
    actor_fade_retire();
#endif
    actor_owned_head=nullptr;actor_owned_live=false;
#if RE4DC_LEON_NATIVE_PIPE
    leon_pipe.live=false;  // its leases are revoked below with every other owner's
#endif
#if RE4DC_CROWD
    crowd_skips=0;
#endif
    re4dc_actor_owner_retire(); // revoke cached matrix pointers before bank reuse
    re4dc_actor_model_frame_retire(); // next primitive owner must reacquire its workspace
    actor_palette_arena.retire();
    re4dc_actor_texture_retire_all();
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
    leon_lod::retired();          // LEON_LOD: a level asked for since the last load loads here (nothing owned is live)
#endif
#if defined(RE4DC_GANADO_LOD) && RE4DC_GANADO_LOD
    re4dc_ganado_lod_retired();   // GANADO_LOD: the same for the cast Ganados (coarse_ganado_lod.inc)
#endif
}
#if RE4DC_CROWD_INVIS_SKIP
// CROWD_INVIS_SKIP (crowd.mk): each Ganado's path in this Render, for the next Trans's decision (owner admission:
// re4dc_crowd_offscreen; plan declined: 2; anything else, or a later decline: 0).
extern "C" void re4dc_invis_note(cModel*,unsigned);  // coarse_actor_owner_ganado.inc
#define INVIS_NOTE(m,k) re4dc_invis_note(m,k)
#else
#define INVIS_NOTE(m,k)
#endif
#if RE4DC_PS2_INTERIOR_OWNER && RE4DC_CROWD
// PS2_INTERIOR_ACTORS=2 (game30.mk): owner-path Ganados hidden by the r100 house interior cell.
extern "C" int re4dc_invis_owner_marked(cModel*);  // coarse_actor_owner_ganado.inc
extern "C" int re4dc_actor_owned_crowd_replay(const Re4dcModelPart*,const Re4dcActorDrawRun*,unsigned,
    const Re4dcActorOwnedMaterial*,unsigned,int,float*);  // native_actor_fast.cpp
#if RE4DC_PS2_INTERIOR_OWNER == 2
extern "C" int re4dc_actor_crowd_peek(const void*,float*);  // native_actor_fast.cpp
#endif
extern "C" { unsigned re4dc_pco_skipped,re4dc_pco_declined,re4dc_pco_checked,re4dc_pco_check_mis; }
#endif
#if defined(RE4DC_ENCV) && RE4DC_ENCV
extern "C" unsigned re4dc_encv_crowd;  // ENC_CENSUS=2 (coarse.cpp): the crowd policy's reason in this call
#endif
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
// ENC_CENSUS (diagnostic, default 0): the draw below runs unchanged; coarse.cpp counts its result per model.
extern "C" void re4dc_enc_note_actor(const void*,int);
static int enc_transaction_draw(cModel* m);
extern "C" int re4dc_actor_transaction_draw(cModel* m) {
    const int result=enc_transaction_draw(m);
    re4dc_enc_note_actor(m,result);
    return result;
}
static int enc_transaction_draw(cModel* m) {
#elif defined(RE4DC_ACTOR_PROF) && RE4DC_ACTOR_PROF
// ACTOR_PROF (diagnostic): the draw below runs unchanged; TX = this call minus the PS2 world flushes it triggers.
static int aprof_transaction_draw(cModel* m);
extern "C" int re4dc_actor_transaction_draw(cModel* m) {
    APROF_FRAME(unsigned(pG->Frame_cnt));
    APROF_CLS(!m?2u:m->id==0?0u:(m->id>=0x10 && m->id<=0x20)?1u:2u);
    APROF_COUNT(APROF_N_CALLS,1);
    const unsigned t=re4dc_aprof_now(),w=re4dc_aprof_wfl_cycles;
    const int result=aprof_transaction_draw(m);
    re4dc_aprof_add(APROF_TX,re4dc_aprof_now()-t-(re4dc_aprof_wfl_cycles-w));
    APROF_CLS(3u);
    return result;
}
static int aprof_transaction_draw(cModel* m) {
#else
extern "C" int re4dc_actor_transaction_draw(cModel* m) {
#endif
    RE4DC_BFC_SCOPE(!m?5u:m->id==0?3u:(m->id>=0x10 && m->id<=0x20)?4u:5u,m?unsigned(m->id):0u);  // BACKFACE_CENSUS
    ATD(m,0,0,0);INVIS_NOTE(m,0);
#if RE4DC_ACTOR_BIND_REUSE
    ++re4dc_actor_tx_serial;  // this call: the Ganado plan's binding token names it (coarse_actor_owner_ganado.inc)
#endif
#if RE4DC_ACTOR_PROOF_LEAN
    // The lifetime serial right after THIS call's admitting actor_semantics (0: this call admitted nothing).
    unsigned lean_serial=0;
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    ++registry_tx_serial;  // this call (the registry plan's token names it)
    bool tx_semantics_held=false;
#endif
    FrameIdentity frame{};ModelIdentity model{};unsigned choice=0;
    const int identity=re4dc_actor_transaction_identity(m,&frame,&model);
    if(identity<0){actor_fail();return -1;}
    if(!identity){ATD(m,1,0,0);return 0;}
    // Frame identity is checked BEFORE touching any retained record pointer.
    if(actor_owned_live && !(actor_owned_frame==frame)){actor_fail();return -1;}
    if(!actor_owned_live){
        actor_owned_frame=frame;actor_owned_live=true;
#if RE4DC_CROWD
        crowd_frame_begin();
#endif
    }
    if(!re4dc_actor_transaction_choice(m,&choice)){actor_fail();return -1;}
    if(choice==1){ATD(m,2,0,0);return 0;} // sticky original-source decision, including pass two
    ActorOwnedRecord* r=nullptr;
#if RE4DC_CROWD
    unsigned crowd_would=0;
    if(choice==0 && crowd_ganado(m)) {
#if RE4DC_CROWD_CENSUS
        ++crowd_cc.seen;
#endif
    }
#endif
    if(choice==2) {
#if RE4DC_ACTOR_GANADO_DEATH_FADE
        // ot_type 0 has one source call. Even a completed fade is not a legal
        // second pass; never reinterpret its pending record as a leased owner.
        if(actor_fade_find(model)){actor_fail();return -1;}
#endif
#if RE4DC_LEON_NATIVE_PIPE
        if(leon_pipe.live && leon_pipe.r.model==model) {
            if(!(leon_pipe.r.frame==frame)){actor_fail();return -1;}
            return leon_pass(m,leon_pipe.r,false);
        }
#endif
        for(auto* p=actor_owned_head;p;p=p->next)if(p->model==model){r=p;break;}
#if RE4DC_CROWD
        if(!r && crowd_skipped(model))return 1;  // a Ganado the crowd policy does not draw: its second pass
#endif
        if(!r || !(r->frame==frame)){actor_fail();return -1;}
    } else {
        // Mark source first; any pre-header admission failure retains the
        // already prepared original path and cannot retry in a later OT group.
        if(!re4dc_actor_transaction_choose(m,1)){actor_fail();return -1;}
        if(m->ot_type==7 && (m->be_flag&0x08000000)){ATD(m,3,0,0);return 0;}
#if RE4DC_LEON_NATIVE_PIPE
        {const int lean=leon_pipe_first(m,frame,model);if(lean!=2)return lean;}
#endif
        APROF_SPAN(aprof_plan,APROF_PLAN);
        Re4dcActorPlan p{};
#if RE4DC_NATIVE_MODEL_REGISTRY
        // NATIVE_MODEL_REGISTRY: the generic descriptors plan after Leon and the Ganado cast. NMR_CENSUS: census builds
        // only (NATIVE_MODEL_REGISTRY_CENSUS=1) count every outcome of an actor's first pass in the scene census
        // (coarse_actor_owner_registry.inc); a production / cost build compiles none of it.
#if RE4DC_NMR_FIRST
        // NATIVE_MODEL_REGISTRY_FIRST: a Ganado-class actor that a room descriptor binds (registry_bind: its id, infos and
        // role rows) plans through that descriptor before the Ganado cast; any other actor plans as without the knob.
#if RE4DC_ACTOR_PL08
        const bool leon_plan=re4dc_actor_plan_leon(m,&p) || re4dc_actor_plan_pl08(m,&p);
#else
        const bool leon_plan=re4dc_actor_plan_leon(m,&p);
#endif
        const bool registry_first=!leon_plan && m->id>=0x10 && m->id<=0x20 && registry_id(m->id) && registry_bind(m);
        const unsigned plan_kind=leon_plan?1u:(registry_first && re4dc_actor_plan_registry(m,&p))?3u:
            re4dc_actor_plan_ganado(m,&p)?2u:(!registry_first && re4dc_actor_plan_registry(m,&p))?3u:0u;
#elif RE4DC_ACTOR_PL08
        const unsigned plan_kind=(re4dc_actor_plan_leon(m,&p) || re4dc_actor_plan_pl08(m,&p))?1u:re4dc_actor_plan_ganado(m,&p)?2u:re4dc_actor_plan_registry(m,&p)?3u:0u;
#else
        const unsigned plan_kind=re4dc_actor_plan_leon(m,&p)?1u:re4dc_actor_plan_ganado(m,&p)?2u:re4dc_actor_plan_registry(m,&p)?3u:0u;
#endif
        if(!plan_kind){
            ATD(m,4,0,0);INVIS_NOTE(m,2);
#if RE4DC_ACTOR_TRANSACTION_DIAG
            if(m->id==0 && m->ot_type==7){unsigned d=0;const unsigned why=owner_leon_bind_why(m,&d);
                re4dc_actor_txdiag_why(m,"leon_bind",why?why:99,d);}  // 99: bound, the plan's own checks declined
#endif
            // The plan the actor's class has (Leon, the Ganado cast, a registry descriptor) declined, or none exists.
            NMR_CENSUS(const unsigned expected=m->id==0?1u:(m->id>=0x10 && m->id<=0x20)?2u:registry_id(m->id)?3u:0u;
                scene_note(m,expected,expected==3?kScRegistryDeclined:expected?kScDeclined:kScAbsent));
            return 0;
        }
        if(!actor_plan_layout(p)){
            ATD(m,5,p.count,p.run_count);
            NMR_CENSUS(if(plan_kind==3)registry_decline(m,&p,kRwLayout);
                scene_note(m,plan_kind,plan_kind==3?kScRegistryDeclined:kScDeclined));
            return 0;
        }
        APROF_STOP(aprof_plan);
        NMR_CENSUS(actor_certificate_reached=false);
        APROF_SPAN(aprof_sem1,APROF_SEM1);
        if(!actor_semantics(m,p)){
            ATD(m,6,p.appearance,p.count);
#if RE4DC_ACTOR_TRANSACTION_DIAG
            {unsigned d=0;const unsigned why=actor_semantics_why(m,p,&d);re4dc_actor_txdiag_why(m,"semantics",why,d);
                if(why==3)re4dc_actor_vis_decline(m,p.appearance,p.info,p.count);}
#endif
            NMR_CENSUS(if(plan_kind==3)registry_decline(m,&p,actor_certificate_reached?kRwCertificate:kRwSemantics);
                scene_note(m,plan_kind,plan_kind==3?kScRegistryDeclined:kScDeclined));
            return 0;
        }
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
#if !RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
#error NATIVE_MODEL_REGISTRY=2 reports through the census (NATIVE_MODEL_REGISTRY_CENSUS=1)
#endif
        // Compare mode: the admitted registry actor's palettes are built into a scratch buffer (finite check) and the
        // actor keeps the source path: no lease, no native TA submission.
        if(plan_kind==3) {
            float* scratch[8];for(auto& s:scratch)s=registry_scratch;
            const bool ok=p.palettes(m,p,scratch)!=0;
            auto& c=registry_count[p.appearance-nmr::appearance_first];
            if(ok)++c.would;else{++c.declined;++c.why[kRwSkin];}
            scene_note(m,3,ok?kScWould:kScRegistryDeclined);return 0;
        }
#endif
#else
#if RE4DC_ACTOR_PL08
        if(!(re4dc_actor_plan_leon(m,&p) || re4dc_actor_plan_pl08(m,&p) || re4dc_actor_plan_ganado(m,&p))){
#else
        if(!(re4dc_actor_plan_leon(m,&p) || re4dc_actor_plan_ganado(m,&p))){
#endif
            ATD(m,4,0,0);INVIS_NOTE(m,2);
#if RE4DC_ACTOR_TRANSACTION_DIAG
            if(m->id==0 && m->ot_type==7){unsigned d=0;const unsigned why=owner_leon_bind_why(m,&d);
                re4dc_actor_txdiag_why(m,"leon_bind",why?why:99,d);}  // 99: bound, the plan's own checks declined
#endif
            return 0;
        }
        if(!actor_plan_layout(p)){ATD(m,5,p.count,p.run_count);return 0;}
        if(!actor_semantics(m,p)){
            ATD(m,6,p.appearance,p.count);
#if RE4DC_ACTOR_TRANSACTION_DIAG
            {unsigned d=0;const unsigned why=actor_semantics_why(m,p,&d);re4dc_actor_txdiag_why(m,"semantics",why,d);
                if(why==3)re4dc_actor_vis_decline(m,p.appearance,p.info,p.count);}
#endif
            return 0;
        }
#endif
        APROF_STOP(aprof_sem1);
#if RE4DC_ACTOR_PROOF_LEAN
        lean_serial=re4dc_material::life::exhausted?0u:re4dc_material::life::serial;
#endif
        APROF_SPAN(aprof_crowd,APROF_CROWD);
#if RE4DC_CROWD
        if(crowd_ganado(m)) {
            crowd_would=crowd_policy(m);
#if RE4DC_ACTOR_GANADO_DEATH_FADE
            if(crowd_would && actor_fade_eligible_g1(m,p))return 0;
#endif
#if defined(RE4DC_ENCV) && RE4DC_ENCV
            re4dc_encv_crowd=crowd_would;  // ENC_CENSUS=2 (coarse.cpp)
#endif
#if RE4DC_CROWD_CENSUS
            ++crowd_cc.skip[crowd_would];
#endif
#if RE4DC_CROWD_CULL == 2
            if(crowd_would==1)++crowd_chk_would;
            if(crowd_would>1)  // =2 checks the cull only; a policy skip still skips
#else
            if(crowd_would)
#endif
            {
                if(crowd_skips==kCrowdSkips)crowd_would=0;  // no room to remember it: drawn as before
                else {
                    if(!re4dc_actor_transaction_choose(m,2)){actor_fail();return -1;}
                    crowd_skip[crowd_skips++]=model;
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
                    scene_note(m,plan_kind,kScCrowd);
#endif
                    return 1;
                }
            }
        }
#endif
        APROF_STOP(aprof_crowd);
#if RE4DC_ACTOR_GANADO_DEATH_FADE
#if RE4DC_NMR_DYING && RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
        if(actor_fade_eligible(m,p)) {
            // The census counts a queued fade as a native draw; a refused one (0) keeps the source path.
            const int faded=actor_fade_enqueue(m,p,frame,model);
            if(faded==1 && plan_kind==3){++registry_count[p.appearance-nmr::appearance_first].admitted;registry_note_admit(m,p.appearance);}
            if(faded==0 && plan_kind==3)registry_decline(m,&p,kRwAcquire);
            if(faded>=0)scene_note(m,plan_kind,faded==1?kScNative:plan_kind==3?kScRegistryDeclined:kScDeclined);
            return faded;
        }
#else
        if(actor_fade_eligible(m,p))return actor_fade_enqueue(m,p,frame,model);
#endif
#endif
        APROF_SPAN(aprof_acq,APROF_ACQ);
        bool failed=false;r=actor_acquire(m,p,frame,model,failed);
        APROF_STOP(aprof_acq);
        if(failed){actor_fail();return -1;}
#if RE4DC_NATIVE_MODEL_REGISTRY
        if(!r){
            ATD(m,31,p.appearance,0);INVIS_NOTE(m,0);
            NMR_CENSUS(if(plan_kind==3)registry_decline(m,&p,kRwAcquire);
                scene_note(m,plan_kind,plan_kind==3?kScRegistryDeclined:kScDeclined));
            return 0;
        }
#else
        if(!r){ATD(m,31,p.appearance,0);INVIS_NOTE(m,0);return 0;}
#endif
        if(!re4dc_actor_transaction_choose(m,2)){actor_release(*r);actor_fail();return -1;}
        ATD(m,16,p.appearance,p.run_count);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
        // A registry actor acquired by THIS call passed actor_semantics above; since then only native code ran
        // (actor_acquire's leases, palettes, skin, lighting state read, preflight; the ledger choice): the verdict holds
        // for this pass. A later pass (another OT group) proves it again.
        tx_semantics_held=plan_kind==3;
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
        if(plan_kind==3){++registry_count[p.appearance-nmr::appearance_first].admitted;registry_note_admit(m,p.appearance);}
        scene_note(m,plan_kind,kScNative);
#endif
#if RE4DC_CROWD
        r->crowd_ganado=crowd_ganado(m);r->crowd_would=crowd_would;r->crowd_emit=0;
        r->crowd_why=crowd_would==1?crowd_why:0;r->crowd_depth=crowd_depth;r->crowd_fog=crowd_fog;
#endif
    }
    APROF_SPAN(aprof_pass,APROF_PASS);
    const unsigned pass=m->ot_type==7 && (m->be_flag&0x08000000)?2u:1u;
    if((r->done&pass) || r->released){actor_fail();return -1;}
#if RE4DC_ACTOR_PROOF_LEAN
    // ACTOR_PROOF_LEAN (Leon, the Ganado cast and registry plans alike): the pass that acquired the actor in THIS call
    // keeps the actor_semantics verdict it got before actor_acquire, and the modelviews actor_acquire computed from the
    // same matrices, when the lifetime serial has not moved since that verdict. Audit (one call, verdict -> here):
    // crowd_policy (reads m, the cast pregate balls, the fog far; writes crowd statics), actor_acquire (native frame
    // scratch, texture / workspace / palette-arena / prim-tail leases, the palette build: owner_*_bind / registry_bind
    // reads and their binding slots, re4dc_actor_binding_revision; re4dc_actor_skin_acquire, actor_source_lighting reads
    // GX state, preflight), re4dc_actor_transaction_choose (the ledger's presentation choice; membership unchanged). None
    // runs source code or writes cModel / cParts / cModelInfo / pG / gxCsScale, the plan copy (r->plan=p) or the room
    // rows; a lifetime record can move only by life::next() (CROWD_READOPT inside a bind, a binding refresh), which
    // the serial guard turns into the full proof. A later pass (Leon's second OT group) proves everything again.
    const bool lean_held=lean_serial && !re4dc_material::life::exhausted && re4dc_material::life::serial==lean_serial;
#if RE4DC_ACTOR_PROOF_LEAN == 2
    const bool lean_full=actor_semantics(m,r->plan);
    ++actor_lean_c.semantics;if(lean_held){++actor_lean_c.held;if(!lean_full)++actor_lean_c.semantics_bad;}
    if(pG->Frame_cnt/600!=actor_lean_c.last){actor_lean_c.last=pG->Frame_cnt/600;actor_lean_report("periodic");}
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) ||
       m->pParts!=r->parts_owner || !lean_full){actor_release(*r);actor_fail();return -1;}
#elif RE4DC_NATIVE_MODEL_REGISTRY_TX
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) || m->pParts!=r->parts_owner ||
       (!lean_held && !tx_semantics_held && !actor_semantics(m,r->plan))){actor_release(*r);actor_fail();return -1;}
#else
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) ||
       m->pParts!=r->parts_owner || (!lean_held && !actor_semantics(m,r->plan))){actor_release(*r);actor_fail();return -1;}
#endif
#elif RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
    bool tx_semantics=actor_semantics(m,r->plan);
    ++registry_txc.semantics;if(tx_semantics_held){++registry_txc.held;if(!tx_semantics)++registry_txc.semantics_bad;}
    if(pG->Frame_cnt/600!=registry_txc.last){registry_txc.last=pG->Frame_cnt/600;registry_tx_report("periodic");}
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) ||
       m->pParts!=r->parts_owner || !tx_semantics){actor_release(*r);actor_fail();return -1;}
#elif RE4DC_NATIVE_MODEL_REGISTRY_TX
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) ||
       m->pParts!=r->parts_owner || (!tx_semantics_held && !actor_semantics(m,r->plan))){actor_release(*r);actor_fail();return -1;}
#else
    if(!actor_palette_arena.data(r->palette,r->plan.palette_bytes) ||
       m->pParts!=r->parts_owner || !actor_semantics(m,r->plan)){actor_release(*r);actor_fail();return -1;}
#endif
    float projection[7],viewport[6];GXGetProjectionv(projection);GXGetViewportv(viewport);
    if(std::memcmp(projection,r->base.projection,sizeof(projection)) || std::memcmp(viewport,r->base.viewport,sizeof(viewport))) {
        actor_release(*r);actor_fail();return -1;
    }
    // Detect changed visibility/list before any second-pass submission. Source
    // callbacks never run here. Once a prior pass emitted, failure aborts rather
    // than drawing a late source duplicate over a partial native actor.
    unsigned order=0;
    for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
        if(order==r->count || r->part[order].info!=info || r->part[order].flags!=info->be_flag) {
            actor_release(*r);actor_fail();return -1;
        }
#if RE4DC_ACTOR_PROOF_LEAN == 1
        if(!lean_held) {
            Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
            if(std::memcmp(r->part[order].mv,mv,sizeof(mv))){actor_release(*r);actor_fail();return -1;}
        }
#elif RE4DC_ACTOR_PROOF_LEAN == 2
        {
            Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
            const bool same=!std::memcmp(r->part[order].mv,mv,sizeof(mv));
            if(lean_held){++actor_lean_c.mv;if(!same)++actor_lean_c.mv_bad;}
            if(!same){actor_release(*r);actor_fail();return -1;}
        }
#else
        Mtx pm,mv;RE4DC_RENDER_MTXConcat(m->pParts->mat,info->mat,pm);RE4DC_RENDER_MTXConcat(pG->Cam.v_mat,pm,mv);
        if(std::memcmp(r->part[order].mv,mv,sizeof(mv))){actor_release(*r);actor_fail();return -1;}
#endif
        ++order;
    }
    if(order!=r->count){actor_release(*r);actor_fail();return -1;}
    Re4dcActorDrawRun runs[kRe4dcActorRuns];unsigned n=0;
#if RE4DC_ACTOR_PLAN
    // ACTOR_PLAN: the call that acquired the actor (lean_held: its lifetime token still holds) submits this pass's runs,
    // a subset of the runs actor_acquire preflighted, through re4dc_actor_submit_preflighted_runs.
#define RE4DC_ACTOR_SUBMIT_OWNED (lean_held && RE4DC_PLAN_ON?re4dc_actor_submit_preflighted_runs:re4dc_actor_submit_owned_runs)
#else
#define RE4DC_ACTOR_SUBMIT_OWNED re4dc_actor_submit_owned_runs
#endif
    for(unsigned i=0;i<r->count;++i) {
        const auto& p=r->part[i];
        if(!(p.flags&8))continue;
        if(m->ot_type==7 && ((p.flags&0x40)?2u:1u)!=pass)continue;
        for(unsigned j=0;j<r->run_count;++j)if(r->runs[j].chunk.info==p.info)runs[n++]=r->runs[j];
    }
    APROF_STOP(aprof_pass);
#if RE4DC_CROWD_OUTPUT
    const unsigned crowd_out0=re4dc_model_output_count();
#endif
#if RE4DC_PS2_INTERIOR_OWNER && RE4DC_CROWD
    // PS2_INTERIOR_ACTORS=2: Trans marked this owner-path Ganado as hidden behind the house walls. Its CROWD_LOD notes
    // are left as its runs would leave them and the owned submission is skipped (=2: drawn, the notes checked after).
    bool pco_skip=false;float pco_nearest=0;int pco_check=0;
#ifdef RE4DC_PS2_INTERIOR_OWNER_SELECT
    // PS2_INTERIOR_OWNER_SELECT=0|1 (layout control, diagnostic): one .data word, 1 off, 2 on.
    static volatile unsigned pco_select=1U+RE4DC_PS2_INTERIOR_OWNER_SELECT;
    if(pco_select==2U && r->crowd_ganado && n && re4dc_invis_owner_marked(m)) {
#else
    if(r->crowd_ganado && n && re4dc_invis_owner_marked(m)) {
#endif
#if RE4DC_PS2_INTERIOR_OWNER == 2
        pco_check=re4dc_actor_owned_crowd_replay(&r->base,runs,n,r->plan.materials,r->plan.material_count,0,&pco_nearest);
#else
        pco_skip=re4dc_actor_owned_crowd_replay(&r->base,runs,n,r->plan.materials,r->plan.material_count,1,&pco_nearest)!=0;
        if(pco_skip)++re4dc_pco_skipped;else ++re4dc_pco_declined;
#endif
    }
    (void)pco_nearest;(void)pco_check;
    const int result=pco_skip?1:n?RE4DC_ACTOR_SUBMIT_OWNED(&r->base,runs,n,r->plan.materials,r->plan.material_count,&r->workspace,&r->skin,r->textures):1;
#if RE4DC_PS2_INTERIOR_OWNER == 2
    if(pco_check) {
        float have=0;const int noted=re4dc_actor_crowd_peek(m,&have);
        ++re4dc_pco_checked;
        if(!noted || std::memcmp(&have,&pco_nearest,sizeof(have))) {
            ++re4dc_pco_check_mis;
            if(re4dc_pco_check_mis<=32)re4dc_log("INVISPCO BAD t=%u m=%p noted=%d have=%g predicted=%g\n",unsigned(pG->Frame_cnt),m,noted,have,pco_nearest);
        }
    }
#endif
#else
    const int result=n?RE4DC_ACTOR_SUBMIT_OWNED(&r->base,runs,n,r->plan.materials,r->plan.material_count,&r->workspace,&r->skin,r->textures):1;
#endif
#undef RE4DC_ACTOR_SUBMIT_OWNED
#if defined(RE4DC_PVR_RTT) && RE4DC_PVR_RTT
    if(result==1 && n) {   // PVR_RTT: the ice pass over the runs of infos that show a render target
        Re4dcActorDrawRun ice[kRe4dcActorRuns];unsigned k=0;int slot=-1;
        for(unsigned j=0;j<n;++j) {
            const int s=re4dc_nmr_ice_slot(static_cast<const cModelInfo*>(static_cast<const void*>(runs[j].chunk.info)));
            if(s>=0){slot=s;ice[k++]=runs[j];}
        }
        if(k) {
            re4dc_rtt_want(slot);
            if(re4dc_rtt_ready(slot)) {
                Re4dcActorOwnedMaterial mats[kRe4dcActorMaterials];
                for(unsigned i=0;i<r->plan.material_count;++i){mats[i]=r->plan.materials[i];mats[i].blend=0;mats[i].depth_mode=1;}
                re4dc_rtt_override(slot);
                const int ice_result=re4dc_actor_submit_owned_runs(&r->base,ice,k,mats,r->plan.material_count,&r->workspace,&r->skin,r->textures);
                re4dc_rtt_override(-1);
                static unsigned ice_passes,ice_failed;
                ++ice_passes;if(ice_result!=1)++ice_failed;
                if((ice_passes&127)==1)re4dc_log("PVR_RTT ice pass: model=%p slot=%d runs=%u passes=%u failed=%u\n",m,slot,k,ice_passes,ice_failed);
            }
        }
    }
#endif
#if RE4DC_CROWD_OUTPUT
    if(r->crowd_ganado) {
        const unsigned emitted=re4dc_model_output_count()-crowd_out0;
        r->crowd_emit+=emitted;
#if RE4DC_CROWD_CULL == 2
        if(r->crowd_would==1 && emitted) {
            ++crowd_chk_violations;crowd_chk_tris+=emitted;
            if(++crowd_chk_log<=40)re4dc_log("CROWDCULL VIOLATION t=%u m=%p pass=%u emitted=%u why=%u depth=%d fog=%d\n",unsigned(pG->Frame_cnt),m,pass,
                emitted,r->crowd_why,int(r->crowd_depth),int(r->crowd_fog));
        }
#endif
#if RE4DC_CROWD_CENSUS
        crowd_cc.tris+=emitted;
        if((r->done|pass)==r->passes)++(r->crowd_emit?crowd_cc.drawn:crowd_cc.empty);
#endif
    }
#endif
    if(result!=1) {
        actor_release(*r);
        // Even a pre-header decline is a broken reservation after admission;
        // never silently switch presentation at an original second pass.
        actor_fail();return -1;
    }
    ATD(m,n?(pass==1?18u:19u):17u,n,r->plan.appearance);
    r->submitted|=n!=0;r->done|=pass;
    if(r->done==r->passes && !actor_release(*r))return -1;
    return 1;
}
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
// mcheck.mk MCHECK_LEONGC (test builds): every hand-off of the player's model to the source (GameCube) path is a
// bug (user, 2026-10-13: never the GC Leon). trans.cpp calls re4dc_leon_gc_note when the transaction did not own
// pPL; the line names the transaction's last decline (why: 1 identity, 2 sticky source choice, 3 second-pass group,
// 4 no plan, 5 layout, 6 semantics / certificate; bind: the role-binding event 21..30 of the last plan attempt;
// cert: the material certificate error / role) and the hand infos. Bounded: a line on each change of the cause,
// else one per 600 frames, each with the running total. tools/d367/mcheck/leongc_check.py turns them into PASS / FAIL.
#include "player.h"
#include "pl_body.h"
namespace { unsigned leon_gc_why,leon_gc_a,leon_gc_b,leon_gc_bind,leon_gc_total,leon_gc_last_key,leon_gc_last_frame,leon_gc_acq,leon_gc_acq_a,leon_gc_acq_b; }
unsigned re4dc_leon_gc_cert_error,re4dc_leon_gc_cert_role;
extern "C" void re4dc_leon_gc_atd(cModel* m,unsigned e,unsigned a,unsigned b) {
    static bool armed;
    if(!armed){armed=true;re4dc_log("LEONGC armed (MCHECK_LEONGC)\n");}
    if(!m || m!=(cModel*)pPL)return;
    if(e==0){leon_gc_why=leon_gc_bind=leon_gc_acq=0;re4dc_leon_gc_cert_error=re4dc_leon_gc_cert_role=0;return;}
    if(e<=6){leon_gc_why=e;leon_gc_a=a;leon_gc_b=b;}
    else if(e>=7 && e<=15){leon_gc_acq=e;leon_gc_acq_a=a;leon_gc_acq_b=b;}  // the acquire's resource decline
    else if(e>=20 && e<=31)leon_gc_bind=e;
}
extern "C" void re4dc_leon_gc_note(cModel* m) {
    if(!m || m!=(cModel*)pPL)return;
    ++leon_gc_total;
    const unsigned f=pG->Frame_cnt;
    const unsigned key=leon_gc_why|leon_gc_bind<<8|re4dc_leon_gc_cert_error<<16|re4dc_leon_gc_cert_role<<24;
    // Both source passes of a frame may decline for different causes: keep the last two causes.
    static unsigned prev_key=~0u;
    // Throttle on the note count: pG->Frame_cnt holds still in some scripted states (the r10b boat ride).
    static unsigned last_total;
    if((key==leon_gc_last_key || key==prev_key) && leon_gc_total-last_total<600u)return;
    last_total=leon_gc_total;
    if(key!=leon_gc_last_key){prev_key=leon_gc_last_key;leon_gc_last_key=key;}
    leon_gc_last_frame=f;
    const auto* body=pPL->Body;
    re4dc_log("LEONGC f=%u room=%04x why=%u a=%u b=%u bind=%u cert=%u/%u total=%u right=%p/%p left=%p/%p infos=%u acq=%u/%u/%u\n",f,
              unsigned(pG->room_id),leon_gc_why,leon_gc_a,leon_gc_b,leon_gc_bind,re4dc_leon_gc_cert_error,re4dc_leon_gc_cert_role,
              leon_gc_total,body?(void*)body->pRight:nullptr,body?body->pRightData:nullptr,body?(void*)body->pLeft:nullptr,
              body?body->pLeftData:nullptr,[&]{unsigned n=0;for(auto* q=m->pModelInfo;q && n<64;q=q->pList)++n;return n;}(),
              leon_gc_acq,leon_gc_acq_a,leon_gc_acq_b);
}
#endif
