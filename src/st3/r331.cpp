#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "atari.h"
#include "light.h"
#include "map_obj.h"
#include "widget.h"
#include "flag_rsf.h"
#include "event.h"
#include "global.h"
#include "sce.h"
#include "sce_sys.h"
#include "sce_at.h"
#include "scroll.h"
#include "obj.h"
#include "em.h"
#include "player.h"
#include "pl_sub.h"
#include "snd.h"
#include "fade.h"
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_ROUTE_MOVIES && RE4DC_ROUTE_CH3
// Route cutscenes (ROUTE_CH3, st3 lane 2026-10-15): s00 / s10 (the mine cart) presented by the PS2 movies
// (dc/movie/r331<event>.seq) when the disc carries them, as r316s00: the GC evds are not on the disc-2 image
// (EvtRead: DC.setData failed, then "mem over", and the event never ran). With a movie no evd is read; the
// handler's begin / end modes run and the code after the event is unchanged. Without it the source path applies.
#include "route_movie.h"
#define R331_ROUTE_MOVIES 1
#else
#define R331_ROUTE_MOVIES 0
#endif

// Room 3-31 (D:/Bio4/Prog/r331.cpp): the s00 event (into the mine cart) and the s10 event (the count-down
// start) with their room jumps.

struct R331Work {
    int timer;   // 0x0  count-down frames when the s10 event started
};

static R331Work* r331_work;

// st3.cpp's count-down helpers
void st3_setCountDownTimer(int frame);
int st3_getCountDownTimer();
void st3_startCountDown();
void st3_checkCountDown();

static void R331ExecEventS00();
static void R331ExecEventS10();
extern "C" void Evt_R331S00_Func(Event* e);
extern "C" void Evt_R331S10_Func(Event* e);

// 1 while the event is being skipped (EVT status bit 30).
static inline int r331_evtSkip(Event* e)
{
    int skip = 1;

    if ((e->StatusFlag & 0x40000000) == 0) {
        skip = 0;
    }
    return skip;
}

// Room init: the s00 / s10 callbacks; until Room_flg bit 0 area 3 = the s00 event (pre-loaded). With
// Scenario_flg[0] 0x200 (the count-down phase): BGM table 0x331 set 2 and the s10 event task, the
// count-down resumed; else BGM table 3 enabled.
void R331Init()
{
#line 58 "D:/Bio4/Prog/r331.cpp"
    r331_work = (R331Work*) MEM_CALLOC(sizeof(R331Work), 1, 0xd);
    EvtMgr.SetFunc("evt_r331s00_func", (void*) Evt_R331S00_Func);
    EvtMgr.SetFunc("evt_r331s10_func", (void*) Evt_R331S10_Func);
    if (RsfCheck(G_ROOM_ID, 0) == 0) {
        SceAtDataSet_exec(3, 0x12, 0, (TaskFunc) R331ExecEventS00, 0, 1);
#if R331_ROUTE_MOVIES
        if (!re4dc_movie_available(0x33100))
#endif
        EvtMgr.EvtReadAram("event/evd/r331s00.evd", 0, 0, 0, 0);
    }
    if (pG->Scenario_flg[0] & 0x200) {
        SndBgmTblSetDisable(3, 0);
        SndBgmTblSet(0x331, 2);
        SceExec(0x12, (TaskFunc) R331ExecEventS10, 0, 2, 2, 0);
        st3_startCountDown();
    } else {
        SndBgmTblSetEnable(3, 0);
    }
}

// Per frame: the island count-down check (time over -> the death demo).
void R331Main()
{
    st3_checkCountDown();
}

// Area 3 once (Room_flg bit 0): event r331s00 (Leon and Ashley board the mine cart): Ashley marked as
// separated (Status_flg[3] bit 31, following off), then a room jump to r332 at the cart start.
static void R331ExecEventS00()
{
    if (RsfCheck(G_ROOM_ID, 0) == 0) {
        RsfSet(G_ROOM_ID, 0);
        SceAtSetEnable(3, 0);
        SceEventStart(0);
#if R331_ROUTE_MOVIES
        if (re4dc_movie_available(0x33100)) {
            RouteMoviePlay(0x33100, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R331S00_Func, 0);
        } else
#endif
        EvtMgr.EvtReadExec("event/evd/r331s00.evd", 0, 0);
        SceEventEnd(0);
        pG->Status_flg[3] |= 0x80000000;
        SubCharCtrl(2, 0);
        BitOff(pG->Status_flg[3], 0x04000000);
        pG->System_flg |= 0x400;
        {
            Vec pos = {-42000.0f, 15800.0f, 46900.0f};
            Vec rot = {0.0f, 0.0f, 0.0f};

            SceAtExecRoomJump(0x332, &pos, &rot, 0);
        }
    }
}

// Once (Room_flg bit 1) in the count-down phase: event r331s10, Ashley following again, BGM table
// 0x331 set 1 with both BGMs started, then a room jump to r333.
static void R331ExecEventS10()
{
    if (RsfCheck(G_ROOM_ID, 1) == 0) {
        RsfSet(G_ROOM_ID, 1);
        pG->System_flg |= 0x400;
        SceSleep(1);
        SceEventStart(0);
#if R331_ROUTE_MOVIES
        if (re4dc_movie_available(0x33110)) {
            RouteMoviePlay(0x33110, ROUTE_MOVIE_SND_EVENT, (RouteEvtFunc) Evt_R331S10_Func, 0);
        } else
#endif
        EvtMgr.EvtReadExec("event/evd/r331s10.evd", 0, 0);
        SceEventEnd(0);
        pG->Status_flg[3] |= 0x04000000;
        SndBgmTblSet(0x331, 1);
        SndRoomBgmStart(0, 0);
        SndRoomBgmStart(1, 0);
        pG->System_flg |= 0x400;
        {
            Vec pos = {-646166.0f, -12718.0f, -588290.0f};
            Vec rot = {0.0f, -1.78f, 0.0f};

            SceAtExecRoomJump(0x333, &pos, &rot, 0);
        }
    }
}

// Event r331s00 callback: cut 0 hands scroll object 0x24 (scr0000) to the event; cut 4 fades out unless
// the event is skipped; the end restores the object.
extern "C" void Evt_R331S00_Func(Event* e)
{
    Vec pos = {0.0f, 0.0f, 0.0f};
    Vec rot = {0.0f, 0.0f, 0.0f};
    cObj* obj;
    SmdWork* w;

    switch (e->funcMode) {
    case 0:
        break;
    case 1:
        switch (e->NowCut) {
        case 0:
            if (e->NowFrame == 0) {
                if ((obj = SmdGetObjPtr(0x24)) != 0) {
                    e->SetMod("scr0000", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
            }
            break;
        case 4:
            if (e->NowFrame == e->MaxFrame - 40) {
                int skip = r331_evtSkip(e);

                if (skip == 0) {
                    FadeSetW(2, 40, 0, 0);
                }
            }
            break;
        }
        break;
    case 2:
        w = SmdGetWorkPtr(0x24);
        if ((obj = SmdGetObjPtr(0x24)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        pG->System_flg |= 0x400;
        break;
    }
}

// Event r331s10 callback: remembers the count-down at the start; cut 0 hands scroll object 0x24 to the
// event with a fade-in, cut 2 fades out; the end restores the object and restarts the count-down with
// the event's length subtracted.
extern "C" void Evt_R331S10_Func(Event* e)
{
    Vec pos = {0.0f, 0.0f, 0.0f};
    Vec rot = {0.0f, 0.0f, 0.0f};
    cObj* obj;
    SmdWork* w;

    switch (e->funcMode) {
    case 0:
        r331_work->timer = st3_getCountDownTimer();
        break;
    case 1:
        switch (e->NowCut) {
        case 0:
            if (e->NowFrame == 0) {
                int skip;

                if ((obj = SmdGetObjPtr(0x24)) != 0) {
                    e->SetMod("scr0000", obj, 5, 0, 2, 0);
                    obj->setPos(&pos);
                    obj->setAng(&rot);
                    obj->be_flag |= 0x20;
                    e->EspSetModelPtr(obj);
                }
                skip = r331_evtSkip(e);
                if (skip == 0) {
                    FadeSetW(0x80000002, 40, 0, 0);
                }
            }
            break;
        case 2:
            if (e->NowFrame == e->MaxFrame - 40) {
                int skip = r331_evtSkip(e);

                if (skip == 0) {
                    FadeSetW(2, 40, 0, 0);
                }
            }
            break;
        }
        break;
    case 2:
        w = SmdGetWorkPtr(0x24);
        if ((obj = SmdGetObjPtr(0x24)) != 0 && w != 0) {
            obj->setPos(&w->pos);
            obj->setAng(&w->rot);
        }
        st3_setCountDownTimer(r331_work->timer - e->MaxTotalFrame);
        st3_startCountDown();
        pG->System_flg |= 0x400;
        break;
    }
}
