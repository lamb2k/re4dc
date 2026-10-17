#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "map_obj.h"
#include "light.h"
#include "widget.h"
#include "atari.h"
#include "flag_rsf.h"
#include "global.h"
#include "sce.h"
#include "sce_sys.h"
#include "sce_at.h"
#include "scroll.h"
#include "obj.h"
#include "em.h"
#include "em_set.h"
#include "em_wrap.h"
#include "etc_model.h"
#include "player.h"
#include "cam_ctrl.h"
#include "mes.h"
#include "item.h"
#include "item_model.h"
#include "sscrn.h"
#include "snd.h"
#include "est.h"
#include "esp.h"
#include "game.h"
#include "rnd.h"
#include "vec.h"
#include "cSceObj.h"

// Room 3-27 (D:/Bio4/Prog/r327.cpp): the ganado camp with its two lamp switches, the card reader, the
// gatling ganado, the re-appearing enemy groups and the switch the ganado disables.

// A way-point runner: cEmControl's points run once in setGoto mode 0xD.
class cEmRun : public cEmControl {
public:
    int run;   // 0x11C  1 while a route is being run

    int SetRoute(s16 no, Vec* tbl, int n);
    int Move();
};

// One room enemy: the handle, its list entry and its route runner.
struct R327Em {
    cEmWrap em;    // 0x000
    int set;       // 0x00C  1 once setEm was called for it
    cEmRun run;    // 0x010
    int id;        // 0x130  enemy list entry
};

struct R327Work {
    R327Em em[32];   // 0x0000
    cEmWrap em2;     // 0x2680  the ganado that disables the switch (list 0x9E)
    cObj* sw;        // 0x268C  the switch model while it moves
    int first;       // 0x2690  1 on the first visit (enemies from the tables)
};

// {work slot, enemy list entry}
struct R327EmTbl {
    int idx;
    int id;
};

// One-member struct: the work pointer is reloaded after every store through the work (the r229 idiom).
struct R327WorkPtr {
    R327Work* p;
};

static R327WorkPtr r327_work;

// The table entries are passed to cEmWrap::setEm as ints (no s16 truncation at the call: COMPILER-DIFF 4,
// the r204/r205/r21d int view of the member).
int cEmWrapSetEmI(cEmWrap* w, int no, int list, int errOn, int chkDead, int setAlive) asm("setEm__7cEmWrapsSciii");
int cEmRunSetRouteI(cEmRun* r, int no, Vec* tbl, int n) asm("SetRoute__6cEmRunsP3Veci");

// Typed view of pG->emlist (the r400 idiom).
struct EmListView {
    u8 pad[0x52E8];
    EmListData emlist[0x100];
};
#define EM_LIST_V(no) (((EmListView*) pG)->emlist[(no)])

// The original object's .data is 8-aligned (0x170 in the REL after r320's 0x16c).
asm(".section .data; .balign 8");
static R327EmTbl r327_firstTbl[11] = {
    {0, 0x79}, {1, 0x7A}, {2, 0x7B}, {4, 0x7D}, {5, 0x81}, {6, 0x82}, {7, 0x85}, {8, 0x86}, {9, 0x8E}, {10, 0x93}, {30, 0x9C},
};
static R327EmTbl r327_tblA[2] = {{18, 0x8B}, {19, 0x90}};
static R327EmTbl r327_tblB[3] = {{15, 0x80}, {16, 0x87}, {17, 0x88}};
static R327EmTbl r327_tblC[2] = {{11, 0x7E}, {12, 0x7F}};
static R327EmTbl r327_tblD[2] = {{13, 0x89}, {14, 0x8A}};
static R327EmTbl r327_appearTbl[2][4] = {
    {{22, 0x91}, {23, 0x92}, {24, 0x94}, {25, 0x96}},
    {{26, 0x97}, {27, 0x98}, {28, 0x99}, {29, 0x9A}},
};

int r327_EnemySetSub(R327EmTbl* a, u32 na, R327EmTbl* b, u32 nb);
static void r327_EnemySet();
static void r327_GatlingGanadoSet();
static void r327_GatlingGanadoSetEndProc(int idx);
static void r327_SwitchOperate(int no);
static void r327_LampSet(int no);
void r327_LampSetEndProc();
static void r327_GanadoAppearCut();
static void r327_GanadoAppearCutEndProc(int side);
static void r327_CheckDoor();
static void r327_DoorOpen();
static void r327_DoorOpenEndProc(int se);
static void r327_GanadoGotoCheck();
static void r327_CheckCardReader();
static void r327_CheckUseCardKey();
static void r327_SetSwitchEnable();
static void r327_SetSwitchEnableEndProc();
static void r327_SetSwitchDisable();
static void r327_SetSwitchDisableEndProc();
static void r327_EnemySet2nd();
static void r327_ContinuePointSet();
static void r327_StrCheck();
static void r327_BoxOpen(u32 id);
static void r327_BoxOpened(u32 id);

#if !defined(RE4DC_PS2_ENEMY_ST3)
#define RE4DC_PS2_ENEMY_ST3 0
#endif
// PS2_ENEMY_ST3 bit 2 (stage 3 lane, PS2-ENEMY-CODE-DIFF-20261015): the PS2 USA r327 camp (st3_3). R327Init sends
// 9 of the 11 first Ganados (0x7B / 0x93 held); a PS2-only task (0x107c0) sends 0x8F, 0x93, 0x7B one by one while
// fewer than 8 are alive and Leon is inside the PS2 flag area 0x1C (r327.dat AEV, Room_flg[2] bit 31). EnemySetSub
// (0x10908) sends its second table only while alive(0x1D) < 9 and alerts both (setFindPL). GanadoAppearCut
// (0x113d8) runs EmFarDelete(5, any view), always opens with side 0 (0x94 0x96 0x99 0x9A), then sends side 1
// (0x92 0x91 0x98 0x97) from index (alive - 1) on. The gatling cut (0x10dd8) runs the room-local r327EmFarDelete(8)
// (0x12f20). EnemySet2nd (0x12b30) sends 0x83 / 0x84 once, only while alive(0x1D) < 8. Default 0: GameCube code.

// ALIVE_CAP (ch5found16 10-17): a send the cap holds is set here but not active yet. The gatling trigger counts set and
// inactive slots as dead; on the PS2 a held Ganado is alive, so it is not counted (at cap 4 the 5 held first-table
// sends fired the gatling cut at room entry, and its far delete (keep 8, alive 10) then removed 2 live Ganados).
#if defined(RE4DC_ALIVE_CAP_ON) && RE4DC_ALIVE_CAP_ON
extern "C" int re4dc_aliveCapIsHeld(int no);
extern "C" int re4dc_aliveCapHeldCount(int lo, int hi);
extern "C" int re4dc_aliveCapFarDrop(int max, int clearAlive);
static inline int r327_capHeld(int no) { return re4dc_aliveCapIsHeld(no); }
#else
static inline int r327_capHeld(int no) { (void) no; return 0; }
#endif
#define R327_PS2 (RE4DC_PS2_ENEMY_ST3 & 4)
#if R327_PS2
#include "em_far_delete.h"
#include "area.h"

// PS2 r327.dat AEV 0x1C (type 4 flag area, payload flag 0x4000: Room_flg[2] bit 31 while Leon is inside).
static AreaData r327Ps2Area1C = {1, AREA_TYPE_XZ4, 0, {{6073.498f, 1000.0f, 750.0f,
    {{-29959.08f, 17694.914f}, {-5803.9912f, 18114.957f}, {-6132.836f, 50690.387f}, {-31227.494f, 50795.023f}}}}};
static const R327EmTbl r327ps2_firstTbl[9] = {
    {0, 0x79}, {1, 0x7A}, {4, 0x7D}, {5, 0x81}, {6, 0x82}, {7, 0x85}, {8, 0x86}, {9, 0x8E}, {30, 0x9C},
};
// PS2 slots 0x13 / 0xA / 2 (0x8F takes the GameCube work's free slot 20).
static const R327EmTbl r327ps2_lateTbl[3] = {{20, 0x8F}, {10, 0x93}, {2, 0x7B}};
static const R327EmTbl r327ps2_appearTbl[2][4] = {
    {{22, 0x94}, {23, 0x96}, {24, 0x99}, {25, 0x9A}},
    {{26, 0x92}, {27, 0x91}, {28, 0x98}, {29, 0x97}},
};
static int r327ps2_cnt;   // PS2 work +0x4DF0: alive(0x1D) after the appear cut's far delete, minus 1

static void r327ps2_send(const R327EmTbl* t, int noSuspend)
{
    R327Em* e = &r327_work.p->em[t->idx];

    OSReport("[r327-ps2] send id=%x alive=%d alive1d=%d\n", t->id, SceCountEmAlive(0x10, 0x20), SceCountEmAlive(0x1D, -1));
    cEmWrapSetEmI(&e->em, t->id, 7, 0, 1, 1);
    e->set = 1;
    e->id = t->id;
    if (noSuspend >= 0) {
        e->em.setNoSuspend(noSuspend);
    }
}

// PS2-only task (0x107c0).
static void r327ps2_lateSet()
{
    u32 i = 0;

    SceSleep(1);
    while (i < 3) {
        if (SceCountEmAlive(0x10, 0x20) < 8 && AreaHitCheck(&r327Ps2Area1C, &pPL->pos)) {
            OSReport("[r327-ps2] late send id=%x alive=%d gate=8\n", r327ps2_lateTbl[i].id, SceCountEmAlive(0x10, 0x20));
            cEmWrapSetEmI(&r327_work.p->em[r327ps2_lateTbl[i].idx].em, r327ps2_lateTbl[i].id, -1, 0, 1, 1);
            i++;
        }
        SceSleep(1);
    }
}

static int r327ps2_EnemySetSub(R327EmTbl* a, u32 na, R327EmTbl* b, u32 nb)
{
    int ret = 0;
    u32 i;

    if (r327_work.p->first == 0) {
        return 0;
    }
    for (i = 0; i < na; i++) {
        if (r327_work.p->em[a[i].idx].set == 0) {
            r327ps2_send(&a[i], -1);
            r327_work.p->em[a[i].idx].em.setFindPL();
            ret = 1;
            break;
        }
    }
    if ((u32) SceCountEmAlive(0x1D, -1) < 9) {
        for (i = 0; i < nb; i++) {
            if (r327_work.p->em[b[i].idx].set == 0) {
                r327ps2_send(&b[i], -1);
                r327_work.p->em[b[i].idx].em.setFindPL();
                ret = 1;
                break;
            }
        }
    }
    return ret;
}

// Room-local r327EmFarDelete(keep, 33) (0x12f20): any view, over the room's wraps; the side-0 appear Ganados and
// types 0x16 / 2 / 5 / 6 / 0xA / 0xD / 0xB / 0x1A are kept; farthest (d2 > 3000) first; wrap destroy only.
static void r327ps2_farDelete(int keep)
{
    int n = SceCountEmAlive(0x10, 0x20) - keep;
    int k;

    OSReport("[r327-ps2] room far delete keep=%d alive=%d\n", keep, SceCountEmAlive(0x10, 0x20));
#if defined(RE4DC_ALIVE_CAP_ON) && RE4DC_ALIVE_CAP_ON
    // ALIVE_CAP (ch5found16 10-17): the count includes the cap's held sends (alive on the PS2). Over `keep`, the held
    // ones go first (latest held first, off screen, as em_far_delete.h does), so no live Ganado vanishes in front of
    // the player while sends wait in the hold; then the farthest live ones as before. Same number removed as the PS2.
    if (n > 0) {
        int held = re4dc_aliveCapHeldCount(0x10, 0x20);

        if (held > n) {
            held = n;
        }
        if (held > 0) {
            n -= re4dc_aliveCapFarDrop(held, 0);
        }
    }
#endif
    for (k = 0; k < n; k++) {
        int best = -1;
        f32 bestD = 0.0f;
        int i;

        for (i = 0; i < 32; i++) {
            R327Em* e = &r327_work.p->em[i];
            cEm* em;
            f32 dx, dy, dz, d2;

            if (i >= 22 && i <= 25) {
                continue;
            }
            if (e->em.isActive() != 1 || (em = e->em.getPtr()) == 0) {
                continue;
            }
            switch (em->type) {
            case 0x16: case 2: case 5: case 6: case 0xA: case 0xD: case 0xB: case 0x1A:
                continue;
            }
            dx = em->pos.x - pPL->pos.x;
            dy = em->pos.y - pPL->pos.y;
            dz = em->pos.z - pPL->pos.z;
            d2 = dx * dx + dy * dy + dz * dz;
            if (!(d2 > 3000.0f) || !(d2 > bestD)) {
                continue;
            }
            bestD = d2;
            best = i;
        }
        if (best != -1) {
            OSReport("[r327-ps2] room far delete slot=%d id=%x\n", best, r327_work.p->em[best].id);
            r327_work.p->em[best].em.destroy();
        }
    }
}

static void r327ps2_GanadoAppearCutEndProc(int side)
{
    int i;

    (void) side;
    for (i = 0; i < 4; i++) {
        const R327EmTbl* t = &r327ps2_appearTbl[0][i];

        if (r327_work.p->em[t->idx].set == 0) {
            r327ps2_send(t, -1);
        }
        r327_work.p->em[t->idx].em.setNoSuspend(0);
        r327_work.p->em[t->idx].em.setFindPL();
    }
    for (i = r327ps2_cnt; i < 4; i++) {
        const R327EmTbl* t = &r327ps2_appearTbl[1][i];

        if (r327_work.p->em[t->idx].set == 0) {
            r327ps2_send(t, -1);
        }
        r327_work.p->em[t->idx].em.setNoSuspend(0);
        r327_work.p->em[t->idx].em.setFindPL();
    }
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    SceExec(0x12, (TaskFunc) r327_EnemySet, 0, 0, 2, 0);
}

static void r327ps2_GanadoAppearCut()
{
    int i;
    int n;

    if (r327_work.p->first == 0) {
        SceExit();
    }
    n = re4dc_EmFarDelete(5, 0);
    r327ps2_cnt = SceCountEmAlive(0x1D, -1);
    OSReport("[r327-ps2] appear cut far delete keep=5 deleted=%d alive1d=%d\n", n, r327ps2_cnt);
    SceEventStart(1);
    for (i = 0; i < 4; i++) {
        r327ps2_send(&r327ps2_appearTbl[0][i], 1);
    }
    CamCtrl.CutCall(0x10);
    if (r327ps2_cnt != 0) {
        r327ps2_cnt--;
    }
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327ps2_GanadoAppearCutEndProc, 0, 0, 1);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    pG->Room_flg[0] |= 0x40000000;
    for (i = r327ps2_cnt; i < 4; i++) {
        r327ps2_send(&r327ps2_appearTbl[1][i], 1);
    }
    CamCtrl.CutCall(8);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327ps2_GanadoAppearCutEndProc(1);
}

static void r327ps2_GatlingGanadoSet()
{
    int idx;

    if (r327_work.p->first == 0) {
        SceExit();
    }
    for (;;) {
        u32 n = 0;
        int i;

        for (i = 0; i < 32; i++) {
            R327Em* e = &r327_work.p->em[i];

            if (e->set != 0 && !e->em.isActive() && !r327_capHeld(e->id)) {
                n++;
            }
        }
        if (n > 4) {
            break;
        }
        SceSleep(1);
    }
    RsfSet(G_ROOM_ID, 2);
    SceEventStart(1);
    if (SceAtHitCheck(0xB)) {
        r327_work.p->em[31].em.setEm(0x9D, 7, 0, 1, 1);
        idx = 31;
        r327_work.p->em[31].id = 0x9D;
        CamCtrl.CutCall(7);
    } else {
        r327_work.p->em[3].em.setEm(0x7C, 7, 0, 1, 1);
        idx = 3;
        r327_work.p->em[3].id = 0x7C;
        CamCtrl.CutCall(5);
    }
    r327ps2_farDelete(8);
    r327_work.p->em[idx].em.setNoSuspend(1);
    r327_work.p->em[idx].em.setFindPL();
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_GatlingGanadoSetEndProc, idx, 0, 1);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_GatlingGanadoSetEndProc(idx);
}

static void r327ps2_EnemySet2nd()
{
    if (RsfCheck(G_ROOM_ID, 16) == 0) {
        cEm* door;

        getRoomEtcDoor(1, &door, 1);
        if (door != 0) {
            while ((door->flag & 0x10000000) == 0) {
                SceSleep(1);
            }
            RsfSet(G_ROOM_ID, 16);
            OSReport("[r327-ps2] 2nd alive1d=%d gate=8\n", SceCountEmAlive(0x1D, -1));
            if ((u32) SceCountEmAlive(0x1D, -1) < 8) {
                setEm(0x83, 7, 0, 1, 1);
                setEm(0x84, 7, 0, 1, 1);
            }
        }
    }
}
#endif

// Room init (the Ganado camp): on a return after Scenario_flg[1] 0x40000000 the room's 0x1D enemies are
// dropped from the list, else the first-visit tables set the eleven camp Ganados; the two lamp switches
// (areas 4/3 until Room_flg bits 0/1, both -> the gate open), area 6 = the door check, the card reader
// (area 0x18 + card key 0x74 watcher until bit 11), the gatling Ganado until bit 2, the goto and
// enemy-refill tasks, seven box item events, the continue point (area 0x1B), the stream.
void R327Init()
{
    u32 i;

#line 61 "D:/Bio4/Prog/r327.cpp"
    r327_work.p = (R327Work*) MEM_CALLOC(sizeof(R327Work), 1, 0xd);
    // Reference-view store: the flags test's `pG` load is issued after it (alias.c keeps them ordered).
    IntSet(r327_work.p->first, 1);
    if (pG->Scenario_flg[1] & 0x40000000) {
        for (i = 0; i < 0x100; i++) {
            EmListData* e = (EmListData*) ((u8*) pG + (0x52E8 + i * 0x20));

            if (e->room == 0x327 && e->id == 0x1D) {
                e->be_flag &= ~1;
            }
        }
        r327_work.p->first = 0;
    }
    if (r327_work.p->first != 0) {
#if R327_PS2
        for (i = 0; i < 9; i++) {
            r327ps2_send(&r327ps2_firstTbl[i], -1);
        }
        SceExec(0x12, (TaskFunc) r327ps2_lateSet, 0, 0, 2, 0);
    }
    if (0) {
#endif
        for (i = 0; i < 11; i++) {
            cEmWrapSetEmI(&r327_work.p->em[r327_firstTbl[i].idx].em, r327_firstTbl[i].id, 7, 0, 1, 1);
            r327_work.p->em[r327_firstTbl[i].idx].set = 1;
            r327_work.p->em[r327_firstTbl[i].idx].id = r327_firstTbl[i].id;
        }
    }
    if (RsfCheck(G_ROOM_ID, 0) && RsfCheck(G_ROOM_ID, 1)) {
        SceAtSetEnable(5, 0);
        SceAtSetEnable(6, 0);
        SmdGetObjPtr(0x52)->pos.y = 9400.0f;
        SmdGetObjPtr(0x52)->matUpdate();
        EstSet(0, -1, 0, 0, 1, 0, 1, 5, 0, 0);
        EstSet(0, -1, 0, 0, 1, 1, 1, 5, 0, 0);
    } else {
        if (RsfCheck(G_ROOM_ID, 0) == 0) {
            SceAtDataSet_exec(4, 0x12, 0, (TaskFunc) r327_SwitchOperate, 0, 1);
        } else {
            EstSet(0, -1, 0, 0, 1, 0, 1, 5, 0, 0);
        }
        if (RsfCheck(G_ROOM_ID, 1) == 0) {
            SceAtDataSet_exec(3, 0x12, 0, (TaskFunc) r327_SwitchOperate, (void*) 1, 1);
        } else {
            EstSet(0, -1, 0, 0, 1, 1, 1, 5, 0, 0);
        }
        SceAtDataSet_exec(6, 0x12, 0, (TaskFunc) r327_CheckDoor, 0, 1);
    }
    if (RsfCheck(G_ROOM_ID, 12)) {
        EstSet(0, -1, 0, 0, 1, 2, 1, 2, 0, 0);
        EstSet(0, -1, 0, 0, 1, 4, 1, 3, 0, 0);
    } else {
        EstSet(0, -1, 0, 0, 1, 3, 1, 2, 0, 0);
        EstSet(0, -1, 0, 0, 1, 5, 1, 3, 0, 0);
    }
    if (RsfCheck(G_ROOM_ID, 2) == 0) {
        SceExec(0x12, (TaskFunc) r327_GatlingGanadoSet, 0, 0, 2, 0);
    }
    SceExec(0x12, (TaskFunc) r327_GanadoGotoCheck, 0, 0, 2, 0);
    if (RsfCheck(G_ROOM_ID, 11) == 0) {
        SceAtDataSet_exec(0x18, 0x12, 0, (TaskFunc) r327_CheckCardReader, 0, 1);
        SceExec(0x12, (TaskFunc) r327_CheckUseCardKey, 0, 0, 2, 0);
        if (RsfCheck(G_ROOM_ID, 13)) {
            EstSet(0, -1, 0, 0, 1, 6, 1, 4, 0, 0);
        } else {
            EstSet(0, -1, 0, 0, 1, 7, 1, 4, 0, 0);
        }
    } else {
        EstSet(0, -1, 0, 0, 1, 7, 1, 0, 0, 0);
    }
    SceSetItemEvent(0x10, 0x83, 3, 0x15, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x68, 0);
    SceSetItemEvent(0x11, 0x82, 4, 0x18, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x4A, 0);
    SceSetItemEvent(0x13, -1, 6, 0x17, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x48, 0);
    SceSetItemEvent(0x12, -1, 5, 0x13, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x4C, 0);
    SceSetItemEvent(0x14, -1, 7, 0x12, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x4E, 0);
    SceSetItemEvent(0x16, 0x87, 9, 0x14, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x79, 0);
    SceSetItemEvent(0x1A, 0x89, 0xE, 0x16, (void (*)(int)) r327_BoxOpen, (void (*)()) r327_BoxOpened, 0x6A, 0);
    SceAtDataSet_exec(0x1B, 0x12, 0, (TaskFunc) r327_ContinuePointSet, 0, 1);
    SceExec(0x12, (TaskFunc) r327_StrCheck, 0, 0, 2, 0);
    SceExec(0x12, (TaskFunc) r327_EnemySet2nd, 0, 0, 2, 0);
}

// Per frame: each active camp enemy on a route keeps hunting the player and steps its route; inactive
// ones that may be reset are destroyed; debug count of 0x1D enemies.
void R327Main()
{
    int i;

    for (i = 0; i < 32; i++) {
        R327Em* e = &r327_work.p->em[i];

        if (e->em.isActive()) {
            cEmRun* run = &e->run;

            if (run->run != 0) {
                e->em.setFindPL();
                run->Move();
            }
        } else if (e->em.ckResetEnable() == 1) {
            e->em.destroy();
        }
    }
    SceDebugDisp("Em[%d]", SceCountEmAlive(0x1D, -1));
}

// Sets the first free enemy of table `a`, then of table `b`; 1 when one was set.
int r327_EnemySetSub(R327EmTbl* a, u32 na, R327EmTbl* b, u32 nb)
{
#if R327_PS2
    return r327ps2_EnemySetSub(a, na, b, nb);
#endif
    int ret = 0;
    u32 i;

    if (r327_work.p->first == 0) {
        return 0;
    }
    for (i = 0; i < na; i++) {
        if (r327_work.p->em[a[i].idx].set == 0) {
            cEmWrapSetEmI(&r327_work.p->em[a[i].idx].em, a[i].id, 7, 0, 1, 1);
            r327_work.p->em[a[i].idx].set = 1;
            r327_work.p->em[a[i].idx].id = a[i].id;
            ret = 1;
            break;
        }
    }
    for (i = 0; i < nb; i++) {
        if (r327_work.p->em[b[i].idx].set == 0) {
            cEmWrapSetEmI(&r327_work.p->em[b[i].idx].em, b[i].id, 7, 0, 1, 1);
            r327_work.p->em[b[i].idx].set = 1;
            r327_work.p->em[b[i].idx].id = b[i].id;
            ret = 1;
            break;
        }
    }
    return ret;
}

// Refills the camp: whenever an enemy dies, two more from the tables of the area the player is in.
static void r327_EnemySet()
{
    u32 last = 0;

    for (;;) {
        u32 n = SceCountEmAlive(0x1D, -1);

        if (n < last) {
            if (SceAtHitCheck(0xC)) {
                u32 r = Rnd();

                switch ((u8) (r % 3)) {
                case 0:
                    r327_EnemySetSub(r327_tblB, 3, r327_tblC, 2);
                    break;
                case 1:
                    r327_EnemySetSub(r327_tblC, 2, r327_tblD, 2);
                    break;
                case 2:
                    r327_EnemySetSub(r327_tblD, 2, r327_tblB, 3);
                    break;
                }
            } else if (SceAtHitCheck(0xB)) {
                u32 r = Rnd();

                switch ((u8) (r % 3)) {
                case 0:
                    r327_EnemySetSub(r327_tblA, 2, r327_tblC, 2);
                    break;
                case 1:
                    r327_EnemySetSub(r327_tblC, 2, r327_tblD, 2);
                    break;
                case 2:
                    r327_EnemySetSub(r327_tblD, 2, r327_tblA, 2);
                    break;
                }
            } else if (SceAtHitCheck(9)) {
                u32 r = Rnd();

                switch ((u8) (r % 3)) {
                case 0:
                    r327_EnemySetSub(r327_tblA, 2, r327_tblB, 3);
                    break;
                case 1:
                    r327_EnemySetSub(r327_tblB, 3, r327_tblD, 2);
                    break;
                case 2:
                    r327_EnemySetSub(r327_tblD, 2, r327_tblA, 2);
                    break;
                }
            } else if (SceAtHitCheck(0xA)) {
                u32 r = Rnd();

                switch ((u8) (r % 3)) {
                case 0:
                    r327_EnemySetSub(r327_tblA, 2, r327_tblB, 3);
                    break;
                case 1:
                    r327_EnemySetSub(r327_tblB, 3, r327_tblC, 2);
                    break;
                case 2:
                    r327_EnemySetSub(r327_tblC, 2, r327_tblA, 2);
                    break;
                }
            } else {
                u32 r = Rnd();

                switch ((u8) (r & 3)) {
                case 0:
                    r327_EnemySetSub(r327_tblA, 2, r327_tblB, 3);
                    break;
                case 1:
                    r327_EnemySetSub(r327_tblB, 3, r327_tblC, 2);
                    break;
                case 2:
                    r327_EnemySetSub(r327_tblC, 2, r327_tblD, 2);
                    break;
                case 3:
                    r327_EnemySetSub(r327_tblD, 2, r327_tblA, 2);
                    break;
                }
            }
        }
        last = n;
        SceSleep(1);
    }
}

// Once five of the first enemies are dead: the gatling ganado appears (camera cut 5 or 7 by the player's side).
static void r327_GatlingGanadoSet()
{
#if R327_PS2
    r327ps2_GatlingGanadoSet();
    return;
#endif
    int idx;

    if (r327_work.p->first == 0) {
        SceExit();
    }
    for (;;) {
        u32 n = 0;
        int i;

        for (i = 0; i < 32; i++) {
            R327Em* e = &r327_work.p->em[i];

            if (e->set != 0 && !e->em.isActive() && !r327_capHeld(e->id)) {
                n++;
            }
        }
        if (n > 4) {
            break;
        }
        SceSleep(1);
    }
    RsfSet(G_ROOM_ID, 2);
    SceEventStart(1);
    if (SceAtHitCheck(0xB)) {
        r327_work.p->em[31].em.setEm(0x9D, 7, 0, 1, 1);
        idx = 31;
        r327_work.p->em[31].id = 0x9D;
        CamCtrl.CutCall(7);
    } else {
        r327_work.p->em[3].em.setEm(0x7C, 7, 0, 1, 1);
        idx = 3;
        r327_work.p->em[3].id = 0x7C;
        CamCtrl.CutCall(5);
    }
    r327_work.p->em[idx].em.setNoSuspend(1);
    r327_work.p->em[idx].em.setFindPL();
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_GatlingGanadoSetEndProc, idx, 0, 1);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_GatlingGanadoSetEndProc(idx);
}

// End of the gatling Ganado's cut: camera back, it may suspend, SceEventEnd.
static void r327_GatlingGanadoSetEndProc(int idx)
{
    CamCtrl.Comeback(0);
    r327_work.p->em[idx].em.setNoSuspend(0);
    SceEventEnd(0);
}

// The lamp switch `no` (0 / 1): the "turn it on?" question.
static void r327_SwitchOperate(int no)
{
    if (RsfCheck(G_ROOM_ID, 12)) {
        SceUpCut(4, -1, -1, 0);
    } else if (RsfCheck(G_ROOM_ID, 13) == 0) {
        SceExec(0x12, (TaskFunc) r327_SetSwitchDisable, 0, 0, 2, 0);
    } else {
        SceEventStart(1);
        SceMesSet(1, 0, 1, 0x64, 0x150 - cMes.getWork()->lineSpace - cMes.getWork()->m_font_h - 1);
        if (SceMesGetSelection() == 1) {
            RoomSeCall(0, 0, 0, 0, 0);
            SceSleep(5);
            SceExec(0x12, (TaskFunc) r327_LampSet, no, 0, 2, 0);
        }
        SceEventEnd(0);
    }
}

// Lamp `no` lights up (camera cut 4).
static void r327_LampSet(int no)
{
    int lamp;

    if (no == 0) {
        lamp = 0;
        RsfSet(G_ROOM_ID, 0);
        SceAtSetEnable(4, 0);
    } else {
        lamp = 1;
        RsfSet(G_ROOM_ID, 1);
        SceAtSetEnable(3, 0);
    }
    int zero = 0;
    SceEventStart(1);
    CamCtrl.CutCall(4);
    pG->Room_flg[0] &= ~0x80000000;
    SceSleep(10);
    RoomSeCall(0x1F, 0, 0, 0, 0);
    EstSet(0, -1, 0, 0, 1, lamp, 1, 0, (u32) zero, (void*) zero);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_LampSetEndProc();
}

// End of a lamp cut: camera back, SceEventEnd; with both lamps lit (Room_flg bits 0/1) the gate opens.
void r327_LampSetEndProc()
{
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    if (RsfCheck(G_ROOM_ID, 0) && RsfCheck(G_ROOM_ID, 1)) {
        SceExec(0x12, (TaskFunc) r327_DoorOpen, 0, 0, 2, 0);
    }
}

// After the switch was disabled: a group of four appears at one side (both sides when few are left).
static void r327_GanadoAppearCut()
{
#if R327_PS2
    r327ps2_GanadoAppearCut();
    return;
#endif
    u32 side = Rnd() & 1;
    int both = 0;
    int i;

    if (r327_work.p->first == 0) {
        SceExit();
    }
    if ((u32) SceCountEmAlive(0x1D, -1) <= 5) {
        both = 1;
    }
    SceEventStart(1);
    if (both == 0) {
        side = 0;
    }
    for (i = 0; i < 4; i++) {
        R327EmTbl* t = &r327_appearTbl[side][i];

        cEmWrapSetEmI(&r327_work.p->em[t->idx].em, t->id, 7, 0, 1, 1);
        r327_work.p->em[t->idx].set = 1;
        r327_work.p->em[t->idx].id = t->id;
        r327_work.p->em[t->idx].em.setNoSuspend(1);
    }
    CamCtrl.CutCall(side == 0 ? 0x10 : 8);
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_GanadoAppearCutEndProc, side, 0, 1);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    if (both == 1) {
        side ^= 1;
        for (i = 0; i < 4; i++) {
            R327EmTbl* t = &r327_appearTbl[side][i];

            cEmWrapSetEmI(&r327_work.p->em[t->idx].em, t->id, 7, 0, 1, 1);
            r327_work.p->em[t->idx].set = 1;
            r327_work.p->em[t->idx].id = t->id;
            r327_work.p->em[t->idx].em.setNoSuspend(1);
        }
        CamCtrl.CutCall(side == 0 ? 0x10 : 8);
        while (!CamCtrl.IsMotionEnd()) {
            SceSleep(1);
        }
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_GanadoAppearCutEndProc(side != 0 ? 1 : 0);
}

// End of the appearance cut: the four Ganados of side 0 (and side 1 when `side`) are set from
// r327_appearTbl if not yet, released and alerted; camera back, SceEventEnd.
static void r327_GanadoAppearCutEndProc(int side)
{
#if R327_PS2
    r327ps2_GanadoAppearCutEndProc(side);
    return;
#endif
    // The table pointer is a two-set variable (the dead `t = t2` below): its first value is not folded
    // into the loop's giv init (`lis/addi r9; mr r31,r9`) and the hoisted `set = 1` constant is a loop
    // movable ranking below the end pointer (r27 after r28). The second table keeps its copy through
    // the codeless "=m" anchor (a second use of the REG_EQUIV address).
    R327EmTbl* t = r327_appearTbl[0];
    int i;

    for (i = 0; i < 4; i++) {
        if (r327_work.p->em[t[i].idx].set == 0) {
            cEmWrapSetEmI(&r327_work.p->em[t[i].idx].em, t[i].id, 7, 0, 1, 1);
            r327_work.p->em[t[i].idx].set = 1;
            r327_work.p->em[t[i].idx].id = t[i].id;
        }
        r327_work.p->em[t[i].idx].em.setNoSuspend(0);
        r327_work.p->em[t[i].idx].em.setFindPL();
    }
    if (side == 1) {
        R327EmTbl* t2 = r327_appearTbl[1];

        t = t2;
        asm("" : "=m"(*t2) : "r"(t2)); // COMPILER-DIFF: #13 (see above)
        for (i = 0; i < 4; i++) {
            if (r327_work.p->em[t2[i].idx].set == 0) {
                cEmWrapSetEmI(&r327_work.p->em[t2[i].idx].em, t2[i].id, 7, 0, 1, 1);
                r327_work.p->em[t2[i].idx].set = 1;
                r327_work.p->em[t2[i].idx].id = t2[i].id;
            }
            r327_work.p->em[t2[i].idx].em.setNoSuspend(0);
            r327_work.p->em[t2[i].idx].em.setFindPL();
        }
    }
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    SceExec(0x12, (TaskFunc) r327_EnemySet, 0, 0, 2, 0);
}

// Area 6: once the switch was pulled out (Room_flg bit 13) the door message, else the Ganado disables the switch.
static void r327_CheckDoor()
{
    if (RsfCheck(G_ROOM_ID, 13)) {
        SceUpCut(0, -1, 2, 0);
    } else {
        SceExec(0x12, (TaskFunc) r327_SetSwitchDisable, 0, 0, 2, 0);
    }
}

// Both lamps on: the gate rises (camera cut 3).
static void r327_DoorOpen()
{
    cObj* obj = SmdGetObjPtr(0x52);
    u32 se;

    SceEventStart(1);
    CamCtrl.CutCall(3);
    se = RoomSeCall(1, &obj->pos, 0, 0, 0);
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_DoorOpenEndProc, se, 0, 1);
    obj->be_flag |= 0x20;
    while (obj->pos.y < 9400.0f) {
        obj->pos.y += 40.0f;
        SceSleep(1);
    }
    obj->pos.y = 9400.0f;
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_DoorOpenEndProc(se);
}

// End of the gate rise (also its cancel path, Room_flg[0] bit 31): the gate 0x52 snapped to y 9400 with
// its SE stopped, camera back, areas 5/6 off, door_unlock[1] 0x00400000, SceEventEnd.
static void r327_DoorOpenEndProc(int se)
{
    if ((int) pG->Room_flg[0] < 0) {
        SmdGetObjPtr(0x52)->pos.y = 9400.0f;
        SndStop(se, 0);
    }
    CamCtrl.Comeback(0);
    SceAtSetEnable(5, 0);
    SceAtSetEnable(6, 0);
    pG->door_unlock[1] |= 0x00400000;
    SceEventEnd(0);
}

// Enemies inside area 13 with the player run one of three routes out of it.
static void r327_GanadoGotoCheck()
{
    Vec route0[3] = {{-19170.0f, 6079.0f, 43324.0f}, {-23135.0f, 6078.0f, 43810.0f}, {-27515.0f, 6078.0f, 41375.0f}};
    Vec route1[3] = {{-22857.0f, 6078.0f, 30100.0f}, {-24502.0f, 6078.0f, 24525.0f}, {-27820.0f, 6078.0f, 26791.0f}};
    Vec route2 = {-23076.0f, 6078.0f, 34282.0f};

    for (;;) {
        if (SceAtCheckHitModel(0xD, pPL) == 1) {
            int i;

            for (i = 0; i < 32; i++) {
                R327Em* e = &r327_work.p->em[i];

                if (e->em.isActive()) {
                    cEmRun* run = &e->run;

                    if (run->run == 0 && !SceAtCheckHitModel(0xD, e->em.getPtr()) &&
                        !SceAtCheckHitModel(0xE, e->em.getPtr()) && !SceAtCheckHitModel(0xF, e->em.getPtr())) {
                        u32 r = Rnd();

                        switch ((u8) (r % 3)) {
                        case 0:
                            cEmRunSetRouteI(run, e->id, route0, 3);
                            break;
                        case 1:
                            cEmRunSetRouteI(run, e->id, route1, 3);
                            break;
                        case 2:
                            cEmRunSetRouteI(run, e->id, &route2, 1);
                            break;
                        }
                    }
                }
            }
        }
        SceSleep(1);
    }
}

// Area 0x18, the card reader: up-cut 6 (after the switch was disabled, bit 12) or 5; with the card key
// (item 0x74) held the item screen opens.
static void r327_CheckCardReader()
{
    if (RsfCheck(G_ROOM_ID, 12)) {
        SceUpCut(6, 9, -1, 4);
    } else {
        SceUpCut(5, 9, -1, 4);
    }
    if (ItemMgr.num(0x74) != 0) {
        SubScreenOpen(0x80, 1);
    } else {
        CamCtrl.Comeback(0);
    }
}

// Task: waits for the card key (item 0x74) to be used, Room_flg bit 11, the reader effect swapped,
// up-cut 3, area 0x18 off, then the switch re-enable cut.
static void r327_CheckUseCardKey()
{
    while (ItemMgr.check(0x74) == 0) {
        SceSleep(1);
    }
    // The EstSet stack zeros come from one callee-saved `li r30,0` set before the flag call (the r11d idiom).
    int zero = 0;
    RsfSet(G_ROOM_ID, 11);
    EffectEspDelete(1, 4, 0, 0);
    EffectEspgenDelete(1, 4, 0);
    EffectEfmDelete(1, 4, 0);
    EstSet(0, -1, 0, 0, 1, 7, 1, 4, (u32) zero, (void*) zero);
    SceUpCut(3, 9, 0x1D, 0);
    SceAtSetEnable(0x18, 0);
    SceExec(0x12, (TaskFunc) r327_SetSwitchEnable, 0, 0, 2, 0);
}

// The card key re-enables the switch: camera cuts 13 / 14 on the two lamps.
static void r327_SetSwitchEnable()
{
    int zero = 0;

    RsfClear(G_ROOM_ID, 12);
    SceEventStart(1);
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_SetSwitchEnableEndProc, 0, 0, 1);
    CamCtrl.CutCall(0xD);
    SceSleep(10);
    RoomSeCall(0x1E, 0, 0, 0, 0);
    EffectEspDelete(1, 3, 0, 0);
    EffectEspgenDelete(1, 3, 0);
    EffectEfmDelete(1, 3, 0);
    EstSet(0, -1, 0, 0, 1, 5, 1, 3, (u32) zero, (void*) zero);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    CamCtrl.CutCall(0xE);
    SceSleep(10);
    RoomSeCall(0x1E, 0, 0, 0, 0);
    EffectEspDelete(1, 2, 0, 0);
    EffectEspgenDelete(1, 2, 0);
    EffectEfmDelete(1, 2, 0);
    EstSet(0, -1, 0, 0, 1, 3, 1, 2, 0, 0);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_SetSwitchEnableEndProc();
}

// End of the re-enable cut (cancelled: the lamp effects swapped to the lit ones): camera back, SceEventEnd.
static void r327_SetSwitchEnableEndProc()
{
    int zero = 0;

    if ((int) pG->Room_flg[0] < 0) {
        EffectEspDelete(1, 2, 0, 0);
        EffectEspgenDelete(1, 2, 0);
        EffectEfmDelete(1, 2, 0);
        EffectEspDelete(1, 3, 0, 0);
        EffectEspgenDelete(1, 3, 0);
        EffectEfmDelete(1, 3, 0);
        EstSet(0, -1, 0, 0, 1, 3, 1, 2, (u32) zero, (void*) zero);
        EstSet(0, -1, 0, 0, 1, 5, 1, 3, (u32) zero, (void*) zero);
    }
    CamCtrl.Comeback(0);
    SceEventEnd(0);
}

// A ganado runs to the switch and pulls it out (camera cuts 17, 9, 15, 13, 14, 3).
static void r327_SetSwitchDisable()
{
    Vec gotoPos = {-23793.0f, 12126.0f, 28944.0f};
    Vec pos = {-26300.0f, 13480.0f, 21560.0f};
    Vec pos2 = {-26200.0f, 13580.0f, 21560.0f};
    Vec rot = {0.0f, 1.5707964f, -0.8f};
    Vec dpos;
    cSceObj sce;
    void* bin;
    void* tpl;

    if (ItemGetBinTplAddr(0x74, &bin, &tpl) == 1) {
        r327_work.p->sw = SetObjSmd(bin, tpl, &pos, &rot, 0x10, 1);
        r327_work.p->sw->setNoSuspend(1);
    }
    RsfSet(G_ROOM_ID, 12);
    RsfSet(G_ROOM_ID, 13);
    SceEventStart(1);
    pG->Room_flg[0] &= ~0x80000000;
    SceSetEventCancel(1, (TaskFunc) r327_SetSwitchDisableEndProc, 0, 0, 1);
    r327_work.p->em2.setEm(0x9E, -1, 0, 0, 0);
    r327_work.p->em2.setNoSuspend(1);
    CamCtrl.CutCall(0x11);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    CamCtrl.CutCall(9);
    SceSleep(10);
    EffectEspDelete(1, 4, 0, 0);
    EffectEspgenDelete(1, 4, 0);
    EffectEfmDelete(1, 4, 0);
    EstSet(0, -1, 0, 0, 1, 6, 1, 4, 0, 0);
    PSVECSubtract(&pos2, &pos, &dpos);
    sce.initMove1_all(r327_work.p->sw, 10, &dpos, &rot, 0.0f, 0.0f, 1);
    RoomSeCall(0x20, &r327_work.p->sw->pos, 0, 0, 0);
    while (sce.move() == 1) {
        SceSleep(1);
    }
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    r327_work.p->sw->be_flag &= ~2;
    r327_work.p->em2.setGoto(&gotoPos, 1);
    CamCtrl.CutCall(0xF);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    CamCtrl.CutCall(0xD);
    SceSleep(15);
    RoomSeCall(0x1E, 0, 0, 0, 0);
    EffectEspDelete(1, 3, 0, 0);
    EffectEspgenDelete(1, 3, 0);
    EffectEfmDelete(1, 3, 0);
    EstSet(0, -1, 0, 0, 1, 4, 1, 3, 0, 0);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    CamCtrl.CutCall(0xE);
    SceSleep(15);
    RoomSeCall(0x1E, 0, 0, 0, 0);
    EffectEspDelete(1, 2, 0, 0);
    EffectEspgenDelete(1, 2, 0);
    EffectEfmDelete(1, 2, 0);
    EstSet(0, -1, 0, 0, 1, 2, 1, 2, 0, 0);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    CamCtrl.CutCall(3);
    SceSleep(15);
    while (!CamCtrl.IsMotionEnd()) {
        SceSleep(1);
    }
    SceSetEventCancel(0, 0, 0, -1, 1);
    r327_SetSwitchDisableEndProc();
}

// End of the disable cut (cancelled: the lamp / reader effects swapped to the dead ones): the
// switch-pulling Ganado destroyed, camera back, SceEventEnd, then the appearance groups.
static void r327_SetSwitchDisableEndProc()
{
    int zero = 0;

    if ((int) pG->Room_flg[0] < 0) {
        EffectEspDelete(1, 2, 0, 0);
        EffectEspgenDelete(1, 2, 0);
        EffectEfmDelete(1, 2, 0);
        EffectEspDelete(1, 3, 0, 0);
        EffectEspgenDelete(1, 3, 0);
        EffectEfmDelete(1, 3, 0);
        EstSet(0, -1, 0, 0, 1, 2, 1, 2, (u32) zero, (void*) zero);
        EstSet(0, -1, 0, 0, 1, 4, 1, 3, (u32) zero, (void*) zero);
        EffectEspDelete(1, 4, 0, 0);
        EffectEspgenDelete(1, 4, 0);
        EffectEfmDelete(1, 4, 0);
        EstSet(0, -1, 0, 0, 1, 6, 1, 4, (u32) zero, (void*) zero);
    }
    r327_work.p->em2.destroy();
    CamCtrl.Comeback(0);
    SceEventEnd(0);
    ObjMgr.destroy(r327_work.p->sw);
    r327_work.p->sw = (cObj*) zero;
    SceExec(0x12, (TaskFunc) r327_GanadoAppearCut, 0, 0, 2, 0);
}

// Two more enemies once door 1 has been opened.
static void r327_EnemySet2nd()
{
#if R327_PS2
    r327ps2_EnemySet2nd();
    return;
#endif
    if (RsfCheck(G_ROOM_ID, 16) == 0) {
        cEm* door;

        getRoomEtcDoor(1, &door, 1);
        if (door != 0) {
            while ((door->flag & 0x10000000) == 0) {
                SceSleep(1);
            }
            RsfSet(G_ROOM_ID, 16);
            setEm(0x83, 7, 0, 1, 1);
            setEm(0x84, 7, 0, 1, 1);
        }
    }
}

// Area 0x1B once (Room_flg bit 15): autosave.
static void r327_ContinuePointSet()
{
    if (RsfCheck(G_ROOM_ID, 15) == 0) {
        RsfSet(G_ROOM_ID, 15);
        GameSaveSave(&GameSave, pSaveData, -1);
    }
}

// Battle stream while the player is seen and enemies are alive.
static void r327_StrCheck()
{
    for (;;) {
        while (SceCkFindPL(0) == 0) {
            SceSleep(1);
        }
        SndRoomStrStart(1, 0, 1);
        while (SceCountEmAlive(0x1D, -1) != 0) {
            SceSleep(1);
        }
        SndRoomStrStop(3);
    }
}

// Item-event opener: box `id` (duralumin 0x68 type 8, lockers type 1, double door 0x6A) opens.
static void r327_BoxOpen(u32 id)
{
    switch (id) {
    case 0x68:
        OpenBoxMain(8, 0, 0x18, 0x68, -1, -1);
        break;
    case 0x48:
    case 0x4A:
    case 0x4C:
    case 0x4E:
    case 0x78:
    case 0x79:
    case 0x7A:
        OpenBoxMain(1, 0, 0x1C, id, -1, -1);
        break;
    case 0x6A:
        OpenBoxMain(0, 0, 0x1C, 0x6A, 0x6B, -1);
        break;
    }
}

// Item-event "already opened": box `id` posed open (0x6A still animates: vendor copy).
static void r327_BoxOpened(u32 id)
{
    switch (id) {
    case 0x68:
        OpenBoxMain(8, 1, 0x18, 0x68, -1, -1);
        break;
    case 0x48:
    case 0x4A:
    case 0x4C:
    case 0x4E:
    case 0x78:
    case 0x79:
    case 0x7A:
        OpenBoxMain(1, 1, 0x1C, id, -1, -1);
        break;
    case 0x6A:
        OpenBoxMain(0, 0, 0x1C, 0x6A, 0x6B, -1);
        break;
    }
}

// Bind the runner to enemy `no` with an n-point route; run = 1 starts Move stepping it.
int cEmRun::SetRoute(s16 no, Vec* tbl, int n)
{
    if (SetControl(no, tbl, n, 0) == 0) {
        return 0;
    }
    run = 1;
    return 1;
}

// One step of the route: the next point in mode 0xD when the current one is reached; 0 when done.
int cEmRun::Move()
{
    cEmWrap* w = &em;

    if (active == 0) {
        run = 0;
        return 0;
    }
    if (!w->isActive()) {
        run = 0;
        return 0;
    }
    if (w->ckGoto() != 0xD) {
        if (cur >= nPoint) {
            run = 0;
            return 0;
        }
        w->setGoto(&point[cur].pos, 0xD);
        prev = cur;
        cur++;
    }
    return 1;
}
