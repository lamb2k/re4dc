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
// ScenarioMove (the room's main, the event manager, the scenario tasks 5..17).
void sched_host_scenario(unsigned tick);
// After the game task's step (main.cpp: TaskScheduler runs slots 0..3 after slot 0's gameMainLoop): every scene.
void sched_host_tasks(unsigned tick);
// After play: the E1 SCHED line (task steps, cost a tick, stacks' high-water marks, KOS thread records).
void sched_host_report();
#endif
