#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "atari.h"
#include "event.h"
#include "light.h"
#include "map_obj.h"
#include "widget.h"
#include "flag_rsf.h"
#include "global.h"
#include "main.h"
#include "sce.h"
#include "sce_sys.h"
#include "sce_at.h"
#include "scroll.h"
#include "obj.h"
#include "obj13.h"
#include "em.h"
#include "emdoor.h"
#include "emwindow.h"
#include "em_set.h"
#include "em_wrap.h"
#include "etc_model.h"
#include "read.h"
#include "dvd.h"
#include "datactrl.h"
#include "esp.h"
#include "est.h"
#include "player.h"
#include "pl_sub.h"
#include "pl_npc.h"
#include "motion.h"
#include "math_sub.h"
#include "mes.h"
#include "cam_ctrl.h"
#include "sscrn.h"
#include "snd.h"
#include "rnd.h"
#include "room_data.h"
#include "flr_at.h"
#include "merchant.h"
#include "TexRender.h"
#include "db_log.h"
#include "eprintf.h"

// PS2_ENEMY_ROOMS bit 0x40 (lane alivecap 2026-10-15): the PS2 cabin (waves of 5, refills below 5 alive, 7 new
// em13 rows, HP +200; list rows from ps2_enemy_ch22.cpp under the same bit).
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ROUTE_CH22 && \
    defined(RE4DC_PS2_ENEMY_RULES) && RE4DC_PS2_ENEMY_RULES && \
    defined(RE4DC_PS2_ENEMY_ROOMS) && (RE4DC_PS2_ENEMY_ROOMS & 0x40)
#define CH22_PS2_ROOM 1
#include "libgpu.h"
extern "C" void OSPanic(const char* file, int line, const char* msg, ...);
#else
#define CH22_PS2_ROOM 0
#endif

#define DEG(d) ((d) * (PI / 180.0f))

// Room 1-1C (D:/Bio4/Prog/r11c.cpp): the village square at night; the besieged cabin (s00: Luis
// arrives, s10: the Ganado wave, s20: the escape), the two gate levers with the gear/chain machinery,
// the merchant.

void Obj18CmfOn(cObj* o, u32 n);   // game/obj18.cpp
void RoomEfmRegist(void* model, void* tpl, u8 id);   // game/eff_sys.cpp (the bin/tpl overload)

// The original passes an uninitialised int to cEmDoor::setCloseLock(int) (no r4 setup).
void cEmDoorSetCloseLock(cEm* door) asm("setCloseLock__7cEmDoori");

extern StockEntry stock_r11c[];               // game/merchant.cpp
extern StockEntry stock_r11c_after_event[];
extern LevelEntry level_null[];

struct R11cWork {
    ReadModule* mod3;        // 0x00  enemy module 3 (Luis; the s00 event data is swapped into its archive)
    ReadModule* mod4;        // 0x04  enemy module 4 (Ashley; the s10 event data)
    u8 pad_8[0x30 - 0x08];
    cDataUnit* evd0;         // 0x30  evd/r11cs00.evd
    cDataUnit* evd1;         // 0x34  evd/r11cs10.evd
    cEm* ashley;             // 0x38  EmMgr.create(4) for the s10 event
    cEm* em;                 // 0x3C  enemy list entry 0xC8 (Luis outside)
    cObj* fire[3];           // 0x40  the bonfires (setFire)
    TexRenderMng* tex;       // 0x4C  TexRenderInit output (the s20 event's water surface)
    u8 texTbl[0x80];         // 0x50  TexRenderModSet parts table
    cObjLadder* ladder[4];   // 0xD0  etc ladders 6..9
    f32 gateY[2];            // 0xE0  rest pos.y of the two gates (smd 0x33 / 0x34)
    ScePrim* closeGate;      // 0xE8  r11c_closeGate task
    ScePrim* gear;           // 0xEC  r11c_moveGear task
    ScePrim* chain;          // 0xF0  r11c_moveChain task
    int eff;                 // 0xF4  EspPullCoreKind of the room ambience
    int effGear;             // 0xF8  EspPullCoreKind of the gear effect
    int effGate;             // 0xFC  EspPullCoreKind of the gate effect
    u32 seGear;              // 0x100 SndCall handle of the gears
    u32 seGate;              // 0x104 SndCall handle of the gate
#if CH22_PS2_ROOM
    int ladderResetTime[4];  // PS2 room work +0x108
    int ps2ScenarioVariant;   // frozen PS2 stage-entry selector (GlobalWork +0x7ec9)
#endif
};

// One-member struct: every store into the work reloads the pointer afterwards.
struct R11cWorkPtr {
    R11cWork* p;
};
static R11cWorkPtr r11c_work;
#define W r11c_work.p

// The room save block: +4 is the flag word (bit 25 event done, bits 21..24 ladders 3..0 down,
// bit 30 a route chosen, bit 29 the right route).
struct R11cSave {
    u32 x0;
    u32 flags;
};
static inline u32* r11c_evtKey(EventMgr* m) { return &m->NowExeEvtKey; }
struct PlPtr { cPlayer* p; };
#define pPLS (((PlPtr*) &pPL)->p)

static inline R11cSave* r11c_save() { return (R11cSave*) RoomData.getRoomSavePtr(pGS->room_id); }

// Death bit of entry `no` of the loaded enemy list (0 while no list is loaded), em_set.cpp style: the
// row offset is added to pG before the table offset (`lwz 0x5034(pG + list * 0x20)`).
static inline u32 r11c_emDead(u32 no)
{
    u32 v;

    if (pG->em_list_no >= 0) {
        u32* tbl = (u32*) (pG->em_list_no * 0x20 + (u32) pG + 0x501C);

        v = tbl[no >> 5] & (0x80000000 >> (no & 31));
    } else {
        v = 0;
    }
    return v;
}

#if CH22_PS2_ROOM
// PS2 USA st1_3.rel tables 0x1dcd8/0x1dcf0/0x1dd08 and 0x1dd78.
// Rows 155/158 are authored but held and absent from the source wave tables.
static const int r11cPs2Wave[2][5] = {
    {201, 202, 204, 206, 207},
    {153, 154, 156, 157, 159},
};
static const int r11cPs2WaveLadder[5] = {1, -1, 3, 0, 2};
static const int r11cPs2LadderTime[4] = {60, 150, 210, 300};

// Native Em10Work::pLadder is +0x4E4 from cEm::x3E0. A separate
// SH-4 TU including em10.h checks this offset and projection size at compile
// time; obj13.h and em10.h have distinct declarations of cObjLadder.
struct R11cNativeGanadoLadder {
    u8 beforeLadder[0x4E4];
    cObjLadder* pLadder;
};

// PS2 helper 0xf3f8: preserve the otherwise-unused Rnd call and routine state.
static void r11c_ps2Climb(cEm* em, int no)
{
    if (no < 0 || no >= 4) return;
    cObjLadder* ladder = W->ladder[no];
    if (ladder == 0 || ladder->getStatus() != 0) return;
    Rnd();
    if (em == 0) return;
    ((R11cNativeGanadoLadder*) &em->x3E0)->pLadder = ladder;
    ladder->setClimb();
    em->r_no_0 = 1;
    em->r_no_1 = 0x40;
    em->r_no_2 = 0;
    em->r_no_3 = 0;
}

// PS2 helper 0xf500: only a successful reset advances the siege count.
static int r11c_ps2Reset(cEm* em, int* count)
{
    cEmGanado* ganado = (cEmGanado*) em;
    if (ganado->ckResetEnable() != 1) return 0;
    if (r11c_save()->flags & 0x02000000) ganado->chgSet(0xE);
    ganado->setReset();
    ++*count;
    return 1;
}

// PS2 helper 0xf2c8, called each siege tick after the upper floor opens.
static void r11c_ps2ResetLadders()
{
    for (int i = 0; i < 4; i++) {
        cObjLadder* ladder = W->ladder[i];
        if (ladder != 0 && ladder->getStatus() == 1) {
            if (--W->ladderResetTime[i] <= 0) {
                W->ladderResetTime[i] = r11cPs2LadderTime[Rnd() & 3];
                ladder->setReset(1);
            }
        }
    }
}

static void r11c_ps2FlagArea()
{
    // Exact PS2 AEV13 flag-area bounds; source native AEV ends at12/type2.
    static AreaData area = {1, AREA_TYPE_XZ4, 0, {{2476.53662f, 5814.60205f, 750.0f, {{104543.586f, -56024.9062f}, {119500.336f, -56018.5391f}, {119668.531f, -43924.3398f}, {104757.055f, -43849.1875f}}}}};
    SceAtWork* prev = SceAtPtr(12);
    if (prev == 0 || prev->type != 2 || prev->otNo != 2) {
        OSPanic(__FILE__, __LINE__, "ch22 r11c: expected source AEV12 boundary");
        return;
    }
    Vec corners[4];
    for (int i = 0; i < 4; i++) {
        corners[i].x = area.u.xz4.p[i].x;
        corners[i].y = area.u.xz4.floor;
        corners[i].z = area.u.xz4.p[i].z;
    }
    int no = SceAtCreateExecAt(pPL, corners, 0, 1, 1, area.u.xz4.height,
                             2, 0.0f, 0.0f, 0, 0, 0, 0, 0);
    SceAtWork* at = no >= 0 ? SceAtPtr(no) : 0;
    if (at == 0) {
        OSPanic(__FILE__, __LINE__, "ch22 r11c: PS2 AEV allocation failed");
        return;
    }
    DelPrim((u32*) sceAtSetOtStart(), (u32*) at);
    at->area = area;
    at->type = 4;
    at->pParent = 0;
    at->parentParts = 0;
    at->angleRange = 45;
    at->flg.kind = 0;
    at->flg.off = 0;
    at->flg.no = 65;
    AddPrim((u32*) prev, (u32*) at);
}
#endif

extern "C" void r11c_eventInit();
static void r11c_EventBesiegedStart();
static void r11c_ThunderMove();
extern "C" void r11c_initGate();
extern "C" void r11c_openGate(u32 id);
static void r11c_closeGate(u32 id);
static void r11c_moveGear(int dir);
static void r11c_moveChain(int dir);
static void r11c_moveLever2(int dir);
extern "C" void r11c_moveLever(int dir, int noGear);
static void r11c_selectRoute_end(int sel);
static void r11c_selectRoute();
static void r11c_operator();
extern "C" void setFire();
extern "C" void deleteFire();
extern "C" void Evt_R11CS00_Func(Event* e);
extern "C" void Evt_R11CS10_Func(Event* e);
extern "C" void Evt_R11CS20_Func(Event* e);

// Room init: thunder task, rain on the player, Status_flg[1] 0x400, the four etc ladders (all down
// before the siege event, else only those the save block's bits 21..24 remember as knocked down); until
// the siege is done (save flags bit 25) area 3 starts it and Luis (ESL 0xC8) waits outside; afterwards
// areas 8/9 are off, the merchant stock (stock_r11c / _after_event) is added, area 0xC is the typewriter
// and the gates follow the chosen route (r11c_initGate). Bonfires, room ambience effect, rack ranges.
void R11cInit()
{
    cEm* rack;
    cEm* em;
    void* arc;

#line 75 "D:/Bio4/Prog/r11c.cpp"
    W = (R11cWork*) MEM_CALLOC(sizeof(R11cWork), 1, 0xd);
#if CH22_PS2_ROOM
    // PS2 main ELF gameStageInit 0x217b84..0x217bdc derives its
    // scenario selector from difficulty, with JP special-mode overrides.
    // Native pG->language is a persistent language setting and is not this
    // derived field. Snapshot at room entry before events change system flags.
    W->ps2ScenarioVariant = pG->game_mode >= 4;
    if (pSys->language == 0 && (pG->System_flg & 0xC0001000u)) {
        W->ps2ScenarioVariant = 0;
    }
    r11c_ps2FlagArea();
#endif

    SceExec(0x12, (TaskFunc) r11c_ThunderMove, 0, 0, SCE_PRIO_DEF_2, 0);
    EstSet((int) pPL, -1, 0, 0, 1, 0, 0x800, 0, 0, 0);
    EstSet((int) pPL, -1, 0, 0, 3, 1, 0x800, 0, 0, 0);
    EstSet((int) pPL, -1, 0, 0, 0, 0x23, 0x800, 0, 0, 0);
    pG->Status_flg[1] |= 0x400;
    EstSet(0, -1, 0, 0, 1, 0xA, 1, 2, 0, 0);
    getRoomEtcLadder(6, (cEm**) &W->ladder[0], 1);
    getRoomEtcLadder(7, (cEm**) &W->ladder[1], 1);
    getRoomEtcLadder(8, (cEm**) &W->ladder[2], 1);
    getRoomEtcLadder(9, (cEm**) &W->ladder[3], 1);
    if (!(r11c_save()->flags & 0x02000000)) {
        if (W->ladder[0]) {
            W->ladder[0]->setOff();
            W->ladder[0]->setDowned();
        }
        if (W->ladder[1]) {
            W->ladder[1]->setOff();
            W->ladder[1]->setDowned();
        }
        if (W->ladder[2]) {
            W->ladder[2]->setOff();
            W->ladder[2]->setDowned();
        }
        if (W->ladder[3]) {
            W->ladder[3]->setOff();
            W->ladder[3]->setDowned();
        }
    } else {
        if (!(r11c_save()->flags & 0x01000000) && W->ladder[0]) {
            W->ladder[0]->setDowned();
        }
        if (!(r11c_save()->flags & 0x00800000) && W->ladder[1]) {
            W->ladder[1]->setDowned();
        }
        if (!(r11c_save()->flags & 0x00400000) && W->ladder[2]) {
            W->ladder[2]->setDowned();
        }
        if (!(r11c_save()->flags & 0x00200000) && W->ladder[3]) {
            W->ladder[3]->setDowned();
        }
    }
    if (getRoomEtcRack(0, &rack, 1)) {
        ((cEmRack*) rack)->setRange(0.0f, 0.0f, 0.0f, 10000.0f);
    }
    if (getRoomEtcRack(1, &rack, 1)) {
        ((cEmRack*) rack)->setRange(0.0f, 10000.0f, 0.0f, 10000.0f);
    }
    if (getRoomEtcRack(2, &rack, 1)) {
        ((cEmRack*) rack)->setRange(0.0f, 10000.0f, 0.0f, 10000.0f);
    }
    if (!(pG->Item_find_flg & 0x00020000)) {
        SceAtDataSet_exec(3, SCE_LEVEL10, 0, (TaskFunc) r11c_EventBesiegedStart, 0, 1);
        r11c_eventInit();
        if (!r11c_emDead(0xC8)) {
            W->em = EmSetFromList2(0xC8, 0);
            if (W->em != 0) {
                Vec pos = {62402.0f, -0.33f, -58554.0f};
                Vec ang;
                f32 ry = -2.86535f;
                cEm* e = W->em;
                Vec* pa = &ang;

                e->setPos(&pos);
                ang.x = 0.0f;
                pa->y = ry;
                ang.z = 0.0f;
                e->setAng(&ang);
            }
        }
        W->eff = EspPullCoreKind();
        EstSet(0, -1, 0, 0, 1, 0xB, 1, (u8) W->eff, 0, 0);
    } else {
        if (!r11c_emDead(0xC8)) {
            EmSetFromList2(0xC8, 0);
        }
        SceAtSetEnable(8, 0);
        SceAtSetEnable(9, 0);
        SmdGetObjPtr(0x3F)->be_flag &= ~2;
    }
    {
        cObj* g0 = SmdGetObjPtr(0x33);
        cObj* g1 = SmdGetObjPtr(0x34);

        if (g0 && g1) {
            g0->be_flag |= 0x20;
            g1->be_flag |= 0x20;
            W->gateY[0] = g0->pos.y;
            W->gateY[1] = g1->pos.y;
            W->effGear = EspPullCoreKind();
            W->effGate = EspPullCoreKind();
        }
    }
    r11c_initGate();
    EvtMgr.SetFunc("evt_r11cs00_func", (void*) Evt_R11CS00_Func);
    EvtMgr.SetFunc("evt_r11cs10_func", (void*) Evt_R11CS10_Func);
    EvtMgr.SetFunc("evt_r11cs20_func", (void*) Evt_R11CS20_Func);
    if (!(pG->Scenario_flg[0] & 0x00020000)) {
        SceAtDataSet_exec(0xC, SCE_LEVEL10, 0, (TaskFunc) r11c_operator, 0, 1);
    }
    if (EtcGetDasAddr(0x14, &arc)) {
        RoomEfmRegist(GetEtcAddr(arc, "et1400.bin"), GetEtcAddr(arc, "et1400.tpl"), 0x6F);
    }
    FlrAtSetDefVal(0, 0, 3);
    if (!(pG->Item_find_flg & 0x00020000) && RoomData.checkPassed(pG->room_id, 0) == 0) {
        levelDataAdd(merchantData, level_null);
        stockDataAdd(merchantData, stock_r11c);
    }
    merchantChar.setChar(&merchant_info_A, merchantData, g_item_price_tbl, g_item_price_tbl, level_price);
    TexRenderInit(&W->tex, 0, 2);
    CamCtrl.AreaOnOff(1, 0, 0);
}

// The ladders the player knocked down are remembered in the room save block.
void R11cMain()
{
    cEm* ladder;

    if (r11c_save()->flags & 0x02000000) {
        if (getRoomEtcLadder(6, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 0) {
            r11c_save()->flags |= 0x01000000;
        }
        if (getRoomEtcLadder(7, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 0) {
            r11c_save()->flags |= 0x00800000;
        }
        if (getRoomEtcLadder(8, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 0) {
            r11c_save()->flags |= 0x00400000;
        }
        if (getRoomEtcLadder(9, &ladder, 1) && ((cObjLadder*) ladder)->getStatus() == 0) {
            r11c_save()->flags |= 0x00200000;
        }
    }
}

#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ROUTE_MOVIES && RE4DC_ROUTE_CH22
// Route cutscenes (ROUTE_CH22, r11c the chapter 2-2 end): s00 (the siege begins), s10 (the siege ends) and s20 (the
// way out) are presented by their PS2 movies, the r117 pattern. While the movies own the events no evd is read: the
// two DC.setData registrations, both ARAM loads and the s20 ARAM read are skipped, and enemy modules 0x13 / 3 / 4 are
// read at their own size instead of being sized for the evd swaps. The handlers' begin / end modes run; the rest of
// the source (flags, waves, Ashley, ladders, windows, merchant, chapter end) is unchanged. All three movies must exist.
#include "route_movie.h"
#if RE4DC_CABIN_SOURCE
#define R11C_ROUTE_MOVIES 0
#else
#define R11C_ROUTE_MOVIES 1
#endif
#define R11C_MOVIES_OWN() (re4dc_movie_available(0x11c00) && re4dc_movie_available(0x11c10) && re4dc_movie_available(0x11c20))
#else
#define R11C_ROUTE_MOVIES 0
#define R11C_MOVIES_OWN() 0
#endif

// Before the siege: pre-load evd r11cs00 to ARAM and register r11cs10, pre-read enemy modules 0x13 and 3
// (Luis), mark Ashley as following (Status_flg[3] 0x04000000), init the partner at Leon's position in
// chase mode, and keep module 3 for the event-data swap.
#if RE4DC_CABIN_SOURCE
#include "native_cabin.h"
#include "re4dc_platform.h"
#endif
#if RE4DC_CABIN_SOURCE
static void r11c_cabin_begin(unsigned id){
    const unsigned heap=MemGetCurrentHeap();
    if(heap>=MEM_HEAP_NUM || Heap[heap].handle<0 || Heap[4].handle<0 ||
       !re4dc_cabin_begin(id,(void*)Heap[heap].start,Heap[heap].end-Heap[heap].start,
                         (void*)Heap[4].start,Heap[4].end-Heap[4].start))
        re4dc_missing("cabin source entry");
}
static void r11c_cabin_done(unsigned id,int keep){
    re4dc_cabin_source_done(id,keep);
    if(!keep)while(!re4dc_cabin_aftermath(id))SceSleep(1);
}
#endif
extern "C" void r11c_eventInit()
{
#if RE4DC_CABIN_SOURCE
    if(!re4dc_cabin_preflight(pG->game_costume))re4dc_missing("cabin preflight");
#endif
#if R11C_ROUTE_MOVIES
    if (R11C_MOVIES_OWN()) {
        EmReadSearch(0x13, 0, 0);
        EmReadSearch(3, 0, 0);
    } else {
#endif
    W->evd0 = DC.setData(EvtMgr.NameChange("evd/r11cs00.evd"));
    W->evd0->setCommand(CMND_ARAM_LOAD, 0, 0);
    W->evd1 = DC.setData(EvtMgr.NameChange("evd/r11cs10.evd"));
    EmReadSearch(0x13, 0, W->evd0->m_size);
    EmReadSearch(3, 0, 0x120000);
#if R11C_ROUTE_MOVIES
    }
#endif
    BitOn(pG->Status_flg[3], 0x04000000);
    SubCharInit(1, &pPL->pos, pPL->ang.y);
    SubCharCtrl(SCC_CHASE, 0);
    W->mod3 = SearchEmModule(3);
}

// Area 3: the cabin siege. The s00 event, the Ganado waves (list 0xC9..0xD1) until 40 are down or
// 3600 frames passed, then the s10 event and the chapter end.
static void r11c_EventBesiegedStart()
{
    cEm* door;
    ReadModule* mod;
    int err;

    BitOn(pG->Item_find_flg, 0x00020000);
    BitOn(pG->Room_flg[0], 0x40000000);
    EffectEspDelete(0, (u8) W->eff, 0, 0);
    EffectEspgenDelete(0, (u8) W->eff, 0);
    EffectEfmDelete(0, (u8) W->eff, 0);
    SceEventStart(0);
    if (pSUB) {
        EmMgr.destroy(pSUB);
        pG->Status_flg[3] &= ~0x04000000;
    }
    if (getRoomEtcDoor(0xA, &door, 1)) {
        door->setNoSuspend(0);
        cEmDoorSetCloseLock(door);
    }
    pG->System_flg |= 0x400;
#if R11C_ROUTE_MOVIES
    if (!W->evd0) {
        EmMgr.destroy(W->em);
        SceSleep(2);
        InitModule(W->mod3);
        RouteMoviePlay(0x11c00, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R11CS00_Func, 0);
    } else {
#endif
    err = W->evd0->waitLoadOk() == 0;
    EmMgr.destroy(W->em);
    SceSleep(2);
    InitModule(W->mod3);
    mod = SearchEmModule(0x13);
    if (err == 1) {
        pLog->err(0, 0, "r11c_Event00 data read error");
        {
            Vec pos = {109264.0f, 4.0f, -50575.0f};
            Vec ang;
            f32 ry = 1.11f;
            cPlayer* pl = pPLS;
            Vec* pa = &ang;

            pl->setPos(&pos);
            ang.x = 0.0f;
            pa->y = ry;
            ang.z = 0.0f;
            pl->setAng(&ang);
        }
    } else if (W->evd0->m_size > mod->size) {
        pLog->err(0, 0, "r11c_Event00 data size over");
        {
            Vec pos = {109264.0f, 4.0f, -50575.0f};
            Vec ang;
            f32 ry = 1.11f;
            cPlayer* pl = pPLS;
            Vec* pa = &ang;

            pl->setPos(&pos);
            ang.x = 0.0f;
            pa->y = ry;
            ang.z = 0.0f;
            pl->setAng(&ang);
        }
    } else {
        MemorySwap(mod->pArc, (u32) W->evd0->m_addr, W->evd0->m_size);
#if RE4DC_CABIN_SOURCE
        r11c_cabin_begin(0x11c00);
#endif
        EvtMgr.SetEvt(mod->pArc, (u32*) 0);
        SceSleep(2);
        SceSleep(2);
        while (EvtMgr.IsAliveEvt(&EvtMgr.NowExeEvtKey, 0, 0) != 0) {
            SceSleep(1);
        }
        MemorySwap(mod->pArc, (u32) W->evd0->m_addr, W->evd0->m_size);
    }
    W->evd0->setCommand(CMND_DEL_DATA, 0, 0);
#if R11C_ROUTE_MOVIES
    }
#endif
    pG->System_flg |= 0x400;
#if R11C_ROUTE_MOVIES
    EmReadSearch(4, 0, W->evd1 ? 0x120000 : 0);
#else
    EmReadSearch(4, 0, 0x120000);
#endif
    W->ashley = EmMgr.create(4);
    // Mid-function declarations: the two error arms above own block-local pos/ang pairs, so these
    // reuse their (combined) temp slots and the em[] array lands behind them.
    Vec pos = {107427.0f, 4.0f, -48370.0f};
    Vec ang;
    f32 ry = 1.27f;
    cEm* ashley = W->ashley;
    Vec* pa = &ang;

    ashley->setPos(&pos);
    ang.x = 0.0f;
    pa->y = ry;
    ang.z = 0.0f;
    ashley->setAng(&ang);
    W->ashley->set = 1;
    W->mod4 = SearchEmModule(4);
    {
        cPlayer* pl = pPLS;
        const f32 x = 107436.0f;
        const f32 y = 4.0f;
        const f32 z = -47160.0f;
        f32 ry2 = -2.41f;

        pos.x = x;
        pos.y = y;
        pos.z = z;
        pl->setPos(&pos);
        pos.x = 0.0f;
        pos.y = ry2;
        pos.z = 0.0f;
        pl->setAng(&pos);
    }
    cEm* em[20];
    cEm* e;
    cEm* win;
    cEm* ladder;
    Event* ev;
    cEm* door2;
    cEm* win2;
    int n;
    int i;
    int kill;
    int t;
    ReadModule* mod2;
    int err2;

#if R11C_ROUTE_MOVIES
    if (W->evd1)
#endif
    W->evd1->setCommand(CMND_ARAM_LOAD, 0, 0);
    SceSleep(2);
    pG->System_flg &= ~0x400;
    SceEventEnd(0);
#if RE4DC_CABIN_SOURCE
    r11c_cabin_done(0x11c00,0);
#endif
    CamCtrl.AreaOnOff(1, 0, 1);
    SndRoomStrStart(1, 3, 1);
#if R11C_ROUTE_MOVIES
    if (W->evd1)
#endif
    EvtMgr.EvtReadAram("event/evd/r11cs20.evd", 0, 0, 0, 0);
    EffectEspDelete(0, 2, 0, 0);
    EffectEspgenDelete(0, 2, 0);
    EffectEfmDelete(0, 2, 0);
    setFire();
    if (getRoomEtcWindow(3, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(4, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(5, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(0x12, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(0x13, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(0x14, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
    if (getRoomEtcWindow(0x15, &win, 1)) {
        ((cEmWindow*) win)->SetEnableFence(0, 1);
    }
#if CH22_PS2_ROOM
    n = 10;
    for (i = 0; i < n; i++) em[i] = 0;
    for (i = 0; i < 5; i++) em[i] = EmSetFromList2(r11cPs2Wave[0][i], 0);
    for (i = 0; i < 4; i++) W->ladderResetTime[i] = r11cPs2LadderTime[i];
#else
    n = 0;
    e = EmSetFromList2(0xC9, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCA, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCB, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCC, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCD, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCE, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xCF, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xD0, 0);
    if (e) {
        em[n] = e;
        n++;
    }
    e = EmSetFromList2(0xD1, 0);
    if (e) {
        em[n] = e;
        n++;
    }
#endif
    kill = 0;
    t = 0;
#if CH22_PS2_ROOM
    // PS2 st1_3.rel 0xfbb4: normal variant 40/9000, easy 30/7200.
    const int killLimit = W->ps2ScenarioVariant ? 40 : 30;
    const int timeLimit = W->ps2ScenarioVariant ? 9000 : 7200;
#endif
    while (1) {
#if CH22_PS2_ROOM
        if (pG->Room_flg[0] & 0x20000000) {
            SceEventStart(0);
            SndRoomStrStop(3);
            pG->System_flg |= 0x400;
            SceDestroyEm(0x10, 0x20);
            SceSleep(2);
            InitModule(SearchEmModule(0x13));
#if R11C_ROUTE_MOVIES
            if (!W->evd1) {
                RouteMoviePlay(0x11c20, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R11CS20_Func, 0);
            } else
#endif
#if RE4DC_CABIN_SOURCE
            r11c_cabin_begin(0x11c20);
#endif
            EvtMgr.EvtReadExec("event/evd/r11cs20.evd", 0, 2);
            SceEventEnd(0);
#if RE4DC_CABIN_SOURCE
            r11c_cabin_done(0x11c20,1);
#endif
            SceExit();
        }
        if (SceCountEmAlive(0x10, 0x20) < 5) {
            for (i = 0; i < 5; i++) {
                int upper = (pG->Room_flg[2] & 0x40000000) != 0;
                int slot = upper * 5 + i;
                e = em[slot];
                int changed;
                if (e == 0) {
                    e = EmSetFromList2(r11cPs2Wave[upper][i], 0);
                    if (e == 0) continue;
                    em[slot] = e;
                    ++kill;
                    changed = 1;
                } else {
                    changed = r11c_ps2Reset(e, &kill);
                }
                if (changed) {
                    if (upper) r11c_ps2Climb(e, r11cPs2WaveLadder[i]);
                    break;
                }
            }
        }
#else
        for (i = 0; i < n; i++) {
            if (pG->Room_flg[0] & 0x20000000) {
                SceEventStart(0);
                SndRoomStrStop(3);
                pG->System_flg |= 0x400;
                SceDestroyEm(0x10, 0x20);
                SceSleep(2);
                InitModule(SearchEmModule(0x13));
#if R11C_ROUTE_MOVIES
                if (!W->evd1) {
                    RouteMoviePlay(0x11c20, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R11CS20_Func, 0);
                } else
#endif
#if RE4DC_CABIN_SOURCE
                r11c_cabin_begin(0x11c20);
#endif
                EvtMgr.EvtReadExec("event/evd/r11cs20.evd", 0, 2);
                SceEventEnd(0);
#if RE4DC_CABIN_SOURCE
                r11c_cabin_done(0x11c20,1);
#endif
                SceExit();
            }
            e = em[i];
            if (((cEmGanado*) e)->ckResetEnable() == 1) {
                kill++;
                if (r11c_save()->flags & 0x02000000) {
                    ((cEmGanado*) e)->chgSet(0xE);
                }
                ((cEmGanado*) e)->setReset();
            }
        }
#endif
        t++;
        if (t == 3600) {
            r11c_save()->flags |= 0x02000000;
            W->ashley->set = 2;
            if (getRoomEtcLadder(6, &ladder, 1)) {
                ((cObjLadder*) ladder)->setOn();
            }
            if (getRoomEtcLadder(7, &ladder, 1)) {
                ((cObjLadder*) ladder)->setOn();
            }
            if (getRoomEtcLadder(8, &ladder, 1)) {
                ((cObjLadder*) ladder)->setOn();
            }
            if (getRoomEtcLadder(9, &ladder, 1)) {
                ((cObjLadder*) ladder)->setOn();
            }
        }
#if CH22_PS2_ROOM
        if (r11c_save()->flags & 0x02000000) r11c_ps2ResetLadders();
#endif
#if CH22_PS2_ROOM
        if (kill >= killLimit || t >= timeLimit || DebugTrg(0) == 1) {
#else
        if (kill > 39 || t > 8999 || DebugTrg(0) == 1) {
#endif
            break;
        }
        SceDebugDisp("T[%d]", 9000 - t);
        SceDebugDisp("E[%d]", 40 - kill);
        SceSleep(1);
    }
    EffectEspDelete(0, 2, 0, 0);
    EffectEspgenDelete(0, 2, 0);
    EffectEfmDelete(0, 2, 0);
    deleteFire();
    if (W->ladder[0]) {
        W->ladder[0]->be_flag &= ~2;
    }
    if (W->ladder[1]) {
        W->ladder[1]->be_flag &= ~2;
    }
    if (W->ladder[2]) {
        W->ladder[2]->be_flag &= ~2;
    }
    if (W->ladder[3]) {
        W->ladder[3]->be_flag &= ~2;
    }
    SndRoomStrStop(5);
    SceEventStart(0);
    pG->System_flg |= 0x400;
#if R11C_ROUTE_MOVIES
    err2 = W->evd1 ? W->evd1->waitLoadOk() == 0 : 0;
#else
    err2 = W->evd1->waitLoadOk() == 0;
#endif
    for (i = 0; i < n; i++) {
        e = em[i];
#if CH22_PS2_ROOM
        if (e != 0 && (e->be_flag & 0x201) == 1) {
#else
        if ((e->be_flag & 0x201) == 1) {
#endif
            EmMgr.destroy(e);
        }
    }
    EmMgr.destroy(W->ashley);
    pSUB = 0;
    SceSleep(2);
    InitModule(W->mod4);
    mod2 = SearchEmModule(0x13);
#if R11C_ROUTE_MOVIES
    if (!W->evd1) {
        RouteMoviePlay(0x11c10, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R11CS10_Func, 0);
    } else
#endif
    if (err2 != 1) {
        if (W->evd1->m_size > mod2->size) {
            pLog->err(0, 0, "r11c_Event10 exec error");
        } else {
            MemorySwap(mod2->pArc, (u32) W->evd1->m_addr, W->evd1->m_size);
#if RE4DC_CABIN_SOURCE
            r11c_cabin_begin(0x11c10);
#endif
            if (EvtMgr.SetEvt(mod2->pArc, (u32*) &ev)) {
                ev->StatusFlag |= 0x400;
            }
            while (EvtMgr.IsAliveEvt(r11c_evtKey(&EvtMgr), 0, 0) != 0) {
                SceSleep(1);
            }
            MemorySwap(mod2->pArc, (u32) W->evd1->m_addr, W->evd1->m_size);
        }
    }
#if R11C_ROUTE_MOVIES
    if (W->evd1)
#endif
    W->evd1->setCommand(CMND_DEL_DATA, 0, 0);
    pG->System_flg &= ~0x400;
    SceEventEnd(0);
#if RE4DC_CABIN_SOURCE
    r11c_cabin_done(0x11c10,0);
#endif
    r11c_initGate();
    BitOn(pG->Status_flg[3], 0x04000000);
    SubCharInit(1, &pPL->pos, pPL->ang.y);
    SubCharCtrl(SCC_CHASE, 0);
    if (!r11c_emDead(0xC8)) {
        EM_LIST(0xC8)->be_flag &= ~2;
        EmSetFromList2(0xC8, 0);
    }
    CamCtrl.AreaOnOff(1, 0, 0);
    if (getRoomEtcDoor(0xA, &door2, 1)) {
        ((cEmDoor*) door2)->setNormal();
    }
    if (getRoomEtcWindow(3, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(4, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(5, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(0x12, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(0x13, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(0x14, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (getRoomEtcWindow(0x15, &win2, 1)) {
        ((cEmWindow*) win2)->SetEnableFence(1, 1);
    }
    if (W->ladder[0]) {
        W->ladder[0]->be_flag |= 2;
    }
    if (W->ladder[1]) {
        W->ladder[1]->be_flag |= 2;
    }
    if (W->ladder[2]) {
        W->ladder[2]->be_flag |= 2;
    }
    if (W->ladder[3]) {
        W->ladder[3]->be_flag |= 2;
    }
    {
        // The zero for EstSet's two stack arguments is born at the top of the block (it crosses the
        // calls below, so sched1 may hoist it): a block-local, as in r111.
        void* zero = 0;

        pG->Item_find_flg |= 0x40;
        stockDataAdd(merchantData, stock_r11c_after_event);
        merchantChar.setChar(&merchant_info_A, merchantData, g_item_price_tbl, g_item_price_tbl, level_price);
        SceAtSetEnable(8, 0);
        SceAtSetEnable(9, 0);
        SmdGetObjPtr(0x3F)->be_flag &= ~2;
        EstSet(0, -1, 0, 0, 1, 0xA, 1, 0, (u32) zero, zero);
    }
    pG->Room_flg[0] &= ~0x40000000;
    SceSetChapterEnd(CHAPTER_2_2, -1);
}

// Thunder while the siege is not running.
// The loop body is written in small statements on purpose: the loop is one haifa scheduling region
// only if its LUID span (insns + notes) is <= 100, and the target shows no interblock motion (the
// `cmpwi cnt` stays behind the flag branch, the EstSet arg `li`s stay behind `bne`), so the target's
// loop was over that limit.
static void r11c_ThunderMove()
{
    int cnt = 0;

    SceSleep(1);
    for (;;) {
        u32 f;

        f = pG->Room_flg[0];
        if (!(f & 0x40000000)) {
            if (cnt <= 0) {
                int st;

                st = EffGetAreaState(3);
                if (st == 0) {
                    EstSet(0, -1, 0, 0, 1, 1, 1, 0, 0, 0);
                } else {
                    EstSet(0, -1, 0, 0, 1, 0xC, 1, 0, 0, 0);
                }
                SceSndCallThunder();
                {
                    u8 r;
                    int c;

                    r = Rnd();
                    r %= 30;
                    c = r * 5;
                    c += 90;
                    cnt = c;
                }
            }
            cnt--;
        } else {
            u8 r;
            int c;

            r = Rnd();
            r %= 30;
            c = r * 5;
            c += 90;
            cnt = c;
        }
        SceSleep(1);
    }
}

// The two gates (smd 0x33 left, 0x34 right): up before the siege, then by the chosen route.
extern "C" void r11c_initGate()
{
    cObj* g0 = SmdGetObjPtr(0x33);
    cObj* g1 = SmdGetObjPtr(0x34);

    if (g0 && g1) {
        if (!(pG->Item_find_flg & 0x00020000)) {
            const f32 h = 3600.0f;

            g0->pos.y += h;
            g1->pos.y += h;
        } else {
            SceAtDataSet_exec(4, SCE_LEVEL10, 0, (TaskFunc) r11c_selectRoute, 0, 2);
            if (!(r11c_save()->flags & 0x40000000)) {
                g0->pos.y = 0.0f;
                g1->pos.y = 0.0f;
            } else {
                if (r11c_save()->flags & 0x20000000) {
                    g1->pos.y += 3600.0f;
                    SceAtSetEnable(5, 0);
                } else {
                    g0->pos.y += 3600.0f;
                    SceAtSetEnable(6, 0);
                }
                SceAtSetEnable(0xA, 0);
                SceAtSetEnable(0xB, 0);
            }
        }
    }
}

// Task: raise gate `id` (smd 0x33 / 0x34) by 3600 units over 80 frames with a rattle, gate effect and
// sound; sets Room_flg[2] bit 31 (a gate is open).
extern "C" void r11c_openGate(u32 id)
{
    cObj* g = SmdGetObjPtr(id);
    const f32 step = 45.0f;
    f32 dst;
    int i;

    g->be_flag |= 0x20;
    dst = 3600.0f + g->pos.y;
    EstSet(0, -1, 0, 0, 1, 6, 1, (u8) W->effGate, 0, 0);
    W->seGate = SndCall(6, 0x57, 0, 0, 0, 0);
    {
        f32 sw[4] = {10.0f, -10.0f, 20.0f, -20.0f};

        for (i = 0; i < 80; i++) {
            g->pos.y += sw[i % 4] + step;
            SceSleep(1);
        }
    }
    g->pos.y -= step;
    SceSleep(1);
    g->pos.y += step;
    SceSleep(1);
    g->pos.y = dst;
    EffectEspDelete(0, (u8) W->effGate, 0, 0);
    EffectEspgenDelete(0, (u8) W->effGate, 0);
    EffectEfmDelete(0, (u8) W->effGate, 0);
    pG->Room_flg[2] |= 0x80000000;
    SceSleep(10);
}

// Task: drop gate `id` 3600 units with acceleration 20/frame^2, then clears the task handle W->closeGate.
static void r11c_closeGate(u32 id)
{
    cObj* g = SmdGetObjPtr(id);
    f32 dst = g->pos.y - 3600.0f;
    const f32 acc = 20.0f;
    f32 spd = 0.0f;

    g->be_flag |= 0x20;
    // The exit store on the break path keeps jump1 from folding the peeled exit test over `b END`;
    // jump2's cross-jump merges the two exit jumps (`cmp; b TEST; ...; TEST: bge TOP; stfs dst`).
    for (;;) {
        g->pos.y -= spd;
        spd += acc;
        if (g->pos.y < dst) {
            g->pos.y = dst;
            break;
        }
        SceSleep(1);
    }
    W->closeGate = 0;
}

// The gear train (smd 0x10, 0x11, 0x32) turns while the gate moves (sceat_x17C bit 31).
static void r11c_moveGear(int dir)
{
    cObj* g0;
    cObj* g1;
    cObj* g2;
    const f32 t0 = 72.0f;
    const f32 t2 = 63.0f;
    const f32 t1 = 36.0f;
    const f32 max = 1.0f;
    const f32 acc = 0.04f;
    f32 t;
    f32 d;

    SceSleep(15);
    g0 = SmdGetObjPtr(0x10);
    g1 = SmdGetObjPtr(0x11);
    g2 = SmdGetObjPtr(0x32);
    t = 0.0f;
    g0->be_flag |= 0x20;
    g1->be_flag |= 0x20;
    g2->be_flag |= 0x20;
    W->seGear = SndCall(6, 0x56, 0, 0, 0, 0);
    d = (f32) dir;
    g0->pParts->ang.z += d * DEG(0.2f);
    SceSleep(1);
    g0->pParts->ang.z += d * DEG(0.4f);
    SceSleep(1);
    d *= DEG(0.6f);
    g0->pParts->ang.z += d;
    g1->pParts->ang.y += d;
    SceSleep(1);
    EstSet(0, -1, 0, 0, 1, 5, 1, (u8) W->effGear, 0, 0);
    while ((s32) pG->Room_flg[2] >= 0) {
        f32 a;

        t += acc;
        if (t > max) {
            t = max;
        }
        a = t * DEG(1.0f) * (f32) dir;
        g0->pParts->ang.z += a;
        g1->pParts->ang.y += -a * t0 / t1;
        g2->pParts->ang.z += -a * t0 / t1 * t2 / t0;
        SceSleep(1);
    }
    EffectEspDelete(0, (u8) W->effGear, 0, 0);
    EffectEspgenDelete(0, (u8) W->effGear, 0);
    EffectEfmDelete(0, (u8) W->effGear, 0);
    SceSleep(10);
    pG->Room_flg[2] &= 0x7FFFFFFF;
    W->gear = 0;
}

// The chain (smd 2 / 3) drops while the gate moves.
static void r11c_moveChain(int dir)
{
    u32 id = 2;
    cObj* c;
    const f32 max = 15.0f;
    const f32 acc = 1.0f;
    f32 spd;

    if (dir == 1) {
        id = 3;
    }
    SceSleep(15);
    c = SmdGetObjPtr(id);
    spd = 0.0f;
    c->be_flag |= 0x20;
    while ((s32) pGS->Room_flg[2] >= 0) {
        spd += acc;
        if (spd > max) {
            spd = max;
        }
        c->pos.y -= spd;
        SceSleep(1);
    }
    W->chain = 0;
}

// The lever (smd 0x35) swings back.
static void r11c_moveLever2(int dir)
{
    cObj* lv;
    int i;
    f32 spd;

    lv = SmdGetObjPtr(0x35);
    spd = (f32) dir * DEG(5.5f);
    for (i = 0; i < 10; i++) {
        lv->pParts->ang.z -= spd;
        SceSleep(1);
    }
    spd = (f32) dir * DEG(1.0f);
    for (i = 0; i < 3; i++) {
        lv->pParts->ang.z += spd;
        SceSleep(1);
    }
    lv->pParts->ang.z = 0.0f;
}

// The lever is pulled; unless `noGear`, the gear and chain tasks start.
extern "C" void r11c_moveLever(int dir, int noGear)
{
    cObj* lv;
    int i;
    f32 d;
    f32 d2;
    f32 spd;

    lv = SmdGetObjPtr(0x35);
    lv->be_flag |= 0x20;
    lv->pParts->ang.z = 0.0f;
    d = (f32) dir;
    spd = d * DEG(5.5f);
    SndCall(6, 0xA, 0, 0, 0, 0);
    d2 = d * DEG(1.0f);
    for (i = 0; i < 3; i++) {
        lv->pParts->ang.z += d2;
        SceSleep(1);
    }
    for (i = 0; i < 10; i++) {
        lv->pParts->ang.z += spd;
        SceSleep(1);
    }
    d2 = (f32) dir * DEG(1.0f);
    for (i = 0; i < 3; i++) {
        lv->pParts->ang.z -= d2;
        SceSleep(1);
    }
    if (noGear == 0) {
        W->gear = SceExec(0x12, (TaskFunc) r11c_moveGear, dir, 0, SCE_PRIO_DEF_2, 0);
        W->chain = SceExec(0x12, (TaskFunc) r11c_moveChain, dir, 0, SCE_PRIO_DEF_2, 0);
    }
}

// End (or cancel, flags_174 bit 28) of the route selection: stop the machinery, set the gates and the
// route flags.
static void r11c_selectRoute_end(int sel)
{
    cObj* g0 = SmdGetObjPtr(0x33);
    cObj* g1 = SmdGetObjPtr(0x34);
    cObj* lv = SmdGetObjPtr(0x35);

    if (pG->Room_flg[0] & 0x10000000) {
        if (lv) {
            lv->pParts->ang.z = 0.0f;
        }
        if (W->closeGate) {
            SceKill(W->closeGate);
        }
        if (W->gear) {
            SceKill(W->gear);
        }
        if (W->chain) {
            SceKill(W->chain);
        }
        if (W->seGate) {
            SndStop(W->seGate, 0);
        }
        if (W->seGear) {
            SndStop(W->seGear, 0);
        }
        EffectEspDelete(0, (u8) W->effGear, 0, 0);
        EffectEspgenDelete(0, (u8) W->effGear, 0);
        EffectEfmDelete(0, (u8) W->effGear, 0);
        EffectEspDelete(0, (u8) W->effGate, 0, 0);
        EffectEspgenDelete(0, (u8) W->effGate, 0);
        EffectEfmDelete(0, (u8) W->effGate, 0);
        pG->Room_flg[2] &= 0x7FFFFFFF;
    }
    W->seGear = 0;
    W->seGate = 0;
    if (sel < 0) {
        if (pG->Room_flg[0] & 0x10000000) {
            if (g0) {
                g0->pos.y = W->gateY[0] + 3600.0f;
            }
            if (g1) {
                g1->pos.y = W->gateY[1];
            }
        }
        r11c_save()->flags |= 0x40000000;
        r11c_save()->flags &= ~0x20000000;
        SceAtSetEnable(6, 0);
        SceAtSetEnable(5, 1);
        SceAtSetEnable(0xA, 0);
        SceAtSetEnable(0xB, 0);
    } else {
        if (pG->Room_flg[0] & 0x10000000) {
            if (g0) {
                g0->pos.y = W->gateY[0];
            }
            if (g1) {
                g1->pos.y = W->gateY[1] + 3600.0f;
            }
        }
        r11c_save()->flags |= 0x40000000;
        r11c_save()->flags |= 0x20000000;
        SceAtSetEnable(6, 1);
        SceAtSetEnable(5, 0);
        SceAtSetEnable(0xA, 0);
        SceAtSetEnable(0xB, 0);
    }
    CamCtrl.Comeback(0);
    SceEventEnd(0);
}

// Area 4: the lever. Message 0 selects the route; the gate opens (and the other closes).
static void r11c_selectRoute()
{
    W->closeGate = 0;
    W->gear = 0;
    W->chain = 0;
    W->seGate = 0;
    W->seGear = 0;
    pGS->Room_flg[2] &= 0x7FFFFFFF;
    SceEventStart(0);
    CamCtrl.CutCall(3);
    SceMesSet(0, 0x220, 1, 0x64, 0x150 - cMes.getWork()->lineSpace - cMes.getWork()->m_font_h - 1);
    switch (SceMesGetSelection()) {
    case 1:
        if ((r11c_save()->flags & 0x40000000) && !(r11c_save()->flags & 0x20000000)) {
            r11c_moveLever(-1, 1);
            SceExec(0x12, (TaskFunc) r11c_moveLever2, -1, 0, SCE_PRIO_DEF_2, 0);
        } else {
            SceSetEventCancel(1, (TaskFunc) r11c_selectRoute_end, -1, 3, 1);
            r11c_moveLever(-1, 0);
            CamCtrl.CutCall(4);
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            CamCtrl.CutCall(5);
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            CamCtrl.CutCall(6);
            r11c_openGate(0x33);
            if (r11c_save()->flags & 0x40000000) {
                W->closeGate = SceExec(0x12, (TaskFunc) r11c_closeGate, 0x34, 0, SCE_PRIO_DEF_2, 0);
            }
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            SceExec(0x12, (TaskFunc) r11c_moveLever2, -1, 0, SCE_PRIO_DEF_2, 0);
            SceSetEventCancel(0, 0, 0, -1, 1);
            r11c_selectRoute_end(-1);
            return;
        }
        break;
    case 2:
        if ((r11c_save()->flags & 0x40000000) && (r11c_save()->flags & 0x20000000)) {
            r11c_moveLever(1, 1);
            SceExec(0x12, (TaskFunc) r11c_moveLever2, 1, 0, SCE_PRIO_DEF_2, 0);
        } else {
            SceSetEventCancel(1, (TaskFunc) r11c_selectRoute_end, 1, 3, 1);
            r11c_moveLever(1, 0);
            CamCtrl.CutCall(4);
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            CamCtrl.CutCall(5);
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            CamCtrl.CutCall(7);
            r11c_openGate(0x34);
            if (r11c_save()->flags & 0x40000000) {
                W->closeGate = SceExec(0x12, (TaskFunc) r11c_closeGate, 0x33, 0, SCE_PRIO_DEF_2, 0);
            }
            while (CamCtrl.IsMotionEnd() == 0) {
                SceSleep(1);
            }
            SceExec(0x12, (TaskFunc) r11c_moveLever2, 1, 0, SCE_PRIO_DEF_2, 0);
            SceSetEventCancel(0, 0, 0, -1, 1);
            r11c_selectRoute_end(1);
            return;
        }
        break;
    case -1:
        break;
    }
    CamCtrl.Comeback(0);
    SceEventEnd(0);
}

// Area 0xC: the typewriter terminal.
static void r11c_operator()
{
    if (!(pG->Scenario_flg[0] & 0x00020000)) {
        pG->Scenario_flg[0] |= 0x00020000;
        SceAtSetEnable(0xC, 0);
        OpeSetOpenTerm(0xB, 71600.0f, -10.0f, -55420.0f, 1.6f);
    }
}

// The three bonfires (room archive 0x1F/0x20, motion 0x21).
extern "C" void setFire()
{
    {
        Vec pos = {112339.0f, -522.0f, -61101.0f};
        Vec rot = {0.0f, 0.0f, 0.0f};
        cObj* o;

        o = SetObjSmd(ROOM_ARC_PTR(pG->pRoom, 0x1F), ROOM_ARC_PTR(pG->pRoom, 0x20), &pos, &rot, 0x10, 1);
        W->fire[0] = o;
        if (o == 0) {
            pLog->err(0, 0, "setFire : set failed");
            return;
        }
        MotionSetCore(o, &o->Motion, ROOM_ARC_PTR(pG->pRoom, 0x21), 0, 0, 5, 0);
        EstSet((int) o, -1, 0, 0, 1, 0xD, 0, 2, 0, 0);
    }
    {
        Vec pos = {97770.0f, -598.0f, -49354.0f};
        Vec rot = {0.0f, DEG(-80.0f), 0.0f};
        cObj* o;

        o = SetObjSmd(ROOM_ARC_PTR(pG->pRoom, 0x1F), ROOM_ARC_PTR(pG->pRoom, 0x20), &pos, &rot, 0x10, 1);
        W->fire[1] = o;
        if (o == 0) {
            pLog->err(0, 0, "setFire : set failed");
            return;
        }
        MotionSetCore(o, &o->Motion, ROOM_ARC_PTR(pG->pRoom, 0x21), 0, 0, 5, 0);
        EstSet((int) o, -1, 0, 0, 1, 0xD, 0, 2, 0, 0);
    }
    {
        Vec pos = {122765.0f, -516.0f, -51246.0f};
        Vec rot = {0.0f, DEG(-80.0f), 0.0f};
        cObj* o;

        o = SetObjSmd(ROOM_ARC_PTR(pG->pRoom, 0x1F), ROOM_ARC_PTR(pG->pRoom, 0x20), &pos, &rot, 0x10, 1);
        W->fire[2] = o;
        if (o == 0) {
            pLog->err(0, 0, "setFire : set failed");
            return;
        }
        MotionSetCore(o, &o->Motion, ROOM_ARC_PTR(pG->pRoom, 0x21), 0, 0, 5, 0);
        EstSet((int) o, -1, 0, 0, 1, 0xD, 0, 2, 0, 0);
    }
}

// Destroy the three bonfire objects (the s20 event replaces them).
extern "C" void deleteFire()
{
    ObjMgr.destroy(W->fire[0]);
    ObjMgr.destroy(W->fire[1]);
    ObjMgr.destroy(W->fire[2]);
}

// Event r11cs00 handler: the cabin etc models, the scroll object 0x3F handed to the event.
extern "C" void Evt_R11CS00_Func(Event* e)
{
    Vec pos = {0.0f, 0.0f, 0.0f};
    Vec ang = {0.0f, 0.0f, 0.0f};
    void* mod;
    cObj* o;

    switch (e->funcMode) {
    case 0:
        setRoomEtcDisp(0x16, 0, 1);
        setRoomEtcDisp(0xF, 0, 1);
        setRoomEtcDisp(0xA, 0, 1);
        break;
    case 1:
        switch (e->NowCut) {
        case 0: {
            int frame = e->NowFrame;

            if (frame == 0) {
                EffectEspDelete(0x2001, 3, 0, 0);
                EffectEspgenDelete(0x2001, 3, 0);
                EffectEfmDelete(0x2001, 3, 0);
                EstSet(0, -1, 0, 0, 1, 0xD, 0x2001, 3, frame, (void*) frame);
                o = SmdGetObjPtr(0x3F);
                if (o) {
                    e->SetMod("scr0000", o, 5, 0, 2, 0);
                    o->be_flag |= 0x12;
                    o->setPos(&pos);
                    o->setAng(&ang);
                    o->be_flag |= 0x20;
                    e->EspSetModelPtr(o);
                }
                if (e->GetMod(&mod, "et1700", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cModel*) mod)->be_flag |= 2;
                }
            }
            break;
        }
        case 0x13:
            setRoomEtcDisp(0, 0, 1);
            break;
        case 0x14:
            setRoomEtcDisp(0, 1, 1);
            break;
        }
        break;
    case 2: {
        SmdWork* w;

        SmdSetTrans(0x3F, 1);
        w = SmdGetWorkPtr(0x3F);
        o = SmdGetObjPtr(0x3F);
        if (o && w) {
            o->setPos(&w->pos);
            o->setAng(&w->rot);
        }
        setRoomEtcDisp(0, 1, 1);
        setRoomEtcDisp(0x16, 1, 1);
        setRoomEtcDisp(0xF, 1, 1);
        setRoomEtcDisp(0xA, 1, 1);
        break;
    }
    }
}

// Event r11cs10 handler: the ladders and the door.
extern "C" void Evt_R11CS10_Func(Event* e)
{
    switch (e->funcMode) {
    case 0: {
        cObj* o;

        LadderEventTrans(0);
        setRoomEtcDisp(0xA, 0, 1);
        o = SmdGetObjPtr(0x3F);
        if (o) {
            o->be_flag &= ~2;
        }
        break;
    }
    case 1:
        switch (e->NowCut) {
        case 0:
            break;
        case 8:
            setRoomEtcDisp(0, 0, 1);
            break;
        }
        break;
    case 2:
        setRoomEtcDisp(0xA, 1, 1);
        setRoomEtcDisp(0, 1, 1);
        LadderEventTrans(1);
        break;
    }
}

// Per-cut effect of the s20 event on the render texture.
static inline void r11c_evtEsp(Event* e, int no)
{
    if (e->NowFrame == 0) {
        EffectEspDelete(W->tex->mask | 0x3001, 0, 0, 0);
        EffectEspgenDelete(W->tex->mask | 0x3001, 0, 0);
        EffectEfmDelete(W->tex->mask | 0x3001, 0, 0);
        EstSet(0, -1, 0, 0, 1, no, W->tex->mask | 0x3001, 0, 0, 0);
    }
}

// Event r11cs20 handler: the door, the render texture on the two players, the water effects.
extern "C" void Evt_R11CS20_Func(Event* e)
{
    // Function scope: the address-taken `door` of a case block is kept until the switch ends, so
    // a second block-local `door` would get its own slot.
    cEm* door;

    switch (e->funcMode) {
    case 0:
        if (getRoomEtcDoor(0xA, &door, 1)) {
            door->setNoSuspend(1);
        }
        setRoomEtcDisp(0xA, 1, 1);
        break;
    case 1:
        switch (e->NowCut) {
        case 0:
            if (e->NowFrame == 0) {
                void* mod;

                if (e->GetMod(&mod, "pl0000", 0, 0) == 1) {
                    TexRenderModSet((cModel*) mod, 6, W->texTbl, W->tex, 0, 1, 1, 1, 1.0f);
                }
                if (e->GetMod(&mod, "pl0400", 0, 0) == 1) {
                    TexRenderModSet((cModel*) mod, 3, W->texTbl, W->tex, 0, 1, 1, 1, 1.0f);
                }
            }
            r11c_evtEsp(e, 0xE);
            break;
        case 1:
            r11c_evtEsp(e, 0xF);
            break;
        case 2:
            r11c_evtEsp(e, 0x10);
            break;
        case 3:
            r11c_evtEsp(e, 0x11);
            break;
        case 4:
            r11c_evtEsp(e, 0x12);
            break;
        case 5:
            r11c_evtEsp(e, 0x13);
            break;
        case 6:
            r11c_evtEsp(e, 0x14);
            break;
        }
        break;
    case 2:
        if (getRoomEtcDoor(0xA, &door, 1)) {
            door->setNoSuspend(0);
        }
        setRoomEtcDisp(0xA, 1, 1);
        break;
    }
}
