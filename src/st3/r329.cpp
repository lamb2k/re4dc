#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "atari.h"
#include "event.h"
#include "flag_rsf.h"
#include "global.h"
#include "sce.h"
#include "sce_sys.h"
#include "scroll.h"
#include "obj.h"
#include "em.h"
#include "em_set.h"
#include "read.h"
#include "player.h"
#include "pl_npc.h"
#include "pl_sub.h"
#include "esp.h"
#include "snd.h"
#include "fade.h"

// Room 3-29 (D:/Bio4/Prog/r329.cpp): the s00 event (Leon and Ashley reunited) and the room state it
// leaves behind.

struct R329Work {
    u8 dummy;
};

static R329Work* r329_work;

void Obj18CmfOn(cObj* obj, u32 no);
// The list id is masked to a byte at the EmReadSearch call: the room build's prototype returned int (r40e's
// build already had the u8 return that drops the mask).
int GetEmIdFromListI(u32 no) asm("GetEmIdFromList");

// The s00 player position is written through the Vec pointer (the target's `mr r4, r9` + `4(r9)`/`8(r9)`
// stores with the x store folded back onto r1).
static inline void setVec(Vec* v, f32 x, f32 y, f32 z)
{
    v->x = x;
    v->y = y;
    v->z = z;
}

#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ROUTE_MOVIES && RE4DC_ROUTE_CH3
// Route cutscene (ROUTE_CH3, st3 lane 2026-10-15): r329s00 is presented by its PS2 movie (dc/movie/r329s00.seq) when
// the disc carries it, as r300s00: the GC evd is not on the disc-2 image (EvtRead: DC.setData failed, then "mem over",
// and the event never ran). With the movie no evd is read; the handler's begin / end modes run and the code after
// the event is unchanged. Without the movie the source event path applies.
#include "route_movie.h"
#define R329_ROUTE_MOVIES 1
#else
#define R329_ROUTE_MOVIES 0
#endif
static void R329EventS00();
extern "C" void Evt_R329S00_Func(Event* e);

// Room init: the s00 (and s99) callback. Before the reunion (Room_flg bit 0): r329s00 pre-loaded with
// the enemy of ESL 0x95, Ashley marked as following, the event task (unless debug trigger 1), the
// pre-event scroll objects (0x30/0x31 shown, 0x2E/0x2F hidden) and the attribute sounds off; after it
// the post-event objects.
void R329Init()
{
#line 41 "D:/Bio4/Prog/r329.cpp"
    r329_work = (R329Work*) MEM_CALLOC(sizeof(R329Work), 1, 0xd);
    EvtMgr.SetFunc("evt_r329s00_func", (void*) Evt_R329S00_Func);
    EvtMgr.SetFunc("evt_r329s99_func", (void*) Evt_R329S00_Func);
    if (RsfCheck(G_ROOM_ID, 0) == 0) {
#if R329_ROUTE_MOVIES
        if (!re4dc_movie_available(0x32900))
#endif
        EvtMgr.EvtReadAram("event/evd/r329s00.evd", 3, 0, 0, 0);
        pG->Status_flg[3] |= 0x04000000;
        if (DebugTrg(1) == 0) {
            SceExec(0x12, (TaskFunc) R329EventS00, 0, 0, 2, 0);
        }
        EmReadSearch((u8) GetEmIdFromListI(0x95), 0, 0);
        SmdSetTrans(0x30, 1);
        SmdSetTrans(0x31, 1);
        SmdSetTrans(0x2E, 0);
        SmdSetTrans(0x2F, 0);
        SeAtSetOnOff(0, 0);
        SeAtSetOnOff(1, 0);
    } else {
        SmdSetTrans(0x30, 0);
        SmdSetTrans(0x31, 0);
        SmdSetTrans(0x2E, 1);
        SmdSetTrans(0x2F, 1);
        SmdSetTrans(0x2B, 0);
        EstSet(0, -1, 0, 0, 1, 3, 1, 0, 0, 0);
        EstSet(0, -1, 0, 0, 1, 4, 1, 0, 0, 0);
    }
}

// Per-frame room main: nothing.
void R329Main()
{
}

// Once (Room_flg bit 0): two door_unlock[1] bits cleared, event r329s00 (Leon and Ashley reunited),
// a fade-in, Leon placed at the fixed spot, Ashley initialised beside him in chase mode, Scenario_flg[1]
// 0x40000000, the post-event objects.
static void R329EventS00()
{
    if (RsfCheck(G_ROOM_ID, 0) == 0) {
        RsfSet(G_ROOM_ID, 0);
        BitOff(pG->door_unlock[1], 0x04000000);
        BitOff(pG->door_unlock[1], 0x00040000);
        SceEventStart(0);
        pG->System_flg |= 0x400;
        SceSleep(1);
#if R329_ROUTE_MOVIES
        if (re4dc_movie_available(0x32900)) {
            RouteMoviePlay(0x32900, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R329S00_Func, 0);
        } else
#endif
        EvtMgr.EvtReadExec("event/evd/r329s00.evd", 3, 0);
        FadeSetW(0x80000002, 30, 0, 0);
        {
            // COMPILER-DIFF: #17 (local-alloc qty order). The three pool constants are block-local
            // qtys with refs 3; sched1 issues their loads 2 insns apart (x, y, z) and the second
            // setPos stores them 1 insn apart, so ours ranks y (len 76) above x (len 78) and hands
            // out f29/f28/f27 to z/y/x. The target has x above y (z f29, x f28, y f27); no
            // statement order reproduces that tie, so x is pinned.
            register f32 px PPC_REG("fr28");
            Vec pos;

            px = -1890.0f;
            setVec(&pos, px, -922.0f, -662.0f);
            pPL->setPos(&pos);
        }
        {
            Vec ang;

            ang.x = 0.0f;
            ang.y = -1.5f;
            ang.z = 0.0f;
            pPL->setAng(&ang);
        }
        BitOn(pG->Scenario_flg[1], 0x40000000);
        BitOn(pG->Status_flg[3], 0x04000000);
        SubCharInit(1, &pPL->pos, pPL->ang.y);
        SubCharCtrl(1, 0);
        {
            Vec pos;

            pos.x = -1890.0f;
            pos.y = -922.0f;
            pos.z = -662.0f;
            pSUB->setPos(&pos);
        }
        {
            Vec ang;

            ang.x = 0.0f;
            ang.y = -1.5f;
            ang.z = 0.0f;
            pSUB->setAng(&ang);
        }
        SndBgmTblSet(0x329, 1);
        SndRoomBgmStart(0, 0);
        SndRoomBgmStart(1, 0);
        SeAtSetOnOff(0, 1);
        SeAtSetOnOff(1, 1);
        SceEventEnd(0);
    }
}

// Event r329s00 callback: Status_flg[1] 0x800 and the pre-event object set at start; per cut the Leon
// model's flags, the et1200 / et1210 etc models (CMF on) and hand-offs of scroll objects; the end
// restores the room.
extern "C" void Evt_R329S00_Func(Event* e)
{
    Vec pos = {0.0f, 0.0f, 0.0f};
    Vec rot = {0.0f, 0.0f, 0.0f};
    cObj* obj;
    SmdWork* w;

    switch (e->funcMode) {
    case 0:
        pG->Status_flg[1] |= 0x800;
        SmdSetTrans(0x30, 1);
        SmdSetTrans(0x31, 1);
        SmdSetTrans(0x2E, 0);
        SmdSetTrans(0x2F, 0);
        SmdSetTrans(0x33, 0);
        SmdSetTrans(0x32, 0);
        break;
    case 1:
        if (e->NowCut == 0) {
            if (e->NowFrame == 0) {
                void* mod;

                if (e->GetMod(&mod, "pl0000", 0, 0) == 1) {
                    ((cModel*) mod)->be_flag &= ~0x01000000;
                }
                if ((obj = SmdGetObjPtr(0x29)) != 0) {
                    e->SetMod("scr0000", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
                if ((obj = SmdGetObjPtr(0x2A)) != 0) {
                    e->SetMod("scr0100", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
                if ((obj = SmdGetObjPtr(0x2B)) != 0) {
                    e->SetMod("scr0200", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
                if ((obj = SmdGetObjPtr(0x2C)) != 0) {
                    e->SetMod("scr0300", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
                if (e->GetMod(&mod, "et1200", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1210", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1220", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1230", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1240", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1250", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
                if (e->GetMod(&mod, "et1260", 0, 0) == 1) {
                    Obj18CmfOn((cObj*) mod, 5);
                    ((cObj*) mod)->be_flag |= 2;
                }
            }
        }
        if (e->NowCut == 0) {
            if (e->NowFrame == 0) {
                void* mod;

                if (e->GetMod(&mod, "pl0100", 0, 0) == 1) {
                    ((cObj*) mod)->o18.be_flag |= 0x40;
                }
            }
        } else {
            if (e->NowFrame == 0) {
                void* mod;

                if (e->GetMod(&mod, "pl0100", 0, 0) == 1) {
                    ((cObj*) mod)->o18.be_flag &= ~0x40;
                }
            }
        }
        {
            void* mod;

            if (e->NowCut <= 0x14) {
                if (e->NowFrame == 0) {
                    if (e->GetMod(&mod, "pl0200", 0, 0) == 1) {
                        ((cObj*) mod)->o18.be_flag |= 0x40;
                    }
                }
            } else {
                if (e->NowFrame == 0) {
                    if (e->GetMod(&mod, "pl0200", 0, 0) == 1) {
                        ((cObj*) mod)->o18.be_flag &= ~0x40;
                    }
                }
            }
            if (e->NowCut == 0x1A) {
                if (e->NowFrame == 0) {
                    if (e->GetMod(&mod, "em3000a", 0, 0) == 1) {
                        ((cObj*) mod)->o18.be_flag |= 0x40;
                    }
                }
            } else {
                if (e->NowFrame == 0) {
                    if (e->GetMod(&mod, "em3000a", 0, 0) == 1) {
                        ((cObj*) mod)->o18.be_flag &= ~0x40;
                    }
                }
            }
        }
        break;
    case 2:
        pG->Status_flg[1] &= ~0x800;
        w = SmdGetWorkPtr(0x29);
        if ((obj = SmdGetObjPtr(0x29)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        w = SmdGetWorkPtr(0x2A);
        if ((obj = SmdGetObjPtr(0x2A)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        w = SmdGetWorkPtr(0x2B);
        if ((obj = SmdGetObjPtr(0x2B)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        w = SmdGetWorkPtr(0x2C);
        if ((obj = SmdGetObjPtr(0x2C)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        SmdSetTrans(0x30, 0);
        SmdSetTrans(0x31, 0);
        SmdSetTrans(0x2E, 1);
        SmdSetTrans(0x2F, 1);
        SmdSetTrans(0x2B, 0);
        SmdSetTrans(0x33, 1);
        SmdSetTrans(0x32, 1);
        EstSet(0, -1, 0, 0, 1, 3, 1, 0, 0, 0);
        EstSet(0, -1, 0, 0, 1, 4, 1, 0, 0, 0);
        break;
    }
}
