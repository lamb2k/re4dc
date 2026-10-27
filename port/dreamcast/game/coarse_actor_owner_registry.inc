// NATIVE_MODEL_REGISTRY (native_model_registry.mk; render only): generic native models on the ACTOR_TRANSACTION owner
// path. Included once by coarse_actor_owner_leon.inc, before the geometry-once table and the transaction.
// Input: native_model_registry.h from a private bundle (tools/d367/model_registry.py): per descriptor the source
// model id, the pack's own bone count, parents and inverse bind, one chunk per source info (source info order),
// each chunk's texture package, and the source identity rows (native_model_registry_*.inc, merged into
// actor_material_records.inc) that the lifetime/material proofs check. Nothing is matched by model id alone: an
// actor plans a descriptor only when the archive adoption proof binds EVERY info of the actor to that descriptor's
// exact source BIN + TPL rows (re4dc_actor_role_bindings), its skeleton has the descriptor's bone count and parents
// and its rest rotations equal the descriptor's inverse bind. The plan then goes through the unchanged transaction:
// layout, semantics (live info state, immutable chunk proof), the material certificate (registry branch in
// coarse_actor_material.inc), the shared palette/workspace/skin/texture leases and the source pass order.
// Any failure before the first TA header keeps the whole actor on the source path (counted by reason below).
// =1 draws admitted actors; =2 (compare) runs the same admission and the palette build into a scratch buffer, then
// keeps the source path (no native TA submission): "NMR" lines count would-admit and every decline reason.
// NATIVE_MODEL_REGISTRY_PACK=1: nothing above is compiled in. The same descriptors / chunks / textures come from the
// room's validated package (coarse_actor_registry_pack.inc publishes them into the view below for one room
// generation; until then and after its retire the view is empty and every actor keeps the source path).
// Identical chunk geometry is stored once: a chunk names its unique geometry, which keys the skin stream and the
// immutable chunk ID; texture and source identity stay per descriptor.
#include "coarse_skin.h"
#include "actor_ganado_ps2_stump.h"
#if defined(RE4DC_ASHLEY_PS2_RIG) && RE4DC_ASHLEY_PS2_RIG
#include "ashley_ps2_rig27.h"
static_assert(ashley_ps2_rig27::version==1,"ASHLEY_PS2_RIG needs its PS2 rig build assets");
#endif
#if defined(RE4DC_ASHLEY_PLAYABLE_PS2_RIG) && RE4DC_ASHLEY_PLAYABLE_PS2_RIG
#include "ashley_playable_ps2_rig27.h"
static_assert(ashley_playable_ps2_rig27::version==1,"ASHLEY_PLAYABLE_PS2_RIG needs its own PS2 rig build assets");
#endif
#if RE4DC_COARSE_SKIN_FTRV != 1
#error NATIVE_MODEL_REGISTRY builds its palettes with COARSE_SKIN_FTRV=1
#endif
#if RE4DC_NMR_SLOTS && !RE4DC_NATIVE_MODEL_REGISTRY_PACK
#error PS2_ASHLEY (RE4DC_NMR_SLOTS, draw-slot descriptors) needs NATIVE_MODEL_REGISTRY_PACK=1
#endif
#if defined(RE4DC_NMR_POOL_LOD) && RE4DC_NMR_POOL_LOD
extern "C" unsigned re4dc_ganado_lod_level();  // coarse_ganado_lod.inc (GANADO_LOD=1): the level loaded now, ~0u none
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
namespace nmr {
struct Weight { unsigned char bone[3], count; float value[3]; };
struct Chunk { unsigned source_info, position_count, normal_count, palette_count, triangles, stream_bytes;
    const unsigned char *positions, *normals, *uv, *stream; const Weight *weights; unsigned uv_bytes, texture, skin_bytes, geometry;
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
    // Source role stays distinct; only the reviewed Luis face may share its head's draw.
    unsigned draw_owner;
#endif
#if RE4DC_NMR_MASK
    // NATIVE_MODEL_REGISTRY_MASK: a section drawn as two runs, the opaque triangles (geometry mask_geometry[0], the
    // chunk texture) and the alpha-masked ones (geometry mask_geometry[1], colour + I4 mask pair: textures
    // mask_texture[0] / [1], pair key pair_crc / pair_fnv as native_ui.cpp model_mask_key derives it). ~0u: none.
    unsigned mask_geometry[2], mask_texture[2], pair_crc, pair_fnv;
#endif
};
struct Texture { unsigned crc, fnv, width, height; };
struct Descriptor { char name[16]; unsigned appearance, model_id, bones, sections, first_chunk, skin_bytes;
    const signed char* parents; const float (*bind)[12];
#if RE4DC_NMR_SHIFT
    unsigned shift;  // NATIVE_MODEL_REGISTRY_SHIFT: the chunks' position fraction bits (package descriptor word 44; 0 = 4)
#endif
#if RE4DC_NMR_SLOTS
    // PS2_ASHLEY (native_model_registry.mk): source_bones != 0 marks a draw-slot descriptor. The model has source_bones
    // joints (each with source_parents[j], 0xff = the model, and its rest inverse bind[j]); the chunks' weights name
    // the `bones` draw slots, slot k drawing source joint source_parents[source_bones + k] (the slot map follows the
    // parents; strictly increasing). 0: an ordinary descriptor (parents / bind per bone, as without the knob).
    unsigned source_bones; const unsigned char* source_parents;
#endif
#if RE4DC_NMR_POOL
    unsigned pool;  // NATIVE_MODEL_REGISTRY_POOL: 1 = the sections are a pool (package descriptor word 44 bit 24)
#endif
#if defined(RE4DC_NMR_LOD) && RE4DC_NMR_LOD
    unsigned lod_of;  // NATIVE_MODEL_REGISTRY_LOD: 0, or a gameplay level of descriptor lod_of - 1 (word 44 bit 25)
#endif
#if defined(RE4DC_NMR_POOL_LOD) && RE4DC_NMR_POOL_LOD
    unsigned lod_level;  // NMR_POOL_LOD: a numbered pool level (word 44 bits 26..29, GANADO_LOD level order); 0 = none
#endif
};
constexpr unsigned appearance_first=0x200u;
}
static_assert(sizeof(nmr::Weight)==16,"package weight records");
// Explicit capacities of one room package (the generator and the loader refuse more). NATIVE_MODEL_REGISTRY_BONES
// (native_model_registry.mk, default 48) sets the skeleton capacity.
#ifndef RE4DC_NMR_BONES
#define RE4DC_NMR_BONES 48
#endif
#if defined(RE4DC_NMR_POOL) && RE4DC_NMR_POOL && defined(RE4DC_NMR_ROLES5) && RE4DC_NMR_ROLES5
#define RE4DC_NMR_CHUNKS 96  // NATIVE_MODEL_REGISTRY_ROLES5 (lane cast16): room packages of several pools (island soldiers
                             // with accessories: 65..72 chunk refs; r227 em14 types 6..9: 71)
#elif defined(RE4DC_NMR_POOL) && RE4DC_NMR_POOL
#define RE4DC_NMR_CHUNKS 64  // NATIVE_MODEL_REGISTRY_POOL: a pool descriptor (one chunk per pool section) + a partner package
#elif defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER
#define RE4DC_NMR_CHUNKS 48  // PS2_ASHLEY_ROOMS: a room package + Ashley's partner package (r112: 14 + 21 chunks)
#else
#define RE4DC_NMR_CHUNKS 32
#endif
// PS2_ASHLEY_ROOMS=2 (RE4DC_NMR_PARTNER=2, lane ashley17): room package + partner share a 32-entry texture table
// (r11c: Luis 11 + Ashley 6 = 17 refused the partner at 16).
#if defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER>=2
#define RE4DC_NMR_REG_TEXTURES 32
#else
#define RE4DC_NMR_REG_TEXTURES 16
#endif
#if RE4DC_NMR_POOL && defined(RE4DC_NMR_ROLES5) && RE4DC_NMR_ROLES5
// ROLES5: 32 package textures (r227: em14 types 6..9 carry 20 atlas pages).
// r202's original monks, closed/open Merchant and full Ashley partner need 69 unique geometries.
// Reserve eight additional records only in the explicit recipe; the loader admits >64 only in r202.
#if defined(RE4DC_NMR_R202_CAST_CAPACITY) && RE4DC_NMR_R202_CAST_CAPACITY
#define RE4DC_NMR_ROLES5_GEOMETRY 72
#else
#define RE4DC_NMR_ROLES5_GEOMETRY 64
#endif
constexpr unsigned kRegDescriptors=16,kRegChunks=RE4DC_NMR_CHUNKS,kRegGeometry=RE4DC_NMR_ROLES5_GEOMETRY,kRegTextures=32,kRegBones=RE4DC_NMR_BONES;
constexpr unsigned kRegPoolSections=48;  // a pool descriptor's sections (role rows); a plan still draws <= 8 of them
#elif RE4DC_NMR_POOL
constexpr unsigned kRegDescriptors=16,kRegChunks=RE4DC_NMR_CHUNKS,kRegGeometry=64,kRegTextures=RE4DC_NMR_REG_TEXTURES,kRegBones=RE4DC_NMR_BONES;
constexpr unsigned kRegPoolSections=48;  // a pool descriptor's sections (role rows); a plan still draws <= 8 of them
#else
constexpr unsigned kRegDescriptors=16,kRegChunks=RE4DC_NMR_CHUNKS,kRegGeometry=32,kRegTextures=RE4DC_NMR_REG_TEXTURES,kRegBones=RE4DC_NMR_BONES;
#endif
#if RE4DC_NMR_SLOTS
// A draw-slot descriptor's source skeleton (parents are u8 with 0xff = root, so at most 255 joints): the draw-slot
// capacity stays kRegBones (bindings, palettes, jobs); only the skeleton proof walks the source joints.
constexpr unsigned kRegSourceBones=255;
#endif
#else
#include "native_model_registry.h"
static_assert(nmr::descriptor_count && nmr::descriptor_count<=32 && nmr::chunk_count && nmr::max_bones<=256,"registry bundle shape");
static_assert(nmr::texture_count<=64,"registry textures");
constexpr unsigned kRegDescriptors=nmr::descriptor_count,kRegChunks=nmr::chunk_count,kRegGeometry=nmr::chunk_count,
    kRegTextures=nmr::texture_count,kRegBones=nmr::max_bones;
#endif
extern "C" unsigned re4dc_ui_frame();
// NATIVE_MODEL_REGISTRY_CENSUS (diagnostic, default 0): the decline-reason counters, bind deviation maxima and the
// scene census below exist only in census builds; a production / cost build has none of their storage or work.
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
#define NMR_CENSUS(...) __VA_ARGS__
#else
#define NMR_CENSUS(...)
#endif
#define NMR_WHY(x) NMR_CENSUS(registry_why=(x))
namespace {
// Immutable asset IDs after the transaction's fixed table (coarse_actor_geometry_once.inc).
#if RE4DC_CROWD_FAR
constexpr unsigned kRegistryAsset0=66u+1u+RE4DC_GANADO_STUMP_IDS;
#else
constexpr unsigned kRegistryAsset0=46u+1u+RE4DC_GANADO_STUMP_IDS;
#endif
constexpr unsigned kRegistryAssetEnd=kRegistryAsset0+kRegGeometry;  // one past the last ID (one per unique geometry)
// The registry as the owner path reads it: the compiled bundle, or the published room package.
struct RegistryView {
    const nmr::Descriptor* descriptors;const nmr::Chunk* chunks;const nmr::Texture* textures;
    unsigned descriptor_count,chunk_count,texture_count,geometry_count,generation;
};
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
RegistryView registry{};
inline unsigned registry_geometry(unsigned chunk) {return registry.chunks[chunk].geometry;}
#else
const RegistryView registry{nmr::descriptors,nmr::chunks,nmr::textures,nmr::descriptor_count,nmr::chunk_count,
    nmr::texture_count,nmr::chunk_count,1};
inline unsigned registry_geometry(unsigned chunk) {return chunk;}
#endif
// Decline reasons (the first failing stage of an actor whose model id has a descriptor).
enum RegistryWhy : unsigned {
    kRwNone,kRwShape,kRwRevision,kRwRoles,kRwSkeleton,kRwFinite,kRwSkin,kRwPlan,kRwLayout,kRwSemantics,
    kRwCertificate,kRwAcquire,kRwCount
};
unsigned registry_tokens[kRegTextures];
Re4dcUiImage registry_image(unsigned t) {
    return Re4dcUiImage{&registry_tokens[t],nullptr,registry.textures[t].width,registry.textures[t].height,6,0xffffffffU,0};
}
#if RE4DC_NMR_MASK
// NATIVE_MODEL_REGISTRY_MASK: every geometry's own arrays (the published package's geometry views; a masked section's
// run streams / UVs come from its two run geometries) and the I4 mask image of a pair (format 0, its own token).
// The views decode on demand from the package's 64-byte geometry headers (no per-geometry table: static bytes are heap).
const unsigned char *registry_geom,*registry_blob;
nmr::Chunk registry_geom_view(const unsigned char* geom,const unsigned char* blob,unsigned g) {
    const unsigned char* r=geom+g*64u;unsigned w[13];std::memcpy(w,r,sizeof(w));
    nmr::Chunk v{};v.position_count=w[0];v.normal_count=w[1];v.palette_count=w[2];v.triangles=w[3];v.stream_bytes=w[4];
    v.uv_bytes=w[5];v.skin_bytes=w[6];v.geometry=g;v.positions=blob+w[8];v.normals=blob+w[9];v.uv=blob+w[10];
    v.stream=blob+w[11];v.weights=reinterpret_cast<const nmr::Weight*>(blob+w[12]);v.mask_geometry[0]=v.mask_geometry[1]=~0u;
    return v;
}
#if defined(RE4DC_NMR_PARTNER) && RE4DC_NMR_PARTNER
// PS2_ASHLEY_ROOMS: geometries from registry_geom_base2 on are the partner package's (its own header table and blob).
const unsigned char *registry_geom2,*registry_blob2;unsigned registry_geom_base2=~0u;
nmr::Chunk registry_gview(unsigned g){
    if(g<registry_geom_base2)return registry_geom_view(registry_geom,registry_blob,g);
    nmr::Chunk v=registry_geom_view(registry_geom2,registry_blob2,g-registry_geom_base2);v.geometry=g;return v;
}
#else
nmr::Chunk registry_gview(unsigned g){return registry_geom_view(registry_geom,registry_blob,g);}
#endif
Re4dcUiImage registry_mask_image(unsigned t) {
    return Re4dcUiImage{&registry_tokens[t],nullptr,registry.textures[t].width,registry.textures[t].height,0,0xffffffffU,0};
}
#endif
// FTRV palette groups (coarse_skin.h), one stream per unique geometry; per descriptor its used bones.
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
unsigned char* registry_skin;unsigned registry_skin_cap;  // the package cell's skin arena (header skin_bytes)
#else
alignas(32) unsigned char registry_skin[(nmr::skin_stream_bytes+31u)&~31u];
constexpr unsigned registry_skin_cap=sizeof(registry_skin);
#endif
unsigned registry_skin_first[kRegGeometry],registry_skin_groups[kRegGeometry];
unsigned char registry_skin_built[kRegGeometry];
unsigned char registry_skin_bone[kRegDescriptors][kRegBones];
unsigned registry_skin_used[kRegDescriptors],registry_skin_state[kRegDescriptors],registry_skin_next;
alignas(32) float registry_T[kRegBones][12];
CoarseBoneJob registry_jobs[kRegBones];
// Model ids with at least one descriptor: an O(1) reject for every other actor.
unsigned registry_id_mask[8];
bool registry_mask_ready;
struct RegistryBinding {
    cModel* owner;cParts* list;const void* root;unsigned serial,revision,descriptor,count;
    cModelInfo* infos[8];cParts* parts[kRegBones];
#if RE4DC_NMR_POOL
    unsigned char sec[8];  // a pool descriptor: the pool section each info (source order) proved; else sec[i] = i
#endif
};
RegistryBinding registry_bindings[16];
unsigned registry_replace;
RegistryBinding* registry_bound;
#if RE4DC_NMR_POOL
// NATIVE_MODEL_REGISTRY_POOL: a plan matches its descriptor's shape: an ordinary descriptor, exactly its sections in
// order (pool 0); a pool descriptor, 1..8 distinct pool sections in source info order, section 0 (the body) first.
bool registry_plan_shape(const Re4dcActorPlan* p,const nmr::Descriptor* desc) {
    if(!desc->pool)return !p->pool && p->count==desc->sections;
    if(!p->pool || !p->count || p->count>8u || p->count>desc->sections || p->section[0])return false;
    unsigned long long seen=0;
    for(unsigned k=0;k<p->count;++k) {
        const unsigned x=p->section[k];
        if(x>=desc->sections || ((seen>>x)&1u))return false;
        seen|=1ull<<x;
    }
    return true;
}
#define RE4DC_PLAN_SHAPE(p,desc) registry_plan_shape((p),(desc))
#define RE4DC_PLAN_SECTIONS(p,desc) ((desc)->pool?(p)->count:(desc)->sections)
#else
#define RE4DC_PLAN_SHAPE(p,desc) ((p)->count==(desc)->sections)
#define RE4DC_PLAN_SECTIONS(p,desc) ((desc)->sections)
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
// NATIVE_MODEL_REGISTRY_TX (native_model_registry.mk): the plan's binding proof (registry_bind: shape, revision, role
// rows, skeleton, finite matrices) is reused by the palette build of the SAME transaction instead of running a second
// time. registry_tx_serial counts re4dc_actor_transaction_draw calls; the plan leaves a token naming that call, the
// model, its binding slot and the room generation, and the palette build consumes it once. Between the two only native
// code runs (layout, semantics, the leases, actor_acquire), none of which writes a source field the proof reads (the
// audit is in native_model_registry.mk). Any other caller, model, slot, generation or call runs the whole proof again.
unsigned registry_tx_serial;
struct RegistryTxToken { unsigned serial,generation;const cModel* m;const RegistryBinding* b; };
RegistryTxToken registry_tx{};
// Exact whole-array form of coarse_finite: bit 31 of the OR of (exponent field + 0x00800000) is set iff some
// element's exponent field is all ones (infinite or NaN). Integer loads, no branch per element.
typedef unsigned __attribute__((may_alias)) RegistryWord;
inline bool registry_all_finite(const float* f,unsigned n) {
    const RegistryWord* u=reinterpret_cast<const RegistryWord*>(f);unsigned a=0,b=0,k=0;
    for(;k+4<=n;k+=4)a|=((u[k]&0x7f800000u)+0x00800000u)|((u[k+1]&0x7f800000u)+0x00800000u),
        b|=((u[k+2]&0x7f800000u)+0x00800000u)|((u[k+3]&0x7f800000u)+0x00800000u);
    for(;k<n;++k)a|=(u[k]&0x7f800000u)+0x00800000u;
    return !((a|b)&0x80000000u);
}
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND
// NATIVE_MODEL_REGISTRY_PALBOUND (native_model_registry.mk): the palette outputs' finite test is replaced, when it is
// implied, by a test of the descriptor's used bone matrices T (registry_skin_used bones x 12, about 1/6 of the output
// elements). Every output element is re4dc_coarse_skin_groups' sum of at most 4 products w*t, t an element of a used
// bone's T and w the entry's weight or 0 (coarse_group_build; one-bone entries are copies with w = 1). With every
// such w in [0, 1] (registry_skin_unit, checked once per room generation at the skin build) and every |t| < 2^125
// (exponent field <= 0xFB, which also excludes inf / NaN), |w*t| <= |t| and the sum stays below 2^127: finite. Not
// bounded: the whole output test runs as before. So the verdict equals the output test's; =2 counts bounded chunks
// whose outputs are not finite (must be 0) and "stricter": bound failed, the output test ran (not a rejection).
unsigned char registry_skin_unit[kRegDescriptors];  // 1: every weight of the descriptor's chunks lies in [0, 1]
inline bool registry_all_bounded(const float* f,unsigned n) {
    const RegistryWord* u=reinterpret_cast<const RegistryWord*>(f);unsigned a=0;
    for(unsigned k=0;k<n;++k)a|=(u[k]&0x7f800000u)+0x02000000u;  // bit 31 iff the exponent field >= 0xFC
    return !(a&0x80000000u);
}
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND == 2
struct RegistryBoundCompare { unsigned chunks,bounded,bad,stricter,last; };
RegistryBoundCompare registry_pbc{};
void registry_pb_report(const char* why) {
    re4dc_log("NMRPB %s f=%u chunks=%u bounded=%u bounded_not_finite=%u stricter=%u\n",why,unsigned(pG->Frame_cnt),
        registry_pbc.chunks,registry_pbc.bounded,registry_pbc.bad,registry_pbc.stricter);
}
#endif
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
// Compare build: every reused or reduced verdict is computed both ways; the original verdict decides. "NMRTX" lines.
struct RegistryTxCompare { unsigned bind,reused,bind_bad,skeleton,skeleton_bad,finite,finite_bad,semantics,held,
    semantics_bad,roles,roles_bad,last; };
RegistryTxCompare registry_txc{};
void registry_tx_report(const char* why) {
    const auto& c=registry_txc;
    re4dc_log("NMRTX %s f=%u palette_binds=%u reused=%u bind_bad=%u skeleton=%u skeleton_bad=%u finite=%u finite_bad=%u "
        "semantics=%u held=%u semantics_bad=%u role_scans=%u roles_bad=%u\n",why,unsigned(pG->Frame_cnt),c.bind,c.reused,
        c.bind_bad,c.skeleton,c.skeleton_bad,c.finite,c.finite_bad,c.semantics,c.held,c.semantics_bad,c.roles,c.roles_bad);
}
#endif
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
unsigned registry_why;
// Census (cumulative since boot): per descriptor admitted / declined, per reason, the largest rest-inverse deviation
// from the descriptor's bind accepted (rotation, translation), the last planned actor's position, and the scene table.
struct RegistryCount { unsigned planned,admitted,would,declined,why[kRwCount];float bind_rotation,bind_translation,pos[3]; };
RegistryCount registry_count[kRegDescriptors];
#if defined(RE4DC_NMR_BIN_DIAG) && RE4DC_NMR_BIN_DIAG
extern "C" void re4dc_nmr_bin_name(const cModelInfo*,unsigned);  // actor_lifetime.inc (NATIVE_MODEL_REGISTRY_BIN_DIAG)
#endif
unsigned registry_unbound_why[kRwCount];  // declines before a descriptor was chosen (shape / roles / skeleton)
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
alignas(32) float registry_scratch[256*12];
// Compare mode: the source palette of this game frame (trans.cpp commonScreenMatSub, right after calcWeightMat) per
// registry actor, checked against inv(root) x part.mat x descriptor bind recomputed at the owner draw: equal when
// the native palettes see the same pose and bind the source skinned with.
struct RegistrySnap { const cModel* m;unsigned serial,frame,bones;float T[kRegBones][12]; };
RegistrySnap registry_snaps[16];
unsigned registry_snap_next,registry_cmp_models,registry_cmp_bad,registry_cmp_nosnap;
float registry_cmp_max;
#endif
inline bool registry_id(unsigned id) {
    if(!registry_mask_ready) {
        for(unsigned d=0;d<registry.descriptor_count;++d) {
            const unsigned id=registry.descriptors[d].model_id;registry_id_mask[(id&255u)>>5]|=1u<<(id&31u);
        }
        registry_mask_ready=true;
    }
    return id<256 && (registry_id_mask[id>>5]>>(id&31u)&1u);
}
inline const nmr::Descriptor* registry_descriptor(unsigned appearance) {
    if(appearance<nmr::appearance_first || appearance-nmr::appearance_first>=registry.descriptor_count)return nullptr;
    return &registry.descriptors[appearance-nmr::appearance_first];
}
#if RE4DC_NMR_SLOTS
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
#error PS2_ASHLEY draw slots are not modelled by the compare mode (its snapshot indexes source palettes by draw bone)
#endif
// The model part count a descriptor proves: its source joints (a draw-slot descriptor) or its bones.
inline unsigned registry_source_bones(const nmr::Descriptor& d) { return d.source_bones?d.source_bones:d.bones; }
#endif
#if RE4DC_NMR_SHIFT
// NATIVE_MODEL_REGISTRY_SHIFT: the owned part's position shift (coarse_actor_transaction.inc): a registry
// appearance's package shift (a model whose source positions exceed the 1/16 range: El Gigante, shift 2), else 4.
inline unsigned registry_position_shift(unsigned appearance) {
    const nmr::Descriptor* d=registry_descriptor(appearance);
    return d?d->shift:4u;
}
#endif
bool registry_skin_init(unsigned d) {
    if(registry_skin_state[d])return registry_skin_state[d]==1;
    const auto& desc=registry.descriptors[d];
    unsigned char used[kRegBones]={};
    if(desc.bones>kRegBones){registry_skin_state[d]=2;return false;}
    for(unsigned i=0;i<desc.sections;++i) {
        const unsigned ci=desc.first_chunk+i,g=registry_geometry(ci);
        const auto& c=registry.chunks[ci];
        for(unsigned j=0;j<c.palette_count;++j)for(unsigned k=0;k<c.weights[j].count;++k) {
            if(c.weights[j].bone[k]>=desc.bones){registry_skin_state[d]=2;return false;}
            used[c.weights[j].bone[k]]=1;  // the bones coarse_group_build marks
        }
        if(registry_skin_built[g])continue;  // a geometry shared with an earlier descriptor: its stream exists
        registry_skin_first[g]=registry_skin_next;
        const unsigned b=coarse_group_build(c.weights,c.palette_count,registry_skin+registry_skin_next,registry_skin_cap-registry_skin_next,
            &registry_skin_groups[g],used);
        if(!b || b!=c.skin_bytes){registry_skin_state[d]=2;re4dc_log("NMR %s skin palette does not fit\n",desc.name);return false;}
        registry_skin_next+=b;registry_skin_built[g]=1;
    }
    registry_skin_used[d]=0;
    for(unsigned b=0;b<desc.bones;++b)if(used[b])registry_skin_bone[d][registry_skin_used[d]++]=(unsigned char)b;
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND
    registry_skin_unit[d]=1;
    for(unsigned i=0;i<desc.sections;++i) {
        const auto& c=registry.chunks[desc.first_chunk+i];
        for(unsigned j=0;j<c.palette_count;++j)for(unsigned k=0;k<c.weights[j].count;++k)
            if(!(c.weights[j].value[k]>=0.0f && c.weights[j].value[k]<=1.0f))registry_skin_unit[d]=0;
    }
#endif
    re4dc_log("NMR skin %s bones=%u used=%u stream=%u/%u\n",desc.name,desc.bones,registry_skin_used[d],registry_skin_next,
        registry_skin_cap);
    registry_skin_state[d]=1;return true;
}
// The skeleton proof, run on EVERY bind (a cache hit included, so no skeleton / inverse-bind change depends on which
// source mutations bump re4dc_actor_binding_revision): the parts list is walked again (count = the descriptor's
// bones), every part's parent is the descriptor's, its rest inverse (lt_inv_mat, written by the source joint setup)
// equals the descriptor's inverse bind (rotation within .001, translation within kRegistryBindMm source units: the
// generated bind, from the cast's captured source rest, is what the palettes skin with), and every matrix is finite.
constexpr float kRegistryBindMm=0.1f;
#if RE4DC_NMR_SLOTS
// PS2_ASHLEY: a draw-slot descriptor's proof covers EVERY source joint (the walk, each parent, each rest inverse) on a
// stack list (no static storage: coarse_actor.o's data sits in the 16 KiB-padded character data block, whose slack is
// a few hundred bytes); the binding then keeps only the slots' parts (b.parts[k] = joint slot k's source joint), which
// are all the palettes read. dev[0] / dev[1]: the census's rotation / translation deviation maxima.
__attribute__((noinline)) bool registry_skeleton_slots(cModel* m,RegistryBinding& b,const nmr::Descriptor& desc,float* dev) {
    cParts* src[kRegSourceBones];
    const unsigned joints=desc.source_bones;const unsigned char* const up=desc.source_parents;
#if defined(RE4DC_ASHLEY_PLAYABLE_PS2_RIG) && RE4DC_ASHLEY_PLAYABLE_PS2_RIG
    // registry_bind has already reproved every adopted player-family role.
    // Shape alone never authorizes mapping: Leon and unrelated model0 owners
    // cannot use this adapter, even if a descriptor resembles playable Ashley.
    if(ashley_playable_ps2_rig27::shape(desc.model_id,joints,desc.sections) &&
       ((const cModel*)pPL!=m || m->ot_type!=7u ||
        !ashley_playable_ps2_rig27::slots_match(up+joints,desc.bones)))return false;
#endif
#if defined(RE4DC_ASHLEY_PS2_RIG) && RE4DC_ASHLEY_PS2_RIG
    // A PS2 rig arm must not silently skin an old surface-transferred package.
    if(ashley_ps2_rig27::applies(desc.model_id,joints,desc.sections) &&
       !ashley_ps2_rig27::slots_match(up+joints,desc.bones))return false;
#endif
    cParts* part=m->pList;
    for(unsigned k=0;k<joints;++k){if(!part)return false;src[k]=part;part=part->pList;}
    if(part)return false;
    for(unsigned k=0;k<joints;++k) {
        const cCoord* want=up[k]==0xffu?(const cCoord*)m:(const cCoord*)src[up[k]];
        if(src[k]->pParent!=want)return false;
        for(unsigned row=0;row<3;++row)for(unsigned col=0;col<4;++col) {
            const float d=__builtin_fabsf(src[k]->lt_inv_mat[row][col]-desc.bind[k][row*4+col]);
            if(!(d<=(col==3?kRegistryBindMm:.001f)))return false;
            if(col==3){if(d>dev[1])dev[1]=d;}else if(d>dev[0])dev[0]=d;
        }
    }
    for(unsigned k=0;k<desc.bones;++k)b.parts[k]=src[up[joints+k]];
    return true;
}
#endif
bool registry_skeleton(cModel* m,RegistryBinding& b,const nmr::Descriptor& desc) {
#if RE4DC_NMR_SLOTS
    float dev[2]={0.0f,0.0f};
    if(desc.source_bones) {
        if(!registry_skeleton_slots(m,b,desc,dev))return false;
    } else {
        cParts* part=m->pList;
        for(unsigned k=0;k<desc.bones;++k){if(!part)return false;b.parts[k]=part;part=part->pList;}
        if(part)return false;
        for(unsigned k=0;k<desc.bones;++k) {
            const int parent=desc.parents[k];
            const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)b.parts[parent];
            if(b.parts[k]->pParent!=want)return false;
            for(unsigned row=0;row<3;++row)for(unsigned col=0;col<4;++col) {
                const float d=__builtin_fabsf(b.parts[k]->lt_inv_mat[row][col]-desc.bind[k][row*4+col]);
                if(!(d<=(col==3?kRegistryBindMm:.001f)))return false;
                if(col==3){if(d>dev[1])dev[1]=d;}else if(d>dev[0])dev[0]=d;
            }
        }
    }
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    const float dr=dev[0],dt=dev[1];
#endif
#else
    cParts* part=m->pList;
    for(unsigned k=0;k<desc.bones;++k){if(!part)return false;b.parts[k]=part;part=part->pList;}
    if(part)return false;
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    float dr=0.0f,dt=0.0f;
#endif
    for(unsigned k=0;k<desc.bones;++k) {
        const int parent=desc.parents[k];
        const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)b.parts[parent];
        if(b.parts[k]->pParent!=want)return false;
        for(unsigned row=0;row<3;++row)for(unsigned col=0;col<4;++col) {
            const float d=__builtin_fabsf(b.parts[k]->lt_inv_mat[row][col]-desc.bind[k][row*4+col]);
            if(!(d<=(col==3?kRegistryBindMm:.001f)))return false;
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
            if(col==3){if(d>dt)dt=d;}else if(d>dr)dr=d;
#endif
        }
    }
#endif
    NMR_WHY(kRwFinite);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    // Every rest inverse element already passed the bind comparison above, which fails a NaN or infinite element
    // (no -ffinite-math-only: a NaN compares false, |inf - bind| is inf or NaN), so only the current matrices remain.
    bool finite=true;
    for(unsigned i=0;i<desc.bones && finite;++i)finite=registry_all_finite(&b.parts[i]->mat[0][0],12);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
    bool full=true;
    for(unsigned i=0;i<desc.bones;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&b.parts[i]->lt_inv_mat[0][0])[j]) || !coarse_finite((&b.parts[i]->mat[0][0])[j]))full=false;
    ++registry_txc.skeleton;if(finite!=full)++registry_txc.skeleton_bad;
    finite=full;
#endif
    if(!finite)return false;
#else
    for(unsigned i=0;i<desc.bones;++i)for(unsigned j=0;j<12;++j)
        if(!coarse_finite((&b.parts[i]->lt_inv_mat[0][0])[j]) || !coarse_finite((&b.parts[i]->mat[0][0])[j]))return false;
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
    auto& c=registry_count[&desc-registry.descriptors];
    if(dr>c.bind_rotation)c.bind_rotation=dr;
    if(dt>c.bind_translation)c.bind_translation=dt;
#endif
    return true;
}
#if defined(RE4DC_NMR_LOD) && RE4DC_NMR_LOD
// NATIVE_MODEL_REGISTRY_LOD (lane cast16 2026-10-16; user 10-16: a boss whose room projects < 30 fps draws a reduced
// gameplay model, the full model in cutscenes): the descriptor to draw for full (or level) descriptor d now. While an
// in-engine event / cutscene holds the game (Status_flg[1] 0x10000000, as GANADO_LOD) the full one; otherwise its
// gameplay level when the package has one whose role rows prove this model's infos, else the full one.
unsigned registry_lod_want(cModel* m,unsigned d,unsigned count) {
    if(d>=registry.descriptor_count)return d;
    const unsigned full=registry.descriptors[d].lod_of?registry.descriptors[d].lod_of-1u:d;
#if defined(RE4DC_ASHLEY_LOD) && RE4DC_ASHLEY_LOD
    const auto& ashley=registry.descriptors[full];
    if(ashley_ps2_rig27::applies(ashley.model_id,ashley.source_bones,ashley.sections)) {
        // Only the render descriptor changes. Keep close-ups and in-engine events
        // full; partner motion, cloth, event scheduling and RNG always run once.
        const float dx=m->pParts->mat[0][3]-pG->Cam.param.pos.x;
        const float dy=m->pParts->mat[1][3]-pG->Cam.param.pos.y;
        const float dz=m->pParts->mat[2][3]-pG->Cam.param.pos.z;
        const float dist2=dx*dx+dy*dy+dz*dz;
        const unsigned want=(pG->Status_flg[1]&0x10000000u)?0u:dist2>=10000.0f*10000.0f?2u:
                            dist2>=5000.0f*5000.0f?1u:0u;
        if(!want)return full;
        unsigned best=full,best_level=0;
        cModelInfo* probe[8]{};
        for(unsigned l=0;l<registry.descriptor_count;++l) {
            const auto& ld=registry.descriptors[l];
            if(ld.lod_of!=full+1u || ld.pool || !ld.lod_level || ld.lod_level>want || ld.lod_level<=best_level)continue;
            if(!re4dc_actor_role_bindings(m,ld.appearance,probe,count))continue;
            best=l;best_level=ld.lod_level;
        }
        return best;
    }
#endif
#if defined(RE4DC_NMR_POOL_LOD) && RE4DC_NMR_POOL_LOD
    // NMR_POOL_LOD (lane lod26b): a pool Ganado follows the level the cast Ganados draw now (GANADO_LOD level_cur:
    // its own event rule and GANADO_EVENT_KEEP_LOD apply): the numbered pool level with the highest number not above
    // it, else the full descriptor. One knob (GANADO_LOD_LEVEL) covers every Ganado.
    if(registry.descriptors[full].pool) {
        unsigned want=re4dc_ganado_lod_level();
        if(want==~0u)want=0;
        unsigned best=full,best_level=0;
        cModelInfo* probe[8]{};unsigned char psec[8]{};
        for(unsigned l=0;l<registry.descriptor_count;++l) {
            const auto& ld=registry.descriptors[l];
            if(ld.lod_of!=full+1u || !ld.pool || !ld.lod_level || ld.lod_level>want || ld.lod_level<=best_level)continue;
            if(!re4dc_actor_pool_bindings(m,ld.appearance,ld.sections,probe,psec,count))continue;
            best=l;best_level=ld.lod_level;
        }
        return best;
    }
#endif
    if(pG && (pG->Status_flg[1]&0x10000000u))return full;
#if defined(RE4DC_NMR_GRAB_FULL) && RE4DC_NMR_GRAB_FULL
    // NATIVE_MODEL_REGISTRY_GRAB_FULL: the player's custom damage routine (SetPlDamage: routine 4) that this actor
    // started (dmgType holds the enemy) is a close-up: the full model, as in an event.
    if(pPL && pPL->r_no_0==4 && pPL->dmgType==(int)(intptr_t)m)return full;
#endif
    for(unsigned l=0;l<registry.descriptor_count;++l) {
        const auto& ld=registry.descriptors[l];
        if(ld.lod_of!=full+1u || ld.sections!=count)continue;
        cModelInfo* probe[8]{};
        if(re4dc_actor_role_bindings(m,ld.appearance,probe,count))return l;
    }
    return full;
}
#endif
// The actor's descriptor from its adopted source infos and skeleton (sets registry_bound / registry_why). The cache
// only remembers which descriptor's role rows proved the infos (the multi-descriptor search); the role proof itself,
// the info pointers and the skeleton proof run again on every call.
bool registry_bind(cModel* m) {
    registry_bound=nullptr;NMR_WHY(kRwShape);
#if RE4DC_NMR_SLOTS
    if(!m || !registry_id(m->id) || !m->pList || !m->pParts || (m->be_flag&0x4000) || m->nParts>kRegSourceBones)return false;
#else
    if(!m || !registry_id(m->id) || !m->pList || !m->pParts || (m->be_flag&0x4000) || m->nParts>kRegBones)return false;
#endif
    unsigned count=0;
    for(auto* i=m->pModelInfo;i;i=i->pList)if(++count>8)return false;
    if(!count)return false;
    NMR_WHY(kRwRevision);
    const unsigned revision=re4dc_actor_binding_revision(m);if(!revision)return false;
    RegistryBinding* b=nullptr;
    for(auto& e:registry_bindings)
        if(e.owner==m && e.serial==m->serial && e.list==m->pList && e.root==m->pParts && e.revision==revision && e.count==count){b=&e;break;}
#if defined(RE4DC_NMR_LOD) && RE4DC_NMR_LOD
    // NATIVE_MODEL_REGISTRY_LOD: a cached binding to the full model during gameplay, or to a gameplay level while an
    // in-engine event holds the game, is dropped; the search below binds the descriptor wanted now.
    if(b && b->descriptor!=registry_lod_want(m,b->descriptor,count)){b->owner=nullptr;b=nullptr;}
#endif
    cModelInfo* infos[8]{};
#if RE4DC_NMR_POOL
    unsigned char sec[8]{};
#endif
    NMR_WHY(kRwRoles);
    if(b) {
        // Current source pointers/owner revisions are checked even on a binding hit.
#if RE4DC_NMR_POOL
        const auto& bd=registry.descriptors[b->descriptor];
        if(bd.pool) {
            if(!re4dc_actor_pool_bindings(m,bd.appearance,bd.sections,infos,sec,count))return false;
            for(unsigned i=0;i<count;++i)if(infos[i]!=b->infos[i] || sec[i]!=b->sec[i])return false;
        } else
#endif
        if(!re4dc_actor_role_bindings(m,registry.descriptors[b->descriptor].appearance,infos,count))return false;
        for(unsigned i=0;i<count;++i)if(infos[i]!=b->infos[i])return false;
    } else {
        unsigned found=registry.descriptor_count;
        for(unsigned d=0;d<registry.descriptor_count;++d) {
            const auto& desc=registry.descriptors[d];
#if defined(RE4DC_NMR_LOD) && RE4DC_NMR_LOD
            if(desc.lod_of)continue;  // a gameplay level is chosen from its full descriptor (registry_lod_want)
#endif
#if RE4DC_NMR_POOL
            // A pool descriptor: count <= its sections, every info proving a distinct pool row (body first).
            if(desc.pool) {
                if(desc.model_id!=m->id || count>desc.sections || desc.bones!=m->nParts)continue;
                if(!re4dc_actor_pool_bindings(m,desc.appearance,desc.sections,infos,sec,count))continue;
                if(found!=registry.descriptor_count)return false;
                found=d;continue;
            }
#endif
#if RE4DC_NMR_SLOTS
            if(desc.model_id!=m->id || desc.sections!=count || registry_source_bones(desc)!=m->nParts)continue;
#else
            if(desc.model_id!=m->id || desc.sections!=count || desc.bones!=m->nParts)continue;
#endif
            if(!re4dc_actor_role_bindings(m,desc.appearance,infos,count))continue;
            // Two descriptors proving the same infos would be ambiguous: the generator refuses equal source
            // identities, and role rows bind an info to one TPL owner; refuse here too.
            if(found!=registry.descriptor_count)return false;
            found=d;
        }
        if(found==registry.descriptor_count)return false;
#if defined(RE4DC_NMR_LOD) && RE4DC_NMR_LOD
        found=registry_lod_want(m,found,count);
#endif
        const auto& desc=registry.descriptors[found];
#if RE4DC_NMR_POOL
        if(desc.pool) {
            if(!re4dc_actor_pool_bindings(m,desc.appearance,desc.sections,infos,sec,count))return false;
        } else {
            if(!re4dc_actor_role_bindings(m,desc.appearance,infos,count))return false;
            for(unsigned i=0;i<count;++i)sec[i]=(unsigned char)i;
        }
#else
        if(!re4dc_actor_role_bindings(m,desc.appearance,infos,count))return false;
#endif
        b=&registry_bindings[registry_replace++%16];*b={};
        b->owner=m;b->serial=m->serial;b->list=m->pList;b->root=m->pParts;b->revision=revision;b->descriptor=found;b->count=count;
        for(unsigned i=0;i<count;++i)b->infos[i]=infos[i];
#if RE4DC_NMR_POOL
        for(unsigned i=0;i<count;++i)b->sec[i]=sec[i];
#endif
    }
    NMR_WHY(kRwSkeleton);
    if(!registry_skeleton(m,*b,registry.descriptors[b->descriptor])){b->owner=nullptr;return false;}
    registry_bound=b;NMR_WHY(kRwNone);return true;
}
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
// The palette build's binding: the plan's proof when its token names this transaction, model, slot and generation.
bool registry_bind_tx(cModel* m) {
    const bool reuse=registry_tx.m==m && registry_tx.serial==registry_tx_serial && registry_tx.b==registry_bound &&
        registry_tx.generation==registry.generation && registry_bound && registry_bound->owner==m;
    registry_tx.m=nullptr;  // one use
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
    const RegistryBinding* const was=registry_bound;const bool full=registry_bind(m);
    ++registry_txc.bind;if(reuse){++registry_txc.reused;if(!full || registry_bound!=was)++registry_txc.bind_bad;}
    return full;
#else
    return reuse || registry_bind(m);
#endif
}
#endif
int registry_palettes(cModel* m,const Re4dcActorPlan& p,float* const* output) {
    const auto* desc=registry_descriptor(p.appearance);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    if(!desc || !registry_bind_tx(m) || registry_bound->descriptor!=p.appearance-nmr::appearance_first ||
#else
    if(!desc || !registry_bind(m) || registry_bound->descriptor!=p.appearance-nmr::appearance_first ||
#endif
       !RE4DC_PLAN_SHAPE(&p,desc) || !registry_skin_init(registry_bound->descriptor))return 0;
    for(unsigned i=0;i<p.count;++i)if(p.info[i]!=registry_bound->infos[i] || !output[i])return 0;
#if RE4DC_NMR_POOL
    if(p.count!=registry_bound->count)return 0;
    for(unsigned i=0;i<p.count;++i)if(RE4DC_PLAN_ROLE(&p,i)!=registry_bound->sec[i])return 0;
#endif
    Mtx inv;if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
    const unsigned d=registry_bound->descriptor;
    for(unsigned u=0;u<registry_skin_used[d];++u) {
        const unsigned b=registry_skin_bone[d][u];
#if RE4DC_NMR_SLOTS
        // A draw-slot descriptor's bind run holds one inverse per SOURCE joint: slot b skins with its joint's
        // (source_parents[source_bones + b], the joint registry_skeleton_slots bound to parts[b]).
        const float* bind=desc->source_bones?desc->bind[desc->source_parents[desc->source_bones+b]]:desc->bind[b];
#if defined(RE4DC_ASHLEY_PLAYABLE_PS2_RIG) && RE4DC_ASHLEY_PLAYABLE_PS2_RIG
        // The full source/owner/slot proof above remains required on every bind.
        // Read the existing solver's bind for garment links; never advance it.
        if((const cModel*)pPL==m && m->ot_type==7u &&
           ashley_playable_ps2_rig27::shape(desc->model_id,desc->source_bones,desc->sections) &&
           desc->source_parents[desc->source_bones+b]>=64u)
            bind=&registry_bound->parts[b]->lt_inv_mat[0][0];
#endif
#if defined(RE4DC_ASHLEY_PS2_RIG) && RE4DC_ASHLEY_PS2_RIG
        // PS2 shared bones use the package's PS2 bind. Garments use the existing
        // solver's skin delta; no extra solver call, animation tick or RNG.
        if(ashley_ps2_rig27::applies(desc->model_id,desc->source_bones,desc->sections) &&
           desc->source_parents[desc->source_bones+b]>=64u)
            bind=&registry_bound->parts[b]->lt_inv_mat[0][0];
#endif
        registry_jobs[u]={&registry_bound->parts[b]->mat[0][0],bind,registry_T[b]};
#else
        registry_jobs[u]={&registry_bound->parts[b]->mat[0][0],desc->bind[b],registry_T[b]};
#endif
    }
    re4dc_coarse_skin_bones(invx,registry_jobs,registry_skin_used[d]);
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND
    bool bounded=registry_skin_unit[d]==1;
    for(unsigned u=0;u<registry_skin_used[d] && bounded;++u)bounded=registry_all_bounded(registry_T[registry_skin_bone[d][u]],12);
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
    {
        const RegistrySnap* s=nullptr;
        for(const auto& e:registry_snaps)if(e.m==m && e.serial==unsigned(m->serial) && e.frame==unsigned(pG->Frame_cnt)){s=&e;break;}
        if(!s || s->bones!=desc->bones)++registry_cmp_nosnap;
        else {
            float worst=0.0f;
            for(unsigned b=0;b<desc->bones;++b) {
                Mtx tmp,bind,T;PSMTXConcat(inv,registry_bound->parts[b]->mat,tmp);
                for(unsigned k=0;k<12;++k)(&bind[0][0])[k]=desc->bind[b][k];
                PSMTXConcat(tmp,bind,T);
                for(unsigned k=0;k<12;++k){const float e=__builtin_fabsf((&T[0][0])[k]-s->T[b][k]);if(!(e<=worst))worst=e;}
            }
            ++registry_cmp_models;if(!(worst<=0.5f))++registry_cmp_bad;
            if(!(worst<=registry_cmp_max))registry_cmp_max=worst;
        }
    }
#endif
    for(unsigned i=0;i<p.count;++i) {
        const unsigned g=registry_geometry(desc->first_chunk+RE4DC_PLAN_ROLE(&p,i));
        const auto& c=registry.chunks[desc->first_chunk+RE4DC_PLAN_ROLE(&p,i)];
        if(p.input[i].palette_count!=c.palette_count)return 0;
        re4dc_coarse_skin_groups(registry_skin+registry_skin_first[g],registry_skin_groups[g],
            &registry_T[0][0],output[i],c.palette_count);
#if RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND == 1
        if(!bounded && !registry_all_finite(output[i],c.palette_count*12))return 0;
#elif RE4DC_NATIVE_MODEL_REGISTRY_PALBOUND == 2
        {
            const bool finite=registry_all_finite(output[i],c.palette_count*12);  // the =0 verdict decides
            ++registry_pbc.chunks;if(bounded){++registry_pbc.bounded;if(!finite)++registry_pbc.bad;}else if(finite)++registry_pbc.stricter;
            if(pG->Frame_cnt/600!=registry_pbc.last){registry_pbc.last=pG->Frame_cnt/600;registry_pb_report("periodic");}
            if(!finite)return 0;
        }
#elif RE4DC_NATIVE_MODEL_REGISTRY_TX
        bool finite=registry_all_finite(output[i],c.palette_count*12);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX == 2
        bool full=true;for(unsigned j=0;j<c.palette_count*12;++j)if(!coarse_finite(output[i][j]))full=false;
        ++registry_txc.finite;if(finite!=full)++registry_txc.finite_bad;
        finite=full;
#endif
        if(!finite)return 0;
#else
        for(unsigned j=0;j<c.palette_count*12;++j)if(!coarse_finite(output[i][j]))return 0;
#endif
    }
    return 1;
}
#if RE4DC_NATIVE_MODEL_REGISTRY_CENSUS
// Per actor (census): the first native admission of each model address and its last admitted frame; the source's
// model retire (actor_lifetime.inc re4dc_actor_model_retire, also on destruction) of a tracked address is logged with
// them, so a killed / removed animal can be followed from native draws to the source's removal.
struct RegistryTracked { const cModel* m;unsigned appearance,first,last,frames,declines,why; };
RegistryTracked registry_tracked[32];
unsigned registry_tracked_n,registry_tracked_full;
void registry_note_admit(const cModel* m,unsigned appearance) {
    const unsigned frame=unsigned(pG->Frame_cnt);
    for(unsigned k=0;k<registry_tracked_n;++k)if(registry_tracked[k].m==m && registry_tracked[k].appearance==appearance) {
        auto& t=registry_tracked[k];if(t.last!=frame){t.last=frame;++t.frames;}
        if(t.why){re4dc_log("NMRM readmit t=%u m=%08x appearance=%03x\n",frame,unsigned(uintptr_t(m)),appearance);t.why=0;}
        return;
    }
    if(registry_tracked_n==32){++registry_tracked_full;return;}
    registry_tracked[registry_tracked_n++]={m,appearance,frame,frame,1,0,0};
    re4dc_log("NMRM admit t=%u room=%04x m=%08x id=%02x desc=%s pos=%d,%d,%d gen=%u\n",frame,unsigned(G_ROOM_ID),unsigned(uintptr_t(m)),
        unsigned(m->id),registry.descriptors[appearance-nmr::appearance_first].name,int(m->pos.x),int(m->pos.y),int(m->pos.z),
        registry.generation);
}
void registry_note_retire(const cModel* m,const char* how) {
    for(unsigned k=0;k<registry_tracked_n;++k)if(registry_tracked[k].m==m) {
        const auto t=registry_tracked[k];registry_tracked[k]=registry_tracked[--registry_tracked_n];
        re4dc_log("NMRM %s t=%u m=%08x appearance=%03x admitted_first=%u last=%u frames=%u declines=%u\n",how,unsigned(pG->Frame_cnt),
            unsigned(uintptr_t(m)),t.appearance,t.first,t.last,t.frames,t.declines);
        return;
    }
}
const char* const kRwName[kRwCount]={"none","shape","revision","roles","skeleton","finite","skin","plan","layout","semantics",
    "certificate","acquire"};
void registry_decline(const cModel* m,const Re4dcActorPlan* p,unsigned why) {
    // A tracked (once natively admitted) actor: every change of its decline reason is logged with its frame.
    for(unsigned k=0;k<registry_tracked_n;++k)if(registry_tracked[k].m==m) {
        auto& t=registry_tracked[k];++t.declines;
        if(t.why!=why+1) {
            t.why=why+1;
            re4dc_log("NMRM decline t=%u m=%08x appearance=%03x why=%s (whole source path) last_admitted=%u\n",unsigned(pG->Frame_cnt),
                unsigned(uintptr_t(m)),t.appearance,kRwName[why<kRwCount?why:0],t.last);
        }
        break;
    }
    const auto* desc=p?registry_descriptor(p->appearance):nullptr;
    if(desc) {auto& c=registry_count[desc-registry.descriptors];++c.declined;++c.why[why<kRwCount?why:0];}
    else ++registry_unbound_why[why<kRwCount?why:0];
#if defined(RE4DC_NMR_BIN_DIAG) && RE4DC_NMR_BIN_DIAG
    // NATIVE_MODEL_REGISTRY_BIN_DIAG: a registry actor that fails on its role rows names every source info (once per
    // model, 24 models): NMRBIN lines (archive entry numbers of the BIN / TPL).
    if(why==kRwRoles && m) {
        static const cModel* named[24];static unsigned n_named;bool seen=false;
        for(unsigned k=0;k<n_named;++k)if(named[k]==m)seen=true;
        if(!seen && n_named<24) {named[n_named++]=m;for(auto* i=m->pModelInfo;i;i=i->pList)re4dc_nmr_bin_name(i,unsigned(m->id));}
    }
#endif
}
// Scene census: every model whose first OT pass reaches the transaction, by (id, ot_type, parts, infos) and outcome.
enum SceneClass : unsigned { kScNative,kScCrowd,kScDeclined,kScRegistryDeclined,kScAbsent,kScWould,kScCount };
const char* const kSceneName[kScCount]={"native","crowd-skip","declined","registry-declined","absent","would-native"};
struct SceneRow { unsigned short id,parts;unsigned char ot,infos,plan,pad;unsigned count[kScCount]; };
SceneRow scene_rows[48];
unsigned scene_count,scene_overflow,scene_last_frame;
unsigned short scene_room;
void scene_report(unsigned frame) {
    for(unsigned d=0;d<registry.descriptor_count;++d) {
        const auto& c=registry_count[d];if(!c.planned && !c.declined)continue;
        re4dc_log("NMRD f=%u %s planned=%u admitted=%u would=%u declined=%u roles=%u skeleton=%u layout=%u semantics=%u certificate=%u acquire=%u skin=%u plan=%u bind_rot_e6=%d bind_mm_e4=%d pos=%d,%d,%d\n",
            frame,registry.descriptors[d].name,c.planned,c.admitted,c.would,c.declined,c.why[kRwRoles],c.why[kRwSkeleton],c.why[kRwLayout],
            c.why[kRwSemantics],c.why[kRwCertificate],c.why[kRwAcquire],c.why[kRwSkin],c.why[kRwPlan],int(c.bind_rotation*1e6f),int(c.bind_translation*1e4f),
            int(c.pos[0]),int(c.pos[1]),int(c.pos[2]));
    }
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
    re4dc_log("NMRC f=%u palette_check models=%u over_0.5=%u no_snapshot=%u max_abs_e4=%d\n",frame,registry_cmp_models,
        registry_cmp_bad,registry_cmp_nosnap,int(registry_cmp_max*1e4f));
#endif
    for(unsigned k=0;k<registry_tracked_n;++k) {
        const auto& t=registry_tracked[k];
        re4dc_log("NMRM live f=%u t=%u m=%08x appearance=%03x admitted_first=%u last=%u frames=%u declines=%u\n",frame,
            unsigned(pG->Frame_cnt),unsigned(uintptr_t(t.m)),t.appearance,t.first,t.last,t.frames,t.declines);
    }
    if(registry_tracked_full)re4dc_log("NMRM f=%u untracked=%u\n",frame,registry_tracked_full);
    re4dc_log("NMRU f=%u shape=%u revision=%u roles=%u skeleton=%u finite=%u\n",frame,registry_unbound_why[kRwShape],
        registry_unbound_why[kRwRevision],registry_unbound_why[kRwRoles],registry_unbound_why[kRwSkeleton],registry_unbound_why[kRwFinite]);
    re4dc_log("NMRU2 f=%u none=%u skin=%u plan=%u layout=%u semantics=%u certificate=%u acquire=%u\n",frame,registry_unbound_why[0],
        registry_unbound_why[kRwSkin],registry_unbound_why[kRwPlan],registry_unbound_why[kRwLayout],registry_unbound_why[kRwSemantics],
        registry_unbound_why[kRwCertificate],registry_unbound_why[kRwAcquire]);
    for(unsigned k=0;k<scene_count;++k) {
        const auto& r=scene_rows[k];
        re4dc_log("NMRS f=%u room=%04x id=%02x ot=%u parts=%u infos=%u plan=%c native=%u crowd=%u declined=%u registry_declined=%u absent=%u would=%u\n",
            frame,scene_room,r.id,r.ot,r.parts,r.infos,"-LGR"[r.plan&3],r.count[kScNative],r.count[kScCrowd],r.count[kScDeclined],
            r.count[kScRegistryDeclined],r.count[kScAbsent],r.count[kScWould]);
    }
    if(scene_overflow)re4dc_log("NMRS f=%u overflow=%u\n",frame,scene_overflow);
}
// plan: 0 none, 1 Leon, 2 Ganado, 3 registry
void scene_note(cModel* m,unsigned plan,unsigned cls) {
    const unsigned frame=re4dc_ui_frame();
    const unsigned short room=(unsigned short)G_ROOM_ID;
#ifndef RE4DC_NMR_CENSUS_PERIOD
#define RE4DC_NMR_CENSUS_PERIOD 600  // NATIVE_MODEL_REGISTRY_CENSUS_PERIOD (native_model_registry.mk)
#endif
    if(room!=scene_room || frame-scene_last_frame>=RE4DC_NMR_CENSUS_PERIOD) {
        // One report per 600 UI frames (by default) and at every room change (the rows are per room).
        if(scene_count)scene_report(frame);
        if(room!=scene_room){scene_count=0;scene_overflow=0;scene_room=room;}
        scene_last_frame=frame;
    }
    unsigned infos=0;for(auto* i=m->pModelInfo;i && infos<255;i=i->pList)++infos;
    SceneRow* row=nullptr;
    for(unsigned k=0;k<scene_count;++k) {
        auto& r=scene_rows[k];
        if(r.id==m->id && r.ot==m->ot_type && r.parts==m->nParts && r.infos==infos && r.plan==plan){row=&r;break;}
    }
    if(!row) {
        if(scene_count==sizeof(scene_rows)/sizeof(scene_rows[0])){++scene_overflow;return;}
        row=&scene_rows[scene_count++];*row={};row->id=(unsigned short)m->id;row->ot=(unsigned char)m->ot_type;
        row->parts=(unsigned short)m->nParts;row->infos=(unsigned char)infos;row->plan=(unsigned char)plan;
    }
    ++row->count[cls<kScCount?cls:kScAbsent];
}
#endif
}
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
extern "C" void re4dc_registry_snapshot(cModel* m,const Mtx* palette) {
    if(!m || !registry_id(m->id) || !m->nParts || m->nParts>kRegBones)return;
    auto& s=registry_snaps[registry_snap_next++%16];
    s.m=m;s.serial=unsigned(m->serial);s.frame=unsigned(pG->Frame_cnt);s.bones=m->nParts;
    for(unsigned b=0;b<s.bones;++b)for(unsigned k=0;k<12;++k)s.T[b][k]=(&palette[b][0][0])[k];
    // One exact sample for host attribution (skinning the source BIN and the pack chunk with the same palette):
    // every registry actor's source palette at the first skinned game frame >= 600 (a paced build may skip 600's
    // Trans), as raw float bits.
    static unsigned dump_frame;
    if(!dump_frame && s.frame>=600)dump_frame=s.frame;
    if(s.frame==dump_frame) {
        re4dc_log("NMRP f=%u m=%08x id=%02x serial=%u pos=%d,%d,%d bones=%u\n",s.frame,unsigned(uintptr_t(m)),unsigned(m->id),s.serial,
            int(m->pos.x),int(m->pos.y),int(m->pos.z),s.bones);
        for(unsigned b=0;b<s.bones;++b) {
            unsigned u[12];__builtin_memcpy(u,s.T[b],sizeof(u));
            re4dc_log("NMRP m=%08x b=%u %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x %08x\n",unsigned(uintptr_t(m)),b,
                u[0],u[1],u[2],u[3],u[4],u[5],u[6],u[7],u[8],u[9],u[10],u[11]);
        }
    }
}
#endif
extern "C" int re4dc_actor_plan_registry(cModel* m,Re4dcActorPlan* out) {
    if(!out || !registry_bind(m)) {
        NMR_CENSUS(if(m && registry_id(m->id))registry_decline(m,nullptr,registry_why));
        return 0;
    }
    const unsigned d=registry_bound->descriptor;const auto& desc=registry.descriptors[d];
    if(!registry_skin_init(d)){NMR_CENSUS(registry_decline(m,nullptr,kRwSkin));return 0;}
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    // Built in the transaction's plan: no second zeroed plan and no whole-plan copy (a declined plan is not used).
    Re4dcActorPlan& p=*out;p=Re4dcActorPlan{};
#else
    Re4dcActorPlan p{};
#endif
#if RE4DC_NMR_POOL
    if(desc.pool) {
        p.pool=1;p.count=registry_bound->count;
        for(unsigned i=0;i<p.count;++i)p.section[i]=registry_bound->sec[i];
    } else p.count=desc.sections;
    p.appearance=desc.appearance;p.palettes=registry_palettes;
    for(unsigned i=0;i<p.count;++i) {
#else
    p.count=desc.sections;p.appearance=desc.appearance;p.palettes=registry_palettes;
    for(unsigned i=0;i<desc.sections;++i) {
#endif
        const auto& c=registry.chunks[desc.first_chunk+RE4DC_PLAN_ROLE(&p,i)];
        const re4dc_source::ChunkInput input{{c.positions,c.position_count*8u},{c.normals,c.normal_count*8u},{c.uv,c.uv_bytes},
            {c.stream,c.stream_bytes},{reinterpret_cast<const unsigned char*>(c.weights),c.palette_count*16u},
            c.position_count,c.normal_count,c.palette_count,c.triangles,desc.bones};
        re4dc_actor::plan_chunk(p,i,registry_bound->infos[i],c,input);
        p.immutable_asset_id[i]=kRegistryAsset0+registry_geometry(desc.first_chunk+RE4DC_PLAN_ROLE(&p,i));
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
        // The covered face keeps its input/palette/identity and lifetime proof;
        // the source-qualified head emits their merged geometry once.
        if(c.draw_owner!=RE4DC_PLAN_ROLE(&p,i))continue;
#endif
#if (RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK) || RE4DC_NMR_POOL
#if RE4DC_NMR_MASK
        // A mask-only section (the pack check admits it for the Luis face and, under NATIVE_MODEL_REGISTRY_POOL, for a
        // pool section whose every triangle is a masked card): its pair run alone.
        if(c.mask_geometry[0]==~0u && c.mask_geometry[1]!=~0u) {
            if(p.run_count==kRe4dcActorRuns || p.material_count==kRe4dcActorMaterials){NMR_CENSUS(registry_decline(m,&p,kRwPlan));return 0;}
            const nmr::Chunk gh=registry_gview(c.mask_geometry[1]);
            auto& mh=p.materials[p.material_count];
            mh.image=registry_image(c.mask_texture[0]);mh.mask=registry_mask_image(c.mask_texture[1]);
            mh.crc=c.pair_crc;mh.fnv=c.pair_fnv;
            mh.material_flags=4;mh.blend=0;mh.depth_mode=1;mh.mask_ref=0;mh.mask_same_uv=1;mh.wrap_s=mh.wrap_t=1;
            auto& rh=p.runs[p.run_count++];rh.role=i;rh.material=p.material_count++;rh.immutable_asset_id=kRegistryAsset0+c.mask_geometry[1];
            rh.triangles=gh.triangles;rh.uv={gh.uv,gh.uv_bytes};rh.stream={gh.stream,gh.stream_bytes};
            continue;
        }
#endif
#endif
        // Materials: each chunk's own texture package, shared when chunks name the same package.
        unsigned mat=0;
        while(mat<p.material_count && p.materials[mat].image.pixels!=&registry_tokens[c.texture])++mat;
        if(mat==p.material_count) {
            if(p.material_count==kRe4dcActorMaterials){NMR_CENSUS(registry_decline(m,&p,kRwPlan));return 0;}
            auto& m0=p.materials[p.material_count++];m0.image=registry_image(c.texture);
            m0.crc=registry.textures[c.texture].crc;m0.fnv=registry.textures[c.texture].fnv;
        }
#if RE4DC_NMR_MASK
        if(c.mask_geometry[0]!=~0u) {
            // Two runs over this role's chunk (its positions / normals / palettes): the opaque triangles with the chunk
            // texture, then the alpha-masked ones with the colour + mask pair (the source's mask pass: TR, blended,
            // no depth write, as the Leon hair's native-look material).
            const nmr::Chunk go=registry_gview(c.mask_geometry[0]),gh=registry_gview(c.mask_geometry[1]);
            if(p.run_count+2>kRe4dcActorRuns || p.material_count==kRe4dcActorMaterials){NMR_CENSUS(registry_decline(m,&p,kRwPlan));return 0;}
            auto& ro=p.runs[p.run_count++];ro.role=i;ro.material=mat;ro.immutable_asset_id=kRegistryAsset0+c.mask_geometry[0];
            ro.triangles=go.triangles;ro.uv={go.uv,go.uv_bytes};ro.stream={go.stream,go.stream_bytes};
            auto& mh=p.materials[p.material_count];
            mh.image=registry_image(c.mask_texture[0]);mh.mask=registry_mask_image(c.mask_texture[1]);
            mh.crc=c.pair_crc;mh.fnv=c.pair_fnv;
            mh.material_flags=4;mh.blend=0;mh.depth_mode=1;mh.mask_ref=0;mh.mask_same_uv=1;mh.wrap_s=mh.wrap_t=1;
            auto& rh=p.runs[p.run_count++];rh.role=i;rh.material=p.material_count++;rh.immutable_asset_id=kRegistryAsset0+c.mask_geometry[1];
            rh.triangles=gh.triangles;rh.uv={gh.uv,gh.uv_bytes};rh.stream={gh.stream,gh.stream_bytes};
            continue;
        }
#endif
        auto& run=p.runs[p.run_count++];run.role=i;run.material=mat;run.immutable_asset_id=p.immutable_asset_id[i];
        run.triangles=c.triangles;run.uv=input.uv;run.stream=input.stream;
    }
    p.image=p.materials[0].image;p.crc=p.materials[0].crc;p.fnv=p.materials[0].fnv;
    NMR_CENSUS(++registry_count[d].planned;registry_count[d].pos[0]=m->pos.x;registry_count[d].pos[1]=m->pos.y;
        registry_count[d].pos[2]=m->pos.z);
#if RE4DC_NATIVE_MODEL_REGISTRY_TX
    registry_tx={registry_tx_serial,registry.generation,m,registry_bound};
    return 1;
#else
    *out=p;return 1;
#endif
}
// The certificate's registry branch: every run draws its chunk's own descriptor texture (coarse_actor_material.inc).
#if RE4DC_NMR_MASK
namespace {
bool registry_plain_material(const Re4dcActorOwnedMaterial& m,unsigned t) {
    const auto& x=registry.textures[t];
    return m.image.pixels==&registry_tokens[t] && m.crc==x.crc && m.fnv==x.fnv && m.image.width==x.width && m.image.height==x.height &&
        m.image.format==6 && !m.image.palette && !m.image.palette_bytes && !m.mask.pixels && !m.material_flags && !m.blend &&
        !m.depth_mode && m.mask_ref==256 && !m.wrap_s && !m.wrap_t;
}
bool registry_run_is(const Re4dcActorPlannedRun& r,unsigned role,unsigned g) {
    const nmr::Chunk v=registry_gview(g);
    return r.role==role && r.immutable_asset_id==kRegistryAsset0+g && r.triangles==v.triangles && r.stream.data==v.stream &&
        r.stream.size==v.stream_bytes && r.uv.data==v.uv && r.uv.size==v.uv_bytes;
}
}
// NATIVE_MODEL_REGISTRY_MASK: the registry branch with masked sections (opaque run + pair run per such section).
extern "C" int re4dc_registry_runs_match(const Re4dcActorPlan* p) {
    const auto* desc=p?registry_descriptor(p->appearance):nullptr;
    if(!desc || !RE4DC_PLAN_SHAPE(p,desc) || !p->material_count || p->material_count>kRe4dcActorMaterials)return 0;
    unsigned seen=0,j=0;
    for(unsigned i=0;i<RE4DC_PLAN_SECTIONS(p,desc);++i) {
        const auto& c=registry.chunks[desc->first_chunk+RE4DC_PLAN_ROLE(p,i)];
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
        if(c.draw_owner!=RE4DC_PLAN_ROLE(p,i))continue;
#endif
#if (RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK) || RE4DC_NMR_POOL
        if(c.mask_geometry[0]==~0u && c.mask_geometry[1]!=~0u) {
            if(j>=p->run_count)return 0;
            const auto& h=p->runs[j];
            if(!registry_run_is(h,i,c.mask_geometry[1]) || h.material>=p->material_count)return 0;
            const auto& m=p->materials[h.material];const auto& ct=registry.textures[c.mask_texture[0]];const auto& mt=registry.textures[c.mask_texture[1]];
            if(m.image.pixels!=&registry_tokens[c.mask_texture[0]] || m.image.width!=ct.width || m.image.height!=ct.height || m.image.format!=6 ||
               m.image.palette || m.image.palette_bytes || m.mask.pixels!=&registry_tokens[c.mask_texture[1]] || m.mask.width!=mt.width ||
               m.mask.height!=mt.height || m.mask.format!=0 || m.crc!=c.pair_crc || m.fnv!=c.pair_fnv || m.material_flags!=4 || m.blend ||
               m.depth_mode!=1 || m.mask_ref || m.mask_same_uv!=1 || m.wrap_s!=1 || m.wrap_t!=1)return 0;
            seen|=1u<<h.material;++j;continue;
        }
#endif
        if(j>=p->run_count)return 0;
        const auto& r=p->runs[j];
        if(r.material>=p->material_count || !registry_plain_material(p->materials[r.material],c.texture))return 0;
        seen|=1u<<r.material;
        if(c.mask_geometry[0]==~0u) {
            if(r.role!=i || r.immutable_asset_id!=kRegistryAsset0+registry_geometry(desc->first_chunk+RE4DC_PLAN_ROLE(p,i)) || r.triangles!=c.triangles ||
               r.stream.data!=c.stream || r.uv.data!=c.uv)return 0;
            ++j;continue;
        }
        if(!registry_run_is(r,i,c.mask_geometry[0]) || j+1>=p->run_count)return 0;
        const auto& h=p->runs[j+1];
        if(!registry_run_is(h,i,c.mask_geometry[1]) || h.material>=p->material_count)return 0;
        const auto& m=p->materials[h.material];const auto& ct=registry.textures[c.mask_texture[0]];const auto& mt=registry.textures[c.mask_texture[1]];
        if(m.image.pixels!=&registry_tokens[c.mask_texture[0]] || m.image.width!=ct.width || m.image.height!=ct.height || m.image.format!=6 ||
           m.image.palette || m.image.palette_bytes || m.mask.pixels!=&registry_tokens[c.mask_texture[1]] || m.mask.width!=mt.width ||
           m.mask.height!=mt.height || m.mask.format!=0 || m.crc!=c.pair_crc || m.fnv!=c.pair_fnv || m.material_flags!=4 || m.blend ||
           m.depth_mode!=1 || m.mask_ref || m.mask_same_uv!=1 || m.wrap_s!=1 || m.wrap_t!=1)return 0;
        seen|=1u<<h.material;j+=2;
    }
    return j==p->run_count && seen==(1u<<p->material_count)-1u;
}
// The certificate's mask capability: a registry plan whose every masked source section draws its pair run.
extern "C" int re4dc_registry_masked(const Re4dcActorPlan* p) {
    const auto* desc=p?registry_descriptor(p->appearance):nullptr;
    if(!desc)return 0;
#if RE4DC_NMR_POOL
    if(!RE4DC_PLAN_SHAPE(p,desc))return 0;
#endif
#if (RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK) || RE4DC_NMR_POOL
    for(unsigned i=0;i<RE4DC_PLAN_SECTIONS(p,desc);++i)if(registry.chunks[desc->first_chunk+RE4DC_PLAN_ROLE(p,i)].mask_geometry[1]!=~0u)return 1;
#else
    for(unsigned i=0;i<RE4DC_PLAN_SECTIONS(p,desc);++i)if(registry.chunks[desc->first_chunk+RE4DC_PLAN_ROLE(p,i)].mask_geometry[0]!=~0u)return 1;
#endif
    return 0;
}
#else
extern "C" int re4dc_registry_runs_match(const Re4dcActorPlan* p) {
    const auto* desc=p?registry_descriptor(p->appearance):nullptr;
    if(!desc || !RE4DC_PLAN_SHAPE(p,desc) || p->run_count!=RE4DC_PLAN_SECTIONS(p,desc) || !p->material_count || p->material_count>kRe4dcActorMaterials)return 0;
    unsigned seen=0;
    for(unsigned j=0;j<p->run_count;++j) {
        const auto& r=p->runs[j];const auto& c=registry.chunks[desc->first_chunk+RE4DC_PLAN_ROLE(p,j)];
        if(r.role!=j || r.material>=p->material_count || r.immutable_asset_id!=kRegistryAsset0+registry_geometry(desc->first_chunk+RE4DC_PLAN_ROLE(p,j)) ||
           r.triangles!=c.triangles || r.stream.data!=c.stream || r.uv.data!=c.uv)return 0;
        const auto& m=p->materials[r.material];
        const auto& t=registry.textures[c.texture];
        if(m.image.pixels!=&registry_tokens[c.texture] || m.crc!=t.crc || m.fnv!=t.fnv ||
           m.image.width!=t.width || m.image.height!=t.height || m.image.format!=6 ||
           m.image.palette || m.image.palette_bytes || m.mask.pixels || m.material_flags || m.blend || m.depth_mode ||
           m.mask_ref!=256 || m.wrap_s || m.wrap_t)return 0;
        seen|=1u<<r.material;
    }
    return seen==(1u<<p->material_count)-1u;
}
#endif
#if RE4DC_ROUTE_CH22 && RE4DC_NATIVE_MODEL_REGISTRY_PACK
// A covered source role has no independent draw, but retains its distinct
// source BIN/TPL, immutable input, palette and lifetime/material certificate.
// Only the pack validator's complete pinned Luis descriptor can nominate it.
extern "C" int re4dc_registry_covered_roles(const cModel* m,const Re4dcActorPlan* p,unsigned* covered) {
    if(!covered || !p)return 0;
    *covered=0;
    const auto* desc=registry_descriptor(p->appearance);
    if(!desc)return 1;  // Leon and the ordinary Ganado plans have no covered roles.
#if RE4DC_NMR_SLOTS
    if(!m || !RE4DC_PLAN_SHAPE(p,desc) || m->id!=desc->model_id || m->nParts!=registry_source_bones(*desc))return 0;
#else
    if(!m || !RE4DC_PLAN_SHAPE(p,desc) || m->id!=desc->model_id || m->nParts!=desc->bones)return 0;
#endif
#if RE4DC_NMR_POOL
    if(desc->pool)return 1;  // pool sections are never covered (the package check admits covered roles for Luis only)
#endif
    for(unsigned i=0;i<desc->sections;++i) {
        const auto& c=registry.chunks[desc->first_chunk+i];
        if(c.draw_owner==i)continue;
        if(desc->model_id!=4u || desc->bones!=90u || desc->sections!=6u || i!=2u || c.draw_owner!=1u)return 0;
        const auto& owner=registry.chunks[desc->first_chunk+1u];
        if(owner.draw_owner!=1u || c.geometry!=owner.geometry || c.texture!=owner.texture ||
           p->immutable_asset_id[i]!=p->immutable_asset_id[1])return 0;
        const auto& a=p->input[i];const auto& b=p->input[1];
        if(a.positions.data!=b.positions.data || a.positions.size!=b.positions.size ||
           a.normals.data!=b.normals.data || a.normals.size!=b.normals.size ||
           a.uv.data!=b.uv.data || a.uv.size!=b.uv.size || a.stream.data!=b.stream.data || a.stream.size!=b.stream.size ||
           a.weights.data!=b.weights.data || a.weights.size!=b.weights.size ||
           a.position_count!=b.position_count || a.normal_count!=b.normal_count || a.palette_count!=b.palette_count ||
           a.triangles!=b.triangles || a.bones!=b.bones)return 0;
        const auto* info=p->info[i];const auto* head=p->info[1];
        if(!info || !head || info==head || info->be_flag!=head->be_flag || std::memcmp(info->mat,head->mat,sizeof(info->mat)))return 0;
        *covered|=1u<<i;
    }
    return 1;
}
#endif
#if RE4DC_ROUTE_CH22 || RE4DC_ROUTE_CH23 || RE4DC_NMR_MERCHANT
// em18_R0_Init sets 0x20 on its robe (BIN0xE/TPL0xF), and
// em18ClothPartsSet sets it on the closed/open coat (BIN0xC/0xB, TPL0xF).
// This nominates the exact certified role; info() still requires white color,
// no modifiers and exact visibility/pass bits, and source lighting checks it.
extern "C" int re4dc_registry_merchant_robe(unsigned appearance,unsigned role,unsigned bin,unsigned tpl) {
    const auto* desc=registry_descriptor(appearance);
    return desc && desc->model_id==0x18u && desc->bones==61u && desc->sections==7u &&
        tpl==0xFu && ((role==1u && bin==0xEu) ||
                     (role==5u && (bin==0xBu || bin==0xCu)));
}
#endif
#if RE4DC_NMR_CH1CAST
// PS2_CAST_CH1: the r106 bats (em29, model 0x29) are ot_type 1 (ModelTrans: OT 0x11, AddOtWorldPosRadius, the same
// ModelRender callback as ot_type 0 in a later group); the owner path draws inside that callback, so the order is kept.
#define RE4DC_REGISTRY_OT_BASE(m,desc) (!(m)->ot_type || ((m)->ot_type==1 && (desc)->model_id==0x29u))
#else
#define RE4DC_REGISTRY_OT_BASE(m,desc) (!(m)->ot_type)
#endif
#if defined(RE4DC_NMR_OT5) && RE4DC_NMR_OT5
// NATIVE_MODEL_REGISTRY_OT5: the Verdugo (em2c, model 0x2c) is ot_type 5 (ModelTrans: AddOtDirect(0x10, ModelRender,
// 0, 2), one source call per frame); the owner path draws inside that callback, so the order is kept.
#define RE4DC_REGISTRY_OT_OK(m,desc) (RE4DC_REGISTRY_OT_BASE(m,desc) || ((m)->ot_type==5 && (desc)->model_id==0x2cu))
#else
#define RE4DC_REGISTRY_OT_OK(m,desc) RE4DC_REGISTRY_OT_BASE(m,desc)
#endif
extern "C" int re4dc_registry_model(const cModel* m,const Re4dcActorPlan* p) {
    const auto* desc=p?registry_descriptor(p->appearance):nullptr;
#if RE4DC_NMR_SLOTS
    bool player_ot=false;
#if RE4DC_NMR_ASHLEY >= 2 && defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
    // cPlAshley uses the source OT7 callback (including its skirt second pass).
    // Leon's model0/119-joint owner and unrelated OT7 models cannot qualify.
    player_ot=desc && m && (const cModel*)pPL==m && m->ot_type==7u &&
        desc->model_id==0u && desc->source_bones==141u && desc->sections==7u;
#endif
    return desc && m && m->id==desc->model_id && m->nParts==registry_source_bones(*desc) && RE4DC_PLAN_SHAPE(p,desc) && (RE4DC_REGISTRY_OT_OK(m,desc) || player_ot);
#else
    return desc && m && m->id==desc->model_id && m->nParts==desc->bones && RE4DC_PLAN_SHAPE(p,desc) && RE4DC_REGISTRY_OT_OK(m,desc);
#endif
}
// The entry gate (source_actor_owner_hooks.inc, re4dc_actor_transaction_candidate): a model id with a validated
// runtime descriptor (contract entries such as the crow have none) leaves the FRONT_NATIVE fast return so its OT
// callbacks reach commonModelTrans and the transaction. Id and part count only nominate (another model class can
// share an id: r103 has a 4-part id 0x21 model besides the 32-bone dog); admission is the proofs above.
#if defined(RE4DC_NMR_NO_GC_FRONT) && RE4DC_NMR_NO_GC_FRONT
// NATIVE_MODEL_REGISTRY_NO_GC_FRONT (native_model_registry.mk): 1 while a registry binding owns this model (same address
// and serial), i.e. the registry drew it on an earlier frame; trans.cpp then never draws it through frontNativeRender.
extern "C" int re4dc_registry_owned(const cModel* m) {
    if(!m || !registry_id(m->id))return 0;
    for(const auto& e:registry_bindings)if(e.owner==m && e.serial==m->serial)return 1;
    return 0;
}
#endif
extern "C" int re4dc_registry_candidate(const cModel* m) {
    if(!registry_id(m->id))return 0;
    for(unsigned d=0;d<registry.descriptor_count;++d)
#if RE4DC_NMR_SLOTS
        if(registry.descriptors[d].model_id==m->id && registry_source_bones(registry.descriptors[d])==m->nParts)return 1;
#else
        if(registry.descriptors[d].model_id==m->id && registry.descriptors[d].bones==m->nParts)return 1;
#endif
    return 0;
}
#if RE4DC_NMR_ASHLEY >= 2
// PS2_ASHLEY=2 (user look decision pending): Ashley's head info carries the GC shape (morph) data (ModInfoMgr.create
// sets be_flag 2 when shapeOfs != 0; cSubAshley::setFace blends shapes 0x6C / 0x6D on it). The PS2 head has no shapes,
// so the owner path draws it at its rest face: expressions are not shown. Only the validated draw-slot descriptor of
// model 3 with seven sections nominates its role 1 (BIN 7, the subShape head). =1 keeps the source path for her.
extern "C" int re4dc_registry_ashley_face(unsigned appearance,unsigned role) {
    const auto* desc=registry_descriptor(appearance);
    return desc && desc->model_id==3u && desc->source_bones && desc->sections==7u && role==1u;
}
#if defined(RE4DC_NMR_PL_ASHLEY) && RE4DC_NMR_PL_ASHLEY
// NATIVE_MODEL_REGISTRY_PL_ASHLEY (native_model_registry.mk): playable Ashley (chapter 3-4; cPlAshley, the player pPL,
// model id 0, ot_type 7) by a draw-slot descriptor of model 0 over her complete 141-joint source owner, with the seven
// sections of cPlAshley::setModel + setRightHand / setLeftHand in its info order: body 4/5, face 7/9 (Body->pShape,
// be_flag 2), hair 6/B, skirt 8/5 (be_flag 0x40: the ot_type 7 second pass, coarse_actor_transaction.inc), extra A/5,
// right hand, left hand. Leon (model 0, 119 joints, his own owner) never matches. 1 = the face, 2 = the skirt, 0 = other.
inline const nmr::Descriptor* registry_player_ashley(unsigned appearance) {
    const auto* desc=registry_descriptor(appearance);
    return desc && desc->model_id==0u && desc->source_bones==141u && desc->sections==7u?desc:nullptr;
}
extern "C" int re4dc_registry_player_ashley_role(unsigned appearance,unsigned role,unsigned bin,unsigned tpl) {
    if(!registry_player_ashley(appearance))return 0;
    if(role==1u && bin==7u && tpl==9u)return 1;
    if(role==3u && bin==8u && tpl==5u)return 2;
    return 0;
}
// The transaction's shape-role test (it has no archive ordinals; the certificate proved them per role first).
extern "C" int re4dc_registry_player_ashley_face(unsigned appearance,unsigned role) {
    return registry_player_ashley(appearance) && role==1u;
}
#endif
#endif
extern "C" unsigned re4dc_registry_sections(unsigned appearance) {
    const auto* desc=registry_descriptor(appearance);return desc?desc->sections:0;
}
extern "C" int re4dc_registry_texture_key(const Re4dcUiImage* i,unsigned* c,unsigned* f) {
#if RE4DC_NMR_MASK
    // A pair's I4 mask image (format 0) keys like the colour image: model_mask_key hashes the two keys into the pair's.
    if(!i || (i->format!=6 && i->format!=0) || i->palette_bytes)return 0;
#else
    if(!i || i->format!=6 || i->palette_bytes)return 0;
#endif
    for(unsigned t=0;t<registry.texture_count;++t) {
        if(i->pixels!=&registry_tokens[t] || i->width!=registry.textures[t].width || i->height!=registry.textures[t].height)continue;
        *c=registry.textures[t].crc;*f=registry.textures[t].fnv;return 1;
    }
    return 0;
}
