/* actor_rt.h: the Dreamcast-native actor runtime, in-game preview (lane behave18, 2026-10-18; ENGINE_PREVIEW=1).
 *
 * Shared room services for enemies, computed once per room or once per tick, read by every actor:
 *   - the room grid (EDGR v1, tools/enginebake/build_grid.py; r101 only in the preview): floor planes, wall segments,
 *     8-neighbour passability;
 *   - one flow field toward Leon (BFS over the grid, rerun only when Leon changes cell);
 *   - grid movement collision (walls + floor) that replaces the polygon world check where the grid can decide.
 * The game's cEm10 stays the facade (position, hp, routines, damage, events); see em10.cpp RE4DC_ENGINE_PREVIEW.
 * Coordinates: game mm, y up. All functions are C, no allocation (static tables), no FPSCR changes.
 */
#ifndef ACTOR_RT_H
#define ACTOR_RT_H
#ifdef __cplusplus
extern "C" {
#endif

/* 1 when the runtime has a grid for this room ((stage << 8) | room). */
int re4dc_rt_room(unsigned room);
/* once per tick (any caller; repeated calls in the same tick do nothing): the flow field toward (lx, lz). */
void re4dc_rt_tick(unsigned frame, float lx, float lz);
/* steering goal for an actor at (x, z): a point one step along the flow field. 0 = no field here (use the game's). */
int re4dc_rt_steer(float x, float z, float* gx, float* gz);
/* grid collision for an actor moved to (*x, *y, *z) from (ox, oz): wall push-out + floor height. Returns 0 when the
 * grid cannot decide (outside, no floor, a floor more than 400 mm from y: multi-level cells), and leaves x/y/z as is. */
int re4dc_rt_collide(float* x, float* y, float* z, float ox, float oz);
/* foot IK floor query for the actor in re4dc_rt_ik_actor (set by cEm10::move for the actor the runtime owns, else 0):
 * the grid floor under (x, z) near y, or -100000 when the grid cannot decide (the caller then asks SatMgr). */
extern void* re4dc_rt_ik_actor;
float re4dc_rt_floor(float x, float y, float z);
/* counters for the preview log line */
void re4dc_rt_count(int owned, int fallback);
void re4dc_rt_log(unsigned frame, int leon_life);
void re4dc_rt_state(const void* em, unsigned stat, int hp, unsigned frame, float x, float z);

#ifdef __cplusplus
}
#endif
#endif
