/* room_occl.c: ENEMY_VIS_CULL=1 (lane engine19, option C; render only): enemies the camera cannot see behind a large
 * opaque occluder of the room's PS2 world.
 *
 * The room data file's OCCL section (tools/enginebake/occl.py + occl_rank.c) holds slab occluders: a rectangle on a
 * reference plane plus a half thickness, such that the drawn opaque surface inside the slab covers the rectangle at
 * every LOD level, seen from the occluder's front side. re4dc_room_vis_hidden answers for a world box from the real eye
 * of the Trans camera: 1 only when, for one candidate occluder of the eye's 4 m cell,
 *   - the eye is in front of the slab (and the slab is one-sided toward it);
 *   - every corner of both slab faces lies deeper than the near plane and nearer than the fogged far the next Render
 *     culls the world at, and within the section's range (r100 / r101: the far shell's 18.75 m);
 *   - every corner of the box lies behind the slab's back face and inside the shadow wedges of BOTH faces from the eye,
 *     so every eye -> box segment enters and leaves the slab inside the rectangle and crosses the drawn surface;
 * and this frame's PS2 world is the one compiled from (re4dc_ps2_world_intact). Anything else: 0 (drawn).
 * The callers are CROWD_INVIS_SKIP's interior tests (coarse_actor_owner_ganado.inc); the skip is draw-only. */
#include <stdint.h>
#include <string.h>
#include "room_file.h"
#include "room_vis.h"

extern void re4dc_log(const char* fmt, ...);
extern unsigned re4dc_ui_frame(void);
extern int re4dc_ps2_world_intact(unsigned room, uint32_t crc);   /* native_static.cpp (ENEMY_VIS_CULL) */
extern int re4dc_ps2_placements_intact(unsigned room, const unsigned char* fields, unsigned n);

#define OCC_STRIDE 56
static struct {
    int ok;
    unsigned room;
    uint16_t vw, vh, nocc, nlist;
    float x0, z0, inv_cs, range2;
    uint32_t crc;
    const uint8_t* occ;     /* 56 B: f32 c[4][3], f32 half, s8 side */
    const uint8_t* cells;   /* 4 B */
    const uint8_t* lists;   /* u16 */
    const uint8_t* pool;    /* u16 source placement fields; occluder i: r[53] of them from rd16(r + 54) */
} o;
static unsigned c_tests, c_hidden, c_noeye, c_notintact, c_visible, c_logged;
static unsigned intact_frame = ~0u;
static int intact;

static inline uint16_t rd16(const uint8_t* p) { return (uint16_t) (p[0] | (p[1] << 8)); }

void re4dc_room_vis_enter(unsigned room)
{
    room &= 0xFFF;
    memset(&o, 0, sizeof(o));
    intact_frame = ~0u;
    unsigned len = 0, ver = 0, flags = 0;
    const re4dc_room_header* h = 0;
    const uint8_t* s = (const uint8_t*) re4dc_room_section("OCCL", &len, &ver, &flags, &h);
    const char* why = 0;
    if (!s) why = "no OCCL";
    else if (ver != 2 || len < 32) why = "OCCL version";
    else {
        const unsigned vw = rd16(s), vh = rd16(s + 2), div = rd16(s + 4), nocc = rd16(s + 6), nlist = rd16(s + 8),
                       range_cm = rd16(s + 10), npool = rd16(s + 22);
        const unsigned lb = (2 * nlist + 3) & ~3u, pb = (2 * npool + 3) & ~3u;
        if (!div || vw != (h->w + div - 1) / div || vh != (h->h + div - 1) / div ||
            len != 32 + OCC_STRIDE * nocc + 4 * vw * vh + lb + pb)
            why = "OCCL size";
        const uint8_t* cells = s + 32 + OCC_STRIDE * nocc;
        const uint8_t* lists = cells + 4 * vw * vh;
        for (unsigned c = 0; !why && c < vw * vh; c++)
            if (rd16(cells + 4 * c) + cells[4 * c + 2] > nlist) why = "OCCL cell";
        for (unsigned i = 0; !why && i < nlist; i++)
            if (rd16(lists + 2 * i) >= nocc) why = "OCCL list";
        for (unsigned i = 0; !why && i < nocc; i++) {
            const uint8_t* r = s + 32 + OCC_STRIDE * i;
            const int8_t side = (int8_t) r[52];
            if (side != 1 && side != -1) why = "OCCL side";
            else if (!r[53] || rd16(r + 54) + r[53] > npool) why = "OCCL sources";
        }
        o.pool = lists + lb;
        if (!why) {
            o.vw = (uint16_t) vw; o.vh = (uint16_t) vh; o.nocc = (uint16_t) nocc; o.nlist = (uint16_t) nlist;
            o.x0 = h->x0; o.z0 = h->z0; o.inv_cs = 1.0f / (float) (h->cell_mm * div);
            o.range2 = (range_cm * 10.0f) * (range_cm * 10.0f);
            o.crc = (uint32_t) rd16(s + 12) | ((uint32_t) rd16(s + 14) << 16);
            o.occ = s + 32; o.cells = cells; o.lists = lists;
            o.ok = 1; o.room = room;
        }
    }
    re4dc_log("ENEMYVIS r%03x %s occluders=%u crc=%08x\n", room, why ? why : "ok", (unsigned) o.nocc, (unsigned) o.crc);
}

void re4dc_room_vis_leave(void) { memset(&o, 0, sizeof(o)); }
int re4dc_room_vis_active(void) { return o.ok; }

static inline float dot3(const float* a, const float* b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
static inline void cross3(const float* a, const float* b, float* r)
{
    r[0] = a[1] * b[2] - a[2] * b[1]; r[1] = a[2] * b[0] - a[0] * b[2]; r[2] = a[0] * b[1] - a[1] * b[0];
}

/* every box corner inside the shadow wedge of quad q (4 corners) from eye e */
static int wedge_holds(const float q[4][3], const float* e, const float bx[8][3])
{
    float ctr[3] = {0, 0, 0};
    for (int i = 0; i < 4; i++) for (int k = 0; k < 3; k++) ctr[k] += 0.25f * q[i][k];
    float ce[3] = {ctr[0] - e[0], ctr[1] - e[1], ctr[2] - e[2]};
    for (int i = 0; i < 4; i++) {
        const float* p = q[i];
        const float* r = q[(i + 1) & 3];
        float a[3] = {p[0] - e[0], p[1] - e[1], p[2] - e[2]}, b[3] = {r[0] - e[0], r[1] - e[1], r[2] - e[2]}, m[3];
        cross3(a, b, m);
        if (dot3(m, ce) < 0.0f) { m[0] = -m[0]; m[1] = -m[1]; m[2] = -m[2]; }
        for (int j = 0; j < 8; j++) {
            float v[3] = {bx[j][0] - e[0], bx[j][1] - e[1], bx[j][2] - e[2]};
            if (!(dot3(m, v) >= 0.0f)) return 0;   /* NaN fails too */
        }
    }
    return 1;
}

static int occluder_hides(const uint8_t* rec, const float* view, const float* e, float near, float far,
                          const float bx[8][3])
{
    float c[4][3], half;
    memcpy(c, rec, sizeof(c));
    memcpy(&half, rec + 48, 4);
    const float side = (float) (int8_t) rec[52];
    float u[3] = {c[1][0] - c[0][0], c[1][1] - c[0][1], c[1][2] - c[0][2]};
    float w[3] = {c[3][0] - c[0][0], c[3][1] - c[0][1], c[3][2] - c[0][2]};
    float n[3];
    cross3(u, w, n);
    const float l2 = dot3(n, n);
    if (!(l2 > 0.0f)) return 0;
    const float inv = side / __builtin_sqrtf(l2);
    n[0] *= inv; n[1] *= inv; n[2] *= inv;   /* the front normal: toward the side the eye must be on */
    const float d = dot3(n, c[0]);
    if (!(dot3(n, e) - d >= half + 50.0f)) return 0;
    for (int j = 0; j < 8; j++)            /* box wholly behind the back face (cheap first reject) */
        if (!(dot3(n, bx[j]) - d <= -half - 1.0f)) return 0;
    float fq[4][3], bq[4][3];
    for (int i = 0; i < 4; i++)
        for (int k = 0; k < 3; k++) { fq[i][k] = c[i][k] + n[k] * half; bq[i][k] = c[i][k] - n[k] * half; }
    for (int i = 0; i < 8; i++) {          /* both faces wholly between the near plane and the world's far, in range */
        const float* p = i < 4 ? fq[i] : bq[i - 4];
        const float depth = -(view[8] * p[0] + view[9] * p[1] + view[10] * p[2] + view[11]);
        if (!(depth >= near + 10.0f && depth <= far - 100.0f)) return 0;
        const float dx = p[0] - e[0], dy = p[1] - e[1], dz = p[2] - e[2];
        if (!(dx * dx + dy * dy + dz * dz <= o.range2)) return 0;
    }
    return wedge_holds((const float (*)[3]) fq, e, bx) && wedge_holds((const float (*)[3]) bq, e, bx);
}

int re4dc_room_vis_hidden(const float* view, float near, float far, const float lo_in[3], const float hi_in[3])
{
    if (!o.ok) return 0;
    ++c_tests;
    if (!(c_tests & 255) && c_logged < 400) {
        ++c_logged;
        re4dc_log("ENEMYVIS r%03x tests=%u hidden=%u noeye=%u notintact=%u visible=%u\n", o.room, c_tests, c_hidden,
                  c_noeye, c_notintact, c_visible);
    }
    /* the eye of the world-to-view affine (rows): v = R w + t, w = -R^T t (R orthonormal: the game's camera) */
    const float e[3] = {-(view[0] * view[3] + view[4] * view[7] + view[8] * view[11]),
                        -(view[1] * view[3] + view[5] * view[7] + view[9] * view[11]),
                        -(view[2] * view[3] + view[6] * view[7] + view[10] * view[11])};
    const float fx = (e[0] - o.x0) * o.inv_cs, fz = (e[2] - o.z0) * o.inv_cs;
    if (!(fx >= 0.0f && fz >= 0.0f)) { ++c_noeye; return 0; }
    const unsigned cx = (unsigned) fx, cz = (unsigned) fz;
    if (cx >= o.vw || cz >= o.vh) { ++c_noeye; return 0; }
    const uint8_t* cell = o.cells + 4 * (cx + cz * o.vw);
    const unsigned first = rd16(cell), count = cell[2];
    if (!count) { ++c_noeye; return 0; }
    /* the box with a 50 mm margin (held weapons and effects are drawn by their own owners) */
    float lo[3], hi[3], bx[8][3];
    for (int k = 0; k < 3; k++) { lo[k] = lo_in[k] - 50.0f; hi[k] = hi_in[k] + 50.0f; }
    for (int j = 0; j < 8; j++) { bx[j][0] = (j & 1) ? hi[0] : lo[0]; bx[j][1] = (j & 2) ? hi[1] : lo[1]; bx[j][2] = (j & 4) ? hi[2] : lo[2]; }
    const unsigned f = re4dc_ui_frame();
    if (f != intact_frame) { intact_frame = f; intact = re4dc_ps2_world_intact(o.room, o.crc); }
    if (!intact) { ++c_notintact; return 0; }
    int hit = 0, moved = 0;
    unsigned which = 0;
    for (unsigned i = 0; i < count && !hit; i++) {
        which = rd16(o.lists + 2 * (first + i));
        const uint8_t* r = o.occ + OCC_STRIDE * which;
        if (!occluder_hides(r, view, e, near, far, (const float (*)[3]) bx)) continue;
        /* its source placements drawn at rest now */
        if (re4dc_ps2_placements_intact(o.room, o.pool + 2 * rd16(r + 54), r[53])) hit = 1;
        else moved = 1;
    }
    if (!hit) { if (moved) ++c_notintact; else ++c_visible; return 0; }
    ++c_hidden;
#if defined(RE4DC_ENEMY_VIS_DEBUG) && RE4DC_ENEMY_VIS_DEBUG
    /* every cull, for the offline oracle (occ_eval-style check of the runtime decisions) */
    re4dc_log("ENEMYVIS hide f=%u occ=%u eye=%d,%d,%d lo=%d,%d,%d hi=%d,%d,%d\n", f, which, (int) e[0], (int) e[1],
              (int) e[2], (int) lo_in[0], (int) lo_in[1], (int) lo_in[2], (int) hi_in[0], (int) hi_in[1], (int) hi_in[2]);
#endif
    return 1;
}
