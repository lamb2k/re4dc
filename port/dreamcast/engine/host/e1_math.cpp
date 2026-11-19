// SDK math entry points (PSMTX*/PSVEC*) of the E1 image: forwarders to the SDK C bodies built from src/lib (copied
// from the old port's platform/mtx.cpp; its SH-4 bodies are proven bit-identical to these, so either gives the reference's results).
// Matrix / vector interface: the game calls the SDK's paired-single PS*
// entry points; here they forward to the SDK's own C reference functions
// (src/lib/mtx.c, mtxvec.c, mtx44.c, vec.c, quat.c compiled in platform/sdk
// with the CodeWarrior asm bodies stripped), so the arithmetic is the SDK's.
typedef unsigned long u32;
typedef float f32;
typedef f32 Mtx[3][4];
typedef f32 Mtx44[4][4];
typedef f32 ROMtx[4][3];
struct Vec { f32 x, y, z; };
struct Quaternion { f32 x, y, z, w; };

extern "C" {

void C_MTXIdentity(Mtx m);
void C_MTXCopy(const Mtx src, Mtx dst);
void C_MTXConcat(const Mtx a, const Mtx b, Mtx ab);
void C_MTXTranspose(const Mtx src, Mtx xPose);
u32 C_MTXInverse(const Mtx src, Mtx inv);
void C_MTXRotRad(Mtx m, char axis, f32 rad);
void C_MTXRotTrig(Mtx m, char axis, f32 sinA, f32 cosA);
void C_MTXRotAxisRad(Mtx m, const Vec* axis, f32 rad);
void C_MTXTrans(Mtx m, f32 x, f32 y, f32 z);
void C_MTXTransApply(const Mtx src, Mtx dst, f32 x, f32 y, f32 z);
void C_MTXScale(Mtx m, f32 x, f32 y, f32 z);
void C_MTXQuat(Mtx m, const Quaternion* q);
void C_MTXMultVec(const Mtx m, const Vec* src, Vec* dst);
void C_MTXMultVecArray(const Mtx m, const Vec* src, Vec* dst, u32 count);
void C_MTXMultVecSR(const Mtx m, const Vec* src, Vec* dst);
void C_MTX44MultVec(const Mtx44 m, const Vec* src, Vec* dst);
void C_VECAdd(const Vec* a, const Vec* b, Vec* ab);
void C_VECSubtract(const Vec* a, const Vec* b, Vec* ab);
void C_VECScale(const Vec* src, Vec* dst, f32 scale);
void C_VECNormalize(const Vec* src, Vec* unit);
f32 C_VECSquareMag(const Vec* v);
f32 C_VECMag(const Vec* v);
f32 C_VECDotProduct(const Vec* a, const Vec* b);
void C_VECCrossProduct(const Vec* a, const Vec* b, Vec* axb);
f32 C_VECSquareDistance(const Vec* a, const Vec* b);
f32 C_VECDistance(const Vec* a, const Vec* b);

#if defined(RE4DC_VEC_NORM_INLINE) && RE4DC_VEC_NORM_INLINE == 2
// GAME_VEC_NORM_INLINE=2 (include/vec.h, sdk mtx.c): every inline normalize compared with C_VECNormalize.
void re4dc_log(const char* fmt, ...);
static u32 vnrmCalls, vnrmBad;
void re4dc_vnorm_check(const Vec* src, const Vec* unit)
{
    Vec ref;
    C_VECNormalize(src, &ref);
    vnrmCalls++;
    vnrmBad += __builtin_memcmp(&ref, unit, sizeof(Vec)) != 0;
    if ((vnrmCalls & 0xFFF) == 0) {
        re4dc_log("VNRM calls=%u mismatch=%u\n", vnrmCalls, vnrmBad);
    }
}
#endif

// GAME_PS_ALIAS (game30.mk): platform/ps_alias.ld binds the PS* names to the C_* bodies at
// link time instead (same arithmetic, one call frame less per call).
#if !RE4DC_PS_ALIAS
void PSMTXIdentity(Mtx m) { C_MTXIdentity(m); }
void PSMTXCopy(const Mtx s, Mtx d) { C_MTXCopy(s, d); }
void PSMTXConcat(const Mtx a, const Mtx b, Mtx ab) { C_MTXConcat(a, b, ab); }
void PSMTXTranspose(const Mtx s, Mtx d) { C_MTXTranspose(s, d); }
u32 PSMTXInverse(const Mtx s, Mtx d) { return C_MTXInverse(s, d); }
void PSMTXRotRad(Mtx m, char axis, f32 rad) { C_MTXRotRad(m, axis, rad); }
void PSMTXRotTrig(Mtx m, char axis, f32 s, f32 c) { C_MTXRotTrig(m, axis, s, c); }
void PSMTXRotAxisRad(Mtx m, const Vec* axis, f32 rad) { C_MTXRotAxisRad(m, axis, rad); }
void PSMTXTrans(Mtx m, f32 x, f32 y, f32 z) { C_MTXTrans(m, x, y, z); }
void PSMTXTransApply(const Mtx s, Mtx d, f32 x, f32 y, f32 z) { C_MTXTransApply(s, d, x, y, z); }
void PSMTXScale(Mtx m, f32 x, f32 y, f32 z) { C_MTXScale(m, x, y, z); }
void PSMTXQuat(Mtx m, const Quaternion* q) { C_MTXQuat(m, q); }
void PSMTXMultVec(const Mtx m, const Vec* s, Vec* d) { C_MTXMultVec(m, s, d); }
void PSMTXMultVecArray(const Mtx m, const Vec* s, Vec* d, u32 n) { C_MTXMultVecArray(m, s, d, n); }
void PSMTXMultVecSR(const Mtx m, const Vec* s, Vec* d) { C_MTXMultVecSR(m, s, d); }
void PSMTX44MultVec(const Mtx44 m, const Vec* s, Vec* d) { C_MTX44MultVec(m, s, d); }
void PSVECAdd(const Vec* a, const Vec* b, Vec* ab) { C_VECAdd(a, b, ab); }
void PSVECSubtract(const Vec* a, const Vec* b, Vec* ab) { C_VECSubtract(a, b, ab); }
void PSVECScale(const Vec* s, Vec* d, f32 k) { C_VECScale(s, d, k); }
void PSVECNormalize(const Vec* s, Vec* d) { C_VECNormalize(s, d); }
f32 PSVECSquareMag(const Vec* v) { return C_VECSquareMag(v); }
f32 PSVECMag(const Vec* v) { return C_VECMag(v); }
f32 PSVECDotProduct(const Vec* a, const Vec* b) { return C_VECDotProduct(a, b); }
void PSVECCrossProduct(const Vec* a, const Vec* b, Vec* d) { C_VECCrossProduct(a, b, d); }
f32 PSVECSquareDistance(const Vec* a, const Vec* b) { return C_VECSquareDistance(a, b); }
f32 PSVECDistance(const Vec* a, const Vec* b) { return C_VECDistance(a, b); }
#endif

// mtx44.c carries PSMTX44MultVec only as paired-single asm; the C form.
void C_MTX44MultVec(const Mtx44 m, const Vec* src, Vec* dst)
{
    f32 x = src->x, y = src->y, z = src->z;
    f32 ox = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3];
    f32 oy = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3];
    f32 oz = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3];
    f32 w = m[3][0] * x + m[3][1] * y + m[3][2] * z + m[3][3];
    w = w == 0.0f ? 1.0f : 1.0f / w;
    dst->x = ox * w;
    dst->y = oy * w;
    dst->z = oz * w;
}

#if !RE4DC_SH4_MATH  // GAME_SH4_MATH: platform/mtx_sh4.S (_re4dc_sh4_MTXReorder)
// The SDK's PSMTXReorder: a 3x4 row matrix into the column-major 4x3 form the
// skinning palette uses (rotation columns first, translation last).
void PSMTXReorder(const Mtx src, ROMtx dst)
{
    for (int i = 0; i < 3; i++) {
        dst[i][0] = src[0][i];
        dst[i][1] = src[1][i];
        dst[i][2] = src[2][i];
    }
    dst[3][0] = src[0][3];
    dst[3][1] = src[1][3];
    dst[3][2] = src[2][3];
}
#endif

}  // extern "C"
