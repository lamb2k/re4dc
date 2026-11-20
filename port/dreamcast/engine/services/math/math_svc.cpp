// Native math helpers (lane eng-svc5): math_sub.cpp's and sub2.cpp's entry points as engine code (math_svc.h).
//
// Every helper is a pure function of its inputs (or writes only its outputs), so the engine's body gives the original's
// results when it forms them with the same float operations: products and sums are written in the original's order
// (with -ffp-contract=off), the transcendental functions are the engine's libm (sinf, cosf, atan2f, acosf, asinf), and
// matrices are the SDK interface's. What is the engine's own: SH4ZAM vector arithmetic, no heap traffic in the B-spline
// basis and the dense inverse (a stack scratch; the original allocated and freed two to n + 2 blocks a call), no dead
// work (MtxRotAxisPosRad's first rotation, Matrix2AxisAngle's unused columns), and identity matrices written in place.
// include/math_sub.h defines a static fabsf (the SDK header's) that clashes with the C library's, which SH4ZAM's headers
// declare: the game headers see it under another name.
#define fabsf math_svc_game_fabsf
#include "types.h"
#include "global.h"
#include "model.h"
#include "player.h"
#include "camera.h"
#include "atari.h"
#include "math_sub.h"
#include "main_mem.h"
#include "db_log.h"
#undef fabsf
#include "math_svc.h"
#include "sh4zam/shz_vector.h"

extern "C" {
double atan2(double y, double x);
void GXGetProjectionv(f32* p);
void GXGetViewportv(f32* vp);
void GXProject(f32 x, f32 y, f32 z, const Mtx mtx, const f32* pm, const f32* vp, f32* sx, f32* sy, f32* sz);
MathCounters math_cnt;
int math_control;
}

#define PI2 6.2831855f

namespace {

// ---- SH4ZAM vectors over the game's Vec ----
inline shz_vec3_t V(const Vec* v) { return shz_vec3_init(v->x, v->y, v->z); }
inline void put(Vec* d, shz_vec3_t v) { d->x = v.x, d->y = v.y, d->z = v.z; }
inline f32 dot(const Vec* a, const Vec* b) { return shz_vec3_dot(V(a), V(b)); }
inline f32 mag(const Vec* v) { return __builtin_sqrtf(shz_vec3_magnitude_sqr(V(v))); }   // exact root (math_svc.h)

// The behaviour's checked normalize (include/math_sub.h VECNormalize): a zero vector is logged and gives zero; else
// the SDK's normalize: 1 / root of the squared length, times each component.
inline void normalize(const Vec* src, Vec* dst)
{
    if (0.0f == src->x && 0.0f == src->y && 0.0f == src->z) {
        math_cnt.normalize_zero++;
        pLog->err(0, 0, "VECNormalize:[%s/%d]", __FILE__, __LINE__);
        dst->x = dst->y = dst->z = 0.0f;
        return;
    }
    const shz_vec3_t v = V(src);
    put(dst, shz_vec3_scale(v, 1.0f / __builtin_sqrtf(shz_vec3_magnitude_sqr(v))));
}

// A rotation in the upper 3x3, translation zero (the identity's last column).
inline void basis(Mtx m, const Vec& x, const Vec& y, const Vec& z)
{
    m[0][0] = x.x, m[0][1] = y.x, m[0][2] = z.x, m[0][3] = 0.0f;
    m[1][0] = x.y, m[1][1] = y.y, m[1][2] = z.y, m[1][3] = 0.0f;
    m[2][0] = x.z, m[2][1] = y.z, m[2][2] = z.z, m[2][3] = 0.0f;
}

// The game's sin series (the GameCube's paired-single loop, both slots in scalar): odd powers x .. x^9 with the even
// coefficients in one sum, even powers x^2 .. x^10 with the odd coefficients in the other, the two sums added last.
const f32 kSinCoeff[10] = {
    1.0000012f, 2.9073722e-06f, -0.16666685f, -5.727683e-06f, 0.008331681f,
    4.281338e-06f, -0.00019622728f, -6.4099936e-07f, 2.363633e-06f, 4.0048576e-08f,
};
f32 coeff(int i)
{
    f32 c = kSinCoeff[i];
    return math_control == 1 && i == 8 ? 0.0f : c;   // control "mathsin": the x^9 term dropped
}
inline f32 sin_series(f32 x)
{
    math_cnt.series++;
    const f32 x2 = x * x;
    f32 p1 = x, p2 = x2, s0 = 0.0f, s1 = 0.0f;
    for (int k = 0; k < 5; k++) {
        s0 += p1 * coeff(2 * k);
        s1 += p2 * coeff(2 * k + 1);
        p1 *= x2;
        p2 *= x2;
    }
    return s0 + s1;
}

inline f32 turn_limit(f32 limit) { return math_control == 2 ? limit * 1.05f : limit; }   // control "mathmuku"

// Scratch for the B-spline basis and the dense inverse: the stack when it fits, the heap (as the original) when not.
template <class T, unsigned N> struct Scratch {
    T local[N];
    T* p;
    explicit Scratch(unsigned n)
    {
        if (n <= N) {
            p = local;
            math_cnt.scratch_stack++;
        } else {
            p = (T*) MEM_ALLOC(n * sizeof(T), 1, 13);
            math_cnt.scratch_heap++;
        }
    }
    ~Scratch()
    {
        if (p && p != local) Mem_free(p);
    }
};

}   // namespace

// ==== math_sub.cpp ====

// Rotation whose Z axis is z and X axis is x, orthonormalised (X from Y x Z).
void SetOrientationZX(Vec* z, Vec* x, Mtx m)
{
    Vec vx, vy, vz;
    normalize(x, &vx);
    normalize(z, &vz);
    put(&vy, shz_vec3_cross(V(&vz), V(&vx)));
    normalize(&vy, &vy);
    put(&vx, shz_vec3_cross(V(&vy), V(&vz)));
    normalize(&vx, &vx);
    basis(m, vx, vy, vz);
}

// Rotation whose Z axis is z and Y axis is y, orthonormalised (Y from Z x X).
void SetOrientationZY(Vec* z, Vec* y, Mtx m)
{
    Vec vx, vy, vz;
    normalize(y, &vy);
    normalize(z, &vz);
    put(&vx, shz_vec3_cross(V(&vy), V(&vz)));
    normalize(&vx, &vx);
    put(&vy, shz_vec3_cross(V(&vz), V(&vx)));
    normalize(&vy, &vy);
    basis(m, vx, vy, vz);
}

// Rotation matrix -> Euler angles in the RotMatrix order: x and y from the matrix's third row, z from what remains once
// the x and y rotation is taken out.
void Matrix2AxisAngle(Mtx m, Vec* rot)
{
    const f32 r20 = m[2][0], r21 = m[2][1], r22 = m[2][2];
    Mtx r, inv;
    rot->z = 0.0f;
    rot->x = -atan2f(-r21, r22);
    rot->y = -asinf(r20 > 1.0f ? 1.0f : r20 < -1.0f ? -1.0f : r20);
    RotMatrix(r, rot);
    PSMTXInverse(r, inv);
    PSMTXConcat(m, inv, r);
    rot->z = atan2f(r[1][0], r[0][0]);
}

// Each component wrapped into [-PI, PI).
void VecRadLimit(Vec* v)
{
    f32* p = &v->x;
    for (int i = 0; i < 3; i++) {
        while (p[i] >= PI) p[i] -= PI2;
        while (p[i] < -PI) p[i] += PI2;
    }
}

// Angle between two vectors (radians).
f32 VecAngle(Vec* a, Vec* b)
{
    f32 d = dot(a, b);
    f32 l = mag(a);
    l *= mag(b);
    d /= l;
    return acosf(d < -1.0f ? -1.0f : (d > 1.0f ? 1.0f : d));
}

// Elevation above the XZ plane (radians).
f32 VecElevation(Vec* v)
{
    return atan2f(v->y, SQRTF(v->x * v->x + v->z * v->z));
}

// Rotation of rad about axis through pos: translate to the axis, rotate, translate back.
void MtxRotAxisPosRad(Mtx m, Vec* axis, Vec* pos, f32 rad)
{
    Mtx t1, t2, t3, t21;
    PSMTXTrans(t1, -pos->x, -pos->y, -pos->z);
    PSMTXRotAxisRad(t2, axis, rad);
    PSMTXTrans(t3, pos->x, pos->y, pos->z);
    PSMTXConcat(t2, t1, t21);
    PSMTXConcat(t3, t21, m);
}

// out = s * a + t * b.
void VecLinearCombination(Vec* a, Vec* b, f32 s, f32 t, Vec* out)
{
    put(out, shz_vec3_add(shz_vec3_scale(V(a), s), shz_vec3_scale(V(b), t)));
}

// The direction of a turned toward b by s : t of the angle between them.
void VecInternalDivisionAngle(Vec* a, Vec* b, f32 s, Vec* out, f32 t)
{
    const f32 ang = VecAngle(a, b);
    if (ang == 0.0f) {
        normalize(a, out);
    } else if (ang != PI) {
        Mtx r;
        Vec axis;
        put(&axis, shz_vec3_cross(V(a), V(b)));
        PSMTXRotAxisRad(r, &axis, s / (t + s) * ang);
        PSMTXMultVecSR(r, a, out);
        normalize(out, out);
    }
}

// v = s * vec1 + t * vec2 on the plane the two span.
void VecLinearDecomposition(Vec* v, Vec* vec1, Vec* vec2, f32* s, f32* t)
{
    const shz_vec3_t n = shz_vec3_cross(V(vec1), V(vec2));
    const shz_vec3_t mm = shz_vec3_cross(V(v), n);
    const shz_vec3_t ab = shz_vec3_sub(V(vec2), V(vec1));
    shz_vec3_t va = shz_vec3_sub(V(v), V(vec1));
    f32 k = shz_vec3_dot(mm, va);
    k /= shz_vec3_dot(mm, ab);
    va = shz_vec3_add(V(vec1), shz_vec3_scale(ab, k));
    f32 l = mag(v);
    l /= __builtin_sqrtf(shz_vec3_magnitude_sqr(va));
    *s = l * (1.0f - k);
    *t = l * k;
}

// The three columns scaled by s.
void ScaleMatrix(Mtx m, Vec* s)
{
    for (int r = 0; r < 3; r++) {
        m[r][0] *= s->x;
        m[r][1] *= s->y;
        m[r][2] *= s->z;
    }
}

void TransMatrix(Mtx m, Vec* pos)
{
    m[0][3] = pos->x;
    m[1][3] = pos->y;
    m[2][3] = pos->z;
}

// The game's Euler matrix: Rz * Ry * Rx (X applied first), translation zero; sin and cos from libm.
namespace {
inline void euler(Mtx m, f32 sx, f32 cx, f32 sy, f32 cy, f32 sz, f32 cz)
{
    const f32 szcx = sz * cx, szsx = sz * sx, czsx = cz * sx, czcx = cz * cx;
    m[0][0] = cz * cy;
    m[0][1] = czsx * sy - szcx;
    m[0][2] = czcx * sy + szsx;
    m[0][3] = 0.0f;
    m[1][0] = sz * cy;
    m[1][1] = szsx * sy + czcx;
    m[1][2] = szcx * sy - czsx;
    m[1][3] = 0.0f;
    m[2][0] = -sy;
    m[2][1] = cy * sx;
    m[2][2] = cy * cx;
    m[2][3] = 0.0f;
}
}   // namespace
void RotMatrix(Mtx m, Vec* rot)
{
    const f32 ax = rot->x, ay = rot->y, az = rot->z;   // read before the first store (m may overlap rot)
    euler(m, sinf(ax), cosf(ax), sinf(ay), cosf(ay), sinf(az), cosf(az));
}

// The same matrix with the game's series sin / cos, a zero angle short-cut to (0, 1).
void low_RotMatrix(Mtx m, Vec* rot)
{
    const f32 ax = rot->x, ay = rot->y, az = rot->z;
    const f32 sx = ax == 0.0f ? 0.0f : SINF(ax), cx = ax == 0.0f ? 1.0f : COSF(ax);
    const f32 sy = ay == 0.0f ? 0.0f : SINF(ay), cy = ay == 0.0f ? 1.0f : COSF(ay);
    const f32 sz = az == 0.0f ? 0.0f : SINF(az), cz = az == 0.0f ? 1.0f : COSF(az);
    euler(m, sx, cx, sy, cy, sz, cz);
}

// m = Ry * Rx * Rz (Z applied first).
void RotMatrixZXY(Mtx m, Vec* rot)
{
    Mtx t;
    PSMTXRotRad(m, 'y', rot->y);
    PSMTXRotRad(t, 'x', rot->x);
    PSMTXConcat(m, t, m);
    PSMTXRotRad(t, 'z', rot->z);
    PSMTXConcat(m, t, m);
}

// Cubic Hermite of p[0]..p[1] with tangents v[0]..v[1].
f32 hermite(f32* p, f32* v, f32 t)
{
    const f32 t2 = t * t;
    const f32 t3 = t * t2;
    const f32 h01 = -(t3 + t3) + 3.0f * t2;
    const f32 h11 = t3 - t2;
    const f32 h10 = h11 - t2 + t;
    const f32 h00 = -h01 + 1.0f;
    return p[0] * h00 + p[1] * h01 + v[0] * h10 + v[1] * h11;
}

// n x m floats on the debug heap (the interface the behaviour may call; the engine's own users take a scratch).
f32** malloc_2dim_array_f32(int n, int m)
{
    f32** p = (f32**) MEM_ALLOC(n * sizeof(f32*), 1, 13);
    if (!p) {
        pLog->err(0, 0, "malloc_2dim_array_f32(): Memory Allocation Error!");
        return NULL;
    }
    for (int i = 0; i < n; i++) {
        p[i] = (f32*) MEM_ALLOC(m * sizeof(f32), 1, 13);
        if (!p[i]) {
            pLog->err(0, 0, "malloc_2dim_array_f32(): Memory Allocation Error!");
            for (int j = 0; j < i; j++) Mem_free(p[j]);
            return NULL;
        }
    }
    return p;
}

void free_2dim_array_f32(int n, int m, f32** p)
{
    for (int i = 0; i < n; i++) Mem_free(p[i]);
    Mem_free(p);
}

// B-spline basis of order k + 1 for n control points at t (de Boor-Cox), the knot vector from `knot` (NULL: uniform).
// The table is one (n + k + 1) x (k + 1) block and the knots one row, from a stack scratch when they fit.
int de_Boor_Cox(int n, f32* knot, int k, f32 t, f32* out)
{
    const int m = k + 1, rows = n + m;
    Scratch<f32, 512> tab((unsigned) (rows * m));
    Scratch<f32, 64> qs((unsigned) rows);
    if (!tab.p || !qs.p) {
        pLog->err(0, 0, "de_Boor_Cox(): Memory Allocation Error!");
        return 0;
    }
    f32* B = tab.p;
    f32* q = qs.p;
#define DB(i, j) B[(i) * m + (j)]
    for (int i = 0; i < rows * m; i++) B[i] = 0.0f;
    if (knot) {
        for (int j = 0; j < m; j++) q[j] = knot[0];
        for (int j = m; j < n; j++) q[j] = (knot[j - m] + knot[j]) * 0.5f;
        for (int j = n; j < rows; j++) q[j] = knot[n - 1];
    } else {
        for (int j = 0; j < m; j++) q[j] = 0.0f;
        for (int j = m; j < n; j++) q[j] = (f32) (j - m) + (f32) m * 0.5f;
        for (int j = n; j < rows; j++) q[j] = (f32) (n - 1);
    }
    for (int i = 0; i < n; i++)
        if (q[i] <= t && t < q[i + 1]) DB(i, 0) = 1.0f;
    if (q[rows - 2] <= t && t <= q[rows - 1] + 0.00001f) DB(n - 1, 0) = 1.0f;
    for (int j = 1; j < m; j++)
        for (int i = 0; i < n; i++) {
            DB(i, j) = 0.0f;
            if (q[i + 1] != q[i + j + 1]) DB(i, j) += (q[i + j + 1] - t) * DB(i + 1, j - 1) / (q[i + j + 1] - q[i + 1]);
            if (q[i] != q[i + j]) DB(i, j) += (t - q[i]) * DB(i, j - 1) / (q[i + j] - q[i]);
        }
    for (int i = 0; i < n; i++) out[i] = DB(i, m - 1);
#undef DB
    return 1;
}

// LU decomposition with partial pivoting of the n x n matrix A (row order in ip); the determinant, 0 when singular.
f32 MtxNNLUDecomposition(int n, f32* A, int* ip)
{
    int l = 0;
    for (int i = 0; i < n; i++) ip[i] = i;
    f32 det = 1.0f;
    for (int k = 0; k < n; k++) {
        f32 max = -1.0f;
        for (int i = k; i < n; i++) {
            const f32 v = __builtin_fabsf(A[ip[i] * n + k]);
            if (v > max) max = v, l = i;
        }
        if (l != k) {
            const int j = ip[l];
            ip[l] = ip[k];
            ip[k] = j;
            det = -det;
        }
        max = A[ip[k] * n + k];
        det *= max;
        if (max == 0.0f) {
            pLog->err(0, 0, "Error: Can't calc Inverse Matrix !");
            return 0.0f;
        }
        for (int i = k + 1; i < n; i++) {
            const f32 t = A[ip[i] * n + k] / max;
            A[ip[i] * n + k] = t;
            for (int j = k + 1; j < n; j++) A[ip[i] * n + j] -= t * A[ip[k] * n + j];
        }
    }
    return det;
}

// Inverse of the n x n matrix m into inv; the determinant (0: singular, inv untouched).
f32 MtxNNInverse(int n, f32* m, f32* inv)
{
    Scratch<int, 16> ips((unsigned) n);
    Scratch<f32, 256> lus((unsigned) (n * n));
    if (!ips.p || !lus.p) {
        pLog->err(0, 0, "MtxNNInverse(): Memory allocation error!");
        return 0.0f;
    }
    int* ip = ips.p;
    f32* lu = lus.p;
    __builtin_memcpy(lu, m, n * n * sizeof(f32));
    const f32 det = MtxNNLUDecomposition(n, lu, ip);
    if (det != 0.0f) {
        for (int k = 0; k < n; k++) {
            for (int i = 0; i < n; i++) {
                const int p = ip[i];
                f32 t = (p == k) ? 1.0f : 0.0f;
                for (int j = 0; j < i; j++) t -= lu[p * n + j] * inv[j * n + k];
                inv[i * n + k] = t;
            }
            for (int i = n - 1; i >= 0; i--) {
                const int p = ip[i];
                f32 t = inv[i * n + k];
                for (int j = i + 1; j < n; j++) t -= lu[p * n + j] * inv[j * n + k];
                inv[i * n + k] = t / lu[p * n + i];
            }
        }
    }
    return det;
}

// out = mtx (n x m) * v.
void MtxNNMultVecSR(int n, int m, f32* mtx, f32* v, f32* out)
{
    for (int i = 0; i < n; i++) {
        out[i] = 0.0f;
        for (int j = 0; j < m; j++) out[i] += mtx[m * i + j] * v[j];
    }
}

// p projected along dir onto the plane (plane_p, plane_n).
void OrthographicProjection(Vec* p, Vec* out, Vec* dir, Vec* plane_p, Vec* plane_n)
{
    const shz_vec3_t d = shz_vec3_sub(V(plane_p), V(p));
    f32 s = shz_vec3_dot(V(plane_n), d);
    s /= dot(plane_n, dir);
    put(out, shz_vec3_add(V(p), shz_vec3_scale(V(dir), s)));
}

f32 IPOW(f32 x, int n)
{
    f32 r = 1.0f;
    for (int i = 0; i < n; i++) r *= x;
    return r;
}

// The game's square root: 0 at or below 1e-5.
f32 SQRTF(f32 x)
{
    return x <= 0.00001f ? 0.0f : __builtin_sqrtf(x);
}

// The game's sin and cos: the angle wrapped into [-PI, PI), then the series (cos as sin of x + PI / 2).
f32 SINF(f32 x) { return sin_series(LIMIT_ANGLE(x)); }
f32 COSF(f32 x) { return sin_series(LIMIT_ANGLE(x + 1.5707964f)); }

// Wrap into [-PI, PI) by whole turns, one at a time (the original's loop).
f32 LIMIT_ANGLE(f32 x)
{
    if (x >= PI) {
        do x -= PI2;
        while (x >= PI);
    } else if (x < -PI) {
        do x += PI2;
        while (x < -PI);
    }
    return x;
}

// ==== sub2.cpp ====

// 1 when the XZ point p lies inside the convex quad (corners in order).
int HitCheckPoint4(Vec* p, Vec* quad)
{
    f32 px = p->x - quad[0].x, pz = p->z - quad[0].z;
    f32 ax = quad[1].x - quad[0].x, az = quad[1].z - quad[0].z;
    f32 bx = quad[3].x - quad[0].x, bz = quad[3].z - quad[0].z;
    if (ax * pz > az * px || bx * pz < bz * px) return 0;
    const f32 cx = quad[2].x - quad[0].x, cz = quad[2].z - quad[0].z;
    px -= cx, pz -= cz, ax -= cx, az -= cz, bx -= cx, bz -= cz;
    if (ax * pz < az * px || bx * pz > bz * px) return 0;
    return 1;
}

f32 GetXZAngle(Vec* from, Vec* to) { return LIMIT_ANGLE(atan2f(to->x - from->x, to->z - from->z)); }
f32 GetXYAngle(Vec* from, Vec* to)
{
    const f32 dx = to->x - from->x, dy = to->y - from->y;
    return LIMIT_ANGLE(atan2f(dy, dx));
}
f32 GetXZAngleLocal(Vec* from, Vec* to, f32 ang) { return LIMIT_ANGLE(GetXZAngle(from, to) - ang); }

namespace {
inline f32 dist2(const Vec* v0, const Vec* v1)
{
    const f32 x = v1->x - v0->x, y = v1->y - v0->y, z = v1->z - v0->z;
    return x * x + y * y + z * z;
}
}   // namespace
f32 GetDistance(Vec* v0, Vec* v1) { return dist2(v0, v1); }
f32 GetDistance(Vec& v0, Vec& v1) { return dist2(&v0, &v1); }
f32 GetDistanceXZ(Vec* v0, Vec* v1)
{
    const f32 x = v1->x - v0->x, z = v1->z - v0->z;
    return x * x + z * z;
}

// Turning step toward target from facing ang: the signed yaw difference clamped to +-limit.
f32 Muku(Vec* pos, Vec* target, f32 ang, f32 limit)
{
    limit = turn_limit(limit);
    const f32 d = LIMIT_ANGLE(GetXZAngle(pos, target) - ang);
    if (d > 0.0f) {
        if (d < limit) limit = d;
    } else if (d > -limit) {
        limit = -d;
    }
    return d >= 0.0f ? limit : -limit;
}

// Turning step from ang to target the short way round, clamped to +-limit.
f32 Muku2(f32 ang, f32 target, f32 limit)
{
    limit = turn_limit(limit);
    f32 d = target - ang;
    if (d < 0.0f) d += PI2;
    if (d < PI) {
        if (limit > d) limit = d;
    } else {
        d -= PI2;
        limit = limit > -d ? d : -limit;
    }
    return limit;
}

// Muku2 toward the XZ direction of dir: the double atan2, as the original (the explicit casts keep C++'s float overload,
// which SH4ZAM's <math.h> brings in, from turning it into atan2f: mathtest found 548 of 20000 one step off).
f32 Muku3(Vec* dir, f32 ang, f32 limit) { return Muku2(ang, (f32) atan2((double) dir->x, (double) dir->z), limit); }

// 1 when b lies within +-ang of a's facing.
int Front_check(cModel* a, cModel* b, f32 ang)
{
    const f32 d = GetXZAngleLocal(&a->pos, &b->pos, a->ang.y);
    return !(d < -ang) && !(d > ang);
}
int Front_check(cModel* a, Vec* b, f32 ang)
{
    const f32 d = GetXZAngleLocal(&a->pos, b, a->ang.y);
    return !(d < -ang) && !(d > ang);
}
int Front_check(Vec* a, Vec* b, f32 rot, f32 ang)
{
    const f32 d = GetXZAngleLocal(a, b, rot);
    return !(d < -ang) && !(d > ang);
}

// Moves m by speed given in its own frame.
void AddSpeed(cModel* m, const Vec* speed)
{
    Mtx mtx;
    Vec v;
    low_RotMatrix(mtx, &m->ang);
    PSMTXMultVec(mtx, speed, &v);
    put(&m->pos, shz_vec3_add(V(&m->pos), V(&v)));
}

f32 RootSumSquare3(Vec* v) { return SQRTF(v->x * v->x + v->y * v->y + v->z * v->z); }

f32 GetDistance3(Vec* v0, Vec* v1)
{
    Vec d;
    put(&d, shz_vec3_sub(V(v1), V(v0)));
    return RootSumSquare3(&d);
}

// src rotated by the Euler angles rot (low_RotMatrix).
void RotVector(Vec* src, Vec* rot, Vec* dst)
{
    Mtx mtx;
    low_RotMatrix(mtx, rot);
    PSMTXMultVec(mtx, src, dst);
}

// The 8 corners of a box rotated by rot and moved to pos.
void BoxWorldCalc(Vec* src, Vec* dst, Vec* pos, Vec* rot)
{
    Mtx mtx;
    RotMatrix(mtx, rot);
    TransMatrix(mtx, pos);
    for (int i = 0; i < 8; i++) PSMTXMultVec(mtx, &src[i], &dst[i]);
}

// A world point on the screen with the current camera; 1 when it is in front.
int GetScreenPos(Vec* pos, Vec* scr)
{
    f32 proj[7], vp[6];
    Vec cam;
    CameraCurrentProjection();
    GXGetProjectionv(proj);
    GXGetViewportv(vp);
    GXProject(pos->x, pos->y, pos->z, pG->Cam.v_mat, proj, vp, &scr->x, &scr->y, &scr->z);
    PSMTXMultVec(pG->Cam.v_mat, pos, &cam);
    return cam.z < -0.0f;
}

// The world point under screen position (sx, sy): where the camera ray meets height y (y == 1e8: the scenery hit, else
// the player's height), or the far point 20000 away.
void Get3DPosFrom2D(Vec* out, f32 sx, f32 sy, f32 y)
{
    Camera* cam = &pG->Cam;
    Vec dir, far, hit;
    CamPos2ScrnVec(&dir, sx, sy);
    normalize(&dir, &dir);
    put(&dir, shz_vec3_scale(V(&dir), 20000.0f));
    put(&far, shz_vec3_add(V(&cam->param.pos), V(&dir)));
    if (y == 100000000.0f) {
        if (SatMgr.hitCheck(&cam->param.pos, &far, &hit, 0, 0x40, 0)) {
            *out = hit;
            return;
        }
        y = pPL->pos.y;
    }
    const f32 t = (y - cam->param.pos.y) / (far.y - cam->param.pos.y);
    if (t > 0.0f) put(out, shz_vec3_add(V(&cam->param.pos), shz_vec3_scale(V(&dir), t)));
    else *out = far;
}

// out = pos1 * (1 - t) + pos2 * t.
void PosToPos(Vec* pos1, Vec* pos2, Vec* out, f32 t)
{
    put(out, shz_vec3_add(shz_vec3_scale(V(pos1), 1.0f - t), shz_vec3_scale(V(pos2), t)));
}

// A stick vector (x right, y forward) as a world XZ direction in the camera's heading.
void VecToCamVec(Vec* v, Vec* out)
{
    Mtx mtx;
    Vec t = {0.0f, 0.0f, 1.0f};
    PSMTXMultVecSR(pG->Cam.mat, &t, &t);
    const f32 ang = atan2f(t.x, t.z);
    t.x = v->x;
    t.y = 0.0f;
    t.z = -v->y;
    PSMTXRotRad(mtx, 'y', ang);
    PSMTXMultVecSR(mtx, &t, out);
}

// Does the segment a-b enter the sphere (c, r)? 1 with the entry point in out (a itself when it starts inside).
int LineSphereCrossCk(Vec* a, Vec* b, Vec* c, Vec* out, f32 r)
{
    const f32 r2 = r * r;
    f32 dist = (a->x - c->x) * (a->x - c->x) + (a->y - c->y) * (a->y - c->y) + (a->z - c->z) * (a->z - c->z);
    if (dist < r2) {
        if (out) *out = *a;
        return 1;
    }
    const f32 len2 = (a->x - b->x) * (a->x - b->x) + (a->y - b->y) * (a->y - b->y) + (a->z - b->z) * (a->z - b->z);
    if (len2 <= 0.1f) return 0;
    const shz_vec3_t ab = shz_vec3_sub(V(b), V(a));
    const f32 s = shz_vec3_dot(ab, shz_vec3_sub(V(c), V(a))) / len2;
    const shz_vec3_t p = shz_vec3_add(shz_vec3_scale(ab, s), V(a));   // the closest point of the line to c
    const f32 h2 = (p.x - c->x) * (p.x - c->x) + (p.y - c->y) * (p.y - c->y) + (p.z - c->z) * (p.z - c->z);
    if (h2 >= r2) return 0;
    const f32 h = SQRTF(r2 - h2);
    shz_vec3_t q = shz_vec3_sub(V(a), p);
    q = shz_vec3_add(shz_vec3_scale(q, h / __builtin_sqrtf(shz_vec3_magnitude_sqr(q))), p);   // the entry point
    dist = (a->x - q.x) * (a->x - q.x) + (a->y - q.y) * (a->y - q.y) + (a->z - q.z) * (a->z - q.z);
    if (dist > len2) return 0;
    if (shz_vec3_dot(shz_vec3_sub(V(a), q), shz_vec3_sub(V(a), V(b))) < 0.0f) return 0;
    if (shz_vec3_dot(shz_vec3_sub(V(b), q), shz_vec3_sub(V(b), V(a))) < 0.0f) return 0;
    if (out) put(out, q);
    return 1;
}

// 1 when two spheres overlap.
int SphereHitCk(Vec* p1, Vec* p2, f32 ra, f32 rb)
{
    const shz_vec3_t d = shz_vec3_sub(V(p1), V(p2));
    const f32 r = ra + rb;
    return d.x * d.x + d.y * d.y + d.z * d.z < r * r;
}

// Launch velocity (gravity 20 a frame) that carries a body from `from` to `to` peaking h above the higher end.
void CalcParabolaVector(Vec* out, Vec* from, Vec* to, f32 h)
{
    if (h <= 0.0f) {
        put(out, shz_vec3_sub(V(to), V(from)));
        return;
    }
    h += from->y > to->y ? from->y : to->y;
    f32 t = SQRTF((h - from->y) * 2.0f / 20.0f);
    t += SQRTF((h - to->y) * 2.0f / 20.0f);
    put(out, shz_vec3_scale(shz_vec3_sub(V(to), V(from)), 1.0f / t));
    out->y = SQRTF((h - from->y) * 40.0f);
}

// Distance covered while speed falls by decel a frame to 0.
f32 CalcStopDist(f32 speed, f32 decel)
{
    f32 d = 0.0f;
    do {
        d += speed;
        speed -= decel;
    } while (!(speed <= 0.0f));
    return d;
}

// pos moved dist toward target; 1 (snapped) when it arrives.
int CalcMovePosDist(Vec* pos, Vec* target, f32 dist)
{
    if (dist2(pos, target) <= dist * dist) {
        *pos = *target;
        return 1;
    }
    Vec dir;
    put(&dir, shz_vec3_sub(V(target), V(pos)));
    normalize(&dir, &dir);
    put(pos, shz_vec3_add(V(pos), shz_vec3_scale(V(&dir), dist)));
    return 0;
}
