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
#include "re4dc_screen.h"
#include "native_actor.hpp"
#if RE4DC_ACTOR_TRANSACTION
#include "actor_native_owner.h"
#endif

#include "actor_lifetime.h"
#ifndef RE4DC_ACTOR_LOG
#define RE4DC_ACTOR_LOG 0
#endif
#if RE4DC_ACTOR_LOG
#include "re4dc_platform.h"
#endif
#include "warp_late.h"
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
class Converter {
public:
    Converter(const Re4dcModelPart& part, const SortSource& sort, u8* out, unsigned out_bytes, Arena scratch, bool lod)
        : p(part), s(sort), out(out), capacity(out_bytes), arena(scratch),
          stride((part.flags & 0x80000000U) ? 8U : 6U), lod(lod) {}

    bool run() {
        if (capacity < sizeof(BlobHeader) + 32 || p.stream_bytes > 0x3FFFCU) ACTOR_REJECT();
        if (!parse()) return false;
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

private:
    struct Strip { u32 a, b; u16 n; u8 mode, pad; };  // mode 0 run, 1 quad (1,2,0,3), 2 fan triangle
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
    unsigned used = 0, size = 0, meshlets = 0, triangles = 0, uv_excess = 0;
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
        return k == 0 ? p.stream + t.a : p.stream + t.b + (k - 1) * stride;
    }
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
                 bool keep_order, u16* strip_meshlet, Emit&& emit) {
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
                    if (nrec + distinct[j] - score[j] > kMaxVertices || nidx + n[j] > kMaxIndices) continue;
                    if (score[j] > best_score || (score[j] == best_score && j < best)) { best = j; best_score = score[j]; }
                }
                if (best == ~0U) {
                    // Nothing adjacent fits (always, in keep_order mode): the
                    // first unused strip in order, if it fits.
                    while (next < count && done[next]) ++next;
                    if (next < count) {
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
                     }))
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
            unsigned a = unsigned(x < 0 ? -x : x), bits = 0;
            if (!a) continue;
            while (!(a & 1U)) a >>= 1;  // significant bits: trailing zeros dropped
            while (a >> bits) ++bits;
            if (bits > 8 && bits - 8 > uv_excess) uv_excess = bits - 8;
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

// ----------------------------------------------------------- skin registry --
struct SkinEntry { const void* info; const void* positions; const float* palette; unsigned entries, materialized; };
constexpr unsigned kSkins = 64;
SkinEntry skins[kSkins];
unsigned skin_count = 0, skin_frame = ~0U;
SkinEntry* find_skin(const void* info, const void* positions) {
    for (unsigned i = 0; i < skin_count; ++i)
        if (skins[i].info == info && skins[i].positions == positions) return &skins[i];
    return nullptr;
}


#if RE4DC_ACTOR_TRANSACTION
#include "include/native_actor_owner_registry.inc"
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
            same_words(f.viewport, p.viewport, 6)) {
            // Mode is a function of (info, positions) within a frame.
            return &f;
        }
    Frame& f = frames[frame_victim]; frame_victim = (frame_victim + 1) % kFrames;
    f = Frame{};
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
            // One skin table at a time (parts arrive info by info): an older
            // skinned Frame is dropped from the cache and its table reused.
            for (Frame& o : frames)
                if (&o != &f && o.skin_positions) {
                    o.frame = ~0U; o.skin_positions = o.skin_dirs = nullptr; o.skin_ready = o.dirs_ready = nullptr;
                }
            workspace_end = workspace_bytes;
            f.skin_positions = static_cast<float*>(frame_table(entries * (28U * 4U + 2U)));
            if (f.skin_positions) {
                f.skin_dirs = f.skin_positions + entries * 16U;
                f.skin_ready = reinterpret_cast<u8*>(f.skin_dirs + entries * 12U);
                f.dirs_ready = f.skin_ready + entries;
                std::memset(f.skin_ready, 0, entries * 2U);
#if RE4DC_AVK
                f.avk_all = false;
#endif
                f.dirs_fold[0] = NAN;  // no directions built yet
            }
            ++stats.skinned_parts;
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
    bool fast = false;       // directional fold valid: diffuse clamp, <=3 lights, caps 255
    bool constant = false;   // lighting disabled: one colour for every vertex
    unsigned count = 0;
    u32 constant_rgb = 0;
    float dir[3][4]{};       // normal space, x nq (w = 0)
    alignas(8) float color[16]{};
    const SourceLighting* source = nullptr;
    re4dc::render::PreparedSourceLights prepared;
    float view_dot[3]{};     // light . direction from the part centre to the camera (view space)
};

bool build_lights(const Re4dcModelPart& p, const Frame& f, const float center[3], Lights& L) {
    const SourceLighting& S = *p.lighting;
    L = Lights{};
    L.source = &S;
    constexpr float k = 1.0f / 255.0f;
    float scale[3], ambient[3];
    bool caps255 = true;
    for (unsigned c = 0; c < 3; ++c) {
        scale[c] = S.material[c] * k * S.tev_scale * 255.0f;
        ambient[c] = S.enable ? S.ambient[c] * k : 1.0f;
        caps255 &= scale[c] >= 255.0f;
    }
    if (S.ambient_vertex || S.material_vertex) return false;  // per-vertex colour: slow path
    if (!S.enable) {
        L.constant = true;
        L.constant_rgb = (channel(std::min(ambient[0], 1.0f) * scale[0]) << 16) |
                         (channel(std::min(ambient[1], 1.0f) * scale[1]) << 8) | channel(std::min(ambient[2], 1.0f) * scale[2]);
        return true;
    }
    if (S.diffuse != 2 || !caps255) return false;
    const float* m = p.modelview;
    const float px = m[0] * center[0] + m[1] * center[1] + m[2] * center[2] + m[3];
    const float py = m[4] * center[0] + m[5] * center[1] + m[6] * center[2] + m[7];
    const float pz = m[8] * center[0] + m[9] * center[1] + m[10] * center[2] + m[11];
    const float* N = S.normal_matrix;
    float col[3][3]{};
    const float c2 = px * px + py * py + pz * pz, cr = c2 > 0.0f ? -1.0f / std::sqrt(c2) : 0.0f;
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
        if (L.count == 3) return false;  // fourth significant light: slow path
        float* o = L.dir[L.count];
        o[0] = (N[0] * lx + N[4] * ly + N[8] * lz) * f.nq;
        o[1] = (N[1] * lx + N[5] * ly + N[9] * lz) * f.nq;
        o[2] = (N[2] * lx + N[6] * ly + N[10] * lz) * f.nq;
        o[3] = 0.0f;
        L.view_dot[L.count] = (lx * px + ly * py + lz * pz) * cr;
        col[L.count][0] = red; col[L.count][1] = green; col[L.count][2] = blue;
        ++L.count;
    }
    // Colour matrix (matrix_t: [column][row]); input (m0, m1, m2, 1).
    for (unsigned l = 0; l < 3; ++l)
        for (unsigned c = 0; c < 3; ++c) L.color[l * 4 + c] = 0.5f * col[l][c] * scale[c];
    for (unsigned c = 0; c < 3; ++c) L.color[12 + c] = ambient[c] * scale[c];
    L.fast = true;
    ++stats.light_sets;
    return true;
}

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
#if RE4DC_TA_HASH
    // TA_HASH (test builds): a store-queue meshlet's words as every copy below sends them: the cache entry with its
    // flags word from index bit 7 (EOL ends a strip). Whole meshlets (Part::whole, the common direct case and the
    // ONE_SUBMIT window) were the actor fast path's unhashed writer (review 2026-10-04).
    if constexpr (SQ) {
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
    const std::uint32_t eol = PVR_CMD_VERTEX_EOL;
#if RE4DC_TA_HASH
    // TA_HASH (test builds): the words this strip sends (EOL in the last flags word), as re4dc_ta_put hashes its own.
    for (unsigned k = 0; k < n; ++k) {
        std::uint32_t w[8];
        __builtin_memcpy(w, cache + (index[k] & 127u), 32);
        if (k + 1 == n) w[0] = eol;
        re4dc_ta_hash(w, 32);
    }
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
void world_of(const Frame& f, const Re4dcModelPart& p, const Records& r, unsigned i, float w[3], float n[3]) {
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
        w[4] = ((u + 0x8000U) & 0xFFFF0000U) | ((t + 0x8000U) >> 16);
    }
}
// With no scroll and a power-of-two image (u_scale 1), u = raw x 2^-k: its
// bf16 is exact when raw has <= 8 significant bits and otherwise off by up to
// 2^(excess-1) raw units = 2^(excess-1) x uv_scale x size texels, which must
// stay within half a texel. Scrolled or padded textures keep 32-bit UV.
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

struct Part {
    const Re4dcModelPart& p;
    Frame& f;
    Projection projection;
    re4dc::render::ClipParameters clip;
    Re4dcModelPacket packet{};
    Cache cache{};
    unsigned used = 0, input = 0, output = 0, primed = 0;
    bool streaming = false, committed = false;
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

    bool flush() {
        if (!streaming) return false;
        re4dc_model_packet_commit(used); committed = true;
        used = 0; ++stats.flushes;
        return true;
    }
    bool room(unsigned n) {
#if RE4DC_ACTOR_DIRECT
        if (direct) return slots + n <= 32767U;
#endif
        return packet.capacity - used >= n || (flush() && packet.capacity >= n);
    }
    pvr_vertex_t* at() { return static_cast<pvr_vertex_t*>(packet.vertices) + used; }
    void put(const pvr_vertex_t* v, unsigned n) {  // prepared vertices (clipped triangles)
#if RE4DC_ACTOR_DIRECT
#if RE4DC_COARSE_ONE_SUBMIT == 2
        if (direct) one_tap_put(cache.v, v, n);
#endif
        if (direct) { sq = re4dc_ta_put(sq, v, n); slots += n; return; }
#endif
        std::memcpy(at(), v, n * sizeof(pvr_vertex_t)); used += n;
    }
    void strip(const u8* index, unsigned n) {
#if RE4DC_ACTOR_DIRECT
#if RE4DC_COARSE_ONE_SUBMIT == 2
        if (direct) one_tap_strip(cache.v, index, n);
#endif
        if (direct) { sq = emit_sq(sq, cache.v, index, n); slots += n; return; }
#endif
        emit(at(), cache.v, index, n); used += n;
    }
    // A meshlet with no corner outside, beyond far or in front of near.
    bool fits(unsigned n) const {
#if RE4DC_ACTOR_DIRECT
        if (direct) return slots + n <= 32767U;
#endif
        return packet.capacity - used >= n || (streaming && packet.capacity >= n);
    }
    bool whole(const u8* index, unsigned count, unsigned triangles) {
        if (!room(count)) return false;
#if RE4DC_ACTOR_DIRECT
        if (direct) {
#if RE4DC_COARSE_ONE_SUBMIT == 2
            one_tap_meshlet(cache.v, index, count);
#endif
            sq = static_cast<std::uint32_t*>(emit_meshlet<true>(sq, cache.v, index, count)); slots += count;
        } else
#endif
        { emit_meshlet<false>(at(), cache.v, index, count); used += count; }
        input += triangles; output += triangles;
        return true;
    }
    // Flags/oargb words of the cache entries (the passes never write them).
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
        ++stats.fallback_runs;
        for (unsigned t = 0; t + 2 < n; ++t) {
            unsigned tri[3] = {t, t + 1, t + 2};
            if (t & 1) std::swap(tri[0], tri[1]);  // strip parity
            re4dc::render::RenderVertex in[3];
            float opacity[3];
            for (unsigned k = 0; k < 3; ++k) {
                const unsigned li = index[tri[k]] & 127U;
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
            ++stats.fallback_triangles;
            if (uv16) pack_uv16(triangles, 3 * m, false);
            if (m && !room(3 * m)) return false;
            put(triangles, 3 * m);
            output += m;
        }
        return true;
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
unsigned avk_positions(Part& e, const Records& r, unsigned n, const PosConst& k, bool s16_uv) {
    Frame& f = e.f;
    const bool skin = f.mode == kSkin;
    // The kernels sign-extend the u16 record fields (mov.w), as ACTOR_POS_ASM does.
#if RE4DC_AVK_RIGID6
    // AVK_RIGID6 (game30.mk): rigid parts with stride 6 positions (kPos6) take the pipelined rigid6 kernels.
    const bool six = !skin && f.position_stride == 6;
    if (!n || (f.position_stride != 8 && !six) || f.position_count > 32768U || (skin && !f.skin_positions)) return 0;
#else
    if (!n || f.position_stride != 8 || f.position_count > 32768U || (skin && !f.skin_positions)) return 0;
#endif
    AvkPos a;
    a.pos = f.positions; a.uv = e.p.uv; a.rs = r.stride * 2U;
    a.matrix = skin ? f.skin_positions : f.screen; a.ready = f.skin_ready; a.entries = f.palette_entries;
    a.width = k.width; a.height = k.height; a.near_distance = k.near_distance; a.far_distance = k.far_distance;
    a.au = k.au; a.bu = k.bu; a.av = k.av; a.bv = k.bv;
#if RE4DC_AVK_RIGID6
    unsigned (*const kernel)(const AvkPos*) = skin ? (s16_uv ? re4dc_avk_pos_skin_s16 : re4dc_avk_pos_skin_u16)
                                            : six  ? (s16_uv ? re4dc_avk_pos_rigid6_s16 : re4dc_avk_pos_rigid6_u16)
                                                   : (s16_uv ? re4dc_avk_pos_rigid_s16 : re4dc_avk_pos_rigid_u16);
#else
    unsigned (*const kernel)(const AvkPos*) = skin ? (s16_uv ? re4dc_avk_pos_skin_s16 : re4dc_avk_pos_skin_u16)
                                                   : (s16_uv ? re4dc_avk_pos_rigid_s16 : re4dc_avk_pos_rigid_u16);
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
    const unsigned why =
#if RE4DC_ACTOR_LIGHT_N16 == 2
        n16_ref ? unsigned(kN16Ref) :
#endif
        e.colors ? unsigned(kN16Colors)
        : (skin ? ns != 8U : (ns != 8U && ns != 6U)) ? unsigned(kN16Stride)
        : f.normal_count > 32768U ? unsigned(kN16Count)
        : (skin && !f.skin_dirs) ? unsigned(kN16NoTable) : unsigned(kN16Kernel);
#if RE4DC_ACTOR_LIGHT_N16 == 2
    ++n16_meshlets[why]; n16_vertices[why] += n;
    if (why == kN16Kernel) n16_kind_vertices[skin ? 0 : ns == 6U ? 2 : 1] += n;
#endif
    if (why != kN16Kernel || !n) return 0;
    AvkLight a;
    a.nrm = f.normals; a.rs = r.stride * 2U; a.color = L.color; a.alpha = e.alpha;
    a.dirs = skin ? f.skin_dirs : &L.dir[0][0]; a.ready = f.dirs_ready; a.entries = f.palette_entries;
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin_n16
                                              : ns == 6U ? re4dc_avk_light_rigid_n16s6 : re4dc_avk_light_rigid_n16;
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
#if RE4DC_AVK_RIGID6
    const bool three = !skin && f.normal_stride == 3;  // AVK_RIGID6: rigid stride-3 normals (kNrm3)
    if (!n || !f.small_normals || e.colors || (f.normal_stride != 4 && !three) || f.normal_count > 32768U ||
        (skin && !f.skin_dirs))
        return 0;
#else
    if (!n || !f.small_normals || e.colors || f.normal_stride != 4 || f.normal_count > 32768U || (skin && !f.skin_dirs))
        return 0;
#endif
    AvkLight a;
    a.nrm = f.normals; a.rs = r.stride * 2U; a.color = L.color; a.alpha = e.alpha;
    a.dirs = skin ? f.skin_dirs : &L.dir[0][0]; a.ready = f.dirs_ready; a.entries = f.palette_entries;
#if RE4DC_AVK_RIGID6
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin
                                              : three ? re4dc_avk_light_rigid3 : re4dc_avk_light_rigid;
#else
    unsigned (*const kernel)(const AvkLight*) = skin ? re4dc_avk_light_skin : re4dc_avk_light_rigid;
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
void pass_lights(Part& e, const Lights& L, const Records& r, unsigned n);
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
    static const u8 white[4] = {255, 255, 255, 255};
#if RE4DC_ACTOR_EXACT_FAST
    // ACTOR_EXACT_FAST=1 (render only): evaluate_prepared_source_lighting's arithmetic (source_lighting.cpp) per
    // vertex, with the per-light constants (colour / 255, a, k, position, direction) taken out of the vertex loop,
    // one fsrra for the light distance instead of a square root and three divisions, and one division for the
    // attenuation. Same light order, ambient start, clamp, material and TEV scale; results differ from the reference
    // evaluator only in float rounding (the 8-bit colour, rarely by one step).
    const SourceLighting& S = *L.source;
    const re4dc::render::PreparedSourceLights& P = L.prepared;
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
        world_of(e.f, e.p, r, i, w, nn);
        const u8* color = vertex_colour ? e.p.colors + r.ci(i) * 4 : white;
        const u8* ambient = S.ambient_vertex ? color : S.ambient;
        const u8* material = S.material_vertex ? color : S.material;
        float out0 = S.enable ? ambient[0] / 255.f : 1.f, out1 = S.enable ? ambient[1] / 255.f : 1.f,
              out2 = S.enable ? ambient[2] / 255.f : 1.f;
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
        const float rgb0 = material[0] / 255.f * std::min(std::max(out0, 0.f), 1.f) * S.tev_scale;
        const float rgb1 = material[1] / 255.f * std::min(std::max(out1, 0.f), 1.f) * S.tev_scale;
        const float rgb2 = material[2] / 255.f * std::min(std::max(out2, 0.f), 1.f) * S.tev_scale;
        const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
        e.cache.v[i].argb = a | (channel(rgb0 * 255.0f) << 16) | (channel(rgb1 * 255.0f) << 8) | channel(rgb2 * 255.0f);
    }
    stats.slow_light_vertices += n;
    return;
#endif
    for (unsigned i = 0; i < n; ++i) {
        float w[3], nn[3], rgb[3];
        world_of(e.f, e.p, r, i, w, nn);
        const u8* color = (L.source->ambient_vertex || L.source->material_vertex) && e.p.colors ? e.p.colors + r.ci(i) * 4 : white;
        re4dc::render::evaluate_prepared_source_lighting(w[0], w[1], w[2], nn[0], nn[1], nn[2], *L.source, L.prepared, color, rgb);
        const u32 a = e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha;
        e.cache.v[i].argb = a | (channel(rgb[0] * 255.0f) << 16) | (channel(rgb[1] * 255.0f) << 8) | channel(rgb[2] * 255.0f);
    }
    stats.slow_light_vertices += n;
}

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
    // Rebake: light every level-0 record into its colour field.
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
struct CrowdEntry { const void* model; float distance; unsigned seen; unsigned tier; };
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
    }
    stats.crowd_models = n;
}
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
    return kPrelit && p.blend == 0 && !(p.alpha_state & 256) && p.lighting->enable && !p.lighting->ambient_vertex &&
           !p.lighting->material_vertex && re4dc_actor_model_prelit(p.model, p.info) != 0;
}

// A part of a lazily deferred info (no arrays yet) qualifies only if it will
// run in skin mode (prepare_frame's conditions), so no array is ever read.
bool lazy_skin(const Re4dcModelPart& p) {
    if (!RE4DC_NATIVE_ACTOR_SKIN_LAZY || p.positions || p.position_stride != 6) return false;
    const SkinEntry* e = find_skin(p.info, nullptr);
    Re4dcActorSource src{};
    return e && !e->materialized && e->palette && e->entries && re4dc_actor_model_source(p.info, &src) &&
           src.positions && src.normals && src.position_count == p.position_count &&
           src.normal_count == p.normal_count && bool(src.small_normals) == (p.normal_shift == 6);
}

bool qualifies(const Re4dcModelPart& p) {
    return p.lighting && p.alpha_state <= 511 &&
           (!(p.alpha_state & 256) || ((p.flags & 0x80000000U) && p.colors)) &&
           ((!p.lighting->ambient_vertex && !p.lighting->material_vertex) || ((p.flags & 0x80000000U) && p.colors)) &&
           (!p.lighting->enable || p.lighting->attenuation == 1 || p.lighting->attenuation == 2) &&
           p.shift <= 30 && (p.position_stride == 6 || p.position_stride == 8) &&
           (p.normal_shift == 6 || p.normal_shift == 14) && p.normal_stride >= 3 &&
           p.position_count && p.normal_count && p.stream_bytes <= 1024 * 1024 && p.stream_bytes >= 32 &&
           ((ram(p.positions, p.position_count * p.position_stride) &&
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
        if (!work) { ++stats.workspace_misses; workspace_top = mark; return nullptr; }
        const bool opaque = p.blend == 0;
#if defined(RE4DC_ACTOR_TEST)
        const double t0 = test_now_us();
#endif
        Converter c(p, sort, out, p.stream_bytes, Arena{work, room}, false);
        const bool ok = c.run();
#if defined(RE4DC_ACTOR_TEST)
        const double dt = test_now_us() - t0;
        test_convert_us += dt; test_convert_max_us = std::max(test_convert_max_us, dt);
#endif
        workspace_top = mark;
        if (ok) {
            if (kLodBuild && opaque && lod_budget_frame) out[2] |= kLodPending;  // levels: relod()
            unsigned size = c.bytes();
            if (prelit_candidate(p)) size = add_bake_field(out, size, p.stream_bytes);
            Re4dcActorStreamMutation mutation(p.stream,p.stream_bytes);
            std::memcpy(const_cast<u8*>(p.stream), out, size);
            ++stats.conversions;
            if (c.level_count()) ++stats.lod_parts;
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
    if (!work) { ++stats.workspace_misses; workspace_top = mark; return nullptr; }
    Converter c(p, sort, out, want, Arena{work, rest}, false);  // per submit: no LOD, unbaked
    if (!c.run()) { ++stats.conversion_rejects; workspace_top = mark; return nullptr; }
    workspace_top = unsigned(out - workspace) + ((c.bytes() + 31U) & ~31U);
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
    if (triangles >= kLodMinTriangles && !lod_take(triangles)) return;
    Re4dcActorStreamMutation mutation(p.stream,p.stream_bytes);
    stream[2] &= u8(~kLodPending);
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
    if (!work) { ++stats.workspace_misses; workspace_top = mark; return; }
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
    const bool built = c.run() && c.level_count();
    level_ladder = lod_fractions;
    if (built) {
        unsigned size = c.bytes();
        if (b.flags & kHasBake) size = add_bake_field(out, size, p.stream_bytes);  // rebaked on the next draw
        std::memcpy(stream, out, size);
        ++stats.lod_parts; ++stats.lod_rebuilds;
    }
    workspace_top = mark;
}
}  // namespace

extern "C" void re4dc_actor_frame(void* memory, unsigned bytes) {
#if RE4DC_ACTOR_TRANSACTION
    re4dc_actor_owner_retire(); // before workspace rebinding
#endif

    workspace = static_cast<unsigned char*>(memory);
    workspace_bytes = memory ? bytes & ~31U : 0;
    workspace_top = 0; workspace_end = workspace_bytes;
    ++frame_serial;
    lod_budget = lod_budget_frame;
    lod_wanted_last = lod_wanted; lod_wanted = false;
    if constexpr (kCrowd) crowd_rank();
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
    if (frame != skin_frame) {
#if RE4DC_ACTOR_TRANSACTION
        owned_skin_clear();owned_skin_invalidate_frames();
#endif
        skin_frame = frame; skin_count = 0;
    }
    if (!palette || !entries) return 0;
#if RE4DC_ACTOR_TRANSACTION
    for(unsigned i=0;i<skin_count;++i)if(owned_skins[i].serial && owned_skins[i].info==info)return 0;
#endif
    // Lazy (no arrays): the info's latest Trans() wins, as its pPosBuf would.
    if (!position_buffer)
        if (SkinEntry* e = find_skin(info, nullptr)) {
#if RE4DC_ACTOR_TRANSACTION
            if(owned_skins[unsigned(e-skins)].serial)return 0;
#endif
            *e = {info, nullptr, palette, entries, 0}; ++stats.skin_registered; return 1;
        }
#if RE4DC_ACTOR_TRANSACTION
    for(unsigned i=0;i<skin_count;++i)if(!skins[i].info && !owned_skins[i].serial){
        skins[i]={info,position_buffer,palette,entries,0};++stats.skin_registered;return 1;
    }
#endif
    if (skin_count == kSkins) return 0;
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
    const SkinEntry* e = find_skin(info, position_buffer);
    if (!e || e->materialized) { *entries = 0; return nullptr; }
#if RE4DC_SKIN_PALETTE_LAZY
    re4dc_skin_palette_resolve(e->palette);  // the caller reads it (prepare_frame's skin Frame)
#endif
    *entries = e->entries;
    return e->palette;
}

extern "C" void re4dc_actor_materialize(const Re4dcModelPart* p) {
    if (!p) return;
    SkinEntry* e = find_skin(p->info, p->positions);
    if (!e || e->materialized) return;
    re4dc_skin_materialize(e->info, e->palette);
    e->materialized = 1;
    ++stats.materialized_infos;
#if RE4DC_ACTOR_CENSUS
    if (census_mat_row) *census_mat_row += 1;
#endif
}

#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
extern "C" int re4dc_actor_materialize_lazy(Re4dcModelPart* p) {
    if (!p || p->positions) return 1;
    SkinEntry* e = find_skin(p->info, nullptr);
    if (!e) return 0;
    if (!e->materialized) {
        if (!re4dc_skin_materialize(e->info, e->palette)) return 0;
        e->materialized = 1;
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
extern "C" int re4dc_actor_submit(const Re4dcModelPart* part) {
    ++stats.parts;
#if RE4DC_ACTOR_CENSUS
    census_cur = nullptr; census_mat_row = nullptr;
    if (part) census_note(*part);
#if RE4DC_ACTOR_CENSUS_SKIP_OBJ00
    // Diagnostic A/B only: cObj00 room objects (id 0, ot 0, one part) are not drawn.
    if (part && re4dc_actor_census_key(part->model) == 0x00010000U) { re4dc_model_result(0, 0, 0); return 1; }
#endif
#endif
    if (!part || !qualifies(*part)) { ++stats.declined; RE4DC_CENSUS_DEC(part); return 0; }
    const Re4dcModelPart& p = *part;
    const float near_distance = p.projection[6] / (p.projection[5] - 1.0f);
    const float far_distance = p.projection[6] / p.projection[5];
    if (!re4dc::render::is_finite(near_distance) || !re4dc::render::is_finite(far_distance) ||
        near_distance <= 0.0f || far_distance <= near_distance) { ++stats.declined; RE4DC_CENSUS_DEC(part); return 0; }
    const unsigned mark = workspace_top;
    struct Release { unsigned mark; ~Release() { workspace_top = mark; } } release{mark};
    const BlobHeader* blob = blob_of(p);
    int crowd_class = 0;
    if constexpr (kCrowd) crowd_class = re4dc_actor_model_class(p.model, p.info);
    if (kLodBuild && blob && (blob->flags & kLodPending)) relod(p, crowd_class > 0);
    if (!blob && !(blob = convert(p))) { ++stats.declined; RE4DC_CENSUS_DEC(part); return 0; }
    const u8* base = reinterpret_cast<const u8*>(blob);
    ++stats.handled;
    if (p.cull == 3) { re4dc_model_result(0, 0, 0); return 1; }
    // Translucent parts keep the existing bounded drain; its replay re-enters
    // re4dc_model_submit and lands here again with draining set.
    if (re4dc_model_defer_part(&p)) { ++stats.deferred; return 1; }

    Frame& f = *prepare_frame(p, near_distance, far_distance);
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
        if (depth > cull_far) { ++fog_gate_culled; re4dc_model_result(0, 0, 0); return 1; }
    }
#endif
    if (f.mode == kRigid && blob->radius > 0.0f) {
        // Whole-part depth test of the bind-pose sphere (bind == drawn pose).
        const float* m = p.modelview; const float* c = blob->center;
        const float z = m[8] * c[0] + m[9] * c[1] + m[10] * c[2] + m[11];
        if (-z + blob->radius < near_distance || -z - blob->radius > far_distance) {
            ++stats.culled_parts; re4dc_model_result(0, 0, 0); return 1;
        }
    }
    Part e{p, f, {p.projection, p.viewport}, {near_distance, far_distance, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF, project, nullptr}};
    e.clip.context = &e.projection;
    e.streaming = re4dc_model_packet_streaming() != 0;
    if (!re4dc_model_packet_reserve(&p, &e.packet)) { re4dc_model_result(2, 0, 0); return 1; }
#if RE4DC_ACTOR_UV16
    // Consumed by the begin call below (direct or packet), whatever its result.
    e.uv16 = uv16_safe(p, *blob);
    if (e.uv16) ++stats.uv16_parts;
    const u32 pcw_set = kPcwStripLength6 | (e.uv16 ? kPcwUv16 : 0U), pcw_clear = kPcwStripLength6 | kPcwUv16;
    re4dc_model_next_header_pcw(pcw_set, pcw_clear);
#endif
#if RE4DC_ACTOR_DIRECT
    Re4dcModelDirect direct{};
    if (re4dc_model_direct_enabled() && re4dc_model_direct_begin(&p, &direct)) {
        if (direct.scratch_capacity < kCacheSlots) {
            // Nothing sent yet beyond the header: an empty part.
            re4dc_model_direct_end(0); re4dc_model_result(2, 0, 0); return 1;
        }
        e.direct = true; e.sq = direct.sq;
        e.packet.u_scale = direct.u_scale; e.packet.v_scale = direct.v_scale;
        e.cache.v = static_cast<pvr_vertex_t*>(direct.scratch);
    } else
#endif
    {
#if RE4DC_ACTOR_UV16
        re4dc_model_next_header_pcw(pcw_set, pcw_clear);
#endif
        if (!re4dc_model_packet_begin(&p, &e.packet) || e.packet.capacity < kCacheSlots + 64U) {
            re4dc_model_result(2, 0, 0);
            return 1;
        }
        e.packet.capacity -= kCacheSlots;
        e.cache.v = static_cast<pvr_vertex_t*>(e.packet.vertices) + e.packet.capacity;
    }
    e.cache.oc = reinterpret_cast<u8*>(e.cache.v + kMaxVertices);

    Lights lights;
    if (!build_lights(p, f, blob->center, lights)) lights.prepared = re4dc::render::prepare_actor_lights(*p.lighting);
    lights.source = p.lighting;
    const unsigned tier = crowd_class > 0 ? crowd_tier(p, crowd_class) : kTierFull;
    if (tier >= (kCrowdFlat ? kTierNear : kTierMid) && tier != kTierFull && lights.fast && !lights.constant) {
        lights.constant = true;
        lights.constant_rgb = part_colour(lights);
    }
    // Skinned directions follow the part's light fold; parts of one info whose
    // folds agree within kDirTolerance of the largest direction (light
    // directions from nearby part centres) keep the entries already built.
    if (f.skin_dirs && !lights.constant) {
        float dmax = 0.0f;
        for (unsigned i = 0; i < 12; ++i) dmax = std::max(dmax, std::fabs(lights.dir[i / 4][i % 4]));
        if (!near_vec(&lights.dir[0][0], f.dirs_fold, 12, dmax * kDirTolerance)) {
            std::memset(f.dirs_ready, 0, f.palette_entries);
            std::memcpy(f.dirs_fold, &lights.dir[0][0], sizeof(f.dirs_fold));
            ++stats.skin_dir_sets;
        }
    }
    const bool s16_uv = (p.flags & 0x80000000U) != 0;
    const float uv_scale = s16_uv ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const PosConst k{0.0f, uv_scale * e.packet.u_scale, p.uv_offset[0] * e.packet.u_scale,
                     uv_scale * e.packet.v_scale, p.uv_offset[1] * e.packet.v_scale, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF,
                     near_distance, far_distance};
    e.colors = (p.alpha_state & 256) ? p.colors : nullptr;
    e.alpha = u32(p.alpha_state & 255) << 24;
    const auto* table = reinterpret_cast<const MeshletInfo*>(base + sizeof(BlobHeader));
    const unsigned rs = 3U + ((blob->flags & kHasCi) ? 1U : 0U) + ((blob->flags & kHasBake) ? 1U : 0U);
    const unsigned color_index = blob->color_index;
    const unsigned level = tier == kTierFar ? blob->levels
                           : select_level(p, *blob, near_distance, tier == kTierMid ? crowd_mid_tau : RE4DC_NEAR_LOD_TAU);
    const LevelInfo* li = level ? reinterpret_cast<const LevelInfo*>(base + blob->lod4 * 4U) + (level - 1) : nullptr;
    const MeshletLevel* lt = li ? reinterpret_cast<const MeshletLevel*>(base + li->table4 * 4U) : nullptr;
    const u8* lists = li ? base + li->lists4 * 4U : base + blob->idx4 * 4U;
    const u8* records = base + blob->rec4 * 4U;
    unsigned bake_scale[3];
    const BakeUse bake = kPrelit && (blob->flags & kHasBake) && blob->bake4 && lights.fast && !lights.constant && !e.colors
        ? bake_prepare(e, lights, *blob, rs, bake_scale) : kBakeNone;
    ++stats.lod_draws[level];
    if (kCrowd) ++stats.crowd_parts[tier];
    bool ok = true;
    for (unsigned mi = 0; ok && mi < blob->meshlets; ++mi) {
        const MeshletInfo& m = table[mi];
        const Counts c = lt ? lt[mi].n : m.n;
        const unsigned nv = c.vertices(), ni = c.indices(), nt = c.triangles();
        if (!ni) continue;  // wholly collapsed at this level
        const Records r{reinterpret_cast<const u16*>(records) + m.first * rs, rs, color_index, (blob->flags & kHasCi) != 0};
        const u8* index = lists + (lt ? lt[mi].index : m.index);
        ++stats.meshlets; stats.vertices += nv; stats.corners += ni; stats.triangles += nt;
        if (kCrowd) stats.crowd_triangles[tier] += nt;
#if RE4DC_ACTOR_CENSUS
        if (census_cur) { census_cur->nv += nv; census_cur->nt += nt; census_cur->lvl += level; }
#endif
        unsigned all, any;
        pass_positions(e, r, nv, k, s16_uv, all, any);
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
        if (lights.constant) {
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
            for (unsigned i = 0; i < nv; ++i)
                e.cache.v[i].argb = (e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha) | lights.constant_rgb;
        } else if (bake != kBakeNone) {
            pass_baked(e, r, nv, bake == kBakeScaled ? bake_scale : nullptr);
        } else if (lights.fast) {
            pass_lights(e, lights, r, nv);
        } else {
            pass_lights_exact(e, lights, r, nv);
        }
        if (bake == kBakeNone) stats.normals_lit += nv;
        if (any & kOcNear) ++stats.meshlets_clipped;
        if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; ok = e.whole(index, ni, nt); }
        else ok = e.strips(r, index, ni);
    }
#if RE4DC_ACTOR_DIRECT
    if (e.direct) {
        if (!ok) re4dc_model_packet_abort();
        re4dc_model_direct_end(e.slots);
        re4dc_model_result(ok ? 0 : 3, e.input, ok ? e.output : 0);
        return 1;
    }
#endif
    if (!ok) {
        if (e.committed) re4dc_model_packet_abort();
        re4dc_model_result(3, e.input, 0);
        return 1;
    }
    re4dc_model_packet_commit(e.used);
    re4dc_model_result(0, e.input, e.output);
    return 1;
}

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
#if !RE4DC_ACTOR_DIRECT || RE4DC_ACTOR_UV16 || !RE4DC_NATIVE_ACTOR_SKIN_LAZY || (defined(RE4DC_TA_GUARD) && RE4DC_TA_GUARD)
#error "COARSE_ONE_SUBMIT needs NATIVE_ACTOR_DIRECT=1 NATIVE_ACTOR_SKIN_LAZY=1 NATIVE_ACTOR_UV16=0 TA_GUARD=0 (a window is one guarded part)"
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
    return se && !se->materialized && se->palette && se->entries && re4dc_actor_model_source(p.info, &src) &&
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
            same_words(f.viewport, p.viewport, 6))
            return f;
    Frame& f = frames[frame_victim]; frame_victim = (frame_victim + 1) % kFrames;
    f = Frame{};
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
    for (Frame& o : frames)
        if (&o != &f && o.skin_positions) {
            o.frame = ~0U; o.skin_positions = o.skin_dirs = nullptr; o.skin_ready = o.dirs_ready = nullptr;
        }
    workspace_end = workspace_bytes;
    const unsigned entries = se.entries;
    f.skin_positions = static_cast<float*>(frame_table(entries * (28U * 4U + 2U)));
    if (f.skin_positions) {
        f.skin_dirs = f.skin_positions + entries * 16U;
        f.skin_ready = reinterpret_cast<u8*>(f.skin_dirs + entries * 12U);
        f.dirs_ready = f.skin_ready + entries;
        std::memset(f.skin_ready, 0, entries * 2U);
#if RE4DC_AVK
        f.avk_all = false;
#endif
        f.dirs_fold[0] = NAN;  // no directions built yet
    }
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
    bool open = false;
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
    re4dc_model_direct_end(w.slots);
    w.open = false; w.slots = 0; w.primed = 0;
}

// re4dc_actor_submit() for one chunk, sent into the window (opened here when closed): 1 / 0 as that call
// would return; -1 when the part is not an array-less (lazily skinned) part: nothing done.
#if RE4DC_LEON_NATIVE_PIPE
// LEON_NATIVE_PIPE (native_actor_leon_pipe.inc): known != nullptr hands in one_qualifies' result (its registry entry
// and source), which the caller's preflight proved for this part; one_chunk(p, w) below is the unchanged call.
int one_chunk_core(Re4dcModelPart& p, OneWindow& w, const SkinEntry* known, const Re4dcActorSource* known_src) {
    if (p.positions) return -1;
    ++stats.parts;
    const SkinEntry* se = nullptr;
    Re4dcActorSource src{};
    if (known) { se = known; src = *known_src; }
    else if (!one_qualifies(p, se, src)) { ++stats.declined; return 0; }
#else
int one_chunk(Re4dcModelPart& p, OneWindow& w) {
    if (p.positions) return -1;
    ++stats.parts;
    const SkinEntry* se = nullptr;
    Re4dcActorSource src{};
    if (!one_qualifies(p, se, src)) { ++stats.declined; return 0; }
#endif
    const float near_distance = p.projection[6] / (p.projection[5] - 1.0f);
    const float far_distance = p.projection[6] / p.projection[5];
    if (!re4dc::render::is_finite(near_distance) || !re4dc::render::is_finite(far_distance) ||
        near_distance <= 0.0f || far_distance <= near_distance) { ++stats.declined; return 0; }
    const unsigned mark = workspace_top;
    struct Release { unsigned mark; ~Release() { workspace_top = mark; } } release{mark};
    const BlobHeader* blob = blob_of(p);
    int crowd_class = 0;
    if constexpr (kCrowd) crowd_class = re4dc_actor_model_class(p.model, p.info);
    if (kLodBuild && blob && (blob->flags & kLodPending)) relod(p, crowd_class > 0);
    if (!blob && !(blob = convert(p))) { ++stats.declined; return 0; }
    const u8* base = reinterpret_cast<const u8*>(blob);
    ++stats.handled;
    if (p.cull == 3) { re4dc_model_result(0, 0, 0); return 1; }
#if RE4DC_ACTOR_TRANSACTION
    if (!owned_submission && re4dc_model_defer_part(&p)) { ++stats.deferred; return 1; }
#else
    if (re4dc_model_defer_part(&p)) { ++stats.deferred; return 1; }
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
    Part e{p, f, {p.projection, p.viewport}, {near_distance, far_distance, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF, project, nullptr}};
    e.clip.context = &e.projection;
    e.streaming = re4dc_model_packet_streaming() != 0;
    if (!w.open) {
        if (!re4dc_model_packet_reserve(&p, &e.packet)) { re4dc_model_result(2, 0, 0); return 1; }
        if (re4dc_model_direct_enabled() && re4dc_model_direct_begin_reserved(&p, &e.packet, &w.direct)) {
            if (w.direct.scratch_capacity < kCacheSlots) {
                re4dc_model_direct_end(0); re4dc_model_result(2, 0, 0); return 1;
            }
            w.open = true; w.sq = w.direct.sq; w.slots = 0; w.primed = 0;
        } else {
            if (!re4dc_model_packet_begin(&p, &e.packet) || e.packet.capacity < kCacheSlots + 64U) {
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

    const SourceLighting& S = *p.lighting;
    const bool constant_source = !S.enable && !S.ambient_vertex && !S.material_vertex;
    Lights* lp = constant_source ? &w.lights : &w.lit;
    if (!constant_source || !w.lights_ready || w.lights.source != p.lighting) {
        if (!build_lights(p, f, blob->center, *lp)) lp->prepared = re4dc::render::prepare_actor_lights(*p.lighting);
        lp->source = p.lighting;
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
    if (tier >= (kCrowdFlat ? kTierNear : kTierMid) && tier != kTierFull && lights.fast && !lights.constant) {
        lights.constant = true;  // never the window's record: lights.fast is false for constant lighting
        lights.constant_rgb = part_colour(lights);
    }
    if (f.skin_dirs && !lights.constant) {
        float dmax = 0.0f;
        for (unsigned i = 0; i < 12; ++i) dmax = std::max(dmax, std::fabs(lights.dir[i / 4][i % 4]));
        if (!near_vec(&lights.dir[0][0], f.dirs_fold, 12, dmax * kDirTolerance)) {
            std::memset(f.dirs_ready, 0, f.palette_entries);
            std::memcpy(f.dirs_fold, &lights.dir[0][0], sizeof(f.dirs_fold));
            ++stats.skin_dir_sets;
        }
    }
    const bool s16_uv = (p.flags & 0x80000000U) != 0;
    const float uv_scale = s16_uv ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const PosConst k{0.0f, uv_scale * e.packet.u_scale, p.uv_offset[0] * e.packet.u_scale,
                     uv_scale * e.packet.v_scale, p.uv_offset[1] * e.packet.v_scale, RE4DC_SCREEN_WF, RE4DC_SCREEN_HF,
                     near_distance, far_distance};
    e.colors = (p.alpha_state & 256) ? p.colors : nullptr;
    e.alpha = u32(p.alpha_state & 255) << 24;
    const unsigned rs = 3U + ((blob->flags & kHasCi) ? 1U : 0U) + ((blob->flags & kHasBake) ? 1U : 0U);
    const unsigned color_index = blob->color_index;
    const unsigned level = tier == kTierFar ? blob->levels
                           : select_level(p, *blob, near_distance, tier == kTierMid ? crowd_mid_tau : RE4DC_NEAR_LOD_TAU);
    const LevelInfo* li = level ? reinterpret_cast<const LevelInfo*>(base + blob->lod4 * 4U) + (level - 1) : nullptr;
    const MeshletLevel* lt = li ? reinterpret_cast<const MeshletLevel*>(base + li->table4 * 4U) : nullptr;
    const u8* lists = li ? base + li->lists4 * 4U : base + blob->idx4 * 4U;
    const u8* records = base + blob->rec4 * 4U;
    unsigned bake_scale[3];
    const BakeUse bake = kPrelit && (blob->flags & kHasBake) && blob->bake4 && lights.fast && !lights.constant && !e.colors
        ? bake_prepare(e, lights, *blob, rs, bake_scale) : kBakeNone;
    ++stats.lod_draws[level];
    if (kCrowd) ++stats.crowd_parts[tier];
    bool ok = true;
    for (unsigned mi = 0; ok && mi < blob->meshlets; ++mi) {
        const MeshletInfo& m = table[mi];
        const Counts c = lt ? lt[mi].n : m.n;
        const unsigned nv = c.vertices(), ni = c.indices(), nt = c.triangles();
        if (!ni) continue;  // wholly collapsed at this level
        const Records r{reinterpret_cast<const u16*>(records) + m.first * rs, rs, color_index, (blob->flags & kHasCi) != 0};
        const u8* index = lists + (lt ? lt[mi].index : m.index);
        ++stats.meshlets; stats.vertices += nv; stats.corners += ni; stats.triangles += nt;
        if (kCrowd) stats.crowd_triangles[tier] += nt;
        unsigned all, any;
        pass_positions(e, r, nv, k, s16_uv, all, any);
        if (all & kOcCull) {
            ++stats.meshlets_culled;
            e.input += nt;
            continue;
        }
        e.prime(nv);
        if (lights.constant) {
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
            for (unsigned i = 0; i < nv; ++i)
                e.cache.v[i].argb = (e.colors ? u32(e.colors[r.ci(i) * 4 + 3]) << 24 : e.alpha) | lights.constant_rgb;
        } else if (bake != kBakeNone) {
            pass_baked(e, r, nv, bake == kBakeScaled ? bake_scale : nullptr);
        } else if (lights.fast) {
            pass_lights(e, lights, r, nv);
        } else {
            pass_lights_exact(e, lights, r, nv);
        }
        if (bake == kBakeNone) stats.normals_lit += nv;
        if (any & kOcNear) ++stats.meshlets_clipped;
        if (!(any & (kOcCull | kOcNear)) && e.fits(ni)) { ++stats.meshlets_whole; ok = e.whole(index, ni, nt); }
        else ok = e.strips(r, index, ni);
    }
    if (e.direct) {
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
