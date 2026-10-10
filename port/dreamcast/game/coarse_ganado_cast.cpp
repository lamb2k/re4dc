// COARSE_GANADO_CAST=1 (with COARSE_GANADO=1; render only): the Ganados draw the external cast's
// per-appearance meshes instead of the one retargeted 874-triangle mesh of coarse_ganado.cpp, which this
// file replaces in the link. Input: ganado_cast_runtime.h from a private bundle in COARSE_ACTOR_ASSET_DIR
// (generated outside the repository from the cast packs): per appearance four chunks in the source info
// order (body, head, right hand, left hand), the appearance's inverse bind, the source infos' signatures
// and the atlas key. An actor draws the appearance whose body and head signatures its source infos carry;
// a hand info with any cast hand-pose signature draws that appearance's default hand for its side (hand
// poses are not integrated yet). The game owns the pose, part visibility and simulation; nothing here
// reaches game logic. =2 (check build): the 874 adapter's matcher runs beside every attempt and "GCAST"
// lines count both / cast only / 874 only / neither, per-role disagreements, the appearances drawn and
// skeletons whose rest translations differ from the appearance's bind.
#include "re4dc_screen.h"
#include "global.h"
#include "model.h"
#include "native_actor.hpp"
#include "ganado_cast_runtime.h" // private generated bundle, outside the repository
#if RE4DC_CROWD_FAR
#include "ganado_far_runtime.h" // lane crowd far tier, private generated (tools/d367/crowd/far_header.py)
#endif
#include <cstring>
#include <kos/fs.h>
#if RE4DC_COARSE_GANADO_CAST == 2
#include <cstdio>
#include "ganado874_runtime.h"
#include "ganado874_variants.h"
#endif
#if RE4DC_COARSE_SKIN_FTRV
#include "coarse_skin.h"
#endif
#if RE4DC_CHARBAKE_TOGGLE
#include "charbake_variants.h" // charbake.mk CHARBAKE_TOGGLE: the character texture variants (keys only)
#endif

extern "C" void re4dc_log(const char*, ...);
extern "C" void GXGetProjectionv(float*);
extern "C" void GXGetViewportv(float*);
extern "C" void re4dc_bind_actor_frame();
extern "C" int re4dc_coarse_leon_texture_ready(const Re4dcUiImage*,unsigned,unsigned);
#if RE4DC_ACTOR_EARLY_COARSE
#include "actor_early_coarse.h"
extern "C" void re4dc_model_packet_abort();
namespace { bool owner_ganado_bind(cModel*); }
#endif

namespace {
namespace gc = ganadocast;
constexpr unsigned kApps = gc::appearance_count, kBones = gc::bone_count;
static_assert(kBones == 34, "the coarse Ganado skeleton");
#if RE4DC_CROWD_FAR
// Lane crowd far tier (crowd.mk CROWD_FAR_M / CROWD_NEAR_MAX; render only, a look change): appearance indexes
// kApps..2 kApps-1 are the far bundle's appearances (ganadocast::far, tools/d367/crowd/far_header.py) in the near
// order. They share the near skeleton, bind and atlas (far_same checks it before a far appearance's first use; a
// mismatch never draws far: its skin_init fails and the owner plan keeps the near appearance).
constexpr unsigned kTierApps = kApps * 2, kFarSkinBytes = gc::far::skin_stream_bytes;
static_assert(gc::far::appearance_count == kApps && gc::far::bone_count == kBones, "far tier layout");
inline const gc::Chunk& cast_chunk(unsigned a, unsigned i) { return a < kApps ? gc::chunks[a][i] : gc::far::chunks[a - kApps][i]; }
inline unsigned cast_app(unsigned a) { return a < kApps ? a : a - kApps; }
// The near texture index holding far appearance x's atlas (the far bundle's atlases must be near atlases too:
// the near PS2 em15-00 bundle adds its own atlas, the far tier keeps the cast's), or texture_count.
unsigned far_texture(unsigned x) {
    const auto& f = gc::far::textures[gc::far::appearance_texture[x]];
    for (unsigned t = 0; t < gc::texture_count; ++t)
        if (gc::textures[t].crc == f.crc && gc::textures[t].fnv == f.fnv && gc::textures[t].width == f.width &&
            gc::textures[t].height == f.height) return t;
    return gc::texture_count;
}
bool far_same(unsigned a) {
    const unsigned x = cast_app(a);
    return !std::strcmp(gc::far::appearance_names[x], gc::appearance_names[x]) &&
        !std::memcmp(gc::far::bind[x], gc::bind[x], sizeof(gc::bind[x])) && !std::memcmp(gc::far::parents, gc::parents, sizeof(gc::parents)) &&
        far_texture(x) < gc::texture_count;
}
#else
constexpr unsigned kTierApps = kApps, kFarSkinBytes = 0;
inline const gc::Chunk& cast_chunk(unsigned a, unsigned i) { return gc::chunks[a][i]; }
inline unsigned cast_app(unsigned a) { return a; }
#endif
#if RE4DC_CHARBAKE_TOGGLE
// charbake.mk CHARBAKE_TOGGLE (test builds): the selected variant (re4dc_charbake_ganado_set, from coarse_actor.cpp
// re4dc_charbake_set) gives the cast atlas (charbake_variants.h kGanadoCrc / kGanadoFnv) its key, read by the plans,
// the texture key hook and the readiness check, and every cast image its own identity per variant (the texture cache
// keeps the first key of an identity). far_texture keeps matching the bundle keys.
unsigned texture_tokens[re4dc_charbake::kCount][gc::texture_count];
unsigned charbake_variant=RE4DC_CHARBAKE_VARIANT%re4dc_charbake::kCount;
#define RE4DC_GC_TOKEN(t) (&texture_tokens[charbake_variant][t])
gc::Texture charbake_textures[gc::texture_count];
bool charbake_ready;
const gc::Texture* charbake_keys(){
    if(!charbake_ready){
        const auto& e=re4dc_charbake::variants[charbake_variant];
        for(unsigned t=0;t<gc::texture_count;++t) {
            charbake_textures[t]=gc::textures[t];
            if(gc::textures[t].crc==re4dc_charbake::kGanadoCrc && gc::textures[t].fnv==re4dc_charbake::kGanadoFnv)
                {charbake_textures[t].crc=e.ganado_crc;charbake_textures[t].fnv=e.ganado_fnv;}
        }
        charbake_ready=true;
    }
    return charbake_textures;
}
#define RE4DC_GC_KEYS charbake_keys()
#else
unsigned texture_token[gc::texture_count];
#define RE4DC_GC_TOKEN(t) (&texture_token[t])
#define RE4DC_GC_KEYS gc::textures
#endif
Re4dcUiImage image_of(unsigned t){return Re4dcUiImage{RE4DC_GC_TOKEN(t),nullptr,gc::textures[t].width,gc::textures[t].height,6,0xffffffffU,0};}
struct Binding { cModel* owner; unsigned serial; cParts* list; cParts* parts[kBones]; unsigned appearance;
                 cModelInfo* infos[4]; const ModelData* qualified[4]; unsigned short signature[4]; };
Binding bindings[32];
Binding* bound;
unsigned replacement;
int mesh_limit=RE4DC_COARSE_GANADO_LIMIT;
bool config_read;
int stress_layout;
unsigned frame_meshes, frame_emitted, frame_candidates, frame_fallback, frame_triangles;
Mtx local_skin[kBones];
alignas(32) float palette[256][12]; // one synchronous opaque info at a time
re4dc::render::SourceLighting light; // constant texture colour for this proof
unsigned attempts, drawn, fallback, rejected, missing_texture;
#if RE4DC_COARSE_SKIN_FTRV
// FTRV palettes: each appearance's entries built once (on its first draw) from the generated weights.
alignas(32) unsigned char skin_stream[(gc::skin_stream_bytes + kFarSkinBytes + 31) & ~31U];
alignas(32) float bone_T[kBones][12];
CoarseBoneJob skin_jobs[kBones];
unsigned char skin_bone[kTierApps][kBones];
unsigned skin_first[kTierApps][4], skin_groups[kTierApps][4], skin_used[kTierApps], skin_state[kTierApps], skin_next;
#if RE4DC_COARSE_SKIN_FTRV == 2
CoarseSkinCheck skin_chk;
#endif
bool skin_init(unsigned a) {
    if (skin_state[a]) return skin_state[a] == 1;
#if RE4DC_CROWD_FAR
    if (a >= kApps && !far_same(a)) { skin_state[a] = 2; re4dc_log("CROWD_FAR %s: far bundle differs (bind/atlas)\n", gc::appearance_names[cast_app(a)]); return false; }
#endif
    unsigned n = 0, bytes = skin_next; unsigned char used[kBones] = {};
    for (unsigned i = 0; i < 4; ++i) {
        const auto& c = cast_chunk(a, i);
        for (unsigned j = 0; j < c.palette_count; ++j)
            for (unsigned k = 0; k < c.weights[j].count; ++k)
                if (c.weights[j].bone[k] >= kBones) { skin_state[a] = 2; return false; }
        skin_first[a][i] = bytes;
        const unsigned b = coarse_group_build(c.weights, c.palette_count, skin_stream + bytes, sizeof(skin_stream) - bytes, &skin_groups[a][i], used);
        if (!b) { skin_state[a] = 2; re4dc_log("COARSE_GANADO_CAST %s skin palette does not fit\n", gc::appearance_names[cast_app(a)]); return false; }
        bytes += b; n += c.palette_count;
    }
    skin_next = bytes;
    skin_used[a] = 0;
    for (unsigned b = 0; b < kBones; ++b) if (used[b]) skin_bone[a][skin_used[a]++] = (unsigned char)b;
    re4dc_log("COARSE_GANADO_CAST skin ftrv=%d %s entries=%u bones=%u stream=%u/%u\n", RE4DC_COARSE_SKIN_FTRV,
              gc::appearance_names[cast_app(a)], n, skin_used[a], skin_next, (unsigned)sizeof(skin_stream));
    skin_state[a] = 1;
    return true;
}
#endif
#if RE4DC_COARSE_PREGATE
bool visible(const cModelInfo* info);
extern "C" unsigned re4dc_model_output_count();
// COARSE_PREGATE (render only; game30.mk): an actor-level cull ahead of the skin work. A visible chunk is
// skipped (no bones, palettes or submission, so no TA header either: re4dc_actor_submit writes the header in
// re4dc_model_direct_begin, after its fog gate) when every position it can draw is provably outside one
// plane that the actor path's outcodes cull on (native_actor_fast.cpp pass_positions: x < 0, y < 0,
// x > 640, y > 480 with x = X'/|W|, y = Y'/|W|; W > far), so that re4dc_actor_submit would emit nothing.
// Bound, built once per appearance from the chunk's own positions and weights (no mesh change): per chunk
// and bone b, a ball in b's bind-local frame (B_b x, B_b the appearance's inverse bind) around every
// position that b moves (weight > 0). A drawn position is sum_k w_k R^-1 P_k B_k x with w_k >= 0 and
// sum_k w_k = 1 (checked here; otherwise the appearance is never culled), so its world point lies in the
// convex hull of the world balls P_k(ball_k) (radius r ||P_k||, a Gershgorin bound on P_k's 3x3), and a
// half-space that holds every ball holds the hull. X', Y' and W (screen_rows) are affine in the world
// point, g.w + g3, so a ball (c, r) clears a plane when g.c + g3 -+ r|g| does (right and bottom also need
// W > 0 over the ball, where |W| = W). Margins: radius x 1.002 + 4 units. The palette (fog) gate remains
// the final arbiter for every chunk that is kept. The crowd table (crowd_tier) no longer sees a wholly
// culled actor; harmless here: a cast chunk draws with lighting off (constant colour) and a blob without
// LOD levels, the only two things a crowd tier changes, and only cast chunks are crowd-classed (Leon is 0).
// =2 (check build): nothing is skipped; each chunk the gate would skip is submitted as before and must
// add 0 to the frame owner's emitted-triangle count (model_output): "COARSE_PREGATE" lines.
struct GateBall { float c[3], r; };
constexpr unsigned kGatePool = kTierApps * kBones * 2;
constexpr float kGateQ = 1.0f / 16.0f;  // the chunks' shift 4: a position is its s16 x 2^-4 (Frame::q)
GateBall gate_ball[kGatePool];
unsigned char gate_bone[kGatePool];
unsigned short gate_first[kTierApps][4];
unsigned char gate_count[kTierApps][4], gate_state[kTierApps];  // state: 0 not built, 1 ready, 2 never culled
unsigned gate_next, gate_visible;
unsigned gate_actors, gate_culled_actors, gate_chunks, gate_culled_chunks, gate_ungated;
#if RE4DC_COARSE_PREGATE == 2
unsigned gate_violations, gate_confirmed, gate_missed, gate_emitted, gate_logs;
#endif
inline void gate_local(const float* B, const float x[3], float y[3]) {
    for (unsigned r = 0; r < 3; ++r) y[r] = B[r * 4] * x[0] + B[r * 4 + 1] * x[1] + B[r * 4 + 2] * x[2] + B[r * 4 + 3];
}
bool gate_build(unsigned a) {
    unsigned next = gate_next;
    for (unsigned i = 0; i < 4; ++i) {
        const auto& c = cast_chunk(a, i);
        if (!c.palette_count || !c.positions) return false;
        float lo[kBones][3], hi[kBones][3], rr[kBones];
        bool use[kBones] = {};
        for (unsigned pass = 0; pass < 2; ++pass)
            for (unsigned v = 0; v < c.position_count; ++v) {
                const short* s = reinterpret_cast<const short*>(c.positions + v * 8);
                unsigned e = (unsigned short)s[3];
                if (e >= c.palette_count) e = 0;  // position_matrix's clamp
                const auto& w = c.weights[e];
                if (!w.count || w.count > 3) return false;
                float sum = 0.0f;
                for (unsigned k = 0; k < w.count; ++k) {
                    if (w.bone[k] >= kBones || !(w.value[k] >= 0.0f)) return false;
                    sum += w.value[k];
                }
                if (!(__builtin_fabsf(sum - 1.0f) <= 1e-4f)) return false;
                const float x[3] = {float(s[0]) * kGateQ, float(s[1]) * kGateQ, float(s[2]) * kGateQ};
                for (unsigned k = 0; k < w.count; ++k) {
                    if (!(w.value[k] > 0.0f)) continue;
                    const unsigned b = w.bone[k];
                    float y[3];
                    gate_local(gc::bind[cast_app(a)][b], x, y);
                    if (pass) {
                        float d2 = 0.0f;
                        for (unsigned j = 0; j < 3; ++j) { const float d = y[j] - 0.5f * (lo[b][j] + hi[b][j]); d2 += d * d; }
                        if (d2 > rr[b]) rr[b] = d2;
                    } else if (!use[b]) {
                        use[b] = true; rr[b] = 0.0f;
                        for (unsigned j = 0; j < 3; ++j) lo[b][j] = hi[b][j] = y[j];
                    } else {
                        for (unsigned j = 0; j < 3; ++j) { if (y[j] < lo[b][j]) lo[b][j] = y[j]; if (y[j] > hi[b][j]) hi[b][j] = y[j]; }
                    }
                }
            }
        gate_first[a][i] = (unsigned short)next; gate_count[a][i] = 0;
        for (unsigned b = 0; b < kBones; ++b) {
            if (!use[b]) continue;
            if (next == kGatePool) return false;
            gate_ball[next] = GateBall{{0.5f * (lo[b][0] + hi[b][0]), 0.5f * (lo[b][1] + hi[b][1]), 0.5f * (lo[b][2] + hi[b][2])},
                                       __builtin_sqrtf(rr[b])};
            gate_bone[next++] = (unsigned char)b; ++gate_count[a][i];
        }
    }
    gate_next = next;
    return true;
}
bool gate_init(unsigned a) {
    if (!gate_state[a]) {
        gate_state[a] = gate_build(a) ? 1 : 2;
        unsigned flat = 1;  // the crowd-tier argument above: lighting off, no LOD levels / pending build / bake
        for (unsigned i = 0; i < 4; ++i) {
            const unsigned char* h = cast_chunk(a, i).stream;
            if (h[0] != 0xFE || h[3] || (h[2] & 0x82)) flat = 0;
        }
        if (light.enable) flat = 0;
        re4dc_log("COARSE_PREGATE=%d %s state=%u balls=%u/%u/%u/%u pool=%u/%u flat=%u\n", RE4DC_COARSE_PREGATE,
                  gc::appearance_names[cast_app(a)], gate_state[a], gate_count[a][0], gate_count[a][1], gate_count[a][2],
                  gate_count[a][3], gate_next, kGatePool, flat);
    }
    return gate_state[a] == 1;
}
#if RE4DC_COARSE_GATE_ONCE != 1
// ||A|| (spectral) <= sqrt(max row sum of |A^T A|): exact for orthogonal columns (rotation x scale).
inline float gate_scale(const float (*A)[4]) {
    float s = 0.0f;
    for (unsigned i = 0; i < 3; ++i) {
        float row = 0.0f;
        for (unsigned j = 0; j < 3; ++j) row += __builtin_fabsf(A[0][i] * A[0][j] + A[1][i] * A[1][j] + A[2][i] * A[2][j]);
        if (row > s) s = row;
    }
    return __builtin_sqrtf(s);
}
// The visible chunks' modelviews into mv (the loop reuses them; gate_visible = their mask) and the mask
// of visible chunks the gate skips.
unsigned gate_cull(cModel* m, unsigned app, cModelInfo* const* infos, cParts* const* parts, const Mtx inv, Mtx* mv) {
    gate_visible = 0;
    for (unsigned i = 0; i < 4; ++i) {
        if (!visible(infos[i])) continue;
        Mtx pm;
        PSMTXConcat(m->pParts->mat, infos[i]->mat, pm);
        PSMTXConcat(pG->Cam.v_mat, pm, mv[i]);
        gate_visible |= 1U << i;
    }
    ++gate_actors;
    if (!gate_init(app) || stress_layout) { ++gate_ungated; return 0; }
    float P[7], V[6];
    GXGetProjectionv(P); GXGetViewportv(V);
    if (P[0] != 0.0f || !(V[2] > 0.0f) || !(V[3] > 0.0f)) return 0;
    const float far = P[6] / P[5], near = P[6] / (P[5] - 1.0f);
    if (!(near > 0.0f) || !(far > near) || !(far < 3.0e38f)) return 0;
    const float cx = (V[0] + V[2] * 0.5f) * RE4DC_SCREEN_WF / V[2], cy = (V[1] + V[3] * 0.5f) * RE4DC_SCREEN_HF / V[3];
    const float rows[3][3] = {{RE4DC_SCREEN_HALF_WF * P[1], 0.0f, RE4DC_SCREEN_HALF_WF * P[2] - cx}, {0.0f, -RE4DC_SCREEN_HALF_HF * P[3], -RE4DC_SCREEN_HALF_HF * P[4] - cy},
                              {0.0f, 0.0f, -1.0f}};
    float scale[kBones];
    unsigned have[2] = {0, 0};
    unsigned culled = 0;
    for (unsigned i = 0; i < 4; ++i) {
        if (!((gate_visible >> i) & 1U)) continue;
        ++gate_chunks;
        const unsigned n = gate_count[app][i], first = gate_first[app][i];
        if (!n) continue;
        // G: X', Y', W, X' - 640 W, Y' - 480 W of a world point (screen rows x modelview x root inverse).
        float M[3][4], G[5][4], norm[5];
        for (unsigned r = 0; r < 3; ++r)
            for (unsigned c = 0; c < 4; ++c) M[r][c] = rows[r][0] * mv[i][0][c] + rows[r][1] * mv[i][1][c] + rows[r][2] * mv[i][2][c];
        for (unsigned r = 0; r < 3; ++r) {
            for (unsigned c = 0; c < 3; ++c) G[r][c] = M[r][0] * inv[0][c] + M[r][1] * inv[1][c] + M[r][2] * inv[2][c];
            G[r][3] = M[r][0] * inv[0][3] + M[r][1] * inv[1][3] + M[r][2] * inv[2][3] + M[r][3];
        }
        for (unsigned c = 0; c < 4; ++c) { G[3][c] = G[0][c] - RE4DC_SCREEN_WF * G[2][c]; G[4][c] = G[1][c] - RE4DC_SCREEN_HF * G[2][c]; }
        for (unsigned f = 0; f < 5; ++f) norm[f] = __builtin_sqrtf(G[f][0] * G[f][0] + G[f][1] * G[f][1] + G[f][2] * G[f][2]);
        unsigned planes = 31;  // left, top, right, bottom, far
        for (unsigned j = 0; j < n && planes; ++j) {
            const GateBall& g = gate_ball[first + j];
            const unsigned b = gate_bone[first + j];
            const float (*A)[4] = parts[b]->mat;
            if (!((have[b >> 5] >> (b & 31)) & 1U)) { scale[b] = gate_scale(A); have[b >> 5] |= 1U << (b & 31); }
            float w[3];
            for (unsigned r = 0; r < 3; ++r) w[r] = A[r][0] * g.c[0] + A[r][1] * g.c[1] + A[r][2] * g.c[2] + A[r][3];
            const float rho = g.r * scale[b] * 1.002f + 4.0f;
            float d[5];
            for (unsigned f = 0; f < 5; ++f) d[f] = G[f][0] * w[0] + G[f][1] * w[1] + G[f][2] * w[2] + G[f][3];
            const float wmin = d[2] - rho * norm[2];
            unsigned out = 0;
            if (d[0] + rho * norm[0] < 0.0f) out |= 1;
            if (d[1] + rho * norm[1] < 0.0f) out |= 2;
            if (wmin > 0.0f && d[3] - rho * norm[3] > 0.0f) out |= 4;
            if (wmin > 0.0f && d[4] - rho * norm[4] > 0.0f) out |= 8;
            if (wmin > far) out |= 16;
            planes &= out;
        }
        if (planes) { culled |= 1U << i; ++gate_culled_chunks; }
    }
    if (gate_visible && culled == gate_visible) ++gate_culled_actors;
    return culled;
}
#endif
#if RE4DC_COARSE_GATE_ONCE
// COARSE_GATE_ONCE (render only; game30.mk): gate_cull's decisions and modelviews, bit for bit, with less work.
// - The view constants (far, near, screen rows) are rebuilt only when the projection / viewport words change.
// - A visible chunk whose info matrix repeats (word for word) the last one concatenated takes that chunk's
//   modelview (the same PSMTXConcat pair on the same three matrices), and a repeated modelview keeps the gate
//   matrix G and its norms (the same operations on the same inputs): one G per actor when its infos agree.
// - A ball evaluates only the planes still undecided (planes &= out never sets a bit), each by gate_cull's own
//   expression. Its radius term rho (which needs the bone's scale) is computed only when the centre does not
//   settle every live plane: rho >= 4 or NaN (g.r, scale >= 0) and norm >= 0 or NaN, so rho x norm is >= 0 or
//   NaN, and a centre with d0 >= 0 (d1 >= 0; d2 <= 0 or d3 <= 0; d2 <= 0 or d4 <= 0; d2 <= far), or a NaN
//   there, leaves the left (top; right; bottom; far) bit clear whatever rho is (IEEE rounding is monotone).
// - The scale's Gram A^T A is symmetric: (A^T A)_ij and (A^T A)_ji are the same three products (multiplication
//   commutes) summed in the same order, so six dot products give the nine entries' bits.
// =2 (check build): gate_cull runs first as the reference (its counters restored), then this one decides; masks
// and modelviews are compared and every scale / kept G is recomputed ("GATE1 PREGATE" lines, mismatches 0).
inline float gate_scale_sym(const float (*A)[4]) {
    const float g00 = A[0][0] * A[0][0] + A[1][0] * A[1][0] + A[2][0] * A[2][0];
    const float g01 = A[0][0] * A[0][1] + A[1][0] * A[1][1] + A[2][0] * A[2][1];
    const float g02 = A[0][0] * A[0][2] + A[1][0] * A[1][2] + A[2][0] * A[2][2];
    const float g11 = A[0][1] * A[0][1] + A[1][1] * A[1][1] + A[2][1] * A[2][1];
    const float g12 = A[0][1] * A[0][2] + A[1][1] * A[1][2] + A[2][1] * A[2][2];
    const float g22 = A[0][2] * A[0][2] + A[1][2] * A[1][2] + A[2][2] * A[2][2];
    const float a01 = __builtin_fabsf(g01), a02 = __builtin_fabsf(g02), a12 = __builtin_fabsf(g12);
    float s = 0.0f, row;
    row = __builtin_fabsf(g00) + a01 + a02; if (row > s) s = row;
    row = a01 + __builtin_fabsf(g11) + a12; if (row > s) s = row;
    row = a02 + a12 + __builtin_fabsf(g22); if (row > s) s = row;
    return __builtin_sqrtf(s);
}
// gate_cull's G and norms for one modelview.
void gate_matrix(const float (*rows)[3], const float (*mv)[4], const Mtx inv, float (*G)[4], float* norm) {
    float M[3][4];
    for (unsigned r = 0; r < 3; ++r)
        for (unsigned c = 0; c < 4; ++c) M[r][c] = rows[r][0] * mv[0][c] + rows[r][1] * mv[1][c] + rows[r][2] * mv[2][c];
    for (unsigned r = 0; r < 3; ++r) {
        for (unsigned c = 0; c < 3; ++c) G[r][c] = M[r][0] * inv[0][c] + M[r][1] * inv[1][c] + M[r][2] * inv[2][c];
        G[r][3] = M[r][0] * inv[0][3] + M[r][1] * inv[1][3] + M[r][2] * inv[2][3] + M[r][3];
    }
    for (unsigned c = 0; c < 4; ++c) { G[3][c] = G[0][c] - RE4DC_SCREEN_WF * G[2][c]; G[4][c] = G[1][c] - RE4DC_SCREEN_HF * G[2][c]; }
    for (unsigned f = 0; f < 5; ++f) norm[f] = __builtin_sqrtf(G[f][0] * G[f][0] + G[f][1] * G[f][1] + G[f][2] * G[f][2]);
}
struct GateView { bool valid, ok; unsigned P[7], V[6]; float far, rows[3][3]; };
GateView gate_view;
#if RE4DC_CROWD_CULL
float gate_far_limit = 3.0e38f;  // lane crowd (re4dc_crowd_offscreen only): a nearer far plane for one call
#endif
#if RE4DC_COARSE_GATE_ONCE == 2
unsigned g1_calls, g1_mask_mismatch, g1_visible_mismatch, g1_mv_mismatch, g1_mv_reused, g1_g_reused, g1_g_mismatch,
    g1_view_reused, g1_scales, g1_scale_mismatch, g1_rho, g1_rho_skipped;
#endif
unsigned gate_cull_once(cModel* m, unsigned app, cModelInfo* const* infos, cParts* const* parts, const Mtx inv, Mtx* mv) {
    gate_visible = 0;
    int last = -1;  // the last visible chunk whose modelview was concatenated
    for (unsigned i = 0; i < 4; ++i) {
        if (!visible(infos[i])) continue;
        if (last >= 0 && !std::memcmp(infos[i]->mat, infos[last]->mat, sizeof(Mtx))) {
            std::memcpy(mv[i], mv[last], sizeof(Mtx));
#if RE4DC_COARSE_GATE_ONCE == 2
            ++g1_mv_reused;
#endif
        } else {
            Mtx pm;
            PSMTXConcat(m->pParts->mat, infos[i]->mat, pm);
            PSMTXConcat(pG->Cam.v_mat, pm, mv[i]);
            last = int(i);
        }
        gate_visible |= 1U << i;
    }
    ++gate_actors;
    if (!gate_init(app) || stress_layout) { ++gate_ungated; return 0; }
    float P[7], V[6];
    GXGetProjectionv(P); GXGetViewportv(V);
    GateView& gv = gate_view;
    if (!gv.valid || std::memcmp(gv.P, P, sizeof(P)) || std::memcmp(gv.V, V, sizeof(V))) {
        gv.valid = true; std::memcpy(gv.P, P, sizeof(P)); std::memcpy(gv.V, V, sizeof(V));
        gv.ok = false;
        if (!(P[0] != 0.0f || !(V[2] > 0.0f) || !(V[3] > 0.0f))) {
            const float far = P[6] / P[5], near = P[6] / (P[5] - 1.0f);
            if (!(!(near > 0.0f) || !(far > near) || !(far < 3.0e38f))) {
                const float cx = (V[0] + V[2] * 0.5f) * RE4DC_SCREEN_WF / V[2], cy = (V[1] + V[3] * 0.5f) * RE4DC_SCREEN_HF / V[3];
                const float rows[3][3] = {{RE4DC_SCREEN_HALF_WF * P[1], 0.0f, RE4DC_SCREEN_HALF_WF * P[2] - cx}, {0.0f, -RE4DC_SCREEN_HALF_HF * P[3], -RE4DC_SCREEN_HALF_HF * P[4] - cy},
                                          {0.0f, 0.0f, -1.0f}};
                std::memcpy(gv.rows, rows, sizeof(rows));
                gv.far = far; gv.ok = true;
            }
        }
    }
#if RE4DC_COARSE_GATE_ONCE == 2
    else ++g1_view_reused;
#endif
    if (!gv.ok) return 0;
#if RE4DC_CROWD_CULL
    // Lane crowd: re4dc_crowd_offscreen's far plane is the actor path's cull depth (the fogged View far when nearer).
    const float far = gate_far_limit < gv.far ? gate_far_limit : gv.far;
#else
    const float far = gv.far;
#endif
    float scale[kBones];
    unsigned have[2] = {0, 0};
    unsigned culled = 0;
    float G[5][4], norm[5];
    int gfor = -1;  // the chunk whose modelview G and norm were built from
    for (unsigned i = 0; i < 4; ++i) {
        if (!((gate_visible >> i) & 1U)) continue;
        ++gate_chunks;
        const unsigned n = gate_count[app][i], first = gate_first[app][i];
        if (!n) continue;
        if (gfor >= 0 && !std::memcmp(mv[i], mv[gfor], sizeof(Mtx))) {
#if RE4DC_COARSE_GATE_ONCE == 2
            ++g1_g_reused;
            float G2[5][4], norm2[5];
            gate_matrix(gv.rows, mv[i], inv, G2, norm2);
            if (std::memcmp(G2, G, sizeof(G)) || std::memcmp(norm2, norm, sizeof(norm))) ++g1_g_mismatch;
#endif
        } else {
            gate_matrix(gv.rows, mv[i], inv, G, norm);
            gfor = int(i);
        }
        unsigned planes = 31;  // left, top, right, bottom, far
        for (unsigned j = 0; j < n && planes; ++j) {
            const GateBall& g = gate_ball[first + j];
            const unsigned b = gate_bone[first + j];
            const float (*A)[4] = parts[b]->mat;
            float w[3];
            for (unsigned r = 0; r < 3; ++r) w[r] = A[r][0] * g.c[0] + A[r][1] * g.c[1] + A[r][2] * g.c[2] + A[r][3];
            float d[5];
            if (planes & 1U) d[0] = G[0][0] * w[0] + G[0][1] * w[1] + G[0][2] * w[2] + G[0][3];
            if (planes & 2U) d[1] = G[1][0] * w[0] + G[1][1] * w[1] + G[1][2] * w[2] + G[1][3];
            if (planes & 28U) d[2] = G[2][0] * w[0] + G[2][1] * w[1] + G[2][2] * w[2] + G[2][3];
            if (planes & 4U) d[3] = G[3][0] * w[0] + G[3][1] * w[1] + G[3][2] * w[2] + G[3][3];
            if (planes & 8U) d[4] = G[4][0] * w[0] + G[4][1] * w[1] + G[4][2] * w[2] + G[4][3];
            // The live planes the centre alone does not settle (every other live bit of out is 0).
            const unsigned open = ((planes & 1U) && d[0] < 0.0f ? 1U : 0U) | ((planes & 2U) && d[1] < 0.0f ? 2U : 0U) |
                                  ((planes & 4U) && d[2] > 0.0f && d[3] > 0.0f ? 4U : 0U) |
                                  ((planes & 8U) && d[2] > 0.0f && d[4] > 0.0f ? 8U : 0U) |
                                  ((planes & 16U) && d[2] > far ? 16U : 0U);
            if (!open) {
#if RE4DC_COARSE_GATE_ONCE == 2
                ++g1_rho_skipped;
#endif
                planes = 0;
                break;
            }
#if RE4DC_COARSE_GATE_ONCE == 2
            ++g1_rho;
#endif
            if (!((have[b >> 5] >> (b & 31)) & 1U)) {
                scale[b] = gate_scale_sym(A); have[b >> 5] |= 1U << (b & 31);
#if RE4DC_COARSE_GATE_ONCE == 2
                ++g1_scales;
                const float ref = gate_scale(A);
                if (std::memcmp(&ref, &scale[b], sizeof(ref))) ++g1_scale_mismatch;
#endif
            }
            const float rho = g.r * scale[b] * 1.002f + 4.0f;
            unsigned out = 0;
            if ((open & 1U) && d[0] + rho * norm[0] < 0.0f) out |= 1;
            if ((open & 2U) && d[1] + rho * norm[1] < 0.0f) out |= 2;
            if (open & 28U) {
                const float wmin = d[2] - rho * norm[2];
                if ((open & 4U) && wmin > 0.0f && d[3] - rho * norm[3] > 0.0f) out |= 4;
                if ((open & 8U) && wmin > 0.0f && d[4] - rho * norm[4] > 0.0f) out |= 8;
                if ((open & 16U) && wmin > far) out |= 16;
            }
            planes &= out;
        }
        if (planes) { culled |= 1U << i; ++gate_culled_chunks; }
    }
    if (gate_visible && culled == gate_visible) ++gate_culled_actors;
    return culled;
}
#if RE4DC_COARSE_GATE_ONCE == 2
unsigned gate_cull_checked(cModel* m, unsigned app, cModelInfo* const* infos, cParts* const* parts, const Mtx inv, Mtx* mv) {
    const unsigned c0 = gate_actors, c1 = gate_ungated, c2 = gate_chunks, c3 = gate_culled_chunks, c4 = gate_culled_actors;
    Mtx ref_mv[4];
    const unsigned ref = gate_cull(m, app, infos, parts, inv, ref_mv), ref_visible = gate_visible;
    gate_actors = c0; gate_ungated = c1; gate_chunks = c2; gate_culled_chunks = c3; gate_culled_actors = c4;
    const unsigned got = gate_cull_once(m, app, infos, parts, inv, mv);
    ++g1_calls;
    if (got != ref) ++g1_mask_mismatch;
    if (gate_visible != ref_visible) ++g1_visible_mismatch;
    for (unsigned i = 0; i < 4; ++i)
        if (((gate_visible >> i) & 1U) && std::memcmp(mv[i], ref_mv[i], sizeof(Mtx))) ++g1_mv_mismatch;
    return got;
}
#else
inline unsigned gate_cull_checked(cModel* m, unsigned app, cModelInfo* const* infos, cParts* const* parts, const Mtx inv, Mtx* mv) {
    return gate_cull_once(m, app, infos, parts, inv, mv);
}
#endif
#endif
#if RE4DC_COARSE_PREGATE == 2
void gate_note(unsigned app, unsigned i, bool skipped, unsigned emitted) {
    if (skipped) {
        if (emitted) {
            ++gate_violations; gate_emitted += emitted;
            if (++gate_logs <= 12)
                re4dc_log("COARSE_PREGATE VIOLATION t=%u %s chunk=%u emitted=%u\n", pG->Frame_cnt, gc::appearance_names[app], i, emitted);
        } else {
            ++gate_confirmed;
        }
    } else if (!emitted) {
        ++gate_missed;
    }
}
#endif
#endif

unsigned fingerprint(const void* data) {
    const auto* p=(const unsigned char*)data;unsigned h=2166136261U;
    for(unsigned i=0;i<64;++i)h=(h^p[i])*16777619U;
    return h;
}
// The source infos' roles and the appearance from the signature table. A ModelData that passed a
// signature's hash stays qualified for that signature (the fingerprint runs once per new ModelData).
bool match_infos(cModel* m, Binding& b, unsigned& app) {
    auto& infos=b.infos;
    std::memset(infos,0,sizeof(infos));
    app=~0U;
    unsigned count=0;
    constexpr unsigned kSigs=sizeof(gc::signatures)/sizeof(gc::signatures[0]);
    for(cModelInfo* info=m->pModelInfo;info && count<32;info=info->pList,++count){
        const ModelData* d=info->pData;if(!d || !d->vtxOrig)continue;
        const unsigned n=d->weight_ext_num>255?d->weight_ext_num:d->weight_palette_num;
        unsigned k=kSigs;
        for(unsigned r=0;r<4;++r)if(b.qualified[r]==d){k=b.signature[r];break;}
        if(k==kSigs){
            unsigned h=0;bool hashed=false;
            for(unsigned s=0;s<kSigs;++s){
                const auto& g=gc::signatures[s];
                if(d->nVtx!=g.positions || d->nNrm!=g.normals || n!=g.palette)continue;
                if(!hashed){h=fingerprint(d->vtxOrig);hashed=true;}
                if(h==g.vertex_hash){k=s;break;}
            }
            if(k==kSigs)continue;
            b.qualified[gc::signatures[k].role]=d;b.signature[gc::signatures[k].role]=(unsigned short)k;
        }
        const auto& g=gc::signatures[k];
        if(infos[g.role])return false;
        if(g.appearance!=0xFF){if(app!=~0U && app!=g.appearance)return false;app=g.appearance;}
        infos[g.role]=info;
    }
    for(unsigned i=0;i<4;++i)if(!infos[i])return false;
    return app<kApps;
}
bool bind_source(cModel* m) {
    if(!m || (m->id<0x10 || m->id>0x20) || m->nParts!=kBones || !m->pList || (m->be_flag&0x4000))return false;
    bound=nullptr;
    for(auto& entry:bindings)if(entry.owner==m && entry.serial==m->serial && entry.list==m->pList){bound=&entry;break;}
    if(!bound){
        Binding& entry=bindings[replacement++%32];
        std::memset(&entry,0,sizeof(entry));
        cParts* p=m->pList;
        for(unsigned i=0;i<kBones;++i){if(!p)return false;entry.parts[i]=p;p=p->pList;}
        if(p)return false;
        for(unsigned i=0;i<kBones;++i){
            const int parent=gc::parents[i];
            const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)entry.parts[parent];
            if(entry.parts[i]->pParent!=want)return false;
        }
        entry.owner=m;entry.serial=m->serial;entry.list=m->pList;entry.appearance=~0U;bound=&entry;
    }
    unsigned app;
    if(!match_infos(m,*bound,app))return false;
    if(bound->appearance!=app){
        // The appearance's mesh is retargeted with its own inverse bind (as the 874 mesh is): the bone
        // axes must agree; rest translations may differ (=2 counts those skeletons).
        for(unsigned i=0;i<kBones;++i)for(unsigned row=0;row<3;++row)for(unsigned col=0;col<3;++col)
            if(__builtin_fabsf(bound->parts[i]->lt_inv_mat[row][col]-gc::bind[app][i][row*4+col])>.001f)return false;
        bound->appearance=app;
    }
    return true;
}
bool visible(const cModelInfo* info) {
    // ModelTrans queues ot_type 7 twice; commonModelTrans selects bit 0x40
    // in its second pass (and sets model bit 0x08000000 after the first).
    // Coarse submits each actor once, so include both source pass groups here.
    // Bit 8 and invisible_factor remain the actual presentation visibility.
    return (info->be_flag&8) && info->invisible_factor>0;
}

#if RE4DC_COARSE_GANADO_CAST == 2
// The 874 adapter's acceptance (coarse_ganado.cpp's bind_source without its caches) for the same actor.
unsigned chk_both, chk_cast_only, chk_old_only, chk_neither, chk_role_mismatch, chk_bind_off, chk_app[kApps];
bool old_match(cModel* m, cModelInfo* (&infos)[4]) {
    std::memset(infos,0,sizeof(infos));
    if(!m || (m->id<0x10 || m->id>0x20) || m->nParts!=34 || !m->pList || (m->be_flag&0x4000))return false;
    cParts* parts[34];cParts* p=m->pList;
    for(unsigned i=0;i<34;++i){
        if(!p)return false;parts[i]=p;
        for(unsigned row=0;row<3;++row)for(unsigned col=0;col<3;++col)
            if(__builtin_fabsf(p->lt_inv_mat[row][col]-ganado874::bind[i][row*4+col])>.001f)return false;
        p=p->pList;
    }
    if(p)return false;
    for(unsigned i=0;i<34;++i){
        const int parent=ganado874::parents[i];
        const cCoord* want=parent<0?(const cCoord*)m:(const cCoord*)parts[parent];
        if(parts[i]->pParent!=want)return false;
    }
    unsigned count=0;
    for(cModelInfo* info=m->pModelInfo;info && count<32;info=info->pList,++count){
        const ModelData* d=info->pData;if(!d || !d->vtxOrig)continue;
        const unsigned n=d->weight_ext_num>255?d->weight_ext_num:d->weight_palette_num;
        for(const auto& s:ganado874::variants){
            if(d->nVtx!=s.positions || d->nNrm!=s.normals || n!=s.palette || fingerprint(d->vtxOrig)!=s.vertex_hash)continue;
            if(infos[s.role])return false;
            infos[s.role]=info;break;
        }
    }
    for(unsigned i=0;i<4;++i)if(!infos[i])return false;
    return true;
}
void check_attempt(cModel* m, bool cast_ok) {
    cModelInfo* old[4];
    const bool old_ok=old_match(m,old);
    if(cast_ok && old_ok){
        ++chk_both;
        for(unsigned i=0;i<4;++i)if(old[i]!=bound->infos[i])++chk_role_mismatch;
    }
    else if(cast_ok)++chk_cast_only;
    else if(old_ok)++chk_old_only;
    else ++chk_neither;
    if(cast_ok){
        ++chk_app[bound->appearance];
        for(unsigned i=0;i<kBones;++i)for(unsigned row=0;row<3;++row)
            if(__builtin_fabsf(bound->parts[i]->lt_inv_mat[row][3]-gc::bind[bound->appearance][i][row*4+3])>.01f){++chk_bind_off;return;}
    }
}
#endif
}

// These hooks are called before model_bridge casts a cModelInfo pointer.
extern "C" int re4dc_coarse_ganado_source(const void* info,Re4dcActorSource* out) {
    for(const auto& a:gc::chunks)for(const auto& c:a)if(info==&c){
        *out={c.positions,c.normals,c.position_count,c.normal_count,c.palette_count,0};return 1;
    }
    return 0;
}
extern "C" int re4dc_coarse_ganado_texture_key(const Re4dcUiImage* i,unsigned* c,unsigned* f) {
    for(unsigned t=0;t<gc::texture_count;++t){
        if(i->pixels!=RE4DC_GC_TOKEN(t) || i->width!=gc::textures[t].width || i->height!=gc::textures[t].height || i->format!=6 || i->palette_bytes)continue;
        *c=RE4DC_GC_KEYS[t].crc;*f=RE4DC_GC_KEYS[t].fnv;return 1;
    }
    return 0;
}
#if RE4DC_CHARBAKE_TOGGLE
extern "C" void re4dc_charbake_ganado_set(unsigned variant){
    charbake_variant=variant%re4dc_charbake::kCount;charbake_ready=false;charbake_keys();
}
#endif

// Called with coarse store queues closed. Opaque submissions complete here;
// none borrow the shared palette after the next info overwrites it.
extern "C" int re4dc_coarse_ganado(cModel* m) {
    ++frame_candidates;
    if(mesh_limit>=0 && frame_meshes>=unsigned(mesh_limit))return stress_layout?1:0;
    ++attempts;
#if RE4DC_ACTOR_EARLY_COARSE
    const bool ok=owner_ganado_bind(m);
#else
    const bool ok=bind_source(m);
#endif
#if RE4DC_COARSE_GANADO_CAST == 2
    check_attempt(m,ok);
#endif
    if(!ok){
        ++frame_fallback;
        if(++fallback<=12)re4dc_log("COARSE_GANADO_CAST unsupported id=%u parts=%u\n",m?m->id:255,m?m->nParts:0);
        return 0;
    }
    auto& infos=bound->infos;auto& parts=bound->parts;const unsigned app=bound->appearance;
    const Re4dcUiImage image=image_of(gc::appearance_texture[app]);
    const auto& tex=RE4DC_GC_KEYS[gc::appearance_texture[app]];
    if(m->invisible_factor*m->invisible_factor2<=0)return 1;
    if(m->invisible_factor*m->invisible_factor2<.999f)return 0;
    for(unsigned i=0;i<4;++i)if(visible(infos[i])) {
        if(infos[i]->blend_mode || infos[i]->invisible_factor<.999f)return 0;
        // As coarse_ganado.cpp: bone-driven info 3 only; other morphing geometry and animated
        // materials remain unsupported.
        if(((infos[i]->be_flag&2) && i!=3) || infos[i]->flagsDC)return 0;
    }
#if RE4DC_ACTOR_EARLY_COARSE
    Re4dcActorTextureLease texture{};
    if(!re4dc_coarse_source_actor_texture(m,&texture) ||
       !re4dc_actor_texture_validate_key(&texture,tex.crc,tex.fnv) || !re4dc_actor_texture_commit(&texture))return 0;
#endif
    if(!re4dc_coarse_leon_texture_ready(&image,tex.crc,tex.fnv)){
        if(++missing_texture<=3)re4dc_log("COARSE_GANADO_CAST texture unavailable\n");return 0;
    }
    re4dc_bind_actor_frame();
    Mtx inv,relative,mv,pm;
    if(!PSMTXInverse(m->pParts->mat,inv))return 0;
    const float (*bind)[12]=gc::bind[app];
#if RE4DC_COARSE_SKIN_FTRV
    if(!skin_init(app))return 0;
#endif
#if RE4DC_COARSE_PREGATE
    Mtx gate_mv[4];
#if RE4DC_COARSE_GATE_ONCE
    const unsigned gate_skip=gate_cull_checked(m,app,infos,parts,inv,gate_mv);
#else
    const unsigned gate_skip=gate_cull(m,app,infos,parts,inv,gate_mv);
#endif
#if RE4DC_COARSE_PREGATE == 1
    // Every visible chunk skipped: no bones either (the chunk loop below skips each of them).
    if(!gate_visible || gate_skip!=gate_visible){
#endif
#endif
#if RE4DC_COARSE_SKIN_FTRV
    {
        alignas(32) float invx[16];coarse_inv_xmtrx(inv,invx);
        for(unsigned u=0;u<skin_used[app];++u){
            const unsigned b=skin_bone[app][u];
            skin_jobs[u]={&parts[b]->mat[0][0],bind[b],bone_T[b]};
        }
        re4dc_coarse_skin_bones(invx,skin_jobs,skin_used[app]);
    }
#endif
#if RE4DC_COARSE_SKIN_FTRV != 1
    for(unsigned i=0;i<kBones;++i){
        PSMTXConcat(inv,parts[i]->mat,relative);
        PSMTXConcat(relative,(const float (*)[4])bind[i],local_skin[i]);
    }
#endif
#if RE4DC_COARSE_PREGATE == 1
    }
#endif
#if RE4DC_COARSE_ONE_SUBMIT
    // COARSE_ONE_SUBMIT: as coarse_actor.cpp, the kept visible chunks in groups whose palettes fit the buffer
    // together (each at an even entry), one re4dc_actor_submit_chunks call per group: 4 -> 1.
    unsigned triangles=0,mask=0;
    const unsigned emitted_before=re4dc_actor_stats()->triangles;
    Re4dcModelPart p{};
    p.model=m;p.position_stride=6;p.normal_stride=6;p.normal_shift=14;p.shift=4;
    p.lighting=&light;p.image=image;p.source_key[2]=1;
    p.depth_mode=m->z_mode;p.cull=0;p.alpha_state=255;
    GXGetProjectionv(p.projection);GXGetViewportv(p.viewport);
    Re4dcActorChunk group[4];unsigned member[4],n=0,used=0;
    float mvs[4][12];
    auto submit=[&]{
        const unsigned ok=n?re4dc_actor_submit_chunks(&p,group,n):0U;
        for(unsigned k=0;k<n;++k){
            if(!((ok>>k)&1U)){++rejected;continue;}
            triangles+=gc::chunks[app][member[k]].triangles;mask|=1U<<member[k];
        }
        n=0;used=0;
    };
    for(unsigned i=0;i<4;++i){
        auto& c=gc::chunks[app][i];cModelInfo* src=infos[i];
        if(!visible(src))continue;
        if(c.palette_count>256){submit();return 0;}
#if RE4DC_COARSE_PREGATE == 1
        if((gate_skip>>i)&1U)continue;
#endif
        unsigned at=(used+1U)&~1U;
        if(at+c.palette_count>256){submit();at=0;}
        float (*pal)[12]=palette+at;
#if RE4DC_COARSE_SKIN_FTRV
        re4dc_coarse_skin_groups(skin_stream+skin_first[app][i],skin_groups[app][i],&bone_T[0][0],&pal[0][0],c.palette_count);
#if RE4DC_COARSE_SKIN_FTRV == 2
        for(unsigned j=0;j<c.palette_count;++j)skin_chk.entry(c.weights[j],local_skin,pal[j]);
#endif
#else
        for(unsigned j=0;j<c.palette_count;++j){
            const auto& w=c.weights[j];
            for(unsigned col=0;col<4;++col)for(unsigned row=0;row<3;++row){
                float value=0;
                for(unsigned k=0;k<w.count;++k)value+=local_skin[w.bone[k]][row][col]*w.value[k];
                pal[j][col*3+row]=value;
            }
        }
#endif
        if(!re4dc_actor_skin_register(pG->Frame_cnt,&c,nullptr,&pal[0][0],c.palette_count)){
            ++rejected;continue;
        }
#if RE4DC_COARSE_PREGATE
        std::memcpy(mv,gate_mv[i],sizeof(mv));  // gate_cull's PSMTXConcat pair on the same matrices
        (void)pm;
#else
        PSMTXConcat(m->pParts->mat,src->mat,pm);
        PSMTXConcat(pG->Cam.v_mat,pm,mv);
#endif
        if(stress_layout){
            const unsigned slot=frame_meshes%7,row=frame_meshes/7;
            const int order[7]={0,-1,1,-2,2,-3,3};
            mv[0][3]=float(order[slot])*(row?850.f:650.f);
            mv[1][3]=row?-350.f:-1100.f;
            mv[2][3]=row?-6500.f:-4200.f;
        }
        std::memcpy(mvs[n],mv,sizeof(mv));
        group[n]={&c,c.stream,c.uv,mvs[n],c.stream_bytes,c.position_count,c.normal_count};
        member[n++]=i;used=at+c.palette_count;
    }
    submit();
#else
    unsigned triangles=0,mask=0;
    const unsigned emitted_before=re4dc_actor_stats()->triangles;
    for(unsigned i=0;i<4;++i){
        auto& c=gc::chunks[app][i];cModelInfo* src=infos[i];
        if(!visible(src))continue;
        if(c.palette_count>256)return 0;
#if RE4DC_COARSE_PREGATE == 1
        if((gate_skip>>i)&1U)continue;
#endif
#if RE4DC_COARSE_SKIN_FTRV
        re4dc_coarse_skin_groups(skin_stream+skin_first[app][i],skin_groups[app][i],&bone_T[0][0],&palette[0][0],c.palette_count);
#if RE4DC_COARSE_SKIN_FTRV == 2
        for(unsigned j=0;j<c.palette_count;++j)skin_chk.entry(c.weights[j],local_skin,palette[j]);
#endif
#else
        for(unsigned j=0;j<c.palette_count;++j){
            const auto& w=c.weights[j];
            for(unsigned col=0;col<4;++col)for(unsigned row=0;row<3;++row){
                float value=0;
                for(unsigned k=0;k<w.count;++k)value+=local_skin[w.bone[k]][row][col]*w.value[k];
                palette[j][col*3+row]=value;
            }
        }
#endif
        if(!re4dc_actor_skin_register(pG->Frame_cnt,&c,nullptr,&palette[0][0],c.palette_count)){
            ++rejected;continue;
        }
#if RE4DC_COARSE_PREGATE
        std::memcpy(mv,gate_mv[i],sizeof(mv));  // gate_cull's PSMTXConcat pair on the same matrices
        (void)pm;
#else
        PSMTXConcat(m->pParts->mat,src->mat,pm);
        PSMTXConcat(pG->Cam.v_mat,pm,mv);
#endif
        if(stress_layout){
            // Arrange the existing live poses in camera space for a bounded
            // renderer stress test. Source positions, bones, AI and camera
            // remain untouched. This placement must never ship as gameplay.
            const unsigned slot=frame_meshes%7,row=frame_meshes/7;
            const int order[7]={0,-1,1,-2,2,-3,3};
            mv[0][3]=float(order[slot])*(row?850.f:650.f);
            mv[1][3]=row?-350.f:-1100.f;
            mv[2][3]=row?-6500.f:-4200.f;
        }
        Re4dcModelPart p{};
        p.model=m;p.info=&c;p.part=&c;p.position_count=c.position_count;p.normal_count=c.normal_count;
        p.position_stride=6;p.normal_stride=6;p.normal_shift=14;p.shift=4;
        p.stream=c.stream;p.stream_bytes=c.stream_bytes;p.uv=c.uv;
        p.lighting=&light;p.image=image;p.source_key[2]=1;
        p.depth_mode=m->z_mode;p.cull=0;p.alpha_state=255;
        std::memcpy(p.modelview,mv,sizeof(mv));GXGetProjectionv(p.projection);GXGetViewportv(p.viewport);
#if RE4DC_COARSE_PREGATE == 2
        const unsigned output_before=re4dc_model_output_count();
        const int submitted=re4dc_actor_submit(&p);
        gate_note(app,i,(gate_skip>>i)&1U,re4dc_model_output_count()-output_before);
        if(!submitted){++rejected;continue;}
#else
        if(!re4dc_actor_submit(&p)){++rejected;continue;}
#endif
        triangles+=c.triangles;mask|=1U<<i;
    }
#endif
#if RE4DC_ACTOR_EARLY_COARSE
    // Submission rejects must be surfaced, never silently called a complete
    // native image. The surrounding owner invalidates the diagnostic frame.
    unsigned expected=0;
    for(unsigned i=0;i<4;++i)if(visible(infos[i])) {
#if RE4DC_COARSE_PREGATE == 1
        if((gate_skip>>i)&1U)continue;
#endif
        expected|=1u<<i;
    }
    if(mask!=expected){re4dc_model_packet_abort();return 0;}
#endif
    ++drawn;++frame_meshes;frame_triangles+=triangles;
    frame_emitted+=re4dc_actor_stats()->triangles>emitted_before;
#if RE4DC_COARSE_SKIN_FTRV == 2
    if(drawn<=3 || drawn%120==0)skin_chk.log("ganado",pG->Frame_cnt);
#endif
    if(drawn<=3 || drawn%120==0)re4dc_log("COARSE_GANADO_CAST t=%u draws=%u app=%s tris=%u mask=%02x fallback=%u rejected=%u texture_miss=%u\n",
        pG->Frame_cnt,drawn,gc::appearance_names[app],triangles,mask,fallback,rejected,missing_texture);
    return 1;
}

extern "C" void re4dc_coarse_ganado_begin(){
    if(!config_read){
        config_read=true;
        const file_t file=fs_open("/cd/dc/coarse-crowd.txt",O_RDONLY);
        if(file>=0){
            char text[16]={};const int size=fs_read(file,text,15);fs_close(file);
            int value=0;unsigned i=0;const bool neg=text[0]=='-';if(neg)i=1;
            const unsigned start=i;
            while(i<unsigned(size>0?size:0) && text[i]>='0' && text[i]<='9'){value=value*10+text[i++]-'0';}
            if(i>start && value<=64){if(neg)value=-value;if(value>=-1)mesh_limit=value;}
            while(i<unsigned(size>0?size:0) && (text[i]==' ' || text[i]=='\t'))++i;
            if(i<unsigned(size>0?size:0) && text[i]=='1')stress_layout=1;
        }
        re4dc_log("COARSE_CROWD config mesh_limit=%d layout=%d source=diagnostic-file ACT_CAP=0\n",mesh_limit,stress_layout);
        re4dc_log("COARSE_GANADO_CAST=%d appearances=%u signatures=%u textures=%u skin_stream=%u\n",RE4DC_COARSE_GANADO_CAST,kApps,
            (unsigned)(sizeof(gc::signatures)/sizeof(gc::signatures[0])),gc::texture_count,gc::skin_stream_bytes);
    }
    frame_meshes=frame_emitted=frame_candidates=frame_fallback=frame_triangles=0;
}
extern "C" void re4dc_coarse_ganado_end(){
#if RE4DC_ACTOR_EARLY_COARSE
    re4dc_actor_early_coarse_note_frame();
#endif
#if defined(RE4DC_COARSE_FREEZE_AT) && RE4DC_COARSE_FREEZE_AT
    // Diagnostic (COARSE_FREEZE_AT=N, captures only): stop the CPU inside frame N's actor pass. Frame N-1,
    // already submitted, stays on screen, so every capture after the marker shows exactly that frame.
    if(pG->Frame_cnt>=RE4DC_COARSE_FREEZE_AT){
        re4dc_log("COARSE_FREEZE t=%u: the screen holds frame %u\n",pG->Frame_cnt,pG->Frame_cnt-1);
        for(;;)__asm__ volatile("nop");
    }
#endif
    if(pG->Frame_cnt%120==0)re4dc_log("COARSE_CROWD t=%u limit=%d layout=%d candidates=%u meshes=%u emitted=%u tris=%u unsupported=%u rejected=%u texture_miss=%u\n",
        pG->Frame_cnt,mesh_limit,stress_layout,frame_candidates,frame_meshes,frame_emitted,frame_triangles,frame_fallback,rejected,missing_texture);
#if RE4DC_COARSE_PREGATE
    // Totals since boot: actors / wholly culled actors / visible chunks / culled chunks (=2: culled chunks that
    // emitted triangles anyway (must stay 0), culled chunks confirmed empty, kept chunks that emitted nothing).
    if(pG->Frame_cnt%120==0)
#if RE4DC_COARSE_PREGATE == 2
        re4dc_log("COARSE_PREGATE t=%u actors=%u culled_actors=%u chunks=%u culled_chunks=%u ungated=%u violations=%u violation_tris=%u confirmed=%u kept_empty=%u\n",
            pG->Frame_cnt,gate_actors,gate_culled_actors,gate_chunks,gate_culled_chunks,gate_ungated,gate_violations,gate_emitted,gate_confirmed,gate_missed);
#else
        re4dc_log("COARSE_PREGATE t=%u actors=%u culled_actors=%u chunks=%u culled_chunks=%u ungated=%u\n",
            pG->Frame_cnt,gate_actors,gate_culled_actors,gate_chunks,gate_culled_chunks,gate_ungated);
#endif
#if RE4DC_COARSE_GATE_ONCE == 2
    // COARSE_GATE_ONCE=2: gate_cull_once against gate_cull (mismatches must be 0) and how often each shortcut ran.
    if(pG->Frame_cnt%120==0)
        re4dc_log("GATE1 PREGATE t=%u calls=%u mask_mismatch=%u visible_mismatch=%u mv_mismatch=%u mv_reused=%u g_reused=%u g_mismatch=%u view_reused=%u scales=%u scale_mismatch=%u rho=%u rho_skipped=%u\n",
            pG->Frame_cnt,g1_calls,g1_mask_mismatch,g1_visible_mismatch,g1_mv_mismatch,g1_mv_reused,g1_g_reused,g1_g_mismatch,
            g1_view_reused,g1_scales,g1_scale_mismatch,g1_rho,g1_rho_skipped);
#endif
#endif
#if RE4DC_COARSE_GANADO_CAST == 2
    if(pG->Frame_cnt%120==0){
        char apps[64];unsigned n=0;
        for(unsigned a=0;a<kApps && n+12<sizeof(apps);++a)n+=sprintf(apps+n,"%s%u",a?"/":"",chk_app[a]);
        re4dc_log("GCAST t=%u both=%u cast_only=%u old_only=%u neither=%u role_mismatch=%u bind_translation_off=%u app=%s\n",
            pG->Frame_cnt,chk_both,chk_cast_only,chk_old_only,chk_neither,chk_role_mismatch,chk_bind_off,apps);
    }
#endif
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    // Trace builds only (never a timing arm): per-frame Ganado submission and Leon's life for the
    // scripted village-fight fixture, so a timing window and visible-versus-submitted counts are
    // chosen from exact frames. Read-only; logic_trace_diff / dtcmp ignore this line.
    re4dc_log("CROWDF t=%u c=%u m=%u e=%u fb=%u tri=%u hp=%d/%d\n",pG->Frame_cnt,frame_candidates,frame_meshes,
        frame_emitted,frame_fallback,frame_triangles,(int)(short)pG->pl_life,(int)pG->pl_life_max);
#endif
}

extern "C" int re4dc_coarse_ganado_layout(){return stress_layout;}

#include "coarse_actor_owner_ganado.inc"
