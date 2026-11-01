// Appended to coarse_actor.cpp. No copied private mesh arrays.
#if RE4DC_ACTOR_TRANSACTION
#include "coarse_actor_transaction.h"
#include "actor_material_owner.h"
#include "actor_lifetime.h"
#include "actor_material_policy.h"
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
extern "C" int re4dc_atlas_apply(Re4dcActorPlan*);
extern "C" int re4dc_atlas_has_tile(const Re4dcActorPlan*);
extern "C" unsigned re4dc_atlas_capability(const Re4dcActorPlan*);
extern "C" void re4dc_atlas_retire_pl08();
#endif
#if RE4DC_PS2_LEON
// ps2leon.mk PS2_LEON: the arm's hair as one owned run per hair material it uses (A: 1, B: 2; tools/d367/ps2leon
// pack_arm.py, restripified as CHARBAKE_HAIR's runs), the leon_hair_runs.h API; its palette_count is chunk 7's.
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
// LEON_LOD=1: the hair run row is filled from the loaded rung (lod_pack.py derive: no hair arrays in the image).
#include "ps2leon_hair_runs_lod.h"
#define RE4DC_LEON_HAIR_PALETTES leon_lod::hair_palettes
#else
#include "ps2leon_hair_runs.h"
#define RE4DC_LEON_HAIR_PALETTES leon_hair_runs::palette_count
#endif
// The plans declare only the hair materials the runs draw (the transaction refuses a declared material no run uses):
// A draws all its hair with hair colour 0 (material 1, as the PS2 does), B with both colours (materials 1 and 2).
static_assert(leon_hair_runs::material_mask==2u || leon_hair_runs::material_mask==6u,
              "PS2_LEON hair runs must use material 1, or materials 1 and 2");
#define RE4DC_LEON_HAIR_MATERIALS (leon_hair_runs::material_mask==6u?2u:1u)
#elif RE4DC_CHARBAKE_HAIR
#include "leon_hair_runs_g2.h" // charbake.mk CHARBAKE_HAIR: the same hair, one run per material (cb_hair.py)
#else
#include "leon_hair_runs.h"
#endif
#ifndef RE4DC_LEON_HAIR_PALETTES
#define RE4DC_LEON_HAIR_PALETTES 229
#endif
#ifndef RE4DC_LEON_HAIR_MATERIALS
#define RE4DC_LEON_HAIR_MATERIALS 2
#endif
#include "warp_late.h"
#if RE4DC_LEON_HAND_TABLE
#if !RE4DC_LEON_HAND_POSES || !RE4DC_ACTOR_PL08 || !RE4DC_PS2_LEON
#error LEON_HAND_DIR needs LEON_HAND_POSES=1, ACTOR_PL08=1 and PS2_LEON
#endif
namespace { // ps2leon_hands.h: included by coarse_actor.cpp
unsigned leon_hand_asset(unsigned pose);  // coarse_actor_geometry_once.inc ID range, defined after it
// The PS2 pose of a hand info (role 5 right / 6 left): -1 = arm A's standard hand (the handgun grip, the left grip,
// or a pose with no converted PS2 hand). Key: the GC section's counts and the first 64 bytes of its positions.
int leon_hand_pose(unsigned role,const cModelInfo* info) {
    if(!info || !info->pData || !info->pData->vtxOrig)return -1;
    const ModelData* d=info->pData;
    const unsigned pal=d->weight_ext_num>255?d->weight_ext_num:d->weight_palette_num;
    const unsigned h=fingerprint(d->vtxOrig);
    for(unsigned k=0;k<leon_hands::key_count;++k) {
        const auto& e=leon_hands::keys[k];
        if(e.role==role && e.positions==d->nVtx && e.normals==d->nNrm && e.palette==pal && e.vertex_hash==h)return int(e.pose);
    }
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    // Test builds: a hand pose with no PS2 hand (it draws the PS2 standard hand). One line per distinct key.
    static unsigned seen[16],nseen;
    bool known=h==leon_hands::standard_vertex_hash[role-5];  // the standard hand itselffor(unsigned k=0;k<nseen;++k)known|=seen[k]==(h^role);
    if(!known && nseen<16){seen[nseen++]=h^role;
        re4dc_log("LEONHAND standard role=%u key=%u/%u/%u/%u (no PS2 pose hand)\n",role,unsigned(d->nVtx),unsigned(d->nNrm),pal,h);}
#endif
    return -1;
}
// The chunk, owner input and immutable ID that draw role 5 / 6 for this hand info.
struct LeonHandPick { const leon4k::Chunk* chunk;re4dc_source::ChunkInput input;unsigned asset;int pose; };
LeonHandPick leon_hand_pick(unsigned role,const cModelInfo* info,const leon4k::Chunk& standard,
                            const re4dc_source::ChunkInput& standard_input) {
    const int pose=leon_hand_pose(role,info);
    if(pose<0)return {&standard,standard_input,role+1u,-1};
    const auto& c=leon_hands::chunks[pose];const auto& s=leon_hands::spans[pose];
    return {&c,re4dc_source::ChunkInput{s.positions,s.normals,s.uv,s.stream,s.weights,
            c.position_count,c.normal_count,c.palette_count,c.triangles,119u},leon_hand_asset(unsigned(pose)),pose};
}
inline unsigned leon_r32(unsigned x){return (x+31u)&~31u;}
// The pl00 plan's role chunks (roles 5 / 6 follow the hand poses) and their skin key: costume 0 plus the poses,
// so a pose change rebuilds the FTRV palette program (skin_build) before the palettes read it.
const leon4k::Chunk* leon_cur[8]={&leon4k::chunks[0],&leon4k::chunks[1],&leon4k::chunks[2],&leon4k::chunks[3],
    &leon4k::chunks[4],&leon4k::chunks[5],&leon4k::chunks[6],&leon4k::chunks[7]};
unsigned leon_cur_key;
inline unsigned leon_hand_key(unsigned costume,int right,int left) {
    return costume|unsigned(right+1)<<8|unsigned(left+1)<<16;
}
}
#define RE4DC_LEON_STD_INPUT(r) RE4DC_OWNER_INPUT(leon4k,i##r,leon4k::chunks[r],119)
#define RE4DC_LEON_STD_PAL(r) leon4k::chunks[r].palette_count
#elif RE4DC_LEON_HAND_PACK
#if !RE4DC_LEON_HAND_POSES || !RE4DC_ACTOR_PL08 || !RE4DC_PS2_LEON
#error LEON_HAND_PACK needs LEON_HAND_POSES=1, ACTOR_PL08=1 and PS2_LEON
#endif
#include "coarse_actor_leon_hands.inc" // LEON_HAND_PACK: the hands from the outfit's package through a small cache
#define RE4DC_LEON_STD_INPUT(r) re4dc_source::ChunkInput{}
#define RE4DC_LEON_STD_PAL(r) leon_hand_pack::std_pal(r)
#endif
#define RE4DC_LEON_HAND_ANY (RE4DC_LEON_HAND_TABLE || RE4DC_LEON_HAND_PACK)
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
#if !RE4DC_LEON_HAND_PACK || !RE4DC_PS2_LEON
#error LEON_LOD needs PS2_LEON=1 and LEON_HAND_PACK=1
#endif
#include "coarse_actor_leon_lod.inc" // LEON_LOD: Leon's mesh rung from dc/native/pl00/leon_lod.re4lp
// The owner inputs, plan bytes and hair run arrays of the loaded rung (roles 5 / 6 stay the hand pack's).
#define RE4DC_LEON_ROLE_INPUT(r,prefix) leon_lod::input[r]
#define RE4DC_LEON_PLAN_PAL leon_lod::plan_palette_bytes
#define RE4DC_LEON_PLAN_WS leon_lod::plan_workspace_bytes
#define RE4DC_PL08_PLAN_PAL leon_lod::pl08_plan_palette_bytes
#define RE4DC_PL08_PLAN_WS leon_lod::pl08_plan_workspace_bytes
#define RE4DC_LEON_HAIR_UV_DATA leon_lod::hair_uv
#define RE4DC_LEON_HAIR_UV_SIZE leon_lod::hair_uv_bytes
#define RE4DC_LEON_LOD_READY() leon_lod::ready()
#else
#define RE4DC_LEON_ROLE_INPUT(r,prefix) RE4DC_OWNER_INPUT(leon4k,prefix,leon4k::chunks[r],119)
#define RE4DC_LEON_PLAN_PAL leon4k::plan_palette_bytes
#define RE4DC_LEON_PLAN_WS leon4k::plan_workspace_bytes
#define RE4DC_PL08_PLAN_PAL leon4k::pl08_plan_palette_bytes
#define RE4DC_PL08_PLAN_WS leon4k::pl08_plan_workspace_bytes
#define RE4DC_LEON_HAIR_UV_DATA leon_hair_runs::uv
#define RE4DC_LEON_HAIR_UV_SIZE sizeof(leon_hair_runs::uv)
#define RE4DC_LEON_LOD_READY() true
#endif
#if !RE4DC_COARSE_SOURCE_ACTORS || !RE4DC_COARSE_ONE_SUBMIT || RE4DC_COARSE_SKIN_FTRV != 1 || !RE4DC_NATIVE_ACTOR_FAST
#error ACTOR_TRANSACTION requires the source ledger, ONE_SUBMIT and SKIN_FTRV=1 native path
#endif
#if RE4DC_ACTOR_SWAP || RE4DC_FRONT_NATIVE >= 2
#error ACTOR_TRANSACTION is incompatible with duplicate-draw/replay adapters
#endif
#if RE4DC_ACTOR_PLAN
#include "actor_plan.h"
extern "C" unsigned re4dc_actor_tx_serial;              // coarse_actor_transaction.inc (ACTOR_BIND_REUSE)
extern "C" unsigned re4dc_actor_binding_peek(cModel*);  // actor_lifetime.inc (ACTOR_BIND_REUSE)
namespace re4dc_material { namespace life { extern unsigned serial; extern bool exhausted; } }
#endif
namespace {
unsigned owner_binding_revision;
#if RE4DC_ACTOR_PLAN
// ACTOR_PLAN: a single-use token of the bind re4dc_actor_plan_leon made in this transaction call (first proved by lane
// codex-actor-t15, 168042a3): owner_leon_palettes, later in the same call, replays it instead of binding again. It
// names the model, the call, the source frame, the lifetime serial right after the bind and the binding revision;
// between the two only native code runs (layout, semantics, crowd policy, the leases: the ACTOR_PROOF_LEAN audit: none
// writes cModel / cParts), so the bone matrices the bind's finite scan passed are the same words: the replay does not
// scan them again (hw model ap17b2: the scan is 0.136 ms of memory reads per pass, the same with the word-OR form).
struct LeonPlanBind { cModel* model;unsigned tx,frame,life,revision; } leon_plan_bind{};
// The bind's finite test of Leon's 119 bones as one exponent-field OR (coarse_finite is the exponent test: bit 31 of
// (exponent field + 0x00800000) is set iff the field is all ones): the same verdict, branch-free per word.
bool leon_bones_finite(cParts* const* bones) {
    typedef unsigned __attribute__((may_alias)) Word;
    unsigned bad=0;
    for(unsigned i=0;i<119;++i) {
        const Word* a=reinterpret_cast<const Word*>(&bones[i]->lt_inv_mat[0][0]);
        const Word* c=reinterpret_cast<const Word*>(&bones[i]->mat[0][0]);
        for(unsigned j=0;j<12;++j)bad|=((a[j]&0x7f800000u)+0x00800000u)|((c[j]&0x7f800000u)+0x00800000u);
    }
    return !(bad&0x80000000u);
}
#endif
cModel* owner_root_parts;
#if RE4DC_CHARBAKE_TOGGLE
// charbake.mk CHARBAKE_TOGGLE (test builds): the hair colour images take the selected variant's identity and key
// (coarse_actor.cpp re4dc_charbake_set); the materials draw the pair keys the runtime derives from those
// (native_ui.cpp model_mask_key; charbake_variants.h). Variant 0 holds the keys below the #else.
unsigned hair_tokens[re4dc_charbake::kCount][2],hair_mask_token;
Re4dcUiImage hair_colours[2]={{&hair_tokens[RE4DC_CHARBAKE_VARIANT%re4dc_charbake::kCount][0],nullptr,64,128,14,0xffffffffu,0},
                              {&hair_tokens[RE4DC_CHARBAKE_VARIANT%re4dc_charbake::kCount][1],nullptr,64,128,14,0xffffffffu,0}};
const Re4dcUiImage hair_mask{&hair_mask_token,nullptr,64,128,0,0xffffffffu,0};
unsigned hair_colour_crc[2]={kCharbakeBoot.hair_colour_crc[0],kCharbakeBoot.hair_colour_crc[1]},
         hair_colour_fnv[2]={kCharbakeBoot.hair_colour_fnv[0],kCharbakeBoot.hair_colour_fnv[1]};
unsigned hair_pair_crc[2]={kCharbakeBoot.hair_pair_crc[0],kCharbakeBoot.hair_pair_crc[1]},
         hair_pair_fnv[2]={kCharbakeBoot.hair_pair_fnv[0],kCharbakeBoot.hair_pair_fnv[1]};
#else
unsigned hair_tokens[3];
const Re4dcUiImage hair_colours[2]={{&hair_tokens[0],nullptr,64,128,14,0xffffffffu,0},{&hair_tokens[1],nullptr,64,128,14,0xffffffffu,0}};
const Re4dcUiImage hair_mask{&hair_tokens[2],nullptr,64,128,0,0xffffffffu,0};
constexpr unsigned hair_colour_crc[2]={0xac381b1a,0x7a9de1fd},hair_colour_fnv[2]={0x3ade84b1,0x0e415f15};
constexpr unsigned hair_pair_crc[2]={0xfc24a99c,0x9cf7f055},hair_pair_fnv[2]={0x03d13534,0xd40aae38};
#endif
bool owner_leon_bind(cModel* m) {
    if(!m || m->id || m->nParts!=119 || !m->pList || !m->pParts || (m->be_flag&0x4000))return false;
    // Current dual archive/model adoption records supply exact role identity,
    // including hidden infos. No signature scan or pointer-only positive cache.
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
#if RE4DC_ACTOR_PLAN
    if(RE4DC_PLAN_ON)return leon_bones_finite(parts);
#endif
    for(unsigned i=0;i<119;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&parts[i]->lt_inv_mat[0][0])[j]) ||
           !coarse_finite((&parts[i]->mat[0][0])[j]))return false;
    return true;
}
#if RE4DC_ACTOR_PLAN
// The plan's bind of this call (see LeonPlanBind), or the full bind.
bool owner_leon_bind_planned(cModel* m) {
    using namespace re4dc_material;
    const LeonPlanBind t=leon_plan_bind;leon_plan_bind.model=nullptr;  // one use
    const bool reuse=RE4DC_PLAN_ON && m && t.model==m && t.tx==re4dc_actor_tx_serial && t.frame==unsigned(pG->Frame_cnt) &&
        !life::exhausted && t.life==life::serial && t.revision==owner_binding_revision &&
        owner==m && owner_serial==m->serial && owner_parts==m->pList && owner_root_parts==m->pParts &&
        !m->id && m->nParts==119 && m->pList && m->pParts && !(m->be_flag&0x4000) &&
        re4dc_actor::exact_infos(m->pModelInfo,infos,8) && re4dc_actor_binding_peek(m)==t.revision;
#if RE4DC_ACTOR_PLAN == 2
    const bool full=owner_leon_bind(m);
    re4dc_actor_plan_note(APLAN_BIND,reuse,reuse && !full);
    return full;
#else
    re4dc_actor_plan_note(APLAN_BIND,reuse,0);
    return reuse || owner_leon_bind(m);
#endif
}
#endif
#if RE4DC_ACTOR_TRANSACTION_DIAG
// WP2 census (diagnostic): the first owner_leon_bind clause that fails, in its order; detail = part index etc.
unsigned owner_leon_bind_why(cModel* m,unsigned* detail) {
    *detail=0;
    if(!m)return 1;
    if(m->id)return 2;
    if(m->nParts!=119){*detail=m->nParts;return 3;}
    if(!m->pList)return 4;
    if(!m->pParts)return 5;
    if(m->be_flag&0x4000)return 6;
    cModelInfo* roles[8]{};
    if(!re4dc_actor_role_bindings(m,0x100,roles,8))return 7;
    if(!re4dc_actor::exact_infos(m->pModelInfo,roles,8)){
        for(cModelInfo* f=m->pModelInfo;f && *detail<999;f=f->pList)++*detail;
        return 8;
    }
    if(!re4dc_actor_binding_revision(m))return 9;
    cParts* part=m->pList;
    for(unsigned i=0;i<119;++i) {
        if(!part){*detail=i;return 10;}
        for(unsigned j=0;j<12;++j)if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) ||
            (!RE4DC_LEON_RIG_SIM(i) && __builtin_fabsf((&part->lt_inv_mat[0][0])[j]-leon4k::bind[i][j])>.01f)){*detail=i*16+j;return 11;}
        part=part->pList;
    }
    if(part)return 12;
    part=m->pList;
    for(unsigned i=0;i<119;++i,part=part->pList)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&part->lt_inv_mat[0][0])[j]) || !coarse_finite((&part->mat[0][0])[j])){*detail=i;return 13;}
    return 0;
}
#endif
int owner_leon_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
#if RE4DC_ACTOR_PLAN
#define RE4DC_LEON_PALETTE_BIND(m) owner_leon_bind_planned(m)
#else
#define RE4DC_LEON_PALETTE_BIND(m) owner_leon_bind(m)
#endif
#if RE4DC_LEON_HAND_ANY
    if(!RE4DC_LEON_PALETTE_BIND(m) || !skin_build(leon_cur_key,leon_cur,8))return 0;
    for(unsigned i=0;i<8;++i)if(p.input[i].palette_count!=leon_cur[i]->palette_count)return 0;
#else
    if(!RE4DC_LEON_PALETTE_BIND(m) || !skin_init())return 0;
#endif
#undef RE4DC_LEON_PALETTE_BIND
    for(unsigned i=0;i<8;++i)if(p.info[i]!=infos[i] || !output[i])return 0;
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    for(unsigned u=0;u<skin_used;++u) {
        const unsigned b=skin_bone[u];
        skin_jobs[u]={&parts[b]->mat[0][0],RE4DC_LEON_BIND_ROW(b,parts[b]),bone_T[b]};
    }
    re4dc_coarse_skin_bones(invx,skin_jobs,skin_used);
    for(unsigned i=0;i<8;++i) {
#if RE4DC_LEON_HAND_ANY
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],p.input[i].palette_count);
#if RE4DC_ACTOR_PLAN
        if(RE4DC_PLAN_ON){if(!re4dc_plan_all_finite(output[i],p.input[i].palette_count*12))return 0;continue;}
#endif
        for(unsigned j=0;j<p.input[i].palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
#else
        re4dc_coarse_skin_groups(skin_stream+skin_first[i],skin_groups[i],&bone_T[0][0],output[i],leon4k::chunks[i].palette_count);
        for(unsigned j=0;j<leon4k::chunks[i].palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
#endif
    }
    return 1;
}
}
extern "C" int re4dc_actor_plan_leon(cModel* m,Re4dcActorPlan* out) {
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    if(RE4DC_WARP_LATE(RE4DC_LATE_LEON_SOURCE))return 0; // test-only old-path arm (warp_late.h 0x10)
#endif
    if(!m || !out || m->id || RE4DC_LEON_OT_BAD(m) || !RE4DC_LEON_LOD_READY() || !owner_leon_bind(m))return 0;
#if RE4DC_ACTOR_PLAN
    leon_plan_bind={m,re4dc_actor_tx_serial,unsigned(pG->Frame_cnt),re4dc_material::life::serial,owner_binding_revision};
#endif
    Re4dcActorPlan p{};p.count=8;p.appearance=0x100;p.image=image;p.crc=crc;p.fnv=fnv;p.palettes=owner_leon_palettes;
#define RE4DC_LEON_OWNER(role,prefix) re4dc_actor::plan_chunk(p,role,infos[role],leon4k::chunks[role],RE4DC_LEON_ROLE_INPUT(role,prefix))
    RE4DC_LEON_OWNER(0,i0);RE4DC_LEON_OWNER(1,i1);RE4DC_LEON_OWNER(2,i2);RE4DC_LEON_OWNER(3,i3);
#if RE4DC_LEON_HAND_ANY
    // LEON_HAND_DIR: roles 5 / 6 draw the PS2 hand of the current pose (leon_hand_pick); the plan bytes follow.
    const LeonHandPick hand5=leon_hand_pick(5,infos[5],leon4k::chunks[5],RE4DC_LEON_STD_INPUT(5));
    const LeonHandPick hand6=leon_hand_pick(6,infos[6],leon4k::chunks[6],RE4DC_LEON_STD_INPUT(6));
#if RE4DC_LEON_HAND_PACK
    if(!hand5.chunk || !hand6.chunk)return 0;
#endif
    RE4DC_LEON_OWNER(4,i4);re4dc_actor::plan_chunk(p,5,infos[5],*hand5.chunk,hand5.input);
    re4dc_actor::plan_chunk(p,6,infos[6],*hand6.chunk,hand6.input);RE4DC_LEON_OWNER(7,i7);
    leon_cur[5]=hand5.chunk;leon_cur[6]=hand6.chunk;leon_cur_key=leon_hand_key(0,hand5.pose,hand6.pose);
    const unsigned hand_palette=leon_r32(hand5.chunk->palette_count*48u)+leon_r32(hand6.chunk->palette_count*48u)
        -leon_r32(RE4DC_LEON_STD_PAL(5)*48u)-leon_r32(RE4DC_LEON_STD_PAL(6)*48u);
    if(p.palette_bytes!=RE4DC_LEON_PLAN_PAL+hand_palette || p.workspace_bytes!=RE4DC_LEON_PLAN_WS)return 0;
#else
    RE4DC_LEON_OWNER(4,i4);RE4DC_LEON_OWNER(5,i5);RE4DC_LEON_OWNER(6,i6);RE4DC_LEON_OWNER(7,i7);
#endif
#undef RE4DC_LEON_OWNER
#if RE4DC_LEON_HAND_ANY
#elif RE4DC_PS2_LEON
    // The arm's palette / workspace bytes (ps2leon_runtime.h, from its chunks' palette counts).
    if(p.palette_bytes!=leon4k::plan_palette_bytes || p.workspace_bytes!=leon4k::plan_workspace_bytes)return 0;
#else
    if(p.palette_bytes!=32000 || p.workspace_bytes!=26112)return 0;
#endif
    p.material_count=1+RE4DC_LEON_HAIR_MATERIALS;
    p.materials[0].image=image;p.materials[0].crc=crc;p.materials[0].fnv=fnv;
    for(unsigned i=0;i<RE4DC_LEON_HAIR_MATERIALS;++i) {
        auto& mat=p.materials[i+1];mat.image=hair_colours[i];mat.mask=hair_mask;
        mat.crc=hair_pair_crc[i];mat.fnv=hair_pair_fnv[i];
        // Source attr04: alpha>0, SRC_ALPHA/INV_SRC_ALPHA, LEQUAL/write,
        // same-UV I4 mask, repeat/bilinear. Routing is not shader acceptance.
        mat.material_flags=4;mat.blend=0;mat.depth_mode=RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u;
        mat.mask_ref=0;mat.mask_same_uv=1;mat.wrap_s=mat.wrap_t=1;
        // The default-off native-look policy disables hair depth writes. This
        // prevents transparent texels writing depth and intentionally differs
        // from GC depthwrite+alpha-test. Exact-source policy stays unadmitted.
    }
    for(unsigned i=0;i<8;++i)p.immutable_asset_id[i]=i+1;
#if RE4DC_LEON_HAND_ANY
    p.immutable_asset_id[5]=hand5.asset;p.immutable_asset_id[6]=hand6.asset;
#endif
    for(unsigned i=0;i<7;++i) {
        const auto& c=p.input[i];auto& r=p.runs[p.run_count++];
#if RE4DC_LEON_HAND_ANY
        r.role=i;r.immutable_asset_id=p.immutable_asset_id[i];r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
#else
        r.role=i;r.immutable_asset_id=i+1;r.triangles=c.triangles;r.uv=c.uv;r.stream=c.stream;
#endif
    }
    for(const auto& run:leon_hair_runs::runs) {
        auto& r=p.runs[p.run_count++];r.role=7;r.material=run.material;r.immutable_asset_id=run.asset_id;r.triangles=run.triangles;
        r.uv={RE4DC_LEON_HAIR_UV_DATA,RE4DC_LEON_HAIR_UV_SIZE};r.stream={run.stream,run.bytes};
    }
    if((re4dc_actor_material_runs_capability(&p)&3u)!=3u)return 0;
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
    re4dc_atlas_apply(&p); // atomic decline preserves the ordinary qualified plan
#endif
    *out=p;return 1;
}
extern "C" int re4dc_actor_hair_texture_key(const Re4dcUiImage* i,unsigned* c,unsigned* f) {
    if(!i || !c || !f || i->palette || i->palette_bytes || i->palette_format!=0xffffffffu || i->width!=64 || i->height!=128)return 0;
    for(unsigned k=0;k<2;++k)if(i->pixels==hair_colours[k].pixels && i->format==14){*c=hair_colour_crc[k];*f=hair_colour_fnv[k];return 1;}
    if(i->pixels==hair_mask.pixels && i->format==0){*c=0x94e9dc56;*f=0x070dc44a;return 1;}
    return 0;
}
extern "C" unsigned re4dc_actor_material_runs_capability(const Re4dcActorPlan* p) {
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
    if(re4dc_atlas_has_tile(p))return re4dc_atlas_capability(p);
#endif
    // The hair runs of the included header: 14 (leon_hair_runs.h), 2 with CHARBAKE_HAIR (leon_hair_runs_g2.h), the
    // arm's with PS2_LEON (ps2leon_hair_runs.h: 1 for A, 2 for B).
    constexpr unsigned kHair=leon_hair_runs::run_count;
#if RE4DC_LEON_HEADLESS
    // LEON_HEADLESS (0x109, Leon after setHead(0)): seven roles, one whole-chunk run each in role order, no hair runs
    // (the hair info is gone), the one atlas material.
    if(p && p->appearance==0x109) {
        if(p->count!=7 || p->run_count!=7 || p->material_count!=1)return 0;
        for(unsigned i=0;i<7;++i) {
            const auto& r=p->runs[i];
            if(r.role!=i || r.material || !p->info[i] || r.triangles!=p->input[i].triangles ||
               r.stream.data!=p->input[i].stream.data || r.uv.data!=p->input[i].uv.data)return 0;
        }
        return 3u|(RE4DC_ACTOR_LEON_NATIVE_LOOK?4u:0u);
    }
    // LEON_HEADLESS v2 (0x10A, the flying head): one role, a face run on the atlas (material 0, the chunk's UVs) then a
    // hair run on hair material 1 (its own UVs), together the role's triangles; the atlas and hair pair 1 materials.
    if(p && p->appearance==0x10A) {
        if(p->count!=1 || p->run_count!=2 || p->material_count!=2 || !p->info[0])return 0;
        const auto& f=p->runs[0];const auto& h=p->runs[1];
        if(f.role || f.material || h.role || h.material!=1 || f.triangles+h.triangles!=p->input[0].triangles ||
           f.uv.data!=p->input[0].uv.data || f.uv.size!=p->input[0].uv.size)return 0;
        const auto& m=p->materials[1];
        if(m.image.pixels!=hair_colours[0].pixels || m.mask.pixels!=hair_mask.pixels || m.crc!=hair_pair_crc[0] || m.fnv!=hair_pair_fnv[0] ||
           m.material_flags!=4 || m.blend || m.depth_mode!=(RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u) || m.mask_ref || m.mask_same_uv!=1 ||
           m.wrap_s!=1 || m.wrap_t!=1)return 0;
        return 3u|(RE4DC_ACTOR_LEON_NATIVE_LOOK?4u:0u);
    }
#endif
#if RE4DC_ACTOR_PL08
    // pl08 (0x108): nine roles; the same hair (role 7, pl00's runs 7..20) and one role-8 run last, its whole chunk.
    const bool pl08=p && p->appearance==0x108;
    if(!p || (pl08?(p->count!=9 || p->run_count!=8+kHair || p->runs[7+kHair].role!=8 || p->runs[7+kHair].material ||
                    p->runs[7+kHair].triangles!=p->input[8].triangles || p->runs[7+kHair].stream.data!=p->input[8].stream.data):
                   (p->appearance!=0x100 || p->count!=8 || p->run_count!=7+kHair)) || p->material_count!=1+RE4DC_LEON_HAIR_MATERIALS ||
       p->input[7].palette_count!=RE4DC_LEON_HAIR_PALETTES || p->immutable_asset_id[7]!=8 || !p->info[7] || !(p->info[7]->be_flag&0x40))return 0;
#else
    if(!p || p->appearance!=0x100 || p->count!=8 || p->material_count!=1+RE4DC_LEON_HAIR_MATERIALS || p->run_count!=7+kHair ||
       p->input[7].palette_count!=RE4DC_LEON_HAIR_PALETTES || p->immutable_asset_id[7]!=8 || !p->info[7] || !(p->info[7]->be_flag&0x40))return 0;
#endif
    for(unsigned k=0;k<kHair;++k) {
        const auto& want=leon_hair_runs::runs[k];const auto& r=p->runs[7+k];
        if(r.role!=7 || r.material!=want.material || r.immutable_asset_id!=29+k || r.triangles!=want.triangles ||
           r.uv.data!=RE4DC_LEON_HAIR_UV_DATA || r.uv.size!=RE4DC_LEON_HAIR_UV_SIZE || r.stream.data!=want.stream || r.stream.size!=want.bytes)return 0;
    }
    for(unsigned k=0;k<RE4DC_LEON_HAIR_MATERIALS;++k) {
        const auto& m=p->materials[k+1];
        if(m.image.pixels!=hair_colours[k].pixels || m.mask.pixels!=hair_mask.pixels || m.crc!=hair_pair_crc[k] || m.fnv!=hair_pair_fnv[k] ||
           m.image.width!=64 || m.image.height!=128 || m.image.format!=14 || m.mask.width!=64 || m.mask.height!=128 || m.mask.format!=0 ||
           m.material_flags!=4 || m.blend || m.depth_mode!=(RE4DC_ACTOR_LEON_NATIVE_LOOK?1u:0u) || m.mask_ref || m.mask_same_uv!=1 || m.wrap_s!=1 || m.wrap_t!=1)return 0;
    }
    return 3u|(RE4DC_ACTOR_LEON_NATIVE_LOOK?4u:0u); // routing/order/native-look; live material certificate still gates admission
}
#if RE4DC_NATIVE_MODEL_REGISTRY
#include "coarse_actor_owner_registry.inc"
#endif
#include "coarse_actor_geometry_once.inc"
#if RE4DC_LEON_HAND_TABLE
namespace { unsigned leon_hand_asset(unsigned pose) {return kLeonHandAsset0+pose;} }
#elif RE4DC_LEON_HAND_PACK
// LEON_HAND_PACK: a slot change re-qualifies its role's chunk (IDs 6 / 7 hold the slot's current bytes).
namespace leon_hand_pack { void reset_role_ids(unsigned role) {actor_immutable_chunks[role]={};} }
#endif
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
// LEON_LOD: a rung load re-qualifies roles 0-4 / 7 (IDs 1..5, 8, shared by pl08's roles 2..7) and the hair run (ID 29).
namespace leon_lod { void reset_ids() {
    for(unsigned k=0;k<6;++k)actor_immutable_chunks[kRoles[k]]={};
    for(const auto& run:leon_hair_runs::runs)if(run.asset_id && run.asset_id<=RE4DC_IMMUTABLE_CHUNK_COUNT)actor_immutable_chunks[run.asset_id-1]={};
} }
#endif
#if RE4DC_ACTOR_PL08_PACK
#include "coarse_actor_pl08_pack.inc" // ACTOR_PL08_PACK: the pl08-only chunks from a costume-resident heap-4 cell
#endif
#if RE4DC_ACTOR_PL08
#include "coarse_actor_owner_pl08.inc"
#endif
#if defined(RE4DC_LEON_ATLAS_SPLIT) && RE4DC_LEON_ATLAS_SPLIT
#include "coarse_actor_atlas_split.inc"
#endif
#include "coarse_actor_transaction.inc"
#if RE4DC_ACTOR_PL08_PACK
namespace { bool pl08_pack_owned_live() {return actor_owned_live;} }
#endif
#if defined(RE4DC_LEON_LOD) && RE4DC_LEON_LOD
namespace leon_lod { bool owned_live() {return actor_owned_live;} }
#endif
#include "coarse_actor_material.inc" // actor-lifetime-r2 current-owner/material policy
#if RE4DC_ACTOR_EARLY_COARSE
#include "actor_early_coarse.inc"
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
#include "coarse_actor_registry_pack.inc" // the room-owned registry package (loader, publish, retire)
#endif
#endif
