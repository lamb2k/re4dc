/* actor_rt.h: the Dreamcast-native actor runtime (ENGINE_PREVIEW=1; lanes behave18 -> engine19). Original brain, new
 * body: cEm10's AI runs unchanged; in a room whose data file carries a static GRID the runtime answers the body calls
 * the AI makes (movement collision, the foot IK floor).
 *
 * The room grid lives in the room data file (/cd/dc/native/rXXX/room.r4rc, R4RC v1, tools/enginebake/room_compile.py),
 * loaded at room entry into heap 4 and freed at room leave. Without it the room runs the source path.
 * Coordinates: game mm, y up. All functions are C; queries do no allocation and no FPSCR changes.
 */
#ifndef ACTOR_RT_H
#define ACTOR_RT_H
#ifdef __cplusplus
extern "C" {
#endif

/* room lifecycle (ui_bridge.cpp): room = (stage << 8) | room */
void re4dc_rt_room_enter(unsigned room);
void re4dc_rt_room_leave(void);
/* 1 when the runtime has a grid for this room ((stage << 8) | room). */
int re4dc_rt_room(unsigned room);
/* grid collision for an actor moved to (*x, *y, *z) from (ox, oz): wall push-out + floor height. Returns 0 when the
 * grid cannot decide (outside, no floor, a floor more than 400 mm from y: multi-level cells), and leaves x/y/z as is. */
int re4dc_rt_collide(float* x, float* y, float* z, float ox, float oz);
/* foot IK floor query for the actor in re4dc_rt_ik_actor (set by cEm10::move for the actor the runtime owns, else 0):
 * the grid floor under (x, z) near y, or -100000 when the grid cannot decide (the caller then asks SatMgr). */
extern void* re4dc_rt_ik_actor;
float re4dc_rt_floor(float x, float y, float z);
/* counters for the log line */
void re4dc_rt_count(int owned, int fallback);
void re4dc_rt_log(unsigned frame, int leon_life);
void re4dc_rt_state(const void* em, unsigned stat, int hp, unsigned frame, float x, float z);

#ifdef __cplusplus
}
#endif
#endif
