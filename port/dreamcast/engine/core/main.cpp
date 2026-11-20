// E1 engine main loop (lane eng-e1): boots straight into the village (r101) and runs Leon's original player and camera
// code on the engine, one logic tick a picture (SHELL_MAP section 2, "what an engine-owned loop must call").
//
// Tick: 1 input latched into Joy[] / Key (hosted PadRead over the engine's pad script), 2 Frame_cnt++,
// 3 the game task's hosted subset in gameMainLoop order (player move, object move, camera move) with the services it
// calls synchronously, 8 engine draw from the engine tables, 9 pacer.
#include "global.h"
#include "player.h"
#include "obj.h"
#include "em.h"
#include "model.h"
#include "cam_ctrl.h"
#include "camera.h"
#include "main.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#ifdef E2_BOSS
#include "boss_e2.h"   // eng-boss: the El Gigante slice
#endif
#include <stdio.h>
#include <string.h>


extern "C" void PlayerInit();
extern "C" void PadRead();
void CameraMove();
void CameraRoomInit();
void* GetDataExt(void* arc, const char* tag, int no);
void ReadPlayerData(int type, int costume);

volatile uint32_t e1_tick;
extern "C" void e1_stamp_c(unsigned k);
void e1_stamp(unsigned k) { e1_stamp_c(k); }
volatile uint32_t e1_state[8];   // 0 stage, 1 tick, 2 ticks total, 3 done
E1Timing e1_timing[E1_TICKS];

static uint64_t now_us() { return timer_us_gettime64(); }

// Room set-up: the subset of gameRoomInit (game.cpp:509) the hosted player and camera need, in its order.
static void room_init()
{
    const E1Route& r = e1_route();
    e1_room_globals(r);                 // pG room id, flags, PlayerInit (hosted)
#ifdef E2_BOSS
    e2_room_globals();
#endif
    PlayerInit();
    MemCreateHeap(4, MemGetHeapStartAddr(0) + 0x1000, MemGetHeapEndAddr(0));
    MemSetCurrentHeap(4);
    e1_load_room(r.room);               // room archive sections and the core camera data (engine room pack)
    pG->Rtp = GetDataExt(pG->pRoom, "RTP", 0);   // read.cpp ReadAreaData: the room's route points (the partner's follow)
    ReadPlayerData(pG->pl_type, pG->pl_costume);
#ifdef E2_BOSS
    e2_managers_room_init();
#else
    e1_managers_room_init();            // ModInfoMgr, PartsMgr, EmMgr, ObjMgr arrays on the room heap
#endif
    e1_collision_room_init();           // SatMgr / EatMgr over the room's SAT / EAT
    pG->sub_pos.x = r.pos[0];
    pG->sub_pos.y = r.pos[1];
    pG->sub_pos.z = r.pos[2];
    pG->sub_angle = r.ang;
    EmMgr.create(0, 0);                 // the player: cPlLeon on the actor table (hosted constructor + startUp)
    CameraRoomInit();
    void* cam = GetDataExt(pG->pRoom, "CAM", 0);
    if (cam) CamCtrl.RoomDataRead((CameraDataHeader*) cam);
    else pG->pCamRoom = cam;
    CamCtrl.CoreDataRead((CameraDataHeader*) (pG->pArc->ofs_30 + (u32) pG->pArc));
    CamCtrl.roomInit();
    e1_view_room_init();
#ifdef E2_BOSS
    e2_room_init();                     // enemy list, the boss module, the room script (R119Init)
#endif
    pG->Rno0 = 3;
    pG->Rno1 = 0;
    e1_partner_room_init();             // the hill scene: Leon resumed, Ashley created (core/partner.cpp)
}

// gameMainLoop, the hosted subset in its order (game.cpp:798).
static void game_tick(E1Timing& tm)
{
    BitOff(pG->Status_flg[2], 0x10000000);
    pG->quake_ofs.x = 0.0f;
    pG->quake_ofs.y = 0.0f;
    pG->quake_ofs.z = 0.0f;
    // gameMainLoop's slow-motion rule (Status_flg[3] bit 27): the player's motion speed, 1.0 on the first tick
    static int preb_slow_flg = 1;
    if (pG->Status_flg[3] & 0x8000000) {
        pPL->setSlow(0.6f);
        preb_slow_flg = 1;
    } else {
        if (preb_slow_flg == 1) pPL->setSlow(1.0f);
        preb_slow_flg = 0;
    }
    e1_svc_begin();
    tm.chars_us = 0;
#ifdef E2_BOSS
    {   // gameMainLoop order: ScenarioMove (room main + scenario tasks), then EmMgr.move, then the player
        uint64_t t = now_us();
        e2_scenario_move(e1_tick);
        e2_em_move();
        tm.obj_us = now_us() - t;   // reported as the enemy share below
    }
#else
    if (e1_scene == E1_SCENE_HILL) e1_partner_chars_move(tm);   // EmMgr.move: the partner (gameMainLoop order)
#endif
    e1_stamp(1);
    e1_rng_owner(1);
    if (!(pG->Stop_flg & 0x10000000) && (pPL->be_flag & 0x20) &&
        (!(pG->Status_flg[1] & 0x10000000) || (pPL->be_flag & 0x800))) {
        uint64_t t = now_us();
        pPL->move();
        tm.player_us = now_us() - t;
    }
    BitOff(pG->Status_flg[2], 0x8000000);
    e1_stamp(2);
    e1_rng_owner(3);
    uint64_t t1 = now_us();
    if (!(pG->Stop_flg & 0x4000000)) ObjMgr.move();
    uint64_t t2 = now_us();
    e1_rng_owner(2);
    CameraMove();
    e1_rng_owner(0);
#ifdef E2_BOSS
    e2_fx_move();                       // effect service, then DmgMgr / collision die checks
    e2_after_tick();
    tm.obj_us += t2 - t1;
#else
    tm.obj_us = t2 - t1;
#endif
    tm.cam_us = now_us() - t2;
    e1_svc_publish();                   // the palette (world x bind) for drawing, once a tick after the behaviour
    tm.services_us = e1_svc_end();
    for (unsigned g = 0; g < E1_SVC_GROUPS; g++) tm.svc_group_us[g] = e1_svc_group(g);
}

int main()
{
    e1_log("E1 engine: boot\n");
    e1_memmap_boot();
    e1_state[0] = 1;
    e1_arena_init();
    e1_globals_init();
    e1_partner_boot();                  // scene and comparison boot options (HILL, FEED, CTRLFOL)
    // The hill scene holds 0.84 MB more room data (the partner's archive and motion keys): the renderer's pack goes
    // first, while the KOS heap is empty, so its whole-file staging read (7.8 MB; the textures then go to video
    // memory) fits before the room data is loaded.
    const bool pack_first = e1_scene == E1_SCENE_HILL;
    if (pack_first) e1_draw_open();
    e1_state[0] = 2;
    room_init();
    e1_state[0] = 3;
    e1_log("E1 engine: room %03x ready, player %p pos %d %d %d\n", (unsigned) pG->room_id, (void*) pPL,
           (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z);
    if (!pack_first) e1_draw_open();
    e1_memmap_sample();
    e1_state[0] = 4;
    const unsigned ticks = e1_route().ticks;
    e1_state[2] = ticks;
    e1_trace_tick(0);
    for (e1_tick = 1; e1_tick <= ticks; e1_tick++) {
        e1_state[1] = e1_tick;
        E1Timing& tm = e1_timing[(e1_tick - 1) % E1_TICKS];
        uint64_t a = now_us();
        e1_stamp_pic = e1_tick - 1;
        e1_stamp(6);
        e1_input_latch(e1_tick);
        e1_partner_tick_begin(e1_tick);
        PadRead();
        pG->Frame_cnt++;
        e1_stamp(0);
        uint64_t b = now_us();
        game_tick(tm);
        e1_partner_tick_end(e1_tick);
        e1_stamp(3);
        uint64_t c = now_us();
        e1_trace_tick(e1_tick);
        e1_stamp(4);
        uint64_t d = now_us();
        e1_draw_picture(tm);
        uint64_t e = now_us();
        tm.input_us = b - a;
        tm.tick_us = c - b;
        tm.trace_us = d - c;
        tm.draw_us = e - d;
        e1_pace_end(tm);
        tm.frame_us = now_us() - a;
    }
    e1_state[0] = 5;
    e1_report();
#ifdef E2_BOSS
    e2_report();
#endif
    e1_state[3] = 1;
    for (;;) thd_sleep(1000);
}
