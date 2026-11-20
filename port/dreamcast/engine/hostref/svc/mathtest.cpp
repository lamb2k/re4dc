// mathtest.cpp (lane eng-svc5): the native math helpers (services/math/math_svc.cpp) against the original units
// math_sub.cpp and sub2.cpp on random inputs, bit for bit. The original objects are linked with every global symbol
// renamed orig_<symbol> (svc.mk mathtest), so both run in one program on the same inputs.
//
//   mathtest [count]     RE4_SVC_CONTROL=mathsin|mathmuku sets the native control (the test must then FAIL)
//
// Inputs mix small values, angles over several turns, positions of a room (+-40000), exact zeros of both signs and
// near-degenerate vectors. Output: one line a function (calls, outputs compared, outputs differing, the first
// difference); exit 1 when any output differs, 2 when a function was never called with a valid input.
// Not covered here: GetScreenPos, Get3DPosFrom2D and VecToCamVec (the camera and the scenery; the fixtures reach them).
#define fabsf mathtest_game_fabsf
#include "types.h"
#include "model.h"
#include "math_sub.h"
#include "main_mem.h"
#include "db_log.h"
#undef fabsf
#include "../../services/math/math_svc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

// ---- the original units under their renamed symbols ----
#define O(name) asm("orig_" #name)
extern "C" {
f32 o_SINF(f32) O(SINF);
f32 o_COSF(f32) O(COSF);
f32 o_LIMIT_ANGLE(f32) O(LIMIT_ANGLE);
f32 o_SQRTF(f32) O(SQRTF);
f32 o_IPOW(f32, int) O(IPOW);
f32 o_hermite(f32*, f32*, f32) O(hermite);
void o_low_RotMatrix(Mtx, Vec*) O(low_RotMatrix);
void o_RotMatrixZXY(Mtx, Vec*) O(RotMatrixZXY);
void o_SetOrientationZX(Vec*, Vec*, Mtx) O(SetOrientationZX);
void o_SetOrientationZY(Vec*, Vec*, Mtx) O(SetOrientationZY);
void o_Matrix2AxisAngle(Mtx, Vec*) O(Matrix2AxisAngle);
void o_VecRadLimit(Vec*) O(VecRadLimit);
f32 o_VecAngle(Vec*, Vec*) O(VecAngle);
f32 o_VecElevation(Vec*) O(VecElevation);
void o_MtxRotAxisPosRad(Mtx, Vec*, Vec*, f32) O(MtxRotAxisPosRad);
void o_VecLinearCombination(Vec*, Vec*, f32, f32, Vec*) O(VecLinearCombination);
void o_VecInternalDivisionAngle(Vec*, Vec*, f32, Vec*, f32) O(VecInternalDivisionAngle);
void o_VecLinearDecomposition(Vec*, Vec*, Vec*, f32*, f32*) O(VecLinearDecomposition);
int o_de_Boor_Cox(int, f32*, int, f32, f32*) O(de_Boor_Cox);
f32 o_MtxNNLUDecomposition(int, f32*, int*) O(MtxNNLUDecomposition);
f32 o_MtxNNInverse(int, f32*, f32*) O(MtxNNInverse);
void o_MtxNNMultVecSR(int, int, f32*, f32*, f32*) O(MtxNNMultVecSR);
void o_OrthographicProjection(Vec*, Vec*, Vec*, Vec*, Vec*) O(OrthographicProjection);
int o_HitCheckPoint4(Vec*, Vec*) O(HitCheckPoint4);
f32 o_GetXZAngle(Vec*, Vec*) O(GetXZAngle);
f32 o_GetXYAngle(Vec*, Vec*) O(GetXYAngle);
f32 o_GetXZAngleLocal(Vec*, Vec*, f32) O(GetXZAngleLocal);
f32 o_GetDistance(Vec*, Vec*) O(GetDistance);
f32 o_GetDistanceXZ(Vec*, Vec*) O(GetDistanceXZ);
f32 o_Muku(Vec*, Vec*, f32, f32) O(Muku);
f32 o_Muku2(f32, f32, f32) O(Muku2);
f32 o_Muku3(Vec*, f32, f32) O(Muku3);
void o_AddSpeed(cModel*, const Vec*) O(AddSpeed);
f32 o_RootSumSquare3(Vec*) O(RootSumSquare3);
f32 o_GetDistance3(Vec*, Vec*) O(GetDistance3);
void o_RotVector(Vec*, Vec*, Vec*) O(RotVector);
void o_BoxWorldCalc(Vec*, Vec*, Vec*, Vec*) O(BoxWorldCalc);
void o_PosToPos(Vec*, Vec*, Vec*, f32) O(PosToPos);
int o_LineSphereCrossCk(Vec*, Vec*, Vec*, Vec*, f32) O(LineSphereCrossCk);
int o_SphereHitCk(Vec*, Vec*, f32, f32) O(SphereHitCk);
void o_CalcParabolaVector(Vec*, Vec*, Vec*, f32) O(CalcParabolaVector);
f32 o_CalcStopDist(f32, f32) O(CalcStopDist);
int o_CalcMovePosDist(Vec*, Vec*, f32) O(CalcMovePosDist);
// C++ names (mangled), renamed the same way
void o_RotMatrix(Mtx, Vec*) asm("orig__Z9RotMatrixPA4_fP3Vec");
void o_ScaleMatrix(Mtx, Vec*) asm("orig__Z11ScaleMatrixPA4_fP3Vec");
void o_TransMatrix(Mtx, Vec*) asm("orig__Z11TransMatrixPA4_fP3Vec");
f32 o_GetDistanceRef(Vec&, Vec&) asm("orig__Z11GetDistanceR3VecS0_");
int o_Front_check_mm(cModel*, cModel*, f32) asm("orig__Z11Front_checkP6cModelS0_f");
int o_Front_check_mv(cModel*, Vec*, f32) asm("orig__Z11Front_checkP6cModelP3Vecf");
int o_Front_check_vv(Vec*, Vec*, f32, f32) asm("orig__Z11Front_checkP3VecS0_ff");
}

// ---- what the units need of the game: the log, the debug heap ----
cLogPtr pLog;
void cLog::err(int, int, const char*, ...) {}
void* mem_alloc(u32 size, const char*, int, int, int) { return malloc(size ? size : 1); }
void Mem_free(void* p) { free(p); }
// math_sub.cpp writes a singular matrix's message to the C library's stderr through newlib's _impure_ptr
extern "C" {
struct ReentStdT { int e; void* in; void* out; void* err; };
ReentStdT g_reent;
ReentStdT* _impure_ptr = &g_reent;
}

namespace {
u32 g_seed = 0x2545F491u;
u32 rnd() { g_seed ^= g_seed << 13, g_seed ^= g_seed >> 17, g_seed ^= g_seed << 5; return g_seed; }
f32 uni(f32 lo, f32 hi) { return lo + (hi - lo) * ((rnd() >> 8) * (1.0f / 16777216.0f)); }
// a float of one of the input classes
f32 val()
{
    switch (rnd() % 10) {
    case 0: return 0.0f;
    case 1: return -0.0f;
    case 2: return uni(-1.0f, 1.0f);
    case 3: return uni(-1e-4f, 1e-4f);
    case 4: return uni(-40000.0f, 40000.0f);
    case 5: return uni(-20.0f, 20.0f);   // angles over several turns
    case 6: return (f32) ((int) (rnd() % 9) - 4) * 3.1415927f;   // whole half turns: the wrap's edges
    default: return uni(-4.0f, 4.0f);
    }
}
f32 ang() { return rnd() % 4 ? uni(-7.0f, 7.0f) : val(); }
Vec vec() { return Vec{val(), val(), val()}; }
Vec vec_near(const Vec& a) { Vec b = a; b.x += uni(-1e-3f, 1e-3f); return b; }

struct Row {
    const char* name;
    unsigned calls, outs, diff;
    char first[160];
};
Row rows[64];
int nrows;
Row* cur;
u32 bits(f32 f) { u32 u; memcpy(&u, &f, 4); return u; }
void cmp_f(const char* what, f32 a, f32 b)
{
    cur->outs++;
    if (bits(a) != bits(b)) {
        if (!cur->diff++) snprintf(cur->first, sizeof cur->first, "%s: orig %08x (%g) native %08x (%g)", what, bits(a), a, bits(b), b);
    }
}
void cmp_v(const char* what, const Vec& a, const Vec& b) { cmp_f(what, a.x, b.x), cmp_f(what, a.y, b.y), cmp_f(what, a.z, b.z); }
void cmp_m(const char* what, Mtx a, Mtx b)
{
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 4; c++) cmp_f(what, a[r][c], b[r][c]);
}
void cmp_i(const char* what, int a, int b)
{
    cur->outs++;
    if (a != b && !cur->diff++) snprintf(cur->first, sizeof cur->first, "%s: orig %d native %d", what, a, b);
}
void begin(const char* name)
{
    for (int i = 0; i < nrows; i++)
        if (!strcmp(rows[i].name, name)) { cur = &rows[i]; cur->calls++; return; }
    cur = &rows[nrows++];
    memset(cur, 0, sizeof *cur);
    cur->name = name;
    cur->calls = 1;
}
void mtx(Mtx m)
{
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 4; c++) m[r][c] = val();
}
}   // namespace

int main(int argc, char** argv)
{
    const unsigned N = argc > 1 ? (unsigned) atoi(argv[1]) : 20000;
    g_reent.err = fopen("/dev/null", "w");
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && !strcmp(c, "mathsin")) math_control = 1;
    if (c && !strcmp(c, "mathmuku")) math_control = 2;
    alignas(16) static u8 ma[2][4096], mb[2][4096];   // two cModel records (pos, ang) a side
    for (unsigned it = 0; it < N; it++) {
        f32 x = rnd() % 3 ? ang() : val(), y = val(), t = uni(-0.5f, 1.5f);
        Vec a = vec(), b = rnd() % 8 ? vec() : vec_near(a), cc = vec(), d = vec(), oa, ob, oa2, ob2;
        Mtx m1, m2, src;
        begin("SINF"), cmp_f("SINF", o_SINF(x), SINF(x));
        begin("COSF"), cmp_f("COSF", o_COSF(x), COSF(x));
        begin("LIMIT_ANGLE"), cmp_f("LIMIT_ANGLE", o_LIMIT_ANGLE(x), LIMIT_ANGLE(x));
        begin("SQRTF"), cmp_f("SQRTF", o_SQRTF(y), SQRTF(y));
        { const int n = rnd() % 6; begin("IPOW"), cmp_f("IPOW", o_IPOW(x, n), IPOW(x, n)); }
        { f32 p[2] = {val(), val()}, v[2] = {val(), val()}; begin("hermite"), cmp_f("hermite", o_hermite(p, v, t), hermite(p, v, t)); }
        { Vec r = {ang(), ang(), ang()};
          if (rnd() % 3 == 0) r.x = 0.0f;
          if (rnd() % 3 == 0) r.z = 0.0f;
          begin("RotMatrix"), o_RotMatrix(m1, &r), RotMatrix(m2, &r), cmp_m("RotMatrix", m1, m2);
          begin("low_RotMatrix"), o_low_RotMatrix(m1, &r), low_RotMatrix(m2, &r), cmp_m("low_RotMatrix", m1, m2);
          begin("RotMatrixZXY"), o_RotMatrixZXY(m1, &r), RotMatrixZXY(m2, &r), cmp_m("RotMatrixZXY", m1, m2);
          Vec r1, r2;
          o_RotMatrix(src, &r);
          memcpy(m1, src, sizeof(Mtx)), memcpy(m2, src, sizeof(Mtx));
          begin("Matrix2AxisAngle"), o_Matrix2AxisAngle(m1, &r1), Matrix2AxisAngle(m2, &r2), cmp_v("Matrix2AxisAngle", r1, r2);
          Vec v = vec(), w1, w2;
          begin("RotVector"), o_RotVector(&v, &r, &w1), RotVector(&v, &r, &w2), cmp_v("RotVector", w1, w2);
          Vec box[8], d1[8], d2[8], pos = vec();
          for (int i = 0; i < 8; i++) box[i] = vec();
          begin("BoxWorldCalc"), o_BoxWorldCalc(box, d1, &pos, &r), BoxWorldCalc(box, d2, &pos, &r);
          for (int i = 0; i < 8; i++) cmp_v("BoxWorldCalc", d1[i], d2[i]);
          Vec s = vec();
          mtx(m1), memcpy(m2, m1, sizeof(Mtx));
          begin("ScaleMatrix"), o_ScaleMatrix(m1, &s), ScaleMatrix(m2, &s), cmp_m("ScaleMatrix", m1, m2);
          begin("TransMatrix"), o_TransMatrix(m1, &s), TransMatrix(m2, &s), cmp_m("TransMatrix", m1, m2);
        }
        if (!(a.x == 0 && a.y == 0 && a.z == 0) && !(b.x == 0 && b.y == 0 && b.z == 0)) {
            begin("SetOrientationZX"), o_SetOrientationZX(&a, &b, m1), SetOrientationZX(&a, &b, m2), cmp_m("SetOrientationZX", m1, m2);
            begin("SetOrientationZY"), o_SetOrientationZY(&a, &b, m1), SetOrientationZY(&a, &b, m2), cmp_m("SetOrientationZY", m1, m2);
            begin("VecAngle"), cmp_f("VecAngle", o_VecAngle(&a, &b), VecAngle(&a, &b));
            const f32 s = uni(0.0f, 2.0f), tt = uni(0.1f, 2.0f);
            Vec ia = {0, 0, 0}, ib = {0, 0, 0};
            begin("VecInternalDivisionAngle"), o_VecInternalDivisionAngle(&a, &b, s, &ia, tt), VecInternalDivisionAngle(&a, &b, s, &ib, tt);
            cmp_v("VecInternalDivisionAngle", ia, ib);
        }
        begin("VecElevation"), cmp_f("VecElevation", o_VecElevation(&a), VecElevation(&a));
        { Vec r1 = {x, y * 0.001f, uni(-30.0f, 30.0f)}, r2 = r1;
          begin("VecRadLimit"), o_VecRadLimit(&r1), VecRadLimit(&r2), cmp_v("VecRadLimit", r1, r2); }
        { const f32 rad = ang();
          begin("MtxRotAxisPosRad"), o_MtxRotAxisPosRad(m1, &a, &b, rad), MtxRotAxisPosRad(m2, &a, &b, rad), cmp_m("MtxRotAxisPosRad", m1, m2); }
        { const f32 s = val(), tt = val();
          begin("VecLinearCombination"), o_VecLinearCombination(&a, &b, s, tt, &oa), VecLinearCombination(&a, &b, s, tt, &ob), cmp_v("VecLinearCombination", oa, ob);
          f32 s1, t1, s2, t2;
          begin("VecLinearDecomposition"), o_VecLinearDecomposition(&cc, &a, &b, &s1, &t1), VecLinearDecomposition(&cc, &a, &b, &s2, &t2);
          cmp_f("VecLinearDecomposition.s", s1, s2), cmp_f("VecLinearDecomposition.t", t1, t2); }
        { const int k = 1 + rnd() % 3, n = k + 1 + rnd() % (it % 50 == 0 ? 120 : 8);   // every 50th: the heap path
          f32 knot[128], o1[128], o2[128];
          for (int i = 0; i < n; i++) knot[i] = (i ? knot[i - 1] : 0.0f) + (rnd() % 4 ? uni(0.0f, 3.0f) : 0.0f);
          const f32 tt = uni(-0.5f, (f32) n + 0.5f);
          f32* kn = rnd() % 2 ? knot : NULL;
          begin("de_Boor_Cox");
          const int r1 = o_de_Boor_Cox(n, kn, k, tt, o1), r2 = de_Boor_Cox(n, kn, k, tt, o2);
          cmp_i("de_Boor_Cox ret", r1, r2);
          for (int i = 0; i < n; i++) cmp_f("de_Boor_Cox", o1[i], o2[i]); }
        { const int n = 1 + rnd() % (it % 50 == 1 ? 20 : 6);   // every 50th: the heap path
          f32 A[400], A1[400], A2[400], i1[400], i2[400];
          int ip1[20], ip2[20];
          for (int i = 0; i < n * n; i++) A[i] = rnd() % 7 ? uni(-10.0f, 10.0f) : 0.0f;
          memcpy(A1, A, sizeof A), memcpy(A2, A, sizeof A);
          begin("MtxNNLUDecomposition"), cmp_f("MtxNNLUDecomposition det", o_MtxNNLUDecomposition(n, A1, ip1), MtxNNLUDecomposition(n, A2, ip2));
          for (int i = 0; i < n * n; i++) cmp_f("MtxNNLUDecomposition A", A1[i], A2[i]);
          for (int i = 0; i < n; i++) cmp_i("MtxNNLUDecomposition ip", ip1[i], ip2[i]);
          memset(i1, 0, sizeof i1), memset(i2, 0, sizeof i2);
          begin("MtxNNInverse"), cmp_f("MtxNNInverse det", o_MtxNNInverse(n, A, i1), MtxNNInverse(n, A, i2));
          for (int i = 0; i < n * n; i++) cmp_f("MtxNNInverse", i1[i], i2[i]);
          f32 v[20], r1[20], r2[20];
          for (int i = 0; i < n; i++) v[i] = val();
          begin("MtxNNMultVecSR"), o_MtxNNMultVecSR(n, n, A, v, r1), MtxNNMultVecSR(n, n, A, v, r2);
          for (int i = 0; i < n; i++) cmp_f("MtxNNMultVecSR", r1[i], r2[i]); }
        begin("OrthographicProjection"), o_OrthographicProjection(&a, &oa, &b, &cc, &d), OrthographicProjection(&a, &ob, &b, &cc, &d), cmp_v("OrthographicProjection", oa, ob);
        { Vec q[4] = {vec(), vec(), vec(), vec()};
          begin("HitCheckPoint4"), cmp_i("HitCheckPoint4", o_HitCheckPoint4(&a, q), HitCheckPoint4(&a, q)); }
        begin("GetXZAngle"), cmp_f("GetXZAngle", o_GetXZAngle(&a, &b), GetXZAngle(&a, &b));
        begin("GetXYAngle"), cmp_f("GetXYAngle", o_GetXYAngle(&a, &b), GetXYAngle(&a, &b));
        begin("GetXZAngleLocal"), cmp_f("GetXZAngleLocal", o_GetXZAngleLocal(&a, &b, x), GetXZAngleLocal(&a, &b, x));
        begin("GetDistance"), cmp_f("GetDistance", o_GetDistance(&a, &b), GetDistance(&a, &b));
        begin("GetDistance&"), cmp_f("GetDistance&", o_GetDistanceRef(a, b), GetDistance(a, b));
        begin("GetDistanceXZ"), cmp_f("GetDistanceXZ", o_GetDistanceXZ(&a, &b), GetDistanceXZ(&a, &b));
        { const f32 lim = rnd() % 4 ? uni(0.0f, 0.5f) : val();
          begin("Muku"), cmp_f("Muku", o_Muku(&a, &b, x, lim), Muku(&a, &b, x, lim));
          const f32 tg = ang();
          begin("Muku2"), cmp_f("Muku2", o_Muku2(x, tg, lim), Muku2(x, tg, lim));
          begin("Muku3"), cmp_f("Muku3", o_Muku3(&a, x, lim), Muku3(&a, x, lim)); }
        { cModel* m1p = (cModel*) ma[0]; cModel* m2p = (cModel*) ma[1];
          cModel* n1p = (cModel*) mb[0]; cModel* n2p = (cModel*) mb[1];
          m1p->pos = m2p->pos = a, m1p->ang = m2p->ang = Vec{ang(), ang(), ang()};
          n1p->pos = n2p->pos = b;
          const f32 fa = uni(0.0f, 3.5f);
          begin("Front_check(mm)"), cmp_i("Front_check(mm)", o_Front_check_mm(m1p, n1p, fa), Front_check(m2p, n2p, fa));
          begin("Front_check(mv)"), cmp_i("Front_check(mv)", o_Front_check_mv(m1p, &b, fa), Front_check(m2p, &b, fa));
          begin("Front_check(vv)"), cmp_i("Front_check(vv)", o_Front_check_vv(&a, &b, x, fa), Front_check(&a, &b, x, fa));
          const Vec sp = vec();
          begin("AddSpeed"), o_AddSpeed(m1p, &sp), AddSpeed(m2p, &sp), cmp_v("AddSpeed", m1p->pos, m2p->pos); }
        begin("RootSumSquare3"), cmp_f("RootSumSquare3", o_RootSumSquare3(&a), RootSumSquare3(&a));
        begin("GetDistance3"), cmp_f("GetDistance3", o_GetDistance3(&a, &b), GetDistance3(&a, &b));
        begin("PosToPos"), o_PosToPos(&a, &b, &oa, t), PosToPos(&a, &b, &ob, t), cmp_v("PosToPos", oa, ob);
        { // a segment, a sphere near it; out given or not
          Vec s0 = vec(), s1 = rnd() % 4 ? Vec{s0.x + uni(-3000, 3000), s0.y + uni(-3000, 3000), s0.z + uni(-3000, 3000)} : vec();
          Vec ce = {s0.x + uni(-2000, 2000), s0.y + uni(-2000, 2000), s0.z + uni(-2000, 2000)};
          const f32 r = rnd() % 5 ? uni(0.0f, 1500.0f) : val();
          oa = ob = Vec{1, 2, 3};
          const bool give = rnd() % 4;
          begin("LineSphereCrossCk"), cmp_i("LineSphereCrossCk", o_LineSphereCrossCk(&s0, &s1, &ce, give ? &oa : 0, r),
                                               LineSphereCrossCk(&s0, &s1, &ce, give ? &ob : 0, r));
          cmp_v("LineSphereCrossCk out", oa, ob);
          const f32 rb = uni(0, 500);
          begin("SphereHitCk"), cmp_i("SphereHitCk", o_SphereHitCk(&s0, &ce, r, rb), SphereHitCk(&s0, &ce, r, rb)); }
        { const f32 h = rnd() % 4 ? uni(-100.0f, 3000.0f) : val();
          begin("CalcParabolaVector"), o_CalcParabolaVector(&oa, &a, &b, h), CalcParabolaVector(&ob, &a, &b, h), cmp_v("CalcParabolaVector", oa, ob); }
        { const f32 sp = uni(0.0f, 200.0f), dc = uni(0.5f, 20.0f);
          begin("CalcStopDist"), cmp_f("CalcStopDist", o_CalcStopDist(sp, dc), CalcStopDist(sp, dc)); }
        { Vec p1 = a, p2 = a; const f32 dd = rnd() % 4 ? uni(0.0f, 500.0f) : val();
          begin("CalcMovePosDist"), cmp_i("CalcMovePosDist", o_CalcMovePosDist(&p1, &b, dd), CalcMovePosDist(&p2, &b, dd)), cmp_v("CalcMovePosDist pos", p1, p2); }
        (void) ob2, (void) oa2;
    }
    int bad = 0;
    for (int i = 0; i < nrows; i++) {
        Row& r = rows[i];
        printf("%-28s calls %7u outputs %8u differ %7u%s%s\n", r.name, r.calls, r.outs, r.diff, r.diff ? "  first: " : "",
               r.diff ? r.first : "");
        if (r.diff) bad = 1;
        if (!r.outs) bad = bad ? bad : 2;
    }
    printf("native counters: scratch_stack %u scratch_heap %u normalize_zero %u; control %d\n", math_cnt.scratch_stack,
           math_cnt.scratch_heap, math_cnt.normalize_zero, math_control);
    printf("%s\n", bad == 1 ? "FAIL: outputs differ" : bad == 2 ? "FAIL: a function had no output" : "PASS: every output bit-identical");
    return bad;
}
