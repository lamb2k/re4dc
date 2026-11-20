// E1 collision tables (lane eng-e1): the room's SAT (scenery) and EAT (effect) collision in the engine's tables,
// set up as gameRoomInit does (game.cpp: roomInit, arrayAlloc, create over the room archive's SAT / EAT).
// The query cores run natively on tables baked here (services/collision/col.cpp, lane eng-e1c): hitCheck2, hitCheck,
// polySphereCk; check, getFloor, wallAdjust and adjust above them stay the original's (atari.cpp).
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
    e1_svc_room_ready();                // the native collision tables of the room's pieces (col_bake_all)
    e1_log("E1 collision: SAT %p EAT %p\n", sat, eat);
}
