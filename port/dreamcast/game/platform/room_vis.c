/* room_vis.c: ENEMY_VIS_CULL (lane engine19; render only): enemies the camera cannot see behind the room's world.
 *
 * The room data file's VIS section (tools/enginebake/room_compile.py build_vis + vis_pvs.c) holds, per 4 m camera cell
 * (with the eye height range it was computed for), a bit per target volume (a 4 m cell's height band): clear = no
 * sampled sight line from anywhere in the camera cell to anywhere in the volume misses the room's opaque PS2 world
 * (every LOD level; two-sided parts, or back-culled crossings of both facings). re4dc_room_vis_hidden answers for a
 * world box: 1 only when the eye lies in a cell with a row and inside its eye range, the box fits one band of every
 * cell it overlaps, all those bits are clear, its farthest corner is within the section's range (r100 / r101: the
 * far shell's 18.75 m, beyond which the world is drawn coarser) and this frame's PS2 world is the one compiled from
 * (re4dc_ps2_world_intact: package open for the room, no dynamic / gated / area-hidden placement changed).
 * The callers are CROWD_INVIS_SKIP's interior tests (coarse_actor_owner_ganado.inc): a hidden Ganado then takes the
 * PS2_INTERIOR_ACTORS skip paths (exact by construction there). No file / no VIS: 0 always. */
#include <stdint.h>
#include <string.h>
#include "room_file.h"
#include "room_vis.h"

extern void re4dc_log(const char* fmt, ...);
extern unsigned re4dc_ui_frame(void);
extern int re4dc_ps2_world_intact(unsigned room, uint32_t crc);   /* native_static.cpp (ENEMY_VIS_CULL) */

static struct {
    int ok;
    unsigned room;
    uint16_t vw, vh, nrow, rowb, ntgt;
    float x0, z0, cs, inv_cs, range2, span;
    uint32_t crc;           /* R4PW sidecar crc the occluders came from */
    const uint8_t* cells;   /* 12 B */
    const uint8_t* camrow;  /* u16 per camera volume */
    const uint8_t* rows;
    float estep, espan;
} v;
static unsigned c_tests, c_hidden, c_noteye, c_notintact, c_box, c_vis, c_far, c_logged;
static unsigned intact_frame = ~0u;
static int intact;

static inline uint16_t rd16(const uint8_t* p) { return (uint16_t) (p[0] | (p[1] << 8)); }
static inline int16_t rs16(const uint8_t* p) { return (int16_t) rd16(p); }

void re4dc_room_vis_enter(unsigned room)
{
    room &= 0xFFF;
    memset(&v, 0, sizeof(v));
    intact_frame = ~0u;
    unsigned len = 0, ver = 0, flags = 0;
    const re4dc_room_header* h = 0;
    const uint8_t* s = (const uint8_t*) re4dc_room_section("VIS\0", &len, &ver, &flags, &h);
    const char* why = 0;
    if (!s) why = "no VIS";
    else if (ver != 2 || len < 32) why = "VIS version";
    else {
        const unsigned vw = rd16(s), vh = rd16(s + 2), div = rd16(s + 4), nrow = rd16(s + 6), rowb = rd16(s + 8),
                       ntgt = rd16(s + 10), range_cm = rd16(s + 12), span_cm = rd16(s + 14), ncam = rd16(s + 20),
                       estep = rd16(s + 22), espan = rd16(s + 24);
        const unsigned camb = (2 * ncam + 3) & ~3u;
        if (!div || !estep || espan < estep || vw != (h->w + div - 1) / div || vh != (h->h + div - 1) / div ||
            rowb != (ntgt + 7) / 8 || len != 32 + 12 * vw * vh + camb + nrow * rowb)
            why = "VIS size";
        const uint8_t* cr = s + 32 + 12 * vw * vh;
        for (unsigned c = 0; !why && c < vw * vh; c++) {
            const uint8_t* e = s + 32 + 12 * c;
            const unsigned fc = rd16(e + 6), ne = e[2], nb = e[3], ft = rd16(e + 8);
            if (fc != 0xFFFF && (!ne || fc + ne > ncam || ft + nb > ntgt)) why = "VIS cell";
        }
        for (unsigned a = 0; !why && a < ncam; a++)
            if (rd16(cr + 2 * a) >= nrow) why = "VIS camera row";
        if (!why) {
            v.camrow = cr; v.estep = estep * 10.0f; v.espan = espan * 10.0f;
            v.rows = cr + camb;
            v.vw = (uint16_t) vw; v.vh = (uint16_t) vh; v.nrow = (uint16_t) nrow; v.rowb = (uint16_t) rowb;
            v.ntgt = (uint16_t) ntgt;
            v.x0 = h->x0; v.z0 = h->z0; v.cs = (float) (h->cell_mm * div); v.inv_cs = 1.0f / v.cs;
            v.range2 = (range_cm * 10.0f) * (range_cm * 10.0f); v.span = span_cm * 10.0f;
            v.crc = (uint32_t) rd16(s + 16) | ((uint32_t) rd16(s + 18) << 16);
            v.cells = s + 32;
            v.ok = 1; v.room = room;
        }
    }
    re4dc_log("ENEMYVIS r%03x %s crc=%08x\n", room, why ? why : "ok", (unsigned) v.crc);
}

void re4dc_room_vis_leave(void) { memset(&v, 0, sizeof(v)); }
int re4dc_room_vis_active(void) { return v.ok; }

static inline int cell_of(float x, float z, int* cx, int* cz)
{
    const float fx = (x - v.x0) * v.inv_cs, fz = (z - v.z0) * v.inv_cs;
    if (!(fx >= 0.0f) || !(fz >= 0.0f)) return 0;
    *cx = (int) fx; *cz = (int) fz;
    return *cx < v.vw && *cz < v.vh;
}

int re4dc_room_vis_hidden(const float* view, float near, float far, const float lo[3], const float hi[3])
{
    (void) near; (void) far;
    if (!v.ok) return 0;
    ++c_tests;
    if (!(c_tests & 1023) && c_logged < 400) {
        ++c_logged;
        re4dc_log("ENEMYVIS r%03x tests=%u hidden=%u noteye=%u notintact=%u box=%u visible=%u far=%u\n", v.room, c_tests,
                  c_hidden, c_noteye, c_notintact, c_box, c_vis, c_far);
    }
    /* the eye of the world-to-view affine (rows): v = R w + t, w = -R^T t (R orthonormal: the game's camera) */
    const float e0 = -(view[0] * view[3] + view[4] * view[7] + view[8] * view[11]);
    const float e1 = -(view[1] * view[3] + view[5] * view[7] + view[9] * view[11]);
    const float e2 = -(view[2] * view[3] + view[6] * view[7] + view[10] * view[11]);
    int ex, ez;
    if (!cell_of(e0, e2, &ex, &ez)) { ++c_noteye; return 0; }
    const uint8_t* ec = v.cells + 12 * (ex + ez * v.vw);
    const unsigned fc = rd16(ec + 6), ne = ec[2];
    if (fc == 0xFFFF) { ++c_noteye; return 0; }
    const float ef = (e1 - rs16(ec) * 10.0f) / v.estep;
    if (!(ef >= 0.0f)) { ++c_noteye; return 0; }
    unsigned j = (unsigned) ef;
    if (j >= ne) j = ne - 1;
    if (!(e1 <= rs16(ec) * 10.0f + j * v.estep + v.espan)) { ++c_noteye; return 0; }
    const unsigned row = rd16(v.camrow + 2 * (fc + j));
    /* farthest box corner within range */
    float d2 = 0.0f;
    const float e[3] = {e0, e1, e2};
    for (int a = 0; a < 3; a++) {
        const float p = e[a] - lo[a], q = hi[a] - e[a];
        const float m = p > q ? p : q;
        d2 += m * m;
    }
    if (!(d2 <= v.range2)) { ++c_far; return 0; }
    int x0, z0, x1, z1;
    if (!cell_of(lo[0], lo[2], &x0, &z0) || !cell_of(hi[0], hi[2], &x1, &z1)) { ++c_box; return 0; }
    const uint8_t* bits = v.rows + (unsigned) row * v.rowb;
    for (int z = z0; z <= z1; z++)
        for (int x = x0; x <= x1; x++) {
            const uint8_t* tc = v.cells + 12 * (x + z * v.vw);
            const unsigned nb = tc[3];
            if (!nb || rd16(tc + 6) == 0xFFFF) { ++c_box; return 0; }
            const float b0 = rs16(tc + 4) * 10.0f;
            const float kf = (lo[1] - b0) * 0.001f;   /* band step 1 m */
            if (!(kf >= 0.0f)) { ++c_box; return 0; }
            const unsigned k = (unsigned) kf;
            if (k >= nb || !(hi[1] <= b0 + k * 1000.0f + v.span)) { ++c_box; return 0; }
            const unsigned t = rd16(tc + 8) + k;
            if ((bits[t >> 3] >> (t & 7)) & 1) {
#if defined(RE4DC_ENEMY_VIS_DEBUG) && RE4DC_ENEMY_VIS_DEBUG
                if (!(c_vis & 255))
                    re4dc_log("ENEMYVIS dbg eye=%d,%d,%d cell=%d,%d row=%u lo=%d,%d,%d hi=%d,%d,%d tcell=%d,%d k=%u t=%u\n",
                              (int) e0, (int) e1, (int) e2, ex, ez, row, (int) lo[0], (int) lo[1], (int) lo[2], (int) hi[0],
                              (int) hi[1], (int) hi[2], x, z, k, t);
#endif
                ++c_vis; return 0;
            }
        }
    const unsigned f = re4dc_ui_frame();
    if (f != intact_frame) { intact_frame = f; intact = re4dc_ps2_world_intact(v.room, v.crc); }
    if (!intact) { ++c_notintact; return 0; }
    ++c_hidden;
    return 1;
}
