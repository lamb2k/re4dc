/* vis_pvs.c (lane engine19, offline, host only): the room compile's cell-to-cell visibility (VIS section).
 *
 * For every camera cell A and target cell B of a coarse x/z lattice, B is "possibly visible" from A unless EVERY
 * sampled segment from an eye sample in A (expanded by the margin, at EYE_N heights over A's eye y range) to a target
 * sample in B (expanded by the margin, at TGT_N heights over B's target y range) crosses an opaque world triangle.
 * Pairs closer than NEAR_CELLS (Chebyshev) or farther than the range are written visible (no culling there).
 * Cells with no y range (no floor) are visible from everywhere and see everything.
 *
 * input  (binary, little-endian): "PVSI", u32 ntri, u32 w, u32 h, f32 x0, f32 z0, f32 cell, f32 margin, f32 range,
 *        u32 samples (per axis), u32 eye_n, u32 tgt_n, u32 near_cells, u32 threads,
 *        f32 cellrange[w*h][4] (eye_lo, eye_hi, unused, unused; eye_lo > eye_hi = no range),
 *        u32 ntgt, then ntgt x {u32 cell, f32 ylo, f32 yhi} (target volumes: a cell's height band),
 *        f32 tri[ntri][10] (3 corners, then 1.0 for a back-culled part's triangle, 0.0 two-sided)
 * output: w*h rows of ceil(ntgt/8) bytes, bit (b & 7) of byte (b >> 3) set = target volume b possibly visible.
 * usage: vis_pvs <in> <out>     build: cc -O2 -pthread -o vis_pvs vis_pvs.c -lm
 */
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { float v0[3], e1[3], e2[3], ylo, yhi; int cull; } Tri;
#define MINDIST 200.0f   /* a hit nearer than this to the eye does not count (near plane, camera inside a surface) */
static Tri* T;
static uint32_t NT, W, H, SN, EN, TN, NEARC, NTH;
static float X0, Z0, CELL, MARGIN, RANGE;
static float (*CR)[4];
static uint8_t* OUT;
static uint32_t ROWB;
typedef struct { uint32_t cell; float ylo, yhi; } Tgt;
static Tgt* TG;
static uint32_t NTG;
/* triangle buckets */
#define BK 2000.0f
static uint32_t BW, BH;
static float BX0, BZ0;
static uint32_t* bstart;
static uint32_t* bidx;

static int seg_hits(const float* o, const float* p, uint32_t* mark, uint32_t stamp)
{
    float d[3] = {p[0] - o[0], p[1] - o[1], p[2] - o[2]};
    /* 2D DDA over buckets from o to p in x/z */
    float fx = (o[0] - BX0) / BK, fz = (o[2] - BZ0) / BK;
    float gx = (p[0] - BX0) / BK, gz = (p[2] - BZ0) / BK;
    int cx = (int) floorf(fx), cz = (int) floorf(fz), ex = (int) floorf(gx), ez = (int) floorf(gz);
    int sx = d[0] > 0 ? 1 : -1, sz = d[2] > 0 ? 1 : -1;
    float tdx = d[0] != 0 ? fabsf(BK / d[0]) : 1e30f, tdz = d[2] != 0 ? fabsf(BK / d[2]) : 1e30f;
    float tmx = d[0] != 0 ? ((sx > 0 ? (cx + 1) - fx : fx - cx) * BK) / fabsf(d[0]) : 1e30f;
    float tmz = d[2] != 0 ? ((sz > 0 ? (cz + 1) - fz : fz - cz) * BK) / fabsf(d[2]) : 1e30f;
    float ylo = fminf(o[1], p[1]), yhi = fmaxf(o[1], p[1]);
    float len = sqrtf(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
    int fwd = 0, bwd = 0;
    for (int guard = 0; guard < 4096; guard++) {
        if (cx >= 0 && cz >= 0 && cx < (int) BW && cz < (int) BH) {
            uint32_t b = cx + cz * BW;
            for (uint32_t k = bstart[b]; k < bstart[b + 1]; k++) {
                uint32_t i = bidx[k];
                if (mark[i] == stamp) continue;
                mark[i] = stamp;
                const Tri* t = &T[i];
                if (t->yhi < ylo || t->ylo > yhi) continue;
                float h[3] = {d[1] * t->e2[2] - d[2] * t->e2[1], d[2] * t->e2[0] - d[0] * t->e2[2], d[0] * t->e2[1] - d[1] * t->e2[0]};
                float a = t->e1[0] * h[0] + t->e1[1] * h[1] + t->e1[2] * h[2];
                if (fabsf(a) < 1e-6f) continue;
                float f = 1.0f / a;
                float s[3] = {o[0] - t->v0[0], o[1] - t->v0[1], o[2] - t->v0[2]};
                float u = f * (s[0] * h[0] + s[1] * h[1] + s[2] * h[2]);
                if (u < 0 || u > 1) continue;
                float q[3] = {s[1] * t->e1[2] - s[2] * t->e1[1], s[2] * t->e1[0] - s[0] * t->e1[2], s[0] * t->e1[1] - s[1] * t->e1[0]};
                float v = f * (d[0] * q[0] + d[1] * q[1] + d[2] * q[2]);
                if (v < 0 || u + v > 1) continue;
                float tt = f * (t->e2[0] * q[0] + t->e2[1] * q[1] + t->e2[2] * q[2]);
                if (tt * len > MINDIST && tt < 0.9999f) {
                    /* a two-sided triangle always blocks; a back-culled one blocks only with another back-culled
                     * crossing of the other facing (one of the two faces the eye whatever the winding convention) */
                    if (!t->cull) return 1;
                    if (a > 0) fwd = 1; else bwd = 1;
                    if (fwd && bwd) return 1;
                }
            }
        }
        if (cx == ex && cz == ez) break;
        if (tmx < tmz) { if (tmx > 1.0f) break; tmx += tdx; cx += sx; } else { if (tmz > 1.0f) break; tmz += tdz; cz += sz; }
    }
    return 0;
}

static void samples(uint32_t c, int eye, float (*out)[3], uint32_t* n)
{
    /* eye: c = camera cell (y range CR[c][0..1]); target: c = target volume index (TG) */
    float lo = eye ? CR[c][0] : TG[c].ylo, hi = eye ? CR[c][1] : TG[c].yhi;
    if (!eye) c = TG[c].cell;
    uint32_t cx = c % W, cz = c / W;
    uint32_t hn = eye ? EN : TN;
    *n = 0;
    for (uint32_t k = 0; k < hn; k++) {
        float y = hn > 1 ? lo + (hi - lo) * k / (hn - 1) : (lo + hi) * 0.5f;
        for (uint32_t j = 0; j < SN; j++)
            for (uint32_t i = 0; i < SN; i++) {
                float fx = SN > 1 ? (float) i / (SN - 1) : 0.5f, fz = SN > 1 ? (float) j / (SN - 1) : 0.5f;
                out[*n][0] = X0 + cx * CELL - MARGIN + fx * (CELL + 2 * MARGIN);
                out[*n][1] = y;
                out[*n][2] = Z0 + cz * CELL - MARGIN + fz * (CELL + 2 * MARGIN);
                (*n)++;
            }
    }
}

static uint32_t next_row;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;

static void* worker(void* arg)
{
    (void) arg;
    uint32_t cap = SN * SN * (EN > TN ? EN : TN);
    float (*es)[3] = malloc(sizeof(float) * 3 * cap), (*ts)[3] = malloc(sizeof(float) * 3 * cap);
    uint32_t* mark = calloc(NT ? NT : 1, 4);
    uint32_t stamp = 0;
    for (;;) {
        pthread_mutex_lock(&mu);
        uint32_t a = next_row++;
        pthread_mutex_unlock(&mu);
        if (a >= W * H) break;
        uint8_t* row = OUT + (size_t) a * ROWB;
        int ae = CR[a][0] <= CR[a][1];
        uint32_t ne = 0;
        if (ae) samples(a, 1, es, &ne);
        for (uint32_t b = 0; b < NTG; b++) {
            int vis = 1;
            int bt = TG[b].ylo <= TG[b].yhi;
            uint32_t bc = TG[b].cell;
            int dx = abs((int) (a % W) - (int) (bc % W)), dz = abs((int) (a / W) - (int) (bc / W));
            float dist = (dx > dz ? dx : dz) * CELL;
            if (ae && bt && (uint32_t) (dx > dz ? dx : dz) >= NEARC && dist <= RANGE) {
                uint32_t nt = 0;
                samples(b, 0, ts, &nt);
                vis = 0;
                for (uint32_t i = 0; i < ne && !vis; i++)
                    for (uint32_t j = 0; j < nt; j++) {
                        if (++stamp == 0) { memset(mark, 0, NT * 4); stamp = 1; }
                        if (!seg_hits(es[i], ts[j], mark, stamp)) { vis = 1; break; }
                    }
            }
            if (vis) row[b >> 3] |= (uint8_t) (1u << (b & 7));
        }
    }
    free(es); free(ts); free(mark);
    return 0;
}

int main(int argc, char** argv)
{
    if (argc != 3) { fprintf(stderr, "usage: vis_pvs <in> <out>\n"); return 2; }
    FILE* f = fopen(argv[1], "rb");
    if (!f) return 1;
    char mg[4];
    uint32_t u[3];
    float fl[5];
    uint32_t u2[5];
    if (fread(mg, 1, 4, f) != 4 || memcmp(mg, "PVSI", 4) || fread(u, 4, 3, f) != 3 || fread(fl, 4, 5, f) != 5 ||
        fread(u2, 4, 5, f) != 5) { fprintf(stderr, "bad input\n"); return 1; }
    NT = u[0]; W = u[1]; H = u[2];
    X0 = fl[0]; Z0 = fl[1]; CELL = fl[2]; MARGIN = fl[3]; RANGE = fl[4];
    SN = u2[0]; EN = u2[1]; TN = u2[2]; NEARC = u2[3]; NTH = u2[4] ? u2[4] : 1;
    CR = malloc(sizeof(float) * 4 * W * H);
    if (fread(CR, 16, W * H, f) != W * H) return 1;
    if (fread(&NTG, 4, 1, f) != 1) return 1;
    TG = malloc(sizeof(Tgt) * (NTG ? NTG : 1));
    for (uint32_t i = 0; i < NTG; i++)
        if (fread(&TG[i].cell, 4, 1, f) != 1 || fread(&TG[i].ylo, 4, 1, f) != 1 || fread(&TG[i].yhi, 4, 1, f) != 1) return 1;
    float* raw = malloc(sizeof(float) * 10 * (NT ? NT : 1));
    if (fread(raw, 40, NT, f) != NT) return 1;
    fclose(f);
    T = malloc(sizeof(Tri) * (NT ? NT : 1));
    float mnx = 1e30f, mnz = 1e30f, mxx = -1e30f, mxz = -1e30f;
    for (uint32_t i = 0; i < NT; i++) {
        float* r = raw + 10 * i;
        T[i].cull = r[9] != 0.0f;
        for (int k = 0; k < 3; k++) { T[i].v0[k] = r[k]; T[i].e1[k] = r[3 + k] - r[k]; T[i].e2[k] = r[6 + k] - r[k]; }
        T[i].ylo = fminf(r[1], fminf(r[4], r[7])); T[i].yhi = fmaxf(r[1], fmaxf(r[4], r[7]));
        for (int k = 0; k < 9; k += 3) { mnx = fminf(mnx, r[k]); mxx = fmaxf(mxx, r[k]); mnz = fminf(mnz, r[k + 2]); mxz = fmaxf(mxz, r[k + 2]); }
    }
    BX0 = mnx - BK; BZ0 = mnz - BK;
    BW = (uint32_t) ((mxx - BX0) / BK) + 2; BH = (uint32_t) ((mxz - BZ0) / BK) + 2;
    if (!NT) { BW = BH = 1; }
    uint32_t* cnt = calloc(BW * BH + 1, 4);
    for (int pass = 0; pass < 2; pass++) {
        if (pass) {
            bstart = calloc(BW * BH + 1, 4);
            for (uint32_t b = 0; b < BW * BH; b++) bstart[b + 1] = bstart[b] + cnt[b];
            bidx = malloc(4 * (bstart[BW * BH] + 1));
            memset(cnt, 0, 4 * (BW * BH + 1));
        }
        for (uint32_t i = 0; i < NT; i++) {
            float* r = raw + 10 * i;
            int x0 = (int) ((fminf(r[0], fminf(r[3], r[6])) - BX0) / BK), x1 = (int) ((fmaxf(r[0], fmaxf(r[3], r[6])) - BX0) / BK);
            int z0 = (int) ((fminf(r[2], fminf(r[5], r[8])) - BZ0) / BK), z1 = (int) ((fmaxf(r[2], fmaxf(r[5], r[8])) - BZ0) / BK);
            for (int z = z0; z <= z1; z++)
                for (int x = x0; x <= x1; x++) {
                    uint32_t b = x + z * BW;
                    if (pass) bidx[bstart[b] + cnt[b]] = i;
                    cnt[b]++;
                }
        }
    }
    ROWB = (NTG + 7) / 8;
    OUT = calloc((size_t) ROWB * W * H, 1);
    pthread_t th[64];
    if (NTH > 64) NTH = 64;
    for (uint32_t i = 0; i < NTH; i++) pthread_create(&th[i], 0, worker, 0);
    for (uint32_t i = 0; i < NTH; i++) pthread_join(th[i], 0);
    FILE* o = fopen(argv[2], "wb");
    fwrite(OUT, ROWB, W * H, o);
    fclose(o);
    return 0;
}
