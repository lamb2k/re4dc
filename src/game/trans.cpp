#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#include "fallback_audit35.h"
#endif
#line 1
// game/trans.cpp: the model renderer. ModelTrans registers a model in the ordering tables,
// commonScreenMatSub skins its vertices into the primitive buffer, ModelRender / commonModelTrans
// set up the TEV stages of every material and submit the display lists.

#include "atari.h"
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "native_primitive.h"
#include "native_model.h"
#endif
#include "light.h"
#include "ctrl.h"
#include "global.h"
#include "model.h"
#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
#define RE4DC_OTHER_UNIT "trans"
#include "other_profile.h"
#else
#define OTHER_PHASE(p) ((void)0)
#endif
#if RE4DC_ACTOR_TRANSACTION
#include "coarse_actor_transaction.h"
#endif
#if RE4DC_ACTOR_TEX_PREP
#include "actor_tex_prep.h"
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__)
#include "cache20.h"
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
#include "ps2_source_world.h"
namespace {
constexpr unsigned kSourceWorldCallbackStack=8;
Re4dcSourceWorldCallback sourceWorldCallbacks[kSourceWorldCallbackStack]{};
unsigned sourceWorldCallbackDepth,sourceWorldModelDepth;
bool sourceWorldCallbackPoisoned;
struct SourceWorldModelScope {
    SourceWorldModelScope(){re4dc_source_world_model_enter();}
    ~SourceWorldModelScope(){re4dc_source_world_model_leave();}
};
}
extern "C" void re4dc_source_world_callback_begin(unsigned table,const void* node,
        void (*func)(void*),void* data,unsigned kind) {
    if(sourceWorldCallbackPoisoned)return;
    if(sourceWorldCallbackDepth==~0U){sourceWorldCallbackPoisoned=true;return;}
    const unsigned depth=++sourceWorldCallbackDepth;
    if(depth<=kSourceWorldCallbackStack)
        sourceWorldCallbacks[depth-1]={table,kind,depth,0,node,func,data};
}
extern "C" void re4dc_source_world_callback_end() {
    if(sourceWorldCallbackPoisoned)return;
    if(!sourceWorldCallbackDepth){sourceWorldCallbackPoisoned=true;return;}
    --sourceWorldCallbackDepth;
}
extern "C" int re4dc_source_world_callback_current(Re4dcSourceWorldCallback* out) {
    if(!out || sourceWorldCallbackPoisoned || !sourceWorldCallbackDepth ||
       sourceWorldCallbackDepth>kSourceWorldCallbackStack)return 0;
    *out=sourceWorldCallbacks[sourceWorldCallbackDepth-1];
    out->model_depth=sourceWorldModelDepth;
    return 1;
}
extern "C" void re4dc_source_world_model_enter() {
    if(sourceWorldCallbackPoisoned)return;
    if(sourceWorldModelDepth==~0U){sourceWorldCallbackPoisoned=true;return;}
    ++sourceWorldModelDepth;
}
extern "C" void re4dc_source_world_model_leave() {
    if(sourceWorldCallbackPoisoned)return;
    if(!sourceWorldModelDepth){sourceWorldCallbackPoisoned=true;return;}
    --sourceWorldModelDepth;
}
#endif

#if RE4DC_PS2_WORLD_TRANSITION_OWNER
namespace { bool sourceWorldModelBlocked(cModel*); }
#endif

#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
namespace {
#if RE4DC_PS2_WORLD_R11F_OWNER
bool sourceWorldR11fModelAborted(const cModel*);
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
bool sourceWorldModelAborted(const cModel*);
#endif
// A failed owned draw can have retired the payload. This test compares only
// captured addresses and transaction state; cleanup must not read the model.
bool sourceWorldModelPostludeBlocked(const cModel* model) {
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(sourceWorldR11fModelAborted(model))return true;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(sourceWorldModelAborted(model))return true;
#endif
    return false;
}
}
#define SOURCE_WORLD_MODEL_POSTLUDE_GUARD(model) if(sourceWorldModelPostludeBlocked(model))return
#else
#define SOURCE_WORLD_MODEL_POSTLUDE_GUARD(model) ((void)0)
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
namespace { bool sourceWorldR11fModelBlocked(cModel* model); }
#endif


#include "em.h"
#include "obj.h"
#include "camera.h"
#include "view.h"
#include "main_sub.h"
#include "math_sub.h"
#include "db_log.h"
#include "trans_ot.h"
#include "trans.h"
#include "shadow.h"
#include "room_tex.h"
#include "tpl.h"
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
#include "frontend_tpl_owner34.h"
#include "scroll.h"
#endif
#include "TexRender.h"
#include "examine.h"
#include "debug.h"
#include "cloth.h"
#include "filter.h"
#include "foot_shadow.h"
#include "db_cam.h"
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
extern "C" void re4dc_leon_gc_note(cModel*); // mcheck.mk MCHECK_LEONGC (coarse_actor_transaction.inc)
#endif

#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
#include "draw_setup_audit.h"
#define DSA24_RENDER() const re4dc::dsa24::RenderScope dsa_render;
#define DSA24_MODEL() const re4dc::dsa24::Scope dsa_model(re4dc::dsa24::ModelList); re4dc::dsa24::count(re4dc::dsa24::Models);
#define DSA24_MODEL_OT(call) { const re4dc::dsa24::Scope dsa_ot(re4dc::dsa24::ModelList); call; }
#else
#define DSA24_RENDER()
#define DSA24_MODEL()
#define DSA24_MODEL_OT(call) call
#endif
#line 1 "D:/Bio4/Prog/trans.cpp"

extern cEm* pPL;   // game/em.cpp
extern cEm* pSUB;  // game/em.cpp
extern int isSelfUse;     // game/shadow.cpp
extern int g_SelfShdNum;  // game/shadow.cpp
extern f32 shd_ofs;       // game/shadow.cpp
extern f32 shd_tex_scale_x;

extern "C" {
void OSReport(const char* fmt, ...);
int EspTrans();
void EspgenTrans();
void ProcessTickGet(int no, const char* name);
void DCStoreRangeNoSync(void* addr, u32 nBytes);
void GXSetCurrentGXThread();
void GXSetDrawSync(u16 token);
void GXSetDrawSyncCallback(void (*cb)(u16));
void bio4_AddBgColor();
void Filter09Render(int);
void PSMTXReorder(Mtx src, f32 dst[4][3]);
void __GXSetIndirectMask(u32 mask);
void GXSetTevIndBumpXYZ(int tev_stage, int ind_stage, int matrix_sel);
void LightSetModel(cModel* m);
void ResetShape(cModelInfo* info, void* dst);
void CalculateShape_new(cModelInfo* info, ShapeData* data, f32 rate, void* dst);
}
void SetDrawTmpBufType(int type);   // game/TmpBuf.cpp (C++)
void drawGround(int big);           // game/db_cam.cpp (C++)
int Filter09GetbUse();              // game/filter09.cpp (C++)
void CameraCurrentProjection();     // game/camera.cpp (C++)
void* GetDrawTmpBufAddr(int type);

// The renderer's view of pG+0x184..0x4F14: the stage counters, the skinning matrix palette, the
// texture objects of the current model and the primitive buffer write pointer.
struct GxWork {
    GxStageWork stage;      // 0x000
    Mtx mtx[0xF8];          // 0x00C
    GXTexObj texObj[0xF8];  // 0x2E8C
    u8* prim;               // 0x4D8C
};
#define GXWORK() ((GxWork*) &pG->gxStage)

// cModel fields past the 0x1D8 the header declares (KNOWN DEBT: cModel is 0x320 in the original).
struct cModelExt {
    u8 pad_0[0x308];
    void* pFootShadowTbl;  // 0x308
    EmLightArea litArea;   // 0x30C
    cTexChg* pTexChg;      // 0x31C
};
#define MODEL_EXT(m) ((cModelExt*) (m))

// Parts (cParts) fields past cCoord: the parts chain and the inverse bind matrix.
struct cPartsWk {
    u8 pad_0[0xF4];
    cPartsWk* next;  // 0xF4
    Mtx bindMat;     // 0xF8
};

// Skinning weights: up to 3 matrices per vertex.
struct WeightExt {
    u16 idx[3];   // 0x00
    u16 num;      // 0x06
    u8 weight[4]; // 0x08  percent
};
struct Weight {
    u8 id[3];    // 0x00
    u8 num;       // 0x03
    u8 wht[4]; // 0x04  percent
};

#define PTR_INVALID(p) ((s32) (p) >= 0 || (u32) (p) > RE4_MEM_HI)
// Written as shifts, not `& ~0x1F`: combine folds (x >> 5) << 5 into an AND whose mask is narrowed by
// nonzero_bits (u16 * 6 -> rlwinm 0,12,26), which a literal `& ~0x1F` never gets.
#define ALIGN32(x) ((((x) + 0x1F) >> 5) << 5)
#define PTR_INVALID2(p) ((u32) (p) - RE4_MEM_LO > (RE4_MEM_HI - RE4_MEM_LO))
#define HALT()                                                    \
    {                                                             \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
        RE4DC_HALT_STORE();                                       \
    }

// u8 -> f32 through GQR2 straight from memory: the compiler only emits psq_l from a stack slot.
#if defined(__PPC__)
#define PSQ_L_U8(p) ({ f32 f_; asm volatile("psq_l %0,0(%1),1,2" : "=f"(f_) : "b"(p) : "memory"); f_; })
#else
#define PSQ_L_U8(p) ((f32) *(const u8*) (p))
#endif
// Loads straight into the named variable so the asm output shares the variable's (global) register.
#if defined(__PPC__)
#define PSQ_L_U8_TO(dst, p) asm volatile("psq_l %0,0(%1),1,2" : "=f"(dst) : "b"(p) : "memory")
#else
#define PSQ_L_U8_TO(dst, p) ((dst) = (f32) *(const u8*) (p))
#endif

// D367 frontend30 FRONT_LEAN (obj/frontend30.h; default off = previous image). Scenery whose
// every drawn info is a static native mesh that is already lit (native_static.cpp light_part runs
// once per mesh part) never reads the GX light objects, light list or normal matrix again, and a
// model whose every info is rigid never reads the skinning palette. Those inputs are render-only:
// LightInfo.pLight feeds LightSetModel / shadow-cast light counts / debug views, the normal matrix
// feeds GXLoadNrmMtxImm, pG->mtxPalette feeds MakeWeightPalette of the same call. Gameplay
// (collision, AI, events, sound) reads none of them (determinism trace gate: LOGIC_TRACE=1).
#ifndef RE4DC_FRONT_LEAN
#define RE4DC_FRONT_LEAN 0
#endif
#if RE4DC_FRONT_LEAN && defined(__sh__)
extern "C" int re4dc_static_mesh_lit(const void* object, unsigned vertices, unsigned parts);
#define FRONT_LEAN_LIGHTS 1   // skip light selection / GX light objects / normal matrix
#define FRONT_LEAN_WEIGHTS 2  // skip the skinning palette (calcWeightMat)
static int g_leanRender;   // ModelRender -> commonModelTrans: FRONT_LEAN_LIGHTS for this model
static int g_leanWeights;  // ModelTrans -> commonScreenMatSub: FRONT_LEAN_WEIGHTS for this model
static cModel* g_leanSkipped[128];  // setModel2 skipped by the last Trans() (their lists were cleared)
static u32 g_leanSkippedNum;
static int frontLean(cModel* m)
{
    int drawn = 0;
    int rigidAll = 1;
    cModelInfo* info;

    if (m->kindid != 2 || m->pShadowModelInfo != 0) {
        return 0;
    }
    for (info = m->pModelInfo; info != 0; info = info->pList) {
        ModelData* d = info->pData;
        int rigid;

        if (PTR_INVALID(info) || PTR_INVALID(d)) {
            return 0;
        }
        rigid = (m->be_flag & 0x4000) ||
                (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1);
        if (!rigid) {
            rigidAll = 0;
        }
        if (!(info->be_flag & 8)) {
            continue;
        }
        // Exactly the bridge's static_geometry test (model_bridge.cpp): only such parts reach the
        // native mesh path; anything else is drawn with source lighting.
        if (!rigid || d->shapeOfs || (info->be_flag & 2) ||
            !re4dc_static_mesh_lit(m, d->nVtx, d->displist_num)) {
            return 0;
        }
        drawn = 1;
    }
    if (!drawn) {
        return 0;
    }
    return FRONT_LEAN_LIGHTS | (rigidAll ? FRONT_LEAN_WEIGHTS : 0);
}
#endif
// D367 SKIN_PALETTE_LAZY (game30.mk; default off = previous image; render only, exact). ModelTrans's
// commonScreenMatSub registers a lazily skinned info (NATIVE_ACTOR_SKIN_LAZY) with its palette copy reserved
// (same prim-tail allocation) but not built: calcWeightMat + MakeWeightPalette run only when a render consumer
// first reads that palette (re4dc_skin_palette_resolve: native_actor_fast.cpp prepare_frame / one_frame,
// re4dc_skin_materialize), in the same game frame, from the same parts matrices and weights, through the same
// functions: the same words. Owner-drawn (ACTOR_TRANSACTION) and culled actors never read it. Consumer census:
// pG->mtxPalette and the locked-cache palette are read only by MakeWeightPalette* / CalcSk1_x right after this
// file writes them (and by NATIVE_MODEL_REGISTRY=2, refused below); no logic reads either. =2 (check build): the
// palette is also built eagerly and drawn; the lazy build compares against it ("SKLAZY ... bad=" lines).
#if RE4DC_SKIN_PALETTE_LAZY
#if !RE4DC_NATIVE_ACTOR_SKIN_LAZY || RE4DC_SKIN_CENSUS || RE4DC_NATIVE_MODEL_REGISTRY == 2 || defined(__PPC__)
#error "SKIN_PALETTE_LAZY needs NATIVE_ACTOR_SKIN_LAZY=1, SKIN_CENSUS=0 and NATIVE_MODEL_REGISTRY != 2"
#endif
// Four words of .bss (=1): the pending state lives in each reserved copy itself (skinDeferPending), so no table
// shifts the data layout.
static int g_skinLazyArm;       // ModelTrans -> commonScreenMat: this call may defer palettes
static int g_skinLazyNow;       // commonScreenMat -> commonScreenMatSub
static cModel* g_skinLazyMtx;   // the model whose calcWeightMat pG->mtxPalette holds for render-time resolves
static u32 g_skinLazyMtxFrame;  // ... in this game frame
static int skinDeferPending(cModel* m, cModelInfo* info, ModelData* d, int* mtxBuilt);
#define SKIN_LAZY_MTX(m, built)       \
    if (!(built)) {                   \
        calcWeightMat(m);             \
        g_skinLazyMtx = 0;            \
        (built) = 1;                  \
    }
#endif
// D367 LEON_FACE_LAZY (game30.mk, lane ln; default off = previous image; render only, exact; needs
// SKIN_PALETTE_LAZY=1). ModelTrans's commonScreenMatSub for Leon's (id 0) morphed face info (be_flag 2) allocates
// its arrays and runs its morph (ResetShape + CalculateShape_new: the same calls at the same time, so the motion lease
// and the morphed source in pPosBuf are as before) but defers calcWeightMat + MakeWeightPalette + CalcSk1_x (positions,
// in place) + CalcSk1_x2 / CalcSk1_x (normals) to re4dc_face_lazy_resolve: the first render read of those arrays
// (model_bridge.cpp re4dc_draw_model_part / re4dc_actor_model_buffers, shadow.cpp, mirror.cpp; the only readers of
// pPosBuf / pNrmBuf), same game frame, same parts matrices (SKIN_PALETTE_LAZY's calcWeightMat memo), same functions
// and GQR6 values: the same words. GQR6 ends as the eager pass leaves it; render-time GQR6 is restored. When the
// owner path draws Leon nothing reads them. One pending job (16 bytes of .bss); a job not resolved in its frame is
// dropped by the next ModelTrans of the info.
#if RE4DC_LEON_FACE_LAZY
#if !RE4DC_SKIN_PALETTE_LAZY || RE4DC_SKIN_PALETTE_LAZY == 2
#error "LEON_FACE_LAZY needs SKIN_PALETTE_LAZY=1"
#endif
static int faceLazyDefer(cModel* m, cModelInfo* info, ModelData* d);
#endif
// D367 frontend30 FRONT_NATIVE (obj/frontend30.h; default off = previous image). On Dreamcast the
// GX calls of the model draw are stubs: only the texture objects, the channel / light / normal
// matrix state (g_lighting, material alpha), the final colour-stage scale and the projection /
// viewport reach the native bridge (model_bridge.cpp); TEV stages, tex gens, vertex descriptors,
// blend / z / cull / alpha-compare modes and display lists are sinks. FRONT_NATIVE=1 draws a model
// with only the state the bridge reads: the same lights, info walk, matrices, texture objects,
// material / alpha-mask selection and colour scale in the same order, then the same
// re4dc_draw_model_part per part. Thermal scope, refraction / EFB shaders, self shadow, cast-shadow
// candidates, the flat colour mode (be_flag 0x20000) and unlit models keep the source path.
// FRONT_NATIVE=2 draws with the source path and replays the native path without drawing,
// comparing every part the bridge would submit field by field (model_bridge.cpp). Render-only.
#ifndef RE4DC_FRONT_NATIVE
#define RE4DC_FRONT_NATIVE 0
#endif
#if RE4DC_FRONT_NATIVE && defined(__sh__)
extern "C" int re4dc_model_diagnostic_enabled();
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" void re4dc_front_verify(int mode);  // model_bridge.cpp: 1 record, 2 compare, 0 off
static int frontNativeOk(cModel* m);
static void frontNativeRender(cModel* m, int dry);
#if defined(RE4DC_NMR_NO_GC_FRONT) && RE4DC_NMR_NO_GC_FRONT
extern "C" int re4dc_registry_owned(const cModel*);
#endif
#endif

// Bit test as 0 / 1 (matching helper).
static inline int isBit(u32 f, u32 b)
{
    if (f & b) {
        return 1;
    }
    return 0;
}

struct IntView {
    int v;
};
#define ISET0(x) (((IntView*) &(x))->v = 0)

#define IV(x) (((IntView*) &(x))->v)
static inline void U32Set(u32& d, u32 v) { d = v; }
static inline u16 U16Ref(u16& v) { return v; }
static inline int IRef(int& v) { return v; }
static inline f32 FRef(f32& v) { return v; }
static inline void ISet(int& d, int v) { d = v; }
static inline void PSet(void*& d, void* v) { d = v; }
static inline void PSet(ShadowMng*& d, ShadowMng* v) { d = v; }

u8 min_lod;
u8 max_lod;
f32 lod_bias;
ShadowMng* g_pShdMng;
int tev_stage;
int tev_reg;
int tev_kcolor;
int tex_map;
int tex_coord;
int ind_stage;
int g_material_tex_coord;
int g_specular_tev_stage;
void* g_prev_tpl_addr;
void* g_prev_add_tpl_addr;
// D367 records30 FRONT_TEXOBJ (R1; obj/records30.h, default off = previous image).
#ifndef RE4DC_FRONT_TEXOBJ
#define RE4DC_FRONT_TEXOBJ 0
#endif
#ifndef RE4DC_FRONT_TPL_OWNER
#define RE4DC_FRONT_TPL_OWNER 0
#endif
#if RE4DC_FRONT_TEXOBJ && RE4DC_FRONT_NATIVE && defined(__sh__)
static void frontTexFlush();
#define FRONT_TEX_FLUSH() frontTexFlush()
#else
#define FRONT_TEX_FLUSH()
#endif

GXTexObj g_Get_tex_obj;
Mtx specular_mat;
GXTexObj Specular[9];
GXTexObj GlobalIlmTex[5];
GXTexObj IndTex[2];
GXTlutObj ThermoTlut;

u32 aniso = 0;
// Declared incomplete first: the symbol is encoded as non-small-data (lis/addi at every use)
// even though the 4-byte definition below lands in .sdata.
extern u8 gxCsScale[];
u8 gxCsScale[4] = {2, 2, 2, 2};

// The next free texture coordinate slot (tex_coord), with an overflow error past 7.
static inline int getTexCoord()
{
    int tbl[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    if (tex_coord > 7) {
        pLog->err(0, 0, "TexCoord over!");
    }
    return tbl[tex_coord];
}

// The texture matrix index (GX_TEXMTX0 + 3 * tex_coord) for the current coordinate slot.
static inline u32 getTexMtx()
{
    u32 tbl[10] = {0x1E, 0x21, 0x24, 0x27, 0x2A, 0x2D, 0x30, 0x33, 0x36, 0x39};
    if (tex_coord > 9) {
        pLog->err(0, 0, "TexCoord over!");
    }
    return tbl[tex_coord];
}

// The next free texture map (tex_map), error past 7.
static inline int getTexMap()
{
    int tbl[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    if (tex_map > 7) {
        pLog->err(0, 0, "TexMap over!");
    }
    return tbl[tex_map];
}

// The next free TEV constant colour register (tev_kcolor), error past 3.
static inline int getKColor()
{
    int tbl[4] = {0, 1, 2, 3};
    if (tev_kcolor > 3) {
        pLog->err(0, 0, "KColor over!");
    }
    return tbl[tev_kcolor];
}

// The TEV colour-input selector for the current constant colour (GX_TEV_KCSEL_K0..3).
static inline int getKColorSel()
{
    int tbl[4] = {0xC, 0xD, 0xE, 0xF};
    if (tev_kcolor > 3) {
        pLog->err(0, 0, "KColor over!");
    }
    return tbl[tev_kcolor];
}

// The TEV alpha-input selector for the current constant colour (GX_TEV_KASEL_K0_A..).
static inline int getKAlphaSel()
{
    int tbl[4] = {0x1C, 0x1D, 0x1E, 0x1F};
    if (tev_kcolor > 3) {
        pLog->err(0, 0, "KColor over!");
    }
    return tbl[tev_kcolor];
}

// TEV output register for stage slot `no` (GX_TEVREG0..2), error past 2.
static inline int getTevReg(int no)
{
    int tbl[3] = {1, 2, 3};
    if (no > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return tbl[no];
}

// Range check of a TEV register slot.
static inline int checkTevReg(int no)
{
    if (no > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return no;
}

// Allocates the next TEV register slot after tev_reg; returns its GX register.
static inline int getTevRegNext(int& no)
{
    int tbl[3] = {1, 2, 3};
    no = checkTevReg(tev_reg + 1);
    return tbl[no];
}

// The colour-input selector reading TEV register slot `no` (GX_CC_C0..C2).
static inline int getTevRegC(int no)
{
    int tbl[3] = {2, 4, 6};
    if (no > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return tbl[no];
}

// The alpha-input selector reading TEV register slot `no` (GX_CC_A0..A2).
static inline int getTevRegA(int no)
{
    int tbl[3] = {3, 5, 7};
    if (no > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return tbl[no];
}

// Variants reading the global directly: the original reloads `tev_reg` after the error call
// instead of keeping a copy in a callee-saved register.
static inline int getTevReg()
{
    int tbl[3] = {1, 2, 3};
    if (tev_reg > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return tbl[tev_reg];
}

// The colour-input selector of the current tev_reg slot.
static inline int getTevRegC()
{
    int tbl[3] = {2, 4, 6};
    if (tev_reg > 2) {
        pLog->err(0, 0, "TevReg over!");
    }
    return tbl[tev_reg];
}

class cTevStage {
public:
    int no;
    int getID()
    {
        static int tbl[16] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15};
        if (no > 15) {
            pLog->err(0, 0, "TevStage over!");
        }
        return tbl[no];
    }
};

class cIndTexStage {
public:
    int no;
    int getID()
    {
        static int tbl[4] = {0, 1, 2, 3};
        if (no > 3) {
            pLog->err(0, 0, "IndStage over!");
        }
        return tbl[no];
    }
};

#define TEV_STAGE_ID() (((cTevStage*) &tev_stage)->getID())
#define IND_STAGE_ID() (((cIndTexStage*) &ind_stage)->getID())

extern "C" {
static void ThermoShaderSetup(cModel* m, cModelInfo* info, ModelPart* part);
static void shaderSetup(cModel* m, cModelInfo* info, ModelPart* part, Mtx mv);
static void TextureBlend(ModelPart* part, cModelInfo* info, int colIn, int alphaIn);
static void TextureBlend2(ModelPart* part, cModelInfo* info, int colIn, int alphaIn);
static void TextureBlend3(ModelPart* part, cModelInfo* info, int colIn, int alphaIn);
static void materialSetup(ModelPart* part, cModelInfo* info, int colIn, int alphaIn);
static void specularSetup(ModelPart* part, cModelInfo* info, int flag);
static void specularSetup2(ModelPart* part, int flag);
static void GlobalIlluminationSetup(ModelPart* part, int nrm8);
static void SetCastShadowLight(cModel* m, Vec* pos, Vec* dir, ShadowMng* mng);
static void ShadowCastSetup(ModelPart* part, cModel* m);
static void SelfShadowSetup(ModelPart* part, cModel* m, ShadowMng* mng);
static void bumpSetup(ModelPart* part, cModelInfo* info);
static void alphaSetup(cModel* m, ModelPart* part, cModelInfo* info, int thermo);
static void CalcSk1_x(void* dst, void* src, u32 n);

// The skinning matrix palette lives in the Gekko locked cache. Off PowerPC the platform
// layer provides the same 16 KB as an ordinary buffer (port/dreamcast/game/platform/lc.cpp).
#if defined(__PPC__)
#define RE4DC_LC_PALETTE 0xE0000000u
#else
extern "C" unsigned char re4dc_locked_cache[];
#define RE4DC_LC_PALETTE ((u32) re4dc_locked_cache)
#endif
static void CalcSk1_x2(void* dst, void* src, u32 n);
static int MakeWeightPaletteExt(WeightExt* w, int n);
static int MakeWeightPalette(Weight* w, int n);
#if RE4DC_SKIN_CENSUS
// SKIN_CENSUS (diagnostic): Trans() skinned infos per 120 frames: deferred to the native actor path,
// defer failed, skinned on the CPU here (CalcSk1_x), and of those morphed (be_flag & 2); "infos/verts".
extern "C" void re4dc_log(const char* fmt, ...);
static u32 skincen_f0, skincen_def, skincen_defv, skincen_fail, skincen_failv, skincen_cpu, skincen_cpuv,
    skincen_morph, skincen_morphv;
#endif
static void updateMatrices(Mtx m, Mtx dst, cModel* model);
static void RefractShaderSetup(cModel* m, cModelInfo* info, ModelPart* part, Mtx mv);
}

// Binds model texture `id` to texture map `map`: from the GX work's texture objects (0..0xF7), or
// a render-to-texture manager's texture (0xF8..).
void org_LoadTexObj(u32 id, int map)
{
    FRONT_TEX_FLUSH();
    GxWork* gx = GXWORK();

    if (id <= 0xF7) {
        GXLoadTexObj(&gx->texObj[id], map);
    } else {
        GXLoadTexObj(&GetTexRenderMgrAddr(id - 0xF8)->m_Tex_obj, map);
    }
}

// Per frame, the "transform" pass: effects, effect generators and the ctrl manager, shadows,
// cloth, filters and render textures register their draw callbacks, then every object and enemy
// (objTrans / emTrans -> ModelTrans); the primitive buffer written is flushed to memory.
#if RE4DC_PACE_CATCHUP
// port/dreamcast/game/pace.cpp (PACE_CATCHUP): render skip with catch-up.
extern "C" int re4dc_pace_skipping;     // ModelRender: this iteration draws nothing
#if RE4DC_EFM_PS2_CUT
extern "C" int re4dc_efm_ps2_cut(const cModel* m);  // eff_sys.cpp EFM_PS2_CUT: an effect model the PS2 deleted
#endif
#if RE4DC_ACTOR_SWAP
extern "C" int re4dc_actor_swap(cModel* m);   // ACTOR_SWAP benchmark (port/dreamcast/game/actor_swap.cpp)
#endif
extern "C" int re4dc_pace_drop_models;  // v2: this tick's image is dropped (no ModelTrans)
#ifndef RE4DC_PACE_TRANS_SKIP
#define RE4DC_PACE_TRANS_SKIP 0
#endif
// PACE_TRANS_SKIP (test knob, bitmask): presentation stages a dropped image does not need.
#if RE4DC_COARSE
#if RE4DC_PACE_CATCHUP < 2 || !(RE4DC_PACE_TRANS_SKIP & 2048)
#error COARSE needs PACE_CATCHUP=2 and the qualified PACE_TRANS_SKIP mask (bit 2048)
#endif
// port/dreamcast/game/coarse.cpp (COARSE): in-room play images drawn from gameplay records. Such a
// tick's presentation stages run as for a dropped image; Render() of the image draws the coarse view.
extern "C" int re4dc_coarse_tick(int dropped);
#if !defined(__PPC__)
// sscrn_bridge.cpp (SUBSCREEN=1): 1 while the sub screen's data fills the 3 MiB window at pG->pStFnt.
#if RE4DC_TRANS_SS_GUARD
// SUBSCREEN=1 (subscreen.mk): a strong reference, and tools/link.sh refuses a generated stub for it while
// this marker is defined (a stub returns 0 and Trans would walk the swapped lists again).
extern "C" int re4dc_ss_ui_order();
extern "C" const int re4dc_trans_ss_guard = 1;
#define RE4DC_SS_HOOK_PRESENT 1
#else
// Weak: a build without the sub screen backing has no such window (the call is skipped).
extern "C" int re4dc_ss_ui_order() __attribute__((weak));
#define RE4DC_SS_HOOK_PRESENT (re4dc_ss_ui_order != 0)
#endif
// Trans(): the room's obj / em works are in that window while it is swapped (heap 4 and the demand
// pools' chunks), so their alive lists are sub screen bytes, not works. SubScreenExec step 2 sets every
// Disp_flg hide bit first (restored after the swap back), so every objTrans / emTrans callback would
// return without a write; only the walk itself remains, and it reads the sub screen's bytes as pNext.
// Flycast reads on; a real SH-4 raises an address error on an odd one (r21v console, Trans+0x166).
static int roomListsSwapped()
{
    if (!RE4DC_SS_HOOK_PRESENT || !re4dc_ss_ui_order()) return 0;
    static u32 logged;
    if (logged != (u32) pG->Frame_cnt / 600 + 1) {
        logged = (u32) pG->Frame_cnt / 600 + 1;
        re4dc_log("Trans: room lists not walked while the sub screen window is swapped (obj %p em %p disp %08x)\n",
                  (void*) ObjMgr.pAlive, (void*) EmMgr.pAlive, (unsigned) pG->Disp_flg);
    }
    return 1;
}
#endif
#ifndef RE4DC_COARSE_SOURCE_OBJECTS
#define RE4DC_COARSE_SOURCE_OBJECTS 0
#endif
#if RE4DC_COARSE_SOURCE_OBJECTS
extern "C" void re4dc_log(const char*, ...);
#endif
// COARSE_SCENERY_FALLBACK=1 (game30.mk): coarse images skip scenery (kind 2) only in a room whose PS2
// world package replaces it (native_ps2_world.cpp); any other room keeps its own scenery, the Standard
// R4IM meshes through native_static, instead of the grey collision view. Render only.
#ifndef RE4DC_COARSE_SCENERY_FALLBACK
#define RE4DC_COARSE_SCENERY_FALLBACK 0
#endif
#if RE4DC_COARSE_SCENERY_FALLBACK
extern "C" int re4dc_ps2_world_covers(unsigned room);
#if RE4DC_PS2_WORLD_PARTS
extern "C" int re4dc_ps2_dyn_source(unsigned room, const void* object, unsigned serial);
#endif
#endif
extern "C" int re4dc_coarse_image;
extern "C" void re4dc_coarse_draw(void);
static int coarseTick;
// A drawn coarse image keeps TransTexRenderMgr (bit 64): the HUD's render textures.
#define PTS(b) ((RE4DC_PACE_TRANS_SKIP & (b)) && (re4dc_pace_drop_models || (coarseTick && !((b) & 64))))
#else
#define PTS(b) ((RE4DC_PACE_TRANS_SKIP & (b)) && re4dc_pace_drop_models)
#endif
#define PTSK(b) ((RE4DC_PACE_TRANS_SKIP & (b)) && re4dc_pace_skipping)
#if RE4DC_PACE_TRANS_SKIP
extern "C" int re4dc_esp_logic_only, re4dc_esp_logic_queued;
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
extern "C" int re4dc_esp_sprite_pass;   // esp.cpp (COARSE_FX_SPRITES, effects30.mk)
#endif
#endif
#ifndef RE4DC_WATER45_NATIVE
#define RE4DC_WATER45_NATIVE 0
#endif
#if RE4DC_WATER45_NATIVE
extern "C" int re4dc_espgen_draw_pass;   // espgen.cpp (WATER45_NATIVE, ROUTE_CH13)
#endif
#if RE4DC_PACE_CHECK
extern "C" void re4dc_pace_check(int phase);
#endif
#endif
#ifndef RE4DC_COARSE_SOURCE_ACTORS
#define RE4DC_COARSE_SOURCE_ACTORS 0
#endif
#if RE4DC_COARSE_SOURCE_ACTORS
#if !RE4DC_COARSE || RE4DC_PACE_CATCHUP < 2 || !RE4DC_ATCHK_LIST
#error COARSE_SOURCE_ACTORS requires coarse, catchup2 and alive-list generations
#endif
#include "coarse_source_frame.h"
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
extern "C" const bool* const re4dc_room4_live_ptr;
extern "C" const unsigned* const re4dc_room4_generation_ptr;
#endif
extern "C" void* re4dc_prim_tail(unsigned,unsigned);
extern "C" void re4dc_log(const char*,...);
namespace {
using re4dc_source::FrameIdentity;
using re4dc_source::ModelIdentity;
using re4dc_source::ModelPath;
using re4dc_source::Membership;
re4dc_source::FrameLedger sourceActorLedger;
unsigned sourceActorEpoch,sourceActorFailures,sourceActorCount;
unsigned sourceActorPrimBase,sourceActorPrimBytes,sourceActorPrimBuffer;
bool sourceActorActive;
#if RE4DC_ACTOR_TRANSACTION
// re4dc_coarse_image is a consumed Trans-to-Render handoff, not a callback
// lifetime. Only this scope grants ownership at original Render OT callbacks.
bool sourceActorRenderActive;
struct SourceActorRenderScope {
    bool previous;
    unsigned epoch;
    explicit SourceActorRenderScope(bool enabled)
        :previous(sourceActorRenderActive),epoch(sourceActorEpoch) {
        sourceActorRenderActive=enabled;
    }
    ~SourceActorRenderScope() {
        // A primitive retirement during a nested scope cannot resurrect it.
        sourceActorRenderActive=previous && epoch==sourceActorEpoch && sourceActorActive;
    }
};
#endif

bool sourceActorRam(const void* p) {
#if defined(__sh__)
    const auto a=reinterpret_cast<std::uintptr_t>(p);
    return a>=RE4_MEM_LO && a<=RE4_MEM_HI-sizeof(cModel);
#else
    return p!=nullptr; // host harness supplies actual objects, never guest addresses
#endif
}
void sourceActorFailure(unsigned reason) {
    ++sourceActorFailures;
    if(sourceActorFailures<=8 || !(pG->Frame_cnt%120))
        re4dc_log("SOURCE_ACTORS_FAIL t=%u reason=%u count=%u\n",
            unsigned(pG->Frame_cnt),reason,sourceActorFailures);
}
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
void sourceActorPresentation32Retire();
#endif
void sourceActorRetire() {
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
    sourceActorPresentation32Retire();
#endif
#if RE4DC_ACTOR_TRANSACTION
    sourceActorRenderActive=false;
    re4dc_actor_transaction_retire();
#endif
    sourceActorLedger.retire();
    sourceActorActive=false;sourceActorCount=0;
    if(sourceActorEpoch!=UINT32_MAX)++sourceActorEpoch;
}
bool sourceActorIdentity(FrameIdentity& now) {
    unsigned generation,cells,bytes,stale,refused;
    // A replaced primitive owner must not make borrowed old storage readable,
    // even when frame/room numbers or the manager lists have not changed.
    if(sourceActorActive && (unsigned(pG->prim_cnt)!=sourceActorPrimBase ||
       unsigned(pG->nPrim)!=sourceActorPrimBytes || unsigned(pG->vtx_buf_no)!=sourceActorPrimBuffer))return false;
#if defined(RE4DC_GC_CENSUS_TRIM) && RE4DC_GC_CENSUS_TRIM
    // GC_CENSUS_TRIM (lane t2exact): re4dc_room4_state's live flag and generation, read in place.
    (void)cells;(void)bytes;(void)stale;(void)refused;
    if(sourceActorEpoch==UINT32_MAX || !*re4dc_room4_live_ptr || !(generation=*re4dc_room4_generation_ptr))return false;
#else
    if(sourceActorEpoch==UINT32_MAX ||
       !re4dc_room4_state(&generation,&cells,&bytes,&stale,&refused) || !generation)return false;
#endif
    now={unsigned(pG->Frame_cnt),(unsigned(pG->stage_no)<<8)|pG->room_no,
        generation,sourceActorEpoch,unsigned(re4dc_alive_gen[1]),unsigned(re4dc_alive_gen[2])};
    return true;
}
ModelIdentity sourceActorModel(cModel* m) {
    const unsigned manager=m==(cModel*)pPL?0u:m==(cModel*)pSUB?1u:2u;
    return {reinterpret_cast<std::uintptr_t>(m),unsigned(m->serial),manager};
}
#if RE4DC_ACTOR_TEX_PREP_DRAW
void sourceActorTextureDraw(cModel* m) {
    FrameIdentity now{};
    if(!sourceActorActive || sourceActorRenderActive || !sourceActorRam(m) ||
       !sourceActorIdentity(now) ||
       !sourceActorLedger.texture_draw_pending(now,reinterpret_cast<std::uintptr_t>(m)))return;
    sourceActorLedger.note_texture_draw(now,sourceActorModel(m));
}
#endif
#if RE4DC_ACTOR_EARLY_COARSE
// This synchronous certificate scope grants only material inspection. It does
// not grant original-callback ownership or let transaction_draw choose a path.
cModel* sourceActorProofModel;
FrameIdentity sourceActorProofFrame{};
ModelIdentity sourceActorProofIdentity{};
struct SourceActorProofScope {
    SourceActorProofScope(cModel* m,const FrameIdentity& now) {
        sourceActorProofModel=m;sourceActorProofFrame=now;sourceActorProofIdentity=sourceActorModel(m);
    }
    ~SourceActorProofScope(){sourceActorProofModel=nullptr;}
};
#endif
ModelPath sourceActorPath(cModel* m) {
#if RE4DC_ACTOR_TRANSACTION
    // Every model receives its original source callback once. Native ownership
    // is chosen later, at the original OT callback, after native UI begin.
    return ModelPath::Source;
#else
    // Class-only first step. Reviewed adapter state/lease admission is separate.
    return m==(cModel*)pPL || (m!=(cModel*)pSUB && m->id>=0x10 && m->id<=0x20)
        ?ModelPath::Coarse:ModelPath::Source;
#endif
}
#if RE4DC_ACTOR_SKIN_RESERVE
#if RE4DC_NATIVE_MODEL_REGISTRY
extern "C" int re4dc_registry_candidate(const cModel*);
#endif
// The same nomination predicate is used here and at the original OT callback.
// This grants storage priority only; every later owner proof still applies.
static bool sourceActorNativeOwner(cModel* m) {
#if RE4DC_NATIVE_MODEL_REGISTRY
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22
    // Keep the original OT candidate's exact cabin-Luis partner exception.
    return m && (m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
        re4dc_registry_candidate(m))) || (m==(cModel*)pSUB && m->id==4 && re4dc_registry_candidate(m)));
#else
    return m && (m==(cModel*)pPL || (m!=(cModel*)pSUB && ((m->id>=0x10 && m->id<=0x20) ||
        re4dc_registry_candidate(m))));
#endif
#else
    return m && (m==(cModel*)pPL || (m!=(cModel*)pSUB && m->id>=0x10 && m->id<=0x20));
#endif
}
// Collect all current source-plan native nominees before ordinary callbacks.
// Each main-info chain remains bounded by the existing per-owner role limit;
// shared source infos occupy one key in the existing 64/80-slot source table.
static int sourceActorReserveNative(const FrameIdentity& planned,const ModelIdentity& player) {
    FrameIdentity now{};
    if(!sourceActorActive || !pPL || !sourceActorRam(pPL) ||
       !sourceActorIdentity(now) || !(now==planned) || !(sourceActorModel((cModel*)pPL)==player))return 0;
    const void* infos[kRe4dcActorSkinKeys];unsigned n=0,count=0;
    bool player_seen=false;
    for(cUnit* u=EmMgr.pAlive;u;u=u->pNext) {
        if(!sourceActorRam(u) || count>=EmMgr.nArray || count>=sourceActorCount ||
           count>=re4dc_source::FrameLedger::MaxEntries)return 0;
        ++count;
        cModel* m=(cModel*)u;ModelPath path{};
        if(!sourceActorLedger.planned_path(now,sourceActorModel(m),path))return 0;
        player_seen|=m==(cModel*)pPL;
        if(path!=ModelPath::Source || !sourceActorNativeOwner(m))continue;
        const void* chain[kRe4dcActorRoles];unsigned roles=0;
        for(cModelInfo* info=m->pModelInfo;info;info=info->pList) {
            if(roles==kRe4dcActorRoles)return 0;
#if defined(__sh__)
            const auto a=reinterpret_cast<std::uintptr_t>(info);
            if((a&3u) || a<RE4_MEM_LO || a>RE4_MEM_HI-sizeof(cModelInfo))return 0;
#endif
            for(unsigned i=0;i<roles;++i)if(chain[i]==info)return 0;
            chain[roles++]=info;
            bool seen=false;for(unsigned i=0;i<n;++i)seen|=infos[i]==info;
            if(!seen){if(n==kRe4dcActorSkinKeys)return 0;infos[n++]=info;}
        }
        if(!roles)return 0;
    }
    if(count!=sourceActorCount || !player_seen || !sourceActorIdentity(now) || !(now==planned) ||
       !(sourceActorModel((cModel*)pPL)==player))return 0;
    return n && re4dc_actor_skin_reserve(planned.frame,infos,n);
}
#endif
// 1=selective plan; 0=early full-source safety image; -1=malformed source list.
int sourceActorPlan() {

#if RE4DC_ACTOR_TRANSACTION
    re4dc_actor_transaction_retire();
#endif
    sourceActorLedger.retire();sourceActorActive=false;sourceActorCount=0;
    FrameIdentity now{};
    if(!sourceActorIdentity(now)){sourceActorFailure(1);return 0;}
    unsigned count=0;
    bool player_seen=!pPL,partner_seen=!pSUB;
    for(cUnit* u=EmMgr.pAlive;u;u=u->pNext) {
        if(!sourceActorRam(u) || count>=EmMgr.nArray || count>=4096){sourceActorFailure(2);return -1;}
        ++count;player_seen|=u==(cUnit*)pPL;partner_seen|=u==(cUnit*)pSUB;
    }
    if(count>re4dc_source::FrameLedger::MaxEntries || !player_seen || !partner_seen){sourceActorFailure(3);return 0;}
    std::size_t bytes=0;
    if(!re4dc_source::FrameLedger::storage_bytes(count,bytes)){sourceActorFailure(4);return 0;}
    // Existing primitive owner; preserve the actor workspace's established reserve.
    void* storage=count?re4dc_prim_tail(unsigned(bytes),16*1024):nullptr;
    if(count && !storage){sourceActorFailure(5);return 0;}
    if(!sourceActorLedger.begin(storage,bytes,count,now)){sourceActorFailure(6);return 0;}
#if RE4DC_ACTOR_SKIN_RESERVE
    ModelIdentity reserved_player{};
#endif
    for(cUnit* u=EmMgr.pAlive;u;u=u->pNext) {
        cModel* m=(cModel*)u;
#if RE4DC_ACTOR_EARLY_COARSE
        Re4dcActorEarlyTicket ticket{};ModelPath path=ModelPath::Source;
        {
            SourceActorProofScope proof(m,now);
            if(m!=(cModel*)pPL && m!=(cModel*)pSUB && re4dc_actor_early_coarse_admit(m,&ticket))path=ModelPath::Coarse;
        }
        if(!sourceActorLedger.append(now,sourceActorModel(m),path,0) ||
           (path==ModelPath::Coarse && !sourceActorLedger.attach_coarse_ticket(now,sourceActorModel(m),ticket))) {
            re4dc_actor_texture_release(&ticket.texture);
            re4dc_actor_texture_retire_all();sourceActorFailure(7);sourceActorLedger.retire();return -1;
        }
#else
        if(!sourceActorLedger.append(now,sourceActorModel(m),sourceActorPath(m),0)) {
            sourceActorFailure(7);sourceActorLedger.retire();return -1;
        }
#endif
#if RE4DC_ACTOR_SKIN_RESERVE
        if(m==(cModel*)pPL)reserved_player=sourceActorModel(m);
#endif
    }
    if(!sourceActorLedger.seal(now)){sourceActorFailure(8);sourceActorLedger.retire();return -1;}
    sourceActorPrimBase=unsigned(pG->prim_cnt);sourceActorPrimBytes=unsigned(pG->nPrim);
    sourceActorPrimBuffer=unsigned(pG->vtx_buf_no);
    sourceActorCount=count;sourceActorActive=true;
#if RE4DC_ACTOR_SKIN_RESERVE
    // Failure leaves the complete original source path available.
    sourceActorReserveNative(now,reserved_player);
#endif
    return 1;
}
bool sourceActorPrepare() {
    if(!sourceActorActive){sourceActorFailure(9);return false;}
    FrameIdentity now{};
    if(!sourceActorIdentity(now)){sourceActorFailure(10);return false;}
    unsigned count=0;
    for(cUnit* u=EmMgr.pAlive;u;) {
        if(!sourceActorRam(u) || count++>=EmMgr.nArray || count>re4dc_source::FrameLedger::MaxEntries){sourceActorFailure(11);return false;}
        cUnit* current=u;u=u->pNext; // preserve original cached-next traversal
        cModel* m=(cModel*)current;
#if RE4DC_ACTOR_EARLY_COARSE
        ModelPath path{};
        if(!sourceActorLedger.planned_path(now,sourceActorModel(m),path)){sourceActorFailure(21);return false;}
        if(path==ModelPath::Coarse)continue;
#else
        if(sourceActorPath(m)==ModelPath::Coarse)continue;
#endif
        re4dc_source::PreparationTicket ticket{};
        const ModelIdentity model=sourceActorModel(m);
        if(!sourceActorLedger.claim(now,ticket) || !(ticket.model==model)){sourceActorFailure(12);return false;}
        emTrans(m); // original visibility, material animation, skinning and both OTs
        FrameIdentity after{};
        if(!sourceActorIdentity(after) || !sourceActorLedger.complete(after,ticket,sourceActorModel(m))){sourceActorFailure(13);return false;}
    }
    if(!sourceActorLedger.ready(now)){sourceActorFailure(14);return false;}
    return true;
}
}
extern "C" int re4dc_coarse_source_actors_ready() {
    FrameIdentity now{};
    if(!sourceActorActive || !sourceActorIdentity(now) || !sourceActorLedger.ready(now)){sourceActorFailure(15);return 0;}
    unsigned count=0;bool player_seen=!pPL,partner_seen=!pSUB;
    for(cUnit* u=EmMgr.pAlive;u;u=u->pNext) {
        if(!sourceActorRam(u) || count++>=EmMgr.nArray || count>re4dc_source::FrameLedger::MaxEntries){sourceActorFailure(16);return 0;}
        cModel* m=(cModel*)u;
        const auto membership=sourceActorLedger.membership(now,sourceActorModel(m));
#if RE4DC_ACTOR_EARLY_COARSE
        if(membership==Membership::Coarse) {
            Re4dcActorEarlyTicket ticket{};SourceActorProofScope proof(m,now);
            if(!sourceActorLedger.coarse_ticket(now,sourceActorModel(m),ticket) ||
               !re4dc_actor_early_coarse_validate(m,&ticket)){sourceActorFailure(22);return 0;}
        } else if(membership!=Membership::SourceHandled){sourceActorFailure(17);return 0;}
#else
        const auto want=sourceActorPath(m)==ModelPath::Coarse?Membership::Coarse:Membership::SourceHandled;
        if(membership!=want){sourceActorFailure(17);return 0;}
#endif
        player_seen|=m==(cModel*)pPL;partner_seen|=m==(cModel*)pSUB;
    }
    if(count!=sourceActorCount || !player_seen || !partner_seen){sourceActorFailure(18);return 0;}
    return 1;
}
#if RE4DC_ACTOR_TEX_PREP
#include "source_actor_tex_prep.inc"
#endif
#if RE4DC_ACTOR_EARLY_COARSE
extern "C" int re4dc_actor_early_proof_active(cModel* m) {
    FrameIdentity now{};
    return m && m==sourceActorProofModel && sourceActorRam(m) && sourceActorIdentity(now) &&
        now==sourceActorProofFrame && sourceActorModel(m)==sourceActorProofIdentity;
}
extern "C" int re4dc_coarse_source_actor_texture(cModel* m,Re4dcActorTextureLease* out) {
    FrameIdentity now{};Re4dcActorEarlyTicket ticket{};
    if(!out || !m || !sourceActorActive || !sourceActorRam(m) || !sourceActorIdentity(now) ||
       !sourceActorLedger.coarse_ticket(now,sourceActorModel(m),ticket))return 0;
    *out=ticket.texture;return 1;
}
#endif
// 0=coarse,1=source callback handled,2=invalid diagnostic (never ribbon fallback).
extern "C" int re4dc_coarse_source_actor_route(const void* object) {
    FrameIdentity now{};cModel* m=(cModel*)object;
    if(!sourceActorActive || !sourceActorRam(m) || !sourceActorIdentity(now)){sourceActorFailure(19);return 2;}
    const auto membership=sourceActorLedger.membership(now,sourceActorModel(m));
    if(membership==Membership::SourceHandled)return 1;
    if(membership==Membership::Coarse)return 0;
    sourceActorFailure(20);return 2;
}
#endif

#if RE4DC_ACTOR_TRANSACTION
#include "source_actor_owner_hooks.inc"
#endif

#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
// CROWD_INVIS_SKIP (crowd.mk; lane iv; render only): a Ganado the next Render would draw nothing of gets no drawing
// work after the game's own view test (coarse_actor_owner_ganado.inc decides). Armed only for a coarse image's source
// actor preparation, whose Render owns the Ganados through the actor transaction. A skipped Ganado keeps
// commonScreenMatSub's texture animation / UV scroll advance (invisAdvance) and skips the screen matrices and
// lightSetEm (its light list is read only by its own draw). Kind 1 (owner path) loses its OT entry as the
// screen-matrix failure path does; kind 2 (source path) keeps it, and its ModelRender replays the state calls and
// commonModelTrans's texture-object / TPL cache step without the draw (invisReplayRender). =2 (check build): nothing
// is skipped; ModelRender reports each Ganado's emitted triangles (re4dc_invis_check).
extern "C" void re4dc_invis_begin(const float* P, float fog_pred);
extern "C" unsigned re4dc_invis_decide(cModel* m);
extern "C" float re4dc_fog_far_for_gate(float far);  // native_static.cpp (SCENERY_GATE)
extern int ProjType;                                   // camera.cpp
static int g_invisArmed;
static int invisAdvance(cModelInfo* info);
#if RE4DC_CROWD_INVIS_SKIP == 2
extern "C" void re4dc_invis_check(cModel* m, unsigned emitted, int crowd);
extern "C" unsigned re4dc_invis_marked(cModel* m);
extern "C" unsigned re4dc_model_output_count();
extern "C" int re4dc_actor_crowd_peek(const void* model, float* distance);  // native_actor_fast.cpp
extern "C" float re4dc_actor_crowd_distance(const float* modelview);
static int invisCrowdCheck(cModel* m);
#else
extern "C" void re4dc_actor_crowd_note(const void* model, const float* modelview);  // native_actor_fast.cpp
extern "C" void re4dc_bind_actor_frame();                                           // model_bridge.cpp
static cModel* g_invisReplay[64];
static u32 g_invisReplayNum;
static void invisReplayRender(cModel* m, int alphaUpdate);
#endif
// Trans start: the next Render's projection (CameraSetProjection(1)'s words) and fogged View far (cLightMgr::setFog
// and re4dc_fog_note_far's clamp).
static void invisTransBegin()
{
    float P[7];
    const float* pp = 0;
    g_invisArmed = 0;
#if RE4DC_CROWD_INVIS_SKIP == 1
    g_invisReplayNum = 0;
#endif
    if (ProjType == 1) {
        const f32(*M)[4] = pG->Cam.ProjMat;
        P[0] = 0.0f; P[1] = M[0][0]; P[2] = M[0][2]; P[3] = M[1][1]; P[4] = M[1][2]; P[5] = M[2][2]; P[6] = M[2][3];
        pp = P;
    }
    cLightEnv* env = LightMgr.getEnvPtr();
    float fog = 0.0f;
    if (!(pG->Disp_flg & 0x4000) && !(pG->Status_flg[1] & 0x04000000) && env->Fog.Type != 0) {
        fog = re4dc_fog_far_for_gate(env->Fog.End * (1.0f - env->far_play_ratio) + 1.0f);
    }
    re4dc_invis_begin(pp, fog);
}
// ModelTrans, the OT entry made: 1 when the Ganado is skipped.
static int invisSkip(cModel* m, int ot, int ret)
{
    if (m->kindid != 0 || m->ot_type != 0 || (m->be_flag & 0x4001) != 1 || m->Shader_type != 0 ||
        (pG->Status_flg[2] & 0x00100000) || (pG->Debug_flg[1] & 0x40000000)) {
        return 0;
    }
    const unsigned k = re4dc_invis_decide(m);
#if RE4DC_CROWD_INVIS_SKIP == 2
    (void) k; (void) ot; (void) ret;
    return 0;
#else
    if (k == 0 || (k == 2 && g_invisReplayNum == sizeof(g_invisReplay) / sizeof(g_invisReplay[0]))) {
        return 0;
    }
    if (invisAdvance(m->pModelInfo) && m->pShadowModelInfo != 0) {
        invisAdvance(m->pShadowModelInfo);
    }
    if (k == 1) {
        DeleteOtData(ot, (u16) ret);
    } else {
        g_invisReplay[g_invisReplayNum++] = m;
    }
    return 1;
#endif
}
#endif

#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
#include "other_profile_trans.inc"
#endif
#if defined(RE4DC_FLASHLIGHT_POOL) && RE4DC_FLASHLIGHT_POOL
// FLASHLIGHT_POOL=1 (effects30.mk; #55 item 3, user option B; render only, approximation): the night rooms' room
// light data attach a spot light (xD 3 / 6) and a point light to Leon (r11e: chest spot + ~4 m point). The GameCube
// lights the world with them; our PS2 world is pre-lit and reads no game light. Here, in a room where such a spot is
// alive on the player, an additive light pool (a 12-triangle Gouraud fan, no texture, no GameCube asset) is laid on
// the ground RE4DC_FLASHLIGHT_POOL_DIST ahead of Leon along his facing, with the spot's + half the point's colour,
// fading to nothing at its rim; the normal depth test hides it behind nearer walls (native_flashlight_pool.inc).
// The translucent list's auto-sort forces GEQUAL on the PVR, so the pool lights the floor, not wall faces.
// Reads game state only (light list, player pose, camera).
#include "native_ui.h"
#ifndef RE4DC_FLASHLIGHT_POOL_DIST
#define RE4DC_FLASHLIGHT_POOL_DIST 3500
#endif
#ifndef RE4DC_FLASHLIGHT_POOL_SIZE
#define RE4DC_FLASHLIGHT_POOL_SIZE 1800
#endif
#ifndef RE4DC_FLASHLIGHT_POOL_GAIN
#define RE4DC_FLASHLIGHT_POOL_GAIN 150
#endif
extern "C" void re4dc_log(const char* fmt, ...);
static void re4dc_flashlight_pool()
{
    static u16 s_room = 0xFFFF;
    cLight* spot = 0;
    cLight* point = 0;
    if (pPL == 0) {
        return;
    }
    for (cLight* l = LightMgr.pAlive; l; l = (cLight*) l->pNext) {
        if (l->pParent != (cModel*) pPL || !LightMgr.checkKind(l->Kind)) {
            continue;
        }
        if ((l->xD == 3 || l->xD == 6) && l->Radius > 0.0f && l->Radius <= 4000.0f && !spot) {   // a hand-held torch; r11d's r=18673 room spot is not one
            spot = l;
        } else if (l->xD <= 2 && l->Radius > 0.0f && !point) {
            point = l;
        }
    }
    if (spot == 0) {
        return;
    }
    f32 rgb[3];
    const GXColor sc = spot->DispCol;
    const f32 ks = (f32) (int) sc.a * 0.0078125f;
    rgb[0] = sc.r * ks;
    rgb[1] = sc.g * ks;
    rgb[2] = sc.b * ks;
    if (point) {
        const GXColor pc = point->DispCol;
        const f32 kp = (f32) (int) pc.a * 0.0078125f * 0.5f;
        rgb[0] += pc.r * kp;
        rgb[1] += pc.g * kp;
        rgb[2] += pc.b * kp;
    }
    u32 argb = 0xFF000000U;
    for (int c = 0; c < 3; c++) {
        f32 v = rgb[c] * (RE4DC_FLASHLIGHT_POOL_GAIN / 100.0f);
        argb |= (u32) (v > 255.0f ? 255.0f : v) << (16 - 8 * c);
    }
    const f32 a = pPL->ang.y, s = sinf(a), co = cosf(a);
    Vec c0 = pPL->pos;
    c0.x += s * RE4DC_FLASHLIGHT_POOL_DIST;
    c0.z += co * RE4DC_FLASHLIGHT_POOL_DIST;
    c0.y += 20.0f;
    Re4dcEffectFan f;
    memset(&f, 0, sizeof(f));
    f.n = 12;
    Vec v;
    PSMTXMultVec(pG->Cam.v_mat, &c0, &v);
    f.centre[0] = v.x;
    f.centre[1] = v.y;
    f.centre[2] = v.z;
    for (u32 i = 0; i < f.n; i++) {
        const f32 t = (f32) i * (6.2831855f / 12.0f);
        const f32 along = cosf(t) * RE4DC_FLASHLIGHT_POOL_SIZE * 1.3f, across = sinf(t) * RE4DC_FLASHLIGHT_POOL_SIZE;
        Vec w = {c0.x + s * along + co * across, c0.y, c0.z + co * along - s * across};
        PSMTXMultVec(pG->Cam.v_mat, &w, &v);
        f.ring[i][0] = v.x;
        f.ring[i][1] = v.y;
        f.ring[i][2] = v.z;
    }
    f.centre_argb = argb;
    CameraSetProjection(1);
    RE4DC_GXF_GET_PROJECTION(f.projection);
    RE4DC_GXF_GET_VIEWPORT(f.viewport);
    if (s_room != G_ROOM_ID) {
        s_room = G_ROOM_ID;
        re4dc_log("flashlight pool: room=%03x spot xD=%u r=%d disp=%08x point=%s argb=%08x\n", (unsigned) G_ROOM_ID,
                  (unsigned) spot->xD, (int) spot->Radius, *(const u32*) &spot->DispCol, point ? "yes" : "no", argb);
    }
    re4dc_effect_fan(&f);
}
#endif
void Trans()
{
    u8* primStart = (u8*) pG->prim_base;
    void (*func)(cModel*);
    cUnit* u;

#if !defined(__PPC__)
    const int roomSwapped = roomListsSwapped();
#else
    const int roomSwapped = 0;
#endif
#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
    OTHER_INSTR_BEGIN();
    otherAliveSnapshot(roomSwapped);
    OTHER_INSTR_END();
#endif
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
    invisTransBegin();
#endif
#if RE4DC_COARSE
    coarseTick = re4dc_coarse_tick(re4dc_pace_drop_models);
    // No coarse image of a swapped room: its plan walks EmMgr too (sourceActorPlan).
    if (roomSwapped) {coarseTick = 0;re4dc_coarse_image = 0;}
#if RE4DC_COARSE_SOURCE_ACTORS

    OTHER_PHASE(1);
#if RE4DC_ACTOR_TRANSACTION
    re4dc_actor_transaction_retire();
#endif
    sourceActorLedger.retire();sourceActorActive=false;
    if(coarseTick && !re4dc_pace_drop_models) {
        // Full/check source path wins before any PTS presentation stage is skipped.
        const int plan=RE4DC_PACE_CHECK?0:sourceActorPlan();
        if(plan<=0) {coarseTick=0;re4dc_coarse_image=0;}
        if(plan<0){OTHER_PHASE(4);return;} // explicit malformed-list failure; never rewalk a cycle
    }
    OTHER_PHASE(4);
#endif
#endif
#if RE4DC_FRONT_LEAN && defined(__sh__)
    g_leanSkippedNum = 0;
#endif
#if RE4DC_PACE_CATCHUP >= 2
#if RE4DC_PACE_TRANS_SKIP
    // Bit 2048 (qualified): a dropped image still queues the effect draws that carry state
    // (esp.cpp / espgen.cpp logic-only mode); bits 1 / 2 alone skip the stages outright.
    re4dc_esp_logic_queued = 0;
    if (!(pG->Disp_flg & 0x04000000)) {
        if (!PTS(1)) {
            EspTrans();
        } else if (RE4DC_PACE_TRANS_SKIP & 2048) {
            re4dc_esp_logic_only = 1;
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
            re4dc_esp_sprite_pass = coarseTick && !re4dc_pace_drop_models;   // a drawn coarse image
#endif
            EspTrans();
            re4dc_esp_logic_only = 0;
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
            re4dc_esp_sprite_pass = 0;
#endif
        }
    }
    if (!(pG->Disp_flg & 0x01000000)) {
        if (!PTS(2)) {
            EspgenTrans();
        } else if (RE4DC_PACE_TRANS_SKIP & 2048) {
            re4dc_esp_logic_only = 1;
#if RE4DC_WATER45_NATIVE
            re4dc_espgen_draw_pass = coarseTick && !re4dc_pace_drop_models;   // a drawn coarse image (espgen.cpp)
#endif
            EspgenTrans();
#if RE4DC_WATER45_NATIVE
            re4dc_espgen_draw_pass = 0;
#endif
            re4dc_esp_logic_only = 0;
        }
    }
#else
    if (!(pG->Disp_flg & 0x04000000) && !PTS(1)) {
        EspTrans();
    }
    if (!(pG->Disp_flg & 0x01000000) && !PTS(2)) {
        EspgenTrans();
    }
#endif
    if (!(pG->Disp_flg & 0x00400000) && !PTS(4)) {
        CtrlMgr.trans();
    }
    ProcessTickGet(5, "EspTrans");
    if (!PTS(8)) {
        ShadowTrans();
    }
    ProcessTickGet(5, "ShadowTrans");
    ProcessTickGet(5, "MirrorTrans");
#if defined(RE4DC_CLOTH_NATIVE) && RE4DC_CLOTH_NATIVE && RE4DC_COARSE
    // CLOTH_NATIVE: a drawn coarse image runs no world OT, so its cloth sheets go to the native effect FIFO now
    // (PACE_TRANS_SKIP bit 16 skipped them on every coarse image; dropped images still skip).
    if (!(pG->Disp_flg & 0x00020000) && PTS(16) && coarseTick && !re4dc_pace_drop_models) {
        ClothDrawNow();
    } else
#endif
    if (!(pG->Disp_flg & 0x00020000) && !PTS(16)) {
        ClothDraw();
    }
    ProcessTickGet(5, "ClothTrans");
#if defined(RE4DC_FLASHLIGHT_POOL) && RE4DC_FLASHLIGHT_POOL
#if RE4DC_COARSE
    if (!re4dc_pace_drop_models)
#endif
    {
        re4dc_flashlight_pool();
    }
#endif
    if (!(pG->Disp_flg & 0x00100000) && !PTS(32)) {
        FilterTrans();
    }
    if (!(pG->Disp_flg & 0x04000000) && !PTS(64)) {
        if (!(pG->Disp_flg & 0x400)) {
            TransTexRenderMgr();
        }
    }
#else
    if (!(pG->Disp_flg & 0x04000000)) {
        EspTrans();
    }
    if (!(pG->Disp_flg & 0x01000000)) {
        EspgenTrans();
    }
    if (!(pG->Disp_flg & 0x00400000)) {
        CtrlMgr.trans();
    }
    ProcessTickGet(5, "EspTrans");
    ShadowTrans();
    ProcessTickGet(5, "ShadowTrans");
    ProcessTickGet(5, "MirrorTrans");
    if (!(pG->Disp_flg & 0x00020000)) {
        ClothDraw();
    }
    ProcessTickGet(5, "ClothTrans");
    if (!(pG->Disp_flg & 0x00100000)) {
        FilterTrans();
    }
    if (!(pG->Disp_flg & 0x04000000)) {
        if (!(pG->Disp_flg & 0x400)) {
            TransTexRenderMgr();
        }
    }
#endif
    OTHER_PHASE(1);
#if RE4DC_PACE_CATCHUP >= 2
    // v2: a dropped image needs no model OT (iteration k+1 draws nothing); every other Trans
    // stage above (effects, shadows, cloth, filters, render textures) ran as usual.
    // PACE_CHECK: run it anyway and prove it leaves every logic-trace field unchanged.
#if RE4DC_COARSE
    const int paceDrop = re4dc_pace_drop_models || coarseTick;
#else
    const int paceDrop = re4dc_pace_drop_models;
#endif
#if RE4DC_PACE_CHECK
    if (paceDrop) {
        re4dc_pace_check(0);
    }
#endif
    if (!paceDrop || RE4DC_PACE_CHECK) {
#endif
    if (!roomSwapped) {
    func = objTrans;
    for (u = ObjMgr.pAlive; u != 0;) {
        cUnit* cur = u;
        u = u->pNext;
        RE4DC_C20_PREF_OBJ(u);   // PREF_WALK (cache20.h): the next model while this one is prepared
        func((cModel*) cur);
    }
    func = emTrans;
    for (u = EmMgr.pAlive; u != 0;) {
        cUnit* cur = u;
        u = u->pNext;
        RE4DC_C20_PREF_OBJ(u);
        func((cModel*) cur);
    }
    }
#if RE4DC_PACE_CATCHUP >= 2
    }
#if RE4DC_COARSE && (RE4DC_COARSE_SOURCE_OBJECTS || RE4DC_COARSE_SOURCE_ACTORS)
    // Coarse draw_actors has no ObjMgr path. Restore the original preparation
    // and OTs for non-scenery source objects at their ordinary model boundary.
    // The original full/check branch above wins, so no object is prepared twice.
    else if (coarseTick && !re4dc_pace_drop_models) {
#if RE4DC_COARSE_SOURCE_OBJECTS
        unsigned source_calls=0, scenery_skipped=0;
        func = objTrans;
#if RE4DC_COARSE_SCENERY_FALLBACK
        const int skip_scenery = re4dc_ps2_world_covers(G_ROOM_ID);
#else
        const int skip_scenery = 1;
#endif
        for (u = ObjMgr.pAlive; u != 0;) {
            cUnit* cur = u;
            u = u->pNext; // original traversal captures next before the callback
            cModel* model = (cModel*) cur;
            if (model->kindid == 2 && skip_scenery
#if RE4DC_PS2_WORLD_PARTS
                && !re4dc_ps2_dyn_source(G_ROOM_ID, model, model->serial)
#endif
            ) { ++scenery_skipped; continue; }
            func(model); // source visibility, culling, materials, skin and OT order
            ++source_calls;
        }
        if (!(pG->Frame_cnt % 120))
            re4dc_log("SOURCE_OBJECTS t=%u calls=%u scenery_skipped=%u\n",
                unsigned(pG->Frame_cnt),source_calls,scenery_skipped);
#endif
#if RE4DC_COARSE_SOURCE_ACTORS
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
        g_invisArmed = !roomSwapped;
#endif
        if(!sourceActorPrepare())sourceActorLedger.retire();
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
        g_invisArmed = 0;
#endif
#endif
    }
#endif
#if RE4DC_PACE_CHECK
    if (paceDrop) {
        re4dc_pace_check(1);
    }
#endif
#endif
    OTHER_PHASE(4);
    ProcessTickGet(5, "objTrans");
    DCStoreRangeNoSync(primStart, (u8*) pG->prim_base - primStart);
}

// Picks the lights for an enemy model that will be drawn (LightMgr.setModel2), honouring the
// player / partner / enemy hide flags of Disp_flg.
void lightSetEm(cModel* m)
{
    if ((m->be_flag & 3) != 3) {
        return;
    }
    if (m == pPL) {
        if (pG->Disp_flg & 0x40000000) {
            return;
        }
    } else if (m == pSUB) {
        if (pG->Disp_flg & 0x20000000) {
            return;
        }
    } else {
        if ((s32) pG->Disp_flg < 0) {
            return;
        }
    }
    LightMgr.setModel2(m);
}

// Picks the lights for an object model that will be drawn (scenery kind 2: Disp_flg 0x08000000,
// other objects 0x10000000 hide them).
void lightSetObj(cModel* m)
{
    if ((m->be_flag & 3) != 3) {
        return;
    }
    if (m->kindid == 2) {
        if (pG->Disp_flg & 0x08000000) {
            return;
        }
    } else {
        if (pG->Disp_flg & 0x10000000) {
            return;
        }
    }
    LightMgr.setModel2(m);
}

#if defined(RE4DC_ENCV) && RE4DC_ENCV
// ENC_CENSUS=2 (game30.mk; diagnostic, lane iv): a Ganado's emTrans / ModelRender run inside a wrapper named after
// its visibility state in the previous drawn image (coarse.cpp re4dc_encv_*), so the hw model's call tree prices
// each state; the census notes this image's state (hidden, outside the view test, reached the OT, then the draw's
// outcome). Distinct stores keep the wrappers from being merged or tail-called.
extern "C" unsigned re4dc_encv_trans_pick(cModel* m);     // ~0u: not a Ganado
extern "C" unsigned re4dc_encv_render_pick(cModel* m);    // ~0u: not a Ganado
extern "C" void re4dc_encv_trans_note(cModel* m, unsigned state);
extern "C" void re4dc_encv_render_note(cModel* m, unsigned emitted, unsigned input);
extern "C" void re4dc_encv_render_done();
extern "C" unsigned re4dc_model_output_count();
extern "C" unsigned re4dc_model_input_count();
static cModel* g_encvTrans;  // the Ganado whose emTrans runs (ModelTrans notes only that one)
volatile unsigned g_encvLast;
static void emTransBody(cModel* m);
static void ModelRenderBody(cModel* m);
#define ENCV_TRANS_WRAP(name, k)                                                                                   \
    static __attribute__((noinline, noipa)) void name(cModel* m)                                                    \
    {                                                                                                               \
        g_encvLast = (k);                                                                                           \
        emTransBody(m);                                                                                             \
        g_encvLast = (k) + 100;                                                                                     \
    }
#define ENCV_RENDER_WRAP(name, k)                                                                                  \
    static __attribute__((noinline, noipa)) void name(cModel* m)                                                    \
    {                                                                                                               \
        g_encvLast = (k) + 200;                                                                                     \
        const unsigned o0 = re4dc_model_output_count(), i0 = re4dc_model_input_count();                             \
        ModelRenderBody(m);                                                                                         \
        SOURCE_WORLD_MODEL_POSTLUDE_GUARD(m);                                                                       \
        re4dc_encv_render_note(m, re4dc_model_output_count() - o0, re4dc_model_input_count() - i0);                \
    }
extern "C" {
ENCV_TRANS_WRAP(re4dc_iv_t_new, 0)
ENCV_TRANS_WRAP(re4dc_iv_t_hidden, 1)
ENCV_TRANS_WRAP(re4dc_iv_t_frustum, 2)
ENCV_TRANS_WRAP(re4dc_iv_t_off, 3)
ENCV_TRANS_WRAP(re4dc_iv_t_fog, 4)
ENCV_TRANS_WRAP(re4dc_iv_t_empty, 5)
ENCV_TRANS_WRAP(re4dc_iv_t_drawn, 6)
ENCV_TRANS_WRAP(re4dc_iv_t_source, 7)
ENCV_TRANS_WRAP(re4dc_iv_t_other, 8)
ENCV_RENDER_WRAP(re4dc_iv_r_new, 0)
ENCV_RENDER_WRAP(re4dc_iv_r_hidden, 1)
ENCV_RENDER_WRAP(re4dc_iv_r_frustum, 2)
ENCV_RENDER_WRAP(re4dc_iv_r_off, 3)
ENCV_RENDER_WRAP(re4dc_iv_r_fog, 4)
ENCV_RENDER_WRAP(re4dc_iv_r_empty, 5)
ENCV_RENDER_WRAP(re4dc_iv_r_drawn, 6)
ENCV_RENDER_WRAP(re4dc_iv_r_source, 7)
ENCV_RENDER_WRAP(re4dc_iv_r_other, 8)
}
void emTrans(cModel* m)
{
    const unsigned s = re4dc_encv_trans_pick(m);
    if (s == ~0u) {
        emTransBody(m);
        return;
    }
    g_encvTrans = m;
    switch (s) {
    case 0: re4dc_iv_t_new(m); break;
    case 1: re4dc_iv_t_hidden(m); break;
    case 2: re4dc_iv_t_frustum(m); break;
    case 3: re4dc_iv_t_off(m); break;
    case 4: re4dc_iv_t_fog(m); break;
    case 5: re4dc_iv_t_empty(m); break;
    case 6: re4dc_iv_t_drawn(m); break;
    case 7: re4dc_iv_t_source(m); break;
    default: re4dc_iv_t_other(m); break;
    }
    g_encvTrans = 0;
}
void ModelRender(cModel* m)
{
#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
    SourceWorldModelScope sourceWorldModelScope;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(sourceWorldModelBlocked(m))return;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(sourceWorldR11fModelBlocked(m))return;
#endif
    const unsigned s = re4dc_encv_render_pick(m);
    switch (s) {
    case 0: re4dc_iv_r_new(m); break;
    case 1: re4dc_iv_r_hidden(m); break;
    case 2: re4dc_iv_r_frustum(m); break;
    case 3: re4dc_iv_r_off(m); break;
    case 4: re4dc_iv_r_fog(m); break;
    case 5: re4dc_iv_r_empty(m); break;
    case 6: re4dc_iv_r_drawn(m); break;
    case 7: re4dc_iv_r_source(m); break;
    case 8: re4dc_iv_r_other(m); break;
    default: ModelRenderBody(m); break;
    }
    g_encvLast = 300;  // no sibling call: the call tree must see each wrapper as a callee of ModelRender
}
#define ENCV_TRANS_NOTE(m, s)                                                                                      \
    if ((m) == g_encvTrans) re4dc_encv_trans_note((m), (s))
#else
#define ENCV_TRANS_NOTE(m, s)
#endif

// Transform pass of one enemy (skipped when its Disp_flg hide bit is set).
#if defined(RE4DC_ENCV) && RE4DC_ENCV
static void emTransBody(cModel* m)
#else
void emTrans(cModel* m)
#endif
{
    if (m == pPL) {
        if (pG->Disp_flg & 0x40000000) {
            return;
        }
    } else if (m == pSUB) {
        if (pG->Disp_flg & 0x20000000) {
            return;
        }
    } else {
        if ((s32) pG->Disp_flg < 0) {
            ENCV_TRANS_NOTE(m, 1);
            return;
        }
#if defined(RE4DC_ENC_SKIP_GANADO) && RE4DC_ENC_SKIP_GANADO
        // ENC_SKIP_GANADO (game30.mk; diagnostic A/B only, default 0, lane enc): Ganados (kindid 0, ids
        // 0x10..0x20) get no transform pass: no OT entry, screen matrices, skinning, lights or draw. Prices the
        // render side of the Ganados in a view; never a play build.
        if (m->kindid == 0 && m->id >= 0x10 && m->id <= 0x20) {
            return;
        }
#endif
    }
    ModelTrans(m);
}

// Transform pass of one object (skipped when hidden by Disp_flg).
void objTrans(cModel* m)
{
    if (m->kindid == 2) {
        if (pG->Disp_flg & 0x08000000) {
            return;
        }
    } else {
        if (pG->Disp_flg & 0x10000000) {
            return;
        }
    }
    ModelTrans(m);
}

// Light origin of the model in world space (lightInfo.ofs in the space of parts x52 - 1).
// `p` is one function-scope local shared by every expansion (a block-scope `p` per expansion is
// local-allocated and cannot take r31).
#define LIGHT_POS(m, li, pos)                                           \
    {                                                                   \
        p = (m)->getPartsPtr((li)->PartsNo - 1);                            \
        PSMTXMultVecSR(p->mat, &(li)->Offset, &(pos));                     \
        PSVECAdd(&(pos), &p->world, &(pos));                         \
    }

// Registers a visible model (be_flag 1 | 2 | 4; in events only be_flag 0x800 models) in the
// ordering tables by ot_type: 0 world depth-sorted (7: plus the 0xB translucent table, drawn a
// second time), 1 model table, 2 world, 3 / 4 / 5 fixed 0xB buckets, 6 table 0x10, 8 table 0x14;
// frustum-culled by the light-info sphere (scaled). Then skins its vertices (commonScreenMat)
// — a skinning failure removes the entry again.
void ModelTrans(cModel* m)
{
    Vec pos;
    int ret = 0xFFFF;
    int ret2 = 0xFFFF;
    int ot;
    int ot2;
    cLightInfo* li;
    f32 radius;
    cModel* p;

    if ((pG->Status_flg[1] & 0x10000000) && !(m->be_flag & 0x800)) {
        ENCV_TRANS_NOTE(m, 1);
        return;
    }
    if (!(m->be_flag & 2)) {
        ENCV_TRANS_NOTE(m, 1);
        return;
    }
    if (!(m->be_flag & 4)) {
        ENCV_TRANS_NOTE(m, 1);
        return;
    }
    li = &m->LightInfo;
    if (isBit(m->be_flag, 0x1000)) {
        radius = 999999.0f;
    } else {
        radius = SQRTF(m->LightInfo.Size.x * m->LightInfo.Size.x + m->LightInfo.Size.y * m->LightInfo.Size.y + m->LightInfo.Size.z * m->LightInfo.Size.z);
        if (m->scale.x == m->scale.y && m->scale.x == m->scale.z) {
            radius *= m->scale.x;
        } else {
            if (m->scale.x > m->scale.y) {
                if (m->scale.x > m->scale.z) {
                    radius *= m->scale.x;
                } else {
                    radius *= m->scale.z;
                }
            } else {
                if (m->scale.y > m->scale.z) {
                    radius *= m->scale.y;
                } else {
                    radius *= m->scale.z;
                }
            }
        }
    }
    ot = OT_MAX;
    ot2 = OT_MAX;
    switch (m->ot_type) {
    case 7:
        m->be_flag &= ~0x08000000;
        if (m->pParts == 0) {
            ret2 = AddOtWorldPosRadius(m, (void (*)(void*)) ModelRender, &m->pos, radius, 1, 1.0f);
            ot2 = 0x11;
        } else {
            ot2 = 0x11;
            LIGHT_POS(m, li, pos);
            ret2 = AddOtWorldPosRadius(m, (void (*)(void*)) ModelRender, &pos, radius, 1, 1.0f);
        }
        if (ret2 != 0xFFFF) {
            ot = 0xB;
            LIGHT_POS(m, li, pos);
            ret = AddOtDirect(0xB, m, (void (*)()) ModelRender, 1, 2, &pos, radius);
        } else {
            ret = 0;
            ot = 0xB;
            ret |= 0xFFFF;
        }
        break;
    case 0:
        if (m->pParts == 0) {
            ret = AddOtModelPosRadius(m, (void (*)(void*)) ModelRender, &m->pos, radius, 1, 1.0f);
            ot = 0xD;
        } else {
            cModel* p = m->getPartsPtr(0);
            ot = 0xD;
            ret = AddOtModelPosRadius(m, (void (*)(void*)) ModelRender, &p->world, radius, 1, 1.0f);
        }
        break;
    case 1:
        if (m->pParts == 0) {
            ret = AddOtWorldPosRadius(m, (void (*)(void*)) ModelRender, &m->pos, radius, 1, 1.0f);
            ot = 0x11;
        } else {
            ot = 0x11;
            LIGHT_POS(m, li, pos);
            ret = AddOtWorldPosRadius(m, (void (*)(void*)) ModelRender, &pos, radius, 1, 1.0f);
        }
        break;
    case 2:
        ot = 0xB;
        LIGHT_POS(m, li, pos);
        ret = AddOtDirect(0xB, m, (void (*)()) ModelRender, 4, 2, &pos, radius);
        break;
    case 3:
        ot = 0xB;
        LIGHT_POS(m, li, pos);
        ret = AddOtDirect(0xB, m, (void (*)()) ModelRender, 2, 2, &pos, radius);
        break;
    case 4:
        ot = 0xB;
        LIGHT_POS(m, li, pos);
        ret = AddOtDirect(0xB, m, (void (*)()) ModelRender, 1, 2, &pos, radius);
        break;
    case 5:
        ot = 0x10;
        LIGHT_POS(m, li, pos);
        ret = AddOtDirect(0x10, m, (void (*)()) ModelRender, 0, 2, &pos, radius);
        break;
    case 6:
        if (m->pParts == 0) {
            ret = AddOtDirect(0x14, m, (void (*)()) ModelRender, 1, 1, NULL, 0.0f);
            ot = 0x14;
        } else {
            m->getPartsPtr(0);
            ot = 0x14;
            ret = AddOtDirect(0x14, m, (void (*)()) ModelRender, 1, 1, NULL, 0.0f);
        }
        break;
    default:
        pLog->err(0, 0, "ModelTrans() : OT_TYPE[%d] invalid.", m->ot_type);
        ret = 0;
        ret |= 0xFFFF;
        break;
    }
    if (ot == OT_MAX) {
        pLog->err(0, 0, "ModelTrans() : OT_TYPE not init.");
        ret = 0;
        ret |= 0xFFFF;
    }
    ENCV_TRANS_NOTE(m, ret != 0xFFFF ? 9u : 2u);  // 9: reached the OT (the draw decides), 2: outside the view test
    if (ret != 0xFFFF) {
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
        if (g_invisArmed && invisSkip(m, ot, ret)) {
            return;
        }
#endif
#if RE4DC_SKIN_PALETTE_LAZY
        g_skinLazyArm = 1;  // this commonScreenMat may defer weight palettes (SKIN_PALETTE_LAZY)
#endif
#if RE4DC_FRONT_LEAN && defined(__sh__)
        const int lean = frontLean(m);
        int screen;
        g_leanWeights = lean & FRONT_LEAN_WEIGHTS;
        screen = commonScreenMat(m);
        g_leanWeights = 0;
        if (screen == 0) {
#else
        if (commonScreenMat(m) == 0) {
#endif
            ENCV_TRANS_NOTE(m, 8);  // screen matrices failed: the OT entry is deleted
            DeleteOtData(ot, (u16) ret);
            if (m->ot_type == 7) {
                DeleteOtData(ot2, (u16) ret2);
            }
#if RE4DC_ACTOR_TEX_PREP_DRAW
        } else {
            sourceActorTextureDraw(m);
#endif
        }
        if (m->kindid == 0) {
            lightSetEm(m);
#if RE4DC_FRONT_LEAN && defined(__sh__)
        } else if ((lean & FRONT_LEAN_LIGHTS) && (m->be_flag & 3) == 3 && !(pG->Disp_flg & 0x08000000) &&
                   g_leanSkippedNum < sizeof(g_leanSkipped) / sizeof(g_leanSkipped[0])) {
            // lightSetObj() for kindid 2 without the light search: the list only feeds GX light
            // objects the lit native mesh never reads. Cleared, so nothing can follow a stale
            // light pointer; ModelRender recomputes it if the model stops qualifying.
            memclr_asm(m->LightInfo.pLight, sizeof(m->LightInfo.pLight));
            g_leanSkipped[g_leanSkippedNum++] = m;
#endif
        } else {
            lightSetObj(m);
        }
    } else {
        if (pG->Debug_flg[0] & 0x10) {
            if (m->kindid == 0) {
                lightSetEm(m);
            } else {
                lightSetObj(m);
            }
        }
    }
}

// Builds this frame's vertex buffers for a model (and its shadow model info). 0 when the model is
// off / hidden or a buffer could not be had.
int commonScreenMat(cModel* m)
{
#if RE4DC_SKIN_PALETTE_LAZY
    // Only ModelTrans's call (armed just before it) defers; mirror / shadow / TexRender calls build eagerly.
    g_skinLazyNow = g_skinLazyArm;
    g_skinLazyArm = 0;
#endif
    int off = !(m->be_flag & 1);

    if (off) {
        return 0;
    }
    if (!(m->be_flag & 2)) {
        return 0;
    }
    if (!(m->be_flag & 4)) {
        return 0;
    }
    if (commonScreenMatSub(m, m->pModelInfo) == 0) {
        return 0;
    }
    if (m->pShadowModelInfo != 0) {
        if (commonScreenMatSub(m, m->pShadowModelInfo) == 0) {
            return 0;
        }
    }
    return 1;
}

#define UV_WRAP_HI(x)                       \
    {                                       \
        f32 a_ = (x);                       \
        if (a_ > 2.0f) {                    \
            f32 b_;                         \
            do {                            \
                b_ = a_ - 2.0f;             \
                a_ = b_;                    \
            } while (b_ > 2.0f);            \
            (x) = b_;                       \
        }                                   \
    }
#define UV_WRAP_LO(x)                       \
    {                                       \
        f32 a_ = (x);                       \
        if (a_ < 0.0f) {                    \
            f32 b_;                         \
            do {                            \
                b_ = a_ + 2.0f;             \
                a_ = b_;                    \
            } while (b_ < 0.0f);            \
            (x) = b_;                       \
        }                                   \
    }

// For every model info of the list: advances the texture animation / UV scroll, allocates the
// position (and normal) buffers from the prim buffer (unskinned single-part models draw from the
// original vertices), builds the weight palette from the parts matrices, applies the shape morphs
// (be_flag bit1) and skins the vertices (paired-single). 0 on an invalid pointer / full buffer.
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
extern "C" void re4dc_registry_snapshot(cModel*, const Mtx*);
#endif
int commonScreenMatSub(cModel* m, cModelInfo* info)
{
#if defined(__sh__)
    unsigned dc_stamp=re4dc_model_source_stamp();
#endif
#if RE4DC_SKIN_PALETTE_LAZY
    // ModelTrans's call: the parts matrices are built only when an info needs its palette now (SKIN_LAZY_MTX).
    int dc_mtx_built = 1;
#if RE4DC_FRONT_LEAN && defined(__sh__)
    if (!g_leanWeights)
#endif
    {
        if (g_skinLazyNow) {
            dc_mtx_built = 0;
        } else {
            calcWeightMat(m);
            g_skinLazyMtx = 0;
        }
    }
#else
#if RE4DC_FRONT_LEAN && defined(__sh__)
    // Every info of this model takes the rigid 'continue' below: nothing reads the palette.
    if (!g_leanWeights)
#endif
    calcWeightMat(m);
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY == 2
    {
        // NATIVE_MODEL_REGISTRY=2 (compare): the palette this frame's source skinning used, for the registry's
        // render-time palette check (coarse_actor_owner_registry.inc). Registry ids only; no effect on the source.
#if RE4DC_FRONT_LEAN && defined(__sh__)
        if (!g_leanWeights)
#endif
        re4dc_registry_snapshot(m, pG->mtxPalette);
    }
#endif
#if defined(__sh__)
    re4dc_model_source_span(0,dc_stamp);
#endif

    for (; info != 0; info = info->pList) {
        ModelData* d = info->pData;
        ModelTexInfo* t = MODEL_TEX(info);
        void* src;
        void* nsrc;
        void* buf;
        u32 nVtx;
        u32 n;
        u32 size;
        u32 asize;

        if (info->flagsDC & 2) {
            t->frame++;
            if (t->frame >= t->anim[1]) {
                t->frame = 0;
            }
        }
        if (!(pG->Stop_flg & 0x08000000) && (t->flags & 1)) {
            f32 u = t->u + t->su;
            f32 v = t->v + t->sv;
            t->u = u;
            t->v = v;
            if (u > 2.0f) {
                do {
                    u -= 2.0f;
                } while (u > 2.0f);
                t->u = u;
            }
            UV_WRAP_HI(t->v);
            UV_WRAP_LO(t->u);
            UV_WRAP_LO(t->v);
        }
        if (PTR_INVALID(d)) {
            pLog->err(0, 0, "commonScreenMatSub() : pHeader ptr err.");
            return 0;
        }
        if (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1) {
            continue;
        }
        if (m->be_flag & 0x4000) {
            continue;
        }
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
        // D367 actors30 (NATIVE_ACTOR_SKIN_LAZY): the weight palette first; an
        // info the native actor path takes (unmorphed, palette copy registered)
        // skins at draw time and gets no pPosBuf/pNrmBuf here at all (NULL,
        // allocated and filled at Render() only if one of its parts declines).
        // Those arrays are read only by renderers. GQR6 ends as below.
        int dc_palette_built = 0;
        if (!(info->be_flag & 2)) {
            int re4dc_skin_defer_lazy(cModelInfo* info, ModelData* d);
#if RE4DC_SKIN_PALETTE_LAZY
            if (g_skinLazyNow) {
                // SKIN_PALETTE_LAZY: registered with its copy reserved, built at the first render read.
                if (skinDeferPending(m, info, d, &dc_mtx_built)) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                    re4dc::fa35::hit(re4dc::fa35::SkinDeferred, 1);
                    re4dc::fa35::hit(re4dc::fa35::SkinDeferredVertices, d->nVtx);
#endif
#line 1862
                    info->pPosBuf[pG->vtx_buf_no] = 0;
                    info->pNrmBuf[pG->vtx_buf_no] = 0;
                    setupGQR6(0x32073207);
                    if (d->flags & 0x20000000) {
                        setupGQR6(0x20062006);
                    }
                    continue;
                }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::SkinDeferFail, 1);
                re4dc::fa35::hit(re4dc::fa35::SkinFailVertices, d->nVtx);
#endif
#line 1870
                goto dc_skin_cpu;  // not deferred: the CPU pass below builds the palette (dc_palette_built 0)
            }
#endif
#if defined(__sh__)
            dc_stamp=re4dc_model_source_stamp();
#endif
            if (d->weight_ext_num > 0xFF) {
                MakeWeightPaletteExt((WeightExt*) d->pWeight, d->weight_ext_num);
            } else {
                MakeWeightPalette((Weight*) d->pWeight, d->weight_palette_num);
            }
#if defined(__sh__)
            re4dc_model_source_span(1,dc_stamp);
#endif
            dc_palette_built = 1;
#if RE4DC_SKIN_CENSUS
            // SKIN_CENSUS (diagnostic): Trans() infos by path, per 120 frames.
            {
                const int ok = re4dc_skin_defer_lazy(info, d);
                if (ok) { ++skincen_def; skincen_defv += d->nVtx; } else { ++skincen_fail; skincen_failv += d->nVtx; }
#line 1890
                if (ok) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                    re4dc::fa35::hit(re4dc::fa35::SkinDeferred, 1);
                    re4dc::fa35::hit(re4dc::fa35::SkinDeferredVertices, d->nVtx);
#endif
#line 1891
                    info->pPosBuf[pG->vtx_buf_no] = 0;
                    info->pNrmBuf[pG->vtx_buf_no] = 0;
                    setupGQR6(0x32073207);
                    if (d->flags & 0x20000000) {
                        setupGQR6(0x20062006);
                    }
                    continue;
                }
            }
            if (0) {
#else
            if (re4dc_skin_defer_lazy(info, d)) {
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::SkinDeferred, 1);
                re4dc::fa35::hit(re4dc::fa35::SkinDeferredVertices, d->nVtx);
#endif
#line 1904
                info->pPosBuf[pG->vtx_buf_no] = 0;
                info->pNrmBuf[pG->vtx_buf_no] = 0;
                setupGQR6(0x32073207);
                if (d->flags & 0x20000000) {
                    setupGQR6(0x20062006);
                }
                continue;
            }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::SkinDeferFail, 1);
            re4dc::fa35::hit(re4dc::fa35::SkinFailVertices, d->nVtx);
#endif
#line 1912
        }
#if RE4DC_SKIN_PALETTE_LAZY
    dc_skin_cpu:
#endif
#endif
        size = d->nVtx * 6;
        asize = size + 31;
        asize = asize >> 5 << 5;
        // The original keeps `size` live past the `+ 31` at one of the three alloc sites, so
        // `size` and `asize` conflict and `size` does not inherit asize's r3 preference
        // (mulli r9 / addi r3 instead of a chained r3). The source form that did this is
        // unknown; the empty asm reproduces the liveness without emitting code.
        asm("" : : "r"(size));
        buf = GetPrimBuff(asize);
        if (PTR_INVALID2(buf)) {
            pLog->warn(0, 0, "commonScreenMatSub() : VTX prim alloc failed.");
            return 0;
        }
        info->pPosBuf[pG->vtx_buf_no] = buf;
        if (d->flags & 0x20000000) {
            size = d->nNrm * 3;
            asize = size + 31;
            asize = asize >> 5 << 5;
        } else {
            size = d->nNrm * 6;
            asize = size + 31;
            asize = asize >> 5 << 5;
        }
        buf = GetPrimBuff(asize);
        if (PTR_INVALID2(buf)) {
            pLog->warn(0, 0, "commonScreenMatSub() : Nor prim alloc failed.");
            return 0;
        }
        info->pNrmBuf[pG->vtx_buf_no] = buf;
#if RE4DC_LEON_FACE_LAZY
        if (info->be_flag & 2) {
            const int face = faceLazyDefer(m, info, d);
            if (face < 0) {
                return 0;  // the eager pass's PTR ERR (logged there)
            }
            if (face) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::SkinDeferred, 1);
                re4dc::fa35::hit(re4dc::fa35::SkinDeferredVertices, d->nVtx);
#endif
#line 1953
                continue;
            }
        }
#endif
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
        if (!dc_palette_built) {
#endif
#if RE4DC_SKIN_PALETTE_LAZY
        SKIN_LAZY_MTX(m, dc_mtx_built)
#endif
#if defined(__sh__)
        dc_stamp=re4dc_model_source_stamp();
#endif
        if (d->weight_ext_num > 0xFF) {
            MakeWeightPaletteExt((WeightExt*) d->pWeight, d->weight_ext_num);
        } else {
            MakeWeightPalette((Weight*) d->pWeight, d->weight_palette_num);
        }
#if defined(__sh__)
        re4dc_model_source_span(1,dc_stamp);
#endif
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
        }
#endif
        setupGQR6(((d->shift << 24) | (d->shift << 8)) | 0x00070007);
        src = d->vtxOrig;
        if (info->be_flag & 2) {
            int i;
#if defined(__sh__)
            dc_stamp=re4dc_model_source_stamp();
#endif
            src = info->pPosBuf[pG->vtx_buf_no];
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK >= 2
            {
                extern void* re4dc_otwc_shape_model;
                extern u32 re4dc_otwc_shape_model_id;
                re4dc_otwc_shape_model = m;
                re4dc_otwc_shape_model_id = (u32) m->id;
            }
#endif
            for (i = 0; i < 5; i++) {
                if (i == 0) {
                    ResetShape(info, src);
                }
                if (info->shape[i].data) {
                    CalculateShape_new(info, info->shape[i].data, info->shape[i].rate, src);
                }
            }
        }
#if defined(__sh__)
        if(info->be_flag & 2)re4dc_model_source_span(2,dc_stamp);
#endif
        nVtx = d->nVtx;
        if (PTR_INVALID(info->pPosBuf[pG->vtx_buf_no]) || PTR_INVALID(src)) {
            pLog->err(0, 0, "ComnScreenMatSub() PTR ERR");
            return 0;
        }
        // Native model/shadow/mirror adapters consume these arrays on SH-4;
        // only newly packed PVR commands are transferred to TA. Keep all other
        // cache/DMA boundaries, including the separate primStart flush, intact.
#if RE4DC_NATIVE_ACTOR_SKIN && !RE4DC_NATIVE_ACTOR_SKIN_LAZY
        // D367 actors30: pPosBuf/pNrmBuf are read only by renderers. When the
        // native actor path takes this info (the palette just built is copied
        // and registered), it skins at draw time and this render-only pass is
        // skipped; GQR6 ends in the same state. Morphed infos keep the pass.
        {
            int re4dc_skin_defer(cModelInfo* info, ModelData* d);
            if (!(info->be_flag & 2) && re4dc_skin_defer(info, d)) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::SkinDeferred, 1);
                re4dc::fa35::hit(re4dc::fa35::SkinDeferredVertices, d->nVtx);
#endif
#line 2021
                setupGQR6(0x32073207);
                if (d->flags & 0x20000000) {
                    setupGQR6(0x20062006);
                }
                continue;
            }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            if (!(info->be_flag & 2)) {
                re4dc::fa35::hit(re4dc::fa35::SkinDeferFail, 1);
                re4dc::fa35::hit(re4dc::fa35::SkinFailVertices, d->nVtx);
            }
#endif
#line 2027
        }
#endif
#if defined(__sh__)
        dc_stamp=re4dc_model_source_stamp();
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::SkinCpu, 1);
        re4dc::fa35::hit(re4dc::fa35::SkinCpuVertices, nVtx);
        if (info->be_flag & 2) {
            re4dc::fa35::hit(re4dc::fa35::SkinMorph, 1);
            re4dc::fa35::hit(re4dc::fa35::SkinMorphVertices, nVtx);
        }
#endif
#line 2032
#if RE4DC_SKIN_CENSUS
        ++skincen_cpu; skincen_cpuv += nVtx;
        if (info->be_flag & 2) { ++skincen_morph; skincen_morphv += nVtx; }
        if (pG->Frame_cnt - skincen_f0 >= 120) {
            re4dc_log("SKINCEN frame=%u deferred=%u/%u defer_failed=%u/%u cpu=%u/%u morph=%u/%u\n", pG->Frame_cnt,
                      skincen_def, skincen_defv, skincen_fail, skincen_failv, skincen_cpu, skincen_cpuv, skincen_morph,
                      skincen_morphv);
            skincen_f0 = pG->Frame_cnt;
            skincen_def = skincen_defv = skincen_fail = skincen_failv = skincen_cpu = skincen_cpuv = 0;
            skincen_morph = skincen_morphv = 0;
        }
#endif
        CalcSk1_x(info->pPosBuf[pG->vtx_buf_no], src, nVtx);
#if defined(__sh__)
        re4dc_model_source_span(3,dc_stamp);
        dc_stamp=re4dc_model_source_stamp();
#endif
#if !defined(__sh__) || !RE4DC_D349_RENDERER_STACK
        DCStoreRangeNoSync(info->pPosBuf[pG->vtx_buf_no], d->nVtx * 6);
#if defined(__sh__)
        re4dc_model_source_span(5,dc_stamp);
#endif
#else
        re4dc_model_skipped_writeback(d->nVtx*6);
#endif
        setupGQR6(0x32073207);
        nsrc = d->nrmOrig;
        n = d->nNrm;
#if defined(__sh__)
        dc_stamp=re4dc_model_source_stamp();
#endif

        if (d->flags & 0x20000000) {
            void* dst = info->pNrmBuf[pG->vtx_buf_no];
            setupGQR6(0x20062006);
            CalcSk1_x2(dst, nsrc, n);
        } else {
            CalcSk1_x(info->pNrmBuf[pG->vtx_buf_no], nsrc, n);
        }
#if defined(__sh__)
        re4dc_model_source_span(4,dc_stamp);
        dc_stamp=re4dc_model_source_stamp();
#endif
#if !defined(__sh__) || !RE4DC_D349_RENDERER_STACK
        DCStoreRangeNoSync(info->pNrmBuf[pG->vtx_buf_no], d->nNrm * 6);
#if defined(__sh__)
        re4dc_model_source_span(5,dc_stamp);
#endif
#else
        re4dc_model_skipped_writeback(d->nNrm*6);
#endif
    }
    return 1;
}

#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP
// CROWD_INVIS_SKIP: commonScreenMatSub's per-info texture animation / UV scroll advance, alone (0: an invalid
// header, where commonScreenMatSub stops).
static int invisAdvance(cModelInfo* info)
{
    for (; info != 0; info = info->pList) {
        ModelTexInfo* t = MODEL_TEX(info);
        if (info->flagsDC & 2) {
            t->frame++;
            if (t->frame >= t->anim[1]) {
                t->frame = 0;
            }
        }
        if (!(pG->Stop_flg & 0x08000000) && (t->flags & 1)) {
            f32 u = t->u + t->su;
            f32 v = t->v + t->sv;
            t->u = u;
            t->v = v;
            if (u > 2.0f) {
                do {
                    u -= 2.0f;
                } while (u > 2.0f);
                t->u = u;
            }
            UV_WRAP_HI(t->v);
            UV_WRAP_LO(t->u);
            UV_WRAP_LO(t->v);
        }
        if (PTR_INVALID(info->pData)) {
            return 0;
        }
    }
    return 1;
}
// The modelview commonModelTrans loads for one info (its pm, then the camera view), as re4dc_draw_model_part hands it
// to the native parts (Re4dcModelPart::modelview, crowd_tier's distance).
static void invisInfoModelview(cModel* m, cModelInfo* info, ModelData* d, Mtx mv)
{
    Mtx pm;
    if (m->be_flag & 0x4000) {
        RE4DC_RENDER_MTXConcat(m->mat, (f32(*)[4]) &info->x5C, pm);
    } else if (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1) {
        RE4DC_RENDER_MTXConcat(m->getPartsPtr(d->pHead->partsNo)->mat, (f32(*)[4]) &info->x5C, pm);
    } else {
        RE4DC_RENDER_MTXConcat(m->pParts->mat, (f32(*)[4]) &info->x5C, pm);
    }
    RE4DC_RENDER_MTXConcat(pG->Cam.v_mat, pm, mv);
}
#if RE4DC_CROWD_INVIS_SKIP == 2
// =2: the crowd entry the source draw just left (native_actor_fast.cpp) against the one invisReplayRender would note:
// 1 equal (seen or not, and the distance bit for bit), 0 different.
static int invisCrowdCheck(cModel* m)
{
    int seen = 0;
    float best = 0.0f;
    if (re4dc_model_diagnostic_enabled()) {
        for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
            if (PTR_INVALID(info)) {
                break;
            }
            if (!(info->be_flag & 8)) {
                continue;
            }
            ModelData* d = info->pData;
            if (PTR_INVALID(d) || d->nTex > 0xF7) {
                break;
            }
            if (d->displist_num == 0) {
                continue;
            }
            Mtx mv;
            invisInfoModelview(m, info, d, mv);
            const float dist = re4dc_actor_crowd_distance(&mv[0][0]);
            if (!seen || dist < best) {
                best = dist;
            }
            seen = 1;
        }
    }
    float have = 0.0f;
    const int noted = re4dc_actor_crowd_peek(m, &have);
    return noted == seen && (!seen || memcmp(&have, &best, sizeof(best)) == 0);
}
#endif
#if RE4DC_CROWD_INVIS_SKIP == 1
static const GXColor invisCol64 = {0x40, 0x40, 0x40, 0x40};  // ModelRender's col64
// ModelRender of a kind 2 Ganado: its state calls, then commonModelTrans's texture-object / TPL cache step for every
// info it would draw (the cache and the objects stay as the source draw leaves them for the next model).
static void invisReplayRender(cModel* m, int alphaUpdate)
{
    GxWork* gx = GXWORK();
    GXSetAlphaCompare(7, 0, 1, 7, 0);
    if (m->z_mode == 0) {
        GXSetZMode(1, 3, 1);
    } else if (m->z_mode == 1) {
        GXSetZMode(1, 3, 0);
    } else if (m->z_mode == 2) {
        GXSetZMode(1, 7, 0);
    }
    CameraCurrentProjection();
    if (m->be_flag & 0x00020000) {
        GXSetNumChans(1);
        GXSetChanCtrl(0, 0, 0, 0, 0, 2, 2);
        GXSetChanCtrl(2, 0, 0, 0, 0, 2, 2);
        GXSetChanAmbColor(4, invisCol64);
        GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
    } else {
        LightSetModel(m);
    }
    if (alphaUpdate) {
        GXSetAlphaUpdate(1);
        GXSetDstAlpha(1, 0);
    }
    FRONT_TEX_FLUSH();
    // The crowd ranking (CROWD_LOD) notes the model as its source parts would: the actor frame bound at its first
    // drawn part (re4dc_draw_model_part), then one entry update per drawn info with a display list.
    const int crowd = RE4DC_MODEL_DIAG();
    int bound = 0;
    for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
        if (PTR_INVALID(info)) {
            break;
        }
        if (!(info->be_flag & 8)) {
            continue;
        }
        ModelData* d = info->pData;
        if (PTR_INVALID(d) || d->nTex > 0xF7) {
            break;
        }
        if (g_prev_tpl_addr != info->tpl_addr || g_prev_add_tpl_addr != info->pAddTpl) {
            for (u32 i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++) {
                TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
                TEXDescriptor* td;
                u8 mip;
                int filt;
                u8 edge;
                if (tpl->numDescriptors == 0) {
                    td = TEXGet(info->pAddTpl, i);
                } else if (i < tpl->numDescriptors) {
                    td = TEXGet(tpl, i);
                } else {
                    td = TEXGet(info->pAddTpl, i - tpl->numDescriptors);
                }
                if ((s32) d->flags < 0) {
                    TEXHeader* wh = td->textureHeader;
#if RE4DC_FRONT_TPL_OWNER
                    if (wh->wrapT != 1 || wh->wrapS != 1) re4dc_front_tpl_header_changed(wh);
#endif
                    wh->wrapT = 1;
                    wh->wrapS = 1;
                }
                if (td->textureHeader->minLOD == td->textureHeader->maxLOD) {
                    mip = 0;
                    filt = 1;
                } else {
                    mip = 1;
                    filt = 5;
                }
                if (aniso != 0) {
                    edge = 1;
                } else {
                    edge = td->textureHeader->edgeLODEnable;
                }
                GXInitTexObj(&gx->texObj[i], td->textureHeader->data, td->textureHeader->width, td->textureHeader->height,
                             td->textureHeader->format, td->textureHeader->wrapS, td->textureHeader->wrapT, mip);
                if (mip == 1) {
                    GXInitTexObjLOD(&gx->texObj[i], filt, 1, (f32) min_lod, (f32) max_lod, lod_bias, 0, edge, aniso);
                }
            }
            if (MODEL_EXT(m)->pTexChg != 0) {
                MODEL_EXT(m)->pTexChg->move(gx->texObj);
            }
        }
        PSet(g_prev_tpl_addr, info->tpl_addr);
        PSet(g_prev_add_tpl_addr, info->pAddTpl);
        if (crowd && d->displist_num != 0) {
            if (!bound) {
                re4dc_bind_actor_frame();
                bound = 1;
            }
            Mtx mv;
            invisInfoModelview(m, info, d, mv);
            re4dc_actor_crowd_note(m, &mv[0][0]);
        }
    }
    if (alphaUpdate) {
        GXSetAlphaUpdate(0);
        GXSetDstAlpha(0, 0);
    }
    shaderReset();
}
#endif
#endif

// Per parts: world matrix x bind matrix into the parts' weight matrix (the skinning palette base).
void calcWeightMat(cModel* m)
{
    Mtx inv;
    Mtx tmp;
    u32 i = 0;
    cPartsWk* p;

    RE4DC_RENDER_MTXInverse(m->pParts->mat, inv);
    for (p = (cPartsWk*) m->pParts; p != 0; p = p->next) {
        RE4DC_RENDER_MTXConcat(inv, ((cModel*) p)->mat, tmp);
        if (i > 0xF7) {
            pLog->err(0, 0, "commonScreenMatSub() SMAT OVERFLOW %d", i);
            break;
        }
        RE4DC_RENDER_MTXConcat(tmp, p->bindMat, pG->mtxPalette[i]);
        i++;
    }
}

// Builds the blended skinning matrices for the extended weight table (u8 percentages, more than
// 255 palette entries). Returns the count.
static int MakeWeightPaletteExt(WeightExt* w0, int n)
{
    GxWork* gx = GXWORK();
    int cnt = 0;
    int i;
    u32 wa = (u32) w0;
#define w ((WeightExt*) wa)

#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    if (n > 0) re4dc::fa35::hit(re4dc::fa35::PaletteExtended, unsigned(n));
#endif
#line 2308
    for (i = 0; i < n; i++, wa += sizeof(WeightExt)) {
        Mtx m;
        f32 total;
        int j;

        memclr_asm(m, sizeof(Mtx));
        total = 0.0f;
        for (j = 0; j < w->num; j++) {
            f32 rate;
            f32* s;
            PSQ_L_U8_TO(rate, &w->weight[j]);
            rate *= 0.01f;
            if (j == w->num - 1) {
                rate = 1.0f - total;
            }
            total += rate;
            s = (f32*) gx->mtx[w->idx[j]];
            m[0][0] += *s++ * rate;
            m[0][1] += *s++ * rate;
            m[0][2] += *s++ * rate;
            m[0][3] += *s++ * rate;
            m[1][0] += *s++ * rate;
            m[1][1] += *s++ * rate;
            m[1][2] += *s++ * rate;
            m[1][3] += *s++ * rate;
            m[2][0] += *s++ * rate;
            m[2][1] += *s++ * rate;
            m[2][2] += *s++ * rate;
            m[2][3] += *s++ * rate;
            cnt++;
        }
        PSMTXReorder(m, (f32(*)[3]) (RE4DC_LC_PALETTE + i * 0x30));
    }
#undef w
    return cnt;
}

// Builds the blended skinning matrices for the weight table (sum of parts matrices x weights, the
// last weight takes the remainder). Returns the count.
#if RE4DC_WPAL_FAST == 2 || RE4DC_WPAL_FAST == 4
extern "C" void re4dc_log(const char* fmt, ...);
#endif
#if RE4DC_WPAL_FAST >= 3
extern "C" int re4dc_wpal_sh4(const Weight* w, int n, const f32* mtx, f32* dst);  // platform/wpal_sh4.S
#endif
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM && defined(__sh__)
extern "C" unsigned re4dc_skin_sh4zam_mask;                                                  // platform/sh4zam_skin.c
extern "C" int re4dc_shz_weight_palette(const Weight* w, int n, const f32* mtx, f32* dst);  // platform/sh4zam_skin.c
#endif
static int MakeWeightPalette(Weight* w0, int n)
{
    GxWork* gx = GXWORK();
    int cnt;
    int i;
    u32 wa = (u32) w0;
#define w ((Weight*) wa)

    if (PTR_INVALID(w0)) {
        pLog->err(0, 0, "MakeWeightPalette() PTR ERR");
        return 0;
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    if (n > 0) re4dc::fa35::hit(re4dc::fa35::PaletteOrdinary, unsigned(n));
#endif
#line 2369
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM && defined(__sh__)
    // SKIN_SH4ZAM 0x20 (game30.mk; render only): the entries built in XMTRX (shz_xmtrx_init_zero + shz_xmtrx_blend per
    // weight, platform/sh4zam_skin.c), stored transposed as the loop below stores them.
    if (re4dc_skin_sh4zam_mask & 0x20u) {
        return re4dc_shz_weight_palette(w0, n, (const f32*) gx->mtx, (f32*) RE4DC_LC_PALETTE);
    }
#endif
    cnt = 0;
#if RE4DC_WPAL_FAST
    // GAME_WPAL_FAST (game30.mk; render only, exact): the same per-element operations in the same
    // order (m = ((0 + s0 * r0) + s1 * r1) ..., contract off), accumulated in registers and stored
    // transposed straight into the palette: the reference spilled all 12 sums to the stack after every
    // weight and called memclr_asm and PSMTXReorder per entry. =3: the same loop in platform/wpal_sh4.S
    // (two temps interleaved). =2 / =4 (check builds of =1 / =3): the reference loop runs after and the
    // palette words are compared ("WPAL" lines).
#if RE4DC_WPAL_FAST >= 3
    cnt = re4dc_wpal_sh4(w0, n, (const f32*) gx->mtx, (f32*) RE4DC_LC_PALETTE);
#else
    for (i = 0; i < n; i++, wa += sizeof(Weight)) {
        const int num = w->num;
        f32 m00 = 0.0f, m01 = 0.0f, m02 = 0.0f, m03 = 0.0f;
        f32 m10 = 0.0f, m11 = 0.0f, m12 = 0.0f, m13 = 0.0f;
        f32 m20 = 0.0f, m21 = 0.0f, m22 = 0.0f, m23 = 0.0f;
        f32 total = 0.0f;
        for (int j = 0; j < num; j++) {
            f32 rate;
            PSQ_L_U8_TO(rate, &w->wht[j]);
            rate *= 0.01f;
            if (j == num - 1) {
                rate = 1.0f - total;
            }
            total += rate;
            const f32* s = (const f32*) gx->mtx[w->id[j]];
            m00 += s[0] * rate;
            m01 += s[1] * rate;
            m02 += s[2] * rate;
            m03 += s[3] * rate;
            m10 += s[4] * rate;
            m11 += s[5] * rate;
            m12 += s[6] * rate;
            m13 += s[7] * rate;
            m20 += s[8] * rate;
            m21 += s[9] * rate;
            m22 += s[10] * rate;
            m23 += s[11] * rate;
        }
        cnt += num;
        f32* d = (f32*) (RE4DC_LC_PALETTE + i * 0x30);
        d[0] = m00;
        d[1] = m10;
        d[2] = m20;
        d[3] = m01;
        d[4] = m11;
        d[5] = m21;
        d[6] = m02;
        d[7] = m12;
        d[8] = m22;
        d[9] = m03;
        d[10] = m13;
        d[11] = m23;
    }
#endif
#if RE4DC_WPAL_FAST == 2 || RE4DC_WPAL_FAST == 4
    {
        static u32 wpal_entries, wpal_words, wpal_bad, wpal_calls;
        u32 fast[12];
        wa = (u32) w0;
        for (i = 0; i < n; i++, wa += sizeof(Weight)) {
            u32* d = (u32*) (RE4DC_LC_PALETTE + i * 0x30);
            memcpy(fast, d, sizeof(fast));
            Mtx m;
            f32 total = 0.0f;
            memclr_asm(m, sizeof(Mtx));
            for (int j = 0; j < w->num; j++) {
                f32 rate;
                f32* s;
                PSQ_L_U8_TO(rate, &w->wht[j]);
                rate *= 0.01f;
                if (j == w->num - 1) {
                    rate = 1.0f - total;
                }
                total += rate;
                s = (f32*) gx->mtx[w->id[j]];
                m[0][0] += *s++ * rate;
                m[0][1] += *s++ * rate;
                m[0][2] += *s++ * rate;
                m[0][3] += *s++ * rate;
                m[1][0] += *s++ * rate;
                m[1][1] += *s++ * rate;
                m[1][2] += *s++ * rate;
                m[1][3] += *s++ * rate;
                m[2][0] += *s++ * rate;
                m[2][1] += *s++ * rate;
                m[2][2] += *s++ * rate;
                m[2][3] += *s++ * rate;
            }
            PSMTXReorder(m, (f32(*)[3]) d);
            ++wpal_entries;
            for (int k = 0; k < 12; k++) {
                ++wpal_words;
                if (fast[k] != d[k]) ++wpal_bad;
            }
        }
        if ((++wpal_calls & 4095) == 0) {
            re4dc_log("WPAL calls=%u entries=%u words=%u mismatch=%u\n", wpal_calls, wpal_entries, wpal_words,
                      wpal_bad);
        }
    }
#endif
    return cnt;
#endif
    for (i = 0; i < n; i++, wa += sizeof(Weight)) {
        Mtx m;
        f32 total;
        int j;

        memclr_asm(m, sizeof(Mtx));
        total = 0.0f;
        for (j = 0; j < w->num; j++) {
            f32 rate;
            f32* s;
            PSQ_L_U8_TO(rate, &w->wht[j]);
            rate *= 0.01f;
            if (j == w->num - 1) {
                rate = 1.0f - total;
            }
            total += rate;
            s = (f32*) gx->mtx[w->id[j]];
            m[0][0] += *s++ * rate;
            m[0][1] += *s++ * rate;
            m[0][2] += *s++ * rate;
            m[0][3] += *s++ * rate;
            m[1][0] += *s++ * rate;
            m[1][1] += *s++ * rate;
            m[1][2] += *s++ * rate;
            m[1][3] += *s++ * rate;
            m[2][0] += *s++ * rate;
            m[2][1] += *s++ * rate;
            m[2][2] += *s++ * rate;
            m[2][3] += *s++ * rate;
            cnt++;
        }
        PSMTXReorder(m, (f32(*)[3]) (RE4DC_LC_PALETTE + i * 0x30));
    }
#undef w
    return cnt;
}

#if RE4DC_PS2_FX_COMMON_HAZE
extern "C" void re4dc_ps2_fx_common_render(int coarse,int skipping);
#endif
#if RE4DC_PS2_FX_ADDITIONS
extern "C" void re4dc_ps2_fx_stage1_render(int coarse,int skipping);
#endif

#if RE4DC_PS2_WORLD_SOURCE_OWNER
#include "ps2_source_world.h"
#if RE4DC_TRANSITION_GATE_DIAG
extern "C" void re4dc_ps2_source_group_package_diag(); // native_source_world.inc
extern "C" void re4dc_r200_scroll_diag();               // source_world_scroll.inc
#endif
#include "source_world_frame.inc"
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#include "source_world_r11f.inc"
#endif

// Per frame, the draw pass: runs the ordering tables in order (render textures, shadow setup,
// far sub screen, scroll, sub screen, models, shadow draw, near sub screen, effects, world, VU1
// effects, screen, cockpit, id models, messages, after-render, debug, then 0x13..0x15), the
// filter 09 post-process and the draw-sync callback. Skipped output while System_flg 0x800.
void Render()
{ DSA24_RENDER()
#if RE4DC_PS2_WORLD_R11F_OWNER
    R11fRenderScope r11fScope;
#endif
    Camera save;
    GXColor fogCol;
    GXColor c;

    g_prev_tpl_addr = (void*) -1;
    g_prev_add_tpl_addr = (void*) -1;
    GXSetCurrentGXThread();
#if RE4DC_COARSE
    const int coarse = re4dc_coarse_image;
    re4dc_coarse_image = 0;
#if RE4DC_ACTOR_TRANSACTION
    // RAII clears/restores the gate on normal completion and every early return.
    SourceActorRenderScope sourceActorRenderScope(coarse!=0);
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
    SourceActorPresentation32Scope sourceActorPresentation32Scope;
#endif
#endif
#endif
#if RE4DC_PS2_FX_COMMON_HAZE && RE4DC_PACE_CATCHUP
    // Retire a skipped image's pending token even when Render returns early.
    if(re4dc_pace_skipping)re4dc_ps2_fx_common_render(0,1);
#endif
#if RE4DC_PS2_FX_ADDITIONS && RE4DC_PACE_CATCHUP
    if(re4dc_pace_skipping)re4dc_ps2_fx_stage1_render(0,1);
#endif
#if RE4DC_PACE_CATCHUP >= 2
    // Skipped whole: the letterbox bit below is set here and cleared at the end of Render().
#if RE4DC_PACE_TRANS_SKIP
    // Bit 2048: an image whose logic-only effect pass queued draws still runs its OTs (only those
    // entries and the ones of stages that were not skipped are in them).
    if (PTSK(1024) && !((RE4DC_PACE_TRANS_SKIP & 2048) && re4dc_esp_logic_queued)) {
        return;
    }
#else
    if (PTSK(1024)) {
        return;
    }
#endif
#endif
    if (pG->System_flg & 0x800) {
        pG->Status_flg[3] |= 0x10000000;
        SetScissorState();
    }
    LightMgr.setFog();
    ExecOt(0);
    SetDrawTmpBufType(0);
    ExecOt(OT_TYPE_TEX_RENDER1);
    SetDrawTmpBufType(0);
#if RE4DC_COARSE
    // A coarse image (coarse.cpp): its opaque view replaces the world OTs after the render textures.
    if (coarse) {
        re4dc_coarse_draw();
    } else {
#endif
    ExecOt(OT_TYPE_SHADOW_SETUP);
    SetDrawTmpBufType(0);
    ExecOt(OT_TYPE_SUBSCRN_FAR);
    SetDrawTmpBufType(0);
    OTHER_PHASE(3);
    ExecOt(OT_TYPE_SCROLL);
    OTHER_PHASE(4);
    SetDrawTmpBufType(0);
    ExecOt(OT_TYPE_SUBSCRN);
    SetDrawTmpBufType(0);
    DSA24_MODEL_OT(ExecOt(OT_TYPE_MODEL));
    SetDrawTmpBufType(0);
    ExecOt(OT_TYPE_SHADOW_DRAW);
    SetDrawTmpBufType(0);
    bio4_AddBgColor();
    if (pG->Debug_flg[0] & 0x00040000) {
        drawGround(0);
    }
    ExecOt(OT_TYPE_SUBSCRN_NEAR);
#if RE4DC_COARSE
    }
#endif
#if RE4DC_PS2_FX_COMMON_HAZE
    // The prior Trans ticket has this exact source frame; native begin and
    // opaque drawing have completed, but source effect callbacks have not.
#if RE4DC_COARSE
    re4dc_ps2_fx_common_render(coarse,0);
#else
    re4dc_ps2_fx_common_render(0,0);
#endif
#endif
#if RE4DC_PS2_FX_ADDITIONS
#if RE4DC_COARSE
    re4dc_ps2_fx_stage1_render(coarse,0);
#else
    re4dc_ps2_fx_stage1_render(0,0);
#endif
#endif
    ClearZbuf();
    ExecOt(OT_TYPE_EFFECT);
    ExecOt(OT_TYPE_WORLD);
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    // Actual source model registration table 0x0b; preserve every callback.
    { SourceWorldRenderScope sourceWorldScope; ExecOt(OT_TYPE_EFFECT_VU1); }
#else
    ExecOt(OT_TYPE_EFFECT_VU1);
#endif
    ExecOt(OT_TYPE_SCREEN);
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    // Actual source model registration table 0x0d; preserve every callback.
    { SourceWorldRenderScope sourceWorldScope; ExecOt(OT_TYPE_COCKPIT); }
#else
    ExecOt(OT_TYPE_COCKPIT);
#endif
    ExecOt(OT_TYPE_ID_MODEL);
    ExecOt(OT_TYPE_MESSAGE);
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    // ModelTrans ot_type 5 registers into this table; camera/scissor are still
    // the source world context (the item camera is installed only at 0x14).
    { SourceWorldRenderScope sourceWorldScope; ExecOt(OT_TYPE_AFTER_RENDER); }
#else
    ExecOt(OT_TYPE_AFTER_RENDER);
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    // Actual source model registration table 0x11; preserve every callback.
    { SourceWorldRenderScope sourceWorldScope; ExecOt(OT_TYPE_DEBUG); }
#else
    ExecOt(OT_TYPE_DEBUG);
#endif
    ExecOt(OT_TYPE_MAX);
    pG->Status_flg[3] &= ~0x10000000;
    SetScissorState();
    ExecOt(0x13);
    save = pG->Cam;
    pG->Cam = itemCamera;
    ExecOt(0x14);
    pG->Cam = save;
    c.r = c.g = c.b = c.a = 0;
    GXSetFog(0, 0.0f, 0.0f, FRef(ZNEAR), FRef(ZFAR), c);
    ExecOt(0x15);
    if (Filter09GetbUse() == 1) {
        Filter09Render(0);
    }
    GXSetDrawSync(0xADEB);
    GXSetDrawSyncCallback(Render_DrawSyncCallback);
    pG->System_flg &= ~0x10000000;
#if defined(RE4DC_ENCV) && RE4DC_ENCV
    re4dc_encv_render_done();  // ENC_CENSUS=2: this image's Ganado states are final
#endif
}

static const GXColor col64 = {0x40, 0x40, 0x40, 0x40};
#if defined(RE4DC_STATIC_OBJ_BAKE) && RE4DC_STATIC_OBJ_BAKE
extern "C" int re4dc_sob_bake_skip(const void* model);  // model_bridge.cpp (STATIC_OBJ_BAKE)
#endif
#if defined(RE4DC_GCOBJ_SKIP) && RE4DC_GCOBJ_SKIP
// GCOBJ_SKIP (crowd.mk, measurement only): the GC-path object classes; statics only when only_static.
static inline bool re4dc_gcobj_class(unsigned kind, unsigned id, bool only_static) {
    if (kind == 0) return id == 0x41 || id == 0x43 || id == 0x45 || id == 0x46 || (!only_static && id == 0x42);
    if (kind == 1) return id == 0x00 || id == 0x21 || (!only_static && (id == 0x12 || id == 0x19));
    return false;
}
#endif

// OT callback for a model: z mode by z_mode (0 test+write, 1 test only, 2 off), the alpha-omit
// compare, then commonModelTrans with the camera view; invisible models (invisible_factor 0) skip.
#if defined(RE4DC_ENCV) && RE4DC_ENCV
static void ModelRenderBody(cModel* m)
#else
void ModelRender(cModel* m)
#endif
{ DSA24_MODEL()
#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
    OtherActorDraw otherActorDraw(m);
#endif
#if !(defined(RE4DC_ENCV) && RE4DC_ENCV)
#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
    SourceWorldModelScope sourceWorldModelScope;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(sourceWorldR11fModelBlocked(m))return;
#endif
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    // A revoked captured address is suppressed before ModelRender reads it.
    if(sourceWorldModelBlocked(m))return;
#endif
#endif
    static int modeltransalphaupdate = 1;

#if RE4DC_PACE_CATCHUP
    // Skipped iteration (pace.cpp): the draw writes nothing logic reads; the frame is not shown.
    if (re4dc_pace_skipping) {
        return;
    }
#endif
    if (m->invisible_factor * m->invisible_factor2 == 0.0f) {
        return;
    }
#if defined(RE4DC_STATIC_OBJ_BAKE) && RE4DC_STATIC_OBJ_BAKE
    // STATIC_OBJ_BAKE (crowd.mk, render only): drawn from the room's PS2 world this frame (model_bridge.cpp)
    if (m->kindid <= 1 && re4dc_sob_bake_skip(m)) {
        return;
    }
#endif
#if defined(RE4DC_GCOBJ_SKIP) && (RE4DC_GCOBJ_SKIP == 1 || RE4DC_GCOBJ_SKIP == 2)
    if (re4dc_gcobj_class(m->kindid, m->id, RE4DC_GCOBJ_SKIP == 2)) {
        return;
    }
#endif
#if RE4DC_EFM_PS2_CUT
    // EFM_PS2_CUT (render only): an effect model the PS2 release deleted is not drawn; its object runs unchanged.
    if (re4dc_efm_ps2_cut(m)) {
        return;
    }
#endif
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP == 1
    if (g_invisReplayNum != 0) {
        u32 k;
        for (k = 0; k < g_invisReplayNum && g_invisReplay[k] != m; k++) {
        }
        if (k < g_invisReplayNum) {
            g_invisReplay[k] = 0;
            invisReplayRender(m, modeltransalphaupdate);
            return;
        }
    }
#endif
#if RE4DC_ACTOR_SWAP
    // ACTOR_SWAP (benchmark): Leon / the Ganados through the reduced-mesh adapters, both OT passes.
    if (re4dc_actor_swap(m)) {
        return;
    }
#endif
#if RE4DC_FRONT_NATIVE && defined(__sh__)
    int frontNative = frontNativeOk(m);
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    if(sourceWorldCandidate(m))frontNative=0;
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(sourceWorldR11fCandidate(m))frontNative=0;
#endif
#if RE4DC_ACTOR_TRANSACTION
    if(re4dc_actor_transaction_candidate(m))frontNative=0;
#endif
#if defined(RE4DC_NMR_NO_GC_FRONT) && RE4DC_NMR_NO_GC_FRONT
    // NATIVE_MODEL_REGISTRY_NO_GC_FRONT: a registry-owned actor the ledger did not nominate this frame (door demo start)
    // is not drawn through the GameCube front path; LEON_NO_GC_FRONT: neither is Leon (native_model_registry.mk).
    if(frontNative && (re4dc_registry_owned(m) || (RE4DC_LEON_NO_GC_FRONT && m==(cModel*)pPL)))return;
#endif

#if RE4DC_FRONT_NATIVE < 2
    if (frontNative) {
        frontNativeRender(m, 0);
        return;
    }
#else
    // The replay must meet the texture objects / TPL cache the source path met.
    static GXTexObj frontTexObj[0xF8];
    u32 frontBeFlag = m->be_flag;
    void* frontTpl = g_prev_tpl_addr;
    void* frontAddTpl = g_prev_add_tpl_addr;
    FRONT_TEX_FLUSH();
    if (frontNative) {
        memcpy(frontTexObj, GXWORK()->texObj, sizeof(frontTexObj));
        re4dc_front_verify(1);
    }
#endif
#endif
    GXSetAlphaCompare(7, 0, 1, 7, 0);
    if (m->z_mode == 0) {
        GXSetZMode(1, 3, 1);
    } else if (m->z_mode == 1) {
        GXSetZMode(1, 3, 0);
    } else if (m->z_mode == 2) {
        GXSetZMode(1, 7, 0);
    }
    CameraCurrentProjection();
    if (m->be_flag & 0x00020000) {
        GXSetNumChans(1);
        GXSetChanCtrl(0, 0, 0, 0, 0, 2, 2);
        GXSetChanCtrl(2, 0, 0, 0, 0, 2, 2);
        GXSetChanAmbColor(4, col64);
        GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
    } else {
#if RE4DC_FRONT_LEAN && defined(__sh__)
        // Still lit natively: the cleared list gives LightSetModel's black-light path (channel,
        // ambient and material state unchanged). Otherwise restore a list Trans() skipped.
        g_leanRender = frontLean(m) & FRONT_LEAN_LIGHTS;
        if (!g_leanRender) {
            for (u32 k = 0; k < g_leanSkippedNum; k++) {
                if (g_leanSkipped[k] == m) {
                    LightMgr.setModel2(m);
                    break;
                }
            }
        }
#endif
        LightSetModel(m);
    }
    if (modeltransalphaupdate) {
        GXSetAlphaUpdate(1);
        GXSetDstAlpha(1, 0);
    }
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP == 2
    const unsigned invisOut0 = re4dc_model_output_count();
#endif
    commonModelTrans(m, m->pModelInfo, pG->Cam.v_mat, 0);

#if RE4DC_PS2_WORLD_R11F_OWNER || RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(sourceWorldModelPostludeBlocked(m)) {
        // Preserve caller cleanup before skipping all model-dependent observers
        // and postludes, including CROWD_INVIS_SKIP=2 and debug/front replay.
#if RE4DC_FRONT_LEAN && defined(__sh__)
        g_leanRender=0;
#endif
        if(modeltransalphaupdate){GXSetAlphaUpdate(0);GXSetDstAlpha(0,0);}
        shaderReset();
        return;
    }
#endif
#if defined(RE4DC_CROWD_INVIS_SKIP) && RE4DC_CROWD_INVIS_SKIP == 2
    if (m->kindid == 0) {
        const unsigned invisEmitted = re4dc_model_output_count() - invisOut0;
        re4dc_invis_check(m, invisEmitted, re4dc_invis_marked(m) == 2 ? invisCrowdCheck(m) : -1);
    }
#endif
#if RE4DC_FRONT_LEAN && defined(__sh__)
    g_leanRender = 0;
#endif
    if (modeltransalphaupdate) {
        GXSetAlphaUpdate(0);
        GXSetDstAlpha(0, 0);
    }
    shaderReset();
    if (pG->Debug_flg[1] & 0x40000000) {
        m->drawAllBoundingBox(m->pModelInfo);
    }
#if RE4DC_FRONT_NATIVE >= 2 && defined(__sh__)
    if (frontNative) {
        // Replay natively without drawing and compare each part with the one just submitted.
        // The replay starts from the source path's inputs: its end-of-draw mark (ot_type 7,
        // be_flag 0x08000000) would steer the info walk, so it is set aside meanwhile.
        u32 after = m->be_flag;
        m->be_flag = frontBeFlag;
        memcpy(GXWORK()->texObj, frontTexObj, sizeof(frontTexObj));
        PSet(g_prev_tpl_addr, frontTpl);
        PSet(g_prev_add_tpl_addr, frontAddTpl);
        re4dc_front_verify(2);
        frontNativeRender(m, 1);
        re4dc_front_verify(0);
        m->be_flag = after;
    }
#endif
}

// Draws every model info of `m`: the shadow-cast light when a shadow light covers it, material
// colour, vertex descriptors / arrays (skinned buffers or the original vertices), cull mode,
// texture objects for the TPL (+ added textures, anisotropy / mip filters, the cTexChg swaps),
// then per part the TEV shader (shaderSetup), blend mode (blend_mode table), alpha compare and
// the display list; foot shadows afterwards. flag bit0 = the shadow / depth pass (no alpha).
void commonModelTrans(cModel* m, cModelInfo* info, Mtx viewMat, int flag)
{
    FRONT_TEX_FLUSH();
    static int bl[5][4] = {
        {1, 4, 5, 0},
        {1, 4, 1, 0},
        {1, 1, 1, 0},
        {1, 2, 1, 0},
        {0, 1, 0, 0},
    };
    Mtx mv;
    GxWork* gx = GXWORK();
    int efbDone;
    int matSet;

    PSet(g_pShdMng, 0);
    if ((pG->Status_flg[2] & 0x00100000) && (m->be_flag & 0x02000000) && !(pG->Disp_flg & 0x00040000) &&
        (pG->Status_flg[1] & 0x200)) {
        if (!(pG->Status_flg[1] & 0x100)) {
        g_pShdMng = GetCastShadowMngPtr(m);
        if (g_pShdMng != 0) {
            ShadowLightWork* w = (ShadowLightWork*) g_pShdMng->pLight->work;
            TEXPalette* tpl;
            if (RoomGetTplAddr(w->texId, &tpl) == 0) {
                pLog->err(0, 0, "SHADOW_CAST : TEX_ID[%x] no data", w->texId);
                g_pShdMng = 0;
            }
            u32 n = m->LightInfo.getLightNum();
            if (n > 7) {
                if (!(pG->Debug_flg[1] & 0x00040000)) {
                    pLog->err(0, 0, "CAST LIGHT NUM OVER %d", n);
                }
                g_pShdMng = 0;
            }
        }
        }
    }
    efbDone = 0;
    matSet = 0;
#if RE4DC_PS2_WORLD_SOURCE_OWNER && RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(!flag){
        const int owned=sourceWorldDraw(m);
        if(owned<0)return; // caller restores render state without reading a retired model
        if(owned>0)info=nullptr; // successful source postludes still execute
    }
#elif RE4DC_PS2_WORLD_SOURCE_OWNER
    if(!flag && sourceWorldDraw(m)!=0)info=nullptr; // source postludes still execute
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    if(!flag) {
        const int owned=sourceWorldR11fDraw(m);
        if(owned<0)return; // ModelRender restores alpha/shader state without reading m.
        if(owned>0)info=nullptr; // Successful ownership retains source postludes.
    }
#endif
#if RE4DC_ACTOR_TRANSACTION
    if(!flag) {
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
        // Capture before a yielding texture acquisition can retire the owner.
        // A direct image has no prepared source arrays to fall back to.
        const bool direct_image=re4dc_actor_presentation32_required(m)!=0;
#endif
        const int owned=re4dc_actor_transaction_draw(m);
#if defined(RE4DC_MCHECK_LEONGC) && RE4DC_MCHECK_LEONGC
        // mcheck.mk MCHECK_LEONGC (test builds): the player's model left to the source (GameCube) path.
        if(owned==0 && m==(cModel*)pPL)re4dc_leon_gc_note(m);
#endif
#if defined(RE4DC_ACTOR_PRESENTATION32) && RE4DC_ACTOR_PRESENTATION32
        if(direct_image && owned==0)return;
#endif
        if(owned<0)return; // caller still restores alpha state and shaderReset
        if(owned>0)info=nullptr; // original postlude still executes below
    }
#endif
    while (info != 0) {
        ModelData* d;
        void* tex;
        f32 (*mat0)[4];
        u16 nParts;
        ModelPart* part;
        u32 i;

        if (!(pG->Status_flg[1] & 0x100) && m->ot_type == 7) {
            if (m->be_flag & 0x08000000) {
                if (!(info->be_flag & 0x40)) {
                    info = info->pList;
                    continue;
                }
            } else {
                if (info->be_flag & 0x40) {
                    info = info->pList;
                    continue;
                }
            }
        }
        if (info->be_flag & 0x20) {
            GXSetChanMatColor(4, *(GXColor*) info->color);
            matSet = 1;
        } else if (matSet == 1) {
            GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
        }
        if (PTR_INVALID(info)) {
            pLog->err(0, 0, "commonModelTrans() pModelInfo INVALID PTR %08X", info);
            break;
        }
        if (!(info->be_flag & 8)) {
            info = info->pList;
            continue;
        }
        if (efbDone == 0 && (m->Shader_type == 1 || m->Shader_type == 2) && !(info->be_flag & 4)) {
            efbDone = 1;
            GetEfbTex(m);
        }
        d = info->pData;
        if (PTR_INVALID(d)) {
            pLog->err(0, 0, "commonModelTrans() pHead PTR ERR %08x", d);
            return;
        }
        if (d->nTex > 0xF7) {
            pLog->err(0, 0, "commonModelTrans() TEXOBJ OVERFLOW %d", d->nTex);
            return;
        }
        Mtx inv;
        Mtx nrm;
        Mtx pm;
        if (m->be_flag & 0x4000) {
            RE4DC_RENDER_MTXConcat(m->mat, (f32(*)[4]) &info->x5C, pm);
        } else if (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1) {
            RE4DC_RENDER_MTXConcat(m->getPartsPtr(d->pHead->partsNo)->mat, (f32(*)[4]) &info->x5C, pm);
        } else {
            RE4DC_RENDER_MTXConcat(m->pParts->mat, (f32(*)[4]) &info->x5C, pm);
        }
        mat0 = m->mat;
        RE4DC_RENDER_MTXConcat(viewMat, pm, mv);
#if RE4DC_FRONT_LEAN && defined(__sh__)
        // The normal matrix only lights; a lit native mesh never reads it. 'inv' is rebuilt by
        // PSMTXScale below before its other use.
        if (!g_leanRender) {
            RE4DC_RENDER_MTXInverse(mv, inv);
            PSMTXTranspose(inv, nrm);
        }
        GXLoadPosMtxImm(mv, 0);
        if (!g_leanRender) {
            GXLoadNrmMtxImm(nrm, 0);
        }
#else
        RE4DC_RENDER_MTXInverse(mv, inv);
        PSMTXTranspose(inv, nrm);
        GXLoadPosMtxImm(mv, 0);
        GXLoadNrmMtxImm(nrm, 0);
#endif
        GXSetCurrentMtx(0);
        tex = d->pTex;
        GXClearVtxDesc();
        GXSetVtxDesc(9, 3);
        GXSetVtxDesc(10, 3);
        GXSetVtxDesc(13, 3);
        if (d->flags & 0x20000000) {
            GXSetVtxAttrFmt(0, 10, 0, 1, 0);
        } else {
            GXSetVtxAttrFmt(0, 10, 0, 3, 14);
        }
        if ((s32) d->flags < 0) {
            void* clr = d->pClr;
            GXSetVtxAttrFmt(0, 13, 1, 3, 8);
            GXSetVtxDesc(11, 3);
            GXSetVtxAttrFmt(0, 11, 1, 5, 0);
            GXSetArray(11, clr, 4);
        } else {
            GXSetVtxAttrFmt(0, 13, 1, 2, 15);
        }
        GXSetArray(13, tex, 4);
        GXSetVtxAttrFmt(0, 9, 1, 3, d->shift);
        if ((m->be_flag & 0x4000) || (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1)) {
            GXSetArray(9, d->vtxOrig, 8);
            if (d->flags & 0x20000000) {
                GXSetArray(10, d->nrmOrig, 4);
            } else {
                GXSetArray(10, d->nrmOrig, 8);
            }
        } else {
            GXSetArray(9, info->pPosBuf[pG->vtx_buf_no], 6);
            if (d->flags & 0x20000000) {
                GXSetArray(10, info->pNrmBuf[pG->vtx_buf_no], 3);
            } else {
                GXSetArray(10, info->pNrmBuf[pG->vtx_buf_no], 6);
            }
        }
        switch (m->CullMode) {
        case 0:
            GXSetCullMode(1);
            break;
        case 1:
            GXSetCullMode(2);
            break;
        case 2:
            GXSetCullMode(0);
            break;
        }
        if (pG->Debug_flg[0] & 0x20000000) {
            GXSetCullMode(1);
        }
        if (g_prev_tpl_addr != info->tpl_addr || g_prev_add_tpl_addr != info->pAddTpl) {
            u32 n;
            for (i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++) {
                TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
                TEXDescriptor* td;
                u8 mip;
                int filt;
                u8 edge;
                if (tpl->numDescriptors == 0) {
                    td = TEXGet(info->pAddTpl, i);
                } else if (i < tpl->numDescriptors) {
                    td = TEXGet(tpl, i);
                } else {
                    td = TEXGet(info->pAddTpl, i - tpl->numDescriptors);
                }
                if ((s32) d->flags < 0) {
                    TEXHeader* wh = td->textureHeader;
#if RE4DC_FRONT_TPL_OWNER
                    if (wh->wrapT != 1 || wh->wrapS != 1) re4dc_front_tpl_header_changed(wh);
#endif
                    wh->wrapT = 1;
                    wh->wrapS = 1;
                }
                if (td->textureHeader->minLOD == td->textureHeader->maxLOD) {
                    mip = 0;
                    filt = 1;
                } else {
                    mip = 1;
                    filt = 5;
                }
                if (aniso != 0) {
                    edge = 1;
                } else {
                    edge = td->textureHeader->edgeLODEnable;
                }
                GXInitTexObj(&gx->texObj[i], td->textureHeader->data, td->textureHeader->width, td->textureHeader->height,
                             td->textureHeader->format, td->textureHeader->wrapS, td->textureHeader->wrapT, mip);
                if (mip == 1) {
                    GXInitTexObjLOD(&gx->texObj[i], filt, 1, (f32) min_lod, (f32) max_lod, lod_bias, 0, edge, aniso);
                }
            }
            if (MODEL_EXT(m)->pTexChg != 0) {
                MODEL_EXT(m)->pTexChg->move(gx->texObj);
            }
        }
        PSet(g_prev_tpl_addr, info->tpl_addr);
        PSet(g_prev_add_tpl_addr, info->pAddTpl);
        nParts = d->displist_num;
        part = d->pParts;
        if (m->scale.x == 1.0f && m->scale.y == 1.0f && m->scale.z == 1.0f) {
            updateMatrices(mat0, specular_mat, m);
        } else {
            PSMTXScale(inv, 1.0f / m->scale.x, 1.0f / m->scale.y, 1.0f / m->scale.z);
            PSMTXConcat(inv, mat0, inv);
            updateMatrices(inv, specular_mat, m);
        }
        for (i = 0; i < nParts; i++) {
            u8* p;
#if defined(RE4DC_GAME) && !defined(__PPC__)
            re4dc_model_material(0, 0, 0, 0);
#endif
            shaderSetup(m, info, part, mv);
            GXSetBlendMode(bl[info->blend_mode][0], bl[info->blend_mode][1], bl[info->blend_mode][2], bl[info->blend_mode][3]);
            if (flag & 1) {
                GXSetAlphaCompare(7, 0, 1, 7, 0);
            }
            if (!(flag & 1)) {
                f32 a = m->invisible_factor * m->invisible_factor2 * info->invisible_factor;
                if (a < 1.0f) {
                    GXColor c = *(GXColor*) info->color;
                    c.a = (u8) ((f32) (int) c.a * a);
                    GXSetChanMatColor(4, c);
                }
            }
            p = (u8*) part + 0x20;
            if ((u32) p & 0x1F) {
#line 2044 "D:/Bio4/Prog/trans.cpp"
                HALT();
            }
#if defined(RE4DC_GAME) && !defined(__PPC__)
            re4dc_draw_model_part(m, info, part, mv, flag);
#endif
            GXCallDisplayList(p, part->size);
            part = (ModelPart*) (p + part->size);
            if (IND_STAGE_ID() != 0) {
                GXSetNumIndStages(0);
                GXSetTevDirect(0);
                GXSetTevDirect(1);
                GXSetTevDirect(2);
                GXSetTevDirect(3);
                GXSetTevDirect(4);
                GXSetTevDirect(5);
                GXSetTevDirect(6);
                GXSetTevDirect(7);
                GXSetTevDirect(8);
            }
        }
        info = info->pList;
    }
    if (!(pG->Status_flg[1] & 0x100)) {
        if (MODEL_EXT(m)->pFootShadowTbl != 0 && (m->be_flag & 0x10)) {
            DrawFootShadow((cEm*) m);
        }
    }
    if (!(pG->Status_flg[1] & 0x100)) {
        if (m->ot_type == 7) {
            m->be_flag |= 0x08000000;
        }
    }
}

#if RE4DC_FRONT_NATIVE && defined(__sh__)
// FRONT_NATIVE: a model the native path draws exactly as the source would. Everything else
// (thermal scope, refraction / EFB, self shadow, cast-shadow candidates, flat colour mode, unlit
// light info, an invalid light type, bridge off) keeps the source path.
static int frontNativeWhy(cModel* m)
{
    if (!re4dc_model_diagnostic_enabled()) {
        return 1;
    }
    if (m->be_flag & 0x00020000) {
        return 2;  // flat colour mode
    }
    if (m->LightInfo.Flag & 4) {
        return 3;  // unlit (LightDisable)
    }
    if (pG->Status_flg[1] & 0x04000000) {
        return 4;  // thermal scope
    }
    if (m->Shader_type == 1 || m->Shader_type == 2) {
        return 5;  // refraction / EFB
    }
    if ((pG->Status_flg[2] & 0x00100000) && (m->be_flag & 0x02000000) && !(pG->Disp_flg & 0x00040000) &&
        (pG->Status_flg[1] & 0x200) && !(pG->Status_flg[1] & 0x100)) {
        return 6;  // cast-shadow candidate
    }
    if ((pGS->Status_flg[0] & 1) && isSelfUse) {
        for (u32 i = 0; i < (u32) g_SelfShdNum; i++) {
            if (GetSelfShadowMng(i)->pModel[0] == m) {
                return 7;  // self shadow
            }
        }
    }
    if (!(m->be_flag & 0x8000)) {
        cLight** list = m->LightInfo.pLight;
        for (int i = 0; i < 8; i++) {
            if (list[i] != NULL && list[i]->xD > 7) {
                return 8;  // invalid light type (the source clears the light)
            }
        }
    }
    return 0;
}

// Per model: native or the source path's reason (frontNativeWhy); counts logged every 600 frames.
static int frontNativeOk(cModel* m)
{
    static u32 count[9];
    static u32 block = ~0U;
    int why = frontNativeWhy(m);
    count[why]++;
    if (pG->Frame_cnt / 600 != block) {
        block = pG->Frame_cnt / 600;
        re4dc_log("front_native: frame=%u native=%u source=%u,%u,%u,%u,%u,%u,%u,%u\n", pG->Frame_cnt, count[0], count[1],
                  count[2], count[3], count[4], count[5], count[6], count[7], count[8]);
    }
    return why == 0;
}

// commonModelTrans(m, info, viewMat, 0) for a frontNativeOk model, keeping only what reaches the
// bridge: per info the material colour, the position / normal matrices, the texture objects (same
// TPL cache, wrap fix-up and cTexChg swaps); per part the material texture (animated frame, UV
// scroll), the alpha mask (part flags 4), the model's colour-stage scale and the faded material
// alpha. `dry` (FRONT_NATIVE=2 replay): no foot shadow or draw mark.
#if RE4DC_FRONT_TEXOBJ
// D367 records30 FRONT_TEXOBJ (R1): the texture objects of a TPL set, built once. The source
// re-initialises gx->texObj[0..n) (GXInitTexObj per descriptor, after the wrap fix-up) whenever
// a model's TPL differs from the previous model's, then applies that model's cTexChg swaps.
// Here that state is kept symbolic: the cached object words of (TPL, added TPL, count, wrap fix-up)
// plus the swap result as an index remap, and the parts read their object from it. gx->texObj is
// written (the same bytes) only when something else reads it: the source path, org_LoadTexObj,
// the FRONT_NATIVE=2 snapshot, or before a new set with fewer objects (whose tail keeps the old
// objects, as in the source). Swaps with an index outside the set, and sets that do not fit the
// cache, take the source loop. Render only.
#if RE4DC_FRONT_TPL_OWNER
static void frontTexFlush();
#endif
namespace {
#if RE4DC_FRONT_TPL_OWNER
// Only SMD palettes whose TPL/descriptor/header spans and image-data pointers
// lie in the current native room archive are certified. The info table is a bounded,
// direct-mapped sidecar: a collision loses an optimization, never authority.
struct FtOwnerInfo {
    const cModelInfo* info;
    const TEXPalette* base;
    const TEXPalette* add;
    const TEXDescriptor* base_desc;
    const TEXDescriptor* add_desc;
    u32 base_version, add_version, life;
    u8 base_count, add_count, zero_base, qualified;
};
constexpr u32 kFtOwners = 64;
FtOwnerInfo ft_owner_infos[kFtOwners];
const u8* ft_owner_room;
u32 ft_owner_bytes, ft_owner_life = 1, ft_owner_change = 1;
const cSmd* ft_owner_smd;
const cSmd* ft_owner_common;
bool ft_owner_exhausted;

bool ftOwnerSpan(const void* p, u32 bytes)
{
    if (!ft_owner_room || !p || !bytes) return false;
    const __UINTPTR_TYPE__ base = (__UINTPTR_TYPE__) ft_owner_room;
    const __UINTPTR_TYPE__ addr = (__UINTPTR_TYPE__) p;
    if (addr < base) return false;
    const __UINTPTR_TYPE__ delta = addr - base;
    return delta <= ft_owner_bytes && bytes <= ft_owner_bytes - delta;
}
bool ftOwnerAligned(const void* p, u32 alignment)
{
    return (((__UINTPTR_TYPE__) p) & (alignment - 1)) == 0;
}
const u8* ftOwnerOffset(const void* origin, u32 offset, u32 bytes)
{
    if (!ftOwnerSpan(origin, 1)) return 0;
    const __UINTPTR_TYPE__ pos = (__UINTPTR_TYPE__) origin - (__UINTPTR_TYPE__) ft_owner_room;
    if (offset > ft_owner_bytes - pos || bytes > ft_owner_bytes - pos - offset) return 0;
    return ft_owner_room + pos + offset;
}
void ftOwnerNext(u32& serial)
{
    if (serial == ~0U) {
        ft_owner_exhausted = true;  // never reuse an old key or owner token
    } else {
        ++serial;
    }
}
void ftOwnerMutation()
{
    ftOwnerNext(ft_owner_change);
}
void ftOwnerClear()
{
    frontTexFlush();  // a retired set can still own the symbolic GX tail
    ftOwnerNext(ft_owner_life);
    ftOwnerMutation();
    ft_owner_smd = ft_owner_common = 0;
}
bool ftOwnerPalette(const TEXPalette* p, u32& count, const TEXDescriptor*& desc)
{
    if (!ftOwnerAligned(p, alignof(TEXPalette)) || !ftOwnerSpan(p, sizeof(*p)) ||
        p->version != 0x0020AF30) return false;
    count = p->numDescriptors;
    desc = p->descriptorArray;
    if (count > 0xF8 || (count && (!ftOwnerAligned(desc, alignof(TEXDescriptor)) ||
                                  !ftOwnerSpan(desc, count * sizeof(*desc))))) return false;
    for (u32 i = 0; i < count; ++i) {
        const TEXHeader* h = desc[i].textureHeader;
        if (!ftOwnerAligned(h, alignof(TEXHeader)) || !ftOwnerSpan(h, sizeof(*h)) ||
            !ftOwnerSpan(h->data, 1)) return false;
    }
    return true;
}
u32 ftOwnerSlot(const void* info)
{
    return (u32) (((__UINTPTR_TYPE__) info >> 4) & (kFtOwners - 1));
}
u32 ftOwnerStamp(const cModelInfo* info, u32 n)
{
    if (ft_owner_exhausted || !ft_owner_common) return 0;
    const FtOwnerInfo& o = ft_owner_infos[ftOwnerSlot(info)];
    if (o.info != info || o.life != ft_owner_life || !o.qualified || o.base != info->tpl_addr ||
        o.add != info->pAddTpl || o.add_count != info->nAddTex ||
        o.base_count + o.add_count != n) return 0;
    // These bounded top-level reads catch count shrink and descriptor-array
    // remaps before a hit; there is no descendant walk on the qualified path.
    if (!o.zero_base) {
        if (!ftOwnerSpan(o.base, sizeof(*o.base)) || o.base->version != o.base_version ||
            o.base->numDescriptors != o.base_count || o.base->descriptorArray != o.base_desc) return 0;
    } else if (o.base->numDescriptors != 0 || o.base->version != 0x0020AF30) {
        return 0;
    }
    if (!ftOwnerSpan(o.add, sizeof(*o.add)) || o.add->version != o.add_version ||
        o.add->numDescriptors != o.add_count || o.add->descriptorArray != o.add_desc) return 0;
    return ft_owner_change;
}
u32 ftOwnerRestamp(const cModelInfo* info, u32 n)
{
    const u32 stamp=ftOwnerStamp(info,n);
    if (!stamp) return 0;
    const FtOwnerInfo& o=ft_owner_infos[ftOwnerSlot(info)];
    u32 count=0;
    const TEXDescriptor* desc=0;
    if (!o.zero_base && (!ftOwnerPalette(o.base,count,desc) ||
                         count!=o.base_count || desc!=o.base_desc)) return 0;
    if (!ftOwnerPalette(o.add,count,desc) || count!=o.add_count || desc!=o.add_desc) return 0;
    return stamp;
}
u32 ftOwnerCount(const cModelInfo* info, u32& stamp)
{
    stamp = 0;
    if (ft_owner_exhausted) return 0;
    const FtOwnerInfo& o = ft_owner_infos[ftOwnerSlot(info)];
    if (o.info != info || o.life != ft_owner_life) return 0;
    const u32 n = o.base_count + o.add_count;
    stamp = ftOwnerStamp(info, n);
    return stamp ? n : 0;
}
void ftOwnerForeign(const cModelInfo* info)
{
    const FtOwnerInfo& known = ft_owner_infos[ftOwnerSlot(info)];
    if (known.info == info && known.life == ft_owner_life) return;
    if (!ftOwnerSpan(info->tpl_addr, 1) && !ftOwnerSpan(info->pAddTpl, 1)) return;
    // A foreign info can expose a registered TPL through a base or added
    // alias. Refuse the entire published generation rather than trusting that
    // caller to keep the SMD descriptor mutation contract.
    for (u32 i = 0; i < kFtOwners; ++i) {
        const FtOwnerInfo& o = ft_owner_infos[i];
        if (o.life == ft_owner_life && o.qualified &&
            (o.base == info->tpl_addr || o.add == info->tpl_addr ||
             o.base == info->pAddTpl || o.add == info->pAddTpl)) {
            ftOwnerNext(ft_owner_life);
            ftOwnerMutation();
            return;
        }
    }
}
#endif
struct FtRec { u32 w[4]; };  // GXInitTexObj stub words 0..3 (4..7 are zero)
#if RE4DC_FRONT_TPL_OWNER
struct FtKey { void* tpl; void* add; void* data0; u16 first; u8 count; u8 wrap;
    u32 owner_stamp;
};
#else
struct FtKey { void* tpl; void* add; void* data0; u16 first; u8 count; u8 wrap; };
#endif
constexpr u32 kFtKeys = 32, kFtRecs = 512;  // r100 fight peak: 21 keys, 394 records
FtKey ft_keys[kFtKeys];
FtRec ft_recs[kFtRecs];
u32 ft_nkeys, ft_nrecs, ft_room = ~0U;
const FtKey* ft_cur;  // the set gx->texObj holds symbolically (0: gx->texObj is current)
u8 ft_remap[0xF8];
int ft_swapped;
u32 ft_hits, ft_builds, ft_fallbacks, ft_flushes, ft_resets, ft_block = ~0U;
TEXDescriptor* ftDesc(cModelInfo* info, u32 i)
{
    TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
    if (tpl->numDescriptors == 0) {
        return TEXGet(info->pAddTpl, i);
    } else if (i < tpl->numDescriptors) {
        return TEXGet(tpl, i);
    }
    return TEXGet(info->pAddTpl, i - tpl->numDescriptors);
}
void ftObj(GXTexObj* o, const FtRec& r)
{
    u32* w = (u32*) o;
    for (u32 k = 0; k < sizeof(GXTexObj) / 4; k++) {
        w[k] = k < 4 ? r.w[k] : 0;
    }
}
FtRec ftRecord(TEXHeader* h, u8 wrap)
{
    // Preserve the source's header writes even when the packed object matches.
    // Another model can share this header through its added TPL.
    if (wrap) {
#if RE4DC_FRONT_TPL_OWNER
        if (h->wrapT != 1 || h->wrapS != 1) re4dc_front_tpl_header_changed(h);
#endif
        h->wrapT = 1;
        h->wrapS = 1;
    }
    FtRec r;
    r.w[0] = (u32) h->data;
    r.w[1] = ((u32) (u16) h->width << 16) | (u16) h->height;
    r.w[2] = (u32) h->format;
    r.w[3] = ((u32) h->wrapS << 8) | (u32) h->wrapT | ((u32) (u8) (h->minLOD == h->maxLOD ? 0 : 1) << 16);
    return r;
}
#if RE4DC_FRONT_TPL_OWNER
const FtKey* ftLookup(cModelInfo* info, ModelData* d, u32 n, u32 owner_stamp)
#else
const FtKey* ftLookup(cModelInfo* info, ModelData* d, u32 n)
#endif
{
    const u32 room = ((u32) pG->stage_no << 8) | pG->room_no;
    const u8 wrap = (s32) d->flags < 0;
    if (n == 0 || n > 0xF8) {
        return 0;
    }
#if RE4DC_FRONT_TPL_OWNER
    if (!owner_stamp) ftOwnerForeign(info);
    void* data0 = 0;
    bool have_data0 = false;
#else
    void* data0 = ftDesc(info, 0)->textureHeader->data;
#endif
    if (room != ft_room) {
        frontTexFlush();
        ft_room = room;
        ft_nkeys = ft_nrecs = 0;
    }
    for (u32 k = 0; k < ft_nkeys; k++) {
#if RE4DC_FRONT_TPL_OWNER
        FtKey& key = ft_keys[k];
#else
        const FtKey& key = ft_keys[k];
#endif
#if RE4DC_FRONT_TPL_OWNER
        if (key.tpl == info->tpl_addr && key.add == info->pAddTpl && key.count == n && key.wrap == wrap) {
#else
        if (key.tpl == info->tpl_addr && key.add == info->pAddTpl && key.count == n && key.wrap == wrap && key.data0 == data0) {
#endif
#if RE4DC_FRONT_TPL_OWNER
            if (owner_stamp && key.owner_stamp == owner_stamp) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::FrontHit, 1);
#endif
                ++ft_hits;
                return &key;
            }
            if (!have_data0) {
                data0 = ftDesc(info, 0)->textureHeader->data;
                have_data0 = true;
            }
            if (key.data0 != data0) continue;
#endif
            // Pointer identity does not certify the remaining descriptors or
            // their current packed fields after same-room reuse/relocation.
            bool same = true;
            for (u32 i = 0; i < n; i++) {
                const FtRec now = ftRecord(ftDesc(info, i)->textureHeader, wrap);
                const FtRec& old = ft_recs[key.first + i];
                if (now.w[0] != old.w[0] || now.w[1] != old.w[1] || now.w[2] != old.w[2] || now.w[3] != old.w[3]) {
                    same = false;
                    break;
                }
            }
            if (!same) {
                // The preceding symbolic set may use these records. Materialize
                // it before refreshing in place so its tail/remap stay intact.
                frontTexFlush();
                for (u32 i = 0; i < n; i++) {
                    ft_recs[key.first + i] = ftRecord(ftDesc(info, i)->textureHeader, wrap);
                }
#if RE4DC_FRONT_TPL_OWNER
                key.owner_stamp = ftOwnerRestamp(info, n);
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::FrontBuild, 1);
#endif
#line 2228
                ++ft_builds;
                return &key;
            }
#if RE4DC_FRONT_TPL_OWNER
            key.owner_stamp = ftOwnerRestamp(info, n);
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::FrontHit, 1);
#endif
#line 2231
            ++ft_hits;
            return &key;
        }
    }
#if RE4DC_FRONT_TPL_OWNER
    if (!have_data0) data0 = ftDesc(info, 0)->textureHeader->data;
#endif
    if (ft_nkeys == kFtKeys || ft_nrecs + n > kFtRecs) {
        frontTexFlush();
        ft_nkeys = ft_nrecs = 0;
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::FrontReset, 1);
#endif
#line 2238
        ++ft_resets;
    }
    FtKey& key = ft_keys[ft_nkeys++];
    key.tpl = info->tpl_addr;
    key.add = info->pAddTpl;
    key.data0 = data0;
    key.first = (u16) ft_nrecs;
    key.count = (u8) n;
    key.wrap = wrap;
    for (u32 i = 0; i < n; i++) {
        ft_recs[ft_nrecs++] = ftRecord(ftDesc(info, i)->textureHeader, wrap);
    }
#if RE4DC_FRONT_TPL_OWNER
    key.owner_stamp = ftOwnerRestamp(info, n);
#endif
    if (wrap) {
        // The fix-up rewrote the headers: sets of this TPL cached without it are stale.
        for (u32 k = 0; k + 1 < ft_nkeys; k++) {
            if (ft_keys[k].tpl == key.tpl && !ft_keys[k].wrap) {
                ft_keys[k].tpl = 0;
            }
        }
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::FrontBuild, 1);
#endif
#line 2258
    ++ft_builds;
    return &key;
}
// The source's `if (TPL changed) { init texObj; pTexChg->move }` for model m, info: 1 when it was
// taken symbolically, 0 when the caller must run the source loop (gx->texObj is then current).
int frontTexInit(cModel* m, cModelInfo* info, ModelData* d)
{
#if RE4DC_FRONT_TPL_OWNER
    u32 owner_stamp;
    const u32 owned_n = ftOwnerCount(info, owner_stamp);
    const u32 n = owned_n ? owned_n : ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex;
    const FtKey* key = ftLookup(info, d, n, owner_stamp);
#else
    const u32 n = ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex;
    const FtKey* key = ftLookup(info, d, n);
#endif
    cTexChg* chg = MODEL_EXT(m)->pTexChg;
    if (key && chg) {
        u8 remap[0xF8];
        for (u32 i = 0; i < n; i++) {
            remap[i] = (u8) i;
        }
        const u8* p = chg->tbl;
        for (int i = 0; i < chg->num; i++, p += 2) {
            if (p[0] >= n || p[1] >= n) {
                key = 0;
                break;
            }
            remap[p[0]] = remap[p[1]];
        }
        if (key) {
            memcpy(ft_remap, remap, n);
        }
    }
    if (!key) {
        frontTexFlush();
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::FrontRefuse, 1);
#endif
#line 2287
        ++ft_fallbacks;
        return 0;
    }
    if (ft_cur && ft_cur->count > n) {
        frontTexFlush();  // the tail beyond n keeps the previous set's objects
    }
    ft_cur = key;
    ft_swapped = chg != 0;
    if (pG->Frame_cnt / 600 != ft_block) {
        ft_block = pG->Frame_cnt / 600;
        re4dc_log("front_texobj: frame=%u hits=%u builds=%u fallbacks=%u flushes=%u resets=%u keys=%u recs=%u\n", pG->Frame_cnt,
                  ft_hits, ft_builds, ft_fallbacks, ft_flushes, ft_resets, ft_nkeys, ft_nrecs);
    }
    return 1;
}
// The object a part reads for texture `id` (gx->texObj[id] in the source).
inline const void* frontTexObj(GxWork* gx, u32 id)
{
    if (id > 0xF7) {
        return 0;
    }
    if (ft_cur && id < ft_cur->count) {
        return &ft_recs[ft_cur->first + (ft_swapped ? ft_remap[id] : id)];
    }
    return &gx->texObj[id];
}
}
#if RE4DC_FRONT_TPL_OWNER
extern "C" void re4dc_front_tpl_bind_room(const void* room, unsigned bytes)
{
    ftOwnerClear();
    ft_owner_room = 0;
    ft_owner_bytes = 0;
    if (!room || !bytes || (__UINTPTR_TYPE__) room + bytes < (__UINTPTR_TYPE__) room) return;
    ft_owner_room = (const u8*) room;
    ft_owner_bytes = bytes;
}
extern "C" void re4dc_front_tpl_retire_room()
{
    ftOwnerClear();
    ft_owner_room = 0;
    ft_owner_bytes = 0;
}
extern "C" void re4dc_front_tpl_smd_begin(const void* smd, const void* common)
{
    ftOwnerClear();
    if (ftOwnerAligned(smd, alignof(cSmd)) && ftOwnerAligned(common, alignof(cSmd)) &&
        ftOwnerSpan(smd, 16) && ftOwnerSpan(common, 16)) {
        ft_owner_smd = (const cSmd*) smd;
        ft_owner_common = (const cSmd*) common;
    }
}
extern "C" void re4dc_front_tpl_smd_clear()
{
    frontTexFlush();
    ftOwnerNext(ft_owner_life);
    ftOwnerMutation();
}
extern "C" void re4dc_front_tpl_smd_publish(const void* info_ptr, const void* zero_tpl,
                                                const void* smd, const void* common)
{
    if (!info_ptr) return;
    FtOwnerInfo& o = ft_owner_infos[ftOwnerSlot(info_ptr)];
    if (o.info == info_ptr) o.info = 0;
    if (ft_owner_exhausted || !ft_owner_common ||
        common != ft_owner_common || !ftOwnerSpan(common, 16)) return;
    o.info = (const cModelInfo*) info_ptr;
    o.life = ft_owner_life;
    o.qualified = 0;
    const cModelInfo* info = (const cModelInfo*) info_ptr;
    const cSmd* cs = (const cSmd*) common;
    const u8* table = ftOwnerOffset(cs, cs->TplTblOfs, sizeof(u32));
    if (!table || !ftOwnerAligned(table, alignof(u32))) return;
    const u32 add_ofs = *(const u32*) table;
    const TEXPalette* add = (const TEXPalette*) ftOwnerOffset(table, add_ofs, sizeof(TEXPalette));
    if (!add) return;
    if (info->pAddTpl != add) return;
    u32 add_count = 0, base_count = 0;
    const TEXDescriptor *add_desc = 0, *base_desc = 0;
    if (!ftOwnerPalette(add, add_count, add_desc) || !add_count ||
        info->nAddTex != add_count) return;
    const TEXPalette* base = (const TEXPalette*) info->tpl_addr;
    const bool zero = base == zero_tpl;
    if (zero) {
        if (!base || !ftOwnerAligned(base, alignof(TEXPalette)) ||
            base->version != 0x0020AF30 || base->numDescriptors != 0) return;
        base_desc = base->descriptorArray;
    } else if (smd != ft_owner_smd || !ftOwnerPalette(base, base_count, base_desc)) {
        return;
    }
    if (base_count + add_count > 0xF8) return;
    o.info = info;
    o.base = base;
    o.add = add;
    o.base_desc = base_desc;
    o.add_desc = add_desc;
    o.base_count = base_count;
    o.add_count = add_count;
    o.base_version = base->version;
    o.add_version = add->version;
    o.zero_base = zero;
    o.qualified = 1;
    o.life = ft_owner_life;
}
extern "C" void re4dc_front_tpl_smd_slide(const void* smd)
{
    if (smd == ft_owner_smd || smd == ft_owner_common) {
        frontTexFlush();
        ftOwnerNext(ft_owner_life);
        ftOwnerMutation();
    }
}
extern "C" void re4dc_front_tpl_info_changed(const void* info)
{
    FtOwnerInfo& o = ft_owner_infos[ftOwnerSlot(info)];
    if (o.info == info) o.info = 0;
}
extern "C" void re4dc_front_tpl_palette_changed(const void*)
{
    // A different palette can share a nonfirst certified TEXHeader or even a
    // descriptor array. Its address does not identify every descendant that
    // calcTplAddr/Offset or slideTplAddr will write. These are cold structural
    // writers: revoke the whole certified generation before their first
    // descendant store, regardless of the palette's own archive membership.
    // Materialize a symbolic set first so a later record refresh cannot alter
    // the already-selected GX tail/remap.
    frontTexFlush();
    ftOwnerNext(ft_owner_life);
    ftOwnerMutation();
}
extern "C" void re4dc_front_tpl_header_changed(const void* header)
{
    if (!ftOwnerSpan(header, sizeof(TEXHeader))) return;
    // This notifier is used only by the source's wrapS/T writes. If a header
    // was remapped outside the certified image span, do not renew authority.
    if (!ftOwnerSpan(((const TEXHeader*) header)->data, 1)) ftOwnerNext(ft_owner_life);
    ftOwnerMutation();
}
#endif
static void frontTexFlush()
{
    if (!ft_cur) {
        return;
    }
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::FrontFlush, ft_cur->count);
#endif
#line 2319
    GxWork* gx = GXWORK();
    const FtRec* r = ft_recs + ft_cur->first;
    for (u32 i = 0; i < ft_cur->count; i++) {
        ftObj(&gx->texObj[i], r[ft_swapped ? ft_remap[i] : i]);
    }
    ft_cur = 0;
    ++ft_flushes;
}
#endif
// Keep the original source diagnostic locations after the optional cache body.
#line 2302 "D:/Bio4/Prog/trans.cpp"
static void frontNativeModelTrans(cModel* m, Mtx viewMat, int dry)
{
    GxWork* gx = GXWORK();
    cModelInfo* info = m->pModelInfo;
    int matSet = 0;
    int scale;
    const f32 fade = m->invisible_factor * m->invisible_factor2;

    PSet(g_pShdMng, 0);
    // shaderSetup's last colour stage (the value the bridge reads after every part's setup).
    switch (m->TevScaleGroup) {
    case 0:
    case 1:
        switch (gxCsScale[m->TevScaleGroup]) {
        case 0:
            scale = 0;
            break;
        case 1:
            scale = 1;
            break;
        case 2:
            scale = 2;
            break;
        default:
            scale = 0;
            pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", gxCsScale[m->TevScaleGroup]);
            break;
        }
        break;
    case 4:
        scale = 0;
        break;
    case 5:
        scale = 1;
        break;
    case 6:
        scale = 2;
        break;
    default:
        scale = 0;
        pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", m->TevScaleGroup);
        break;
    }
    while (info != 0) {
        ModelData* d;
        u16 nParts;
        ModelPart* part;
        u32 i;

        if (!(pG->Status_flg[1] & 0x100) && m->ot_type == 7) {
            if ((m->be_flag & 0x08000000) ? !(info->be_flag & 0x40) : (info->be_flag & 0x40)) {
                info = info->pList;
                continue;
            }
        }
        if (info->be_flag & 0x20) {
            GXSetChanMatColor(4, *(GXColor*) info->color);
            matSet = 1;
        } else if (matSet == 1) {
            GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
        }
        if (PTR_INVALID(info)) {
            pLog->err(0, 0, "commonModelTrans() pModelInfo INVALID PTR %08X", info);
            break;
        }
        if (!(info->be_flag & 8)) {
            info = info->pList;
            continue;
        }
        d = info->pData;
        if (PTR_INVALID(d)) {
            pLog->err(0, 0, "commonModelTrans() pHead PTR ERR %08x", d);
            return;
        }
        if (d->nTex > 0xF7) {
            pLog->err(0, 0, "commonModelTrans() TEXOBJ OVERFLOW %d", d->nTex);
            return;
        }
        Mtx pm;
        Mtx mv;
        if (m->be_flag & 0x4000) {
            RE4DC_RENDER_MTXConcat(m->mat, (f32(*)[4]) &info->x5C, pm);
        } else if (d->weight_palette_num <= 1 && d->weight_ext_num <= 0xFF && !(info->be_flag & 2) && d->nParts == 1) {
            RE4DC_RENDER_MTXConcat(m->getPartsPtr(d->pHead->partsNo)->mat, (f32(*)[4]) &info->x5C, pm);
        } else {
            RE4DC_RENDER_MTXConcat(m->pParts->mat, (f32(*)[4]) &info->x5C, pm);
        }
        RE4DC_RENDER_MTXConcat(viewMat, pm, mv);
#if RE4DC_FRONT_LEAN
        if (!g_leanRender)
#endif
        {
            Mtx inv;
            Mtx nrm;
            RE4DC_RENDER_MTXInverse(mv, inv);
            PSMTXTranspose(inv, nrm);
            GXLoadNrmMtxImm(nrm, 0);
        }
        if (g_prev_tpl_addr != info->tpl_addr || g_prev_add_tpl_addr != info->pAddTpl) {
#if RE4DC_FRONT_TEXOBJ
            if (!frontTexInit(m, info, d))
#endif
            {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::FrontSource, 1);
#endif
#line 2405
                for (i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++) {
                    TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
                    TEXDescriptor* td;
                    if (tpl->numDescriptors == 0) {
                        td = TEXGet(info->pAddTpl, i);
                    } else if (i < tpl->numDescriptors) {
                        td = TEXGet(tpl, i);
                    } else {
                        td = TEXGet(info->pAddTpl, i - tpl->numDescriptors);
                    }
                    if ((s32) d->flags < 0) {
                        TEXHeader* wh = td->textureHeader;
#if RE4DC_FRONT_TPL_OWNER
                        if (wh->wrapT != 1 || wh->wrapS != 1) re4dc_front_tpl_header_changed(wh);
#endif
#line 2417
                        wh->wrapT = 1;
                        wh->wrapS = 1;
                    }
                    // GXInitTexObjLOD is a sink: only the base object is kept.
                    GXInitTexObj(&gx->texObj[i], td->textureHeader->data, td->textureHeader->width, td->textureHeader->height,
                                 td->textureHeader->format, td->textureHeader->wrapS, td->textureHeader->wrapT,
                                 td->textureHeader->minLOD == td->textureHeader->maxLOD ? 0 : 1);
                }
                if (MODEL_EXT(m)->pTexChg != 0) {
                    MODEL_EXT(m)->pTexChg->move(gx->texObj);
                }
            }
        }
        PSet(g_prev_tpl_addr, info->tpl_addr);
        PSet(g_prev_add_tpl_addr, info->pAddTpl);
        nParts = d->displist_num;
        part = d->pParts;
        ModelTexInfo* t = MODEL_TEX(info);
        const f32 a = fade * info->invisible_factor;
        for (i = 0; i < nParts; i++) {
            u8* p;
            u8 texId = part->texId;
            if ((t->flags & 2) && t->anim != 0) {
                texId = (t->anim + 4)[t->frame];
            }
#if RE4DC_FRONT_TEXOBJ
            re4dc_model_material((GXTexObj*) frontTexObj(gx, texId), t->u, t->v, t->flags);
#else
            re4dc_model_material(texId <= 0xF7 ? &gx->texObj[texId] : 0, t->u, t->v, t->flags);
#endif
            if (part->flags & 4) {
                u8 ref = m->alpha_omit;
                re4dc_model_alpha_material(
#if RE4DC_FRONT_TEXOBJ
                    (GXTexObj*) frontTexObj(gx, part->alphaTex),
#else
                    part->alphaTex <= 0xF7 ? &gx->texObj[part->alphaTex] : 0,
#endif
                                          ref == 0xFF ? part->alphaRef : ref, !(info->flagsDC & 8));
            }
            GXSetTevColorOp(0, 0, 0, scale, 1, 0);
            if (a < 1.0f) {
                GXColor c = *(GXColor*) info->color;
                c.a = (u8) ((f32) (int) c.a * a);
                GXSetChanMatColor(4, c);
            }
            p = (u8*) part + 0x20;
            if ((u32) p & 0x1F) {
                HALT();
            }
            re4dc_draw_model_part(m, info, part, mv, 0);
            part = (ModelPart*) (p + part->size);
        }
        info = info->pList;
    }
    if (dry) {
        return;
    }
    if (!(pG->Status_flg[1] & 0x100)) {
        if (MODEL_EXT(m)->pFootShadowTbl != 0 && (m->be_flag & 0x10)) {
            DrawFootShadow((cEm*) m);
        }
        if (m->ot_type == 7) {
            m->be_flag |= 0x08000000;
        }
    }
}

// ModelRender for a frontNativeOk model: projection, lights, the native model walk, then
// shaderReset's channel-0 state (its other GX calls are sinks).
#ifndef RE4DC_SCENERY_GATE
#define RE4DC_SCENERY_GATE 0
#endif
#if RE4DC_SCENERY_GATE && RE4DC_FRONT_LEAN
extern "C" int re4dc_static_gate(const void* object, const float mv[12], const float projection[7], float zfar);
extern "C" void GXGetProjectionv(f32*);
// D367 scenery30 S1a: a lit native-mesh scenery object (kind 2, ot_type 2-5, one drawn rigid info)
// whose whole mesh lies beyond the native cull depth draws nothing. Skip its lights and part walk;
// keep the state later models read: the TPL cache / texture objects (with its cTexChg swaps), the
// shadow manager reset, the info material colour and shaderReset's channel. Render only.
static int sceneryGate(cModel* m)
{
    cModelInfo* drawn = 0;
    if (m->ot_type < 2 || m->ot_type > 5 || m->invisible_factor * m->invisible_factor2 != 1.0f ||
        (MODEL_EXT(m)->pFootShadowTbl != 0 && (m->be_flag & 0x10)) || !(frontLean(m) & FRONT_LEAN_LIGHTS)) {
        return 0;
    }
    for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
        if (info->be_flag & 8) {
            if (drawn || info->invisible_factor != 1.0f) {
                return 0;
            }
            drawn = info;
        }
    }
    ModelData* d = drawn->pData;
    Mtx pm;
    Mtx mv;
    f32 projection[7];
    if (m->be_flag & 0x4000) {
        RE4DC_RENDER_MTXConcat(m->mat, (f32(*)[4]) &drawn->x5C, pm);
    } else {
        RE4DC_RENDER_MTXConcat(m->getPartsPtr(d->pHead->partsNo)->mat, (f32(*)[4]) &drawn->x5C, pm);
    }
    RE4DC_RENDER_MTXConcat(pG->Cam.v_mat, pm, mv);
    GXGetProjectionv(projection);
    if (!re4dc_static_gate(m, &mv[0][0], projection, View._zfar)) {
        return 0;
    }
    GxWork* gx = GXWORK();
    int matSet = 0;
    int parts = 0;
    PSet(g_pShdMng, 0);
    for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
        if (info->be_flag & 0x20) {
            GXSetChanMatColor(4, *(GXColor*) info->color);
            matSet = 1;
        } else if (matSet == 1) {
            GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
        }
        if (!(info->be_flag & 8)) {
            continue;
        }
        parts += info->pData->displist_num;
        ModelData* id = info->pData;
        if (g_prev_tpl_addr != info->tpl_addr || g_prev_add_tpl_addr != info->pAddTpl) {
#if RE4DC_FRONT_TEXOBJ
            if (!frontTexInit(m, info, id))
#endif
            {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::FrontSource, 1);
#endif
#line 2547
                for (u32 i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++) {
                    TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
                    TEXDescriptor* td;
                    if (tpl->numDescriptors == 0) {
                        td = TEXGet(info->pAddTpl, i);
                    } else if (i < tpl->numDescriptors) {
                        td = TEXGet(tpl, i);
                    } else {
                        td = TEXGet(info->pAddTpl, i - tpl->numDescriptors);
                    }
                    if ((s32) id->flags < 0) {
                        TEXHeader* wh = td->textureHeader;
#if RE4DC_FRONT_TPL_OWNER
                        if (wh->wrapT != 1 || wh->wrapS != 1) re4dc_front_tpl_header_changed(wh);
#endif
                        wh->wrapT = 1;
                        wh->wrapS = 1;
                    }
                    GXInitTexObj(&gx->texObj[i], td->textureHeader->data, td->textureHeader->width, td->textureHeader->height,
                                 td->textureHeader->format, td->textureHeader->wrapS, td->textureHeader->wrapT,
                                 td->textureHeader->minLOD == td->textureHeader->maxLOD ? 0 : 1);
                }
                if (MODEL_EXT(m)->pTexChg != 0) {
                    MODEL_EXT(m)->pTexChg->move(gx->texObj);
                }
            }
        }
        PSet(g_prev_tpl_addr, info->tpl_addr);
        PSet(g_prev_add_tpl_addr, info->pAddTpl);
    }
    if (parts) {
        // The walk's last per-part colour-stage scale (frontNativeModelTrans; errors ignored: the
        // error cases log and use 0 there too).
        int scale = 0;
        const int group = m->TevScaleGroup;
        if (group == 0 || group == 1) {
            scale = gxCsScale[group] == 1 ? 1 : gxCsScale[group] == 2 ? 2 : 0;
        } else if (group == 5) {
            scale = 1;
        } else if (group == 6) {
            scale = 2;
        }
        GXSetTevColorOp(0, 0, 0, scale, 1, 0);
    }
    GXSetChanCtrl(0, 0, 0, 0, 0, 0, 2);
    return 1;
}
#endif
#if defined(RE4DC_PROP_GATE) && RE4DC_PROP_GATE
// PROP_GATE (lane farmprop17 2026-10-17; render only, default 0): a lazily skinned room object (the r103 farm's cObj
// id 2 props: 10 models, 111 parts a frame) whose every drawn part lies beyond the native actor fog gate's cull depth
// draws nothing, yet each frame re4dc_actor_submit qualified every part, built its info's frame (the weight palette:
// calcWeightMat + MakeWeightPalette at the first render read, SKIN_PALETTE_LAZY) and ran the palette depth bound only
// to cull it (Flycast PROP_PROF: ~29 us a part in the native path + ~8 us in the bridge + the per-info walk here).
// This gate decides for the whole model before any of that, from data the frame build reads anyway:
//   - every palette entry is a convex blend (u8 percents, the last = 1 - the others, checked once per weight table) of
//     the parts matrices calcWeightMat builds (inverse root x parts mat x bind mat), so the entry's translation depth is
//     >= the least over all parts and its largest column norm <= the largest over all parts;
//   - every part's stream is a converted blob (only re4dc_actor_submit draws it) with the bind ball the actor gate uses
//     (|centre| + radius);
//   - the info is lazily skinned and registered (no arrays: only the skinned frame can draw it).
// So the actor gate's own depth for every part is >= this model bound; the model is skipped only when the bound is
// beyond the same cull depth (projection far, or the fogged View far) with a margin (0.1 % + 10 units) for rounding.
// The state the part walk leaves for later models is kept as sceneryGate keeps it (material colour, TPL cache /
// texture objects with cTexChg swaps, shadow manager, colour-stage scale); LightSetModel still runs. =2 (check build):
// the walk runs anyway and every part of a gated model must leave the native path at the fog gate ("PGATE ... bad=0").
#if !RE4DC_SCENERY_GATE || !RE4DC_FRONT_LEAN || !RE4DC_SKIN_PALETTE_LAZY || !RE4DC_NATIVE_ACTOR_SKIN_LAZY
#error "PROP_GATE needs SCENERY_GATE=1 FRONT_LEAN=1 SKIN_PALETTE_LAZY=1 NATIVE_ACTOR_SKIN_LAZY=1"
#endif
extern "C" unsigned re4dc_fog_enabled();
extern "C" void re4dc_fog_note_far(float far) __attribute__((weak));  // native_static.cpp (NATIVE_FOG builds)
extern "C" int re4dc_actor_skin_lazy_known(const void* info);        // native_actor_fast.cpp (PROP_GATE)
extern "C" void re4dc_log(const char* fmt, ...);
#if RE4DC_PROP_GATE == 2
extern "C" unsigned re4dc_pg_expect, re4dc_pg_fogged;  // native_actor_fast.cpp: parts that left at the fog gate
#endif
namespace {
const u32 kPgParts = 64;  // parts matrices bounded per model (a model with more is not gated)
struct PgStats {
    u32 tests, culled, kept, why[10], log;
#if RE4DC_PROP_GATE == 2
    u32 chk_models, chk_parts, chk_fogged;
#endif
} g_pg;
const void* g_pgWeights[32];  // weight tables already found convex with ids below their model's parts count
u32 g_pgWeightParts[32], g_pgWeightsNum;
}
static int propGateNo(int why)
{
    g_pg.why[why]++;
    return 0;
}
// 1 when every entry of weight table w blends parts below `parts` with weights >= 0 that sum to 1: the last weight is
// 1 - the others (MakeWeightPalette), so the other percents may not exceed 100.
static int propGateWeights(const Weight* w, u32 n, u32 parts)
{
    for (u32 k = 0; k < g_pgWeightsNum && k < 32; k++) {
        if (g_pgWeights[k] == w && g_pgWeightParts[k] == parts) {
            return 1;
        }
    }
    if (PTR_INVALID(w) || !n) {
        return 0;
    }
    for (u32 i = 0; i < n; i++) {
        const u32 num = w[i].num;
        u32 sum = 0;
        if (num < 1 || num > 3) {
            return 0;
        }
        for (u32 j = 0; j < num; j++) {
            if (w[i].id[j] >= parts) {
                return 0;
            }
            if (j + 1 < num) {
                sum += w[i].wht[j];
            }
        }
        if (sum > 100) {
            return 0;
        }
    }
    g_pgWeights[g_pgWeightsNum & 31] = w;
    g_pgWeightParts[g_pgWeightsNum & 31] = parts;
    g_pgWeightsNum++;
    return 1;
}
static int propGate(cModel* m, Mtx viewMat)
{
    if (pG->Frame_cnt - g_pg.log >= 600) {
        g_pg.log = pG->Frame_cnt;
        re4dc_log("PGATE frame=%u tests=%u culled=%u kept=%u why=%u,%u,%u,%u,%u,%u,%u,%u,%u,%u"
#if RE4DC_PROP_GATE == 2
                  " check models=%u parts=%u fogged=%u bad=%u"
#endif
                  "\n", pG->Frame_cnt, g_pg.tests, g_pg.culled, g_pg.kept, g_pg.why[0], g_pg.why[1], g_pg.why[2],
                  g_pg.why[3], g_pg.why[4], g_pg.why[5], g_pg.why[6], g_pg.why[7], g_pg.why[8], g_pg.why[9]
#if RE4DC_PROP_GATE == 2
                  , g_pg.chk_models, g_pg.chk_parts, g_pg.chk_fogged, g_pg.chk_parts - g_pg.chk_fogged
#endif
        );
    }
    g_pg.tests++;
    if (m->kindid != 1 || m->ot_type == 7 || (MODEL_EXT(m)->pFootShadowTbl != 0 && (m->be_flag & 0x10)) ||
        (m->be_flag & 0x4000) || m->invisible_factor * m->invisible_factor2 != 1.0f || PTR_INVALID(m->pParts)) {
        return propGateNo(0);
    }
    f32 projection[7];
    GXGetProjectionv(projection);
    if (projection[0] != 0) {
        return propGateNo(1);
    }
    const f32 nearZ = projection[6] / (projection[5] - 1), farZ = projection[6] / projection[5];
    if (!(nearZ > 0) || !(farZ > nearZ) || !(farZ < 1.0e30f)) {
        return propGateNo(1);
    }
    f32 cullFar = farZ;
    if (re4dc_fog_enabled()) {
        const f32 v = re4dc_fog_far_for_gate(View._zfar);
        if (v > nearZ && v < farZ) {
            cullFar = v;
        }
    }
    const f32 limit = cullFar * 1.001f + 10.0f;
    // The parts matrices exactly as calcWeightMat builds them: translations and the largest column norm.
    f32 t[kPgParts][3];
    f32 s2 = 0.0f;
    u32 np = 0;
    Mtx inv;
    Mtx tmp;
    Mtx pal;
    RE4DC_RENDER_MTXInverse(m->pParts->mat, inv);
    for (cPartsWk* p = (cPartsWk*) m->pParts; p != 0; p = p->next) {
        if (np == kPgParts) {
            return propGateNo(2);
        }
        RE4DC_RENDER_MTXConcat(inv, ((cModel*) p)->mat, tmp);
        RE4DC_RENDER_MTXConcat(tmp, p->bindMat, pal);
        for (u32 c = 0; c < 3; c++) {
            const f32 n2 = pal[0][c] * pal[0][c] + pal[1][c] * pal[1][c] + pal[2][c] * pal[2][c];
            if (!(n2 <= s2)) {
                s2 = n2;  // NaN propagates: the bound below fails
            }
        }
        t[np][0] = pal[0][3];
        t[np][1] = pal[1][3];
        t[np][2] = pal[2][3];
        np++;
    }
    if (!np || !(s2 < 1.0e30f)) {
        return propGateNo(2);
    }
    const f32 smax = __builtin_sqrtf(s2);
    int drawn = 0;
    for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
        if (PTR_INVALID(info)) {
            return propGateNo(3);
        }
        if (!(info->be_flag & 8)) {
            continue;
        }
        ModelData* d = info->pData;
        if (PTR_INVALID(d) || (info->be_flag & 2) || d->weight_ext_num > 0xFF || d->shapeOfs ||
            (d->weight_palette_num <= 1 && d->nParts == 1) || info->invisible_factor != 1.0f || d->nTex > 0xF7) {
            return propGateNo(4);
        }
        if (info->pPosBuf[pG->vtx_buf_no] != 0 || !re4dc_actor_skin_lazy_known(info)) {
            return propGateNo(5);
        }
        if (!propGateWeights((const Weight*) d->pWeight, d->weight_palette_num, np)) {
            return propGateNo(6);
        }
        // The bind ball of every part: the converted blob's header (BlobHeader: centre at +16, radius at +28).
        f32 R = 0.0f;
        ModelPart* part = d->pParts;
        for (u32 i = 0; i < d->displist_num; i++) {
            const u8* s = (const u8*) part + 0x20;
            if (part->size < 32 || s[0] != 0xFE || s[1] != 3) {
                return propGateNo(7);
            }
            f32 c[4];
            memcpy(c, s + 16, sizeof(c));
            if (!(c[3] > 0.0f) && c[0] == 0.0f && c[1] == 0.0f && c[2] == 0.0f) {
                return propGateNo(7);  // the actor gate skips a part without bounds
            }
            const f32 rr = __builtin_sqrtf(c[0] * c[0] + c[1] * c[1] + c[2] * c[2]) + c[3];
            if (!(rr >= 0.0f) || !(rr < 1.0e30f)) {
                return propGateNo(7);
            }
            if (rr > R) {
                R = rr;
            }
            part = (ModelPart*) (s + part->size);
        }
        // The info's modelview, as frontNativeModelTrans builds it for a skinned info.
        Mtx pm;
        Mtx mv;
        RE4DC_RENDER_MTXConcat(m->pParts->mat, (f32(*)[4]) &info->x5C, pm);
        RE4DC_RENDER_MTXConcat(viewMat, pm, mv);
        const f32 mz = __builtin_sqrtf(mv[2][0] * mv[2][0] + mv[2][1] * mv[2][1] + mv[2][2] * mv[2][2]);
        f32 T = 3.0e38f;
        for (u32 j = 0; j < np; j++) {
            const f32 dz = -(mv[2][0] * t[j][0] + mv[2][1] * t[j][1] + mv[2][2] * t[j][2] + mv[2][3]);
            if (!(dz >= T)) {
                T = dz;
            }
        }
        const f32 depth = T - mz * smax * R;
        if (!(depth > limit)) {
            g_pg.kept++;
            return 0;
        }
        drawn = 1;
    }
    if (!drawn) {
        return propGateNo(8);
    }
#if RE4DC_PROP_GATE == 2
    // Check build: draw it anyway; every part of the model must leave re4dc_actor_submit at the fog gate.
    {
        u32 parts = 0;
        for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
            if (info->be_flag & 8) {
                parts += info->pData->displist_num;
            }
        }
        const u32 f0 = re4dc_pg_fogged;
        re4dc_pg_expect = 1;
        frontNativeModelTrans(m, viewMat, 0);
        re4dc_pg_expect = 0;
        g_pg.chk_models++;
        g_pg.chk_parts += parts;
        g_pg.chk_fogged += re4dc_pg_fogged - f0;
        g_pg.culled++;
        return 1;
    }
#else
    // Skipped: keep what the part walk leaves for later models (sceneryGate's list).
    GxWork* gx = GXWORK();
    int matSet = 0;
    int parts = 0;
    PSet(g_pShdMng, 0);
    for (cModelInfo* info = m->pModelInfo; info != 0; info = info->pList) {
        if (info->be_flag & 0x20) {
            GXSetChanMatColor(4, *(GXColor*) info->color);
            matSet = 1;
        } else if (matSet == 1) {
            GXSetChanMatColor(4, *(GXColor*) m->pModelInfo->color);
        }
        if (!(info->be_flag & 8)) {
            continue;
        }
        parts += info->pData->displist_num;
        ModelData* id = info->pData;
        if (g_prev_tpl_addr != info->tpl_addr || g_prev_add_tpl_addr != info->pAddTpl) {
#if RE4DC_FRONT_TEXOBJ
            if (!frontTexInit(m, info, id))
#endif
            {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::FrontSource, 1);
#endif
#line 2843
                for (u32 i = 0; i < ((TEXPalette*) info->tpl_addr)->numDescriptors + info->nAddTex; i++) {
                    TEXPalette* tpl = (TEXPalette*) info->tpl_addr;
                    TEXDescriptor* td;
                    if (tpl->numDescriptors == 0) {
                        td = TEXGet(info->pAddTpl, i);
                    } else if (i < tpl->numDescriptors) {
                        td = TEXGet(tpl, i);
                    } else {
                        td = TEXGet(info->pAddTpl, i - tpl->numDescriptors);
                    }
                    if ((s32) id->flags < 0) {
                        TEXHeader* wh = td->textureHeader;
#if RE4DC_FRONT_TPL_OWNER
                        if (wh->wrapT != 1 || wh->wrapS != 1) re4dc_front_tpl_header_changed(wh);
#endif
                        wh->wrapT = 1;
                        wh->wrapS = 1;
                    }
                    GXInitTexObj(&gx->texObj[i], td->textureHeader->data, td->textureHeader->width, td->textureHeader->height,
                                 td->textureHeader->format, td->textureHeader->wrapS, td->textureHeader->wrapT,
                                 td->textureHeader->minLOD == td->textureHeader->maxLOD ? 0 : 1);
                }
                if (MODEL_EXT(m)->pTexChg != 0) {
                    MODEL_EXT(m)->pTexChg->move(gx->texObj);
                }
            }
        }
        PSet(g_prev_tpl_addr, info->tpl_addr);
        PSet(g_prev_add_tpl_addr, info->pAddTpl);
    }
    if (parts) {
        int scale = 0;
        const int group = m->TevScaleGroup;
        if (group == 0 || group == 1) {
            scale = gxCsScale[group] == 1 ? 1 : gxCsScale[group] == 2 ? 2 : 0;
        } else if (group == 5) {
            scale = 1;
        } else if (group == 6) {
            scale = 2;
        }
        GXSetTevColorOp(0, 0, 0, scale, 1, 0);
    }
    if (re4dc_fog_note_far) {
        re4dc_fog_note_far(View._zfar);  // the bridge notes the source View far at every part
    }
    g_pg.culled++;
    return 1;
#endif
}
#endif
static void frontNativeRender(cModel* m, int dry)
{
    CameraCurrentProjection();
#if RE4DC_SCENERY_GATE && RE4DC_FRONT_LEAN
    if (!dry && sceneryGate(m)) {
        return;
    }
#endif
#if RE4DC_FRONT_LEAN
    g_leanRender = frontLean(m) & FRONT_LEAN_LIGHTS;
    if (!g_leanRender && !dry) {
        for (u32 k = 0; k < g_leanSkippedNum; k++) {
            if (g_leanSkipped[k] == m) {
                LightMgr.setModel2(m);
                break;
            }
        }
    }
#endif
    LightSetModel(m);
#if defined(RE4DC_PROP_GATE) && RE4DC_PROP_GATE
    if (dry || !propGate(m, pG->Cam.v_mat))  // PROP_GATE: a skinned room object wholly beyond the actor fog gate
#endif
    frontNativeModelTrans(m, pG->Cam.v_mat, dry);
#if RE4DC_FRONT_LEAN
    g_leanRender = 0;
#endif
    GXSetChanCtrl(0, 0, 0, 0, 0, 0, 2);
    if (!dry && (pG->Debug_flg[1] & 0x40000000)) {
        m->drawAllBoundingBox(m->pModelInfo);
    }
}
#endif

// Applies the model's texture replacements (texture object `from` -> `to` pairs).
void cTexChg::move(GXTexObj* texObj)
{
    int i;
    u8* p = tbl;

    for (i = 0; i < num; i++) {
        texObj[p[0]] = texObj[p[1]];
        p += 2;
    }
}

// Thermal-scope view (Status_flg[1] 0x04000000, the rifle's infrared scope): the part is drawn
// with the thermo palette instead of its material.
static void ThermoShaderSetup(cModel* m, cModelInfo* info, ModelPart* part)
{
    int st;
    int map;

    ISET0(tev_stage);
    ISET0(tev_reg);
    ISET0(tev_kcolor);
    ISET0(tex_map);
    ISET0(tex_coord);
    ISET0(ind_stage);
    GXSetAlphaCompare(4, 0, 1, 4, 0xFF);
    GXSetBlendMode(1, 4, 5, 0);
    st = TEV_STAGE_ID();
    map = getTexMap();
    GXSetTevOrder(st, getTexCoord(), map, 4);
    GXSetTevColorIn(st, 0xF, 0xF, 0xF, 0xA);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 5);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
    if (part->flags & 4) {
        alphaSetup(m, part, info, 1);
    }
    GXSetNumTevStages(tev_stage);
    GXSetNumTexGens(tex_coord);
    GXSetNumIndStages(ind_stage);
}

// TEV setup of one part: thermo or refraction shaders take over entirely; else the self-shadow
// or cast-shadow stages, the material (texture, blends), specular / bump (part flags), global
// illumination (be_flag 0x01000000), the alpha texture (part flags 4), and the colour scale of
// the model's TevScaleGroup (gxCsScale).
static void shaderSetup(cModel* m, cModelInfo* info, ModelPart* part, Mtx mv)
{
    int selfDone;
    int st;
    int scale;

    if (pG->Status_flg[1] & 0x04000000) {
        ThermoShaderSetup(m, info, part);
        return;
    }
    if ((m->Shader_type == 1 || m->Shader_type == 2) && m->Refract_ratio != 0xFF && !(info->be_flag & 4)) {
        RefractShaderSetup(m, info, part, mv);
        return;
    }
    ISET0(tev_stage);
    ISET0(tev_reg);
    ISET0(tev_kcolor);
    ISET0(tex_map);
    ISET0(tex_coord);
    ISET0(ind_stage);
    selfDone = 0;
    if ((pGS->Status_flg[0] & 1) && isSelfUse) {
        u32 i;
        for (i = 0; i < g_SelfShdNum; i++) {
            if (GetSelfShadowMng(i)->pModel[0] == m) {
                if (selfDone == 1) {
                    pLog->err(0, 0, "SelfShadowLight overlap!!");
                    break;
                }
                selfDone = 1;
                SelfShadowSetup(part, m, GetSelfShadowMng(i));
                materialSetup(part, info, 0, 0);
            }
        }
    }
    if (selfDone == 0) {
        int colIn;
        int alphaIn;
        if (g_pShdMng != 0) {
            ShadowCastSetup(part, m);
            colIn = 0;
            alphaIn = 0;
        } else {
            colIn = 0xA;
            alphaIn = 5;
        }
        materialSetup(part, info, colIn, alphaIn);
    }
    if (part->flags & 0x80) {
        specularSetup2(part, 0);
    } else {
        specularSetup(part, info, 0);
        bumpSetup(part, info);
    }
    if (m->be_flag & 0x01000000) {
        GlobalIlluminationSetup(part, isBit(info->pData->flags, 0x20000000));
    }
    if (part->flags & 4) {
        alphaSetup(m, part, info, 0);
    }
    st = TEV_STAGE_ID();
    GXSetTevOrder(st, 0xFF, 0xFF, 4);
    GXSetTevColorIn(st, 0xF, 0xF, 0xF, 0);
    switch (m->TevScaleGroup) {
    case 0:
    case 1:
        switch (gxCsScale[m->TevScaleGroup]) {
        case 0:
            scale = 0;
            break;
        case 1:
            scale = 1;
            break;
        case 2:
            scale = 2;
            break;
        default:
            scale = 0;
            pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", gxCsScale[m->TevScaleGroup]);
            break;
        }
        break;
    case 4:
        scale = 0;
        break;
    case 5:
        scale = 1;
        break;
    case 6:
        scale = 2;
        break;
    default:
        scale = 0;
        pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", m->TevScaleGroup);
        break;
    }
    GXSetTevColorOp(st, 0, 0, scale, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 0);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    GXSetNumTevStages(++tev_stage);
    GXSetNumTexGens(IRef(tex_coord));
    GXSetNumIndStages(IRef(ind_stage));
}

// Load the blend table's texture for `part` (tbl: [0] count, [4 + 2i] part texture id or 0xF7, [5 + 2i] texture id).
static inline void loadBlendTex(ModelPart* part, u8* tbl, int map)
{
    int i;
    for (i = 0; i < tbl[0]; i++) {
        u8* e = &tbl[5] + i * 2;
        if (part->texId == e[-1] || e[-1] == 0xF7) {
            org_LoadTexObj(e[0], map);
        }
    }
}

// Material blend type 0 (blendType 0): the blend-table textures (matched to the part's texture)
// layered over the base stage with the info's blendRatio as constant-colour weight.
static void TextureBlend(ModelPart* part, cModelInfo* info, int colIn, int alphaIn)
{
    int st;
    ModelTexInfo* t;
    int map;
    int coord;
    u32 mtx;
    u8* tbl;
    int i;

    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    t = MODEL_TEX(info);
    mtx = getTexMtx();
    {
        u8* btbl = (u8*) t->blendTbl;
        if (t->blendRatio == 0xFF) {
            loadBlendTex(part, btbl, map);
        }
    }
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, alphaIn);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
    if (U16Ref(t->blendRatio) == 0 || t->blendRatio == 0xFF) {
        return;
    }
    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    tbl = (u8*) t->blendTbl;
    for (i = 0; i < tbl[0]; i++) {
        int ofs = i * 2;
        u8* e = tbl + 4;
        u8 id = e[ofs];
        if (part->texId == id || id == 0xF7) {
            int reg;
            GXColor k;
            GXColor kc;
            e = tbl + 5;
            org_LoadTexObj(e[ofs], map);
            if (t->flags & 1) {
                GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
            } else {
                GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
            }
            reg = getTevReg();
            GXSetTevOrder(st, coord, map, 4);
            GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, reg);
            GXSetTevAlphaIn(st, 7, 7, 7, alphaIn);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
            tev_stage++;
            tex_map++;
            tex_coord++;
            st = TEV_STAGE_ID();
            map = getTexMap();
            coord = getTexCoord();
            k.a = k.b = k.g = k.r = (u8) t->blendRatio;
            kc = k;
            GXSetTevKColor(getKColor(), kc);
            GXSetTevKColorSel(st, getKColorSel());
            GXSetTevKAlphaSel(st, getKAlphaSel());
            tev_kcolor++;
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0, getTevRegC(), 0xE, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 0, getTevReg(), 6, 7);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
            tev_reg++;
        }
    }
}

// Material blend type 1: the blend-table texture layered over the base with the blendRatio
// weight; the alpha comes from the second texture (probably: differs from type 0 in the alpha path).
static void TextureBlend2(ModelPart* part, cModelInfo* info, int colIn, int alphaIn)
{
    int st;
    ModelTexInfo* t;
    int map;
    int coord;
    u32 mtx;
    u8* tbl;
    int i;

    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    t = MODEL_TEX(info);
    mtx = getTexMtx();
    {
        u8* btbl = (u8*) t->blendTbl;
        if (t->blendRatio == 0xFF) {
            loadBlendTex(part, btbl, map);
        }
    }
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 4, alphaIn, 7);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
    if (U16Ref(t->blendRatio) == 0 || t->blendRatio == 0xFF) {
        return;
    }
    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    tbl = (u8*) t->blendTbl;
    for (i = 0; i < tbl[0]; i++) {
        int ofs = i * 2;
        u8* e = tbl + 4;
        u8 id = e[ofs];
        if (part->texId == id || id == 0xF7) {
            int reg;
            GXColor k;
            GXColor kc;
            e = tbl + 5;
            org_LoadTexObj(e[ofs], map);
            if (t->flags & 1) {
                GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
            } else {
                GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
            }
            reg = getTevReg();
            GXSetTevOrder(st, coord, map, 4);
            GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, reg);
            GXSetTevAlphaIn(st, 7, 7, 7, 4);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
            tev_stage++;
            tex_map++;
            tex_coord++;
            st = TEV_STAGE_ID();
            map = getTexMap();
            coord = getTexCoord();
            k.a = k.b = k.g = k.r = (u8) t->blendRatio;
            kc = k;
            GXSetTevKColor(getKColor(), kc);
            GXSetTevKColorSel(st, getKColorSel());
            GXSetTevKAlphaSel(st, getKAlphaSel());
            tev_kcolor++;
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0, getTevRegC(), 0xE, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 0);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
            tev_reg++;
        }
    }
}

// Material blend type 2: the blend-table texture over the base (blendRatio 0 = no second
// texture) with the alpha kept from the input (`use_alp`).
static void TextureBlend3(ModelPart* part, cModelInfo* info, int colIn, int alphaIn)
{
    static int use_alp = 1;
    ModelTexInfo* t;
    int st;
    int map;
    int coord;
    u32 mtx;
    u8* tbl;
    int i;

    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    t = MODEL_TEX(info);
    mtx = getTexMtx();
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, alphaIn);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
    if (U16Ref(t->blendRatio) == 0) {
        return;
    }
    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    tbl = (u8*) t->blendTbl;
    for (i = 0; i < tbl[0]; i++) {
        int ofs = i * 2;
        u8* e = tbl + 4;
        u8 id = e[ofs];
        if (part->texId == id || id == 0xF7) {
            u8 texId;
            u8* e2 = tbl + 5;
            texId = e2[ofs];
            org_LoadTexObj(texId, map);
            if (t->flags & 1) {
                GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
            } else {
                GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
            }
            if (use_alp) {
                int reg;
                int reg2;
                GXColor k;
                GXColor kc;
                reg = getTevReg();
                GXSetTevOrder(st, coord, map, 4);
                GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
                GXSetTevColorOp(st, 0, 0, 0, 1, reg);
                GXSetTevAlphaIn(st, 7, 7, 7, 5);
                GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
                tev_stage++;
                tex_map++;
                tex_coord++;
                st = TEV_STAGE_ID();
                map = getTexMap();
                coord = getTexCoord();
                org_LoadTexObj(texId, map);
                if (t->flags & 1) {
                    GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
                } else {
                    GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
                }
                k.a = k.b = k.g = k.r = (u8) t->blendRatio;
                kc = k;
                GXSetTevKColor(getKColor(), kc);
                GXSetTevKColorSel(st, getKColorSel());
                GXSetTevKAlphaSel(st, getKAlphaSel());
                tev_kcolor++;
                reg = getTevRegNext(reg2);
                GXSetTevOrder(st, coord, map, 0xFF);
                if (t->blendRatio > 0xFF) {
                    GXSetTevColorIn(st, 0xF, 0xC, 9, 0xE);
                    GXSetTevColorOp(st, 0, 0, 0, 1, reg);
                    GXSetTevAlphaIn(st, 6, 6, 7, 4);
                    GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
                } else {
                    GXSetTevColorIn(st, 0xF, 0xE, 9, 0xF);
                    GXSetTevColorOp(st, 0, 0, 0, 1, reg);
                    GXSetTevAlphaIn(st, 7, 6, 4, 7);
                    GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
                }
                tev_stage++;
                tex_map++;
                tex_coord++;
                st = TEV_STAGE_ID();
                GXSetTevOrder(st, 0xFF, 0xFF, 4);
                GXSetTevColorIn(st, 0, getTevRegC(), getTevRegA(reg2), 0xF);
                GXSetTevColorOp(st, 0, 0, 0, 1, 0);
                GXSetTevAlphaIn(st, 0, alphaIn, getTevReg(reg2), 7);
                GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
                tev_stage++;
                tev_reg += 2;
            } else {
                int reg = getTevReg();
                GXSetTevOrder(st, coord, map, 4);
                GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
                GXSetTevColorOp(st, 0, 0, 0, 1, reg);
                GXSetTevAlphaIn(st, 7, 7, 7, alphaIn);
                GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
                tev_stage++;
                tex_map++;
                tex_coord++;
                st = TEV_STAGE_ID();
                map = getTexMap();
                coord = getTexCoord();
                org_LoadTexObj(texId, map);
                if (t->flags & 1) {
                    GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
                } else {
                    GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
                }
                GXSetTevOrder(st, coord, map, 0xFF);
                GXSetTevColorIn(st, 0, getTevRegC(), 9, 0xF);
                GXSetTevColorOp(st, 0, 0, 0, 1, 0);
                GXSetTevAlphaIn(st, 0, getTevReg(), 4, 7);
                GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
                tev_stage++;
                tex_map++;
                tex_coord++;
                tev_reg++;
            }
        }
    }
}

// Base material stage: the part's texture (animated frame when the info animates), texgen by UV
// or by the UV-scroll matrix, then one of the blend types when the info blends (flags bit2),
// producing the colour from `colIn` / `alphaIn`.
static void materialSetup(ModelPart* part, cModelInfo* info, int colIn, int alphaIn)
{
    int st;
    ModelTexInfo* t;
    int map;
    int coord;
    u8 texId;

    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    ISet(g_material_tex_coord, coord);
    t = MODEL_TEX(info);
    texId = part->texId;
    if ((t->flags & 2) && t->anim != 0) {
        u8* tbl = t->anim + 4;
        texId = tbl[t->frame];
    }
    org_LoadTexObj(texId, map);
#if defined(RE4DC_GAME) && !defined(__PPC__)
    re4dc_model_material(texId <= 0xF7 ? &GXWORK()->texObj[texId] : 0, t->u, t->v, t->flags);
#endif
    if (t->flags & 1) {
        u32 mtx = getTexMtx();
        Mtx m;
        PSMTXIdentity(m);
        m[0][2] = t->u;
        m[1][2] = t->v;
        GXLoadTexMtxImm(m, mtx, 1);
        GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
    } else {
        GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
    }
    if (t->flags & 4) {
        switch (t->blendType) {
        case 0:
            TextureBlend(part, info, colIn, alphaIn);
            break;
        case 1:
            TextureBlend2(part, info, colIn, alphaIn);
            break;
        case 2:
            TextureBlend3(part, info, colIn, alphaIn);
            break;
        default:
            pLog->err(0, 0, "Model BlendType invalid.[%x]", t->blendType);
            break;
        }
        return;
    }
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 8, colIn, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, alphaIn);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
}

// Specular / environment stage (part flags 0x13): the specular texture selected by the part,
// normal-based texgen, colour from the part's spec colour or the info colour2.
static void specularSetup(ModelPart* part, cModelInfo* info, int flag)
{
    GXColor col;
    GXColor kc;
    Mtx tmp;
    f32 scale;
    int st;
    int map;
    int coord;
    u32 mtx;
    u8 type;

    if ((part->flags & 0x13) == 0) {
        return;
    }
    if (info->color2[3] == 0) {
        col.r = part->specR;
        col.g = part->specG;
        col.b = part->specB;
        col.a = 0xFF;
    } else {
        col.r = info->color2[0];
        col.g = info->color2[1];
        col.b = info->color2[2];
        col.a = 0xFF;
    }
    scale = (f32) (int) part->specPow * 0.01f;
    if (scale == 0.0f) {
        scale = 0.5f;
    }
    if (isBit(info->pData->flags, 0x20000000) == 1) {
        scale *= 0.5f;
    }
    {
        Mtx s;
        Mtx t;
        PSMTXScale(s, scale, -scale, 0.0f);
        PSMTXTrans(t, 0.5f, 0.5f, 1.0f);
        PSMTXConcat(s, specular_mat, tmp);
        PSMTXConcat(t, tmp, tmp);
    }
    type = part->specType;
    st = TEV_STAGE_ID();
    map = getTexMap();
    g_specular_tev_stage = st;
    if (!(part->flags & 0x10)) {
        u32 idx = part->specTex;
        if (idx == 0xFF) {
            idx = 0;
        }
        GXLoadTexObj(&Specular[idx], map);
    } else {
        org_LoadTexObj(part->specTexOrg, map);
    }
    coord = getTexCoord();
    mtx = getTexMtx();
    GXLoadTexMtxImm(tmp, mtx, 0);
    GXSetTexCoordGen2(coord, 0, 1, mtx, 0, 0x7D);
    GXSetTevOrder(st, coord, map, 4);
    switch (type) {
    case 0: {
        int reg = getTevReg();
        GXSetTevColorIn(st, 0xF, 8, 0xA, 0xF);
        if (flag) {
            GXSetTevColorOp(st, 0, 0, 2, 1, reg);
        } else {
            GXSetTevColorOp(st, 0, 0, 0, 1, reg);
        }
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        tex_map++;
        st = TEV_STAGE_ID();
        GXSetTevKColorSel(st, getKColorSel());
        kc = col;
        GXSetTevKColor(getKColor(), kc);
        tev_kcolor++;
        GXSetTevOrder(st, 0xFF, 0xFF, 4);
        GXSetTevColorIn(st, 0xF, 0xE, getTevRegC(), 0);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        tev_reg++;
        break;
    }
    case 1:
        GXSetTevColorIn(st, 0xF, 9, 0, 0);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        tex_map++;
        break;
    }
    tex_coord++;
}

// Bump-mapped specular variant (part flags 0x80): indirect stage with the bump texture
// perturbing the specular lookup.
static void specularSetup2(ModelPart* part, int flag)
{
    static f32 bp_mx = 0.0f;
    static f32 bp_my = 0.0f;
    static f32 mul_x = 1.0f;
    static f32 mul_y = -1.0f;
    static f32 pow = -0.02f;
    int st;

    do {
        if (!(part->flags & 3)) {
            return;
        }
    } while (0);
    st = TEV_STAGE_ID();
    {
        int map = getTexMap();
        org_LoadTexObj(part->bumpTex, map);
        int coord = getTexCoord();
        GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
        GXSetTevOrder(st, coord, map, 4);
        GXSetTevColorIn(st, 0xF, 8, 0xC, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, getTevReg());
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        tex_map++;
        tex_coord++;
    }
    st = TEV_STAGE_ID();
    {
        int coord = getTexCoord();
        u32 mtx = getTexMtx();
        int map = getTexMap();
        Mtx tmp;
        org_LoadTexObj(part->bumpTex, map);
        PSMTXIdentity(tmp);
        tmp[0][2] = bp_mx;
        tmp[1][2] = bp_my;
        GXLoadTexMtxImm(tmp, mtx, 1);
        GXSetTexCoordGen2(coord, 1, 4, mtx, 0, 0x7D);
        GXSetTevOrder(st, coord, map, 4);
        tex_map++;
        tex_coord++;
        __GXSetIndirectMask(0);
        {
            f32 mx = pow * mul_x;
            f32 my = pow * mul_y;
            f32 ang = 0.0f;
            f32 indMtx[2][3];
            indMtx[0][0] = -my * sinf(ang);
            indMtx[0][1] = mx * cosf(ang);
            indMtx[0][2] = ang;
            indMtx[1][0] = my * cosf(ang);
            indMtx[1][1] = mx * sinf(ang);
            indMtx[1][2] = ang;
            GXSetIndTexMtx(2, indMtx, 1);
            int map = getTexMap();
            int coord = getTexCoord();
            GXLoadTexObj(&IndTex[0], map);
            u32 mtx = getTexMtx();
            Mtx s;
            Mtx t;
            PSMTXScale(s, 0.5f, -0.5f, 0.0f);
            PSMTXTrans(t, 0.5f, 0.5f, 1.0f);
            PSMTXConcat(s, specular_mat, tmp);
            PSMTXConcat(t, tmp, tmp);
            GXLoadTexMtxImm(tmp, mtx, 0);
            GXSetTexCoordGen2(coord, 0, 1, mtx, 0, 0x7D);
            int ind = IND_STAGE_ID();
            GXSetIndTexOrder(ind, coord, map);
            GXSetIndTexCoordScale(ind, 0, 0);
            GXSetTevIndWarp(st, ind, 1, 0, 2);
            ind_stage++;
            tex_map++;
            tex_coord++;
        }
        GXSetTevColorIn(st, 0xF, getTevRegC(), 0xC, 8);
        GXSetTevColorOp(st, 1, 1, 0, 1, getTevReg());
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
    }
    st = TEV_STAGE_ID();
    GXSetTevOrder(st, 0xFF, 0xFF, 4);
    GXSetTevColorIn(st, 0xF, 0, getTevRegC(), 0xF);
    GXSetTevColorOp(st, 0, 0, 1, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 0);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tev_reg++;
}

// Adds the global illumination texture stage (normal-based lookup; scale 0.25 for 8-bit normals);
// off with Disp_flg 0x00080000.
static void GlobalIlluminationSetup(ModelPart* part, int nrm8)
{
    Mtx tmp;
    int st;
    int map;
    int coord;
    u32 mtx;

    if (pG->Disp_flg & 0x00080000) {
        return;
    }
    {
        Mtx s;
        Mtx t;
        f32 scale = 0.5f;
        if (nrm8 == 1) {
            scale = 0.25f;
        }
        PSMTXScale(s, scale, -scale, 0.0f);
        PSMTXTrans(t, 0.5f, 0.5f, 1.0f);
        PSMTXConcat(s, specular_mat, tmp);
        PSMTXConcat(t, tmp, tmp);
    }
    st = TEV_STAGE_ID();
    map = getTexMap();
    GXLoadTexObj(&GlobalIlmTex[0], map);
    coord = getTexCoord();
    mtx = getTexMtx();
    GXLoadTexMtxImm(tmp, mtx, 0);
    GXSetTexCoordGen2(coord, 0, 1, mtx, 0, 0x7D);
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 8, 0, 0xF);
    GXSetTevColorOp(st, 0, 0, 1, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 0);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
    tex_coord++;
}

// The GX light used by the shadow-cast pass: at the shadow light's position / direction, with the
// cast colours (cast_col1..3) as material / ambient.
static void SetCastShadowLight(cModel* m, Vec* pos, Vec* dir, ShadowMng* mng)
{
    static u8 cast_col1 = 0xC0;
    static GXColor cast_col2 = {0xFF, 0xFF, 0xFF, 0xFF};
    static GXColor cast_col3 = {0, 0, 0, 0xFF};
    GXLightObj lobj;
    Vec p;
    Vec d;
    GXColor c;
    GXColor k = {0xFF, 0, 0, 0};
    u32 n;
    u32 mask;

    k.a = k.b = k.g = 0xFF;
    PSMTXMultVec(pG->Cam.v_mat, pos, &p);
    GXInitLightPos(&lobj, p.x, p.y, p.z);
    PSMTXMultVecSR(pG->Cam.v_mat, dir, &d);
    GXInitLightDir(&lobj, d.x, d.y, d.z);
    GXInitLightSpot(&lobj, 89.0f, 4);
    GXInitLightDistAttn(&lobj, 0.0f, 0.0f, 0);
    if (m != 0) {
        EmLightArea* la = &MODEL_EXT(m)->litArea;
        if (la->chk(1) == 1 && la->chk(2) == 1 && la->lightNo == mng->pLight->LitIndex) {
            k.r = k.r * (u8) la->scale;
            k.g = k.g * (u8) la->scale;
            k.b = k.b * (u8) la->scale;
        }
    }
    c = k;
    GXInitLightColor(&lobj, c);
    n = m->LightInfo.getLightNum();
    if (n > 7) {
        pLog->err(4, 0, "CastLight: light num over!!");
        return;
    }
    mask = 1 << n;
    GXLoadLightObjImm(&lobj, mask);
    GXSetNumChans(2);
    GXSetChanCtrl(1, 1, 0, 0, mask, 2, 1);
    GXSetChanCtrl(3, 0, 0, 0, 0, 2, 2);
    c = cast_col2;
    GXSetChanMatColor(5, c);
    c = cast_col3;
    GXSetChanAmbColor(5, c);
}

// Adds the stage that projects the shadow light's texture (g_pShdMng texMat x the parts matrix)
// onto the part, modulating the colour.
static void ShadowCastSetup(ModelPart* part, cModel* m)
{
    GXTexObj* tex;
    GXTlutObj* tlut;
    GXColor k;
    GXColor kc;
    ShadowMng* mng = g_pShdMng;
    ShadowLightWork* w;
    int coord;
    u32 mtx;
    int map;
    int st;

    coord = getTexCoord();
    mtx = getTexMtx();
    map = getTexMap();
    st = TEV_STAGE_ID();
    // Declared after the table-copying getters: the frame slot for tm is the merged, freed
    // getTexCoord/getTexMtx table slots at 0x8 (tm shares the base register with them).
    Mtx tm;
    PSMTXConcat(mng->texMat, m->pParts->mat, tm);
    GXLoadTexMtxImm(tm, mtx, 0);
    GXSetTexCoordGen2(coord, 0, 0, mtx, 0, 0x7D);
    w = (ShadowLightWork*) mng->pLight->work;
    if (RoomGetTexObj(w->texId, 0, &tex)) {
        GXLoadTexObj(tex, map);
        if (RoomGetTlutObj(w->texId, &tlut)) {
            GXLoadTlut(tlut, 0);
        }
    }
    if (w->mode == 3 || w->mode == 4) {
        SetCastShadowLight(m, &mng->lightPos, &mng->dir, mng);
    }
    k.r = mng->pLight->Col.r;
    k.g = mng->pLight->Col.g;
    k.b = mng->pLight->Col.b;
    k.a = mng->pLight->Col.a;
    kc = k;
    GXSetTevKColor(getKColor(), kc);
    switch (w->mode) {
    case 1:
        GXSetTevKColorSel(st, getKColorSel());
        GXSetTevKAlphaSel(st, getKAlphaSel());
        tev_kcolor++;
        // Each arm carries the stage's tail through `tev_stage++` so the arm does not end in a
        // call (flow's post-call nop would stop jump2 cross-jumping the shared `li r7; bl`).
        if (U16Ref(w->flags) & 4) {
            GXSetTevOrder(st, coord, map, 0xFF);
            GXSetTevColorIn(st, 0xE, 0xF, 8, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 7);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
        } else {
            GXSetTevOrder(st, coord, map, 0xFF);
            GXSetTevColorIn(st, 0xF, 8, 0xE, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 7);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
        }
        st = TEV_STAGE_ID();
        GXSetTevOrder(st, 0xFF, 0xFF, 4);
        GXSetTevColorIn(st, 0xA, 0xF, 0, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 5);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        break;
    case 2:
        GXSetTevKColorSel(st, getKColorSel());
        GXSetTevKAlphaSel(st, getKAlphaSel());
        tev_kcolor++;
        if (U16Ref(w->flags) & 4) {
            GXSetTevOrder(st, coord, map, 4);
            GXSetTevColorIn(st, 0xE, 0xF, 8, 0xA);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        } else {
            GXSetTevOrder(st, coord, map, 4);
            GXSetTevColorIn(st, 0xF, 8, 0xE, 0xA);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        }
        break;
    case 3:
        GXSetTevOrder(st, coord, map, 5);
        GXSetTevColorIn(st, 0xF, 8, 0xA, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 5);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        st = TEV_STAGE_ID();
        GXSetTevKColorSel(st, getKColorSel());
        GXSetTevKAlphaSel(st, getKAlphaSel());
        tev_kcolor++;
        if (U16Ref(w->flags) & 4) {
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0xE, 0xF, 0, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 7);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
        } else {
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0xF, 0, 0xE, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 7);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
        }
        st = TEV_STAGE_ID();
        GXSetTevOrder(st, 0xFF, 0xFF, 4);
        GXSetTevColorIn(st, 0xA, 0xF, 0, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 5);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        break;
    case 4:
        if (w->flags & 4) {
            GXSetTevOrder(st, coord, map, 5);
            GXSetTevColorIn(st, 0xA, 0xF, 8, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
            st = TEV_STAGE_ID();
            GXSetTevKColorSel(st, getKColorSel());
            GXSetTevKAlphaSel(st, getKAlphaSel());
            tev_kcolor++;
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0xF, 0, 0xE, 0xA);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        } else {
            GXSetTevOrder(st, coord, map, 5);
            GXSetTevColorIn(st, 0xF, 8, 0xA, 0xF);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
            tev_stage++;
            st = TEV_STAGE_ID();
            GXSetTevKColorSel(st, getKColorSel());
            GXSetTevKAlphaSel(st, getKAlphaSel());
            tev_kcolor++;
            GXSetTevOrder(st, 0xFF, 0xFF, 4);
            GXSetTevColorIn(st, 0xF, 0, 0xE, 0xA);
            GXSetTevColorOp(st, 0, 0, 0, 1, 0);
            GXSetTevAlphaIn(st, 7, 7, 7, 5);
            GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        }
        break;
    }
    tev_stage++;
    tex_coord++;
    tex_map++;
}

// Self-shadow stage: the model's own depth shadow map compared through an indirect texture (the
// IndTex ramp) so parts in their own shadow darken.
static void SelfShadowSetup(ModelPart* part, cModel* m, ShadowMng* mng)
{
    static int shd_tex_no = 0;
    static f32 shd_z = -1.001f;
    int coord;
    u32 mtx;
    int map;
    int st;
    ShadowLightWork* w;
    u32 i;

    coord = getTexCoord();
    mtx = getTexMtx();
    map = getTexMap();
    st = TEV_STAGE_ID();
    GXLoadTexObj(&IndTex[shd_tex_no], map);
    // Declared after the table-copying getters: tm and up take the merged, freed table slots at
    // 0x8/0x38, sm and trans follow at 0x50/0x80, the second round of tables lands at 0xb0/0xd0.
    Mtx tm;
    Vec up = {0.0f, 1.0f, 0.0f};
    Mtx sm;
    Mtx trans;
    sm[0][0] = 0.0f;
    sm[0][1] = 0.0f;
    sm[0][2] = 0.0f;
    sm[0][3] = 0.0f;
    sm[1][0] = 0.0f;
    sm[1][1] = 0.0f;
    sm[1][3] = 0.0f;
    sm[2][0] = 0.0f;
    sm[2][1] = 0.0f;
    sm[2][2] = 0.0f;
    sm[2][3] = 0.0f;
    sm[1][2] = shd_tex_scale_x;
    PSMTXIdentity(trans);
    trans[2][3] = shd_ofs + PSVECDistance(&mng->lightPos, &mng->target);
    C_MTXLookAt(tm, &mng->lightPos, &up, &mng->target);
    PSMTXConcat(tm, mng->pModel[0]->pParts->mat, tm);
    PSMTXConcat(trans, tm, tm);
    PSMTXConcat(sm, tm, tm);
    GXLoadTexMtxImm(tm, mtx, 1);
    GXSetTexCoordGen2(coord, 1, 0, mtx, 0, 0x7D);
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 0xC, 9, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 5);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_coord++;
    tex_map++;
    st = TEV_STAGE_ID();
    coord = getTexCoord();
    mtx = getTexMtx();
    map = getTexMap();
    PSMTXConcat(mng->texMat, m->pParts->mat, tm);
    GXLoadTexMtxImm(tm, mtx, 0);
    GXSetTexCoordGen2(coord, 0, 0, mtx, 0, 0x7D);
    GXLoadTexObj(&mng->texObj, map);
    GXSetTevOrder(st, coord, map, 0xFF);
    GXSetTevColorIn(st, 0xC, 0xF, 9, 0);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 0);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    // Reference-setter stores are neither MEM_SCALAR_P nor MEM_IN_STRUCT_P, so the in-struct load
    // of mng->pLight below cannot be scheduled above them (plain `x++` stores are scalar and let it).
    ISet(tev_stage, tev_stage + 1);
    ISet(tex_coord, tex_coord + 1);
    ISet(tex_map, tex_map + 1);
    w = (ShadowLightWork*) mng->pLight->work;
    for (i = 0; i < w->selfShadow; i++) {
        st = TEV_STAGE_ID();
        GXSetTevOrder(st, 0xFF, 0xFF, 0xFF);
        GXSetTevColorIn(st, 0xF, 0, 0, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
    }
    st = TEV_STAGE_ID();
    GXSetTevOrder(st, 0xFF, 0xFF, 4);
    GXSetTevColorIn(st, 0xF, 0xA, 0, 0xF);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 7, 7, 0);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
}

// Bump stage (part flags bit0): the part's bump texture (or the blend table's) as an indirect
// texture perturbing the base lookup.
static void bumpSetup(ModelPart* part, cModelInfo* info)
{
    int off = !(part->flags & 1);
    ModelTexInfo* t;
    int map;
    int coord;
    int ind;
    u8 texId;

    if (off) {
        return;
    }
    t = MODEL_TEX(info);
    __GXSetIndirectMask(0);
    texId = part->bumpTex;
    map = getTexMap();
    if (info->flagsDC & 4) {
        u8* tbl = t->blendTbl;
        int i;
        for (i = 0; i < tbl[0]; i++) {
            u8* e = &tbl[5] + i * 2;
            if (part->bumpTex == e[-1] || e[-1] == 0xF7) {
                texId = e[0];
            }
        }
    }
    org_LoadTexObj(texId, map);
    coord = getTexCoord();
    GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
    ind = IND_STAGE_ID();
    GXSetIndTexOrder(ind, coord, map);
    GXSetIndTexCoordScale(ind, 0, 0);
    GXSetTevIndBumpXYZ(g_specular_tev_stage, ind, 1);
    tex_map++;
    tex_coord++;
    ind_stage++;
}

// Alpha texture stage (part flags 4): alpha compare against the part's alphaRef (or the model's
// alpha_omit), the alpha texture multiplied into the output alpha.
static void alphaSetup(cModel* m, ModelPart* part, cModelInfo* info, int thermo)
{
    int map;
    int st;
    int coord;
    u8 ref;

    GXSetZCompLoc(0);
    ref = m->alpha_omit;
    if (ref == 0xFF) {
        GXSetAlphaCompare(4, part->alphaRef, 1, 4, 0xFF);
    } else {
        GXSetAlphaCompare(4, ref, 1, 4, 0xFF);
    }
    map = getTexMap();
    org_LoadTexObj(part->alphaTex, map);
#if defined(RE4DC_GAME) && !defined(__PPC__)
    re4dc_model_alpha_material(part->alphaTex <= 0xF7 ? &GXWORK()->texObj[part->alphaTex] : 0,
                              ref == 0xFF ? part->alphaRef : ref,
                              !(info->flagsDC & 8) && !thermo);
#endif
    st = TEV_STAGE_ID();
    if ((info->flagsDC & 8) || thermo) {
        coord = getTexCoord();
        GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
        tex_coord++;
    } else {
        coord = g_material_tex_coord;
    }
    GXSetTevOrder(st, coord, map, 4);
    GXSetTevColorIn(st, 0xF, 0xF, 0xF, 0);
    GXSetTevColorOp(st, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(st, 7, 4, 0, 7);
    GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    tev_stage++;
    tex_map++;
}

// Frame start: flips the double-buffered primitive / vertex buffer (vtx_buf_no) and resets the
// allocation pointer.
#if RE4DC_PRIM_WATER
// PRIM_WATER (test only): the bytes each frame took from the primitive buffer, peak per room.
extern "C" void re4dc_log(const char* fmt, ...);
static u32 primw_room, primw_peak, primw_tail, primw_tail_peak, primw_frames, primw_cap, primw_declined, primw_overflow;
static u8* primw_start;
static void primWaterFrame()
{
    GxWork* g = GXWORK();
    if (primw_start && g->prim >= primw_start) {
        const u32 used = (u32) (g->prim - primw_start);
        if (used > primw_peak) primw_peak = used;
        if (primw_tail > primw_tail_peak) primw_tail_peak = primw_tail;
    }
    primw_tail = 0;
    if (primw_room != (u32) pG->room_id || primw_cap != (u32) pG->nPrim || (++primw_frames % 300) == 0) {
        if (primw_room) {
            re4dc_log("prim water: room %03x cap %u peak %u (actor tail peak %u) frames %u tail declined %u overflow %u\n",
                      primw_room, primw_cap, primw_peak, primw_tail_peak, primw_frames, primw_declined, primw_overflow);
        }
        if (primw_room != (u32) pG->room_id || primw_cap != (u32) pG->nPrim) {
            primw_peak = primw_tail_peak = primw_frames = primw_declined = primw_overflow = 0;
        }
        primw_room = pG->room_id;
        primw_cap = pG->nPrim;
    }
}
#endif
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
// OT_WALK_CHECK (lane ch4found16, debug arm): every GetPrimBuff slot is tagged (address, size, frame, caller) in a
// 2048-entry ring, and every buffer flip (SetPrimBuffPtr) too (size 0, caller = the new start), so the ExecOt check
// can name the allocations that cover a bad node (trans_ot.cpp re4dc_otwc_report).
struct Re4dcPrimTag { u32 addr, size, frame, caller; };
extern "C" { Re4dcPrimTag re4dc_prim_tags[2048]; u32 re4dc_prim_tag_n; }
#if RE4DC_OT_WALK_CHECK >= 2
extern "C" void re4dc_log(const char*, ...);
static u32* re4dc_otwc_pad;
static u32 re4dc_otwc_pad_prev, re4dc_otwc_pad_reports, re4dc_otwc_pad_owner;
static const u32 kOtwcPadWords = 1024, kOtwcPadFill = 0xA5A5A5A5u;
static void re4dc_otwc_pad_fill(u32* pad)
{
    re4dc_otwc_pad = pad;
    re4dc_otwc_pad_owner = (u32) pG->prim_cnt;   // a room's new primitive buffer drops the old pad unchecked
    for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;
}
// A checkpoint: `where` (a caller address) is the code about to run; the previous checkpoint ran before the write.
extern "C" void re4dc_otwc_pad_check(u32 where)
{
    u32* pad = re4dc_otwc_pad;
    if (!pad) return;
    if ((u32) pG->prim_cnt != re4dc_otwc_pad_owner) { re4dc_otwc_pad = 0; return; }
    u32 first = kOtwcPadWords;
    for (u32 i = 0; i < kOtwcPadWords; i++) if (pad[i] != kOtwcPadFill) { first = i; break; }
    if (first < kOtwcPadWords) {
        if (re4dc_otwc_pad_reports++ < 8) {
            u32 n = 0, last = first;
            for (u32 i = first; i < kOtwcPadWords; i++) if (pad[i] != kOtwcPadFill) { n++; last = i; }
            re4dc_log("OTWC pad write: frame %u room %03x %u words %08x..%08x between checkpoint %08x and %08x\n",
                      (unsigned) pG->Frame_cnt, (unsigned) pG->room_id, (unsigned) n, (unsigned) (u32) (pad + first),
                      (unsigned) (u32) (pad + last), (unsigned) re4dc_otwc_pad_prev, (unsigned) where);
            for (u32 i = first & ~7u; i <= last && i < kOtwcPadWords; i += 8) {
                re4dc_log("OTWC   %08x: %08x %08x %08x %08x %08x %08x %08x %08x\n", (unsigned) (u32) (pad + i),
                          pad[i], pad[i + 1], pad[i + 2], pad[i + 3], pad[i + 4], pad[i + 5], pad[i + 6], pad[i + 7]);
            }
        }
        for (u32 i = 0; i < kOtwcPadWords; i++) pad[i] = kOtwcPadFill;
    }
    re4dc_otwc_pad_prev = where;
}
#endif
static inline void re4dc_prim_tag(const void* a, u32 size, u32 caller)
{
    Re4dcPrimTag& t = re4dc_prim_tags[re4dc_prim_tag_n++ & 2047];
    t.addr = (u32) a; t.size = size; t.frame = pG->Frame_cnt; t.caller = caller;
}
#endif
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
extern "C" void re4dc_actor_skin_retire_pending();
#endif
void SetPrimBuffPtr()
{
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    re4dc_actor_skin_retire_pending();
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER || RE4DC_PS2_WORLD_R11F_OWNER
    ++sourceWorldPrimGeneration; // invalidates even same-frame/address reuse
#endif
#if RE4DC_COARSE_SOURCE_ACTORS
    sourceActorRetire(); // before even the no-buffer return or any storage reuse
#endif
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    re4dc_actor_skin_recipe_retire(); // also when prim_cnt==0 or Frame_cnt is unchanged
#endif
    GxWork* gx = GXWORK();

    if (pG->prim_cnt == 0) {
        return;
    }
#if RE4DC_PRIM_WATER
    primWaterFrame();
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_PRIMITIVE_BUFFERS == 1
    // Render() has consumed the old OT and its source arrays synchronously.
    // Preserve the full per-frame capacity; reuse only the dead frame's bytes.
    U32Set(pG->vtx_buf_no, 0);
#else
    U32Set(pG->vtx_buf_no, pG->vtx_buf_no ^ 1);
#endif
    gx->prim = (u8*) pG->prim_cnt + pG->nPrim * pG->vtx_buf_no;
#if RE4DC_PRIM_WATER
    primw_start = gx->prim;
#endif
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
#if RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check((u32) __builtin_return_address(0));
    re4dc_otwc_pad_fill((u32*) gx->prim);
    gx->prim += kOtwcPadWords * 4;
#endif
    re4dc_prim_tag(gx->prim, 0, pG->nPrim | (u32) pG->vtx_buf_no << 31);
#endif
}

#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
static unsigned skin_recipe_credit=0;
extern "C" unsigned re4dc_prim_recipe_credit(){return skin_recipe_credit;}
extern "C" unsigned re4dc_prim_recipe_frame(){return pG->Frame_cnt;}
extern "C" void re4dc_prim_recipe_retire_credit(){skin_recipe_credit=0;}
static bool re4dc_prim_recipe_room(unsigned* available) {
    const u8* base=(const u8*)pG->prim_cnt;
    if(!available || PTR_INVALID(base) || pG->vtx_buf_no>1 ||
       pG->nPrim>~0u/(pG->vtx_buf_no+1u))return false;
    const std::uintptr_t begin=reinterpret_cast<std::uintptr_t>(base);
    const unsigned span=pG->nPrim*(pG->vtx_buf_no+1u);
    if(begin>~std::uintptr_t(0)-span)return false;
    const std::uintptr_t end=begin+span;
    const std::uintptr_t at=reinterpret_cast<std::uintptr_t>(GXWORK()->prim);
    if(at<begin || at>end)return false;
    *available=unsigned(end-at);
    return true;
}
extern "C" int re4dc_prim_recipe_release(unsigned bytes) {
    if(!bytes || (bytes&31u) || bytes>skin_recipe_credit)return 0;
    skin_recipe_credit-=bytes;return 1;
}
// One non-yielding claim transfers an old pending row's credit or adds a
// descriptor. The admission margin is checked here only; later allocations
// protect the hard palette credit without charging another 16 KiB per row.
extern "C" int re4dc_prim_recipe_claim(unsigned descriptor,unsigned old_credit,
                                        unsigned new_credit,void** allocation) {
    if(!allocation || (descriptor&31u) || (old_credit&31u) || (new_credit&31u) ||
       old_credit>skin_recipe_credit || !new_credit)return 0;
    unsigned room=0;
    if(!re4dc_prim_recipe_room(&room) || skin_recipe_credit-old_credit>~0u-new_credit)return 0;
    const unsigned total=skin_recipe_credit-old_credit+new_credit;
    if(room<descriptor || room-descriptor<total ||
       room-descriptor-total<16u*1024u)return 0;
    GxWork* gx=GXWORK();*allocation=gx->prim;
    gx->prim+=descriptor;skin_recipe_credit=total;
    return 1;
}
#endif
// Allocates `size` bytes (32-byte aligned) from this frame's primitive buffer; 0 when exhausted.
void* GetPrimBuff(int size)
{
    GxWork* gx = GXWORK();
    u8* base = (u8*) pG->prim_cnt;
#if !defined(RE4DC_SKIN_RECIPE32) || !RE4DC_SKIN_RECIPE32
    u8* limit;
#endif
    u8* p;
    u8* next;

    if (PTR_INVALID(base)) {
        pLog->err(0, 0, "GetPrimBuff() PTR ERR %08X", base);
        return 0;
    }
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    unsigned room=0;
    if(size<0 || size>0x7fffffff-31 || !re4dc_prim_recipe_room(&room)) {
#if RE4DC_PRIM_WATER
        ++primw_overflow;
#endif
        pLog->err(0, 0, "GetPrimBuff() : OVERFLOW");
        return 0;
    }
#else
    limit = base + pG->nPrim * (pG->vtx_buf_no + 1);
#endif
    size = (size + 0x1F) / 32 * 32;
    p = gx->prim;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(unsigned(size)>room || skin_recipe_credit>room-unsigned(size)) {
#else
    next = p + size;
    if (limit < next) {
#endif
#if RE4DC_PRIM_WATER
        ++primw_overflow;
#endif
        pLog->err(0, 0, "GetPrimBuff() : OVERFLOW");
        return 0;
    }
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    next=p+size;
#endif
    gx->prim = next;
#if defined(RE4DC_OT_WALK_CHECK) && RE4DC_OT_WALK_CHECK
#if RE4DC_OT_WALK_CHECK >= 2
    re4dc_otwc_pad_check((u32) __builtin_return_address(0));
#endif
    re4dc_prim_tag(p, (u32) size, (u32) __builtin_return_address(0));
#endif
    return p;
}

#if defined(RE4DC_GAME) && !defined(__PPC__)
// Native actor scratch (render-only, D367 PROPOSAL option A): the unused tail
// of this frame's primitive buffer, requested during Render() after Trans()
// finished filling it. Taken only when `reserve` bytes remain afterwards, so
// it never triggers GetPrimBuff's OVERFLOW report. D358: 37% peak use of 312 KiB.
extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve)
{
#if !defined(RE4DC_SKIN_RECIPE32) || !RE4DC_SKIN_RECIPE32
    GxWork* gx = GXWORK();
#endif
    u8* base = (u8*) pG->prim_cnt;
    if (PTR_INVALID(base)) {
        return 0;
    }
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    unsigned room=0;
    if(bytes>~0u-31u || !re4dc_prim_recipe_room(&room))return 0;
#else
    u8* limit = base + pG->nPrim * (pG->vtx_buf_no + 1);
#endif
    u32 size = (bytes + 0x1F) / 32 * 32;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if(size>0x7fffffffu || size>room || reserve>room-size ||
       skin_recipe_credit>room-size-reserve) {
#else
    if (gx->prim + size + reserve > limit) {
#endif
#if RE4DC_PRIM_WATER
        ++primw_declined;
#endif
        return 0;
    }
#if RE4DC_PRIM_WATER
    primw_tail += size;
#endif
    return GetPrimBuff(size);
}
#endif

// Resets the TEV / indirect / texgen state and the allocation counters (tev_stage, tev_reg,
// tex_coord, tex_map, tev_kcolor) between models.
void shaderReset()
{
    if (IND_STAGE_ID() != 0) {
        GXSetNumIndStages(0);
        GXSetTevDirect(0);
        GXSetTevDirect(1);
        GXSetTevDirect(2);
        GXSetTevDirect(3);
        GXSetTevDirect(4);
        GXSetTevDirect(5);
        GXSetTevDirect(6);
        GXSetTevDirect(7);
        GXSetTevDirect(8);
        GXSetTevDirect(9);
        GXSetTevDirect(10);
        GXSetTevDirect(11);
        GXSetTevDirect(12);
        GXSetTevDirect(13);
        GXSetTevDirect(14);
        GXSetTevDirect(15);
    }
    GXSetChanCtrl(0, 0, 0, 0, 0, 0, 2);
    GXSetChanCtrl(1, 0, 0, 0, 0, 0, 2);
    GXSetAlphaCompare(7, 0, 1, 7, 0);
}

// Dead-stripped in the DOL (STRIP_UNUSED): only its constant pool (0.0, 448.0, 1.0 and the signed
// int -> float double) remains in .rodata between GetPrimBuff and updateMatrices.
static void primBuffDebugDisp(int n)
{
    f32 zero = 0.0f;
    f32 h = 448.0f;
    f32 one = 1.0f;
    GXSetViewport(zero, zero, h, one, (f32) n, one);
}

// Skin `n` vertices (s16 x/y/z + s16 matrix index, 8 bytes) from src into dst (s16 x/y/z, 6 bytes)
// with the matrix palette in locked cache (0xE0000000, ROMtx 0x30 each). GQR6 holds the fixed point scale.
#if defined(__PPC__)
static void CalcSk1_x(void* dst, void* src, u32 n)
{
    asm volatile(
        "lha 9, 6(4)\n"
        "subi 3, 3, 6\n"
        "li 0, 0\n"
        "subi 4, 4, 8\n"
        "mulli 9, 9, 0x30\n"
        "addis 9, 9, 0xE000\n"
        "mtctr 5\n"
        "1:\n"
        "psq_l 0, 0(9), 0, 0\n"
        "psq_l 1, 8(9), 1, 0\n"
        "psq_l 2, 0xc(9), 0, 0\n"
        "psq_l 3, 0x14(9), 1, 0\n"
        "psq_l 4, 0x18(9), 0, 0\n"
        "psq_l 5, 0x20(9), 1, 0\n"
        "psq_l 6, 0x24(9), 0, 0\n"
        "psq_l 7, 0x2c(9), 1, 0\n"
        "psq_lu 8, 8(4), 0, 6\n"
        "psq_l 9, 4(4), 1, 6\n"
        "ps_madds0 12, 0, 8, 6\n"
        "ps_madds0 13, 1, 8, 7\n"
        "ps_madds1 12, 2, 8, 12\n"
        "ps_madds1 13, 3, 8, 13\n"
        "ps_madds0 12, 4, 9, 12\n"
        "ps_madds0 13, 5, 9, 13\n"
        "psq_stu 12, 6(3), 0, 6\n"
        "psq_st 13, 4(3), 1, 6\n"
        "lha 9, 0xe(4)\n"
        "mulli 9, 9, 0x30\n"
        "addis 9, 9, 0xE000\n"
        "bdnz 1b\n");
}

// Same for s8 normals (s8 x/y/z + u8 matrix index, 4 bytes) into s8 x/y/z (3 bytes).
static void CalcSk1_x2(void* dst, void* src, u32 n)
{
    asm volatile(
        "lbz 9, 3(4)\n"
        "subi 3, 3, 3\n"
        "li 0, 0\n"
        "subi 4, 4, 4\n"
        "mulli 9, 9, 0x30\n"
        "addis 9, 9, 0xE000\n"
        "mtctr 5\n"
        "1:\n"
        "psq_l 0, 0(9), 0, 0\n"
        "psq_l 1, 8(9), 1, 0\n"
        "psq_l 2, 0xc(9), 0, 0\n"
        "psq_l 3, 0x14(9), 1, 0\n"
        "psq_l 4, 0x18(9), 0, 0\n"
        "psq_l 5, 0x20(9), 1, 0\n"
        "psq_l 6, 0x24(9), 0, 0\n"
        "psq_l 7, 0x2c(9), 1, 0\n"
        "psq_lu 8, 4(4), 0, 6\n"
        "psq_l 9, 2(4), 1, 6\n"
        "ps_madds0 12, 0, 8, 6\n"
        "ps_madds0 13, 1, 8, 7\n"
        "ps_madds1 12, 2, 8, 12\n"
        "ps_madds1 13, 3, 8, 13\n"
        "ps_madds0 12, 4, 9, 12\n"
        "ps_madds0 13, 5, 9, 13\n"
        "psq_stu 12, 3(3), 0, 6\n"
        "psq_st 13, 2(3), 1, 6\n"
        "lbz 9, 7(4)\n"
        "mulli 9, 9, 0x30\n"
        "addis 9, 9, 0xE000\n"
        "bdnz 1b\n");
}

// Sets GQR6 (the paired-single quantisation register the skinning loads use).
void setupGQR6(u32 v)
{
    asm volatile("mtspr 918, %0" : : "r"(v));
}

#else
// Off PowerPC the same loops in C. GQR6 is modelled: its load half dequantises the
// s16/s8 input (x 2^-scale), its store half quantises the result (x 2^scale, truncated
// toward zero and saturated, as the paired-single store does). Both halves use the same
// scale here, so the rotation part is exact fixed point and only the translation row is
// scaled; the normal passes set a large negative scale so that row vanishes (0x32073207,
// 0x20062006), exactly as on the Gekko.
static u32 g_gqr6;
#if RE4DC_NATIVE_ACTOR_SKIN
static u32 g_skin_palette;  // nonzero: re4dc_skin_materialize()'s saved palette
#define RE4DC_SKIN_PALETTE (g_skin_palette ? g_skin_palette : RE4DC_LC_PALETTE)
#else
#define RE4DC_SKIN_PALETTE RE4DC_LC_PALETTE
#endif

static inline f32 gqrScale(u32 field)  // 6-bit two's-complement scale field -> 2^-scale
{
    int sc = (int) ((field >> 8) & 0x3F);
    if (sc & 0x20) {
        sc -= 64;
    }
    return __builtin_ldexpf(1.0f, -sc);
}

static inline s32 psQuant(f32 v, s32 lo, s32 hi)
{
    if (v >= (f32) hi) {
        return hi;
    }
    if (v <= (f32) lo) {
        return lo;
    }
    return (s32) v;  // C truncation == round toward zero
}

#if RE4DC_SK1_ASM
// GAME_SK1_ASM (game30.mk; render only, exact): the two loops below in platform/sk1_sh4.S (same
// operations, the three components interleaved, psQuant as ftrc + an integer range test). =2 (check
// build): the C loop re-runs into locals and compares every component ("SK1" lines).
extern "C" void re4dc_sk1_s16(s16* dst, const s16* src, u32 n, const f32* pal, f32 ls, f32 ss);
extern "C" void re4dc_sk1_s8(s8* dst, const s8* src, u32 n, const f32* pal, f32 ls, f32 ss);
#if RE4DC_SK1_ASM == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 sk1_calls, sk1_words, sk1_bad, sk1_inplace, sk1_skipped;
static void sk1_note(u32 words, u32 bad)
{
    sk1_words += words;
    sk1_bad += bad;
    if ((++sk1_calls & 1023) == 0) {
        re4dc_log("SK1 calls=%u words=%u mismatch=%u inplace=%u skipped=%u\n", sk1_calls, sk1_words, sk1_bad,
                  sk1_inplace, sk1_skipped);
    }
}
// Morphed infos skin in place (src = pPosBuf = dst): the check compares against a copy of the source.
static u8 sk1_src_copy[64 * 1024] __attribute__((aligned(8)));
static const void* sk1_source(const void* src, const void* dst, u32 bytes, u32 dbytes)
{
    const u8* s = (const u8*) src;
    const u8* d = (const u8*) dst;
    if (s + bytes <= d || d + dbytes <= s) {
        return src;
    }
    ++sk1_inplace;
    if (bytes > sizeof(sk1_src_copy)) {
        ++sk1_skipped;
        return nullptr;
    }
    memcpy(sk1_src_copy, src, bytes);
    return sk1_src_copy;
}
#endif
#endif

static void CalcSk1_x(void* dst, void* src, u32 n)
{
    s16* d = (s16*) dst;
    const s16* s = (const s16*) src;
    const f32 ls = gqrScale(g_gqr6 >> 16);
    const f32 ss = 1.0f / gqrScale(g_gqr6 & 0xFFFF);
#if RE4DC_SK1_ASM
#if RE4DC_SK1_ASM == 2
    const s16* s_check = (const s16*) sk1_source(s, d, n * 8, n * 6);
#endif
    re4dc_sk1_s16(d, s, n, (const f32*) RE4DC_SKIN_PALETTE, ls, ss);
#if RE4DC_SK1_ASM == 2
    if (!s_check) {
        return;
    }
    s = s_check;
    u32 bad = 0;
    for (u32 i = 0; i < n; i++, s += 4, d += 3) {
        const f32* m = (const f32*) (RE4DC_SKIN_PALETTE + (u32) ((s32) s[3] * 0x30));
        f32 x = (f32) s[0] * ls;
        f32 y = (f32) s[1] * ls;
        f32 z = (f32) s[2] * ls;
        f32 ox = x * m[0] + y * m[3] + z * m[6] + m[9];
        f32 oy = x * m[1] + y * m[4] + z * m[7] + m[10];
        f32 oz = x * m[2] + y * m[5] + z * m[8] + m[11];
        bad += d[0] != (s16) psQuant(ox * ss, -32768, 32767);
        bad += d[1] != (s16) psQuant(oy * ss, -32768, 32767);
        bad += d[2] != (s16) psQuant(oz * ss, -32768, 32767);
    }
    sk1_note(n * 3, bad);
#endif
    return;
#endif
    for (u32 i = 0; i < n; i++, s += 4, d += 3) {
        const f32* m = (const f32*) (RE4DC_SKIN_PALETTE + (u32) ((s32) s[3] * 0x30));
        f32 x = (f32) s[0] * ls;
        f32 y = (f32) s[1] * ls;
        f32 z = (f32) s[2] * ls;
        f32 ox = x * m[0] + y * m[3] + z * m[6] + m[9];
        f32 oy = x * m[1] + y * m[4] + z * m[7] + m[10];
        f32 oz = x * m[2] + y * m[5] + z * m[8] + m[11];
        d[0] = (s16) psQuant(ox * ss, -32768, 32767);
        d[1] = (s16) psQuant(oy * ss, -32768, 32767);
        d[2] = (s16) psQuant(oz * ss, -32768, 32767);
    }
}

static void CalcSk1_x2(void* dst, void* src, u32 n)
{
    s8* d = (s8*) dst;
    const s8* s = (const s8*) src;
    const f32 ls = gqrScale(g_gqr6 >> 16);
    const f32 ss = 1.0f / gqrScale(g_gqr6 & 0xFFFF);
#if RE4DC_SK1_ASM
#if RE4DC_SK1_ASM == 2
    const s8* s_check = (const s8*) sk1_source(s, d, n * 4, n * 3);
#endif
    re4dc_sk1_s8(d, s, n, (const f32*) RE4DC_SKIN_PALETTE, ls, ss);
#if RE4DC_SK1_ASM == 2
    if (!s_check) {
        return;
    }
    s = s_check;
    u32 bad = 0;
    for (u32 i = 0; i < n; i++, s += 4, d += 3) {
        const f32* m = (const f32*) (RE4DC_SKIN_PALETTE + (u32) ((u8) s[3] * 0x30));
        f32 x = (f32) s[0] * ls;
        f32 y = (f32) s[1] * ls;
        f32 z = (f32) s[2] * ls;
        f32 ox = x * m[0] + y * m[3] + z * m[6] + m[9];
        f32 oy = x * m[1] + y * m[4] + z * m[7] + m[10];
        f32 oz = x * m[2] + y * m[5] + z * m[8] + m[11];
        bad += d[0] != (s8) psQuant(ox * ss, -128, 127);
        bad += d[1] != (s8) psQuant(oy * ss, -128, 127);
        bad += d[2] != (s8) psQuant(oz * ss, -128, 127);
    }
    sk1_note(n * 3, bad);
#endif
    return;
#endif
    for (u32 i = 0; i < n; i++, s += 4, d += 3) {
        const f32* m = (const f32*) (RE4DC_SKIN_PALETTE + (u32) ((u8) s[3] * 0x30));
        f32 x = (f32) s[0] * ls;
        f32 y = (f32) s[1] * ls;
        f32 z = (f32) s[2] * ls;
        f32 ox = x * m[0] + y * m[3] + z * m[6] + m[9];
        f32 oy = x * m[1] + y * m[4] + z * m[7] + m[10];
        f32 oz = x * m[2] + y * m[5] + z * m[8] + m[11];
        d[0] = (s8) psQuant(ox * ss, -128, 127);
        d[1] = (s8) psQuant(oy * ss, -128, 127);
        d[2] = (s8) psQuant(oz * ss, -128, 127);
    }
}

void setupGQR6(u32 v)
{
    g_gqr6 = v;
}

#if RE4DC_NATIVE_ACTOR_SKIN
#include "native_actor.hpp"
// D367 actors30 (NATIVE_ACTOR_SKIN). Trans(): keep a copy of the weight
// palette MakeWeightPalette just built (primitive buffer, same lifetime as
// pPosBuf) and register it with the native actor path, which then skins
// this info at draw time. Space is taken only with 64 KiB left afterwards,
// so the source's own allocations never reach GetPrimBuff's OVERFLOW.
extern "C" void* re4dc_prim_tail(unsigned bytes, unsigned reserve);
int re4dc_skin_defer(cModelInfo* info, ModelData* d)
{
    const u32 n = d->weight_ext_num > 0xFF ? d->weight_ext_num : d->weight_palette_num;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (n > (0x7FFFFFFFu - 31u) / 48u) return 0;
#endif
    if (!n || !re4dc_model_diagnostic_enabled()) {
        return 0;
    }
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    Re4dcActorSkinAdmission admission{};
    if (!re4dc_actor_skin_admit(pG->Frame_cnt, info, info->pPosBuf[pG->vtx_buf_no], n, &admission)) return 0;
#endif
    void* copy = re4dc_prim_tail(n * 0x30, 64 * 1024);
    if (!copy) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
        re4dc_actor_skin_cancel(&admission);
#endif
        return 0;
    }
    memcpy(copy, (const void*) RE4DC_LC_PALETTE, n * 0x30);
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    return re4dc_actor_skin_commit(&admission, (const float*) copy);
#else
    return re4dc_actor_skin_register(pG->Frame_cnt, info, info->pPosBuf[pG->vtx_buf_no], (const float*) copy, n);
#endif
}

#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
// NATIVE_ACTOR_SKIN_LAZY: as above, before Trans() allocates the info's
// arrays; the registration key is (info, NULL) and pPosBuf/pNrmBuf stay NULL.
// 16 KiB must remain after the palette copy (the actor workspace reserve).
int re4dc_skin_defer_lazy(cModelInfo* info, ModelData* d)
{
    const u32 n = d->weight_ext_num > 0xFF ? d->weight_ext_num : d->weight_palette_num;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (n > (0x7FFFFFFFu - 31u) / 48u) return 0;
#endif
    if (!n || !re4dc_model_diagnostic_enabled()) {
        return 0;
    }
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    Re4dcActorSkinAdmission admission{};
    if (!re4dc_actor_skin_admit(pG->Frame_cnt, info, 0, n, &admission)) return 0;
#endif
    void* copy = re4dc_prim_tail(n * 0x30, 16 * 1024);
    if (!copy) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
        re4dc_actor_skin_cancel(&admission);
#endif
        return 0;
    }
    memcpy(copy, (const void*) RE4DC_LC_PALETTE, n * 0x30);
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    return re4dc_actor_skin_commit(&admission, (const float*) copy);
#else
    return re4dc_actor_skin_register(pG->Frame_cnt, info, 0, (const float*) copy, n);
#endif
}

#if RE4DC_SKIN_PALETTE_LAZY
// SKIN_PALETTE_LAZY: a reserved, not yet built copy starts with this header (the copy is n * 0x30 >= 48 bytes and
// nothing reads it before re4dc_skin_palette_resolve, whose build overwrites the header). The magic is a NaN: no
// built palette (source, owner or coarse; their matrices are finite) starts with it. A resolve in a later game frame
// than its deferral would build from moved matrices (=2 counts such "stale" resolves: 0 in every run).
struct SkinLazyHead {
    u32 magic;   // kSkinLazyMagic
    u32 frame;   // pG->Frame_cnt at the deferral
    cModel* m;   // whose parts matrices (calcWeightMat) the palette is built from
    void* w;     // ModelData::pWeight
    u32 n_ext;   // entries | 0x10000 for a WeightExt table (weight_ext_num > 0xFF)
};
static const u32 kSkinLazyMagic = 0x7FA5E1A5u;
#if RE4DC_SKIN_PALETTE_LAZY == 2
// Check build: the copy holds the eager palette (drawn); this frame's deferrals are kept in a table instead.
extern "C" void re4dc_log(const char* fmt, ...);
struct SkinLazyChk {
    const void* palette;
    SkinLazyHead h;
    u32 open;
};
static SkinLazyChk g_sklzTab[128];
static u32 g_sklzNum, g_sklzOpen, g_sklzFrame;
static u32 sklz_reg, sklz_res, sklz_never, sklz_bad, sklz_badw, sklz_stale, sklz_full, sklz_mtx, sklz_f0;
#endif

// Trans()'s palette of weights w (n entries) from the parts matrices in pG->mtxPalette, into dst: the same
// MakeWeightPalette* (GAME_WPAL_FAST=3: its re4dc_wpal_sh4 straight into dst; otherwise the locked cache + copy).
static void skinLazyBuild(void* w, u32 n, int ext, void* dst)
{
    if (ext) {
        MakeWeightPaletteExt((WeightExt*) w, n);
    } else {
#if RE4DC_WPAL_FAST == 3
        if (!PTR_INVALID(w)) {
            re4dc_wpal_sh4((const Weight*) w, n, (const f32*) GXWORK()->mtx, (f32*) dst);
            return;
        }
#endif
        MakeWeightPalette((Weight*) w, n);
    }
    if (dst != (void*) RE4DC_LC_PALETTE) {
        memcpy(dst, (const void*) RE4DC_LC_PALETTE, n * 0x30);
    }
}

// re4dc_skin_defer_lazy's checks, allocation and registration, without the build (the copy holds a SkinLazyHead
// until re4dc_skin_palette_resolve). 0: not deferred (nothing built; the caller's CPU pass builds the palette).
static int skinDeferPending(cModel* m, cModelInfo* info, ModelData* d, int* mtxBuilt)
{
    const u32 n = d->weight_ext_num > 0xFF ? d->weight_ext_num : d->weight_palette_num;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    if (n > 0xFFFFu) return 0; // SkinLazyHead captures the count in its low half.
#endif
    if (!n || !re4dc_model_diagnostic_enabled()) {
        return 0;
    }
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    Re4dcActorSkinAdmission admission{};
    if (!re4dc_actor_skin_admit(pG->Frame_cnt, info, 0, n, &admission)) return 0;
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
    const unsigned n_ext=n|(d->weight_ext_num>0xFF?0x10000u:0u);
    const int recipe=re4dc_actor_skin_recipe_claim(&admission,m,d->pWeight,n_ext);
    if(recipe) {
        if(recipe<0)re4dc_actor_skin_cancel(&admission);
        return recipe>0;
    }
#endif
#endif
    void* copy = re4dc_prim_tail(n * 0x30, 16 * 1024);
    if (!copy) {
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
        re4dc_actor_skin_cancel(&admission);
#endif
        return 0;
    }
    SkinLazyHead h;
    h.magic = kSkinLazyMagic;
    h.frame = pG->Frame_cnt;
    h.m = m;
    h.w = d->pWeight;
    h.n_ext = n | (d->weight_ext_num > 0xFF ? 0x10000u : 0u);
#if RE4DC_SKIN_PALETTE_LAZY == 2
    SKIN_LAZY_MTX(m, *mtxBuilt)
    skinLazyBuild(d->pWeight, n, h.n_ext >> 16, copy);
    if (g_sklzFrame != pG->Frame_cnt + 1) {
        sklz_never += g_sklzOpen;
        if (pG->Frame_cnt - sklz_f0 >= 600) {
            re4dc_log("SKLAZY frame=%u reg=%u resolved=%u never=%u bad=%u badw=%u stale=%u full=%u mtx=%u\n",
                      pG->Frame_cnt, sklz_reg, sklz_res, sklz_never, sklz_bad, sklz_badw, sklz_stale, sklz_full,
                      sklz_mtx);
            sklz_f0 = pG->Frame_cnt;
        }
        g_sklzFrame = pG->Frame_cnt + 1;
        g_sklzNum = 0;
        g_sklzOpen = 0;
    }
#else
    (void) mtxBuilt;
    memcpy(copy, &h, sizeof(h));
#endif
#if defined(RE4DC_SKIN_ADMISSION32) && RE4DC_SKIN_ADMISSION32
    if (!re4dc_actor_skin_commit(&admission, (const float*) copy)) {
#else
    if (!re4dc_actor_skin_register(pG->Frame_cnt, info, 0, (const float*) copy, n)) {
#endif
        return 0;
    }
#if RE4DC_SKIN_PALETTE_LAZY == 2
    ++sklz_reg;
    if (g_sklzNum < sizeof(g_sklzTab) / sizeof(g_sklzTab[0])) {
        SkinLazyChk* e = &g_sklzTab[g_sklzNum++];
        e->palette = copy;
        e->h = h;
        e->open = 1;
        ++g_sklzOpen;
    } else {
        ++sklz_full;
    }
#endif
    return 1;
}

// A render consumer is about to read `palette`: build it now if it is a pending SKIN_PALETTE_LAZY copy. The parts
// matrices of one model are built once per game frame for its resolves; any other calcWeightMat clears the memo.
extern "C" void re4dc_skin_palette_resolve(const float* palette)
{
    SkinLazyHead h;
#if RE4DC_SKIN_PALETTE_LAZY == 2
    SkinLazyChk* e = 0;
    if (!g_sklzOpen) {
        return;
    }
    for (u32 i = 0; i < g_sklzNum; i++) {
        if (g_sklzTab[i].palette == (const void*) palette && g_sklzTab[i].open) {
            e = &g_sklzTab[i];
            break;
        }
    }
    if (!e) {
        return;
    }
    e->open = 0;
    --g_sklzOpen;
    h = e->h;
    ++sklz_res;
    if (h.frame != pG->Frame_cnt) {
        ++sklz_stale;
    }
#else
    if (!palette || *(const u32*) palette != kSkinLazyMagic) {
        return;
    }
    memcpy(&h, palette, sizeof(h));  // a header of another frame (=2: stale=0) is built too, never read raw
#endif
    if (g_skinLazyMtx != h.m || g_skinLazyMtxFrame != pG->Frame_cnt) {
        calcWeightMat(h.m);
        g_skinLazyMtx = h.m;
        g_skinLazyMtxFrame = pG->Frame_cnt;
#if RE4DC_SKIN_PALETTE_LAZY == 2
        ++sklz_mtx;
#endif
    }
#if RE4DC_SKIN_PALETTE_LAZY == 2
    skinLazyBuild(h.w, h.n_ext & 0xFFFF, h.n_ext >> 16, (void*) RE4DC_LC_PALETTE);
    {
        const u32* a = (const u32*) RE4DC_LC_PALETTE;
        const u32* b = (const u32*) palette;
        u32 bad = 0;
        for (u32 k = 0; k < (h.n_ext & 0xFFFF) * 12; k++) {
            bad += a[k] != b[k];
        }
        sklz_badw += bad;
        sklz_bad += bad != 0;
    }
#else
    skinLazyBuild(h.w, h.n_ext & 0xFFFF, h.n_ext >> 16, (void*) palette);
#endif
}
#if defined(RE4DC_SKIN_RECIPE32) && RE4DC_SKIN_RECIPE32
extern "C" const float* re4dc_skin_recipe_materialize(const void* model,const void* weight,
                                                       unsigned n_ext,unsigned frame,unsigned bytes) {
    if(!model || !weight || !bytes || (bytes&31u) ||
       !re4dc_prim_recipe_release(bytes))return nullptr;
    // The reserved credit was removed immediately before the exact allocation.
    // GetPrimBuff still protects every other live recipe's credit.
    void* copy=GetPrimBuff(int(bytes));
    if(!copy) {
        skin_recipe_credit+=bytes;
        return nullptr;
    }
    SkinLazyHead h;
    h.magic=kSkinLazyMagic;h.frame=frame;
    h.m=(cModel*)model;h.w=const_cast<void*>(weight);h.n_ext=n_ext;
    memcpy(copy,&h,sizeof(h));
    re4dc_skin_palette_resolve((const float*)copy);
    return (const float*)copy;
}
#endif
#if RE4DC_LEON_FACE_LAZY
// LEON_FACE_LAZY's pending job (see the knob note at the top of this file).
static struct {
    cModelInfo* info;  // the deferred face info (0: none)
    cModel* m;         // its model: calcWeightMat's parts matrices
    void* pos;         // its pPosBuf at the deferral (the morphed source until resolved)
    u32 frame;         // pG->Frame_cnt at the deferral
} g_faceLazy;

// commonScreenMatSub, right after the info's two arrays were allocated: 1 = morphed and deferred (GQR6 as the eager
// pass leaves it), 0 = not deferred (the eager pass runs), -1 = the eager pass's PTR ERR return (logged as there).
static int faceLazyDefer(cModel* m, cModelInfo* info, ModelData* d)
{
    if (g_faceLazy.info == info) {
        g_faceLazy.info = 0;  // an unresolved job of this info's previous ModelTrans: its arrays are not current
    }
    if (!g_skinLazyNow || m->id != 0 || (g_faceLazy.info && g_faceLazy.frame == pG->Frame_cnt)) {
        return 0;
    }
    void* src = info->pPosBuf[pG->vtx_buf_no];
    for (int i = 0; i < 5; i++) {
        if (i == 0) {
            ResetShape(info, src);
        }
        if (info->shape[i].data) {
            CalculateShape_new(info, info->shape[i].data, info->shape[i].rate, (u8*) src);
        }
    }
    if (PTR_INVALID(info->pPosBuf[pG->vtx_buf_no]) || PTR_INVALID(src)) {
        pLog->err(0, 0, "ComnScreenMatSub() PTR ERR");
        return -1;
    }
    g_faceLazy.info = info;
    g_faceLazy.m = m;
    g_faceLazy.pos = src;
    g_faceLazy.frame = pG->Frame_cnt;
#if defined(__sh__) && RE4DC_D349_RENDERER_STACK
    re4dc_model_skipped_writeback(d->nVtx * 6);
    re4dc_model_skipped_writeback(d->nNrm * 6);
#endif
    setupGQR6(0x32073207);
    if (d->flags & 0x20000000) {
        setupGQR6(0x20062006);
    }
    return 1;
}

// A render read of info's pPosBuf / pNrmBuf follows: build them now if they are the pending face job's (the eager
// pass's palette, positions and normals; GQR6 restored).
extern "C" void re4dc_face_lazy_resolve(const void* info_ptr)
{
    cModelInfo* info = (cModelInfo*) info_ptr;
    if (!info || info != g_faceLazy.info || g_faceLazy.pos != info->pPosBuf[pG->vtx_buf_no]) {
        return;
    }
    g_faceLazy.info = 0;
    cModel* m = g_faceLazy.m;
    ModelData* d = info->pData;
    const u32 saved = g_gqr6;
    if (g_skinLazyMtx != m || g_skinLazyMtxFrame != pG->Frame_cnt) {
        calcWeightMat(m);
        g_skinLazyMtx = m;
        g_skinLazyMtxFrame = pG->Frame_cnt;
    }
    if (d->weight_ext_num > 0xFF) {
        MakeWeightPaletteExt((WeightExt*) d->pWeight, d->weight_ext_num);
    } else {
        MakeWeightPalette((Weight*) d->pWeight, d->weight_palette_num);
    }
    setupGQR6(((d->shift << 24) | (d->shift << 8)) | 0x00070007);
    CalcSk1_x(info->pPosBuf[pG->vtx_buf_no], info->pPosBuf[pG->vtx_buf_no], d->nVtx);
#if !defined(__sh__) || !RE4DC_D349_RENDERER_STACK
    DCStoreRangeNoSync(info->pPosBuf[pG->vtx_buf_no], d->nVtx * 6);
#endif
    setupGQR6(0x32073207);
    if (d->flags & 0x20000000) {
        setupGQR6(0x20062006);
        CalcSk1_x2(info->pNrmBuf[pG->vtx_buf_no], d->nrmOrig, d->nNrm);
    } else {
        CalcSk1_x(info->pNrmBuf[pG->vtx_buf_no], d->nrmOrig, d->nNrm);
    }
#if !defined(__sh__) || !RE4DC_D349_RENDERER_STACK
    DCStoreRangeNoSync(info->pNrmBuf[pG->vtx_buf_no], d->nNrm * 6);
#endif
    g_gqr6 = saved;
}
#endif
#endif
#endif

// Render(): the generic path needs this info's pPosBuf/pNrmBuf after all.
// The source's own CalcSk1_x/_x2 from the saved palette, into the buffers
// Trans() allocated; the locked cache and GQR6 state are left untouched.
// NATIVE_ACTOR_SKIN_LAZY: a NULL pPosBuf is allocated here first (primitive
// buffer, same lifetime; no allocation -> 0 and the part is not drawn).
extern "C" int re4dc_skin_materialize(const void* info_ptr, const float* palette)
{
    cModelInfo* info = (cModelInfo*) info_ptr;
    ModelData* d = info->pData;
#if RE4DC_SKIN_PALETTE_LAZY
    re4dc_skin_palette_resolve(palette);
#endif
#if RE4DC_NATIVE_ACTOR_SKIN_LAZY
    if (!info->pPosBuf[pG->vtx_buf_no]) {
        const u32 nb = (d->flags & 0x20000000) ? d->nNrm * 3 : d->nNrm * 6;
        void* pos = re4dc_prim_tail(d->nVtx * 6 + 31 + nb + 31, 0);
        if (!pos) {
            return 0;
        }
        info->pPosBuf[pG->vtx_buf_no] = pos;
        info->pNrmBuf[pG->vtx_buf_no] = (u8*) pos + ((d->nVtx * 6 + 31) & ~31U);
    }
#endif
    const u32 saved = g_gqr6;
    g_skin_palette = (u32) palette;
    setupGQR6(((d->shift << 24) | (d->shift << 8)) | 0x00070007);
    CalcSk1_x(info->pPosBuf[pG->vtx_buf_no], d->vtxOrig, d->nVtx);
    setupGQR6(0x32073207);
    if (d->flags & 0x20000000) {
        setupGQR6(0x20062006);
        CalcSk1_x2(info->pNrmBuf[pG->vtx_buf_no], d->nrmOrig, d->nNrm);
    } else {
        CalcSk1_x(info->pNrmBuf[pG->vtx_buf_no], d->nrmOrig, d->nNrm);
    }
    g_skin_palette = 0;
    g_gqr6 = saved;
    return 1;
}
#endif

#endif

// Relocate a TPL whose texture headers also carry a CLUT (thermo palette).
void CalcTplAddrC8(TEXPalette* tpl)
{
    u32 i;

    if (tpl == 0) {
        return;
    }
    if ((s32) tpl->descriptorArray < 0) {
        return;
    }
#if RE4DC_FRONT_TPL_OWNER
    // The core/thermo palette can alias a room descendant even though the
    // palette itself lies outside the certified room. Revoke before touching
    // its texture and CLUT headers, as the model.cpp TPL writers do.
    re4dc_front_tpl_palette_changed(tpl);
#endif
    tpl->descriptorArray = (TEXDescriptor*) ((u32) tpl->descriptorArray + (u32) tpl);
    for (i = 0; i < tpl->numDescriptors; i++) {
        TEXDescriptor* td = &tpl->descriptorArray[i];
        td->textureHeader = (TEXHeader*) ((u32) tpl + (u32) td->textureHeader);
        td->textureHeader->data = (void*) ((u32) tpl + (u32) td->textureHeader->data);
        if (td->CLUTHeader != 0) {
            td->CLUTHeader = (CLUTHeader*) ((u32) tpl + (u32) td->CLUTHeader);
            td->CLUTHeader->data = (void*) ((u32) tpl + (u32) td->CLUTHeader->data);
        }
    }
}

// Boot (CoreDataRead): the specular environment textures, the two indirect ramp textures and the
// thermal palette from the core archive.
void SpecularInit(TEXPalette* spec, TEXPalette* ind, TEXPalette* ind2, TEXPalette* thermo)
{
    u32 i;
    u32 ns;
    u32 n;
    u32 n2;
    TEXDescriptor* td;
    TEXHeader* h;
    CLUTHeader* cl;

    calcTplAddr(spec);
    ns = spec->numDescriptors;
    for (i = 0; i < ns; i++) {
        td = TEXGet(spec, i);
        h = td->textureHeader;
        GXInitTexObj(&Specular[i], h->data, h->width, h->height, h->format, h->wrapS, h->wrapT, 0);
    }
    calcTplAddr(ind);
    n = ind->numDescriptors;
    for (i = 0; i < n; i++) {
        td = TEXGet(ind, i);
        h = td->textureHeader;
        GXInitTexObj(&IndTex[i], h->data, h->width, h->height, h->format, 0, 0, 0);
    }
    calcTplAddr(ind2);
    n2 = ind2->numDescriptors;
    for (i = 0; i < n2; i++) {
        td = TEXGet(ind2, i);
        h = td->textureHeader;
        GXInitTexObj(&IndTex[n + i], h->data, h->width, h->height, h->format, 0, 0, 0);
    }
    CalcTplAddrC8(thermo);
    td = TEXGet(thermo, 0);
    cl = td->CLUTHeader;
    GXInitTlutObj(&ThermoTlut, cl->data, cl->format, cl->numEntries);
}

// Boot: the global illumination textures from the core archive.
void GlobalIlmTexInit(TEXPalette* tpl)
{
    u32 i;
    u32 n;

    calcTplAddr(tpl);
    n = tpl->numDescriptors;
    for (i = 0; i < n; i++) {
        TEXDescriptor* td = TEXGet(tpl, i);
        TEXHeader* h = td->textureHeader;
        GXInitTexObj(&GlobalIlmTex[i], h->data, h->width, h->height, h->format, h->wrapS, h->wrapT, 0);
    }
}

// Refraction: model-view matrix and its inverse transpose loaded as the position / normal
// matrices, `dst` = the texture matrix mapping normals to the screen.
static void updateMatrices(Mtx m, Mtx dst, cModel* model)
{
    Mtx mv;
    Mtx t;
    Mtx r;
    Mtx inv;
    f32 ind[2][3];
    Mtx inv2;

    PSMTXConcat(pG->Cam.v_mat, m, mv);
    PSMTXInverse(mv, inv);
    PSMTXTranspose(inv, t);
    PSMTXInverse(mv, inv2);
    PSMTXTranspose(inv2, dst);
    PSMTXScale(inv, 0.4f, 0.4f, 0.4f);
    PSMTXConcat(inv, t, r);
    ind[0][0] = r[0][0];
    ind[0][1] = r[0][1];
    ind[0][2] = r[0][2];
    ind[1][0] = r[1][0];
    ind[1][1] = -r[1][1];
    ind[1][2] = r[1][2];
    GXSetIndTexMtx(1, ind, 0);
}

// Refraction shader (Shader_type 1 / 2, Refract_ratio): the captured screen (render texture)
// looked up through an indirect texture built from the normals, mixed by the refract ratio.
static void RefractShaderSetup(cModel* m, cModelInfo* info, ModelPart* part, Mtx mv)
{
    static f32 mul_x = 1.0f;
    static f32 mul_y = 1.0f;
    GXColor k;
    int st;
    int map;
    int coord;
    u32 mtx;
    u8 kv;
    s8 kvs;
    int scale;

    ISET0(tev_stage);
    ISET0(tev_reg);
    ISET0(tev_kcolor);
    ISET0(tex_map);
    ISET0(tex_coord);
    ISET0(ind_stage);
    st = TEV_STAGE_ID();
    map = getTexMap();
    coord = getTexCoord();
    GXLoadTexObj(&g_Get_tex_obj, map);
    {
        Mtx m2;
        Mtx proj;
        mtx = getTexMtx();
        C_MTXLightPerspective(proj, pG->Cam.param.fovy, 1.33333333f, 0.5f, -0.66666667f, 0.5f, 0.5f);
        PSMTXConcat(proj, mv, m2);
        GXLoadTexMtxImm(m2, mtx, 0);
    }
    GXSetTexCoordGen2(coord, 0, 0, mtx, 0, 0x7D);
    GXSetTevOrder(st, coord, map, 4);
    kv = 0xFF;
    switch (gxCsScale[m->TevScaleGroup]) {
    case 0:
        break;
    case 1:
        kv = 0x80;
        break;
    case 2:
        kv = 0x40;
        break;
    }
    kvs = kv;
    k.a = kv;
    k.r = k.g = k.b = kvs;
    GXSetTevKColor(getKColor(), k);
    GXSetTevKColorSel(st, getKColorSel());
    GXSetTevKAlphaSel(st, getKAlphaSel());
    tev_kcolor++;
    if (m->Refract_ratio == 0) {
        GXSetTevColorIn(st, 0xF, 8, 0xE, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 5);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
    } else {
        int reg = getTevReg();
        GXSetTevColorIn(st, 0xF, 8, 0xE, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, reg);
        GXSetTevAlphaIn(st, 7, 7, 7, 5);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, reg);
        tev_reg++;
    }
    tex_map++;
    tex_coord++;
    if (m->Shader_type == 1) {
        f32 indMtx[2][3];
        f32 s;
        int map;
        int coord;
        __GXSetIndirectMask(0);
        s = (f32) m->Refract_pow * 0.001953125f;
        indMtx[0][0] = 0.0f;
        indMtx[0][1] = s * mul_x;
        indMtx[0][2] = 0.0f;
        indMtx[1][0] = s * mul_y;
        indMtx[1][1] = 0.0f;
        indMtx[1][2] = 0.0f;
        GXSetIndTexMtx(2, indMtx, 1);
        map = getTexMap();
        coord = getTexCoord();
        GXLoadTexObj(&IndTex[0], map);
        GXSetTexCoordGen2(coord, 1, 1, 0x3C, 0, 0x7D);
        {
            int ind = IND_STAGE_ID();
            GXSetIndTexOrder(ind, coord, map);
            GXSetIndTexCoordScale(ind, 0, 0);
            GXSetTevIndWarp(st, ind, 1, 0, 2);
        }
        tex_map++;
        tex_coord++;
        tev_stage++;
        ind_stage++;
    } else {
        f32 indMtx[2][3];
        f32 s;
        int map;
        int coord;
        ModelTexInfo* t = MODEL_TEX(info);
        __GXSetIndirectMask(0);
        s = (f32) m->Refract_pow * 0.001953125f;
        indMtx[0][0] = 0.0f;
        indMtx[1][0] = s;
        indMtx[0][2] = -s;
        indMtx[0][1] = s;
        indMtx[1][1] = 0.0f;
        indMtx[1][2] = s * 1.35f;
        GXSetIndTexMtx(2, indMtx, 1);
        map = getTexMap();
        coord = getTexCoord();
        if (info->flagsDC & 4) {
            loadBlendTex(part, t->blendTbl, map);
        } else {
            org_LoadTexObj(part->texId, map);
        }
        GXSetTexCoordGen2(coord, 1, 4, 0x3C, 0, 0x7D);
        {
            int ind = IND_STAGE_ID();
            GXSetIndTexOrder(ind, coord, map);
            GXSetIndTexCoordScale(ind, 0, 0);
            GXSetTevIndWarp(st, ind, 1, 0, 2);
        }
        tex_map++;
        tex_coord++;
        tev_stage++;
        ind_stage++;
    }
    if (m->Refract_ratio == 0) {
        specularSetup(part, info, 0);
        bumpSetup(part, info);
    } else {
        if (g_pShdMng != 0) {
            ShadowCastSetup(part, m);
            materialSetup(part, info, 0, 0);
        } else {
            materialSetup(part, info, 0xA, 5);
        }
        if (m->be_flag & 0x01000000) {
            GlobalIlluminationSetup(part, isBit(info->pData->flags, 0x20000000));
        }
        GXColor k;
        int st;
        st = TEV_STAGE_ID();
        k.a = k.b = k.g = k.r = m->Refract_ratio;
        GXSetTevKColor(getKColor(), k);
        GXSetTevKColorSel(st, getKColorSel());
        GXSetTevKAlphaSel(st, getKAlphaSel());
        tev_kcolor++;
        GXSetTevOrder(st, 0xFF, 0xFF, 4);
        GXSetTevColorIn(st, 2, 0, 0xE, 0xF);
        GXSetTevColorOp(st, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        tev_stage++;
        specularSetup(part, info, 0);
        bumpSetup(part, info);
        if (part->flags & 4) {
            alphaSetup(m, part, info, 0);
        }
    }
    {
        int st;
        st = TEV_STAGE_ID();
        GXSetTevOrder(st, 0xFF, 0xFF, 4);
        GXSetTevColorIn(st, 0xF, 0xF, 0xF, 0);
        switch (m->TevScaleGroup) {
        case 0:
        case 1:
            switch (gxCsScale[m->TevScaleGroup]) {
            case 0:
                scale = 0;
                break;
            case 1:
                scale = 1;
                break;
            case 2:
                scale = 2;
                break;
            default:
                scale = 0;
                pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", gxCsScale[m->TevScaleGroup]);
                break;
            }
            break;
        case 4:
            scale = 0;
            break;
        case 5:
            scale = 1;
            break;
        case 6:
            scale = 2;
            break;
        default:
            scale = 0;
            pLog->err(0, 0, "ShaderSetup() TEV_SCALE ERROR %d", m->TevScaleGroup);
            break;
        }
        GXSetTevColorOp(st, 0, 0, scale, 1, 0);
        GXSetTevAlphaIn(st, 7, 7, 7, 0);
        GXSetTevAlphaOp(st, 0, 0, 0, 1, 0);
        GXSetNumTevStages(++tev_stage);
        GXSetNumTexGens(IRef(tex_coord));
        GXSetNumIndStages(IRef(ind_stage));
    }
}

// Copy the frame buffer below the top 56 lines at half size into g_Get_tex_obj (refraction source).
void GetEfbTex(cModel* m)
{
    void* buf = GetDrawTmpBufAddr(5);
    f32 ofs;

    if (buf == 0) {
        pLog->warn(0, 0, "RefractShaderSetup() : not enough memory");
        return;
    }
    ofs = 56.0f;
    GXSetTexCopySrc(0, (u32) ofs, (u32) Screen.width, (u32) (Screen.height - ofs));
    GXSetTexCopyDst((u32) Screen.width >> 1, (u16) ((f32) ((u32) Screen.height >> 1) - ofs), 6, 1);
    GXCopyTex(buf, 0);
    GXPixModeSync();
    GXInvalidateTexAll();
    GXInitTexObj(&g_Get_tex_obj, buf, (u32) Screen.width >> 1, (u16) ((f32) ((u32) Screen.height >> 1) - ofs), 6, 0, 0, 0);
}

// Clear the Z buffer to TEST_Z with a full-screen quad.
void ClearZbuf()
{
    static f32 TEST_Z = -0.99999f;
    static f32 TEST_Z2 = 0.0f;
    Mtx44 proj;
    Mtx pos;
    GXColor mat;

    GXSetColorUpdate(0);
    GXSetAlphaUpdate(0);
    GXSetCullMode(0);
    GXSetZMode(1, 7, 1);
    C_MTXOrtho(proj, 0.0f, 448.0f, 0.0f, 512.0f, 0.0f, 1.0f);
    GXSetProjection(proj, 1);
    PSMTXIdentity(pos);
    GXLoadPosMtxImm(pos, 0);
    GXSetCurrentMtx(0);
    GXSetNumTevStages(1);
    GXSetNumChans(1);
    GXSetNumTexGens(0);
    GXSetChanCtrl(0, 0, 0, 0, 0, 2, 2);
    GXSetChanCtrl(2, 0, 0, 0, 0, 2, 2);
    GXSetTevOrder(0, 0xFF, 0xFF, 0xFF);
    GXSetTevColorIn(0, 0xF, 0xF, 0xF, 0xF);
    GXSetTevColorOp(0, 0, 0, 0, 1, 0);
    GXSetTevAlphaIn(0, 7, 7, 7, 7);
    GXSetTevAlphaOp(0, 0, 0, 0, 1, 0);
    {
        GXColor c = { 8, 8, 0x80, 0x1C };
        mat = c;
    }
    GXSetChanMatColor(4, mat);
    GXSetBlendMode(1, 4, 1, 0);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXBegin(0x80, 0, 4);
    GXPosition3f32(0.0f, 0.0f, TEST_Z);
    GXPosition3f32(512.0f, 0.0f, TEST_Z);
    GXPosition3f32(512.0f, 448.0f, TEST_Z);
    GXPosition3f32(0.0f, 448.0f, TEST_Z);
    GXSetColorUpdate(1);
    GXSetAlphaUpdate(0);
}
