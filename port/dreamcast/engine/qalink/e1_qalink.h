// e1_qalink.h: the RE4 engine's layer on dc-qalink 0.2 (lane eng-link2, 2026-11-23; docs/engine/CONSOLE_LOOP.md
// section 17). QA and test builds only: game/qalink.mk links it with SENDABLE=1 (DCQL_ENABLE defaults to it); a build
// without it (the default, FIGHT=1 and BOSS=1 images, or SENDABLE=1 DCQL_ENABLE=0) has none of it and these calls are
// not compiled (core/main.cpp: #ifdef E1_QALINK).
#ifndef E1_QALINK_H
#define E1_QALINK_H
#include "e1_core.h"

// First thing in main (before any /cd read): started by the loader with the link on the adapter, mounts the network
// disc (the PC's changed files over the GDEMU disc; args disc=gd: the GDEMU disc alone) and declares the live data.
void e1_ql_early();
// Before the first tick: the run's length from the arguments (ticks=N), else the scene's own.
unsigned e1_ql_ticks(unsigned ticks);
// After each picture, outside the tick's rows (after e1_room_tick_done, before the room-change check): the picture's
// record copied for the PC, the PC's commands (a warp plants the room-change request the loop answers next), the
// in-game menu (held pictures while it is open). Returns 1 when the PC asked to end the run now.
int e1_ql_picture(const E1Timing& tm);
#endif
