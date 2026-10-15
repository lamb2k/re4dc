/* sh4zam_selftest.c: SH4ZAM_SELFTEST=1 (game30.mk; test builds only, needs GAME_SH4ZAM=1; lane sh4zam-direct).
 * Once at OSInit, before any game code: every re4dc_zam_* routine (platform/sh4zam_direct.c) against the exact C
 * reference bodies (C_MTX* / C_VEC* in sdk/mtx.o and sdk/vec.o, re4dc_sincosf) on deterministic random inputs. One log
 * line per routine: "ZAMTEST <name> n= maxulp= maxabs_e6= maxrel_e9= bad=".
 *   maxulp: largest distance in units in the last place over the outputs whose reference magnitude is at least
 *           1/1024 of the largest output of that call (near-zero entries are covered by maxrel instead).
 *   maxabs: largest absolute difference; maxrel: largest |difference| / (largest |reference output| of that call).
 *   bad:    NaN / inf where the reference is finite (and the reverse), or a different singular return.
 * The numbers are those of the machine that runs it: on Flycast they are Flycast's FTRV / FIPR / FSRRA / FSCA
 * emulation (FSCA uses the hardware table; FIPR / FTRV / FSRRA are computed at host precision), not a console. */
#include <stdint.h>
#include <math.h>

typedef struct { float x, y, z; } zvec_t;
typedef float zmtx_t[3][4];

void re4dc_log(const char* fmt, ...);

void C_MTXConcat(const float (*a)[4], const float (*b)[4], float (*ab)[4]);
void C_MTXMultVec(const float (*m)[4], const zvec_t* s, zvec_t* d);
void C_MTXMultVecSR(const float (*m)[4], const zvec_t* s, zvec_t* d);
uint32_t C_MTXInverse(const float (*s)[4], float (*d)[4]);
void C_MTXRotTrig(float (*m)[4], char axis, float s, float c);
void C_MTXRotAxisRad(float (*m)[4], const zvec_t* axis, float rad);
float C_VECDotProduct(const zvec_t* a, const zvec_t* b);
float C_VECSquareMag(const zvec_t* v);
float C_VECMag(const zvec_t* v);
void C_VECNormalize(const zvec_t* s, zvec_t* d);
void C_VECCrossProduct(const zvec_t* a, const zvec_t* b, zvec_t* d);
float C_VECDistance(const zvec_t* a, const zvec_t* b);
void re4dc_sincosf(float x, float* s, float* c);

void re4dc_zam_MTXConcat(const float (*a)[4], const float (*b)[4], float (*ab)[4]);
void re4dc_zam_MTXMultVec(const float (*m)[4], const zvec_t* s, zvec_t* d);
void re4dc_zam_MTXMultVecSR(const float (*m)[4], const zvec_t* s, zvec_t* d);
uint32_t re4dc_zam_MTXInverse(const float (*s)[4], float (*d)[4]);
void re4dc_zam_MTXRotRad(float (*m)[4], char axis, float rad);
void re4dc_zam_MTXRotAxisRad(float (*m)[4], const zvec_t* axis, float rad);
float re4dc_zam_VECDotProduct(const zvec_t* a, const zvec_t* b);
float re4dc_zam_VECSquareMag(const zvec_t* v);
float re4dc_zam_VECMag(const zvec_t* v);
void re4dc_zam_VECNormalize(const zvec_t* s, zvec_t* d);
void re4dc_zam_VECCrossProduct(const zvec_t* a, const zvec_t* b, zvec_t* d);
float re4dc_zam_VECDistance(const zvec_t* a, const zvec_t* b);
void re4dc_zam_sincosf(float x, float* s, float* c);

static uint32_t g_seed = 0x5eed2015u;
static float rnd(float lo, float hi)
{
    g_seed = g_seed * 1664525u + 1013904223u;
    return lo + (hi - lo) * (float) (g_seed >> 8) * (1.0f / 16777216.0f);
}

typedef struct { const char* name; unsigned n; uint32_t maxulp; float maxabs, maxrel; unsigned bad; } zstat_t;

static int32_t ordered(float f)
{
    union { float f; int32_t i; } u = { f };
    return u.i < 0 ? (int32_t) 0x80000000 - u.i : u.i;
}

/* One call's outputs: ref[k] vs got[k], k < cnt. */
static void acc(zstat_t* st, const float* ref, const float* got, int cnt)
{
    float big = 0.0f;
    int k;
    for (k = 0; k < cnt; k++) {
        float a = fabsf(ref[k]);
        if (a > big && isfinite(a)) big = a;
    }
    for (k = 0; k < cnt; k++) {
        float d;
        int fr = isfinite(ref[k]), fg = isfinite(got[k]);
        if (fr != fg) { st->bad++; continue; }
        if (!fr) continue;
        d = fabsf(ref[k] - got[k]);
        if (d > st->maxabs) st->maxabs = d;
        if (big > 0.0f && d / big > st->maxrel) st->maxrel = d / big;
        if (fabsf(ref[k]) >= big * (1.0f / 1024.0f)) {
            int64_t du = (int64_t) ordered(ref[k]) - (int64_t) ordered(got[k]);
            uint32_t u = (uint32_t) (du < 0 ? -du : du);
            if (u > st->maxulp) st->maxulp = u;
        }
    }
    st->n++;
}

static void out(const zstat_t* st)
{
    /* integers only (the log's printf may lack floating point): maxabs in 1e-6 units, maxrel in 1e-9 units */
    re4dc_log("ZAMTEST %s n=%u maxulp=%lu maxabs_e6=%lu maxrel_e9=%lu bad=%u\n", st->name, st->n,
              (unsigned long) st->maxulp, (unsigned long) (st->maxabs < 4000.0f ? st->maxabs * 1e6f + 0.5f : 4e9f),
              (unsigned long) (st->maxrel < 4.0f ? st->maxrel * 1e9f + 0.5f : 4e9f), st->bad);
}

/* A game-like affine matrix: rotation (exact SDK sin / cos) x scale, translation up to +-tr. */
static void rnd_affine(float (*m)[4], float smin, float smax, float tr)
{
    zmtx_t r1, r2, r3, t;
    float s, c;
    int i, j;
    re4dc_sincosf(rnd(-3.2f, 3.2f), &s, &c); C_MTXRotTrig(r1, 'x', s, c);
    re4dc_sincosf(rnd(-3.2f, 3.2f), &s, &c); C_MTXRotTrig(r2, 'y', s, c);
    re4dc_sincosf(rnd(-3.2f, 3.2f), &s, &c); C_MTXRotTrig(r3, 'z', s, c);
    C_MTXConcat((const float (*)[4]) r1, (const float (*)[4]) r2, t);
    C_MTXConcat((const float (*)[4]) t, (const float (*)[4]) r3, m);
    for (i = 0; i < 3; i++) {
        float k = rnd(smin, smax);
        for (j = 0; j < 3; j++) m[i][j] *= k;
        m[i][3] = rnd(-tr, tr);
    }
}

static void rnd_general(float (*m)[4])
{
    int i, j;
    for (i = 0; i < 3; i++) for (j = 0; j < 4; j++) m[i][j] = rnd(-2.0f, 2.0f);
}

void re4dc_zam_selftest(void)
{
    enum { N = 2000 };
    zstat_t sc = { "MTXConcat" }, sg = { "MTXConcat(general)" }, smv = { "MTXMultVec" }, ssr = { "MTXMultVecSR" },
            sinv = { "MTXInverse" }, srr = { "MTXRotRad" }, sax = { "MTXRotAxisRad" }, sdot = { "VECDotProduct" },
            ssq = { "VECSquareMag" }, smag = { "VECMag" }, snrm = { "VECNormalize" }, scr = { "VECCrossProduct" },
            sdst = { "VECDistance" }, ssin = { "sincosf" };
    zmtx_t a, b, r, z;
    int i;
    for (i = 0; i < N; i++) {
        rnd_affine(a, 0.05f, 4.0f, 2000.0f);
        rnd_affine(b, 0.05f, 4.0f, 2000.0f);
        C_MTXConcat((const float (*)[4]) a, (const float (*)[4]) b, r);
        re4dc_zam_MTXConcat((const float (*)[4]) a, (const float (*)[4]) b, z);
        acc(&sc, &r[0][0], &z[0][0], 12);
        /* aliasing: ab == a */
        {
            zmtx_t a2;
            int k;
            for (k = 0; k < 12; k++) (&a2[0][0])[k] = (&a[0][0])[k];
            re4dc_zam_MTXConcat((const float (*)[4]) a2, (const float (*)[4]) b, a2);
            for (k = 0; k < 12; k++) if ((&a2[0][0])[k] != (&z[0][0])[k]) { sc.bad++; break; }
        }
        rnd_general(a);
        rnd_general(b);
        C_MTXConcat((const float (*)[4]) a, (const float (*)[4]) b, r);
        re4dc_zam_MTXConcat((const float (*)[4]) a, (const float (*)[4]) b, z);
        acc(&sg, &r[0][0], &z[0][0], 12);
        {
            zvec_t v = { rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f) }, vr, vz;
            rnd_affine(a, 0.05f, 4.0f, 2000.0f);
            C_MTXMultVec((const float (*)[4]) a, &v, &vr);
            re4dc_zam_MTXMultVec((const float (*)[4]) a, &v, &vz);
            acc(&smv, &vr.x, &vz.x, 3);
            C_MTXMultVecSR((const float (*)[4]) a, &v, &vr);
            re4dc_zam_MTXMultVecSR((const float (*)[4]) a, &v, &vz);
            acc(&ssr, &vr.x, &vz.x, 3);
        }
        {
            uint32_t rr, rz;
            rnd_affine(a, 0.05f, 4.0f, 2000.0f);
            rr = C_MTXInverse((const float (*)[4]) a, r);
            rz = re4dc_zam_MTXInverse((const float (*)[4]) a, z);
            if (rr != rz) sinv.bad++;
            else if (rr) acc(&sinv, &r[0][0], &z[0][0], 12);
        }
        {
            static const char ax[3] = { 'x', 'y', 'z' };
            float x = rnd(-6.3f, 6.3f), s, c;
            re4dc_sincosf(x, &s, &c);
            C_MTXRotTrig(r, ax[i % 3], s, c);
            re4dc_zam_MTXRotRad(z, ax[i % 3], x);
            acc(&srr, &r[0][0], &z[0][0], 12);
        }
        {
            zvec_t axis = { rnd(-1.0f, 1.0f), rnd(-1.0f, 1.0f), rnd(-1.0f, 1.0f) };
            float x = rnd(-6.3f, 6.3f);
            if (fabsf(axis.x) + fabsf(axis.y) + fabsf(axis.z) < 0.01f) axis.y = 1.0f;
            C_MTXRotAxisRad(r, &axis, x);
            re4dc_zam_MTXRotAxisRad(z, &axis, x);
            acc(&sax, &r[0][0], &z[0][0], 12);
        }
        {
            zvec_t p = { rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f) };
            zvec_t q = { rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f), rnd(-500.0f, 500.0f) };
            zvec_t vr, vz;
            float fr, fz;
            fr = C_VECDotProduct(&p, &q); fz = re4dc_zam_VECDotProduct(&p, &q); acc(&sdot, &fr, &fz, 1);
            fr = C_VECSquareMag(&p); fz = re4dc_zam_VECSquareMag(&p); acc(&ssq, &fr, &fz, 1);
            fr = C_VECMag(&p); fz = re4dc_zam_VECMag(&p); acc(&smag, &fr, &fz, 1);
            C_VECNormalize(&p, &vr); re4dc_zam_VECNormalize(&p, &vz); acc(&snrm, &vr.x, &vz.x, 3);
            C_VECCrossProduct(&p, &q, &vr); re4dc_zam_VECCrossProduct(&p, &q, &vz); acc(&scr, &vr.x, &vz.x, 3);
            fr = C_VECDistance(&p, &q); fz = re4dc_zam_VECDistance(&p, &q); acc(&sdst, &fr, &fz, 1);
        }
        {
            float x = rnd(-50.0f, 50.0f), rs[2], zs[2];
            re4dc_sincosf(x, &rs[0], &rs[1]);
            re4dc_zam_sincosf(x, &zs[0], &zs[1]);
            /* sin and cos separately against 1.0 (the output range), not the call's larger output. */
            {
                float o1[2] = { rs[0], 1.0f }, g1[2] = { zs[0], 1.0f }, o2[2] = { rs[1], 1.0f }, g2[2] = { zs[1], 1.0f };
                acc(&ssin, o1, g1, 2);
                acc(&ssin, o2, g2, 2);
            }
        }
    }
    out(&sc); out(&sg); out(&smv); out(&ssr); out(&sinv); out(&srr); out(&sax);
    out(&sdot); out(&ssq); out(&smag); out(&snrm); out(&scr); out(&sdst); out(&ssin);
    re4dc_log("ZAMTEST done\n");
}
