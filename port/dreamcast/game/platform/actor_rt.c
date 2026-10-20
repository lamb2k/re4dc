/* actor_rt.c: the native actor runtime's shared room services (ENGINE_PREVIEW=1; lanes behave18 -> engine19).
 *
 * The room grid comes from the room's data file (tools/enginebake/room_compile.py, R4RC v1, section GRID v1), read at
 * room entry into room memory by platform/room_file.c (heap 4, the native package reserve rules) and freed at room
 * leave. No file, a refused allocation, a bad file, or a room whose collision has object SAT members (GRID flag bit1
 * clear): the room runs the source path (SatMgr) exactly as without the switch. Nothing of the grid is in the program.
 * Grid semantics are the behave18 preview's (EDGR v1 cells, planes, walls; the flow field the preview never used is
 * gone). Queries do no allocation, no file access and no FPSCR changes. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <kos/fs.h>
#include "actor_rt.h"
#include "room_file.h"

extern void re4dc_log(const char* fmt, ...);

#define BODY_R 300.0f

typedef struct {
    int ok;
    unsigned room;
    uint16_t w, h, bw, bh;
    float x0, z0, cell, inv_cell;
    const uint16_t* btab;   /* [bw*bh] 0xFFFF = empty block */
    const uint16_t* bcell;  /* [nblock][64] */
    const uint8_t* combos;  /* 6 B: u16 plane, u16 wl first, u8 nwall, u8 pad */
    const float* planes;    /* y = a x + c z + d */
    const int16_t* segs;    /* x0 z0 x1 z1 ymin ymax, cm */
    const uint16_t* wl;
} rt_grid;

static rt_grid g_grid;
static unsigned g_bytes, c_loads, c_refused;
static unsigned c_owned, c_fallback, c_collide, c_nogrid;

static inline uint16_t rd16(const uint8_t* p) { return (uint16_t) (p[0] | (p[1] << 8)); }
static inline uint32_t rd32(const uint8_t* p) { return (uint32_t) (p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t) p[3] << 24)); }

/* Checks every table of a GRID v1 section against its length and every index against its table. */
static const char* adopt_grid(const uint8_t* s, uint32_t n, uint16_t w, uint16_t h, uint32_t cell_mm)
{
    rt_grid* g = &g_grid;
    if (n < 16 || ((uintptr_t) s & 3)) return "grid header";
    unsigned npl = rd16(s), nseg = rd16(s + 2), nco = rd16(s + 4), nwl = rd16(s + 6);
    unsigned bw = rd16(s + 8), bh = rd16(s + 10), nb = rd16(s + 12);
    if (!w || !h || bw != (w + 7u) / 8u || bh != (h + 7u) / 8u || cell_mm < 100) return "grid size";
    uint32_t p = 16 + 2u * bw * bh;
    p = (p + 3u) & ~3u;
    const uint32_t bd = p;
    p += 128u * nb;
    const uint32_t co = p;
    p += 6u * nco;
    p = (p + 3u) & ~3u;
    const uint32_t pl = p;
    p += 12u * npl;
    const uint32_t sg = p;
    p += 12u * nseg;
    const uint32_t wo = p;
    p += 2u * nwl;
    if (p != n) return "grid length";
    const uint16_t* btab = (const uint16_t*) (s + 16);
    for (unsigned i = 0; i < bw * bh; i++) if (btab[i] != 0xFFFF && btab[i] >= nb) return "grid block";
    const uint16_t* bc = (const uint16_t*) (s + bd);
    for (unsigned i = 0; i < 64u * nb; i++) if (bc[i] != 0xFFFF && bc[i] >= nco) return "grid cell";
    for (unsigned i = 0; i < nco; i++) {
        const uint8_t* c = s + co + 6u * i;
        if (rd16(c) >= npl || (unsigned) rd16(c + 2) + c[4] > nwl) return "grid combo";
    }
    const uint16_t* wl = (const uint16_t*) (s + wo);
    for (unsigned i = 0; i < nwl; i++) if (wl[i] >= nseg) return "grid wall list";
    g->w = w; g->h = h; g->bw = (uint16_t) bw; g->bh = (uint16_t) bh;
    g->cell = (float) cell_mm; g->inv_cell = 1.0f / g->cell;
    g->btab = btab; g->bcell = bc; g->combos = s + co;
    g->planes = (const float*) (s + pl); g->segs = (const int16_t*) (s + sg); g->wl = wl;
    return 0;
}

/* Room entry (ui_bridge.cpp re4dc_room_enter, after re4dc_room_file_enter read the room data file's GRID section). */
void re4dc_rt_room_enter(unsigned room)
{
    room &= 0xFFF;
    memset(&g_grid, 0, sizeof(g_grid));
    g_bytes = 0;
    unsigned len = 0, ver = 0, flags = 0;
    const re4dc_room_header* h = 0;
    const uint8_t* s = (const uint8_t*) re4dc_room_section("GRID", &len, &ver, &flags, &h);
    const char* why = !s ? "no GRID" : ver != 1 ? "GRID version" : !(flags & 2) ? "object collision (GRID not static)"
                    : adopt_grid(s, len, h->w, h->h, h->cell_mm);
    if (why) {
        memset(&g_grid, 0, sizeof(g_grid));
        c_refused++;
        re4dc_log("ENGINE r%03x %s: source path\n", room, why);
        return;
    }
    g_grid.x0 = h->x0; g_grid.z0 = h->z0;
    g_bytes = len; g_grid.ok = 1; g_grid.room = room;
    c_loads++;
    re4dc_log("ENGINE r%03x grid=%ux%u cell=%d bytes=%u loads=%u\n", room, g_grid.w, g_grid.h, (int) g_grid.cell, len, c_loads);
}

/* Room leave (ui_bridge.cpp re4dc_room_leave; the block is room_file.c's). */
void re4dc_rt_room_leave(void)
{
    g_bytes = 0;
    memset(&g_grid, 0, sizeof(g_grid));
}

int re4dc_rt_room(unsigned room)
{
    return g_grid.ok && g_grid.room == (room & 0xFFF);
}

/* combo of the cell under (x, z), or 0 when outside the grid or no floor */
static inline const uint8_t* combo_at(const rt_grid* g, float x, float z)
{
    float fx = (x - g->x0) * g->inv_cell, fz = (z - g->z0) * g->inv_cell;
    if (fx < 0 || fz < 0) return 0;
    int cx = (int) fx, cz = (int) fz;
    if (cx >= g->w || cz >= g->h) return 0;
    uint16_t b = g->btab[(cx >> 3) + (cz >> 3) * g->bw];
    if (b == 0xFFFF) return 0;
    uint16_t c = g->bcell[64u * b + (cx & 7) + 8 * (cz & 7)];
    return c == 0xFFFF ? 0 : g->combos + 6u * c;
}

int re4dc_rt_collide(float* x, float* y, float* z, float ox, float oz)
{
    const rt_grid* g = &g_grid;
    if (!g->ok) return 0;
    float nx = *x, nz = *z, ny = *y;
    const uint8_t* cb = combo_at(g, nx, nz);
    if (!cb) { c_nogrid++; return 0; }
    /* walls of this cell (the grid lists every wall within body radius of the cell) */
    int nw = cb[4];
    const uint16_t* wl = g->wl + rd16(cb + 2);
    for (int k = 0; k < nw; k++) {
        const int16_t* s = g->segs + 6 * wl[k];
        float ymin = s[4] * 10.0f, ymax = s[5] * 10.0f;
        if (ymax < ny + 300.0f || ymin > ny + 1600.0f) continue;
        float x0 = s[0] * 10.0f, z0 = s[1] * 10.0f, x1 = s[2] * 10.0f, z1 = s[3] * 10.0f;
        float dx = x1 - x0, dz = z1 - z0;
        float L = dx * dx + dz * dz;
        float t = L > 0 ? ((nx - x0) * dx + (nz - z0) * dz) / L : 0;
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        float px = nx - (x0 + t * dx), pz = nz - (z0 + t * dz);
        float d2 = px * px + pz * pz;
        if (d2 < BODY_R * BODY_R && d2 > 1e-6f) {
            float d = sqrtf(d2);
            float push = (BODY_R - d) / d;
            nx += px * push;
            nz += pz * push;
        }
    }
    cb = combo_at(g, nx, nz);
    if (!cb) { nx = ox; nz = oz; cb = combo_at(g, nx, nz); if (!cb) { c_nogrid++; return 0; } }
    const float* pl = g->planes + 3 * rd16(cb);
    float fy = pl[0] * nx + pl[1] * nz + pl[2];
    if (fabsf(fy - ny) > 400.0f) { c_nogrid++; return 0; }   /* another level (stairs, upper floors): the game decides */
    *x = nx; *z = nz; *y = fy;
    c_collide++;
    return 1;
}

void* re4dc_rt_ik_actor;
static unsigned c_ik, c_ikpass;

float re4dc_rt_floor(float x, float y, float z)
{
    const rt_grid* g = &g_grid;
    const uint8_t* cb = g->ok ? combo_at(g, x, z) : 0;
    if (!cb) { c_ikpass++; return -100000.0f; }
    const float* pl = g->planes + 3 * rd16(cb);
    float fy = pl[0] * x + pl[1] * z + pl[2];
    if (fy > y + 500.0f || fy < y - 1500.0f) { c_ikpass++; return -100000.0f; }  /* not this level: SatMgr decides */
    c_ik++;
    return fy;
}

void re4dc_rt_count(int owned, int fallback)
{
    c_owned += owned;
    c_fallback += fallback;
}

void re4dc_rt_log(unsigned frame, int leon_life)
{
    static unsigned last;
    if (frame - last < 60 && frame >= last) return;
    last = frame;
    re4dc_log("engine preview: f=%u life=%d owned=%u fallback=%u gridmove=%u gridpass=%u ik=%u ikpass=%u room=%03x bytes=%u\n",
              frame, leon_life, c_owned, c_fallback, c_collide, c_nogrid, c_ik, c_ikpass, g_grid.room, g_bytes);
}

/* routine transitions of the Ganados in a grid room (r_no_0 / r_no_1 from the cModel status word): one line per change */
void re4dc_rt_state(const void* em, unsigned stat, int hp, unsigned frame, float x, float z)
{
    static const void* who[16];
    static uint16_t was[16];
    int k, fr = -1;
    uint16_t now = (uint16_t) (stat & 0xFFFF);
    for (k = 0; k < 16; k++) {
        if (who[k] == em) break;
        if (fr < 0 && !who[k]) fr = k;
    }
    if (k == 16) {
        if (fr < 0) return;
        k = fr; who[k] = em; was[k] = 0xFFFF;
    }
    if (was[k] == now) return;
    was[k] = now;
    re4dc_log("engine preview: em%d f=%u r0=%u r1=%02x hp=%d at %d,%d\n", k, frame, now & 0xFF, now >> 8, hp, (int) x, (int) z);
}
