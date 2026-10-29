#pragma once
#include "coarse_source_frame.h"
#include "coarse_actor_preflight.h"
#include "actor_native_owner.h"
#include "coarse_actor_geometry_once.h"
class cModel;
class cModelInfo;

// Source-only candidate; RE4DC_ACTOR_TRANSACTION remains default zero.
// Certificate rows must describe the reviewed SOURCE material/TPL identities,
// not only the replacement atlas. Missing certificates decline before owners.
struct Re4dcActorMaterialCertificate {
    unsigned appearance,role,parts,material_crc,material_fnv,texture_crc,texture_fnv;
};
struct Re4dcActorPlannedRun {
    unsigned role=0,material=0,immutable_asset_id=0,triangles=0;
    re4dc_source::ByteSpan uv{},stream{};
};
struct Re4dcActorPlan {
    unsigned count=0,appearance=0,palette_bytes=0,workspace_bytes=0;
    cModelInfo* info[kRe4dcActorRoles]{}; // role indexed; source list order is retained separately
    re4dc_source::ChunkInput input[kRe4dcActorRoles]{};
    Re4dcUiImage image{};
    unsigned crc=0,fnv=0;
    int (*palettes)(cModel*,const Re4dcActorPlan&,float* const*)=nullptr;
    // Palette/skin ownership remains role-indexed. Runs never allocate palettes.
    unsigned immutable_asset_id[kRe4dcActorRoles]{};
    unsigned material_count=0,run_count=0;
    Re4dcActorOwnedMaterial materials[kRe4dcActorMaterials]{};
    Re4dcActorPlannedRun runs[kRe4dcActorRuns]{};
#if defined(RE4DC_NMR_POOL) && RE4DC_NMR_POOL
    // NATIVE_MODEL_REGISTRY_POOL (native_model_registry.mk; every object): a pool descriptor's plan keeps its roles in
    // source info order and names, per role, the pool section (role row and chunk) that info proved. pool=0 for every
    // other plan: role k is section k.
    unsigned pool=0;
    unsigned char section[kRe4dcActorRoles]{};
#endif
};
#if defined(RE4DC_NMR_POOL) && RE4DC_NMR_POOL
inline unsigned re4dc_plan_section(const Re4dcActorPlan* p,unsigned k) {return p->pool?p->section[k]:k;}
#define RE4DC_PLAN_ROLE(p,k) re4dc_plan_section((p),(k))
#else
#define RE4DC_PLAN_ROLE(p,k) (k)
#endif
extern "C" {
int re4dc_actor_plan_leon(cModel*,Re4dcActorPlan*);
int re4dc_actor_plan_ganado(cModel*,Re4dcActorPlan*);
#if RE4DC_ACTOR_PL08
int re4dc_actor_plan_pl08(cModel*,Re4dcActorPlan*);
#endif
// This callback is the explicit, currently unpopulated source certificate
// boundary. It may only return one after comparing every original info's
// material and source TPL identity to a reviewed private certificate row.
int re4dc_actor_material_certificate(cModel*,const Re4dcActorPlan*);
// Exact original opaque hand/accessory descriptor, owned and unchanged.
int re4dc_actor_source_material(cModel*,cModelInfo*,unsigned appearance,unsigned role,Re4dcActorOwnedMaterial*);
// Implementation routing capability only, not proof of exact alpha coverage,
// lighting, current source ownership or visual acceptance.
unsigned re4dc_actor_material_runs_capability(const Re4dcActorPlan*);
int re4dc_actor_transaction_draw(cModel*);
void re4dc_actor_transaction_retire();
// Trans owns these guards. A ticket never exports a borrowed ledger address.
int re4dc_actor_transaction_identity(cModel*,re4dc_source::FrameIdentity*,re4dc_source::ModelIdentity*);
int re4dc_actor_transaction_choice(cModel*,unsigned*);
int re4dc_actor_transaction_choose(cModel*,unsigned);
int re4dc_actor_transaction_candidate(cModel*);
}

// The player owners: pl00 (appearance 0x100, eight infos) and, under ACTOR_PL08=1, the no-jacket pl08 (0x108, nine
// infos, the same 119-bone skeleton). Both keep the Leon-only semantics: role 3 is the bone-driven face (shape bit),
// role 7 the second-pass hair, the player's own lighting path. Off: exactly the former 0x100 tests.
#if RE4DC_ACTOR_PL08 && RE4DC_LEON_HEADLESS
// LEON_HEADLESS (crowd.mk): 0x109 is pl08 after setHead(0) (seven infos, no face role: the neck has no shape).
#define RE4DC_LEON_LIKE(app) ((app)==0x100u || (app)==0x108u || (app)==0x109u)
// LEON_HEADLESS v2: 0x10A is the flying head (cObj01 of player arc 0xC): its own class, never the player.
#define RE4DC_HEAD_APP(app) ((app)==0x10Au)
#define RE4DC_LEON_FACE_ROLE(p,i) (((p).count==8 || (p).appearance==0x108u) && (i)==3)
#elif RE4DC_ACTOR_PL08
#define RE4DC_LEON_LIKE(app) ((app)==0x100u || (app)==0x108u)
#define RE4DC_LEON_FACE_ROLE(p,i) (((p).count==8 || (p).appearance==0x108u) && (i)==3)
#else
#define RE4DC_LEON_LIKE(app) ((app)==0x100u)
#define RE4DC_LEON_FACE_ROLE(p,i) ((p).count==8 && (i)==3)
#endif
#ifndef RE4DC_HEAD_APP
#define RE4DC_HEAD_APP(app) false
#endif
// A role whose info may carry the shape bit (be_flag 2) on the owner path: Leon's bone-driven face and, under
// PS2_ASHLEY=2 (native_model_registry.mk; user look decision pending), Ashley's head drawn at its PS2 rest face
// (coarse_actor_owner_registry.inc re4dc_registry_ashley_face). Off: exactly RE4DC_LEON_FACE_ROLE.
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
// NATIVE_MODEL_REGISTRY_PL_ASHLEY: also playable Ashley's face (role 1 of her model 0 / 141-joint descriptor).
extern "C" int re4dc_registry_ashley_face(unsigned appearance,unsigned role);
extern "C" int re4dc_registry_player_ashley_face(unsigned appearance,unsigned role);
extern "C" int re4dc_registry_player_ashley_role(unsigned appearance,unsigned role,unsigned bin,unsigned tpl);
#define RE4DC_ACTOR_SHAPE_ROLE(p,i) (RE4DC_LEON_FACE_ROLE(p,i) || re4dc_registry_ashley_face((p).appearance,(i)) || \
    re4dc_registry_player_ashley_face((p).appearance,(i)))
#elif defined(RE4DC_NMR_ASHLEY) && RE4DC_NMR_ASHLEY >= 2
extern "C" int re4dc_registry_ashley_face(unsigned appearance,unsigned role);
#define RE4DC_ACTOR_SHAPE_ROLE(p,i) (RE4DC_LEON_FACE_ROLE(p,i) || re4dc_registry_ashley_face((p).appearance,(i)))
#else
#define RE4DC_ACTOR_SHAPE_ROLE(p,i) RE4DC_LEON_FACE_ROLE(p,i)
#endif
namespace re4dc_actor {
#if RE4DC_ACTOR_SOURCE_SPAN
// Called only after the plan's immutable chunk proof. Preserve the parser's
// logical allocations, including unreferenced records and padding.
inline bool source_span(const re4dc_source::ChunkInput& c,Re4dcActorSourceSpan& a) {
    if(c.positions.size>UINT32_MAX || c.normals.size>UINT32_MAX || c.uv.size>UINT32_MAX || c.stream.size>UINT32_MAX)return false;
    a={c.positions.data,c.normals.data,unsigned(c.positions.size),unsigned(c.normals.size),unsigned(c.uv.size),
       Re4dcActorSourceSpan::U16Q15,0,0};
    return true;
}
#endif
inline bool exact_infos(cModelInfo* first,cModelInfo* const* roles,unsigned n) {
    unsigned seen=0,count=0;
    for(auto* p=first;p;p=p->pList) {
        if(count++==n)return false;
        unsigned k=0;for(;k<n && roles[k]!=p;++k){}
        if(k==n || (seen&(1u<<k)))return false;
        seen|=1u<<k;
    }
    return count==n && seen==(1u<<n)-1;
}
template<class Chunk> inline void plan_chunk(Re4dcActorPlan& p,unsigned role,cModelInfo* info,
    const Chunk& c,const re4dc_source::ChunkInput& input) {
    p.info[role]=info;p.input[role]=input;
    const unsigned palette=(c.palette_count*48u+31u)&~31u;
    const unsigned skin=(c.palette_count*114u+31u)&~31u;
    p.palette_bytes+=palette;
    if(skin>p.workspace_bytes)p.workspace_bytes=skin;
}
}
#define RE4DC_OWNER_SPAN(a) {reinterpret_cast<const unsigned char*>(a),sizeof(a)}
#define RE4DC_OWNER_INPUT(ns,prefix,c,bones) \
    re4dc_source::ChunkInput{RE4DC_OWNER_SPAN(ns::prefix##_pos),RE4DC_OWNER_SPAN(ns::prefix##_nrm), \
    RE4DC_OWNER_SPAN(ns::prefix##_uv),RE4DC_OWNER_SPAN(ns::prefix##_gx),RE4DC_OWNER_SPAN(ns::prefix##_weights), \
    c.position_count,c.normal_count,c.palette_count,c.triangles,bones}
