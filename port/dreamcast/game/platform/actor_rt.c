/* actor_rt.c: the native actor runtime's shared room services, in-game preview (ENGINE_PREVIEW=1, lane behave18).
 * Grid layout and the flow / wall code follow port/dreamcast/engine/edemo_engine.c (edemo18, phase 0). */
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "actor_rt.h"

extern void re4dc_log(const char* fmt, ...);
extern const uint8_t re4dc_rt_grid101[];      /* actor_rt_grid.S: EDGR v1 r101 grid (private data, incbin) */
extern const uint32_t re4dc_rt_grid101_size;

#define GW_MAX 100
#define GH_MAX 88
#define FLOW_R 24
#define BODY_R 300.0f

typedef struct {
    int ok;
    uint16_t w, h;
    float x0, z0, cell, inv_cell;
    uint16_t nplane, nseg;
    const uint8_t* cells;   /* 6 B: floor plane (0xFF none), nwall, nbr bits, pad, u16 wall list offset */
    const float* planes;    /* y = a x + c z + d */
    const int16_t* segs;    /* x0 z0 x1 z1 ymin ymax, cm */
    const uint16_t* wl;
} rt_grid;

static rt_grid g_grid;
static int g_parsed;
static uint8_t flow_dir[GW_MAX * GH_MAX];
static uint8_t flow_stamp[GW_MAX * GH_MAX];
static uint8_t flow_gen;
static int flow_cell = -1;
static unsigned flow_frame = ~0u;
static uint16_t flow_q[(2 * FLOW_R + 1) * (2 * FLOW_R + 1)];
static unsigned c_owned, c_fallback, c_flows, c_steer, c_collide, c_nogrid;

static const int8_t DX[8] = { 1, 1, 0, -1, -1, -1, 0, 1 };
static const int8_t DZ[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };

static inline uint16_t rd16(const uint8_t* p) { return (uint16_t) (p[0] | (p[1] << 8)); }
static inline float rdf(const uint8_t* p) { float v; memcpy(&v, p, 4); return v; }

static void parse(void)
{
    const uint8_t* s = re4dc_rt_grid101;
    g_parsed = 1;
    if (re4dc_rt_grid101_size < 24 || memcmp(s, "EDGR", 4)) { re4dc_log("engine preview: no r101 grid\n"); return; }
    rt_grid* g = &g_grid;
    g->w = rd16(s + 4); g->h = rd16(s + 6);
    g->x0 = rdf(s + 8); g->z0 = rdf(s + 12);
    g->cell = rd16(s + 16); g->inv_cell = 1.0f / g->cell;
    g->nplane = rd16(s + 18); g->nseg = rd16(s + 20);
    if (g->w > GW_MAX || g->h > GH_MAX) { re4dc_log("engine preview: grid %ux%u too large\n", g->w, g->h); return; }
    g->cells = s + 24;
    g->planes = (const float*) (s + 24 + 6 * g->w * g->h);   /* 4-aligned: 6*w*h is even, w*h*6 % 4 checked below */
    g->segs = (const int16_t*) ((const uint8_t*) g->planes + 12 * g->nplane);
    g->wl = (const uint16_t*) ((const uint8_t*) g->segs + 12 * g->nseg);
    if (((uintptr_t) g->planes & 3) || ((uintptr_t) g->segs & 1)) { re4dc_log("engine preview: grid misaligned\n"); return; }
    g->ok = 1;
    re4dc_log("engine preview: r101 grid %ux%u cell %d mm, %u planes, %u walls, %u bytes\n", g->w, g->h, (int) g->cell,
              g->nplane, g->nseg, (unsigned) re4dc_rt_grid101_size);
}

int re4dc_rt_room(unsigned room)
{
    if (room != 0x101) return 0;
    if (!g_parsed) parse();
    return g_grid.ok;
}

static inline int cell_of(const rt_grid* g, float x, float z)
{
    float fx = (x - g->x0) * g->inv_cell, fz = (z - g->z0) * g->inv_cell;
    if (fx < 0 || fz < 0) return -1;
    int cx = (int) fx, cz = (int) fz;
    if (cx >= g->w || cz >= g->h) return -1;
    return cx + cz * g->w;
}

void re4dc_rt_tick(unsigned frame, float lx, float lz)
{
    const rt_grid* g = &g_grid;
    if (frame == flow_frame || !g->ok) return;
    flow_frame = frame;
    int c0 = cell_of(g, lx, lz);
    if (c0 < 0 || c0 == flow_cell) return;
    flow_cell = c0;
    c_flows++;
    if (++flow_gen == 0) { memset(flow_stamp, 0, sizeof(flow_stamp)); flow_gen = 1; }
    int cx0 = c0 % g->w, cz0 = c0 / g->w;
    int head = 0, tail = 0;
    flow_q[tail++] = (uint16_t) c0;
    flow_stamp[c0] = flow_gen;
    flow_dir[c0] = 0xFF;
    while (head < tail) {
        int c = flow_q[head++];
        int cx = c % g->w, cz = c / g->w;
        uint8_t nb = g->cells[6 * c + 2];
        for (int k = 0; k < 8; k++) {
            if (!(nb & (1 << k))) continue;
            int nx = cx + DX[k], nz = cz + DZ[k];
            if (nx < cx0 - FLOW_R || nx > cx0 + FLOW_R || nz < cz0 - FLOW_R || nz > cz0 + FLOW_R) continue;
            int n = nx + nz * g->w;
            if (flow_stamp[n] == flow_gen) continue;
            flow_stamp[n] = flow_gen;
            flow_dir[n] = (uint8_t) ((k + 4) & 7);   /* from n back toward c */
            flow_q[tail++] = (uint16_t) n;
        }
    }
}

int re4dc_rt_steer(float x, float z, float* gx, float* gz)
{
    const rt_grid* g = &g_grid;
    if (!g->ok || flow_cell < 0) return 0;
    int c = cell_of(g, x, z);
    if (c < 0 || flow_stamp[c] != flow_gen || flow_dir[c] == 0xFF) return 0;
    /* follow the field two cells: the goal is the centre of the second cell (smooths the 8-way steps) */
    int n = c;
    for (int s = 0; s < 2; s++) {
        if (flow_stamp[n] != flow_gen || flow_dir[n] == 0xFF) break;
        int k = flow_dir[n];
        int nx = n % g->w + DX[k], nz = n / g->w + DZ[k];
        if (nx < 0 || nz < 0 || nx >= g->w || nz >= g->h) break;
        n = nx + nz * g->w;
    }
    *gx = g->x0 + ((n % g->w) + 0.5f) * g->cell;
    *gz = g->z0 + ((n / g->w) + 0.5f) * g->cell;
    c_steer++;
    return 1;
}

int re4dc_rt_collide(float* x, float* y, float* z, float ox, float oz)
{
    const rt_grid* g = &g_grid;
    if (!g->ok) return 0;
    float nx = *x, nz = *z, ny = *y;
    int c = cell_of(g, nx, nz);
    if (c < 0 || g->cells[6 * c] == 0xFF) { c_nogrid++; return 0; }
    /* walls of this cell (the grid lists every wall within body radius of the cell) */
    const uint8_t* cl = g->cells + 6 * c;
    int nw = cl[1];
    const uint16_t* wl = g->wl + rd16(cl + 4);
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
    c = cell_of(g, nx, nz);
    if (c < 0 || g->cells[6 * c] == 0xFF) { nx = ox; nz = oz; c = cell_of(g, nx, nz); if (c < 0 || g->cells[6 * c] == 0xFF) { c_nogrid++; return 0; } }
    const float* pl = g->planes + 3 * g->cells[6 * c];
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
    int c = g->ok ? cell_of(g, x, z) : -1;
    if (c < 0 || g->cells[6 * c] == 0xFF) { c_ikpass++; return -100000.0f; }
    const float* pl = g->planes + 3 * g->cells[6 * c];
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
    re4dc_log("engine preview: f=%u life=%d owned=%u fallback=%u gridmove=%u gridpass=%u ik=%u ikpass=%u\n", frame,
              leon_life, c_owned, c_fallback, c_collide, c_nogrid, c_ik, c_ikpass);
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
