/*! \file
 *  \brief   Test and benchmark of the cloth kernel (cloth_kernel.h), on the PC (lane eng-svc3).
 *
 *  make -C port/dreamcast/engine/hostref cloth_ktest   (builds and runs it; svc/svc.mk)
 *
 *  1. The primitives on the SW back-end against the C library the original calls (C_VECNormalize, C_VECDotProduct,
 *     C_VECCrossProduct, C_MTXMultVec(SR), C_MTXRotAxisRad, C_MTXConcat; SQRTF as math_sub.cpp builds it on the
 *     PC; acosf): bit for bit over random inputs.
 *  2. Random chains (variant 1 and 3, upper links before and after their links, side links, spheres and cylinders,
 *     the flag combinations the stages test): the fused schedule (cloth_k_step) against the original's pass order
 *     (cloth_k_step_passes), every link and bone value after every tick, bit for bit; the one-pass schedule's
 *     largest link difference (why it is not used).
 *  3. Benchmark: ns a chain step of each schedule on chains shaped like Leon's hair (21 links, variant 1), jacket
 *     (24, variant 3) and Ashley's skirt (48, variant 3, side links), with four volumes. PC host timing (x86): not an
 *     SH-4 number.
 *  Exit 0 when 1 and 2 hold.
 */
#include "cloth_kernel.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct { float x, y, z; } Vec;
typedef float Mtx[3][4];
void C_VECNormalize(const Vec* src, Vec* unit);
float C_VECDotProduct(const Vec* a, const Vec* b);
void C_VECCrossProduct(const Vec* a, const Vec* b, Vec* axb);
void C_MTXMultVec(const Mtx m, const Vec* src, Vec* dst);
void C_MTXMultVecSR(const Mtx m, const Vec* src, Vec* dst);
void C_MTXRotAxisRad(Mtx m, const Vec* axis, float rad);
void C_MTXConcat(const Mtx a, const Mtx b, Mtx ab);
void cloth_k_test_normalize(const float* in, float* out);
float cloth_k_test_dot(const float* a, const float* b);
void cloth_k_test_cross(const float* a, const float* b, float* out);
void cloth_k_test_mul(const float* m, const float* in, float* out, int sr);
void cloth_k_test_rot_axis(float* m, const float* axis, float rad);
void cloth_k_test_concat(const float* a, float* b);
float cloth_k_test_sqrt(float x);
float cloth_k_test_acos(float x);

static uint32_t g_r = 12345;
static float rnd(float lo, float hi) {
    g_r ^= g_r << 13;
    g_r ^= g_r >> 17;
    g_r ^= g_r << 5;
    return lo + (hi - lo) * (float) (g_r >> 8) * (1.0f / 16777216.0f);
}
static int same(const void* a, const void* b, size_t n) { return memcmp(a, b, n) == 0; }

static int test_primitives(void) {
    int bad = 0;
    const int N = 200000;
    for (int k = 0; k < N; k++) {
        float a[3] = {rnd(-500, 500), rnd(-500, 500), rnd(-500, 500)};
        float b[3] = {rnd(-2, 2), rnd(-2, 2), rnd(-2, 2)};
        float o[3], m[12], m2[12];
        Vec va = {a[0], a[1], a[2]}, vb = {b[0], b[1], b[2]}, vr;
        cloth_k_test_normalize(a, o);
        C_VECNormalize(&va, &vr);
        bad += !same(o, &vr, 12);
        float d = cloth_k_test_dot(a, b), dr = C_VECDotProduct(&va, &vb);
        bad += !same(&d, &dr, 4);
        cloth_k_test_cross(a, b, o);
        C_VECCrossProduct(&va, &vb, &vr);
        bad += !same(o, &vr, 12);
        const float rad = rnd(-3.1f, 3.1f);
        Mtx rm;
        cloth_k_test_rot_axis(m, b, rad);
        C_MTXRotAxisRad(rm, &vb, rad);
        bad += !same(m, rm, 48);
        for (int i = 0; i < 12; i++) m[i] = rnd(-2, 2);
        Mtx mm;
        memcpy(mm, m, 48);
        cloth_k_test_mul(m, a, o, 0);
        C_MTXMultVec(mm, &va, &vr);
        bad += !same(o, &vr, 12);
        cloth_k_test_mul(m, a, o, 1);
        C_MTXMultVecSR(mm, &va, &vr);
        bad += !same(o, &vr, 12);
        for (int i = 0; i < 12; i++) m2[i] = rnd(-300, 300);
        Mtx a2, b2, ab;
        memcpy(a2, m, 48);
        memcpy(b2, m2, 48);
        C_MTXConcat(a2, b2, ab);
        cloth_k_test_concat(m, m2);
        bad += !same(m2, ab, 48);
        const float x = rnd(-0.001f, 4e6f);
        float s = cloth_k_test_sqrt(x), sr = x <= 0.00001f ? 0.0f : sqrtf(x);
        bad += !same(&s, &sr, 4);
        const float c = rnd(-1, 1);
        float ac = cloth_k_test_acos(c), acr = acosf(c);
        bad += !same(&ac, &acr, 4);
    }
    printf("primitives: %d random inputs x 9 operations against the C library: %s (%d differ)\n", N, bad ? "FAIL" : "bit-identical", bad);
    return bad;
}

// ---- random chains ----
typedef struct Chain {
    ClothKLink link[64];
    ClothKCold cold[64];
    float wx[64], wy[64], wz[64];
    float mat[64 * 16];
    ClothKVol vol[4];
    float gravity[64], rate[64], maxa[64], windRate[64], windAng[64];
    PresRng rng;
    ClothKStep s;
} Chain;

static void make_chain(Chain* c, int n, int variant, int cols, int unordered, uint32_t flags, int nVol, int bundle) {
    memset(c, 0, sizeof *c);
    for (int i = 0; i < n; i++) {
        ClothKLink* L = &c->link[i];
        const int row = i / cols, col = i % cols;
        L->bone = (uint8_t) (i + 1);
        L->up = row ? (uint8_t) (i - cols) : CLOTH_K_NONE;
        for (int q = 0; q < 4; q++) L->side[q] = CLOTH_K_NONE;
        if (cols > 1) {
            if (col > 0) L->side[0] = (uint8_t) (i - 1);
            if (col + 1 < cols) L->side[1] = (uint8_t) (i + 1);
            if (row && col > 0) L->side[2] = (uint8_t) (i - cols - 1);
            if (row && col + 1 < cols) L->side[3] = (uint8_t) (i - cols + 1);
        }
        L->len = 30.0f;
        L->pos.x = col * 20.0f + rnd(-2, 2);
        L->pos.y = 1000.0f - row * 30.0f + rnd(-2, 2);
        L->pos.z = rnd(-2, 2);
        L->oldPos = L->pos;
        L->nrm.x = 0;
        L->nrm.y = -1;
        L->nrm.z = 0;
        for (int q = 0; q < 4; q++) c->cold[i].dist[q] = 10.0f;
        c->cold[i].fixPos = L->pos;
        if (i == 0 && (flags & 0x1000)) L->fix = 1;
        c->gravity[i] = rnd(0.5f, 2.0f);
        c->rate[i] = rnd(0.8f, 0.99f);
        c->maxa[i] = rnd(0.2f, 1.2f);
        c->windRate[i] = rnd(0.0f, 1.0f);
        c->windAng[i] = rnd(0.0f, 2.0f);
    }
    if (unordered && n > 4) {   // one upper link after its link: the fused schedule must take the separate passes
        c->link[2].up = (uint8_t) (n - 1);
    }
    for (int b = 0; b < 64; b++) {
        float* m = c->mat + 16 * b;
        const float a = rnd(-3, 3);
        m[0] = cosf(a); m[1] = 0; m[2] = sinf(a); m[3] = rnd(-50, 50);
        m[4] = 0; m[5] = 1; m[6] = 0; m[7] = 1000.0f - b * 10.0f;
        m[8] = -sinf(a); m[9] = 0; m[10] = cosf(a); m[11] = rnd(-50, 50);
        c->wx[b] = m[3];
        c->wy[b] = m[7];
        c->wz[b] = m[11];
    }
    for (int k = 0; k < nVol; k++) {
        ClothKVol* v = &c->vol[k];
        v->type = k & 1;
        v->p0.x = rnd(-20, 40); v->p0.y = rnd(900, 1000); v->p0.z = rnd(-20, 20);
        v->p1 = v->p0;
        v->p1.y -= 80.0f;
        v->r = rnd(10, 30);
        v->len = 80.0f;
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 4; j++) v->mat[i][j] = v->inv[i][j] = (i == j) ? 1.0f : 0.0f;
        v->mat[0][3] = v->p0.x; v->mat[1][3] = v->p0.y; v->mat[2][3] = v->p0.z;
        v->inv[0][3] = -v->p0.x; v->inv[1][3] = -v->p0.y; v->inv[2][3] = -v->p0.z;
    }
    pres_seed(&c->rng, 7);
    ClothKStep* s = &c->s;
    s->n = (uint32_t) n;
    s->variant = (uint32_t) variant;
    s->flags = flags & 0xFFF;
    s->bundle = (uint32_t) bundle;
    s->stretchy = 0.9f;
    s->gravity = 1.0f;
    s->pGravity = (flags & 0x2000) ? c->gravity : 0;
    s->rate = 0.95f;
    s->pRate = c->rate;
    s->pMax = c->maxa;
    s->floorY = 700.0f;
    s->integrate = 1;
    s->wind = variant == 1 && (flags & 0x200);
    s->spdLen = 2.0f;
    s->windAng = c->windAng;
    s->pWindRate = c->windRate;
    s->windScale = 1.0f;
}
static void bind(Chain* c) {
    ClothKStep* s = &c->s;
    s->link = c->link;
    s->cold = c->cold;
    s->wx = c->wx;
    s->wy = c->wy;
    s->wz = c->wz;
    s->boneMat = c->mat;
    s->vol = c->s.flags & 1 ? 0 : c->vol;
    s->nVol = 4;
    s->rng = &c->rng;
}
static void tick_inputs(Chain* c, int t) {
    c->s.move.x = 3.0f * sinf(0.1f * t);
    c->s.move.y = 0.0f;
    c->s.move.z = 2.0f * cosf(0.07f * t);
    c->s.mpos.x = c->wx[0];
    c->s.mpos.y = c->wy[0];
    c->s.mpos.z = c->wz[0];
    for (int b = 0; b < 64; b++) {   // the bones follow the root (the skeleton's world pass)
        c->mat[16 * b + 3] += c->s.move.x;
        c->mat[16 * b + 11] += c->s.move.z;
        c->wx[b] = c->mat[16 * b + 3];
        c->wz[b] = c->mat[16 * b + 11];
    }
    for (int i = 0; i < (int) c->s.n; i++) c->link[i].hit = 0;
}
static float max_link_diff(const Chain* a, const Chain* b) {
    float m = 0;
    for (uint32_t i = 0; i < a->s.n; i++) {
        float d = fabsf(a->link[i].pos.x - b->link[i].pos.x) + fabsf(a->link[i].pos.y - b->link[i].pos.y) +
                  fabsf(a->link[i].pos.z - b->link[i].pos.z);
        if (d > m || d != d) m = d != d ? 1e30f : d;
    }
    return m;
}

static int test_chains(void) {
    static Chain A, B, C;
    int bad = 0, cases = 0, ticks = 0;
    float onepass = 0;
    const uint32_t flagSets[] = {0x0, 0x80, 0x4, 0x8, 0x100, 0x200, 0x10, 0x2, 0x1, 0x1000 | 0x80, 0x2000 | 0x200};
    for (int variant = 1; variant <= 3; variant += 2)
        for (int shape = 0; shape < 4; shape++)
            for (unsigned f = 0; f < sizeof flagSets / sizeof flagSets[0]; f++)
                for (int bundle = 1; bundle <= 3; bundle++) {
                    const int n = shape == 0 ? 21 : shape == 1 ? 24 : shape == 2 ? 48 : 30;
                    const int cols = shape == 2 ? 8 : shape == 3 ? 5 : 1;
                    const int unordered = shape == 3;
                    make_chain(&A, n, variant, cols, unordered, flagSets[f], 4, bundle);
                    B = A;
                    C = A;
                    bind(&A);
                    bind(&B);
                    bind(&C);
                    cases++;
                    for (int t = 0; t < 120; t++) {
                        tick_inputs(&A, t);
                        tick_inputs(&B, t);
                        tick_inputs(&C, t);
                        cloth_k_step_passes(&A.s);
                        cloth_k_step(&B.s);
                        cloth_k_step_onepass(&C.s);
                        ticks++;
                        if (!same(A.link, B.link, sizeof A.link) || !same(A.mat, B.mat, sizeof A.mat) ||
                            !same(A.wx, B.wx, sizeof A.wx) || !same(A.wy, B.wy, sizeof A.wy) || !same(A.wz, B.wz, sizeof A.wz)) {
                            if (!bad)
                                printf("  first difference: variant %d shape %d flags %x bundle %d tick %d (max link %g)\n", variant,
                                       shape, flagSets[f], bundle, t, max_link_diff(&A, &B));
                            bad++;
                            break;
                        }
                        const float d = max_link_diff(&A, &C);
                        if (d > onepass) onepass = d;
                    }
                }
    printf("chains: %d cases, %d chain-ticks: fused schedule against the original pass order: %s (%d cases differ)\n", cases, ticks,
           bad ? "FAIL" : "bit-identical", bad);
    printf("        one pass against the original pass order: largest link difference %.3g u (not used)\n", onepass);
    printf("        volume tests %u (hits %u), rotations %u\n", cloth_k_cnt.vol_tests, cloth_k_cnt.vol_hits, cloth_k_cnt.rotations);
    return bad;
}

static double now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e9 + ts.tv_nsec;
}
static void bench(void) {
    static Chain A;
    const struct { const char* name; int n, variant, cols; } sh[] = {
        {"hair-like, 21 links, Move", 21, 1, 1}, {"jacket-like, 24 links, Move3", 24, 3, 1}, {"skirt-like, 48 links, Move3, side links", 48, 3, 8}};
    printf("benchmark (PC host, x86, ns a chain step; not an SH-4 number):\n");
    for (int k = 0; k < 3; k++) {
        double t[3];
        for (int mode = 0; mode < 3; mode++) {
            make_chain(&A, sh[k].n, sh[k].variant, sh[k].cols, 0, 0x100, 4, 2);
            bind(&A);
            const int N = 20000;
            const double t0 = now_ns();
            for (int i = 0; i < N; i++) {
                tick_inputs(&A, i & 63);
                if (mode == 0) cloth_k_step_passes(&A.s);
                else if (mode == 1) cloth_k_step(&A.s);
                else cloth_k_step_onepass(&A.s);
            }
            t[mode] = (now_ns() - t0) / N;
        }
        printf("  %-42s original pass order %7.0f, fused %7.0f, one pass %7.0f\n", sh[k].name, t[0], t[1], t[2]);
    }
}

int main(void) {
    int bad = test_primitives();
    bad += test_chains();
    bench();
    printf("%s\n", bad ? "FAIL" : "PASS");
    return bad ? 1 : 0;
}
