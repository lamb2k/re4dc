// E1 collision tables (lane eng-e1): the room's SAT (scenery) and EAT (effect) collision in the engine's tables,
// set up as gameRoomInit does (game.cpp: roomInit, arrayAlloc, create over the room archive's SAT / EAT).
// The queries are the collision service units (SHELL_MAP section 4, "collision queries": hitCheck, getFloor, check)
// compiled under the service boundary (game/hosted.mk SVC_ORIG_SRCS, first form).
#include "global.h"
#include "atari.h"
#include "e1_engine.h"
#include "e1_core.h"
void* GetDataExt(void* arc, const char* tag, int no);
void e1_collision_room_init()
{
    Vec pos = {0.0f, 0.0f, 0.0f}, rot = {0.0f, 0.0f, 0.0f};
    void* sat = GetDataExt(pG->pRoom, "SAT", 0);
    SatMgr.roomInit();
    SatMgr.arrayAlloc(16);
    SatMgr.create(sat, 0, &pos, &rot, 0);
    void* eat = GetDataExt(pG->pRoom, "EAT", 0);
    EatMgr.roomInit();
    EatMgr.arrayAlloc(16);
    EatMgr.create(eat, 0, &pos, &rot, 0);
    SatMgr.seCk = 0;
    EatMgr.seCk = 1;
    EatMgr.initEffInfo();
    e1_log("E1 collision: SAT %p EAT %p\n", sat, eat);
}
