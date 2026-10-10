// COARSE=1 (30 fps rethink, step 2): the coarse complete square. In-room play runs unchanged
// (enemies, events, HUD, audio); each image is drawn here from gameplay records instead of the
// source visual pipeline:
//   world    every live collision piece's front-facing polygons (SatMgr: the geometry gameplay walks
//            on and collides with) but its invisible walls (kSeeThrough), culled through the pieces'
//            XZ block trees, near-clipped, flat lit, fogged;
//   actors   the player, the partner and every drawn enemy in view as camera-facing ribbons along the
//            parent -> part segments of the gameplay skeleton (the part world matrices of the tick),
//            a blob under each;
//   effects  a billboard per live world-space effect (position, size and colour of the record).
// Trans() of such a tick runs its presentation stages in the qualified PACE_TRANS_SKIP mode (no
// model OT; effects queue only the draws that carry state), and Render() of the image replaces
// the world OTs (0 .. SUBSCRN_NEAR) with re4dc_coarse_draw(); effects, HUD, messages, filters and
// the letterbox keep their source OTs. Render() runs before the next tick's moves, so the records
// read here are the state of the image's own tick.
#ifndef RE4DC_PS2_WORLD_DRAW
#define RE4DC_PS2_WORLD_DRAW 0
#endif
#if RE4DC_PS2_WORLD_DRAW
#include "re4dc_screen.h"
#include "platform/include/native_ps2_world.h"
#endif
#ifndef RE4DC_COARSE_SCENERY_FALLBACK
#define RE4DC_COARSE_SCENERY_FALLBACK 0
#endif
// COARSE_SAT_SCENERY_ONLY (game30.mk, render only): once the image's scenery is drawn by another path (the
// PS2 world, or the room's own scenery under COARSE_SCENERY_FALLBACK), no collision piece is drawn, not only
// piece 0. The other pieces are gameplay-only collision: AEV wall areas (sce_at.cpp sceAtSetScrAt, attr 0x40)
// and object pieces, which the GameCube never draws (r100 bridge: the post-s20 wall drew as a flat block).
#ifndef RE4DC_COARSE_SAT_SCENERY_ONLY
#define RE4DC_COARSE_SAT_SCENERY_ONLY 0
#endif
#if RE4DC_COARSE_SCENERY_FALLBACK
extern "C" int re4dc_ps2_world_covers(unsigned room);   // platform/native_ps2_world.cpp
#endif
#include "global.h"
#include "player.h"
#include "pl_npc.h"
#include "em.h"
#include "atari.h"
#include "model.h"
#include "esp.h"
#include "espgen.h"
#include "camera.h"
#include "view.h"
#include <dc/matrix.h>
#include <dc/pvr.h>
#include <kos/timer.h>
#include <string.h>
#include <cstdint>

// <math.h> and dolphin/gx/GXGet.h clash with the game headers (math_sub.h, gx.h): declared here.
extern "C" void GXGetProjectionv(f32* p);                // platform/gx_stub.cpp
extern "C" void GXGetViewportv(f32* vp);
extern "C" std::uint32_t* re4dc_coarse_begin(int fog);   // platform/native_ui.cpp
extern "C" void re4dc_coarse_end(unsigned vertices);
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" void* re4dc_ui_movie_texture() __attribute__((weak));   // ROUTE_MOVIES builds
extern "C" void re4dc_fog_note_far(float far) __attribute__((weak));   // NATIVE_FOG builds
extern "C" int ESP_IsActive(cEsp* esp);                             // esp.cpp (C linkage)
#if RE4DC_COARSE_WORLD
// COARSE_WORLD (game30.mk, lane wd test): the world beyond the flat collision (coarse_world.cpp; data in
// the generated private coarse_world.h). Supersedes the one-house test (COARSE_HOUSE, never landed).
#include "coarse_scene.h"
#include "coarse_world.h"
extern "C" float re4dc_fog_gate_far() __attribute__((weak));   // ACTOR_FOG_GATE builds (native_static.cpp)
#endif

// Global scope: an extern "C" name defined inside the unnamed namespace links to a silent stub.
extern "C" {
int re4dc_coarse_image;   // Render(): the image being drawn is coarse (latched by Trans())
}

#if RE4DC_COARSE_LEON
extern "C" int re4dc_coarse_leon(cModel*);
#endif
#if RE4DC_COARSE_GANADO
extern "C" int re4dc_coarse_ganado(cModel*);
extern "C" void re4dc_coarse_ganado_begin();
extern "C" void re4dc_coarse_ganado_end();
extern "C" int re4dc_coarse_ganado_layout();
#endif
#ifndef RE4DC_COARSE_SOURCE_ACTORS
#define RE4DC_COARSE_SOURCE_ACTORS 0
#endif
#if RE4DC_COARSE_SOURCE_ACTORS
extern "C" int re4dc_coarse_source_actors_ready();
extern "C" int re4dc_coarse_source_actor_route(const void*);
#if RE4DC_ACTOR_EARLY_COARSE
extern "C" void re4dc_model_packet_abort();
#endif
#endif
namespace {
constexpr float kNear = 40.0f;         // clip plane, mm in front of the eye
#ifdef RE4DC_FAR_CAP
constexpr float kFar = float(RE4DC_FAR_CAP); // FOG_FAR_CAP (post30.mk, look study): follows FOG_FAR
#else
constexpr float kFar = 25000.0f;       // block cull distance (FOG_FAR: opaque fog there)
#endif
constexpr unsigned kSplit = 30000;     // vertices per header (native_ui's store-queue window)
constexpr unsigned kMaxPolys = 1u << 16;
#if RE4DC_PS2_WORLD_DRAW
bool g_ps2_world=false; // current ordinary coarse image only
#endif
unsigned char g_seen[kMaxPolys / 8];   // polygons of this piece already drawn (blocks overlap)
// Invisible walls. Collision walls are one-sided (the normal faces the side they hold back) and the
// game's line tests are too: the camera's (cameraHitCheck, from its target to the lens) only meets
// a wall it enters from the front. So nothing keeps a wall whose plane separates the lens (in
// front) from the player (behind) out of the view: one-way barriers are such walls (r101: piece 0
// polygon 690, attr 40000000, 0.5 m in front of the lens, covered the whole view and, the port's
// ClearZbuf being a GX sink, the HUD gauge's 3D digits too). Not drawn: back faces, walls with the
// player behind their plane, and walls the camera looks through by attribute (its scenery test:
// SatMgr.hitCheck flag 0x8000 mask 0x1C2810, which also passes attr 0x800000; attr 0x400: the
// camera-only bounds, seen by flag 0x8000 checks alone).
constexpr u32 kSeeThrough = 0x800000u | 0x1C2810u | 0x400u;

struct Stats {
    unsigned frames, pieces, blocks, polys, backs, hidden, tris, verts, clipped, actors, segments, effects, us;
    unsigned maxVerts, maxUs;
#if RE4DC_COARSE_WORLD
    unsigned replaced;   // collision polygons drawn by coarse_world.cpp instead
#endif
} g_st;
#if RE4DC_COARSE_WORLD
bool g_world;   // COARSE_WORLD: this image is in the data's room and its piece 0 matches
#endif

// ------------------------------------------------------------------ store-queue output
struct Out {
    std::uint32_t* sq;
    unsigned n;       // vertices under the current header
    unsigned total;   // vertices this image
};
inline std::uint32_t fbits(float f) { return __builtin_bit_cast(std::uint32_t, f); }
#if RE4DC_COARSE >= 2
// COARSE=2 probe: in the logged images every emitted triangle is tested against a few screen
// points; the nearest (largest 1/W') at each point is what the PVR shows there.
struct Probe {
    float x, y, z;
    char kind;       // W world, A actor segment, B blob, E effect
    unsigned a, b;   // W: piece, polygon; A / B: actor id, part; E: effect slot
};
Probe g_probe[6];
bool g_probing;
char g_kind;
unsigned g_ta, g_tb;
float g_px[2], g_py[2], g_pz[2];
unsigned g_pn;
void probe_tri(float x0, float y0, float z0, float x1, float y1, float z1, float x2, float y2, float z2)
{
    const float d = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0);
    if (d == 0.0f) {
        return;
    }
    for (Probe& p : g_probe) {
        const float b1 = ((p.x - x0) * (y2 - y0) - (x2 - x0) * (p.y - y0)) / d;
        const float b2 = ((x1 - x0) * (p.y - y0) - (p.x - x0) * (y1 - y0)) / d;
        if (b1 < 0.0f || b2 < 0.0f || b1 + b2 > 1.0f) {
            continue;
        }
        const float z = z0 + b1 * (z1 - z0) + b2 * (z2 - z0);
        if (z > p.z) {
            p.z = z;
            p.kind = g_kind;
            p.a = g_ta;
            p.b = g_tb;
        }
    }
}
inline void tag(char kind, unsigned a, unsigned b)
{
    g_kind = kind;
    g_ta = a;
    g_tb = b;
}
// Attribute words of the candidate polygons of a probed image (floor or not): value -> count.
struct AttrCount {
    u32 attr;
    unsigned floor, other;
};
AttrCount g_attrs[40];
unsigned g_nattrs;
void note_attr(u32 attr, bool floor)
{
    unsigned i = 0;
    while (i < g_nattrs && g_attrs[i].attr != attr) {
        ++i;
    }
    if (i == g_nattrs) {
        if (g_nattrs == 40) {
            return;
        }
        g_attrs[g_nattrs++] = AttrCount{attr, 0, 0};
    }
    (floor ? g_attrs[i].floor : g_attrs[i].other)++;
}
#else
inline void tag(char, unsigned, unsigned) {}
#endif
inline void put(Out& o, std::uint32_t cmd, float x, float y, float z, std::uint32_t argb)
{
#if RE4DC_COARSE >= 2
    if (g_probing) {
        if (g_pn >= 2) {
            probe_tri(g_px[0], g_py[0], g_pz[0], g_px[1], g_py[1], g_pz[1], x, y, z);
        }
        g_px[0] = g_px[1];
        g_py[0] = g_py[1];
        g_pz[0] = g_pz[1];
        g_px[1] = x;
        g_py[1] = y;
        g_pz[1] = z;
        g_pn = cmd == PVR_CMD_VERTEX_EOL ? 0 : g_pn + 1;
    }
#endif
    std::uint32_t* d = o.sq;
    d[0] = cmd;
    d[1] = fbits(x);
    d[2] = fbits(y);
    d[3] = fbits(z);
    d[4] = 0;
    d[5] = 0;
    d[6] = argb;
    d[7] = 0;
    __asm__ __volatile__("pref @%0" : : "r"(d) : "memory");
    o.sq = d + 8;
    o.n++;
}
// Between strips: a new header before the store-queue window fills. False: stop drawing.
inline bool room(Out& o)
{
    if (o.n < kSplit) {
        return o.sq != nullptr;
    }
    re4dc_coarse_end(o.n);
    o.total += o.n;
    o.n = 0;
    o.sq = re4dc_coarse_begin(1);
    return o.sq != nullptr;
}

// ------------------------------------------------------------------ camera
// Screen rows as native_actor_fast.cpp screen_rows: X' Y' W' of a world point; the screen point
// is (X'/W', Y'/W') and the PVR depth 1/W' (GEQUAL).
float g_S[3][4];
float g_focal;                // 320 * P[1]: pixels per unit x at W' = 1
Vec g_eye, g_dir;             // eye and horizontal view direction (world)
Vec g_subject;                // the player's chest (the lens's subject), or the look-at point
float g_cosHalf, g_sinHalf;   // inflated horizontal half field of view
float g_n0x, g_n0z, g_n1x, g_n1z;   // inward side-plane normals (world XZ) through the eye

// Inward normals of the two side planes for a horizontal view direction (x, z).
inline void side_planes(float x, float z, float& n0x, float& n0z, float& n1x, float& n1z)
{
    n0x = x * g_sinHalf + z * g_cosHalf;
    n0z = z * g_sinHalf - x * g_cosHalf;
    n1x = x * g_sinHalf - z * g_cosHalf;
    n1z = z * g_sinHalf + x * g_cosHalf;
}

void setup_camera()
{
    CameraCurrentProjection();
    f32 P[7], V[6];
    GXGetProjectionv(P);
    GXGetViewportv(V);
    const float* m = &pG->Cam.v_mat[0][0];
#if RE4DC_PS2_WORLD_MESH
    re4dc_ps2_mesh_camera(m, P, V); // the PS2 world's MeshDraw path needs view, projection, viewport
#endif
    const float cx = (V[0] + V[2] * 0.5f) * RE4DC_SCREEN_WF / V[2];
    const float cy = (V[1] + V[3] * 0.5f) * RE4DC_SCREEN_HF / V[3];
    const float rows[3][3] = {{RE4DC_SCREEN_HALF_WF * P[1], 0.0f, RE4DC_SCREEN_HALF_WF * P[2] - cx},
                              {0.0f, -RE4DC_SCREEN_HALF_HF * P[3], -RE4DC_SCREEN_HALF_HF * P[4] - cy},
                              {0.0f, 0.0f, -1.0f}};
    for (unsigned r = 0; r < 3; ++r) {
        for (unsigned c = 0; c < 4; ++c) {
            g_S[r][c] = rows[r][0] * m[c] + rows[r][1] * m[4 + c] + rows[r][2] * m[8 + c];
        }
    }
    g_focal = RE4DC_SCREEN_HALF_WF * P[1];
    g_eye = pG->Cam.param.pos;
    float dx = pG->Cam.param.at.x - g_eye.x, dz = pG->Cam.param.at.z - g_eye.z;
    const float l = __builtin_sqrtf(dx * dx + dz * dz);
    if (l > 1e-3f) {
        dx /= l;
        dz /= l;
    } else {
        dx = 0.0f;
        dz = 1.0f;
    }
    g_dir.x = dx;
    g_dir.y = 0.0f;
    g_dir.z = dz;
    if (pPL) {
        g_subject = Vec{pPL->pos.x, pPL->pos.y + 1200.0f, pPL->pos.z};
    } else {
        g_subject = pG->Cam.param.at;
    }
    // P[1] = cot(fovx / 2): half = atan(1 / P[1]) + 0.21 rad (~12 degrees for the pitch of the
    // shoulder camera), by the angle sum.
    const float t = 1.0f / P[1];
    const float ca = 1.0f / __builtin_sqrtf(1.0f + t * t), sa = t * ca;
    g_cosHalf = ca * 0.978031f - sa * 0.208460f;
    g_sinHalf = sa * 0.978031f + ca * 0.208460f;
    side_planes(dx, dz, g_n0x, g_n0z, g_n1x, g_n1z);
}

// XMTRX = [rows; 0 0 0 1] (KOS matrix_t is column-major: mt[column][row]).
void load_rows(const float R[3][4])
{
    static matrix_t mt __attribute__((aligned(32)));
    for (unsigned c = 0; c < 4; ++c) {
        mt[c][0] = R[0][c];
        mt[c][1] = R[1][c];
        mt[c][2] = R[2][c];
        mt[c][3] = c == 3 ? 1.0f : 0.0f;
    }
    mat_load(&mt);
}

// R = S * [A; 0 0 0 1] (A: 3x4 affine, piece -> world)
void compose(const float A[3][4], float R[3][4])
{
    for (unsigned r = 0; r < 3; ++r) {
        for (unsigned c = 0; c < 4; ++c) {
            float v = g_S[r][0] * A[0][c] + g_S[r][1] * A[1][c] + g_S[r][2] * A[2][c];
            if (c == 3) {
                v += g_S[r][3];
            }
            R[r][c] = v;
        }
    }
}

struct H {
    float x, y, w;
};
inline H xf(const Vec& p)
{
    float x = p.x, y = p.y, z = p.z;
    mat_trans_single3_nodiv(x, y, z);
    return H{x, y, z};
}
// FSRRA (1 / sqrt, pipelined; FDIV is not): rsqrt(x), and 1 / w for w > 0 as rsqrt(w * w).
inline float rsqrt(float x)
{
    __asm__("fsrra %0" : "+f"(x));
    return x;
}
inline float rcp(float w) { return rsqrt(w * w); }

// ------------------------------------------------------------------ polygons
inline std::uint32_t shade(std::uint32_t rgb, float k)
{
    if (k < 0.0f) {
        k = 0.0f;
    }
    unsigned r = (unsigned) (((rgb >> 16) & 255) * k), g = (unsigned) (((rgb >> 8) & 255) * k),
             b = (unsigned) ((rgb & 255) * k);
    r = r > 255 ? 255 : r;
    g = g > 255 ? 255 : g;
    b = b > 255 ? 255 : b;
    return 0xFF000000u | (r << 16) | (g << 8) | b;
}

// A convex polygon (3 or 4 vertices, fan order), near-clipped against W' >= kNear, as one strip.
void emit_poly(Out& o, const H* v, unsigned n, std::uint32_t argb)
{
    if (n == 3 && v[0].w >= kNear && v[1].w >= kNear && v[2].w >= kNear) {
        const float i0 = rcp(v[0].w), i1 = rcp(v[1].w), i2 = rcp(v[2].w);
        put(o, PVR_CMD_VERTEX, v[0].x * i0, v[0].y * i0, i0, argb);
        put(o, PVR_CMD_VERTEX, v[1].x * i1, v[1].y * i1, i1, argb);
        put(o, PVR_CMD_VERTEX_EOL, v[2].x * i2, v[2].y * i2, i2, argb);
        g_st.tris++;
        return;
    }
    H c[8];
    unsigned m = 0;
    for (unsigned i = 0; i < n; ++i) {
        const H& a = v[i];
        const H& b = v[i + 1 == n ? 0 : i + 1];
        const bool ia = a.w >= kNear, ib = b.w >= kNear;
        if (ia) {
            c[m++] = a;
        }
        if (ia != ib) {
            const float t = (kNear - a.w) / (b.w - a.w);
            c[m++] = H{a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, kNear};
        }
    }
    if (m < 3) {
        return;
    }
    if (m != n) {
        g_st.clipped++;
    }
    // fan 0, 1, ..., m-1 as a strip: 0, 1, m-1, 2, m-2, ...
    const H* seq[8];
    unsigned k = 0, lo = 1, hi = m - 1;
    seq[k++] = &c[0];
    seq[k++] = &c[lo++];
    while (lo <= hi) {
        seq[k++] = &c[hi--];
        if (lo <= hi) {
            seq[k++] = &c[lo++];
        }
    }
    for (unsigned i = 0; i < k; ++i) {
        const float iw = rcp(seq[i]->w);
        put(o, i + 1 == k ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX, seq[i]->x * iw, seq[i]->y * iw, iw, argb);
    }
    g_st.tris += k - 2;
}

// ------------------------------------------------------------------ world (collision pieces)
struct PieceView {
    Vec eye;                    // eye in piece space
    Vec subject;                // g_subject in piece space
    Vec dir;                    // horizontal view direction in piece space
    float n0x, n0z, n1x, n1z;   // inward side-plane normals (XZ) through the eye
};

bool block_visible(const PieceView& pv, const cSatBlock* b)
{
    const float x0 = b->min.x, z0 = b->min.z, x1 = x0 + b->m_Size.x, z1 = z0 + b->m_Size.z;
    const float dx = pv.eye.x < x0 ? x0 - pv.eye.x : pv.eye.x > x1 ? pv.eye.x - x1 : 0.0f;
    const float dz = pv.eye.z < z0 ? z0 - pv.eye.z : pv.eye.z > z1 ? pv.eye.z - z1 : 0.0f;
    if (dx * dx + dz * dz > kFar * kFar) {
        return false;
    }
    if (dx == 0.0f && dz == 0.0f) {
        return true;   // the eye is over the block
    }
    const float xs[4] = {x0, x1, x1, x0}, zs[4] = {z0, z0, z1, z1};
    int behind = 0, out0 = 0, out1 = 0;
    for (int i = 0; i < 4; ++i) {
        const float rx = xs[i] - pv.eye.x, rz = zs[i] - pv.eye.z;
        behind += rx * pv.dir.x + rz * pv.dir.z < -1500.0f;
        out0 += rx * pv.n0x + rz * pv.n0z < -800.0f;
        out1 += rx * pv.n1x + rz * pv.n1z < -800.0f;
    }
    return behind < 4 && out0 < 4 && out1 < 4;
}

unsigned g_piece;   // SatMgr index of the piece being drawn (COARSE=2 probe tags)

void draw_block_polys(Out& o, cSat* sat, const cSatBlock* b, const PieceView& pv, const float N[3][3])
{
    const unsigned n = (unsigned) b->m_nFloor + b->m_nSlope + b->m_nWall;
    const u16* idx = b->idx;
    for (unsigned i = 0; i < n; ++i) {
        const unsigned no = idx[i];
        if (no >= kMaxPolys) {
            continue;
        }
        const unsigned char bit = (unsigned char) (1u << (no & 7));
        if (g_seen[no >> 3] & bit) {
            continue;
        }
        g_seen[no >> 3] |= bit;
#if RE4DC_COARSE_WORLD & 0x33
        if (g_world && g_piece == 0 && no < coarse_world::kPolys) {
            unsigned char skip = 0;
#if RE4DC_COARSE_WORLD & 1
            skip |= coarse_world::kSkip[no >> 3];   // drawn as a house shell (coarse_world.cpp)
#endif
#if RE4DC_COARSE_WORLD & 2
            skip |= coarse_world::kSkipGround[no >> 3];   // drawn as the ground (coarse_world.cpp)
#endif
#if RE4DC_COARSE_WORLD & 16
            skip |= coarse_world::kSkipMesh[no >> 3];   // drawn as a mesh record (R1)
#endif
#if RE4DC_COARSE_WORLD & 32
            skip |= coarse_world::kSkipBackdrop[no >> 3];   // stood in for by the far scenery (R7)
#endif
            if (skip & bit) {
                g_st.replaced++;
                continue;
            }
        }
#endif
        const AtPoly& p = sat->poly_p[no];
        // the world normal (rotation part of the piece matrix): the class and the flat light
        const Vec& pn = sat->norm_p[p.n];
        const Vec& a = sat->vtx[p.v[0]];
        if (pn.x * (pv.eye.x - a.x) + pn.y * (pv.eye.y - a.y) + pn.z * (pv.eye.z - a.z) <= 0.0f) {
            g_st.backs++;
            continue;   // the eye sees its back
        }
        const float ny = N[1][0] * pn.x + N[1][1] * pn.y + N[1][2] * pn.z;
#if RE4DC_COARSE >= 2
        if (g_probing) {
            note_attr(p.attr, ny > 0.7f);
        }
#endif
        if (ny <= 0.7f && ((p.attr & kSeeThrough) ||
                           pn.x * (pv.subject.x - a.x) + pn.y * (pv.subject.y - a.y) + pn.z * (pv.subject.z - a.z) < 0.0f)) {
            g_st.hidden++;
            continue;   // invisible wall: see-through by attribute, or the player behind its plane
        }
        g_st.polys++;
        H v[3];
        v[0] = xf(a);
        v[1] = xf(sat->vtx[p.v[1]]);
        v[2] = xf(sat->vtx[p.v[2]]);
        if (v[0].w < kNear && v[1].w < kNear && v[2].w < kNear) {
            continue;
        }
        if (!room(o)) {
            return;
        }
        const float nx = N[0][0] * pn.x + N[0][1] * pn.y + N[0][2] * pn.z;
        const float nz = N[2][0] * pn.x + N[2][1] * pn.y + N[2][2] * pn.z;
        // the village's tones (fog 716C5A): the HUD gauge is a translucent lens over the view, and
        // its unlit LCD segments show against a light one
        std::uint32_t base;
        if (ny > 0.7f) {
            base = 0x5C5240;   // floors: earth
        } else if (ny < -0.7f) {
            base = 0x443C36;   // ceilings, undersides
        } else {
            base = 0x70685C;   // walls
        }
        const float d = nx * 0.42f + ny * 0.78f + nz * 0.46f;
        tag('W', g_piece, no);
        emit_poly(o, v, 3, shade(base, 0.42f + 0.58f * (d > 0.0f ? d : -0.35f * d)));
    }
}

void draw_blocks(Out& o, cSat* sat, const cSatBlock* b, const PieceView& pv, const float N[3][3])
{
    for (; b; b = b->next) {
        if (!block_visible(pv, b)) {
            continue;
        }
        g_st.blocks++;
        if (b->m_Flag & 1) {
            draw_blocks(o, sat, (const cSatBlock*) b->idx, pv, N);
        } else {
            draw_block_polys(o, sat, b, pv, N);
        }
    }
}

void draw_world(Out& o)
{
#if RE4DC_COARSE_SAT_SCENERY_ONLY
    bool scenery_drawn = false;
#if RE4DC_PS2_WORLD_DRAW
    scenery_drawn = scenery_drawn || g_ps2_world;
#endif
#if RE4DC_COARSE_SCENERY_FALLBACK
    scenery_drawn = scenery_drawn || !re4dc_ps2_world_covers(G_ROOM_ID);
#endif
    if (scenery_drawn) {
        return;   // every piece is collision only: the scenery path draws what is seen
    }
#endif
    for (u32 i = 0; i < SatMgr.nArray; ++i) {
#if RE4DC_PS2_WORLD_DRAW
        if(i==0 && g_ps2_world)continue; // replaces diagnostic collision drawing only
#endif
#if RE4DC_COARSE_SCENERY_FALLBACK
        if(i==0 && !re4dc_ps2_world_covers(G_ROOM_ID))continue; // the room's own scenery draws (trans.cpp)
#endif
#if RE4DC_COARSE_WORLD & 128
        if (i == 0 && g_world) {
            continue;   // K0: the world data covers every piece-0 polygon (coarse_world.h kCover); drawing only
        }
#endif
        cSat* sat = (cSat*) ((u8*) SatMgr.pArray + SatMgr.size * i);
        if (!sat->isAlive() || !sat->block_p || !sat->poly_p) {
            continue;
        }
        g_st.pieces++;
        g_piece = i;
        PieceView pv;
        PSMTXMultVec(sat->imat, &g_eye, &pv.eye);
        PSMTXMultVec(sat->imat, &g_subject, &pv.subject);
        PSMTXMultVecSR(sat->imat, &g_dir, &pv.dir);
        pv.n0x = pv.dir.x * g_sinHalf + pv.dir.z * g_cosHalf;
        pv.n0z = pv.dir.z * g_sinHalf - pv.dir.x * g_cosHalf;
        pv.n1x = pv.dir.x * g_sinHalf - pv.dir.z * g_cosHalf;
        pv.n1z = pv.dir.z * g_sinHalf + pv.dir.x * g_cosHalf;
        const unsigned bytes = (sat->polygon_num + 7u) / 8u;
        memset(g_seen, 0, bytes < sizeof(g_seen) ? bytes : sizeof(g_seen));
        float R[3][4];
        compose(sat->mat, R);
        load_rows(R);
        float N[3][3];
        for (int r = 0; r < 3; ++r) {
            for (int c = 0; c < 3; ++c) {
                N[r][c] = sat->mat[r][c];
            }
        }
        draw_blocks(o, sat, sat->block_p, pv, N);
    }
}

// ------------------------------------------------------------------ actors
// A bone as a camera-facing ribbon: the two joints projected (2 transforms), widened across the
// screen direction of the bone by the limb half-thickness t at each end's depth (at least 0.75 px),
// lit side to shaded side across the width (a cylinder's look), one 4-vertex strip.
void segment(Out& o, const Vec& a, const Vec& b, float t, std::uint32_t rgb)
{
    const float dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
    const float len2 = dx * dx + dy * dy + dz * dz;
    if (len2 < 60.0f * 60.0f || len2 > 1600.0f * 1600.0f) {
        return;   // face / finger bones: a cluster of squares at limb width
    }
    const float tl = 0.3f * len2 * rsqrt(len2);   // no wider than 0.3 x the bone
    t = t < tl ? t : tl;
    const H ha = xf(a), hb = xf(b);
    if (ha.w < kNear || hb.w < kNear || !room(o)) {
        return;
    }
    const float ia = rcp(ha.w), ib = rcp(hb.w);
    const float ax = ha.x * ia, ay = ha.y * ia, bx = hb.x * ib, by = hb.y * ib;
    float px = ay - by, py = bx - ax;
    const float pl2 = px * px + py * py;
    if (pl2 > 1e-4f) {
        const float il = rsqrt(pl2);
        px *= il;
        py *= il;
    } else {
        px = 1.0f;   // the bone points at the eye: a square of the half width
        py = 0.0f;
    }
    float wa = t * g_focal * ia, wb = t * g_focal * ib;
    wa = wa < 0.75f ? 0.75f : wa;
    wb = wb < 0.75f ? 0.75f : wb;
    const float k = 0.62f + 0.38f * (dy * dy) * rsqrt(len2 * len2);   // upright limbs catch more light
    const std::uint32_t lit = shade(rgb, k * 1.15f), dark = shade(rgb, k * 0.62f);
    put(o, PVR_CMD_VERTEX, ax + px * wa, ay + py * wa, ia, lit);
    put(o, PVR_CMD_VERTEX, ax - px * wa, ay - py * wa, ia, dark);
    put(o, PVR_CMD_VERTEX, bx + px * wb, by + py * wb, ib, lit);
    put(o, PVR_CMD_VERTEX_EOL, bx - px * wb, by - py * wb, ib, dark);
    g_st.tris += 2;
    g_st.segments++;
}

// Actor bounding sphere (0.9 m above its position, radius 2 m) against the view: distance, behind
// the eye, outside a side plane.
bool actor_visible(const cModel* m)
{
    const float r = 2000.0f;
    const float rx = m->pos.x - g_eye.x, rz = m->pos.z - g_eye.z;
    if (rx * rx + rz * rz > (kFar + r) * (kFar + r)) {
        return false;
    }
    return rx * g_dir.x + rz * g_dir.z > -r && rx * g_n0x + rz * g_n0z > -r && rx * g_n1x + rz * g_n1z > -r;
}

void blob(Out& o, const Vec& at, float r)
{
    const Vec q[4] = {{at.x - r, at.y + 8.0f, at.z - r}, {at.x + r, at.y + 8.0f, at.z - r},
                      {at.x + r, at.y + 8.0f, at.z + r}, {at.x - r, at.y + 8.0f, at.z + r}};
    H v[4];
    for (int i = 0; i < 4; ++i) {
        v[i] = xf(q[i]);
    }
    if (room(o)) {
        emit_poly(o, v, 4, 0xFF1C1814);
    }
}

void draw_model(Out& o, cModel* m, std::uint32_t rgb, float t)
{
#if RE4DC_COARSE_SOURCE_ACTORS
    // Both source-handled and invalid membership suppress this substitute.
    // Invalid membership is logged by the owner and invalidates the candidate.
    if(re4dc_coarse_source_actor_route(m)!=0)return;
#endif
    bool crowd_layout=false;
#if RE4DC_COARSE_GANADO
    crowd_layout=re4dc_coarse_ganado_layout() && m->id>=0x10 && m->id<=0x20;
#endif
#if !RE4DC_ACTOR_EARLY_COARSE
    if (!crowd_layout && !actor_visible(m))return;
#endif
    g_st.actors++;
#if RE4DC_COARSE_LEON
    if(m==(cModel*)pPL){
        if(o.sq)re4dc_coarse_end(o.n);
        o.total+=o.n;o.n=0;o.sq=nullptr;
        const int handled=re4dc_coarse_leon(m);
        o.sq=re4dc_coarse_begin(1);load_rows(g_S);
        if(handled){if(o.sq)blob(o,m->pos,330.0f);return;}
    }
#endif
#if RE4DC_COARSE_GANADO
    if(m->id>=0x10 && m->id<=0x20){
        if(o.sq)re4dc_coarse_end(o.n);
        o.total+=o.n;o.n=0;o.sq=nullptr;
        const int handled=re4dc_coarse_ganado(m);
#if RE4DC_ACTOR_EARLY_COARSE
        if(!handled){re4dc_model_packet_abort();return;}
#endif
        o.sq=re4dc_coarse_begin(1);load_rows(g_S);
        if(handled){if(o.sq && !crowd_layout)blob(o,m->pos,330.0f);return;}
    }
#endif
#if RE4DC_ACTOR_EARLY_COARSE
    re4dc_model_packet_abort();return; // no ribbon substitute for an admitted actor
#endif
    for (cParts* p = m->pList; p; p = p->pList) {
        if (p->motParts.flags & 2) {
            continue;   // no world matrix this tick (partsWorldCalc skipped it)
        }
        const cCoord* q = p->pParent;
        if (!q || q == (const cCoord*) m) {
            continue;
        }
        const Vec a = {q->mat[0][3], q->mat[1][3], q->mat[2][3]};
        const Vec b = {p->mat[0][3], p->mat[1][3], p->mat[2][3]};
        tag('A', m->id, 0);
        segment(o, a, b, t, rgb);
    }
    tag('B', m->id, 0);
    blob(o, m->pos, 330.0f);
}

void draw_actors(Out& o)
{
#if RE4DC_COARSE_GANADO
    re4dc_coarse_ganado_begin();
#endif
    load_rows(g_S);
    cModel* pl = pPL;
    cModel* sub = pSUB;
    if (pl && (pl->be_flag & 3) == 3) {
        draw_model(o, pl, 0x2F4F9A, 42.0f);
    }
    if (sub && (sub->be_flag & 3) == 3) {
        draw_model(o, sub, 0xC89A3C, 38.0f);
    }
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        cModel* m = e;
        if (m == pl || m == sub || (m->be_flag & 3) != 3) {
            continue;
        }
        const bool ganado = m->id >= 0x10 && m->id <= 0x20;
        draw_model(o, m, ganado ? 0x8A5A3A : 0x707070, ganado ? 44.0f : 60.0f);
    }
#if RE4DC_COARSE_GANADO
    re4dc_coarse_ganado_end();
#endif
}

// ------------------------------------------------------------------ effects
inline unsigned byte255(float v) { return v <= 0.0f ? 0u : v >= 255.0f ? 255u : (unsigned) v; }

#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
extern "C" int re4dc_esp_sprite_class(cEsp* esp);   // esp_sub.cpp (COARSE_FX_SPRITES, effects30.mk)
#endif
void draw_effects(Out& o)
{
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES >= 2
    return;   // the sprite classes draw in the effect OT; no markers for the rest
#endif
    cEspSystem* sys = g_pEspSys;
    if (!sys || !sys->pEspBuf) {
        return;
    }
    // ESP_IsActive(e) is (m_Be_flg & 1) outside the event pause (Status_flg[1] 0x10000000): call it
    // only under the pause (446 calls per drawn tick in the r101 square).
    const bool pause = (pG->Status_flg[1] & 0x10000000) != 0;
    for (u32 i = 0; i < sys->nEsp; i++) {
        cEsp* e = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (!(e->m_Be_flg & 1) || (pause && !ESP_IsActive(e))) {
            continue;
        }
        if ((u8) (e->m_Parts_no + 8) <= 5) {
            continue;   // screen sprite (Parts_no 0xF8 .. 0xFD)
        }
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
        if (re4dc_esp_sprite_class(e)) {
            continue;   // a native sprite in the effect OT (esp.cpp queued its EspCommonTrans)
        }
#endif
        if (e->m_Col_a < 64.0f) {
            continue;   // faint (ambient haze, fading smoke): opaque here, it would hide the view
        }
        Vec w;
        if (e->parent && e->parent != pEffParentWorld) {
            PSMTXMultVec(e->parent->mat, &e->m_Pos, &w);
        } else {
            w = e->m_Pos;
        }
        const H c = xf(w);
        if (c.w < 300.0f || !room(o)) {
            continue;   // at the lens: a full-screen square
        }
        const float s = e->m_Size_base_x * e->m_Size_mul;
        const float iw = rcp(c.w);
        float r = s * g_focal * iw * 0.5f;
        r = r < 1.5f ? 1.5f : r > 32.0f ? 32.0f : r;   // opaque: a marker, never a screen cover
        const float sx = c.x * iw, sy = c.y * iw;
        const std::uint32_t argb =
            0xFF000000u | (byte255(e->m_Col_r) << 16) | (byte255(e->m_Col_g) << 8) | byte255(e->m_Col_b);
        tag('E', i, 0);
        put(o, PVR_CMD_VERTEX, sx - r, sy + r, iw, argb);
        put(o, PVR_CMD_VERTEX, sx - r, sy - r, iw, argb);
        put(o, PVR_CMD_VERTEX, sx + r, sy + r, iw, argb);
        put(o, PVR_CMD_VERTEX_EOL, sx + r, sy - r, iw, argb);
        g_st.tris += 2;
        g_st.effects++;
    }
}
}  // namespace

#if RE4DC_NO_STD_SCENERY
#if !RE4DC_COARSE_WORLD
#error COARSE_NO_STD_SCENERY needs COARSE_WORLD (the room the coarse world draws)
#endif
// COARSE_NO_STD_SCENERY (game30.mk): native_static.cpp skips the scenery mesh package of the room this data draws
// and counts that package's readers by the image kind each tick latches.
extern "C" void re4dc_std_scenery_tick(int coarse);   // platform/native_static.cpp
extern "C" unsigned re4dc_coarse_world_room()
{
    return coarse_world::kRoom;
}
#endif
#if !RE4DC_NO_STD_SCENERY && RE4DC_PS2_WORLD_ROOMS >= 2
extern "C" void re4dc_std_scenery_tick(int coarse);   // platform/native_static.cpp (PS2_WORLD_ROOMS=2)
#endif
#if RE4DC_PS2_WORLD_ROOMS >= 2
// PS2_WORLD_ROOMS=2 (native_static.cpp re4dc_ps2_mesh_source): the camera of the source image being drawn, read
// at its first scenery part (the GX projection / viewport that part draws with); sets nothing.
extern "C" int re4dc_coarse_source_camera(float view[12], float projection[7], float viewport[6])
{
    if (!pG) {
        return 0;
    }
    memcpy(view, &pG->Cam.v_mat[0][0], 12 * sizeof(float));
    GXGetProjectionv(projection);
    GXGetViewportv(viewport);
    return 1;
}
#endif
// Trans() of tick k: 1 in in-room play (the pace.cpp context: Rno0 3, no held picture or room
// change, no sub screen, no movie), where the presentation stages run in the qualified skip mode.
// Latches whether image k (drawn by iteration k+1) is coarse: every such image not dropped.
extern "C" int re4dc_coarse_tick(int dropped)
{
    int ctx = pG && pG->Rno0 == 3 && !(pG->System_flg & (0x400 | 0x100000)) && !(pG->Status_flg[2] & 0x04000000);
    if (ctx && re4dc_ui_movie_texture && re4dc_ui_movie_texture()) {
        ctx = 0;
    }
    re4dc_coarse_image = ctx && !dropped;
#if RE4DC_NO_STD_SCENERY || RE4DC_PS2_WORLD_ROOMS >= 2
    re4dc_std_scenery_tick(re4dc_coarse_image);
#endif
    return ctx;
}

// Render() of a coarse image: the whole opaque view, before the effect / HUD OTs.
extern "C" void re4dc_coarse_draw(void)
{
#if RE4DC_COARSE_SOURCE_ACTORS
    // Validate all actors before the first coarse TA header; no late source retry.
    if(!re4dc_coarse_source_actors_ready())return;
#endif
    if (!pG || !SatMgr.pArray) {
        return;
    }
    const std::uint64_t t0 = timer_us_gettime64();
#if RE4DC_PS2_WORLD_DRAW
    // Texture/file work must precede coarse_begin acquiring the TA store queues.
    setup_camera();
    if(re4dc_fog_note_far)re4dc_fog_note_far(View._zfar);
    g_ps2_world=re4dc_ps2_world_draw(G_ROOM_ID,g_S,View._zfar)!=0;
#endif
    Out o{re4dc_coarse_begin(1), 0, 0};
    if (!o.sq) {
        return;
    }
    if (re4dc_fog_note_far) {
        re4dc_fog_note_far(View._zfar);   // as a native model draw would: the fog table's far (FOG_FAR)
    }
    #if !RE4DC_PS2_WORLD_DRAW
    setup_camera();
    #endif
#if RE4DC_COARSE >= 2
    // COARSE=2 (diagnostic): the first images log the camera, Leon's projected root and the first
    // world triangle (native_ui logs the stream state at re4dc_coarse_begin).
    static unsigned dbg;
    if (dbg < 4 || dbg % 600 == 0) {
        load_rows(g_S);
        re4dc_log("COARSE2 n=%u eye %.0f %.0f %.0f dir %.3f %.3f focal %.1f S2 %.4f %.4f %.4f %.1f\n", dbg, g_eye.x,
                  g_eye.y, g_eye.z, g_dir.x, g_dir.z, g_focal, g_S[2][0], g_S[2][1], g_S[2][2], g_S[2][3]);
        if (pPL) {
            const Vec r = {pPL->pos.x, pPL->pos.y + 1000.0f, pPL->pos.z};
            const H h = xf(r);
            re4dc_log("COARSE2 leon %.0f %.0f %.0f -> screen %.1f %.1f w %.1f\n", r.x, r.y, r.z, h.x / h.w, h.y / h.w, h.w);
        }
        for (u32 i = 0; i < SatMgr.nArray; ++i) {
            cSat* sat = (cSat*) ((u8*) SatMgr.pArray + SatMgr.size * i);
            if (!sat->isAlive() || !sat->poly_p) {
                continue;
            }
            const float(*M)[4] = sat->mat;
            re4dc_log("COARSE2 piece %u polys %u mat %.3f %.3f %.3f %.0f | %.3f %.3f %.3f %.0f | %.3f %.3f %.3f %.0f\n", i,
                      sat->polygon_num, M[0][0], M[0][1], M[0][2], M[0][3], M[1][0], M[1][1], M[1][2], M[1][3],
                      M[2][0], M[2][1], M[2][2], M[2][3]);
        }
        static const float pts[6][2] = {{320, 240}, {120, 120}, {520, 120}, {120, 360}, {520, 360}, {320, 400}};
        for (unsigned i = 0; i < 6; ++i) {
            g_probe[i] = Probe{pts[i][0], pts[i][1], 0.0f, '-', 0, 0};
        }
        g_pn = 0;
        g_nattrs = 0;
        g_probing = true;
    }
    ++dbg;
#endif
#if RE4DC_COARSE_WORLD
    {
        const cSat* s0 = (const cSat*) SatMgr.pArray;
        g_world = G_ROOM_ID == coarse_world::kRoom && SatMgr.nArray > 0 && s0->isAlive() &&
                  s0->polygon_num == coarse_world::kPolys;
    }
#endif
    draw_world(o);
#if RE4DC_COARSE_WORLD
    if (g_world) {
        CoarseView v;
        for (unsigned r = 0; r < 3; ++r) {
            for (unsigned c = 0; c < 4; ++c) {
                v.S[r][c] = g_S[r][c];
            }
        }
        v.eye[0] = g_eye.x;
        v.eye[1] = g_eye.y;
        v.eye[2] = g_eye.z;
        v.dir[0] = g_dir.x;
        v.dir[1] = g_dir.z;
        v.n0[0] = g_n0x;
        v.n0[1] = g_n0z;
        v.n1[0] = g_n1x;
        v.n1[1] = g_n1z;
        v.focal = g_focal;
        const float fog_far = re4dc_fog_gate_far ? re4dc_fog_gate_far() : 0.0f;
        v.far = fog_far > 1000.0f && fog_far < kFar ? fog_far : kFar;
        v.det = g_S[0][0] * (g_S[1][1] * g_S[2][2] - g_S[1][2] * g_S[2][1]) -
                g_S[0][1] * (g_S[1][0] * g_S[2][2] - g_S[1][2] * g_S[2][0]) +
                g_S[0][2] * (g_S[1][0] * g_S[2][1] - g_S[1][1] * g_S[2][0]);
        v.fog_rgb[0] = 113.0f;   // r101's fog table colour 716C5A (the sky's horizon, later bits)
        v.fog_rgb[1] = 108.0f;
        v.fog_rgb[2] = 90.0f;
        if (o.sq) {
            re4dc_coarse_end(o.n);
            o.total += o.n;
            o.n = 0;
        }
        o.total += re4dc_coarse_world_draw(&v);
        o.sq = re4dc_coarse_begin(1);
    }
#endif
    draw_actors(o);
    draw_effects(o);
    if (o.sq) {
        re4dc_coarse_end(o.n);
    }
#if RE4DC_COARSE >= 2
    if (g_probing) {
        g_probing = false;
        for (const Probe& p : g_probe) {
            re4dc_log("COARSE2 probe %.0f %.0f: %c %u %u z %.3g W' %.0f\n", p.x, p.y, p.kind, p.a, p.b, p.z,
                      p.z > 0.0f ? 1.0f / p.z : 0.0f);
            if (p.kind != 'W') {
                continue;
            }
            cSat* sat = (cSat*) ((u8*) SatMgr.pArray + SatMgr.size * p.a);
            const AtPoly& q = sat->poly_p[p.b];
            Vec w[3];
            for (int k = 0; k < 3; ++k) {
                PSMTXMultVec(sat->mat, &sat->vtx[q.v[k]], &w[k]);
            }
            const Vec& n = sat->norm_p[q.n];
            re4dc_log("COARSE2   poly %.0f %.0f %.0f | %.0f %.0f %.0f | %.0f %.0f %.0f n %.2f %.2f %.2f attr %08x\n", w[0].x,
                      w[0].y, w[0].z, w[1].x, w[1].y, w[1].z, w[2].x, w[2].y, w[2].z, n.x, n.y, n.z, (unsigned) q.attr);
        }
        for (unsigned i = 0; i < g_nattrs; ++i) {
            re4dc_log("COARSE2 attr %08x floor %u other %u%s\n", (unsigned) g_attrs[i].attr, g_attrs[i].floor,
                      g_attrs[i].other, (g_attrs[i].attr & kSeeThrough) ? " see-through" : "");
        }
    }
#endif
    o.total += o.n;
    const unsigned us = (unsigned) (timer_us_gettime64() - t0);
    g_st.frames++;
    g_st.verts += o.total;
    g_st.us += us;
    g_st.maxVerts = o.total > g_st.maxVerts ? o.total : g_st.maxVerts;
    g_st.maxUs = us > g_st.maxUs ? us : g_st.maxUs;
    if (g_st.frames == 120) {
        const unsigned f = g_st.frames;
        re4dc_log("COARSE t=%u frames=%u pieces=%u blocks=%u polys=%u backs=%u hidden=%u tris=%u verts=%u/%u clipped=%u actors=%u seg=%u fx=%u us=%u/%u\n",
                  (unsigned) pG->Frame_cnt, f, g_st.pieces / f, g_st.blocks / f, g_st.polys / f, g_st.backs / f,
                  g_st.hidden / f, g_st.tris / f, g_st.verts / f, g_st.maxVerts, g_st.clipped / f,
                  g_st.actors / f, g_st.segments / f, g_st.effects / f, g_st.us / f, g_st.maxUs);
#if RE4DC_COARSE_WORLD
        re4dc_log("COARSE world replaced=%u\n", g_st.replaced / f);
        re4dc_coarse_world_log(f);
#endif
        g_st = Stats();
    }
}

#if defined(RE4DC_ENC_CENSUS) && RE4DC_ENC_CENSUS
// ENC_CENSUS (game30.mk; diagnostic, default 0, lane enc): one "ENC" line per presented frame (native_ui's frame
// mark, the hwproject frame number), read-only. ga / oa: Ganados (ids 0x10..0x20, be_flag & 0x201 == 1, act_cap's
// rule) / other enemies alive in EmMgr; gr: Ganados that reached commonModelTrans's first pass (the game's own OT
// view test passed); go / gs / gx: of those, drawn by the actor owner (the cast mesh) / left to the source path /
// failed; gb: the reaching Ganados by view distance < 5 m / 5-12 m / 12-25 m / >= 25 m; or: other enemies reaching
// commonModelTrans; ct: crowd tiers (full / near / mid / far) of the Ganado models native_actor_fast tiered since
// the last line. v2 adds sr: why the source path drew them (no cast plan: ATD 4 / sticky source choice: ATD 2 /
// other), and an "ENC_OA" line with the ids of the other enemies alive whenever that set changes.
extern "C" void re4dc_enc_crowd_tiers(unsigned* out);
extern "C" {
unsigned re4dc_enc_atd;   // actor_transaction_diag.h: ATD writes its event code here in ENC_CENSUS builds
}
namespace {
unsigned enc_reach, enc_owned, enc_source, enc_failed, enc_band[4], enc_other_reach, enc_src_why[3];
unsigned enc_oa_sig;
}
extern "C" void re4dc_enc_note_actor(const void* model, int result)
{
    const cModel* m = static_cast<const cModel*>(model);
    if (!m || m->kindid != 0 || (m->ot_type == 7 && (m->be_flag & 0x08000000))) {
        return;   // not an enemy, or the second (translucent) pass of a model already counted
    }
    if (m->id < 0x10 || m->id > 0x20) {
        ++enc_other_reach;
        return;
    }
    ++enc_reach;
    if (result < 0) {
        ++enc_failed;
    } else if (!result) {
        ++enc_source;
        ++enc_src_why[re4dc_enc_atd == 4 ? 0 : re4dc_enc_atd == 2 ? 1 : 2];
        // First source-path sighting of each model: "ENC_GS" id, parts, infos, be_flag, the ATD code.
        static const void* seen[32];
        static unsigned nseen;
        bool known = false;
        for (unsigned i = 0; i < nseen && !known; ++i) known = seen[i] == model;
        if (!known && nseen < 32) {
            seen[nseen++] = model;
            unsigned infos = 0;
            for (const cModelInfo* i = m->pModelInfo; i && infos < 99; i = i->pList) ++infos;
            re4dc_log("ENC_GS m=%p id=%02x parts=%u infos=%u be=%08x atd=%u\n", model, (unsigned) m->id,
                      (unsigned) m->nParts, infos, (unsigned) m->be_flag, re4dc_enc_atd);
        }
    } else {
        ++enc_owned;
    }
    const Mtx& v = pG->Cam.v_mat;
    const float x = v[0][0] * m->pos.x + v[0][1] * m->pos.y + v[0][2] * m->pos.z + v[0][3];
    const float y = v[1][0] * m->pos.x + v[1][1] * m->pos.y + v[1][2] * m->pos.z + v[1][3];
    const float z = v[2][0] * m->pos.x + v[2][1] * m->pos.y + v[2][2] * m->pos.z + v[2][3];
    const float d2 = x * x + y * y + z * z;
    ++enc_band[d2 < 25e6f ? 0 : d2 < 144e6f ? 1 : d2 < 625e6f ? 2 : 3];
}
#if defined(RE4DC_ENCV) && RE4DC_ENCV
// ENC_CENSUS=2 (game30.mk; diagnostic, lane iv 2026-10-05): every Ganado (ids 0x10..0x20, not Leon / the partner)
// that emTrans walks gets one visibility state per drawn image:
//   1 hidden (Disp_flg hide, event filter, be_flag 2 / 4 clear: ModelTrans returns at once)
//   2 frustum (outside the game's own OT view test, AddOt*: no OT entry, no screen matrices or lights)
//   3 off (reached the OT; the crowd policy culled it off-screen, CROWD_CULL reason 1)
//   4 fog (reached the OT; CROWD_FOGSKIP, reason 4)
//   5 empty (reached the OT and was submitted, owner or source path, but emitted no triangle)
//   6 drawn (owner path, triangles emitted)   7 source (source path, triangles emitted)
//   8 other (reached the OT without a draw: screen-matrix failure, ModelRender's early returns, a crowd cap)
// trans.cpp runs the Ganado's emTrans inside re4dc_iv_t_<state> and its ModelRender inside re4dc_iv_r_<state>, the
// state being the one of the previous drawn image (0 new: first sighting), so the hw model's call tree gives each
// state's inclusive cost and calls. "ENCV" line per presented frame: images finalized, states, how many Ganados
// changed state since their previous image (their wrapper named the old state), 5-info Ganados among off / empty /
// drawn, the emitted triangles of drawn ones, and owner / source split of empty.
extern "C" {
unsigned re4dc_encv_crowd = 0xFFU;  // coarse_actor_transaction.inc: the crowd policy's reason this call (0xFF none)
}
extern "C" float re4dc_fog_gate_far() __attribute__((weak));   // ACTOR_FOG_GATE builds (native_static.cpp)
namespace {
// g: the first pass's geometry of the part origins (view depth range, NDC x / y range of those in front of the near
// plane, how many lie behind it) and the triangles that pass fed the renderer: "ENCVE" lines (every 8th image of a
// Ganado that reached the OT) say where off / fog / empty Ganados are relative to the frustum.
struct EncvGeo { float d0, d1, x0, x1, y0, y1, nearz, farz, fog; unsigned short parts, behind; unsigned input; };
struct EncvEntry { const void* m; unsigned char prev, trans, render, infos; unsigned emit, atd, diag; EncvGeo g; };
constexpr unsigned kEncvMax = 64;
EncvEntry encv[kEncvMax];
unsigned encv_n, encv_images, encv_st[10], encv_mis, encv_x5[3], encv_tri, encv_empty_src, encv_full, encv_lines_e,
    encv_fx[7];
EncvEntry* encv_find(const void* m, bool add)
{
    for (unsigned i = 0; i < encv_n; ++i)
        if (encv[i].m == m) return &encv[i];
    if (!add) return nullptr;
    if (encv_n == kEncvMax) { ++encv_full; return nullptr; }
    EncvEntry& e = encv[encv_n++];
    e = EncvEntry{};
    e.m = m;
    return &e;
}
void encv_geo(cModel* m, EncvGeo& g)
{
    float P[7];
    GXGetProjectionv(P);
    g.nearz = P[6] / (P[5] - 1.0f); g.farz = P[6] / P[5];
    g.fog = re4dc_fog_gate_far ? re4dc_fog_gate_far() : 0.0f;
    g.d0 = g.x0 = g.y0 = 3.0e38f; g.d1 = g.x1 = g.y1 = -3.0e38f; g.parts = g.behind = 0;
    const Mtx& v = pG->Cam.v_mat;
    for (int i = 0; i < m->nParts; ++i) {
        const cModel* p = m->getPartsPtr(i);
        if (!p) continue;
        const float wx = p->mat[0][3], wy = p->mat[1][3], wz = p->mat[2][3];
        const float x = v[0][0] * wx + v[0][1] * wy + v[0][2] * wz + v[0][3];
        const float y = v[1][0] * wx + v[1][1] * wy + v[1][2] * wz + v[1][3];
        const float d = -(v[2][0] * wx + v[2][1] * wy + v[2][2] * wz + v[2][3]);
        ++g.parts;
        if (d < g.d0) g.d0 = d;
        if (d > g.d1) g.d1 = d;
        if (d < g.nearz) { ++g.behind; continue; }
        const float nx = (P[1] * x - P[2] * d) / d, ny = (P[3] * y - P[4] * d) / d;
        if (nx < g.x0) g.x0 = nx;
        if (nx > g.x1) g.x1 = nx;
        if (ny < g.y0) g.y0 = ny;
        if (ny > g.y1) g.y1 = ny;
    }
}
bool encv_ganado(const cModel* m)
{
    return m && m->kindid == 0 && m->id >= 0x10 && m->id <= 0x20 && m != (const cModel*) pPL && m != (const cModel*) pSUB;
}
}
extern "C" unsigned re4dc_encv_trans_pick(cModel* m)
{
    if (!encv_ganado(m)) return ~0U;
    EncvEntry* e = encv_find(m, true);
    if (!e) return ~0U;
    unsigned infos = 0;
    for (const cModelInfo* i = m->pModelInfo; i && infos < 99; i = i->pList) ++infos;
    e->infos = (unsigned char) infos;
    e->trans = 1;  // emTrans reached it; ModelTrans refines (hidden unless it says otherwise)
    e->render = 0; e->emit = 0; e->atd = 0;
    return e->prev;
}
extern "C" void re4dc_encv_trans_note(cModel* m, unsigned state)
{
    if (EncvEntry* e = encv_find(m, false)) e->trans = (unsigned char) state;
}
extern "C" unsigned re4dc_encv_render_pick(cModel* m)
{
    if (!encv_ganado(m)) return ~0U;
    EncvEntry* e = encv_find(m, false);
    if (!e) return ~0U;
    re4dc_encv_crowd = 0xFFU;
    re4dc_enc_atd = 0xFFFFU;  // sentinel: the actor transaction did not run (ModelRender returned before it)
    return e->prev;
}
extern "C" void re4dc_encv_render_note(cModel* m, unsigned emitted, unsigned input)
{
    EncvEntry* e = encv_find(m, false);
    if (!e) return;
    e->emit += emitted;
    if (!e->render) {  // the first pass decides; a second (translucent) pass only adds triangles
        const unsigned c = re4dc_encv_crowd, a = re4dc_enc_atd;
        // 10: submitted (owner or source path), the outcome follows from the triangles emitted.
        e->render = c == 1 ? 3 : c == 4 ? 4 : (c != 0xFFU && c != 0) ? 8 : a == 0xFFFFU ? 8 : 10;
        e->atd = a;
        encv_geo(m, e->g);
        e->g.input = 0;
    }
    e->g.input += input;
    re4dc_encv_crowd = 0xFFU;
}
extern "C" void re4dc_encv_render_done()
{
    bool any = false;
    for (unsigned i = 0; i < encv_n; ++i) {
        EncvEntry& e = encv[i];
        if (!e.trans) continue;
        any = true;
        unsigned s = e.trans;
        if (s == 9) {  // reached the OT
            if (e.render == 10) {
                const bool owner = e.atd >= 16 && e.atd <= 19;
                s = !e.emit ? 5 : owner ? 6 : 7;
                if (!e.emit && !owner) ++encv_empty_src;
            } else {
                s = e.render ? e.render : 8;
            }
        }
        ++encv_st[s];
        if (s >= 3 && s <= 7 && !(e.diag++ & 7U) && encv_lines_e < 6000) {
            ++encv_lines_e;
            const EncvGeo& g = e.g;
            re4dc_log("ENCVE t=%u id=%02x s=%u atd=%u emit=%u in=%u parts=%u behind=%u d=%d..%d nx=%d..%d ny=%d..%d "
                      "near=%d far=%d fog=%d\n", pG ? (unsigned) pG->Frame_cnt : 0U,
                      (unsigned) static_cast<const cModel*>(e.m)->id, s, e.atd, e.emit, g.input, g.parts, g.behind,
                      int(g.d0), int(g.d1), int(g.x0 * 100.0f), int(g.x1 * 100.0f), int(g.y0 * 100.0f),
                      int(g.y1 * 100.0f), int(g.nearz), int(g.farz), int(g.fog));
        }
        if (s != e.prev) ++encv_mis;
        if (e.infos >= 5 && (s == 3 || s == 5 || s == 6)) ++encv_x5[s == 3 ? 0 : s == 5 ? 1 : 2];
        if (s == 6 || s == 7) encv_tri += e.emit;
        e.prev = (unsigned char) s;
        e.trans = 0;
    }
    if (any) ++encv_images;
    // Live effects (cEsp pool) attached to a Ganado (m_pMod: follows its parts) or owned by one (Core_pEm), by the
    // Ganado's state this image: invisible (hidden .. empty) / visible (drawn, source) / other.
    if (any && g_pEspSys) {
        cEspSystem* sys = g_pEspSys;
        for (u32 i = 0; i < sys->nEsp; ++i) {
            cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);
            if (!ESP_IsActive(esp)) continue;
            ++encv_fx[0];
            for (unsigned k = 0; k < 2; ++k) {
                const void* g = k ? (const void*) esp->info.Core_pEm : (const void*) esp->m_pMod;
                const EncvEntry* o = g ? encv_find(g, false) : nullptr;
                if (!o) continue;
                const unsigned s = o->prev;
                ++encv_fx[1 + k * 3 + (s >= 1 && s <= 5 ? 0 : (s == 6 || s == 7) ? 1 : 2)];
            }
        }
    }
}
#endif
extern "C" __attribute__((noinline)) void re4dc_enc_frame(unsigned frame)
{
#if defined(RE4DC_ENCV) && RE4DC_ENCV
    re4dc_log("ENCV f=%u n=%u st=%u/%u/%u/%u/%u/%u/%u/%u/%u mis=%u x5=%u/%u/%u tri=%u esrc=%u full=%u t=%u "
              "fx=%u/%u/%u/%u/%u/%u/%u\n", frame,
              encv_images, encv_st[0], encv_st[1], encv_st[2], encv_st[3], encv_st[4], encv_st[5], encv_st[6], encv_st[7],
              encv_st[8], encv_mis, encv_x5[0], encv_x5[1], encv_x5[2], encv_tri, encv_empty_src, encv_full,
              pG ? (unsigned) pG->Frame_cnt : 0U, encv_fx[0], encv_fx[1], encv_fx[2], encv_fx[3], encv_fx[4], encv_fx[5],
              encv_fx[6]);
    encv_images = encv_mis = encv_tri = encv_empty_src = 0;
    for (unsigned& v : encv_st) v = 0;
    for (unsigned& v : encv_x5) v = 0;
    for (unsigned& v : encv_fx) v = 0;
    // Every 64th line: drop entries whose model left the enemy list (a freed work reused by another model starts
    // as new; until then it inherits the old state, counted in mis).
    static unsigned encv_lines;
    if (!(++encv_lines & 63U)) {
        for (unsigned i = 0; i < encv_n;) {
            bool alive = false;
            for (cEm* e = pG ? EmMgr.pAlive : nullptr; e && !alive; e = (cEm*) e->pNext) alive = (const void*) e == encv[i].m;
            if (alive) { ++i; continue; }
            encv[i] = encv[--encv_n];
        }
    }
#endif
    unsigned ga = 0, oa = 0, ct[4] = {}, sig = 2166136261U;
    if (pG) {
        for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
            if ((e->be_flag & 0x201) != 1) {
                continue;
            }
            if (e->id >= 0x10 && e->id <= 0x20) {
                ++ga;
            } else {
                ++oa;
                sig = (sig ^ (unsigned) e->id) * 16777619U;
            }
        }
        if (sig != enc_oa_sig) {
            enc_oa_sig = sig;
            char ids[160];
            unsigned n = 0;
            for (cEm* e = EmMgr.pAlive; e && n + 4 < sizeof(ids); e = (cEm*) e->pNext) {
                if ((e->be_flag & 0x201) == 1 && (e->id < 0x10 || e->id > 0x20)) {
                    static const char hex[] = "0123456789abcdef";
                    ids[n++] = hex[(e->id >> 4) & 15]; ids[n++] = hex[e->id & 15]; ids[n++] = ' ';
                }
            }
            ids[n] = 0;
            re4dc_log("ENC_OA f=%u n=%u ids=%s\n", frame, oa, ids);
        }
    }
    re4dc_enc_crowd_tiers(ct);
    re4dc_log("ENC f=%u ga=%u oa=%u gr=%u go=%u gs=%u gx=%u gb=%u/%u/%u/%u or=%u ct=%u/%u/%u/%u sr=%u/%u/%u hp=%d t=%u\n",
              frame, ga, oa, enc_reach, enc_owned, enc_source, enc_failed, enc_band[0], enc_band[1], enc_band[2],
              enc_band[3], enc_other_reach, ct[0], ct[1], ct[2], ct[3], enc_src_why[0], enc_src_why[1],
              enc_src_why[2], pG ? (int) (short) pG->pl_life : 0, pG ? (unsigned) pG->Frame_cnt : 0U);
    enc_reach = enc_owned = enc_source = enc_failed = enc_other_reach = 0;
    enc_band[0] = enc_band[1] = enc_band[2] = enc_band[3] = 0;
    enc_src_why[0] = enc_src_why[1] = enc_src_why[2] = 0;
}
#endif

#if RE4DC_COARSE_WORLD & 64
// COARSE_WORLD R3: native_ui's room-entry texture preload adds the world's list (coarse_world.cpp
// re4dc_coarse_world_tex) only in the data's room.
extern "C" int re4dc_coarse_world_room(void)
{
    return pG && G_ROOM_ID == coarse_world::kRoom;
}
#endif
