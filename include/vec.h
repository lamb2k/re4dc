#ifndef VEC_H
#define VEC_H

// Dolphin SDK vector/matrix types and the PS* routines used by game code. The SDK headers in
// include/dolphin/ pull in the CodeWarrior libc and cannot be compiled by ProDG/GCC, so game
// units include this instead. Shares the dolphin/mtx.h guard so both can coexist.

#include "types.h"

#ifndef _DOLPHIN_MTX_H_
#define _DOLPHIN_MTX_H_

typedef struct {
    f32 x, y, z;
} Vec;

typedef f32 Mtx[3][4];
typedef f32 (*MtxPtr)[4];
typedef f32 Mtx44[4][4];

#ifdef __cplusplus
extern "C" {
#endif

void PSMTXIdentity(Mtx m);
void PSMTXCopy(const Mtx src, Mtx dst);
void PSMTXConcat(const Mtx lhs, const Mtx rhs, Mtx ab);
void PSMTXTranspose(const Mtx src, Mtx xPose);
u32 PSMTXInverse(const Mtx src, Mtx inv);
void PSMTXRotRad(Mtx m, char axis, f32 rad);
void PSMTXRotTrig(Mtx m, char axis, f32 sinA, f32 cosA);
void PSMTXRotAxisRad(Mtx m, const Vec* axis, f32 rad);
void PSMTXTrans(Mtx m, f32 xT, f32 yT, f32 zT);
void PSMTXScale(Mtx m, f32 xS, f32 yS, f32 zS);
void PSMTXMultVec(const Mtx m, const Vec* src, Vec* dst);
void PSMTXMultVecArray(const Mtx m, const Vec* srcBase, Vec* dstBase, u32 count);
void PSMTXMultVecSR(const Mtx m, const Vec* src, Vec* dst);
void PSMTXTransApply(const Mtx src, Mtx dst, f32 xT, f32 yT, f32 zT);
// RE4DC SH4_APPROX_RENDER: as include/dolphin/mtx.h (render-only call sites; off = the exact PS entry points).
#if defined(RE4DC_SH4_APPROX_RENDER) && RE4DC_SH4_APPROX_RENDER
void re4dc_shz_MTXConcat(const Mtx a, const Mtx b, Mtx ab);
void re4dc_shz_MTXRotRad(Mtx m, char axis, f32 rad);
#define RE4DC_RENDER_MTXConcat re4dc_shz_MTXConcat
#define RE4DC_RENDER_MTXRotRad re4dc_shz_MTXRotRad
#else
#define RE4DC_RENDER_MTXConcat PSMTXConcat
#define RE4DC_RENDER_MTXRotRad PSMTXRotRad
#endif

void C_MTXOrtho(Mtx44 m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 f);
void C_MTXPerspective(Mtx44 m, f32 fovY, f32 aspect, f32 n, f32 f);
void C_MTXFrustum(Mtx44 m, f32 t, f32 b, f32 l, f32 r, f32 n, f32 f);
void C_MTXLookAt(Mtx m, const Vec* camPos, const Vec* camUp, const Vec* target);
void PSMTX44MultVec(const Mtx44 m, const Vec* src, Vec* dst);
void C_MTXLightPerspective(Mtx m, f32 fovY, f32 aspect, f32 scaleS, f32 scaleT, f32 transS, f32 transT);

void PSVECAdd(const Vec* a, const Vec* b, Vec* ab);
void PSVECSubtract(const Vec* a, const Vec* b, Vec* a_b);
void PSVECScale(const Vec* src, Vec* dst, f32 scale);
void PSVECNormalize(const Vec* src, Vec* unit);
f32 PSVECSquareMag(const Vec* v);
f32 PSVECMag(const Vec* v);
f32 PSVECDotProduct(const Vec* a, const Vec* b);
void PSVECCrossProduct(const Vec* a, const Vec* b, Vec* axb);
f32 PSVECSquareDistance(const Vec* a, const Vec* b);
f32 PSVECDistance(const Vec* a, const Vec* b);
void C_VECReflect(const Vec* src, const Vec* normal, Vec* dst);

typedef struct {
    f32 x, y, z, w;
} Quaternion;

void C_QUATMtx(Quaternion* r, const Mtx m);
void C_QUATSlerp(const Quaternion* p, const Quaternion* q, Quaternion* r, f32 t);
void PSMTXQuat(Mtx m, const Quaternion* q);

#ifdef __cplusplus
}
#endif

#if defined(RE4DC_VEC_INLINE) && RE4DC_VEC_INLINE
// GAME_VEC_INLINE=1 (game30.mk, contract-off game units only): the small PSVEC* routines inline.
// On the Dreamcast each was two calls (platform/mtx.cpp PS* -> the SDK's C_* body); these are the
// C_* bodies of src/lib/vec.c with the same operations in the same order (and the same temporaries
// where the source keeps one), so the results are bit-identical with -ffp-contract=off.
static inline void re4dc_vec_add(const Vec* a, const Vec* b, Vec* ab)
{
    ab->x = a->x + b->x;
    ab->y = a->y + b->y;
    ab->z = a->z + b->z;
}
static inline void re4dc_vec_sub(const Vec* a, const Vec* b, Vec* a_b)
{
    a_b->x = a->x - b->x;
    a_b->y = a->y - b->y;
    a_b->z = a->z - b->z;
}
static inline void re4dc_vec_scale(const Vec* src, Vec* dst, f32 scale)
{
    dst->x = (src->x * scale);
    dst->y = (src->y * scale);
    dst->z = (src->z * scale);
}
static inline f32 re4dc_vec_sqmag(const Vec* v)
{
    return v->z * v->z + ((v->x * v->x) + (v->y * v->y));
}
static inline f32 re4dc_vec_dot(const Vec* a, const Vec* b)
{
    return (a->z * b->z) + ((a->x * b->x) + (a->y * b->y));
}
static inline void re4dc_vec_cross(const Vec* a, const Vec* b, Vec* axb)
{
    Vec vTmp;
    vTmp.x = (a->y * b->z) - (a->z * b->y);
    vTmp.y = (a->z * b->x) - (a->x * b->z);
    vTmp.z = (a->x * b->y) - (a->y * b->x);
    axb->x = vTmp.x;
    axb->y = vTmp.y;
    axb->z = vTmp.z;
}
static inline f32 re4dc_vec_sqdist(const Vec* a, const Vec* b)
{
    Vec diff;
    diff.x = a->x - b->x;
    diff.y = a->y - b->y;
    diff.z = a->z - b->z;
    return (diff.z * diff.z) + ((diff.x * diff.x) + (diff.y * diff.y));
}
#define PSVECAdd(a, b, ab) re4dc_vec_add((a), (b), (ab))
#define PSVECSubtract(a, b, ab) re4dc_vec_sub((a), (b), (ab))
#define PSVECScale(s, d, k) re4dc_vec_scale((s), (d), (k))
#define PSVECSquareMag(v) re4dc_vec_sqmag((v))
#define PSVECDotProduct(a, b) re4dc_vec_dot((a), (b))
#define PSVECCrossProduct(a, b, d) re4dc_vec_cross((a), (b), (d))
#define PSVECSquareDistance(a, b) re4dc_vec_sqdist((a), (b))
#endif
#if defined(RE4DC_VEC_NORM_INLINE) && RE4DC_VEC_NORM_INLINE && defined(__sh__)
// GAME_VEC_NORM_INLINE (game30.mk, lane gskel; exact): PSVECNormalize inline in the units that call it
// most (cloth, the orientation builders). The body of C_VECNormalize (platform/sdk/gen/vec.c) with the
// same operations in the same order: the magnitude sum, fsqrt as that unit emits it (no errno guard
// there), 1 / root, the three products; each component is read after the previous store, as there
// (src and unit may be the same vector).
//   =2 (check build): each call is also made to C_VECNormalize on a copy of the input and the words are
//       compared (platform/mtx.cpp, "VNRM" log line).
#if RE4DC_VEC_NORM_INLINE == 2
#ifdef __cplusplus
extern "C"
#endif
void re4dc_vnorm_check(const Vec* src, const Vec* unit);
#endif
static inline __attribute__((always_inline)) void re4dc_vec_normalize(const Vec* src, Vec* unit)
{
#if RE4DC_VEC_NORM_INLINE == 2
    const Vec in = *src;
#endif
    f32 mag = (src->z * src->z) + ((src->x * src->x) + (src->y * src->y));
    __asm__("fsqrt\t%0" : "+f"(mag));
    mag = 1.0f / mag;
    unit->x = src->x * mag;
    unit->y = src->y * mag;
    unit->z = src->z * mag;
#if RE4DC_VEC_NORM_INLINE == 2
    re4dc_vnorm_check(&in, unit);
#endif
}
#define PSVECNormalize(s, d) re4dc_vec_normalize((s), (d))
#endif

#endif

#endif
