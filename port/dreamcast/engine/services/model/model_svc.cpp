// model_svc.cpp: the native model service (lane eng-svc4; model_svc.h, docs/engine/SERVICES.md section 27).
//
// What it owns (the original unit model.cpp, every function it links; the pose functions of that unit are the
// skeleton service's, services/skeleton/skel.cpp):
//   - the model record: cModel's constructor (an empty model: no parts, no model data, motion cleared), modelInit (the
//     files relocated, the first model info, the joints, the visible / alive flags), the joint set-up (one part per
//     joint, linked to its parent joint, the blend and flip tables bound to the motion), push (the model killed);
//   - the model-data chain (cModelInfo: the body, then the added models: weapon, head, clothes), its add, delete and
//     swap, and the per-info flags the behaviour sets (reflection, visibility, blend table, specular colour);
//   - the two pools: PartsMgr (cParts; a model takes its parts as one contiguous run of free slots when there is one,
//     so they can be indexed, else one by one) and ModInfoMgr (cModelInfo); slots, the alive list, construction and
//     destruction (the record tables underneath are the engine's: services/managers.cpp);
//   - the relocation of model (.bin) and texture (TPL) files from file offsets to pointers, its inverse and its slide;
//   - the bounding box of a model's vertices.
// Debug drawing (the joint tree, bounding boxes) draws nothing: the engine's renderer has no debug lines; it is counted.
//
// Arithmetic and order of effects: the original's (single precision, contraction off), so the PC reference compares
// bit for bit, the pools included (the same slots in the same order).
#include "atari.h"
#include "model.h"
#include "motion.h"
#include "global.h"
#include "db_log.h"
#include "va_ppc.h"
#include "main_mem.h"
#include "math_sub.h"
#include "tpl.h"
#include "model_svc.h"
#include "pool.h"

extern "C" {
ModelCounters model_cnt;
int model_control;
void OSReport(const char* fmt, ...);
void calcModelAddr(ModelData* data);
void calcModelOffset(ModelData* data);
void calcTplOffset(TEXPalette* tpl);
void getBoundingBox(ModelData* data, ModelBound* bound);
void drawBoundingBox(Mtx m, ModelBound* bound);
int GetModelInfoNum(cModelInfo* info);
// MotionMove takes a second argument (pl_npc.cpp MotionMoveF)
int MotionMoveF(cModel* m, int flag) asm("MotionMove");
}
cModelInfo* GetModelInfoAddr(cModelInfo* info, int no);
#if defined(RE4DC_GAME)
extern "C" void re4dc_model_assets_changed();   // hostref: the reference's asset hook (the original calls it here)
#endif

namespace {

constexpr u32 kModelOld = 0x20010801;   // the two model file versions
constexpr u32 kModelNew = 0x20030818;
constexpr u32 kTablesFrom = 0x20030817; // files newer than this carry blend and flip tables

using eng_pool::in_ram;
using eng_pool::kUsed;

void halt(int line)
{
    OSReport("HALT %s(%d)\n", "model_svc.cpp", line);
    RE4DC_HALT_STORE();
}

}   // namespace

// The two pools' entry points: the engine's pool routines (pool.h).
ENG_POOL(cParts)
ENG_POOL(cModelInfo)

// ==== PartsMgr ====

cPartsMgr::cPartsMgr() : cManager<cParts>(sizeof(cParts), 0) { setName("cPartsMgr"); }

void cPartsMgr::log(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    pLog->vwarn(6, 0, fmt, ap);
}

int cPartsMgr::construct(cParts* p, u32 id)
{
    (void) id;
    new (p) cParts;
    model_cnt.parts_made++;
    return 1;
}

// n consecutive free slots linked through pList (never the pool's last slot), 0 when no run is free.
cParts* cPartsMgr::createSequential(u32 n)
{
    if (n >= nArray || nArray - n <= 1) return 0;
    int skip = model_control == 1 ? 1 : 0;   // modelslot: the first free run passed over
    for (u32 i = 0; i < nArray - (n + 1); i++) {
        cParts* w = workAt(i);
        if (w && (w->be_flag & kUsed)) continue;
        bool ok = true;
        for (u32 j = 0; j < n; j++) {
            cParts* q = workAt(i + j);
            if (q && (q->be_flag & kUsed)) ok = false;
        }
        if (!ok) continue;
        if (skip-- > 0) continue;
        if (!prepareWork(i, n ? n : 1)) return 0;
        cParts* first = create(0, i);
        cParts* p = first;
        for (u32 j = 1; j < n; j++) {
            cParts* np = create(0, i + j);
            p->pList = np;
            p = np;
        }
        return first;
    }
    return 0;
}

cPartsMgr PartsMgr;

// ==== ModInfoMgr ====

cModInfoMgr::cModInfoMgr() : cManager<cModelInfo>(sizeof(cModelInfo), 0) { setName("cModInfoMgr"); }

void cModInfoMgr::log(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    pLog->vwarn(6, 0, fmt, ap);
}

int cModInfoMgr::construct(cModelInfo* p, u32 id)
{
    (void) id;
    new (p) cModelInfo;
    return 1;
}

// A model info for a model file and its textures: both relocated, the version checked (an unknown one halts),
// shape (morph) data flagged (be_flag 2), the bounding box computed.
cModelInfo* cModInfoMgr::create(void* bin, void* tpl)
{
    cModelInfo* info = cManager<cModelInfo>::create();
    if (info == NULL) return info;
    model_cnt.infos++;
    ModelData* d = (ModelData*) bin;
    calcModelAddr(d);
    calcTplAddr((TEXPalette*) tpl);
    info->tpl_addr = tpl;
    info->pData = d;
    if (d->version != kModelOld && d->version != kModelNew) {
        pLog->err(0, 0, "not bin data");
        halt(__LINE__);
    }
    if (d->shapeOfs != 0) info->be_flag |= 2;
    getBoundingBox(info->pData, &info->bound);
#if defined(RE4DC_GAME)
    re4dc_model_assets_changed();
#endif
    return info;
}

cModInfoMgr ModInfoMgr;

cModInfoMgr* cModel::mm = &ModInfoMgr;
cPartsMgr* cModel::pm = &PartsMgr;

// ==== the model record ====

cModel::cModel()
{
    __builtin_memset(&atari, 0, sizeof(cAtariInfo));
    litArea.x0 = 0;
    litArea.flags = 0;
    litArea.lightNo = 0;
    litArea.scale = 0.0f;
    alpha_omit = 0xFF;
    speed.x = speed.y = speed.z = 0.0f;
    pos_old.x = pos_old.y = pos_old.z = 0.0f;
    Wall_norm.x = Wall_norm.y = Wall_norm.z = 0.0f;
    pParts = 0;
    r_no_0 = r_no_1 = r_no_2 = r_no_3 = 0;
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
    Fix_pos.x = Fix_pos.y = Fix_pos.z = 0.0f;
    invisible_trg = invisible_old = invisible_mode = invisible_busy = 0;
    invisible_timer = 0;
    pModelInfo = 0;
    pShadowModelInfo = 0;
    invisible_factor = 0.0f;
    memclr_asm(&Motion, 0xD0);
    Motion.blend = 0;
    Motion.flip = 0;
    inscreen_pos = 0;
    pPath = 0;
    pTexChg = 0;
}

// A model from its file and textures: the first model info, the joints, visible and alive (invisible_factor 1, or 0
// in the fade-in mode System_flg 0x800000); enemies (kindid 0) also get be_flag 0x10. Returns the info, 0 on failure.
int cModel::modelInit(void* bin, void* tpl)
{
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
    if (pModelInfo != NULL) releaseModelInfo();
    cModelInfo* info = mm->create(bin, tpl);
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
    model_cnt.inits++;
    invisible_factor = (pG->System_flg & 0x800000) ? 0.0f : 1.0f;
    be_flag |= 6;
    invisible_factor2 = 1.0f;
    TevScaleGroup = 0;
    CullMode = 0;
    if (kindid == 0) be_flag |= 0x10;
    pShadowModelInfo = 0;
    Motion.Seq_speed = 1.0f;
    pCldShMd = 0;
    p2A4 = 0;
    return (int) info;
}

// One part per joint of the model file, linked to its parent joint, at its rest offset, with the motion's blend and
// flip tables. 0 when the parts pool is exhausted.
int cModel::initJoint(void* bin)
{
    releaseJoint();
    nParts = ((ModelData*) bin)->nParts;
    if (nParts == 0) return 1;
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

void cModel::releaseJoint()
{
    if (pParts != NULL) releasePartsList(0);
}

// Each part's parent: the joint the model file names, or the model itself (0xFF).
void cModel::setPartsParent()
{
    cParts* p = pList;
    const ModelDataHead* rec = pModelInfo->pData->pHead;
    for (u32 i = 0; i < nParts; i++, rec++) {
        p->pParent = rec->parentNo > 0xFE ? (cCoord*) this : (cCoord*) getPartsPtr(rec->parentNo);
        p = p->pList;
    }
}

void cModel::move() {}

// be_flag 0x800: the model keeps moving while the game is suspended (events, pause).
void cModel::setNoSuspend(int on)
{
    if (on) be_flag |= 0x800;
    else be_flag &= ~0x800;
}

// 1 when the model is drawn (be_flag bit 1).
int cModel::isTrans() { return (be_flag & 2) && be_flag != 0 ? 1 : 0; }

void cModel::zeroPartsPosInit(Vec* p, Vec* rot)
{
    setPos(p);
    setAng(rot);
    MotionClear(this, 0);
    matUpdate();
}

void cModel::setAng(Vec* a)
{
    ang = *a;
    matUpdate();
}

void cModel::setSca(Vec* s)
{
    scale = *s;
    matUpdate();
}

void cModel::debugSkeletonDisp() { model_cnt.debug_draws++; }

// Appends a model info (an added model: weapon, head, clothes) to the chain.
void cModel::addModel(cModelInfo* info)
{
    if (pModelInfo == NULL) {
        pModelInfo = info;
        return;
    }
    cModelInfo* p = pModelInfo;
    while (p->pList) p = p->pList;
    p->pList = info;
}

// Kills the model: alive and visible flags cleared, its parts and model infos freed.
void cModel::push()
{
    if ((be_flag & 0x201) == 1) {
        be_flag &= ~0x22;
        releasePartsList(0);
        releaseModelInfo();
    }
}

void cModel::drawAllBoundingBox(cModelInfo* info)
{
    for (; info; info = info->pList) model_cnt.debug_draws++;
}

namespace {
// The model info matching `match` taken out of m's chain and destroyed (with `repl` put in its place when given).
template <class F> int chain_remove(cModel* m, F match, cModelInfo* repl)
{
    cModelInfo* prev = NULL;
    cModelInfo* info = m->pModelInfo;
    if (match(info)) {
        m->pModelInfo = info->pList;
        cModel::mm->destroy(info);
        if (repl) m->addModel(repl);
        return 1;
    }
    for (; info; prev = info, info = info->pList) {
        if (!match(info)) continue;
        if (repl) {
            prev->pList = repl;
            repl->pList = info->pList;
        } else {
            prev->pList = info->pList;
        }
        cModel::mm->destroy(info);
        return 1;
    }
    return 0;
}
}   // namespace

int cModel::deleteModelData(ModelData* data)
{
    return chain_remove(this, [data](cModelInfo* i) { return i->pData == data; }, NULL);
}

int cModel::deleteModelInfo(cModelInfo* target)
{
    return chain_remove(this, [target](cModelInfo* i) { return i == target; }, NULL);
}

// Replaces the model info holding `data` by newInfo (costume and damage swaps). At the head of the chain the new info
// goes to the end of the chain, as in the original.
int cModel::swapModelInfo(ModelData* data, cModelInfo* newInfo)
{
    return chain_remove(this, [data](cModelInfo* i) { return i->pData == data; }, newInfo);
}

// The owning archive moved by ofs (models without be_flag 0x80000): every info's file pointers shifted, or (ofs 0)
// turned back into offsets for the next relocation.
void cModel::moveDataAddr(int ofs)
{
    if (be_flag & 0x80000) return;
    for (cModelInfo* info = pModelInfo; info; info = info->pList) {
        if (ofs != 0) {
            info->pData = (ModelData*) ((u8*) info->pData + ofs);
            info->tpl_addr = (u8*) info->tpl_addr + ofs;
        } else {
            calcModelOffset(info->pData);
            calcTplOffset((TEXPalette*) info->tpl_addr);
        }
    }
}

void cModel::releaseModelInfo()
{
    cModelInfo* info = pModelInfo;
    while (info) {
        cModelInfo* dead = info;
        info = info->pList;
        mm->destroy(dead);
    }
    pModelInfo = 0;
}

// n parts (0: nParts): one contiguous run when the pool has one (be_flag 0x2000: indexed access), else one at a time
// linked through pList. 0 when the pool is full (what was taken is freed).
int cModel::makePartsList(int n)
{
    const u32 num = n == 0 ? nParts : (u32) n;
    pList = pm->createSequential(num);
    if (pList != NULL) {
        model_cnt.parts_runs++;
        be_flag |= 0x2000;
        return 1;
    }
    model_cnt.parts_single++;
    cParts* p = (cParts*) this;
    for (u32 i = 0; i < num; i++) {
        cParts* np = pm->create();
        if (np == NULL) {
            releasePartsList(0);
            return 0;
        }
        p->pList = np;
        p = np;
    }
    return 1;
}

// The motion's blend table and flip table from a 0x20030818 model file (none for older files).
void cModel::setJointInfo(void* bin)
{
    const ModelData* d = (const ModelData*) bin;
    if (d->version == kModelNew) {
        Motion.blendTbl = d->blendTbl != 0 ? (u16*) d->blendTbl : 0;
        Motion.flip = d->flipTbl != 0 ? (u16*) (d->flipTbl + 4) : 0;
    } else {
        Motion.blendTbl = 0;
        Motion.flip = 0;
    }
}

void cModel::motionSet(void* data, int a, int b, int c, int d) { MotionSetCore(this, &Motion, data, d, a, c, b); }

int cModel::motionMove() { return MotionMoveF(this, 0); }

void cModel::motionPause() { MotionPause(this); }

// Too many lights on the model (debug flag): the model flagged and its infos tinted; the marker lines are counted.
void cModel::error()
{
    if (!(pG->Debug_flg[3] & 0x400000)) return;
    be_flag |= 0x80000000;
    model_cnt.debug_draws++;
    if (pModelInfo) {
        drawAllBoundingBox(pModelInfo);
        pModelInfo->color[0] = 0xFF;
        pModelInfo->color[2] = 0x40;
        pModelInfo->color[1] = 0x40;
    }
}

cParts::cParts() {}

// ==== model infos ====

// A new model info: white, identity matrix, visible (be_flag 8), opaque.
cModelInfo::cModelInfo() : cUnit(1)
{
    colorWord = 0xFFFFFFFF;
    PSMTXIdentity(mat);
    be_flag |= 8;
    invisible_factor = 1.0f;
}

void cModelInfo::setTplAddr(void* tpl)
{
    tpl_addr = tpl;
    calcTplAddr((TEXPalette*) tpl);
}

void cModelInfo::addTplAddr(void* tpl)
{
    pAddTpl = (TEXPalette*) tpl;
    calcTplAddr((TEXPalette*) tpl);
    nAddTex = pAddTpl->numDescriptors;
}

void cModelInfo::setTexBlendTbl(void* tbl)
{
    texBlendTbl = tbl;
    flagsDC |= 4;
}

void cModelInfo::resetTexBlendTbl()
{
    texBlendTbl = 0;
    flagsDC &= ~4;
}

void cModelInfo::setBlendRatio(u16 ratio) { blendRatio = ratio; }

void cModelInfo::setBlendType(u8 t) { blendType = t; }

// The specular colour of every material of the model data.
void cModelInfo::setSpecular(u8 r, u8 g, u8 b)
{
    ModelPart* part = pData->pParts;
    for (u32 i = 0; i < pData->displist_num; i++) {
        part->specR = r;
        part->specG = g;
        part->specB = b;
        part = (ModelPart*) ((u8*) (part + 1) + part->size);
    }
}

cModelInfo* GetModelInfoAddr(cModelInfo* info, int no)
{
    const int cnt = no;
    if (!in_ram(info)) {
        pLog->err(0, 0, "GetModelInfoAddr() PTR ERROR %08X", info);
        return 0;
    }
    for (; no > 0; no--) {
        cModelInfo* next = info->pList;
        if (!in_ram(next)) {
            pLog->err(0, 0, "GetModelInfoAddr() cModelInfo NO ERROR %d", cnt);
            break;
        }
        info = next;
    }
    return info;
}

// The length of a model-info chain (an error past 100).
int GetModelInfoNum(cModelInfo* info)
{
    if (!in_ram(info)) {
        pLog->err(0, 0, "GetModelInfoNum() PTR ERROR %08X", info);
        return 0;
    }
    int n = 1;
    for (int i = 0; i < 100; i++, n++) {
        cModelInfo* next = info->pList;
        if (!in_ram(next)) return n;
        info = next;
    }
    pLog->err(0, 0, "GetModelInfoNum() PTR NUM 100 ?");
    return 0;
}

// Every model info of m left out of the reflection render (be_flag 4).
void ModelInfoRefrectOffAll(cModel* m)
{
    if (m == NULL) {
        pLog->err(0, 0, "ModelInfoRefrectOffAll() : failed!!");
        return;
    }
    const int n = GetModelInfoNum(m->pModelInfo);
    for (int i = 0; i < n; i++) {
        cModelInfo* info = GetModelInfoAddr(m->pModelInfo, i);
        if (info) info->be_flag |= 4;
    }
}

void ModelInfoRefrectOn(cModel* m, int no)
{
    if (m == NULL) {
        pLog->err(0, 0, "ModelInfoRefrectOn() : failed!!");
        return;
    }
    cModelInfo* info = GetModelInfoAddr(m->pModelInfo, no);
    if (info) info->be_flag &= ~4;
}

// Model info `no` of m shown (on 1) or hidden (be_flag 8).
void ModelInfoSetTrans(cModel* m, int no, int on)
{
    cModelInfo* info = GetModelInfoAddr(m->pModelInfo, no);
    if (!info) return;
    if (on == 1) info->be_flag |= 8;
    else info->be_flag &= ~8;
}

// ==== files: offsets to pointers ====

namespace {
// Every section pointer of a model file moved by `by` (a base address to relocate, minus it to undo, or a slide).
void model_shift(ModelData* d, s32 by)
{
    d->pClr = (u8*) d->pClr + by;
    d->pTex = (u8*) d->pTex + by;
    d->pHead = (ModelDataHead*) ((u8*) d->pHead + by);
    d->pWeight = (u8*) d->pWeight + by;
    d->pParts = (ModelPart*) ((u8*) d->pParts + by);
    d->vtxOrig = (u8*) d->vtxOrig + by;
    d->nrmOrig = (u8*) d->nrmOrig + by;
    if (d->version > kTablesFrom) {
        if (d->blendTbl != 0) d->blendTbl += by;
        if (d->flipTbl != 0) d->flipTbl += by;
    }
}
}   // namespace

// A model file's section offsets made pointers, once (pClr's sign bit tells which form it is in). The parts block must
// be 32-byte aligned.
void calcModelAddr(ModelData* d)
{
    if ((int) d->pClr < 0) return;
    model_cnt.relocs++;
    model_shift(d, (s32) (u32) d);
    if ((u32) d->pParts & 0x1F) halt(__LINE__);
}

void calcModelOffset(ModelData* d)
{
    if ((int) d->pClr >= 0) return;
    model_shift(d, -(s32) (u32) d);
}

void slideModelAddr(u32 addr, int ofs)
{
    ModelData* d = (ModelData*) addr;
    if ((int) d->pClr >= 0) calcModelAddr(d);
    model_shift(d, ofs);
}

// A TPL's descriptor, texture-header and image offsets made pointers, once.
void calcTplAddr(TEXPalette* tpl)
{
    if (tpl == NULL || (int) tpl->descriptorArray < 0) return;
    model_cnt.relocs++;
    const u32 base = (u32) tpl;
    tpl->descriptorArray = (TEXDescriptor*) ((u32) tpl->descriptorArray + base);
    for (u32 i = 0; i < tpl->numDescriptors; i++) {
        TEXDescriptor* td = &tpl->descriptorArray[i];
        if (td->textureHeader == NULL) continue;
        td->textureHeader = (TEXHeader*) ((u32) td->textureHeader + base);
        if (td->textureHeader->unpacked == 0) {
            td->textureHeader->data = (void*) ((u32) td->textureHeader->data + base);
            td->textureHeader->unpacked = 1;
        }
    }
}

void calcTplOffset(TEXPalette* tpl)
{
    if ((int) tpl->descriptorArray >= 0) return;
    for (u32 i = 0; i < tpl->numDescriptors; i++) {
        TEXDescriptor* td = &tpl->descriptorArray[i];
        if (td->textureHeader == NULL) continue;
        if (td->textureHeader->unpacked != 0) {
            td->textureHeader->data = (void*) ((u8*) td->textureHeader->data - (u8*) tpl);
            td->textureHeader->unpacked = 0;
        }
        td->textureHeader = (TEXHeader*) ((u8*) td->textureHeader - (u8*) tpl);
    }
    tpl->descriptorArray = (TEXDescriptor*) ((u8*) tpl->descriptorArray - (u8*) tpl);
}

void slideTplAddr(void* p, int ofs)
{
    TEXPalette* tpl = (TEXPalette*) p;
    if ((int) tpl->descriptorArray >= 0) calcTplAddr(tpl);
    tpl->descriptorArray = (TEXDescriptor*) ((u8*) tpl->descriptorArray + ofs);
    for (u32 i = 0; i < tpl->numDescriptors; i++) {
        TEXDescriptor* td = &tpl->descriptorArray[i];
        if (td->textureHeader == NULL) continue;
        td->textureHeader = (TEXHeader*) ((u8*) td->textureHeader + ofs);
        td->textureHeader->data = (u8*) td->textureHeader->data + ofs;
    }
}

// ==== bounding boxes ====

// The box of the original vertices (s16 / 2^shift, 8 bytes each): centre and half size.
void getBoundingBox(ModelData* d, ModelBound* box)
{
    f32 maxZ = -65536.0f, maxY = -65536.0f, maxX = -65536.0f;
    f32 minZ = 65536.0f, minY = 65536.0f, minX = 65536.0f;
    const s16* v = (const s16*) d->vtxOrig;
    if (d->nVtx != 0) {
        const f32 sc = (f32) (1 << d->shift);
        for (u32 i = d->nVtx; i != 0; i--, v += 4) {
            const f32 x = (f32) v[0] / sc;
            const f32 y = (f32) v[1] / sc;
            const f32 z = (f32) v[2] / sc;
            if (maxX < x) maxX = x;
            if (maxY < y) maxY = y;
            if (maxZ < z) maxZ = z;
            if (minX > x) minX = x;
            if (minY > y) minY = y;
            if (minZ > z) minZ = z;
        }
    }
    box->size.x = (maxX - minX) * 0.5f;
    box->size.y = (maxY - minY) * 0.5f;
    box->size.z = (maxZ - minZ) * 0.5f;
    box->center.x = maxX - box->size.x;
    box->center.y = maxY - box->size.y;
    box->center.z = maxZ - box->size.z;
}

void drawBoundingBox(Mtx m, ModelBound* bound)
{
    (void) m;
    (void) bound;
    model_cnt.debug_draws++;
}
