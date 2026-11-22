// E1 engine main loop (lane eng-e1): boots straight into the village (r101) and runs Leon's original player and camera
// code on the engine, one logic tick a picture (SHELL_MAP section 2, "what an engine-owned loop must call").
//
// Tick: 1 input latched into Joy[] / Key (hosted PadRead over the engine's pad script), 2 Frame_cnt++,
// 3 the game task's hosted subset in gameMainLoop order (player move, object move, camera move) with the services it
// calls synchronously, 8 engine draw from the engine tables, 9 pacer.
#include "global.h"
#include "e1_clock.h"   // lane eng-clock1: the engine's clock (TMU2 counts at the reload's rate)
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
#include "camera/eng_camera.h"   // lane eng-e1l: the camera record's finite check
#include "camera/camera_svc.h"   // lane eng-e1p: the room's camera tracks converted at load
#include "room_change.h"         // lane eng-load1: room-to-room loading through a door
#include "rnd.h"
unsigned e1_door_seed();
void e1_load_step(const char* what);   // core/room_change.cpp (lane eng-load1)
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

static uint64_t now_us() { return e1_clock_us(); }

// Room set-up: the subset of gameRoomInit (game.cpp:509) the hosted player and camera need, in its order. Lane eng-load1:
// the first room (first: the game's start, PlayerInit) and every room a door leads to (core/room_change.cpp: the room,
// the player's start and angle from the door's request; the room heap made again, so the last room's records go).
void RndInit(u16 seed);
static void room_init(unsigned room, const float* pos, float ang, int first)
{
    if (first) {
        const E1Route& r = e1_route();
        // lane eng-snd1 (R9): the behaviour generator starts from the scene's seed (the fixture's), first, as re4ref seeds
        // before PlayerInit; the SEED boot option (core/globals.cpp, the game-seed control) puts 0x5A5A in its place.
        // Control SEED0 (boot file): the seed left at 0, as before R9; the village's request check must fail on its footsteps.
        if (r.seed >= 0) {
            file_t f0 = fs_open("/cd/SEED0", O_RDONLY);
            const int seed0 = f0 >= 0;
            if (seed0) { fs_close(f0); e1_log("E1 CONTROL SEED0: the behaviour generator left at 0\n"); }
            if (!seed0) RndInit(e1_game_seed_option ? 0x5A5A : (u16) r.seed);
        }
        e1_room_globals(r);             // pG room id, flags, PlayerInit (hosted)
#ifdef E2_BOSS
        e2_room_globals();
#endif
        PlayerInit();
    } else {
        pG->room_id = (u16) room;
    }
    e1_room_heap_create(4);             // the room heap above heap 0, not over it (host/e1_heap.cpp; lane eng-e1e)
    MemSetCurrentHeap(4);
    e1_load_room(room);                 // room archive sections and the core camera data (engine room pack)
    e1_load_step("setup.archive");      // lane eng-load1: the KOS heap after each step (DOOR scene only)
    if (!first && !pG->pRoom) return;   // lane eng-load1: a missing archive refuses the room (core/room_change.cpp)
    pG->Rtp = GetDataExt(pG->pRoom, "RTP", 0);   // read.cpp ReadAreaData: the room's route points (the partner's follow)
    ReadPlayerData(pG->pl_type, pG->pl_costume);
#ifdef E2_BOSS
    e2_managers_room_init();
#else
    e1_managers_room_init();            // ModInfoMgr, PartsMgr, EmMgr, ObjMgr arrays on the room heap
#endif
    e1_load_step("setup.managers");
    e1_collision_room_init();           // SatMgr / EatMgr over the room's SAT / EAT
    e1_load_step("setup.collision");
    pG->sub_pos.x = pos[0];
    pG->sub_pos.y = pos[1];
    pG->sub_pos.z = pos[2];
    pG->sub_angle = ang;
    EmMgr.create(0, 0);                 // the player: cPlLeon on the actor table (hosted constructor + startUp)
    e1_load_step("setup.player");
    CameraRoomInit();
    void* cam = GetDataExt(pG->pRoom, "CAM", 0);
    if (cam) CamCtrl.RoomDataRead((CameraDataHeader*) cam);
    else pG->pCamRoom = cam;
    CamCtrl.CoreDataRead((CameraDataHeader*) (pG->pArc->ofs_30 + (u32) pG->pArc));
    {   // lane eng-e1p (H-018.1): every motion cut of the room's and the core's camera data exported and converted now,
        // loading work; a cut switch in play is a lookup. A room whose tracks do not fit the store is refused.
        const int rc = cam_track_room_load(pG->pCamRoom, pG->pCamCore);
        u32 cuts, tracks, refused, bytes, limit;
        cam_track_room(&cuts, &tracks, &refused, &bytes, &limit);
        if (rc) {
            e1_log("E1 load: camera tracks refused: room %03x needs %lu bytes for %lu motion cuts, the room store's ceiling "
                   "%lu (56 cuts)\n",
                   (unsigned) pG->room_id, (unsigned long) bytes, (unsigned long) cuts, (unsigned long) limit);
            for (;;) thd_sleep(1000);
        }
        e1_log("E1 CAMTRACK room %03x: motion cuts %lu converted %lu refused %lu, room store %lu bytes (allocated at load; "
               "ceiling %lu)\n",
               (unsigned) pG->room_id, (unsigned long) cuts, (unsigned long) tracks, (unsigned long) refused,
               (unsigned long) bytes, (unsigned long) limit);
    }
    e1_load_step("setup.camera-tracks");
    CamCtrl.roomInit();
    e1_view_room_init();
    e1_load_step("setup.camera-view");
#ifdef E2_BOSS
    e2_room_init();                     // enemy list, the boss module, the room script (R119Init)
#endif
    pG->Rno0 = 3;
    pG->Rno1 = 0;
    e1_partner_room_init();             // the hill scene: Leon resumed, Ashley created (core/partner.cpp)
}
void e1_room_setup(unsigned room, const float pos[3], float ang, int first) { room_init(room, pos, ang, first); }

// Lab arm CAMEVERY (boot file; the camera check's control, lane eng-e1m): after Leon's move the shoulder camera is handed
// his matrix every tick, as the PC reference did before its routine bytes were swapped (it read Leon idle and not moved
// as moving). The game hands it over only when he moved (player.cpp move); the camera check must fail with this arm.
static int cam_every;

// gameMainLoop, the hosted subset in its order (game.cpp:798).
static void game_tick(E1Timing& tm)
{
    BitOff(pG->Status_flg[2], 0x10000000);
    pG->quake_ofs.x = 0.0f;
    pG->quake_ofs.y = 0.0f;
    pG->quake_ofs.z = 0.0f;
    e1_room_change_tick_begin(e1_tick);   // lane eng-load1: SceAtCheck's place (the DOOR scene's door request; else nothing)
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
        if (cam_every) CamCtrl.m_QuasiFPS.setPlayerLocation(pPL->mat, pPL->pFloor_norm);   // CAMEVERY (control)
    }
    BitOff(pG->Status_flg[2], 0x8000000);
    e1_stamp(2);
    e1_rng_owner(3);
    uint64_t t1 = now_us();
    if (!(pG->Stop_flg & 0x4000000)) ObjMgr.move();
    uint64_t t2 = now_us();
    e1_rng_owner(2);
    CameraMove();                       // lane eng-e1j: the camera service writes the renderer's record itself (eng_camera.h)
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
    e1_cloth_stat_tick();               // CLOTHSTAT only (diagnostic, outside the timed rows)
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
    e1_clock_boot();                    // lane eng-clock1: the TMU2 reload check; GAPPROBE (core/e1_clock.cpp)
    e1_svc_boot();                      // the native services' check build (SKELCHECK)
    e1_lab_boot();                      // lane eng-e1o: the record's controls, read before play (core/e1_core.h)
    e1_room_change_boot();              // lane eng-load1: the DOOR scene (DOOR.TXT) and its controls, before play
    if (e1_door_scene) RndInit((u16) e1_door_seed());   // the fixture's generator seed (re4ref RndInit(seed))
    {
        file_t f = fs_open("/cd/CAMEVERY", O_RDONLY);
        if (f >= 0) {
            fs_close(f);
            cam_every = 1;
            e1_log("E1 CAMEVERY: the shoulder camera handed Leon's matrix every tick (lab arm, control)\n");
        }
    }
    // The hill scene holds 0.84 MB more room data (the partner's archive and motion keys): the renderer's pack goes
    // first, while the KOS heap is empty, so its whole-file staging read (7.8 MB; the textures then go to video
    // memory) fits before the room data is loaded.
    const bool pack_first = e1_scene == E1_SCENE_HILL;
    if (pack_first) e1_draw_open();
    e1_state[0] = 2;
    {
        const E1Route& r = e1_route();
        room_init(r.room, r.pos, r.ang, 1);
    }
    e1_state[0] = 3;
    e1_log("E1 engine: room %03x ready, player %p pos %d %d %d\n", (unsigned) pG->room_id, (void*) pPL,
           (int) pPL->pos.x, (int) pPL->pos.y, (int) pPL->pos.z);
    if (!pack_first) e1_draw_open();
    e1_pool_control();                  // POOLCTL boot file: a forced double free (lane eng-e1i, the selector's control)
    e1_memmap_sample();
    e1_heap_room_checks();              // heap descriptors' map; HEAPCK: the heap-4 exercise (lane eng-e1e)
    e1_state[0] = 4;
    unsigned ticks = e1_route().ticks;
    e1_state[2] = ticks;
    e1_trace_tick(0);
    e1_clock_fields();                  // lane eng-clock1: GAPPROBE's field span (no-op without the boot file)
    e1_fields_start();                  // presented fields from the hardware's vblank count (lane eng-e1f)
    // lane eng-load1: the round trip's first marks, at the point of the loop where every later room's are taken (the room
    // ready, its first tick next): after the field counter's start, whose vblank handler node (KOS vblank.c
    // vblank_handler_add, 24 B on the KOS heap, boot lifetime) Flycast run 4 showed in the first mark's difference
    if (e1_door_scene) e1_room_marks_take("first");
    for (e1_tick = 1; e1_tick <= ticks; e1_tick++) {
        e1_state[1] = e1_tick;
        E1Timing& tm = e1_timing[(e1_tick - 1) % E1_TICKS];
        uint64_t a = now_us();
        e1_stamp_pic = e1_tick - 1;
        e1_stamp(6);
        e1_input_latch(e1_tick);
        e1_partner_tick_begin(e1_tick);
        e1_svc_tick_begin(e1_tick);     // RUMBLEX only (lane eng-e1e): the rumble exercise's planted calls
        PadRead();
        pG->Frame_cnt++;
        e1_stamp(0);
        uint64_t b = now_us();
        game_tick(tm);
        e1_partner_tick_end(e1_tick);
        e1_stamp(3);
        uint64_t c = now_us();
        if (!e1_lab.camrec0)            // CAMREC0 (lane eng-e1o, control): no tick checked; the selector must fail it
            eng_cam_check_tick(e1_tick);    // lane eng-e1l: the camera record finite (E1 CAMREC; outside the tick's rows)
        e1_trace_tick(e1_tick);
        e1_stamp(4);
        uint64_t d = now_us();
        e1_draw_picture(tm);
        uint64_t e = now_us();
        tm.input_us = b - a;
        tm.tick_us = c - b;
        tm.trace_us = d - c;
        // lane eng-e1e (E1 audit section 5): the Drawing row is the renderer's own span, stamp 5 (chip ready) to 7
        // (picture submitted), set by e1_draw_picture as the hardware model times it; the PVR wait is pvr_us; the
        // call's set-up before stamp 5 (skeleton views) stays in the frame's remainder
        (void) e;
        e1_fields_late(e1_tick);        // LATEPIC (control): picture 300 held 100 ms after its scene
        e1_pace_end(tm);                // waits for the target field (core/frame.cpp; lab arm PACETMU: the timer)
        e1_fields_tick(e1_tick);        // the tick's end in fields (the headless images' interval)
        tm.frame_us = now_us() - a;
        // lane eng-load1: the game asked for a room change (its door handler set the routine to 4): the loading state,
        // outside the tick's rows (core/room_change.cpp). A failed load ends the run with its report (no hang).
        e1_room_tick_done();
        if (e1_room_change_pending() && e1_room_change_run(e1_tick) < 0) {
            ticks = e1_tick;
            e1_state[2] = ticks;
            break;
        }
    }
    e1_fields_finish(ticks);            // each row's presented-field interval, and the E1 FIELDS line
    e1_state[0] = 5;
    e1_report();
#ifdef E2_BOSS
    e2_report();
#endif
    e1_state[3] = 1;
    for (;;) thd_sleep(1000);
}
