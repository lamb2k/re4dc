// game/stage: stage-level room set-up and the enemy list files. StageSet (from the room-change
// routine) reloads the stage heap / room REL when the stage or the reload flags change and picks
// the enemy list ("etc/emleonNN.esl" / omake lists, chosen per room and story flags by
// checkEmListNo) into pG->Em_list; SubMissionCheck runs the per-stage side missions — stage 1's
// blue medallion count (15 targets in rooms 103 / 108, the HUD counter id 0x33, the merchant
// bonus at 10 and the flag at 15).
#include "types.h"
#include "vec.h"
#include "global.h"
#include "map_obj.h"
#include "light.h"
#include "widget.h"
#include "card.h"
#include "room_data.h"
#include "mes.h"
#include "main_mem.h"
#include "scheduler.h"
#include "math_sub.h"
#include "id_sys.h"
#include "etc_model.h"

#include "dvd.h"
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22 && defined(RE4DC_PS2_CH2_ENEMY) && RE4DC_PS2_CH2_ENEMY
#include "ps2_enemy_ch22.h"
extern "C" void re4dc_missing(const char* name);
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23 && defined(RE4DC_PS2_CH2_ENEMY) && RE4DC_PS2_CH2_ENEMY
#include "ps2_enemy_ch23.h"
extern "C" void re4dc_missing(const char* name);
#endif
#if defined(RE4DC_PS2_CH3_ENEMY) && RE4DC_PS2_CH3_ENEMY
#include "ps2_enemy_ch3.h"
extern "C" void re4dc_missing(const char* name);
#endif

// game/sce_com.cpp: per-scenario free counters (pG + 0x51E8)
extern "C" int GetFree(int no);
extern "C" void SetFree(int no, int val);

// game/merchant.cpp
struct MerchantData;
extern MerchantData merchantData;
extern u16 stock_1st_mission[];
extern "C" void stockDataAdd(MerchantData* m, u16* stock);

extern "C" {
int checkEmListNo(u16 room);
const char* getEmListName(u32 no);
const char* getEmListDbgName(int no);
int getEmListNum();
void StageSet();
void readEmList(int mode);
int checkSubMissionTarget(int stage, int no);
void subMissionSt1();
void subMissionSt2();
void subMissionSt3();
void SubMissionCheck();
#if defined(RE4DC_GAME) && !defined(__PPC__)
void re4dc_room_leave();
#endif
}

// Village rooms 200..208: list 2 until the church bell (Scenario_flg[0] 0x40000), then 3.
static inline int emListVillage(int room)
{
    switch (room) {
    case 0x200:
    case 0x201:
    case 0x202:
    case 0x203:
    case 0x204:
    case 0x207:
    case 0x208:
        if (!(pG->Scenario_flg[0] & 0x40000)) {
            return 2;
        }
    }
    return 3;
}

// Enemy list (ESL file) number for a room (stage << 8 | room), -1 = none.
// Which enemy list file `room` uses: 8 for Assignment Ada (System_flg bit31), 9 / 10 for the
// Mercenaries (0x40000000; 10 in rooms 403 / 404), else by stage and story progress (0..7);
// -1 = the room keeps the current list.
int checkEmListNo(u16 room)
{
    int stage = room >> 8;
    u32 flags = pG->System_flg;

    if ((s32) flags < 0) {
        return 8;
    }
    if (flags & 0x40000000) {
        switch (room) {
        default:
            return 9;
        case 0x403:
        case 0x404:
            return 10;
        }
    }
    switch (stage) {
    case 1:
        if (room == 0x120) {
            return 0;
        }
        if (room == 0x10E) {
            if (flags & 0x2000) {
                return 1;
            }
            return -1;
        }
        return room > 0x10B;
    case 2:
        if (room == 0x22B) {
            return -1;
        }
        if (room == 0x22C) {
            return -1;
        }
        if (room == 0x22D) {
            return -1;
        }
        if (room == 0x200) {
            if (!(pG->Scenario_flg[0] & 0x800000)) {
                return 1;
            }
            return 2;
        }
        if (room > 0x219) {
            if (room == 0x222) {
                return 4;
            }
            return 5;
        }
        if (room > 0x210) {
            return 4;
        }
        if (pG->Scenario_flg[0] & 0x10000000) {
            return 4;
        }
        return emListVillage(room);
    case 3:
        if (room <= 0x314) {
            return 6;
        }
        return 7;
    case 4:
        if (room > 0x404) {
            return 8;
        }
        switch (room) {
        case 0x403:
        case 0x404:
            break;
        default:
            return 9;
        }
        return 10;
    }
    return -1;
}

static const char* emlist_name[11] = {
    "etc/emleon00.esl", "etc/emleon01.esl", "etc/emleon02.esl", "etc/emleon03.esl",
    "etc/emleon04.esl", "etc/emleon05.esl", "etc/emleon06.esl", "etc/emleon07.esl",
    "etc/omake00.esl",  "etc/omake01.esl",  "etc/omake02.esl",
};

static const char* emlist_dbg_name[11] = {
    "1st-1", "1st-2", "2st-1", "2st-2", "2st-3", "2st-4", "3st-1", "3st-2", "ada", "etc", "etc2",
};

// File name of enemy list `no` (0..10).
const char* getEmListName(u32 no)
{
    const char* name;

    if (no <= 10) {
        name = emlist_name[no];
    } else {
        name = "...no string";
    }
    return name;
}

// Debug name of enemy list `no` ("1st-1" .. "etc2").
const char* getEmListDbgName(int no)
{
    const char* name;

    if (no >= 0) {
        if ((u32) no <= 10) {
            name = emlist_dbg_name[no];
        } else {
            name = "...no string";
        }
        return name;
    }
    return "?????";
}

// Number of enemy list files (11).
int getEmListNum()
{
    return 11;
}

// Stage change: reload the stage data (heap 2) and link the room's relocatable data (heap 3).
// Room change: when the stage changed or a reload is flagged (System_flg 0x2000 new game, 0x100
// continue, 0x80000) the stage heap is replaced, messages re-initialised (stage 1 sets the
// "village map" flag); when the room needs another REL the room heap is replaced and the REL
// linked; then the enemy list is read.
void StageSet()
{
    GlobalWork* g = pG;
    u32 flags = g->System_flg;
    int reload = 0;
    int relink = 0;

#if defined(RE4DC_GAME) && !defined(__PPC__)
    // Native room owners live in heap 4, which the stage reload / REL relink
    // below overlays with heaps 2 and 3 before gameRoomMemInit replaces it:
    // retire them while it is intact (ui_bridge.cpp room lifecycle).
    re4dc_room_leave(); RE4DC_DOORPH("set.leave");
#endif
    if (flags & 0x2000) {
        reload = 1;
    } else if (flags & 0x100) {
        reload = 1;
    } else if (flags & 0x80000) {
        reload = 1;
    } else if (g->stage_prev != g->stage_no) {
        reload = 1;
    }
    if (reload == 1) {
        RoomData.stopRelData();
        MemReplaceHeap(1, 2); RE4DC_TRACE_OWNER_RELEASE(1);
        MemSetCurrentHeap(2);
        cMes.stageInit(); RE4DC_DOORPH("set.reload");
        if (pG->stage_no == 1) {
            pG->Item_find_flg |= 0x4;
        }
        TaskSleep(1);
    }
    if (RoomData.checkRelRead(G_ROOM_ID) == 1) {
        relink = 1;
    }
    if (relink == 1 || reload == 1) {
        RoomData.stopRelData();
        RoomData.m_RelNo = 0;
        MemReplaceHeap(2, 3); RE4DC_TRACE_OWNER_RELEASE(2);
        MemSetCurrentHeap(3);
        RoomData.linkRelData(G_ROOM_ID); RE4DC_DOORPH("set.rel");
    }
    readEmList(1); RE4DC_DOORPH("set.em");
}

// Reads the enemy list file for the current room into pG->Em_list when it differs from the loaded
// one (always on a new game / save kind 3 / debug); a failed read clears the list.
#if defined(RE4DC_PS2_ENEMY_RULES) && RE4DC_PS2_ENEMY_RULES
#include "em_set.h"
// PS2 enemy rules: the PS2 USA emleon00.esl differs from the GameCube list in these fields only (positions
// aside, which differ by 1 unit of rounding). Entries that start dead are either held back by the PS2 room
// code (r101 0x1A/0x1B, r107 0xA5..0xA9 / 0xED..0xEF: see those rooms) or simply not on the PS2 (r101's
// chicken, three cows and three chickens of r103, two snakes of r10a). The emleon01 rooms (r10f..r11d)
// are not converted until their PS2 room code is ported.
// PS2_ENEMY_ROOMS list rows (lane ps2enemy): r100 / r104 (list 0) and r11a (list 1) belong to these bits alone; the
// ROUTE_CH22 full-record adapter (ps2_enemy_ch22.cpp, applied after this) only owns the chapter 2-2 rooms, so
// ROUTE_CH22 no longer changes r100 / r104 / r11a by itself (lane alivecap 2026-10-15).
#if defined(RE4DC_PS2_ENEMY_ROOMS)
#define RE4DC_PS2_ROOMS_LIST RE4DC_PS2_ENEMY_ROOMS
#else
#define RE4DC_PS2_ROOMS_LIST 0
#endif
static void re4dc_ps2EnemyList(int no)
{
    static const u8 dead00[] = {0x1A, 0x1B, 0x4E, 0x50, 0x54, 0x55, 0x57, 0x58, 0x5C,
                                0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xED, 0xEE, 0xEF, 0xC2, 0xC3};
    u32 i;

#if RE4DC_PS2_ROOMS_LIST & 0x10
    // PS2_ENEMY_ROOMS r11a: the PS2 emleon01 holds 0x16/0x18/0x1C/0x1D back (st1_2 R11aInit and its task send them).
    if (no == 1) {
        EM_LIST(0x16)->be_flag &= ~1;
        EM_LIST(0x18)->be_flag &= ~1;
        EM_LIST(0x1C)->be_flag &= ~1;
        EM_LIST(0x1D)->be_flag &= ~1;
    }
#endif
    if (no != 0) {
        return;
    }
#if RE4DC_PS2_ROOMS_LIST & 0x01
    // PS2_ENEMY_ROOMS r100: the PS2 list swaps the flags of the ambush Ganados 3 and 4.
    EM_LIST(3)->flag = 0x8000003C;
    EM_LIST(4)->flag = 0x2000003C;
#endif
#if RE4DC_PS2_ROOMS_LIST & 0x04
    // PS2_ENEMY_ROOMS r104: entry 0xF1 (a patrol that joins at the dash-in) has the PS2 flags and Character 1.
    EM_LIST(0xF1)->flag = 0x01032400;
    EM_LIST(0xF1)->Character = 1;
#endif
    for (i = 0; i < sizeof(dead00); i++) {
        EM_LIST(dead00[i])->be_flag &= ~1;
    }
    for (i = 0x22; i <= 0x24; i++) {   // r101: flag 0x80 on, Character 1 -> 0
        EM_LIST(i)->flag |= 0x80;
        EM_LIST(i)->Character = 0;
    }
    EM_LIST(0x45)->flag &= ~0x400;     // r101
    EM_LIST(0x46)->flag &= ~0x400;
}
#define RE4DC_PS2_ENEMY_LIST(no) re4dc_ps2EnemyList(no)
#else
#define RE4DC_PS2_ENEMY_LIST(no)
#endif
#line 280 "D:/Bio4/Prog/stage.cpp"
void readEmList(int mode)
{
    const char* name = NULL;
    int result;
    int no;
    int req;

    no = checkEmListNo(G_ROOM_ID);
    if (no >= 0) {
        GlobalWork* g = pG;
        if (no > g->em_list_no || (g->System_flg & 0x2000) || g->SaveKind == 3 ||
            ((s32) g->Debug_flg[2] < 0 && g->em_list_no != no)) {
            name = getEmListName(no);
            pG->em_list_no = no;
        }
    }
    if (name != NULL) {
#line 296 "D:/Bio4/Prog/stage.cpp"
        req = DvdReadN(name, pG->Em_list, 0, 0, 0, mode | 0x10, __FILE__, __LINE__);
        while (Dvd.ReadCheck(req, &result, 0, 0) != 1) {
            TaskSleep(1);
        }
        if (result == 0) {
            memclr_asm(pG->Em_list, 0x2000);
        } else {
            RE4DC_PS2_ENEMY_LIST(pG->em_list_no);
#if defined(RE4DC_ROUTE_CH22) && RE4DC_ROUTE_CH22 && defined(RE4DC_PS2_CH2_ENEMY) && RE4DC_PS2_CH2_ENEMY
            if (re4dc_ps2EnemyListCh22(pG->em_list_no, pG->Em_list, sizeof(pG->Em_list)) < 0)
                re4dc_missing("required PS2 chapter 2-2 enemy list did not match its qualified source");
#endif
#if defined(RE4DC_ROUTE_CH23) && RE4DC_ROUTE_CH23 && defined(RE4DC_PS2_CH2_ENEMY) && RE4DC_PS2_CH2_ENEMY
            if (re4dc_ps2EnemyListCh23(pG->em_list_no, pG->Em_list, sizeof(pG->Em_list)) < 0)
                re4dc_missing("required PS2 chapter 2-3 enemy list did not match its qualified source");
#endif
#if defined(RE4DC_PS2_CH3_ENEMY) && RE4DC_PS2_CH3_ENEMY
            if (re4dc_ps2EnemyListCh3(pG->em_list_no, pG->Em_list, sizeof(pG->Em_list)) < 0)
                re4dc_missing("required PS2 chapter 3 enemy list did not match its qualified source");
#endif
        }
    }
}

// Sub-mission 1 (stage 1 blue medallions): room / room / item no per target.
struct SubMissionTarget {
    u16 room1;   // 0x00
    u16 room2;   // 0x02
    u16 no;      // 0x04
};

static SubMissionTarget st1_target_tbl[15] = {
    {0x103, 0x113, 0x0F}, {0x103, 0x113, 0x10}, {0x103, 0x113, 0x11}, {0x103, 0x113, 0x12},
    {0x103, 0x113, 0x14}, {0x103, 0x113, 0x13}, {0x103, 0x113, 0x15}, {0x108, 0x118, 0x04},
    {0x108, 0x118, 0x05}, {0x108, 0x118, 0x06}, {0x108, 0x118, 0x07}, {0x108, 0x118, 0x09},
    {0x108, 0x118, 0x08}, {0x108, 0x118, 0x0A}, {0x108, 0x118, 0x0B},
};

// Stage 1 medallion `no` (0..14) still unbroken in both of its rooms.
int checkSubMissionTarget(int stage, int no)
{
    u16* p1;
    u16* p2;

    if (stage != 1) {
        return 0;
    }
    p1 = GetEtcFlgPtr(st1_target_tbl[no].no, st1_target_tbl[no].room1);
    p2 = GetEtcFlgPtr(st1_target_tbl[no].no, st1_target_tbl[no].room2);
    if ((*p1 & 1) == 0) {
        if ((*p2 & 1) == 0) {
            return 1;
        }
    } else {
        return 0;
    }
    return 0;
}

// Stage 1 side mission (blue medallions): syncs each target's broken flag between its two rooms,
// counts them; a change shows the counter id (0x33) for 150 frames (450 at 10, which also adds the
// merchant's reward stock and clears Status_flg[2] 0x40000; 15 sets Scenario_flg[0] 0x8000); in
// shooting-range mode the medallion in the current room is shown and pointed at.
void subMissionSt1()
{
    static EtcItem* pCoin = NULL;
    static s16 timer = 0;
    SubMissionTarget* tbl;
    SubMissionTarget* t;
    u16* p1;
    u16* p2;
    EtcItem* item;
    IdUnit* u;
    Vec scr;
    Vec pos;
    int digit[2];
    int count = 0;
    int i;
    int j;

    tbl = st1_target_tbl;
    {
    // `ofs = 0` between `tbl = ...` and `t = tbl` keeps cse from rewriting the lo_sum to set `t`
    // (cse_insn's (set REG0 REG1) swap needs the previous insn to be REG1's set), so the addi
    // result stays `tbl` and `t`/`t0` are copies. room1 is read through `(u32) t0 + ofs`: the
    // base is a register (base-first `lhzx`) that cse2 makes a copy of `t`.
    u32 ofs = 0;
    t = tbl;
    SubMissionTarget* t0 = t;
    do {
        p1 = GetEtcFlgPtr(t->no, t->room1);
        p2 = GetEtcFlgPtr(t->no, t->room2);
        if ((*p1 & 1) || (*p2 & 1)) {
            *p1 |= 1;
            *p2 |= 1;
        }
        if (*p1 & 1) {
            count++;
        }
        if (pG->shooting_mode != 0) {
            if (G_ROOM_ID == ((SubMissionTarget*) ((u32) t0 + ofs))->room1 && !(*p1 & 1)) {
                if (getRoomEtcItem(t->no, &item, 1)) {
                    item->flags &= ~2;
                    pCoin = item;
                }
            }
            if (G_ROOM_ID == t->room2 && !(*p2 & 1)) {
                if (getRoomEtcItem(t->no, &item, 1)) {
                    item->flags &= ~2;
                    pCoin = item;
                }
            }
        }
        t++;
        ofs += sizeof(SubMissionTarget);
    } while (t <= &tbl[14]);
    }

    if (GetFree(0) != count) {
        timer = 150;
        SetFree(0, count);
        if (count == 10) {
            pG->Item_find_flg |= 0x40000;
            timer = 450;
            stockDataAdd(&merchantData, stock_1st_mission);
            pG->Status_flg[2] &= ~0x40000;
        }
        if (count == 15) {
            pG->Scenario_flg[0] |= 0x8000;
        }
        int n = 0;
        int base = 0;

        IdSys.kill(0xFF, 0x33);
        IdSys.set((void*) (pG->pArc->ofs_9C + (u32) pG->pArc), 0xFF, 0x33, 0x13, 5, 0);
        u = IdSys.unitPtr(0, 0x33);
        if (pCoin != NULL) {
            pos = pCoin->pos;
            GetScreenPos(&pos, &scr);
            scr.x = (scr.x - 256.0f) * 1.25f;
            scr.y = (scr.y - 224.0f) * -1.0714285f;
            u->scr = scr;
        }
        for (i = 0; i <= 1; i++) {
            switch (i) {
            case 0:
                n = count;
                base = 1;
                break;
            case 1:
                n = 15;
                base = 0x11;
                break;
            }
            for (j = 0; j <= 1; j++) {
                digit[j] = n % 10;
                n /= 10;
            }
            for (j = 0; j <= 1; j++) {
                u = IdSys.unitPtr(base + j, 0x33);
                u->be_flag |= 0x8;
                u->tex_flag |= 0x2;
                u->texNo = digit[j];
            }
        }
    }
    if (timer > 0) {
        timer--;
        if (timer == 0) {
            IdSys.kill(0xFF, 0x33);
        }
    }
}

// No stage 2 side mission.
void subMissionSt2()
{
}

// No stage 3 side mission.
void subMissionSt3()
{
}

// Per frame (scenario after-hook): the current stage's side mission.
void SubMissionCheck()
{
    switch (pG->stage_no) {
    case 1:
        subMissionSt1();
        break;
    case 2:
        subMissionSt2();
        break;
    case 3:
        subMissionSt3();
        break;
    }
}
