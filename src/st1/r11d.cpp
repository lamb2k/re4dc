#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "atari.h"
#include "light.h"
#include "map_obj.h"
#include "widget.h"
#include "flag_rsf.h"
#include "global.h"
#include "game.h"
#include "sce.h"
#include "sce_sys.h"
#include "sce_at.h"
#include "area.h"
#include "scroll.h"
#include "obj.h"
#include "obj00.h"
#include "obj13.h"
#include "em.h"
#include "emdoor.h"
#include "em_wrap.h"
#include "etc_model.h"
#include "esp.h"
#include "est.h"
#include "player.h"
#include "pl_npc.h"
#include "pl_sub.h"
#include "pad.h"
#include "item.h"
#include "mes.h"
#include "cam_ctrl.h"
#include "sscrn.h"
#include "snd.h"
#include "flr_at.h"
#include "rnd.h"

// PS2_ENEMY_ROOMS bit 0x80 (lane alivecap 2026-10-15): the PS2 r11d enemy rules (list rows from
// ps2_enemy_ch23.cpp under the same bit).
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23 && \
    defined(RE4DC_PS2_ENEMY_RULES) && RE4DC_PS2_ENEMY_RULES && \
    defined(RE4DC_PS2_ENEMY_ROOMS) && (RE4DC_PS2_ENEMY_ROOMS & 0x80)
#define CH23_PS2_ROOM 1
#include "libgpu.h"
extern "C" void OSPanic(const char* file, int line, const char* msg, ...);
#include "em_set.h"
#include "read.h"
#else
#define CH23_PS2_ROOM 0
#endif

// Room 1-1d (D:/Bio4/Prog/r11d.cpp): the two sisters (the big one on the balcony object, the
// little one with her own motion), the iron door key, the closet hides, the show view, the enemy
// reset waves, the thunder and the battle stream.

struct R11dWork {
    u8 eff0;              // 0x00  EspPullCoreKind() of the big sister's glow
    u8 eff1;              // 0x01  ... of the appear event
    u8 eff2;              // 0x02  ... of the show view
    u8 pad_3;
    cEmWrap em0;          // 0x04  the big sister
    cEmWrap em1;          // 0x10  the little sister
    cEm* door;            // 0x1C  the iron door (etc door 0x26)
    u32 strId;            // 0x20  SndStrReq handle of the show-view stream
    cModelInfo* mi;       // 0x24  the big sister's extra model
    cEmPatrol patrol[5];  // 0x28
#if CH23_PS2_ROOM
    cEmWrap ps2Em[23]; // source handles 0xB48..0xC50, indexed below
#endif
};

static R11dWork* r11d_work;
// The original's .data is 8-aligned (r105 has the same).
asm(".section .data; .balign 8");
static u8 r11d_hideCnt = 0;

// COMPILER-DIFF #4: the original passes the int list entries to the s16 parameters without
// truncation (`lwz` straight into r4); an int-parameter view of the callees.
int cEmWrapSetPtrI(cEmWrap* w, int no, int list, int errOn) asm("setPtr__7cEmWrapsSci");
cEm* setEmI(int no, int list, int errOn, int chkDead, int setAlive) asm("setEm__FsSciii");

// Pointer store through a reference: the work pointer is reloaded after it (see st_room.h).
static inline void PSet(cModelInfo*& d, cModelInfo* v) { d = v; }

static void r11d_checkIronDoorKeyUse();
static void r11d_checkIronDoor();
static void r11d_checkEmDead();
extern "C" void r11d_appearBigSister();
extern "C" void r11d_appearLittleSister();
static void r11d_execEmAppear_end();
static void r11d_execEmAppear();
extern "C" void r11d_setEmSister();
static void r11d_execShowView_end();
static void r11d_execShowView();
extern "C" void r11d_execHide_main(int mode, u32 objId);
static void r11d_execHide0(int mode);
static void r11d_execHide1(int mode);
static void r11d_execHide2(int mode);
static void r11d_checkDoor();
static void r11d_checkEmReset();
static void r11d_ThunderMove();
static void r11d_str_check();
#if CH23_PS2_ROOM
static void r11d_ps2Init();
static void r11d_ps2FirstArea();
static void r11d_ps2SecondArea();
static void r11d_ps2Reinforcement();
static void r11d_ps2RetreatArea();
#endif

// Room init (the village at night, the Bella sisters): rain on the player, Status_flg[1] 0x400; the
// enemy waves start on area 2 the first time (Room_flg bit 0) else at once; area 1 = the locked front
// door until door_unlock[0] 0x00010000; the sister effect data; closets 3/4/5 as hide spots; the show
// view once (bit 2) else thunder at once; area 6 = the sisters' appearance until bit 3 else they are
// re-set from flags; the iron door (etc 0x26, key item 0xB) on area 8 with its key-use watcher until
// door_unlock[0] 0x00100000; five two-point patrols between area pairs 0xA..0x13; ladder 1 camera 0xC.
void R11dInit()
{
    void* zero = 0;
    Vec pos[2];
    cEm* ladder;

#line 52 "D:/Bio4/Prog/r11d.cpp"
    r11d_work = (R11dWork*) MEM_CALLOC(sizeof(R11dWork), 1, 0xd);

    EstSet((int) pPL, -1, 0, 0, 3, 1, 0x800, 0, (u32) zero, zero);
    EstSet((int) pPL, -1, 0, 0, 1, 0, 0x800, 0, (u32) zero, zero);
    BitOn(pG->Status_flg[1], 0x400);
#if CH23_PS2_ROOM
    // PS2 R11dInit 0x12180: load the sisters' actor before the first trigger.
    EmReadSearch(GetEmIdFromList(0xE6), 0, 0);
#endif
    if (RsfCheck(G_ROOM_ID, 0) == 0) {
        SceAtDataSet_exec(2, SCE_LEVEL10, 0, (TaskFunc) r11d_checkEmReset, 0, 1);
    } else {
        SceExec(0x12, (TaskFunc) r11d_checkEmReset, 0, 0, SCE_PRIO_DEF_2, 0);
    }
    if (!(pG->door_unlock[0] & 0x00010000)) {
        SceAtDataSet_exec(1, SCE_LEVEL10, 0, (TaskFunc) r11d_checkDoor, 0, 1);
    } else {
        SmdGetObjPtr(0x20)->be_flag &= ~2;
    }
    EspDataLoad((u32) ROOM_ARC_PTR(pG->pRoom, 0x1F), 0xCA, 0);
    SceAtDataSet_hide(3, r11d_execHide0);
    SceAtDataSet_hide(4, r11d_execHide1);
    SceAtDataSet_hide(5, r11d_execHide2);
    if (RsfCheck(G_ROOM_ID, 2) == 0) {
        SceExec(0x12, (TaskFunc) r11d_execShowView, 0, 0, SCE_PRIO_DEF_2, 0);
    } else {
        SceExec(0x12, (TaskFunc) r11d_ThunderMove, 0, 0, SCE_PRIO_DEF_2, 0);
        SceExec(0x12, (TaskFunc) r11d_str_check, 0, 0, SCE_PRIO_DEF_2, 0);
    }
    if (RsfCheck(G_ROOM_ID, 3) == 0) {
        SmdGetObjPtr(0x1A)->be_flag &= ~2;
        SceAtDataSet_exec(6, SCE_LEVEL10, 0, (TaskFunc) r11d_execEmAppear, 0, 1);
    } else {
        r11d_setEmSister();
    }
    if (!(pG->door_unlock[0] & 0x00100000)) {
        if (getRoomEtcDoor(0x26, &r11d_work->door, 1)) {
            ((cEmDoor*) r11d_work->door)->setKey(0xB);
        }
        SceAtDataSet_exec(8, SCE_LEVEL10, 0, (TaskFunc) r11d_checkIronDoor, 0, 1);
        SceExec(0x12, (TaskFunc) r11d_checkIronDoorKeyUse, 0, 0, SCE_PRIO_DEF_2, 0);
    } else if (pG->pEmi != 0 && ((u8*) pG->pEmi)[0xD08] == 5) {
        ((u8*) pG->pEmi)[0xD08] = 0;
    }
#if !CH23_PS2_ROOM
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xA)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xB)->area);
    r11d_work->patrol[0].SetPatrol(0xE2, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xC)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xD)->area);
    r11d_work->patrol[1].SetPatrol(0xDD, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xE)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xF)->area);
    r11d_work->patrol[2].SetPatrol(0xE8, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0x10)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0x11)->area);
    r11d_work->patrol[3].SetPatrol(0xF5, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0x12)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0x13)->area);
    r11d_work->patrol[4].SetPatrol(0xE7, pos, 2, 0, 0);
#endif
    FlrAtSetDefVal(0, 0, 3);
    if (getRoomEtcLadder(1, &ladder, 1)) {
        ((cObjLadder*) ladder)->setCamera(0xC);
    }
#if CH23_PS2_ROOM
    r11d_ps2Init();
#endif
}


#if CH23_PS2_ROOM
// PS2 USA st1_3.rel 0x120d8..0x12d34. The wrappers below preserve the
// source cohort handles; their native layout is supplied by cEmWrap.
enum R11dPs2Em {
    PS2_E6, PS2_EC, PS2_DD, PS2_DF, PS2_E0, PS2_E1, PS2_E2, PS2_E3,
    PS2_E4, PS2_E5, PS2_E7, PS2_E8, PS2_F5, PS2_ED, PS2_EE, PS2_EF,
    PS2_F2, PS2_F3, PS2_F4, PS2_E9, PS2_EA, PS2_EB, PS2_DC
};
// Exact r11d_015.AEV areas 0x16..0x19. Area 0x18 sets event flag 64;
// the others execute once on the player's position, with room saves 6/7/9.
static AreaData r11dPs2Area[4] = {
    {1, AREA_TYPE_XZ4, 0, {{2833.07349f, 1620.34985f, 750.0f, {{-18199.6992f, 5811.51709f}, {-13973.1709f, 5819.13818f}, {-13948.8125f, 9331.8125f}, {-17925.8691f, 9151.66016f}}}}},
    {1, AREA_TYPE_XZ4, 0, {{-382.328033f, 1618.40002f, 750.0f, {{-9740.55957f, 6576.90479f}, {-4970.16016f, 8084.08545f}, {-5993.97998f, 10197.0381f}, {-11609.6094f, 9289.63477f}}}}},
    {1, AREA_TYPE_XZ4, 0, {{-0.00299072266f, 1000.0f, 750.0f, {{-13631.7705f, -906.314819f}, {-11114.1875f, -12203.1338f}, {-3398.29199f, -9296.87695f}, {-5603.91943f, 2493.67993f}}}}},
    {1, AREA_TYPE_XZ4, 0, {{-1418.703f, 2912.30005f, 750.0f, {{523.061707f, -2365.8042f}, {7062.33154f, -2077.96753f}, {6671.53662f, 2588.69043f}, {373.590088f, 2649.01172f}}}}},
};

// Append a PS2-only AEV record after its authored predecessor. Keep the free
// native number: restored item areas may already use the PS2 logical numbers.
// Runtime creation owns allocation/cleanup; the callbacks use save/event flags.
static SceAtWork* r11d_ps2Area(SceAtWork* prev, AreaData* area, int type)
{
    if (prev == 0 || prev->otNo != 2) {
        OSPanic(__FILE__, __LINE__, "ch23 r11d: unexpected AEV boundary");
        return 0;
    }
    Vec corners[4];
    for (int i = 0; i < 4; i++) {
        corners[i].x = area->u.xz4.p[i].x;
        corners[i].y = area->u.xz4.floor;
        corners[i].z = area->u.xz4.p[i].z;
    }
    int at = SceAtCreateExecAt(pPL, corners, 0, type == 4 ? 1 : 0x81,
                             1, area->u.xz4.height, 2, 0.0f, 0.0f,
                             0, 0, 0, 0, 0);
    SceAtWork* w = at >= 0 ? SceAtPtr(at) : 0;
    if (w == 0) {
        OSPanic(__FILE__, __LINE__, "ch23 r11d: PS2 AEV allocation failed");
        return 0;
    }
    DelPrim((u32*) sceAtSetOtStart(), (u32*) w);
    w->area = *area;
    w->type = type;
    w->pParent = 0;
    w->parentParts = 0;
    w->angleRange = 45;
    AddPrim((u32*) prev, (u32*) w);
    return w;
}

static void r11d_ps2Init()
{
    SceAtWork* prev = SceAtPtr(0x15);
    SceAtWork* areas[4];
    for (int i = 0; i < 4; i++) {
        SceAtWork* at = r11d_ps2Area(prev, &r11dPs2Area[i], i == 2 ? 4 : 2);
        areas[i] = at;
        prev = at;
        if (i == 2 && at != 0) {
            at->flg.kind = 0;
            at->flg.off = 0;
            at->flg.no = 64;
        }
    }
    if (areas[0] != 0 && RsfCheck(G_ROOM_ID, 6) == 0) {
        SceAtDataSet_exec(areas[0]->no, SCE_LEVEL10, 0, (TaskFunc) r11d_ps2FirstArea, 0, 1);
    }
    if (areas[1] != 0 && RsfCheck(G_ROOM_ID, 7) == 0) {
        SceAtDataSet_exec(areas[1]->no, SCE_LEVEL10, 0, (TaskFunc) r11d_ps2SecondArea, 0, 1);
    }
    if (areas[3] != 0 && RsfCheck(G_ROOM_ID, 9) == 0) {
        SceAtDataSet_exec(areas[3]->no, SCE_LEVEL10, 0, (TaskFunc) r11d_ps2RetreatArea, 0, 1);
    }
    r11d_work->ps2Em[PS2_DC].setEm(0xDC, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_DF].setEm(0xDF, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E0].setEm(0xE0, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E1].setEm(0xE1, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E3].setEm(0xE3, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E4].setEm(0xE4, -1, 0, 1, 1);
    SceExec(0x12, (TaskFunc) r11d_ps2Reinforcement, 0, 0, SCE_PRIO_DEF_2, 0);
}

// 0x12678: replace the entry cohort with the five held patrols.
static void r11d_ps2FirstArea()
{
    Vec pos[2];
    RsfSet(G_ROOM_ID, 6);
    r11d_work->ps2Em[PS2_DF].destroy();
    r11d_work->ps2Em[PS2_E0].destroy();
    r11d_work->ps2Em[PS2_E1].destroy();
    r11d_work->ps2Em[PS2_E3].destroy();
    r11d_work->ps2Em[PS2_E4].destroy();
    r11d_work->ps2Em[PS2_E5].destroy();
    r11d_work->ps2Em[PS2_DD].setEm(0xDD, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E2].setEm(0xE2, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E7].setEm(0xE7, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E8].setEm(0xE8, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_F5].setEm(0xF5, -1, 0, 1, 1);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xA)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xB)->area);
    r11d_work->patrol[0].SetPatrol(0xE2, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xC)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xD)->area);
    r11d_work->patrol[1].SetPatrol(0xDD, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0xE)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0xF)->area);
    r11d_work->patrol[2].SetPatrol(0xE8, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0x10)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0x11)->area);
    r11d_work->patrol[3].SetPatrol(0xF5, pos, 2, 0, 0);
    AreaGetCenterPos(&pos[0], &SceAtPtr(0x12)->area);
    AreaGetCenterPos(&pos[1], &SceAtPtr(0x13)->area);
    r11d_work->patrol[4].SetPatrol(0xE7, pos, 2, 0, 0);
    SceExit();
}

// 0x12928: after the sisters, replace ED/F2/F4 with EF/E9/EA/EB.
static void r11d_ps2SecondArea()
{
    RsfSet(G_ROOM_ID, 7);
    r11d_work->ps2Em[PS2_ED].setPtr(0xED, -1, 0);
    r11d_work->ps2Em[PS2_F2].setPtr(0xF2, -1, 0);
    r11d_work->ps2Em[PS2_F4].setPtr(0xF4, -1, 0);
    r11d_work->ps2Em[PS2_ED].destroy();
    r11d_work->ps2Em[PS2_F2].destroy();
    r11d_work->ps2Em[PS2_F4].destroy();
    r11d_work->ps2Em[PS2_EF].setEm(0xEF, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_E9].setEm(0xE9, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_EA].setEm(0xEA, -1, 0, 1, 1);
    r11d_work->ps2Em[PS2_EB].setEm(0xEB, -1, 0, 1, 1);
    SceExit();
}

// 0x12a68: one reinforcement after area 0x18 when any entry guard is inactive.
static void r11d_ps2Reinforcement()
{
    SceSleep(2);
    for (;;) {
        if (RsfCheck(G_ROOM_ID, 8) == 0 && (pG->Room_flg[2] & 0x80000000)) {
            if (!r11d_work->ps2Em[PS2_DF].isActive() ||
                !r11d_work->ps2Em[PS2_E0].isActive() ||
                !r11d_work->ps2Em[PS2_E1].isActive() ||
                !r11d_work->ps2Em[PS2_E3].isActive() ||
                !r11d_work->ps2Em[PS2_E4].isActive()) {
                r11d_work->ps2Em[PS2_E5].setEm(0xE5, -1, 0, 1, 1);
                RsfSet(G_ROOM_ID, 8);
            }
        }
        SceSleep(1);
    }
}

// 0x12b70: the active rear guards run to the first authored target; inactive
// sisters are released. The PS2 copies three vectors but passes &target[0]
// at all three setGoto sites (0x12c2c/0x12c54/0x12c7c).
static void r11d_ps2RetreatArea()
{
    Vec target = {5440.0f, 3200.0f, -2220.0f};
    RsfSet(G_ROOM_ID, 9);
    r11d_work->ps2Em[PS2_ED].setPtr(0xED, -1, 0);
    r11d_work->ps2Em[PS2_F2].setPtr(0xF2, -1, 0);
    r11d_work->ps2Em[PS2_F4].setPtr(0xF4, -1, 0);
    if (r11d_work->ps2Em[PS2_ED].isActive()) r11d_work->ps2Em[PS2_ED].setGoto(&target, 1);
    if (r11d_work->ps2Em[PS2_F2].isActive()) r11d_work->ps2Em[PS2_F2].setGoto(&target, 1);
    if (r11d_work->ps2Em[PS2_F4].isActive()) r11d_work->ps2Em[PS2_F4].setGoto(&target, 1);
    r11d_work->ps2Em[PS2_E6].setPtr(0xE6, -1, 0);
    r11d_work->ps2Em[PS2_EC].setPtr(0xEC, -1, 0);
    if (r11d_work->ps2Em[PS2_E6].isAlive() && !r11d_work->ps2Em[PS2_E6].isActive()) {
        r11d_work->ps2Em[PS2_E6].destroy();
    }
    if (r11d_work->ps2Em[PS2_EC].isAlive() && !r11d_work->ps2Em[PS2_EC].isActive()) {
        r11d_work->ps2Em[PS2_EC].destroy();
    }
    SceExit();
}
#endif

// Per-frame room main: nothing.
void R11dMain()
{
}

// Once the player holds the key the iron door area unlocks.
static void r11d_checkIronDoorKeyUse()
{
    while (ItemMgr.check(0x8C) != 1) {
        SceSleep(1);
    }
    pG->door_unlock[0] |= 0x00100000;
    SceUpCut(2, -1, 2, 0);
    SceAtSetEnable(8, 0);
    GameSaveSave(&GameSave, pSaveData, -1);
    if (pG->pEmi != 0 && ((u8*) pG->pEmi)[0xD08] == 5) {
        ((u8*) pG->pEmi)[0xD08] = 0;
    }
}

// The locked iron door: the up-cut message, or the key use through the sub screen.
static void r11d_checkIronDoor()
{
    if (ItemMgr.num(0x8C) == 0) {
        SceUpCut(1, -1, 3, UP_CUT_ATTR_CUT_FIX);
        CamCtrl.Comeback(0);
    } else {
        SndCall(6, 3, 0, 0, 0, 0);
        SubScreenOpen(SS_OPEN_ITEM, SS_ATTR_EVENT);
    }
}

// The big sister's item was taken: her glow goes away.
static void r11d_checkEmDead()
{
    while (SceAtItemFlgCk(0x80) == 0) {
        SceSleep(1);
    }
    RsfSet(G_ROOM_ID, 4);
    BitOff(r11d_work->mi->be_flag, 8);
    EffectEspDelete(0, r11d_work->eff0, 0, 0);
    EffectEspgenDelete(0, r11d_work->eff0, 0);
    EffectEfmDelete(0, r11d_work->eff0, 0);
}

// The big sister on the balcony object with her glow.
extern "C" void r11d_appearBigSister()
{
    void* zero = 0;

    r11d_work->em0.setEm(0xE6, -1, 0, 1, 1);
    BitOn(pG->Room_flg[0], 0x80000000);
    if (r11d_work->em0.isAlive() == 1) {
        Vec pos = {0.0f, -2.0f, 180.0f};
        Vec rot = {0.0f, 0.0f, 0.0f};
        cObj* obj;

        obj = SetObj00((void*) (pG->pArc->ofs_20 + (u32) pG->pArc), (void*) (pG->pArc->ofs_24 + (u32) pG->pArc), &pos, &rot);
        OyaSetObj00(obj, r11d_work->em0.getPtr(), 2);
        obj->setNoSuspend(1);
        PSet(r11d_work->mi, ModInfoMgr.create(ROOM_ARC_PTR(pG->pRoom, 0x21), ROOM_ARC_PTR(pG->pRoom, 0x22)));
        if (r11d_work->mi != 0) {
            r11d_work->em0.addModel(r11d_work->mi);
        }
        r11d_work->eff0 = EspPullCoreKind();
        EstSet((int) obj, -1, 0, 0, 0, 0x2D, 0x801, r11d_work->eff0, (u32) zero, zero);
        SceExec(0x12, (TaskFunc) r11d_checkEmDead, 0, 0, SCE_PRIO_DEF_2, 0);
    }
}

// The little sister with her own motion; the first time the two flash effects.
extern "C" void r11d_appearLittleSister()
{
    if (r11d_work->em1.setEm(0xEC, -1, 0, 1, 1) == 1) {
        cEm* em = r11d_work->em1.getPtr();

        if (em != 0) {
            ((cEmGanado*) em)->setR11DMotion(ROOM_ARC_PTR(pG->pRoom, 0x23));
        }
    }
    // The two EstSet stack zeros come from one callee-saved `li r31,0` set here (after the join).
    int zero = 0;
    pG->Room_flg[0] |= 0x40000000;
    BitOff(SmdGetObjPtr(0x32)->be_flag, 2);
    BitOn(SmdGetObjPtr(0x1A)->be_flag, 2);
    if (RsfCheck(G_ROOM_ID, 5) == 0) {
        RsfSet(G_ROOM_ID, 5);
        EstSet(0, -1, 0, 0, 1, 7, 1, 0, (u32) zero, (void*) zero);
    }
    // Outside the `if`: the original's `bne` skips only the first EstSet (a source-logic bug had both
    // inside, which also gave the first call's `li`s output dependents and sank its stack stores).
    EstSet(0, -1, 0, 0, 1, 8, 1, 0, (u32) zero, (void*) zero);
}

// End of the sisters' appearance: set them from flags, drop the flash effect, let them suspend, camera
// back, SceEventEnd, clear Status_flg[2] 0x02000000 / Room_flg[0] 0x20000000; destroy the first-wave
// Ganados that are not carrying Ashley away (ckTakeAway) and spawn the second list (9 entries); a ladder
// left in state 4 is reset.
static void r11d_execEmAppear_end()
{
    u32 i;

    r11d_setEmSister();
    if (r11d_work->eff1 != 0) {
        EffectEspDelete(0, r11d_work->eff1, 0, 0);
        EffectEspgenDelete(0, r11d_work->eff1, 0);
        EffectEfmDelete(0, r11d_work->eff1, 0);
    }
    r11d_work->em0.setNoSuspend(0);
    r11d_work->em1.setNoSuspend(0);
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    BitOff(pG->Status_flg[2], 0x02000000);
    BitOff(pG->Room_flg[0], 0x20000000);
    int list0[11] = {0xDD, 0xDF, 0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE7, 0xE8, 0xF5};
#if CH23_PS2_ROOM
    // PS2 0x1346c..0x1349c; the remaining rear cohort is sent by area 0x17.
    int list1[3] = {0xED, 0xF2, 0xF4};
#else
    int list1[9] = {0xED, 0xEE, 0xEF, 0xF2, 0xF3, 0xF4, 0xE9, 0xEA, 0xEB};
#endif
    cEm* ladder;
    for (i = 0; i < 11; i++) {
        cEmWrap em;
        cEmWrapSetPtrI(&em, list0[i], -1, 0);
        if (!(em.isAlive() == 1 && ((cEmGanado*) em.getPtr())->ckTakeAway() == 1)) {
            em.destroy();
        }
    }
#if CH23_PS2_ROOM
    for (i = 0; i < 3; i++) {
#else
    for (i = 0; i < 9; i++) {
#endif
        setEmI(list1[i], -1, 0, 1, 1);
    }
    if (getRoomEtcLadder(0, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 4) {
        ((cObjLadder*) ladder)->setStand();
    }
    if (getRoomEtcLadder(0x27, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 4) {
        ((cObjLadder*) ladder)->setStand();
    }
}

// The sisters appear: the player is thrown, the big sister falls from the balcony, the little one
// comes in.
static void r11d_execEmAppear()
{
    RsfSet(G_ROOM_ID, 3);
    pG->Room_flg[0] |= 0x20000000;
    while (PlGetStatus() & 0x80000) {
        SceSleep(1);
    }
    pPL->dmg.set(0, 0x80);
    KeyStop(0xEFCF0000ULL);
    SceSleep(15);
    SceEventStart(0);
    BitOn(pG->Status_flg[2], 0x02000000);
    pPL->setNoSuspend(1);
    r11d_work->eff1 = 0;
    SceSetEventCancel(1, (TaskFunc) r11d_execEmAppear_end, 0, -1, 1);
    pPL->setNoSuspend(1);
    SndRoomStrStart(1, 0, 1);
    SndStrReq(1, 8, 0x80000003, 0, 0, 0.0f);
    r11d_appearBigSister();
    r11d_work->em0.setNoSuspend(1);
    r11d_work->eff1 = EspPullCoreKind();
    EstSet(0, -1, 0, 0, 1, 9, 1, r11d_work->eff1, 0, 0);
    CamCtrl.CutCall(4);
    while (CamCtrl.IsMotionEnd() == 0) {
        SceSleep(1);
    }
    EffectEspDelete(0, r11d_work->eff1, 0, 0);
    EffectEspgenDelete(0, r11d_work->eff1, 0);
    EffectEfmDelete(0, r11d_work->eff1, 0);
    EstSet(0, -1, 0, 0, 1, 0xA, 1, r11d_work->eff1, 0, 0);
    CamCtrl.CutCall(5);
    if (r11d_work->em0.isAlive() == 1) {
        while (r11d_work->em0.getPosY() > 300.0f) {
            SceSleep(1);
        }
    }
    SceSleep(30);
    while (CamCtrl.IsMotionEnd() == 0) {
        SceSleep(1);
    }
    r11d_work->em0.setNoSuspend(0);
    EffectEspDelete(0, r11d_work->eff1, 0, 0);
    EffectEspgenDelete(0, r11d_work->eff1, 0);
    EffectEfmDelete(0, r11d_work->eff1, 0);
    r11d_appearLittleSister();
    r11d_work->em1.setNoSuspend(1);
    CamCtrl.CutCall(6);
    while (CamCtrl.IsMotionEnd() == 0) {
        SceSleep(1);
    }
    r11d_execEmAppear_end();
}

// The sisters already met: set them again from the saved flags.
extern "C" void r11d_setEmSister()
{
    if (RsfCheck(G_ROOM_ID, 4) == 0 && !(pG->Room_flg[0] & 0x80000000)) {
        r11d_appearBigSister();
    }
    if (!(pG->Room_flg[0] & 0x40000000)) {
        r11d_appearLittleSister();
    }
}

// End of the show view: drop its effect, fade the stream (50 frames), camera back, SceEventEnd, then
// start the battle-stream and thunder tasks and autosave.
static void r11d_execShowView_end()
{
    EffectEspDelete(0, r11d_work->eff2, 0, 0);
    EffectEspgenDelete(0, r11d_work->eff2, 0);
    EffectEfmDelete(0, r11d_work->eff2, 0);
    SndStrReq(r11d_work->strId, 4, 50, 0);
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    SceExec(0x12, (TaskFunc) r11d_str_check, 0, 0, SCE_PRIO_DEF_2, 0);
    SceExec(0x12, (TaskFunc) r11d_ThunderMove, 0, 0, SCE_PRIO_DEF_2, 0);
    GameSaveSave(&GameSave, pSaveData, -1);
}

// Show the room: camera cuts 2 and 3 with the stream and the glow.
static inline f32 FCRef(const f32& v) { return v; }

// One-shot (Room_flg bit 2) on entry: stream 0x16, event start, camera cuts 2 then 3 over the village
// with a rain effect; player-cancellable.
static void r11d_execShowView()
{
    // The 0.0 is loaded after the RsfSet store: a pool constant would move above it (pool loads never
    // depend on stores), a `static const` read through a reference stays below (docs/matching.md, cSceObj).
    static const f32 vol = 0.0f;
    void* zero = 0;

    RsfSet(G_ROOM_ID, 2);
    r11d_work->strId = SndStrReq(0, 0x16, 0x80000003, 0, 0, FCRef(vol));
    SceSetEventCancel(1, (TaskFunc) r11d_execShowView_end, 0, -1, 1);
    SceEventStart(1);
    pG->Status_flg[1] &= ~0x10000000;
    r11d_work->eff2 = EspPullCoreKind();
    EstSet(0, -1, 0, 0, 1, 3, 1, r11d_work->eff2, (u32) zero, zero);
    CamCtrl.CutCall(2);
    while (CamCtrl.IsMotionEnd() == 0) {
        SceSleep(1);
    }
    CamCtrl.CutCall(3);
    while (CamCtrl.IsMotionEnd() == 0) {
        SceSleep(1);
    }
    r11d_execShowView_end();
}

// The closet door `objId` swings open (mode 0) or closed while Ashley hides.
extern "C" void r11d_execHide_main(int mode, u32 objId)
{
    cObj* door;

    door = SmdGetObjPtr(objId);
    door->be_flag |= 0x20;
    if (mode == 0) {
        const f32 lim = -1.692f;
        const f32 add = 0.1f;
        f32 spd = 0.0f;

        // A real loop (LOOP_BEG note after the call = sched1 barrier: the entry jump depends on the
        // li r4..r8 but not on li r3, which the call re-sets, so `li r3,6` is issued last as in the
        // target). The asm keeps jump1 from peeling the exit test (asm_noperands in the exit code).
        SndCall(6, 0x14, &pSUB->pos, 0, 0, 0);
        for (;;) {
            door->pParts->ang.x -= spd;
            asm("" : "+f"(spd)); // COMPILER-DIFF: candidate #9
            spd += add;
            if (door->pParts->ang.x < lim) {
                break;
            }
            SceSleep(1);
        }
        door->pParts->ang.x = lim;
    } else {
        SndCall(6, 0x13, &pSUB->pos, 0, 0, 0);
        goto close;
    wait_close:
        SceSleep(1);
    close:
        door->pParts->ang.x += 0.2f;
        if (!(door->pParts->ang.x > 0.0f)) {
            goto wait_close;
        }
        door->pParts->ang.x = 0.0f;
    }
}

// Closet 3: the first hide sets the flag and the camera cut; later ones count up to the reset.
static void r11d_execHide0(int mode)
{
    if (mode == 0) {
        if (RsfCheck(G_ROOM_ID, 1) == 0) {
            RsfSet(G_ROOM_ID, 1);
            SceAtPtr(3)->hide.cut = 8;
        } else {
            r11d_hideCnt++;
            if (r11d_hideCnt > 7) {
                RsfClear(G_ROOM_ID, 1);
                r11d_hideCnt = mode;
            }
            SceAtPtr(3)->hide.cut = 0xC;
        }
    }
    r11d_execHide_main(mode, 0x23);
}

// Closet 4 hide spot: door object 0x27.
static void r11d_execHide1(int mode)
{
    r11d_execHide_main(mode, 0x27);
}

// Closet 5 hide spot: door object 0x25.
static void r11d_execHide2(int mode)
{
    r11d_execHide_main(mode, 0x25);
}

// The front door the first time: camera cut 10, the barred window and the message.
static void r11d_checkDoor()
{
    SceEventStart(0);
    CamCtrl.CutCall(0xA);
    SceSleep(15);
    SmdSetTrans(0x20, 0);
    pG->door_unlock[0] |= 0x00010000;
    SndCall(6, 0xB, 0, 0, 0, 0);
    SceMesSet(0, 0, 1, 0x64, 0x150 - cMes.getWork()->lineSpace - cMes.getWork()->m_font_h - 1);
    SceAtDataReset(1);
    CamCtrl.Comeback(0);
    SceEventEnd(0);
}

// The enemy waves: one more Ganado every second while fewer than 11 are alive.
static void r11d_checkEmReset()
{
    int i;

    RsfSet(G_ROOM_ID, 0);
    u8 tbl[10] = {0xD2, 0xD7, 0xD3, 0xD8, 0xD4, 0xD9, 0xD5, 0xDA, 0xD6, 0xDB};
    u8* t = tbl;
    // Layout of the target: `bl SceSleep; b CHECK`, the 60-frame sleep falling into the wait loop's
    // body (one SceSleep(1) copy shared by the first wait and the re-waits), the count test, setEm, and
    // the exit as the fall-through of `bne sleep` -- no labelled empty exit block, so haifa forms one
    // region for the whole loop and hoists setEm's `li r4..r7` above the count compare. `i++` in the
    // test puts the `addi` between the compare and the branch; `t` keeps the array base in one pseudo.
    SceSleep(1);
    i = 0;
    goto check;
sleep:
    SceSleep(60);
    do {
        SceSleep(1);
    check:;
#if CH23_PS2_ROOM
    } while ((u32) SceCountEmAlive(0x10, 0x20) >= 5);
    // PS2 0x13ff0..0x14038: below five, then immediately find the player.
    cEm* em = setEm(t[i], -1, 0, 1, 1);
    if (em != 0) {
        ((cEmGanado*) em)->setFindPL();
    }
#else
    } while ((u32) SceCountEmAlive(0x10, 0x20) > 10);
    setEm(t[i], -1, 0, 1, 1);
#endif
    // The `do { } while (0)` puts the test's block at loop depth 2 (weighted refs of `i` 5 -> 8), so
    // global-alloc ranks `i` above `t` (r31/r30 as in the original).
    do {
        if (i++ != 9) {
            goto sleep;
        }
    } while (0);
}

// Thunder every 90..235 frames, paused during the appear event.
static void r11d_ThunderMove()
{
    int cnt;

    SceSleep(1);
    {
        u8 r = Rnd() % 30;
        cnt = r * 5 + 90;
    }
    for (;;) {
        while (pG->Room_flg[0] & 0x20000000) {
            SceSleep(1);
        }
        if (cnt == 0) {
            if (!(pG->Status_flg[1] & 0x02000000)) {
                EstSet(0, -1, 0, 0, 1, 1, 1, 0, 0, 0);
            }
            {
                u8 r = Rnd() % 30;
                cnt = r * 5 + 90;
            }
            SceSndCallThunder();
        }
        cnt--;
        SceSleep(1);
    }
}

// Battle stream while a Ganado within 30 m has found the player.
static void r11d_str_check()
{
    int on = 0;
    f32 dist;

    for (;;) {
        int find = 0;

        if (SceCkFindPL(&dist) == 1 && dist < 30000.0f) {
            find = 1;
        }
        if (find == 1) {
            if (on == 0) {
                SndRoomStrStart(1, 0, 1);
                on = 1;
            }
        } else {
            if (on == 1) {
                SndRoomStrStop(3);
                on = 0;
            }
        }
        SceSleep(1);
    }
}
