/* edemo_main.c: standalone KOS stress demo for the Dreamcast-native enemy runtime (lane edemo18, phase 0).
 *
 * Loads /cd/EDEMO.PAK (pack_demo.py) and /cd/ARMS.TXT (one arm per line: n skin2 lod logic_hz zam frames), then
 * runs each arm as a segment: N Ganados chase and attack a scripted dummy Leon on the r101 grid, drawn with the
 * real PS2 Ganado mesh and its VQ atlas. Per segment it prints (serial) the per-frame CPU split. Frame numbers are
 * deterministic (no input, no timing in the logic), so the hw model can trace any segment's frames by number:
 * edemo_frame_word is stored once per frame (hwproject --frameaddr).
 */
#include <kos.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <dc/pvr.h>
#include <sh4zam/shz_xmtrx.h>
#include "../edemo_engine.h"

KOS_INIT_FLAGS(INIT_DEFAULT);

volatile uint32_t edemo_frame_word __attribute__((aligned(32)));
/* RAM log ring read from the host by the harness's read_log.py (<buf> <head> <stage> offsets from sh-elf-nm) */
char edemo_logbuf[0x10000] __attribute__((aligned(32)));
volatile uint32_t edemo_loghead;
volatile uint32_t edemo_stage;

#include <stdarg.h>
static void elog(const char* fmt, ...)
{
    char tmp[512];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(tmp, sizeof tmp, fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n > (int) sizeof tmp - 1) n = sizeof tmp - 1;
    uint32_t h = edemo_loghead;
    for (int i = 0; i < n; i++) edemo_logbuf[(h + i) & 0xFFFF] = tmp[i];
    edemo_loghead = h + n;
    fputs(tmp, stdout);
}

static ed_data D;
static ed_ganado G[ED_MAXG];
static ed_pose P;
static ed_proj PROJ[1024] __attribute__((aligned(32)));
static pvr_poly_hdr_t hdr_tex, hdr_col;
static pvr_ptr_t tex;

#define MAXF 4096
static uint32_t fr_cpu[MAXF], fr_logic[MAXF], fr_anim[MAXF], fr_draw[MAXF], fr_scene[MAXF], fr_int[MAXF];

static uint8_t* load_file(const char* path, uint32_t* size)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) return 0;
    *size = fs_total(f);
    uint8_t* b = memalign(32, *size + 32);
    fs_read(f, b, *size);
    fs_close(f);
    return b;
}

static void mat_view_proj(ed_mat4* vp, const float eye[3], const float at[3])
{
    float f[3] = { at[0] - eye[0], at[1] - eye[1], at[2] - eye[2] };
    float r = 1.0f / sqrtf(f[0] * f[0] + f[1] * f[1] + f[2] * f[2]);
    f[0] *= r; f[1] *= r; f[2] *= r;
    float s[3] = { f[2], 0, -f[0] };          /* cross(up, f) */
    r = 1.0f / sqrtf(s[0] * s[0] + s[2] * s[2]);
    s[0] *= r; s[2] *= r;
    float u[3] = { f[1] * s[2] - f[2] * s[1], f[2] * s[0] - f[0] * s[2], f[0] * s[1] - f[1] * s[0] };
    ed_mat4 v = { { s[0], u[0], f[0], 0, s[1], u[1], f[1], 0, s[2], u[2], f[2], 0,
                    -(s[0] * eye[0] + s[1] * eye[1] + s[2] * eye[2]), -(u[0] * eye[0] + u[1] * eye[1] + u[2] * eye[2]),
                    -(f[0] * eye[0] + f[1] * eye[1] + f[2] * eye[2]), 1 } };
    const float fx = 1.0f / tanf(0.5f * 1.2217f) * 0.75f, fy = 1.0f / tanf(0.5f * 1.2217f); /* 70 deg vertical */
    /* X = 320 zv + 320 fx xv, Y = 240 zv - 240 fy yv, Z = 1, W = zv */
    ed_mat4 pm = { { 320 * fx, 0, 0, 0, 0, -240 * fy, 0, 0, 320, 240, 0, 1, 0, 0, 1, 0 } };
    ed_mat_mul(vp, &pm, &v, 0);
}

static void world_of(ed_mat4* w, float x, float y, float z, float fx, float fz)
{
    ed_mat4 m = { { fz, 0, -fx, 0, 0, 1, 0, 0, fx, 0, fz, 0, x, y, z, 1 } };
    *w = m;
}

static void quad(float x0, float y0, float z0, float x1, float y1, float z1, float x2, float y2, float z2, float x3, float y3, float z3,
                 const ed_mat4* vp, uint32_t argb)
{
    float in[4][3] = { { x0, y0, z0 }, { x1, y1, z1 }, { x3, y3, z3 }, { x2, y2, z2 } };
    float o[4][3];
    for (int k = 0; k < 4; k++) {
        const float* m = vp->m;
        float X = m[0] * in[k][0] + m[4] * in[k][1] + m[8] * in[k][2] + m[12];
        float Y = m[1] * in[k][0] + m[5] * in[k][1] + m[9] * in[k][2] + m[13];
        float W = m[3] * in[k][0] + m[7] * in[k][1] + m[11] * in[k][2] + m[15];
        if (W < 200.0f) return;
        o[k][0] = X / W; o[k][1] = Y / W; o[k][2] = 1.0f / W;
    }
    for (int k = 0; k < 4; k++) {
        pvr_vertex_t* v = pvr_dr_target();
        v->flags = k == 3 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
        v->x = o[k][0]; v->y = o[k][1]; v->z = o[k][2];
        v->u = v->v = 0;
        v->argb = argb; v->oargb = 0;
        pvr_dr_commit(v);
    }
}

/* scenery + Leon: ground cells and wall segments within 12 m of Leon (not part of the enemy cost) */
static int scene_no_leon;
static __attribute__((noinline)) void edemo_scene_draw(const ed_mat4* vp, float lx, float ly, float lz)
{
    const ed_grid* g = &D.grid;
    pvr_prim(&hdr_col, sizeof hdr_col);
    int cx0 = (int) ((lx - g->x0) * g->inv_cell), cz0 = (int) ((lz - g->z0) * g->inv_cell);
    for (int cz = cz0 - 12; cz <= cz0 + 12; cz++) {
        for (int cx = cx0 - 12; cx <= cx0 + 12; cx++) {
            if (cx < 0 || cz < 0 || cx >= g->w || cz >= g->h) continue;
            const uint8_t* c = g->cells + 6 * (cx + cz * g->w);
            if (c[0] == 0xFF) continue;
            const float* pl = g->planes + 3 * c[0];
            float x0 = g->x0 + cx * g->cell, z0 = g->z0 + cz * g->cell, x1 = x0 + g->cell, z1 = z0 + g->cell;
            uint32_t col = ((cx + cz) & 1) ? 0xff4a4636 : 0xff55503e;
            quad(x0, pl[0] * x0 + pl[1] * z0 + pl[2], z0, x1, pl[0] * x1 + pl[1] * z0 + pl[2], z0,
                 x1, pl[0] * x1 + pl[1] * z1 + pl[2], z1, x0, pl[0] * x0 + pl[1] * z1 + pl[2], z1, vp, col);
        }
    }
    /* wall segments touching the window */
    for (int i = 0; i < g->nseg; i++) {
        const int16_t* s = g->segs + 6 * i;
        float ax = s[0] * 10.0f, az = s[1] * 10.0f, bx = s[2] * 10.0f, bz = s[3] * 10.0f;
        float mx = 0.5f * (ax + bx) - lx, mz = 0.5f * (az + bz) - lz;
        if (mx * mx + mz * mz > 12000.0f * 12000.0f) continue;
        quad(ax, s[4] * 10.0f, az, bx, s[4] * 10.0f, bz, bx, s[5] * 10.0f, bz, ax, s[5] * 10.0f, az, vp, 0xff6e7480);
    }
    /* Leon: a 0.6 x 1.8 m post */
    if (scene_no_leon) return;
    quad(lx - 300, ly, lz, lx + 300, ly, lz, lx + 300, ly + 1800, lz, lx - 300, ly + 1800, lz, vp, 0xff2050c0);
    quad(lx, ly, lz - 300, lx, ly, lz + 300, lx, ly + 1800, lz + 300, lx, ly + 1800, lz - 300, vp, 0xff2050c0);
}

static void spawn(int n, int scen)
{
    const ed_grid* g = &D.grid;
    for (int i = 0; i < n; i++) {
        float a = 6.2831853f * i / n + 0.3f;
        float rad = scen ? 10000.0f + 15000.0f * ((i * 7) % 11) / 10.0f : 4000.0f + 4000.0f * ((i * 7) % 5) / 4.0f;
        float x = D.arena[0] + rad * cosf(a), z = D.arena[1] + rad * sinf(a);
        int ok = 0;
        float y = 0;
        for (int k = 0; k < 40 && !ok; k++) {
            y = ed_floor_y(g, x, z, &ok);
            if (!ok) { x += (D.arena[0] - x) * 0.1f; z += (D.arena[1] - z) * 0.1f; }
        }
        ed_ganado* e = &G[i];
        memset(e, 0, sizeof *e);
        e->x = e->px = x; e->y = e->py = y; e->z = e->pz = z;
        float dx = D.arena[0] - x, dz = D.arena[1] - z, r = 1.0f / sqrtf(dx * dx + dz * dz);
        e->fx = e->pfx = dx * r; e->fz = e->pfz = dz * r;
        e->frame = (float) ((i * 13) % 40);
        e->argb = 0xff000000 | (0xb0 + 8 * (i & 3)) << 16 | (0xa8 + 6 * (i & 1)) << 8 | 0x98;
    }
}

/* console results screen: one line per segment, drawn with the BIOS font into a 512x512 RGB565 texture */
static char res_lines[40][64];
static int res_n;

static void results_screen(void)
{
    uint16_t* buf = memalign(32, 512 * 512 * 2);
    memset(buf, 0, 512 * 512 * 2);
    bfont_draw_str(buf + 2 * 512 + 4, 512, 1, "N sk lod 15Hz zam scen  ms/frame");
    for (int i = 0; i < res_n && i < 20; i++) bfont_draw_str(buf + (26 + 24 * i) * 512 + 4, 512, 1, res_lines[i]);
    pvr_ptr_t t = pvr_mem_malloc(512 * 512 * 2);
    pvr_txr_load(buf, t, 512 * 512 * 2);
    pvr_poly_cxt_t cxt;
    pvr_poly_hdr_t h;
    pvr_poly_cxt_txr(&cxt, PVR_LIST_OP_POLY, PVR_TXRFMT_RGB565 | PVR_TXRFMT_NONTWIDDLED, 512, 512, t, PVR_FILTER_NONE);
    pvr_poly_compile(&h, &cxt);
    for (int fr = 0;; fr++) {
        edemo_frame_word++;
        if (fr == 10) {
            uint32_t sof = *(volatile uint32_t*) 0xA05F8050 & 0xFFFFFC;
            elog("EDEMO STILL seg 99 skin2 0 lod 0 clip 0 fb=%08lx,%08lx\n", (unsigned long) (0xa5000000 + 2 * sof),
                 (unsigned long) (0xa5000000 + 2 * sof));
        }
        pvr_wait_ready();
        pvr_scene_begin();
        pvr_list_begin(PVR_LIST_OP_POLY);
        pvr_prim(&h, sizeof h);
        const float xs[4] = { 0, 640, 0, 640 }, ys[4] = { 0, 0, 512, 512 }, us[4] = { 0, 1, 0, 1 }, vs[4] = { 0, 0, 1, 1 };
        for (int k = 0; k < 4; k++) {
            pvr_vertex_t* v = pvr_dr_target();
            v->flags = k == 3 ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
            v->x = xs[k]; v->y = ys[k]; v->z = 1; v->u = us[k]; v->v = vs[k]; v->argb = 0xffffffff; v->oargb = 0;
            pvr_dr_commit(v);
        }
        pvr_list_finish();
        pvr_scene_finish();
    }
}

static int cmp_u32(const void* a, const void* b)
{
    uint32_t x = *(const uint32_t*) a, y = *(const uint32_t*) b;
    return x < y ? -1 : x > y;
}

static void pct(uint32_t* v, int n, uint32_t out[3])
{
    static uint32_t tmp[MAXF];
    memcpy(tmp, v, n * 4);
    qsort(tmp, n, 4, cmp_u32);
    out[0] = tmp[n / 2]; out[1] = tmp[(n * 99) / 100]; out[2] = tmp[n - 1];
}

static void selftest(void)
{
    ed_mat4 a, b, c0, c1;
    for (int i = 0; i < 16; i++) { a.m[i] = (float) ((i * 7) % 5) - 1.5f; b.m[i] = (float) ((i * 3) % 7) * 0.5f - 1; }
    ed_mat_mul(&c0, &a, &b, 0);
    ed_mat_mul(&c1, &a, &b, 1);
    float e = 0;
    for (int i = 0; i < 16; i++) e = fmaxf(e, fabsf(c0.m[i] - c1.m[i]));
    elog("EDEMO selftest zam_vs_plain_matmul maxdiff %g\n", (double) e);
}

int main(int argc, char** argv)
{
    (void) argc; (void) argv;
    pvr_init_params_t pp = { { PVR_BINSIZE_32, PVR_BINSIZE_0, PVR_BINSIZE_0, PVR_BINSIZE_0, PVR_BINSIZE_0 }, 1536 * 1024, 0, 0, 0, 3, 0 };
    pvr_init(&pp);
    pvr_set_bg_color(0.35f, 0.42f, 0.5f);
    uint32_t sz;
    uint8_t* pak = load_file("/cd/EDEMO.PAK", &sz);
#if defined(EDEMO_EMBED)
    extern const uint8_t edemo_pak_start[], edemo_pak_end[];
    if (!pak) { pak = (uint8_t*) edemo_pak_start; sz = edemo_pak_end - edemo_pak_start; }
#endif
    if (!pak) { elog("EDEMO no pak\n"); return 1; }
    int r = edemo_load(&D, pak, sz);
    elog("EDEMO load %d pak %lu bytes clips nf %d/%d/%d/%d speed walk %.1f mesh nv %lu/%lu/%lu strip verts %lu/%lu/%lu\n", r,
           (unsigned long) sz, D.clips[0].nf, D.clips[1].nf, D.clips[2].nf, D.clips[3].nf, (double) D.clips[0].speed,
           (unsigned long) D.mesh[0].nv, (unsigned long) D.mesh[1].nv, (unsigned long) D.mesh[2].nv,
           (unsigned long) D.mesh[0].nidx, (unsigned long) D.mesh[1].nidx, (unsigned long) D.mesh[2].nidx);
    if (r) return 1;
    selftest();
    tex = pvr_mem_malloc(D.tex_bytes);
    pvr_txr_load(D.tex, tex, D.tex_bytes);
    pvr_poly_cxt_t cxt;
    pvr_poly_cxt_txr(&cxt, PVR_LIST_OP_POLY, PVR_TXRFMT_RGB565 | PVR_TXRFMT_VQ_ENABLE | PVR_TXRFMT_TWIDDLED, 512, 512, tex,
                     PVR_FILTER_BILINEAR);
    cxt.gen.culling = PVR_CULLING_NONE;
    cxt.gen.shading = PVR_SHADE_FLAT;
    pvr_poly_compile(&hdr_tex, &cxt);
    pvr_poly_cxt_col(&cxt, PVR_LIST_OP_POLY);
    cxt.gen.culling = PVR_CULLING_NONE;
    pvr_poly_compile(&hdr_col, &cxt);

    ed_arm arms[64];
    int na = 0;
    uint32_t asz;
    char* at = (char*) load_file("/cd/ARMS.TXT", &asz);
#if defined(EDEMO_EMBED)
    extern const char edemo_arms_start[], edemo_arms_end[];
    if (!at) { asz = edemo_arms_end - edemo_arms_start; at = malloc(asz + 1); memcpy(at, edemo_arms_start, asz); }
#endif
    if (at) {
        at[asz] = 0;
        char* line = strtok(at, "\n");
        while (line && na < 64) {
            ed_arm a;
            a.still = 0; a.scen = 0;
            if (sscanf(line, "%d %d %d %d %d %d %d %d", &a.n, &a.skin2, &a.lod, &a.logic_hz, &a.zam, &a.frames, &a.still, &a.scen) >= 6) arms[na++] = a;
            line = strtok(0, "\n");
        }
    }
    if (!na) { arms[0] = (ed_arm) { 4, 1, 0, 30, 1, 300, 0, 0 }; na = 1; }
    uint32_t frame = 0;
    for (int ai = 0; ai < na; ai++) {
        ed_arm* A = &arms[ai];
        if (A->frames > MAXF) A->frames = MAXF;
        spawn(A->n, A->scen);
        uint64_t seg_t0 = timer_ns_gettime64(), prev = seg_t0;
        uint32_t flow_runs0 = 0, verts_sum = 0, drawn_sum = 0, lod_hist[3] = { 0, 0, 0 };
        uint64_t sum_logic = 0, sum_anim = 0, sum_draw = 0, sum_scene = 0;
        int meas0 = (A->frames * 2) / 3;   /* = the hw-model window 160..239 of a 240-frame segment */
        elog("EDEMO seg %d start_frame %lu n %d skin2 %d lod %d logic_hz %d zam %d frames %d scen %d\n", ai, (unsigned long) frame, A->n,
               A->skin2, A->lod, A->logic_hz, A->zam, A->frames, A->scen);
        for (int f = 0; f < A->frames; f++, frame++) {
            edemo_frame_word = frame;
            float ang = f * (6.2831853f / 1800.0f);   /* segment-local: every arm replays the same scene */
            float lx = D.arena[0] + 3000.0f * cosf(ang), lz = D.arena[1] + 3000.0f * sinf(ang);
            int ok;
            float ly = ed_floor_y(&D.grid, lx, lz, &ok);
            uint64_t t0 = timer_ns_gettime64();
            if (A->still) {
                /* still pair mode: one Ganado in front of a fixed camera, frozen pose */
                ang = 0; lx = D.arena[0]; lz = D.arena[1]; ly = ed_floor_y(&D.grid, lx, lz, &ok);
                ed_ganado* e = &G[0];
                e->x = e->px = lx; e->z = e->pz = lz; e->y = e->py = ly; e->fx = e->pfx = -0.5f; e->fz = e->pfz = -0.866f;
                e->clip = A->still == 2 ? 1 : 0; e->frame = A->still == 2 ? 30.0f : 20.0f; e->since_logic = 1;
            } else {
                edemo_logic_flow(&D, lx, lz);
                edemo_logic_tick(&D, G, A->n, f, A->logic_hz, lx, ly, lz);
            }
            uint64_t t1 = timer_ns_gettime64();
            float eye[3] = { lx - 5500.0f * cosf(ang + 0.6f), ly + 4500.0f, lz - 5500.0f * sinf(ang + 0.6f) };
            float tgt[3] = { lx, ly + 600.0f, lz };
            if (A->still) {
                eye[0] = lx - 1000.0f; eye[1] = ly + 1400.0f; eye[2] = lz - 1750.0f;
                tgt[0] = lx; tgt[1] = ly + 950.0f; tgt[2] = lz;
            }
            ed_mat4 vp;
            mat_view_proj(&vp, eye, tgt);
            pvr_wait_ready();
            pvr_scene_begin();
            pvr_list_begin(PVR_LIST_OP_POLY);
            uint64_t t2 = timer_ns_gettime64();
            scene_no_leon = A->still;
            edemo_scene_draw(&vp, lx, ly, lz);
            uint64_t t3 = timer_ns_gettime64();
            uint64_t anim = 0, draw = 0;
            uint32_t verts = 0, drawn = 0;
            int hdr_sent = 0;
            for (int i = 0; i < A->n; i++) {
                ed_ganado* e = &G[i];
                float x = e->x, y = e->y, z = e->z, fx = e->fx, fz = e->fz;
                if (A->logic_hz == 15) {
                    float u = e->since_logic == 0 ? 0.5f : 1.0f;
                    x = e->px + (e->x - e->px) * u; y = e->py + (e->y - e->py) * u; z = e->pz + (e->z - e->pz) * u;
                    fx = e->pfx + (e->fx - e->pfx) * u; fz = e->pfz + (e->fz - e->pfz) * u;
                    float r = 1.0f / sqrtf(fx * fx + fz * fz + 1e-6f);
                    fx *= r; fz *= r;
                }
                /* cull: bounding sphere (centre 0.9 m up, r 1.1 m) against near plane and screen */
                const float* m = vp.m;
                float cy = y + 900.0f;
                float X = m[0] * x + m[4] * cy + m[8] * z + m[12];
                float Y = m[1] * x + m[5] * cy + m[9] * z + m[13];
                float W = m[3] * x + m[7] * cy + m[11] * z + m[15];
                if (W < 1300.0f) continue;
                float sx = X / W, sy = Y / W, rr = 1100.0f * 320.0f * 1.3f / W;
                if (sx < -rr || sx > 640 + rr || sy < -rr || sy > 480 + rr) continue;
                int lod = A->lod;
                if (lod == 3) lod = W < 10000.0f ? 0 : (W < 20000.0f ? 1 : 2);
                lod_hist[lod]++;
                uint64_t a0 = timer_ns_gettime64();
                edemo_anim_pose(&D, &D.clips[e->clip], e->frame, &P, A->zam);
                uint64_t a1 = timer_ns_gettime64();
                ed_mat4 w, vpw;
                world_of(&w, x, y, z, fx, fz);
                ed_mat_mul(&vpw, &vp, &w, A->zam);
                edemo_draw_skinmats(&D, &vpw, &P, A->zam);
                if (!hdr_sent) { pvr_prim(&hdr_tex, sizeof hdr_tex); hdr_sent = 1; }
                verts += edemo_draw_mesh(&D.mesh[lod], &P, PROJ, A->skin2, A->zam, e->argb);
                uint64_t a2 = timer_ns_gettime64();
                anim += a1 - a0;
                draw += a2 - a1;
                drawn++;
            }
            pvr_list_finish();
            pvr_scene_finish();
            uint64_t now = timer_ns_gettime64();
            fr_logic[f] = (uint32_t) (t1 - t0);
            fr_scene[f] = (uint32_t) (t3 - t2);
            fr_anim[f] = (uint32_t) anim;
            fr_draw[f] = (uint32_t) draw;
            fr_cpu[f] = fr_logic[f] + fr_anim[f] + fr_draw[f];
            fr_int[f] = (uint32_t) (now - prev);
            prev = now;
            if (A->still && f == 20) {
                uint32_t sof = *(volatile uint32_t*) 0xA05F8050 & 0xFFFFFC;
                elog("EDEMO STILL seg %d skin2 %d lod %d clip %d fb=%08lx,%08lx\n", ai, A->skin2, A->lod, G[0].clip,
                     (unsigned long) (0xa5000000 + 2 * sof), (unsigned long) (0xa5000000 + 2 * sof));
            }
            if (f >= meas0) {
                sum_logic += fr_logic[f]; sum_anim += fr_anim[f]; sum_draw += fr_draw[f]; sum_scene += fr_scene[f];
                verts_sum += verts; drawn_sum += drawn;
            }
            (void) flow_runs0;
        }
        int nm = A->frames - meas0;
        uint32_t pc[3], pi[3];
        pct(fr_cpu + meas0, nm, pc);
        pct(fr_int + meas0, nm, pi);
        int hits = 0;
        int attacks = 0;
        for (int i = 0; i < A->n; i++) { hits += G[i].hits; attacks += G[i].attacks; }
        elog("EDEMO res seg %d scen %d n %d skin2 %d lod %d logic_hz %d zam %d frames %d..%lu enemy_ms mean %.3f p50 %.3f p99 %.3f max %.3f "
               "logic %.3f anim %.3f draw %.3f scene %.3f interval_ms p50 %.2f p99 %.2f max %.2f drawn_per_frame %.2f verts_per_frame %.1f "
               "lod %lu/%lu/%lu attacks %d hits %d\n",
               ai, A->scen, A->n, A->skin2, A->lod, A->logic_hz, A->zam, (int) (frame - A->frames + meas0), (unsigned long) (frame - 1),
               (double) ((sum_logic + sum_anim + sum_draw) / 1e6 / nm), pc[0] / 1e6, pc[1] / 1e6, pc[2] / 1e6,
               (double) (sum_logic / 1e6 / nm), (double) (sum_anim / 1e6 / nm), (double) (sum_draw / 1e6 / nm),
               (double) (sum_scene / 1e6 / nm), pi[0] / 1e6, pi[1] / 1e6, pi[2] / 1e6, (double) drawn_sum / nm, (double) verts_sum / nm,
               (unsigned long) lod_hist[0], (unsigned long) lod_hist[1], (unsigned long) lod_hist[2], attacks, hits);
        (void) seg_t0;
        if (res_n < 40 && !A->still)
            snprintf(res_lines[res_n++], 64, "%d %d%d%d%d%d %5.2f L%.2f A%.2f D%.2f", A->n, A->skin2, A->lod,
                     A->logic_hz == 15, A->zam, A->scen, (double) ((sum_logic + sum_anim + sum_draw) / 1e6 / nm), (double) (sum_logic / 1e6 / nm),
                     (double) (sum_anim / 1e6 / nm), (double) (sum_draw / 1e6 / nm));
    }
    elog("EDEMO done frames %lu\n", (unsigned long) frame);
    edemo_frame_word = frame;
    results_screen();
    return 0;
}
