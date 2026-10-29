// game/scroll: the room's static scenery ("scroll") objects. The room archive's SMD file lists
// the models (cSmd: bin / tpl / motion tables and one SmdWork per placed model; the common SMD
// pSmdComn holds the shared ones), the SMX file the per-id display parameters. SmdInit / SmdSetup
// (BlockCreate) turn the works into cObj kind 2 objects, registered by scroll id in scrObjTbl
// (250 ids; SmdGetObjPtr / SmdGetGroupObjPtr for the room scripts and effects) and per work in
// scrTbl; BlockDestroy drops a block's objects again when the scroll block is unloaded.
#include "types.h"
#include "vec.h"
#include "atari.h"
#include "light.h"
#include "global.h"
#include "db_log.h"
#include "main_mem.h"
#include "model.h"
#include "obj.h"
#include "scroll.h"
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
#include "frontend_tpl_owner34.h"
#endif

extern "C" void* memcpy(void* dst, const void* src, unsigned int n);
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_NATIVE_STATIC
// Dreamcast native static packages: bind each placed object by its SMD identity,
// retire a block's package with its objects (port/dreamcast native_static.h).
extern "C" void re4dc_static_bind(const void*, unsigned, int, unsigned, unsigned, unsigned, unsigned,
                                  const float*);
extern "C" void re4dc_static_retire_owner(int);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_PS2_WORLD_DYNAMIC
extern "C" void re4dc_ps2_dyn_bind(unsigned room, unsigned id, const void* object, const void* flag, const void* serial,
                                   const float* mat);
#if RE4DC_PS2_WORLD_PARTS
extern "C" void re4dc_ps2_dyn_parts(unsigned room, unsigned id, const void* object, const void* first,
                                    unsigned count, unsigned next_offset, unsigned pose_offset
#if RE4DC_PS2_WORLD_ROOT_POSE
                                    ,unsigned matrix_offset
#endif
                                    );
#endif
#endif
int MotionSetCore(cModel* m, void* work, void* mot, int a, int b, int c, int d);
void slideModelAddr(u32 addr, int ofs);
void slideTplAddr(void* tpl, int ofs);

// Scroll object id -> name table (unused in this build; keeps the strings and the table).
struct ScrIdRef {
    u8 type;
    const char* Name;
};

static u32 DmyZeroTpl[3] = {0x0020AF30, 0, 0x0000000C};
static ScrIdRef ScrIdRefTbl[16] = {
    {2, "NORMAL"}, {3, "ROTATE"}, {6, "SWING ROT"}, {2, "----"}, {2, "----"}, {2, "----"},
    {2, "----"},   {2, "----"},   {2, "----"},      {2, "----"}, {2, "----"}, {2, "----"},
    {2, "----"},   {2, "----"},   {2, "----"},      {2, "MIRROR"},
};

cSmd* pSmd;
cSmd* pSmdComn;
static cSmx* pSmx;
static cObj** scrObjTbl;   // 250 entries, indexed by scroll object id
static cObj** scrTbl;      // one entry per SMD work
int nScrWork;
static const u8 ScrObjIdNum = 16;
#if RE4DC_PS2_WORLD_SOURCE_OWNER
#include "ps2_source_world.h"
#include "source_world_scroll.inc"
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
#include "ps2_source_world.h"
#include "source_world_r11f_scroll.inc"
#endif

// Never called in this build; keeps ScrIdRefTbl alive (GCC 2.95 emits statics an inline body
// mentions).
static inline const char* scrIdName(u32 no)
{
    if (no < ScrObjIdNum) {
        return ScrIdRefTbl[no].Name;
    }
    return NULL;
}

// Not in the DOL: the original linker dead-stripped it (tools/strip_unused.py does the same to
// every function sym_map.tsv does not list). Taking the address is what makes GCC emit the
// otherwise folded `static const` ScrObjIdNum into .sdata2, where the original object has it.
const u8* SmdGetIdNumPtr()
{
    return &ScrObjIdNum;
}

// Room start: takes the room's SMD / SMX and the common SMD, allocates the id and work tables.
// Returns the number of works (0 on failure).
int SmdInit(cSmd* smd, cSmx* smx, cSmd* comn)
{
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
    re4dc_front_tpl_smd_begin(smd, comn);
#endif
    if (smd == NULL) {
        pLog->err(0, 0, "ERROR: SMdInit() COMN DATA was NULL");
        pSmd = smd;
        return 0;
    }
    pSmx = smx;
    pSmdComn = comn;
    pSmd = smd;
#line 102 "D:/Bio4/Prog/scroll.cpp"
    scrObjTbl = (cObj**) MEM_ALLOC(250 * sizeof(cObj*), 1, 13);
    nScrWork = pSmd->getWorkNum();
    scrTbl = (cObj**) MEM_ALLOC(nScrWork * sizeof(cObj*), 1, 13);
    SmdClear(0);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    sourceWorldR200Qualify();
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    sourceWorldR11fQualify();
#endif
    return nScrWork;
}

// mode 0: forgets every scroll object; 1: forgets those belonging to a block (blk != -1), keeping
// the SetObjSmd ones.
void SmdClear(int mode)
{
    int i;
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
    re4dc_front_tpl_smd_clear();
#endif

    switch (mode) {
    case 0:
#if RE4DC_PS2_WORLD_R11F_OWNER
        sourceWorldR11fScrollClear();
#endif
#if RE4DC_PS2_WORLD_SOURCE_OWNER
        sourceWorldScrollClear();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        sourceWorldR200ScrollClear();
#endif
#endif
        memclr_asm(scrObjTbl, 250 * sizeof(cObj*));
        memclr_asm(scrTbl, nScrWork * sizeof(cObj*));
        break;
    case 1:
        for (i = 0; i < 250; i++) {
            // index-first integer address: the store through the plain pointer may alias the
            // scalar `scrObjTbl`, which is reloaded every iteration in the target.
            cObj** p = (cObj**) (i * sizeof(cObj*) + (u32) scrObjTbl);
            if (*p != NULL && (*p)->blk != -1) {
                *p = NULL;
            }
        }
        break;
    }
}

// Marks a new scroll object: kind 2, type 0, ot_type 3, no block yet, keeps moving in events.
void workInit(cObj* obj)
{
    obj->setNoSuspend(1);
    obj->kindid = 2;
    obj->type = 0;
    obj->ot_type = 3;
    obj->blk = -2;
}

// Creates the objects of the current SMD for scroll block `blk` (version check).
void SmdSetup(int blk)
{
    if (pSmd == NULL) {
        return;
    }
    if (pSmd->Version == 0) {
        pLog->err(0, 0, "ERROR! SmdSet() OLD version %02x.", pSmd->Version);
    }
    setObj(blk);
}

// Creates a cObj (createBack 2) for every used SmdWork (id != 0xFF), registers it by id (0xFE = not
// registered) and work index, gives it its model / motion / placement (SmdSetParam) and its SMX
// parameters; a work already owned by another block is an error. Returns -1 on a model failure.
int setObj(int blk)
{
    SmdWork* w = pSmd->getWorkPtr(0);
    cObj* obj;
    int i;

    for (i = 0; i < pSmd->nModel; i++, w++) {
        if (w->id == 0xFF) {
            continue;
        }
        obj = ObjMgr.createBack(2);
        if (obj == NULL) {
            pLog->err(0, 0, "SmdInit() setObj() CAN'T ALLOC cObj WORK %d", i);
            continue;
        }
        workInit(obj);
        if (scrObjTbl[w->id] == NULL && w->id != 0xFE) {
            scrObjTbl[w->id] = obj;
        }
        scrTbl[i] = obj;
        if (obj->blk != -2 && obj->blk != blk) {
            pLog->err(0, 0, "Smd::setObj() REDECLARATION WORK %d. BLK %d and %d", w->id, obj->blk, blk);
            continue;
        }
        obj->blk = blk;
        if (SmdSetParam(obj, w) == 0) {
            return -1;
        }
        if (pSmx != NULL && w->id != 0xFE) {
            smxInit(obj, w->id);
        }
        if (obj->type == 0) {
            obj->be_flag &= ~0x20;
        }
        obj->matUpdate();
#if RE4DC_PS2_WORLD_SOURCE_OWNER
        sourceWorldScrollBind(unsigned(i),obj);
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        sourceWorldR200ScrollBind(unsigned(i),obj);
#endif
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
        sourceWorldR11fScrollBind(unsigned(i),obj);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_NATIVE_STATIC
        re4dc_static_bind(obj, ((unsigned) pG->stage_no << 8) | pG->room_no, blk, i, w->binNo,
                          (w->flags & 0x10) != 0, obj->serial, &obj->mat[0][0]);
#endif
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_PS2_WORLD_DYNAMIC
        // PS2_WORLD_DYNAMIC (render only): the object registered under this id and its rest matrix, so the PS2
        // world follows the room code's moves and hides of it (native_static.cpp dyn).
        if (w->id < 250 && scrObjTbl[w->id] == obj) {
            re4dc_ps2_dyn_bind(((unsigned) pG->stage_no << 8) | pG->room_no, w->id, obj, &obj->be_flag, &obj->serial,
                               &obj->mat[0][0]);
#if RE4DC_PS2_WORLD_PARTS
            if (obj->pList && obj->nParts) {
                const unsigned char* part = (const unsigned char*) obj->pList;
                re4dc_ps2_dyn_parts(((unsigned) pG->stage_no << 8) | pG->room_no, w->id, obj, part, obj->nParts,
                    (const unsigned char*) &obj->pList->pList - part, (const unsigned char*) &obj->pList->pos - part
#if RE4DC_PS2_WORLD_ROOT_POSE
                    ,(const unsigned char*) &obj->pList->mat[0][0] - part
#endif
                    );
            }
#endif
        }
#endif
    }
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
    if(blk==-1)sourceWorldR200ScrollPublish();
#endif
#if RE4DC_PS2_WORLD_R11F_OWNER
    sourceWorldR11fScrollPublish();
#endif
    return 0;
}

// Model (bin / tpl from the room or the common SMD by flags bit4, with the common TPL table
// added), motion (bit6 = common), position / rotation / scale and a bounding-box light for one
// scroll object. Returns 0 when the model failed (object destroyed).
int SmdSetParam(cObj* obj, SmdWork* w)
{
    void* bin;
    void* tpl;
    void* mot;
    ModelBound* b;
    Vec size;

    obj->be_flag |= 4;
    obj->be_flag &= ~0x20;
    obj->x3D0 = w->b.x47;
    if (pSmd->Version <= 0x1F && w->motNo == 0) {
        w->motNo = 0xFF;
    }
    if (w->binNo == 0xFF) {
        w->binNo = 0;
        pLog->err(0, 0, "SmdInit() NULL BIN USED");
    }
    if (w->tplNo == 0xFF) {
        w->tplNo = 0;
        pLog->err(0, 0, "SmdInit() NULL TPL USED");
    }
    if (w->flags & 0x10) {
        bin = pSmdComn->getBinPtr(w->binNo);
        obj->be_flag |= 0x80000;
    } else {
        bin = pSmd->getBinPtr(w->binNo);
    }
    if (w->flags & 0x10) {
        tpl = DmyZeroTpl;
    } else {
        tpl = pSmd->getTplPtr(w->tplNo);
    }
    if (obj->modelInit(bin, tpl) == 0) {
        pLog->err(0, 0, "setObj() failed.");
        ObjMgr.destroy(obj);
        return 0;
    }
    if (pSmdComn != NULL) {
        u8* tbl = (u8*) pSmdComn + pSmdComn->TplTblOfs;
        obj->pModelInfo->addTplAddr(tbl + *(u32*) tbl);
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
        re4dc_front_tpl_smd_publish(obj->pModelInfo, DmyZeroTpl, pSmd, pSmdComn);
#endif
    }
    if (w->motNo != 0xFF) {
        if (w->flags & 0x40) {
            mot = pSmdComn->getMotPtr(w->motNo);
        } else {
            mot = pSmd->getMotPtr(w->motNo);
        }
        if (mot != NULL) {
            MotionSetCore(obj, &obj->pMotion, mot, 0, 0, 5, 0);
        }
    }
    obj->pos = w->pos;
    obj->ang = w->rot;
    obj->scale = w->scale;
    if (obj->scale.x == 0.0f || obj->scale.y == 0.0f || obj->scale.z == 0.0f) {
        pLog->warn(0, 0, "SmdInit() cObj SCALE SET 0.0");
    }
    b = &obj->pModelInfo->bound;
    size.x = b->size.x;
    size.y = b->size.y;
    size.z = b->size.z;
    obj->LightInfo.init2(2, 1, &obj->pModelInfo->bound.center, &size, 0x10);
    obj->matUpdate();
    obj->LightInfo.updateMatrix(obj);
    return 1;
}

// SMX display flags: bit0 be_flag 0x10, bit2 0x2000000, bit3 alpha_omit 0x80, bit4 0x8000, bit5
// x3D0 bit0.
void SmxSetFlag(cObj* obj, u32 flags)
{
    if (flags & 1) {
        obj->be_flag |= 0x10;
    }
    if (flags & 4) {
        obj->be_flag |= 0x2000000;
    } else {
        obj->be_flag &= ~0x2000000;
    }
    if (flags & 8) {
        obj->alpha_omit = 0x80;
    }
    if (flags & 0x10) {
        obj->be_flag |= 0x8000;
    }
    if (flags & 0x20) {
        obj->x3D0 |= 1;
    }
}

// The SMX flags an object currently shows (inverse of SmxSetFlag, plus bit1 from the model data).
int SmxGetFlag(cObj* obj)
{
    u32 be = obj->be_flag;
    int flags = 0;

    if (be & 0x10) {
        flags = 1;
    }
    if (obj->pModelInfo->pData->flags & 0x40000000) {
        flags |= 2;
    }
    if (be & 0x2000000) {
        flags |= 4;
    }
    if (obj->alpha_omit != 0xFF) {
        flags |= 8;
    }
    if (be & 0x8000) {
        flags |= 0x10;
    }
    if (obj->x3D0 & 1) {
        flags |= 0x20;
    }
    return flags;
}

// `pSmx` read directly in the loop test: gcse PRE re-loads it for the loop block and cse2 turns
// that into the `mr r10,r9` copy the loop uses; a `cSmx* smx = pSmx` local merges both reads.
void smxInit(cObj* obj, u8 id)
{
    SmxWork* w = pSmx->work;
    int i;

    for (i = 0; i < pSmx->nWork; i++, w++) {
        if (w->id == id) {
            smxInit(obj, w);
            return;
        }
    }
}

#if !defined(__PPC__)
// Source packed colors are numeric 0xRRGGBBAA, while GX-facing arrays are bytes.
static void NativeStoreSourceColor(u8* dst, u32 color)
{
    dst[0] = (u8) (color >> 24);
    dst[1] = (u8) (color >> 16);
    dst[2] = (u8) (color >> 8);
    dst[3] = (u8) color;
}
#endif

// Applies an SMX record: type / ot_type / cull mode / light mask / flags, the model colours
// (colour 0 alpha = blend mode), UV scroll, and the 0x78-byte work copied into the object; a
// non-zero type makes the object a moving one (be_flag 0x20).
void smxInit(cObj* obj, SmxWork* w)
{
    cModelInfo* mi;
    u32 col;

    if (w->id > 0xF9) {
        pLog->err(0, 0, "SmdInit() SMX WORK NUM ERR %d", w->id);
        return;
    }
    if ((u32) obj < RE4_MEM_LO || (u32) obj > RE4_MEM_HI || (obj->be_flag & 0x201) != 1) {
        pLog->err(0, 0, "SmdInit() SMX UNUSED cObj SELECT %d", w->id);
        return;
    }
    obj->type = w->type;
    obj->LightInfo.SelectMask = w->SelectMask;
    obj->ot_type = w->type2;
    SmxSetFlag(obj, w->flags);
    obj->CullMode = w->CullMode;
    mi = obj->pModelInfo;
    if (mi != NULL) {
        col = w->color;
#if defined(__PPC__)
        *(u32*) mi->color = col;
#else
        NativeStoreSourceColor(mi->color, col);
#endif
        if ((col & ~0xFF) == 0) {
            mi->color[0] = 0xFF;
            mi->color[1] = 0xFF;
            mi->color[2] = 0xFF;
        }
        col = w->color2;
#if defined(__PPC__)
        *(u32*) mi->color2 = col;
#else
        NativeStoreSourceColor(mi->color2, col);
#endif
        if ((col & ~0xFF) == 0) {
            mi->color2[3] = 0;
        } else {
            mi->color2[3] = 0xFF;
        }
        mi->blend_mode = mi->color[3];
        mi->color[3] = 0xFF;
        mi->uvScrollU = w->uvScrollU;
        mi->uvScrollV = w->uvScrollV;
        if (w->uvScrollU != 0.0f || w->uvScrollV != 0.0f) {
            mi->flagsDC |= 1;
        }
    }
    memcpy(obj->work, w->work, 0x78);
    if (obj->type == 0xF) {
        pLog->err(0, 0, "smxInit() : mirror model used.");
    }
    if (obj->type != 0) {
        obj->be_flag |= 0x20;
    }
}

// TPL `no` of the current SMD.
void* SmdGetTplPtr(int no)
{
    u8* tbl = (u8*) pSmd + pSmd->TplTblOfs;
    return tbl + ((u32*) tbl)[no];
}

// The scroll object with id `id` (0..0xF9); NULL (with an error unless the debug flags silence it)
// when unknown. Complains when the id is a group head.
cObj* SmdGetObjPtr(u32 id)
{
    cObj* obj;

    if (id > 0xF9) {
        if (pG->Debug_flg[0] & 0x80000000) {
            if (!(pG->Debug_flg[0] & 0x2000000)) {
                return NULL;
            }
        }
        {
            // The format string in a local: the string address is expanded before the pLog load,
            // so jump.c does not hoist the early `return NULL`s above the flag tests (the three
            // `li r3, 0` tails are cross-jumped instead) and each error block keeps its schedule.
            const char* s = "SmdGetObjPtr() invalid ID [%d] used";
            pLog->err(0, 0, s, id);
        }
        id = 0;
    }
    obj = scrObjTbl[id];
    if ((u32) obj < RE4_MEM_LO || (u32) obj > RE4_MEM_HI) {
        if (pG->Debug_flg[0] & 0x80000000) {
            if (!(pG->Debug_flg[0] & 0x2000000)) {
                return NULL;
            }
        }
        {
            const char* s = "SmdGetObjPtr(%d) invalid work";
            pLog->err(0, 0, s, id);
        }
        return NULL;
    }
    if (obj->x3D0 & 4) {
        pLog->err(0, 0, "SmdGetObjPtr(%d) GROUP -> SmdGetGroupObjPtr()", id);
    }
    return scrObjTbl[id];
}

// Number of SMD works.
int SmdGetObjNum()
{
    return nScrWork;
}

// The scroll id of `obj` (searching the groups too), -1 when it is none.
int SmdGetWorkId(cObj* obj)
{
    cObj* p;
    int i;

    for (i = 0; i < 250; i++) {
        for (p = scrObjTbl[i]; p != NULL; p = SmdGetGroupNext(p)) {
            if (p == obj) {
                return i;
            }
        }
    }
    return -1;
}

// Scroll block `blk` loaded: creates its objects from `smd`.
void BlockCreate(int blk, cSmd* smd)
{
    pSmd = smd;
    SmdSetup(blk);
}

// Scroll block `blk` unloaded: destroys its objects (kind 2 with that blk).
void BlockDestroy(int blk)
{
#if RE4DC_PS2_WORLD_SOURCE_OWNER
    // A block replacement invalidates the bounded whole-room witness.
    sourceWorldScrollClear();
#if RE4DC_PS2_WORLD_TRANSITION_OWNER
        sourceWorldR200ScrollClear();
#endif
#endif
    cObj* p = ObjMgr.pAlive;
    cObj* cur;
    cObj* next;

    // Entry test on the head, bottom test on `next` (pl_sub PlDataRelease shape).
    if (p != NULL) {
        do {
            cur = p;
            next = (cObj*) cur->pNext;
            p = next;
            if (cur->kindid == 2 && cur->blk == blk) {
                ObjMgr.destroy(cur);
            }
        } while (next != NULL);
    }
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_NATIVE_STATIC
    re4dc_static_retire_owner(blk);
#endif
}

// The SMD moved in memory by `ofs`: relocates the pointers inside every used bin and tpl.
void cSmd::slide(int ofs)
{
#if defined(RE4DC_FRONT_TPL_OWNER) && RE4DC_FRONT_TPL_OWNER
    re4dc_front_tpl_smd_slide(this);
#endif
    SmdWork* w = getWorkPtr(0);
    int nBin = 0;
    int nTpl;
    u32* tbl;
    u32 addr;
    int i;

    if ((u32) w < RE4_MEM_LO || (u32) w > RE4_MEM_HI) {
        pLog->err(0, 0, "cSmd::slide(%d) PTR ERROR", ofs);
        return;
    }
    for (i = 0; i < nModel; i++, w++) {
        if (w->id != 0xFF && !(w->flags & 0x10) && w->binNo + 1 > nBin) {
            nBin = w->binNo + 1;
        }
    }
    {
        // An integer base (not a pointer) ranks below the hoisted 0x02FFFFFF constant in the
        // callee-saved allocation (base r28, constant r29).
        u32 base = (u32) this + BinTblOfs;
        for (i = 0; i < nBin; i++) {
            addr = base + ((u32*) base)[i];
            if (addr < RE4_MEM_LO || addr > RE4_MEM_HI) {
                pLog->err(0, 0, "cSmd::slide() PTR ERR %08X", addr);
                return;
            }
            slideModelAddr(addr, ofs);
        }
    }
    nTpl = 0;   // set before the call: the pseudo crosses it and takes a callee-saved register
    w = getWorkPtr(0);
    for (i = 0; i < nModel; i++, w++) {
        if (w->id != 0xFF && !(w->flags & 0x10) && w->tplNo + 1 > nTpl) {
            nTpl = w->tplNo + 1;
        }
    }
    tbl = (u32*) ((u8*) this + TplTblOfs);
    for (i = 0; i < nTpl; i++) {
        slideTplAddr((u8*) tbl + tbl[i], ofs);
    }
}

// Work `no` (the works follow the group count table when Flag bit0).
SmdWork* cSmd::getWorkPtr(int no)
{
    return (Flag & 1) ? (SmdWork*) ((u8*) this + grp.nGroup * 4 + 0x14) : &work[no];
}

// Model bin `no`.
void* cSmd::getBinPtr(int no)
{
    u8* tbl = (u8*) this + BinTblOfs;
    return tbl + ((u32*) tbl)[no];
}

// Texture tpl `no`.
void* cSmd::getTplPtr(int no)
{
    u8* tbl = (u8*) this + TplTblOfs;
    return tbl + ((u32*) tbl)[no];
}

// Motion `no`.
void* cSmd::getMotPtr(int no)
{
    u8* tbl = (u8*) this + MotTblOfs;
    return tbl + ((u32*) tbl)[no];
}

// Works in the file including the group members.
int cSmd::getWorkNum()
{
    int n = nModel;
    u32 i;

    if (Flag & 1) {
        // guarded do-while + indexing: the loop test's second `grp.nGroup` read becomes the
        // `mr r10,r0` PRE copy, and `grp.num[i]` gives the `addi r3,r3,0x14` after the compare
        i = 0;
        if (i < grp.nGroup) {
            do {
                n += grp.num[i];
                i++;
            } while (i < grp.nGroup);
        }
    }
    return n;
}

// The SmdWork with scroll id `id`, or NULL.
SmdWork* SmdGetWorkPtr(int id)
{
    SmdWork* w;
    u32 i;

    for (i = 0; i < pSmd->getWorkNum(); i++) {
        w = pSmd->getWorkPtr(i);
        if (w->id == id) {
            return w;
        }
    }
    return NULL;
}

// The head object of scroll id `id` (groups allowed); NULL when unknown.
cObj* SmdGetGroupObjPtr(u32 id)
{
    cObj* obj;

    if (id > 0xF9) {
        if (pG->Debug_flg[0] & 0x80000000) {
            if (!(pG->Debug_flg[0] & 0x2000000)) {
                goto ng;
            }
        }
        {
            const char* s = "SmdGetObjPtr() invalid ID [%d] used";
            pLog->err(0, 0, s, id);
        }
        id = 0;
    }
    obj = scrObjTbl[id];
    if ((u32) obj < RE4_MEM_LO || (u32) obj > RE4_MEM_HI) {
        if (pG->Debug_flg[0] & 0x80000000) {
            if (!(pG->Debug_flg[0] & 0x2000000)) {
                goto ng;
            }
        }
        {
            const char* s = "SmdGetObjPtr(%d) invalid work";
            pLog->err(0, 0, s, id);
        }
        // The shared `return NULL` block sits after the second error call and the call jumps over
        // it to the normal return (the layout of the original).
        goto ok;
    ng:
        return NULL;
    }
ok:
    return scrObjTbl[id];
}

// Head object of `id` without any error reporting.
cObj* SmdGetGroupObjPtr2(u32 id)
{
    if (id > 0xF9) {
        return NULL;
    }
    return scrObjTbl[id];
}

// Next member of a scroll group (x3D0 bit2), NULL at the end.
cObj* SmdGetGroupNext(cObj* obj)
{
    if (!(obj->x3D0 & 4)) {
        return NULL;
    }
    return ObjMgr.getPrevWork(obj);
}

// Shows / hides (be_flag bit1) every object of scroll id `id`.
void SmdSetTrans(u32 id, int on)
{
    cObj* obj = SmdGetGroupObjPtr(id);

    if ((u32) obj < RE4_MEM_LO || (u32) obj > RE4_MEM_HI) {
        pLog->err(0, 0, "SmdSetTrans() INVALID INDEX %d", id);
        return;
    }
    do {
        if (on == 1) {
            obj->be_flag |= 2;
        } else {
            obj->be_flag &= ~2;
        }
        obj = SmdGetGroupNext(obj);
    } while (obj != NULL);
}

// A scenery object created by a room script (not from the SMD): blk -1, moving, bounding-box
// light with `lightFlag`; `front` puts it at the front of the object list.
cObj* SetObjSmd(void* bin, void* tpl, Vec* pos, Vec* rot, int lightFlag, int front)
{
    cObj* obj;
    cModelInfo* mi;
    ModelBound* b;
    Vec size;
    Vec d;

    if (front == 1) {
        obj = ObjMgr.create(2);
    } else {
        obj = ObjMgr.createBack(2);
    }
    if (obj == NULL) {
        return NULL;
    }
    if (obj->modelInit(bin, tpl) == 0) {
        ObjMgr.destroy(obj);
        return NULL;
    }
    obj->pos = *pos;
    obj->ang = *rot;
    obj->setNoSuspend(1);
    obj->be_flag |= 0x20;
    obj->blk = -1;
    mi = obj->pModelInfo;
    b = &mi->bound;
    size.x = b->size.x;
    size.y = b->size.y;
    size.z = b->size.z;
    PSVECSubtract(&mi->bound.center, &obj->pParts->pos, &d);
    obj->LightInfo.init2(2, 1, &d, &size, lightFlag);
    return obj;
}
