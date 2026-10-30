#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
#include "include/actor_format32_uv.hpp"
extern "C" void re4dc_log(const char*, ...);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "include/draw_fallback_audit.h"
#define DFA26_MODEL_HIT(reason, n) ::re4dc::dfa26::hit(::re4dc::dfa26::reason, (n));
#define DFA26_MODEL_SLOW(reason, n, ...) { DFA26_MODEL_HIT(reason, n) __VA_ARGS__ }
#else
#define DFA26_MODEL_HIT(reason, n)
#define DFA26_MODEL_SLOW(reason, n, ...) __VA_ARGS__
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "include/fallback_audit29.h"
#include "include/fallback_actor_audit29.hpp"
#endif
#include "include/gc_asset_motion_unknown.h"
#include "include/gc_asset_actor.h"
// D367 actors30: meshlet actor path (NATIVE_ACTOR=1 NATIVE_ACTOR_FAST=1).
//
// Same contract as native_actor.cpp (the source selects, animates, lights and
// orders every draw; this file only changes the render representation), with
// a representation built for the SH4 instead of per-corner GX decoding:
//
//  1. Conversion, once per part, in place. The part's GX display list (read
//     only by renderers: GXCallDisplayList is a no-op stub, and the native
//     generic/static walkers reject unknown opcodes) is rewritten into a
//     smaller native blob: <=128-vertex meshlets of unique (position, normal,
//     uv, colour) index tuples, sorted by skinning palette entry, plus u8
//     strip indices (bit 7 = end of strip). Winding and the triangle set are
//     the GX list's; opaque strips are grouped by shared tuples (translucent
//     parts keep GX order). A blob that would not fit in place is built as a
//     per-submit transient instead; if that fails too, the part declines.
//  2. Per frame per meshlet: every tuple is transformed once (ftrv through
//     screen x modelview [x palette entry] x dequantisation, fsrra 1/w) and
//     lit once (per-object directional light set, fipr dots, colour matrix by
//     ftrv) into a 32-byte PVR vertex in a 4 KiB cache; strips are then
//     copied into the packet (or store queues, NATIVE_ACTOR_DIRECT) by index.
//     Meshlets/strips wholly outside one screen edge or the near/far plane
//     are skipped; a meshlet with no vertex outside is emitted whole; strips
//     crossing near take the existing clipper per triangle (near only).
//  3. NATIVE_ACTOR_SKIN: for infos whose source CalcSk1_x pass was skipped
//     (trans.cpp keeps the source-built weight palette in the primitive
//     buffer), positions/normals are skinned here from vtxOrig/nrmOrig with
//     that palette. Anything that needs pPosBuf/pNrmBuf (the generic path)
//     first materializes them with the source's own CalcSk1_x.
#include "include/bfc_class.h"
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
extern "C" unsigned re4dc_backface_model_tag(const void* model);
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
#include "../../room/backface_sh4.hpp"  // CPU_BACKFACE=2: common SH-4 SQ ABI
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
extern "C" unsigned char re4dc_bf_room_on;  // native_static.cpp (BACKFACE_ROOMS)
#endif
#elif defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
#include "../../room/backface_emit.hpp"  // CPU_BACKFACE=1: unchanged C reference
#endif
#include "re4dc_screen.h"
#include "native_actor.hpp"
#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29
#include "include/fallback_scan29.hpp"
#endif
#ifndef RE4DC_ACTOR_LIGHT_FAST_ONLY
#define RE4DC_ACTOR_LIGHT_FAST_ONLY 0
#endif
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
#include "include/actor_light_fast_only.h"
#endif
#ifndef RE4DC_ACTOR_CLIP_FRONT26
#define RE4DC_ACTOR_CLIP_FRONT26 0
#endif
#if RE4DC_ACTOR_CLIP_FRONT26
#include "include/actor_clip_front26.hpp"
#endif
#ifndef RE4DC_ACTOR_CLIP_REUSE
#define RE4DC_ACTOR_CLIP_REUSE 0
#endif
#if RE4DC_ACTOR_CLIP_REUSE
#include "include/actor_clip_reuse.hpp"
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
#include "include/draw_setup_audit.h"
extern "C" unsigned re4dc_dsa24_model_translucent(const Re4dcModelPart*);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
extern "C" unsigned re4dc_dsa28_model_class(const Re4dcModelPart*);
#endif
#endif
// ACTOR_BACKFACE_CONE (backface.mk, lane backface-cone23; render only; default 0: no code). For the models
// coarse_actor_transaction.inc marks (Leon, Ganados, El Gigante, Ashley: re4dc_abc_mark), the converter splits each
// opaque part's strips by (palette entry, facing) before clustering, so a meshlet's triangles share one skinning matrix
// and face one way; after conversion each meshlet gets a normal cone in that matrix's input space (abc_build, stored
// in the stream's unused tail). At draw a meshlet whose every triangle faces the side the part's cull removes is
// skipped before its transform, lighting and store-queue writes; every other meshlet draws unchanged.
// =2 (check build): rejected meshlets are transformed anyway and every triangle is checked with the TA's screen-area
// rule (room/backface_emit.hpp); "bad" counts triangles a rejected meshlet would have drawn (must stay 0).
#ifndef RE4DC_ACTOR_BACKFACE_CONE
#define RE4DC_ACTOR_BACKFACE_CONE 0
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
#include "include/actor_cone32.hpp"
#endif
#if RE4DC_ACTOR_BACKFACE_CONE
extern "C" void re4dc_log(const char* fmt, ...);
// The models the split applies to, marked by coarse_actor_transaction.inc (model -> class 1 Leon, 2 Ganado,
// 3 El Gigante, 4 Ashley); a part is split when it is converted while its model is marked.
namespace { struct AbcMark { const void* model; unsigned cls; }; AbcMark abc_marks[64]; unsigned abc_mark_next = 0; }
unsigned abc_unsplit = 0, abc_rec_split = 0, abc_rec_plain = 0, abc_ml_split = 0, abc_ml_plain = 0;
unsigned abc_nmarks = 0, abc_conv = 0, abc_conv_op = 0, abc_conv_mk = 0, abc_part_calls = 0, abc_part_cull = 0;
extern "C" void re4dc_abc_mark(const void* model, unsigned cls) {
    ++abc_nmarks;
    for (AbcMark& m : abc_marks) if (m.model == model) { m.cls = cls; return; }
    abc_marks[abc_mark_next] = {model, cls}; abc_mark_next = (abc_mark_next + 1U) & 63U;
}
static unsigned abc_class_of(const void* model) {
    if (model) for (const AbcMark& m : abc_marks) if (m.model == model) return m.cls;
    return 0U;
}
#endif
#ifndef RE4DC_ACTOR_SKIN_OWNER_POOL
#define RE4DC_ACTOR_SKIN_OWNER_POOL 0
#endif
#if RE4DC_ACTOR_SKIN_OWNER_POOL && !RE4DC_ACTOR_TRANSACTION
#error "ACTOR_SKIN_OWNER_POOL requires ACTOR_TRANSACTION"
#endif
#if RE4DC_ACTOR_TRANSACTION
#include "actor_native_owner.h"
#include "actor_prof.h"
#include "actor_plan.h"
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
#include "include/native_actor_continuation.h"
#include <new>
#if defined(__sh__) && !defined(PLACEMENT_NEW_DEFINED)
// This platform TU uses libstdc++ <new>, unlike the recovered game's shim.
// Its placement overload already exists; honor the shared compatibility guard.
#define PLACEMENT_NEW_DEFINED
#endif
#include "include/coarse_actor_geometry_once.h"
extern "C" void* re4dc_prim_tail(unsigned,unsigned);
#endif
#if defined(RE4DC_ACTOR_PROBE_LIGHT) && RE4DC_ACTOR_PROBE_LIGHT
#include "actor_light_probe.h"
#endif
// GANADO_LIT=1 (crowd.mk, lane ganlit 2026-10-16; render only; default 0: nothing changes; needs ACTOR_PROBE_LIGHT=2):
// the Ganado probe's per-vertex light is limited to the RE4DC_GANADO_LIT_NEAREST nearest Ganado models (0: none, every
// Ganado one colour per part from its probe; -1: every near-tier Ganado, as ACTOR_PROBE_LIGHT=2 alone). The rest keep
// one colour per part from the probe. GANADO_LIT_TOGGLE=1 (debug builds only): warp `ganlit <m>` picks the mode at load
// (0 = test 15: Ganados off the probe; 1..8 = the m - 1 nearest; 9 = every near-tier Ganado).
#ifndef RE4DC_GANADO_LIT
#define RE4DC_GANADO_LIT 0
#endif
#ifndef RE4DC_GANADO_LIT_TOGGLE
#define RE4DC_GANADO_LIT_TOGGLE 0
#endif
#if RE4DC_GANADO_LIT
#ifndef RE4DC_GANADO_LIT_NEAREST
#define RE4DC_GANADO_LIT_NEAREST -1
#endif
static int ganlit_nearest = RE4DC_GANADO_LIT_NEAREST;
#endif
#ifndef RE4DC_GANADO_LIT_FILL
#define RE4DC_GANADO_LIT_FILL 0
#endif
#if RE4DC_GANADO_LIT_FILL
static int ganlit_fill = RE4DC_GANADO_LIT_FILL > 0 ? RE4DC_GANADO_LIT_FILL : 0;  // percent; the toggle build: -1 = 0 at boot
#endif
#if RE4DC_GANADO_LIT_TOGGLE
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" {
unsigned re4dc_ganlit_mode = RE4DC_GANADO_LIT_NEAREST < 0 ? 9U : unsigned(RE4DC_GANADO_LIT_NEAREST) + 1U;
void re4dc_ganlit_set(unsigned mode) {
    re4dc_ganlit_mode = mode > 9U ? 9U : mode;
    ganlit_nearest = re4dc_ganlit_mode == 9U ? -1 : re4dc_ganlit_mode == 0U ? 0 : int(re4dc_ganlit_mode) - 1;
    re4dc_log("GANLIT_MODE %u nearest=%d\n", re4dc_ganlit_mode, ganlit_nearest);
}
#if RE4DC_GANADO_LIT_FILL
void re4dc_ganlit_fill_set(unsigned percent) {
    ganlit_fill = percent > 100U ? 100 : int(percent);
    re4dc_log("GANLIT_FILL %d\n", ganlit_fill);
}
#endif
}
#endif

#include "actor_lifetime.h"
#ifndef RE4DC_ACTOR_LOG
#define RE4DC_ACTOR_LOG 0
#endif
#if RE4DC_ACTOR_LOG
#include "re4dc_platform.h"
#endif
#include "warp_late.h"
// ACTOR_NO_CLEAR (game30.mk; render only, default 0): repeated per-part clears on the actor path are dropped where
// the cleared words are never read (lights_reset, Lights::prepared, the Frame cache invalidation).
#ifndef RE4DC_ACTOR_NO_CLEAR
#define RE4DC_ACTOR_NO_CLEAR 0
#endif
// ACTOR_SETUP_LEAN (game30.mk; default 0): keep kernel arguments and dispatch in the current Part. A new Part
// always starts unprepared; palette readiness and each call's records/output pointers are still read live.
#ifndef RE4DC_ACTOR_SETUP_LEAN
#define RE4DC_ACTOR_SETUP_LEAN 0
#endif
// ACTOR_BYTES_LEAN (game30.mk; default 0): a Part's constant ARGB survives position/UV updates.
// Prime its cache slots once, including the headroom fold. MOVCA position allocation cannot retain it.
#ifndef RE4DC_ACTOR_BYTES_LEAN
#define RE4DC_ACTOR_BYTES_LEAN 0
#endif
// ACTOR_MOVCA (game30.mk; render only, default 0): the position kernels allocate each meshlet cache entry's line
// with movca.l (no fill from RAM: the line is written before it is read); emit / emit_sq write the flags word.
#ifndef RE4DC_ACTOR_MOVCA
#define RE4DC_ACTOR_MOVCA 0
#endif
#include "../../room/pvr_geometry.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#ifndef RE4DC_ACTOR_FOG_GATE
#define RE4DC_ACTOR_FOG_GATE 0  // obj/scenery30.h (ACTOR_FOG_GATE)
#endif
#if defined(RE4DC_ACTOR_TEST)
#include <cstdio>
#endif
#if defined(__sh__)
#include <dc/matrix.h>
#include <dc/fmath_base.h>
#endif

// TA_DIRECT store-queue submission (needs the frame owner's direct API).
#ifndef RE4DC_ACTOR_DIRECT
#define RE4DC_ACTOR_DIRECT 0
#endif
#if RE4DC_ACTOR_DIRECT
#include "ta_direct.hpp"
#endif
// COARSE_ONE_SUBMIT (game30.mk): re4dc_actor_submit_chunks, one TA window per coarse actor (end of file).
#ifndef RE4DC_COARSE_ONE_SUBMIT
#define RE4DC_COARSE_ONE_SUBMIT 0
#endif
// COARSE_GATE_ONCE (game30.mk; with COARSE_ONE_SUBMIT): the window path's fog gate keeps a chunk on one palette
// entry's proof (one_chunk, end of file).
#ifndef RE4DC_COARSE_GATE_ONCE
#define RE4DC_COARSE_GATE_ONCE 0
#endif

#ifndef RE4DC_ACTOR_ASM
#if defined(__sh__)
#define RE4DC_ACTOR_ASM 1
#else
#define RE4DC_ACTOR_ASM 0
#endif
#endif

// ACTOR_VTX_KERNEL (game30.mk; render only): a meshlet's vertex passes (pass_positions,
// pass_lights) on the software-pipelined loops of platform/avk_sh4.S. =2: check build, the
// previous path recomputes every kernel vertex and the words are compared ("VTXK" log lines).
#ifndef RE4DC_ACTOR_VTX_KERNEL
#define RE4DC_ACTOR_VTX_KERNEL 0
#endif
#if RE4DC_ACTOR_VTX_KERNEL && defined(__sh__) && RE4DC_ACTOR_ASM && !defined(ACTOR_TEST_XMTRX)
#define RE4DC_AVK RE4DC_ACTOR_VTX_KERNEL
// The kernels' argument blocks (offsets fixed by avk_sh4.S). At file scope: an extern "C" name
// declared inside the unnamed namespace would not bind to the assembler symbol.
struct AvkPos {
    const std::uint8_t* rec; unsigned n; const std::uint8_t* pos; const std::uint8_t* uv;  // 0 4 8 12
    void* dst; std::uint8_t* oc; unsigned rs;                                             // 16 20 24
    const float* matrix; const std::uint8_t* ready; unsigned entries;                     // 28 32 36
    float width, height, near_distance, far_distance, au, bu, av, bv;                     // 40 .. 68
};
struct AvkLight {
    const std::uint8_t* rec; unsigned n; const std::uint8_t* nrm; std::uint32_t* argb;    // 0 4 8 12
    unsigned rs; const float* color; const float* dirs;                                   // 16 20 24
    const std::uint8_t* ready; unsigned entries; std::uint32_t alpha;                     // 28 32 36
};
static_assert(__builtin_offsetof(AvkPos, matrix) == 28 && __builtin_offsetof(AvkPos, width) == 40 &&
              __builtin_offsetof(AvkPos, bv) == 68, "avk_sh4.S AvkPos");
static_assert(__builtin_offsetof(AvkLight, dirs) == 24 && __builtin_offsetof(AvkLight, alpha) == 36,
              "avk_sh4.S AvkLight");
extern "C" {
unsigned re4dc_avk_pos_skin_s16(const AvkPos*);
unsigned re4dc_avk_pos_skin_u16(const AvkPos*);
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM
unsigned re4dc_shz_pos_skin_s16(const AvkPos*);
unsigned re4dc_shz_pos_skin_u16(const AvkPos*);
#endif
unsigned re4dc_avk_pos_rigid_s16(const AvkPos*);
unsigned re4dc_avk_pos_rigid_u16(const AvkPos*);
#ifndef RE4DC_AVK_RIGID6
#define RE4DC_AVK_RIGID6 0
#endif
#if RE4DC_AVK_RIGID6
unsigned re4dc_avk_pos_rigid6_s16(const AvkPos*);
unsigned re4dc_avk_pos_rigid6_u16(const AvkPos*);
unsigned re4dc_avk_light_rigid3(const AvkLight*);
#endif
unsigned re4dc_avk_light_skin(const AvkLight*);
unsigned re4dc_avk_light_rigid(const AvkLight*);
#ifndef RE4DC_ACTOR_LIGHT_N16
#define RE4DC_ACTOR_LIGHT_N16 0
#endif
#if RE4DC_ACTOR_LIGHT_N16
// ACTOR_LIGHT_N16 (game30.mk): the s16-normal light kernels (mkavk.py @n16).
unsigned re4dc_avk_light_skin_n16(const AvkLight*);
unsigned re4dc_avk_light_rigid_n16(const AvkLight*);
unsigned re4dc_avk_light_rigid_n16s6(const AvkLight*);
#endif
void re4dc_log(const char* fmt, ...);
}
#else
#define RE4DC_AVK 0
#endif
#if defined(RE4DC_GIGANTE_LIGHTS) && RE4DC_GIGANTE_LIGHTS
extern "C" int re4dc_actor_model_id(const void* model);  // model_bridge.cpp (GIGANTE_LIGHTS)
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS
extern "C" int re4dc_actor_obj_id(const void* model);  // model_bridge.cpp (STATUE_LIGHTS)
#endif
#endif
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
extern "C" unsigned re4dc_leon_light_mode;  // LEON_LIGHT_TOGGLE (defined below, next to the probe API)
#endif

namespace {
using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using re4dc::render::SourceLight;
using re4dc::render::SourceLighting;

#if RE4DC_ACTOR_STATS_LEAN && !RE4DC_ACTOR_LOG
// ACTOR_STATS_LEAN (game30.mk; exact): the statistics only the NATIVE_ACTOR_LOG line reads compile to
// nothing (they were ~9% of re4dc_actor_submit: a load / add / store per counter per meshlet). Only
// `triangles` is live: coarse_ganado reads it through re4dc_actor_stats().
Re4dcActorStats stats_live{};
struct NopStat {
    NopStat& operator++() { return *this; }
    NopStat& operator+=(unsigned) { return *this; }
    NopStat& operator-=(unsigned) { return *this; }
    NopStat& operator=(unsigned) { return *this; }
    operator unsigned() const { return 0; }
};
struct LeanStats {
    NopStat parts, handled, declined, deferred, culled_infos, culled_parts;
    NopStat info_preparations, position_transforms, light_sets, normals_lit;
    NopStat corners, runs, fallback_runs, fallback_triangles, flushes;
    NopStat workspace_misses, attenuated_lights, near_vertices;
    NopStat conversions, conversion_rejects, meshlets, meshlets_culled, meshlets_clipped;
    NopStat vertices, slow_light_vertices, skinned_parts, materialized_infos, skin_registered;
    NopStat transient_conversions, strips_culled, meshlets_whole;
    NopStat lod_parts, lod_rebuilds, lod_draws[4], bake_hits, bake_scaled, bake_builds, uv16_parts;
    NopStat skin_dir_sets;
    NopStat crowd_models, crowd_parts[4], crowd_triangles[4];
    unsigned& triangles = stats_live.triangles;
};
LeanStats stats;
#define RE4DC_STATS_OBJECT stats_live
#else
Re4dcActorStats stats{};
#define RE4DC_STATS_OBJECT stats
#endif
unsigned char* workspace = nullptr;
unsigned workspace_bytes = 0, frame_serial = 0;

// ---------------------------------------------------------------- helpers --
inline unsigned be16(const u8* p) { return (unsigned(p[0]) << 8) | p[1]; }
inline bool ram(const void* p, unsigned bytes) {
#if defined(__sh__)
    const auto a = reinterpret_cast<std::uintptr_t>(p);
    return a >= 0x8c000000U && a < 0x8d000000U && bytes <= 0x8d000000U - a;
#else
    (void)bytes; return p != nullptr;
#endif
}
// 2^e for |e| < 126 without a libm call.
inline float pow2(int e) { return __builtin_bit_cast(float, u32(127 + e) << 23); }
inline float inverse_sqrt(float x) {
#if defined(__sh__)
    return __frsqrt(x);
#else
    return 1.0f / std::sqrt(x);
#endif
}
inline unsigned channel(float x) { return x <= 0.0f ? 0U : x >= 255.0f ? 255U : unsigned(x); }

// XMTRX: KOS matrix_t layout, m[column][row]. Host builds model it in C;
// the qemu-sh4 kernel test supplies its own (qemu has no ftrv).
#if defined(ACTOR_TEST_XMTRX)
ACTOR_TEST_XMTRX
#elif defined(__sh__)
inline void load_xmtrx(const float* m) { mat_load(reinterpret_cast<matrix_t*>(const_cast<float*>(m))); }
#define ACTOR_FTRV(x, y, z, w) mat_trans_nodiv(x, y, z, w)
#else
float host_xmtrx[16];
inline void load_xmtrx(const float* m) { std::memcpy(host_xmtrx, m, sizeof(host_xmtrx)); }
#define ACTOR_FTRV(x, y, z, w) do { const float _x = (x), _y = (y), _z = (z), _w = (w); \
    (x) = host_xmtrx[0] * _x + host_xmtrx[4] * _y + host_xmtrx[8] * _z + host_xmtrx[12] * _w; \
    (y) = host_xmtrx[1] * _x + host_xmtrx[5] * _y + host_xmtrx[9] * _z + host_xmtrx[13] * _w; \
    (z) = host_xmtrx[2] * _x + host_xmtrx[6] * _y + host_xmtrx[10] * _z + host_xmtrx[14] * _w; \
    (w) = host_xmtrx[3] * _x + host_xmtrx[7] * _y + host_xmtrx[11] * _z + host_xmtrx[15] * _w; } while (0)
#endif

// Plain 4x4 (column-major, like matrix_t) x vec4, for setup code only.
inline void mul4(const float* m, const float v[4], float out[4]) {
    for (unsigned r = 0; r < 4; ++r)
        out[r] = m[r] * v[0] + m[4 + r] * v[1] + m[8 + r] * v[2] + m[12 + r] * v[3];
}

// ------------------------------------------------------------ blob format --
// A converted part, built once in place of its GX list:
//   header | level-0 meshlet table | record array | level-0 index lists |
//   [LOD: per level a MeshletLevel table + index lists] [LevelInfo x levels]
//   [BakeBlock]
// Records are the part's unique corner tuples as u16 fields: vi, ni, ti,
// then ci when the colour index varies (kHasCi; every D358 actor part has a
// constant one, kept in the header), then a baked RGB565 colour (kHasBake).
// Level-0 meshlet i owns a contiguous record range; its indices are u8 per
// corner (bit 7 = last corner of a strip).
// LOD level k >= 1: the part simplified part-wide (seam-aware half-edge
// collapses by quadric error on bind-pose positions; positions shared by two
// meshlets and open-boundary positions stay) to a triangle subset over the
// SAME records: each meshlet orders its records by the coarsest level that
// still uses them, so level k transforms and lights only a prefix
// (MeshletLevel.vertices) and draws its own restripified index list. No
// extra per-record work at draw time; a level costs ~1 byte per corner.
// LevelInfo.error bounds the geometric error in object units; a draw picks
// the coarsest level whose projected error is at most lod_tau pixels.
constexpr u8 kMagic = 0xFE;  // not a GX opcode: every other walker rejects it
constexpr u8 kVersion = 3;
constexpr unsigned kMaxVertices = 128;   // u8 index, bit 7 = end of strip
constexpr unsigned kMaxIndices = 1024;   // per meshlet (packet slab ~1400)
constexpr unsigned kMaxStrip = 64;       // long GX strips are cut (2-corner overlap)
constexpr unsigned kMaxLevels = 3;
// NATIVE_ACTOR_LOD=0 builds define a zero budget: no level is ever built and
// the simplifier compiles out (levels already in a blob would still draw).
#ifndef RE4DC_ACTOR_LOD_BUDGET
#define RE4DC_ACTOR_LOD_BUDGET 128U
#endif
constexpr bool kLodBuild = RE4DC_ACTOR_LOD_BUDGET != 0;
enum : u8 { kHasCi = 1, kHasBake = 2, kLodPending = 0x80 };
struct BlobHeader {
    u8 magic, version, flags, levels;  // flags: kHasCi | kHasBake | uv excess << 2 | kLodPending; levels after 0
    u16 meshlets, color_index;         // level-0 meshlets; the constant colour index
    u16 rec4, idx4;                    // record array / level-0 index lists offset / 4
    u16 lod4, bake4;                   // LevelInfo[levels] / BakeBlock offset / 4 (0: none)
    float center[3], radius;           // bind-pose bounds of the referenced positions
};
static_assert(sizeof(BlobHeader) == 32, "blob header");
// flags bits 2..6 (16-bit UV check): over the part's raw uv components, the
// most significant bits beyond 8 (0: every component is exact in a bf16 when
// scaled by a power of two; else it rounds by up to 2^(excess-1) raw units).
inline unsigned uv_excess_bits(const BlobHeader& h) { return (h.flags >> 2) & 31U; }
// Meshlet counts packed in one word: vertices (8 bits, <= 128), indices
// (12 bits, <= 2048), triangles (12 bits).
struct Counts {
    u32 w;
    static Counts of(unsigned v, unsigned i, unsigned t) { return {u32(v) | (u32(i) << 8) | (u32(t) << 20)}; }
    unsigned vertices() const { return w & 0xFFU; }
    unsigned indices() const { return (w >> 8) & 0xFFFU; }
    unsigned triangles() const { return w >> 20; }
};
// first: record ordinal; index: byte offset from the level-0 lists (idx4)
struct MeshletInfo { Counts n; u16 first, index; };
static_assert(sizeof(MeshletInfo) == 8, "meshlet header");
// vertices: record prefix; index: byte offset from the level lists (lists4)
struct MeshletLevel { Counts n; u16 index, reserved; };
static_assert(sizeof(MeshletLevel) == 8, "meshlet level");
struct LevelInfo { float error; u16 table4, lists4; };  // MeshletLevel[meshlets] / lists offset / 4
// Static prelit state (kHasBake): the per-object light fold the baked record
// colours were computed with. state: 0 = not baked, else 1 | palette hash
// (skinned parts: the pose the directions were folded through); clamped: some
// baked channel saturated (a darker scaled fold must rebake).
struct BakeBlock { u32 state, clamped; float dir[12]; float color[16]; };
// A meshlet's packed records.
struct Records {
    const u16* r; unsigned stride, color; bool has_ci;
    unsigned vi(unsigned i) const { return r[i * stride]; }
    unsigned ni(unsigned i) const { return r[i * stride + 1]; }
    unsigned ti(unsigned i) const { return r[i * stride + 2]; }
    unsigned ci(unsigned i) const { return has_ci ? r[i * stride + 3] : color; }
};

inline const BlobHeader* blob_of(const Re4dcModelPart& p) {
    return p.stream_bytes >= sizeof(BlobHeader) && p.stream[0] == kMagic && p.stream[1] == kVersion
        ? reinterpret_cast<const BlobHeader*>(p.stream) : nullptr;
}

// Palette index of a vtxOrig / nrmOrig entry (0 when not skinned).
struct SortSource {
    const u8* positions = nullptr; const u8* normals = nullptr;
    unsigned position_count = 0, normal_count = 0; bool small_normals = true;
    unsigned position_palette(unsigned vi) const {
        if (!positions || vi >= position_count) return 0;
        return u16(reinterpret_cast<const short*>(positions + vi * 8)[3]);
    }
    unsigned normal_palette(unsigned ni) const {
        if (!normals || ni >= normal_count) return 0;
        return small_normals ? normals[ni * 4 + 3] : u16(reinterpret_cast<const short*>(normals + ni * 8)[3]);
    }
};

#if defined(RE4DC_ACTOR_TEST)
double test_convert_us = 0, test_lod_us = 0, test_convert_max_us = 0;
#if defined(__x86_64__)
double test_now_us() { return double(__builtin_ia32_rdtsc()) / 3000.0; }  // ~3 GHz TSC, host-relative only
#else
double test_now_us() { return 0.0; }
#endif
unsigned reject_line = 0, test_meshlets = 0, test_records = 0, test_indices = 0, test_lod_parts = 0, test_lod_bytes = 0,
         test_blob_bytes = 0;
#define ACTOR_REJECT() do { reject_line = __LINE__; return false; } while (0)
#else
#define ACTOR_REJECT() return false
#endif

// LOD ladder: a level is snapshotted when the part's triangle count falls to
// these fractions (or collapses run out); levels that do not fit are dropped.
float lod_fractions[kMaxLevels] = {0.8f, 0.6f, 0.35f};
// NATIVE_ACTOR_CROWD: Ganado-family parts are built with a steeper ladder (their
// mid and far tiers draw the coarser levels); level_ladder is the one in use.
float lod_fractions_crowd[kMaxLevels] = {0.5f, 0.25f, 0.1f};
const float* level_ladder = lod_fractions;
bool lod_metric_qem = false;  // test: level error = running quadric error instead of the geometric one
constexpr unsigned kLodMinTriangles = 24;

// Bump allocator over one conversion's scratch.
struct Arena {
    u8* p; unsigned left;
    template <class T> T* take(unsigned n) {
        const unsigned bytes = (n * unsigned(sizeof(T)) + 7U) & ~7U;
        if (bytes > left) return nullptr;
        T* r = reinterpret_cast<T*>(p); p += bytes; left -= bytes; return r;
    }
};

// Greedy stripifier over one meshlet's triangles (u8 local indices, winding
// kept): strips of at most kMaxStrip corners, bit 7 on each strip's last
// corner. Returns the corner count, 0 when `out` (cap bytes) is too small.
unsigned stripify(const u8* tri, unsigned count, u8* out, unsigned cap, u8* used, u16* first, u16* list) {
    // vertex -> triangles (CSR over <= 128 local vertices)
    std::memset(first, 0, (kMaxVertices + 1) * sizeof(u16));
    for (unsigned t = 0; t < count * 3; ++t) ++first[tri[t] + 1];
    for (unsigned v = 0; v < kMaxVertices; ++v) first[v + 1] = u16(first[v + 1] + first[v]);
    u16 fill[kMaxVertices];
    for (unsigned v = 0; v < kMaxVertices; ++v) fill[v] = first[v];
    for (unsigned t = 0; t < count; ++t)
        for (unsigned k = 0; k < 3; ++k) list[fill[tri[t * 3 + k]]++] = u16(t);
    std::memset(used, 0, count);
    // unused triangle with directed edge a->b; its third corner
    auto find = [&](unsigned a, unsigned b, unsigned& third) -> unsigned {
        for (unsigned i = first[a]; i < first[a + 1]; ++i) {
            const unsigned t = list[i];
            if (used[t]) continue;
            const u8* c = tri + t * 3;
            for (unsigned k = 0; k < 3; ++k)
                if (c[k] == a && c[(k + 1) % 3] == b) { third = c[(k + 2) % 3]; return t; }
        }
        return ~0U;
    };
    unsigned n = 0;
    u8 best[kMaxStrip], strip[kMaxStrip];
    u16 best_t[kMaxStrip], strip_t[kMaxStrip];
    for (unsigned s = 0; s < count; ++s) {
        if (used[s]) continue;
        unsigned best_n = 0, best_tn = 0;
        for (unsigned r = 0; r < 3; ++r) {
            const u8* c = tri + s * 3;
            unsigned sn = 3, tn = 1;
            strip[0] = c[r]; strip[1] = c[(r + 1) % 3]; strip[2] = c[(r + 2) % 3]; strip_t[0] = u16(s);
            used[s] = 1;
            while (sn < kMaxStrip) {
                unsigned third = 0;
                // triangle k = sn - 2: even (s[k], s[k+1], x), odd (s[k+1], s[k], x)
                const unsigned t = ((sn - 2) & 1) ? find(strip[sn - 1], strip[sn - 2], third)
                                                  : find(strip[sn - 2], strip[sn - 1], third);
                if (t == ~0U) break;
                used[t] = 1; strip_t[tn++] = u16(t); strip[sn++] = u8(third);
            }
            for (unsigned i = 0; i < tn; ++i) used[strip_t[i]] = 0;
            if (sn > best_n) {
                best_n = sn; best_tn = tn;
                std::memcpy(best, strip, sn); std::memcpy(best_t, strip_t, tn * sizeof(u16));
            }
        }
        for (unsigned i = 0; i < best_tn; ++i) used[best_t[i]] = 1;
        if (n + best_n > cap) return 0;
        for (unsigned i = 0; i < best_n; ++i) out[n + i] = best[i];
        out[n + best_n - 1] |= 0x80U;
        n += best_n;
    }
    return n;
}

// One conversion, run once per part (the result replaces the GX list when it
// fits). Steps:
//  1. The GX list becomes "strips": GX strips (cut at kMaxStrip corners with
//     a two-corner overlap, same winding), quads as 4-corner strips
//     (1,2,0,3), list/fan triangles as 3-corner strips.
//  2. Windows of consecutive strips (as many corners as the scratch allows;
//     whole parts for everything but the largest room objects) are packed
//     into meshlets: seeded by the first unused strip, then greedily the
//     unused strip sharing the most corner tuples with the meshlet
//     (ties: GX order), else the next unused strip that fits. Tuples are
//     deduplicated per window by exact (vi, ni, ti, ci). Translucent parts
//     keep GX order (sequential packing), so their draw order is unchanged.
//  3. Each meshlet's records are sorted by (position palette, normal
//     palette, vi) so draw-time skinning reloads matrices once per run.
//  4. Whole-part opaque windows: LOD levels (see the blob format).
// The triangle set and each triangle's winding are the GX list's.
#if RE4DC_ACTOR_BACKFACE_CONE
// ACTOR_BACKFACE_CONE counters (logged as "ABFC" every 300 vblanks); per class 0 other, 1 Leon, 2 Ganado, 3 El Gigante,
// 4 Ashley: meshlets tested / rejected, vertices / triangles skipped, vertices of the tested parts' meshlets.
unsigned abc_splits = 0, abc_built = 0, abc_noroom = 0, abc_cones = 0, abc_nocone = 0, abc_bad = 0, abc_log = 0;
unsigned abc_tests[5], abc_rej[5], abc_vskip[5], abc_tskip[5], abc_verts[5];
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
re4dc::cone32::Counters abc32_stats;
#endif
#endif
class Converter {
public:
    Converter(const Re4dcModelPart& part, const SortSource& sort, u8* out, unsigned out_bytes, Arena scratch, bool lod)
        : p(part), s(sort), out(out), capacity(out_bytes), arena(scratch),
          stride((part.flags & 0x80000000U) ? 8U : 6U), lod(lod) {}

    bool run() {
        if (capacity < sizeof(BlobHeader) + 32 || p.stream_bytes > 0x3FFFCU) ACTOR_REJECT();
        if (!parse()) return false;
#if RE4DC_ACTOR_BACKFACE_CONE
        ++abc_conv; if (p.blend == 0) ++abc_conv_op; if (abc_class_of(p.model)) ++abc_conv_mk;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
        // An uncullable or mutable rigid part cannot use a persistent cone.
        // Keep its original clustering instead of paying split/tail overhead.
        if (!abc_no_split && p.blend == 0 &&
            ((p.cull != 1 && p.cull != 2) || (p.material_flags & 4U) || p.depth_mode != 0 ||
             (p.position_stride == 8 && !p.static_geometry))) {
            abc_no_split = true; ++abc32_stats.split_skipped;
        }
#endif
        if (p.blend == 0 && !abc_no_split) abc_split();  // every opaque actor part (cones are used where the draw culls)
#endif
        rs = 3U + (constant_color ? 0U : 1U);
        infos = arena.take<MeshletInfo>(strip_count);
        idx_all = arena.take<u8>(corner_total);
        if (!infos || !idx_all) ACTOR_REJECT();
        // Per-window working set: ~26 B per corner.
        unsigned window = arena.left > 2048U ? (arena.left - 2048U) / 26U : 0U;
        if (window > corner_total) window = corner_total;
        if (window < 256U && window < corner_total) ACTOR_REJECT();
        const bool keep_order = p.blend != 0;
        used = sizeof(BlobHeader);
        for (unsigned first = 0; first < strip_count;) {
            unsigned last = first, corners = 0;
            while (last < strip_count && (last == first || corners + strips[last].n <= window)) corners += strips[last++].n;
            Arena mark = arena;
            if (!pack(first, last, corners, keep_order)) return false;
            arena = mark;
            first = last;
        }
        if (!meshlets) ACTOR_REJECT();
        return assemble();
    }
    unsigned bytes() const { return size; }
    unsigned level_count() const { return levels; }
#if RE4DC_ACTOR_BACKFACE_CONE
    bool split() const { return skey != nullptr; }
    unsigned record_count() const { return records; }
    unsigned meshlet_count() const { return meshlets; }
    bool abc_force = false;  // relod: the part was split before (its cone table is valid)
    bool abc_no_split = false;  // the split blob does not fit in place (convert's retry) or a per-submit transient
#endif

private:
    struct Strip { u32 a, b; u16 n; u8 mode, pad; };  // mode 0 run, 1 quad (1,2,0,3), 2 fan triangle, 3 reversed run
    const Re4dcModelPart& p;
    const SortSource& s;
    u8* out;
    unsigned capacity;
    Arena arena;
    const unsigned stride;
    const bool lod;
    unsigned rs = 3;
    Strip* strips = nullptr;
    unsigned strip_count = 0, corner_total = 0;
    bool constant_color = true;
    unsigned color = 0;
    MeshletInfo* infos = nullptr;
    u8* idx_all = nullptr;
    unsigned idx_used = 0, records = 0;
    u16* rec_tuple = nullptr;  // whole-part LOD windows: record ordinal -> tuple
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    unsigned used = 0, size = 0, meshlets = 0, triangles = 0;
    unsigned uv_excess = re4dc::format32::kUvCertificateEmpty;
#else
    unsigned used = 0, size = 0, meshlets = 0, triangles = 0, uv_excess = 0;
#endif
    float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
    bool any_bounds = false;
    // LOD result (level data written at level_start.. in `out`, relative offsets)
    unsigned levels = 0, level_start = 0, level_end = 0;
    float level_error[kMaxLevels] = {};
    unsigned level_table[kMaxLevels] = {};  // offsets relative to level_start

    const u8* corner(const Strip& t, unsigned k) const {
        static constexpr u8 quad[4] = {1, 2, 0, 3};
        if (t.mode == 0) return p.stream + t.a + k * stride;
        if (t.mode == 1) return p.stream + t.a + quad[k] * stride;
#if RE4DC_ACTOR_BACKFACE_CONE
        if (t.mode == 3) return p.stream + t.a - k * stride;
#endif
        return k == 0 ? p.stream + t.a : p.stream + t.b + (k - 1) * stride;
    }
#if RE4DC_ACTOR_BACKFACE_CONE
    // ACTOR_BACKFACE_CONE: per strip piece key = palette entry << 3 | facing (0..5: the normal's dominant axis and sign,
    // 7: corners on different palette entries); the clustering keeps one key per meshlet.
    const u16* skey = nullptr;
    bool abc_pos(unsigned vi, float v[3], unsigned& pal) const {
        const u8* base; unsigned count;
        if (p.position_stride == 6) { if (!s.positions) return false; base = s.positions; count = s.position_count; }
        else if (p.position_stride == 8 && p.positions) { base = p.positions; count = p.position_count; }
        else return false;
        if (vi >= count) return false;
        const short* q = reinterpret_cast<const short*>(base + vi * 8U);
        v[0] = float(q[0]); v[1] = float(q[1]); v[2] = float(q[2]);
        pal = p.position_stride == 6 ? unsigned(u16(q[3])) : 0U;
        return true;
    }
    // Key of the triangle (a, b, c) in drawn winding; ~0 when degenerate or unreadable (takes a neighbour's key).
    unsigned abc_key(const u8* a, const u8* b, const u8* c) const {
        float pa[3], pb[3], pc[3]; unsigned qa, qb, qc;
        if (!abc_pos(be16(a), pa, qa) || !abc_pos(be16(b), pb, qb) || !abc_pos(be16(c), pc, qc) || qa > 0x1FFFU) return ~0U;
        if (qa != qb || qa != qc) return (qa << 3) | 7U;
        float n[3];
        if (!normal_of(pa, pb, pc, n)) return ~0U;
        unsigned ax = 0; float m = std::fabs(n[0]);
        if (std::fabs(n[1]) > m) { ax = 1; m = std::fabs(n[1]); }
        if (std::fabs(n[2]) > m) ax = 2;
        return (qa << 3) | (ax * 2U + (n[ax] < 0.0f ? 1U : 0U));
    }
    // Cut every strip where its triangles' key changes (a piece starting on an odd triangle is written reversed, which
    // keeps every triangle's winding; quads with two keys become two triangles), then order the pieces by key.
    // Nothing changes if anything is missing (positions, arena).
    void abc_split() {
        u16 tk[kMaxStrip];
        Strip* ns = nullptr; u16* nk = nullptr;
        unsigned count = 0, corners = 0;
        auto put = [&](u32 a, u32 b, unsigned n, u8 mode, unsigned key) {
            if (ns) { ns[count] = {a, b, u16(n), mode, 0}; nk[count] = u16(key); }
            ++count; corners += n;
        };
        for (unsigned pass = 0; pass < 2; ++pass) {
            count = 0; corners = 0;
            for (unsigned i = 0; i < strip_count; ++i) {
                const Strip& t = strips[i];
                const unsigned tris = t.mode == 1 ? 2U : t.n - 2U;
                unsigned last = ~0U;
                for (unsigned j = 0; j < tris; ++j) {
                    unsigned key;
                    if (j & 1) key = abc_key(corner(t, j + 1), corner(t, j), corner(t, j + 2));
                    else key = abc_key(corner(t, j), corner(t, j + 1), corner(t, j + 2));
                    tk[j] = u16(key == ~0U ? 0xFFFFU : key);
                    if (key != ~0U && last == ~0U) last = key;
                }
                if (last == ~0U) { put(t.a, t.b, t.n, t.mode, 0xFFFFU); continue; }  // nothing readable: one piece
                for (unsigned j = 0; j < tris; ++j) { if (tk[j] == 0xFFFFU) tk[j] = u16(last); else last = tk[j]; }
                if (t.mode == 1) {
                    if (tk[0] == tk[1]) put(t.a, t.b, t.n, 1, tk[0]);
                    else { put(t.a, 0, 3, 0, tk[0]); put(t.a, t.a + 2U * stride, 3, 2, tk[1]); }  // (q0,q1,q2), fan (q0,q2,q3)
                    continue;
                }
                if (t.mode != 0) { put(t.a, t.b, t.n, t.mode, tk[0]); continue; }
                for (unsigned u0 = 0; u0 < tris;) {
                    unsigned u1 = u0;
                    while (u1 + 1 < tris && tk[u1 + 1] == tk[u0]) ++u1;
                    const unsigned key = tk[u0];
                    if (!(u0 & 1U)) put(t.a + u0 * stride, 0, u1 - u0 + 3U, 0, key);
                    else if (u1 & 1U) put(t.a + (u1 + 2U) * stride, 0, u1 - u0 + 3U, 3, key);
                    else {
                        if (u1 > u0) put(t.a + (u1 + 1U) * stride, 0, u1 - u0 + 2U, 3, key);
                        put(t.a + u1 * stride, 0, 3, 0, key);
                    }
                    u0 = u1 + 1;
                }
            }
            if (pass) break;
            if (corners >= 0xFFF0U) return;
            ns = arena.take<Strip>(count); nk = arena.take<u16>(count);
            if (!ns || !nk) return;
        }
        // Shell sort by key (the order inside a key is not significant).
        for (unsigned gap = count / 2U; gap; gap = gap == 2U ? 1U : gap * 5U / 11U)
            for (unsigned i = gap; i < count; ++i) {
                const Strip sv = ns[i]; const u16 kv = nk[i];
                unsigned j = i;
                while (j >= gap && nk[j - gap] > kv) { ns[j] = ns[j - gap]; nk[j] = nk[j - gap]; j -= gap; }
                ns[j] = sv; nk[j] = kv;
            }
        strips = ns; skey = nk; strip_count = count; corner_total = corners;
        ++abc_splits;
    }
#endif
    unsigned ci_of(const u8* c) const { return stride == 8 ? be16(c + 4) : 0U; }
    bool same_tuple(const u8* x, const u8* y) const {
        return be16(x) == be16(y) && be16(x + 2) == be16(y + 2) && be16(x + stride - 2) == be16(y + stride - 2) &&
               ci_of(x) == ci_of(y);
    }
    unsigned hash_of(const u8* c) const {
        return (be16(c) * 2654435761U) ^ (be16(c + 2) * 40503U) ^ (be16(c + stride - 2) * 97U) ^ ci_of(c);
    }

    // Step 1 (two passes: count, then fill).
    bool parse() {
        for (unsigned fill = 0; fill < 2; ++fill) {
            unsigned count = 0, offset = 0;
            const u8* st = p.stream;
            auto add = [&](u32 a, u32 b, unsigned n, u8 mode) {
                if (fill) strips[count] = {a, b, u16(n), mode, 0};
                ++count;
            };
            while (offset < p.stream_bytes) {
                const unsigned op = st[offset++];
                if (!op) continue;
                if (p.stream_bytes - offset < 2) ACTOR_REJECT();
                const unsigned n = be16(st + offset); offset += 2;
                if (n > (p.stream_bytes - offset) / stride) ACTOR_REJECT();
                const u32 a = offset;
                offset += n * stride;
                if (op == 0x98) {
                    if (n < 3) continue;
                    unsigned start = 0;
                    while (n - start > kMaxStrip) { add(a + start * stride, 0, kMaxStrip, 0); start += kMaxStrip - 2; }
                    add(a + start * stride, 0, n - start, 0);
                } else if (op == 0x90) {
                    if (n % 3) ACTOR_REJECT();
                    for (unsigned t = 0; t < n; t += 3) add(a + t * stride, 0, 3, 0);
                } else if (op == 0x80) {
                    if (n % 4) ACTOR_REJECT();
                    for (unsigned q = 0; q < n; q += 4) add(a + q * stride, 0, 4, 1);
                } else if (op == 0xa0) {
                    if (n == 4) add(a, 0, 4, 1);
                    else for (unsigned i = 2; i < n; ++i) add(a, a + (i - 1) * stride, 3, 2);
                } else ACTOR_REJECT();
            }
            if (!fill) {
                strip_count = count;
                if (!count) ACTOR_REJECT();
                strips = arena.take<Strip>(count);
                if (!strips) ACTOR_REJECT();
            }
        }
        corner_total = 0;
        const u8* first = corner(strips[0], 0);
        color = ci_of(first);
        for (unsigned i = 0; i < strip_count; ++i) {
            corner_total += strips[i].n;
            for (unsigned k = 0; k < strips[i].n; ++k) constant_color &= ci_of(corner(strips[i], k)) == color;
        }
        if (!constant_color) color = 0;
        if (corner_total >= 0xFFF0U) ACTOR_REJECT();
        return true;
    }

    // Step 2 core: `count` strips (strip i: n[i] corners whose tuple ids are
    // cid[scid[i]...]) over `tuples` distinct tuples into meshlets; emit()
    // receives each meshlet (tuple list, local indices). strip_meshlet
    // (optional) receives each strip's meshlet serial.
    template <class Emit>
    bool cluster(unsigned count, const u16* n, const u16* scid, const u16* cid, unsigned tuples, unsigned corners,
                 bool keep_order, u16* strip_meshlet, Emit&& emit
#if RE4DC_ACTOR_BACKFACE_CONE
                 , const u16* key = nullptr
#endif
                 ) {
        u16* occ_start = arena.take<u16>(tuples + 1);  // tuple -> strips (distinct), CSR
        u16* occ = arena.take<u16>(corners);
        u16* stamp = arena.take<u16>(tuples);
        u8* local = arena.take<u8>(tuples);
        u8* score = arena.take<u8>(count);
        u8* done = arena.take<u8>(count);
        u8* distinct = arena.take<u8>(count);
        u16* candidates = arena.take<u16>(count);
        u16* rec = arena.take<u16>(kMaxVertices);
        u8* idx = arena.take<u8>(kMaxIndices);
        if (!occ_start || !occ || !stamp || !local || !score || !done || !distinct || !candidates || !rec || !idx)
            ACTOR_REJECT();
        std::memset(occ_start, 0, (tuples + 1) * 2U);
        for (unsigned i = 0; i < tuples; ++i) stamp[i] = 0xFFFF;
        for (unsigned i = 0; i < count; ++i) {
            unsigned d = 0;
            for (unsigned k = 0; k < n[i]; ++k) {
                const unsigned t = cid[scid[i] + k];
                if (stamp[t] != i) { stamp[t] = u16(i); ++occ_start[t + 1]; ++d; }
            }
            distinct[i] = u8(d);
        }
        for (unsigned t = 0; t < tuples; ++t) occ_start[t + 1] = u16(occ_start[t + 1] + occ_start[t]);
        for (unsigned t = 0; t < tuples; ++t) { local[t] = 0; stamp[t] = occ_start[t]; }  // stamp = fill cursor
        for (unsigned i = 0; i < count; ++i)
            for (unsigned k = 0; k < n[i]; ++k) {
                const unsigned t = cid[scid[i] + k];
                if (stamp[t] == occ_start[t] || occ[stamp[t] - 1] != i) occ[stamp[t]++] = u16(i);
            }
        for (unsigned t = 0; t < tuples; ++t) stamp[t] = 0xFFFF;  // now: meshlet serial
        std::memset(score, 0, count);
        std::memset(done, 0, count);

        unsigned serial = 0, next = 0, remaining = count, produced = 0;
        while (remaining) {
            // New meshlet, seeded by the first unused strip.
            unsigned nrec = 0, nidx = 0, ntri = 0, ncand = 0;
            ++serial;
            while (done[next]) ++next;
            unsigned pick = next;
#if RE4DC_ACTOR_BACKFACE_CONE
            const unsigned seed_key = key ? key[pick] : 0U;  // ACTOR_BACKFACE_CONE: one key per meshlet
#endif
            for (;;) {
                done[pick] = 1; --remaining;
                if (strip_meshlet) strip_meshlet[pick] = u16(produced);
                for (unsigned k = 0; k < n[pick]; ++k) {
                    const unsigned tu = cid[scid[pick] + k];
                    if (stamp[tu] != serial) {
                        stamp[tu] = u16(serial); local[tu] = u8(nrec); rec[nrec++] = u16(tu);
                        if (!keep_order)
                            for (unsigned o = occ_start[tu]; o < occ_start[tu + 1]; ++o) {
                                const unsigned j = occ[o];
                                if (done[j]) continue;
                                if (!score[j]) candidates[ncand++] = u16(j);
                                ++score[j];
                            }
                    }
                    idx[nidx++] = u8(local[tu] | (k + 1 == n[pick] ? 0x80U : 0U));
                }
                ntri += n[pick] - 2U;
                if (!remaining) break;
                // Next strip: most shared tuples that still fits.
                unsigned best = ~0U, best_score = 0;
                for (unsigned q = 0; q < ncand; ++q) {
                    const unsigned j = candidates[q];
                    if (done[j]) continue;
#if RE4DC_ACTOR_BACKFACE_CONE
                    if (key && key[j] != seed_key) continue;
#endif
                    if (nrec + distinct[j] - score[j] > kMaxVertices || nidx + n[j] > kMaxIndices) continue;
                    if (score[j] > best_score || (score[j] == best_score && j < best)) { best = j; best_score = score[j]; }
                }
                if (best == ~0U) {
                    // Nothing adjacent fits (always, in keep_order mode): the
                    // first unused strip in order, if it fits.
                    while (next < count && done[next]) ++next;
#if RE4DC_ACTOR_BACKFACE_CONE
                    if (next < count && (!key || key[next] == seed_key)) {
#else
                    if (next < count) {
#endif
                        unsigned fresh = 0;
                        for (unsigned k = 0; k < n[next]; ++k) {
                            const unsigned tu = cid[scid[next] + k];
                            if (stamp[tu] != serial && stamp[tu] != 0xFFFE) { stamp[tu] = 0xFFFE; ++fresh; }  // count once
                        }
                        for (unsigned k = 0; k < n[next]; ++k) {
                            const unsigned tu = cid[scid[next] + k];
                            if (stamp[tu] == 0xFFFE) stamp[tu] = 0xFFFF;
                        }
                        if (nrec + fresh <= kMaxVertices && nidx + n[next] <= kMaxIndices) best = next;
                    }
                }
                if (best == ~0U) break;
                pick = best;
            }
            for (unsigned q = 0; q < ncand; ++q) score[candidates[q]] = 0;
            if (!emit(rec, nrec, idx, nidx, ntri)) return false;
            ++produced;
        }
        return true;
    }

    // Step 2 for strips [first, last).
    bool pack(unsigned first, unsigned last, unsigned corners, bool keep_order) {
        const unsigned count = last - first;
        const bool whole = kLodBuild && lod && !keep_order && first == 0 && last == strip_count;
        unsigned hash_size = 16;
        while (hash_size < corners * 2U) hash_size <<= 1;
        u16* hash = arena.take<u16>(hash_size);
        u32* tuple_corner = arena.take<u32>(corners);   // stream offset of the tuple's first corner
        u16* cid = arena.take<u16>(corners);            // per corner: tuple
        u16* strip_cid = arena.take<u16>(count);        // first cid of each strip
        u16* n = arena.take<u16>(count);
        if (!hash || !tuple_corner || !cid || !strip_cid || !n) ACTOR_REJECT();
        u16* strip_meshlet = whole ? arena.take<u16>(count) : nullptr;
        rec_tuple = whole && strip_meshlet ? arena.take<u16>(corners) : nullptr;
        std::memset(hash, 0, hash_size * 2U);
        unsigned tuples = 0, c = 0;
        for (unsigned i = 0; i < count; ++i) {
            const Strip& t = strips[first + i];
            strip_cid[i] = u16(c); n[i] = t.n;
            for (unsigned k = 0; k < t.n; ++k, ++c) {
                const u8* v = corner(t, k);
                unsigned h = hash_of(v) & (hash_size - 1);
                while (hash[h] && !same_tuple(p.stream + tuple_corner[hash[h] - 1], v)) h = (h + 1) & (hash_size - 1);
                if (!hash[h]) { tuple_corner[tuples] = u32(v - p.stream); hash[h] = u16(++tuples); }
                cid[c] = u16(hash[h] - 1);
            }
        }
        const unsigned meshlet0 = meshlets;
        Arena keep = arena;
        if (!cluster(count, n, strip_cid, cid, tuples, corners, keep_order, strip_meshlet,
                     [&](const u16* rec, unsigned nrec, const u8* idx, unsigned nidx, unsigned ntri) {
                         return finish(rec, nrec, idx, nidx, ntri, tuple_corner);
                     }
#if RE4DC_ACTOR_BACKFACE_CONE
                     , skey ? skey + first : nullptr
#endif
                     ))
            return false;
        arena = keep;
        if (kLodBuild && rec_tuple && meshlet0 == 0) build_levels(count, n, strip_cid, cid, tuples, tuple_corner, strip_meshlet);
        rec_tuple = nullptr;
        return true;
    }

    void key_of(unsigned tuple, const u32* tuple_corner, u16 f[4]) const {
        const u8* c = p.stream + tuple_corner[tuple];
        f[0] = u16(be16(c)); f[1] = u16(be16(c + 2)); f[2] = u16(be16(c + stride - 2)); f[3] = u16(ci_of(c));
    }
    unsigned sort_hi(const u16* f) const { return (s.position_palette(f[0]) << 16) | s.normal_palette(f[1]); }

    bool finish(const u16* rec, unsigned nrec, const u8* idx, unsigned nidx, unsigned ntri, const u32* tuple_corner) {
        if (!nidx) return true;
        if (meshlets == strip_count) ACTOR_REJECT();
        // Step 3: order records by (position palette, normal palette, vi).
        u8 order[kMaxVertices], remap[kMaxVertices];
        u32 key_hi[kMaxVertices], key_lo[kMaxVertices];
        u16 f[kMaxVertices][4];
        for (unsigned i = 0; i < nrec; ++i) {
            key_of(rec[i], tuple_corner, f[i]);
            order[i] = u8(i);
            key_hi[i] = sort_hi(f[i]);
            key_lo[i] = (u32(f[i][0]) << 16) | f[i][1];
        }
        for (unsigned i = 1; i < nrec; ++i) {
            const u8 o = order[i];
            unsigned j = i;
            while (j && (key_hi[order[j - 1]] > key_hi[o] || (key_hi[order[j - 1]] == key_hi[o] && key_lo[order[j - 1]] > key_lo[o]))) {
                order[j] = order[j - 1]; --j;
            }
            order[j] = o;
        }
        for (unsigned i = 0; i < nrec; ++i) remap[order[i]] = u8(i);
        const unsigned bytes = nrec * rs * 2U;
        if (used + bytes > capacity || records + nrec > 0xFFFFU || idx_used + nidx > corner_total) ACTOR_REJECT();
        u16* r = reinterpret_cast<u16*>(out + used);
        for (unsigned i = 0; i < nrec; ++i) {
            const u16* e = f[order[i]];
            u16* d = r + i * rs;
            d[0] = e[0]; d[1] = e[1]; d[2] = e[2];
            if (!constant_color) d[3] = e[3];
            track(e[0]);
            track_uv(e[2]);
            if (rec_tuple) rec_tuple[records + i] = rec[order[i]];
        }
        u8* d = idx_all + idx_used;
        for (unsigned i = 0; i < nidx; ++i) d[i] = u8(remap[idx[i] & 127U] | (idx[i] & 128U));
        infos[meshlets++] = {Counts::of(nrec, nidx, ntri), u16(records), u16(idx_used)};
        records += nrec; idx_used += nidx; used += bytes; triangles += ntri;
#if defined(RE4DC_ACTOR_TEST)
        ++test_meshlets; test_records += nrec; test_indices += nidx;
#endif
        return true;
    }
    void track(unsigned vi) {
        const u8* base = s.positions ? s.positions : p.positions;
        const unsigned st = s.positions ? 8U : p.position_stride;
        const unsigned count = s.positions ? s.position_count : p.position_count;
        if (!base || vi >= count) return;
        const short* v = reinterpret_cast<const short*>(base + vi * st);
        for (unsigned a = 0; a < 3; ++a) { lo[a] = std::min(lo[a], float(v[a])); hi[a] = std::max(hi[a], float(v[a])); }
        any_bounds = true;
    }
    void track_uv(unsigned ti) {
        if (!p.uv) return;
        const u8* t = p.uv + ti * 4U;
        const bool s16 = (p.flags & 0x80000000U) != 0;
        for (unsigned k = 0; k < 2; ++k) {
            const int x = s16 ? int(*reinterpret_cast<const short*>(t + k * 2)) : int(*reinterpret_cast<const u16*>(t + k * 2));
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            uv_excess = re4dc::format32::uv_certificate_add(uv_excess, x);
#else
            unsigned a = unsigned(x < 0 ? -x : x), bits = 0;
            if (!a) continue;
            while (!(a & 1U)) a >>= 1;  // significant bits: trailing zeros dropped
            while (a >> bits) ++bits;
            if (bits > 8 && bits - 8 > uv_excess) uv_excess = bits - 8;
#endif
        }
    }
    void bounds(BlobHeader& h) const {
        const float q = pow2(-int(p.shift));
        float r2 = 0.0f;
        for (unsigned a = 0; a < 3; ++a) {
            h.center[a] = any_bounds ? (lo[a] + hi[a]) * 0.5f * q : 0.0f;
            const float e = any_bounds ? (hi[a] - lo[a]) * 0.5f * q : 0.0f;
            r2 += e * e;
        }
        h.radius = std::sqrt(r2);
    }

    // ---- LOD ---------------------------------------------------------------
    // Part-wide simplifier state (arena, released after build_levels).
    struct Lod {
        unsigned V = 0, F = 0, alive_count = 0, heap_n = 0;
        u16* tpos;          // tuple -> position
        float* P;           // position xyz (object units)
        float* Q;           // position quadric (10)
        u16* head;          // position -> first incidence node (t * 3 + k), 0xFFFF none
        u8* pflag;          // 1 locked, 2 gone, 4 cost stale (recomputed when it reaches the top)
        float* cost; u16* best; u16* heap; u16* hpos;
        u16* tri;           // 3 tuples per triangle
        u8* alive;
        u16* next;          // incidence list links
        u16* rep;           // collapsed position -> the position it went to
    };
    static constexpr float kInf = 1e30f;
    static constexpr u16 kNone = 0xFFFF;

    static void plane_quadric(const float* a, const float* b, const float* c, float q[10]) {
        const float e1[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]}, e2[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
        float n[3] = {e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]};
        const float l = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
        for (unsigned i = 0; i < 10; ++i) q[i] = 0.0f;
        if (!(l > 0.0f)) return;
        n[0] /= l; n[1] /= l; n[2] /= l;
        const float v[4] = {n[0], n[1], n[2], -(n[0] * a[0] + n[1] * a[1] + n[2] * a[2])};
        unsigned k = 0;
        for (unsigned i = 0; i < 4; ++i) for (unsigned j = i; j < 4; ++j) q[k++] = v[i] * v[j];
    }
    static float eval_quadric(const float* q, const float* r, const float* v) {
        float a[10];
        for (unsigned i = 0; i < 10; ++i) a[i] = q[i] + r[i];
        const float x = v[0], y = v[1], z = v[2];
        const float e = a[0] * x * x + 2 * a[1] * x * y + 2 * a[2] * x * z + 2 * a[3] * x + a[4] * y * y + 2 * a[5] * y * z +
                        2 * a[6] * y + a[7] * z * z + 2 * a[8] * z + a[9];
        return e > 0.0f ? std::sqrt(e) : 0.0f;
    }
    static bool normal_of(const float* a, const float* b, const float* c, float n[3]) {
        const float e1[3] = {b[0] - a[0], b[1] - a[1], b[2] - a[2]}, e2[3] = {c[0] - a[0], c[1] - a[1], c[2] - a[2]};
        n[0] = e1[1] * e2[2] - e1[2] * e2[1]; n[1] = e1[2] * e2[0] - e1[0] * e2[2]; n[2] = e1[0] * e2[1] - e1[1] * e2[0];
        const float l = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
        if (!(l > 1e-12f)) return false;
        n[0] /= l; n[1] /= l; n[2] /= l;
        return true;
    }
    // Collapse a -> b valid? Fills map (a's tuples -> b's tuples, <= 16).
    static bool collapse_map(const Lod& L, unsigned a, unsigned b, u16* from, u16* to, unsigned& nmap) {
        nmap = 0;
        for (unsigned node = L.head[a]; node != kNone; node = L.next[node]) {
            const unsigned t = node / 3;
            if (!L.alive[t]) continue;
            const u16* c = L.tri + t * 3;
            int ka = -1, kb = -1;
            for (int k = 0; k < 3; ++k) { if (L.tpos[c[k]] == a) ka = k; if (L.tpos[c[k]] == b) kb = k; }
            if (kb < 0 || ka < 0) continue;
            unsigned i = 0;
            while (i < nmap && from[i] != c[ka]) ++i;
            if (i < nmap) { if (to[i] != c[kb]) return false; continue; }
            if (nmap == 16) return false;
            from[nmap] = c[ka]; to[nmap] = c[kb]; ++nmap;
        }
        if (!nmap) return false;
        for (unsigned node = L.head[a]; node != kNone; node = L.next[node]) {
            const unsigned t = node / 3;
            if (!L.alive[t]) continue;
            const u16* c = L.tri + t * 3;
            bool has_b = false; unsigned ta = kNone;
            for (int k = 0; k < 3; ++k) { if (L.tpos[c[k]] == b) has_b = true; if (L.tpos[c[k]] == a) ta = c[k]; }
            unsigned i = 0;
            while (i < nmap && from[i] != ta) ++i;
            if (i == nmap) return false;  // a record of a has no counterpart at b: would tear a seam
            if (has_b) continue;
            float p0[3][3], n0[3], n1[3];
            for (int k = 0; k < 3; ++k) std::memcpy(p0[k], L.P + L.tpos[c[k]] * 3, 12);
            if (!normal_of(p0[0], p0[1], p0[2], n0)) continue;
            for (int k = 0; k < 3; ++k) if (L.tpos[c[k]] == a) std::memcpy(p0[k], L.P + b * 3, 12);
            if (!normal_of(p0[0], p0[1], p0[2], n1) || n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2] < 0.25f) return false;
        }
        return true;
    }
    // Cheapest collapse of position a. validate = false (after neighbourhood
    // changes): cost order only; the pop re-checks validity and falls back
    // to validate = true (candidates in cost order until one is valid).
    static void prune(Lod& L, unsigned a) {  // drop dead triangles from a's incidence list
        for (u16* link = &L.head[a]; *link != kNone;) {
            if (!L.alive[*link / 3]) *link = L.next[*link];
            else link = &L.next[*link];
        }
    }
    static void compute(Lod& L, unsigned a, bool validate) {
        L.cost[a] = kInf;
        L.pflag[a] &= 3;
        if (L.pflag[a]) return;
        prune(L, a);
        u16 nb[32]; unsigned nn = 0;
        for (unsigned node = L.head[a]; node != kNone; node = L.next[node]) {
            const unsigned t = node / 3;
            if (!L.alive[t]) continue;
            for (int k = 0; k < 3; ++k) {
                const unsigned q = L.tpos[L.tri[t * 3 + k]];
                if (q == a) continue;
                unsigned i = 0;
                while (i < nn && nb[i] != q) ++i;
                if (i == nn) { if (nn == 32) return; nb[nn++] = u16(q); }
            }
        }
        float c[32];
        for (unsigned i = 0; i < nn; ++i) c[i] = eval_quadric(L.Q + a * 10, L.Q + nb[i] * 10, L.P + nb[i] * 3);
        if (!validate) {
            unsigned b = 0;
            for (unsigned i = 1; i < nn; ++i) if (c[i] < c[b]) b = i;
            if (nn) { L.cost[a] = c[b]; L.best[a] = nb[b]; }
            return;
        }
        for (unsigned i = 1; i < nn; ++i) {  // by cost
            const float cv = c[i]; const u16 bv = nb[i];
            unsigned j = i;
            while (j && c[j - 1] > cv) { c[j] = c[j - 1]; nb[j] = nb[j - 1]; --j; }
            c[j] = cv; nb[j] = bv;
        }
        u16 from[16], to[16]; unsigned nmap;
        for (unsigned i = 0; i < nn; ++i)
            if (collapse_map(L, a, nb[i], from, to, nmap)) { L.cost[a] = c[i]; L.best[a] = nb[i]; return; }
    }
    static void heap_fix(Lod& L, unsigned a) {
        unsigned i = L.hpos[a];
        while (i && L.cost[L.heap[(i - 1) / 2]] > L.cost[a]) {
            L.heap[i] = L.heap[(i - 1) / 2]; L.hpos[L.heap[i]] = u16(i); i = (i - 1) / 2;
        }
        for (;;) {
            unsigned c = i * 2 + 1;
            if (c >= L.heap_n) break;
            if (c + 1 < L.heap_n && L.cost[L.heap[c + 1]] < L.cost[L.heap[c]]) ++c;
            if (!(L.cost[L.heap[c]] < L.cost[a])) break;
            L.heap[i] = L.heap[c]; L.hpos[L.heap[i]] = u16(i); i = c;
        }
        L.heap[i] = u16(a); L.hpos[a] = u16(i);
    }
    // Neighbour positions of a (<= cap).
    static unsigned neighbours(const Lod& L, unsigned a, u16* out, unsigned cap) {
        unsigned n = 0;
        for (unsigned node = L.head[a]; node != kNone; node = L.next[node]) {
            const unsigned t = node / 3;
            if (!L.alive[t]) continue;
            for (int k = 0; k < 3; ++k) {
                const unsigned q = L.tpos[L.tri[t * 3 + k]];
                if (q == a) continue;
                unsigned i = 0;
                while (i < n && out[i] != q) ++i;
                if (i == n && n < cap) out[n++] = u16(q);
            }
        }
        return n;
    }
    static void collapse(Lod& L, unsigned a, unsigned b) {
        u16 from[16], to[16]; unsigned nmap;
        collapse_map(L, a, b, from, to, nmap);
        u16 near_a[64];
        const unsigned na = neighbours(L, a, near_a, 64);
        for (unsigned node = L.head[a], nx; node != kNone; node = nx) {
            nx = L.next[node];
            const unsigned t = node / 3;
            if (!L.alive[t]) continue;
            u16* c = L.tri + t * 3;
            bool has_b = false;
            for (int k = 0; k < 3; ++k) has_b |= L.tpos[c[k]] == b;
            if (has_b) { L.alive[t] = 0; --L.alive_count; continue; }
            const unsigned k = node % 3;
            for (unsigned i = 0; i < nmap; ++i) if (from[i] == c[k]) { c[k] = to[i]; break; }
            L.next[node] = L.head[b]; L.head[b] = u16(node);
        }
        L.head[a] = kNone; L.pflag[a] = 2; L.rep[a] = u16(b);
        for (unsigned i = 0; i < 10; ++i) L.Q[b * 10 + i] += L.Q[a * 10 + i];
        L.cost[a] = kInf; heap_fix(L, a);
        // a's former neighbours gained the candidate b (their best may drop):
        // now. b and its other neighbours only lost or got dearer candidates
        // (Q[b] grew): marked stale, recomputed if they reach the top.
        for (unsigned i = 0; i < na; ++i)
            if (near_a[i] != b && !(L.pflag[near_a[i]] & 3)) { compute(L, near_a[i], false); heap_fix(L, near_a[i]); }
        u16 near_b[64];
        const unsigned nb = neighbours(L, b, near_b, 64);
        if (!(L.pflag[b] & 3)) L.pflag[b] |= 4;
        for (unsigned i = 0; i < nb; ++i) if (!(L.pflag[near_b[i]] & 3)) L.pflag[near_b[i]] |= 4;
    }

    void build_levels(unsigned count, const u16* n, const u16* scid, const u16* cid, unsigned tuples,
                      const u32* tuple_corner, const u16* strip_meshlet) {
        Arena mark = arena;
        const unsigned used0 = used;
#if defined(RE4DC_ACTOR_TEST)
        const double t0 = test_now_us();
#endif
        if (!levels_impl(count, n, scid, cid, tuples, tuple_corner, strip_meshlet)) { levels = 0; used = used0; }
#if defined(RE4DC_ACTOR_TEST)
        test_lod_us += test_now_us() - t0;
#endif
        arena = mark;
    }

    bool levels_impl(unsigned count, const u16* n, const u16* scid, const u16* cid, unsigned tuples,
                     const u32* tuple_corner, const u16* strip_meshlet) {
        Lod L;
        for (unsigned i = 0; i < count; ++i) L.F += n[i] - 2U;
        if (L.F < kLodMinTriangles || L.F * 3U >= kNone) return false;
        // positions: vi -> position id
        unsigned hs = 16;
        while (hs < tuples * 2U) hs <<= 1;
        u16* ph = arena.take<u16>(hs);
        u16* pvi = arena.take<u16>(tuples);
        L.tpos = arena.take<u16>(tuples);
        u16* tmesh = arena.take<u16>(tuples);  // tuple -> meshlet, kNone when in several
        if (!ph || !pvi || !L.tpos || !tmesh) return false;
        std::memset(ph, 0xFF, hs * 2U);
        for (unsigned t = 0; t < tuples; ++t) {
            const unsigned vi = be16(p.stream + tuple_corner[t]);
            unsigned h = (vi * 2654435761U) & (hs - 1);
            while (ph[h] != kNone && pvi[ph[h]] != vi) h = (h + 1) & (hs - 1);
            if (ph[h] == kNone) { pvi[L.V] = u16(vi); ph[h] = u16(L.V++); }
            L.tpos[t] = ph[h];
        }
        for (unsigned t = 0; t < tuples; ++t) tmesh[t] = 0xFFFE;
        for (unsigned m = 0; m < meshlets; ++m)
            for (unsigned o = infos[m].first; o < infos[m].first + infos[m].n.vertices(); ++o) {
                u16& x = tmesh[rec_tuple[o]];
                x = x == 0xFFFE ? u16(m) : (x == m ? x : kNone);
            }
        L.P = arena.take<float>(L.V * 3); L.Q = arena.take<float>(L.V * 10);
        L.head = arena.take<u16>(L.V); L.pflag = arena.take<u8>(L.V);
        L.cost = arena.take<float>(L.V); L.best = arena.take<u16>(L.V);
        L.heap = arena.take<u16>(L.V); L.hpos = arena.take<u16>(L.V);
        L.tri = arena.take<u16>(L.F * 3); L.alive = arena.take<u8>(L.F); L.next = arena.take<u16>(L.F * 3);
        L.rep = arena.take<u16>(L.V);
        u16* tri_mesh = arena.take<u16>(L.F);
        if (!L.P || !L.Q || !L.head || !L.pflag || !L.cost || !L.best || !L.heap || !L.hpos || !L.tri || !L.alive ||
            !L.next || !L.rep || !tri_mesh) return false;
        const u8* pos = s.positions ? s.positions : p.positions;
        const unsigned ps = s.positions ? 8U : p.position_stride;
        const unsigned pc = s.positions ? s.position_count : p.position_count;
        const float q = pow2(-int(p.shift));
        for (unsigned v = 0; v < L.V; ++v) {
            if (!pos || pvi[v] >= pc) return false;
            const short* x = reinterpret_cast<const short*>(pos + pvi[v] * ps);
            L.P[v * 3] = x[0] * q; L.P[v * 3 + 1] = x[1] * q; L.P[v * 3 + 2] = x[2] * q;
            L.head[v] = kNone; L.pflag[v] = 0; L.rep[v] = u16(v);
            for (unsigned i = 0; i < 10; ++i) L.Q[v * 10 + i] = 0.0f;
        }
        // positions whose records live in more than one meshlet stay (each
        // level keeps its triangles inside their level-0 meshlet)
        {
            u16* pm = pvi;  // reuse: position -> meshlet (0xFFFF multi)
            for (unsigned v = 0; v < L.V; ++v) pm[v] = 0xFFFE;
            for (unsigned t = 0; t < tuples; ++t) {
                u16& m = pm[L.tpos[t]];
                m = tmesh[t] == kNone ? kNone : m == 0xFFFE ? tmesh[t] : (m == tmesh[t] ? m : kNone);
            }
            for (unsigned v = 0; v < L.V; ++v) if (pm[v] == kNone) L.pflag[v] = 1;
        }
        // triangles (position-degenerate ones are dropped from every level)
        unsigned f = 0;
        for (unsigned i = 0; i < count; ++i)
            for (unsigned j = 0; j + 2 < n[i]; ++j) {
                u16 c[3] = {cid[scid[i] + j], cid[scid[i] + j + 1], cid[scid[i] + j + 2]};
                if (j & 1) std::swap(c[0], c[1]);
                if (L.tpos[c[0]] == L.tpos[c[1]] || L.tpos[c[1]] == L.tpos[c[2]] || L.tpos[c[0]] == L.tpos[c[2]]) continue;
                for (unsigned k = 0; k < 3; ++k) {
                    L.tri[f * 3 + k] = c[k];
                    const unsigned v = L.tpos[c[k]];
                    L.next[f * 3 + k] = L.head[v]; L.head[v] = u16(f * 3 + k);
                }
                L.alive[f] = 1; tri_mesh[f] = strip_meshlet[i];
                float pq[10];
                plane_quadric(L.P + L.tpos[c[0]] * 3, L.P + L.tpos[c[1]] * 3, L.P + L.tpos[c[2]] * 3, pq);
                for (unsigned k = 0; k < 3; ++k) for (unsigned e = 0; e < 10; ++e) L.Q[L.tpos[c[k]] * 10 + e] += pq[e];
                ++f;
            }
        L.F = f; L.alive_count = f;
        if (f < kLodMinTriangles) return false;
        // open-boundary positions stay
        for (unsigned t = 0; t < f; ++t)
            for (unsigned k = 0; k < 3; ++k) {
                const unsigned a = L.tpos[L.tri[t * 3 + k]], b = L.tpos[L.tri[t * 3 + (k + 1) % 3]];
                unsigned shared = 0;
                for (unsigned node = L.head[a]; node != kNone; node = L.next[node]) {
                    const u16* c = L.tri + (node / 3) * 3;
                    shared += L.tpos[c[0]] == b || L.tpos[c[1]] == b || L.tpos[c[2]] == b;
                }
                if (shared == 1) L.pflag[a] = L.pflag[b] = 1;
            }
        L.heap_n = 0;
        for (unsigned v = 0; v < L.V; ++v) {
            compute(L, v, false);
            L.heap[L.heap_n] = u16(v); L.hpos[v] = u16(L.heap_n++);
            heap_fix(L, v);
        }

        // Snapshots: per level the alive triangles (tuples), grouped by meshlet
        // (snap_at[k][m] .. snap_at[k][m + 1]).
        u16* snap[kMaxLevels] = {};
        u32* snap_at[kMaxLevels] = {};
        u32* mesh_at = arena.take<u32>(meshlets + 1);   // level-0 triangles by meshlet
        u16* by_mesh = arena.take<u16>(f);
        if (!mesh_at || !by_mesh) return false;
        std::memset(mesh_at, 0, (meshlets + 1) * 4U);
        for (unsigned t = 0; t < f; ++t) ++mesh_at[tri_mesh[t] + 1];
        for (unsigned m = 0; m < meshlets; ++m) mesh_at[m + 1] += mesh_at[m];
        {
            u32* fill = snap_at[0] = arena.take<u32>(meshlets + 1);  // temporary cursor
            if (!fill) return false;
            std::memcpy(fill, mesh_at, meshlets * 4U);
            for (unsigned t = 0; t < f; ++t) by_mesh[fill[tri_mesh[t]]++] = u16(t);
        }
        float running = 0.0f;
        unsigned built = 0, last_count = f;
        for (unsigned k = 0; k < kMaxLevels; ++k) {
            const unsigned target = unsigned(float(f) * level_ladder[k]);
            while (L.alive_count > target && L.cost[L.heap[0]] < kInf) {
                const unsigned a = L.heap[0];
                if (L.pflag[a] & 4) { compute(L, a, false); heap_fix(L, a); continue; }
                u16 from[16], to[16]; unsigned nmap;
                if (!collapse_map(L, a, L.best[a], from, to, nmap)) { compute(L, a, true); heap_fix(L, a); continue; }
                running = std::max(running, L.cost[a]);
                collapse(L, a, L.best[a]);
            }
            if (L.alive_count * 10U > last_count * 9U) break;  // < 10% fewer than the previous level
            snap[k] = arena.take<u16>(L.alive_count * 4U);
            snap_at[k] = arena.take<u32>(meshlets + 1);
            if (!snap[k] || !snap_at[k]) break;
            unsigned m = 0;
            for (unsigned g = 0; g < meshlets; ++g) {
                snap_at[k][g] = m;
                for (unsigned i = mesh_at[g]; i < mesh_at[g + 1]; ++i) {
                    const unsigned t = by_mesh[i];
                    if (!L.alive[t]) continue;
                    std::memcpy(snap[k] + m * 4, L.tri + t * 3, 6); snap[k][m * 4 + 3] = u16(g); ++m;
                }
            }
            snap_at[k][meshlets] = m;
            last_count = m; built = k + 1;
            // Geometric error: every removed position's distance to the planes of
            // the triangles now around the position it collapsed into (the
            // nearest one), max over positions; never below the previous level.
            float err = k ? level_error[k - 1] : 0.0f;
            for (unsigned v = 0; v < L.V; ++v) {
                if ((L.pflag[v] & 3) != 2) continue;
                unsigned r = v;
                while ((L.pflag[r] & 3) == 2) r = L.rep[r];
                prune(L, r);
                float nearest = kInf;
                for (unsigned node = L.head[r]; node != kNone; node = L.next[node]) {
                    const unsigned t = node / 3;
                    if (!L.alive[t]) continue;
                    const u16* c = L.tri + t * 3;
                    float nrm[3];
                    const float* a = L.P + L.tpos[c[0]] * 3;
                    if (!normal_of(a, L.P + L.tpos[c[1]] * 3, L.P + L.tpos[c[2]] * 3, nrm)) continue;
                    const float* x = L.P + v * 3;
                    const float d = std::fabs(nrm[0] * (x[0] - a[0]) + nrm[1] * (x[1] - a[1]) + nrm[2] * (x[2] - a[2]));
                    if (d < nearest) nearest = d;
                }
                if (nearest < kInf && nearest > err) err = nearest;
            }
            level_error[k] = lod_metric_qem ? running : err;
            if (L.cost[L.heap[0]] >= kInf) break;
        }
        if (!built) return false;

        // Per meshlet: order records by the coarsest level using them (a
        // level's records are a prefix), then each level's index list.
        u8* lmap = arena.take<u8>(tuples);
        u16* lstamp = arena.take<u16>(tuples);
        u8* ltri = arena.take<u8>(kMaxIndices * 3);
        u8* lidx = arena.take<u8>(kMaxIndices * 2U);  // one level's list at a time
        u8* sused = arena.take<u8>(kMaxIndices);
        u16* sfirst = arena.take<u16>(kMaxVertices + 1);
        u16* slist = arena.take<u16>(kMaxIndices * 3);
        MeshletLevel* lt = arena.take<MeshletLevel>(meshlets * kMaxLevels);
        if (!lmap || !lstamp || !ltri || !lidx || !sused || !sfirst || !slist || !lt) return false;
        for (unsigned t = 0; t < tuples; ++t) lstamp[t] = kNone;
        // Level triangles of meshlet m in its (reordered) record numbering.
        auto level_triangles = [&](unsigned k, unsigned m) {
            unsigned nt = 0;
            for (unsigned t = snap_at[k][m]; t < snap_at[k][m + 1]; ++t) {
                const u16* c = snap[k] + t * 4;
                for (unsigned e = 0; e < 3; ++e) ltri[nt * 3 + e] = lmap[c[e]];
                ++nt;
            }
            return nt;
        };
        // Pass 1 per meshlet: order records by the coarsest level using them
        // (a level's records are a prefix), then size each level's strip list.
        for (unsigned m = 0; m < meshlets; ++m) {
            MeshletInfo& mi = infos[m];
            const unsigned nv = mi.n.vertices();
            u16* r = reinterpret_cast<u16*>(out + sizeof(BlobHeader)) + mi.first * rs;
            for (unsigned i = 0; i < nv; ++i) { lmap[rec_tuple[mi.first + i]] = u8(i); lstamp[rec_tuple[mi.first + i]] = u16(m); }
            u8 dlev[kMaxVertices] = {};
            for (unsigned k = 0; k < built; ++k)
                for (unsigned t = snap_at[k][m]; t < snap_at[k][m + 1]; ++t) {
                    const u16* c = snap[k] + t * 4;
                    for (unsigned e = 0; e < 3; ++e) {
                        if (lstamp[c[e]] != m) return false;  // never: collapses stay inside the meshlet
                        dlev[lmap[c[e]]] = u8(k + 1);
                    }
                }
            // new order: (level desc, palette key, vi); stable over the palette-sorted records
            u8 order[kMaxVertices], remap[kMaxVertices];
            for (unsigned i = 0; i < nv; ++i) order[i] = u8(i);
            for (unsigned i = 1; i < nv; ++i) {
                const u8 o = order[i];
                unsigned j = i;
                while (j && dlev[order[j - 1]] < dlev[o]) { order[j] = order[j - 1]; --j; }
                order[j] = o;
            }
            for (unsigned i = 0; i < nv; ++i) remap[order[i]] = u8(i);
            u16 tmp[kMaxVertices * 5];
            std::memcpy(tmp, r, nv * rs * 2U);
            u16 tt[kMaxVertices];
            for (unsigned i = 0; i < nv; ++i) {
                std::memcpy(r + i * rs, tmp + order[i] * rs, rs * 2U);
                tt[i] = rec_tuple[mi.first + order[i]];
            }
            for (unsigned i = 0; i < nv; ++i) { rec_tuple[mi.first + i] = tt[i]; lmap[tt[i]] = u8(i); }
            u8* d = idx_all + mi.index;
            for (unsigned i = 0; i < mi.n.indices(); ++i) d[i] = u8(remap[d[i] & 127U] | (d[i] & 128U));
            for (unsigned k = 0; k < built; ++k) {
                unsigned prefix = 0;
                for (unsigned i = 0; i < nv; ++i) prefix += dlev[order[i]] >= k + 1;
                const unsigned nt = level_triangles(k, m);
                const unsigned ni = nt ? stripify(ltri, nt, lidx, kMaxIndices * 2U, sused, sfirst, slist) : 0U;
                if (nt && !ni) return false;
                lt[k * meshlets + m] = {Counts::of(prefix, ni, nt), 0, 0};
            }
        }
        // Levels kept: the coarsest first while they fit in place (a finer
        // level never has shorter lists), so a large part keeps its far levels.
        level_start = (used + 3U) & ~3U;
        const unsigned limit = capacity - (meshlets * sizeof(MeshletInfo) + ((idx_used + 3U) & ~3U) + 8U +
                                           kMaxLevels * sizeof(LevelInfo));
        unsigned first = built, list_bytes = 0;
        while (first > 0) {
            unsigned add = 0;
            for (unsigned m = 0; m < meshlets; ++m) add += lt[(first - 1) * meshlets + m].n.indices();
            const unsigned need = ((list_bytes + add + 3U) & ~3U) + (built - first + 1U) * meshlets * sizeof(MeshletLevel);
            if (level_start + need > limit || list_bytes + add > 0xFFFFU) break;
            list_bytes += add; --first;
        }
        const unsigned keep = built - first;
        if (!keep) return false;
        // Pass 2: the kept levels' lists (restripified: the same lists).
        unsigned w = level_start;
        for (unsigned m = 0; m < meshlets; ++m) {
            const MeshletInfo& mi = infos[m];
            for (unsigned i = 0; i < mi.n.vertices(); ++i) lmap[rec_tuple[mi.first + i]] = u8(i);
            for (unsigned k = first; k < built; ++k) {
                MeshletLevel& e = lt[k * meshlets + m];
                const unsigned nt = level_triangles(k, m);
                const unsigned ni = nt ? stripify(ltri, nt, lidx, kMaxIndices * 2U, sused, sfirst, slist) : 0U;
                if (ni != e.n.indices()) return false;  // never: stripify is deterministic
                e.index = u16(w - level_start);
                std::memcpy(out + w, lidx, ni);
                w += ni;
            }
        }
        w = (w + 3U) & ~3U;
        for (unsigned j = 0; j < keep; ++j) {
            level_table[j] = w - level_start;
            std::memcpy(out + w, lt + (first + j) * meshlets, meshlets * sizeof(MeshletLevel));
            w += meshlets * sizeof(MeshletLevel);
            level_error[j] = level_error[first + j];
        }
        levels = keep; level_end = w; used = w;
#if defined(RE4DC_ACTOR_TEST)
        ++test_lod_parts; test_lod_bytes += level_end - level_start;
#endif
        return true;
    }

    // Final layout: header | table | records | indices | levels | directory
    // (add_bake_field later widens the records and appends a BakeBlock).
    bool assemble() {
        const unsigned R = records * rs * 2U, Ra = (R + 3U) & ~3U;
        const unsigned T0 = (meshlets * sizeof(MeshletInfo) + 3U) & ~3U, I = (idx_used + 3U) & ~3U;
        unsigned L = levels ? level_end - level_start : 0U;
        unsigned total = sizeof(BlobHeader) + T0 + Ra + I + L + levels * sizeof(LevelInfo);
        if (total > capacity && levels) { levels = 0; L = 0; total = sizeof(BlobHeader) + T0 + Ra + I; }
        if (total > capacity) ACTOR_REJECT();
        const unsigned rec_at = sizeof(BlobHeader) + T0, idx_at = rec_at + Ra, lvl_at = idx_at + I;
        const unsigned dir_at = lvl_at + L;
        if (L) std::memmove(out + lvl_at, out + level_start, L);
        std::memmove(out + rec_at, out + sizeof(BlobHeader), R);
        for (unsigned i = R; i < Ra; ++i) out[rec_at + i] = 0;
        std::memcpy(out + idx_at, idx_all, idx_used);
        for (unsigned i = idx_used; i < I; ++i) out[idx_at + i] = 0;
        auto* info = reinterpret_cast<MeshletInfo*>(out + sizeof(BlobHeader));
        for (unsigned i = 0; i < meshlets; ++i) {
            info[i] = infos[i];
        }
        for (unsigned i = meshlets * sizeof(MeshletInfo); i < T0; ++i) out[sizeof(BlobHeader) + i] = 0;
        for (unsigned k = 0; k < levels; ++k) {
            const LevelInfo li{level_error[k], u16((lvl_at + level_table[k]) / 4U), u16(lvl_at / 4U)};
            std::memcpy(out + dir_at + k * sizeof(LevelInfo), &li, sizeof(li));
        }
        BlobHeader h{};
        h.magic = kMagic; h.version = kVersion;
        h.flags = u8((constant_color ? 0 : kHasCi) | (std::min(uv_excess, 31U) << 2));
        h.levels = u8(levels);
        h.meshlets = u16(meshlets); h.color_index = u16(color);
        h.rec4 = u16(rec_at / 4U); h.idx4 = u16(idx_at / 4U);
        h.lod4 = u16(levels ? dir_at / 4U : 0U); h.bake4 = 0;
        bounds(h);
        std::memcpy(out, &h, sizeof(h));
        size = total;
#if defined(RE4DC_ACTOR_TEST)
        test_blob_bytes += total;
#endif
        if (total / 4U >= 0x10000U) ACTOR_REJECT();
        return true;
    }
};

#if RE4DC_ACTOR_BACKFACE_CONE
// ACTOR_BACKFACE_CONE cone table, in the stream's tail past the blob (the GX list bytes the blob no longer uses):
// AbcTail, then one AbcCone per level-0 meshlet. Valid while the tail's check word matches the blob header.
// A cone bounds every triangle the meshlet draws at any LOD level: all corners on palette entry `pal` (rigid parts: 0),
// raw positions within r of c, and every drawn-winding normal within theta_k = k * 90/63 deg of the unit axis a/32767.
struct AbcCone { short c[3]; u16 r; short a[3]; u8 k, pal; };
static_assert(sizeof(AbcCone) == 16, "abc cone");
struct AbcTail { u32 tag, meshlets, check, bytes; };  // bytes: stream bytes | class << 24
constexpr u32 kAbcTag = 0x31434241U;  // "ABC1"
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
constexpr u32 kAbcTag32 = 0x32434241U; // "ABC2": current source identity follows the tail
static_assert(sizeof(void*) != 4 || sizeof(re4dc::cone32::SourceIdentity) == 16, "SH4 cone source identity");
#endif
constexpr float kAbcStep = 1.5707963f / 63.0f;
u32 abc_check(const u8* stream, unsigned bytes) {
    u32 h = 2166136261U ^ bytes;
    for (unsigned i = 0; i < sizeof(BlobHeader); ++i) h = (h ^ (i == 2 ? stream[i] & 0x7FU : stream[i])) * 16777619U;
    return h;
}
unsigned abc_tail_at(unsigned bytes, unsigned meshlets) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    const unsigned header = sizeof(AbcTail) + sizeof(re4dc::cone32::SourceIdentity);
    if (!meshlets || bytes < header || meshlets > (bytes-header)/sizeof(AbcCone)) return 0;
    return (bytes-header-meshlets*sizeof(AbcCone)) & ~3U;
#endif
    const unsigned need = sizeof(AbcTail) + meshlets * sizeof(AbcCone);
    return bytes >= need ? (bytes - need) & ~3U : 0U;
}
const AbcCone* abc_table(const u8* stream, unsigned bytes, unsigned* cls = nullptr) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    if (!stream || bytes < sizeof(BlobHeader)) return nullptr;
#endif
    const BlobHeader& h = *reinterpret_cast<const BlobHeader*>(stream);
    const unsigned at = abc_tail_at(bytes, h.meshlets);
    if (!at) return nullptr;
    const AbcTail& t = *reinterpret_cast<const AbcTail*>(stream + at);
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    if (t.tag != kAbcTag32 || t.meshlets != h.meshlets || (t.bytes & 0xFFFFFFU) != bytes ||
        (t.bytes >> 24) > 4U || t.check != abc_check(stream, bytes)) return nullptr;
    if (cls) *cls = t.bytes >> 24;
    return reinterpret_cast<const AbcCone*>(stream + at + sizeof(AbcTail) + sizeof(re4dc::cone32::SourceIdentity));
#else
    if (t.tag != kAbcTag || t.meshlets != h.meshlets || (t.bytes & 0xFFFFFFU) != bytes || t.check != abc_check(stream, bytes))
        return nullptr;
    if (cls) *cls = t.bytes >> 24;
    return reinterpret_cast<const AbcCone*>(stream + at + sizeof(AbcTail));
#endif
}
// After a conversion (or a LOD rebuild) in place: size = the blob's bytes. Builds the cones of a split part.
void abc_build(const Re4dcModelPart& p, unsigned size, unsigned cls) {
    u8* stream = const_cast<u8*>(p.stream);
    const BlobHeader& h = *reinterpret_cast<const BlobHeader*>(stream);
    const unsigned at = abc_tail_at(p.stream_bytes, h.meshlets);
    if (!at || at < ((size + 3U) & ~3U)) { ++abc_noroom; return; }
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    // No earlier table survives an unsuccessful rebuild at this location.
    std::memset(stream + at, 0, sizeof(AbcTail) + sizeof(re4dc::cone32::SourceIdentity));
    if (p.position_stride == 8 && !p.static_geometry) return;
#endif
    const u8* pos = nullptr; unsigned count = 0; bool skinned = false;
    if (p.position_stride == 6) {
        Re4dcActorSource src{};
        if (!re4dc_actor_model_source(p.info, &src) || !src.positions || src.position_count != p.position_count) return;
        pos = src.positions; count = src.position_count; skinned = true;
    } else if (p.position_stride == 8 && p.positions) { pos = p.positions; count = p.position_count; }
    else return;
    const unsigned rs = 3U + ((h.flags & kHasCi) ? 1U : 0U) + ((h.flags & kHasBake) ? 1U : 0U);
    const auto* table = reinterpret_cast<const MeshletInfo*>(stream + sizeof(BlobHeader));
    const u16* records = reinterpret_cast<const u16*>(stream + h.rec4 * 4U);
    const LevelInfo* lv = h.levels && h.lod4 ? reinterpret_cast<const LevelInfo*>(stream + h.lod4 * 4U) : nullptr;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    AbcCone* out = reinterpret_cast<AbcCone*>(stream + at + sizeof(AbcTail) + sizeof(re4dc::cone32::SourceIdentity));
#else
    AbcCone* out = reinterpret_cast<AbcCone*>(stream + at + sizeof(AbcTail));
#endif
    for (unsigned mi = 0; mi < h.meshlets; ++mi) {
        AbcCone& cone = out[mi];
        cone = AbcCone{};
        const MeshletInfo& m = table[mi];
        const unsigned nv = m.n.vertices();
        const u16* r = records + m.first * rs;
        float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
        unsigned pal = ~0U; bool ok = nv > 0;
        for (unsigned i = 0; i < nv && ok; ++i) {
            const unsigned vi = r[i * rs];
            if (vi >= count) { ok = false; break; }
            const short* q = reinterpret_cast<const short*>(pos + vi * 8U);
            const unsigned qp = skinned ? unsigned(u16(q[3])) : 0U;
            if (pal == ~0U) pal = qp; else if (qp != pal) ok = false;
            for (unsigned a = 0; a < 3; ++a) { lo[a] = std::min(lo[a], float(q[a])); hi[a] = std::max(hi[a], float(q[a])); }
        }
        if (!ok || pal > 255U) { ++abc_nocone; continue; }
        // Every triangle drawn at level 0 and at each LOD level (pass 0: axis = sum of unit normals; pass 1: widest angle).
        float axis[3] = {0, 0, 0}, mincos = 1.0f;
        for (unsigned pass = 0; pass < 2; ++pass) {
            for (unsigned l = 0; l <= (lv ? h.levels : 0U); ++l) {
                const u8* idx; unsigned ni;
                if (!l) { idx = stream + h.idx4 * 4U + m.index; ni = m.n.indices(); }
                else {
                    const MeshletLevel& ml = reinterpret_cast<const MeshletLevel*>(stream + lv[l - 1].table4 * 4U)[mi];
                    idx = stream + lv[l - 1].lists4 * 4U + ml.index; ni = ml.n.indices();
                }
                for (unsigned s0 = 0; s0 < ni;) {
                    unsigned s1 = s0;
                    while (s1 < ni && !(idx[s1] & 128U)) ++s1;
                    for (unsigned j = s0; j + 2 <= s1; ++j) {
                        unsigned ia = idx[j] & 127U, ib = idx[j + 1] & 127U;
                        const unsigned ic = idx[j + 2] & 127U;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
                        if (ia >= nv || ib >= nv || ic >= nv) { ok = false; break; }
#endif
                        if ((j - s0) & 1U) std::swap(ia, ib);
                        float v[3][3];
                        const unsigned ii[3] = {ia, ib, ic};
                        for (unsigned k = 0; k < 3; ++k) {
                            const short* q = reinterpret_cast<const short*>(pos + r[(ii[k] < nv ? ii[k] : 0U) * rs] * 8U);
                            v[k][0] = float(q[0]); v[k][1] = float(q[1]); v[k][2] = float(q[2]);
                        }
                        const float e1[3] = {v[1][0] - v[0][0], v[1][1] - v[0][1], v[1][2] - v[0][2]};
                        const float e2[3] = {v[2][0] - v[0][0], v[2][1] - v[0][1], v[2][2] - v[0][2]};
                        float n[3] = {e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]};
                        const float ln = std::sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
                        if (!(ln > 1e-6f)) continue;  // zero area: drawn as nothing either way
                        n[0] /= ln; n[1] /= ln; n[2] /= ln;
                        if (!pass) { axis[0] += n[0]; axis[1] += n[1]; axis[2] += n[2]; }
                        else mincos = std::min(mincos, n[0] * axis[0] + n[1] * axis[1] + n[2] * axis[2]);
                    }
                    s0 = s1 + 1;
                }
            }
            if (!pass) {
                const float la = std::sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2]);
                if (!(la > 1e-6f)) { ok = false; break; }
                // quantised first: the angle is measured against the axis the runtime reads
                for (unsigned a = 0; a < 3; ++a) cone.a[a] = short(std::lrint(axis[a] / la * 32767.0f));
                const float lq = std::sqrt(float(cone.a[0]) * cone.a[0] + float(cone.a[1]) * cone.a[1] + float(cone.a[2]) * cone.a[2]);
                for (unsigned a = 0; a < 3; ++a) axis[a] = float(cone.a[a]) / lq;
            }
        }
        // theta + 1 degree (rounding of the runtime's float maths and the 1/32767 axis scale), < 80 degrees
        const float theta = std::acos(std::max(-1.0f, std::min(1.0f, mincos))) + 0.01745f;
        const unsigned k = unsigned(std::ceil(theta / kAbcStep));
        if (!ok || k < 1U || k > 56U) { cone = AbcCone{}; ++abc_nocone; continue; }
        float r2 = 0.0f;
        for (unsigned a = 0; a < 3; ++a) {
            const float c = std::floor((lo[a] + hi[a]) * 0.5f);
            cone.c[a] = short(c);
            const float e = std::max(hi[a] - c, c - lo[a]);
            r2 += e * e;
        }
        cone.r = u16(std::min(65535.0f, std::ceil(std::sqrt(r2)) + 2.0f));
        cone.k = u8(k); cone.pal = u8(pal);
        ++abc_cones;
    }
    AbcTail& t = *reinterpret_cast<AbcTail*>(stream + at);
    t = {kAbcTag, h.meshlets, abc_check(stream, p.stream_bytes), p.stream_bytes | (std::min(cls, 4U) << 24)};
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    const re4dc::cone32::SourceIdentity identity{reinterpret_cast<std::uintptr_t>(p.info),
        reinterpret_cast<std::uintptr_t>(pos), count, p.position_stride};
    std::memcpy(stream + at + sizeof(AbcTail), &identity, sizeof(identity));
    t.tag = kAbcTag32;
#endif
    ++abc_built;
}
#endif

// ----------------------------------------------------------- skin registry --
struct SkinEntry { const void* info; const void* positions; const float* palette; unsigned entries, materialized; };
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
enum : unsigned {
    kSkinRecipePending=2, kSkinRecipeNominee=3,
    kSkinRecipeDone=4, kSkinRecipeReady=5
};
#endif
#if defined(RE4DC_LEON_SKIN_SLOTS) && RE4DC_LEON_SKIN_SLOTS
// LEON_SKIN_SLOTS=1 (crowd.mk): r119 after movie 11900 registers 64 skins before Leon's transaction asks for its 9
// (MCHECK_LEONGC: SKINACQ why=4, registry full), which left Leon to the GameCube path.
// LEON_SKIN_SLOTS=2 (lane fix18 item 9): 112. Measured peak 105 live skins in the r119 fight (frames 946-1138, then
// back to ~20: transient, no leak; g3 through 11900 / 11910 / 11930 / 11920 peaks at 73), plus a margin of 7.
constexpr unsigned kSkins = RE4DC_LEON_SKIN_SLOTS == 2 ? 112 : 80;
#else
constexpr unsigned kSkins = 64;
#endif
SkinEntry skins[kSkins];
unsigned skin_count = 0, skin_frame = ~0U;
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
Re4dcActorSkinAdmission skin_admission_pending{};
unsigned skin_admission_serial;
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
extern bool skin_recipe_building;
bool skin_recipe_drop(SkinEntry&,unsigned);
bool skin_recipe_nominated(const SkinEntry&);
unsigned skin_recipe_registration_state(const SkinEntry&);
void skin_recipe_frame_retire();
#endif
#if RE4DC_ACTOR_SKIN_OWNER_POOL
SkinEntry* find_owned_skin(const void* info);
SkinEntry* find_ordinary_skin(const void* info, const void* positions) {
    for (unsigned i = 0; i < skin_count; ++i)
        if (skins[i].info == info && skins[i].positions == positions) return &skins[i];
    return nullptr;
}
SkinEntry* find_skin(const void* info, const void* positions) {
    // A materialized owned entry still shadows its ordinary lazy entry. Its
    // lease must fail; a lookup must not silently switch back to source data.
    if (!positions) if (SkinEntry* e = find_owned_skin(info)) return e;
    return find_ordinary_skin(info, positions);
}
#else
SkinEntry* find_skin(const void* info, const void* positions) {
    for (unsigned i = 0; i < skin_count; ++i)
        if (skins[i].info == info && skins[i].positions == positions) return &skins[i];
    return nullptr;
}
#endif


#if RE4DC_ACTOR_TRANSACTION
#if RE4DC_ACTOR_SKIN_OWNER_POOL
#include "include/native_actor_owner_pool.inc"
#else
#include "include/native_actor_owner_registry.inc"
#if RE4DC_ACTOR_SKIN_RESERVE
#include "include/native_actor_skin_reserve.inc"
#endif
#endif
#endif
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
#include "include/native_actor_skin_admit32.inc"
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
#include "include/native_actor_skin_recipe32.inc"
#endif

// ---------------------------------------------------------- info context --
enum Mode : unsigned { kRigid = 0, kSource = 1, kSkin = 2 };
struct Frame {  // per (info, matrices) per frame
    const void* info = nullptr;
    unsigned frame = ~0U, mode = kRigid;
    float modelview[12]{}, projection[7]{}, viewport[6]{};
    const u8* positions = nullptr; const u8* normals = nullptr;
    unsigned position_stride = 0, normal_stride = 0, position_count = 0, normal_count = 0;
    bool small_normals = true;
    const float* palette = nullptr; unsigned palette_entries = 0;
    float q = 1.0f, nq = 1.0f, near_distance = 0.0f, far_distance = 0.0f;
    alignas(8) float screen[16]{};  // rows X', Y', W, W (x modelview, x q unless skinned)
    float* skin_positions = nullptr;  // palette_entries x 16 (matrix_t) or nullptr
    float* skin_dirs = nullptr;       // palette_entries x 12: light directions per entry (current part)
    u8* skin_ready = nullptr;         // per entry: skin_positions entry built this frame
    u8* dirs_ready = nullptr;         // per entry: skin_dirs entry built for dirs_fold
    float dirs_fold[12]{};            // the light directions skin_dirs were built from
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
    unsigned table_owner14=0,table_source_frame14=~0u;
#endif
#if RE4DC_AVK
    bool avk_all = false;             // ACTOR_VTX_KERNEL: every skin_positions entry built (avk_build_all)
#endif
#if RE4DC_ACTOR_FOG_GATE
    bool gate_ready = false; float gate_T = 0.0f, gate_G = 0.0f;  // ACTOR_FOG_GATE skinned depth bound
#endif
};
constexpr unsigned kFrames = 4;
Frame frames[kFrames];
unsigned frame_victim = 0;
#if RE4DC_GC_ASSET_GATE
// Geometry origin only; this does not qualify pose/palette/Motion history.
struct GcAssetFrameUse { unsigned serial=0,mask=0;re4dc_gcasset::PayloadProof* payload=nullptr; };
GcAssetFrameUse gcasset_frame_uses[kFrames]{};
static_assert(kFrames==4 && (sizeof(void*)!=4 || sizeof(gcasset_frame_uses)==48),"price fixed geometry receipts");
void gcasset_frame_stamp(Frame& f){
    const auto& use=re4dc_gcasset::source_use;
    gcasset_frame_uses[&f-frames]={use.serial,use.mask,use.payload};
}
void gcasset_frame_check(Frame& f){
    const auto& saved=gcasset_frame_uses[&f-frames];auto& use=re4dc_gcasset::source_use;
    if(!saved.serial || saved.serial!=use.serial || saved.mask!=use.mask || saved.payload!=use.payload){use.serial=0;use.payload=nullptr;}
}
#endif

bool same_words(const float* a, const float* b, unsigned n) {
    const u32* x = reinterpret_cast<const u32*>(a); const u32* y = reinterpret_cast<const u32*>(b);
    for (unsigned i = 0; i < n; ++i) if (x[i] != y[i]) return false;
    return true;
}

// Frame workspace, two-ended: tables that live for the whole source frame
// (skin matrices, cached per Frame) come from the top; per-submit scratch
// (a transient conversion) from the bottom and is released by the submit.
unsigned workspace_top = 0, workspace_end = 0;
#if RE4DC_ACTOR_TRANSACTION
#include "include/native_actor_owner_workspace.inc"
#endif

void* scratch(unsigned bytes) {  // per submit
#if RE4DC_ACTOR_TRANSACTION
    if(bytes>UINT32_MAX-31u)return nullptr;
    bytes=(bytes+31u)&~31u;
    const unsigned end=workspace_scratch_limit();
    if(!workspace || workspace_top>end || bytes>end-workspace_top)return nullptr;
#else
    bytes = (bytes + 31U) & ~31U;
    if (!workspace || workspace_top + bytes > workspace_end) return nullptr;
#endif
    void* p = workspace + workspace_top; workspace_top += bytes; return p;
}
void* frame_table(unsigned bytes) {  // until the next re4dc_actor_frame
    bytes = (bytes + 31U) & ~31U;
    if (!workspace || workspace_end < workspace_top + bytes) return nullptr;
    workspace_end -= bytes;
    return workspace + workspace_end;
}
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
#include "include/native_actor_table_reuse14.inc"
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
#include "include/native_actor_pose_snapshot.inc"
#endif

// Rows of the combined projection (see native_actor.cpp): X'/W and Y'/W are
// the generic path's project() screen coordinates, W = -Zcamera.
void screen_rows(const Re4dcModelPart& p, float M[3][4]) {
    const float* m = p.modelview; const float* P = p.projection; const float* V = p.viewport;
    const float cx = (V[0] + V[2] * 0.5f) * RE4DC_SCREEN_WF / V[2];
    const float cy = (V[1] + V[3] * 0.5f) * RE4DC_SCREEN_HF / V[3];
    const float rows[3][3] = {{RE4DC_SCREEN_HALF_WF * P[1], 0.0f, RE4DC_SCREEN_HALF_WF * P[2] - cx},
                              {0.0f, -RE4DC_SCREEN_HALF_HF * P[3], -RE4DC_SCREEN_HALF_HF * P[4] - cy},
                              {0.0f, 0.0f, -1.0f}};
    for (unsigned r = 0; r < 3; ++r)
        for (unsigned c = 0; c < 4; ++c)
            M[r][c] = rows[r][0] * m[c] + rows[r][1] * m[4 + c] + rows[r][2] * m[8 + c];
}

Frame* prepare_frame(const Re4dcModelPart& p, float near_distance, float far_distance) {
    for (Frame& f : frames)
        if (f.frame == frame_serial && f.info == p.info &&
            same_words(f.modelview, p.modelview, 12) && same_words(f.projection, p.projection, 7) &&
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
            same_words(f.viewport, p.viewport, 6) && table14_current(f,p)) {
#else
            same_words(f.viewport, p.viewport, 6)) {
#endif
            // Mode is a function of (info, positions) within a frame.
#if RE4DC_GC_ASSET_GATE
            gcasset_frame_check(f);
#endif
            return &f;
        }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorFramePrepare, 1)
#endif
    Frame& f = frames[frame_victim]; frame_victim = (frame_victim + 1) % kFrames;
    f = Frame{};
#if RE4DC_GC_ASSET_GATE
    gcasset_frame_stamp(f);
#endif
    f.info = p.info; f.frame = frame_serial;
    std::memcpy(f.modelview, p.modelview, sizeof(f.modelview));
    std::memcpy(f.projection, p.projection, sizeof(f.projection));
    std::memcpy(f.viewport, p.viewport, sizeof(f.viewport));
    f.near_distance = near_distance; f.far_distance = far_distance;
    f.q = pow2(-int(p.shift));
    f.positions = p.positions; f.position_stride = p.position_stride; f.position_count = p.position_count;
    f.normals = p.normals; f.normal_stride = p.normal_stride; f.normal_count = p.normal_count;
    f.small_normals = p.normal_shift == 6; f.nq = pow2(-int(p.normal_shift));
    f.mode = p.position_stride == 8 ? kRigid : kSource;
    if (p.position_stride == 6) {
        unsigned entries = 0;
        const float* palette = re4dc_actor_skin_palette(p.info, p.positions, &entries);
        Re4dcActorSource src{};
        if (palette && entries && re4dc_actor_model_source(p.info, &src) && src.positions && src.normals &&
            src.position_count == p.position_count && src.normal_count == p.normal_count &&
            bool(src.small_normals) == (p.normal_shift == 6)) {
            f.mode = kSkin; f.palette = palette; f.palette_entries = entries;
            f.positions = src.positions; f.position_stride = 8;
            f.normals = src.normals; f.normal_stride = src.small_normals ? 4U : 8U;
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
            table14_prepare(f,p,entries);
#else
            // One skin table at a time (parts arrive info by info): an older
            // skinned Frame is dropped from the cache and its table reused.
            for (Frame& o : frames)
                if (&o != &f && o.skin_positions) {
                    o.frame = ~0U; o.skin_positions = o.skin_dirs = nullptr; o.skin_ready = o.dirs_ready = nullptr;
                }
            workspace_end = workspace_bytes;
#endif
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
            f.skin_positions = static_cast<float*>(frame_table(entries * (16U * 4U + 1U)));
            if (f.skin_positions) {
                f.skin_ready = reinterpret_cast<u8*>(f.skin_positions + entries * 16U);
                std::memset(f.skin_ready, 0, entries);
#else
            f.skin_positions = static_cast<float*>(frame_table(entries * (28U * 4U + 2U)));
            if (f.skin_positions) {
                f.skin_dirs = f.skin_positions + entries * 16U;
                f.skin_ready = reinterpret_cast<u8*>(f.skin_dirs + entries * 12U);
                f.dirs_ready = f.skin_ready + entries;
                std::memset(f.skin_ready, 0, entries * 2U);
#endif
#if RE4DC_AVK
                f.avk_all = false;
#endif
                f.dirs_fold[0] = NAN;  // no directions built yet
            }
            ++stats.skinned_parts;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
            if (!f.skin_positions) re4dc::dfa26::hit(re4dc::dfa26::ActorSkinTable);
        } else {
            re4dc::dfa26::hit(re4dc::dfa26::ActorSkinSource);
#endif
        }
    }
    float M[3][4];
    screen_rows(p, M);
    const float s = f.mode == kSkin ? 1.0f : f.q;
    for (unsigned c = 0; c < 4; ++c) {
        const float k = c < 3 ? s : 1.0f;
        f.screen[c * 4 + 0] = M[0][c] * k; f.screen[c * 4 + 1] = M[1][c] * k;
        f.screen[c * 4 + 2] = M[2][c] * k; f.screen[c * 4 + 3] = M[2][c] * k;
    }
    ++stats.info_preparations;
    return &f;
}

// Combined matrix of palette entry i (skinned): screen x [R_i*q | t_i].
// ACTOR_SKIN_FTRV (render only): the four columns go through FTRV with the screen matrix in
// XMTRX instead of the scalar mul4. The only consumer loads the result into XMTRX right after
// (pass_positions), so XMTRX is free here.
#ifndef RE4DC_ACTOR_SKIN_FTRV
#define RE4DC_ACTOR_SKIN_FTRV 0
#endif
#if RE4DC_ACTOR_SKIN_FTRV == 2
// Check build: the scalar matrix is computed too and the FTRV one compared with it.
extern "C" void re4dc_log(const char* fmt, ...);
float skin_chk_px = 0.0f;
unsigned skin_chk_n = 0, skin_chk_pts = 0, skin_chk_q = 0, skin_chk_1 = 0, skin_chk_near = 0, skin_chk_nan = 0;
inline bool skin_finite(float v) {
    u32 b;
    std::memcpy(&b, &v, 4);
    return ((b >> 23) & 255U) != 255U;
}
#endif
void skin_position_matrix(const Frame& f, unsigned i, float out[16]) {
    const float* P = f.palette + i * 12;  // reordered ROMtx: columns R0,R1,R2,t
#if RE4DC_ACTOR_SKIN_FTRV && defined(__sh__) && !defined(ACTOR_TEST_XMTRX)
    const float q = f.q;
    load_xmtrx(f.screen);
    for (unsigned c = 0; c < 3; ++c) {
        float x = P[c * 3] * q, y = P[c * 3 + 1] * q, z = P[c * 3 + 2] * q, w = 0.0f;
        mat_trans_nodiv(x, y, z, w);
        out[c * 4] = x; out[c * 4 + 1] = y; out[c * 4 + 2] = z; out[c * 4 + 3] = w;
    }
    float x = P[9], y = P[10], z = P[11], w = 1.0f;
    mat_trans_nodiv(x, y, z, w);
    out[12] = x; out[13] = y; out[14] = z; out[15] = w;
#if RE4DC_ACTOR_SKIN_FTRV == 2
    {
        // Eight corners 50 units around the bone origin (raw = model / q for columns 0-2), projected
        // through both matrices; only points past the near plane and on screen count.
        float ref[16];
        for (unsigned c = 0; c < 4; ++c) {
            const float v[4] = {P[c * 3] * (c < 3 ? f.q : 1.0f), P[c * 3 + 1] * (c < 3 ? f.q : 1.0f),
                                P[c * 3 + 2] * (c < 3 ? f.q : 1.0f), c < 3 ? 0.0f : 1.0f};
            mul4(f.screen, v, ref + c * 4);
        }
        const float h = 50.0f / f.q;
        for (unsigned k = 0; k < 8; ++k) {
            const float v[4] = {(k & 1) ? h : -h, (k & 2) ? h : -h, (k & 4) ? h : -h, 1.0f};
            float a4[4], b4[4];
            mul4(out, v, a4);
            mul4(ref, v, b4);
            // Before any filter: both results finite, and the same side of the near plane.
            for (unsigned j = 0; j < 4; ++j)
                if (!skin_finite(a4[j]) || !skin_finite(b4[j])) { ++skin_chk_nan; break; }
            if ((b4[3] <= f.near_distance) != (a4[3] <= f.near_distance)) ++skin_chk_near;
            if (b4[3] <= f.near_distance || a4[3] <= f.near_distance) continue;
            const float bx = b4[0] / b4[3], by = b4[1] / b4[3];
            if (__builtin_fabsf(bx) > 1400.0f || __builtin_fabsf(by) > 1100.0f) continue;
            float d = __builtin_fabsf(a4[0] / a4[3] - bx);
            const float dy = __builtin_fabsf(a4[1] / a4[3] - by);
            if (dy > d) d = dy;
            ++skin_chk_pts;
            if (d > skin_chk_px) skin_chk_px = d;
            if (d > 0.25f) ++skin_chk_q;
            if (d > 1.0f) ++skin_chk_1;
        }
        if ((++skin_chk_n & 0xFFFF) == 0)
            re4dc_log("SKINFTRV builds=%u points=%u max_px=%.4f over_0.25px=%u over_1px=%u near_mismatch=%u "
                      "nonfinite=%u\n", skin_chk_n, skin_chk_pts, double(skin_chk_px), skin_chk_q, skin_chk_1,
                      skin_chk_near, skin_chk_nan);
    }
#endif
#else
    for (unsigned c = 0; c < 4; ++c) {
        const float v[4] = {P[c * 3] * (c < 3 ? f.q : 1.0f), P[c * 3 + 1] * (c < 3 ? f.q : 1.0f),
                            P[c * 3 + 2] * (c < 3 ? f.q : 1.0f), c < 3 ? 0.0f : 1.0f};
        mul4(f.screen, v, out + c * 4);
    }
#endif
}
const float* position_matrix(Frame& f, unsigned i, float* fallback) {
    if (i >= f.palette_entries) i = 0;
    if (!f.skin_positions) { skin_position_matrix(f, i, fallback); return fallback; }
    float* m = f.skin_positions + i * 16;
    if (!f.skin_ready[i]) { skin_position_matrix(f, i, m); f.skin_ready[i] = 1; }
    return m;
}

// ---------------------------------------------------------------- lights --
// The source-selected GX lights folded into <=3 directional lights in the
// normals' own space plus a colour matrix: lit = min(cap, C * (m0,m1,m2,1))
// with m_l = d_l + |d_l| (= 2 max(0, n.l_l)); C carries 0.5 x colour x scale
// in columns 0..2 and ambient x scale in column 3. Same per-object
// approximation (evaluated at the part centre) as native_actor.cpp.
struct Lights {
#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29
    const re4dc::fallback29::Bake* scan29_bake = nullptr;
    unsigned scan29_gain[3]{};
#endif
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    Re4dcActorLight25Colour colour25;
#endif
#if RE4DC_ACTOR_SETUP_LEAN && RE4DC_ACTOR_NO_CLEAR
    // Every successful fold (including the constant/probe paths) calls lights_reset before reading these.
    // Probe declines fall through to build_lights, which also resets. Keep the fields not reset below initialized.
    bool fast, constant;
    unsigned count;
    u32 constant_rgb;
    float dir[3][4];
    alignas(8) float color[16];
    const SourceLighting* source;
#else
    bool fast = false;       // directional fold valid: diffuse clamp, <=3 lights, caps 255
    bool constant = false;   // lighting disabled: one colour for every vertex
    unsigned count = 0;
    u32 constant_rgb = 0;
    float dir[3][4]{};       // normal space, x nq (w = 0)
    alignas(8) float color[16]{};
    const SourceLighting* source = nullptr;
#endif
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS && !RE4DC_ACTOR_EXACT_FAST && !RE4DC_ACTOR_LIGHT_FAST_ONLY
#error STATUE_LIGHTS=2 needs ACTOR_EXACT_FAST (the exact evaluator adds the ambient share)
#endif
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
    bool exact_ready = false;  // STATUE_LIGHTS=2: build_lights already filled the prepared set (strongest 3)
    float extra[3]{};          // STATUE_LIGHTS=2: the dropped lights' share, added to the ambient start
#endif
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
#if RE4DC_ACTOR_NO_CLEAR
    // ACTOR_NO_CLEAR: the exact path's prepared lights are not default-initialised (~0.4 KB per Lights): they are
    // read only by pass_lights_exact, after a fold that returned false, and the callers assign them on that return.
    union PreparedSlot { re4dc::render::PreparedSourceLights v; PreparedSlot() {} } prepared_slot;
#else
    re4dc::render::PreparedSourceLights prepared;
#endif
#endif
#if RE4DC_ACTOR_SETUP_LEAN && RE4DC_ACTOR_NO_CLEAR
    float view_dot[3];
#if RE4DC_ACTOR_PROBE_LIGHT
    bool probe;
#endif
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
    bool half_post;
#endif
#else
    float view_dot[3]{};     // light . direction from the part centre to the camera (view space)
#if RE4DC_ACTOR_PROBE_LIGHT
    bool probe = false;      // ACTOR_PROBE_LIGHT: the actor's probe (ambient + one direction)
#endif
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
    bool half_post = false;  // LEON_LIGHT_HEADROOM: a 2x-texture part outside the owner path, folded at full scale and
                             // halved per vertex after the pass (the 1x look: the fast kernel's cap stays 1.0x)
#endif
#endif
};
// The fold's start state. MEMSET_LEAN=1 (crowd.mk; render only): every field but `prepared` is reset; prepared is
// read only by pass_lights_exact (a fold that returned false), and the callers assign it on that return.
#if RE4DC_ACTOR_NO_CLEAR
#define RE4DC_PREPARED(L) ((L).prepared_slot.v)
#else
#define RE4DC_PREPARED(L) ((L).prepared)
#endif
inline void lights_reset(Lights& L) {
#if (defined(RE4DC_MEMSET_LEAN) && RE4DC_MEMSET_LEAN) || RE4DC_ACTOR_NO_CLEAR
    L.fast = false; L.constant = false; L.count = 0; L.constant_rgb = 0;
    for (unsigned i = 0; i < 3; ++i) { for (unsigned c = 0; c < 4; ++c) L.dir[i][c] = 0.0f; L.view_dot[i] = 0.0f; }
    for (unsigned i = 0; i < 16; ++i) L.color[i] = 0.0f;
    L.source = nullptr;
#if RE4DC_ACTOR_PROBE_LIGHT
    L.probe = false;
#endif
#if RE4DC_ACTOR_NO_CLEAR && defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
    L.half_post = false;  // build_lights only ever sets it (a Lights reused across parts must start clear)
#endif
#else
    L = Lights{};
#endif
}
#if defined(RE4DC_LEON_LIGHT_HEADROOM) && RE4DC_LEON_LIGHT_HEADROOM
// LEON_LIGHT_HEADROOM: Leon's lit record (LEON_SOURCE_LIGHT marks it in normal_matrix[3]) and its colour gain.
inline bool leon_record(const SourceLighting& S) { return S.normal_matrix[3] == 1.0e30f; }
inline float leon_gain(const SourceLighting& S) {
#if defined(RE4DC_LEON_LIGHT_TOGGLE) && RE4DC_LEON_LIGHT_TOGGLE
    if (re4dc_leon_light_mode == 1) return 1.0f;  // PROBE: full scale here, halved per vertex after the pass
#endif
    return leon_record(S) ? 0.5f : 1.0f;
}
#endif

#ifndef RE4DC_LEON_LIGHT_HEADROOM
#define RE4DC_LEON_LIGHT_HEADROOM 0
#endif
#ifndef RE4DC_LEON_LIGHT_TOGGLE
#define RE4DC_LEON_LIGHT_TOGGLE 0
#endif
#if RE4DC_LEON_LIGHT_HEADROOM
// LEON_LIGHT_HEADROOM=1 (crowd.mk; lane lp2; render only; default 0): Leon's textures are stored at 2x on the disc
// (tools/d367/charbake/cb_headroom.py) and every Leon vertex colour is halved, so the PVR's 1.0x modulate cap becomes
// 2.0x of the original texel (the GameCube TEV x2/x4 and the PS2 GS 0x80 = 1.0 have the same headroom). The flat
// record is 128 (coarse_actor_transaction.inc); here the lit records (LEON_SOURCE_LIGHT's marker) take x0.5 after
// the fast fold's caps check, so the folds and kernels are unchanged and only the colour matrix differs.
// LEON_LIGHT_TOGGLE=1 (debug builds, DBG_WARP + LOOK_TOGGLE): the mode cycles live (hold X, D-pad right, START):
//   0 FLAT (test 10)   one colour, 128 (= test 10's 255 on the 2x textures)
//   1 PROBE            the probe at full scale, then halved per vertex: test 10's 1.0x cap (35-45% darker than flat)
//   2 PROBE+HEADROOM   the probe at x0.5: lit vertices reach 2.0x
//   3 FLAT WARM        one colour per part: the hue of the room's GameCube light set (ambient + the lights
//                      LightSetModel picked for Leon, per room and frame), brightest channel 128
#endif
#ifndef RE4DC_GIGANTE_LIGHTS
#define RE4DC_GIGANTE_LIGHTS 0
#endif
#ifndef RE4DC_ACTOR_LIGHT_CAP
#define RE4DC_ACTOR_LIGHT_CAP 0
#endif
#if RE4DC_ACTOR_LIGHT_CAP && !RE4DC_GIGANTE_LIGHTS && !RE4DC_ACTOR_LIGHT_FAST_ONLY
#error ACTOR_LIGHT_CAP needs GIGANTE_LIGHTS (the light fold)
#endif
#ifndef RE4DC_LEON_LIGHT_FILL
#define RE4DC_LEON_LIGHT_FILL 0
#endif
#ifndef RE4DC_ACTOR_PROBE_LIGHT
#define RE4DC_ACTOR_PROBE_LIGHT 0
#endif
#ifndef RE4DC_GIGANTE_LIGHTS_TREES
#define RE4DC_GIGANTE_LIGHTS_TREES 0
#endif
#if RE4DC_GIGANTE_LIGHTS
// GIGANTE_LIGHTS=1/2 (render only): parts of El Gigante (em2b, cModel id 0x2B; with GIGANTE_LIGHTS_TREES=1 also
// cEmTree 0x49) whose torch lights exceed the three-direction fold keep the 1 + 2 = 3 (or 2) strongest lights by
// contribution at the part centre (colour x attenuation) as directions and fold the rest into the ambient term with
// the mean of max(0, n.l) over the camera-facing hemisphere, (1 + l.v) / 4, so overall brightness is kept. Parts
// with <= 3 lights fold as before. 0 = exact (the generic per-vertex path).
unsigned gigante_folds;  // parts folded to `keep` lights (logged with the census)
unsigned gigante_keep(const Re4dcModelPart& p) {
    const int id = re4dc_actor_model_id(p.model);
    if (id == 0x2B || (RE4DC_GIGANTE_LIGHTS_TREES && id == 0x49)) return RE4DC_GIGANTE_LIGHTS == 2 ? 2U : 3U;
#if defined(RE4DC_GANADO_LIGHT_FOLD) && RE4DC_GANADO_LIGHT_FOLD
    // PS2_GANADO_LIT (game30.mk): the lit Ganados (em10..em20 classes, 0x10..0x20) keep the 3 strongest lights per
    // part + ambient, as the PS2 lights its characters per vertex, instead of the exact per-vertex path.
    if (id >= 0x10 && id <= 0x20) return 3U;
#endif
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS
    // STATUE_LIGHTS=2: the r226 statue (cObjRobo, object 0x37) takes the exact 3-light evaluator in build_lights.
    if (id < 0 && re4dc_actor_obj_id(p.model) == 0x37) return 3U;
#endif
#if RE4DC_ACTOR_LIGHT_CAP
    // ACTOR_LIGHT_CAP (barn28.mk): every other model folds the same way (3 strongest lights + ambient share).
    return 3U;
#endif
    return 0U;
}
#endif
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
// The marker's normal transform belongs to the current role, including exact lighting.
// PreparedSourceLights contains lamps only; it does not transform vertex normals.
// Keep this bounded calculation outside every vertex loop and leave the captured GX record untouched.
bool leon_part_normal(const float m[12], float N[12]) {
    const float a00 = m[0], a01 = m[1], a02 = m[2], a10 = m[4], a11 = m[5], a12 = m[6], a20 = m[8], a21 = m[9], a22 = m[10];
    const float c00 = a11 * a22 - a12 * a21, c01 = a12 * a20 - a10 * a22, c02 = a10 * a21 - a11 * a20;
    const float det = a00 * c00 + a01 * c01 + a02 * c02;
    if (det == 0.0f || !re4dc::render::is_finite(det)) return false;
    const float r = 1.0f / det;
    N[0] = c00 * r; N[1] = c01 * r; N[2] = c02 * r; N[3] = 0.0f;
    N[4] = (a02 * a21 - a01 * a22) * r; N[5] = (a00 * a22 - a02 * a20) * r; N[6] = (a01 * a20 - a00 * a21) * r; N[7] = 0.0f;
    N[8] = (a01 * a12 - a02 * a11) * r; N[9] = (a02 * a10 - a00 * a12) * r; N[10] = (a00 * a11 - a01 * a10) * r; N[11] = 0.0f;
    for (unsigned i = 0; i < 12; ++i) if (!re4dc::render::is_finite(N[i])) return false;
    return true;
}
#endif
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
// BARN28_DIAG (barn28.mk; diagnostic, default 0): parts that leave the fast light fold, by model (enemy id / object
// id), reason (1 per-vertex colour, 2 diffuse/scale, 3 fourth light) and significant lights; the exact pass adds its
// vertices. One B28L line per row every 300 actor frames.
}  // namespace
extern "C" int re4dc_b28_model_kind(const void* model);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
extern "C" void re4dc_log(const char* fmt, ...);
#endif
namespace {
namespace b28 {
struct Row { int id, obj; unsigned reason, parts, verts, lights_max, fast_parts; };
Row rows[48]; unsigned nrows, reason, nlights, cur = 0xffffffffU, last;
unsigned key(const Re4dcModelPart& p) {
    const int id = re4dc_b28_model_kind(p.model), obj = 0;
    for (unsigned i = 0; i < nrows; ++i) if (rows[i].id == id && rows[i].obj == obj && rows[i].reason == reason) return i;
    if (nrows == 48) return 47;
    rows[nrows] = Row{id, obj, reason, 0, 0, 0, 0};
    return nrows++;
}
void note(const Re4dcModelPart& p, bool fast) {
    if (fast) { reason = 0; nlights = 0; }
    const unsigned i = key(p);
    if (fast) { ++rows[i].fast_parts; cur = 0xffffffffU; return; }
    ++rows[i].parts; if (nlights > rows[i].lights_max) rows[i].lights_max = nlights;
    cur = i;
}
void verts(unsigned n) { if (cur < 48) rows[cur].verts += n; }
bool note_ret(const Re4dcModelPart& p, bool fast) { note(p, fast); return fast; }
void window(unsigned frame) {
    if (frame - last < 300) return;
    for (unsigned i = 0; i < nrows; ++i) {
        const Row& r = rows[i];
        re4dc_log("B28L f=%u frames=%u id=%d obj=%d why=%u slow_parts=%u verts=%u lights_max=%u fast_parts=%u\n", frame,
                  frame - last, r.id, r.obj, r.reason, r.parts, r.verts, r.lights_max, r.fast_parts);
    }
    nrows = 0; last = frame;
}
}  // namespace b28
#define B28_WHY(x) (b28::reason = (x))
#define B28_NOTE(p, v) b28::note_ret((p), (v))
#else
#define B28_WHY(x) ((void) 0)
#define B28_NOTE(p, v) (v)
#endif
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
bool build_lights(const Re4dcModelPart& p, const Frame& f, const float center[3], Lights& L) {
    const SourceLighting& S = *p.lighting;
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
    b28::reason = 0; b28::nlights = 0;
    for (unsigned i = 0; i < 8; ++i) if (S.mask & (1U << i)) ++b28::nlights;
#endif
#if RE4DC_GIGANTE_LIGHTS
    const unsigned keep = gigante_keep(p);
#endif
    lights_reset(L);
    L.source = &S;
    constexpr float k = 1.0f / 255.0f;
    float scale[3], ambient[3];
    bool caps255 = true;
#if RE4DC_LEON_LIGHT_HEADROOM
    // re4dc_model_submit's x0.5 record (normal_matrix[7] marker; tev_scale already halved): a draw of Leon's 2x textures
    // outside his owner path. The constant colour uses the halved scale; the fast fold runs at full scale and the
    // vertices are halved after the pass (half_post), so it keeps the fast kernel and draws exactly the 1x look.
    const bool hr_half = S.normal_matrix[7] == 1.0e30f;
    for (unsigned c = 0; c < 3; ++c) {
        scale[c] = S.material[c] * k * S.tev_scale * 255.0f;
        ambient[c] = S.enable ? S.ambient[c] * k : 1.0f;
        caps255 &= (hr_half ? 2.0f * scale[c] : scale[c]) >= 255.0f;
    }
#else
    for (unsigned c = 0; c < 3; ++c) {
        scale[c] = S.material[c] * k * S.tev_scale * 255.0f;
        ambient[c] = S.enable ? S.ambient[c] * k : 1.0f;
        caps255 &= scale[c] >= 255.0f;
    }
#endif
#if RE4DC_ACTOR_LIGHT_CAP
    // ACTOR_LIGHT_CAP (user 10-28, no per-vertex fallback): a per-vertex colour record folds with its constant
    // ambient/material (approximation); B28_WHY still records it.
    if (S.ambient_vertex || S.material_vertex) B28_WHY(1);
#else
    if (S.ambient_vertex || S.material_vertex) { DFA26_MODEL_HIT(ActorLightVertex, 1) B28_WHY(1); return false; }  // per-vertex colour: slow path
#endif
    if (!S.enable) {
        L.constant = true;
        L.constant_rgb = (channel(std::min(ambient[0], 1.0f) * scale[0]) << 16) |
                         (channel(std::min(ambient[1], 1.0f) * scale[1]) << 8) | channel(std::min(ambient[2], 1.0f) * scale[2]);
        return true;
    }
#if RE4DC_ACTOR_LIGHT_CAP
    if (S.diffuse != 2 || !caps255) B28_WHY(2);  // folds anyway (clamped diffuse, the fast kernel's 1.0x cap)
#else
    if (S.diffuse != 2 || !caps255) { DFA26_MODEL_HIT(ActorLightScale, 1) B28_WHY(2); return false; }
#endif
#if RE4DC_LEON_LIGHT_HEADROOM
    { const float g = leon_gain(S); for (unsigned c = 0; c < 3; ++c) scale[c] *= g; }
    if (hr_half) { for (unsigned c = 0; c < 3; ++c) scale[c] *= 2.0f; L.half_post = true; }
#endif
    const float* m = p.modelview;
    const float px = m[0] * center[0] + m[1] * center[1] + m[2] * center[2] + m[3];
    const float py = m[4] * center[0] + m[5] * center[1] + m[6] * center[2] + m[7];
    const float pz = m[8] * center[0] + m[9] * center[1] + m[10] * center[2] + m[11];
    const float* N = S.normal_matrix;
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
    // LEON_SOURCE_LIGHT (crowd.mk): a record marked per part (normal_matrix[3], an unused translation word) takes this
    // part's own normal matrix, (modelview 3x3)^-T, since Leon's roles do not share one rotation.
    float Np[12];
    if (N[3] == 1.0e30f) {
        if (!leon_part_normal(m, Np)) DFA26_MODEL_SLOW(ActorLightBasis, 1, return false;)
        N = Np;
    }
#endif
    float col[3][3]{};
    const float c2 = px * px + py * py + pz * pz, cr = c2 > 0.0f ? -1.0f / std::sqrt(c2) : 0.0f;
#if RE4DC_GIGANTE_LIGHTS
    float cand_dir[8][4], cand_vd[8], cand_col[8][3], cand_w[8];
    unsigned cands = 0;
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
    unsigned cand_i[8];
    const bool statue_exact = keep && re4dc_actor_obj_id(p.model) == 0x37;
#endif
#endif
    for (unsigned i = 0; i < 8; ++i) {
        if (!(S.mask & (1U << i))) continue;
        const SourceLight& s = S.lights[i];
        float lx = s.position[0] - px, ly = s.position[1] - py, lz = s.position[2] - pz;
        const float d2 = lx * lx + ly * ly + lz * lz, d = std::sqrt(d2);
        if (d > 0.0f) { const float r = 1.0f / d; lx *= r; ly *= r; lz *= r; }
        else { lx = 0.0f; ly = 0.0f; lz = 1.0f; }
        float attenuation = 1.0f;
        if (S.attenuation == 1) {
            const float cosine = std::max(0.0f, lx * s.direction[0] + ly * s.direction[1] + lz * s.direction[2]);
            const float angular = std::max(0.0f, s.a[0] + s.a[1] * cosine + s.a[2] * cosine * cosine);
            const float denominator = s.k[0] + s.k[1] * d + s.k[2] * d2;
            attenuation = denominator > 0.0f ? angular / denominator : 0.0f;
        }
        if (s.k[1] != 0.0f || s.k[2] != 0.0f) ++stats.attenuated_lights;
        const float red = s.color[0] * k * attenuation, green = s.color[1] * k * attenuation,
                    blue = s.color[2] * k * attenuation;
        if (std::max(red, std::max(green, blue)) <= 1.0f / 1024.0f) continue;
#if RE4DC_GIGANTE_LIGHTS
        if (keep) {  // collect every significant light; chosen after the loop
            float* o = cand_dir[cands];
            o[0] = (N[0] * lx + N[4] * ly + N[8] * lz) * f.nq;
            o[1] = (N[1] * lx + N[5] * ly + N[9] * lz) * f.nq;
            o[2] = (N[2] * lx + N[6] * ly + N[10] * lz) * f.nq;
            o[3] = 0.0f;
            cand_vd[cands] = (lx * px + ly * py + lz * pz) * cr;
            cand_col[cands][0] = red; cand_col[cands][1] = green; cand_col[cands][2] = blue;
            cand_w[cands] = std::max(red, std::max(green, blue));
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
            cand_i[cands] = i;
#endif
            ++cands;
            continue;
        }
#endif
        if (L.count == 3) { DFA26_MODEL_HIT(ActorLightOverflow, 1) B28_WHY(3); return false; }  // fourth significant light: slow path
        float* o = L.dir[L.count];
        o[0] = (N[0] * lx + N[4] * ly + N[8] * lz) * f.nq;
        o[1] = (N[1] * lx + N[5] * ly + N[9] * lz) * f.nq;
        o[2] = (N[2] * lx + N[6] * ly + N[10] * lz) * f.nq;
        o[3] = 0.0f;
        L.view_dot[L.count] = (lx * px + ly * py + lz * pz) * cr;
        col[L.count][0] = red; col[L.count][1] = green; col[L.count][2] = blue;
        ++L.count;
    }
#if RE4DC_GIGANTE_LIGHTS
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
    if (statue_exact) {
        // STATUE_LIGHTS=2: the exact per-vertex evaluator (per-vertex direction and attenuation) on the 3 lights
        // strongest at the part, the rest as a directionless ambient share (mean clamped Lambert, 1/4).
        auto& P = RE4DC_PREPARED(L);
        P.count = 0;
        bool used[8]{};
        for (unsigned l = 0; l < cands && l < 3U; ++l) {
            unsigned best = 8;
            for (unsigned j = 0; j < cands; ++j)
                if (!used[j] && (best == 8 || cand_w[j] > cand_w[best])) best = j;
            used[best] = true;
            P.lights[P.count++] = S.lights[cand_i[best]];
        }
        for (unsigned j = 0; j < cands; ++j)
            if (!used[j]) for (unsigned c = 0; c < 3; ++c) L.extra[c] += 0.25f * cand_col[j][c];
        L.exact_ready = true;
        L.count = 0;
        return false;
    }
#endif
    if (keep) {
        // Strongest first (ties keep the source order); the first `limit` become directions, the rest ambient.
        const unsigned limit = cands > 3 ? keep : 3U;
        bool used[8]{};
        for (unsigned l = 0; l < cands && l < limit; ++l) {
            unsigned best = 8;
            for (unsigned j = 0; j < cands; ++j)
                if (!used[j] && (best == 8 || cand_w[j] > cand_w[best])) best = j;
            used[best] = true;
            std::memcpy(L.dir[L.count], cand_dir[best], sizeof(L.dir[0]));
            L.view_dot[L.count] = cand_vd[best];
            for (unsigned c = 0; c < 3; ++c) col[L.count][c] = cand_col[best][c];
            ++L.count;
        }
        for (unsigned j = 0; j < cands; ++j) {
            if (used[j]) continue;
            const float w = std::max(0.0f, 0.25f * (1.0f + cand_vd[j]));
            for (unsigned c = 0; c < 3; ++c) ambient[c] += w * cand_col[j][c];
        }
        if (cands > limit) ++gigante_folds;
    }
#endif
    // Colour matrix (matrix_t: [column][row]); input (m0, m1, m2, 1).
    for (unsigned l = 0; l < 3; ++l)
        for (unsigned c = 0; c < 3; ++c) L.color[l * 4 + c] = 0.5f * col[l][c] * scale[c];
    for (unsigned c = 0; c < 3; ++c) L.color[12 + c] = ambient[c] * scale[c];
    L.fast = true;
    ++stats.light_sets;
    return true;
}

#if RE4DC_ACTOR_LIGHT_CAP
// ACTOR_LIGHT_CAP=1 (barn28.mk; render only, approximation, default 0; user 10-28 "simple lighting that doesn't fall
// back to per-vertex lighting at all"): no actor part reaches the exact per-vertex evaluator. More than three
// significant lights fold the three strongest + ambient share (gigante_keep: every model); per-vertex colour records
// fold with their constant ambient/material; a diffuse/scale record outside the fold's exact conditions folds anyway.
// Anything still unfolded (no invertible normal basis, ...) draws one flat colour: never the exact evaluator.
void flat_fallback(const Re4dcModelPart& p, Lights& L) {
    const SourceLighting& S = *p.lighting;
    lights_reset(L);
    L.source = &S;
    L.constant = true;
    float rgb[3];
    for (unsigned c = 0; c < 3; ++c) {
        float a = S.enable ? S.ambient[c] / 255.0f : 1.0f;
        if (S.enable) for (unsigned i = 0; i < 8; ++i) if (S.mask & (1U << i)) a += 0.25f * S.lights[i].color[c] / 255.0f;
        rgb[c] = S.material[c] * std::min(a, 1.0f) * S.tev_scale;
    }
    L.constant_rgb = (channel(rgb[0]) << 16) | (channel(rgb[1]) << 8) | channel(rgb[2]);
}
#define RE4DC_CAP_EXACT(p, c, L) flat_fallback((p), (L))
#else
#define RE4DC_CAP_EXACT(p, c, L) ((void) 0)
#endif

#endif
#if RE4DC_ACTOR_PROBE_LIGHT
// ACTOR_PROBE_LIGHT=1/2 (crowd.mk; render only; default 0): one light probe per actor per frame. The GX light set that
// LightSetModel selected for the actor (the record LEON_SOURCE_LIGHT / PS2_GANADO_LIT capture, dynamic lights
// included) is evaluated once, at the actor's origin, into ambient + one directional light (the L0 + L1 spherical
// harmonic fit of the clamped-cosine sum: V = sum(luma(C_i) l_i), coherence a = |V| / sum(luma(C_i)); a x sum(C_i)
// directional along V / |V|, .25 (1 - a) sum(C_i) added to the ambient). Every part of that actor then lights with
// that one direction in its own normal space (Leon: the part's (modelview 3x3)^-T, as LEON_SOURCE_LIGHT; Ganados: the
// shared record's normal matrix) through the existing fast kernel: no per-part light loop, no exact evaluator.
// =1 Leon (the marked record); =2 also the Ganado classes 0x10..0x20: near tier per vertex, mid/far one colour per
// part from the probe (as CROWD_FLAT). The source record is never written.
#ifndef RE4DC_ACTOR_PROBE_LIGHT_LOG
#define RE4DC_ACTOR_PROBE_LIGHT_LOG 600
#endif
extern "C" int re4dc_actor_model_id(const void* model);  // model_bridge.cpp
extern "C" void re4dc_log(const char* fmt, ...);
struct ProbeEntry {
    const void* model = nullptr;
    const SourceLighting* source = nullptr;
    unsigned serial = 0;
    bool ok = false;
    float v[3]{};     // view space, unit (the dominant direction toward the lights)
    float dcol[3]{};  // directional colour (x 1/255 units, attenuated)
    float amb[3]{};   // ambient + folded residual
    float view_dot = 0.0f;
    float coherence = 0.0f;  // |V| / sum luma (actor_light_probe.h)
};
constexpr unsigned kProbeEntries = 8;
ProbeEntry probe_cache[kProbeEntries];
unsigned probe_next = 0;
struct ProbeStats { unsigned built, reused, parts, leon, ganado, declined, last; } probe_stats{};
bool probe_eligible(const Re4dcModelPart& p) {
    const SourceLighting& S = *p.lighting;
    if (!S.enable || S.ambient_vertex || S.material_vertex || S.diffuse != 2) return false;
    if (S.normal_matrix[3] == 1.0e30f) return true;  // Leon (LEON_SOURCE_LIGHT capture)
#if RE4DC_ACTOR_PROBE_LIGHT >= 2
#if RE4DC_GANADO_LIT_TOGGLE
    if (re4dc_ganlit_mode == 0) return false;  // GANADO_LIT_TOGGLE mode 0: Ganados as test 15 (build_lights, flat)
#endif
    const int id = re4dc_actor_model_id(p.model);
    if (id >= 0x10 && id <= 0x20) return true;
#endif
    return false;
}
const ProbeEntry& probe_of(const Re4dcModelPart& p) {
    const SourceLighting& S = *p.lighting;
    for (unsigned i = 0; i < kProbeEntries; ++i) {
        const ProbeEntry& e = probe_cache[i];
        if (e.serial == frame_serial && e.model == p.model && e.source == &S) { ++probe_stats.reused; return e; }
    }
    ProbeEntry& e = probe_cache[probe_next];
    probe_next = (probe_next + 1U) % kProbeEntries;
    e = ProbeEntry{};
    e.model = p.model; e.source = &S; e.serial = frame_serial;
    ++probe_stats.built;
    const float px = p.modelview[3], py = p.modelview[7], pz = p.modelview[11];  // the actor's first part's origin
    if (!re4dc::render::is_finite(px) || !re4dc::render::is_finite(py) || !re4dc::render::is_finite(pz)) return e;
    constexpr float k = 1.0f / 255.0f;
    float vec[3]{}, total[3]{}, weight = 0.0f;
    for (unsigned i = 0; i < 8; ++i) {
        if (!(S.mask & (1U << i))) continue;
        const SourceLight& s = S.lights[i];
        float lx = s.position[0] - px, ly = s.position[1] - py, lz = s.position[2] - pz;
        const float d2 = lx * lx + ly * ly + lz * lz, d = std::sqrt(d2);
        if (d > 0.0f) { const float r = 1.0f / d; lx *= r; ly *= r; lz *= r; }
        else { lx = 0.0f; ly = 0.0f; lz = 1.0f; }
        float attenuation = 1.0f;
        if (S.attenuation == 1) {
            const float cosine = std::max(0.0f, lx * s.direction[0] + ly * s.direction[1] + lz * s.direction[2]);
            const float angular = std::max(0.0f, s.a[0] + s.a[1] * cosine + s.a[2] * cosine * cosine);
            const float denominator = s.k[0] + s.k[1] * d + s.k[2] * d2;
            attenuation = denominator > 0.0f ? angular / denominator : 0.0f;
        }
        const float red = s.color[0] * k * attenuation, green = s.color[1] * k * attenuation,
                    blue = s.color[2] * k * attenuation;
        if (std::max(red, std::max(green, blue)) <= 1.0f / 1024.0f) continue;
        const float w = .2126f * red + .7152f * green + .0722f * blue;
        vec[0] += w * lx; vec[1] += w * ly; vec[2] += w * lz; weight += w;
        total[0] += red; total[1] += green; total[2] += blue;
    }
    const float length = std::sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2]);
    if (!re4dc::render::is_finite(length) || !re4dc::render::is_finite(weight)) return e;
    const float a = weight > 0.0f ? std::min(1.0f, length / weight) : 0.0f;
    const float c2 = px * px + py * py + pz * pz, cr = c2 > 0.0f ? -1.0f / std::sqrt(c2) : 0.0f;
    e.coherence = length > 0.0f ? a : 0.0f;
    if (length > 0.0f) {
        const float r = 1.0f / length;
        e.v[0] = vec[0] * r; e.v[1] = vec[1] * r; e.v[2] = vec[2] * r;
        e.view_dot = (e.v[0] * px + e.v[1] * py + e.v[2] * pz) * cr;
    }
    for (unsigned c = 0; c < 3; ++c) {
        e.dcol[c] = length > 0.0f ? a * total[c] : 0.0f;
        e.amb[c] = S.ambient[c] * k + .25f * (1.0f - a) * total[c];
        if (!re4dc::render::is_finite(e.dcol[c]) || !re4dc::render::is_finite(e.amb[c])) return e;
    }
    e.ok = true;
    return e;
}
// The part's Lights from its actor's probe; false: not eligible / not representable (build_lights then runs).
bool probe_lights(const Re4dcModelPart& p, const Frame& f, Lights& L) {
    if (!probe_eligible(p)) DFA26_MODEL_SLOW(ActorProbeDecline, 1, return false;)
    const SourceLighting& S = *p.lighting;
    float scale[3];
    for (unsigned c = 0; c < 3; ++c) {
        scale[c] = S.material[c] * S.tev_scale;
        if (!(scale[c] >= 255.0f)) { DFA26_MODEL_HIT(ActorProbeDecline, 1) ++probe_stats.declined; return false; }  // build_lights' caps255 condition
    }
#if RE4DC_LEON_LIGHT_HEADROOM
    { const float g = leon_gain(S); for (unsigned c = 0; c < 3; ++c) scale[c] *= g; }
#endif
    const float* N = S.normal_matrix;
    float Np[12];
    const bool leon = N[3] == 1.0e30f;
    if (leon) {
        if (!leon_part_normal(p.modelview, Np)) { DFA26_MODEL_HIT(ActorProbeDecline, 1) ++probe_stats.declined; return false; }
        N = Np;
    }
    const ProbeEntry& e = probe_of(p);
    if (!e.ok) { DFA26_MODEL_HIT(ActorProbeDecline, 1) ++probe_stats.declined; return false; }
    lights_reset(L);
    L.source = &S;
    L.probe = true;
    L.dir[0][0] = (N[0] * e.v[0] + N[4] * e.v[1] + N[8] * e.v[2]) * f.nq;
    L.dir[0][1] = (N[1] * e.v[0] + N[5] * e.v[1] + N[9] * e.v[2]) * f.nq;
    L.dir[0][2] = (N[2] * e.v[0] + N[6] * e.v[1] + N[10] * e.v[2]) * f.nq;
    L.count = 1;
    L.view_dot[0] = e.view_dot;
    for (unsigned c = 0; c < 3; ++c) {
        L.color[c] = 0.5f * e.dcol[c] * scale[c];
        L.color[12 + c] = e.amb[c] * scale[c];
    }
#if RE4DC_LEON_LIGHT_FILL
    // LEON_LIGHT_FILL=F (crowd.mk; Leon only; render only; default 0): the fast kernel's spare second direction becomes a
    // camera-side fill, from the part's origin toward the camera (view space -t / |t|), coloured F% of the probe's
    // total (directional + ambient), at the probe's scale (headroom x0.5 included). The probe record, its direction and
    // the shared actor_light_probe.h record are unchanged (the shadows lane reads those).
    if (leon) {
        const float tx = p.modelview[3], ty = p.modelview[7], tz = p.modelview[11];
        const float t2 = tx * tx + ty * ty + tz * tz;
        if (t2 > 0.0f && re4dc::render::is_finite(t2)) {
            const float r = -1.0f / std::sqrt(t2), cx = tx * r, cy = ty * r, cz = tz * r;
            L.dir[1][0] = (N[0] * cx + N[4] * cy + N[8] * cz) * f.nq;
            L.dir[1][1] = (N[1] * cx + N[5] * cy + N[9] * cz) * f.nq;
            L.dir[1][2] = (N[2] * cx + N[6] * cy + N[10] * cz) * f.nq;
            L.view_dot[1] = 1.0f;
            L.count = 2;
            constexpr float kFill = 0.5f * float(RE4DC_LEON_LIGHT_FILL) / 100.0f;
            for (unsigned c = 0; c < 3; ++c) L.color[4 + c] = kFill * (e.dcol[c] + e.amb[c]) * scale[c];
        }
    }
#endif
#if RE4DC_GANADO_LIT_FILL
    // GANADO_LIT_FILL=F (crowd.mk, lane ganlit; Ganados only; render only; default 0): Leon's camera fill (above) for the
    // probe-lit Ganados, F% of their probe total in the kernel's spare second direction (no new pass). Lifts the
    // camera-facing side the one-direction probe leaves at ambient; the mid/far one-colour parts take it too
    // (part_colour), so every tier keeps one lighting model. GANADO_LIT_TOGGLE: warp `ganfill <F>` sets it at load.
    if (!leon && ganlit_fill > 0) {
        const float tx = p.modelview[3], ty = p.modelview[7], tz = p.modelview[11];
        const float t2 = tx * tx + ty * ty + tz * tz;
        if (t2 > 0.0f && re4dc::render::is_finite(t2)) {
            const float r = -1.0f / std::sqrt(t2), cx = tx * r, cy = ty * r, cz = tz * r;
            L.dir[1][0] = (N[0] * cx + N[4] * cy + N[8] * cz) * f.nq;
            L.dir[1][1] = (N[1] * cx + N[5] * cy + N[9] * cz) * f.nq;
            L.dir[1][2] = (N[2] * cx + N[6] * cy + N[10] * cz) * f.nq;
            L.view_dot[1] = 1.0f;
            L.count = 2;
            const float k = 0.5f * float(ganlit_fill) / 100.0f;
            for (unsigned c = 0; c < 3; ++c) L.color[4 + c] = k * (e.dcol[c] + e.amb[c]) * scale[c];
        }
    }
#endif
    L.fast = true;
    ++stats.light_sets;
    ++probe_stats.parts;
    if (leon) ++probe_stats.leon; else ++probe_stats.ganado;
#if RE4DC_ACTOR_PROBE_LIGHT_LOG
    if (probe_stats.parts == 1 || frame_serial - probe_stats.last >= unsigned(RE4DC_ACTOR_PROBE_LIGHT_LOG)) {
        probe_stats.last = frame_serial;
        re4dc_log("PROBE_LIGHT f=%u built=%u reused=%u parts=%u leon=%u ganado=%u declined=%u v=%d,%d,%d dcol=%d,%d,%d "
                  "amb=%d,%d,%d\n", frame_serial, probe_stats.built, probe_stats.reused, probe_stats.parts,
                  probe_stats.leon, probe_stats.ganado, probe_stats.declined, int(e.v[0] * 100.0f),
                  int(e.v[1] * 100.0f), int(e.v[2] * 100.0f), int(e.dcol[0] * 255.0f), int(e.dcol[1] * 255.0f),
                  int(e.dcol[2] * 255.0f), int(e.amb[0] * 255.0f), int(e.amb[1] * 255.0f), int(e.amb[2] * 255.0f));
    }
#endif
    return true;
}
}  // namespace
#if RE4DC_LEON_LIGHT_TOGGLE
// LEON_LIGHT_TOGGLE: the live Leon lighting mode (pad.cpp X + D-pad right + START; warp `leonlight <n>`), its on-screen
// name for 3 s (native_static.cpp re4dc_look_osd_text) and a log line per change.
extern "C" unsigned re4dc_vi_retrace_count(void);
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" {
unsigned re4dc_leon_light_mode = 2;  // boot: PROBE + HEADROOM (the candidate)
}
static unsigned leon_light_osd_until;
static const char* const kLeonLightNames[4] = {"Leon light: FLAT (test 10)", "Leon light: PROBE",
                                               "Leon light: PROBE + HEADROOM", "Leon light: FLAT WARM (room lights)"};
extern "C" void re4dc_leon_light_set(unsigned mode) {
    re4dc_leon_light_mode = mode % 4U;
    leon_light_osd_until = re4dc_vi_retrace_count() + 180U;
    re4dc_log("LEON_LIGHT_MODE %u %s\n", re4dc_leon_light_mode, kLeonLightNames[re4dc_leon_light_mode]);
}
extern "C" void re4dc_leon_light_cycle(void) { re4dc_leon_light_set(re4dc_leon_light_mode + 1U); }
extern "C" const char* re4dc_leon_light_osd_text(void) {
    return int(leon_light_osd_until - re4dc_vi_retrace_count()) > 0 ? kLeonLightNames[re4dc_leon_light_mode % 4U] : nullptr;
}
#endif
// actor_light_probe.h: the newest probe of a model (this frame's, else the previous frame's).
extern "C" int re4dc_actor_light_probe(const void* model, Re4dcLightProbe* out) {
    const ProbeEntry* best = nullptr;
    for (unsigned i = 0; i < kProbeEntries; ++i) {
        const ProbeEntry& e = probe_cache[i];
        if (!e.ok || e.model != model || frame_serial - e.serial > 1U) continue;
        if (!best || e.serial - best->serial < 0x80000000U) best = &e;
    }
    if (!best || !out) return 0;
    *out = Re4dcLightProbe{};
    out->serial = best->serial;
    for (unsigned c = 0; c < 3; ++c) { out->dir[c] = best->v[c]; out->color[c] = best->dcol[c]; out->ambient[c] = best->amb[c]; }
    out->coherence = best->coherence;
    return 1;
}
namespace {
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// The part's light fold: the actor's probe when it applies, else build_lights.
bool part_lights(const Re4dcModelPart& p, const Frame& f, const float center[3], Lights& L) {
#if RE4DC_LEON_LIGHT_TOGGLE
    if ((re4dc_leon_light_mode == 0 || re4dc_leon_light_mode == 3) && leon_record(*p.lighting)) {
        const SourceLighting& S = *p.lighting;
        lights_reset(L);
        L.source = &S;
        L.constant = true;
        L.constant_rgb = 0x808080U;  // FLAT: 128 on the 2x textures = test 10's white
        if (re4dc_leon_light_mode == 3) {  // FLAT WARM: the hue of the room's light set, brightest channel 128
            float h[3];
            for (unsigned c = 0; c < 3; ++c) {
                h[c] = S.ambient[c];
                for (unsigned i = 0; i < 8; ++i) if (S.mask & (1U << i)) h[c] += S.lights[i].color[c];
            }
            const float mx = std::max(h[0], std::max(h[1], h[2]));
            if (mx > 0.0f) L.constant_rgb = (channel(128.0f * h[0] / mx) << 16) | (channel(128.0f * h[1] / mx) << 8) |
                                            channel(128.0f * h[2] / mx);
        }
        return true;
    }
#endif
    if (probe_lights(p, f, L)) return true;
    return build_lights(p, f, center, L);
}
#define RE4DC_PART_LIGHTS part_lights
#endif
#else
#define RE4DC_PART_LIGHTS build_lights
#endif
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
// XM rows: 0 probe, 1 build_lights fold (fast kernel), 2 exact per-vertex evaluator, 3 constant (flat).
inline unsigned dsa28_light_path(const Lights& L) {
    if (L.constant) return 3;
#if RE4DC_ACTOR_PROBE_LIGHT
    if (L.probe) return 0;
#endif
    return L.fast ? 1 : 2;
}
#endif

#if RE4DC_ACTOR_LIGHT_FAST_ONLY
#include "include/actor_light_fast_only.inc"
#undef RE4DC_PART_LIGHTS
#define RE4DC_PART_LIGHTS fast_only_lights
#endif

#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29 && !RE4DC_ACTOR_LIGHT_FAST_ONLY
#include "include/fallback_scan29_lights.inc"
#endif

#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "include/fallback_actor_audit29.inc"
#endif

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// Light directions of palette entry i (skinned normals): R_i^T l, w = 0,
// cached per entry for the current part's light set.
const float* skin_light_dirs(Frame& f, const Lights& L, unsigned i, float* fallback) {
    if (i >= f.palette_entries) i = 0;
    float* out = f.skin_dirs ? f.skin_dirs + i * 12 : fallback;
    if (f.skin_dirs && f.dirs_ready[i]) return out;
    const float* P = f.palette + i * 12;
    for (unsigned l = 0; l < 3; ++l)
        for (unsigned c = 0; c < 3; ++c)
            out[l * 4 + c] = P[c * 3] * L.dir[l][0] + P[c * 3 + 1] * L.dir[l][1] + P[c * 3 + 2] * L.dir[l][2];
    out[3] = out[7] = out[11] = 0.0f;
    if (f.skin_dirs) f.dirs_ready[i] = 1;
    return out;
}
#if RE4DC_ACTOR_PROBE_LIGHT
// ACTOR_PROBE_LIGHT: a probe fold has one direction, so every palette entry's directions are built in one pass when the
// fold changes (skin_light_dirs' arithmetic for direction 0, directions 1 and 2 zero) instead of the kernels' record
// walks (avk_build_dirs*) finding unbuilt entries meshlet by meshlet.
void probe_dirs_all(Frame& f, const Lights& L) {
    const float l0 = L.dir[0][0], l1 = L.dir[0][1], l2 = L.dir[0][2];
    const float* P = f.palette;
    float* out = f.skin_dirs;
#if RE4DC_LEON_LIGHT_FILL || RE4DC_GANADO_LIT_FILL
    if (L.count == 2) {  // LEON_LIGHT_FILL / GANADO_LIT_FILL: direction 1 is the camera fill
        const float m0 = L.dir[1][0], m1 = L.dir[1][1], m2 = L.dir[1][2];
        for (unsigned i = 0; i < f.palette_entries; ++i, P += 12, out += 12) {
            for (unsigned c = 0; c < 3; ++c) out[c] = P[c * 3] * l0 + P[c * 3 + 1] * l1 + P[c * 3 + 2] * l2;
            out[3] = 0.0f;
            for (unsigned c = 0; c < 3; ++c) out[4 + c] = P[c * 3] * m0 + P[c * 3 + 1] * m1 + P[c * 3 + 2] * m2;
            out[7] = 0.0f;
            for (unsigned k = 8; k < 12; ++k) out[k] = 0.0f;
        }
        std::memset(f.dirs_ready, 1, f.palette_entries);
        return;
    }
#endif
    for (unsigned i = 0; i < f.palette_entries; ++i, P += 12, out += 12) {
        for (unsigned c = 0; c < 3; ++c) out[c] = P[c * 3] * l0 + P[c * 3 + 1] * l1 + P[c * 3 + 2] * l2;
        out[3] = 0.0f;
        for (unsigned k = 4; k < 12; ++k) out[k] = 0.0f;
    }
    std::memset(f.dirs_ready, 1, f.palette_entries);
}
#endif

#endif
// ----------------------------------------------------------- the meshlet --
// Outcode bits, built MSB-first by the SH4 kernel's rotcl chain (ACTOR_VTX_KERNEL: the order of
// avk_sh4.S's chain, near first; ACTOR_POS_ASM combines its two chains to match).
#if RE4DC_AVK
constexpr unsigned kOcBottom = 1, kOcTop = 2, kOcRight = 4, kOcLeft = 8, kOcFar = 16, kOcNear = 32;
#else
constexpr unsigned kOcFar = 1, kOcNear = 2, kOcBottom = 4, kOcTop = 8, kOcRight = 16, kOcLeft = 32;
#endif
// Near is the only clipped plane; far and the screen edges only cull (whole
// meshlets / strips), the PVR scissors the rest. Bits above 5 are don't-care.
constexpr unsigned kOcScreen = kOcBottom | kOcTop | kOcRight | kOcLeft, kOcCull = kOcScreen | kOcFar;

// Per-meshlet vertex cache: 128 PVR vertices + 128 outcode bytes (132 slots
// of 32 bytes), carved from the tail of the part's own packet range, which
// is never sent; <= 4.2 KiB, so a meshlet's working set stays in the 16 KiB
// operand cache with its records and indices.
constexpr unsigned kCacheSlots = kMaxVertices + kMaxVertices / 32U;
struct Cache { pvr_vertex_t* v; u8* oc; };

// Position pass constants; the SH4 kernel keeps them in fr7..fr15.
struct PosConst { float zero, au, bu, av, bv, width, height, near_distance, far_distance; };
// Fast light pass: directions 0/1 (fv8/fv12 in the kernel), direction 2
// (reloaded per vertex into fv0), each with w = 0; then the 255 clamp.
struct alignas(8) LightConst { float l0[4], l1[4], l2[4], cap; };

// qemu-sh4 test builds substitute these (qemu has no ftrv/fipr/fsrra).
#ifndef ACTOR_ASM_FTRV
#define ACTOR_ASM_FTRV "ftrv    xmtrx,fv0\n\t"
#define ACTOR_ASM_FSRRA4 "fsrra   fr4\n\t"
#define ACTOR_ASM_FSRRA3 "fsrra   fr3\n\t"
#define ACTOR_ASM_FIPR(a) "fipr    " a ",fv4\n\t"
#define ACTOR_ASM_FIPR4(n) "fipr    fv4," n "\n\t"
#define ACTOR_ASM_CLOBBER
#endif
#ifndef ACTOR_FSRRA
#define ACTOR_FSRRA(x) inverse_sqrt(x)
#endif
#ifndef ACTOR_DOT3
#define ACTOR_DOT3(a, x, y, z) ((a)[0] * (x) + (a)[1] * (y) + (a)[2] * (z))
#endif

// Pass 1, portable (host; SH4 variants without a kernel; kernel reference).
// Records [0, n) (rs bytes each): position through XMTRX, 1/|w| by
// rsqrt(w^2), x/y scaled, u/v = t * a + b, one outcode byte. With check,
// stops before the first record whose position palette index != palette.
unsigned positions_c(const u8* rec, unsigned rs, unsigned n, const u8* pos, unsigned ps, bool check, int palette,
                     const u8* uv, bool s16_uv, pvr_vertex_t* dst, u8* oc, const PosConst& k, unsigned& all,
                     unsigned& any) {
    unsigned i = 0;
    for (; i < n; ++i, rec += rs) {
        const u16* r = reinterpret_cast<const u16*>(rec);
        const short* s = reinterpret_cast<const short*>(pos + r[0] * ps);
        if (check && s[3] != palette) break;
        const u8* t = uv + r[2] * 4U;
        const float tu = s16_uv ? float(*reinterpret_cast<const short*>(t)) : float(*reinterpret_cast<const u16*>(t));
        const float tv = s16_uv ? float(*reinterpret_cast<const short*>(t + 2)) : float(*reinterpret_cast<const u16*>(t + 2));
        float x = float(s[0]), y = float(s[1]), z = float(s[2]), w = 1.0f;
        ACTOR_FTRV(x, y, z, w);
        const float inv = ACTOR_FSRRA(w * w);
        x *= inv; y *= inv;
        const unsigned code = (k.zero > x ? kOcLeft : 0U) | (x > k.width ? kOcRight : 0U) | (k.zero > y ? kOcTop : 0U) |
                              (y > k.height ? kOcBottom : 0U) | (k.near_distance > w ? kOcNear : 0U) |
                              (w > k.far_distance ? kOcFar : 0U);
        pvr_vertex_t& d = dst[i];
        d.x = x; d.y = y; d.z = inv;
        d.u = tu * k.au + k.bu; d.v = tv * k.av + k.bv;
        oc[i] = u8(code);
        all &= code; any |= code;
    }
    return i;
}

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// Pass 2 (fast lights), portable. XMTRX holds the colour matrix. Small (s8)
// normals only; with check, stops at the first record whose normal palette
// index (byte 3) != palette.
unsigned lights_c(const u8* rec, unsigned rs, unsigned n, const u8* nrm, unsigned ns, bool check, unsigned palette,
                  pvr_vertex_t* dst, const LightConst& L, u32 alpha) {
    unsigned i = 0;
    for (; i < n; ++i, rec += rs) {
        const u16* r = reinterpret_cast<const u16*>(rec);
        const signed char* s = reinterpret_cast<const signed char*>(nrm + r[1] * ns);
        if (check && u8(s[3]) != palette) break;
        const float nx = s[0], ny = s[1], nz = s[2];
        const float d2 = ACTOR_DOT3(L.l2, nx, ny, nz), d0 = ACTOR_DOT3(L.l0, nx, ny, nz), d1 = ACTOR_DOT3(L.l1, nx, ny, nz);
        float m0 = std::fabs(d0) + d0, m1 = std::fabs(d1) + d1, m2 = std::fabs(d2) + d2, one = 1.0f;
        ACTOR_FTRV(m0, m1, m2, one);
        if (m0 > L.cap) m0 = L.cap;
        if (m1 > L.cap) m1 = L.cap;
        if (m2 > L.cap) m2 = L.cap;
        dst[i].argb = alpha | (u32(int(m0)) << 16) | (u32(int(m1)) << 8) | u32(int(m2));
    }
    return i;
}

#endif
#if defined(__sh__) && RE4DC_ACTOR_ASM
// SH4 pass 1: one dynarec block per record (no calls, no spills), constants
// resident in fr7..fr15, stores through one pre-decrementing pointer.
// ~58 instructions per record (Flycast issue model ~40 cycles).
#define ACTOR_POS_ADDR8 "shll2   r1\n\t" "shll    r1\n\t"
#define ACTOR_POS_ADDR6 "mov     r1,r2\n\t" "shll    r1\n\t" "add     r2,r1\n\t" "shll    r1\n\t"
#define ACTOR_POS_CHECK "mov.w   @(6,r1),r0\n\t" "cmp/eq  %[pal],r0\n\t" "bf      9f\n\t"
#if RE4DC_AVK
#define ACTOR_POS_OC "shll2   r2\n\t" "shll2   r2\n\t" "or      r2,r1\n\t"  /* near far left right top bottom */
#else
#define ACTOR_POS_OC "shll2   r1\n\t" "or      r2,r1\n\t"                  /* left right top bottom near far */
#endif
// Scheduled for the SH4 pipes (one LS unit): the position loads and FTRV go
// first; the u/v conversion (fmul + fadd, FE) fills FTRV's latency; w's
// near/far bits are taken before w is squared in place for FSRRA; the u/v
// stores fill FSRRA's latency. Outcode bits: x<0 x>640 y<0 y>480 (r1) then
// w<near w>far (r2), as before.
#define ACTOR_POS_ASM(ADDR, CHECK) \
    "fmov.s  @%[k]+,fr7\n\t"  "fmov.s  @%[k]+,fr8\n\t"  "fmov.s  @%[k]+,fr9\n\t" \
    "fmov.s  @%[k]+,fr10\n\t" "fmov.s  @%[k]+,fr11\n\t" "fmov.s  @%[k]+,fr12\n\t" \
    "fmov.s  @%[k]+,fr13\n\t" "fmov.s  @%[k]+,fr14\n\t" "fmov.s  @%[k]+,fr15\n" \
    "1:\n\t" \
    "mov.w   @%[rec],r1\n\t"        /* vi */ \
    ADDR \
    "add     %[pos],r1\n\t" \
    CHECK \
    "mov.w   @r1+,r2\n\t"           /* x */ \
    "mov.w   @(4,%[rec]),r0\n\t"    /* ti */ \
    "mov.w   @r1+,r3\n\t"           /* y */ \
    "lds     r2,fpul\n\t" \
    "mov.w   @r1,r2\n\t"            /* z */ \
    "float   fpul,fr0\n\t" \
    "lds     r3,fpul\n\t" \
    "shll2   r0\n\t" \
    "float   fpul,fr1\n\t" \
    "lds     r2,fpul\n\t" \
    "add     %[uv],r0\n\t" \
    "float   fpul,fr2\n\t" \
    "mov.w   @r0+,r2\n\t"           /* tu */ \
    "fldi1   fr3\n\t" \
    "mov.w   @r0,r0\n\t"            /* tv */ \
    ACTOR_ASM_FTRV \
    "lds     r2,fpul\n\t" \
    "add     %[rs],%[rec]\n\t" \
    "float   fpul,fr5\n\t" \
    "lds     r0,fpul\n\t" \
    "float   fpul,fr6\n\t" \
    "fmul    fr8,fr5\n\t" \
    "fmul    fr10,fr6\n\t" \
    "fadd    fr9,fr5\n\t"           /* u = tu au + bu */ \
    "fadd    fr11,fr6\n\t"          /* v = tv av + bv */ \
    "fcmp/gt fr3,fr14\n\t" "movt    r2\n\t"     /* w<near */ \
    "fcmp/gt fr15,fr3\n\t" "rotcl   r2\n\t"     /* w>far  */ \
    "fmul    fr3,fr3\n\t" \
    ACTOR_ASM_FSRRA3                /* 1/|w| */ \
    "fmov.s  fr6,@-%[dst]\n\t"      /* v @20 */ \
    "fmov.s  fr5,@-%[dst]\n\t"      /* u @16 */ \
    "fmul    fr3,fr0\n\t" \
    "fmul    fr3,fr1\n\t" \
    "fmov.s  fr3,@-%[dst]\n\t"      /* z @12 */ \
    "fcmp/gt fr0,fr7\n\t"  "movt    r1\n\t"     /* x<0    */ \
    "fcmp/gt fr12,fr0\n\t" "rotcl   r1\n\t"     /* x>640  */ \
    "fmov.s  fr1,@-%[dst]\n\t"      /* y @8  */ \
    "fcmp/gt fr1,fr7\n\t"  "rotcl   r1\n\t"     /* y<0    */ \
    "fcmp/gt fr13,fr1\n\t" "rotcl   r1\n\t"     /* y>480  */ \
    "fmov.s  fr0,@-%[dst]\n\t"      /* x @4  */ \
    ACTOR_POS_OC \
    "mov.b   r1,@%[oc]\n\t" \
    "add     #1,%[oc]\n\t" \
    "and     r1,%[all]\n\t" \
    "or      r1,%[any]\n\t" \
    "dt      %[n]\n\t" \
    "bf/s    1b\n\t" \
    "add     #52,%[dst]\n"          /* entry+4 -> next entry+24 */ \
    "9:\n\t"
#define ACTOR_POS_OPERANDS \
    : [rec] "+r"(rec), [n] "+r"(left), [dst] "+r"(d), [oc] "+r"(oc), [k] "+r"(kp), [all] "+r"(a), [any] "+r"(o) \
    : [rs] "r"(rs), [pos] "r"(pos), [uv] "r"(uv), [pal] "r"(palette) \
    : "r0", "r1", "r2", "r3", "fpul", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "fr8", "fr9", \
      "fr10", "fr11", "fr12", "fr13", "fr14", "fr15", "t", "memory" ACTOR_ASM_CLOBBER
enum PosKernel : unsigned { kPos8 = 0, kPos8Check = 1, kPos6 = 2 };
template <unsigned V>
unsigned positions_asm(const u8* rec, unsigned rs, unsigned n, const u8* pos, int palette, const u8* uv,
                       pvr_vertex_t* dst, u8* oc, const PosConst& k, unsigned& all, unsigned& any) {
    unsigned left = n, a = all, o = any;
    const float* kp = &k.zero;
    float* d = reinterpret_cast<float*>(reinterpret_cast<u8*>(dst) + 24);
    if constexpr (V == kPos8)
        __asm__ __volatile__(ACTOR_POS_ASM(ACTOR_POS_ADDR8, "") ACTOR_POS_OPERANDS);
    else if constexpr (V == kPos8Check)
        __asm__ __volatile__(ACTOR_POS_ASM(ACTOR_POS_ADDR8, ACTOR_POS_CHECK) ACTOR_POS_OPERANDS);
    else
        __asm__ __volatile__(ACTOR_POS_ASM(ACTOR_POS_ADDR6, "") ACTOR_POS_OPERANDS);
    all = a; any = o;
    return n - left;
}

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// SH4 pass 2 (fast lights): fipr per light (fv8, fv12 resident; direction 2
// reloaded into fv0), m = d + |d|, colour by ftrv, clamp, pack.
#define ACTOR_NRM_ADDR4 "shll2   r0\n\t"
#define ACTOR_NRM_ADDR3 "mov     r0,r1\n\t" "shll    r0\n\t" "add     r1,r0\n\t"
#define ACTOR_NRM_CHECK "mov.b   @(3,r3),r0\n\t" "extu.b  r0,r0\n\t" "cmp/eq  %[pal],r0\n\t" "bf      9f\n\t"
// The normal sits in fv4 with fr7 = 0 for the whole loop, so the three dot
// products are independent FIPRs into the w slots of the light vectors
// (fv8 -> fr11, fv12 -> fr15, direction 2 reloaded into fv0 -> fr3; a light
// vector's w only ever meets fr7 = 0) and issue back to back.
#define ACTOR_LIGHT_ASM(ADDR, CHECK) \
    "fmov.s  @%[l]+,fr8\n\t"  "fmov.s  @%[l]+,fr9\n\t"  "fmov.s  @%[l]+,fr10\n\t" "fmov.s  @%[l]+,fr11\n\t" \
    "fmov.s  @%[l]+,fr12\n\t" "fmov.s  @%[l]+,fr13\n\t" "fmov.s  @%[l]+,fr14\n\t" "fmov.s  @%[l]+,fr15\n\t" \
    "fldi0   fr7\n" \
    "1:\n\t" \
    "mov.w   @(2,%[rec]),r0\n\t"    /* ni */ \
    "add     %[rs],%[rec]\n\t" \
    ADDR \
    "add     %[nrm],r0\n\t" \
    "mov     r0,r3\n\t" \
    CHECK \
    "mov.b   @r3+,r1\n\t" \
    "mov.b   @r3+,r2\n\t" \
    "lds     r1,fpul\n\t" \
    "mov.b   @r3,r3\n\t" \
    "float   fpul,fr4\n\t" \
    "lds     r2,fpul\n\t" \
    "float   fpul,fr5\n\t" \
    "lds     r3,fpul\n\t" \
    "float   fpul,fr6\n\t" \
    "fmov.s  @%[l]+,fr0\n\t" "fmov.s  @%[l]+,fr1\n\t" "fmov.s  @%[l],fr2\n\t" \
    "add     #-8,%[l]\n\t" \
    ACTOR_ASM_FIPR4("fv8")          /* d0 -> fr11 */ \
    ACTOR_ASM_FIPR4("fv12")         /* d1 -> fr15 */ \
    ACTOR_ASM_FIPR4("fv0")          /* d2 -> fr3  */ \
    "fmov    fr11,fr0\n\t" "fabs    fr0\n\t" "fadd    fr11,fr0\n\t"   /* m0 */ \
    "fmov    fr15,fr1\n\t" "fabs    fr1\n\t" "fadd    fr15,fr1\n\t"   /* m1 */ \
    "fmov    fr3,fr2\n\t"  "fabs    fr2\n\t" "fadd    fr3,fr2\n\t"    /* m2 */ \
    "fldi1   fr3\n\t" \
    ACTOR_ASM_FTRV \
    "fmov.s  @%[cap],fr4\n\t" \
    "fcmp/gt fr4,fr0\n\t" "bf      2f\n\t" "fmov    fr4,fr0\n" "2:\n\t" \
    "fcmp/gt fr4,fr1\n\t" "bf      3f\n\t" "fmov    fr4,fr1\n" "3:\n\t" \
    "fcmp/gt fr4,fr2\n\t" "bf      4f\n\t" "fmov    fr4,fr2\n" "4:\n\t" \
    "ftrc    fr0,fpul\n\t" "sts     fpul,r1\n\t" \
    "ftrc    fr1,fpul\n\t" "sts     fpul,r2\n\t" \
    "ftrc    fr2,fpul\n\t" "sts     fpul,r3\n\t" \
    "shll16  r1\n\t" \
    "shll8   r2\n\t" \
    "or      r2,r1\n\t" \
    "or      r3,r1\n\t" \
    "or      %[alpha],r1\n\t" \
    "mov.l   r1,@%[dst]\n\t" \
    "dt      %[n]\n\t" \
    "bf/s    1b\n\t" \
    "add     #32,%[dst]\n" \
    "9:\n\t"
#define ACTOR_LIGHT_OPERANDS \
    : [rec] "+r"(rec), [n] "+r"(left), [dst] "+r"(d), [l] "+r"(lp) \
    : [rs] "r"(rs), [nrm] "r"(nrm), [cap] "r"(&L.cap), [alpha] "r"(alpha), [pal] "r"(palette) \
    : "r0", "r1", "r2", "r3", "fpul", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "fr8", "fr9", \
      "fr10", "fr11", "fr12", "fr13", "fr14", "fr15", "t", "memory" ACTOR_ASM_CLOBBER
enum LightKernel : unsigned { kNrm4 = 0, kNrm4Check = 1, kNrm3 = 2 };
template <unsigned V>
unsigned lights_asm(const u8* rec, unsigned rs, unsigned n, const u8* nrm, unsigned palette, pvr_vertex_t* dst,
                    const LightConst& L, u32 alpha) {
    unsigned left = n;
    const float* lp = L.l0;
    u32* d = &dst->argb;
    if constexpr (V == kNrm4)
        __asm__ __volatile__(ACTOR_LIGHT_ASM(ACTOR_NRM_ADDR4, "") ACTOR_LIGHT_OPERANDS);
    else if constexpr (V == kNrm4Check)
        __asm__ __volatile__(ACTOR_LIGHT_ASM(ACTOR_NRM_ADDR4, ACTOR_NRM_CHECK) ACTOR_LIGHT_OPERANDS);
    else
        __asm__ __volatile__(ACTOR_LIGHT_ASM(ACTOR_NRM_ADDR3, "") ACTOR_LIGHT_OPERANDS);
    return n - left;
}
#endif
#endif

// One strip starting at index: corner count and AND/OR of its outcodes.
struct Strip { unsigned n, all, any; };
inline Strip scan(const u8* oc, const u8* index) {
#if defined(__sh__) && RE4DC_ACTOR_ASM
    unsigned n = 0, all = ~0U, any = 0;
    __asm__(
        "1:\n\t"
        "mov.b   @%[index]+,r0\n\t"   /* sign-extended: EOL -> negative */
        "cmp/pz  r0\n\t"
        "and     #127,r0\n\t"
        "mov.b   @(r0,%[oc]),r1\n\t"
        "add     #1,%[n]\n\t"
        "and     r1,%[all]\n\t"
        "bt/s    1b\n\t"
        "or      r1,%[any]\n\t"
        : [n] "+r"(n), [all] "+r"(all), [any] "+r"(any), [index] "+r"(index)
        : [oc] "r"(oc), "m"(*reinterpret_cast<const u8(*)[kMaxVertices]>(oc))
        : "r0", "r1", "t");
    return {n, all, any};
#else
    Strip s{0, ~0U, 0};
    for (;;) {
        const unsigned e = index[s.n++], c = oc[e & 127U];
        s.all &= c; s.any |= c;
        if (e & 128U) return s;
    }
#endif
}

// Copy the n (>= 1) cache entries of one strip into 32-byte aligned packet
// storage; the last one becomes EOL. 64-bit FPU moves (FPSCR.SZ), as in the
// scenery meshlet path (mesh_fastpath.hpp emit()).
inline pvr_vertex_t* emit(pvr_vertex_t* dst, const pvr_vertex_t* cache, const u8* index, unsigned n) {
#if defined(__sh__) && RE4DC_ACTOR_ASM
    __asm__ __volatile__(
        "fschg\n"
        "1:\n\t"
        "mov.b   @%[index]+,r0\n\t"
        "and     #127,r0\n\t"
        "shld    %[five],r0\n\t"
        "add     %[cache],r0\n\t"
        "fmov    @r0+,dr0\n\t"
        "fmov    @r0+,dr2\n\t"
        "fmov    @r0+,dr4\n\t"
        "fmov    @r0+,dr6\n\t"
        "add     #32,%[dst]\n\t"
        "fmov    dr6,@-%[dst]\n\t"
        "fmov    dr4,@-%[dst]\n\t"
        "fmov    dr2,@-%[dst]\n\t"
        "fmov    dr0,@-%[dst]\n\t"
        "dt      %[n]\n\t"
        "bf/s    1b\n\t"
        "add     #32,%[dst]\n\t"
        "fschg\n"
        : [dst] "+r"(dst), [index] "+r"(index), [n] "+r"(n)
        : [cache] "r"(cache), [five] "r"(5)
        : "r0", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "t", "memory");
#if RE4DC_ACTOR_MOVCA
    // ACTOR_MOVCA: cache entries allocated by movca.l carry no primed flags word (emit_sq).
    for (pvr_vertex_t* v = dst - n; v != dst; ++v) v->flags = PVR_CMD_VERTEX;
#endif
    dst[-1].flags = PVR_CMD_VERTEX_EOL;
    return dst;
#else
    for (unsigned k = 0; k < n; ++k) dst[k] = cache[index[k] & 127U];
    dst[n - 1].flags = PVR_CMD_VERTEX_EOL;
    return dst + n;
#endif
}

// A whole meshlet whose strips all qualify (no corner outside a screen edge,
// beyond far or in front of near): every index copied in one loop, the flags
// word derived from index bit 7 (sign of the loaded byte: >> 3 keeps bit 28).
// SQ = true: into the TA store queues, one burst per vertex.
#if RE4DC_AVK == 2
bool avk_emit_ref = false;  // the check's reference copy: the loop below
void avk_check_emit(const pvr_vertex_t* cache, const u8* index, unsigned n);
#elif RE4DC_AVK
constexpr bool avk_emit_ref = false;
#endif
template <bool SQ>
inline void* emit_meshlet(void* dst, const pvr_vertex_t* cache, const u8* index, unsigned n) {
#if RE4DC_TA_HASH && RE4DC_TA_HASH != 4
    // TA_HASH (test builds): a store-queue meshlet's words as every copy below sends them: the cache entry with its
    // flags word from index bit 7 (EOL ends a strip). Whole meshlets (Part::whole, the common direct case and the
    // ONE_SUBMIT window) were the actor fast path's unhashed writer (review 2026-10-04).
    if constexpr (SQ) {
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
        RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));  // an actor burst outside a tagged transaction: class 6
#endif
        for (unsigned k = 0; k < n; ++k) {
            std::uint32_t w[8];
            __builtin_memcpy(w, cache + (index[k] & 127u), 32);
            w[0] = (index[k] & 128u) ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
            re4dc_ta_hash(w, 32);
        }
    }
#endif
#if RE4DC_AVK
    // ACTOR_VTX_KERNEL: the same copy two vertices at a time, software-pipelined: vertex k's four
    // stores, flags word and burst go out while vertex k+1's index, offset and four loads come in
    // (fv0-fv7 / fv8-fv15 alternate). The last half reads one index byte and one cache entry past
    // the list (both inside their buffers) and drops them. =2: each store-queue meshlet is also
    // copied by both loops into RAM and compared (avk_check_emit).
    if (!avk_emit_ref) {
#if RE4DC_AVK == 2
        if constexpr (SQ) avk_check_emit(cache, index, n);
#endif
        const u32 vertex = PVR_CMD_VERTEX, eol_bit = PVR_CMD_VERTEX_EOL ^ PVR_CMD_VERTEX, mask = 127U << 5;
        auto* d = static_cast<u32*>(dst);
        u32 ra, fa, rb, fb;
#define AVK_EMIT_HALF(RN, FN, D0, D2, D4, D6, RM, FM, E0, E2, E4, E6, PREF) \
        "mov.b   @%[index]+," RN "\n\t" \
        "add     #32,%[dst]\n\t" \
        "fmov    " D6 ",@-%[dst]\n\t" \
        "mov     " RN "," FN "\n\t" \
        "fmov    " D4 ",@-%[dst]\n\t" \
        "shld    %[five]," RN "\n\t" \
        "fmov    " D2 ",@-%[dst]\n\t" \
        "and     %[mask]," RN "\n\t" \
        "fmov    " D0 ",@-%[dst]\n\t" \
        "add     %[cache]," RN "\n\t" \
        "mov.l   " FM ",@%[dst]\n\t" \
        "shlr2   " FN "\n\t" \
        PREF \
        "shlr    " FN "\n\t" \
        "fmov    @" RN "+," E0 "\n\t" \
        "and     %[eol]," FN "\n\t" \
        "fmov    @" RN "+," E2 "\n\t" \
        "or      %[vertex]," FN "\n\t" \
        "fmov    @" RN "+," E4 "\n\t" \
        "add     #32,%[dst]\n\t" \
        "fmov    @" RN "+," E6 "\n\t" \
        "dt      %[n]\n\t"
#define AVK_EMIT_MESHLET(PREF) \
        "fschg\n\t" \
        "mov.b   @%[index]+,%[ra]\n\t" \
        "mov     %[ra],%[fa]\n\t" \
        "shld    %[five],%[ra]\n\t" \
        "and     %[mask],%[ra]\n\t" \
        "add     %[cache],%[ra]\n\t" \
        "fmov    @%[ra]+,dr0\n\t" \
        "shlr2   %[fa]\n\t" \
        "fmov    @%[ra]+,dr2\n\t" \
        "shlr    %[fa]\n\t" \
        "fmov    @%[ra]+,dr4\n\t" \
        "and     %[eol],%[fa]\n\t" \
        "fmov    @%[ra]+,dr6\n\t" \
        "or      %[vertex],%[fa]\n" \
        "1:\n\t" \
        AVK_EMIT_HALF("%[rb]", "%[fb]", "dr0", "dr2", "dr4", "dr6", "%[ra]", "%[fa]", "dr8", "dr10", "dr12", "dr14", PREF) \
        "bt      2f\n\t" \
        AVK_EMIT_HALF("%[ra]", "%[fa]", "dr8", "dr10", "dr12", "dr14", "%[rb]", "%[fb]", "dr0", "dr2", "dr4", "dr6", PREF) \
        "bf      1b\n" \
        "2:\n\t" \
        "fschg\n" \
        : [dst] "+r"(d), [index] "+r"(index), [n] "+r"(n), [ra] "=&r"(ra), [fa] "=&r"(fa), [rb] "=&r"(rb), \
          [fb] "=&r"(fb) \
        : [cache] "r"(cache), [five] "r"(5), [mask] "r"(mask), [eol] "r"(eol_bit), [vertex] "r"(vertex) \
        : "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "fr8", "fr9", "fr10", "fr11", "fr12", "fr13", \
          "fr14", "fr15", "t", "memory"
        if constexpr (SQ) __asm__ __volatile__(AVK_EMIT_MESHLET("pref    @%[dst]\n\t"));
        else __asm__ __volatile__(AVK_EMIT_MESHLET(""));
#undef AVK_EMIT_MESHLET
#undef AVK_EMIT_HALF
        return d;
    }
#endif
#if defined(__sh__) && RE4DC_ACTOR_ASM
    const u32 vertex = PVR_CMD_VERTEX, eol_bit = PVR_CMD_VERTEX_EOL ^ PVR_CMD_VERTEX;
    auto* d = static_cast<u32*>(dst);
#define ACTOR_EMIT_MESHLET(PREF) \
        "fschg\n" \
        "1:\n\t" \
        "mov.b   @%[index]+,r0\n\t" \
        "mov     r0,r1\n\t" \
        "and     #127,r0\n\t" \
        "shld    %[five],r0\n\t" \
        "add     %[cache],r0\n\t" \
        "fmov    @r0+,dr0\n\t" \
        "fmov    @r0+,dr2\n\t" \
        "fmov    @r0+,dr4\n\t" \
        "fmov    @r0+,dr6\n\t" \
        "shlr2   r1\n\t" \
        "shlr    r1\n\t" \
        "and     %[eol],r1\n\t" \
        "or      %[vertex],r1\n\t" \
        "add     #32,%[dst]\n\t" \
        "fmov    dr6,@-%[dst]\n\t" \
        "fmov    dr4,@-%[dst]\n\t" \
        "fmov    dr2,@-%[dst]\n\t" \
        "fmov    dr0,@-%[dst]\n\t" \
        "mov.l   r1,@%[dst]\n\t" \
        PREF \
        "dt      %[n]\n\t" \
        "bf/s    1b\n\t" \
        "add     #32,%[dst]\n\t" \
        "fschg\n" \
        : [dst] "+r"(d), [index] "+r"(index), [n] "+r"(n) \
        : [cache] "r"(cache), [five] "r"(5), [eol] "r"(eol_bit), [vertex] "r"(vertex) \
        : "r0", "r1", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "t", "memory"
    if constexpr (SQ) __asm__ __volatile__(ACTOR_EMIT_MESHLET("pref    @%[dst]\n\t"));
    else __asm__ __volatile__(ACTOR_EMIT_MESHLET(""));
#undef ACTOR_EMIT_MESHLET
    return d;
#else
    static_assert(!SQ, "store queues are SH4 only");
    auto* d = static_cast<pvr_vertex_t*>(dst);
    for (unsigned k = 0; k < n; ++k) {
        d[k] = cache[index[k] & 127U];
        d[k].flags = (index[k] & 128U) ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
    }
    return d + n;
#endif
}

#if RE4DC_ACTOR_DIRECT
// The same copy straight into the TA through the store queues (TA_DIRECT):
// EOL goes into the last vertex before its burst leaves.
inline std::uint32_t* emit_sq(std::uint32_t* sq, const pvr_vertex_t* cache, const u8* index, unsigned n) {
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
    RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));
#endif
    const std::uint32_t eol = PVR_CMD_VERTEX_EOL;
#if RE4DC_TA_HASH && RE4DC_TA_HASH != 4
    // TA_HASH (test builds): the words this strip sends (EOL in the last flags word), as re4dc_ta_put hashes its own.
    for (unsigned k = 0; k < n; ++k) {
        std::uint32_t w[8];
        __builtin_memcpy(w, cache + (index[k] & 127u), 32);
#if RE4DC_ACTOR_MOVCA
        // MOVCA leaves cache word0 unprimed; hash the command the SQ loop
        // actually writes, matching CPU_BACKFACE=2's actor trace.
        w[0] = k + 1 == n ? eol : PVR_CMD_VERTEX;
#else
        if (k + 1 == n) w[0] = eol;
#endif
        re4dc_ta_hash(w, 32);
    }
#endif
#if RE4DC_ACTOR_MOVCA
    // ACTOR_MOVCA: the position kernels allocate cache entries with movca.l, so an entry's flags word is not
    // primed: every vertex's flags word is written here (PVR_CMD_VERTEX in the branch's delay slot, then EOL over
    // it on the last one), as emit_meshlet already does for whole meshlets.
    const std::uint32_t vtx = PVR_CMD_VERTEX;
    __asm__ __volatile__(
        "fschg\n"
        "1:\n\t"
        "mov.b   @%[index]+,r0\n\t"
        "and     #127,r0\n\t"
        "shld    %[five],r0\n\t"
        "add     %[cache],r0\n\t"
        "fmov    @r0+,dr0\n\t"
        "fmov    @r0+,dr2\n\t"
        "fmov    @r0+,dr4\n\t"
        "fmov    @r0+,dr6\n\t"
        "add     #32,%[sq]\n\t"
        "fmov    dr6,@-%[sq]\n\t"
        "fmov    dr4,@-%[sq]\n\t"
        "fmov    dr2,@-%[sq]\n\t"
        "fmov    dr0,@-%[sq]\n\t"
        "dt      %[n]\n\t"
        "bf/s    2f\n\t"
        "mov.l   %[vtx],@%[sq]\n\t"
        "mov.l   %[eol],@%[sq]\n"
        "2:\n\t"
        "pref    @%[sq]\n\t"
        "tst     %[n],%[n]\n\t"
        "bf/s    1b\n\t"
        "add     #32,%[sq]\n\t"
        "fschg\n"
        : [sq] "+r"(sq), [index] "+r"(index), [n] "+r"(n)
        : [cache] "r"(cache), [five] "r"(5), [eol] "r"(eol), [vtx] "r"(vtx)
        : "r0", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "t", "memory");
    return sq;
#endif
    __asm__ __volatile__(
        "fschg\n"
        "1:\n\t"
        "mov.b   @%[index]+,r0\n\t"
        "and     #127,r0\n\t"
        "shld    %[five],r0\n\t"
        "add     %[cache],r0\n\t"
        "fmov    @r0+,dr0\n\t"
        "fmov    @r0+,dr2\n\t"
        "fmov    @r0+,dr4\n\t"
        "fmov    @r0+,dr6\n\t"
        "add     #32,%[sq]\n\t"
        "fmov    dr6,@-%[sq]\n\t"
        "fmov    dr4,@-%[sq]\n\t"
        "fmov    dr2,@-%[sq]\n\t"
        "dt      %[n]\n\t"
        "bf/s    2f\n\t"
        "fmov    dr0,@-%[sq]\n\t"
        "mov.l   %[eol],@%[sq]\n"
        "2:\n\t"
        "pref    @%[sq]\n\t"
        "tst     %[n],%[n]\n\t"
        "bf/s    1b\n\t"
        "add     #32,%[sq]\n\t"
        "fschg\n"
        : [sq] "+r"(sq), [index] "+r"(index), [n] "+r"(n)
        : [cache] "r"(cache), [five] "r"(5), [eol] "r"(eol)
        : "r0", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "t", "memory");
    return sq;
}
#endif

// World (camera) position and normal-space normal of a record, for the
// clipper and the exact slow lighting path.
void world_of(const Frame& f, const Re4dcModelPart& p, const Records& r, unsigned i, float w[3], float n[3]
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
              , const float* part_normal = nullptr
#endif
              ) {
    const short* s = reinterpret_cast<const short*>(f.positions + r.vi(i) * f.position_stride);
    float a = s[0] * f.q, b = s[1] * f.q, c = s[2] * f.q;
    float nx, ny, nz;
    int npi = 0;
    if (f.small_normals) {
        const signed char* t = reinterpret_cast<const signed char*>(f.normals + r.ni(i) * f.normal_stride);
        nx = t[0]; ny = t[1]; nz = t[2]; npi = f.mode == kSkin ? int(u8(t[3])) : 0;
    } else {
        const short* t = reinterpret_cast<const short*>(f.normals + r.ni(i) * f.normal_stride);
        nx = t[0]; ny = t[1]; nz = t[2]; npi = f.mode == kSkin ? int(u16(t[3])) : 0;
    }
    if (f.mode == kSkin) {
        const unsigned pi = unsigned(u16(s[3])) < f.palette_entries ? unsigned(u16(s[3])) : 0U;
        const float* P = f.palette + pi * 12;
        const float x = P[0] * a + P[3] * b + P[6] * c + P[9];
        const float y = P[1] * a + P[4] * b + P[7] * c + P[10];
        const float z = P[2] * a + P[5] * b + P[8] * c + P[11];
        a = x; b = y; c = z;
        const float* R = f.palette + (unsigned(npi) < f.palette_entries ? unsigned(npi) : 0U) * 12;
        const float rx = R[0] * nx + R[3] * ny + R[6] * nz;
        const float ry = R[1] * nx + R[4] * ny + R[7] * nz;
        const float rz = R[2] * nx + R[5] * ny + R[8] * nz;
        nx = rx; ny = ry; nz = rz;
    }
    const float* m = p.modelview;
    w[0] = m[0] * a + m[1] * b + m[2] * c + m[3];
    w[1] = m[4] * a + m[5] * b + m[6] * c + m[7];
    w[2] = m[8] * a + m[9] * b + m[10] * c + m[11];
    nx *= f.nq; ny *= f.nq; nz *= f.nq;
    const float* N = p.lighting ? p.lighting->normal_matrix : nullptr;
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
    if (part_normal) N = part_normal;
#endif
    if (N) {
        n[0] = N[0] * nx + N[1] * ny + N[2] * nz;
        n[1] = N[4] * nx + N[5] * ny + N[6] * nz;
        n[2] = N[8] * nx + N[9] * ny + N[10] * nz;
    } else { n[0] = nx; n[1] = ny; n[2] = nz; }
}

// Exactly native_model.cpp's project(), for the clipped fallback only.
struct Projection { const float* p; const float* v; };
void project(float& x, float& y, float& z, void* context) {
    const auto& c = *static_cast<const Projection*>(context);
    const float inv = 1.0f / (-z);
    x = (c.v[2] * .5f * (c.p[1] * x + c.p[2] * z) * inv + c.v[0] + c.v[2] * .5f) * RE4DC_SCREEN_WF / c.v[2];
    y = (-c.v[3] * .5f * (c.p[3] * y + c.p[4] * z) * inv + c.v[1] + c.v[3] * .5f) * RE4DC_SCREEN_HF / c.v[3];
    z = inv;
}

// One part: output sink (packet slab, or TA store queues with TA_DIRECT),
// the meshlet cache and the per-meshlet passes.
// ------------------------------------------------------------ 16-bit UV --
// NATIVE_ACTOR_UV16: the TA's 16-bit UV vertex (PCW bit 0) takes u and v as
// the upper halves of their IEEE floats (bf16: 8 significant bits), packed
// u:v in word 4, and stores 20 instead of 24 bytes per vertex. A part uses it
// only when the rounding (half an ulp at its largest |u| or |v|) stays within
// half a texel of its texture; else its header keeps 32-bit UV. Word 5 and the
// offset colour (word 7, unused: no specular in these headers) are ignored by
// the TA; word 7 keeps the float u for the near-plane clipper.
#ifndef RE4DC_ACTOR_UV16
#define RE4DC_ACTOR_UV16 0
#endif
constexpr u32 kPcwUv16 = 1U;             // PVR_TA_CMD_UVFMT
constexpr u32 kPcwStripLength6 = 3U << 18;  // PCW strip length 19:18 = 3 (6 triangles), group enable (bit 23) kept
// Words of a pvr_vertex_t (4 = u, 5 = v, 7 = oargb), read as bits.
typedef u32 __attribute__((may_alias)) vertex_word;
inline float unpacked_u(const pvr_vertex_t& v) {
    union { u32 w; float f; } x;
    x.w = reinterpret_cast<const vertex_word*>(&v)[7];
    return x.f;
}
// keep_u: the cache (clipper input) keeps the float u in word 7. Rounds to
// nearest (a carry into the exponent is the correct rounding).
inline void pack_uv16(pvr_vertex_t* v, unsigned n, bool keep_u) {
    for (unsigned i = 0; i < n; ++i) {
        vertex_word* w = reinterpret_cast<vertex_word*>(v + i);
        const u32 u = w[4], t = w[5];
        if (keep_u) w[7] = u;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
        w[4] = re4dc::format32::uv_pack(u, t);
#else
        w[4] = ((u + 0x8000U) & 0xFFFF0000U) | ((t + 0x8000U) >> 16);
#endif
    }
}
// With no scroll and a power-of-two image (u_scale 1), u = raw x 2^-k: its
// bf16 is exact when raw has <= 8 significant bits and otherwise off by up to
// 2^(excess-1) raw units = 2^(excess-1) x uv_scale x size texels, which must
// stay within half a texel. Scrolled or padded textures keep 32-bit UV.
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
namespace uv32 {
re4dc::format32::UvCounters counters;
#if RE4DC_ACTOR_SOURCE_SPAN
#include "include/actor_source_span.inc"
#endif
#include "include/actor_format32_uv_source.inc"
void log(unsigned frame) {
    if (frame % 120U) return;
    const auto& s=counters;
    re4dc_log("AF32UV frame=%u parts=%u admitted=%u declined=%u why=legacy:%u,binding:%u,precision:%u,nonfinite:%u,begin:%u,source:%u scanned_records=%u splits=%u path=packet:%u,direct:%u,shared:%u\n",
        frame,s.parts,s.admitted,s.parts-s.admitted,s.legacy,s.binding,s.precision,s.nonfinite,
        s.begin_failed,s.source,s.scanned_records,s.splits,s.packet,s.direct,s.shared);
#if RE4DC_ACTOR_SOURCE_SPAN
    re4dc_log("ASPAN f=%u preparations=%u hits=%u geometry_records=%u cache_bytes=%u span_bytes=%u\n",
        frame,span_preparations,span_hits,span_records,unsigned(sizeof(span_entries)),unsigned(sizeof(Re4dcActorSourceSpan)));
#endif
}
}
#endif
[[maybe_unused]] bool uv16_safe(const Re4dcModelPart& p, const BlobHeader& b) {
    const float uv_scale = (p.flags & 0x80000000U) ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const unsigned excess = uv_excess_bits(b);
    for (unsigned a = 0; a < 2; ++a) {
        const unsigned size = a ? p.image.height : p.image.width;
        if (p.uv_offset[a] != 0.0f || size < 8 || size > 1024 || (size & (size - 1))) return false;
        if (excess && std::ldexp(uv_scale * float(size), int(excess) - 1) > 0.5f) return false;
    }
    return true;
}

#if RE4DC_COARSE_ONE_SUBMIT == 2
// COARSE_ONE_SUBMIT=2 (check build): the TA words a direct Part sends, folded (FNV) while one_tap.on, and the
// header its window opened with (the slab slot before the cache). re4dc_actor_submit_chunks compares both
// paths' words chunk by chunk.
struct OneTap { bool on, header_seen; u32 h, words, header[8]; };
OneTap one_tap{};
inline void one_fold(u32 w) { one_tap.h = (one_tap.h ^ w) * 16777619U; ++one_tap.words; }
inline void one_header(const pvr_vertex_t* cache) {
    if (one_tap.header_seen) return;
    one_tap.header_seen = true;
    std::memcpy(one_tap.header, cache - 1, 32);
}
void one_tap_meshlet(const pvr_vertex_t* cache, const u8* index, unsigned n) {  // emit_meshlet<true>
    if (!one_tap.on) return;
    one_header(cache);
    for (unsigned k = 0; k < n; ++k) {
        const u32* w = reinterpret_cast<const u32*>(cache + (index[k] & 127U));
        one_fold((index[k] & 128U) ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX);
        for (unsigned j = 1; j < 8; ++j) one_fold(w[j]);
    }
}
void one_tap_strip(const pvr_vertex_t* cache, const u8* index, unsigned n) {  // emit_sq
    if (!one_tap.on) return;
    one_header(cache);
    for (unsigned k = 0; k < n; ++k) {
        const u32* w = reinterpret_cast<const u32*>(cache + (index[k] & 127U));
        one_fold(k + 1 == n ? PVR_CMD_VERTEX_EOL : w[0]);
        for (unsigned j = 1; j < 8; ++j) one_fold(w[j]);
    }
}
void one_tap_put(const pvr_vertex_t* cache, const pvr_vertex_t* v, unsigned n) {  // re4dc_ta_put
    if (!one_tap.on) return;
    one_header(cache);
    const u32* w = reinterpret_cast<const u32*>(v);
    for (unsigned j = 0; j < n * 8U; ++j) one_fold(w[j]);
}
#endif

#if RE4DC_ACTOR_BACKFACE_CONE
// ACTOR_BACKFACE_CONE at draw. With [X' Y' W] = A x + t the matrix a meshlet's raw positions go through (skinned:
// screen x [R_i q | t_i] of its palette entry; rigid: the part's screen rows), the PVR's screen area of an even strip
// triangle is det(A) dot(n, a - e) / (W_a W_b W_c), e = -A^-1 t the eye in that space and n the drawn-winding normal.
// The TA rejects area >= 0 for cull 2 (CW) and <= 0 for cull 1, so with s = (cull 2 ? 1 : -1) sign(det A) a meshlet is
// rejected when s dot(n, p - e) > 0 for every normal n of its cone and every point p of its sphere: with w = c - e and
// dw = s dot(axis, w), dw cos(theta) - r > sin(theta) sqrt(|w|^2 - dw^2).
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
struct AbcEye { unsigned pal = ~0U; bool ok = false; float e[3] = {0, 0, 0}, s = 0.0f; re4dc::cone32::Guard guard; };
#else
struct AbcEye { unsigned pal = ~0U; bool ok = false; float e[3] = {0, 0, 0}, s = 0.0f; };
#endif
float abc_tab[128];  // cos(theta_k), sin^2(theta_k)
bool abc_tab_ready = false;
bool abc_eye(const Frame& f, unsigned cull, unsigned pal, AbcEye& out) {
    if (out.pal == pal) return out.ok;
    out.pal = pal; out.ok = false;
    const float* S = f.screen;
    float A[3][3], t[3];
    if (f.mode == kSkin) {
        if (pal >= f.palette_entries || !f.palette) return false;
        const float* P = f.palette + pal * 12U;
        const float q = f.q;
        for (unsigned r = 0; r < 3; ++r) {
            for (unsigned c = 0; c < 3; ++c)
                A[r][c] = (S[r] * P[c * 3] + S[4 + r] * P[c * 3 + 1] + S[8 + r] * P[c * 3 + 2]) * q;
            t[r] = S[r] * P[9] + S[4 + r] * P[10] + S[8 + r] * P[11] + S[12 + r];
        }
    } else if (f.mode == kRigid) {
        for (unsigned r = 0; r < 3; ++r) { for (unsigned c = 0; c < 3; ++c) A[r][c] = S[c * 4 + r]; t[r] = S[12 + r]; }
    } else {
        return false;
    }
    const float c00 = A[1][1] * A[2][2] - A[1][2] * A[2][1], c01 = A[0][2] * A[2][1] - A[0][1] * A[2][2],
                c02 = A[0][1] * A[1][2] - A[0][2] * A[1][1];
    const float c10 = A[1][2] * A[2][0] - A[1][0] * A[2][2], c11 = A[0][0] * A[2][2] - A[0][2] * A[2][0],
                c12 = A[0][2] * A[1][0] - A[0][0] * A[1][2];
    const float c20 = A[1][0] * A[2][1] - A[1][1] * A[2][0], c21 = A[0][1] * A[2][0] - A[0][0] * A[2][1],
                c22 = A[0][0] * A[1][1] - A[0][1] * A[1][0];
    const float det = A[0][0] * c00 + A[0][1] * c10 + A[0][2] * c20;
    if (!(std::fabs(det) > 1e-20f) || !re4dc::render::is_finite(det)) return false;
    const float id = -1.0f / det;
    out.e[0] = (c00 * t[0] + c01 * t[1] + c02 * t[2]) * id;
    out.e[1] = (c10 * t[0] + c11 * t[1] + c12 * t[2]) * id;
    out.e[2] = (c20 * t[0] + c21 * t[1] + c22 * t[2]) * id;
    if (!re4dc::render::is_finite(out.e[0]) || !re4dc::render::is_finite(out.e[1]) || !re4dc::render::is_finite(out.e[2]))
        return false;
    out.s = ((cull == 2U) == (det > 0.0f)) ? 1.0f : -1.0f;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    const float adj[9] = {c00,c01,c02,c10,c11,c12,c20,c21,c22};
    if (!re4dc::cone32::prepare(&A[0][0], t, adj, det, out.e, f.near_distance, out.guard)) {
        ++abc32_stats.numeric; return false;
    }
#endif
    out.ok = true;
    return true;
}
inline bool abc_reject(const AbcCone& c, const AbcEye& eye) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    ++abc32_stats.tested;
    const auto result = c.k <= 56U ? re4dc::cone32::test(c, eye, eye.guard, abc_tab[c.k], abc_tab[64+c.k])
                                  : re4dc::cone32::Empty;
    if (result == re4dc::cone32::Near) ++abc32_stats.near;
    else if (result == re4dc::cone32::Numeric) ++abc32_stats.numeric;
    else if (result == re4dc::cone32::Empty) ++abc32_stats.empty;
    else if (result == re4dc::cone32::Reject) { ++abc32_stats.rejected; return true; }
    return false;
#endif
    const float wx = float(c.c[0]) - eye.e[0], wy = float(c.c[1]) - eye.e[1], wz = float(c.c[2]) - eye.e[2];
    const float dw = eye.s * (float(c.a[0]) * wx + float(c.a[1]) * wy + float(c.a[2]) * wz) * (1.0f / 32767.0f);
    const float t = dw * abc_tab[c.k] - float(c.r);
    if (!(t > 0.0f)) return false;
    const float rest = wx * wx + wy * wy + wz * wz - dw * dw;
    return t * t > abc_tab[64 + c.k] * (rest > 0.0f ? rest : 0.0f);
}
// The part's cone table when this draw can use it (culling part, skinned or rigid frame, converted in place).
const AbcCone* abc_part(const Re4dcModelPart& p, const u8* base, const Frame& f, unsigned& cls) {
    cls = 0; ++abc_part_calls; if (p.cull == 1 || p.cull == 2) ++abc_part_cull;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    using namespace re4dc::cone32;
    if ((p.cull != 1 && p.cull != 2) || p.blend != 0 || (p.material_flags & 4U) || p.depth_mode != 0) {
        abc32_stats.decline(Cull); return nullptr;
    }
    if (base != p.stream) { abc32_stats.decline(Transient); return nullptr; }
    if (f.mode != kSkin && f.mode != kRigid) { abc32_stats.decline(re4dc::cone32::Mode); return nullptr; }
    const AbcCone* certified = abc_table(base, p.stream_bytes, &cls);
    if (!certified) { abc32_stats.decline(Table); return nullptr; }
    SourceIdentity identity;
    const auto& h = *reinterpret_cast<const BlobHeader*>(base);
    std::memcpy(&identity, base + abc_tail_at(p.stream_bytes, h.meshlets) + sizeof(AbcTail), sizeof(identity));
    Re4dcActorSource current{};
    if ((f.mode == kRigid && (!p.static_geometry || p.position_stride != 8 || p.positions != f.positions)) ||
        (f.mode == kSkin && p.position_stride != 6) || f.position_stride != 8 ||
        !re4dc_actor_model_source(p.info, &current) || current.positions != f.positions ||
        current.position_count != f.position_count || current.position_count != p.position_count ||
        !identity.matches(p.info, current.positions, current.position_count, p.position_stride)) {
        abc32_stats.decline(Source); return nullptr;
    }
#endif
    if ((p.cull != 1 && p.cull != 2) || base != p.stream || (f.mode != kSkin && f.mode != kRigid)) return nullptr;
    if (!abc_tab_ready) {
        for (unsigned k = 0; k < 64; ++k) {
            const float th = float(k) * kAbcStep;
            abc_tab[k] = std::cos(th); abc_tab[64 + k] = std::sin(th) * std::sin(th);
        }
        abc_tab_ready = true;
    }
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
    ++abc32_stats.admitted;
    return certified;
#else
    return abc_table(base, p.stream_bytes, &cls);
#endif
}
#endif
#if RE4DC_ACTOR_SETUP_LEAN && RE4DC_AVK
template<class Args> struct AvkSetup {
    Args args;
    unsigned (*kernel)(const Args*);
    unsigned state;  // 0: not prepared; light setup uses 1 + its cached eligibility reason
    // Deliberately leave the argument block untouched: its first eligible use writes every field. An aggregate
    // default initializer here would clear the same 112 bytes that this option is intended to stop rewriting.
    AvkSetup() : state(0) {}
};
#endif
struct Part {
    const Re4dcModelPart& p;
    Frame& f;
    Projection projection;
    re4dc::render::ClipParameters clip;
    Re4dcModelPacket packet{};
    Cache cache{};
    unsigned used = 0, input = 0, output = 0, primed = 0;
#if RE4DC_ACTOR_CLIP_FRONT26
    unsigned clip_vertices = 0; // current meshlet, validates cached clip indices
#endif
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
    // Unlike flags/oargb, this must start fresh for each Part even when a OneWindow reuses its cache.
    unsigned flat_primed = 0;
#endif
    bool streaming = false, committed = false;
#if RE4DC_NATIVE_FE_CONTINUATION
    struct NativeContinuationProgress* continuation=nullptr;
#endif
#if RE4DC_ACTOR_DIRECT
    bool direct = false;
    std::uint32_t* sq = nullptr;
    unsigned slots = 0;
#endif
    bool uv16 = false;  // NATIVE_ACTOR_UV16: word 4 = bf16 u | v, word 7 = float u (for the clipper)
    // Records / lights of the current meshlet.
    const u8* rec = nullptr;
    unsigned rs = 6, color_index = 0;
    const u8* colors = nullptr;
    u32 alpha = 0;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    bool dsa_xlu = re4dc_dsa24_model_translucent(&p) != 0;
    unsigned dsa_classified = 0, dsa_overlap = 0;
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    unsigned dsa28_cls = re4dc_dsa28_model_class(&p);
#endif
    void dsa_strip_overlap(const u8* index, unsigned n) {
        if (!dsa_xlu || n < 3) return;
        dsa_classified += n - 2;
        for (unsigned t = 0; t < n - 2; ++t) {
            const unsigned common = cache.oc[index[t] & 127U] &
                cache.oc[index[t + 1] & 127U] & cache.oc[index[t + 2] & 127U];
            if (!(common & kOcScreen)) ++dsa_overlap;
        }
    }
    void dsa_known_overlap(unsigned n) {
        if (dsa_xlu) { dsa_classified += n; dsa_overlap += n; }
    }
    // Existing topology totals cover the ordinary and shared chunk backends.
    // Output is CPU-emitted topology, not pixel/depth visibility on the PVR.
    ~Part() {
        re4dc::dsa24::count(re4dc::dsa24::TrianglesIn, input);
        re4dc::dsa24::count(re4dc::dsa24::TrianglesOut, output);
        if (dsa_xlu) {
            re4dc::dsa24::count(re4dc::dsa24::XluSubmitted, output);
            re4dc::dsa24::count(re4dc::dsa24::XluViewOverlap, dsa_overlap);
            // Alternate chunk backends can emit outside Part's strip sinks.
            // Keep their submitted count; never invent their overlap count.
            if (dsa_classified != output)
                re4dc::dsa24::count(re4dc::dsa24::Unsupported);
        }
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
        // The optional backface path retains pre-backface output accounting.
        re4dc::dsa24::count(re4dc::dsa24::Unsupported);
#endif
    }
#endif
#if RE4DC_ACTOR_SETUP_LEAN && RE4DC_AVK
    AvkSetup<AvkPos> position_setup;
    AvkSetup<AvkLight> light_setup;
#endif

    bool flush() {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
        if (!streaming) return false;
        re4dc_model_packet_commit(used); committed = true;
#if RE4DC_NATIVE_FE_CONTINUATION
        if(continuation && used) {
            ++continuation->result.submitted;
            continuation->result.outcome=re4dc::NativeDrawOutcome::Submitted;
            Re4dcActorStreamState state{};
            if(!re4dc_actor_stream_state(&state))return false;
        }
#endif
        used = 0; ++stats.flushes;
        return true;
    }
    bool room(unsigned n) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
#if RE4DC_ACTOR_DIRECT
        if (direct) return slots + n <= 32767U;
#endif
        return packet.capacity - used >= n || (flush() && packet.capacity >= n);
    }
    pvr_vertex_t* at() { return static_cast<pvr_vertex_t*>(packet.vertices) + used; }
    void put(const pvr_vertex_t* v, unsigned n) {  // prepared vertices (clipped triangles)
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        if (re4dc::dsa24::x28::sample) re4dc::dsa24::x28::packet(dsa28_cls, p.cull, v, n, PVR_CMD_VERTEX_EOL);
#endif
#endif
#if RE4DC_ACTOR_DIRECT
#if RE4DC_COARSE_ONE_SUBMIT == 2
        if (direct) one_tap_put(cache.v, v, n);
#endif
        if (direct) { sq = re4dc_ta_put(sq, v, n); slots += n; return; }
#endif
        std::memcpy(at(), v, n * sizeof(pvr_vertex_t)); used += n;
    }
    void strip(const u8* index, unsigned n) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
        dsa_strip_overlap(index, n);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        if (re4dc::dsa24::x28::sample) re4dc::dsa24::x28::strip(dsa28_cls, p.cull, cache.v, index, n, 127U);
#endif
#endif
#if RE4DC_ACTOR_DIRECT
#if RE4DC_COARSE_ONE_SUBMIT == 2
        if (direct) one_tap_strip(cache.v, index, n);
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
#if RE4DC_CPU_BACKFACE == 2
        if (direct && bf_on()) { bf_send(index, n); return; }
#else
        if (direct && (p.cull == 1 || p.cull == 2)) { bf_send(index, n); return; }
#endif
#endif
        if (direct) { sq = emit_sq(sq, cache.v, index, n); slots += n; return; }
#endif
        emit(at(), cache.v, index, n); used += n;
    }
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE && RE4DC_ACTOR_DIRECT
#if RE4DC_CPU_BACKFACE == 2
    bool bf_on() const {
        // Generic/source submissions need the same material exclusions as
        // owned runs. Preserve their original copy/header for these parts.
#if defined(RE4DC_BACKFACE_ROOMS) && RE4DC_BACKFACE_ROOMS
        return re4dc_bf_room_on && (p.cull == 1 || p.cull == 2) && !(p.material_flags & 4u) && p.depth_mode == 0;
#else
        return (p.cull == 1 || p.cull == 2) && !(p.material_flags & 4u) && p.depth_mode == 0;
#endif
    }
#endif
    // CPU_BACKFACE (lane backface22): only the triangles the ISP keeps (room/backface_emit.hpp); cull-none parts never
    // come here.
    void bf_send(const u8* index, unsigned n) {
#if RE4DC_CPU_BACKFACE == 2
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
        RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));
#endif
        // An unclipped strip: assembly classifies and emits its kept runs;
        // mask127 removes the actor EOL bit from every cache lookup.
        slots += re4dc::bf::strip_sq(cache.v, index, n, 127u, p.cull, sq);
#else
        slots += re4dc::bf::strip(cache.v, index, n, 127u, p.cull,
                                  [&](const std::uint8_t* i, unsigned c) { sq = emit_sq(sq, cache.v, i, c); });
#endif
    }
#if RE4DC_CPU_BACKFACE == 2
    void bf_whole(const u8* index, unsigned n) {
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
        RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));
#endif
        // One whole-meshlet call retains the assembly index/SQ walk. The
        // kernel resets strip parity at bit7 EOL (mask0x17f); no C scan.
        slots += re4dc::bf::stream_sq(cache.v, index, n, p.cull, sq);
    }
#endif
#endif
    // A meshlet with no corner outside, beyond far or in front of near.
    bool fits(unsigned n) const {
#if RE4DC_ACTOR_DIRECT
        if (direct) return slots + n <= 32767U;
#endif
        return packet.capacity - used >= n || (streaming && packet.capacity >= n);
    }
    bool whole(const u8* index, unsigned count, unsigned triangles) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_submit(re4dc::dsa24::Submit);
#endif
        if (!room(count)) return false;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        dsa_known_overlap(triangles);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        if (re4dc::dsa24::x28::sample) re4dc::dsa24::x28::meshlet(dsa28_cls, p.cull, cache.v, index, count);
#endif
#endif
#if RE4DC_ACTOR_DIRECT
        if (direct) {
#if RE4DC_COARSE_ONE_SUBMIT == 2
            one_tap_meshlet(cache.v, index, count);
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
#if RE4DC_CPU_BACKFACE == 2
            if (bf_on()) {
#else
            if (p.cull == 1 || p.cull == 2) {
#endif
#if RE4DC_CPU_BACKFACE == 2
                bf_whole(index, count);
#else
                // the meshlet's strips (bit 7 = the strip's last index), each through the back-face split
                unsigned a = 0;
                for (unsigned k = 0; k < count; ++k)
                    if (index[k] & 128u) { bf_send(index + a, k + 1 - a); a = k + 1; }
                if (a < count) bf_send(index + a, count - a);
#endif
                input += triangles; output += triangles;
                return true;
            }
#endif
            sq = static_cast<std::uint32_t*>(emit_meshlet<true>(sq, cache.v, index, count)); slots += count;
        } else
#endif
        { emit_meshlet<false>(at(), cache.v, index, count); used += count; }
        input += triangles; output += triangles;
        return true;
    }
    // Flags/oargb words of the cache entries (the passes never write them).
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
    void flat_colors(unsigned n, u32 argb) {
        if (n <= flat_primed) return;
        unsigned i = flat_primed;
        pvr_vertex_t* v = cache.v + i;
        for (; i + 4 <= n; i += 4, v += 4) {
            v[0].argb = argb; v[1].argb = argb; v[2].argb = argb; v[3].argb = argb;
        }
        for (; i < n; ++i, ++v) v->argb = argb;
        flat_primed = n;
    }
#endif
    void prime(unsigned n) {
        for (; primed < n; ++primed) { cache.v[primed].flags = PVR_CMD_VERTEX; cache.v[primed].oargb = 0; }
    }

    // One meshlet's strips. Each is decided before anything is written (the
    // direct TA path cannot take vertices back): culled when all corners are
    // outside one screen edge or beyond far, copied when no corner is in
    // front of the near plane, else clipped per triangle.
    bool strips(const Records& r, const u8* index, unsigned count) {
        const u8* end = index + count;
        while (index < end) {
            const Strip s = scan(cache.oc, index);
            input += s.n - 2;
            if (s.all & kOcCull) {
                ++stats.strips_culled;
            } else if (!(s.any & kOcNear)) {
                if (!room(s.n)) return false;
                strip(index, s.n);
                output += s.n - 2;
            } else if (!clip_strip(r, index, s.n)) {
                return false;
            }
            index += s.n;
        }
        return true;
    }
    bool clip_strip(const Records& r, const u8* index, unsigned n) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
        re4dc::dsa24::Scope dsa_clip(re4dc::dsa24::Clip);
        re4dc::dsa24::count(re4dc::dsa24::ClipStrips);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_MODEL_HIT(ActorClipStrip, 1)
#endif
        ++stats.fallback_runs;
#if RE4DC_ACTOR_CLIP_FRONT26
        return re4dc::actor_clip26::walk_strip<RE4DC_ACTOR_CLIP_REUSE != 0, kOcNear | kOcFar>(
            index, n, cache.v, cache.oc, clip_vertices, p.cull, clip.width, clip.height,
            [&](unsigned corner, re4dc::render::RenderVertex& v, float& opacity) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                re4dc::dsa24::count(re4dc::dsa24::ClipRebuilds);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
                DFA26_MODEL_HIT(ActorClipRebuild, 1)
#endif
                const unsigned li = index[corner] & 127U;
                float w[3], nn[3];
                world_of(f, p, r, li, w, nn);
                v = {};
                float x = w[0], y = w[1], z = w[2];
                v.position.world_x = x; v.position.world_y = y; v.position.world_z = z;
                v.position.depth = -z;
                if (z != 0.0f) project(x, y, z, &projection);
                v.position.x = x; v.position.y = y; v.position.z = z;
                v.u = uv16 ? unpacked_u(cache.v[li]) : cache.v[li].u; v.v = cache.v[li].v;
                const u32 rgb = cache.v[li].argb;
                v.light_red = float((rgb >> 16) & 255) * (1.0f / 255.0f);
                v.light_green = float((rgb >> 8) & 255) * (1.0f / 255.0f);
                v.light_blue = float(rgb & 255) * (1.0f / 255.0f);
                opacity = float(colors ? colors[r.ci(li) * 4 + 3] : (p.alpha_state & 255)) * (1.0f / 255.0f);
            },
            [&](const re4dc::render::RenderVertex* in, const float* opacity) {
                pvr_vertex_t triangles[6];
                const unsigned m = re4dc::render::clip_projected_triangle(in, triangles, u8(p.cull), clip, nullptr, opacity);
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
                DFA26_MODEL_HIT(ActorClipTriangle, 1)
#endif
            ++stats.fallback_triangles;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                re4dc::dsa24::count(re4dc::dsa24::ClipTriangles);
#endif
                if (uv16) pack_uv16(triangles, 3 * m, false);
                if (m && !room(3 * m)) return false;
                put(triangles, 3 * m); output += m;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                dsa_known_overlap(m);
#endif
                return true;
            },
            [&](const pvr_vertex_t* triangles) {
                if (!room(3)) return false;
                put(triangles, 3); ++output;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                dsa_known_overlap(1);
#endif
                return true;
            });
#elif RE4DC_ACTOR_CLIP_REUSE
        return re4dc::actor_clip::reuse_strip(n,
            [&](unsigned corner, re4dc::render::RenderVertex& v, float& opacity) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                re4dc::dsa24::count(re4dc::dsa24::ClipRebuilds);
#endif
                const unsigned li = index[corner] & 127U;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
                DFA26_MODEL_HIT(ActorClipRebuild, 1)
#endif
                float w[3], nn[3];
                world_of(f, p, r, li, w, nn);
                v = {};
                float x = w[0], y = w[1], z = w[2];
                v.position.world_x = x; v.position.world_y = y; v.position.world_z = z;
                v.position.depth = -z;
                if (z != 0.0f) project(x, y, z, &projection);
                v.position.x = x; v.position.y = y; v.position.z = z;
                v.u = uv16 ? unpacked_u(cache.v[li]) : cache.v[li].u; v.v = cache.v[li].v;
                const u32 rgb = cache.v[li].argb;
                v.light_red = float((rgb >> 16) & 255) * (1.0f / 255.0f);
                v.light_green = float((rgb >> 8) & 255) * (1.0f / 255.0f);
                v.light_blue = float(rgb & 255) * (1.0f / 255.0f);
                opacity = float(colors ? colors[r.ci(li) * 4 + 3] : (p.alpha_state & 255)) * (1.0f / 255.0f);
            },
            [&](const re4dc::render::RenderVertex* in, const float* opacity) {
                pvr_vertex_t triangles[6];
                const unsigned m = re4dc::render::clip_projected_triangle(in, triangles, u8(p.cull), clip, nullptr, opacity);
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
                DFA26_MODEL_HIT(ActorClipTriangle, 1)
#endif
            ++stats.fallback_triangles;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                re4dc::dsa24::count(re4dc::dsa24::ClipTriangles);
#endif
                if (uv16) pack_uv16(triangles, 3 * m, false);
                if (m && !room(3 * m)) return false;
                put(triangles, 3 * m);
                output += m;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                dsa_known_overlap(m);
#endif
                return true;
            });
#else
        for (unsigned t = 0; t + 2 < n; ++t) {
            unsigned tri[3] = {t, t + 1, t + 2};
            if (t & 1) std::swap(tri[0], tri[1]);  // strip parity
            re4dc::render::RenderVertex in[3];
            float opacity[3];
            for (unsigned k = 0; k < 3; ++k) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
                re4dc::dsa24::count(re4dc::dsa24::ClipRebuilds);
#endif
                const unsigned li = index[tri[k]] & 127U;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
                DFA26_MODEL_HIT(ActorClipRebuild, 1)
#endif
                float w[3], nn[3];
                world_of(f, p, r, li, w, nn);
                auto& v = in[k];
                v = {};
                float x = w[0], y = w[1], z = w[2];
                v.position.world_x = x; v.position.world_y = y; v.position.world_z = z;
                v.position.depth = -z;
                if (z != 0.0f) project(x, y, z, &projection);
                v.position.x = x; v.position.y = y; v.position.z = z;
                v.u = uv16 ? unpacked_u(cache.v[li]) : cache.v[li].u; v.v = cache.v[li].v;
                const u32 rgb = cache.v[li].argb;
                v.light_red = float((rgb >> 16) & 255) * (1.0f / 255.0f);
                v.light_green = float((rgb >> 8) & 255) * (1.0f / 255.0f);
                v.light_blue = float(rgb & 255) * (1.0f / 255.0f);
                opacity[k] = float(colors ? colors[r.ci(li) * 4 + 3] : (p.alpha_state & 255)) * (1.0f / 255.0f);
            }
            pvr_vertex_t triangles[6];
            const unsigned m = re4dc::render::clip_projected_triangle(in, triangles, u8(p.cull), clip, nullptr, opacity);
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
            DFA26_MODEL_HIT(ActorClipTriangle, 1)
#endif
            ++stats.fallback_triangles;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
            re4dc::dsa24::count(re4dc::dsa24::ClipTriangles);
#endif
            if (uv16) pack_uv16(triangles, 3 * m, false);
            if (m && !room(3 * m)) return false;
            put(triangles, 3 * m);
            output += m;
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
            dsa_known_overlap(m);
#endif
        }
        return true;
#endif
    }
};

#if RE4DC_ACTOR_SKIN_FTRV == 2 && defined(__sh__) && !defined(ACTOR_TEST_XMTRX)
// Check build, actual vertices: each skinned run of records is transformed again by the same kernel
// with the scalar-built matrix in XMTRX (the pre-FTRV path), and the submitted screen x/y, 1/w and
// every outcode bit are compared before any filtering. Near-plane clipped triangles are rebuilt from
// world_of + project, which never read this matrix, so equal outcodes mean equal cull / copy / clip
// decisions and equal clipped geometry.
struct SkinVertexCheck {
    unsigned runs, verts, len_mis, oc_mis, near_mis, screen_mis, far_mis, nan_new, nan_ref, near_verts,
        near_band, px_q, px_1;
    float px_front, px_screen, rel_inv;
};
SkinVertexCheck skin_vc;
alignas(32) pvr_vertex_t skin_ref_v[kMaxVertices];
u8 skin_ref_oc[kMaxVertices];
void skin_check_vertices(Part& e, const u8* at, unsigned rs, unsigned n, int palette, const pvr_vertex_t* got,
                         const u8* goc, unsigned done, const PosConst& k, bool s16_uv) {
    Frame& f = e.f;
    const unsigned pi = unsigned(palette) < f.palette_entries ? unsigned(palette) : 0U;
    const float* P = f.palette + pi * 12;
    alignas(8) float ref[16];
    for (unsigned c = 0; c < 4; ++c) {
        const float v[4] = {P[c * 3] * (c < 3 ? f.q : 1.0f), P[c * 3 + 1] * (c < 3 ? f.q : 1.0f),
                            P[c * 3 + 2] * (c < 3 ? f.q : 1.0f), c < 3 ? 0.0f : 1.0f};
        mul4(f.screen, v, ref + c * 4);
    }
    load_xmtrx(ref);
    unsigned all = ~0U, any = 0, rdone;
#if RE4DC_ACTOR_ASM
    if (s16_uv && f.position_stride == 8)
        rdone = positions_asm<kPos8Check>(at, rs, n, f.positions, palette, e.p.uv, skin_ref_v, skin_ref_oc, k, all, any);
    else if (s16_uv && f.position_stride == 6)
        rdone = positions_asm<kPos6>(at, rs, n, f.positions, 0, e.p.uv, skin_ref_v, skin_ref_oc, k, all, any);
    else
#endif
        rdone = positions_c(at, rs, n, f.positions, f.position_stride, true, palette, e.p.uv, s16_uv, skin_ref_v,
                            skin_ref_oc, k, all, any);
    ++skin_vc.runs;
    if (rdone != done) ++skin_vc.len_mis;
    const unsigned m = rdone < done ? rdone : done;
    const float near_band_inv = 0.5f / k.near_distance;  // 1/w above this: w within twice the near distance
    for (unsigned j = 0; j < m; ++j) {
        const pvr_vertex_t& a = got[j];
        const pvr_vertex_t& b = skin_ref_v[j];
        const unsigned oa = goc[j] & 63U, ob = skin_ref_oc[j] & 63U;
        ++skin_vc.verts;
        if (!skin_finite(a.x) || !skin_finite(a.y) || !skin_finite(a.z)) ++skin_vc.nan_new;
        if (!skin_finite(b.x) || !skin_finite(b.y) || !skin_finite(b.z)) ++skin_vc.nan_ref;
        if (oa != ob) {
            ++skin_vc.oc_mis;
            if ((oa ^ ob) & kOcNear) ++skin_vc.near_mis;
            if ((oa ^ ob) & kOcScreen) ++skin_vc.screen_mis;
            if ((oa ^ ob) & kOcFar) ++skin_vc.far_mis;
        }
        if ((oa | ob) & kOcNear) { ++skin_vc.near_verts; continue; }
        if (b.z > near_band_inv) ++skin_vc.near_band;
        float d = __builtin_fabsf(a.x - b.x);
        const float dy = __builtin_fabsf(a.y - b.y);
        if (dy > d) d = dy;
        if (d > skin_vc.px_front) skin_vc.px_front = d;
        if (!((oa | ob) & kOcCull)) {
            if (d > skin_vc.px_screen) skin_vc.px_screen = d;
            if (d > 0.25f) ++skin_vc.px_q;
            if (d > 1.0f) ++skin_vc.px_1;
        }
        const float r = __builtin_fabsf(a.z - b.z) / b.z;
        if (r > skin_vc.rel_inv) skin_vc.rel_inv = r;
    }
    if ((skin_vc.runs & 0x7FFF) == 0)
        re4dc_log("SKINVTX runs=%u verts=%u len_mismatch=%u outcode_mismatch=%u near=%u screen=%u far=%u "
                  "nonfinite_new=%u nonfinite_ref=%u near_plane_verts=%u near_band_verts=%u max_px_front=%.4f "
                  "max_px_screen=%.4f over_0.25px=%u over_1px=%u max_rel_invw=%.3g clip_runs=%u\n",
                  skin_vc.runs, skin_vc.verts, skin_vc.len_mis, skin_vc.oc_mis, skin_vc.near_mis, skin_vc.screen_mis,
                  skin_vc.far_mis, skin_vc.nan_new, skin_vc.nan_ref, skin_vc.near_verts, skin_vc.near_band,
                  double(skin_vc.px_front), double(skin_vc.px_screen), skin_vc.px_q, skin_vc.px_1,
                  double(skin_vc.rel_inv), unsigned(stats.fallback_runs));
}
#endif

#if RE4DC_AVK
// ACTOR_VTX_KERNEL: pass 1 / pass 2 of a meshlet on avk_sh4.S. A kernel call returns the records
// it did not process: a skinned kernel switches palette entries itself and stops only at an entry
// whose matrix / directions are not built yet. Positions: every entry of the Frame is built before
// its first skinned meshlet (avk_build_all), so one call runs to the end. Lights (directions follow
// each part's light fold): at a stop the C side builds the directions the rest of the meshlet needs
// (avk_build_dirs) and calls once more. Both give the values position_matrix / skin_light_dirs
// give. Returns the records done from 0 (0: the kernel does not apply; the path below finishes
// whatever is left).
//
#if RE4DC_AVK == 2
void avk_check_build(const Frame& f);
unsigned avk_build_mc = 0;  // builds that took the movca.l loop (32-byte aligned skin table)
#endif
// Every position entry of a skinned Frame, built at its first skinned meshlet: one linear walk over
// the palette (48 bytes an entry) and the skin table (64), both prefetched two entries ahead, with
// XMTRX = the screen matrix loaded once; each entry gets skin_position_matrix's operations (FTRV
// form: columns 0-2 x q by fmul with w = 0, the translation with w = 1, each by ftrv). An entry
// position_matrix built already is rebuilt with the same operations, so the same bits. The kernels
// then never stop on a missing entry. (Rev 2 collected the entries a meshlet's records use after
// each stop instead: a scan of every remaining record, 1.49 ms a tick in vl13.) The loop body is
// list-scheduled on the hwsim issue rules (33 model cycles an entry, was 58 as rev 3 compiled it):
// single loads, 64-bit stores (FPSCR.SZ toggled around them; the skin table must be 8-byte aligned,
// else the C loop runs), all 16 FP registers hold the entry, q travels in FPUL.
// Rev 5: with the table 32-byte aligned (an entry = two whole cache lines) each line is allocated by
// movca.l (no fill: every word of it is stored right after, the r0 word first overwritten) and the
// table is not prefetched; vl23 spent 63K cycles a tick waiting on those fills (one fill in flight
// behind the palette's). The ready bytes are set after the loop (the loop's byte store missed on
// ~45% of entries). 31 model cycles an entry.
void avk_build_all(Frame& f) {
    f.avk_all = true;
    const unsigned entries = f.palette_entries;
    if (!entries) return;
#if RE4DC_ACTOR_SKIN_FTRV == 1 && defined(__sh__) && !defined(ACTOR_TEST_XMTRX)
    if (!(reinterpret_cast<std::uintptr_t>(f.skin_positions) & 7U)) {
        load_xmtrx(f.screen);
        const union { float f; u32 u; } qu{f.q};  // (memcpy here is a library call)
        const u32 qb = qu.u, one = 1;
        const float* P = f.palette;
        float* O = f.skin_positions + 4;  // entry 0's column 0 end (each column stored from its end)
        u8* R = f.skin_ready;
        unsigned left = entries;
        u32 x;
        if (!(reinterpret_cast<std::uintptr_t>(f.skin_positions) & 31U)) {
            __asm__ __volatile__(
                "lds     %[qb],fpul\n"
                "1:\n\t"
                "fsts    fpul,fr15\n\t"     /* q */
                "mov     %[P],%[x]\n\t"
                "fmov.s  @%[P]+,fr0\n\t"
                "fmov.s  @%[P]+,fr1\n\t"
                "add     #96,%[x]\n\t"      /* palette entry k+2 */
                "fmov.s  @%[P]+,fr2\n\t"
                "fmul    fr15,fr0\n\t"
                "fmov.s  @%[P]+,fr4\n\t"
                "dt      %[left]\n\t"
                "fmul    fr15,fr2\n\t"
                "fmov.s  @%[P]+,fr5\n\t"
                "fmul    fr15,fr1\n\t"
                "fmov.s  @%[P]+,fr6\n\t"
                "fmov.s  @%[P]+,fr8\n\t"
                "fmul    fr15,fr4\n\t"
                "fmul    fr15,fr5\n\t"
                "fldi0   fr3\n\t"
                "ftrv    xmtrx,fv0\n\t"
                "fmov.s  @%[P]+,fr9\n\t"
                "fmul    fr15,fr8\n\t"
                "fmov.s  @%[P]+,fr10\n\t"
                "fmul    fr15,fr6\n\t"
                "fldi0   fr7\n\t"
                "fmov.s  @%[P]+,fr12\n\t"
                "fmul    fr15,fr9\n\t"
                "fmov.s  @%[P]+,fr13\n\t"
                "ftrv    xmtrx,fv4\n\t"
                "fldi0   fr11\n\t"
                "fmov.s  @%[P]+,fr14\n\t"
                "fmul    fr15,fr10\n\t"
                "pref    @%[x]\n\t"
                "movca.l r0,@%[O]\n\t"      /* line 0 of the entry (O = entry + 16) */
                "fschg\n\t"
                "fmov    dr2,@-%[O]\n\t"
                "ftrv    xmtrx,fv8\n\t"
                "fmov    dr0,@-%[O]\n\t"
                "add     #32,%[O]\n\t"
                "fldi1   fr15\n\t"
                "add     #32,%[x]\n\t"
                "fmov    dr6,@-%[O]\n\t"
                "fmov    dr4,@-%[O]\n\t"
                "ftrv    xmtrx,fv12\n\t"
                "add     #32,%[O]\n\t"
                "pref    @%[x]\n\t"
                "movca.l r0,@%[O]\n\t"      /* line 1 (O = entry + 48) */
                "fmov    dr10,@-%[O]\n\t"
                "fmov    dr8,@-%[O]\n\t"
                "add     #32,%[O]\n\t"
                "fmov    dr14,@-%[O]\n\t"
                "fmov    dr12,@-%[O]\n\t"
                "fschg\n\t"
                "bf/s    1b\n\t"
                "add     #32,%[O]\n"
                : [P] "+r"(P), [O] "+r"(O), [left] "+r"(left), [x] "=&r"(x)
                : [qb] "r"(qb)
                : "r0", "fpul", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "fr8", "fr9", "fr10", "fr11",
                  "fr12", "fr13", "fr14", "fr15", "t", "memory");
            std::memset(R, 1, entries);
#if RE4DC_AVK == 2
            ++avk_build_mc;
            avk_check_build(f);
#endif
            return;
        }
        __asm__ __volatile__(
            "lds     %[qb],fpul\n"
            "1:\n\t"
            "fsts    fpul,fr15\n\t"     /* q */
            "mov     %[P],%[x]\n\t"
            "fmov.s  @%[P]+,fr0\n\t"
            "fmov.s  @%[P]+,fr1\n\t"
            "fmul    fr15,fr0\n\t"
            "fmov.s  @%[P]+,fr2\n\t"
            "fmul    fr15,fr1\n\t"
            "fmov.s  @%[P]+,fr4\n\t"
            "fmov.s  @%[P]+,fr5\n\t"
            "fmov.s  @%[P]+,fr6\n\t"
            "fmul    fr15,fr4\n\t"
            "fldi0   fr7\n\t"
            "add     #96,%[x]\n\t"      /* palette entry k+2 */
            "fldi0   fr3\n\t"
            "fmul    fr15,fr2\n\t"
            "fmov.s  @%[P]+,fr8\n\t"
            "fmul    fr15,fr5\n\t"
            "fmov.s  @%[P]+,fr9\n\t"
            "fmul    fr15,fr6\n\t"
            "fmov.s  @%[P]+,fr10\n\t"
            "ftrv    xmtrx,fv0\n\t"
            "pref    @%[x]\n\t"
            "add     #32,%[x]\n\t"
            "pref    @%[x]\n\t"
            "fmul    fr15,fr9\n\t"
            "fmul    fr15,fr8\n\t"
            "fldi0   fr11\n\t"
            "ftrv    xmtrx,fv4\n\t"
            "fmov.s  @%[P]+,fr12\n\t"
            "fmov.s  @%[P]+,fr13\n\t"
            "fmul    fr15,fr10\n\t"
            "mov     %[O],%[x]\n\t"
            "fmov.s  @%[P]+,fr14\n\t"
            "fschg\n\t"
            "fmov    dr2,@-%[O]\n\t"
            "ftrv    xmtrx,fv8\n\t"
            "fldi1   fr15\n\t"
            "dt      %[left]\n\t"
            "add     #112,%[x]\n\t"     /* skin table entry k+2 */
            "fmov    dr0,@-%[O]\n\t"
            "pref    @%[x]\n\t"
            "add     #32,%[O]\n\t"
            "fmov    dr6,@-%[O]\n\t"
            "ftrv    xmtrx,fv12\n\t"
            "add     #32,%[x]\n\t"
            "fmov    dr4,@-%[O]\n\t"
            "add     #32,%[O]\n\t"
            "fmov    dr10,@-%[O]\n\t"
            "fmov    dr8,@-%[O]\n\t"
            "add     #32,%[O]\n\t"
            "pref    @%[x]\n\t"
            "fmov    dr14,@-%[O]\n\t"
            "fmov    dr12,@-%[O]\n\t"
            "fschg\n\t"
            "mov.b   %[one],@%[R]\n\t"
            "add     #32,%[O]\n\t"
            "bf/s    1b\n\t"
            "add     #1,%[R]\n"
            : [P] "+r"(P), [O] "+r"(O), [R] "+r"(R), [left] "+r"(left), [x] "=&r"(x)
            : [qb] "r"(qb), [one] "r"(one)
            : "fpul", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "fr8", "fr9", "fr10", "fr11", "fr12",
              "fr13", "fr14", "fr15", "t", "memory");
#if RE4DC_AVK == 2
        avk_check_build(f);
#endif
        return;
    }
#endif
    for (unsigned j = 0; j < entries; ++j)
        if (!f.skin_ready[j]) { skin_position_matrix(f, j, f.skin_positions + j * 16U); f.skin_ready[j] = 1; }
}
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// Skinned light directions used by records [i, n) and not built yet (skin_light_dirs).
void avk_build_dirs(Frame& f, const Lights& L, const Records& r, unsigned i, unsigned n) {
    alignas(8) float temp[12];
    int last = -1;
    for (; i < n; ++i) {
        const unsigned palette = f.normals[r.ni(i) * 4U + 3];
        if (int(palette) == last) continue;
        last = int(palette);
        if (!f.dirs_ready[palette < f.palette_entries ? palette : 0U]) skin_light_dirs(f, L, palette, temp);
    }
}
#endif
unsigned avk_positions(Part& e, const Records& r, unsigned n, const PosConst& k, bool s16_uv) {
    Frame& f = e.f;
    const bool skin = f.mode == kSkin;
#if RE4DC_ACTOR_SETUP_LEAN
    if (!n) return 0;
    auto& setup = e.position_setup;
    if (!setup.state) {
        setup.state = 1; setup.kernel = nullptr;
#endif
    // The kernels sign-extend the u16 record fields (mov.w), as ACTOR_POS_ASM does.
#if RE4DC_AVK_RIGID6
    // AVK_RIGID6 (game30.mk): rigid parts with stride 6 positions (kPos6) take the pipelined rigid6 kernels.
    const bool six = !skin && f.position_stride == 6;
    if (!n || (f.position_stride != 8 && !six) || f.position_count > 32768U || (skin && !f.skin_positions)) return 0;
#else
    if (!n || f.position_stride != 8 || f.position_count > 32768U || (skin && !f.skin_positions)) return 0;
#endif
#if RE4DC_ACTOR_SETUP_LEAN
    AvkPos& a = setup.args;
    a.pos = f.positions; a.uv = e.p.uv;
#else
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorSetupRepeat, 1)
#endif
    AvkPos a;
    a.pos = f.positions; a.uv = e.p.uv; a.rs = r.stride * 2U;
#endif
    a.matrix = skin ? f.skin_positions : f.screen; a.ready = f.skin_ready; a.entries = f.palette_entries;
    a.width = k.width; a.height = k.height; a.near_distance = k.near_distance; a.far_distance = k.far_distance;
    a.au = k.au; a.bu = k.bu; a.av = k.av; a.bv = k.bv;
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM
    // SKIN_SH4ZAM (game30.mk): the skinned pass through SH4ZAM's shz_xmtrx_project_skinned_* (platform/sh4zam_skin.c).
#define re4dc_avk_pos_skin_s16 re4dc_shz_pos_skin_s16
#define re4dc_avk_pos_skin_u16 re4dc_shz_pos_skin_u16
#endif
#if RE4DC_AVK_RIGID6
    unsigned (*const kernel)(const AvkPos*) = skin ? (s16_uv ? re4dc_avk_pos_skin_s16 : re4dc_avk_pos_skin_u16)
                                            : six  ? (s16_uv ? re4dc_avk_pos_rigid6_s16 : re4dc_avk_pos_rigid6_u16)
                                                   : (s16_uv ? re4dc_avk_pos_rigid_s16 : re4dc_avk_pos_rigid_u16);
#else
    unsigned (*const kernel)(const AvkPos*) = skin ? (s16_uv ? re4dc_avk_pos_skin_s16 : re4dc_avk_pos_skin_u16)
                                                   : (s16_uv ? re4dc_avk_pos_rigid_s16 : re4dc_avk_pos_rigid_u16);
#endif
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM
#undef re4dc_avk_pos_skin_s16
#undef re4dc_avk_pos_skin_u16
#endif
#if RE4DC_ACTOR_SETUP_LEAN
        setup.kernel = kernel;
    }
    if (!setup.kernel) return 0;
    AvkPos& a = setup.args;
    const auto kernel = setup.kernel;
    a.rs = r.stride * 2U;
#endif
    const u8* rec = reinterpret_cast<const u8*>(r.r);
    if (skin && !f.avk_all) avk_build_all(f);
    a.rec = rec; a.n = n; a.dst = e.cache.v; a.oc = e.cache.oc;
    // A stop is not reached (every entry is built); if one were, the C path would finish the rest.
    return n - kernel(&a);
}
// all / any of the outcode bytes [0, n) (the cache's, 32-byte aligned), a word at a time.
inline void avk_fold(const u8* oc, unsigned n, unsigned& all, unsigned& any) {
    typedef u32 __attribute__((may_alias)) word;
    const word* w = static_cast<const word*>(__builtin_assume_aligned(oc, 4));
    u32 a = ~0U, o = 0;
    unsigned j = 0;
    for (; j + 4 <= n; j += 4) { const u32 x = w[j / 4]; a &= x; o |= x; }
    a &= a >> 16; a &= a >> 8; o |= o >> 16; o |= o >> 8;
    for (; j < n; ++j) { a &= oc[j]; o |= oc[j]; }
    all &= a & 255U; any |= o & 255U;
}
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
#if RE4DC_ACTOR_LIGHT_N16
// ACTOR_LIGHT_N16: pass 2 for s16 normals (normal_shift 14: the owner path's parts, skinned stride 8, rigid
// stride 8 or 6) on the n16 kernels, with the s8 kernels' contract: the same fold (L.dir / skin_dirs, built by
// skin_light_dirs exactly as the portable loop uses them), colour matrix and alpha; returns the records lit from
// 0 (0: the portable loop lights the meshlet, as before). The skinned palette index is the normal's 4th word
// (u16, as the loop reads it); an index past the palette uses entry 0 in both. Per-vertex alpha
// (e.colors, alpha_state & 256), another stride, more than 32768 normals (the kernels' mov.w index sign-
// extends) or a skinned Frame without its direction table keep the loop.
enum N16Why : unsigned { kN16Kernel, kN16Colors, kN16Stride, kN16Count, kN16NoTable, kN16Ref, kN16Reasons };
#if RE4DC_ACTOR_LIGHT_N16 == 2
unsigned n16_meshlets[kN16Reasons], n16_vertices[kN16Reasons];
unsigned n16_kind_vertices[3];  // kernel vertices: skinned stride 8, rigid stride 8, rigid stride 6
bool n16_ref = false;  // compare build: inside the reference pass (the portable loop) the kernels are skipped
#endif
inline unsigned n16_palette(const Frame& f, unsigned ni) {
    return *reinterpret_cast<const u16*>(f.normals + ni * 8U + 6U);
}
// Skinned light directions used by records [i, n) and not built yet (avk_build_dirs, s16 normals).
void avk_build_dirs_n16(Frame& f, const Lights& L, const Records& r, unsigned i, unsigned n) {
    alignas(8) float temp[12];
    int last = -1;
    for (; i < n; ++i) {
        const unsigned palette = n16_palette(f, r.ni(i));
        if (int(palette) == last) continue;
        last = int(palette);
        if (!f.dirs_ready[palette < f.palette_entries ? palette : 0U]) skin_light_dirs(f, L, palette, temp);
    }
}
unsigned avk_lights_n16(Part& e, const Lights& L, const Records& r, unsigned n) {
    Frame& f = e.f;
    const bool skin = f.mode == kSkin;
    const unsigned ns = f.normal_stride;
#if RE4DC_ACTOR_SETUP_LEAN
    auto& setup = e.light_setup;
    if (!setup.state) {
        const unsigned why = e.colors ? unsigned(kN16Colors)
            : (skin ? ns != 8U : (ns != 8U && ns != 6U)) ? unsigned(kN16Stride)
            : f.normal_count > 32768U ? unsigned(kN16Count)
            : (skin && !f.skin_dirs) ? unsigned(kN16NoTable) : unsigned(kN16Kernel);
        setup.state = 1U + why; setup.kernel = nullptr;
        if (why == kN16Kernel) {
            AvkLight& a = setup.args;
            a.nrm = f.normals; a.color = L.color; a.alpha = e.alpha;
            a.dirs = skin ? f.skin_dirs : &L.dir[0][0]; a.ready = f.dirs_ready; a.entries = f.palette_entries;
            setup.kernel = skin ? re4dc_avk_light_skin_n16
                           : ns == 6U ? re4dc_avk_light_rigid_n16s6 : re4dc_avk_light_rigid_n16;
        }
    }
    const unsigned why =
#if RE4DC_ACTOR_LIGHT_N16 == 2
        n16_ref ? unsigned(kN16Ref) :
#endif
        setup.state - 1U;
#else
    const unsigned why =
#if RE4DC_ACTOR_LIGHT_N16 == 2
        n16_ref ? unsigned(kN16Ref) :
#endif
        e.colors ? unsigned(kN16Colors)
        : (skin ? ns != 8U : (ns != 8U && ns != 6U)) ? unsigned(kN16Stride)
        : f.normal_count > 32768U ? unsigned(kN16Count)
        : (skin && !f.skin_dirs) ? unsigned(kN16NoTable) : unsigned(kN16Kernel);
#endif
#if RE4DC_ACTOR_LIGHT_N16 == 2
    ++n16_meshlets[why]; n16_vertices[why] += n;
    if (why == kN16Kernel) n16_kind_vertices[skin ? 0 : ns == 6U ? 2 : 1] += n;
#endif
    if (why != kN16Kernel || !n) return 0;
#if RE4DC_ACTOR_SETUP_LEAN
    AvkLight& a = setup.args;
    const auto kernel = setup.kernel;
    a.rs = r.stride * 2U;
#else
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorSetupRepeat, 1)
#endif
    AvkLight a;
    a.nrm = f.normals; a.rs = r.stride * 2U; a.color = L.color; a.alpha = e.alpha;
    a.dirs = skin ? f.skin_dirs : &L.dir[0][0]; a.ready = f.dirs_ready; a.entries = f.palette_entries;
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin_n16
                                              : ns == 6U ? re4dc_avk_light_rigid_n16s6 : re4dc_avk_light_rigid_n16;
#endif
    const u8* rec = reinterpret_cast<const u8*>(r.r);
    if (skin) {
        const unsigned palette = n16_palette(f, r.ni(0));
        if (!f.dirs_ready[palette < f.palette_entries ? palette : 0U]) avk_build_dirs_n16(f, L, r, 0, n);
    }
    unsigned i = 0;
    for (unsigned pass = 0;; ++pass) {
        a.rec = rec + i * a.rs; a.n = n - i; a.argb = &e.cache.v[i].argb;
        const unsigned left = kernel(&a);
        i = n - left;
        if (!left || !skin || pass) return i;
        avk_build_dirs_n16(f, L, r, i, n);
    }
}
#if RE4DC_ACTOR_LIGHT_N16 == 2
// Compare build: after the kernel, the portable loop (the path without the knob) relights records [0, done)
// into n16_ref_v and every colour word is compared ("LN16" line every 256 checked meshlets, with the decline
// reasons of every s16-normal meshlet so far).
void pass_lights(Part& e, const Lights& L, const Records& r, unsigned n);
alignas(32) pvr_vertex_t n16_ref_v[kMaxVertices];
unsigned n16_checks, n16_lit, n16_words, n16_max, n16_off1, n16_off2;
void n16_check(Part& e, const Lights& L, const Records& r, unsigned done) {
    const Cache saved = e.cache;
    e.cache.v = n16_ref_v;
    n16_ref = true;
    pass_lights(e, L, r, done);
    n16_ref = false;
    e.cache = saved;
    for (unsigned j = 0; j < done; ++j) {
        const u32 a = e.cache.v[j].argb, b = n16_ref_v[j].argb;
        ++n16_lit;
        if (a == b) continue;
        ++n16_words;
        unsigned m = 0;
        for (unsigned s = 0; s < 32; s += 8) {
            const int d = int((a >> s) & 255U) - int((b >> s) & 255U);
            m = std::max(m, unsigned(d < 0 ? -d : d));
        }
        n16_max = std::max(n16_max, m);
        if (m == 1) ++n16_off1; else ++n16_off2;
    }
    if ((++n16_checks & 255U) == 0)
        re4dc_log("LN16 checks=%u lit=%u argb_mismatch=%u max_channel=%u off1=%u off2plus=%u | meshlets/verts "
                  "kernel=%u/%u colors=%u/%u stride=%u/%u count=%u/%u notable=%u/%u | kernel verts skin8=%u rigid8=%u "
                  "rigid6=%u\n",
                  n16_checks, n16_lit, n16_words, n16_max, n16_off1, n16_off2, n16_meshlets[kN16Kernel],
                  n16_vertices[kN16Kernel], n16_meshlets[kN16Colors], n16_vertices[kN16Colors],
                  n16_meshlets[kN16Stride], n16_vertices[kN16Stride], n16_meshlets[kN16Count], n16_vertices[kN16Count],
                  n16_meshlets[kN16NoTable], n16_vertices[kN16NoTable], n16_kind_vertices[0], n16_kind_vertices[1],
                  n16_kind_vertices[2]);
}
#endif
#endif
unsigned avk_lights(Part& e, const Lights& L, const Records& r, unsigned n) {
    Frame& f = e.f;
    const bool skin = f.mode == kSkin;
#if RE4DC_ACTOR_LIGHT_N16
    if (!f.small_normals) return avk_lights_n16(e, L, r, n);
#endif
#if RE4DC_ACTOR_SETUP_LEAN
    if (!n) return 0;
    auto& setup = e.light_setup;
    if (!setup.state) {
        setup.state = 1; setup.kernel = nullptr;
#endif
#if RE4DC_AVK_RIGID6
    const bool three = !skin && f.normal_stride == 3;  // AVK_RIGID6: rigid stride-3 normals (kNrm3)
    if (!n || !f.small_normals || e.colors || (f.normal_stride != 4 && !three) || f.normal_count > 32768U ||
        (skin && !f.skin_dirs))
        return 0;
#else
    if (!n || !f.small_normals || e.colors || f.normal_stride != 4 || f.normal_count > 32768U || (skin && !f.skin_dirs))
        return 0;
#endif
#if RE4DC_ACTOR_SETUP_LEAN
    AvkLight& a = setup.args;
    a.nrm = f.normals; a.color = L.color; a.alpha = e.alpha;
#else
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorSetupRepeat, 1)
#endif
    AvkLight a;
    a.nrm = f.normals; a.rs = r.stride * 2U; a.color = L.color; a.alpha = e.alpha;
#endif
    a.dirs = skin ? f.skin_dirs : &L.dir[0][0]; a.ready = f.dirs_ready; a.entries = f.palette_entries;
#if RE4DC_AVK_RIGID6
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin
                                              : three ? re4dc_avk_light_rigid3 : re4dc_avk_light_rigid;
#else
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin : re4dc_avk_light_rigid;
#endif
#if RE4DC_ACTOR_SETUP_LEAN
        setup.kernel = kernel;
    }
    if (!setup.kernel) return 0;
    AvkLight& a = setup.args;
    const auto kernel = setup.kernel;
    a.rs = r.stride * 2U;
#endif
    const u8* rec = reinterpret_cast<const u8*>(r.r);
    if (skin) {
        const unsigned palette = f.normals[r.ni(0) * 4U + 3];
        if (!f.dirs_ready[palette < f.palette_entries ? palette : 0U]) avk_build_dirs(f, L, r, 0, n);
    }
    unsigned i = 0;
    for (unsigned pass = 0;; ++pass) {
        a.rec = rec + i * a.rs; a.n = n - i; a.argb = &e.cache.v[i].argb;
        const unsigned left = kernel(&a);
        i = n - left;
        if (!left || !skin || pass) return i;
        avk_build_dirs(f, L, r, i, n);
    }
}
#endif
#if RE4DC_AVK == 2
// Check build: the kernels run first, then the previous path (positions_asm / positions_c,
// lights_asm) recomputes the same records into the arrays below and every word is compared before
// any filtering. "VTXK" line every 4096 position meshlets.
struct AvkCheck {
    unsigned meshlets, pos_kernel, pos_other, pos_partial, verts, x, y, invw, u, v, oc, oc_near, oc_screen, oc_far,
        allany, nonfinite, near_verts, px_q, px_1;
    unsigned light_kernel, light_other, light_partial, lit, argb, argb_max, gate, gate_mismatch, emits, emit_verts,
        emit_mismatch, builds, build_mismatch;
    float px_front, px_screen, rel_invw, uv;
};
AvkCheck avk_chk;
bool avk_ref = false;  // inside the reference pass: the kernels are skipped
alignas(32) pvr_vertex_t avk_ref_v[kMaxVertices];
alignas(32) u8 avk_ref_oc[kMaxVertices];
inline u32 avk_bits(float x) { u32 b; std::memcpy(&b, &x, 4); return b; }
inline bool avk_finite(float x) { return ((avk_bits(x) >> 23) & 255U) != 255U; }
// The fog gate's hoisted square root (re4dc_actor_submit) against the per-entry loop, bit for bit.
void avk_gate_check(float T, float G, float T2, float G2) {
    ++avk_chk.gate;
    if (avk_bits(T) != avk_bits(T2) || avk_bits(G) != avk_bits(G2)) ++avk_chk.gate_mismatch;
}
// Every entry after avk_build_all against skin_position_matrix: ready byte set, all 16 words equal.
void avk_check_build(const Frame& f) {
    alignas(8) float ref[16];
    for (unsigned j = 0; j < f.palette_entries; ++j) {
        skin_position_matrix(f, j, ref);
        ++avk_chk.builds;
        if (!f.skin_ready[j] || std::memcmp(ref, f.skin_positions + j * 16U, sizeof(ref))) ++avk_chk.build_mismatch;
    }
}
// A store-queue meshlet copied by the pipelined loop and by the previous one into RAM, 64 corners at
// a time, every byte and the returned end compared.
alignas(32) pvr_vertex_t avk_emit_a[64], avk_emit_b[64];
void avk_check_emit(const pvr_vertex_t* cache, const u8* index, unsigned n) {
    for (unsigned at = 0; at < n; at += 64) {
        const unsigned m = n - at < 64U ? n - at : 64U;
        void* ea = emit_meshlet<false>(avk_emit_a, cache, index + at, m);
        avk_emit_ref = true;
        void* eb = emit_meshlet<false>(avk_emit_b, cache, index + at, m);
        avk_emit_ref = false;
        ++avk_chk.emits; avk_chk.emit_verts += m;
        if (ea != static_cast<void*>(avk_emit_a + m) || eb != static_cast<void*>(avk_emit_b + m) ||
            std::memcmp(avk_emit_a, avk_emit_b, m * sizeof(pvr_vertex_t)))
            ++avk_chk.emit_mismatch;
    }
}
void pass_positions(Part& e, const Records& r, unsigned n, const PosConst& k, bool s16_uv, unsigned& all,
                    unsigned& any);
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
void pass_lights(Part& e, const Lights& L, const Records& r, unsigned n);
#endif
void avk_check_positions(Part& e, const Records& r, unsigned n, unsigned done, const PosConst& k, bool s16_uv,
                         unsigned all, unsigned any) {
    AvkCheck& c = avk_chk;
    ++c.meshlets;
    if (!done) ++c.pos_other;
    else {
        ++c.pos_kernel;
        if (done < n) ++c.pos_partial;
        const Cache saved = e.cache;
        e.cache.v = avk_ref_v; e.cache.oc = avk_ref_oc;
        unsigned ra, ro;
        avk_ref = true;
        pass_positions(e, r, done, k, s16_uv, ra, ro);
        avk_ref = false;
        e.cache = saved;
        stats.position_transforms -= done;
        if (((all ^ ra) | (any ^ ro)) & 63U) ++c.allany;
        for (unsigned j = 0; j < done; ++j) {
            const pvr_vertex_t& a = e.cache.v[j];
            const pvr_vertex_t& b = avk_ref_v[j];
            const unsigned oa = e.cache.oc[j] & 63U, ob = avk_ref_oc[j] & 63U;
            ++c.verts;
            c.x += avk_bits(a.x) != avk_bits(b.x); c.y += avk_bits(a.y) != avk_bits(b.y);
            c.invw += avk_bits(a.z) != avk_bits(b.z);
            c.u += avk_bits(a.u) != avk_bits(b.u); c.v += avk_bits(a.v) != avk_bits(b.v);
            if (avk_finite(a.x) != avk_finite(b.x) || avk_finite(a.y) != avk_finite(b.y) ||
                avk_finite(a.z) != avk_finite(b.z))
                ++c.nonfinite;
            if (oa != ob) {
                ++c.oc;
                if ((oa ^ ob) & kOcNear) ++c.oc_near;
                if ((oa ^ ob) & kOcScreen) ++c.oc_screen;
                if ((oa ^ ob) & kOcFar) ++c.oc_far;
            }
            const float du = __builtin_fabsf(a.u - b.u), dv = __builtin_fabsf(a.v - b.v);
            if (du > c.uv) c.uv = du;
            if (dv > c.uv) c.uv = dv;
            // Near-plane corners are clipped from world_of + project: their x / y / 1/w are unused.
            if ((oa | ob) & kOcNear) { ++c.near_verts; continue; }
            float d = __builtin_fabsf(a.x - b.x);
            const float dy = __builtin_fabsf(a.y - b.y);
            if (dy > d) d = dy;
            if (d > c.px_front) c.px_front = d;
            if (!((oa | ob) & kOcCull)) {
                if (d > c.px_screen) c.px_screen = d;
                if (d > 0.25f) ++c.px_q;
                if (d > 1.0f) ++c.px_1;
            }
            const float rel = __builtin_fabsf(a.z - b.z) / b.z;
            if (rel > c.rel_invw) c.rel_invw = rel;
        }
    }
    if ((c.meshlets & 4095U) == 0) {  // three short lines (the log ring cuts long ones)
        re4dc_log("VTXK pos meshlets=%u kernel=%u other=%u partial=%u verts=%u bits x=%u y=%u invw=%u u=%u v=%u\n",
                  c.meshlets, c.pos_kernel, c.pos_other, c.pos_partial, c.verts, c.x, c.y, c.invw, c.u, c.v);
        re4dc_log("VTXK oc mismatch=%u near=%u screen=%u far=%u allany=%u nonfinite=%u near_verts=%u px_front=%.6f "
                  "px_screen=%.6f over_0.25px=%u over_1px=%u rel_invw=%.3g uv=%.3g\n",
                  c.oc, c.oc_near, c.oc_screen, c.oc_far, c.allany, c.nonfinite, c.near_verts, double(c.px_front),
                  double(c.px_screen), c.px_q, c.px_1, double(c.rel_invw), double(c.uv));
        re4dc_log("VTXK light kernel=%u other=%u partial=%u lit=%u argb_mismatch=%u max_channel=%u\n",
                  c.light_kernel, c.light_other, c.light_partial, c.lit, c.argb, c.argb_max);
        re4dc_log("VTXK gate=%u gate_mismatch=%u emit=%u emit_verts=%u emit_mismatch=%u builds=%u build_mismatch=%u "
                  "movca_frames=%u\n",
                  c.gate, c.gate_mismatch, c.emits, c.emit_verts, c.emit_mismatch, c.builds, c.build_mismatch,
                  avk_build_mc);
    }
}
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
void avk_check_lights(Part& e, const Lights& L, const Records& r, unsigned n, unsigned done) {
    AvkCheck& c = avk_chk;
    if (!done) { ++c.light_other; return; }
    ++c.light_kernel;
    if (done < n) ++c.light_partial;
    const Cache saved = e.cache;
    e.cache.v = avk_ref_v;
    avk_ref = true;
    pass_lights(e, L, r, done);
    avk_ref = false;
    e.cache = saved;
    for (unsigned j = 0; j < done; ++j) {
        const u32 a = e.cache.v[j].argb, b = avk_ref_v[j].argb;
        ++c.lit;
        if (a == b) continue;
        ++c.argb;
        for (unsigned s = 0; s < 32; s += 8) {
            const int d = int((a >> s) & 255U) - int((b >> s) & 255U);
            const unsigned m = unsigned(d < 0 ? -d : d);
            if (m > c.argb_max) c.argb_max = m;
        }
    }
}
#endif
#endif
#endif

// Pass 1 over a meshlet: every record's position/uv/outcode into the cache.
void pass_positions(Part& e, const Records& r, unsigned n, const PosConst& k, bool s16_uv, unsigned& all,
                    unsigned& any) {
    Frame& f = e.f;
    const u8* rec = reinterpret_cast<const u8*>(r.r);
    const unsigned rs = r.stride * 2U;
    all = ~0U; any = 0;
    alignas(8) float temp[16];
    unsigned i = 0;
#if RE4DC_AVK
#if RE4DC_AVK == 2
    if (!avk_ref) {
#endif
        i = avk_positions(e, r, n, k, s16_uv);
        if (i) avk_fold(e.cache.oc, i, all, any);
#if RE4DC_AVK == 2
        avk_check_positions(e, r, n, i, k, s16_uv, all, any);
    }
#endif
    if (i == n) { stats.position_transforms += n; return; }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorPositionFallback, n - i)
#endif
    if (f.mode != kSkin) load_xmtrx(f.screen);
    while (i < n) {
        int palette = 0;
        if (f.mode == kSkin) {
            palette = reinterpret_cast<const short*>(f.positions + r.vi(i) * 8U)[3];
            load_xmtrx(position_matrix(f, unsigned(palette) < f.palette_entries ? unsigned(palette) : 0U, temp));
        }
        const u8* at = rec + i * rs;
        unsigned done;
#if defined(__sh__) && RE4DC_ACTOR_ASM
        if (s16_uv && f.position_stride == 8)
            done = f.mode == kSkin
                ? positions_asm<kPos8Check>(at, rs, n - i, f.positions, palette, e.p.uv, e.cache.v + i, e.cache.oc + i, k, all, any)
                : positions_asm<kPos8>(at, rs, n - i, f.positions, 0, e.p.uv, e.cache.v + i, e.cache.oc + i, k, all, any);
        else if (s16_uv && f.position_stride == 6)
            done = positions_asm<kPos6>(at, rs, n - i, f.positions, 0, e.p.uv, e.cache.v + i, e.cache.oc + i, k, all, any);
        else
#endif
            done = positions_c(at, rs, n - i, f.positions, f.position_stride, f.mode == kSkin, palette, e.p.uv, s16_uv,
                               e.cache.v + i, e.cache.oc + i, k, all, any);
#if RE4DC_ACTOR_SKIN_FTRV == 2 && defined(__sh__) && !defined(ACTOR_TEST_XMTRX)
        if (f.mode == kSkin)
            skin_check_vertices(e, at, rs, n - i, palette, e.cache.v + i, e.cache.oc + i, done, k, s16_uv);
#endif
        i += done;
    }
    stats.position_transforms += n;
}

#if RE4DC_ACTOR_LIGHT_FAST_ONLY
// Each part's RGB was computed once. This loop never reads normal/light/palette
// data. The invariant guard is live, and catches any future nonconstant dispatch.
void pass_fast_only(Part& e, const Lights& L, const Records& r, unsigned n) {
    if (!L.constant || !L.fast) light25_add(light25_stats.fallback_parts);
    const bool multiply = e.p.colors && (L.source->ambient_vertex || L.source->material_vertex);
    light25_add(multiply ? light25_stats.multiply_vertices : light25_stats.flat_vertices, n);
    const u32 rgb = L.constant_rgb;
    if (!multiply && !e.colors) {
        const u32 argb = e.alpha | rgb;
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
        e.flat_colors(n, argb);
#else
        for (unsigned i = 0; i < n; ++i) e.cache.v[i].argb = argb;
#endif
        return;
    }
    for (unsigned i = 0; i < n; ++i) {
        const unsigned ci = r.ci(i);
        const u32 alpha = e.colors ? u32(e.colors[ci * 4U + 3U]) << 24 : e.alpha;
        e.cache.v[i].argb = alpha | (multiply ? re4dc_actor_light25_multiply(L.colour25, e.p.colors + ci * 4U) : rgb);
    }
}
#endif

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// Pass 2 (fast directional fold) over a meshlet.
void pass_lights(Part& e, const Lights& L, const Records& r, unsigned n) {
    Frame& f = e.f;
    const u8* rec = reinterpret_cast<const u8*>(r.r);
    const unsigned rs = r.stride * 2U;
    unsigned done = 0;  // records lit by ACTOR_VTX_KERNEL
#if RE4DC_AVK
#if RE4DC_AVK == 2
    if (!avk_ref) {
#endif
        done = avk_lights(e, L, r, n);
#if RE4DC_AVK == 2
        avk_check_lights(e, L, r, n, done);
    }
#endif
#if RE4DC_ACTOR_LIGHT_N16 == 2
    if (!f.small_normals && done) n16_check(e, L, r, done);
#endif
    if (done == n) return;
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorLightFallback, n - done)
#endif
    LightConst k{};
    k.cap = 255.0f;
    load_xmtrx(L.color);
    const bool small = f.small_normals;
    const unsigned ns = f.normal_stride;
    if (!small || e.colors) {  // s16 normals / per-vertex alpha: portable loop
#if RE4DC_ACTOR_LIGHT_N16
        for (unsigned i = small ? 0U : done; i < n; ++i) {  // after the n16 kernel's records (0 when it declined)
#else
        for (unsigned i = 0; i < n; ++i) {
#endif
            float nx, ny, nz;
            int pi;
            if (small) {
                const signed char* s = reinterpret_cast<const signed char*>(f.normals + r.ni(i) * ns);
                nx = s[0]; ny = s[1]; nz = s[2]; pi = f.mode == kSkin ? int(u8(s[3])) : 0;
            } else {
                const short* s = reinterpret_cast<const short*>(f.normals + r.ni(i) * ns);
                nx = s[0]; ny = s[1]; nz = s[2]; pi = f.mode == kSkin ? int(u16(s[3])) : 0;
            }
            alignas(8) float temp[12];
            const float* dirs = f.mode == kSkin ? skin_light_dirs(f, L, unsigned(pi), temp) : &L.dir[0][0];
            const float d0 = ACTOR_DOT3(dirs, nx, ny, nz), d1 = ACTOR_DOT3(dirs + 4, nx, ny, nz),
                        d2 = ACTOR_DOT3(dirs + 8, nx, ny, nz);
            float m0 = std::fabs(d0) + d0, m1 = std::fabs(d1) + d1, m2 = std::fabs(d2) + d2, one = 1.0f;
            ACTOR_FTRV(m0, m1, m2, one);
            const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
            e.cache.v[i].argb = a | (channel(m0) << 16) | (channel(m1) << 8) | channel(m2);
        }
        return;
    }
    unsigned i = done;
    while (i < n) {
        unsigned palette = 0;
        alignas(8) float temp[12];
        const float* dirs = &L.dir[0][0];
        if (f.mode == kSkin) {
            palette = f.normals[r.ni(i) * ns + 3];
            dirs = skin_light_dirs(f, L, palette, temp);
        }
        std::memcpy(k.l0, dirs, 12 * sizeof(float));
        const u8* at = rec + i * rs;
        unsigned done;
#if defined(__sh__) && RE4DC_ACTOR_ASM
        if (ns == 4)
            done = f.mode == kSkin ? lights_asm<kNrm4Check>(at, rs, n - i, f.normals, palette, e.cache.v + i, k, e.alpha)
                                   : lights_asm<kNrm4>(at, rs, n - i, f.normals, 0, e.cache.v + i, k, e.alpha);
        else if (ns == 3 && f.mode != kSkin)
            done = lights_asm<kNrm3>(at, rs, n - i, f.normals, 0, e.cache.v + i, k, e.alpha);
        else
#endif
            done = lights_c(at, rs, n - i, f.normals, ns, f.mode == kSkin, palette, e.cache.v + i, k, e.alpha);
        i += done;
    }
}

#ifndef RE4DC_ACTOR_EXACT_FAST
#define RE4DC_ACTOR_EXACT_FAST 0
#endif
// Pass 2 (exact, slow): the generic path's per-vertex evaluator.
void pass_lights_exact(Part& e, const Lights& L, const Records& r, unsigned n) {
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    fa29_actor_exact_vertices(e.p,n);
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorLightExact, n)
#endif
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
    b28::verts(n);
#endif
    static const u8 white[4] = {255, 255, 255, 255};
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
    float Np[12];
    const float* part_normal = nullptr;
    if (L.source->normal_matrix[3] == 1.0e30f) {
        if (!leon_part_normal(e.p.modelview, Np)) {
            // No invertible normal basis: keep native ownership and the prototype's constant-colour fallback.
            // Do not use the previous role's GX normal matrix or send NaNs to the TA.
            const SourceLighting& S = *L.source;
#if RE4DC_LEON_LIGHT_HEADROOM
            const float ts = S.tev_scale * leon_gain(S);
            const u32 rgb = channel(S.material[0] * ts) << 16 | channel(S.material[1] * ts) << 8 | channel(S.material[2] * ts);
#else
            const u32 rgb = channel(S.material[0] * S.tev_scale) << 16 |
                            channel(S.material[1] * S.tev_scale) << 8 | channel(S.material[2] * S.tev_scale);
#endif
            for (unsigned i = 0; i < n; ++i) {
                const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
                e.cache.v[i].argb = a | rgb;
            }
            stats.slow_light_vertices += n;
            return;
        }
        part_normal = Np;
    }
#endif
#if RE4DC_ACTOR_EXACT_FAST
    // ACTOR_EXACT_FAST=1 (render only): evaluate_prepared_source_lighting's arithmetic (source_lighting.cpp) per
    // vertex, with the per-light constants (colour / 255, a, k, position, direction) taken out of the vertex loop,
    // one fsrra for the light distance instead of a square root and three divisions, and one division for the
    // attenuation. Same light order, ambient start, clamp, material and TEV scale; results differ from the reference
    // evaluator only in float rounding (the 8-bit colour, rarely by one step).
    const SourceLighting& S = *L.source;
    const re4dc::render::PreparedSourceLights& P = RE4DC_PREPARED(L);
    const bool vertex_colour = (S.ambient_vertex || S.material_vertex) && e.p.colors;
    struct FastLight { float x, y, z, dx, dy, dz, a0, a1, a2, k0, k1, k2, r, g, b; };
    FastLight fl[8];
    const unsigned count = P.count < 8U ? P.count : 8U;
    for (unsigned j = 0; j < count; ++j) {
        const SourceLight& s = P.lights[j];
        fl[j] = {s.position[0], s.position[1], s.position[2], s.direction[0], s.direction[1], s.direction[2],
                 s.a[0], s.a[1], s.a[2], s.k[0], s.k[1], s.k[2],
                 s.color[0] / 255.f, s.color[1] / 255.f, s.color[2] / 255.f};
    }
    const bool attenuate = S.attenuation == 1;
    const unsigned diffuse_mode = S.diffuse;
    for (unsigned i = 0; i < n; ++i) {
        float w[3], nn[3];
        world_of(e.f, e.p, r, i, w, nn
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
                 , part_normal
#endif
                 );
        const u8* color = vertex_colour ? e.p.colors + r.ci(i) * 4 : white;
        const u8* ambient = S.ambient_vertex ? color : S.ambient;
        const u8* material = S.material_vertex ? color : S.material;
        float out0 = S.enable ? ambient[0] / 255.f : 1.f, out1 = S.enable ? ambient[1] / 255.f : 1.f,
              out2 = S.enable ? ambient[2] / 255.f : 1.f;
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
        out0 += L.extra[0]; out1 += L.extra[1]; out2 += L.extra[2];
#endif
        for (unsigned j = 0; j < count; ++j) {
            const FastLight& l = fl[j];
            float lx = l.x - w[0], ly = l.y - w[1], lz = l.z - w[2];
            const float d2 = lx * lx + ly * ly + lz * lz;
            float distance = 0.0f;
            if (d2 > 0.0f) {
                const float rs = inverse_sqrt(d2);
                distance = d2 * rs;
                lx *= rs; ly *= rs; lz *= rs;
            } else { lx = nn[0]; ly = nn[1]; lz = nn[2]; }
            float attenuation = 1.0f;
            if (attenuate) {
                const float cosine = std::max(0.f, lx * l.dx + ly * l.dy + lz * l.dz);
                const float angular = std::max(0.f, l.a0 + l.a1 * cosine + l.a2 * cosine * cosine);
                const float denominator = l.k0 + l.k1 * distance + l.k2 * d2;
                attenuation = denominator > 0 ? angular / denominator : 0;
            }
            float diffuse = diffuse_mode ? nn[0] * lx + nn[1] * ly + nn[2] * lz : 1.f;
            if (diffuse_mode == 2) diffuse = std::max(0.f, diffuse);
            const float f = attenuation * diffuse;
            out0 += l.r * f; out1 += l.g * f; out2 += l.b * f;
        }
#if RE4DC_LEON_LIGHT_HEADROOM
        const float ts = S.tev_scale * leon_gain(S);
        const float rgb0 = material[0] / 255.f * std::min(std::max(out0, 0.f), 1.f) * ts;
        const float rgb1 = material[1] / 255.f * std::min(std::max(out1, 0.f), 1.f) * ts;
        const float rgb2 = material[2] / 255.f * std::min(std::max(out2, 0.f), 1.f) * ts;
#else
        const float rgb0 = material[0] / 255.f * std::min(std::max(out0, 0.f), 1.f) * S.tev_scale;
        const float rgb1 = material[1] / 255.f * std::min(std::max(out1, 0.f), 1.f) * S.tev_scale;
        const float rgb2 = material[2] / 255.f * std::min(std::max(out2, 0.f), 1.f) * S.tev_scale;
#endif
        const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
        e.cache.v[i].argb = a | (channel(rgb0 * 255.0f) << 16) | (channel(rgb1 * 255.0f) << 8) | channel(rgb2 * 255.0f);
    }
    stats.slow_light_vertices += n;
    return;
#endif
    for (unsigned i = 0; i < n; ++i) {
        float w[3], nn[3], rgb[3];
        world_of(e.f, e.p, r, i, w, nn
#if defined(RE4DC_LEON_SOURCE_LIGHT) && RE4DC_LEON_SOURCE_LIGHT
                 , part_normal
#endif
                 );
        const u8* color = (L.source->ambient_vertex || L.source->material_vertex) && e.p.colors ? e.p.colors + r.ci(i) * 4 : white;
        re4dc::render::evaluate_prepared_source_lighting(w[0], w[1], w[2], nn[0], nn[1], nn[2], *L.source, RE4DC_PREPARED(L), color, rgb);
        const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
        e.cache.v[i].argb = a | (channel(rgb[0] * 255.0f) << 16) | (channel(rgb[1] * 255.0f) << 8) | channel(rgb[2] * 255.0f);
    }
    stats.slow_light_vertices += n;
}

#endif
// ------------------------------------------------------------- prelit --
// Records of a kHasBake part carry an RGB565 colour lit with BakeBlock's
// fold. A draw whose fold matches (within kBakeTolerance of each light's
// magnitude) copies it (~6 cycles/record instead of ~47 for pass_lights); one
// whose directions match but whose colours changed by a per-channel factor
// (a light dimming or flickering as a whole) scales it; anything else
// relights every level-0 record once into the colour field (rebake).
#ifndef RE4DC_ACTOR_BAKE_TOLERANCE
#define RE4DC_ACTOR_BAKE_TOLERANCE (1.0f / 32.0f)
#endif
constexpr float kBakeTolerance = RE4DC_ACTOR_BAKE_TOLERANCE;
#ifndef RE4DC_ACTOR_DIR_TOLERANCE
#define RE4DC_ACTOR_DIR_TOLERANCE (1.0f / 128.0f)
#endif
constexpr float kDirTolerance = RE4DC_ACTOR_DIR_TOLERANCE;
#ifndef RE4DC_ACTOR_PRELIT
#define RE4DC_ACTOR_PRELIT 1
#endif
constexpr bool kPrelit = RE4DC_ACTOR_PRELIT != 0;
enum BakeUse { kBakeNone, kBakeCopy, kBakeScaled };

inline u16 pack565(u32 argb) {
    return u16(((argb >> 8) & 0xF800U) | ((argb >> 5) & 0x07E0U) | ((argb >> 3) & 0x001FU));
}
u32 palette_hash(const Frame& f) {
    if (f.mode != kSkin || !f.palette) return 1U;
    u32 h = 2166136261U;
    const u32* w = reinterpret_cast<const u32*>(f.palette);
    for (unsigned i = 0; i < f.palette_entries * 12U; ++i) h = (h ^ w[i]) * 16777619U;
    return h | 1U;
}
bool near_vec(const float* a, const float* b, unsigned n, float scale) {
    for (unsigned i = 0; i < n; ++i) if (std::fabs(a[i] - b[i]) > scale) return false;
    return true;
}

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
// Returns the use for this draw; scale[c] = 8.8 fixed per channel (kBakeScaled).
BakeUse bake_prepare(Part& e, const Lights& L, const BlobHeader& b, unsigned rs, unsigned scale[3]) {
    u8* base = reinterpret_cast<u8*>(const_cast<BlobHeader*>(&b));
    BakeBlock& k = *reinterpret_cast<BakeBlock*>(base + b.bake4 * 4U);
    const u32 state = palette_hash(e.f);
    if (k.state == state) {
        float dmax = 0.0f;
        for (unsigned i = 0; i < 12; ++i) dmax = std::max(dmax, std::fabs(L.dir[i / 4][i % 4]));
        if (near_vec(&L.dir[0][0], k.dir, 12, dmax * kBakeTolerance)) {
            // per channel c: entries c, 4+c, 8+c, 12+c (lights 0..2, ambient)
            bool same = true, prop = true;
            for (unsigned c = 0; c < 3; ++c) {
                float now = 0.0f, then = 0.0f;
                for (unsigned j = 0; j < 4; ++j) { now += L.color[j * 4 + c]; then += k.color[j * 4 + c]; }
                const float tol = std::max(now, then) * kBakeTolerance;
                const float s = then > 0.0f ? now / then : (now > 0.0f ? -1.0f : 1.0f);
                for (unsigned j = 0; j < 4; ++j) {
                    same &= std::fabs(L.color[j * 4 + c] - k.color[j * 4 + c]) <= tol;
                    prop &= s >= 0.0f && std::fabs(L.color[j * 4 + c] - s * k.color[j * 4 + c]) <= tol;
                }
                prop &= s >= 0.0f && s <= 2.0f && (s >= 1.0f || !k.clamped);  // error grows with s
                scale[c] = prop ? unsigned(s * 256.0f + 0.5f) : 0U;
            }
            if (same) { ++stats.bake_hits; return kBakeCopy; }
            if (prop) { ++stats.bake_scaled; return kBakeScaled; }
        }
    }
    Re4dcActorStreamMutation mutation(&b,e.p.stream_bytes);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    re4dc_gcasset::HandDerivationScope gcasset_mutation(&b,e.p.stream_bytes);
#endif
    // Rebake: light every level-0 record into its colour field.
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    re4dc::dfa26::hit(re4dc::dfa26::ActorBakeRelight);
#endif
    const auto* table = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
    u16* records = reinterpret_cast<u16*>(base + b.rec4 * 4U);
    u32 clamped = 0;
    for (unsigned mi = 0; mi < b.meshlets; ++mi) {
        const unsigned nv = table[mi].n.vertices();
        u16* rec = records + table[mi].first * rs;
        const Records r{rec, rs, b.color_index, (b.flags & kHasCi) != 0};
        pass_lights(e, L, r, nv);
        for (unsigned i = 0; i < nv; ++i) {
            const u32 c = e.cache.v[i].argb;
            clamped |= ((c & 0xFF0000U) == 0xFF0000U) | ((c & 0xFF00U) == 0xFF00U) | ((c & 0xFFU) == 0xFFU);
            rec[i * rs + rs - 1] = pack565(c);
        }
    }
    k.state = state; k.clamped = clamped;
    std::memcpy(k.dir, &L.dir[0][0], sizeof(k.dir));
    std::memcpy(k.color, L.color, sizeof(k.color));
    ++stats.bake_builds;
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    gcasset_mutation.complete();
#endif
    return kBakeCopy;
}

// Pass 2 (prelit): the baked colours, optionally scaled per channel.
void pass_baked(Part& e, const Records& r, unsigned n, const unsigned* scale) {
    const u16* rec = r.r + (r.stride - 1);
    const unsigned rs = r.stride;
    pvr_vertex_t* v = e.cache.v;
    const u32 a = e.alpha;
    if (!scale) {
        for (unsigned i = 0; i < n; ++i) {
            const u32 c = rec[i * rs];
            const u32 R = (c >> 11) & 31U, G = (c >> 5) & 63U, B = c & 31U;
            v[i].argb = a | (((R << 3) | (R >> 2)) << 16) | (((G << 2) | (G >> 4)) << 8) | ((B << 3) | (B >> 2));
        }
        return;
    }
    for (unsigned i = 0; i < n; ++i) {
        const u32 c = rec[i * rs];
        const u32 R = (c >> 11) & 31U, G = (c >> 5) & 63U, B = c & 31U;
        const u32 r8 = std::min<u32>(255U, (((R << 3) | (R >> 2)) * scale[0] + 128U) >> 8);
        const u32 g8 = std::min<u32>(255U, (((G << 2) | (G >> 4)) * scale[1] + 128U) >> 8);
        const u32 b8 = std::min<u32>(255U, (((B << 3) | (B >> 2)) * scale[2] + 128U) >> 8);
        v[i].argb = a | (r8 << 16) | (g8 << 8) | b8;
    }
}

#endif
#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29 && !RE4DC_ACTOR_LIGHT_FAST_ONLY
#include "include/fallback_scan29_bake.inc"
#endif
// LOD: the coarsest level whose error, projected at the bind-pose bounding
// sphere's nearest depth, is at most lod_tau pixels (0: always level 0).
#ifndef RE4DC_ACTOR_LOD_PX
#define RE4DC_ACTOR_LOD_PX 2.0f
#endif
float lod_tau = RE4DC_ACTOR_LOD_PX;
// Late-activation arms (warp_late.h bit 2, DBG_WARP builds): 8 px from the activation tick on.
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
#define RE4DC_NEAR_LOD_TAU (RE4DC_WARP_LATE(RE4DC_LATE_ACTOR_LOD8) ? 8.0f : lod_tau)
#else
#define RE4DC_NEAR_LOD_TAU lod_tau
#endif
// LOD building is deferred and budgeted: a conversion only marks an opaque
// part kLodPending (it draws level 0, full detail); on a later frame whose
// workspace has at least kLodMinWorkspace (more parts fit their simplifier
// in kLodWorkspaceBytes, which is asked for), relod() rebuilds it, at most
// ~lod_budget_frame triangles per frame (one part of any size when the frame
// has not built any yet). A frame that saw a pending part asks model_bridge
// for the larger workspace next frame (re4dc_actor_workspace_want).
#ifndef RE4DC_ACTOR_LOD_WORKSPACE
#define RE4DC_ACTOR_LOD_WORKSPACE (160U * 1024U)
#endif
#ifndef RE4DC_ACTOR_LOD_MIN_WORKSPACE
#define RE4DC_ACTOR_LOD_MIN_WORKSPACE (96U * 1024U)
#endif
unsigned lod_budget_frame = RE4DC_ACTOR_LOD_BUDGET, lod_budget = RE4DC_ACTOR_LOD_BUDGET;
constexpr unsigned kLodWorkspaceBytes = RE4DC_ACTOR_LOD_WORKSPACE;   // asked for while a build waits
constexpr unsigned kLodMinWorkspace = RE4DC_ACTOR_LOD_MIN_WORKSPACE;  // the least a build is tried with
bool lod_wanted = false, lod_wanted_last = false;  // a pending part seen this / the previous frame
bool lod_take(unsigned triangles) {
    if (!lod_budget_frame || !lod_budget || (triangles > lod_budget && lod_budget != lod_budget_frame)) return false;
    lod_budget = triangles >= lod_budget ? 0U : lod_budget - triangles;
    return true;
}
unsigned select_level(const Re4dcModelPart& p, const BlobHeader& b, float near_distance, float tau) {
    if (!b.levels || !(tau > 0.0f)) return 0;
    const float* m = p.modelview; const float* c = b.center;
    const float depth = -(m[8] * c[0] + m[9] * c[1] + m[10] * c[2] + m[11]) - b.radius;
    if (!(depth > near_distance)) return 0;
    const float scale = std::sqrt(m[0] * m[0] + m[4] * m[4] + m[8] * m[8]);
    const float pixels_per_unit = 0.5f * p.viewport[2] * std::fabs(p.projection[1]) * scale / depth;
    const auto* dir = reinterpret_cast<const LevelInfo*>(reinterpret_cast<const u8*>(&b) + b.lod4 * 4U);
    for (unsigned k = b.levels; k > 0; --k)
        if (dir[k - 1].error * pixels_per_unit <= tau) return k;
    return 0;
}

// ---------------------------------------------------------------- crowd --
// NATIVE_ACTOR_CROWD: every Ganado-family model (re4dc_actor_model_class 1/2)
// gets a render tier from the camera distances of the previous frame: the
// crowd_near_count nearest, and any within crowd_near, draw like Leon (LOD at
// lod_tau, per-vertex lighting); up to crowd_mid the mid tier (LOD at
// crowd_mid_tau, one light colour per part); beyond, the far tier (coarsest
// level, one colour per part). Head infos (class 2) stay one tier finer. A
// model new this frame starts near. Tiers only change how a part is drawn:
// nothing is culled or hidden, and no source state is read back.
#ifndef RE4DC_NATIVE_ACTOR_SKIN_LAZY
#define RE4DC_NATIVE_ACTOR_SKIN_LAZY 0
#endif
#ifndef RE4DC_ACTOR_CROWD
#define RE4DC_ACTOR_CROWD 0
#endif
#ifndef RE4DC_ACTOR_CROWD_NEAR
#define RE4DC_ACTOR_CROWD_NEAR 3U
#endif
#ifndef RE4DC_ACTOR_CROWD_NEAR_M
#define RE4DC_ACTOR_CROWD_NEAR_M 7.0f
#endif
#ifndef RE4DC_ACTOR_CROWD_MID_M
#define RE4DC_ACTOR_CROWD_MID_M 17.0f
#endif
#ifndef RE4DC_ACTOR_CROWD_MID_PX
#define RE4DC_ACTOR_CROWD_MID_PX 8.0f
#endif
#ifndef RE4DC_ACTOR_CROWD_FLAT
#define RE4DC_ACTOR_CROWD_FLAT 0
#endif
constexpr bool kCrowd = RE4DC_ACTOR_CROWD != 0;
// CROWD_FLAT: the near tier also draws with one light colour per part.
constexpr bool kCrowdFlat = RE4DC_ACTOR_CROWD_FLAT != 0;
enum Tier : unsigned { kTierFull = 0, kTierNear = 1, kTierMid = 2, kTierFar = 3 };
constexpr float kSourceUnitsPerMetre = 1000.0f;
unsigned crowd_near_count = RE4DC_ACTOR_CROWD_NEAR;
float crowd_near = RE4DC_ACTOR_CROWD_NEAR_M * kSourceUnitsPerMetre, crowd_mid = RE4DC_ACTOR_CROWD_MID_M * kSourceUnitsPerMetre;
float crowd_mid_tau = RE4DC_ACTOR_CROWD_MID_PX;
#if RE4DC_GANADO_LIT
struct CrowdEntry { const void* model; float distance; unsigned seen; unsigned tier; unsigned lit; };
#else
struct CrowdEntry { const void* model; float distance; unsigned seen; unsigned tier; };
#endif
constexpr unsigned kCrowdMax = 48;
CrowdEntry crowd[kCrowdMax];
unsigned crowd_count = 0;
// Once per frame: keep the models seen last frame, nearest first, and tier
// them. Hysteresis: a model leaves a finer tier only 10% past its limit and
// the near rank one place late.
void crowd_rank() {
    unsigned n = 0;
    for (unsigned i = 0; i < crowd_count; ++i)
        if (crowd[i].seen + 1U == frame_serial) crowd[n++] = crowd[i];
    crowd_count = n;
    for (unsigned i = 1; i < n; ++i)
        for (unsigned j = i; j > 0 && crowd[j].distance < crowd[j - 1].distance; --j) std::swap(crowd[j], crowd[j - 1]);
    for (unsigned i = 0; i < n; ++i) {
        CrowdEntry& e = crowd[i];
        const float d = e.distance;
        const bool was_near = e.tier <= kTierNear, was_mid = e.tier <= kTierMid;
        const bool near = i < crowd_near_count + (was_near ? 1U : 0U) || d <= crowd_near * (was_near ? 1.1f : 1.0f);
        const bool mid = d <= crowd_mid * (was_mid ? 1.1f : 1.0f);
        e.tier = near ? kTierNear : mid ? kTierMid : kTierFar;
#if RE4DC_GANADO_LIT
        // GANADO_LIT (crowd.mk): per-vertex probe light for the N nearest Ganado models only; the next one keeps it
        // while within 10% of the Nth's distance (no flicker between two equally near Ganados). N < 0: every near one.
        const int N = ganlit_nearest;
        e.lit = N < 0 || i < unsigned(N) || (e.lit && N > 0 && i == unsigned(N) && d <= crowd[N - 1].distance * 1.1f);
#endif
    }
    stats.crowd_models = n;
}
#if RE4DC_GANADO_LIT
// The model's GANADO_LIT flag from this frame's ranking (a model first seen this frame: not lit until ranked).
bool crowd_lit(const void* model) {
    for (unsigned i = 0; i < crowd_count; ++i)
        if (crowd[i].model == model) return crowd[i].lit != 0;
    return false;
}
#define RE4DC_GANADO_VERTEX_LIT(p) (ganlit_nearest < 0 || crowd_lit((p).model))
#else
#define RE4DC_GANADO_VERTEX_LIT(p) true
#endif
#if defined(RE4DC_ACTOR_TEST)
int test_crowd_tier = -1;  // >= 0: every crowd model at this tier
#endif
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
struct EncTier { const void* model; unsigned tier; };
EncTier enc_tier[kCrowdMax];
unsigned enc_tier_n = 0;
#endif
// The model's tier this frame (and its distance noted for the next ranking).
unsigned crowd_tier(const Re4dcModelPart& p, int cls) {
#if defined(RE4DC_ACTOR_TEST)
    if (test_crowd_tier >= 0) {
        const unsigned t = unsigned(test_crowd_tier);
        return cls == 2 && t > kTierNear ? t - 1U : t;
    }
#endif
    const float* m = p.modelview;
    const float d = std::sqrt(m[3] * m[3] + m[7] * m[7] + m[11] * m[11]);
    CrowdEntry* e = nullptr;
    for (unsigned i = 0; i < crowd_count && !e; ++i)
        if (crowd[i].model == p.model) e = &crowd[i];
    if (!e) {
        if (crowd_count == kCrowdMax) return kTierNear;
        e = &crowd[crowd_count++];
        *e = CrowdEntry{p.model, d, frame_serial, kTierNear};
    } else if (e->seen != frame_serial) {
        e->seen = frame_serial; e->distance = d;
    } else if (d < e->distance) {
        e->distance = d;
    }
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
    {   // ENC_CENSUS (diagnostic): note the model's body tier once per census frame
        unsigned i = 0;
        while (i < enc_tier_n && enc_tier[i].model != p.model) ++i;
        if (i == enc_tier_n && enc_tier_n < kCrowdMax) enc_tier[enc_tier_n++] = EncTier{p.model, e->tier};
        else if (i < enc_tier_n && cls == 1) enc_tier[i].tier = e->tier;
    }
#endif
    const unsigned t = e->tier;
    return cls == 2 && t > kTierNear ? t - 1U : t;
}
// One colour for a whole part (mid/far tiers): the folded directional lights
// averaged over the normals that face the camera, m_l ~ 0.6 (1 + v.l)
// (1.2 facing the light, 0.6 side-lit, 0 behind), plus ambient; 255 clamp.
u32 part_colour(const Lights& L) {
    float m[3];
    for (unsigned l = 0; l < 3; ++l) m[l] = l < L.count ? 0.6f * (1.0f + L.view_dot[l]) : 0.0f;
    u32 rgb = 0;
    for (unsigned c = 0; c < 3; ++c) {
        const float v = L.color[12 + c] + L.color[c] * m[0] + L.color[4 + c] * m[1] + L.color[8 + c] * m[2];
        rgb = (rgb << 8) | (v >= 255.0f ? 255U : v > 0.0f ? u32(v) : 0U);
    }
    return rgb;
}

// Widens a finished blob's records by the RGB565 colour field and appends a
// zeroed BakeBlock (kHasBake), when that still fits in `capacity` (the GX
// list's size): the sections after the records move up and their offsets
// follow. LOD levels come first; a part whose levels leave no room stays
// unbaked. Returns the blob's size.
unsigned add_bake_field(u8* blob, unsigned size, unsigned capacity) {
    BlobHeader h;
    std::memcpy(&h, blob, sizeof(h));
    if (h.flags & kHasBake) return size;
    const unsigned rs = 3U + ((h.flags & kHasCi) ? 1U : 0U);
    const auto* table = reinterpret_cast<const MeshletInfo*>(blob + sizeof(BlobHeader));
    unsigned nrec = 0;
    for (unsigned m = 0; m < h.meshlets; ++m) nrec = std::max(nrec, unsigned(table[m].first) + table[m].n.vertices());
    const unsigned rec_at = h.rec4 * 4U;
    const unsigned old_end = rec_at + ((nrec * rs * 2U + 3U) & ~3U);
    const unsigned delta = rec_at + ((nrec * (rs + 1U) * 2U + 3U) & ~3U) - old_end;
    const unsigned bake_at = size + delta;
    if (bake_at + sizeof(BakeBlock) > capacity || (bake_at + sizeof(BakeBlock)) / 4U > 0xFFFFU) return size;
    std::memmove(blob + old_end + delta, blob + old_end, size - old_end);
    u16* r = reinterpret_cast<u16*>(blob + rec_at);
    for (unsigned i = nrec; i-- > 0;) {  // back to front: the wider copy never overtakes its source
        for (unsigned k = rs; k-- > 0;) r[i * (rs + 1U) + k] = r[i * rs + k];
        r[i * (rs + 1U) + rs] = 0;
    }
    for (unsigned i = rec_at + nrec * (rs + 1U) * 2U; i < old_end + delta; ++i) blob[i] = 0;
    h.idx4 = u16(h.idx4 + delta / 4U);
    if (h.levels) {
        h.lod4 = u16(h.lod4 + delta / 4U);
        auto* li = reinterpret_cast<LevelInfo*>(blob + h.lod4 * 4U);
        for (unsigned k = 0; k < h.levels; ++k) { li[k].table4 = u16(li[k].table4 + delta / 4U); li[k].lists4 = u16(li[k].lists4 + delta / 4U); }
    }
    std::memset(blob + bake_at, 0, sizeof(BakeBlock));
    h.bake4 = u16(bake_at / 4U);
    h.flags |= kHasBake;
    std::memcpy(blob, &h, sizeof(h));
    return bake_at + sizeof(BakeBlock);
}

// Static prelit candidates (kHasBake): opaque parts of a model the source is
// not animating or morphing (model_bridge), lit through the fold with the
// material's own colour. The baked colours are only a cache: every draw
// compares the fold (and a skinned part's pose) with the one they were baked
// with and rebakes when it moved, so a later motion stays correct.
bool prelit_candidate(const Re4dcModelPart& p) {
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    (void)p;
    return false;
#else
    return kPrelit && p.blend == 0 && !(p.alpha_state & 256) && p.lighting->enable && !p.lighting->ambient_vertex &&
           !p.lighting->material_vertex && re4dc_actor_model_prelit(p.model, p.info) != 0;
#endif
}

// A part of a lazily deferred info (no arrays yet) qualifies only if it will
// run in skin mode (prepare_frame's conditions), so no array is ever read.
bool lazy_skin(const Re4dcModelPart& p) {
    if (!RE4DC_NATIVE_ACTOR_SKIN_LAZY || p.positions || p.position_stride != 6) return false;
    const SkinEntry* e = find_skin(p.info, nullptr);
    Re4dcActorSource src{};
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    return skin_recipe_eligible(e) && re4dc_actor_model_source(p.info, &src) &&
#else
    return e && !e->materialized && e->palette && e->entries && re4dc_actor_model_source(p.info, &src) &&
#endif
           src.positions && src.normals && src.position_count == p.position_count &&
           src.normal_count == p.normal_count && bool(src.small_normals) == (p.normal_shift == 6);
}

bool qualifies(const Re4dcModelPart& p
#if RE4DC_NATIVE_FE_CONTINUATION
    ,bool explicit_pose=false
#endif
) {
#if RE4DC_ACTOR_SOURCE_SPAN
    // A published bounded view must never fall through to an unbounded FE
    // transform. Unknown views retain the existing conservative route.
    if(p.source_span.owner_serial && !uv32::prepare_owned(p))return false;
#endif
    return p.lighting && p.alpha_state <= 511 &&
           (!(p.alpha_state & 256) || ((p.flags & 0x80000000U) && p.colors)) &&
           ((!p.lighting->ambient_vertex && !p.lighting->material_vertex) || ((p.flags & 0x80000000U) && p.colors)) &&
           (!p.lighting->enable || p.lighting->attenuation == 1 || p.lighting->attenuation == 2) &&
           p.shift <= 30 && (p.position_stride == 6 || p.position_stride == 8) &&
           (p.normal_shift == 6 || p.normal_shift == 14) && p.normal_stride >= 3 &&
           p.position_count && p.normal_count && p.stream_bytes <= 1024 * 1024 && p.stream_bytes >= 32 &&
           (
#if RE4DC_NATIVE_FE_CONTINUATION
            explicit_pose ||
#endif
            (ram(p.positions, p.position_count * p.position_stride) &&
             ram(p.normals, p.normal_count * p.normal_stride)) || lazy_skin(p)) &&
           ram(p.stream, p.stream_bytes) && p.uv &&
           p.projection[0] == 0 && p.viewport[2] > 0 && p.viewport[3] > 0;
}

const BlobHeader* convert(const Re4dcModelPart& p) {
    SortSource sort;
    Re4dcActorSource src{};
    if (re4dc_actor_model_source(p.info, &src) && src.positions && src.position_count == p.position_count) {
        sort.positions = src.positions; sort.position_count = src.position_count;
        if (src.normals && src.normal_count == p.normal_count) {
            sort.normals = src.normals; sort.normal_count = src.normal_count; sort.small_normals = src.small_normals != 0;
        }
    }
    const unsigned mark = workspace_top;
    // In place: built in scratch with the GX list's size as the limit.
    {
        u8* out = static_cast<u8*>(scratch(p.stream_bytes));
        const unsigned room = (
#if RE4DC_ACTOR_TRANSACTION
        workspace_scratch_limit()>=workspace_top?workspace_scratch_limit()-workspace_top:0u
#else
        workspace_end - workspace_top
#endif
        ) & ~31U;
        u8* work = out && room ? static_cast<u8*>(scratch(room)) : nullptr;
        if (!work) { DFA26_MODEL_HIT(ActorWorkspace, 1) ++stats.workspace_misses; workspace_top = mark; return nullptr; }
        const bool opaque = p.blend == 0;
#if defined(RE4DC_ACTOR_TEST)
        const double t0 = test_now_us();
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_BACKFACE_CONE == 2
        // The comparison must parse the GX source before the in-place publish.
        // Both scratch buffers are then reused by the actual conversion.
        unsigned abc32_plain_records = 0, abc32_plain_meshlets = 0;
        {
            Converter plain(p, sort, out, p.stream_bytes, Arena{work, room}, false);
            plain.abc_no_split = true;
            if (plain.run()) { abc32_plain_records = plain.record_count(); abc32_plain_meshlets = plain.meshlet_count(); }
        }
#endif
        Converter c(p, sort, out, p.stream_bytes, Arena{work, room}, false);
#if !RE4DC_ACTOR_BACKFACE_CONE
        const bool ok = c.run();
        Converter* const cp = &c;
#else
        bool ok = c.run();
        Converter* cp = &c;
        // ACTOR_BACKFACE_CONE: a split blob that no longer fits in place is built again unsplit (no cones).
        Converter c2(p, sort, out, p.stream_bytes, Arena{work, room}, false);
        if (!ok && c.split()) { c2.abc_no_split = true; ok = c2.run(); cp = &c2; ++abc_unsplit; }
#endif
#if defined(RE4DC_ACTOR_TEST)
        const double dt = test_now_us() - t0;
        test_convert_us += dt; test_convert_max_us = std::max(test_convert_max_us, dt);
#endif
        workspace_top = mark;
        if (ok) {
            if (kLodBuild && opaque && lod_budget_frame) out[2] |= kLodPending;  // levels: relod()
            unsigned size = cp->bytes();
            if (prelit_candidate(p)) size = add_bake_field(out, size, p.stream_bytes);
            Re4dcActorStreamMutation mutation(p.stream,p.stream_bytes);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
            re4dc_gcasset::HandDerivationScope gcasset_mutation(p.stream,p.stream_bytes);
#endif
            std::memcpy(const_cast<u8*>(p.stream), out, size);
#if RE4DC_ACTOR_BACKFACE_CONE
            if (cp->split()) abc_build(p, size, abc_class_of(p.model));
#if RE4DC_ACTOR_BACKFACE_CONE == 2
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
            if (cp->split() && abc32_plain_meshlets) {
                abc_rec_split += cp->record_count(); abc_rec_plain += abc32_plain_records;
                abc_ml_split += cp->meshlet_count(); abc_ml_plain += abc32_plain_meshlets;
            }
#else
            if (cp->split()) {  // check build: the same part unsplit, for the record / meshlet growth
                Converter c3(p, sort, out, p.stream_bytes, Arena{work, room}, false);
                c3.abc_no_split = true;
                if (c3.run()) {
                    abc_rec_split += cp->record_count(); abc_rec_plain += c3.record_count();
                    abc_ml_split += cp->meshlet_count(); abc_ml_plain += c3.meshlet_count();
                }
            }
#endif
#endif
#endif
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
            gcasset_mutation.complete();
#endif
            ++stats.conversions;
            if (cp->level_count()) ++stats.lod_parts;
            return reinterpret_cast<const BlobHeader*>(p.stream);
        }
    }
    // Larger than the GX list: a blob for this submit only (released by it).
    const unsigned room = (
#if RE4DC_ACTOR_TRANSACTION
        workspace_scratch_limit()>=workspace_top?workspace_scratch_limit()-workspace_top:0u
#else
        workspace_end - workspace_top
#endif
        ) & ~31U;
    const unsigned want = std::min((p.stream_bytes * 2U + 1024U + 31U) & ~31U, room / 2U);
    u8* out = static_cast<u8*>(scratch(want));
    const unsigned rest = (
#if RE4DC_ACTOR_TRANSACTION
        workspace_scratch_limit()>=workspace_top?workspace_scratch_limit()-workspace_top:0u
#else
        workspace_end - workspace_top
#endif
        ) & ~31U;
    u8* work = out && rest ? static_cast<u8*>(scratch(rest)) : nullptr;
    if (!work) { DFA26_MODEL_HIT(ActorWorkspace, 1) ++stats.workspace_misses; workspace_top = mark; return nullptr; }
    Converter c(p, sort, out, want, Arena{work, rest}, false);  // per submit: no LOD, unbaked
#if RE4DC_ACTOR_BACKFACE_CONE
    c.abc_no_split = true;
#endif
    if (!c.run()) { ++stats.conversion_rejects; workspace_top = mark; return nullptr; }
    workspace_top = unsigned(out - workspace) + ((c.bytes() + 31U) & ~31U);
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorTransient, 1)
#endif
    ++stats.transient_conversions;
    return reinterpret_cast<const BlobHeader*>(out);
}

// A converted part whose LOD build was deferred: its level-0 strips become a
// temporary GX strip list (0x98, same corner layout) that goes through the
// converter again, now with levels; the result replaces the blob in place.
// The triangle set is unchanged. Tried once, on a frame with enough
// workspace and budget left; on failure the part stays at level 0.
void relod(const Re4dcModelPart& p, bool crowd_part) {
    lod_wanted = true;
    if (workspace_bytes < kLodMinWorkspace) return;
    u8* stream = const_cast<u8*>(p.stream);
    const BlobHeader b = *reinterpret_cast<const BlobHeader*>(stream);
    unsigned triangles = 0, corners = 0, strips = 0;
    const auto* table = reinterpret_cast<const MeshletInfo*>(stream + sizeof(BlobHeader));
    const u8* lists = stream + b.idx4 * 4U;
    for (unsigned m = 0; m < b.meshlets; ++m) {
        triangles += table[m].n.triangles(); corners += table[m].n.indices();
        for (unsigned i = 0; i < table[m].n.indices(); ++i) strips += lists[table[m].index + i] >> 7;
    }
#if defined(RE4DC_ACTOR_LOD_PART_MAX) && RE4DC_ACTOR_LOD_PART_MAX
    // ACTOR_LOD_PART_MAX=N (shotfx20.mk; render only): a part over N triangles is not simplified at run time (one
    // such build is ~20 hw ms in a single frame, the first time a gun, arm or Ganado part is drawn); it stays at
    // level 0, full detail.
    if (triangles > RE4DC_ACTOR_LOD_PART_MAX) {
        Re4dcActorStreamMutation mutation(p.stream, p.stream_bytes);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
        re4dc_gcasset::HandDerivationScope gcasset_mutation(p.stream,p.stream_bytes);
#endif
        stream[2] &= u8(~kLodPending);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
        gcasset_mutation.complete();
#endif
        return;
    }
#endif
    if (triangles >= kLodMinTriangles && !lod_take(triangles)) return;
    Re4dcActorStreamMutation mutation(p.stream,p.stream_bytes);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    re4dc_gcasset::HandDerivationScope gcasset_mutation(p.stream,p.stream_bytes);
#endif
    stream[2] &= u8(~kLodPending);
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    if(triangles<kLodMinTriangles)gcasset_mutation.complete();
#endif
    if (triangles < kLodMinTriangles) return;
    const unsigned stride = (p.flags & 0x80000000U) ? 8U : 6U;
    const unsigned rs = 3U + ((b.flags & kHasCi) ? 1U : 0U) + ((b.flags & kHasBake) ? 1U : 0U);
    const unsigned gx_bytes = (strips * 3U + corners * stride + 31U) & ~31U;
    const unsigned mark = workspace_top;
    u8* gx = static_cast<u8*>(scratch(gx_bytes));
    u8* out = gx ? static_cast<u8*>(scratch(p.stream_bytes)) : nullptr;
    const unsigned room = (
#if RE4DC_ACTOR_TRANSACTION
        workspace_scratch_limit()>=workspace_top?workspace_scratch_limit()-workspace_top:0u
#else
        workspace_end - workspace_top
#endif
        ) & ~31U;
    u8* work = out && room ? static_cast<u8*>(scratch(room)) : nullptr;
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    if(!work)gcasset_mutation.complete(); // the only owned write was the completed flag clear
#endif
    if (!work) { DFA26_MODEL_HIT(ActorWorkspace, 1) ++stats.workspace_misses; workspace_top = mark; return; }
    u8* w = gx;
    auto put16 = [&](unsigned v) { *w++ = u8(v >> 8); *w++ = u8(v); };
    const u16* records = reinterpret_cast<const u16*>(stream + b.rec4 * 4U);
    for (unsigned m = 0; m < b.meshlets; ++m) {
        const u16* r = records + table[m].first * rs;
        const u8* idx = lists + table[m].index;
        for (unsigned i = 0, start = 0; i < table[m].n.indices(); ++i) {
            if (!(idx[i] & 0x80U)) continue;
            *w++ = 0x98; put16(i + 1 - start);
            for (unsigned k = start; k <= i; ++k) {
                const u16* e = r + (idx[k] & 127U) * rs;
                put16(e[0]); put16(e[1]);
                if (stride == 8) put16((b.flags & kHasCi) ? e[3] : b.color_index);
                put16(e[2]);
            }
            start = i + 1;
        }
    }
    const unsigned used = unsigned(w - gx);
    while (w < gx + gx_bytes) *w++ = 0;
    Re4dcModelPart q = p;
    q.stream = gx; q.stream_bytes = used;
    SortSource sort;
    Re4dcActorSource src{};
    if (re4dc_actor_model_source(p.info, &src) && src.positions && src.position_count == p.position_count) {
        sort.positions = src.positions; sort.position_count = src.position_count;
        if (src.normals && src.normal_count == p.normal_count) {
            sort.normals = src.normals; sort.normal_count = src.normal_count; sort.small_normals = src.small_normals != 0;
        }
    }
    level_ladder = crowd_part ? lod_fractions_crowd : lod_fractions;
    Converter c(q, sort, out, p.stream_bytes, Arena{work, room}, true);
#if RE4DC_ACTOR_BACKFACE_CONE
    unsigned abc_cls = abc_class_of(p.model);
    c.abc_force = abc_table(stream, p.stream_bytes, &abc_cls) != nullptr;
#endif
    const bool built = c.run() && c.level_count();
    level_ladder = lod_fractions;
    if (built) {
        unsigned size = c.bytes();
        if (b.flags & kHasBake) size = add_bake_field(out, size, p.stream_bytes);  // rebaked on the next draw
        std::memcpy(stream, out, size);
#if RE4DC_ACTOR_BACKFACE_CONE
        if (c.split()) abc_build(p, size, abc_cls);
#endif
        ++stats.lod_parts; ++stats.lod_rebuilds;
    }
#if RE4DC_GC_ASSET_GATE && RE4DC_GC_ASSET_LEON_HAND_PACK
    gcasset_mutation.complete();
#endif
    workspace_top = mark;
}
}  // namespace

#if defined(RE4DC_ACTOR_LOD_ENTRY) && RE4DC_ACTOR_LOD_ENTRY
extern "C" int re4dc_room4_state(unsigned* generation, unsigned* cells, unsigned* bytes, unsigned* stale,
                                 unsigned* refused);
#endif
extern "C" void re4dc_actor_frame(void* memory, unsigned bytes) {
#if RE4DC_ACTOR_TRANSACTION
    re4dc_actor_owner_retire(); // before workspace rebinding
#endif

    workspace = static_cast<unsigned char*>(memory);
    workspace_bytes = memory ? bytes & ~31U : 0;
    workspace_top = 0; workspace_end = workspace_bytes;
    ++frame_serial;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    uv32::log(frame_serial);
#endif
    lod_budget = lod_budget_frame;
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
    b28::window(frame_serial);
#endif
#if defined(RE4DC_ACTOR_LOD_ENTRY) && RE4DC_ACTOR_LOD_ENTRY
    {   // ACTOR_LOD_ENTRY=K (shotfx20.mk; render only, exact triangles): for the first K frames of a room every part
        // drawn has its detail levels built at once (no per-frame budget), so the builds land in the room-entry
        // window instead of a later gameplay frame. Levels are built in place: no memory cost.
        static unsigned entry_gen = ~0U, entry_left;
        unsigned gen = 0, cells = 0, cb = 0, st = 0, rf = 0;
        re4dc_room4_state(&gen, &cells, &cb, &st, &rf);
        if (gen != entry_gen) { entry_gen = gen; entry_left = RE4DC_ACTOR_LOD_ENTRY; }
        if (entry_left && lod_budget_frame) { --entry_left; lod_budget = 0x7FFFFFFFU; }
    }
#endif
    lod_wanted_last = lod_wanted; lod_wanted = false;
    if constexpr (kCrowd) crowd_rank();
#if RE4DC_GIGANTE_LIGHTS
    if (!(frame_serial % 600U) && gigante_folds) {
        re4dc_log("gigante lights: frame=%u folds=%u (parts over 3 lights, last 600 frames)\n", frame_serial,
                  gigante_folds);
        gigante_folds = 0;
    }
#endif
#if RE4DC_ACTOR_LOG
    if (!(frame_serial % 120U)) {
        const Re4dcActorStats& s = stats;
        re4dc_log("native actor: frame=%u ws=%u parts=%u handled=%u declined=%u conv=%u transient=%u rejects=%u ws_miss=%u "
                  "lod_parts=%u relod=%u draws=%u/%u/%u/%u tris=%u records=%u lit=%u bake=%u/%u/%u uv16=%u dirs=%u\n",
                  frame_serial, workspace_bytes, s.parts, s.handled, s.declined, s.conversions, s.transient_conversions,
                  s.conversion_rejects, s.workspace_misses, s.lod_parts, s.lod_rebuilds, s.lod_draws[0], s.lod_draws[1],
                  s.lod_draws[2], s.lod_draws[3], s.triangles, s.vertices, s.normals_lit, s.bake_builds, s.bake_hits,
                  s.bake_scaled, s.uv16_parts, s.skin_dir_sets);
        if (kCrowd)
            re4dc_log("native actor crowd: models=%u parts=%u/%u/%u/%u tris=%u/%u/%u/%u\n", s.crowd_models,
                      s.crowd_parts[0], s.crowd_parts[1], s.crowd_parts[2], s.crowd_parts[3], s.crowd_triangles[0],
                      s.crowd_triangles[1], s.crowd_triangles[2], s.crowd_triangles[3]);
    }
#endif
}

extern "C" const Re4dcActorStats* re4dc_actor_stats() { return &RE4DC_STATS_OBJECT; }
extern "C" unsigned re4dc_actor_workspace_want() { return lod_wanted_last && lod_budget_frame ? kLodWorkspaceBytes : 0U; }
#if defined(RE4DC_ACTOR_TEST)
// Test: the LOD build budget left in the current frame.
extern "C" void re4dc_actor_test_lod_budget_left(unsigned left) { lod_budget = left; }
extern "C" void re4dc_actor_test_crowd_tier(int tier) { test_crowd_tier = tier; }
#endif
extern "C" void re4dc_actor_crowd(unsigned near_count, float near_distance, float mid_distance, float mid_pixels) {
    crowd_near_count = near_count; crowd_near = near_distance; crowd_mid = mid_distance; crowd_mid_tau = mid_pixels;
}
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
// CROWD_INVIS_SKIP (crowd.mk, lane iv): crowd_tier's bookkeeping without drawing, for a Ganado whose source-path draw
// the knob skipped (trans.cpp invisReplayRender, one call per info it would have drawn, with that info's modelview):
// the model stays in the ranking with the distance its parts would have noted, so crowd_rank sees what it sees with
// the knob off.
extern "C" void re4dc_actor_crowd_note(const void* model, const float* modelview) {
    if constexpr (kCrowd) {
        const float* m = modelview;
        const float d = std::sqrt(m[3] * m[3] + m[7] * m[7] + m[11] * m[11]);
        CrowdEntry* e = nullptr;
        for (unsigned i = 0; i < crowd_count && !e; ++i)
            if (crowd[i].model == model) e = &crowd[i];
        if (!e) {
            if (crowd_count == kCrowdMax) return;
            crowd[crowd_count++] = CrowdEntry{model, d, frame_serial, kTierNear};
        } else if (e->seen != frame_serial) {
            e->seen = frame_serial; e->distance = d;
        } else if (d < e->distance) {
            e->distance = d;
        }
    } else {
        (void)model; (void)modelview;
    }
}
// A source part whose next native draw changes nothing that outlives the frame: converted in place (convert) and no
// LOD build waiting (relod, which also spends the frame's lod_budget). The skip takes only Ganados whose drawn parts
// are all settled, so a skipped draw leaves the part streams and the LOD budget exactly as the source draw would.
extern "C" int re4dc_actor_part_settled(const void* stream, unsigned bytes) {
    const u8* s = static_cast<const u8*>(stream);
    return bytes >= sizeof(BlobHeader) && s[0] == kMagic && s[1] == kVersion && !(s[2] & kLodPending);
}
#if RE4DC_CROWD_INVIS_SKIP == 2 || (defined(RE4DC_PS2_INTERIOR_OWNER) && RE4DC_PS2_INTERIOR_OWNER == 2)
// =2 (check build; also PS2_INTERIOR_ACTORS=2 with PS2_INTERIOR_CULL=2): the model's crowd entry in this frame: 1 and
// its distance when its parts noted it, else 0.
extern "C" int re4dc_actor_crowd_peek(const void* model, float* distance) {
    for (unsigned i = 0; i < crowd_count; ++i)
        if (crowd[i].model == model) {
            if (crowd[i].seen != frame_serial) return 0;
            *distance = crowd[i].distance;
            return 1;
        }
    return 0;
}
// =2: the distance re4dc_actor_crowd_note (and crowd_tier) takes from a modelview.
extern "C" float re4dc_actor_crowd_distance(const float* m) {
    return std::sqrt(m[3] * m[3] + m[7] * m[7] + m[11] * m[11]);
}
#endif
#endif
#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
// ENC_CENSUS (diagnostic, default 0; read by coarse.cpp re4dc_enc_frame): the crowd-classed models drawn in the
// census frame (crowd_tier notes each model once, at its body tier), by tier (full / near / mid / far).
extern "C" void re4dc_enc_crowd_tiers(unsigned* out) {
    for (unsigned i = 0; i < 4; ++i) out[i] = 0;
    for (unsigned i = 0; i < enc_tier_n; ++i) ++out[enc_tier[i].tier & 3U];
    enc_tier_n = 0;
}
#endif
extern "C" void re4dc_actor_lod(float pixels, unsigned budget) {
    lod_tau = pixels;
    lod_budget_frame = budget;
    if (lod_budget > budget) lod_budget = budget;
}
#if defined(RE4DC_ACTOR_TEST)
extern "C" void re4dc_actor_test_lod_ladder(const float* f) {
    for (unsigned k = 0; k < kMaxLevels; ++k) lod_fractions[k] = f[k];
    lod_metric_qem = f[3] != 0.0f;
}
#endif

extern "C" int re4dc_actor_skin_register(unsigned frame, const void* info, const void* position_buffer,
                                         const float* palette, unsigned entries) {
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(skin_recipe_building)return 0;
#endif
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if (skin_admission_pending.serial) return 0;
#endif
    if (frame != skin_frame) {
#if RE4DC_ACTOR_TRANSACTION
        owned_skin_clear();owned_skin_invalidate_frames();
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
        skin_recipe_frame_retire();
#endif
        skin_frame = frame; skin_count = 0;
    }
    if (!palette || !entries) return 0;
#if RE4DC_ACTOR_TRANSACTION
#if RE4DC_ACTOR_SKIN_OWNER_POOL
    if(find_owned_skin(info))return 0;
#else
    for(unsigned i=0;i<skin_count;++i)if(owned_skins[i].serial && owned_skins[i].info==info)return 0;
#endif
#endif
    // Lazy (no arrays): the info's latest Trans() wins, as its pPosBuf would.
    if (!position_buffer)
        if (SkinEntry* e =
#if RE4DC_ACTOR_SKIN_OWNER_POOL
            find_ordinary_skin(info, nullptr)
#else
            find_skin(info, nullptr)
#endif
        ) {
#if RE4DC_ACTOR_TRANSACTION && !RE4DC_ACTOR_SKIN_OWNER_POOL
            if(owned_skins[unsigned(e-skins)].serial)return 0;
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
            if(skin_recipe_building || !skin_recipe_drop(*e,unsigned(e-skins)))return 0;
            const unsigned state=skin_recipe_nominated(*e)?kSkinRecipeReady:0u;
            *e = {info, nullptr, palette, entries, state}; ++stats.skin_registered; return 1;
#else
            *e = {info, nullptr, palette, entries, 0}; ++stats.skin_registered; return 1;
#endif
        }
#if RE4DC_ACTOR_TRANSACTION
    for(unsigned i=0;i<skin_count;++i)if(!skins[i].info
#if !RE4DC_ACTOR_SKIN_OWNER_POOL
        && !owned_skins[i].serial
#endif
    ){
        skins[i]={info,position_buffer,palette,entries,0};++stats.skin_registered;return 1;
    }
#endif
    if (skin_count == kSkins) DFA26_MODEL_SLOW(ActorSkinRegistry, 1, return 0;)
    skins[skin_count++] = {info, position_buffer, palette, entries, 0};
    ++stats.skin_registered;
    return 1;
}

#if RE4DC_ACTOR_CENSUS
namespace { unsigned* census_mat_row; }  // ACTOR_CENSUS: the current part's row "mat" counter
#endif
#if RE4DC_SKIN_PALETTE_LAZY
extern "C" void re4dc_skin_palette_resolve(const float* palette);  // trans.cpp SKIN_PALETTE_LAZY
#endif
extern "C" const float* re4dc_actor_skin_palette(const void* info, const void* position_buffer, unsigned* entries) {
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    SkinEntry* e = find_skin(info, position_buffer);
    if (!e || !skin_recipe_readable(*e) ||
        (e->materialized==kSkinRecipePending && !skin_recipe_materialize(*e))) {*entries=0;return nullptr;}
#else
    const SkinEntry* e = find_skin(info, position_buffer);
    if (!e || e->materialized) { *entries = 0; return nullptr; }
#endif
#if RE4DC_ACTOR_SKIN_RESERVE
    if(!e->palette || !e->entries){*entries=0;return nullptr;} // inert reservation
#endif
#if RE4DC_SKIN_PALETTE_LAZY
    re4dc_skin_palette_resolve(e->palette);  // the caller reads it (prepare_frame's skin Frame)
#endif
    *entries = e->entries;
    return e->palette;
}

#if defined(RE4DC_PROP_GATE) && RE4DC_PROP_GATE
// PROP_GATE (trans.cpp propGate): 1 when an info without arrays has its lazily skinned palette registered and not
// materialized, so its parts can only draw through the skinned frame (lazy_skin / prepare_frame kSkin) and its gate.
extern "C" int re4dc_actor_skin_lazy_known(const void* info) {
    const SkinEntry* e = find_skin(info, nullptr);
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    return skin_recipe_eligible(e);
#else
    return e && !e->materialized && e->palette && e->entries;
#endif
}
#if RE4DC_PROP_GATE == 2
extern "C" { unsigned re4dc_pg_expect, re4dc_pg_fogged; }  // =2 check: parts of a gated model culled at the fog gate
#endif
#endif
extern "C" void re4dc_actor_materialize(const Re4dcModelPart* p) {
    if (!p) return;
    SkinEntry* e = find_skin(p->info, p->positions);
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (!e || !skin_recipe_readable(*e) ||
        (e->materialized==kSkinRecipePending && !skin_recipe_materialize(*e)))return;
#else
    if (!e || e->materialized) return;
#endif
#if RE4DC_ACTOR_SKIN_RESERVE
    if(!e->palette || !e->entries)return; // no source palette was deferred
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorSkinMaterialize, 1)
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (!re4dc_skin_materialize(e->info, e->palette))return;
#else
    re4dc_skin_materialize(e->info, e->palette);
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    e->materialized=skin_recipe_nominated(*e)?kSkinRecipeDone:1u;
#else
    e->materialized = 1;
#endif
    ++stats.materialized_infos;
#if RE4DC_ACTOR_CENSUS
    if (census_mat_row) *census_mat_row += 1;
#endif
}

#if defined(RE4DC_ACTOR_REPLAY_SKIN) && RE4DC_ACTOR_REPLAY_SKIN
// ACTOR_REPLAY_SKIN (crowd.mk): a part whose info's lazily skinned palette this frame was already materialized for the
// generic path (a queued / replayed part, e.g. h2's translucent room model drawn after the codec screen) declines
// here: lazy_skin needs an unmaterialized entry and the part's own arrays have no entry of their own. Re-register the
// same palette for the info's current arrays (the ordinary non-lazy registration Trans() makes), so the skinned
// frame takes the part. Ordinary entries only (an owned entry never switches back to source data); 1 = *p now
// carries the arrays and the entry exists.
extern "C" int re4dc_actor_skin_rearm(Re4dcModelPart* p) {
    if (!p || !p->info) return 0;
    const SkinEntry* e =
#if RE4DC_ACTOR_SKIN_OWNER_POOL
        find_ordinary_skin(p->info, nullptr);
    if (find_owned_skin(p->info)) return 0;
#else
        find_skin(p->info, nullptr);
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (!e || (e->materialized!=1 && e->materialized!=kSkinRecipeDone) || !e->palette || !e->entries)return 0;
#else
    if (!e || !e->materialized || !e->palette || !e->entries) return 0;
#endif
#if RE4DC_ACTOR_TRANSACTION && !RE4DC_ACTOR_SKIN_OWNER_POOL
    if (owned_skins[unsigned(e - skins)].serial) return 0;
#endif
    const float* palette = e->palette; const unsigned entries = e->entries;
    if (!p->positions && !re4dc_actor_model_buffers(p)) return 0;
    if (const SkinEntry* own = find_skin(p->info, p->positions)) return !own->materialized && own->palette == palette;
    return re4dc_actor_skin_register(skin_frame, p->info, p->positions, palette, entries);
}
#endif
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
extern "C" int re4dc_actor_materialize_lazy(Re4dcModelPart* p) {
    if (!p || p->positions) return 1;
    SkinEntry* e = find_skin(p->info, nullptr);
    if (!e) return 0;
#if RE4DC_ACTOR_SKIN_RESERVE
    if(!e->palette || !e->entries)return 0; // never materialize a placeholder
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (e->materialized==kSkinRecipePending && !skin_recipe_materialize(*e))return 0;
    if (!skin_recipe_readable(*e) && e->materialized!=1 &&
        e->materialized!=kSkinRecipeDone)return 0;
    if (skin_recipe_readable(*e)) {
#else
    if (!e->materialized) {
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_MODEL_HIT(ActorSkinMaterialize, 1)
#endif
        if (!re4dc_skin_materialize(e->info, e->palette)) return 0;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
        e->materialized=skin_recipe_nominated(*e)?kSkinRecipeDone:1u;
#else
        e->materialized = 1;
#endif
        ++stats.materialized_infos;
#if RE4DC_ACTOR_CENSUS
        if (census_mat_row) *census_mat_row += 1;
#endif
    }
    return re4dc_actor_model_buffers(p);
}
#endif

#if RE4DC_ACTOR_FOG_GATE
extern "C" float re4dc_fog_gate_far();
extern "C" void re4dc_log(const char* fmt, ...);
namespace {
unsigned fog_gate_tests = 0, fog_gate_culled = 0, fog_gate_log = 0;
// SCENERY_GATE's cull depth: the projection far, or the fogged View far when it is nearer.
float fog_gate_depth(float near_distance, float far_distance) {
    const float view_far = re4dc_fog_gate_far();
    return view_far > near_distance && view_far < far_distance ? view_far : far_distance;
}
// Conservative view depth bound of a skinned Frame: every skinned vertex is a convex blend of
// R_i x + t_i over palette entries i with x in the part's bind ball (|x| <= |c| + r), so its
// view depth -z >= min_i(-z(t_i)) - max_i(|m_z| * s_i) * (|c| + r), s_i = R_i's largest column
// norm. Cached per Frame (T = min depth of t_i, G = max |m_z| s_i).
}  // namespace
#endif
#if RE4DC_ACTOR_CENSUS
// ACTOR_CENSUS (diagnostic): which models reach the per-part native path, per 120 frames:
// parts and source positions by (model id, ot_type, nParts), heaviest first.
extern "C" unsigned re4dc_actor_census_key(const void*);
extern "C" unsigned re4dc_actor_census_vptr(const void*);
extern "C" void re4dc_actor_census_describe(const void*, unsigned);
extern "C" unsigned re4dc_ui_frame();
namespace {
struct CensusRow { unsigned key, parts, verts, vptr, nv, nt, culled, lvl, dec, decv, mat; };
CensusRow* census_cur;
CensusRow census_rows[48]; unsigned census_frame0; bool census_started;
void census_note(const Re4dcModelPart& p) {
    const unsigned frame = re4dc_ui_frame();
    if (!census_started) { census_started = true; census_frame0 = frame; }
    if (frame - census_frame0 >= 120U) {
        for (unsigned n = 0; n < 48; ++n) {
            unsigned best = 48;
            for (unsigned i = 0; i < 48; ++i)
                if (census_rows[i].parts && (best == 48 || census_rows[i].verts > census_rows[best].verts)) best = i;
            if (best == 48) break;
            const CensusRow& r = census_rows[best];
            re4dc_log("ACENSUS frame=%u id=%02x ot=%u nparts=%u parts=%u verts=%u per_frame_verts=%u vptr=%08x nv_pf=%u nt_pf=%u culled_nv=%u lvl_sum=%u dec=%u dec_verts=%u mat=%u\n", frame,
                      r.key & 0xffU, (r.key >> 8) & 0xffU, r.key >> 16, r.parts, r.verts, r.verts / (frame - census_frame0), r.vptr, r.nv / (frame - census_frame0), r.nt / (frame - census_frame0), r.culled, r.lvl, r.dec, r.decv, r.mat);
            census_rows[best].parts = 0;
        }
        for (auto& r : census_rows) r = CensusRow{};
        census_frame0 = frame;
    }
    const unsigned key = re4dc_actor_census_key(p.model);
    if (key == 0x00010000U) re4dc_actor_census_describe(p.model, p.position_count);
    for (auto& r : census_rows)
        if (r.key == key || !r.parts) { if (!r.parts) r.vptr = re4dc_actor_census_vptr(p.model); r.key = key; ++r.parts; r.verts += p.position_count; census_cur = &r; census_mat_row = &r.mat; return; }
}
}
#endif
#if RE4DC_ACTOR_CENSUS
#define RE4DC_CENSUS_DEC(pp) do { if (census_cur) { ++census_cur->dec; census_cur->decv += (pp) ? (pp)->position_count : 0; } } while (0)
#else
#define RE4DC_CENSUS_DEC(pp) do { } while (0)
#endif
#if defined(RE4DC_MODEL_DROP_LOG) && RE4DC_MODEL_DROP_LOG
// MODEL_DROP_LOG (native_ui.cpp): an actor-path resource reject, with the inner reason native_ui noted (else p =
// packet capacity left under kCacheSlots + 64, d = direct scratch under kCacheSlots).
extern "C" void re4dc_model_drop(const Re4dcModelPart*, unsigned, unsigned, unsigned, unsigned, unsigned);
extern "C" unsigned re4dc_model_drop_last();
#define RE4DC_DROP_ACTOR(pp, inner, cap) \
    re4dc_model_drop((pp), 'a' | ((inner) ? (inner) : (re4dc_model_drop_last() & 0xffU) ? re4dc_model_drop_last() & 0xffU : 'p') << 8, (cap), 0, 0, 0)
#else
#define RE4DC_DROP_ACTOR(pp, inner, cap) do { } while (0)
#endif
#if defined(RE4DC_ACC_CROWD_TIER) && RE4DC_ACC_CROWD_TIER
extern "C" const void* re4dc_actor_accessory_parent(const void* model);  // model_bridge.cpp
#endif
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
extern "C" void re4dc_callprof_part(const void* model, unsigned path);  // model_bridge.cpp
#endif
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
extern "C" void re4dc_actor_light25_snapshot(Re4dcActorLight25Stats* out) {
    if (out) *out = light25_stats;
}
extern "C" void re4dc_actor_light25_part_colour(const Re4dcModelPart* p, const float center[3], Re4dcActorLight25Colour* out) {
    if (!out) return;
    if (!p || !p->lighting) { *out = {0xFFFFFFU, {65536U, 65536U, 65536U}}; return; }
    static const float origin[3] = {0.0f, 0.0f, 0.0f};
    const Frame unused{};
    Lights lights;
    fast_only_lights(*p, unused, center ? center : origin, lights);
    if (!lights.constant || !lights.fast) light25_add(light25_stats.fallback_parts);
    *out = lights.colour25;
}
extern "C" unsigned re4dc_actor_light25_part_rgb(const Re4dcModelPart* p, const float center[3]) {
    Re4dcActorLight25Colour colour;
    re4dc_actor_light25_part_colour(p, center, &colour);
    return colour.rgb;
}
#endif
extern "C" int re4dc_actor_stream_encoded(const unsigned char* stream,unsigned bytes) {
    return stream && bytes>=sizeof(BlobHeader) && stream[0]==kMagic && stream[1]==kVersion;
}
#if defined(RE4DC_G1_PART_CENSUS) && RE4DC_G1_PART_CENSUS
// G1_PART_CENSUS (g1parts.mk, diagnostic only): how often the native per-part setup repeats work with the same inputs.
// "G1PC actor" every 120 frames: parts (generic submit / one-chunk owner path), model changes between consecutive
// parts, light builds and builds whose inputs (lighting record contents, modelview, centre, normal scale) equal the
// previous build's, Frame (info) preparations.
namespace g1pc {
unsigned frame0, parts, chunks, models, lights, light_same, light_same_rec;
const void* last_model;
re4dc::render::SourceLighting last_rec; float last_mv[12], last_c[3], last_nq; bool have_last;
void tick() {
    if (frame_serial - frame0 < 120U) return;
    re4dc_log("G1PC actor: frame=%u parts=%u chunks=%u models=%u lights=%u light_same=%u light_same_rec=%u infos=%u\n",
              frame_serial, parts, chunks, models, lights, light_same, light_same_rec, stats.info_preparations);
    frame0 = frame_serial; parts = chunks = models = lights = light_same = light_same_rec = 0;
}
void part(const Re4dcModelPart& p, bool chunk) {
    tick();
    if (chunk) ++chunks; else ++parts;
    if (p.model != last_model) { ++models; last_model = p.model; }
}
void light(const Re4dcModelPart& p, const Frame& f, const float c[3]) {
    ++lights;
    const bool rec = have_last && !std::memcmp(&last_rec, p.lighting, sizeof(last_rec));
    if (rec) ++light_same_rec;
    if (rec && !std::memcmp(last_mv, p.modelview, sizeof(last_mv)) && !std::memcmp(last_c, c, sizeof(last_c)) &&
        last_nq == f.nq) ++light_same;
    std::memcpy(&last_rec, p.lighting, sizeof(last_rec)); std::memcpy(last_mv, p.modelview, sizeof(last_mv));
    std::memcpy(last_c, c, sizeof(last_c)); last_nq = f.nq; have_last = true;
}
}
#define G1PC_PART(p, chunk) g1pc::part(p, chunk)
#define G1PC_LIGHT(p, f, c) g1pc::light(p, f, c)
#else
#define G1PC_PART(p, chunk) do { } while (0)
#define G1PC_LIGHT(p, f, c) do { } while (0)
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
// PROP_PROF (diagnostic): where re4dc_actor_submit leaves for each model key (kind/id/type), with the time from entry
// to the exit, and the meshlet census (tested / all-culled). PXF lines every 120 UI frames.
extern "C" unsigned re4dc_propprof_key(const void* model);
extern "C" unsigned long long re4dc_otp_now_us();
extern "C" unsigned re4dc_ui_frame();
namespace pxf {
enum { kDecl, kCull3, kDefer, kFog, kSphere, kRes, kDraw, kN };
struct Row { unsigned key, n[kN], us[kN], ml, mlc, lit_us, pos_us, q_us, cls_us, def_us; };
Row rows[24]; unsigned nrows, last;
unsigned cur_key; unsigned long long t0;
Row* row() {
    for (unsigned k = 0; k < nrows; ++k) if (rows[k].key == cur_key) return &rows[k];
    if (nrows == 24) return nullptr;
    Row& r = rows[nrows++]; std::memset(&r, 0, sizeof r); r.key = cur_key; return &r;
}
void begin(const Re4dcModelPart* p) {
    const unsigned fr = re4dc_ui_frame();
    if (!last) last = fr;
    if (fr - last >= 120) {
        re4dc_log("PXF f=%u frames=%u\n", fr, fr - last);
        for (unsigned k = 0; k < nrows; ++k) {
            const Row& r = rows[k];
            re4dc_log("PXF  kind=%u id=%x type=%x decl=%u/%u cull3=%u/%u defer=%u/%u fog=%u/%u sphere=%u/%u res=%u/%u draw=%u/%u ml=%u mlcull=%u frame_us=%u lit_us=%u q_us=%u cls_us=%u def_us=%u\n",
                      r.key >> 16, (r.key >> 8) & 255, r.key & 255, r.n[0], r.us[0], r.n[1], r.us[1], r.n[2], r.us[2], r.n[3], r.us[3],
                      r.n[4], r.us[4], r.n[5], r.us[5], r.n[6], r.us[6], r.ml, r.mlc, r.pos_us, r.lit_us, r.q_us, r.cls_us, r.def_us);
        }
        nrows = 0; last = fr;
    }
    cur_key = p ? re4dc_propprof_key(p->model) : 0xffffffu; t0 = re4dc_otp_now_us();
}
void span(unsigned Row::*fld, unsigned long long& t) { const unsigned long long n = re4dc_otp_now_us(); if (Row* r = row()) r->*fld += unsigned(n - t); t = n; }
void exit_(unsigned e) { if (Row* r = row()) { r->n[e]++; r->us[e] += unsigned(re4dc_otp_now_us() - t0); } }
}
#define PXF_BEGIN(p) pxf::begin(p)
#define PXF_EXIT(e) pxf::exit_(pxf::e)
#define PXF_SPAN(fld, t) pxf::span(&pxf::Row::fld, t)
#else
#define PXF_SPAN(fld, t) do { } while (0)
#define PXF_BEGIN(p) do { } while (0)
#define PXF_EXIT(e) do { } while (0)
#endif
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
namespace {
#include "native_actor_chunk.inc"
}  // namespace
#endif
#if defined(RE4DC_RIGID_CHUNK) && RE4DC_RIGID_CHUNK
namespace {
#include "native_actor_rigid.inc"
}  // namespace
#endif
#if defined(RE4DC_RIGID_CENSUS) && RE4DC_RIGID_CENSUS == 2
extern "C" {
volatile unsigned re4dc_rigid_hide;     // dbgwarp_bridge.cpp `rigid <frame> on|off`
// per frame (the benchmark reads and clears it once a tick): parts, meshlets, vertices; the biggest part's model + verts
unsigned re4dc_rigid_census[6];
const void* re4dc_rigid_census_big;
void re4dc_rigid_census_note(const void* model, unsigned ml, unsigned nv, unsigned levels)
{
    ++re4dc_rigid_census[0]; re4dc_rigid_census[1] += ml; re4dc_rigid_census[2] += nv;
    if (nv > re4dc_rigid_census[3]) { re4dc_rigid_census[3] = nv; re4dc_rigid_census[4] = ml; re4dc_rigid_census[5] = levels; re4dc_rigid_census_big = model; }
}
}
#endif
#if RE4DC_ACTOR_BACKFACE_CONE
extern "C" unsigned re4dc_vi_retrace_count(void);
namespace {
// The census lines, every 300 vertical blanks (called per part draw; logic ticks stop under the warp's freeze).
void abc_census() {
    const unsigned frame_serial = re4dc_vi_retrace_count();
    if (frame_serial - abc_log >= 300U) {
        // per class (other, Leon, Ganado, El Gigante, Ashley): meshlets tested/rejected, vertices skipped/of tested parts,
        // triangles skipped; totals since the last line
        abc_log = frame_serial;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
        re4dc_log("AC32C frame=%u parts=%u/%u why=%u/%u/%u/%u/%u tested=%u reject=%u near=%u numeric=%u empty=%u split_skipped=%u\n",
            frame_serial,abc32_stats.admitted,abc32_stats.declined,abc32_stats.why[0],abc32_stats.why[1],
            abc32_stats.why[2],abc32_stats.why[3],abc32_stats.why[4],abc32_stats.tested,abc32_stats.rejected,
            abc32_stats.near,abc32_stats.numeric,abc32_stats.empty,abc32_stats.split_skipped);
#endif
        re4dc_log("ABFC frame=%u splits=%u built=%u noroom=%u cones=%u nocone=%u bad=%u marks=%u conv=%u/%u/%u parts=%u/%u unsplit=%u rec=%u/%u ml=%u/%u\n",
                  frame_serial, abc_splits, abc_built, abc_noroom, abc_cones, abc_nocone, abc_bad, abc_nmarks, abc_conv,
                  abc_conv_op, abc_conv_mk, abc_part_calls, abc_part_cull, abc_unsplit,
                  abc_rec_split, abc_rec_plain, abc_ml_split, abc_ml_plain);
        re4dc_log("ABFC2 frame=%u other=%u/%u/%u/%u/%u leon=%u/%u/%u/%u/%u ganado=%u/%u/%u/%u/%u gigante=%u/%u/%u/%u/%u "
                  "ashley=%u/%u/%u/%u/%u\n", frame_serial,
                  abc_tests[0], abc_rej[0], abc_vskip[0], abc_verts[0], abc_tskip[0],
                  abc_tests[1], abc_rej[1], abc_vskip[1], abc_verts[1], abc_tskip[1],
                  abc_tests[2], abc_rej[2], abc_vskip[2], abc_verts[2], abc_tskip[2],
                  abc_tests[3], abc_rej[3], abc_vskip[3], abc_verts[3], abc_tskip[3],
                  abc_tests[4], abc_rej[4], abc_vskip[4], abc_verts[4], abc_tskip[4]);
        for (unsigned c = 0; c < 5; ++c) abc_tests[c] = abc_rej[c] = abc_vskip[c] = abc_verts[c] = abc_tskip[c] = 0;
    }
}
}  // namespace
#endif
#if RE4DC_ACTOR_BACKFACE_CONE == 2
namespace {
// Check build: a rejected meshlet is transformed anyway (nothing is sent) and each triangle with every corner past near
// is tested with the TA's rule (room/backface_emit.hpp: area negated on odd strip triangles; cull 2 rejects >= 0,
// cull 1 <= 0). A triangle the ISP would draw counts in abc_bad.
void abc_verify(Part& e, const Records& r, unsigned nv, const PosConst& k, bool s16_uv, const u8* index, unsigned ni) {
    unsigned all, any;
    pass_positions(e, r, nv, k, s16_uv, all, any);
    if (all & kOcCull) return;
    const float sign = e.p.cull == 2 ? 1.0f : -1.0f;
    for (unsigned s0 = 0; s0 < ni;) {
        unsigned s1 = s0;
        while (s1 < ni && !(index[s1] & 128U)) ++s1;
        for (unsigned j = s0; j + 2 <= s1; ++j) {
            const unsigned a = index[j] & 127U, b = index[j + 1] & 127U, c = index[j + 2] & 127U;
            if ((e.cache.oc[a] | e.cache.oc[b] | e.cache.oc[c]) & kOcNear) continue;
            const pvr_vertex_t& A = e.cache.v[a]; const pvr_vertex_t& B = e.cache.v[b]; const pvr_vertex_t& C = e.cache.v[c];
            float area = (B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x);
            if ((j - s0) & 1U) area = -area;
            if (sign * area < 0.0f) ++abc_bad;
        }
        s0 = s1 + 1;
    }
}
}  // namespace
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
static int actor_submit_impl(const Re4dcModelPart* part,Frame* explicit_frame,NativeContinuationProgress* progress) {
#else
extern "C" int re4dc_actor_submit(const Re4dcModelPart* part) {
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::Scope dsa_part(re4dc::dsa24::ModelList);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    const re4dc::dsa24::x28::ModelScope dsa28_model(part ? part->model : nullptr);
#endif
    re4dc::dsa24::count(re4dc::dsa24::Parts);
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::motion_model_reason());
#endif
    ++stats.parts;
    PXF_BEGIN(part);
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
    re4dc_callprof_part(part ? part->model : nullptr, 0);
#endif
#if defined(RE4DC_ACC_CROWD_TIER) && RE4DC_ACC_CROWD_TIER
    // ACC_CROWD_TIER=N (crowd.mk, render only): a Ganado's hanging accessory is not drawn while that Ganado's crowd
    // tier this frame is >= N (2 mid, 3 far). Game state is untouched (the accessory still moves and renders on the
    // source side); only its native draw is skipped, counted as a culled part.
    if constexpr (kCrowd) {
        if (part) {
            if (const void* oya = re4dc_actor_accessory_parent(part->model)) {
                for (unsigned i = 0; i < crowd_count; ++i)
                    if (crowd[i].model == oya) {
                        if (crowd[i].tier >= unsigned(RE4DC_ACC_CROWD_TIER)) {
                            ++stats.culled_parts; re4dc_model_result(0, 0, 0); return 1;
                        }
                        break;
                    }
            }
        }
    }
#endif
#if RE4DC_ACTOR_CENSUS
    census_cur = nullptr; census_mat_row = nullptr;
    if (part) census_note(*part);
#if RE4DC_ACTOR_CENSUS_SKIP_OBJ00
    // Diagnostic A/B only: cObj00 room objects (id 0, ot 0, one part) are not drawn.
    if (part && re4dc_actor_census_key(part->model) == 0x00010000U) { re4dc_model_result(0, 0, 0); return 1; }
#endif
#endif
#if defined(RE4DC_ACTOR_REPLAY_SKIN) && RE4DC_ACTOR_REPLAY_SKIN
    // ACTOR_REPLAY_SKIN: a GX list of padding only (no primitive; the converter rejects it: no strips) draws nothing
    // on any path. Consumed here as drawn-nothing, so the generic walker does not accept it (h2: the room model's
    // empty 32-byte lists replayed after the codec screen took the generic path, which carries no member proof, and
    // the re-registered palette of their info was then materialized for the generic walker).
    if (part && part->stream && part->stream_bytes >= 32 && part->stream_bytes <= 256 && ram(part->stream, part->stream_bytes)) {
        unsigned any = 0;
        for (unsigned i = 0; i < part->stream_bytes; ++i) any |= part->stream[i];
        if (!any) { ++stats.culled_parts; re4dc_model_result(0, 0, 0); return 1; }
    }
#endif
    if (!part || !qualifies(*part
#if RE4DC_NATIVE_FE_CONTINUATION
        ,explicit_frame!=nullptr
#endif
    )) { DFA26_MODEL_HIT(ActorQualify, 1) ++stats.declined; RE4DC_CENSUS_DEC(part); PXF_EXIT(kDecl); return 0; }
    const Re4dcModelPart& p = *part;
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::ActorMainSourceScope gcasset_main_scope(&p);
#endif
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
    // Generic/source replay may occur after the transaction scope ended.
    // Re-establish its actual actor identity for every subsequent SQ burst.
    const unsigned bf_tag=re4dc_backface_model_tag(p.model);
    RE4DC_BFC_SCOPE(bf_tag?bf_tag>>8:unsigned(re4dc_bfc_class),bf_tag?bf_tag&255u:unsigned(re4dc_bfc_id));
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    unsigned long long pxt = pxf::t0;
    PXF_SPAN(q_us, pxt);
#endif
    G1PC_PART(p, false);
    const float near_distance = p.projection[6] / (p.projection[5] - 1.0f);
    const float far_distance = p.projection[6] / p.projection[5];
    if (!re4dc::render::is_finite(near_distance) || !re4dc::render::is_finite(far_distance) ||
        near_distance <= 0.0f || far_distance <= near_distance) { DFA26_MODEL_HIT(ActorProjection, 1) ++stats.declined; RE4DC_CENSUS_DEC(part); PXF_EXIT(kDecl); return 0; }
    const unsigned mark = workspace_top;
    struct Release { unsigned mark; ~Release() { workspace_top = mark; } } release{mark};
    const BlobHeader* blob = blob_of(p);
    int crowd_class = 0;
    if constexpr (kCrowd) crowd_class = re4dc_actor_model_class(p.model, p.info);
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    PXF_SPAN(cls_us, pxt);
#endif
    if (kLodBuild && blob && (blob->flags & kLodPending)) relod(p, crowd_class > 0);
    if (!blob && !(blob = convert(p))) { DFA26_MODEL_HIT(ActorConvert, 1) ++stats.declined; RE4DC_CENSUS_DEC(part); PXF_EXIT(kDecl); return 0; }
    const u8* base = reinterpret_cast<const u8*>(blob);
    ++stats.handled;
#if RE4DC_NATIVE_FE_CONTINUATION
    if(progress)progress->result.outcome=re4dc::NativeDrawOutcome::Culled;
#endif
    if (p.cull == 3) { re4dc_model_result(0, 0, 0); PXF_EXIT(kCull3); return 1; }
    // Translucent parts keep the existing bounded drain; its replay re-enters
    // re4dc_model_submit and lands here again with draining set.
    if (
#if RE4DC_NATIVE_FE_CONTINUATION
        !progress &&
#endif
        re4dc_model_defer_part(&p)) { ++stats.deferred; PXF_EXIT(kDefer); return 1; }
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    PXF_SPAN(def_us, pxt);
#endif

    Frame& f =
#if RE4DC_NATIVE_FE_CONTINUATION
        explicit_frame?*explicit_frame:
#endif
        *prepare_frame(p, near_distance, far_distance);
#if defined(RE4DC_RIGID_CENSUS) && RE4DC_RIGID_CENSUS == 2
    // RIGID_CENSUS=2 (benchmark census discs, lane cache20): every rigid part is counted (re4dc_rigid_census: parts,
    // meshlets, vertices of the parts that reached here this frame; the biggest part's model) and is not drawn only while
    // the run-time switch re4dc_rigid_hide is set (the warp line `rigid <frame> off`). Logic is not touched.
    if (f.mode != kSkin) {
        unsigned nv = 0;
        const auto* tb = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
        for (unsigned i = 0; i < blob->meshlets; ++i) nv += tb[i].n.vertices();
        re4dc_rigid_census_note(p.model, blob->meshlets, nv, blob->levels);
        if (re4dc_rigid_hide) { re4dc_model_result(0, 0, 0); return 1; }
    }
#elif defined(RE4DC_RIGID_CENSUS) && RE4DC_RIGID_CENSUS
    if (f.mode != kSkin) {
        static unsigned rgc_parts, rgc_ml, rgc_nv, rgc_log;
        ++rgc_parts; rgc_ml += blob->meshlets;
        const auto* tb = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
        for (unsigned i = 0; i < blob->meshlets; ++i) rgc_nv += tb[i].n.vertices();
        if (frame_serial - rgc_log >= 600U) {
            re4dc_log("RGC frame=%u parts=%u meshlets=%u verts=%u\n", frame_serial, rgc_parts, rgc_ml, rgc_nv);
            rgc_log = frame_serial; rgc_parts = rgc_ml = rgc_nv = 0;
        }
        re4dc_model_result(0, 0, 0); return 1;
    }
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    PXF_SPAN(pos_us, pxt);
    if (pxf::Row* pr = pxf::row()) pr->ml += f.mode == kSkin ? 1000000u : 0u;
#endif
#if RE4DC_ACTOR_FOG_GATE
    if (blob->radius > 0.0f || blob->center[0] != 0.0f || blob->center[1] != 0.0f || blob->center[2] != 0.0f) {
        const float cull_far = fog_gate_depth(near_distance, far_distance);
        const float* m = p.modelview; const float* c = blob->center;
        float depth = -1.0f;  // least view depth (-z) of the part's drawn vertices, if known
        if (f.mode != kSkin) {
            depth = -(m[8] * c[0] + m[9] * c[1] + m[10] * c[2] + m[11]) -
                    std::sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10]) * blob->radius;
        } else if (f.palette && f.palette_entries) {
            if (!f.gate_ready) {
                const float mz = std::sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10]);
                float T = 3.0e38f, G = 0.0f;
#if RE4DC_AVK
                // ACTOR_VTX_KERNEL: the same T and G with one square root after the loop (mz * sqrt(s)
                // does not decrease as s grows, so the largest s gives the largest product; a NaN or
                // 0 x inf product is dropped by std::max in both forms) and the palette lines
                // prefetched three entries ahead (the loop reads each entry once per frame).
                // The three column sums are written out (the same expression per column, so the same
                // contraction) and folded into S directly: max(S, max(max(max(0, s0), s1), s2)) =
                // max(max(max(S, s0), s1), s2) for S >= 0, NaN skipped either way; m's row in locals.
                {
                    float S = 0.0f;
#if defined(__sh__)
                    // Rev 5: the loop below as rev 4 compiled it, operation for operation (d = fmac(m10,
                    // P11, fmac(m8, P9, P10 x m9)) + m11; s0 = fmac(P2, P2, fmac(P0, P0, P1 x P1), s1 and
                    // s2 likewise; T and S by fcmp/gt in the same order), hand-scheduled on the issue model
                    // (33 model cycles an entry; vl23 as compiled: 61 measured, 46 of them issue: ten
                    // pointers, T through the integer registers, a taken branch per compare). One pointer
                    // per column (post-increment + @(r0,Rn) with r0 = 4, so each fmac's multiplier loads
                    // straight into fr0); T is kept negated (T' = -T: T > d exactly when y > T' for
                    // y = -d, NaN and signed zeros included; T = -T' after the loop, exact); the rare
                    // updates run out of line.
                    alignas(8) float io[6] = {m[8], m[9], m[10], m[11], -3.0e38f, 0.0f};
                    const float* pa = f.palette;
                    const float* pb = pa + 3;
                    const float* pc = pa + 6;
                    const float* pd = pa + 9;
                    const float* px = pa + 36;  // prefetch: entry k+3 (both of its lines)
                    unsigned n = f.palette_entries;
                    float* iop = io;
                    __asm__ __volatile__(
                        "mov     #4,r0\n\t"
                        "fmov.s  @%[io]+,fr12\n\t"  /* m8 */
                        "fmov.s  @%[io]+,fr13\n\t"  /* m9 */
                        "fmov.s  @%[io]+,fr14\n\t"  /* m10 */
                        "fmov.s  @%[io]+,fr15\n\t"  /* m11 */
                        "fmov.s  @%[io]+,fr10\n\t"  /* T' */
                        "fmov.s  @%[io]+,fr11\n"    /* S */
                        "1:\n\t"
                        "fmov.s  @(r0,%[d]),fr4\n\t"  /* P10 */
                        "fmov.s  @%[d]+,fr0\n\t"      /* P9 */
                        "fmul    fr13,fr4\n\t"
                        "fmov.s  @(r0,%[a]),fr9\n\t"  /* P1 */
                        "fmov.s  @(r0,%[b]),fr8\n\t"  /* P4 */
                        "fmul    fr9,fr9\n\t"
                        "fmov.s  @(r0,%[c]),fr6\n\t"  /* P7 */
                        "fmac    fr0,fr12,fr4\n\t"
                        "fmov.s  @(r0,%[d]),fr0\n\t"  /* P11 */
                        "fmul    fr8,fr8\n\t"
                        "pref    @%[x]\n\t"
                        "fmul    fr6,fr6\n\t"
                        "add     #44,%[x]\n\t"
                        "fmac    fr0,fr14,fr4\n\t"
                        "fmov.s  @%[a]+,fr0\n\t"      /* P0 */
                        "pref    @%[x]\n\t"
                        "add     #44,%[d]\n\t"
                        "fmac    fr0,fr0,fr9\n\t"
                        "fmov.s  @(r0,%[a]),fr0\n\t"  /* P2 */
                        "fadd    fr15,fr4\n\t"         /* y = -d */
                        "add     #44,%[a]\n\t"
                        "add     #4,%[x]\n\t"
                        "fmac    fr0,fr0,fr9\n\t"      /* s0 */
                        "fmov.s  @%[b]+,fr0\n\t"      /* P3 */
                        "fmac    fr0,fr0,fr8\n\t"
                        "fmov.s  @(r0,%[b]),fr0\n\t"  /* P5 */
                        "fcmp/gt fr11,fr9\n\t"
                        "add     #44,%[b]\n\t"
                        "fmac    fr0,fr0,fr8\n\t"      /* s1 */
                        "fmov.s  @%[c]+,fr0\n\t"      /* P6 */
                        "bt      2f\n"
                        "6:\n\t"
                        "fmac    fr0,fr0,fr6\n\t"
                        "fmov.s  @(r0,%[c]),fr0\n\t"  /* P8 */
                        "fcmp/gt fr11,fr8\n\t"
                        "add     #44,%[c]\n\t"
                        "fmac    fr0,fr0,fr6\n\t"      /* s2 */
                        "bt      3f\n"
                        "7:\n\t"
                        "fcmp/gt fr11,fr6\n\t"
                        "bt      4f\n"
                        "8:\n\t"
                        "fcmp/gt fr10,fr4\n\t"
                        "bt      5f\n"
                        "9:\n\t"
                        "dt      %[n]\n\t"
                        "bf      1b\n\t"
                        "bra     0f\n\t"
                        "nop\n"
                        "2:\n\t"
                        "bra     6b\n\t"
                        "fmov    fr9,fr11\n"
                        "3:\n\t"
                        "bra     7b\n\t"
                        "fmov    fr8,fr11\n"
                        "4:\n\t"
                        "bra     8b\n\t"
                        "fmov    fr6,fr11\n"
                        "5:\n\t"
                        "bra     9b\n\t"
                        "fmov    fr4,fr10\n"
                        "0:\n\t"
                        "fmov.s  fr11,@-%[io]\n\t"
                        "fmov.s  fr10,@-%[io]\n"
                        : [a] "+r"(pa), [b] "+r"(pb), [c] "+r"(pc), [d] "+r"(pd), [x] "+r"(px), [n] "+r"(n),
                          [io] "+r"(iop)
                        :
                        : "r0", "fr0", "fr4", "fr6", "fr8", "fr9", "fr10", "fr11", "fr12", "fr13", "fr14", "fr15", "t",
                          "memory");
                    T = -io[4]; S = io[5];
#else
                    const float m8 = m[8], m9 = m[9], m10 = m[10], m11 = m[11];
                    const float* P = f.palette;
                    for (unsigned i = f.palette_entries; i; --i, P += 12) {
                        __builtin_prefetch(P + 36);
                        __builtin_prefetch(P + 47);
                        const float d = -(m8 * P[9] + m9 * P[10] + m10 * P[11] + m11);
                        const float s0 = P[0] * P[0] + P[1] * P[1] + P[2] * P[2];
                        const float s1 = P[3] * P[3] + P[4] * P[4] + P[5] * P[5];
                        const float s2 = P[6] * P[6] + P[7] * P[7] + P[8] * P[8];
                        T = std::min(T, d);
                        S = std::max(S, s0); S = std::max(S, s1); S = std::max(S, s2);
                    }
#endif
                    G = std::max(G, mz * std::sqrt(S));
                }
#if RE4DC_AVK == 2
                {
                    float T2 = 3.0e38f, G2 = 0.0f;
                    for (unsigned i = 0; i < f.palette_entries; ++i) {
                        const float* P = f.palette + i * 12;
                        const float d = -(m[8] * P[9] + m[9] * P[10] + m[10] * P[11] + m[11]);
                        float s = 0.0f;
                        for (unsigned k = 0; k < 3; ++k)
                            s = std::max(s, P[k * 3] * P[k * 3] + P[k * 3 + 1] * P[k * 3 + 1] + P[k * 3 + 2] * P[k * 3 + 2]);
                        T2 = std::min(T2, d); G2 = std::max(G2, mz * std::sqrt(s));
                    }
                    avk_gate_check(T, G, T2, G2);
                }
#endif
#else
                for (unsigned i = 0; i < f.palette_entries; ++i) {
                    const float* P = f.palette + i * 12;  // columns R0, R1, R2, t
                    const float d = -(m[8] * P[9] + m[9] * P[10] + m[10] * P[11] + m[11]);
                    float s = 0.0f;
                    for (unsigned k = 0; k < 3; ++k)
                        s = std::max(s, P[k * 3] * P[k * 3] + P[k * 3 + 1] * P[k * 3 + 1] + P[k * 3 + 2] * P[k * 3 + 2]);
                    T = std::min(T, d); G = std::max(G, mz * std::sqrt(s));
                }
#endif
                f.gate_ready = true; f.gate_T = T; f.gate_G = G;
            }
            depth = f.gate_T - f.gate_G * (std::sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]) + blob->radius);
        }
        ++fog_gate_tests;
        if (frame_serial - fog_gate_log >= 600U) {
            fog_gate_log = frame_serial;
            re4dc_log("native actor fog gate: frame=%u tests=%u culled=%u far=%.0f\n", frame_serial, fog_gate_tests,
                      fog_gate_culled, cull_far);
        }
        if (depth > cull_far) {
#if defined(RE4DC_PROP_GATE) && RE4DC_PROP_GATE == 2
            if (re4dc_pg_expect) ++re4dc_pg_fogged;
#endif
            ++fog_gate_culled; re4dc_model_result(0, 0, 0); PXF_EXIT(kFog); return 1;
        }
    }
#endif
    if (f.mode == kRigid && blob->radius > 0.0f) {
        // Whole-part depth test of the bind-pose sphere (bind == drawn pose).
        const float* m = p.modelview; const float* c = blob->center;
        const float z = m[8] * c[0] + m[9] * c[1] + m[10] * c[2] + m[11];
        if (-z + blob->radius < near_distance || -z - blob->radius > far_distance) {
            ++stats.culled_parts; re4dc_model_result(0, 0, 0); PXF_EXIT(kSphere); return 1;
        }
    }
#if defined(RE4DC_RIGID_CHUNK) && RE4DC_RIGID_CHUNK
    // RIGID_CHUNK: the size rule (native_actor_rigid.inc).
    const bool rigid = f.mode == kRigid;
    const float rigid_px = rigid ? rigid_pixels(p, *blob, near_distance) : 1.0e9f;
    if (rigid) {
        rigid_log();
        ++rigid_stats.parts;
        if (rigid_px < RE4DC_RIGID_CULL_PX) {
            ++rigid_stats.culled; ++stats.culled_parts; re4dc_model_result(0, 0, 0); PXF_EXIT(kSphere); return 1;
        }
    }
    const bool rigid_flat = rigid && rigid_px < RE4DC_RIGID_FLAT_PX;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (rigid && !rigid_flat) re4dc::dfa26::hit(re4dc::dfa26::ActorRigidFull);
#endif
#endif
    Part e{p, f, {p.projection, p.viewport}, {near_distance, far_distance, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF, project, nullptr}};
    e.clip.context = &e.projection;
#if RE4DC_NATIVE_FE_CONTINUATION
    e.continuation=progress;
#endif
    e.streaming = re4dc_model_packet_streaming() != 0;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    if (!re4dc_model_packet_reserve(&p, &e.packet)) {
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
            RE4DC_DROP_ACTOR(&p, 0, 0);
#if RE4DC_NATIVE_FE_CONTINUATION
            native_refused(progress);
#endif
            re4dc_model_result(2, 0, 0); PXF_EXIT(kRes); return 1; }
#else
    if (!re4dc_model_packet_reserve(&p, &e.packet)) { RE4DC_DROP_ACTOR(&p, 0, 0);
#if RE4DC_NATIVE_FE_CONTINUATION
            native_refused(progress);
#endif
            re4dc_model_result(2, 0, 0); PXF_EXIT(kRes); return 1; }
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    const unsigned uv32_certificate = uv32::checked_certificate(p, *blob);
    re4dc_model_uv16_request32(uv32_certificate);
#else
#if RE4DC_ACTOR_UV16
    // Consumed by the begin call below (direct or packet), whatever its result.
    e.uv16 = uv16_safe(p, *blob);
    if (e.uv16) ++stats.uv16_parts;
    const u32 pcw_set = kPcwStripLength6 | (e.uv16 ? kPcwUv16 : 0U), pcw_clear = kPcwStripLength6 | kPcwUv16;
    re4dc_model_next_header_pcw(pcw_set, pcw_clear);
#endif
#endif
#if RE4DC_ACTOR_DIRECT
    Re4dcModelDirect direct{};
    if (re4dc_model_direct_enabled() && re4dc_model_direct_begin(&p, &direct)) {
#if RE4DC_NATIVE_FE_CONTINUATION
        if(progress)progress->header=true;
#endif
        if (direct.scratch_capacity < kCacheSlots) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
#endif
            // Nothing sent yet beyond the header: an empty part.
            re4dc_model_direct_end(0); RE4DC_DROP_ACTOR(&p, 'd', 0);
#if RE4DC_NATIVE_FE_CONTINUATION
            native_refused(progress);
#endif
            re4dc_model_result(2, 0, 0); return 1;
        }
        e.direct = true; e.sq = direct.sq;
        e.packet.u_scale = direct.u_scale; e.packet.v_scale = direct.v_scale;
        e.cache.v = static_cast<pvr_vertex_t*>(direct.scratch);
    } else
#endif
    {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
        re4dc_model_uv16_request32(uv32_certificate);
#else
#if RE4DC_ACTOR_UV16
        re4dc_model_next_header_pcw(pcw_set, pcw_clear);
#endif
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
        DFA26_MODEL_HIT(ActorPacketPath, 1)
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
        const bool packet_begun=re4dc_model_packet_begin(&p,&e.packet)!=0;
        if(progress && packet_begun)progress->header=true;
        if (!packet_begun || e.packet.capacity < kCacheSlots + 64U) {
#else
        if (!re4dc_model_packet_begin(&p, &e.packet) || e.packet.capacity < kCacheSlots + 64U) {
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
#endif
            RE4DC_DROP_ACTOR(&p, 0, e.packet.capacity);
#if RE4DC_NATIVE_FE_CONTINUATION
            native_refused(progress);
#endif
            re4dc_model_result(2, 0, 0);
            return 1;
        }
        e.packet.capacity -= kCacheSlots;
        e.cache.v = static_cast<pvr_vertex_t*>(e.packet.vertices) + e.packet.capacity;
    }
    e.cache.oc = reinterpret_cast<u8*>(e.cache.v + kMaxVertices);
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    const unsigned uv32_reason = re4dc_model_uv16_result32();
    e.uv16 = uv32_reason == re4dc::format32::Uv16;
    if (e.uv16) ++stats.uv16_parts;
#if RE4DC_ACTOR_DIRECT
    uv32::counters.note(uv32_reason, e.direct ? 1U : 0U);
#else
    uv32::counters.note(uv32_reason, 0U);
#endif
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (!e.uv16) re4dc::dfa26::hit(re4dc::dfa26::ActorUv32);
#endif

#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    const unsigned long long pxf_l0 = re4dc_otp_now_us();
#endif
#if RE4DC_NATIVE_FE_CONTINUATION
    if(progress && !native_pose_of(p)) {
        native_refused(progress);
#if RE4DC_ACTOR_DIRECT
        if(e.direct)re4dc_model_direct_end(0);
#endif
        return 1;
    }
#endif
    Lights lights;
    G1PC_LIGHT(p, f, blob->center);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    B28_NOTE(p, fast_only_lights(p, f, blob->center, lights));
#else
    if (!B28_NOTE(p, RE4DC_PART_LIGHTS(p, f, blob->center, lights))) {
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
        if (!lights.exact_ready)
#endif
        RE4DC_PREPARED(lights) = re4dc::render::prepare_actor_lights(*p.lighting);
        RE4DC_CAP_EXACT(p, blob->center, lights);
    }
#endif
#if !RE4DC_ACTOR_SETUP_LEAN
    lights.source = p.lighting;
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
    if (pxf::Row* r = pxf::row()) r->lit_us += unsigned(re4dc_otp_now_us() - pxf_l0);
#endif
    const unsigned tier = crowd_class > 0 ? crowd_tier(p, crowd_class) : kTierFull;
    if (tier >= (kCrowdFlat ? kTierNear : kTierMid) && tier != kTierFull && lights.fast && !lights.constant
#if RE4DC_ACTOR_PROBE_LIGHT
        && !(lights.probe && tier == kTierNear && RE4DC_GANADO_VERTEX_LIT(p))  // ACTOR_PROBE_LIGHT=2: the near tier lights per vertex
#endif
    ) {
        lights.constant = true;
        lights.constant_rgb = part_colour(lights);
    }
#if defined(RE4DC_RIGID_CHUNK) && RE4DC_RIGID_CHUNK
    if (rigid_flat && lights.fast && !lights.constant) {
        ++rigid_stats.flat;
        lights.constant = true;
        lights.constant_rgb = part_colour(lights);
    }
#endif
#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29 && !RE4DC_ACTOR_LIGHT_FAST_ONLY
    // The offline per-record colours supersede the crowd/rigid flat-colour approximation.
    if (lights.scan29_bake) lights.constant = false;
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    fa29_actor_note(p,lights);
#endif
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    re4dc::dsa24::x28::light(dsa28_light_path(lights), lights.count);
#endif
    // Skinned directions follow the part's light fold; parts of one info whose
    // folds agree within kDirTolerance of the largest direction (light
    // directions from nearby part centres) keep the entries already built.
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
    if (f.skin_dirs && !lights.constant) {
        float dmax = 0.0f;
        for (unsigned i = 0; i < 12; ++i) dmax = std::max(dmax, std::fabs(lights.dir[i / 4][i % 4]));
        if (!near_vec(&lights.dir[0][0], f.dirs_fold, 12, dmax * kDirTolerance)) {
            std::memset(f.dirs_ready, 0, f.palette_entries);
            std::memcpy(f.dirs_fold, &lights.dir[0][0], sizeof(f.dirs_fold));
            ++stats.skin_dir_sets;
#if RE4DC_ACTOR_PROBE_LIGHT
            if (lights.probe && f.palette) probe_dirs_all(f, lights);
#endif
        }
    }
#endif
    const bool s16_uv = (p.flags & 0x80000000U) != 0;
    const float uv_scale = s16_uv ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const PosConst k{0.0f, uv_scale * e.packet.u_scale, p.uv_offset[0] * e.packet.u_scale,
                     uv_scale * e.packet.v_scale, p.uv_offset[1] * e.packet.v_scale, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF,
                     near_distance, far_distance};
    e.colors = (p.alpha_state & 256) ? p.colors : nullptr;
    e.alpha = u32(p.alpha_state & 255) << 24;
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA && !RE4DC_ACTOR_LIGHT_FAST_ONLY
    const bool retain_flat = lights.constant && !e.colors;
    u32 flat_argb = 0;
    if (retain_flat) {
        flat_argb = e.alpha | lights.constant_rgb;
#if RE4DC_LEON_LIGHT_HEADROOM
        if (lights.half_post)
            flat_argb = (flat_argb & 0xFF000000U) | ((flat_argb >> 1) & 0x007F7F7FU);
#endif
    }
#endif
    const auto* table = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
    const unsigned rs = 3U + ((blob->flags & kHasCi) ? 1U : 0U) + ((blob->flags & kHasBake) ? 1U : 0U);
    const unsigned color_index = blob->color_index;
    unsigned level = tier == kTierFar ? blob->levels
                     : select_level(p, *blob, near_distance, tier == kTierMid ? crowd_mid_tau : RE4DC_NEAR_LOD_TAU);
#if defined(RE4DC_RIGID_CHUNK) && RE4DC_RIGID_CHUNK
    if (rigid_flat) level = blob->levels;
#endif
    const LevelInfo* li = level ? reinterpret_cast<const LevelInfo*>(base + blob->lod4 * 4U) + (level - 1) : nullptr;
    const MeshletLevel* lt = li ? reinterpret_cast<const MeshletLevel*>(base + li->table4 * 4U) : nullptr;
    const u8* lists = li ? base + li->lists4 * 4U : base + blob->idx4 * 4U;
    const u8* records = base + blob->rec4 * 4U;
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    constexpr BakeUse bake = kBakeNone;
#else
    unsigned bake_scale[3];
    const BakeUse bake = kPrelit && (blob->flags & kHasBake) && blob->bake4 && lights.fast && !lights.constant && !e.colors
        ? bake_prepare(e, lights, *blob, rs, bake_scale) : kBakeNone;
#endif
    ++stats.lod_draws[level];
    if (kCrowd) ++stats.crowd_parts[tier];
    bool ok = true;
#if RE4DC_ACTOR_BACKFACE_CONE
    unsigned abc_cls;
    const AbcCone* abc = abc_part(p, base, f, abc_cls);
    abc_census();
    AbcEye abc_e;
#endif
    for (unsigned mi = 0; ok && mi < blob->meshlets; ++mi) {
#if RE4DC_NATIVE_FE_CONTINUATION
        if(progress && !native_pose_of(p)){ok=false;break;}
#endif
        const MeshletInfo& m = table[mi];
        const Counts c = lt ? lt[mi].n : m.n;
        const unsigned nv = c.vertices(), ni = c.indices(), nt = c.triangles();
        if (!ni) continue;  // wholly collapsed at this level
        const Records r{reinterpret_cast<const u16*>(records) + m.first * rs, rs, color_index, (blob->flags & kHasCi) != 0};
        const u8* index = lists + (lt ? lt[mi].index : m.index);
        ++stats.meshlets; stats.vertices += nv; stats.corners += ni; stats.triangles += nt;
        if (kCrowd) stats.crowd_triangles[tier] += nt;
#if RE4DC_ACTOR_BACKFACE_CONE
        if (abc) {
            ++abc_tests[abc_cls]; abc_verts[abc_cls] += nv;
            const AbcCone& cn = abc[mi];
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
            if (!cn.k) ++abc32_stats.empty;
#endif
            if (cn.k && abc_eye(f, p.cull, cn.pal, abc_e) && abc_reject(cn, abc_e)) {
                ++abc_rej[abc_cls]; abc_vskip[abc_cls] += nv; abc_tskip[abc_cls] += nt;
#if RE4DC_ACTOR_BACKFACE_CONE == 2
                abc_verify(e, r, nv, k, s16_uv, index, ni);
#endif
                e.input += nt;
                continue;
            }
        }
#endif
#if RE4DC_ACTOR_CENSUS
        if (census_cur) { census_cur->nv += nv; census_cur->nt += nt; census_cur->lvl += level; }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#if RE4DC_ACTOR_BACKFACE_CONE
        if (!abc || !abc[mi].k) re4dc::dfa26::hit(re4dc::dfa26::ActorConeUnavailable);
#else
        re4dc::dfa26::hit(re4dc::dfa26::ActorConeUnavailable);
#endif
#endif
#if RE4DC_ACTOR_CLIP_FRONT26
        e.clip_vertices = nv;
#endif
        unsigned all, any;
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
        chunk_positions(e, r, nv, k, s16_uv, all, any);
#else
        pass_positions(e, r, nv, k, s16_uv, all, any);
#endif
#if defined(RE4DC_PROP_PROF) && RE4DC_PROP_PROF
        if (pxf::Row* pr = pxf::row()) { pr->ml++; if (all & kOcCull) pr->mlc++; }
#endif
        if (all & kOcCull) {
#if RE4DC_ACTOR_CENSUS
            if (census_cur) census_cur->culled += nv;
#endif
            ++stats.meshlets_culled;
            e.input += nt;
            continue;
        }
        e.prime(nv);
        if (e.uv16) pack_uv16(e.cache.v, nv, true);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
        pass_fast_only(e, lights, r, nv);
#else
        if (lights.constant) {
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
            if (e.colors) re4dc::dfa26::hit(re4dc::dfa26::ActorFlatRewrite, nv);
#else
            re4dc::dfa26::hit(re4dc::dfa26::ActorFlatRewrite, nv);
#endif
#endif
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
            if (!e.colors) e.flat_colors(nv, flat_argb);
            else
#else
#if RE4DC_AVK
            // ACTOR_VTX_KERNEL: without per-vertex alpha every vertex gets the same word; one store each
            // (the loop below reloads e.colors after every store: the stores may alias it).
            if (!e.colors) {
                const u32 argb = e.alpha | lights.constant_rgb;
                pvr_vertex_t* v = e.cache.v;
                unsigned i = 0;
                for (; i + 4 <= nv; i += 4, v += 4) {
                    v[0].argb = argb; v[1].argb = argb; v[2].argb = argb; v[3].argb = argb;
                }
                for (; i < nv; ++i, ++v) v->argb = argb;
            } else
#endif
#endif
            for (unsigned i = 0; i < nv; ++i)
                e.cache.v[i].argb = (e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha) | lights.constant_rgb;
        } else if (bake != kBakeNone) {
            pass_baked(e, r, nv, bake == kBakeScaled ? bake_scale : nullptr);
        } else if (lights.fast) {
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
            chunk_lights(e, lights, r, nv);
#else
            pass_lights(e, lights, r, nv);
#endif
        } else {
            pass_lights_exact(e, lights, r, nv);
        }
#if RE4DC_LEON_LIGHT_TOGGLE
        // LEON_LIGHT_TOGGLE mode 1 (PROBE): test 10's 1.0x cap on the 2x textures (the pass ran at full scale)
        if (re4dc_leon_light_mode == 1 && !lights.constant && leon_record(*p.lighting))
            for (unsigned i = 0; i < nv; ++i) {
                const u32 c = e.cache.v[i].argb;
                e.cache.v[i].argb = (c & 0xFF000000U) | ((c >> 1) & 0x007F7F7FU);
            }
#endif
#if RE4DC_LEON_LIGHT_HEADROOM
        // LEON_LIGHT_HEADROOM: a 2x-texture part outside the owner path (build_lights half_post): the 1x look
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
        if (lights.half_post && !retain_flat)
#else
        if (lights.half_post)
#endif
            for (unsigned i = 0; i < nv; ++i) {
                const u32 c = e.cache.v[i].argb;
                e.cache.v[i].argb = (c & 0xFF000000U) | ((c >> 1) & 0x007F7F7FU);
            }
#endif
#endif

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
        if (bake == kBakeNone) stats.normals_lit += nv;
#endif
        if (any & kOcNear) ++stats.meshlets_clipped;
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
        {
            ChunkSink sink;
            chunk_sink_begin(sink, e);
            ok = chunk_sink_strips(sink, r, index, nv, ni, nt, any);
            chunk_sink_end(sink);
        }
#else
#if defined(RE4DC_RIGID_CHUNK) && RE4DC_RIGID_CHUNK
        if (rigid) { ok = rigid_strips(e, r, index, nv, ni, nt, any); continue; }
#endif
        if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; ok = e.whole(index, ni, nt); }
        else DFA26_MODEL_SLOW(ActorStripScan, 1, ok = e.strips(r, index, ni);)
#endif
    }
#if RE4DC_ACTOR_DIRECT
    if (e.direct) {
        if (!ok) re4dc_model_packet_abort();
        re4dc_model_direct_end(e.slots);
#if RE4DC_NATIVE_FE_CONTINUATION
        if(progress) {
            Re4dcActorStreamState state{};
            if(!ok || !re4dc_actor_stream_state(&state))native_refused(progress);
            else if(e.slots){progress->result.outcome=re4dc::NativeDrawOutcome::Submitted;progress->result.submitted=1;}
        }
#endif
        re4dc_model_result(ok ? 0 : 3, e.input, ok ? e.output : 0);
        PXF_EXIT(kDraw);
        return 1;
    }
#endif
    if (!ok) {
        if (e.committed) re4dc_model_packet_abort();
#if RE4DC_NATIVE_FE_CONTINUATION
        native_refused(progress);
#endif
        re4dc_model_result(3, e.input, 0);
        return 1;
    }
    re4dc_model_packet_commit(e.used);
#if RE4DC_NATIVE_FE_CONTINUATION
    if(progress) {
        if(e.used){++progress->result.submitted;progress->result.outcome=re4dc::NativeDrawOutcome::Submitted;}
        Re4dcActorStreamState state{};
        if(!re4dc_actor_stream_state(&state))native_refused(progress);
    }
#endif
    re4dc_model_result(0, e.input, e.output);
    PXF_EXIT(kDraw);
    return 1;
}

#if RE4DC_NATIVE_FE_CONTINUATION
extern "C" int re4dc_actor_submit(const Re4dcModelPart* part){return actor_submit_impl(part,nullptr,nullptr);}
#include "include/native_actor_continuation.inc"
#endif

#if RE4DC_COARSE_ONE_SUBMIT
// ------------------------------------------------- one submission per actor --
// COARSE_ONE_SUBMIT (game30.mk; render only): re4dc_actor_submit_chunks, the coarse adapters' chunks of one
// actor in one call. Each chunk takes re4dc_actor_submit's steps in its order (qualification, blob, crowd
// class, defer, Frame, fog gate, lights, level, meshlets, result) with the same state effects (frame cache
// slots and skin tables, crowd distances, the frame owner's results), but the chunks share one TA_DIRECT
// window: one reserve + texture bind + header + store-queue lock for the window instead of two reserves,
// a bind, a header and a lock for every chunk (the window's opener hands its reservation to
// re4dc_model_direct_begin_reserved, native_ui.cpp, which does not repeat it).
// The part's shared fields are the header inputs, so every chunk's header is the window's (=2 compares them)
// and the TA draws the same triangles in the same order. Inside an open window a chunk's reserve cannot
// fail (its inputs and the owner's state are the opener's: model_used stays 0 in the direct path, and only
// an abort, which closes the window, sets stream_aborted), so it is skipped. Also once per window:
// constant lighting (lighting disabled: build_lights' result is a function of the lighting record) and the
// cache priming (flags / oargb words, never written by the passes); once per repeated matrix set: the
// screen rows; once per repeated translation: crowd_tier (the same distance again changes nothing).
// =2 (check build): every chunk first goes through re4dc_actor_submit, and the TA words both paths emit
// (headers included) are compared chunk by chunk ("C3CHK" lines); the image draws each chunk twice.
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
#if !RE4DC_ACTOR_DIRECT || !RE4DC_NATIVE_ACTOR_SKIN_LAZY || (defined(RE4DC_TA_GUARD) && RE4DC_TA_GUARD)
#error "ACTOR_FORMAT32 coarse windows need DIRECT=1 SKIN_LAZY=1 TA_GUARD=0"
#endif
#else
#if !RE4DC_ACTOR_DIRECT || RE4DC_ACTOR_UV16 || !RE4DC_NATIVE_ACTOR_SKIN_LAZY || (defined(RE4DC_TA_GUARD) && RE4DC_TA_GUARD)
#error "COARSE_ONE_SUBMIT needs NATIVE_ACTOR_DIRECT=1 NATIVE_ACTOR_SKIN_LAZY=1 NATIVE_ACTOR_UV16=0 TA_GUARD=0 (a window is one guarded part)"
#endif
#endif
#if RE4DC_COARSE_GATE_ONCE && (!RE4DC_AVK || !RE4DC_ACTOR_FOG_GATE)
#error "COARSE_GATE_ONCE needs ACTOR_VTX_KERNEL=1 and ACTOR_FOG_GATE=1 (the kernel's fog gate loop)"
#endif
extern "C" void re4dc_log(const char* fmt, ...);
// native_ui.cpp (COARSE_ONE_SUBMIT): re4dc_model_direct_begin for a part the caller has just reserved.
extern "C" int re4dc_model_direct_begin_reserved(const Re4dcModelPart*, const Re4dcModelPacket*, Re4dcModelDirect*);
namespace {
// qualifies() for a part without arrays (positions == nullptr: its array term is lazy_skin()), keeping
// lazy_skin()'s registry entry and source for one_frame().
bool one_qualifies(const Re4dcModelPart& p, const SkinEntry*& se, Re4dcActorSource& src) {
#if RE4DC_ACTOR_SOURCE_SPAN
    if(p.source_span.owner_serial && !uv32::prepare_owned(p))return false;
#endif
    if (!(p.lighting && p.alpha_state <= 511 &&
          (!(p.alpha_state & 256) || ((p.flags & 0x80000000U) && p.colors)) &&
          ((!p.lighting->ambient_vertex && !p.lighting->material_vertex) || ((p.flags & 0x80000000U) && p.colors)) &&
          (!p.lighting->enable || p.lighting->attenuation == 1 || p.lighting->attenuation == 2) &&
          p.shift <= 30 && (p.position_stride == 6 || p.position_stride == 8) &&
          (p.normal_shift == 6 || p.normal_shift == 14) && p.normal_stride >= 3 &&
          p.position_count && p.normal_count && p.stream_bytes <= 1024 * 1024 && p.stream_bytes >= 32 &&
          ram(p.stream, p.stream_bytes) && p.uv &&
          p.projection[0] == 0 && p.viewport[2] > 0 && p.viewport[3] > 0))
        return false;
    if (p.positions || p.position_stride != 6) return false;
    se = find_skin(p.info, nullptr);
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    return skin_recipe_eligible(se) && re4dc_actor_model_source(p.info, &src) &&
#else
    return se && !se->materialized && se->palette && se->entries && re4dc_actor_model_source(p.info, &src) &&
#endif
           src.positions && src.normals && src.position_count == p.position_count &&
           src.normal_count == p.normal_count && bool(src.small_normals) == (p.normal_shift == 6);
}

// The screen rows of the last matrix set (screen_rows is a function of the three matrices' words).
struct OneScreen { bool valid = false; float modelview[12], projection[7], viewport[6], M[3][4]; };

#if RE4DC_COARSE_GATE_ONCE
// COARSE_GATE_ONCE: the fog gate's keep proof. The gate loop in one_chunk (re4dc_actor_submit's rev 5 loop) sets
// T = -max(-3e38, y_k) over the Frame's palette entries k, y_k = entry k's view z (a NaN y_k is skipped), and
// G = max(0, mz sqrt(S)) >= 0, and culls when T - G (|c| + r) > cull_far. For every entry k whose y_k is not NaN,
// T <= -y_k; with r >= 0, G (|c| + r) is >= 0 or NaN, so the depth is <= T (IEEE subtraction of a non-negative
// number rounds to <= T) or NaN, and neither culls. So -y_0 <= cull_far, y_0 being entry 0's z by the loop's own
// four instructions (the same bits), proves that the loop keeps the chunk, and the loop is skipped. The Frame
// records T = -y_0 and G = 0: a later submission of the same Frame (same info and matrices, this frame; the same
// blob and cull depth) decides keep again, as the loop's T and G would make it.
float gate_entry_z(const float* m, const float* P) {
    float y;
    const float* pm = m + 8;
    const float* pd = P + 9;
    __asm__(
        "mov     #4,r0\n\t"
        "fmov.s  @%[m]+,fr12\n\t"     /* m8 */
        "fmov.s  @%[m]+,fr13\n\t"     /* m9 */
        "fmov.s  @%[m]+,fr14\n\t"     /* m10 */
        "fmov.s  @%[m]+,fr15\n\t"     /* m11 */
        "fmov.s  @(r0,%[d]),fr4\n\t"  /* P10 */
        "fmov.s  @%[d]+,fr0\n\t"      /* P9 */
        "fmul    fr13,fr4\n\t"
        "fmac    fr0,fr12,fr4\n\t"
        "fmov.s  @(r0,%[d]),fr0\n\t"  /* P11 */
        "fmac    fr0,fr14,fr4\n\t"
        "fadd    fr15,fr4\n\t"         /* y = entry 0's z */
        "fmov    fr4,%[y]\n"
        : [m] "+r"(pm), [d] "+r"(pd), [y] "=f"(y)
        : "m"(*reinterpret_cast<const float(*)[12]>(m)), "m"(*reinterpret_cast<const float(*)[12]>(P))
        : "r0", "fr0", "fr4", "fr12", "fr13", "fr14", "fr15");
    return y;
}
#if RE4DC_COARSE_GATE_ONCE == 2
// =2 (check build): the proof is computed and counted, the gate loop still decides (proof_cull: chunks the loop culls
// that the proof kept, must stay 0).
struct GateOnceCheck {
    unsigned proofs, loops, proof_cull, log_frame;
} gate1_chk{};
#endif
#endif

// prepare_frame() for a part one_qualifies() accepted: its kSkin branch with lazy_skin()'s entry and source
// (re4dc_actor_skin_palette finds the same entry), the same cache search, victim, fields and skin table.
Frame& one_frame(const Re4dcModelPart& p, float near_distance, float far_distance, const SkinEntry& se,
                 const Re4dcActorSource& src, OneScreen& memo) {
    for (Frame& f : frames)
        if (f.frame == frame_serial && f.info == p.info &&
            same_words(f.modelview, p.modelview, 12) && same_words(f.projection, p.projection, 7) &&
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
            same_words(f.viewport, p.viewport, 6) && table14_current(f,p))
#else
            same_words(f.viewport, p.viewport, 6))
#endif
#if RE4DC_GC_ASSET_GATE
            {gcasset_frame_check(f);return f;}
#else
            return f;
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    DFA26_MODEL_HIT(ActorFramePrepare, 1)
#endif
    Frame& f = frames[frame_victim]; frame_victim = (frame_victim + 1) % kFrames;
    f = Frame{};
#if RE4DC_GC_ASSET_GATE
    gcasset_frame_stamp(f);
#endif
    f.info = p.info; f.frame = frame_serial;
    std::memcpy(f.modelview, p.modelview, sizeof(f.modelview));
    std::memcpy(f.projection, p.projection, sizeof(f.projection));
    std::memcpy(f.viewport, p.viewport, sizeof(f.viewport));
    f.near_distance = near_distance; f.far_distance = far_distance;
    f.q = pow2(-int(p.shift));
    f.position_count = p.position_count; f.normal_count = p.normal_count;
    f.small_normals = p.normal_shift == 6; f.nq = pow2(-int(p.normal_shift));
#if RE4DC_SKIN_PALETTE_LAZY
    re4dc_skin_palette_resolve(se.palette);  // the new skin Frame reads it (a source entry pending since Trans())
#endif
    f.mode = kSkin; f.palette = se.palette; f.palette_entries = se.entries;
    f.positions = src.positions; f.position_stride = 8;
    f.normals = src.normals; f.normal_stride = src.small_normals ? 4U : 8U;
#if defined(RE4DC_ACTOR_TABLE_REUSE14) && RE4DC_ACTOR_TABLE_REUSE14
    table14_prepare(f,p,se.entries);
#else
    for (Frame& o : frames)
        if (&o != &f && o.skin_positions) {
            o.frame = ~0U; o.skin_positions = o.skin_dirs = nullptr; o.skin_ready = o.dirs_ready = nullptr;
        }
    workspace_end = workspace_bytes;
#endif
    const unsigned entries = se.entries;
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    f.skin_positions = static_cast<float*>(frame_table(entries * (16U * 4U + 1U)));
    if (f.skin_positions) {
        f.skin_ready = reinterpret_cast<u8*>(f.skin_positions + entries * 16U);
        std::memset(f.skin_ready, 0, entries);
#else
    f.skin_positions = static_cast<float*>(frame_table(entries * (28U * 4U + 2U)));
    if (f.skin_positions) {
        f.skin_dirs = f.skin_positions + entries * 16U;
        f.skin_ready = reinterpret_cast<u8*>(f.skin_dirs + entries * 12U);
        f.dirs_ready = f.skin_ready + entries;
        std::memset(f.skin_ready, 0, entries * 2U);
#endif
#if RE4DC_AVK
        f.avk_all = false;
#endif
        f.dirs_fold[0] = NAN;  // no directions built yet
    }
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (!f.skin_positions) re4dc::dfa26::hit(re4dc::dfa26::ActorSkinTable);
#endif
    ++stats.skinned_parts;
    if (!memo.valid || !same_words(memo.modelview, p.modelview, 12) || !same_words(memo.projection, p.projection, 7) ||
        !same_words(memo.viewport, p.viewport, 6)) {
        screen_rows(p, memo.M);
        std::memcpy(memo.modelview, p.modelview, sizeof(memo.modelview));
        std::memcpy(memo.projection, p.projection, sizeof(memo.projection));
        std::memcpy(memo.viewport, p.viewport, sizeof(memo.viewport));
        memo.valid = true;
    }
    const float s = f.mode == kSkin ? 1.0f : f.q;
    for (unsigned c = 0; c < 4; ++c) {
        const float k = c < 3 ? s : 1.0f;
        f.screen[c * 4 + 0] = memo.M[0][c] * k; f.screen[c * 4 + 1] = memo.M[1][c] * k;
        f.screen[c * 4 + 2] = memo.M[2][c] * k; f.screen[c * 4 + 3] = memo.M[2][c] * k;
    }
    ++stats.info_preparations;
    return f;
}

struct OneWindow {
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    unsigned motion_accounted=0; // local only; chunks own their accepted records
#endif
    bool open = false;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    bool uv16 = false;
#endif
    Re4dcModelDirect direct{};
    std::uint32_t* sq = nullptr;
    unsigned slots = 0, primed = 0;  // the window's slots so far; cache entries whose flags / oargb are primed
    bool lights_ready = false;       // lights: build_lights' result for a lighting-disabled record
    Lights lights, lit;              // lit: a lit chunk's own (built per chunk, as re4dc_actor_submit does)
    const void* tier_model = nullptr;  // crowd_tier memo: the last call's model, class, translation and result
    int tier_class = 0;
    u32 tier_t[3]{};
    unsigned tier = 0;
    OneScreen screen;
};
void one_close(OneWindow& w) {
    if (!w.open) return;
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    if(w.motion_accounted)re4dc_gcasset::motion_pending_accounted();
    w.motion_accounted=0;
#endif
    re4dc_model_direct_end(w.slots);
    w.open = false; w.slots = 0; w.primed = 0;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    w.uv16 = false;
#endif
}

// re4dc_actor_submit() for one chunk, sent into the window (opened here when closed): 1 / 0 as that call
// would return; -1 when the part is not an array-less (lazily skinned) part: nothing done.
#if RE4DC_LEON_NATIVE_PIPE
// LEON_NATIVE_PIPE (native_actor_leon_pipe.inc): known != nullptr hands in one_qualifies' result (its registry entry
// and source), which the caller's preflight proved for this part; one_chunk(p, w) below is the unchanged call.
int one_chunk_core(Re4dcModelPart& p, OneWindow& w, const SkinEntry* known, const Re4dcActorSource* known_src) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::Scope dsa_part(re4dc::dsa24::ModelList);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    const re4dc::dsa24::x28::ModelScope dsa28_model(p.model);
#endif
    re4dc::dsa24::count(re4dc::dsa24::Parts);
#endif
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
    re4dc_callprof_part(p.model, 1);
#endif
    if (p.positions) return -1;
    ++stats.parts;
    const SkinEntry* se = nullptr;
    Re4dcActorSource src{};
    if (known) { se = known; src = *known_src; }
    else if (!one_qualifies(p, se, src)) { DFA26_MODEL_HIT(ActorQualify, 1) ++stats.declined; return 0; }
#else
int one_chunk(Re4dcModelPart& p, OneWindow& w) {
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
    re4dc::dsa24::Scope dsa_part(re4dc::dsa24::ModelList);
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    const re4dc::dsa24::x28::ModelScope dsa28_model(p.model);
#endif
    re4dc::dsa24::count(re4dc::dsa24::Parts);
#endif
    if (p.positions) return -1;
    APROF_SPAN(aprof_chunk, APROF_CHUNK);
    APROF_COUNT(APROF_N_CHUNKS, 1);
    ++stats.parts;
#if defined(RE4DC_CALLPROF) && RE4DC_CALLPROF
    re4dc_callprof_part(p.model, 1);
#endif
    const SkinEntry* se = nullptr;
    Re4dcActorSource src{};
    if (!one_qualifies(p, se, src)) { DFA26_MODEL_HIT(ActorQualify, 1) ++stats.declined; return 0; }
#endif
#if RE4DC_GC_ASSET_GATE
    re4dc_gcasset::ActorSourceScope gcasset_actor_scope(&p,&src);
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
    re4dc_gcasset::MotionUnknownScope gcasset_motion_scope(re4dc_gcasset::motion_model_reason());
#endif
#endif
    const float near_distance = p.projection[6] / (p.projection[5] - 1.0f);
    const float far_distance = p.projection[6] / p.projection[5];
    if (!re4dc::render::is_finite(near_distance) || !re4dc::render::is_finite(far_distance) ||
        near_distance <= 0.0f || far_distance <= near_distance) { DFA26_MODEL_HIT(ActorProjection, 1) ++stats.declined; return 0; }
    const unsigned mark = workspace_top;
    struct Release { unsigned mark; ~Release() { workspace_top = mark; } } release{mark};
    const BlobHeader* blob = blob_of(p);
    int crowd_class = 0;
    if constexpr (kCrowd) crowd_class = re4dc_actor_model_class(p.model, p.info);
    if (kLodBuild && blob && (blob->flags & kLodPending)) relod(p, crowd_class > 0);
    if (!blob && !(blob = convert(p))) { DFA26_MODEL_HIT(ActorConvert, 1) ++stats.declined; return 0; }
    const u8* base = reinterpret_cast<const u8*>(blob);
    ++stats.handled;
    if (p.cull == 3) { re4dc_model_result(0, 0, 0); return 1; }
#if RE4DC_ACTOR_TRANSACTION
    if (!owned_submission && re4dc_model_defer_part(&p)) { ++stats.deferred; return 1; }
#else
    if (re4dc_model_defer_part(&p)) { ++stats.deferred; return 1; }
#endif

#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(se->materialized==kSkinRecipePending) {
        SkinEntry* live=find_skin(p.info,nullptr);
        if(live!=se || !skin_recipe_materialize(*live)) {++stats.declined;return 0;}
    }
#endif
    Frame& f = one_frame(p, near_distance, far_distance, *se, src, w.screen);
#if RE4DC_ACTOR_FOG_GATE
    if (blob->radius > 0.0f || blob->center[0] != 0.0f || blob->center[1] != 0.0f || blob->center[2] != 0.0f) {
        const float cull_far = fog_gate_depth(near_distance, far_distance);
        const float* m = p.modelview; const float* c = blob->center;
        float depth = -1.0f;  // least view depth (-z) of the part's drawn vertices, if known
        if (f.palette && f.palette_entries) {  // f.mode == kSkin
#if RE4DC_COARSE_GATE_ONCE
            // COARSE_GATE_ONCE: entry 0 proves keep (gate_entry_z), or the loop decides.
            bool proven = false;
            if (!f.gate_ready && blob->radius >= 0.0f) {
                const float y0 = gate_entry_z(m, f.palette);
                proven = -y0 <= cull_far;
#if RE4DC_COARSE_GATE_ONCE == 1
                if (proven) { f.gate_ready = true; f.gate_T = -y0; f.gate_G = 0.0f; }
#else
                ++(proven ? gate1_chk.proofs : gate1_chk.loops);
#endif
            }
#if RE4DC_COARSE_GATE_ONCE == 1
            if (!proven) {
#endif
#endif
            if (!f.gate_ready) {
                const float mz = std::sqrt(m[8] * m[8] + m[9] * m[9] + m[10] * m[10]);
                float T = 3.0e38f, G = 0.0f;
#if RE4DC_AVK
                {
                    float S = 0.0f;
#if defined(__sh__)
                    // re4dc_actor_submit's rev 5 loop, operation for operation.
                    alignas(8) float io[6] = {m[8], m[9], m[10], m[11], -3.0e38f, 0.0f};
                    const float* pa = f.palette;
                    const float* pb = pa + 3;
                    const float* pc = pa + 6;
                    const float* pd = pa + 9;
                    const float* px = pa + 36;
                    unsigned n = f.palette_entries;
                    float* iop = io;
                    __asm__ __volatile__(
                        "mov     #4,r0\n\t"
                        "fmov.s  @%[io]+,fr12\n\t"
                        "fmov.s  @%[io]+,fr13\n\t"
                        "fmov.s  @%[io]+,fr14\n\t"
                        "fmov.s  @%[io]+,fr15\n\t"
                        "fmov.s  @%[io]+,fr10\n\t"
                        "fmov.s  @%[io]+,fr11\n"
                        "1:\n\t"
                        "fmov.s  @(r0,%[d]),fr4\n\t"
                        "fmov.s  @%[d]+,fr0\n\t"
                        "fmul    fr13,fr4\n\t"
                        "fmov.s  @(r0,%[a]),fr9\n\t"
                        "fmov.s  @(r0,%[b]),fr8\n\t"
                        "fmul    fr9,fr9\n\t"
                        "fmov.s  @(r0,%[c]),fr6\n\t"
                        "fmac    fr0,fr12,fr4\n\t"
                        "fmov.s  @(r0,%[d]),fr0\n\t"
                        "fmul    fr8,fr8\n\t"
                        "pref    @%[x]\n\t"
                        "fmul    fr6,fr6\n\t"
                        "add     #44,%[x]\n\t"
                        "fmac    fr0,fr14,fr4\n\t"
                        "fmov.s  @%[a]+,fr0\n\t"
                        "pref    @%[x]\n\t"
                        "add     #44,%[d]\n\t"
                        "fmac    fr0,fr0,fr9\n\t"
                        "fmov.s  @(r0,%[a]),fr0\n\t"
                        "fadd    fr15,fr4\n\t"
                        "add     #44,%[a]\n\t"
                        "add     #4,%[x]\n\t"
                        "fmac    fr0,fr0,fr9\n\t"
                        "fmov.s  @%[b]+,fr0\n\t"
                        "fmac    fr0,fr0,fr8\n\t"
                        "fmov.s  @(r0,%[b]),fr0\n\t"
                        "fcmp/gt fr11,fr9\n\t"
                        "add     #44,%[b]\n\t"
                        "fmac    fr0,fr0,fr8\n\t"
                        "fmov.s  @%[c]+,fr0\n\t"
                        "bt      2f\n"
                        "6:\n\t"
                        "fmac    fr0,fr0,fr6\n\t"
                        "fmov.s  @(r0,%[c]),fr0\n\t"
                        "fcmp/gt fr11,fr8\n\t"
                        "add     #44,%[c]\n\t"
                        "fmac    fr0,fr0,fr6\n\t"
                        "bt      3f\n"
                        "7:\n\t"
                        "fcmp/gt fr11,fr6\n\t"
                        "bt      4f\n"
                        "8:\n\t"
                        "fcmp/gt fr10,fr4\n\t"
                        "bt      5f\n"
                        "9:\n\t"
                        "dt      %[n]\n\t"
                        "bf      1b\n\t"
                        "bra     0f\n\t"
                        "nop\n"
                        "2:\n\t"
                        "bra     6b\n\t"
                        "fmov    fr9,fr11\n"
                        "3:\n\t"
                        "bra     7b\n\t"
                        "fmov    fr8,fr11\n"
                        "4:\n\t"
                        "bra     8b\n\t"
                        "fmov    fr6,fr11\n"
                        "5:\n\t"
                        "bra     9b\n\t"
                        "fmov    fr4,fr10\n"
                        "0:\n\t"
                        "fmov.s  fr11,@-%[io]\n\t"
                        "fmov.s  fr10,@-%[io]\n"
                        : [a] "+r"(pa), [b] "+r"(pb), [c] "+r"(pc), [d] "+r"(pd), [x] "+r"(px), [n] "+r"(n),
                          [io] "+r"(iop)
                        :
                        : "r0", "fr0", "fr4", "fr6", "fr8", "fr9", "fr10", "fr11", "fr12", "fr13", "fr14", "fr15", "t",
                          "memory");
                    T = -io[4]; S = io[5];
#else
                    const float m8 = m[8], m9 = m[9], m10 = m[10], m11 = m[11];
                    const float* P = f.palette;
                    for (unsigned i = f.palette_entries; i; --i, P += 12) {
                        __builtin_prefetch(P + 36);
                        __builtin_prefetch(P + 47);
                        const float d = -(m8 * P[9] + m9 * P[10] + m10 * P[11] + m11);
                        const float s0 = P[0] * P[0] + P[1] * P[1] + P[2] * P[2];
                        const float s1 = P[3] * P[3] + P[4] * P[4] + P[5] * P[5];
                        const float s2 = P[6] * P[6] + P[7] * P[7] + P[8] * P[8];
                        T = std::min(T, d);
                        S = std::max(S, s0); S = std::max(S, s1); S = std::max(S, s2);
                    }
#endif
                    G = std::max(G, mz * std::sqrt(S));
                }
#if RE4DC_AVK == 2
                {
                    float T2 = 3.0e38f, G2 = 0.0f;
                    for (unsigned i = 0; i < f.palette_entries; ++i) {
                        const float* P = f.palette + i * 12;
                        const float d = -(m[8] * P[9] + m[9] * P[10] + m[10] * P[11] + m[11]);
                        float s = 0.0f;
                        for (unsigned k = 0; k < 3; ++k)
                            s = std::max(s, P[k * 3] * P[k * 3] + P[k * 3 + 1] * P[k * 3 + 1] + P[k * 3 + 2] * P[k * 3 + 2]);
                        T2 = std::min(T2, d); G2 = std::max(G2, mz * std::sqrt(s));
                    }
                    avk_gate_check(T, G, T2, G2);
                }
#endif
#else
                for (unsigned i = 0; i < f.palette_entries; ++i) {
                    const float* P = f.palette + i * 12;  // columns R0, R1, R2, t
                    const float d = -(m[8] * P[9] + m[9] * P[10] + m[10] * P[11] + m[11]);
                    float s = 0.0f;
                    for (unsigned k = 0; k < 3; ++k)
                        s = std::max(s, P[k * 3] * P[k * 3] + P[k * 3 + 1] * P[k * 3 + 1] + P[k * 3 + 2] * P[k * 3 + 2]);
                    T = std::min(T, d); G = std::max(G, mz * std::sqrt(s));
                }
#endif
                f.gate_ready = true; f.gate_T = T; f.gate_G = G;
            }
            depth = f.gate_T - f.gate_G * (std::sqrt(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]) + blob->radius);
#if RE4DC_COARSE_GATE_ONCE == 1
            }
#elif RE4DC_COARSE_GATE_ONCE == 2
            if (proven && depth > cull_far) ++gate1_chk.proof_cull;  // the loop culls what entry 0 kept: must stay 0
#endif
        }
        ++fog_gate_tests;
        if (frame_serial - fog_gate_log >= 600U) {
            fog_gate_log = frame_serial;
            re4dc_log("native actor fog gate: frame=%u tests=%u culled=%u far=%.0f\n", frame_serial, fog_gate_tests,
                      fog_gate_culled, cull_far);
        }
        if (depth > cull_far) { ++fog_gate_culled; re4dc_model_result(0, 0, 0); return 1; }
    }
#endif
    // (A skinned Frame: re4dc_actor_submit's rigid sphere test does not apply.)
    // The most slots this chunk can send (a whole meshlet 3 per triangle at most, a clipped one 6): the
    // window stays inside the store-queue window of 32767 slots.
    const auto* table = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
    if (w.open) {
        unsigned bound = 0;
        for (unsigned mi = 0; mi < blob->meshlets; ++mi) bound += table[mi].n.triangles();
        if (w.slots + 6U * bound > 32767U) one_close(w);
    }
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    const unsigned uv32_certificate = uv32::checked_certificate(p, *blob);
    unsigned uv32_reason = re4dc::format32::BeginFailed;
    if (w.open) {
        uv32_reason = re4dc_model_uv16_live32(&p, uv32_certificate);
        const bool uv32_want = uv32_reason == re4dc::format32::Uv16;
        if (w.uv16 != uv32_want) { one_close(w); ++uv32::counters.splits; }
    }
    const bool uv32_shared = w.open;
#endif
    Part e{p, f, {p.projection, p.viewport}, {near_distance, far_distance, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF, project, nullptr}};
    e.clip.context = &e.projection;
    e.streaming = re4dc_model_packet_streaming() != 0;
    if (!w.open) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
        if (!re4dc_model_packet_reserve(&p, &e.packet)) {
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
            RE4DC_DROP_ACTOR(&p, 0, 0); re4dc_model_result(2, 0, 0); return 1; }
#else
        if (!re4dc_model_packet_reserve(&p, &e.packet)) { RE4DC_DROP_ACTOR(&p, 0, 0); re4dc_model_result(2, 0, 0); return 1; }
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
        re4dc_model_uv16_request32(uv32_certificate);
#endif
        if (re4dc_model_direct_enabled() && re4dc_model_direct_begin_reserved(&p, &e.packet, &w.direct)) {
            if (w.direct.scratch_capacity < kCacheSlots) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
#endif
                re4dc_model_direct_end(0); RE4DC_DROP_ACTOR(&p, 'd', 0); re4dc_model_result(2, 0, 0); return 1;
            }
            w.open = true; w.sq = w.direct.sq; w.slots = 0; w.primed = 0;
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            w.uv16 = re4dc_model_uv16_result32() == re4dc::format32::Uv16;
#endif
        } else {
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
            DFA26_MODEL_HIT(ActorPacketPath, 1)
#endif
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            re4dc_model_uv16_request32(uv32_certificate);
#endif
            if (!re4dc_model_packet_begin(&p, &e.packet) || e.packet.capacity < kCacheSlots + 64U) {
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
            uv32::counters.note(re4dc::format32::BeginFailed, 3U);
#endif
                RE4DC_DROP_ACTOR(&p, 0, e.packet.capacity);
                re4dc_model_result(2, 0, 0);
                return 1;
            }
            e.packet.capacity -= kCacheSlots;
            e.cache.v = static_cast<pvr_vertex_t*>(e.packet.vertices) + e.packet.capacity;
        }
    }
    if (w.open) {
        e.direct = true; e.sq = w.sq; e.primed = w.primed;
        e.packet.u_scale = w.direct.u_scale; e.packet.v_scale = w.direct.v_scale;
        e.cache.v = static_cast<pvr_vertex_t*>(w.direct.scratch);
    }
    e.cache.oc = reinterpret_cast<u8*>(e.cache.v + kMaxVertices);
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
    if (!uv32_shared) uv32_reason = re4dc_model_uv16_result32();
    e.uv16 = uv32_reason == re4dc::format32::Uv16;
    if (e.uv16) ++stats.uv16_parts;
    uv32::counters.note(uv32_reason, uv32_shared ? 2U : (e.direct ? 1U : 0U));
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    if (!e.uv16) re4dc::dfa26::hit(re4dc::dfa26::ActorUv32);
#endif

    APROF_SPAN(aprof_lit0, APROF_LIT);
    const SourceLighting& S = *p.lighting;
    const bool constant_source = !S.enable && !S.ambient_vertex && !S.material_vertex;
    Lights* lp = constant_source ? &w.lights : &w.lit;
    G1PC_PART(p, true);
    if (!constant_source || !w.lights_ready || w.lights.source != p.lighting) {
        G1PC_LIGHT(p, f, blob->center);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
        B28_NOTE(p, fast_only_lights(p, f, blob->center, *lp));
#else
        if (!B28_NOTE(p, RE4DC_PART_LIGHTS(p, f, blob->center, *lp))) {
#if defined(RE4DC_STATUE_LIGHTS) && RE4DC_STATUE_LIGHTS >= 2
        if (!lp->exact_ready)
#endif
        RE4DC_PREPARED(*lp) = re4dc::render::prepare_actor_lights(*p.lighting);
        RE4DC_CAP_EXACT(p, blob->center, *lp);
        }
#endif
#if !RE4DC_ACTOR_SETUP_LEAN
        lp->source = p.lighting;
#endif
        w.lights_ready = constant_source;
    }
    Lights& lights = *lp;
    unsigned tier = kTierFull;
    if (crowd_class > 0) {
        const u32* mw = reinterpret_cast<const u32*>(p.modelview);
        if (w.tier_model && w.tier_model == p.model && w.tier_class == crowd_class && w.tier_t[0] == mw[3] &&
            w.tier_t[1] == mw[7] && w.tier_t[2] == mw[11]) {
            tier = w.tier;
        } else {
            tier = crowd_tier(p, crowd_class);
            w.tier_model = p.model; w.tier_class = crowd_class; w.tier = tier;
            w.tier_t[0] = mw[3]; w.tier_t[1] = mw[7]; w.tier_t[2] = mw[11];
        }
    }
    if (tier >= (kCrowdFlat ? kTierNear : kTierMid) && tier != kTierFull && lights.fast && !lights.constant
#if RE4DC_ACTOR_PROBE_LIGHT
        && !(lights.probe && tier == kTierNear && RE4DC_GANADO_VERTEX_LIT(p))  // ACTOR_PROBE_LIGHT=2: the near tier lights per vertex
#endif
    ) {
        lights.constant = true;  // never the window's record: lights.fast is false for constant lighting
        lights.constant_rgb = part_colour(lights);
    }
#if defined(RE4DC_FALLBACK_SCAN29) && RE4DC_FALLBACK_SCAN29 && !RE4DC_ACTOR_LIGHT_FAST_ONLY
    // The offline per-record colours supersede the crowd/rigid flat-colour approximation.
    if (lights.scan29_bake) lights.constant = false;
#endif
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    fa29_actor_note(p,lights);
#endif
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    re4dc::dsa24::x28::light(dsa28_light_path(lights), lights.count);
#endif
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
    if (f.skin_dirs && !lights.constant) {
        float dmax = 0.0f;
        for (unsigned i = 0; i < 12; ++i) dmax = std::max(dmax, std::fabs(lights.dir[i / 4][i % 4]));
        if (!near_vec(&lights.dir[0][0], f.dirs_fold, 12, dmax * kDirTolerance)) {
            std::memset(f.dirs_ready, 0, f.palette_entries);
            std::memcpy(f.dirs_fold, &lights.dir[0][0], sizeof(f.dirs_fold));
            ++stats.skin_dir_sets;
#if RE4DC_ACTOR_PROBE_LIGHT
            if (lights.probe && f.palette) probe_dirs_all(f, lights);
#endif
        }
    }
#endif
    APROF_STOP(aprof_lit0);
    const bool s16_uv = (p.flags & 0x80000000U) != 0;
    const float uv_scale = s16_uv ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const PosConst k{0.0f, uv_scale * e.packet.u_scale, p.uv_offset[0] * e.packet.u_scale,
                     uv_scale * e.packet.v_scale, p.uv_offset[1] * e.packet.v_scale, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF,
                     near_distance, far_distance};
    e.colors = (p.alpha_state & 256) ? p.colors : nullptr;
    e.alpha = u32(p.alpha_state & 255) << 24;
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA && !RE4DC_ACTOR_LIGHT_FAST_ONLY
    const bool retain_flat = lights.constant && !e.colors;
    u32 flat_argb = 0;
    if (retain_flat) {
        flat_argb = e.alpha | lights.constant_rgb;
#if RE4DC_LEON_LIGHT_HEADROOM
        if (lights.half_post)
            flat_argb = (flat_argb & 0xFF000000U) | ((flat_argb >> 1) & 0x007F7F7FU);
#endif
    }
#endif
    const unsigned rs = 3U + ((blob->flags & kHasCi) ? 1U : 0U) + ((blob->flags & kHasBake) ? 1U : 0U);
    const unsigned color_index = blob->color_index;
    const unsigned level = tier == kTierFar ? blob->levels
                           : select_level(p, *blob, near_distance, tier == kTierMid ? crowd_mid_tau : RE4DC_NEAR_LOD_TAU);
    const LevelInfo* li = level ? reinterpret_cast<const LevelInfo*>(base + blob->lod4 * 4U) + (level - 1) : nullptr;
    const MeshletLevel* lt = li ? reinterpret_cast<const MeshletLevel*>(base + li->table4 * 4U) : nullptr;
    const u8* lists = li ? base + li->lists4 * 4U : base + blob->idx4 * 4U;
    const u8* records = base + blob->rec4 * 4U;
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
    constexpr BakeUse bake = kBakeNone;
#else
    unsigned bake_scale[3];
    const BakeUse bake = kPrelit && (blob->flags & kHasBake) && blob->bake4 && lights.fast && !lights.constant && !e.colors
        ? bake_prepare(e, lights, *blob, rs, bake_scale) : kBakeNone;
#endif
    ++stats.lod_draws[level];
    if (kCrowd) ++stats.crowd_parts[tier];
    bool ok = true;
#if RE4DC_ACTOR_BACKFACE_CONE
    unsigned abc_cls;
    const AbcCone* abc = abc_part(p, base, f, abc_cls);
    abc_census();
    AbcEye abc_e;
#endif
#if defined(RE4DC_ACTOR_PROF) && RE4DC_ACTOR_PROF
    {   // census only: distinct position / normal indices of the records this chunk draws at its level
        static u16 seen_v[16384], seen_n[16384], seen_m[16384], last_n[16384], last_t[16384]; static u16 stamp, mstamp;
        if (++stamp == 0) { std::memset(seen_v, 0, sizeof seen_v); std::memset(seen_n, 0, sizeof seen_n); stamp = 1; }
        unsigned uv = 0, un = 0, ut = 0, um = 0;
        for (unsigned mi = 0; mi < blob->meshlets; ++mi) {
            const Counts c = lt ? lt[mi].n : table[mi].n;
            const Records rr{reinterpret_cast<const u16*>(records) + table[mi].first * rs, rs, color_index, (blob->flags & kHasCi) != 0};
            if (++mstamp == 0) { std::memset(seen_m, 0, sizeof seen_m); mstamp = 1; }
            for (unsigned i = 0, nv = c.indices() ? c.vertices() : 0; i < nv; ++i) {
                const unsigned vi = rr.vi(i) & 16383u, ni = rr.ni(i) & 16383u, ti = rr.ti(i);
                if (seen_v[vi] != stamp) { seen_v[vi] = stamp; ++uv; ++ut; last_n[vi] = u16(ni); last_t[vi] = u16(ti); }
                else if (last_n[vi] != ni || last_t[vi] != ti) { ++ut; last_n[vi] = u16(ni); last_t[vi] = u16(ti); }
                if (seen_n[ni] != stamp) { seen_n[ni] = stamp; ++un; }
                if (seen_m[vi] != mstamp) { seen_m[vi] = mstamp; ++um; }
            }
        }
        APROF_COUNT(APROF_N_UVI, uv); APROF_COUNT(APROF_N_UNI, un); APROF_COUNT(APROF_N_UTR, ut); APROF_COUNT(APROF_N_UVM, um);
    }
#endif
    for (unsigned mi = 0; ok && mi < blob->meshlets; ++mi) {
        const MeshletInfo& m = table[mi];
        const Counts c = lt ? lt[mi].n : m.n;
        const unsigned nv = c.vertices(), ni = c.indices(), nt = c.triangles();
        if (!ni) continue;  // wholly collapsed at this level
        const Records r{reinterpret_cast<const u16*>(records) + m.first * rs, rs, color_index, (blob->flags & kHasCi) != 0};
        const u8* index = lists + (lt ? lt[mi].index : m.index);
        ++stats.meshlets; stats.vertices += nv; stats.corners += ni; stats.triangles += nt;
        if (kCrowd) stats.crowd_triangles[tier] += nt;
#if RE4DC_ACTOR_BACKFACE_CONE
        if (abc) {
            ++abc_tests[abc_cls]; abc_verts[abc_cls] += nv;
            const AbcCone& cn = abc[mi];
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32
            if (!cn.k) ++abc32_stats.empty;
#endif
            if (cn.k && abc_eye(f, p.cull, cn.pal, abc_e) && abc_reject(cn, abc_e)) {
                ++abc_rej[abc_cls]; abc_vskip[abc_cls] += nv; abc_tskip[abc_cls] += nt;
#if RE4DC_ACTOR_BACKFACE_CONE == 2
                abc_verify(e, r, nv, k, s16_uv, index, ni);
#endif
                e.input += nt;
                continue;
            }
        }
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#if RE4DC_ACTOR_BACKFACE_CONE
        if (!abc || !abc[mi].k) re4dc::dfa26::hit(re4dc::dfa26::ActorConeUnavailable);
#else
        re4dc::dfa26::hit(re4dc::dfa26::ActorConeUnavailable);
#endif
#endif
#if RE4DC_ACTOR_CLIP_FRONT26
        e.clip_vertices = nv;
#endif
        unsigned all, any;
        APROF_COUNT(APROF_N_VERTS, nv); APROF_COUNT(APROF_N_MESHLETS, 1);
        APROF_SPAN(aprof_pos, APROF_POS);
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
        chunk_positions(e, r, nv, k, s16_uv, all, any);
#else
        pass_positions(e, r, nv, k, s16_uv, all, any);
#endif
        APROF_STOP(aprof_pos);
        if (all & kOcCull) {
            ++stats.meshlets_culled;
            e.input += nt;
            continue;
        }
        e.prime(nv);
#if defined(RE4DC_ACTOR_FORMAT32) && RE4DC_ACTOR_FORMAT32 && RE4DC_ACTOR_UV16
        if (e.uv16) pack_uv16(e.cache.v, nv, true);
#endif
        APROF_SPAN(aprof_lit, APROF_LIT);
#if RE4DC_ACTOR_LIGHT_FAST_ONLY
        pass_fast_only(e, lights, r, nv);
#else
        if (lights.constant) {
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
            if (e.colors) re4dc::dfa26::hit(re4dc::dfa26::ActorFlatRewrite, nv);
#else
            re4dc::dfa26::hit(re4dc::dfa26::ActorFlatRewrite, nv);
#endif
#endif
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
            if (!e.colors) e.flat_colors(nv, flat_argb);
            else
#else
#if RE4DC_AVK
            if (!e.colors) {
                const u32 argb = e.alpha | lights.constant_rgb;
                pvr_vertex_t* v = e.cache.v;
                unsigned i = 0;
                for (; i + 4 <= nv; i += 4, v += 4) {
                    v[0].argb = argb; v[1].argb = argb; v[2].argb = argb; v[3].argb = argb;
                }
                for (; i < nv; ++i, ++v) v->argb = argb;
            } else
#endif
#endif
            for (unsigned i = 0; i < nv; ++i)
                e.cache.v[i].argb = (e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha) | lights.constant_rgb;
        } else if (bake != kBakeNone) {
            pass_baked(e, r, nv, bake == kBakeScaled ? bake_scale : nullptr);
        } else if (lights.fast) {
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
            chunk_lights(e, lights, r, nv);
#else
            pass_lights(e, lights, r, nv);
#endif
        } else {
            pass_lights_exact(e, lights, r, nv);
        }
#if RE4DC_LEON_LIGHT_TOGGLE
        // LEON_LIGHT_TOGGLE mode 1 (PROBE): test 10's 1.0x cap on the 2x textures (the pass ran at full scale)
        if (re4dc_leon_light_mode == 1 && !lights.constant && leon_record(*p.lighting))
            for (unsigned i = 0; i < nv; ++i) {
                const u32 c = e.cache.v[i].argb;
                e.cache.v[i].argb = (c & 0xFF000000U) | ((c >> 1) & 0x007F7F7FU);
            }
#endif
#if RE4DC_LEON_LIGHT_HEADROOM
        // LEON_LIGHT_HEADROOM: a 2x-texture part outside the owner path (build_lights half_post): the 1x look
#if RE4DC_ACTOR_BYTES_LEAN && !RE4DC_ACTOR_MOVCA
        if (lights.half_post && !retain_flat)
#else
        if (lights.half_post)
#endif
            for (unsigned i = 0; i < nv; ++i) {
                const u32 c = e.cache.v[i].argb;
                e.cache.v[i].argb = (c & 0xFF000000U) | ((c >> 1) & 0x007F7F7FU);
            }
#endif

#endif
        APROF_STOP(aprof_lit);

#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
        if (bake == kBakeNone) stats.normals_lit += nv;
#endif
        if (any & kOcNear) ++stats.meshlets_clipped;
        APROF_SPAN(aprof_pack, APROF_PACK);
#if defined(RE4DC_CHAR_CHUNK) && RE4DC_CHAR_CHUNK
        {
            ChunkSink sink;
            chunk_sink_begin(sink, e);
            ok = chunk_sink_strips(sink, r, index, nv, ni, nt, any);
            chunk_sink_end(sink);
        }
#else
        if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; ok = e.whole(index, ni, nt); }
        else DFA26_MODEL_SLOW(ActorStripScan, 1, ok = e.strips(r, index, ni);)
#endif
        APROF_STOP(aprof_pack);
    }
    if (e.direct) {
#if RE4DC_GC_ASSET_GATE
        if(e.slots)gcasset_actor_scope.accepted();
#endif
#if RE4DC_GC_ASSET_MOTION_UNKNOWN
        if(e.slots){re4dc_gcasset::motion_accept_current(e.slots);w.motion_accounted=1;}
#endif
        w.sq = e.sq; w.slots += e.slots; w.primed = e.primed;
        if (!ok) {
            re4dc_model_packet_abort();
            one_close(w);
            re4dc_model_result(3, e.input, 0);
            return 1;
        }
        re4dc_model_result(0, e.input, e.output);
        return 1;
    }
    if (!ok) {
        if (e.committed) re4dc_model_packet_abort();
        re4dc_model_result(3, e.input, 0);
        return 1;
    }
    re4dc_model_packet_commit(e.used);
    re4dc_model_result(0, e.input, e.output);
    return 1;
}
#if RE4DC_LEON_NATIVE_PIPE
int one_chunk(Re4dcModelPart& p, OneWindow& w) { return one_chunk_core(p, w, nullptr, nullptr); }
#endif
#if RE4DC_COARSE_ONE_SUBMIT == 2
constexpr unsigned kOneCheckMax = 8;
struct OneCheck {
    unsigned calls, chunks, words, word_mismatch, header_mismatch, result_mismatch, headers, logged, log_frame;
} one_chk{};
struct OneRef { int r; u32 h, words, header[8]; bool header_seen; };
void one_note(const OneRef& a, const OneRef& b, unsigned k, const void* info) {
    ++one_chk.chunks; one_chk.words += b.words;
    const bool words = a.h != b.h || a.words != b.words;
    const bool header = a.header_seen != b.header_seen || (a.header_seen && std::memcmp(a.header, b.header, 32));
    if (a.header_seen && b.header_seen) ++one_chk.headers;
    if (words) ++one_chk.word_mismatch;
    if (header) ++one_chk.header_mismatch;
    if (a.r != b.r) ++one_chk.result_mismatch;
    if ((words || header || a.r != b.r) && one_chk.logged < 8) {
        ++one_chk.logged;
        re4dc_log("C3CHK mismatch frame=%u chunk=%u info=%08x result=%d/%d words=%u/%u hash=%08x/%08x header=%d/%d%s\n",
                  frame_serial, k, unsigned(reinterpret_cast<std::uintptr_t>(info)), a.r, b.r, a.words, b.words, a.h,
                  b.h, int(a.header_seen), int(b.header_seen), header ? " header-differs" : "");
    }
}
#endif
}  // namespace

extern "C" unsigned re4dc_actor_submit_chunks(Re4dcModelPart* part, const Re4dcActorChunk* chunks, unsigned n) {
    Re4dcModelPart& p = *part;
    auto load = [&](unsigned i) {
        const Re4dcActorChunk& c = chunks[i];
        p.info = c.info; p.part = c.info; p.stream = c.stream; p.stream_bytes = c.stream_bytes; p.uv = c.uv;
        p.position_count = c.position_count; p.normal_count = c.normal_count;
#if RE4DC_ACTOR_SOURCE_SPAN
        p.source_span=c.source_span;
#endif
        std::memcpy(p.modelview, c.modelview, sizeof(p.modelview));
    };
#if RE4DC_COARSE_ONE_SUBMIT == 2
    // The reference: every chunk through re4dc_actor_submit, its TA words folded.
    OneRef ref[kOneCheckMax];
    const unsigned nref = n < kOneCheckMax ? n : kOneCheckMax;
    for (unsigned i = 0; i < nref; ++i) {
        load(i);
        one_tap = OneTap{}; one_tap.on = true;
        ref[i].r = re4dc_actor_submit(&p);
        one_tap.on = false;
        ref[i].h = one_tap.h; ref[i].words = one_tap.words; ref[i].header_seen = one_tap.header_seen;
        std::memcpy(ref[i].header, one_tap.header, 32);
    }
    // The reference's Frames of these infos are not reused: the window path prepares its own.
    for (unsigned i = 0; i < nref; ++i)
        for (Frame& o : frames)
            if (o.info == chunks[i].info) o.frame = ~0U;
    ++one_chk.calls;
#endif
    unsigned done = 0;
    OneWindow w;
    for (unsigned i = 0; i < n; ++i) {
        load(i);
#if RE4DC_COARSE_ONE_SUBMIT == 2
        one_tap = OneTap{}; one_tap.on = i < nref;
#endif
        int r = one_chunk(p, w);
        if (r < 0) { one_close(w); r = re4dc_actor_submit(&p); }
#if RE4DC_COARSE_ONE_SUBMIT == 2
        one_tap.on = false;
        if (i < nref) {
            OneRef got{r, one_tap.h, one_tap.words, {}, one_tap.header_seen};
            std::memcpy(got.header, one_tap.header, 32);
            one_note(ref[i], got, i, chunks[i].info);
        }
#endif
        if (r) done |= 1U << i;
    }
    one_close(w);
#if RE4DC_COARSE_ONE_SUBMIT == 2
    if (frame_serial - one_chk.log_frame >= 120U) {
        one_chk.log_frame = frame_serial;
        re4dc_log("C3CHK frame=%u calls=%u chunks=%u words=%u word_mismatch=%u header_mismatch=%u result_mismatch=%u "
                  "headers=%u\n", frame_serial, one_chk.calls, one_chk.chunks, one_chk.words, one_chk.word_mismatch,
                  one_chk.header_mismatch, one_chk.result_mismatch, one_chk.headers);
    }
#endif
#if RE4DC_COARSE_GATE_ONCE == 2
    if (frame_serial - gate1_chk.log_frame >= 120U) {
        gate1_chk.log_frame = frame_serial;
        re4dc_log("GATE1CHK frame=%u proofs=%u loops=%u proof_cull=%u\n", frame_serial, gate1_chk.proofs,
                  gate1_chk.loops, gate1_chk.proof_cull);
    }
#endif
    return done;
}

#if RE4DC_ACTOR_TRANSACTION
#include "include/native_actor_owner_submit.inc"
#if defined(RE4DC_PS2_INTERIOR_OWNER) && RE4DC_PS2_INTERIOR_OWNER && defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
// PS2_INTERIOR_ACTORS=2 (game30.mk; coarse_actor_transaction.inc): an owner-path Ganado whose owned submission the
// interior cell skips. one_chunk notes every run that reaches crowd_tier in the CROWD_LOD ranking; Trans proved that
// the fog gate keeps each drawn chunk (coarse_actor_owner_ganado.inc invis_owner_interior), and actor_acquire's
// preflight that every run qualifies and reserves. This checks what one_chunk does before crowd_tier for each run,
// as re4dc_actor_submit_owned_runs loads it (owned_run_load): one_qualifies, finite near / far, a settled part
// (CROWD_INVIS_SKIP's re4dc_actor_part_settled: converted in place, no LOD build waiting, so the skip leaves the
// streams and the LOD budget as the submission would), cull != 3. All pass: 1, *nearest = the least distance noted,
// and with note != 0 each run's crowd class > 0 notes its modelview through re4dc_actor_crowd_note (CROWD_INVIS_SKIP's
// crowd_tier bookkeeping). Any fails: 0, nothing noted (the caller submits).
extern "C" int re4dc_actor_owned_crowd_replay(const Re4dcModelPart* base, const Re4dcActorDrawRun* runs, unsigned n,
                                              const Re4dcActorOwnedMaterial* materials, unsigned nm, int note,
                                              float* nearest) {
    if constexpr (!kCrowd) return 0;
    if (!base || !runs || !materials || !n || n > kRe4dcActorRuns) return 0;
    Re4dcModelPart p = *base;
    float best = 0.0f;
    for (unsigned i = 0; i < n; ++i) {
        if (runs[i].material >= nm) return 0;
        owned_run_load(p, runs[i], materials[runs[i].material]);
        const SkinEntry* se = nullptr;
        Re4dcActorSource src{};
        if (p.positions || !one_qualifies(p, se, src)) return 0;
        const float near_distance = p.projection[6] / (p.projection[5] - 1.0f);
        const float far_distance = p.projection[6] / p.projection[5];
        if (!re4dc::render::is_finite(near_distance) || !re4dc::render::is_finite(far_distance) ||
            near_distance <= 0.0f || far_distance <= near_distance) return 0;
        if (!re4dc_actor_part_settled(p.stream, p.stream_bytes) || p.cull == 3) return 0;
        const float* m = p.modelview;
        const float d = std::sqrt(m[3] * m[3] + m[7] * m[7] + m[11] * m[11]);
        if (!i || d < best) best = d;
    }
    if (note)
        for (unsigned i = 0; i < n; ++i) {
            owned_run_load(p, runs[i], materials[runs[i].material]);
            if (re4dc_actor_model_class(p.model, p.info) > 0) re4dc_actor_crowd_note(p.model, p.modelview);
        }
    *nearest = best;
    return 1;
}
#endif
#if RE4DC_LEON_NATIVE_PIPE
#include "include/native_actor_leon_pipe.inc"
#endif
#endif
#endif

#if defined(RE4DC_ACTOR_TEST)
extern "C" unsigned re4dc_actor_test_reject_line() { return reject_line; }
extern "C" void re4dc_actor_test_meshlet_stats(unsigned out[8]) {
    out[0] = test_meshlets; out[1] = test_records; out[2] = test_indices; out[3] = test_lod_parts;
    out[4] = test_blob_bytes; out[5] = test_lod_bytes;
    out[6] = unsigned(test_convert_us); out[7] = unsigned(test_lod_us);
    std::printf("converter host time: total %.0f us (LOD %.0f us), max part %.0f us\n", test_convert_us, test_lod_us, test_convert_max_us);
}
#endif

#if defined(RE4DC_ACTOR_PROF) && RE4DC_ACTOR_PROF
// ACTOR_PROF (actorplan.mk; diagnostic only): actor_prof.h. Cycle sums per class x phase since the last report.
#include <arch/timer.h>
#include <stdio.h>
extern "C" void re4dc_log(const char*, ...);
namespace {
const char* const kAprofNames[APROF_PHASES] = {"TX", "PLAN", "SEM1", "CROWD", "ACQ", "PAL", "PRE1", "PASS", "SUB",
                                               "PRE2", "WFL", "CHUNK", "POS", "LIT", "PACK"};
const char* const kAprofClass[4] = {"leon", "ganado", "other", "free"};
unsigned long long aprof_sum[4][APROF_PHASES];
unsigned aprof_n[4][APROF_COUNTS];
unsigned aprof_first, aprof_last, aprof_frames;
}  // namespace
extern "C" {
unsigned re4dc_aprof_cls = 3;
unsigned re4dc_aprof_wfl_cycles;
// TMU2 nanoseconds (timer_ns_gettime64; Flycast does not count PRFC0) as 200 MHz cycles: 1 cycle = 5 ns.
unsigned re4dc_aprof_now(void) { return unsigned(timer_ns_gettime64() / 5u); }
void re4dc_aprof_add(unsigned phase, unsigned cycles) {
    if (phase < APROF_PHASES) aprof_sum[re4dc_aprof_cls & 3][phase] += cycles;
}
void re4dc_aprof_count(unsigned what, unsigned n) {
    if (what < APROF_COUNTS) aprof_n[re4dc_aprof_cls & 3][what] += n;
}
// Called with the source frame at each transaction: a report every 300 distinct frames (per-frame means, cycles at
// 200 MHz printed as microseconds x10 = 0.1 us units / 2 ... printed directly as us with one decimal).
void re4dc_aprof_frame(unsigned frame) {
    if (frame == aprof_last) return;
    if (!aprof_frames) aprof_first = frame;
    aprof_last = frame; ++aprof_frames;
    if (aprof_frames <= 300) return;
    const unsigned frames = aprof_frames - 1;  // the frames fully summed before this one
    for (unsigned c = 0; c < 4; ++c) {
        if (!aprof_n[c][APROF_N_CALLS] && !aprof_n[c][APROF_N_CHUNKS]) continue;
        char line[512]; int at = snprintf(line, sizeof line, "APROF f=%u..%u frames=%u cls=%s calls10=%u chunks10=%u verts=%u "
            "meshlets10=%u hits10=%u uvi=%u uni=%u utr=%u uvm=%u", aprof_first, frame - 1, frames, kAprofClass[c],
            aprof_n[c][0] * 10 / frames, aprof_n[c][1] * 10 / frames, aprof_n[c][2] / frames, aprof_n[c][3] * 10 / frames,
            aprof_n[c][4] * 10 / frames, aprof_n[c][APROF_N_UVI] / frames, aprof_n[c][APROF_N_UNI] / frames,
            aprof_n[c][APROF_N_UTR] / frames, aprof_n[c][APROF_N_UVM] / frames);
        for (unsigned p = 0; p < APROF_PHASES && at > 0 && at < int(sizeof line); ++p) {
            // us per frame with one decimal: cycles / frames / 200 MHz
            const unsigned long long us10 = aprof_sum[c][p] / frames / 20;
            at += snprintf(line + at, sizeof line - at, " %s=%llu.%llu", kAprofNames[p], us10 / 10, us10 % 10);
        }
        re4dc_log("%s us/frame\n", line);
    }
    std::memset(aprof_sum, 0, sizeof aprof_sum); std::memset(aprof_n, 0, sizeof aprof_n);
    aprof_frames = 1; aprof_first = frame;
}
}
#endif

#if defined(RE4DC_ACTOR_PLAN) && RE4DC_ACTOR_PLAN
// ACTOR_PLAN (actorplan.mk, actor_plan.h): the runtime switch and the compare counters.
#include <stdio.h>
extern "C" void re4dc_log(const char*, ...);
namespace {
const char* const kAplanNames[APLAN_KINDS] = {"bind", "pre", "roles", "row", "hand", "sem", "mat"};
unsigned aplan_checks[APLAN_KINDS], aplan_hits[APLAN_KINDS], aplan_bad[APLAN_KINDS], aplan_log_frame;
}  // namespace
extern "C" {
unsigned re4dc_actor_plan_on = 1;
alignas(32) unsigned char re4dc_actor_plan_store[RE4DC_ACTOR_PLAN_STORE];
void re4dc_actor_plan_note(unsigned kind, int hit, int bad) {
    if (kind >= APLAN_KINDS) return;
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
    static_assert(re4dc::dfa26::ActorPlanMat - re4dc::dfa26::ActorPlanBind + 1 == APLAN_KINDS,
                  "Build 26 plan reasons retain the APLAN kind order");
    if (!hit) re4dc::dfa26::hit(static_cast<re4dc::dfa26::Reason>(re4dc::dfa26::ActorPlanBind + kind));
#endif
    ++aplan_checks[kind]; aplan_hits[kind] += hit != 0; aplan_bad[kind] += bad != 0;
    if (frame_serial - aplan_log_frame < 600U) return;
    aplan_log_frame = frame_serial;
    char line[400]; int at = snprintf(line, sizeof line, "APLAN f=%u on=%u", frame_serial, re4dc_actor_plan_on);
    for (unsigned k = 0; k < APLAN_KINDS && at > 0 && at < int(sizeof line); ++k)
        at += snprintf(line + at, sizeof line - at, " %s=%u/%u/%u", kAplanNames[k], aplan_checks[k], aplan_hits[k],
                       aplan_bad[k]);
    re4dc_log("%s (checks/hits/bad)\n", line);
}
}
#endif
