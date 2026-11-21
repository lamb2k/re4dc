/* sdktest.c (lane eng-svc5): the native SDK math (services/math/sdk_math.cpp) against the SDK's C reference code the
 * reference build links (src/lib mtx.c, mtxvec.c, mtx44.c, vec.c, quat.c; their global symbols renamed orig_<symbol>,
 * svc.mk sdktest), bit for bit, on random inputs: every function the engine images and re4ref link, through both of the
 * native names (PS* and C_*), in place (output = input) and apart.
 *
 *   sdktest [count]   RE4_SVC_CONTROL=sdkconcat sets the native control (PSMTXConcat's translation without a's own:
 *                     must FAIL)
 * Exit 0 PASS, 1 when any output differs, 2 when a function was never called. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef float f32;
typedef unsigned long u32;
typedef f32 Mtx[3][4];
typedef f32 Mtx44[4][4];
typedef struct { f32 x, y, z; } Vec;
typedef struct { f32 x, y, z, w; } Quaternion;

#define DECL(ret, name, params) ret C_##name params; ret orig_C_##name params; ret PS##name params;
DECL(void, MTXIdentity, (Mtx))
DECL(void, MTXCopy, (const Mtx, Mtx))
DECL(void, MTXConcat, (const Mtx, const Mtx, Mtx))
DECL(void, MTXTranspose, (const Mtx, Mtx))
DECL(u32, MTXInverse, (const Mtx, Mtx))
DECL(void, MTXRotRad, (Mtx, char, f32))
DECL(void, MTXRotTrig, (Mtx, char, f32, f32))
DECL(void, MTXRotAxisRad, (Mtx, const Vec*, f32))
DECL(void, MTXTrans, (Mtx, f32, f32, f32))
DECL(void, MTXTransApply, (const Mtx, Mtx, f32, f32, f32))
DECL(void, MTXScale, (Mtx, f32, f32, f32))
DECL(void, MTXQuat, (Mtx, const Quaternion*))
DECL(void, MTXMultVec, (const Mtx, const Vec*, Vec*))
DECL(void, MTXMultVecArray, (const Mtx, const Vec*, Vec*, u32))
DECL(void, MTXMultVecSR, (const Mtx, const Vec*, Vec*))
DECL(void, VECAdd, (const Vec*, const Vec*, Vec*))
DECL(void, VECSubtract, (const Vec*, const Vec*, Vec*))
DECL(void, VECScale, (const Vec*, Vec*, f32))
DECL(void, VECNormalize, (const Vec*, Vec*))
DECL(f32, VECSquareMag, (const Vec*))
DECL(f32, VECMag, (const Vec*))
DECL(f32, VECDotProduct, (const Vec*, const Vec*))
DECL(void, VECCrossProduct, (const Vec*, const Vec*, Vec*))
DECL(f32, VECSquareDistance, (const Vec*, const Vec*))
DECL(f32, VECDistance, (const Vec*, const Vec*))
void C_MTXLookAt(Mtx, const Vec*, const Vec*, const Vec*);
void orig_C_MTXLookAt(Mtx, const Vec*, const Vec*, const Vec*);
void C_MTXOrtho(Mtx44, f32, f32, f32, f32, f32, f32);
void orig_C_MTXOrtho(Mtx44, f32, f32, f32, f32, f32, f32);
void C_MTXPerspective(Mtx44, f32, f32, f32, f32);
void orig_C_MTXPerspective(Mtx44, f32, f32, f32, f32);
void C_QUATMtx(Quaternion*, const Mtx);
void orig_C_QUATMtx(Quaternion*, const Mtx);
void C_QUATSlerp(const Quaternion*, const Quaternion*, Quaternion*, f32);
void orig_C_QUATSlerp(const Quaternion*, const Quaternion*, Quaternion*, f32);
extern int sdk_math_control;

static uint32_t seed = 0x51ED270Bu;
static uint32_t rnd(void) { seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed; }
static float uni(float lo, float hi) { return lo + (hi - lo) * ((rnd() >> 8) * (1.0f / 16777216.0f)); }
static float val(void)
{
    switch (rnd() % 8) {
    case 0: return 0.0f;
    case 1: return -0.0f;
    case 2: return uni(-1.0f, 1.0f);
    case 3: return uni(-40000.0f, 40000.0f);
    case 4: return uni(-1e-3f, 1e-3f);
    default: return uni(-10.0f, 10.0f);
    }
}
static void fill(float* p, int n) { for (int i = 0; i < n; i++) p[i] = val(); }

struct row { const char* name; unsigned calls, diff; };
static struct row rows[64];
static int nrows;
static struct row* row(const char* n)
{
    for (int i = 0; i < nrows; i++) if (!strcmp(rows[i].name, n)) return &rows[i];
    rows[nrows].name = n;
    return &rows[nrows++];
}
static void check(const char* n, const void* a, const void* b, size_t size)
{
    struct row* r = row(n);
    r->calls++;
    if (memcmp(a, b, size)) r->diff++;
}

int main(int argc, char** argv)
{
    unsigned N = argc > 1 ? (unsigned) atoi(argv[1]) : 100000;
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && !strcmp(c, "sdkconcat")) sdk_math_control = 1;
    for (unsigned it = 0; it < N; it++) {
        Mtx a, b, o1, o2, i1, i2;
        Mtx44 p1, p2;
        Vec v, w, z, r1, r2, va[4], d1[4], d2[4];
        Quaternion q, q2, s1, s2;
        f32 f1, f2, k = val(), t = uni(-0.2f, 1.2f);
        fill(&a[0][0], 12), fill(&b[0][0], 12), fill(&v.x, 3), fill(&w.x, 3), fill(&z.x, 3), fill(&q.x, 4), fill(&q2.x, 4);
        fill(&va[0].x, 12);
        const char ax = "xyzXYZq"[rnd() % 7];
        /* matrices: apart and in place, both native names */
        orig_C_MTXIdentity(o1), C_MTXIdentity(o2), check("MTXIdentity", o1, o2, sizeof o1);
        orig_C_MTXCopy(a, o1), PSMTXCopy(a, o2), check("MTXCopy", o1, o2, sizeof o1);
        orig_C_MTXConcat(a, b, o1), PSMTXConcat(a, b, o2), check("MTXConcat", o1, o2, sizeof o1);
        memcpy(i1, a, sizeof a), memcpy(i2, a, sizeof a);
        orig_C_MTXConcat(i1, b, i1), C_MTXConcat(i2, b, i2), check("MTXConcat (in place)", i1, i2, sizeof i1);
        orig_C_MTXTranspose(a, o1), PSMTXTranspose(a, o2), check("MTXTranspose", o1, o2, sizeof o1);
        memcpy(o1, a, sizeof a), memcpy(o2, a, sizeof a);
        if (rnd() % 8 == 0) o1[0][0] = o2[0][0] = 0.0f, o1[1][0] = o2[1][0] = 0.0f, o1[2][0] = o2[2][0] = 0.0f;   /* singular */
        memcpy(i1, b, sizeof b), memcpy(i2, b, sizeof b);
        { u32 r = orig_C_MTXInverse(o1, i1), s = PSMTXInverse(o2, i2);
          check("MTXInverse", i1, i2, sizeof i1), check("MTXInverse ret", &r, &s, sizeof r); }
        orig_C_MTXInverse(o1, o1), C_MTXInverse(o2, o2), check("MTXInverse (in place)", o1, o2, sizeof o1);
        memcpy(o1, b, sizeof b), memcpy(o2, b, sizeof b);
        orig_C_MTXRotRad(o1, ax, k), PSMTXRotRad(o2, ax, k), check("MTXRotRad", o1, o2, sizeof o1);
        orig_C_MTXRotTrig(o1, ax, v.x, v.y), C_MTXRotTrig(o2, ax, v.x, v.y), check("MTXRotTrig", o1, o2, sizeof o1);
        if (v.x != 0.0f || v.y != 0.0f || v.z != 0.0f)
            orig_C_MTXRotAxisRad(o1, &v, k), PSMTXRotAxisRad(o2, &v, k), check("MTXRotAxisRad", o1, o2, sizeof o1);
        orig_C_MTXTrans(o1, v.x, v.y, v.z), PSMTXTrans(o2, v.x, v.y, v.z), check("MTXTrans", o1, o2, sizeof o1);
        orig_C_MTXTransApply(a, o1, v.x, v.y, v.z), PSMTXTransApply(a, o2, v.x, v.y, v.z), check("MTXTransApply", o1, o2, sizeof o1);
        orig_C_MTXTransApply(o1, o1, w.x, w.y, w.z), C_MTXTransApply(o2, o2, w.x, w.y, w.z), check("MTXTransApply (in place)", o1, o2, sizeof o1);
        orig_C_MTXScale(o1, v.x, v.y, v.z), PSMTXScale(o2, v.x, v.y, v.z), check("MTXScale", o1, o2, sizeof o1);
        orig_C_MTXQuat(o1, &q), PSMTXQuat(o2, &q), check("MTXQuat", o1, o2, sizeof o1);
        orig_C_MTXMultVec(a, &v, &r1), PSMTXMultVec(a, &v, &r2), check("MTXMultVec", &r1, &r2, sizeof r1);
        r1 = r2 = v, orig_C_MTXMultVec(a, &r1, &r1), C_MTXMultVec(a, &r2, &r2), check("MTXMultVec (in place)", &r1, &r2, sizeof r1);
        orig_C_MTXMultVecSR(a, &v, &r1), PSMTXMultVecSR(a, &v, &r2), check("MTXMultVecSR", &r1, &r2, sizeof r1);
        orig_C_MTXMultVecArray(a, va, d1, 4), PSMTXMultVecArray(a, va, d2, 4), check("MTXMultVecArray", d1, d2, sizeof d1);
        if (!(w.x == 0 && w.y == 0 && w.z == 0)) {
            orig_C_MTXLookAt(o1, &v, &w, &z), C_MTXLookAt(o2, &v, &w, &z), check("MTXLookAt", o1, o2, sizeof o1);
        }
        { const f32 tt = val(), bb = val(), ll = val(), rr = val(), nn = uni(1.0f, 100.0f), ff = uni(200.0f, 90000.0f);
          orig_C_MTXOrtho(p1, tt, bb, ll, rr, nn, ff), C_MTXOrtho(p2, tt, bb, ll, rr, nn, ff), check("MTXOrtho", p1, p2, sizeof p1);
          const f32 fov = uni(1.0f, 170.0f), asp = uni(0.5f, 2.5f);
          orig_C_MTXPerspective(p1, fov, asp, nn, ff), C_MTXPerspective(p2, fov, asp, nn, ff), check("MTXPerspective", p1, p2, sizeof p1); }
        /* vectors */
        orig_C_VECAdd(&v, &w, &r1), PSVECAdd(&v, &w, &r2), check("VECAdd", &r1, &r2, sizeof r1);
        orig_C_VECSubtract(&v, &w, &r1), PSVECSubtract(&v, &w, &r2), check("VECSubtract", &r1, &r2, sizeof r1);
        orig_C_VECScale(&v, &r1, k), PSVECScale(&v, &r2, k), check("VECScale", &r1, &r2, sizeof r1);
        if (!(v.x == 0 && v.y == 0 && v.z == 0))
            orig_C_VECNormalize(&v, &r1), PSVECNormalize(&v, &r2), check("VECNormalize", &r1, &r2, sizeof r1);
        f1 = orig_C_VECSquareMag(&v), f2 = PSVECSquareMag(&v), check("VECSquareMag", &f1, &f2, 4);
        f1 = orig_C_VECMag(&v), f2 = C_VECMag(&v), check("VECMag", &f1, &f2, 4);
        f1 = orig_C_VECDotProduct(&v, &w), f2 = PSVECDotProduct(&v, &w), check("VECDotProduct", &f1, &f2, 4);
        orig_C_VECCrossProduct(&v, &w, &r1), PSVECCrossProduct(&v, &w, &r2), check("VECCrossProduct", &r1, &r2, sizeof r1);
        r1 = r2 = v, orig_C_VECCrossProduct(&r1, &w, &r1), C_VECCrossProduct(&r2, &w, &r2), check("VECCrossProduct (in place)", &r1, &r2, sizeof r1);
        f1 = orig_C_VECSquareDistance(&v, &w), f2 = PSVECSquareDistance(&v, &w), check("VECSquareDistance", &f1, &f2, 4);
        f1 = orig_C_VECDistance(&v, &w), f2 = C_VECDistance(&v, &w), check("VECDistance", &f1, &f2, 4);
        /* quaternions: from rotation matrices and from anything */
        { Vec e = {uni(-3.2f, 3.2f), uni(-3.2f, 3.2f), uni(-3.2f, 3.2f)};
          orig_C_MTXRotAxisRad(o1, &e, uni(-7.0f, 7.0f));
          if (rnd() % 4 == 0) memcpy(o1, a, sizeof a);
          orig_C_QUATMtx(&s1, o1), C_QUATMtx(&s2, o1), check("QUATMtx", &s1, &s2, sizeof s1); }
        orig_C_QUATSlerp(&q, &q2, &s1, t), C_QUATSlerp(&q, &q2, &s2, t), check("QUATSlerp", &s1, &s2, sizeof s1);
        s1 = q, s2 = q, orig_C_QUATSlerp(&s1, &s1, &s1, t), C_QUATSlerp(&s2, &s2, &s2, t), check("QUATSlerp (same)", &s1, &s2, sizeof s1);
    }
    int bad = 0;
    for (int i = 0; i < nrows; i++) {
        printf("%-28s calls %7u differ %7u\n", rows[i].name, rows[i].calls, rows[i].diff);
        if (rows[i].diff) bad = 1;
        if (!rows[i].calls && !bad) bad = 2;
    }
    printf("control %d\n%s\n", sdk_math_control, bad == 1 ? "FAIL: outputs differ" : bad == 2 ? "FAIL: never called" : "PASS: every output bit-identical");
    return bad;
}
