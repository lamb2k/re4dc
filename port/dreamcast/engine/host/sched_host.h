// The game's script scheduler hosted on the engine (lane eng-sched1; host/sched_host.cpp). Default image only.
#ifndef ENG_SCHED_HOST_H
#define ENG_SCHED_HOST_H
// Before play (boot files are read here): the OS layer's main thread, the scheduler's task table and stacks, the
// scenario system; the lab scene SCHED (boot file /cd/SCHED) and its control SCHEDX.
void sched_host_boot();
// The room's start, at the end of the engine's room set-up: in the SCHED scene the scenario's room start (sce_sys
// ScenarioRoomInit: the room script's init and one task pass).
void sched_host_room_init();
// The scenario step at gameMainLoop's position (game.cpp: before EmMgr.move and the player): in the SCHED scene sce_sys
// ScenarioMove (the room's main, the event manager, the scenario tasks 5..17), then TaskScheduler (slots 0..3): the
// one point of the engine's tick where any task runs.
void sched_host_scenario(unsigned tick);
// After play: the E1 SCHED line (task steps, cost a tick, stacks' high-water marks, KOS thread records).
void sched_host_report();

// The object a hosted room script gets from SetObj00 (lane eng-sched2; game/obj00.cpp builds a room object from the
// room archive's model and texture data, a service this image does not host). A logged stub on both sides, the
// engine (host/sched_host.cpp) and the PC check's harness (hostref/svc/sched/sched_main.cpp): zeroed storage of the
// object's size whose vtable pointer (GCC's first word) points at a table of SCHED_STUB_OBJ_SLOTS entries, every entry
// the side's one logged stub returning 0. A call through any of the object's virtuals (R101Init: setNoSuspend) is
// counted and touches nothing else; a direct write into the object lands in its own zeroed storage.
#define SCHED_STUB_OBJ_SLOTS 128
static inline void* sched_stub_object(void* storage, unsigned bytes, void** table, void* fn)
{
    unsigned char* b = (unsigned char*) storage;
    for (unsigned i = 0; i < bytes; i++) b[i] = 0;
    table[0] = 0;   // offset to top
    table[1] = 0;   // type information (none: the hosted units are built without it)
    for (unsigned i = 2; i < SCHED_STUB_OBJ_SLOTS + 2; i++) table[i] = fn;
    *(void***) storage = table + 2;
    return storage;
}
#endif
