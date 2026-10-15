/* sh4zam_direct.c: GAME_SH4ZAM=1 (game30.mk; lane sh4zam-direct 2026-10-15). NOT bit-exact.
 *
 * Phase 1 of the SH4ZAM direct mapping (review by an SH4ZAM author, 10-15: "directly map to sh4zam calls as phase 1.
 * Not fully optimal but will gain."). Each GameCube SDK matrix / vector entry point that does FPU arithmetic gets a
 * thin body made of SH4ZAM v0.9.0 calls (kos-ports sh4zam, MIT, pin 0fd3a1e1): XMTRX + FTRV for the concat,
 * FIPR (shz_dot8f / shz_dot6f) for the matrix x vector rows and dot products, FSRRA (shz_inv_sqrtf / shz_invf) for
 * normalize / magnitude / the inverse's 1/det, FSCA (shz_sincosf) for sin / cos. Data-movement entry points
 * (Identity, Copy, Transpose, Scale, Trans, Reorder, VECAdd / Subtract / Scale) do no arithmetic that SH4ZAM could
 * shorten: they keep their exact platform/mtx_sh4.S bodies (see docs/lanes/sh4zam-direct.md).
 *
 * Layout: a GameCube Mtx is float[3][4], row-major, the 4th column the translation (an affine 4x4 whose last row is
 * 0 0 0 1). Its 12 floats are, word for word, an SH4ZAM shz_mat4x3_t (three 4D columns) of the TRANSPOSE. So:
 *   - the rows of a Mtx are contiguous shz_vec4_t;
 *   - shz_xmtrx_load_cols_4x3(b0, b1, b2) puts b^T (with 0 0 0 1 as the 4th column) in XMTRX, and FTRV of a row of a
 *     gives the matching row of a x b (the 4th lane picks up a_i3, the translation term).
 * ABI: -m4-single -ml, FPSCR PR=0 SZ=0 on entry and exit (SH4ZAM's inline asm restores SZ after its paired moves;
 * nothing here sets PR). XMTRX: only re4dc_zam_MTXConcat writes it (clobbered, never restored: see the XMTRX rules
 * in the lane doc); every other routine here uses FIPR / FSRRA / FSCA, which leave XMTRX alone. */
#include <stdint.h>
#include <sh4zam/shz_xmtrx.h>
#include <sh4zam/shz_vector.h>
#include <sh4zam/shz_scalar.h>
#include <sh4zam/shz_trig.h>

typedef struct { float x, y, z; } zvec_t;

void PSMTXRotTrig(float (*m)[4], char axis, float sinA, float cosA);
void re4dc_sincosf(float x, float* s, float* c);

/* sin / cos: FSCA through shz_sincosf (1/65536-turn steps) for |x| <= 0x43490f80 (~201 rad); larger, inf and NaN keep
 * the exact re4dc_sincosf (its sincosf_big path), as Bruceleeto's fe2aed7945 does. */
static inline void zam_sincos(float x, float* s, float* c)
{
    union { float f; uint32_t u; } v = { x };
    if ((v.u & 0x7fffffffu) > 0x43490f80u) {
        re4dc_sincosf(x, s, c);
        return;
    }
    shz_sincos_t r = shz_sincosf(x);
    *s = r.sin;
    *c = r.cos;
}

void re4dc_zam_sincosf(float x, float* s, float* c)
{
    zam_sincos(x, s, c);
}

/* ab = a x b. XMTRX = b^T (b's rows as columns, 0 0 0 1 last); one FTRV per row of a. ab may alias a or b: b is in
 * XMTRX before any store, and row i of a is read before row i of ab is written. CLOBBERS XMTRX. */
void re4dc_zam_MTXConcat(const float (*a)[4], const float (*b)[4], float (*ab)[4])
{
    shz_xmtrx_load_cols_4x3((const shz_vec4_t*) b[0], (const shz_vec4_t*) b[1], (const shz_vec4_t*) b[2]);
    for (int i = 0; i < 3; i++) {
        shz_vec4_t r = shz_xmtrx_transform_vec4(shz_vec4_init(a[i][0], a[i][1], a[i][2], a[i][3]));
        ab[i][0] = r.x;
        ab[i][1] = r.y;
        ab[i][2] = r.z;
        ab[i][3] = r.w;
    }
}

/* dst = m x (src, 1): one FIPR per row. src may alias dst. XMTRX untouched. */
void re4dc_zam_MTXMultVec(const float (*m)[4], const zvec_t* src, zvec_t* dst)
{
    const float x = src->x, y = src->y, z = src->z;
    const float rx = shz_dot8f(m[0][0], m[0][1], m[0][2], m[0][3], x, y, z, 1.0f);
    const float ry = shz_dot8f(m[1][0], m[1][1], m[1][2], m[1][3], x, y, z, 1.0f);
    const float rz = shz_dot8f(m[2][0], m[2][1], m[2][2], m[2][3], x, y, z, 1.0f);
    dst->x = rx;
    dst->y = ry;
    dst->z = rz;
}

/* dst = m3x3 x src (no translation): one FIPR per row. */
void re4dc_zam_MTXMultVecSR(const float (*m)[4], const zvec_t* src, zvec_t* dst)
{
    const float x = src->x, y = src->y, z = src->z;
    const float rx = shz_dot6f(m[0][0], m[0][1], m[0][2], x, y, z);
    const float ry = shz_dot6f(m[1][0], m[1][1], m[1][2], x, y, z);
    const float rz = shz_dot6f(m[2][0], m[2][1], m[2][2], x, y, z);
    dst->x = rx;
    dst->y = ry;
    dst->z = rz;
}

/* inv = src^-1 (affine). Cofactors as cross products of the rows (c0 = r1 x r2, c1 = r2 x r0, c2 = r0 x r1),
 * det = r0 . c0 (FIPR), 1/det by FSRRA (shz_invf) inside 2^+-60, else a divide; inverse row i = (c0_i c1_i c2_i)/det,
 * translation = -(row_i . t) by FIPR. Returns 0 and leaves inv untouched when det == 0, as C_MTXInverse does.
 * src may alias inv (everything is read first). XMTRX untouched. */
uint32_t re4dc_zam_MTXInverse(const float (*src)[4], float (*inv)[4])
{
    const shz_vec3_t r0 = shz_vec3_init(src[0][0], src[0][1], src[0][2]);
    const shz_vec3_t r1 = shz_vec3_init(src[1][0], src[1][1], src[1][2]);
    const shz_vec3_t r2 = shz_vec3_init(src[2][0], src[2][1], src[2][2]);
    const float tx = src[0][3], ty = src[1][3], tz = src[2][3];
    const shz_vec3_t c0 = shz_vec3_cross(r1, r2);
    const shz_vec3_t c1 = shz_vec3_cross(r2, r0);
    const shz_vec3_t c2 = shz_vec3_cross(r0, r1);
    const float det = shz_vec3_dot(r0, c0);
    float id;
    if (det == 0.0f) {
        return 0;
    }
    {
        const float ad = det < 0.0f ? -det : det;
        id = (ad > 0x1p-60f && ad < 0x1p60f) ? shz_invf(det) : 1.0f / det;
    }
    {
        const float m00 = c0.x * id, m01 = c1.x * id, m02 = c2.x * id;
        const float m10 = c0.y * id, m11 = c1.y * id, m12 = c2.y * id;
        const float m20 = c0.z * id, m21 = c1.z * id, m22 = c2.z * id;
        const float t0 = -shz_dot6f(m00, m01, m02, tx, ty, tz);
        const float t1 = -shz_dot6f(m10, m11, m12, tx, ty, tz);
        const float t2 = -shz_dot6f(m20, m21, m22, tx, ty, tz);
        inv[0][0] = m00; inv[0][1] = m01; inv[0][2] = m02; inv[0][3] = t0;
        inv[1][0] = m10; inv[1][1] = m11; inv[1][2] = m12; inv[1][3] = t1;
        inv[2][0] = m20; inv[2][1] = m21; inv[2][2] = m22; inv[2][3] = t2;
    }
    return 1;
}

/* PSMTXRotRad with FSCA sin / cos; the matrix layout is the exact PSMTXRotTrig. */
void re4dc_zam_MTXRotRad(float (*m)[4], char axis, float rad)
{
    float s, c;
    zam_sincos(rad, &s, &c);
    PSMTXRotTrig(m, axis, s, c);
}

/* C_MTXRotAxisRad's formula with FSCA sin / cos and an FSRRA-normalized axis. */
void re4dc_zam_MTXRotAxisRad(float (*m)[4], const zvec_t* axis, float rad)
{
    float s, c;
    zam_sincos(rad, &s, &c);
    {
        const float t = 1.0f - c;
        const shz_vec3_t n = shz_vec3_normalize(shz_vec3_init(axis->x, axis->y, axis->z));
        const float x = n.x, y = n.y, z = n.z;
        const float tx = t * x, ty = t * y;
        m[0][0] = c + tx * x;
        m[0][1] = y * tx - s * z;
        m[0][2] = z * tx + s * y;
        m[0][3] = 0.0f;
        m[1][0] = y * tx + s * z;
        m[1][1] = c + ty * y;
        m[1][2] = z * ty - s * x;
        m[1][3] = 0.0f;
        m[2][0] = z * tx - s * y;
        m[2][1] = z * ty + s * x;
        m[2][2] = c + t * (z * z);
        m[2][3] = 0.0f;
    }
}

float re4dc_zam_VECDotProduct(const zvec_t* a, const zvec_t* b)
{
    return shz_dot6f(a->x, a->y, a->z, b->x, b->y, b->z);
}

float re4dc_zam_VECSquareMag(const zvec_t* v)
{
    return shz_mag_sqr3f(v->x, v->y, v->z);
}

float re4dc_zam_VECMag(const zvec_t* v)
{
    return shz_sqrtf(shz_mag_sqr3f(v->x, v->y, v->z));
}

/* unit = src / |src| (FIPR + FSRRA). A zero vector gives inf x 0 = NaN, as the SDK's 1 / sqrtf(0) path does. */
void re4dc_zam_VECNormalize(const zvec_t* src, zvec_t* unit)
{
    const shz_vec3_t n = shz_vec3_normalize(shz_vec3_init(src->x, src->y, src->z));
    unit->x = n.x;
    unit->y = n.y;
    unit->z = n.z;
}

/* SH4ZAM's cross product is plain C in the SDK's operation order: exact (ulp 0). */
void re4dc_zam_VECCrossProduct(const zvec_t* a, const zvec_t* b, zvec_t* axb)
{
    const shz_vec3_t r = shz_vec3_cross(shz_vec3_init(a->x, a->y, a->z), shz_vec3_init(b->x, b->y, b->z));
    axb->x = r.x;
    axb->y = r.y;
    axb->z = r.z;
}

float re4dc_zam_VECSquareDistance(const zvec_t* a, const zvec_t* b)
{
    return shz_mag_sqr3f(a->x - b->x, a->y - b->y, a->z - b->z);
}

float re4dc_zam_VECDistance(const zvec_t* a, const zvec_t* b)
{
    return shz_sqrtf(shz_mag_sqr3f(a->x - b->x, a->y - b->y, a->z - b->z));
}

/* GAME_SH4ZAM_LOGIC run batching (include/re4dc_xm.h RE4DC_XM_LOAD / _POINT / _DIR): several vectors through one Mtx.
 * The game's C++ units cannot include the SH4ZAM headers (its include/cmath.h declares sinf & co. with C++ linkage,
 * newlib's math.h with C linkage), so the three SH4ZAM calls live here, out of line. XMTRX = the Mtx rows with
 * 0 0 0 1 as the 4th row (shz_xmtrx_load_rows_3x4); each vector is then one FTRV (shz_xmtrx_transform_point3 /
 * _vec3). CLOBBERS XMTRX; the caller transforms right after the load with no game call in between. */
void re4dc_zam_xm_load(const float (*m)[4])
{
    shz_xmtrx_load_rows_3x4((const shz_vec4_t*) m[0], (const shz_vec4_t*) m[1], (const shz_vec4_t*) m[2]);
}

void re4dc_zam_xm_point(const zvec_t* src, zvec_t* dst)
{
    const shz_vec3_t v = shz_xmtrx_transform_point3(shz_vec3_init(src->x, src->y, src->z));
    dst->x = v.x;
    dst->y = v.y;
    dst->z = v.z;
}

void re4dc_zam_xm_dir(const zvec_t* src, zvec_t* dst)
{
    const shz_vec3_t v = shz_xmtrx_transform_vec3(shz_vec3_init(src->x, src->y, src->z));
    dst->x = v.x;
    dst->y = v.y;
    dst->z = v.z;
}
