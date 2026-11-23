/*! \file
 *  \brief   The cloth chain step on SH4ZAM, in one pass (cloth_kernel.h).
 *  \ingroup engine_cloth
 *
 *  Every stage is the original's arithmetic (game/pendulum.cpp's PenClothMove / PenClothMove3 and the volume tests,
 *  through the C library's VECNormalize, PSVECDotProduct, PSMTXRotAxisRad, PSMTXMultVec(SR), PSMTXConcat), in its
 *  order of operations, written on SH4ZAM's primitives: on the SW back-end each primitive forms its result exactly as
 *  the C library does; on the SH4 they are FIPR, FSRRA and FSCA.
 *
 *  \author lane eng-svc3 (RE4 Dreamcast engine line)
 *  \copyright MIT
 */
#include "cloth_kernel.h"
#include "sh4zam/shz_scalar.h"
#include "sh4zam/shz_vector.h"
#include "sh4zam/shz_trig.h"
#include <math.h>

_Static_assert(sizeof(ClothKLink) == 64, "ClothKLink is ClothLink: 64 B");
_Static_assert(sizeof(ClothKCold) == 48, "ClothKCold is ClothCold: 48 B");
_Static_assert(sizeof(ClothKVol) == 0x84, "ClothKVol is PenAt: 0x84 B");

ClothKCounters cloth_k_cnt;
int cloth_k_control_bound;

#define K_PI 3.1415927f
#define K_PI_LIM (3.1415927f - 0.01f)

// ---------------------------------------------------------------------------------------------------------------
// primitives
SHZ_FORCE_INLINE ClothKVec k_vec(float x, float y, float z) {
    ClothKVec v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}
SHZ_FORCE_INLINE ClothKVec k_add(ClothKVec a, ClothKVec b) { return k_vec(a.x + b.x, a.y + b.y, a.z + b.z); }
SHZ_FORCE_INLINE ClothKVec k_sub(ClothKVec a, ClothKVec b) { return k_vec(a.x - b.x, a.y - b.y, a.z - b.z); }
SHZ_FORCE_INLINE ClothKVec k_scale(ClothKVec a, float k) { return k_vec(a.x * k, a.y * k, a.z * k); }
SHZ_FORCE_INLINE int k_zero(ClothKVec a) { return a.x == 0.0f && a.y == 0.0f && a.z == 0.0f; }
//! x * x + y * y + z * z (FIPR on the SH4)
SHZ_FORCE_INLINE float k_mag2(ClothKVec a) { return shz_mag_sqr3f(a.x, a.y, a.z); }
//! PSVECDotProduct (FIPR on the SH4)
SHZ_FORCE_INLINE float k_dot(ClothKVec a, ClothKVec b) { return shz_dot6f(a.x, a.y, a.z, b.x, b.y, b.z); }
//! VECNormalize / PSVECNormalize: a times the reciprocal square root of its magnitude (FSRRA on the SH4)
SHZ_FORCE_INLINE ClothKVec k_normalize(ClothKVec a) {
    cloth_k_cnt.normalize++;
    return k_scale(a, shz_inv_sqrtf_fsrra(k_mag2(a)));
}
//! SQRTF (math_sub.cpp): 0 at or under 0.00001
SHZ_FORCE_INLINE float k_sqrt(float x) {
    cloth_k_cnt.sqrt++;
    if (x <= 0.00001f) return 0.0f;
#if SHZ_BACKEND == SHZ_SH4
    return shz_sqrtf_fsrra(x);
#else
    return sqrtf(x);
#endif
}
SHZ_FORCE_INLINE float k_acos(float x) {
    cloth_k_cnt.acos++;
#if SHZ_BACKEND == SHZ_SH4
    return shz_acosf(x);
#else
    return acosf(x);
#endif
}
SHZ_FORCE_INLINE float k_asin(float x) {
#if SHZ_BACKEND == SHZ_SH4
    return shz_asinf(x);
#else
    return asinf(x);
#endif
}
//! PSVECCrossProduct (shz_vec3_cross forms each component as the C library)
SHZ_FORCE_INLINE ClothKVec k_cross(ClothKVec a, ClothKVec b) {
    shz_vec3_t c = shz_vec3_cross(shz_vec3_init(a.x, a.y, a.z), shz_vec3_init(b.x, b.y, b.z));
    return k_vec(c.x, c.y, c.z);
}
//! PSMTXMultVecSR: the rotation part times a vector (one FIPR a row on the SH4)
SHZ_FORCE_INLINE ClothKVec k_mul_sr(const float* m, ClothKVec v) {
    return k_vec(shz_dot6f(m[0], m[1], m[2], v.x, v.y, v.z), shz_dot6f(m[4], m[5], m[6], v.x, v.y, v.z),
                 shz_dot6f(m[8], m[9], m[10], v.x, v.y, v.z));
}
//! PSMTXMultVec: the translation added last, as the C library adds it
SHZ_FORCE_INLINE ClothKVec k_mul(const float* m, ClothKVec v) {
    ClothKVec r = k_mul_sr(m, v);
    return k_vec(m[3] + r.x, m[7] + r.y, m[11] + r.z);
}
//! PSMTXRotAxisRad (3x4, translation 0)
static void k_rot_axis(float* m, ClothKVec axis, float rad) {
    float s, c;
    cloth_k_cnt.rotations++;
#if SHZ_BACKEND == SHZ_SH4
    shz_sincos_t sc = shz_sincosf(rad);
    s = sc.sin;
    c = sc.cos;
#else
    s = sinf(rad);
    c = cosf(rad);
#endif
    const float t = 1 - c;
    const ClothKVec n = k_normalize(axis);
    const float x = n.x, y = n.y, z = n.z;
    const float xSq = (x * x), ySq = (y * y), zSq = (z * z);
    m[0] = (c + (t * xSq));
    m[1] = (y * (t * x)) - (s * z);
    m[2] = (z * (t * x)) + (s * y);
    m[3] = 0;
    m[4] = ((y * (t * x)) + (s * z));
    m[5] = (c + (t * ySq));
    m[6] = ((z * (t * y)) - (s * x));
    m[7] = 0;
    m[8] = ((z * (t * x)) - (s * y));
    m[9] = ((z * (t * y)) + (s * x));
    m[10] = (c + (t * zSq));
    m[11] = 0;
}
//! b = a x b (PSMTXConcat with the result in b), 3x4
static void k_concat_into(const float* a, float* b) {
    float m[12];
    for (int i = 0; i < 3; i++) {
        const float* r = a + 4 * i;
        m[4 * i + 0] = 0 + r[2] * b[8] + ((r[0] * b[0]) + (r[1] * b[4]));
        m[4 * i + 1] = 0 + r[2] * b[9] + ((r[0] * b[1]) + (r[1] * b[5]));
        m[4 * i + 2] = 0 + r[2] * b[10] + ((r[0] * b[2]) + (r[1] * b[6]));
        m[4 * i + 3] = r[3] + (r[2] * b[11] + (r[0] * b[3] + (r[1] * b[7])));
    }
    for (int k = 0; k < 12; k++) b[k] = m[k];
}

// ---------------------------------------------------------------------------------------------------------------
// the volume tests (pendulum.cpp penClothAtCk, penClothAtCkBorder, penClothAtCkParallel)
//
// Lane eng-cloth1: the plain and the parallel test read the tick's ClothKSph table (k_prep: centres and radii, 16 B a
// volume, in the list's order) instead of the 0x84-byte volume records. Every value a test computes is the original's,
// formed by the same operations in the same order; only work whose result is never used is left out.

// The tick's volume table (a chain has at most 32 volumes: cloth.cpp's build).
static ClothKSph k_sph[32];
static void k_prep(ClothKStep* s) {
    s->sph = k_sph;
    s->cylMask = 0;
    if (!s->vol) return;
    if (s->nVol > 32) s->nVol = 32;
    for (uint32_t i = 0; i < s->nVol; i++) {
        const ClothKVol* a = &s->vol[i];
        k_sph[i].x = a->p0.x;
        k_sph[i].y = a->p0.y;
        k_sph[i].z = a->p0.z;
        k_sph[i].r = a->r;
        if (a->type != 0) s->cylMask |= 1u << i;
    }
}

// penClothAtCk: a link inside a volume is put back on its surface. The link's length (a square root) is taken at the
// first hit instead of before the loop: the same value, made only when a hit reads it.
SHZ_FORCE_INLINE int plain_one(ClothKVec* pos, const ClothKVec* up, const ClothKSph* a, float* len, int hit) {
    float mtx[12];
    ClothKVec v = k_vec(pos->x - a->x, pos->y - a->y, pos->z - a->z);
    const float dd = v.x * v.x + v.y * v.y + v.z * v.z;
    const float rr = a->r * a->r;
    if (!(dd < rr)) return 0;
    if (!hit) *len = k_sqrt(k_mag2(k_sub(*up, *pos)));   // GetDistance3(pos, up): pos as the call found it
    const float L = *len;
    const ClothKVec c = k_vec(a->x, a->y, a->z);
    v = k_sub(c, *up);
    const float d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    const float ang = k_acos((rr - L * L - d * d) / (L * -2.0f * d));
    if (ang > 0.01f && ang < K_PI_LIM) {
        const ClothKVec v2 = k_sub(*pos, *up);
        k_rot_axis(mtx, k_cross(v, v2), ang);
        v = k_normalize(v);
        v = k_scale(v, L);
        v = k_mul(mtx, v);
        *pos = k_add(*up, v);
    } else {
        v = k_normalize(v);
        v = k_scale(v, a->r + 1.0f);
        *pos = k_add(c, v);
    }
    cloth_k_cnt.vol_hits++;
    return 1;
}
static int at_ck_plain(const ClothKStep* s, ClothKVec* pos, const ClothKVec* up) {
    if (!s->vol) return 0;
    const ClothKSph* a = s->sph;
    const uint32_t n = s->nVol;
    float len = 0.0f;
    int hit = 0;
    for (uint32_t i = 0; i < n; i++, a++) hit |= plain_one(pos, up, a, &len, hit);
    cloth_k_cnt.vol_tests += n;
    return hit;
}

int cloth_k_at_ck_border(ClothKVec* pos, const ClothKVec* up, const ClothKVol* a, uint32_t n) {
    if (!a) return 0;
    float mtx[12];
    ClothKVec d = k_sub(*pos, *up), pu, w, tmp;
    const float lenSq = d.x * d.x + d.y * d.y + d.z * d.z;
    if (lenSq == 0.0f) return 0;
    const float invLenSq = 1.0f / lenSq;
    const float len = k_sqrt(lenSq);
    int ret = 0;
    for (uint32_t i = 0; i < n; i++, a++) {
        if (a->type != 0) continue;
        cloth_k_cnt.vol_tests++;
        w.x = pos->x - a->p0.x;
        w.y = pos->y - a->p0.y;
        w.z = pos->z - a->p0.z;
        d.x = pos->x - up->x;
        d.y = pos->y - up->y;
        d.z = pos->z - up->z;
        const float wSq = w.x * w.x + w.y * w.y + w.z * w.z;
        pu.x = a->p0.x - up->x;
        pu.y = a->p0.y - up->y;
        pu.z = a->p0.z - up->z;
        if (pu.x == 0.0f && pu.y == 0.0f && pu.z == 0.0f) pu.y = 1.0f;
        const float puSq = pu.x * pu.x + pu.y * pu.y + pu.z * pu.z;
        const float rr = a->r * a->r;
        if (puSq < rr) continue;
        if (wSq > rr) {
            if (puSq > (len + a->r) * (len + a->r)) continue;
            w.x = a->p0.x - up->x;
            w.y = a->p0.y - up->y;
            w.z = a->p0.z - up->z;
            float t = w.x * d.x + w.y * d.y + w.z * d.z;
            t *= invLenSq;
            if (t < 0.0f) continue;
            if (t > 1.0f) continue;
            w.x = d.x * t + up->x - a->p0.x;
            w.y = d.y * t + up->y - a->p0.y;
            w.z = d.z * t + up->z - a->p0.z;
            if (w.x * w.x + w.y * w.y + w.z * w.z > a->r * a->r) continue;
        }
        if (puSq - a->r * a->r > lenSq) {
            w.x = a->p0.x - up->x;
            w.y = a->p0.y - up->y;
            w.z = a->p0.z - up->z;
            const float rad = a->r + 0.0001f;
            const float dd = k_sqrt(w.x * w.x + w.y * w.y + w.z * w.z);
            const float ang = k_acos((rad * rad - len * len - dd * dd) / (len * -2.0f * dd));
            if (ang > 0.01f && ang < K_PI_LIM) {
                tmp.x = pos->x - up->x;
                tmp.y = pos->y - up->y;
                tmp.z = pos->z - up->z;
                k_rot_axis(mtx, k_cross(w, tmp), ang);
                w = k_normalize(w);
                w.x *= len;
                w.y *= len;
                w.z *= len;
                w = k_mul(mtx, w);
                pos->x = up->x + w.x;
                pos->y = up->y + w.y;
                pos->z = up->z + w.z;
            } else {
                w = k_normalize(w);
                w.x *= rad;
                w.y *= rad;
                w.z *= rad;
                pos->x = a->p0.x + w.x;
                pos->y = a->p0.y + w.y;
                pos->z = a->p0.z + w.z;
            }
        } else {
            const float dd = k_sqrt(puSq);
            const float ang = k_asin(a->r / dd) + 0.0001f;
            k_rot_axis(mtx, k_cross(pu, d), ang);
            w = k_normalize(pu);
            w.x *= len;
            w.y *= len;
            w.z *= len;
            w = k_mul_sr(mtx, w);
            tmp.x = up->x + w.x;
            tmp.y = up->y + w.y;
            tmp.z = up->z + w.z;
            *pos = tmp;
        }
        ret = 1;
        cloth_k_cnt.vol_hits++;
    }
    return ret;
}

// penClothAtCkParallel, one volume: the original's test of the pair (p0, p1) against volume a, on the call's set-up
// (d, nd, lenSq, invLenSq as the original makes them). Out of line: the scan below stays in registers.
typedef struct ParSet {
    ClothKVec d, nd;
    float lenSq, invLenSq;
} ParSet;
static __attribute__((noinline)) void par_one(ClothKVec* P0, ClothKVec* P1, const ParSet* ps, const ClothKVol* a) {
    ClothKVec p0 = *P0, p1 = *P1;
    const ClothKVec d = ps->d, nd = ps->nd;
    const float lenSq = ps->lenSq, invLenSq = ps->invLenSq;
    if (a->type == 0) {
        ClothKVec v;
        const float rr = a->r * a->r;
        float dot = (a->p0.x - p1.x) * d.x + (a->p0.y - p1.y) * d.y;
        dot += (a->p0.z - p1.z) * d.z;
        const float t = dot * invLenSq;
        v.x = nd.x * t + p1.x - a->p0.x;
        v.y = nd.y * t + p1.y - a->p0.y;
        v.z = nd.z * t + p1.z - a->p0.z;
        float push = v.x * v.x + v.y * v.y + v.z * v.z;
        if (push >= rr) return;
        const float ex = a->p0.x - p1.x, ey = a->p0.y - p1.y, ez = a->p0.z - p1.z;
        float d1 = ex * ex + ey * ey;
        d1 += ez * ez;
        float d0 = (a->p0.x - p0.x) * (a->p0.x - p0.x) + (a->p0.y - p0.y) * (a->p0.y - p0.y);
        d0 += (a->p0.z - p0.z) * (a->p0.z - p0.z);
        if (d1 > rr && d0 > rr) {
            if (dot < 0.0f) return;
            if (dot >= lenSq) return;
        }
        push = a->r - k_sqrt(push);
        if (v.x == 0.0f && v.y == 0.0f && v.z == 0.0f) v.y = 1.0f;
        v = k_normalize(v);
        v.x *= push;
        v.y *= push;
        v.z *= push;
        p1.x += v.x;
        p1.y += v.y;
        p1.z += v.z;
        p0.x += v.x;
        p0.y += v.y;
        p0.z += v.z;
        cloth_k_cnt.vol_hits++;
    } else {
        ClothKVec lp1 = k_mul(&a->inv[0][0], p1), lp0 = k_mul(&a->inv[0][0], p0), ld, tmp, q;
        const float l1 = lp1.x * lp1.x + lp1.z * lp1.z;
        const float l0 = lp0.x * lp0.x + lp0.z * lp0.z;
        ld.x = lp0.x - lp1.x;
        ld.y = lp0.y - lp1.y;
        ld.z = lp0.z - lp1.z;
        tmp = ld;
        ld.y = 0.0f;
        const float dot = (-lp1.x) * ld.x + (-lp1.z) * ld.z;
        const float ldSq = ld.x * ld.x + ld.z * ld.z;
        const float rr = a->r * a->r;
        if (l1 > rr && l0 > rr) {
            if (dot < 0.0f) return;
            if (dot >= ldSq) return;
        }
        const float t = dot / ldSq;
        if (ld.x == 0.0f && ld.z == 0.0f) ld.x = 1.0f;
        tmp = k_normalize(tmp);
        q.x = tmp.x * t + lp1.x;
        q.y = tmp.y * t + lp1.y;
        q.z = tmp.z * t + lp1.z;
        if (q.y < 0.0f) return;
        if (q.y > a->len) return;
        q.y = 0.0f;
        float push = q.x * q.x + q.z * q.z;
        if (push >= a->r * a->r) return;
        push = a->r - k_sqrt(push);
        if (q.x == 0.0f && q.y == 0.0f && q.z == 0.0f) return;
        q = k_normalize(q);
        q.x *= push;
        q.y *= push;
        q.z *= push;
        lp1.x += q.x;
        lp1.y += q.y;
        lp1.z += q.z;
        lp0.x += q.x;
        lp0.y += q.y;
        lp0.z += q.z;
        p1 = k_mul(&a->mat[0][0], lp1);
        p0 = k_mul(&a->mat[0][0], lp0);
        cloth_k_cnt.vol_hits++;
    }
    *P1 = p1;
    *P0 = p0;
}

// penClothAtCkParallel: the pair (pos, up) pushed out of each volume in turn. The original tests every volume in full;
// here a sphere whose centre is out of reach of the pair is passed over (it is never a hit, and a volume that does not
// hit changes nothing), and the call's set-up (a normalisation, a square root, a division) is made only once a volume
// is in reach. Every volume tested is tested by the original's arithmetic on the original's values (par_one).
//
// The reach bound. Let c be the centre, r the radius, p1 the upper end, d = p0 - p1 (len its length), nd = d / len,
// t = dot(c - p1, d) / len^2 and q = p1 + nd t (the original's tested point; |q - p1| = |t|). The pair moves only when
// |q - c| < r and (0 <= t < 1, or p1 within r of c, or p0 within r of c):
//   - 0 <= t < 1:      |c - p1| <= |c - q| + |q - p1| < r + 1;
//   - p1 inside:       |c - p1| <= r;
//   - p0 inside:       |c - p1| <= r + len, so |t| <= |c - p1| / len <= 1 + r / len and |c - p1| < r + 1 + r / len.
// So a centre farther than r (1 + 1 / len) + 1 from p1 is never a hit. The bound used is (r (1 + 1 / len) + 1) x 1.001
// + 2 (1 / len through FSRRA): the 0.1% and the 2 units are far above the rounding of the original's values at world
// coordinates up to 10^5 (a few units in the last place of 0.008 each) and of FSRRA (2^-21). Fix 2 of lane eng-svcspd1
// used r + len + 1 (33% of the hill's tests passed over); r (1 + 1 / len) + 1 is tighter for every link longer than
// about sqrt(r).
// The first volume from c on that is in reach of the point (x, y, z), or ce: the scan, its few values in registers.
// Not "<=": a distance that is not a number is in reach, as the original tests it.
SHZ_FORCE_INLINE const ClothKSph* k_reach(const ClothKSph* c, const ClothKSph* ce, float x, float y, float z, float ra,
                                          float rb, uint32_t cyl, const ClothKSph* c0) {
    if (!cyl) {
        for (; c < ce; c++) {
            const float ex = c->x - x, ey = c->y - y, ez = c->z - z;
            const float reach = c->r * ra + rb;
            if (!(ex * ex + ey * ey + ez * ez > reach * reach)) break;
        }
        return c;
    }
    for (; c < ce; c++) {   // a cylinder is always tested
        const float ex = c->x - x, ey = c->y - y, ez = c->z - z;
        const float reach = c->r * ra + rb;
        if (!(ex * ex + ey * ey + ez * ez > reach * reach) || ((cyl >> (c - c0)) & 1)) break;
    }
    return c;
}

static void at_ck_parallel(const ClothKStep* s, ClothKVec* pos, ClothKVec* up) {
    if (!s->vol) return;
    const uint32_t n = s->nVol;
    ParSet ps;
    ClothKVec p1 = *up, p0 = *pos;
    ps.d.x = p0.x - p1.x;
    ps.d.y = p0.y - p1.y;
    ps.d.z = p0.z - p1.z;
    if (ps.d.x == 0.0f && ps.d.y == 0.0f && ps.d.z == 0.0f) ps.d.y = 1.0f;
    ps.lenSq = ps.d.x * ps.d.x + ps.d.y * ps.d.y + ps.d.z * ps.d.z;
    if (ps.lenSq <= 0.00001f) return;   // the original's len == 0 (k_sqrt: 0 at or under 0.00001): nothing tested
    const float ra = (1.0f + shz_inv_sqrtf_fsrra(ps.lenSq)) * 1.001f;
    const float rb = cloth_k_control_bound ? -40.0f : 1.001f + 2.0f;   // control: the bound 40 units short
    const uint32_t cyl = s->cylMask;
    const ClothKSph* const c0 = s->sph;
    const ClothKSph* const ce = c0 + n;
    uint32_t tested = 0;
    for (const ClothKSph* c = c0;; c++) {
        c = k_reach(c, ce, p1.x, p1.y, p1.z, ra, rb, cyl, c0);
        if (c == ce) break;
        if (!tested++) {   // the original's set-up, made once a volume is in reach
            ps.nd = k_normalize(ps.d);   // (the original's len is read only by its zero test, above)
            ps.invLenSq = 1.0f / ps.lenSq;
        }
        if (!cyl || !((cyl >> (c - c0)) & 1)) {
            // the original's first rejection, here without the call: the tested point's distance (push) from the
            // centre, the same operations in the same order as par_one (most spheres in reach end here)
            const float rr = c->r * c->r;
            float dot = (c->x - p1.x) * ps.d.x + (c->y - p1.y) * ps.d.y;
            dot += (c->z - p1.z) * ps.d.z;
            const float t = dot * ps.invLenSq;
            const float vx = ps.nd.x * t + p1.x - c->x, vy = ps.nd.y * t + p1.y - c->y, vz = ps.nd.z * t + p1.z - c->z;
            if (vx * vx + vy * vy + vz * vz >= rr) continue;
        }
        par_one(&p0, &p1, &ps, &s->vol[c - c0]);
    }
    cloth_k_cnt.vol_tests += n;
    cloth_k_cnt.vol_skips += n - tested;
    if (!tested) return;
    *up = p1;
    *pos = p0;
}

// ---------------------------------------------------------------------------------------------------------------
// the per-link stages (cloth.cpp round 2: move1 / move3, angle_limit, matrices)
SHZ_FORCE_INLINE ClothKVec wget(const ClothKStep* s, uint32_t b) { return k_vec(s->wx[b], s->wy[b], s->wz[b]); }
SHZ_FORCE_INLINE void wput(ClothKStep* s, uint32_t b, ClothKVec v) {
    s->wx[b] = v.x;
    s->wy[b] = v.y;
    s->wz[b] = v.z;
}
SHZ_FORCE_INLINE float* mat(ClothKStep* s, uint32_t b) { return s->boneMat + 16 * b; }
SHZ_FORCE_INLINE int at_ck(ClothKStep* s, ClothKVec* p, const ClothKVec* up) {
    return (s->flags & 0x80) ? cloth_k_at_ck_border(p, up, s->vol, s->nVol) : at_ck_plain(s, p, up);
}
SHZ_FORCE_INLINE void fix(ClothKStep* s, uint32_t i) {
    if (s->link[i].fix & 1) s->link[i].pos = s->cold[i].fixPos;
}
// PEN_FLOOR_CK: above the floor; a link landed under its upper link is jittered (two presentation draws)
SHZ_FORCE_INLINE void floor_ck(ClothKStep* s, uint32_t i) {
    if (s->flags & 0x100) return;
    ClothKLink* L = &s->link[i];
    if (L->pos.y < s->floorY) {
        L->pos.y = s->floorY;
        if (L->up != CLOTH_K_NONE) {
            const ClothKLink* U = &s->link[L->up];
            if (L->pos.x == U->pos.x && L->pos.z == U->pos.z) {
                L->pos.x += pres_f11(s->rng);
                L->pos.z += pres_f11(s->rng);
            }
        }
    }
}
// PEN_FLOOR_CK3: both ends of a constraint
SHZ_FORCE_INLINE void floor_ck3(ClothKStep* s, ClothKLink* L, ClothKLink* U) {
    if (s->flags & 0x100) return;
    if (L->pos.y < s->floorY) {
        L->pos.y = s->floorY;
        if (L->pos.x == U->pos.x && L->pos.z == U->pos.z) {
            L->pos.x += pres_f11(s->rng);
            L->pos.z += pres_f11(s->rng);
        }
    }
    if (U->pos.y < s->floorY) U->pos.y = s->floorY;
}

// the root's motion, gravity, the speed, the wind (Move1), the floor and the pin
static void stage_move(ClothKStep* s, uint32_t i) {
    ClothKLink* L = &s->link[i];
    L->pos = k_add(L->pos, s->move);
    L->oldPos = L->pos;
    if (!s->noGravity) L->speed.y -= s->pGravity ? s->pGravity[i] : s->gravity;
    L->pos = k_add(L->pos, L->speed);
    if (s->wind) {
        ClothKVec v = k_sub(L->pos, s->mpos);
        v.y = 0.0f;
        if (v.x != 0.0f && v.z != 0.0f) {
            v = k_normalize(v);
            v = k_scale(v, s->spdLen);
            float ang = 1.0f;
            if (s->windAng) {
                ang = s->windAng[i];
                v = k_scale(v, ang);
            }
            v = k_scale(v, ang);
            v = k_scale(v, s->pWindRate[i]);
            if (s->windScale != 1.0f) v = k_scale(v, s->windScale);
            L->pos = k_add(L->pos, v);
        }
    }
    if (s->debugWind) {
        const float ang = s->windAng ? s->windAng[i] : 0.0f;
        ClothKVec w = k_scale(s->globalWind, ang);
        w = k_scale(w, s->pWindRate[i]);
        L->pos = k_add(L->pos, w);
    }
    floor_ck(s, i);
    fix(s, i);
}

// the angle limit against the upper link
static void stage_angle(ClothKStep* s, uint32_t i) {
    ClothKLink* L = &s->link[i];
    const uint32_t pb = L->bone;
    ClothKVec a, b;
    float mtx[12];
    if (L->fix & 1) return;
    if (L->up != CLOTH_K_NONE) {
        const ClothKLink* U = &s->link[L->up];
        wput(s, pb, U->pos);
        a = k_sub(U->pos, wget(s, U->bone));
        a = k_zero(a) ? L->nrm : k_normalize(a);
    } else {
        a = k_normalize(k_mul_sr(mat(s, pb), L->nrm));
    }
    const ClothKVec pw = wget(s, pb);
    b = k_sub(L->pos, pw);
    const float d = k_sqrt(b.x * b.x + b.y * b.y + b.z * b.z);
    b = k_zero(b) ? L->nrm : k_normalize(b);
    const float ang = k_acos(k_dot(a, b));
    float spdRate = s->pMax[i];
    if (ang > spdRate && ang < K_PI_LIM) {
        spdRate = ang * 0.2f + spdRate * 0.8f;
        k_rot_axis(mtx, k_cross(a, b), spdRate);
        L->pos = k_mul_sr(mtx, a);
        L->pos = k_scale(L->pos, d);
        L->pos = k_add(L->pos, pw);
    }
}

// one constraint pass of a link: its side links and its upper link (or its bone)
static void stage_constrain1(ClothKStep* s, uint32_t i) {
    ClothKLink* L = &s->link[i];
    const ClothKCold* C = &s->cold[i];
    ClothKVec v;
    float d;
    if (!(s->flags & 4)) {
        for (int q = 0; q < 4; q++) {
            if (L->side[q] == CLOTH_K_NONE) continue;
            ClothKLink* U = &s->link[L->side[q]];
            v = k_sub(U->pos, L->pos);
            d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
            v = k_scale(v, (C->dist[q]) / d - 0.5f);
            L->pos = k_sub(L->pos, v);
            U->pos = k_add(U->pos, v);
        }
    }
    if (L->up != CLOTH_K_NONE) {
        ClothKLink* U = &s->link[L->up];
        v = k_sub(U->pos, L->pos);
        d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        v = k_scale(v, 0.5f / d * (L->len - d));
        U->pos = k_add(U->pos, v);
        L->pos = k_sub(L->pos, v);
        if (at_ck(s, &L->pos, &U->pos)) L->hit |= 1;
        floor_ck(s, i);
        fix(s, i);
        fix(s, L->up);
    } else {
        const ClothKVec pw = wget(s, L->bone);
        v = k_sub(pw, L->pos);
        d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        v = k_scale(v, 0.5f / d * (L->len - d));
        L->pos = k_sub(L->pos, v);
        if (at_ck(s, &L->pos, &pw)) L->hit |= 1;
        floor_ck(s, i);
        fix(s, i);
    }
}
static void stage_constrain3(ClothKStep* s, uint32_t i) {
    ClothKLink* L = &s->link[i];
    const ClothKCold* C = &s->cold[i];
    ClothKVec v;
    float d;
    if (!(s->flags & 4)) {
        for (int q = 2; q < 4; q++) {
            if (L->side[q] == CLOTH_K_NONE) continue;
            ClothKLink* U = &s->link[L->side[q]];
            at_ck_parallel(s, &L->pos, &U->pos);
            floor_ck3(s, L, U);
            fix(s, i);
            fix(s, L->side[q]);
        }
        for (int q = 0; q < 2; q++) {
            if (L->side[q] == CLOTH_K_NONE) continue;
            ClothKLink* U = &s->link[L->side[q]];
            at_ck_parallel(s, &L->pos, &U->pos);
            v = k_sub(U->pos, L->pos);
            d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
            v = k_scale(v, (d * 0.5f - (C->dist[q])) * s->stretchy / d);
            L->pos = k_add(L->pos, v);
            U->pos = k_sub(U->pos, v);
            floor_ck3(s, L, U);
            fix(s, i);
            fix(s, L->side[q]);
        }
    }
    if (L->up != CLOTH_K_NONE) {
        ClothKLink* U = &s->link[L->up];
        at_ck_parallel(s, &L->pos, &U->pos);
        v = k_sub(U->pos, L->pos);
        d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        v = k_scale(v, (d - L->len) * 0.5f * s->stretchy / d);
        L->pos = k_add(L->pos, v);
        U->pos = k_sub(U->pos, v);
        floor_ck3(s, L, U);
        fix(s, i);
        fix(s, L->up);
    } else {
        const ClothKVec pw = wget(s, L->bone);
        if (at_ck(s, &L->pos, &pw)) L->hit |= 1;
        v = k_sub(pw, L->pos);
        d = k_sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
        v = k_scale(v, (d - L->len) * 0.5f * s->stretchy / d);
        L->pos = k_add(L->pos, v);
        if (!(s->flags & 0x100)) {
            if (L->pos.y < s->floorY) L->pos.y = s->floorY;
        }
        fix(s, i);
    }
}

// the link's bone looks along its link
static void stage_matrix(ClothKStep* s, uint32_t i) {
    ClothKLink* L = &s->link[i];
    const uint32_t pb = L->bone;
    ClothKLink* U = 0;
    ClothKVec v, a, b;
    float mtx[12];
    if (L->up != CLOTH_K_NONE) {
        U = &s->link[L->up];
        wput(s, pb, U->pos);
    }
    const ClothKVec pw = wget(s, pb);
    if (!(s->flags & 8)) {
        v = k_sub(L->pos, pw);
        v = k_zero(v) ? L->nrm : k_normalize(v);
        v = k_scale(v, L->len);
        L->pos = k_add(pw, v);
    }
    if (at_ck(s, &L->pos, U ? &U->pos : &pw)) L->hit |= 1;
    if (!(s->flags & 0x100)) {   // PEN_FLOOR_CK2
        if (L->pos.y < s->floorY) {
            L->pos.y = s->floorY;
            if (U && L->pos.x == U->pos.x && L->pos.z == U->pos.z) {
                L->pos.x += pres_f11(s->rng);
                L->pos.z += pres_f11(s->rng);
            }
        }
    }
    fix(s, i);
    float spdRate = s->pRate ? s->pRate[i] : s->rate;
    if (L->hit & 1) spdRate *= 0.3f;
    L->speed = k_scale(k_sub(L->pos, L->oldPos), spdRate);
    float* m = mat(s, pb);
    a = k_mul_sr(m, L->nrm);
    b = k_sub(L->pos, pw);
    b = k_zero(b) ? L->nrm : k_normalize(b);
    const float ang = k_acos(k_dot(a, b));
    if (ang > 0.01f && ang < K_PI_LIM) {
        k_rot_axis(mtx, k_cross(a, b), ang);
        k_concat_into(mtx, m);
    }
    m[3] = pw.x;
    m[7] = pw.y;
    m[11] = pw.z;
}

SHZ_FORCE_INLINE int do_angle(const ClothKStep* s) { return !(s->flags & 0x10) && s->pMax; }
SHZ_FORCE_INLINE int do_constrain(const ClothKStep* s) { return !(s->flags & 2); }

// The fused schedule (exact): the motion and the angle limit of a link in one pass when every link's upper link comes
// before it (the angle limit of a link reads its upper link after that link's own motion and limit); the last
// constraint pass and the matrices in one pass, a link's matrix stage run as soon as no later constraint can move it
// or its upper link (need[]): every stage reads what it reads in the original's order.
static void step_fused(ClothKStep* s) {
    const uint32_t n = s->n;
    const int ang = do_angle(s), con = do_constrain(s) && s->bundle > 0;
    uint32_t i, k;
    int ordered = 1;
    for (i = 0; i < n; i++)
        if (s->link[i].up != CLOTH_K_NONE && s->link[i].up >= i) ordered = 0;
    if (ordered) {
        for (i = 0; i < n; i++) {
            if (s->integrate) stage_move(s, i);
            if (ang) stage_angle(s, i);
        }
        cloth_k_cnt.passes += (s->integrate || ang) ? 1 : 0;
    } else {
        if (s->integrate)
            for (i = 0; i < n; i++) stage_move(s, i);
        if (ang)
            for (i = 0; i < n; i++) stage_angle(s, i);
        cloth_k_cnt.passes += (s->integrate ? 1 : 0) + (ang ? 1 : 0);
    }
    if (!con) {
        for (i = 0; i < n; i++) stage_matrix(s, i);
        cloth_k_cnt.passes += 1;
        return;
    }
    for (k = 0; k + 1 < s->bundle; k++)
        for (i = 0; i < n; i++) {
            if (s->variant == 3) stage_constrain3(s, i);
            else stage_constrain1(s, i);
        }
    // last[k]: the last link whose constraint stage moves link k; need[k]: the step after which k's matrix may run
    uint8_t last[256], need[256];
    for (i = 0; i < n; i++) last[i] = (uint8_t) i;
    for (i = 0; i < n; i++) {
        const ClothKLink* L = &s->link[i];
        if (!(s->flags & 4))
            for (int q = 0; q < 4; q++)
                if (L->side[q] != CLOTH_K_NONE && last[L->side[q]] < i) last[L->side[q]] = (uint8_t) i;
        if (L->up != CLOTH_K_NONE && last[L->up] < i) last[L->up] = (uint8_t) i;
    }
    for (i = 0; i < n; i++) {
        const uint8_t u = s->link[i].up;
        need[i] = last[i];
        if (u != CLOTH_K_NONE && last[u] > need[i]) need[i] = last[u];
    }
    uint32_t next = 0;
    for (i = 0; i < n; i++) {
        if (s->variant == 3) stage_constrain3(s, i);
        else stage_constrain1(s, i);
        while (next < n && need[next] <= i) stage_matrix(s, next++);
    }
    while (next < n) stage_matrix(s, next++);
    cloth_k_cnt.passes += s->bundle;
}

void cloth_k_step(ClothKStep* s) {
    k_prep(s);
    step_fused(s);
    cloth_k_cnt.links += s->n;
}

// Every stage of a link before the next link (one pass): measured and not used (svc/cloth_stats.py fails it: a
// link's later neighbours hold last tick's positions while it is constrained). Kept for the kernel test.
void cloth_k_step_onepass(ClothKStep* s) {
    k_prep(s);
    const uint32_t n = s->n;
    const int ang = do_angle(s), con = do_constrain(s);
    for (uint32_t i = 0; i < n; i++) {
        if (s->integrate) stage_move(s, i);
        if (ang) stage_angle(s, i);
        if (con)
            for (uint32_t k = 0; k < s->bundle; k++) {
                if (s->variant == 3) stage_constrain3(s, i);
                else stage_constrain1(s, i);
            }
        stage_matrix(s, i);
    }
    cloth_k_cnt.links += n;
    cloth_k_cnt.passes += 1;
}

void cloth_k_step_passes(ClothKStep* s) {
    k_prep(s);
    const uint32_t n = s->n;
    uint32_t i, k;
    if (s->integrate)
        for (i = 0; i < n; i++) stage_move(s, i);
    if (do_angle(s))
        for (i = 0; i < n; i++) stage_angle(s, i);
    if (do_constrain(s))
        for (k = 0; k < s->bundle; k++)
            for (i = 0; i < n; i++) {
                if (s->variant == 3) stage_constrain3(s, i);
                else stage_constrain1(s, i);
            }
    for (i = 0; i < n; i++) stage_matrix(s, i);
    cloth_k_cnt.links += n;
    cloth_k_cnt.passes += 2 + (do_angle(s) ? 1 : 0) + (do_constrain(s) ? s->bundle : 0);
}

#ifdef CLOTH_K_TEST
// the primitives, for cloth_kernel_test.c (the SW back-end against the C library, bit for bit)
void cloth_k_test_normalize(const float* in, float* out) {
    ClothKVec v = k_normalize(k_vec(in[0], in[1], in[2]));
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
}
float cloth_k_test_dot(const float* a, const float* b) { return k_dot(k_vec(a[0], a[1], a[2]), k_vec(b[0], b[1], b[2])); }
void cloth_k_test_cross(const float* a, const float* b, float* out) {
    ClothKVec v = k_cross(k_vec(a[0], a[1], a[2]), k_vec(b[0], b[1], b[2]));
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
}
void cloth_k_test_mul(const float* m, const float* in, float* out, int sr) {
    ClothKVec v = sr ? k_mul_sr(m, k_vec(in[0], in[1], in[2])) : k_mul(m, k_vec(in[0], in[1], in[2]));
    out[0] = v.x;
    out[1] = v.y;
    out[2] = v.z;
}
void cloth_k_test_rot_axis(float* m, const float* axis, float rad) { k_rot_axis(m, k_vec(axis[0], axis[1], axis[2]), rad); }
void cloth_k_test_concat(const float* a, float* b) { k_concat_into(a, b); }
float cloth_k_test_sqrt(float x) { return k_sqrt(x); }
float cloth_k_test_acos(float x) { return k_acos(x); }
#endif
