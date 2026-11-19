// E1 engine core interface (lane eng-e1).
#ifndef E1_CORE_H
#define E1_CORE_H
#include <stdint.h>

#define E1_TICKS 1024
struct E1Timing {
    uint32_t input_us, tick_us, services_us, trace_us, draw_us, wait_us, frame_us, fields;
};
extern E1Timing e1_timing[E1_TICKS];
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
#endif
