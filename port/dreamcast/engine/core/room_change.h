// Room change (lane eng-load1): the engine's loading state between two rooms. The game decides that the room changes
// (its door handler stores the destination and sets the game routine to 4, sce_at.cpp sceAtFunc_door); the engine
// answers with a loading state outside the timed ticks: the first room's memory returned (its archive, its room heap,
// its collision and skeleton tables, the renderer's pack), the second room loaded, the player placed where the door
// said, then play resumes. docs/engine/CONSOLE_LOOP.md section 14, docs/engine/SERVICES.md "Room change".
#ifndef E1_ROOM_CHANGE_H
#define E1_ROOM_CHANGE_H
#include <stdint.h>
#include "e1_core.h"

// The DOOR scene (boot file /cd/DOOR.TXT, the same fixture text the PC reference replays: tools/plays_right/fixtures/
// door-r101-r103.txt): its start, its pad script and its door requests. Read once before play (e1_room_change_boot).
extern int e1_door_scene;
void e1_room_change_boot();
const E1Route* e1_door_route();                // the scene's start, or 0 outside the DOOR scene
int e1_door_pad(unsigned tick, E1Pad* out);   // the scene's pad for this tick (1), or 0 outside the scene

// Per tick, at the place gameMainLoop runs its area check (game.cpp SceAtCheck): the door request of the scene's
// fixture, planted (a logged stub while the default image does not host the area check; hand-back request R1).
void e1_room_change_tick_begin(unsigned tick);
// After the tick's picture: the game asked for a room change (pG->Rno0 == 4).
int e1_room_change_pending();
// The loading state: returns 0 when play resumes in the new room, -1 when the load failed (the reason is logged as
// "E1 LOAD FAILED ...": the run ends with its report, no hang).
int e1_room_change_run(unsigned tick);

// Room-set-up entry the loop calls for the first room and the room change calls for every later one (core/main.cpp).
void e1_room_setup(unsigned room, const float pos[3], float ang, int first);
// The memory marks taken when a room is ready (before its first tick) and the round-trip check over them.
void e1_room_marks_take(const char* when);
void e1_room_change_report();
// Ticks run in each room (the scene's check that both rooms ran theirs).
void e1_room_tick_done();
#endif
