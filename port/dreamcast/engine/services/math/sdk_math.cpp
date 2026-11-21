// Native SDK math (lane eng-svc5): the matrix, vector and quaternion interface the behaviour calls (the SDK's PSMTX* /
// PSVEC* entry points and their C_* names), as engine code. Write-up: docs/engine/SERVICES.md section 34.
//
// The behaviour calls the PS* names; each is its body here (no forwarder hop: the old port's platform/mtx.cpp and the
// image's host/e1_math.cpp sent every PS* call on to a C_* body in another unit). The C_* names, which the SDK's own
// callers and a few engine files use, are the same bodies. Every result is formed with the operations of the SDK's C
// reference code in their order, including its "0 +" terms (they turn a -0 sum into +0), so on the PC the results are
// bit-identical with the reference build's (sdktest checks every function on random inputs). Vector arithmetic is
// SH4ZAM's where its operation is the same (add, subtract, scale, cross, dot, squared length); roots are the exact IEEE
// root; sin, cos, tan and acos are the engine's libm.
#include "types.h"
#include "sh4zam/shz_vector.h"

typedef f32 Mtx[3][4];
typedef f32 Mtx44[4][4];
struct Vec { f32 x, y, z; };
struct Quaternion { f32 x, y, z, w; };

namespace {
inline shz_vec3_t V(const Vec* v) { return shz_vec3_init(v->x, v->y, v->z); }
inline void put(Vec* d, shz_vec3_t v) { d->x = v.x, d->y = v.y, d->z = v.z; }
inline void copy(const Mtx s, Mtx d) { __builtin_memcpy(d, s, sizeof(Mtx)); }
}   // namespace

extern "C" {

int sdk_math_control;   // re4ref control "sdkconcat": PSMTXConcat's translation column without a's own translation

// ---- matrices (3 x 4) ----
void PSMTXIdentity(Mtx m)
{
    for (int r = 0; r < 3; r++)
        for (int c = 0; c < 4; c++) m[r][c] = r == c ? 1.0f : 0.0f;
}
void PSMTXCopy(const Mtx s, Mtx d)
{
    if (s != d) copy(s, d);
}
// ab = a * b (b applied first); a and b may be ab
void PSMTXConcat(const Mtx a, const Mtx b, Mtx ab)
{
    Mtx t;
    for (int r = 0; r < 3; r++) {
        for (int c = 0; c < 3; c++) t[r][c] = 0.0f + a[r][2] * b[2][c] + ((a[r][0] * b[0][c]) + (a[r][1] * b[1][c]));
        t[r][3] = (sdk_math_control == 1 ? 0.0f : a[r][3]) + (a[r][2] * b[2][3] + (a[r][0] * b[0][3] + (a[r][1] * b[1][3])));
    }
    copy(t, ab);
}
void PSMTXTranspose(const Mtx s, Mtx d)
{
    Mtx t;
    for (int r = 0; r < 3; r++) {
        for (int c = 0; c < 3; c++) t[r][c] = s[c][r];
        t[r][3] = 0.0f;
    }
    copy(t, d);
}
// the inverse of the affine matrix (cofactors over the determinant); 0 and inv untouched when singular
u32 PSMTXInverse(const Mtx s, Mtx inv)
{
    f32 det = ((((s[2][1] * (s[0][2] * s[1][0])) + ((s[2][2] * (s[0][0] * s[1][1])) + (s[2][0] * (s[0][1] * s[1][2])))) -
                (s[0][2] * (s[2][0] * s[1][1]))) -
               (s[2][2] * (s[1][0] * s[0][1]))) -
              (s[1][2] * (s[0][0] * s[2][1]));
    if (0.0f == det) return 0;
    det = 1.0f / det;
    Mtx m;
    m[0][0] = det * +((s[1][1] * s[2][2]) - (s[2][1] * s[1][2]));
    m[0][1] = det * -((s[0][1] * s[2][2]) - (s[2][1] * s[0][2]));
    m[0][2] = det * +((s[0][1] * s[1][2]) - (s[1][1] * s[0][2]));
    m[1][0] = det * -((s[1][0] * s[2][2]) - (s[2][0] * s[1][2]));
    m[1][1] = det * +((s[0][0] * s[2][2]) - (s[2][0] * s[0][2]));
    m[1][2] = det * -((s[0][0] * s[1][2]) - (s[1][0] * s[0][2]));
    m[2][0] = det * +((s[1][0] * s[2][1]) - (s[2][0] * s[1][1]));
    m[2][1] = det * -((s[0][0] * s[2][1]) - (s[2][0] * s[0][1]));
    m[2][2] = det * +((s[0][0] * s[1][1]) - (s[1][0] * s[0][1]));
    for (int r = 0; r < 3; r++) m[r][3] = ((-m[r][0] * s[0][3]) - (m[r][1] * s[1][3])) - (m[r][2] * s[2][3]);
    copy(m, inv);
    return 1;
}
void PSMTXRotTrig(Mtx m, char axis, f32 sinA, f32 cosA)
{
    int a;
    switch (axis) {
    case 'x': case 'X': a = 0; break;
    case 'y': case 'Y': a = 1; break;
    case 'z': case 'Z': a = 2; break;
    default: return;   // m untouched, as the SDK
    }
    PSMTXIdentity(m);
    const int i = (a + 1) % 3, j = (a + 2) % 3;   // the plane the rotation turns: (y, z), (z, x), (x, y)
    m[i][i] = cosA, m[i][j] = -sinA;
    m[j][i] = sinA, m[j][j] = cosA;
}
void PSMTXRotRad(Mtx m, char axis, f32 rad) { PSMTXRotTrig(m, axis, sinf(rad), cosf(rad)); }
void PSVECNormalize(const Vec* src, Vec* unit);
void PSMTXRotAxisRad(Mtx m, const Vec* axis, f32 rad)
{
    const f32 s = sinf(rad), c = cosf(rad), t = 1.0f - c;
    Vec n;
    PSVECNormalize(axis, &n);
    const f32 x = n.x, y = n.y, z = n.z;
    m[0][0] = c + (t * (x * x));
    m[0][1] = (y * (t * x)) - (s * z);
    m[0][2] = (z * (t * x)) + (s * y);
    m[0][3] = 0.0f;
    m[1][0] = (y * (t * x)) + (s * z);
    m[1][1] = c + (t * (y * y));
    m[1][2] = (z * (t * y)) - (s * x);
    m[1][3] = 0.0f;
    m[2][0] = (z * (t * x)) - (s * y);
    m[2][1] = (z * (t * y)) + (s * x);
    m[2][2] = c + (t * (z * z));
    m[2][3] = 0.0f;
}
void PSMTXTrans(Mtx m, f32 x, f32 y, f32 z)
{
    PSMTXIdentity(m);
    m[0][3] = x, m[1][3] = y, m[2][3] = z;
}
void PSMTXTransApply(const Mtx s, Mtx d, f32 x, f32 y, f32 z)
{
    if (s != d)
        for (int r = 0; r < 3; r++) d[r][0] = s[r][0], d[r][1] = s[r][1], d[r][2] = s[r][2];
    d[0][3] = s[0][3] + x;
    d[1][3] = s[1][3] + y;
    d[2][3] = s[2][3] + z;
}
void PSMTXScale(Mtx m, f32 x, f32 y, f32 z)
{
    PSMTXIdentity(m);
    m[0][0] = x, m[1][1] = y, m[2][2] = z;
}
void PSMTXQuat(Mtx m, const Quaternion* q)
{
    const f32 s = 2.0f / ((q->w * q->w) + ((q->z * q->z) + ((q->x * q->x) + (q->y * q->y))));
    const f32 xs = q->x * s, ys = q->y * s, zs = q->z * s;
    const f32 wx = q->w * xs, wy = q->w * ys, wz = q->w * zs;
    const f32 xx = q->x * xs, xy = q->x * ys, xz = q->x * zs;
    const f32 yy = q->y * ys, yz = q->y * zs, zz = q->z * zs;
    m[0][0] = 1.0f - (yy + zz), m[0][1] = xy - wz, m[0][2] = xz + wy, m[0][3] = 0.0f;
    m[1][0] = xy + wz, m[1][1] = 1.0f - (xx + zz), m[1][2] = yz - wx, m[1][3] = 0.0f;
    m[2][0] = xz - wy, m[2][1] = yz + wx, m[2][2] = 1.0f - (xx + yy), m[2][3] = 0.0f;
}
void PSMTXMultVec(const Mtx m, const Vec* s, Vec* d)
{
    Vec t;
    t.x = m[0][3] + ((m[0][2] * s->z) + ((m[0][0] * s->x) + (m[0][1] * s->y)));
    t.y = m[1][3] + ((m[1][2] * s->z) + ((m[1][0] * s->x) + (m[1][1] * s->y)));
    t.z = m[2][3] + ((m[2][2] * s->z) + ((m[2][0] * s->x) + (m[2][1] * s->y)));
    *d = t;
}
void PSMTXMultVecArray(const Mtx m, const Vec* s, Vec* d, u32 count)
{
    for (u32 i = 0; i < count; i++) PSMTXMultVec(m, s + i, d + i);
}
void PSMTXMultVecSR(const Mtx m, const Vec* s, Vec* d)
{
    Vec t;
    t.x = (m[0][2] * s->z) + ((m[0][0] * s->x) + (m[0][1] * s->y));
    t.y = (m[1][2] * s->z) + ((m[1][0] * s->x) + (m[1][1] * s->y));
    t.z = (m[2][2] * s->z) + ((m[2][0] * s->x) + (m[2][1] * s->y));
    *d = t;
}
// the 4 x 4 transform with the divide by w (w == 0: no divide)
void PSMTX44MultVec(const Mtx44 m, const Vec* s, Vec* d)
{
    const f32 x = s->x, y = s->y, z = s->z;
    const f32 ox = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3];
    const f32 oy = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3];
    const f32 oz = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3];
    f32 w = m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3];
    w = w == 0.0f ? 1.0f : 1.0f / w;
    d->x = ox * w, d->y = oy * w, d->z = oz * w;
}

// ---- vectors ----
void PSVECAdd(const Vec* a, const Vec* b, Vec* ab) { put(ab, shz_vec3_add(V(a), V(b))); }
void PSVECSubtract(const Vec* a, const Vec* b, Vec* ab) { put(ab, shz_vec3_sub(V(a), V(b))); }
void PSVECScale(const Vec* s, Vec* d, f32 k) { put(d, shz_vec3_scale(V(s), k)); }
f32 PSVECSquareMag(const Vec* v) { return shz_vec3_magnitude_sqr(V(v)); }
f32 PSVECMag(const Vec* v) { return __builtin_sqrtf(shz_vec3_magnitude_sqr(V(v))); }
f32 PSVECDotProduct(const Vec* a, const Vec* b) { return shz_vec3_dot(V(a), V(b)); }
void PSVECCrossProduct(const Vec* a, const Vec* b, Vec* d) { put(d, shz_vec3_cross(V(a), V(b))); }
f32 PSVECSquareDistance(const Vec* a, const Vec* b) { return shz_vec3_magnitude_sqr(shz_vec3_sub(V(a), V(b))); }
f32 PSVECDistance(const Vec* a, const Vec* b) { return __builtin_sqrtf(PSVECSquareDistance(a, b)); }
void PSVECNormalize(const Vec* src, Vec* unit)
{
    const shz_vec3_t v = V(src);
    put(unit, shz_vec3_scale(v, 1.0f / __builtin_sqrtf(shz_vec3_magnitude_sqr(v))));
}

// ---- camera matrices ----
void C_MTXLookAt(Mtx m, const Vec* camPos, const Vec* camUp, const Vec* target)
{
    Vec look, right, up;
    put(&look, shz_vec3_sub(V(camPos), V(target)));
    PSVECNormalize(&look, &look);
    PSVECCrossProduct(camUp, &look, &right);
    PSVECNormalize(&right, &right);
    PSVECCrossProduct(&look, &right, &up);
    const Vec* rows[3] = {&right, &up, &look};
    for (int r = 0; r < 3; r++) {
        const Vec* v = rows[r];
        m[r][0] = v->x, m[r][1] = v->y, m[r][2] = v->z;
        m[r][3] = -((camPos->z * v->z) + ((camPos->x * v->x) + (camPos->y * v->y)));
    }
}
void C_MTXOrtho(Mtx44 m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 f)
{
    __builtin_memset(m, 0, sizeof(Mtx44));
    f32 k = 1.0f / (r - l);
    m[0][0] = 2.0f * k;
    m[0][3] = k * -(r + l);
    k = 1.0f / (t - b);
    m[1][1] = 2.0f * k;
    m[1][3] = k * -(t + b);
    k = 1.0f / (f - n);
    m[2][2] = -1.0f * k;
    m[2][3] = -f * k;
    m[3][3] = 1.0f;
}
void C_MTXPerspective(Mtx44 m, f32 fovY, f32 aspect, f32 n, f32 f)
{
    __builtin_memset(m, 0, sizeof(Mtx44));
    const f32 cot = 1.0f / tanf((0.5f * fovY) * 0.01745329252f);
    m[0][0] = cot / aspect;
    m[1][1] = cot;
    const f32 k = 1.0f / (f - n);
    m[2][2] = -n * k;
    m[2][3] = k * -(f * n);
    m[3][2] = -1.0f;
}

// ---- quaternions ----
// the rotation of the upper 3 x 3 as a quaternion (the largest diagonal term picks the stable branch)
void C_QUATMtx(Quaternion* r, const Mtx m)
{
    const f32 tr = m[0][0] + m[1][1] + m[2][2];
    if (tr > 0.0f) {
        f32 s = sqrtf(tr + 1.0f);
        r->w = s * 0.5f;
        s = 0.5f / s;
        r->x = (m[2][1] - m[1][2]) * s;
        r->y = (m[0][2] - m[2][0]) * s;
        r->z = (m[1][0] - m[0][1]) * s;
        return;
    }
    static const int next[3] = {1, 2, 0};
    int i = m[1][1] > m[0][0] ? 1 : 0;
    if (m[2][2] > m[i][i]) i = 2;
    const int j = next[i], k = next[j];
    f32 q[3];
    f32 s = sqrtf((m[i][i] - (m[j][j] + m[k][k])) + 1.0f);
    q[i] = s * 0.5f;
    if (s != 0.0f) s = 0.5f / s;
    r->w = (m[k][j] - m[j][k]) * s;
    q[j] = (m[i][j] + m[j][i]) * s;
    q[k] = (m[i][k] + m[k][i]) * s;
    r->x = q[0], r->y = q[1], r->z = q[2];
}
void C_QUATSlerp(const Quaternion* p, const Quaternion* q, Quaternion* r, f32 t)
{
    f32 cs = p->x * q->x + p->y * q->y + p->z * q->z + p->w * q->w;
    f32 tq = 1.0f, tp;
    if (cs < 0.0f) cs = -cs, tq = -tq;
    if (cs <= 0.99999f) {
        const f32 th = acosf(cs), sn = sinf(th);
        tp = sinf((1.0f - t) * th) / sn;
        tq *= sinf(t * th) / sn;
    } else {
        tp = 1.0f - t;
        tq *= t;
    }
    r->x = (tp * p->x) + (tq * q->x);
    r->y = (tp * p->y) + (tq * q->y);
    r->z = (tp * p->z) + (tq * q->z);
    r->w = (tp * p->w) + (tq * q->w);
}

// ---- the C_* names of the same bodies ----
#define SAME(ret, name, params, args) ret C_##name params { return PS##name args; }
SAME(void, MTXIdentity, (Mtx m), (m))
SAME(void, MTXCopy, (const Mtx s, Mtx d), (s, d))
SAME(void, MTXConcat, (const Mtx a, const Mtx b, Mtx ab), (a, b, ab))
SAME(void, MTXTranspose, (const Mtx s, Mtx d), (s, d))
SAME(u32, MTXInverse, (const Mtx s, Mtx d), (s, d))
SAME(void, MTXRotRad, (Mtx m, char axis, f32 rad), (m, axis, rad))
SAME(void, MTXRotTrig, (Mtx m, char axis, f32 s, f32 c), (m, axis, s, c))
SAME(void, MTXRotAxisRad, (Mtx m, const Vec* axis, f32 rad), (m, axis, rad))
SAME(void, MTXTrans, (Mtx m, f32 x, f32 y, f32 z), (m, x, y, z))
SAME(void, MTXTransApply, (const Mtx s, Mtx d, f32 x, f32 y, f32 z), (s, d, x, y, z))
SAME(void, MTXScale, (Mtx m, f32 x, f32 y, f32 z), (m, x, y, z))
SAME(void, MTXQuat, (Mtx m, const Quaternion* q), (m, q))
SAME(void, MTXMultVec, (const Mtx m, const Vec* s, Vec* d), (m, s, d))
SAME(void, MTXMultVecArray, (const Mtx m, const Vec* s, Vec* d, u32 n), (m, s, d, n))
SAME(void, MTXMultVecSR, (const Mtx m, const Vec* s, Vec* d), (m, s, d))
SAME(void, MTX44MultVec, (const Mtx44 m, const Vec* s, Vec* d), (m, s, d))
SAME(void, VECAdd, (const Vec* a, const Vec* b, Vec* ab), (a, b, ab))
SAME(void, VECSubtract, (const Vec* a, const Vec* b, Vec* ab), (a, b, ab))
SAME(void, VECScale, (const Vec* s, Vec* d, f32 k), (s, d, k))
SAME(void, VECNormalize, (const Vec* s, Vec* d), (s, d))
SAME(f32, VECSquareMag, (const Vec* v), (v))
SAME(f32, VECMag, (const Vec* v), (v))
SAME(f32, VECDotProduct, (const Vec* a, const Vec* b), (a, b))
SAME(void, VECCrossProduct, (const Vec* a, const Vec* b, Vec* d), (a, b, d))
SAME(f32, VECSquareDistance, (const Vec* a, const Vec* b), (a, b))
SAME(f32, VECDistance, (const Vec* a, const Vec* b), (a, b))
#undef SAME

}   // extern "C"
