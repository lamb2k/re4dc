// sched_host.cpp (lane eng-sched1, plan 3.3 section 8 B2; SALVAGE_20261121.md row 6): the game's script scheduler on
// the engine. Default image only (the fight and boss images run their own task layer, engine/fight, engine/boss).
//
// Hosted, unchanged (allowed_original.txt "scheduler"): src/game/scheduler.cpp (the 18 task slots, each an OS thread
// with its own stack, run until it sleeps), src/game/sce_sys.cpp (the scenario layer: the task table's walk in ordering
// order, SceExec / SceSleep / SceExit / SceKill, the deferred conditions, the room start and the per-tick step) and the
// village's room script src/st1/r101.cpp. They run on the engine's OS layer (core/os_threads.cpp, lifted from the old
// port) and the engine's list container (services/scene/at_list.cpp).
//
// Where they run in the engine's tick (core/main.cpp), against the original's main loop (main.cpp: PadRead,
// Frame_cnt++, TaskScheduler = slot 0's gameMainLoop, then slots 1..3; the ISR slot 4 after the CPU work):
//   1 input latch and PadRead, Frame_cnt++                       (main.cpp, as the original)
//   2 game_tick = slot 0's gameMainLoop, engine form; its first step is ScenarioMove (game.cpp gameMainLoop: before
//     EmMgr.move and the player): sched_host_scenario -> sce_sys ScenarioMove -> R101Main, EvtMgr.Run, then
//     SceSys.scheduler(): scenario tasks 5..17 in ordering order, each run until it sleeps
//   3 the partner (EmMgr.move), the player, objects, camera                      (gameMainLoop order, engine form)
//   4 sched_host_tasks -> TaskScheduler(): slots 0..3 (slot 0 is the engine's own loop and stays empty; 1..3 hold
//     the debug, sub-screen and movie tasks when a hosted unit starts one)
//   5 draw, pacer. The ISR slot (iTaskScheduler: the background decompression and loading task) is not run: the
//     engine loads nothing in play (core/play_files.c), so no hosted unit may start one (iTaskExec: a logged stub
//     count would show it).
// The room script is started only in the lab scene SCHED (boot file /cd/SCHED, read before play): the default
// village scene hosts no room script yet (that is chapter 1's hosting, a later lane), so its play is unchanged; the
// scheduler itself runs in every scene (step 4).
//
// Memory (lane eng-mem2 owns the map): the task stacks are the scheduler's own pool, 18 slots of 12 KiB (scheduler.cpp
// GetStackSize under its RE4DC_GAME correction: 221,184 bytes), on the KOS heap (scheduler.o's mem_alloc is bound to
// sched_stack_alloc, game/Makefile); each task also takes one KOS thread record (about 1.6 KB of KOS malloc) while
// it lives. The report prints every stack's high-water mark so the map's owner can size them.
#ifndef E2_BOSS
#include "types.h"
#include "global.h"
#include "scheduler.h"
#include "sce_sys.h"
#include "room_data.h"
#include "e1_engine.h"
#include "e1_clock.h"
#include "os_threads.h"
#include "sched_host.h"
#include <kos.h>
#include <malloc.h>
#include <string.h>

void R101Init();
void R101Main();

// ---- the room table, as far as the engine hosts room scripts (roomdata.cpp's dispatch, engine form) and the room's
// save record (the flags the script reads and sets through RsfCheck / RsfSet): one record, a first visit.
cRoomData RoomData;
alignas(32) static u8 room_save[0x100];
void cRoomData::execInitFunc(u16 room)
{
    if (room == 0x101) R101Init();
    else e1_stub_hit("cRoomData::execInitFunc(room not hosted)", room);
}
void cRoomData::execMainFunc(u16 room)
{
    if (room == 0x101) R101Main();
}
u8* cRoomData::getRoomSavePtr(u16) { return room_save; }

// ---- what scheduler.cpp asks of the platform
// No disc call can be in progress inside a task: the engine opens and reads nothing in play.
extern "C" int re4dc_io_busy(const void*) { return 0; }
extern "C" void GXSetCurrentGXThread(void) {}   // the GameCube's graphics FIFO owner: the engine's renderer has none
void DbMenuRestoreStopFlag() {}                 // the debug menu is not hosted
// The scheduler's stack pool, on the KOS heap (game/Makefile binds scheduler.o's mem_alloc here).
extern "C" void* sched_stack_alloc(u32 size, const char*, int, int, int)
{
    void* p = memalign(32, size);
    if (!p) {
        e1_log("E1 SCHED: the task stacks' %lu bytes refused by the KOS heap\n", (unsigned long) size);
        e1_stub_hit("sched_stack_alloc(refused)", (int) size);
    }
    return p;
}

// ---- counters (outside the timed rows: two clock reads a step)
static int scene, ctl_stackx;
static unsigned steps, steps_tick, steps_max, ticks_run, init_tasks;
static uint64_t scen_sum, scen_max, sched_sum, sched_max;
static unsigned scen_max_tick, sched_max_tick, scen_over;
extern "C" void __real_TaskSchedulerMain(TASK* t);
extern "C" void __wrap_TaskSchedulerMain(TASK* t)
{
    steps++;
    steps_tick++;
    __real_TaskSchedulerMain(t);
}

void sched_host_boot()
{
    os_threads_boot();
    TaskSchedulerInit();
    ScenarioInit();
    file_t f = fs_open("/cd/SCHED", O_RDONLY);
    if (f >= 0) { fs_close(f); scene = 1; }
    f = fs_open("/cd/SCHEDX", O_RDONLY);
    if (f >= 0) { fs_close(f); ctl_stackx = 1; }
    e1_log("E1 SCHED boot: scheduler hosted, %u task slots on the KOS heap%s%s\n", (unsigned) TASK_NUM,
           scene ? "; lab scene SCHED: the village's room script (st1/r101) runs" : "",
           ctl_stackx ? "; SCHEDX: a scenario task's stack guard overwritten at tick 300 (control)" : "");
}

void sched_host_room_init()
{
    if (!scene) return;
    steps_tick = 0;
    ScenarioRoomInit();
    for (unsigned i = 5; i < TASK_NUM; i++) init_tasks += Task[i].Status != 0;
}

void sched_host_scenario(unsigned tick)
{
    if (!scene) return;
    if (ctl_stackx && tick == 300) {   // SCHEDX (control): the first live scenario task's guard word
        for (unsigned i = 5; i < TASK_NUM; i++)
            if (Task[i].Status) { *(u32*) (Task[i].pStack - Task[i].StackSize) = 0; break; }
    }
    const uint64_t a = e1_clock_us();
    ScenarioMove();
    const uint64_t d = e1_clock_us() - a;
    scen_sum += d;
    scen_over += d > 100;
    if (d > scen_max) scen_max = d, scen_max_tick = tick;
}

void sched_host_tasks(unsigned tick)
{
    const uint64_t a = e1_clock_us();
    TaskScheduler();
    const uint64_t d = e1_clock_us() - a;
    sched_sum += d;
    if (d > sched_max) sched_max = d, sched_max_tick = tick;
    ticks_run++;
    if (steps_tick > steps_max) steps_max = steps_tick;
    steps_tick = 0;
}

void sched_host_report()
{
    unsigned created, reaped, pending, live = 0;
    os_threads_stats(&created, &reaped, &pending);
    for (unsigned i = 0; i < TASK_NUM; i++) live += Task[i].Status != 0;
    const unsigned n = ticks_run ? ticks_run : 1;
    e1_log("E1 SCHED scene %s: ticks %u, scenario tasks at room start %u, live at end %u; task steps %u (at most %u a "
           "tick); ScenarioMove mean %lu us worst %lu us (tick %u), over 100 us %u; TaskScheduler mean %lu us worst %lu us "
           "(tick %u); KOS thread records created %u reaped %u pending %u\n",
           scene ? "village-script" : "default", ticks_run, init_tasks, live, steps, steps_max,
           (unsigned long) (scen_sum / n), (unsigned long) scen_max, scen_max_tick, scen_over,
           (unsigned long) (sched_sum / n), (unsigned long) sched_max, sched_max_tick, created, reaped, pending);
    OsStackMark m[32];
    const unsigned k = os_threads_stacks(m, 32);
    for (unsigned i = 0; i < k; i++) {
        const TASK* t = 0;
        for (unsigned j = 0; j < TASK_NUM; j++)
            if ((const void*) &Task[j].Thread == m[i].thread) t = &Task[j];
        e1_log("E1 SCHED stack slot %d: bytes %u used %u (high water) guard %08x\n", t ? (int) t->Task_no : -1, m[i].bytes,
               m[i].bytes - m[i].untouched - 4, m[i].guard);
    }
    if (!k) e1_log("E1 SCHED stacks: no task ran\n");
}
#endif
