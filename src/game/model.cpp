#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_pose_reset(const void*);
#endif
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
#include "gc_asset_motion_source.h"
#endif
// game/model: the model class hierarchy (D:/Bio4/Prog/model.cpp). cModel (a cCoord with parts) owns
// a chain of cModelInfo (one per .bin model data + TPL: the body, then added parts models) and a
// linked list of cParts (one per joint, from cPartsMgr), and carries the MotionWork, collision
// info, light info and draw parameters used by every character/object. Also: pointer relocation
// of model/TPL files (calcModelAddr / calcTplAddr and their inverses), bounding boxes, the parts
// and model-info managers (PartsMgr, ModInfoMgr), and the debug skeleton display.
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "actor_lifetime.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#endif
#include "atari.h"
#include "model.h"
#include "motion.h"
#include "global.h"
#include "db_log.h"
#include "va_ppc.h"
#include "main_mem.h"
#include "dbmodule.h"
#include "eprintf.h"
#include "scheduler.h"
#if defined(RE4DC_PWC_DIAG) && RE4DC_PWC_DIAG
#include <string.h>
// GAME_PWC_DIAG (game30.mk, design-logic P1): partsWorldCalc's non-uniform-scale path multiplies a
// matrix by a diagonal scale matrix twice (PSMTXScale + PSMTXConcat, i.e. two full 3x4 concats of
// 63 FP ops each). With b = PSMTXScale(sx, sy, sz) (off-diagonal and translation words +0.0f), the
// contract-off concat kernel (platform/mtx_sh4.S) computes, for row i:
//   j<3: ab_ij = add(add(mul(a_i0,b_0j), mul(a_i1,b_1j)), add(mul(a_i2,b_2j), +0))
//   j=3: ab_i3 = add(add(add(mul(a_i0,+0), mul(a_i1,+0)), mul(a_i2,+0)), a_i3)
// pwcMulDiag below issues exactly the reduced dataflow (see its comment); the exact reduction is proven
// on the host (design-logic/proofs/pwc_diag_check.c: 229M cases x {IEEE, FTZ+DAZ}, 0 mismatches) and at
// runtime by the =2 check build.
// GAME_PWC_DIAG=2 (check build): computes both and counts word mismatches (tick log "pwcdiag=").
extern "C" {
unsigned long re4dc_pwc_diag_checks;
unsigned long re4dc_pwc_diag_mismatch;
}
// out = a * PSMTXScale(sx, sy, sz); out may equal a (all loads precede the stores).
// Kernel words with b = diag(s): ab_ij (j<3) reduces to add(mul(a_ij, s_j), +0) (the other terms
// are a_ik*(+0) = signed zeros; a nonzero x absorbs them and a zero sum is +0 because of the
// kernel's literal +0 term); ab_i3 is the kernel's own column-3 dataflow with b_k3 = +0. Only a
// non-finite a_ik (k<3) breaks the reduction (a_ik*(+0) = NaN): z_i = add(add(a_i0*0, a_i1*0),
// a_i2*0) is NaN exactly then, and z_i is also the first half of ab_i3, so the guard costs one
// compare. Non-finite rotation words: the original PSMTXScale + PSMTXConcat.
static inline __attribute__((always_inline)) void pwcMulDiag(MtxPtr a, f32 sx, f32 sy, f32 sz, MtxPtr out)
{
    const f32 zero = 0.0f;
    f32 z0 = (a[0][0] * zero + a[0][1] * zero) + a[0][2] * zero;
    f32 z1 = (a[1][0] * zero + a[1][1] * zero) + a[1][2] * zero;
    f32 z2 = (a[2][0] * zero + a[2][1] * zero) + a[2][2] * zero;
    f32 g = (z0 + z1) + z2;
    if (__builtin_expect(g != g, 0)) {
        Mtx t;
        PSMTXScale(t, sx, sy, sz);
        PSMTXConcat(a, t, out);
        return;
    }
    for (int i = 0; i < 3; i++) {
        f32 zi = (i == 0) ? z0 : (i == 1) ? z1 : z2;
        f32 a0 = a[i][0], a1 = a[i][1], a2 = a[i][2], a3 = a[i][3];
        out[i][0] = a0 * sx + zero;
        out[i][1] = a1 * sy + zero;
        out[i][2] = a2 * sz + zero;
        out[i][3] = zi + a3;
    }
}
#if RE4DC_PWC_DIAG == 2
static void pwcMulDiagChecked(MtxPtr a, f32 sx, f32 sy, f32 sz, MtxPtr out)
{
    Mtx fast;
    Mtx ref;
    Mtx t;
    pwcMulDiag(a, sx, sy, sz, fast);
    PSMTXScale(t, sx, sy, sz);
    PSMTXConcat(a, t, ref);
    re4dc_pwc_diag_checks++;
    if (memcmp(fast, ref, sizeof(Mtx)) != 0) {
        re4dc_pwc_diag_mismatch++;
    }
    PSMTXCopy(ref, out);
}
#define PWC_MUL_DIAG pwcMulDiagChecked
#else
#define PWC_MUL_DIAG pwcMulDiag
#endif
#endif
#include "math_sub.h"
#include "tpl.h"
#if defined(RE4DC_GAME) && !defined(__PPC__)
extern "C" void re4dc_model_assets_changed();
#endif

// Model / parts / model info (cModel, cParts, cModelInfo) and their pools (PartsMgr, ModInfoMgr).

#define HALT()                                                    \
    {                                                             \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
        RE4DC_HALT_STORE();                                       \
    }

// A relocated pointer into main memory.
#define PTR_OK(p) ((u32) (p) >= RE4_MEM_LO && (u32) (p) <= RE4_MEM_HI)

extern "C" {
void OSReport(const char* fmt, ...);
void PartsWorldPosCalc(cModel* m);
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
extern "C" void re4dc_gcasset_capture_model(const void*);
#endif
void calcModelAddr(ModelData* data);
void calcModelOffset(ModelData* data);
void calcTplOffset(TEXPalette* tpl);
void getBoundingBox(ModelData* data, ModelBound* bound);
void drawBoundingBox(Mtx m, ModelBound* bound);
int GetModelInfoNum(cModelInfo* info);
// MotionMove takes a second argument (pl_npc.cpp MotionMoveF)
int MotionMoveF(cModel* m, int flag) asm("MotionMove");
// cAtariInfo lives in cModel's union (no member constructor call): constructed by hand
#if defined(__PPC__)
cAtariInfo* AtariInfoConstruct(cAtariInfo* p) asm("__10cAtariInfo");
#else
// The constructor only zeroes the object (atariInfo.cpp).
static inline cAtariInfo* AtariInfoConstruct(cAtariInfo* p)
{
    __builtin_memset(p, 0, sizeof(cAtariInfo));
    RE4DC_ATARI_TOUCH(p);
    return p;
}
#endif
}
cModelInfo* GetModelInfoAddr(cModelInfo* info, int no);

cModInfoMgr* cModel::mm = &ModInfoMgr;
cPartsMgr* cModel::pm = &PartsMgr;

// `mm` read as a struct member: keeps its load below a preceding store through `this`
struct ModInfoMgrPtr {
    cModInfoMgr* p;
};
#define MM (((ModInfoMgrPtr*) &cModel::mm)->p)

static inline u32 U32Get(u32& v)
{
    return v;
}

// Clears a model's light-area state.
// The 0.0 pool load of the light area sinks below the three word stores: an inlined helper
// (integrate.c drops RTX_UNCHANGING_P from the pool MEM).
static inline void LightAreaInit(EmLightArea* la)
{
    la->x0 = 0;
    la->flags = 0;
    la->lightNo = 0;
    la->scale = 0.0f;
}

// Byte stores through this setter come from a word-sized zero pseudo, which the word stores
// after the following `if` share (modelInit).
static inline void U8Set(u8& d, u8 v)
{
    d = v;
}

// Empty model: collision/light-area info constructed, no parts, no model info, motion cleared,
// alpha_omit 0xFF.
cModel::cModel()
{
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::motion_source_reset(this);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    AtariInfoConstruct(&atari);
    LightAreaInit(&litArea);
    alpha_omit = 0xFF;
    speed.x = 0.0f;
    speed.y = 0.0f;
    speed.z = 0.0f;
    pos_old.x = 0.0f;
    pos_old.y = 0.0f;
    pos_old.z = 0.0f;
    Wall_norm.x = 0.0f;
    Wall_norm.y = 0.0f;
    Wall_norm.z = 0.0f;
    pParts = 0;
    r_no_0 = 0;
    r_no_1 = 0;
    r_no_2 = 0;
    r_no_3 = 0;
    id = 0;
    type = 0;
    nParts = 0;
    pFloor_norm = 0;
    TevScaleGroup = 0;
    kindid = 0;
    ot_type = 0;
    pCldShMd = 0;
    Shd_color = 0;
    CullMode = 0;
    Shader_type = 0;
    Refract_pow = 0;
    Fix_parts = 0;
    Fix_pos.x = 0.0f;
    invisible_trg = 0;
    invisible_old = 0;
    invisible_mode = 0;
    invisible_busy = 0;
    invisible_timer = 0;
    pModelInfo = 0;
    pShadowModelInfo = 0;
    Fix_pos.y = 0.0f;
    Fix_pos.z = 0.0f;
    invisible_factor = 0.0f;
    memclr_asm(&Motion, 0xD0);
    Motion.blend = 0;
    Motion.flip = 0;
    inscreen_pos = 0;
    pPath = 0;
    pTexChg = 0;
}

// Loads a model: relocates bin/tpl, creates the first cModelInfo, builds the parts list from the
// model's joints (initJoint), sets visible/alive flags (invisible_factor 1, or 0 when the
// System_flg 0x800000 fade-in mode), enemies (kindid 0) get be_flag 0x10. Returns the info (0 on failure).
int cModel::modelInit(void* bin, void* tpl)
{
    cModelInfo* info;

    if (bin == NULL) {
        pLog->err(0, 0, "modelInit() : bin_addr == NULL.");
        return 0;
    }
    if (tpl == NULL) {
        pLog->err(0, 0, "modelInit() : tex_addr == NULL.");
        return 0;
    }
    calcModelAddr((ModelData*) bin);
    calcTplAddr((TEXPalette*) tpl);
    if (pModelInfo != NULL) {
        releaseModelInfo();
    }
    info = mm->create(bin, tpl);
    if (info == NULL) {
        pLog->err(0, 0, "modelInit() cModelInfo alloc failed.");
        return 0;
    }
    addModel(info);
    if (initJoint(bin) != 1) {
        pLog->err(0, 0, "ModelInit()  Parts allocate was failed.");
        releaseModelInfo();
        return 0;
    }
    if (pG->System_flg & 0x800000) {
        invisible_factor = 0.0f;
    } else {
        invisible_factor = 1.0f;
    }
    be_flag |= 6;
    invisible_factor2 = 1.0f;
    U8Set(TevScaleGroup, 0);
    U8Set(CullMode, 0);
    if (kindid == 0) {
        be_flag |= 0x10;
    }
    pShadowModelInfo = 0;
    Motion.Seq_speed = 1.0f;
    pCldShMd = 0;
    p2A4 = 0;
    return (int) info;
}

// Creates nParts cParts for the model's joints, links parents, sets rest offsets and the
// blend/flip tables. 0 when the parts pool is exhausted.
int cModel::initJoint(void* bin)
{
    releaseJoint();
    nParts = ((ModelData*) bin)->nParts;
    if (nParts == 0) {
        return 1;
    }
    if (makePartsList(0) == 0) {
        nParts = 0;
        pParts = 0;
        return 0;
    }
    setPartsParent();
    setPartsOffset(bin);
    setJointInfo(bin);
    return 1;
}

// Frees the parts list.
void cModel::releaseJoint()
{
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::motion_source_reset(this);
#endif
    if (pParts != NULL) {
        releasePartsList(0);
    }
}

// Puts every parts at its rest position (the joint centres from the model data), computes the rest
// matrices at the origin (lt_inv_mat = inverse rest translation, used by skinning) and then the
// world matrices at the model position; initialises world_old.
void cModel::setPartsOffset(void* bin)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cParts* p = pList;
    ModelDataHead* rec;
    Vec pos;
    u32 i;

    calcModelAddr((ModelData*) bin);
    rec = ((ModelData*) bin)->pHead;
    for (i = 0; i < nParts; i++) {
        p->pos.x = rec->center.x;
        p->pos.y = rec->center.y;
        p->pos.z = rec->center.z;
        rec++;
        p = p->pList;
    }
    pos.x = this->pos.x;
    pos.y = this->pos.y;
    pos.z = this->pos.z;
    PSMTXIdentity(mat);
    PSMTXTrans(mat, 0.0f, 0.0f, 0.0f);
    partsMatCalc();
    partsWorldCalc();
    this->pos.x = pos.x;
    this->pos.y = pos.y;
    this->pos.z = pos.z;
    for (p = pList; p; p = p->pList) {
        PSMTXIdentity(p->lt_inv_mat);
        p->lt_inv_mat[0][3] = -p->mat[0][3];
        p->lt_inv_mat[1][3] = -p->mat[1][3];
        p->lt_inv_mat[2][3] = -p->mat[2][3];
    }
    PSMTXTrans(mat, this->pos.x, this->pos.y, this->pos.z);
    partsMatCalc();
    partsWorldCalc();
    for (p = pList; p; p = p->pList) {
        p->world_old = p->world;
        p->world_old2 = p->world;
    }
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
    // Only after both actual rest/world matrix writes, never mere binding.
    re4dc_gcasset::motion_source_note(this,bin,re4dc_gcasset::MotionBind);
#endif
}

// Links each parts to its parent joint from the model data (0xFF = the model itself).
void cModel::setPartsParent()
{
    cParts* p = pList;
    ModelDataHead* rec = pModelInfo->pData->pHead;
    u32 i;

    for (i = 0; i < nParts; i++) {
        if (rec->parentNo > 0xFE) {
            p->pParent = this;
        } else {
            p->pParent = getPartsPtr(rec->parentNo);
        }
        p = p->pList;
        rec++;
    }
}

// Rebuilds every parts' local matrix (l_mat, copied to mat) from its ang/pos/scale.
#if defined(RE4DC_PMC_KERNEL) && RE4DC_PMC_KERNEL && defined(__sh__)
// GAME_PMC_KERNEL (game30.mk; the 30 fps rethink, step 2): parts whose rotation is in RotMatrix's memo
// run through platform/pmc_sh4.S (an exact twin of the four calls below: memo words, pos, the scale
// products, the copy to mat); the kernel returns each memo miss, which takes the four calls, and resumes
// with its pList.
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Winvalid-offsetof"
static_assert(__builtin_offsetof(cParts, pos) == 0x94 && __builtin_offsetof(cParts, ang) == 0xA0 &&
              __builtin_offsetof(cParts, scale) == 0xAC && __builtin_offsetof(cParts, l_mat) == 0x3C &&
              __builtin_offsetof(cParts, mat) == 0x0C && __builtin_offsetof(cParts, pList) == 0xF4,
              "pmc_sh4.S offsets");
#pragma GCC diagnostic pop
extern "C" cParts* re4dc_pmc_run(cParts* p);
#endif
void cModel::partsMatCalc()
{
    cParts* p;

#if defined(RE4DC_PMC_KERNEL) && RE4DC_PMC_KERNEL && defined(__sh__)
    for (p = pList; p;) {
        p = re4dc_pmc_run(p);
        if (!p) {
            break;
        }
        MtxPtr m = p->l_mat;
        RotMatrix(m, &p->ang);
        TransMatrix(m, &p->pos);
        ScaleMatrix(m, &p->scale);
        PSMTXCopy(m, p->mat);
        p = p->pList;
    }
#else
    for (p = pList; p; p = p->pList) {
        MtxPtr m = p->l_mat;
        RotMatrix(m, &p->ang);
        TransMatrix(m, &p->pos);
        ScaleMatrix(m, &p->scale);
        PSMTXCopy(m, p->mat);
    }
#endif
}

// Base move: nothing.
// Out-of-line inlines. Deferred-inline emission is definition order: ~cModelInfo, then the two
// managers (implicit dtor + in-class memAlloc/memFree/memClear, model.h), ~cParts, ~cModel, then
// these three and getPartsPtr, then the cManager::destroy instantiations and the ~cManager
// instantiations the synthesized manager dtors request in finish_file.
inline void cModel::move()
{
}

// be_flag 0x800: the model keeps moving while the game is suspended (events, pause).
inline void cModel::setNoSuspend(int on)
{
    if (on) {
        be_flag |= 0x800;
    } else {
        be_flag &= ~0x800;
    }
}

// 1 when the model is drawn (be_flag bit 1).
RE4_INLINE int cModel::isTrans()
{
    int ret = 0;

    if ((be_flag & 2) && be_flag != 0) {
        ret = 1;
    }
    return ret;
}

// Parts `no` (-1: the model itself); NULL and a log when the chain is shorter. Defined here so
// that the callers below inline it while setPartsParent above calls it.
RE4_INLINE cModel* cModel::getPartsPtr(int no)
{
    cModel* p = pParts;
    int cnt;

    if (no < 0) {
        return this;
    }
    cnt = no;
    if (!PTR_OK(p)) {
        return 0;
    }
    if (be_flag & 0x2000) {
        p = (cModel*) ((cParts*) p + no);
    } else if (no--) {
        do {
            cModel* next = p->pParts;
            if (!PTR_OK(next)) {
                pLog->err(0, 0, "cModel::getPartsPtr() cParts NO ERROR %d", cnt);
                return 0;
            }
            p = next;
        } while (no--);
    }
    return p;
}

// Motion blend: for every parts, mixes the current l_mat (rotation as a quaternion slerp, scale
// and translation linearly) with the parts' ang/pos/scale by `rate` (1 = only the new pose).
void cModel::matBlend(f32 rate)
{
    cParts* p;
    Mtx m;
    Quaternion q0;
    Quaternion q1;
    Quaternion q2;
    Vec pos;
    Vec len;
    Vec vx;
    Vec vy;
    Vec vz;
    Vec trans;

    for (p = pList; p; p = p->pList) {
        // COMPILER-DIFF: 3 (address-copy shape). The original computes `&p->worldMat` into a temp
        // and copies it (`addi r0,r31,60; mr r28,r0`). With the temp pinned to r0 and kept live
        // past the copy by the codeless anchor below (before the PSVECMag call), combine cannot
        // fold the copy into the addi (the r0 set is still needed) and regmove skips hard registers.
        register MtxPtr t PPC_REG("r0") = p->l_mat;
        MtxPtr wm = t;

        vx.x = p->l_mat[0][0];
        vx.y = p->l_mat[1][0];
        vx.z = p->l_mat[2][0];
        asm("" : "=m"(vx) : "r"(t)); // COMPILER-DIFF: 3 (keep-alive for the r0 temp)
        len.x = PSVECMag(&vx);
        vy.x = p->l_mat[0][1];
        vy.y = p->l_mat[1][1];
        vy.z = p->l_mat[2][1];
        len.y = PSVECMag(&vy);
        vz.x = p->l_mat[0][2];
        vz.y = p->l_mat[1][2];
        vz.z = p->l_mat[2][2];
        len.z = PSVECMag(&vz);
        trans.x = p->l_mat[0][3];
        trans.y = p->l_mat[1][3];
        trans.z = p->l_mat[2][3];
        if (len.x != 0.0f && len.y != 0.0f && len.z != 0.0f) {
            if (len.x != 1.0f) {
                PSVECScale(&vx, &vx, 1.0f / len.x);
            }
            if (len.y != 1.0f) {
                PSVECScale(&vy, &vy, 1.0f / len.y);
            }
            if (len.z != 1.0f) {
                PSVECScale(&vz, &vz, 1.0f / len.z);
            }
            p->l_mat[0][0] = vx.x;
            wm[1][0] = vx.y;
            wm[2][0] = vx.z;
            wm[0][1] = vy.x;
            wm[1][1] = vy.y;
            wm[2][1] = vy.z;
            wm[0][2] = vz.x;
            wm[1][2] = vz.y;
            wm[2][2] = vz.z;
            wm[0][3] = trans.x;
            wm[1][3] = trans.y;
            wm[2][3] = trans.z;
        }
        {
            f32 inv = 1.0f - rate;
            PSVECScale(&len, &len, inv);
            PSVECScale(&p->scale, &p->scale, rate);
            PSVECAdd(&p->scale, &len, &p->scale);
            pos.x = p->pos.x * rate + p->l_mat[0][3] * inv;
            pos.y = p->pos.y * rate + p->l_mat[1][3] * inv;
            pos.z = p->pos.z * rate + p->l_mat[2][3] * inv;
            p->pos = pos;
            PSMTXIdentity(m);
            RotMatrix(m, &p->ang);
            C_QUATMtx(&q0, m);
            C_QUATMtx(&q1, wm);
            C_QUATSlerp(&q0, &q1, &q2, inv);
            PSMTXQuat(wm, &q2);
            TransMatrix(wm, &p->pos);
            ScaleMatrix(wm, &p->scale);
        }
    }
}

// Places the model at pos/rot, clears its motion and rebuilds the matrices (player after events).
void cModel::zeroPartsPosInit(Vec* pos, Vec* rot)
{
    setPos(pos);
    setAng(rot);
    MotionClear(this, 0);
    matUpdate();
}

// Computes every parts' world matrix from its parent (parent mat * l_mat, with non-uniform parent
// scale removed and re-applied), applies pending addRot corrections (flag 0x40000000), stores the
// world position and the accumulated r_scale; parts with motParts flag 2 (IK-fixed) are skipped.
#if defined(RE4DC_SKEL_FTRV) && RE4DC_SKEL_FTRV && defined(__sh__)
// GAME_SKEL_FTRV (game30.mk; square plan, one gameplay matrix chain; last-bit FP policy, NOT exact):
// inside a Ganado's update (re4dc_skel_scope, counted up by a guard in cEm10::move) partsWorldCalc
// computes each part with three FTRVs and no temporaries. Row i of mat = P l_mat is l_mat^T applied
// to row i of P, so the part's own l_mat rows go into XMTRX (plus the constant row 0 0 0 1) and the
// parent's three rows, read in place, come out as mat's rows; their fourth element is world (the
// original's MultVec of l_mat's translation, which its TransMatrix writes over mat's translation).
// A non-uniform parent scale (P S^-1 L S) folds in as P's rows times S^-1 and l_mat's columns times
// S, with l_mat's translation column row-scaled by S so that world stays P (l_mat translation).
// Parts with addRot pending finish on the original code.
// =2 (check build): the FTRV pass runs first into a shadow buffer (a parent computed earlier in the
// same pass is read from the shadow, as the live pass would), then the original runs live and the
// two are compared ("SKELFTRV" log line); the logic trace stays STRICT.
extern "C" int re4dc_skel_scope;
int re4dc_skel_scope;
namespace {
struct SkelShadow {
    f32 m[12];
    Vec w;
};
// XMTRX = the 3x4 row-major matrix at L as columns 0-2 (row k of L = column k), column 3 = 0 0 0 1.
inline void skelLoadRows(const f32* L)
{
    __asm__ __volatile__("frchg\n\t"
                         "fmov.s  @%0+,fr0\n\t" "fmov.s  @%0+,fr1\n\t" "fmov.s  @%0+,fr2\n\t" "fmov.s  @%0+,fr3\n\t"
                         "fmov.s  @%0+,fr4\n\t" "fmov.s  @%0+,fr5\n\t" "fmov.s  @%0+,fr6\n\t" "fmov.s  @%0+,fr7\n\t"
                         "fmov.s  @%0+,fr8\n\t" "fmov.s  @%0+,fr9\n\t" "fmov.s  @%0+,fr10\n\t" "fmov.s  @%0+,fr11\n\t"
                         "fldi0   fr12\n\t" "fldi0   fr13\n\t" "fldi0   fr14\n\t" "fldi1   fr15\n\t"
                         "frchg\n"
                         : "+r"(L)
                         :
                         : "memory");
}
// out rows 0-2 = XMTRX x (P row i, scaled by is for columns 0-2).
inline void skelRows(const f32* P, f32 isx, f32 isy, f32 isz, f32* out)
{
    register f32 a0 __asm__("fr0") = P[0] * isx;
    register f32 a1 __asm__("fr1") = P[1] * isy;
    register f32 a2 __asm__("fr2") = P[2] * isz;
    register f32 a3 __asm__("fr3") = P[3];
    register f32 b0 __asm__("fr4") = P[4] * isx;
    register f32 b1 __asm__("fr5") = P[5] * isy;
    register f32 b2 __asm__("fr6") = P[6] * isz;
    register f32 b3 __asm__("fr7") = P[7];
    register f32 c0 __asm__("fr8") = P[8] * isx;
    register f32 c1 __asm__("fr9") = P[9] * isy;
    register f32 c2 __asm__("fr10") = P[10] * isz;
    register f32 c3 __asm__("fr11") = P[11];
    __asm__ __volatile__("ftrv    xmtrx,fv0\n\t"
                         "ftrv    xmtrx,fv4\n\t"
                         "ftrv    xmtrx,fv8\n"
                         : "+f"(a0), "+f"(a1), "+f"(a2), "+f"(a3), "+f"(b0), "+f"(b1), "+f"(b2), "+f"(b3), "+f"(c0),
                           "+f"(c1), "+f"(c2), "+f"(c3));
    out[0] = a0; out[1] = a1; out[2] = a2; out[3] = a3;
    out[4] = b0; out[5] = b1; out[6] = b2; out[7] = b3;
    out[8] = c0; out[9] = c1; out[10] = c2; out[11] = c3;
}
inline void skelRowsUniform(const f32* P, f32* out)
{
    register f32 a0 __asm__("fr0") = P[0];
    register f32 a1 __asm__("fr1") = P[1];
    register f32 a2 __asm__("fr2") = P[2];
    register f32 a3 __asm__("fr3") = P[3];
    register f32 b0 __asm__("fr4") = P[4];
    register f32 b1 __asm__("fr5") = P[5];
    register f32 b2 __asm__("fr6") = P[6];
    register f32 b3 __asm__("fr7") = P[7];
    register f32 c0 __asm__("fr8") = P[8];
    register f32 c1 __asm__("fr9") = P[9];
    register f32 c2 __asm__("fr10") = P[10];
    register f32 c3 __asm__("fr11") = P[11];
    __asm__ __volatile__("ftrv    xmtrx,fv0\n\t"
                         "ftrv    xmtrx,fv4\n\t"
                         "ftrv    xmtrx,fv8\n"
                         : "+f"(a0), "+f"(a1), "+f"(a2), "+f"(a3), "+f"(b0), "+f"(b1), "+f"(b2), "+f"(b3), "+f"(c0),
                           "+f"(c1), "+f"(c2), "+f"(c3));
    out[0] = a0; out[1] = a1; out[2] = a2; out[3] = a3;
    out[4] = b0; out[5] = b1; out[6] = b2; out[7] = b3;
    out[8] = c0; out[9] = c1; out[10] = c2; out[11] = c3;
}
// The original non-uniform-scale arithmetic for one part (a parent scale component of 0).
void skelScaledOriginal(const f32* P, const Vec& rs, const f32* L, f32* M)
{
    Mtx Pm, Lm, m1;
    __builtin_memcpy(Pm, P, sizeof(Mtx));
    __builtin_memcpy(Lm, L, sizeof(Mtx));
    MtxPtr Mm = (MtxPtr) M;
    PSMTXScale(m1, (rs.x != 0.0f) ? 1.0f / rs.x : 0.0f, (rs.y != 0.0f) ? 1.0f / rs.y : 0.0f,
               (rs.z != 0.0f) ? 1.0f / rs.z : 0.0f);
    PSMTXConcat(Pm, m1, m1);
    PSMTXConcat(m1, Lm, Mm);
    PSMTXScale(m1, rs.x, rs.y, rs.z);
    PSMTXConcat(Mm, m1, Mm);
    Vec t = {L[3], L[7], L[11]};
    Vec w;
    PSMTXMultVec(Pm, &t, &w);
    M[3] = w.x;
    M[7] = w.y;
    M[11] = w.z;
}
#if RE4DC_SKEL_FTRV == 2
extern "C" void re4dc_log(const char* fmt, ...);
SkelShadow skelShadowBuf[256];
const void* skelShadowKey[256];
Vec skelShadowRs[256];
u32 skelChkCalls, skelChkParts, skelChkMiss, skelChkNan, skelChkAll, skelChkLen, skelChkIds[64];
f32 skelChkWorld, skelChkRot, skelChkTr;
inline bool skelFinite(f32 v)
{
    u32 b;
    __builtin_memcpy(&b, &v, 4);
    return ((b >> 23) & 255U) != 255U;
}
#endif

// One part-world pass on FTRV. out == 0: live, writes mat / world / r_scale as the original does;
// else the k-th part not skipped goes to out[k] and nothing in the model is written.
u32 skelPass(cModel* self, SkelShadow* out, u32* miss)
{
    u32 n = 0;
    for (cParts* p = self->pList; p; p = p->pList) {
        const u32 fl = p->motParts.flags;
        if (fl & 2) {
            continue;
        }
        const cCoord* parent = p->pParent;
        const f32* P = &parent->mat[0][0];
        Vec rs = parent->r_scale;
#if RE4DC_SKEL_FTRV == 2
        if (out) {
            for (u32 j = n; j-- > 0;) {
                if (skelShadowKey[j] == parent) {
                    P = out[j].m;
                    rs = skelShadowRs[j];
                    break;
                }
            }
        }
#endif
        f32* M = out ? (n < 256 ? out[n].m : out[255].m) : &p->mat[0][0];
        const f32* L = &p->l_mat[0][0];
        if ((rs.x != rs.y || rs.y != rs.z) && (rs.x == 0.0f || rs.y == 0.0f || rs.z == 0.0f)) {
            skelScaledOriginal(P, rs, L, M);   // a zero scale cannot cancel through S^-1: original arithmetic
        } else if (rs.x != rs.y || rs.y != rs.z) {
            const f32 ix = (rs.x != 0.0f) ? 1.0f / rs.x : 0.0f;
            const f32 iy = (rs.y != 0.0f) ? 1.0f / rs.y : 0.0f;
            const f32 iz = (rs.z != 0.0f) ? 1.0f / rs.z : 0.0f;
            f32 Ls[12];
            Ls[0] = L[0] * rs.x; Ls[1] = L[1] * rs.y; Ls[2] = L[2] * rs.z; Ls[3] = L[3] * rs.x;
            Ls[4] = L[4] * rs.x; Ls[5] = L[5] * rs.y; Ls[6] = L[6] * rs.z; Ls[7] = L[7] * rs.y;
            Ls[8] = L[8] * rs.x; Ls[9] = L[9] * rs.y; Ls[10] = L[10] * rs.z; Ls[11] = L[11] * rs.z;
            skelLoadRows(Ls);
            skelRows(P, ix, iy, iz, M);
        } else {
            skelLoadRows(L);
            skelRowsUniform(P, M);
        }
        Vec w = {M[3], M[7], M[11]};
        if (fl & 0x40000000) {
            Mtx m2;
            f32(*Mm)[4] = (f32(*)[4]) M;
            if (!out) {
                p->motParts.flags &= ~0x40000000;
            }
            PSMTXRotRad(m2, 'x', p->addRot.x);
            PSMTXConcat(Mm, m2, Mm);
            PSMTXRotRad(m2, 'z', p->addRot.z);
            PSMTXConcat(Mm, m2, Mm);
            PSMTXRotRad(m2, 'y', p->addRot.y);
            PSMTXConcat(m2, Mm, Mm);
            TransMatrix(Mm, &w);
        }
        Vec r;
        r.x = rs.x * p->scale.x;
        r.y = rs.y * p->scale.y;
        r.z = rs.z * p->scale.z;
        if (out) {
#if RE4DC_SKEL_FTRV == 2
            if (n < 256) {
                out[n].w = w;
                skelShadowKey[n] = p;
                skelShadowRs[n] = r;
            } else if (miss) {
                ++*miss;
            }
#endif
        } else {
            p->world = w;
            p->r_scale = r;
        }
        n++;
    }
    return n;
}
#if RE4DC_SKEL_FTRV == 2
void skelCompare(cModel* self, const SkelShadow* sh, u32 n, u32 miss)
{
    u32 i = 0;
    skelChkCalls++;
    skelChkMiss += miss;
    skelChkIds[self->id & 63] += n;
    for (cParts* p = self->pList; p; p = p->pList) {
        if (p->motParts.flags & 2) {
            continue;
        }
        if (i >= n || i >= 256) {
            break;
        }
        const f32* a = &p->mat[0][0];
        const f32* b = sh[i].m;
        for (int j = 0; j < 12; j++) {
            if (!skelFinite(b[j])) {
                skelChkNan++;
                continue;
            }
            const f32 d = __builtin_fabsf(a[j] - b[j]);
            if ((j & 3) == 3) {
                if (d > skelChkTr) skelChkTr = d;
            } else if (d > skelChkRot) {
                skelChkRot = d;
            }
        }
        const f32 dw[3] = {p->world.x - sh[i].w.x, p->world.y - sh[i].w.y, p->world.z - sh[i].w.z};
        for (int j = 0; j < 3; j++) {
            const f32 d = __builtin_fabsf(dw[j]);
            if (d > skelChkWorld) skelChkWorld = d;
        }
        i++;
        skelChkParts++;
    }
    if (i != n) {
        skelChkLen++;
    }
    if ((skelChkCalls & 0x3FF) == 0) {
        re4dc_log("SKELFTRV calls=%u parts=%u all_parts=%u overflow=%u len_mismatch=%u nonfinite=%u "
                  "max_world=%.6g max_rot=%.6g max_trans=%.6g ids=%u:%u,%u:%u,%u:%u,%u:%u" "\n",
                  skelChkCalls, skelChkParts, skelChkAll, skelChkMiss, skelChkLen, skelChkNan,
                  double(skelChkWorld), double(skelChkRot), double(skelChkTr), 0x10U, skelChkIds[0x10],
                  0x12U, skelChkIds[0x12], 0x15U, skelChkIds[0x15], 0U, skelChkIds[0]);
    }
}
#endif
}   // namespace
#endif
#if defined(RE4DC_PWC_KERNEL) && RE4DC_PWC_KERNEL && defined(__sh__)
#if !(defined(RE4DC_SKEL_FTRV) && RE4DC_SKEL_FTRV == 1)
#error "GAME_PWC_KERNEL needs GAME_SKEL_FTRV=1"
#endif
// GAME_PWC_KERNEL (game30.mk; the 30 fps rethink, step 2): skelPass's live loop as one streaming SH-4
// loop (platform/pwc_sh4.S), an exact twin: the same FP operations on the same operands, only the
// addressing differs (fmov has no displacement form: the compiled loop spends three instructions per
// field) and the inverse scales are computed once per distinct parent scale. The kernel returns each
// part that needs the C path (an addRot request, a zero parent scale component); skelPartLive runs
// that part as skelPass would and the kernel resumes with its pList.
//   =1: the Ganados' update (re4dc_skel_scope), as GAME_SKEL_FTRV=1. Logic trace STRICT.
//   =2: check build: the kernel pass runs first, its outputs are saved and the parts' flags restored,
//       then skelPass recomputes everything live and each mat / world / r_scale word is compared
//       ("PWCK" log line). The live state is skelPass's, so the trace stays STRICT.
//   =3: every model's pass on the kernel: Leon and the objects move from the library path to FTRV
//       (last-bit FP policy; decisions compared with GAME_DECISION_TRACE).
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Winvalid-offsetof"
static_assert(__builtin_offsetof(cParts, mat) == 0x0C, "pwc_sh4.S: mat");
static_assert(__builtin_offsetof(cParts, l_mat) == 0x3C, "pwc_sh4.S: l_mat");
static_assert(__builtin_offsetof(cParts, pParent) == 0x6C, "pwc_sh4.S: pParent");
static_assert(__builtin_offsetof(cParts, world) == 0x70, "pwc_sh4.S: world");
static_assert(__builtin_offsetof(cParts, scale) == 0xAC, "pwc_sh4.S: scale");
static_assert(__builtin_offsetof(cParts, r_scale) == 0xB8, "pwc_sh4.S: r_scale");
static_assert(__builtin_offsetof(cParts, pList) == 0xF4, "pwc_sh4.S: pList");
static_assert(__builtin_offsetof(cParts, motParts.flags) == 0x1C0, "pwc_sh4.S: motParts.flags");
static_assert(__builtin_offsetof(cCoord, mat) == 0x0C && __builtin_offsetof(cCoord, r_scale) == 0xB8,
              "pwc_sh4.S: parent (cCoord) offsets");
#pragma GCC diagnostic pop
extern "C" cParts* re4dc_pwc_ftrv_run(cParts* p);
namespace {
// skelPass's live body for one part (the kernel's bail-outs).
void skelPartLive(cParts* p)
{
    const u32 fl = p->motParts.flags;
    const cCoord* parent = p->pParent;
    const f32* P = &parent->mat[0][0];
    Vec rs = parent->r_scale;
    f32* M = &p->mat[0][0];
    const f32* L = &p->l_mat[0][0];
    if ((rs.x != rs.y || rs.y != rs.z) && (rs.x == 0.0f || rs.y == 0.0f || rs.z == 0.0f)) {
        skelScaledOriginal(P, rs, L, M);
    } else if (rs.x != rs.y || rs.y != rs.z) {
        const f32 ix = (rs.x != 0.0f) ? 1.0f / rs.x : 0.0f;
        const f32 iy = (rs.y != 0.0f) ? 1.0f / rs.y : 0.0f;
        const f32 iz = (rs.z != 0.0f) ? 1.0f / rs.z : 0.0f;
        f32 Ls[12];
        Ls[0] = L[0] * rs.x; Ls[1] = L[1] * rs.y; Ls[2] = L[2] * rs.z; Ls[3] = L[3] * rs.x;
        Ls[4] = L[4] * rs.x; Ls[5] = L[5] * rs.y; Ls[6] = L[6] * rs.z; Ls[7] = L[7] * rs.y;
        Ls[8] = L[8] * rs.x; Ls[9] = L[9] * rs.y; Ls[10] = L[10] * rs.z; Ls[11] = L[11] * rs.z;
        skelLoadRows(Ls);
        skelRows(P, ix, iy, iz, M);
    } else {
        skelLoadRows(L);
        skelRowsUniform(P, M);
    }
    Vec w = {M[3], M[7], M[11]};
    if (fl & 0x40000000) {
        Mtx m2;
        f32(*Mm)[4] = (f32(*)[4]) M;
        p->motParts.flags &= ~0x40000000;
        PSMTXRotRad(m2, 'x', p->addRot.x);
        PSMTXConcat(Mm, m2, Mm);
        PSMTXRotRad(m2, 'z', p->addRot.z);
        PSMTXConcat(Mm, m2, Mm);
        PSMTXRotRad(m2, 'y', p->addRot.y);
        PSMTXConcat(m2, Mm, Mm);
        TransMatrix(Mm, &w);
    }
    Vec r;
    r.x = rs.x * p->scale.x;
    r.y = rs.y * p->scale.y;
    r.z = rs.z * p->scale.z;
    p->world = w;
    p->r_scale = r;
}
inline void pwcKernelPass(cModel* self)
{
    for (cParts* q = self->pList; q;) {
        q = re4dc_pwc_ftrv_run(q);
        if (!q) {
            break;
        }
        skelPartLive(q);
        q = q->pList;
    }
}
#if RE4DC_PWC_KERNEL == 2
extern "C" void re4dc_log(const char* fmt, ...);
u32 pwckFlags[256];
u32 pwckOut[256][18];
u32 pwckCalls, pwckParts, pwckBails, pwckMisParts, pwckMisWords, pwckOver;
void pwckCheck(cModel* self)
{
    u32 n = 0;
    for (cParts* q = self->pList; q; q = q->pList) {
        if (n < 256) {
            pwckFlags[n] = q->motParts.flags;
        }
        n++;
    }
    if (n > 256) {
        pwckOver++;
        skelPass(self, 0, 0);
        return;
    }
    for (cParts* q = self->pList; q;) {
        q = re4dc_pwc_ftrv_run(q);
        if (!q) {
            break;
        }
        pwckBails++;
        skelPartLive(q);
        q = q->pList;
    }
    u32 i = 0;
    for (cParts* q = self->pList; q; q = q->pList, i++) {
        __builtin_memcpy(&pwckOut[i][0], &q->mat[0][0], 48);
        __builtin_memcpy(&pwckOut[i][12], &q->world, 12);
        __builtin_memcpy(&pwckOut[i][15], &q->r_scale, 12);
        q->motParts.flags = pwckFlags[i];
    }
    skelPass(self, 0, 0);
    i = 0;
    for (cParts* q = self->pList; q; q = q->pList, i++) {
        if (pwckFlags[i] & 2) {
            continue;
        }
        u32 ref[18];
        __builtin_memcpy(&ref[0], &q->mat[0][0], 48);
        __builtin_memcpy(&ref[12], &q->world, 12);
        __builtin_memcpy(&ref[15], &q->r_scale, 12);
        u32 bad = 0;
        for (int j = 0; j < 18; j++) {
            bad += ref[j] != pwckOut[i][j];
        }
        pwckParts++;
        pwckMisWords += bad;
        pwckMisParts += bad != 0;
    }
    if ((++pwckCalls & 0x3FF) == 0) {
        re4dc_log("PWCK calls=%u parts=%u bails=%u mismatch_parts=%u mismatch_words=%u overflow=%u\n",
                  pwckCalls, pwckParts, pwckBails, pwckMisParts, pwckMisWords, pwckOver);
    }
}
#endif
}   // namespace
#endif
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
#include "el_census.h"   // EL_CENSUS (game30.mk; lane el): the part-world pass census
#endif
void cModel::partsWorldCalc()
{
    cParts* p;
    Vec tmp;
    Vec sc;
    Mtx m1;
    Mtx m2;

#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    elcPartsWorld(this);
#endif
    r_scale = scale;
    p = pList;
    if (!PTR_OK(p)) {
        pLog->err(2, 0, "partsWorldCalc() MODEL HAS NO PARTS");
        return;
    }
    if (!PTR_OK(p->pParent)) {
        pLog->err(2, 0, "partsWorldCalc() PARENT ADDR ERR %08x", p->pParent);
        return;
    }
#if defined(RE4DC_SKEL_FTRV) && RE4DC_SKEL_FTRV == 1 && defined(__sh__)
#if defined(RE4DC_PWC_KERNEL) && RE4DC_PWC_KERNEL == 3
    if (true) {   // GAME_PWC_KERNEL=3: every model
#else
    if (re4dc_skel_scope) {
#endif
#if defined(RE4DC_PWC_KERNEL) && RE4DC_PWC_KERNEL == 2
        pwckCheck(this);
#elif defined(RE4DC_PWC_KERNEL) && RE4DC_PWC_KERNEL
        pwcKernelPass(this);
#else
        skelPass(this, 0, 0);
#endif
        Motion.Pos_world = pos;
        return;
    }
#elif defined(RE4DC_SKEL_FTRV) && RE4DC_SKEL_FTRV == 2 && defined(__sh__)
    u32 skelN = 0, skelMiss = 0;
    if (re4dc_skel_scope) {
        skelN = skelPass(this, skelShadowBuf, &skelMiss);
    }
    for (cParts* q = p; q; q = q->pList) {
        skelChkAll += !(q->motParts.flags & 2);
    }
#endif
    for (; p; p = p->pList) {
        cCoord* parent = p->pParent;
        MtxPtr m;

        if (p->motParts.flags & 2) {
            continue;
        }
        tmp.x = p->l_mat[0][3];
        tmp.y = p->l_mat[1][3];
        tmp.z = p->l_mat[2][3];
        m = parent->mat;
        PSMTXMultVec(m, &tmp, &p->world);
        if (parent->r_scale.x != parent->r_scale.y || parent->r_scale.y != parent->r_scale.z) {
            sc.x = (parent->r_scale.x != 0.0f) ? 1.0f / parent->r_scale.x : 0.0f;
            sc.y = (parent->r_scale.y != 0.0f) ? 1.0f / parent->r_scale.y : 0.0f;
            sc.z = (parent->r_scale.z != 0.0f) ? 1.0f / parent->r_scale.z : 0.0f;
#if defined(RE4DC_PWC_DIAG) && RE4DC_PWC_DIAG
            PWC_MUL_DIAG(parent->mat, sc.x, sc.y, sc.z, m1);
            PSMTXConcat(m1, p->l_mat, p->mat);
            PWC_MUL_DIAG(p->mat, parent->r_scale.x, parent->r_scale.y, parent->r_scale.z, p->mat);
#else
            PSMTXScale(m1, sc.x, sc.y, sc.z);
            PSMTXConcat(parent->mat, m1, m1);
            PSMTXConcat(m1, p->l_mat, p->mat);
            PSMTXScale(m1, parent->r_scale.x, parent->r_scale.y, parent->r_scale.z);
            PSMTXConcat(p->mat, m1, p->mat);
#endif
        } else {
            PSMTXConcat(m, p->l_mat, p->mat);
        }
        m = p->mat;
        if (p->motParts.flags & 0x40000000) {
            p->motParts.flags &= ~0x40000000;
            PSMTXRotRad(m2, 'x', p->addRot.x);
            PSMTXConcat(m, m2, m);
            PSMTXRotRad(m2, 'z', p->addRot.z);
            PSMTXConcat(m, m2, m);
            PSMTXRotRad(m2, 'y', p->addRot.y);
            PSMTXConcat(m2, m, m);
        }
        TransMatrix(m, &p->world);
        p->r_scale.x = parent->r_scale.x * p->scale.x;
        p->r_scale.y = parent->r_scale.y * p->scale.y;
        p->r_scale.z = parent->r_scale.z * p->scale.z;
    }
    Motion.Pos_world = pos;
#if defined(RE4DC_SKEL_FTRV) && RE4DC_SKEL_FTRV == 2 && defined(__sh__)
    if (re4dc_skel_scope) {
        skelCompare(this, skelShadowBuf, skelN, skelMiss);
    }
#endif
}

// Attaches the root parts to another model (parent coordinate) with an offset and rotation.
void cModel::setParent(cModel* parent, Vec* pos, Vec* rot)
{
    cParts* p = pList;

    p->pParent = parent;
    p->pos = *pos;
    p->ang = *rot;
}

// Attaches the root parts to parts partsNo of another model.
void cModel::setParent(cModel* parent, int partsNo, Vec* pos, Vec* rot)
{
    setParent(parent->getPartsPtr(partsNo), pos, rot);
}

// End of frame: pos_old and each parts' world_old/world_old2 history (used for motion trails and
// collision sweeps).
void cModel::updateOldPos()
{
    cParts* p;

    pos_old = pos;
    for (p = pList; p; p = p->pList) {
        p->world_old2 = p->world_old;
        p->world_old = p->world;
    }
}

// Moves the model and every parts by the delta without recomputing the pose; updates the light
// volume matrix and flags the collision as moved.
void cModel::setPos(Vec* pos)
{
    Vec d;
    cParts* p;

    PSVECSubtract(pos, &this->pos, &d);
    p = pList;
    if (PSVECMag(&d) != 0.0f) {
        PSVECAdd(&this->pos, &d, &this->pos);
        PSVECAdd(&pos_old, &d, &pos_old);
        for (; p; p = p->pList) {
            PSVECAdd(&p->world, &d, &p->world);
            p->world_old = p->world;
            p->mat[0][3] += d.x;
            p->mat[1][3] += d.y;
            p->mat[2][3] += d.z;
        }
        mat[0][3] = this->pos.x;
        mat[1][3] = this->pos.y;
        mat[2][3] = this->pos.z;
    }
    LightInfo.updateMatrix(this);
    atari.m_stat |= 1;
}

// Sets the rotation and rebuilds all matrices.
void cModel::setAng(Vec* ang)
{
    this->ang = *ang;
    matUpdate();
}

// Sets the scale and rebuilds all matrices.
void cModel::setSca(Vec* sca)
{
    scale = *sca;
    matUpdate();
}

// Debug: draws the joint tree (spheres, parent links, local axes) with parts numbers on screen.
void cModel::debugSkeletonDisp()
{
    cParts* p;
    Vec scr;
    Vec ax;
    Vec ay;
    Vec az;
    Vec wp;
    u32 i;
    // COMPILER-DIFF: candidate (gcse PRE pseudo numbering). Four dead pool constants (labels consumed
    // at expand, the loads deleted before gcse, the entries never output) move the 10.0/1.0 pool
    // labels from .LC24/.LC25 to .LC28/.LC29: the PRE'd highs are numbered by hash bucket
    // ((h(name) + 81) % 151 here) and .LC29 wraps to bucket 0 below .LC28's 150, so it is
    // allocated first and takes r22, the 10.0 high r21, like the original (see exception.cpp).
    f32 lc0 = 101.125f;
    f32 lc1 = 102.125f;
    f32 lc2 = 103.125f;
    f32 lc3 = 104.125f;

    p = pList;
    if (p == NULL) {
        return;
    }
    Draw_sphere(&pos, 15.0f, 0xFFFF, 1, 1);
    Draw_line3d(&p->world, &pos, 0xFFFFFFFF, 0);
    ax.x = 25.0f;
    ax.y = 0.0f;
    ax.z = 0.0f;
    ay.x = 0.0f;
    ay.y = 25.0f;
    ay.z = 0.0f;
    az.x = 0.0f;
    az.y = 0.0f;
    az.z = 25.0f;
    RE4DC_XM_LOAD(p->mat);
    RE4DC_XM_POINT(p->mat, &ax, &ax);
    RE4DC_XM_POINT(p->mat, &ay, &ay);
    RE4DC_XM_POINT(p->mat, &az, &az);
    Draw_line3d(&p->world, &ax, 0xFFFF0000, 0);
    Draw_line3d(&p->world, &ay, 0xFF00FF00, 0);
    Draw_line3d(&p->world, &az, 0xFF0000FF, 0);
    Draw_sphere(&p->world, 15.0f, 0xFFFF, 1, 1);
    wp = p->world;
    GetScreenPos(&wp, &scr);
    scr.x += 10.0f;
    scr.y += 10.0f;
    if (scr.z < 1.0f) {
        eprintf2(8, 0xE, (int) scr.x, (int) scr.y, 1, 0, "[%02d]", 0);
    }
    p = p->pList;
    for (i = 1; p; p = p->pList, i++) {
        if (p->pParent) {
            Draw_line3d(&p->world, &p->pParent->world, 0xFFFF, 0);
        }
        Draw_sphere(&p->world, 10.0f, 0xFF0000FF, 1, 1);
        ax.x = 25.0f;
        ax.y = 0.0f;
        ax.z = 0.0f;
        ay.x = 0.0f;
        ay.y = 25.0f;
        ay.z = 0.0f;
        az.x = 0.0f;
        az.y = 0.0f;
        az.z = 25.0f;
        RE4DC_XM_LOAD(p->mat);
        RE4DC_XM_POINT(p->mat, &ax, &ax);
        RE4DC_XM_POINT(p->mat, &ay, &ay);
        RE4DC_XM_POINT(p->mat, &az, &az);
        Draw_line3d(&p->world, &ax, 0xFFFF0000, 0);
        Draw_line3d(&p->world, &ay, 0xFF00FF00, 0);
        Draw_line3d(&p->world, &az, 0xFF0000FF, 0);
        wp = p->world;
        GetScreenPos(&wp, &scr);
        if (scr.z < 1.0f) {
            int dx;
            int dy;

            switch (i & 7) {
            default:
                dx = 0;
                dy = 0;
                break;
            case 1:
                dx = -30;
                dy = 12;
                break;
            case 2:
                dx = 10;
                dy = -12;
                break;
            case 3:
                dx = -30;
                dy = -12;
                break;
            case 4:
                dx = -40;
                dy = 0;
                break;
            case 5:
                dx = 0;
                dy = 24;
                break;
            case 6:
                dx = 0;
                dy = -24;
                break;
            case 7:
                dx = 50;
                dy = 0;
                break;
            }
            eprintf2(8, 0xE, (int) scr.x + dx, (int) scr.y + dy, 4, 0, "[%02d]", i);
        }
        if (pG->debug_mode == 7) {
            wp.x = 100.0f;
            wp.y = 0.0f;
            wp.z = 0.0f;
            PSMTXMultVec(p->mat, &wp, &wp);
            Draw_line3d(&p->world, &wp, 0xFFFF0000, 0);
            wp.x = 0.0f;
            wp.y = 100.0f;
            wp.z = 0.0f;
            PSMTXMultVec(p->mat, &wp, &wp);
            Draw_line3d(&p->world, &wp, 0xFF00FF00, 0);
            wp.x = 0.0f;
            wp.y = 0.0f;
            wp.z = 100.0f;
            PSMTXMultVec(p->mat, &wp, &wp);
            Draw_line3d(&p->world, &wp, 0xFF0000FF, 0);
        }
    }
}

// Appends a model info (extra parts model: weapon, head, clothes) to the model's chain.
void cModel::addModel(cModelInfo* info)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cModelInfo* p;

    if (pModelInfo == NULL) {
        pModelInfo = info;
        return;
    }
    for (p = pModelInfo; p->pList; p = p->pList) {
    }
    p->pList = info;
}

// Remembers parts `no`'s world position so partsFixAdjust can keep it planted (foot lock).
void cModel::partsFixMemory(int no)
{
    cModel* p;

    if (pParts == NULL) {
        Fix_parts = 0;
        return;
    }
    p = getPartsPtr(no);
    Fix_pos = p->world;
    Fix_parts = no + 1;
}

// Moves the model in XZ so the remembered parts stays where it was, then recomputes the parts
// world positions; clears the lock.
void cModel::partsFixAdjust()
{
    cModel* p;
    Vec d;

    if (Fix_parts == 0) {
        return;
    }
    p = getPartsPtr(Fix_parts - 1);
    d.x = p->world.x - Fix_pos.x;
    d.z = p->world.z - Fix_pos.z;
    pos.x -= d.x;
    pos.z -= d.z;
    PartsWorldPosCalc(this);
    Fix_parts = 0;
}

// Kills the model: clears alive/visible flags and frees its parts and model infos.
void cModel::push()
{
    if (isAlive()) {
        be_flag &= ~0x22;
        releasePartsList(0);
        releaseModelInfo();
    }
}

// Debug: draws the bounding box of every model info in the chain.
void cModel::drawAllBoundingBox(cModelInfo* info)
{
    for (; info; info = info->pList) {
        drawBoundingBox(mat, &info->bound);
    }
}


// New model info: white colour, identity matrix, visible, opaque.
cModelInfo::cModelInfo() : cUnit(1)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_GATE
    re4dc_gcasset_pose_reset(this);
#endif
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::motion_source_reset(this);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_info_retire(this);
#endif

    static u32 col = 0xFFFFFFFF;

    colorWord = U32Get(col);
    PSMTXIdentity(mat);
    be_flag |= 8;
    invisible_factor = 1.0f;
}

// Sets (and relocates) the texture palette.
void cModelInfo::setTplAddr(void* tpl)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_info_retire(this);
#endif

    tpl_addr = tpl;
    calcTplAddr((TEXPalette*) tpl);
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_info_adopt(this);
#endif

}

// Sets an additional texture palette (nAddTex textures appended to the model's texture indices).
void cModelInfo::addTplAddr(void* tpl)
{
    pAddTpl = (TEXPalette*) tpl;
    calcTplAddr((TEXPalette*) tpl);
    nAddTex = pAddTpl->numDescriptors;
}

// Installs a texture blend table (per material texture replacement, e.g. tex-render / damage
// textures) and marks it active (flagsDC bit 2).
void cModelInfo::setTexBlendTbl(void* tbl)
{
    texBlendTbl = tbl;
    flagsDC |= 4;
}

// Removes the texture blend table.
void cModelInfo::resetTexBlendTbl()
{
    texBlendTbl = 0;
    flagsDC &= ~4;
}

// Blend ratio (0..255) between the original and blend-table textures.
void cModelInfo::setBlendRatio(u16 ratio)
{
    blendRatio = ratio;
}

// Selects the TEV blend type used by the blend table.
void cModelInfo::setBlendType(u8 type)
{
    blendType = type;
}

// Sets the specular colour of every material of the model data.
void cModelInfo::setSpecular(u8 r, u8 g, u8 b)
{
    ModelData* d = pData;
    ModelPart* part = d->pParts;
    u32 n = d->displist_num;
    u32 i;

    for (i = 0; i < n; i++) {
        part->specR = r;
        part->specG = g;
        part->specB = b;
        {
            u8* next = (u8*) (part + 1);
            part = (ModelPart*) (next + part->size);
        }
    }
}

// Halts (sleep loop) on a model file with an unknown version.
// Never called (the original linker dropped the bodies): the "not bin data" wait loop
// cModInfoMgr::create inlines, and the two shadow model registrations.
static inline void notBinData()
{
    for (;;) {
        eprintf(0x64, 0x190, 0, 0, "not bin data");
        TaskSleep(1);
    }
}

static int lbl_80314C2C = 0;
// Dead like the two functions below; the linker dropped them but kept this table (the 0x10 zero
// bytes between the cCoord and cUnit vtable copies in .rodata).
static const s32 ShadowPtNum[4] = { 0, 0, 0, 0 };

// Leftover shadow model bookkeeping: only the "PtNum Over" check survives.
static void ShadowModelInit(int em, int sh)
{
    if (lbl_80314C2C + ShadowPtNum[em] > sh) {
        pLog->err(0, 0, "ShadowModelInit():PtNum Over (Em:%d/Sh:%d)", em, sh);
    }
}

// Leftover shadow model bookkeeping (see ShadowModelInit).
static void AddShadowModel(int em, int sh)
{
    if (lbl_80314C2C + ShadowPtNum[em] > sh) {
        pLog->err(0, 0, "AddShadowModel():PtNum over(Em:%d/Sh:%d)", em, sh);
    }
}

// Removes (and destroys) the model info whose data is `data` from the chain; 0 when absent.
int cModel::deleteModelData(ModelData* data)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cModelInfo* prev = NULL;
    cModelInfo* info = pModelInfo;

    if (info->pData == data) {
        pModelInfo = info->pList;
        MM->destroy(info);
        return 1;
    }
    while (info) {
        if (info->pData == data) {
            prev->pList = info->pList;
            MM->destroy(info);
            return 1;
        }
        prev = info;
        info = info->pList;
    }
    return 0;
}

// Removes and destroys a model info from the chain; 0 when absent.
int cModel::deleteModelInfo(cModelInfo* target)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cModelInfo* prev = NULL;
    cModelInfo* info = pModelInfo;

    if (info == target) {
        pModelInfo = info->pList;
        MM->destroy(info);
        return 1;
    }
    while (info) {
        if (info == target) {
            prev->pList = info->pList;
            MM->destroy(info);
            return 1;
        }
        prev = info;
        info = info->pList;
    }
    return 0;
}

// Replaces the model info holding `data` by newInfo in place (costume/damage model swaps).
int cModel::swapModelInfo(ModelData* data, cModelInfo* newInfo)
{
    cModelInfo* prev = NULL;
    cModelInfo* info = pModelInfo;

    if (info->pData == data) {
        pModelInfo = info->pList;
        MM->destroy(info);
        addModel(newInfo);
        return 1;
    }
    while (info) {
        if (info->pData == data) {
            prev->pList = newInfo;
            newInfo->pList = info->pList;
            MM->destroy(info);
            return 1;
        }
        prev = info;
        info = info->pList;
    }
    return 0;
}

// After the owning archive moved in memory by ofs (be_flag 0x80000 models): shifts the data/tpl
// pointers of every model info and reconverts them to offsets for the next relocation.
void cModel::moveDataAddr(int ofs)
{
    cModelInfo* info;

    if (be_flag & 0x80000) {
        return;
    }
    for (info = pModelInfo; info; info = info->pList) {
        if (ofs != 0) {
            info->pData = (ModelData*) ((u8*) info->pData + ofs);
            info->tpl_addr = (u8*) info->tpl_addr + ofs;
        } else {
            calcModelOffset(info->pData);
            calcTplOffset((TEXPalette*) info->tpl_addr);
        }
    }
}

// Converts a model file's section offsets (colour, texture, joint heads, weights, parts, original
// vertices/normals, blend/flip tables) to pointers, once (pClr sign bit marks the state). Halts
// when the parts block is not 32-byte aligned.
// Relocates the file offsets of a model bin to pointers (once: pClr is a pointer afterwards).
void calcModelAddr(ModelData* d)
{
    u8* base = (u8*) d;

    if ((int) d->pClr < 0) {
        return;
    }
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE
    // Capture the bounded immutable BIN before any pointer or FE mutation.
    // Preparation alone never logs a drawn/played GC asset.
    re4dc_gcasset_capture_model(d);
#endif
    d->pClr = base + (u32) d->pClr;
    d->pTex = base + (u32) d->pTex;
    d->pHead = (ModelDataHead*) (base + (u32) d->pHead);
    d->pWeight = base + (u32) d->pWeight;
    d->pParts = (ModelPart*) (base + (u32) d->pParts);
    d->vtxOrig = base + (u32) d->vtxOrig;
    d->nrmOrig = base + (u32) d->nrmOrig;
    if (d->version > 0x20030817) {
        if (d->blendTbl != 0) {
            d->blendTbl = (u32) base + d->blendTbl;
        }
        if (d->flipTbl != 0) {
            d->flipTbl = (u32) base + d->flipTbl;
        }
    }
    if ((u32) d->pParts & 0x1F) {
#line 1907 "D:/Bio4/Prog/model.cpp"
        HALT();
    }
}

// Inverse of calcModelAddr: pointers back to offsets (before the file is moved or saved).
void calcModelOffset(ModelData* d)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_data_move(d);
#endif

    u8* base = (u8*) d;

    if ((int) d->pClr >= 0) {
        return;
    }
    d->pClr = (void*) ((u8*) d->pClr - base);
    d->pTex = (void*) ((u8*) d->pTex - base);
    d->pHead = (ModelDataHead*) ((u8*) d->pHead - base);
    d->pWeight = (void*) ((u8*) d->pWeight - base);
    d->pParts = (ModelPart*) ((u8*) d->pParts - base);
    d->vtxOrig = (void*) ((u8*) d->vtxOrig - base);
    d->nrmOrig = (void*) ((u8*) d->nrmOrig - base);
    if (d->version > 0x20030817) {
        if (d->blendTbl != 0) {
            d->blendTbl -= (u32) base;
        }
        if (d->flipTbl != 0) {
            d->flipTbl -= (u32) base;
        }
    }
}

// The bin moved by `ofs` bytes (block.cpp compaction): shift its pointers.
void slideModelAddr(u32 addr, int ofs)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_data_move((void*)addr);
#endif

    ModelData* d = (ModelData*) addr;

    if ((int) d->pClr >= 0) {
        calcModelAddr(d);
    }
    d->pClr = (u8*) d->pClr + ofs;
    d->pTex = (u8*) d->pTex + ofs;
    d->pHead = (ModelDataHead*) ((u8*) d->pHead + ofs);
    d->pWeight = (u8*) d->pWeight + ofs;
    d->pParts = (ModelPart*) ((u8*) d->pParts + ofs);
    d->vtxOrig = (u8*) d->vtxOrig + ofs;
    d->nrmOrig = (u8*) d->nrmOrig + ofs;
    if (d->version > 0x20030817) {
        if (d->blendTbl != 0) {
            d->blendTbl += ofs;
        }
        if (d->flipTbl != 0) {
            d->flipTbl += ofs;
        }
    }
}

// Converts a TPL's descriptor/texture header/image offsets to pointers, once.
void calcTplAddr(TEXPalette* tpl)
{
    u32 i;

    if (tpl == NULL) {
        return;
    }
    if ((int) tpl->descriptorArray < 0) {
        return;
    }
    tpl->descriptorArray = (TEXDescriptor*) ((u32) tpl->descriptorArray + (u32) tpl);
    for (i = 0; i < tpl->numDescriptors; i++) {
        if (tpl->descriptorArray[i].textureHeader != NULL) {
            tpl->descriptorArray[i].textureHeader = (TEXHeader*) ((u32) tpl->descriptorArray[i].textureHeader + (u32) tpl);
            if (tpl->descriptorArray[i].textureHeader->unpacked == 0) {
                tpl->descriptorArray[i].textureHeader->data = (void*) ((u32) tpl->descriptorArray[i].textureHeader->data + (u32) tpl);
                tpl->descriptorArray[i].textureHeader->unpacked = 1;
            }
        }
    }
}

// Inverse of calcTplAddr.
void calcTplOffset(TEXPalette* tpl)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_data_move(tpl);
#endif

    u32 i;

    if ((int) tpl->descriptorArray >= 0) {
        return;
    }
    for (i = 0; i < tpl->numDescriptors; i++) {
        if (tpl->descriptorArray[i].textureHeader != NULL) {
            if (tpl->descriptorArray[i].textureHeader->unpacked != 0) {
                tpl->descriptorArray[i].textureHeader->data = (void*) ((u8*) tpl->descriptorArray[i].textureHeader->data - (u8*) tpl);
                tpl->descriptorArray[i].textureHeader->unpacked = 0;
            }
            tpl->descriptorArray[i].textureHeader = (TEXHeader*) ((u8*) tpl->descriptorArray[i].textureHeader - (u8*) tpl);
        }
    }
    tpl->descriptorArray = (TEXDescriptor*) ((u8*) tpl->descriptorArray - (u8*) tpl);
}

// Shifts a relocated TPL's pointers by ofs.
void slideTplAddr(void* p, int ofs)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_data_move(p);
#endif

    TEXPalette* tpl = (TEXPalette*) p;
    u32 i;

    if ((int) tpl->descriptorArray >= 0) {
        calcTplAddr(tpl);
    }
    tpl->descriptorArray = (TEXDescriptor*) ((u8*) tpl->descriptorArray + ofs);
    for (i = 0; i < tpl->numDescriptors; i++) {
        if (tpl->descriptorArray[i].textureHeader != NULL) {
            tpl->descriptorArray[i].textureHeader = (TEXHeader*) ((u8*) tpl->descriptorArray[i].textureHeader + ofs);
            tpl->descriptorArray[i].textureHeader->data = (u8*) tpl->descriptorArray[i].textureHeader->data + ofs;
        }
    }
}

// Destroys every model info of the chain.
void cModel::releaseModelInfo()
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cModelInfo* info = pModelInfo;

    while (info) {
        cModelInfo* dead = info;
        info = info->pList;
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_GC_ASSET_GATE
        re4dc_gcasset_pose_reset(dead);
#endif
#if defined(RE4DC_GC_ASSET_MOTION_SOURCE) && RE4DC_GC_ASSET_MOTION_SOURCE
        re4dc_gcasset::motion_source_reset(dead);
#endif
        mm->destroy(dead);
    }
    pModelInfo = 0;
}

// Allocates n (0 = nParts) cParts: a contiguous run when the pool has one (be_flag 0x2000, fast
// indexing), else one by one; links them as pList. 0 when the pool is full (list freed).
int cModel::makePartsList(int n)
{
    u32 num;
    cParts* p;
    u32 i;

    if (n == 0) {
        num = nParts;
    } else {
        num = n;
    }
    p = (cParts*) this;
    pList = pm->createSequential(num);
    if (pList != NULL) {
        be_flag |= 0x2000;
    } else {
#if defined(RE4DC_PARTS_LINKED_FLAG) && RE4DC_PARTS_LINKED_FLAG
        // A prior joint may have used a contiguous run. The fallback below
        // links individually allocated parts; getPartsPtr must follow that list.
        be_flag &= ~0x2000;
#endif
        for (i = 0; i < num; i++) {
            cParts* np = pm->create();
            if (np == NULL) {
                releasePartsList(0);
                return 0;
            }
            p->pList = np;
            p = np;
        }
    }
    return 1;
}

// Binds the motion blend table and flip table of a version 0x20030818 model file to the MotionWork.
void cModel::setJointInfo(void* bin)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    ModelData* d = (ModelData*) bin;

    if (d->version == 0x20030818) {
        if (d->blendTbl != 0) {
            Motion.blendTbl = (u16*) d->blendTbl;
        } else {
            Motion.blendTbl = 0;
        }
        if (d->flipTbl != 0) {
            Motion.flip = (u16*) (d->flipTbl + 4);
        } else {
            Motion.flip = 0;
        }
    } else {
        Motion.blendTbl = 0;
        Motion.flip = 0;
    }
}

// Frees the parts from index `no` to the end (0 = all, clearing pParts/nParts).
void cModel::releasePartsList(int no)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
    re4dc_actor_model_changed(this);
#endif

    cParts* p;
    cParts* prev;

    p = (cParts*) getPartsPtr(no);
    if (!PTR_OK(p)) {
        if (no != 0) {
            pLog->err(0, 0, "releasePartsList() idx INVALID. %d", no);
        }
        return;
    }
    while (p) {
        cParts* dead = p;
        p = p->pList;
        pm->destroy(dead);
    }
    if (no == 0) {
        pParts = 0;
        nParts = 0;
        return;
    }
    prev = (cParts*) getPartsPtr(no - 1);
    prev->pList = 0;
}

// Starts a motion on this model (MotionSetCore wrapper with reordered arguments).
void cModel::motionSet(void* data, int a, int b, int c, int d)
{
    MotionSetCore(this, &Motion, data, d, a, c, b);
}

// Advances the motion one frame (MotionMove).
int cModel::motionMove()
{
    return MotionMoveF(this, 0);
}

// Pauses the motion.
void cModel::motionPause()
{
    MotionPause(this);
}

// Rebuilds the model matrix (cCoord), all parts matrices and the light volume matrix.
void cModel::matUpdate()
{
    cCoord::matUpdate();
    if (pParts != NULL) {
        partsMatCalc();
        partsWorldCalc();
    }
    LightInfo.updateMatrix(this);
}

// Parts constructor: nothing beyond cModel.
cParts::cParts()
{
}

// Bounding box of the original vertices (s16 * 2^-shift, 8 bytes each): centre and half size.
void getBoundingBox(ModelData* d, ModelBound* pBox)
{
    f32 maxZ = -65536.0f;
    f32 maxY = -65536.0f;
    f32 maxX = -65536.0f;
    f32 minZ = 65536.0f;
    f32 minY = 65536.0f;
    f32 minX = 65536.0f;
    u32 n = d->nVtx;
    u8 shift = d->shift;
    s16* v = (s16*) d->vtxOrig;
    u32 i;

    if (n != 0) {
        f32 sc = (f32) (1 << shift);
        i = n;
        do {
            f32 x = (f32) v[0] / sc;
            f32 y = (f32) v[1] / sc;
            f32 z = (f32) v[2] / sc;
            if (maxX < x) {
                maxX = x;
            }
            if (maxY < y) {
                maxY = y;
            }
            if (maxZ < z) {
                maxZ = z;
            }
            if (minX > x) {
                minX = x;
            }
            if (minY > y) {
                minY = y;
            }
            if (minZ > z) {
                minZ = z;
            }
            v += 4;
        } while (--i != 0);
    }
    pBox->size.x = (maxX - minX) * 0.5f;
    pBox->size.y = (maxY - minY) * 0.5f;
    pBox->size.z = (maxZ - minZ) * 0.5f;
    pBox->center.x = maxX - pBox->size.x;
    pBox->center.y = maxY - pBox->size.y;
    pBox->center.z = maxZ - pBox->size.z;
}

// Manager of the cParts pool.
cPartsMgr::cPartsMgr() : cManager<cParts>(sizeof(cParts), 0)
{
    setName("cPartsMgr");
}

// Manager warnings to the log.
void cPartsMgr::log(const char* fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    pLog->vwarn(6, 0, fmt, ap);
}

// Unit construction: placement-new of cParts.
int cPartsMgr::construct(cParts* p, u32 id)
{
    new (p) cParts;
    return 1;
}

// Work `no` of a parts manager, NULL when out of range.
static inline cParts* PartsMgrWork(cPartsMgr* m, u32 no)
{
    if (no >= m->nArray) {
        return 0;
    }
#if !defined(__PPC__)
    return m->workAt(no);
#else
    return (cParts*) ((u8*) m->pArray + m->size * no);
#endif
}

// Allocates n consecutive free parts slots (linked as pList) so the model can index them directly;
// 0 when no run of n is free.
cParts* cPartsMgr::createSequential(u32 n)
{
    u32 i;
    u32 j;
    u32 lim;

#if !defined(__PPC__)
    if (n >= nArray || nArray - n <= 1) return 0;
#endif
    // `lim` is recomputed in the loop test: the entry guard's `n + 1` and the hoisted loop copy
    // give the `addi r0; mr r7, r0` pair. A `lim = n + 1` before the loop folds them into one
    // register; `nArray - (n + 1)` is reassociated by fold to `(nArray - 1) - n`.
    for (i = 0; lim = n + 1, i < nArray - lim; i++) {
        int ok;

#if !defined(__PPC__)
        if (PartsMgrWork(this, i) && (PartsMgrWork(this, i)->be_flag & 0x601)) {
#else
        if (PartsMgrWork(this, i)->be_flag & 0x601) {
#endif
            continue;
        }
        ok = 1;
        for (j = 0; j < n; j++) {
#if !defined(__PPC__)
            if (PartsMgrWork(this, i + j) && (PartsMgrWork(this, i + j)->be_flag & 0x601)) {
#else
            if (PartsMgrWork(this, i + j)->be_flag & 0x601) {
#endif
                ok = 0;
            }
        }
        if (ok) {
            cParts* first;
            cParts* p;

#if !defined(__PPC__)
            // A live part outside this run may share its allocation. Fall back
            // to the original linked-list path instead of relocating it.
            if (!prepareWork(i, n ? n : 1)) return 0;
#endif
            first = create(0, i);
            p = first;
            for (j = 1; j < n; j++) {
                cParts* np = create(0, i + j);
                p->pList = np;
                p = np;
            }
            return first;
        }
    }
    return 0;
}

cPartsMgr PartsMgr;

// Manager of the cModelInfo pool.
cModInfoMgr::cModInfoMgr() : cManager<cModelInfo>(sizeof(cModelInfo), 0)
{
    setName("cModInfoMgr");
}

// Manager warnings to the log.
void cModInfoMgr::log(const char* fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    pLog->vwarn(6, 0, fmt, ap);
}

// Unit construction: placement-new of cModelInfo.
int cModInfoMgr::construct(cModelInfo* p, u32 id)
{
    new (p) cModelInfo;
    return 1;
}

// Creates a model info for a bin/tpl pair: relocates both, checks the file version (0x20010801 or
// 0x20030818, else halts), flags shape (morph) data (be_flag 2) and computes the bounding box.
cModelInfo* cModInfoMgr::create(void* bin, void* tpl)
{
    cModelInfo* info = cManager<cModelInfo>::create();

    if (info != NULL) {
        ModelData* d = (ModelData*) bin;

        calcModelAddr(d);
        calcTplAddr((TEXPalette*) tpl);
        info->tpl_addr = tpl;
        info->pData = d;
        if (d->version != 0x20010801 && d->version != 0x20030818) {
            notBinData();
        }
        if (d->shapeOfs != 0) {
            info->be_flag |= 2;
        }
        getBoundingBox(info->pData, &info->bound);
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ACTOR_TRANSACTION
        re4dc_actor_info_adopt(info);
#endif

#if defined(RE4DC_GAME) && !defined(__PPC__)
        re4dc_model_assets_changed();
#endif
    }
    return info;
}

cModInfoMgr ModInfoMgr;

// Parts `no` by walking the pParts chain from `parts`.
cModel* GetPartsAddr(cModel* parts, int no)
{
    int cnt = no;

    if (!PTR_OK(parts)) {
        pLog->err(0, 0, "GetPartsAddr() PTR ERROR %08X", parts);
        return 0;
    }
    if (no--) {
        do {
            cModel* next = parts->pParts;
            if (!PTR_OK(next)) {
                pLog->err(0, 0, "GetPartsAddr() cParts NO ERROR %d", cnt);
                break;
            }
            parts = next;
        } while (no--);
    }
    return parts;
}

// Model info `no` of a chain.
cModelInfo* GetModelInfoAddr(cModelInfo* info, int no)
{
    int cnt = no;

    if (!PTR_OK(info)) {
        pLog->err(0, 0, "GetModelInfoAddr() PTR ERROR %08X", info);
        return 0;
    }
    if (no--) {
        do {
            cModelInfo* next = info->pList;
            if (!PTR_OK(next)) {
                pLog->err(0, 0, "GetModelInfoAddr() cModelInfo NO ERROR %d", cnt);
                break;
            }
            info = next;
        } while (no--);
    }
    return info;
}

// Length of a model info chain (error above 100).
int GetModelInfoNum(cModelInfo* info)
{
    int n = 1;
    int i;

    if (!PTR_OK(info)) {
        pLog->err(0, 0, "GetModelInfoNum() PTR ERROR %08X", info);
        return 0;
    }
    for (i = 0; i < 100; i++) {
        cModelInfo* next = info->pList;
        if (!PTR_OK(next)) {
            return n;
        }
        info = next;
        n++;
    }
    pLog->err(0, 0, "GetModelInfoNum() PTR NUM 100 ?");
    return 0;
}

// Excludes every model info of m from the reflection (mirror/water) render (be_flag 4).
void ModelInfoRefrectOffAll(cModel* m)
{
    int n;
    int i;

    if (m == NULL) {
        pLog->err(0, 0, "ModelInfoRefrectOffAll() : failed!!");
        return;
    }
    n = GetModelInfoNum(m->pModelInfo);
    for (i = 0; i < n; i++) {
        cModelInfo* info = GetModelInfoAddr(m->pModelInfo, i);
        if (info) {
            info->be_flag |= 4;
        }
    }
}

// Re-includes model info `no` in the reflection render.
void ModelInfoRefrectOn(cModel* m, int no)
{
    cModelInfo* info;

    if (m == NULL) {
        pLog->err(0, 0, "ModelInfoRefrectOn() : failed!!");
        return;
    }
    info = GetModelInfoAddr(m->pModelInfo, no);
    if (info) {
        info->be_flag &= ~4;
    }
}

// Shows/hides model info `no` (be_flag 8).
void ModelInfoSetTrans(cModel* m, int no, int on)
{
    cModelInfo* info = GetModelInfoAddr(m->pModelInfo, no);

    if (info) {
        if (on == 1) {
            info->be_flag |= 8;
        } else {
            info->be_flag &= ~8;
        }
    }
}

static inline void VecSet(Vec* v, f32 x, f32 y, f32 z)
{
    v->x = x;
    v->y = y;
    v->z = z;
}

// Debug: draws a bounding box transformed by m as 12 lines.
void drawBoundingBox(Mtx m, ModelBound* bound)
{
    static u8 ptbl[6][4] = {
        {0, 1, 3, 2}, {4, 5, 7, 6}, {0, 1, 5, 4}, {3, 2, 6, 7}, {1, 3, 7, 5}, {2, 0, 4, 6},
    };
    Vec v[8];
    Vec q[4];
    Vec* c;
    int i;
    u32 j;
    f32 sx = bound->size.x;
    f32 sy = bound->size.y;
    f32 sz = bound->size.z;

    c = v;
    VecSet(c, -sx, -sy, -sz);
    c++;
    VecSet(c, sx, -sy, -sz);
    c++;
    VecSet(c, -sx, -sy, sz);
    c++;
    VecSet(c, sx, -sy, sz);
    c++;
    VecSet(c, -sx, sy, -sz);
    c++;
    VecSet(c, sx, sy, -sz);
    c++;
    VecSet(c, -sx, sy, sz);
    c++;
    VecSet(c, sx, sy, sz);
    // A counted loop: loop.c's giv init for `&v[j]` is emitted in the preheader after gcse's
    // `&q[k]` insertions (LUID order decides the sched2 slot of `mr r30,r24`) and the eliminated biv
    // compares the stepped pointer against `&v[7]` (`cmplw; ble`), which the do-while form with an
    // explicit end pointer gave as well but with the copy issued before the addis.
    for (j = 0; j < 8; j++) {
        PSVECAdd(&v[j], &bound->center, &v[j]);
    }
    PSMTXMultVecArray(m, v, v, 8);
    for (i = 0; i < 6; i++) {
        q[0] = v[ptbl[i][0]];
        q[1] = v[ptbl[i][1]];
        q[2] = v[ptbl[i][2]];
        q[3] = v[ptbl[i][3]];
        Draw_line3d(&q[0], &q[1], 0x20FFFFFF, 0);
        Draw_line3d(&q[1], &q[2], 0x20FFFFFF, 0);
        Draw_line3d(&q[2], &q[3], 0x20FFFFFF, 0);
        Draw_line3d(&q[3], &q[0], 0x20FFFFFF, 0);
    }
}

// Too many lights on the model: flag it, draw a marker line and its bounding boxes in red.
void cModel::error()
{
    Vec v;

    if (pG->Debug_flg[3] & 0x400000) {
        be_flag |= 0x80000000;
        v.x = pos.x;
        v.y = pos.y + 50000.0f;
        v.z = pos.z;
        Draw_line3d(&pos, &v, 0xFFFFFFFF, 0);
        if (pModelInfo) {
            drawAllBoundingBox(pModelInfo);
            pModelInfo->color[0] = 0xFF;
            {
                cModelInfo* info = pModelInfo;
                info->color[2] = 0x40;
                info->color[1] = 0x40;
            }
        }
    }
}

