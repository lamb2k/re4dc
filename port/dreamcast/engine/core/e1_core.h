// E1 engine core interface (lane eng-e1; the partner and the hill scene: lane eng-e1b).
#ifndef E1_CORE_H
#define E1_CORE_H
#include <stdint.h>

#define E1_TICKS 1024
struct E1Timing {
    uint32_t input_us, tick_us, services_us, trace_us, draw_us, wait_us, frame_us, fields, player_us, obj_us, cam_us, pvr_us;
    uint32_t chars_us;   // the characters' moves (the partner), inside tick_us
    uint32_t svc_group_us[7];   // the services row split (lane eng-e1c): index E1_SVC_* (0 unused; 5 effects, lane eng-e2; 6 camera, lane eng-e1j)
};
extern E1Timing e1_timing[E1_TICKS];
// Services row split (lane eng-e1c): the group of each service entry point (host/e1_wraps.cpp), also the words of
// the MODELLED service stamps (e1_svc_stamp: 0 back in the behaviour). Lane eng-e1j: 6, the camera service's
// evaluation (services/camera: the record, the frustum and every entry point the hosted controller calls).
enum { E1_SVC_MOTION = 1, E1_SVC_CLOTH = 2, E1_SVC_PARTS = 3, E1_SVC_COLLISION = 4, E1_SVC_EFFECTS = 5, E1_SVC_CAMERA = 6, E1_SVC_GROUPS = 7 };   // effects: lane eng-e2
uint32_t e1_svc_group(unsigned g);
void e1_svc_publish();
// native services host side (lane eng-e1c, host/e1_svc_mem.cpp): boot options, room tables, report
void e1_svc_boot();
void e1_svc_tick_begin(unsigned t);
extern int e1_game_seed_option;   // core/globals.cpp, boot option SEED (lane eng-e1e: the hill scene applies it too)
// (lane eng-e1n: no HUD draw step either: the renderer makes the ammo digits from the live count when it draws them)
extern "C" void e1_pool_control(void);   // services/model/mgr_pool.cpp: POOLCTL (lane eng-e1i)
void e1_svc_room_ready();
void e1_svc_report();
void e1_cloth_stat_tick();   // lane eng-e1d: CLOTHSTAT boot option, the cloth chains' shape statistics   // the palette, once a tick after the behaviour (native skeleton), in the services row
extern volatile uint32_t e1_state[8];

// The route: start state (the reference fixture's warp: room, position, angle, flags) and the pad script, one
// PADStatus per tick (GameCube button bits, stick x / y, analog R), keyed by the tick after the player is placed.
struct E1Pad { uint16_t buttons; int8_t sx, sy; uint8_t trig_r; };
struct E1Route {
    unsigned room, find, ticks;
    float pos[3], ang;
    // lane eng-snd1 (R9): the behaviour generator's seed, part of the start state: the reference fixture's `seed` line,
    // set by core/main.cpp room_init where re4ref sets it (hostref/replay.cpp: before PlayerInit). -1: the image's own
    // start sets it (the fight image: fight/shot_e2.cpp with SHOT.TXT; the boss image: not seeded).
    int seed = -1;
};
const E1Route& e1_route();
void e1_input_latch(unsigned tick);
void e1_room_globals(const E1Route& r);
void e1_globals_init();
void e1_load_room(unsigned room);
void e1_managers_room_init();
void e1_collision_room_init();
void e1_view_room_init();
// services timing: the time spent inside service entry points (skeleton, collision) during the tick
void e1_svc_begin();
uint32_t e1_svc_end();
// memory map
void e1_memmap_boot();
void e1_memmap_sample();
// draw and pace
void e1_draw_open();
void e1_draw_picture(E1Timing& tm);
void e1_pace_end(E1Timing& tm);
// presented fields (lane eng-e1f, core/frame.cpp): start before the first tick, the LATEPIC control and the tick's end
// after each picture, then each row's fields column from the vblank handler's flips (mode tick when headless)
void e1_fields_start();
void e1_fields_late(unsigned tick);
void e1_fields_tick(unsigned tick);
void e1_fields_finish(unsigned ticks);
// trace and report
void e1_trace_tick(unsigned tick);
void e1_report();
// Boot files before play (lane eng-e1o, H-017.7): the record's controls, each a boot file read once before the first
// picture (core/frame.cpp e1_lab_boot). Nothing looks a file up inside a picture: core/play_files.c counts every open
// between the first and the last picture (E1 FILES), the selector fails a timing scene where it is not 0.
//   CAMREC0  the camera record's finite check skipped on every tick (E1 CAMREC ticks 0)
//   MEMCUT   the after-play memory line cut after the arena margin
//   RUNFUNC  the run line says "function" although nothing is traced or captured
//   NUMTEXT  the FIELDS line's release-queue count printed as text
//   OPENX    a boot file looked up at picture 100 (a file open inside play)
//   STACKX   one stack guard word overwritten at tick 300 (lane eng-e1k)
//   LIGHTMISS every character's light view refused (lane eng-e1n: E1 PUB light-view-misses, the scene fails)
//   HUDFREEZE the HUD's ammo count frozen at the renderer's open (lane eng-e1n: hudcheck must fail)
// Lane eng-e1p (H-018):
//   CUTCONV  a cut switch converts its camera track in play, as before (E1 CAMTRACK in-play 1: the scene fails)
//   CAMSTORE the camera track store limited to 1024 bytes (the room is refused at load: "E1 load: camera tracks refused")
//   MEMNOFREE the after-play memory line without its mallinfo free value
//   TICKS1   E1 DONE ticks and E1 CAMREC ticks both 1 (they agree with each other, not with the rows)
//   ROWTOKEN row 300's fields value printed with a trailing token ("2,missing")
//   READX    a disc file opened before play, 2048 bytes read from it at picture 100 (no open in play: E1 FILES reads)
struct E1Lab { int camrec0, memcut, runfunc, numtext, openx, stackx, lightmiss, hudfreeze;
               int cutconv, camstore, memnofree, ticks1, rowtoken, readx, readx_fd; };
extern E1Lab e1_lab;
void e1_lab_boot();
extern "C" void e1_play_files_begin(void);
extern "C" void e1_play_files_end(void);
extern "C" void e1_play_files_report(void);

// Scenes (lane eng-e1b): the village route (Leon alone, the default) and the hill path (Leon and Ashley, the partner;
// boot option HILL; core/partner.cpp).
enum { E1_SCENE_VILLAGE = 0, E1_SCENE_HILL = 1 };
extern int e1_scene;
extern E1Pad e1_pad_now;                      // the pad this tick (trace)
void e1_partner_boot();                       // the scene's boot options (HILL, FEED, CTRLFOL)
void e1_partner_room_init();                  // after the player: the resume, the partner created (SubCharInit)
void e1_partner_tick_begin(unsigned tick);    // before PadRead: the generator feed, partner commands, god
void e1_partner_chars_move(E1Timing& tm);     // the characters' move (EmMgr.move), before the player
void e1_partner_tick_end(unsigned tick);      // after the camera: the follow-distance control
void e1_trace_v2(unsigned tick);              // re4ref trace v2 lines (T, A, R) for the hill scene
void e1_rng_owner(int owner);                 // generator draws per caller: 0 other, 1 player, 2 camera, 3 objects, 4 spawn
void e1_trace_put(const char* line, unsigned n);   // a line into the trace buffer (core/frame.cpp)
// Phase stamps for the SH-4 hardware model (lane eng-e1b; the bench's m1_timing form, read by the observer that
// tools/hwmodel builds through engine/bench/model_profile.py): one store per phase boundary, 8 words a picture,
// 600 pictures. k: 6 picture start, 0 input done, 1 characters done, 2 player done, 3 objects and camera done,
// 4 trace done, 5 graphics chip ready, 7 picture submitted. The value is the microsecond clock (Flycast tier).
extern "C" volatile uint32_t m1_timing[600][8];
extern unsigned e1_stamp_pic;
void e1_stamp(unsigned k);
#endif
