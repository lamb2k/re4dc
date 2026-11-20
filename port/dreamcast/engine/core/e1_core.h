// E1 engine core interface (lane eng-e1; the partner and the hill scene: lane eng-e1b).
#ifndef E1_CORE_H
#define E1_CORE_H
#include <stdint.h>

#define E1_TICKS 1024
struct E1Timing {
    uint32_t input_us, tick_us, services_us, trace_us, draw_us, wait_us, frame_us, fields, player_us, obj_us, cam_us, pvr_us;
    uint32_t chars_us;   // the characters' moves (the partner), inside tick_us
    uint32_t svc_group_us[5];   // the services row split (lane eng-e1c): index E1_SVC_* (0 unused)
};
extern E1Timing e1_timing[E1_TICKS];
// Services row split (lane eng-e1c): the group of each service entry point (host/e1_wraps.cpp), also the words of
// the MODELLED service stamps (e1_svc_stamp: 0 back in the behaviour).
enum { E1_SVC_MOTION = 1, E1_SVC_CLOTH = 2, E1_SVC_PARTS = 3, E1_SVC_COLLISION = 4, E1_SVC_GROUPS = 5 };
uint32_t e1_svc_group(unsigned g);
void e1_svc_publish();   // the palette, once a tick after the behaviour (native skeleton), in the services row
extern volatile uint32_t e1_state[8];

// The route: start state (the reference fixture's warp: room, position, angle, flags) and the pad script, one
// PADStatus per tick (GameCube button bits, stick x / y, analog R), keyed by the tick after the player is placed.
struct E1Pad { uint16_t buttons; int8_t sx, sy; uint8_t trig_r; };
struct E1Route {
    unsigned room, find, ticks;
    float pos[3], ang;
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
// trace and report
void e1_trace_tick(unsigned tick);
void e1_report();

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
