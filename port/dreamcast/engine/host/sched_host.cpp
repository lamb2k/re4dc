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
//   2b the partner (EmMgr.move), the player, objects, camera                     (gameMainLoop order, engine form)
//     then, at the same point, TaskScheduler(): slots 0..3 (slot 0 is the engine's own loop and stays empty; 1..3
//     hold the debug, sub-screen and movie tasks when a hosted unit starts one). This is the one point of the tick
//     where any task thread runs: every task is parked off KOS's run queue (core/os_threads.cpp) except while the
//     main thread waits for it in TaskSchedulerMain's hand-off, the main thread outranks every task, and the layer
//     has no alarms, so no task runs during services or drawing and nothing wakes one on a timer
//   3 draw, pacer. The ISR slot (iTaskScheduler: the background decompression and loading task) is not run: the
//     engine loads nothing in play (core/play_files.c), so no hosted unit may start one (iTaskExec: a logged stub
//     count would show it).
// The task table, the room script and the scheduler run only in the lab scene SCHED (boot file /cd/SCHED, read before
// play): the default village scene hosts no room script yet (that is chapter 1's hosting, a later lane), so its play
// is unchanged.
//
// Memory (docs/engine/MEMORY_MAP.md, the scheduler's rows): the task stacks are the scheduler's own pool, 18 slots at
// the GameCube's sizes (lane eng-sched3, H-043 ruling 2: GetStackSize below, 124,928 bytes; it was 18 x 12 KiB =
// 221,184 under the old port's RE4DC_GAME floor), in the behaviour arena (lane eng-sched2; scheduler.o's mem_alloc is
// bound to sched_stack_alloc, game/Makefile); each task also takes one KOS thread record (about 1.6 KB of KOS malloc)
// while it lives. The report prints every stack's high-water mark and names any slot over half its stack.
#ifndef E2_BOSS
#include "types.h"
#include "global.h"
#include "scheduler.h"
#include "sce_sys.h"
#include "room_data.h"
#include "datactrl.h"
#include "obj00.h"
#include "main_mem.h"
#include "e1_engine.h"
#include "e1_clock.h"
#include "os_threads.h"
#include "sched_host.h"
#include <kos.h>
#include <malloc.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void R101Init();
void R101Main();

// ---- the room table, as far as the engine hosts room scripts (roomdata.cpp's dispatch, engine form) and the room's
// save record (the flags the script reads and sets through RsfCheck / RsfSet): one record, a first visit.
cRoomData RoomData;
alignas(32) static u8 room_save[0x100];
// Lane eng-sched3: the cost split's lab arms (boot files, read before play) run the scenario layer without the room
// script: SCHEDN (with three idle scenario tasks, each SceSleep(1) every tick: the task switch alone) and SCHED0 (no
// task at all); the room's main is then not run.
static int arm_noscript;
static uint64_t main_us;   // this tick's R101Main span (stamps around it; the split's "room main")
void cRoomData::execInitFunc(u16 room)
{
    if (arm_noscript) e1_stub_hit("cRoomData::execInitFunc(lab arm: no room script)", room);
    else if (room == 0x101) R101Init();
    else e1_stub_hit("cRoomData::execInitFunc(room not hosted)", room);
}
void cRoomData::execMainFunc(u16 room)
{
    if (room == 0x101 && !arm_noscript) {
        const uint64_t a = e1_clock_us();
        R101Main();
        main_us += e1_clock_us() - a;
    }
}
u8* cRoomData::getRoomSavePtr(u16) { return room_save; }

// The data controller's units (the room's motion and model data sets, loaded by the original's datactrl, not hosted):
// the room script keeps the unit it is given and writes commands into it (R101Init: R101_SIZE), so a null return
// stops the console; zeroed units, as the PC check's harness (hostref/svc/sched/sched_main.cpp)
alignas(32) static u8 data_units[32][sizeof(cDataUnit)];
static unsigned data_units_used;
cDataUnit* cDataCtrl::setData(char*)
{
    e1_stub_hit("cDataCtrl::setData (a zeroed unit)", (int) data_units_used);
    return (cDataUnit*) data_units[data_units_used < 32 ? data_units_used++ : 31];
}

// ---- what scheduler.cpp asks of the platform
// No disc call can be in progress inside a task: the engine opens and reads nothing in play.
extern "C" int re4dc_io_busy(const void*) { return 0; }
extern "C" void GXSetCurrentGXThread(void) {}   // the GameCube's graphics FIFO owner: the engine's renderer has none
void DbMenuRestoreStopFlag() {}                 // the debug menu is not hosted
// ---- the scheduler's stack pool (TaskSchedulerInit's one MEM_ALLOC; scheduler.o's mem_alloc is bound here by
// objcopy, game/Makefile): the behaviour arena until the map owner places it
// Lane eng-sched2: the behaviour arena (the hosted units' heap API, host/e1_heap.cpp), not the KOS heap. On the KOS
// heap the pool ran the heap 200,704 B past its end into the arena (E1 MEM "free to arena -200704, overlaps 3": the
// village leaves 110,592 B between the heap and the arena) and overwrote the player in heap 4 before the first tick.
// The arena is where the original put it (TaskSchedulerInit's MEM_ALLOC on the current heap); placing it in the
// memory map proper stays with the map's owner.
// Lane eng-sched3 (H-043 ruling 2): the task stacks at the GameCube's sizes, set in the engine's build. scheduler.cpp's
// GetStackSize gives every slot a 12 KiB floor under RE4DC_GAME (the old port's correction for KOS's disc path, two
// PATH_MAX arrays, run on a task stack); the engine opens nothing in play, so the reason does not hold here. scheduler.o's
// GetStackSize is made weak (game/Makefile) and this table, the original's own sizes (its non-RE4DC branch: slot 2 the
// debug task 12 KiB, slots 0..4 8 KiB, the scenario slots 5..17 6 KiB), takes its place: 124,928 bytes in all instead
// of 221,184. The PC reference and the release line keep the correction. The guard stays (CSCHED), and the report
// names any slot whose high-water mark is over half its stack.
u32 GetStackSize(int no)
{
    static_assert(TASK_NUM == 18, "the table holds the original's 18 slots");
    static const u16 bytes[TASK_NUM] = {0x2000, 0x2000, 0x3000, 0x2000, 0x2000, 0x1800, 0x1800, 0x1800, 0x1800,
                                        0x1800, 0x1800, 0x1800, 0x1800, 0x1800, 0x1800, 0x1800, 0x1800, 0x1800};
    return (u32) no < TASK_NUM ? bytes[no] : 0x1800;
}
extern "C" void* sched_stack_alloc(u32 size, const char* file, int line, int flag, int heap)
{
    void* p = mem_alloc(size, file, line, flag, heap);
    if (!p) e1_log("E1 SCHED stack pool: %u bytes refused by the behaviour arena\n", (unsigned) size);
    else e1_log("E1 SCHED stack pool: %u bytes in the behaviour arena at %p\n", (unsigned) size, p);
    return p;
}

// ---- service functions of the hosted units this image does not run (made weak there; game/Makefile), logged stubs:
// r101's Ganado voice task (sound: fight/r101_weak.h makes the static weak; the fight image's is fight/r101_voice.cpp),
// cam_extra's binocular widget and focus blur (drawing). Under their assembler names, as fight/fight_svc_stubs.cpp.
#define SCHED_STUB_FN(sym, fn, label)     extern "C" void fn(void*, int, void*, void*) asm(sym);     extern "C" void fn(void*, int, void*, void*) { e1_stub_hit(label, 0); }
SCHED_STUB_FN("__ZL20r101_callGanadoVoicev", sched_r101_voice, "r101_callGanadoVoice")
SCHED_STUB_FN("__ZN11IdBinocular4initEP6CameraPvS2_", sched_idbino_init, "IdBinocular::init")
SCHED_STUB_FN("__ZN11IdBinocular4moveEPv", sched_idbino_move, "IdBinocular::move")
SCHED_STUB_FN("__ZN11IdBinocular4quitEPv", sched_idbino_quit, "IdBinocular::quit")
SCHED_STUB_FN("__ZN14FocusAnimation4initEi", sched_focus_init, "FocusAnimation::init")
SCHED_STUB_FN("__ZN14FocusAnimation4moveEi", sched_focus_move, "FocusAnimation::move")
SCHED_STUB_FN("__ZN14FocusAnimation4quitEv", sched_focus_quit, "FocusAnimation::quit")
SCHED_STUB_FN("__ZN13IDApplication4initEPv", sched_idapp_init, "IDApplication::init")
SCHED_STUB_FN("__ZN11IdBinocularD0Ev", sched_idbino_d0, "IdBinocular::~IdBinocular (deleting)")
SCHED_STUB_FN("__ZN11IdBinocularD1Ev", sched_idbino_d1, "IdBinocular::~IdBinocular")
SCHED_STUB_FN("__ZN11IdBinocularD2Ev", sched_idbino_d2, "IdBinocular::~IdBinocular (base)")
// the widget base's and the binocular widget's header inlines, emitted by cam_extra (taken from here by name, as the
// fight image takes the destructors): only a binocular camera constructs one (r101's binocular event, never in SCHED)
SCHED_STUB_FN("__ZN11IdBinocularC1Ev", sched_idbino_c1, "IdBinocular::IdBinocular")
SCHED_STUB_FN("__ZN11IdBinocularC2Ev", sched_idbino_c2, "IdBinocular::IdBinocular (base)")
SCHED_STUB_FN("__ZN13IDApplicationC1Ev", sched_idapp_c1, "IDApplication::IDApplication")
SCHED_STUB_FN("__ZN13IDApplicationC2Ev", sched_idapp_c2, "IDApplication::IDApplication (base)")
SCHED_STUB_FN("__ZN13IDApplicationD0Ev", sched_idapp_d0, "IDApplication::~IDApplication (deleting)")
SCHED_STUB_FN("__ZN13IDApplicationD1Ev", sched_idapp_d1, "IDApplication::~IDApplication")
SCHED_STUB_FN("__ZN13IDApplicationD2Ev", sched_idapp_d2, "IDApplication::~IDApplication (base)")
SCHED_STUB_FN("__ZN13IDApplication4moveEPv", sched_idapp_move, "IDApplication::move")
SCHED_STUB_FN("__ZN13IDApplication4quitEPv", sched_idapp_quit, "IDApplication::quit")
SCHED_STUB_FN("__ZN13IDApplicationdlEPvj", sched_idapp_dl, "IDApplication::operator delete")
// scheduler.cpp's debug page of stack use (debug_mode 6: text through the debug print); the E1 SCHED lines give it
SCHED_STUB_FN("_stackUsedCheck", sched_stack_page, "stackUsedCheck")

// ---- SetObj00's object (lane eng-sched2): R101Init's region path (pSys->region != 0, as the engine sets it:
// core/globals.cpp e1_room_globals) keeps the object and calls its setNoSuspend; a logged stub object (sched_host.h),
// the same as the PC check's harness gives
alignas(32) static u8 stub_obj[4][sizeof(cObj)];
static void* stub_obj_table[SCHED_STUB_OBJ_SLOTS + 2];
static unsigned stub_objs;
static int sched_stub_obj_virtual(void*)
{
    e1_stub_hit("SetObj00 object: a virtual call", 0);
    return 0;
}
cObj* SetObj00(void*, void*, Vec*, Vec*)
{
    e1_stub_hit("SetObj00 (a logged stub object)", (int) stub_objs);
    void* p = stub_obj[stub_objs < 4 ? stub_objs++ : 3];
    return (cObj*) sched_stub_object(p, sizeof(cObj), stub_obj_table, (void*) sched_stub_obj_virtual);
}

// ---- counters (outside the timed rows: two clock reads a tick around the scenario step)
static int scene, ctl_stackx, ctl_delay;
static unsigned steps, steps_tick, steps_max, ticks_run, init_tasks;
static uint64_t scen_sum, scen_max, sched_sum, sched_max;
static unsigned scen_max_tick, sched_max_tick, scen_over, stubs_at;
// The task-step record (lane eng-sched2): every TaskSchedulerMain call, as the PC check's trace writes it (tick,
// slot, status and sleep count before and after, the task's function), kept in a buffer in the behaviour arena (SCHED scene
// only) and printed after play (E1 SCHEDT lines; hostref/svc/sched/sched_engine.py compares them with the PC's). The
// tick is the scenario tick: 0 the room start, then 1, 2, ... (the PC harness's numbering).
struct SchedStep {
    u16 tick;
    u8 slot, st0, st, ran, pad[2];
    u32 sl0, sl, func;
};
enum { STEP_MAX = 4096, TICK_MAX = 1024 };
static SchedStep* step_rec;
static unsigned step_n, cur_tick, tick_ran;
// each tick's scenario step (ScenarioMove and TaskScheduler) in us, and whether a task thread ran in it; lane
// eng-sched3: its split, by stamps around the parts (each stamp one clock read, about 1 us, the boot's "clock read"
// line): R101Main's span, the task steps' spans (TaskSchedulerMain: the switch into the task, its work until it sleeps
// and the switch back) and the stub calls made inside the step
struct TickCost { u16 all, main, task; u8 kind, stubs; };
static TickCost* tick_cost;
static uint64_t task_us;   // this tick's task-step spans
extern "C" unsigned e1_stub_calls;   // core/globals.cpp
extern "C" void __real_TaskSchedulerMain(TASK* t);
extern "C" void __wrap_TaskSchedulerMain(TASK* t)
{
    steps++;
    steps_tick++;
    const u8 st0 = (u8) t->Status;
    const u32 sl0 = (u32) t->SleepCtr;
    // a thread runs in this step: a new task, a running one, or a sleeper whose count ends now (scheduler.cpp
    // TaskSchedulerMain); the event and sub-screen holds are left out (no event holds in the SCHED scene)
    const u8 ran = st0 == TASK_EXEC || st0 == TASK_RUN || (st0 == TASK_SLEEP && sl0 == 1);
    const uint64_t a = e1_clock_us();
    __real_TaskSchedulerMain(t);
    task_us += e1_clock_us() - a;
    tick_ran |= ran;
    if (step_rec && step_n < STEP_MAX) {
        SchedStep& s = step_rec[step_n];
        s.tick = (u16) cur_tick;
        s.slot = (u8) (t - Task);
        s.st0 = st0;
        s.st = (u8) t->Status;
        s.ran = ran;
        s.sl0 = sl0;
        s.sl = (u32) t->SleepCtr;
        s.func = (u32) (uintptr_t) t->pFunc;
    }
    step_n++;
}

static void sched_host_tasks(unsigned tick, uint64_t scen_d);

void sched_host_boot()
{
    os_threads_boot();
    file_t f = fs_open("/cd/SCHED", O_RDONLY);
    if (f >= 0) { fs_close(f); scene = 1; }
    f = fs_open("/cd/SCHEDX", O_RDONLY);
    if (f >= 0) { fs_close(f); ctl_stackx = 1; }
    f = fs_open("/cd/SCHEDD", O_RDONLY);
    if (f >= 0) { fs_close(f); ctl_delay = 1; }
    f = fs_open("/cd/SCHEDN", O_RDONLY);
    if (f >= 0) { fs_close(f); arm_noscript = 1; }
    f = fs_open("/cd/SCHED0", O_RDONLY);
    if (f >= 0) { fs_close(f); arm_noscript = 2; }
    e1_log("E1 SCHED boot: scheduler hosted, %u task slots, stacks in the behaviour arena%s%s%s%s\n", (unsigned) TASK_NUM,
           scene ? "; lab scene SCHED: the village's room script (st1/r101) runs" : "",
           ctl_stackx ? "; SCHEDX: a scenario task's stack guard overwritten at tick 300 (control)" : "",
           ctl_delay ? "; SCHEDD: 200 us added inside the timed scenario step at tick 200 (timing control)" : "",
           arm_noscript == 1 ? "; SCHEDN: no room script, three idle scenario tasks (lab arm: the task switch)"
           : arm_noscript == 2 ? "; SCHED0: no room script, no task (lab arm: the scenario layer alone)" : "");
    // the stamps' own cost (lane eng-sched3): 1,000 clock reads back to back, before play
    const uint64_t c0 = e1_clock_ns();
    volatile uint64_t sink = 0;
    for (int i = 0; i < 1000; i++) sink += e1_clock_us();
    e1_log("E1 SCHED clock read: %lu ns each (1,000 reads, before play)\n", (unsigned long) ((e1_clock_ns() - c0) / 1000));
}

// SCHEDN's idle scenario task: sleeps one tick, every tick (as r101's waiting tasks do, with no work between)
static void sched_idle_task()
{
    for (;;) SceSleep(1);
}

void sched_host_room_init()
{
    if (!scene) return;
    // the step record and the per-tick cost (lab scene only; the behaviour arena, about 85 KB: the KOS heap has no room
    // for it in the village, see sched_stack_alloc)
    step_rec = (SchedStep*) mem_alloc(STEP_MAX * sizeof(SchedStep), "sched_host step record", 0, 1, MEM_HEAP_CURRENT);
    tick_cost = (TickCost*) mem_alloc(TICK_MAX * sizeof(TickCost), "sched_host tick cost", 0, 1, MEM_HEAP_CURRENT);
    if (!step_rec || !tick_cost) e1_log("E1 SCHED record: refused by the behaviour arena\n");
    else e1_log("E1 SCHED record: %u bytes in the behaviour arena (steps %u, ticks %u)\n",
                (unsigned) (STEP_MAX * sizeof(SchedStep) + TICK_MAX * sizeof(TickCost)), (unsigned) (STEP_MAX * sizeof(SchedStep)),
                (unsigned) (TICK_MAX * sizeof(TickCost)));
    cur_tick = 0;
    // the task table and its stack pool (in the behaviour arena), then the scenario system and the room's start
    TaskSchedulerInit();
    ScenarioInit();
    steps_tick = 0;
    ScenarioRoomInit();
    if (arm_noscript == 1)   // SCHEDN: as many scenario tasks as r101 starts, each idle
        for (int i = 0; i < 3; i++) SceExec(0x12, (TaskFunc) sched_idle_task, 0, 0, SCE_PRIO_DEF_2, 0);
    for (unsigned i = 5; i < TASK_NUM; i++) init_tasks += Task[i].Status != 0;
}

void sched_host_scenario(unsigned tick)
{
    if (!scene) return;
    if (ctl_stackx && tick == 300) {   // SCHEDX (control): the first live scenario task's guard word
        for (unsigned i = 5; i < TASK_NUM; i++)
            if (Task[i].Status) { *(u32*) (Task[i].pStack - Task[i].StackSize) = 0; break; }
    }
    cur_tick = ticks_run + 1;
    tick_ran = 0;
    main_us = task_us = 0;
    stubs_at = e1_stub_calls;
    const uint64_t a = e1_clock_us();
    if (ctl_delay && cur_tick == 200)   // SCHEDD (timing control): a known 200 us inside the timed step
        while (e1_clock_us() - a < 200) {}
    ScenarioMove();
    const uint64_t d = e1_clock_us() - a;
    scen_sum += d;
    scen_over += d > 100;
    if (d > scen_max) scen_max = d, scen_max_tick = tick;
    sched_host_tasks(tick, d);
}

static void sched_host_tasks(unsigned tick, uint64_t scen_d)
{
    const uint64_t a = e1_clock_us();
    TaskScheduler();
    const uint64_t d = e1_clock_us() - a;
    sched_sum += d;
    if (d > sched_max) sched_max = d, sched_max_tick = tick;
    if (tick_cost && ticks_run < TICK_MAX) {
        const uint64_t all = scen_d + d;
        const unsigned nst = e1_stub_calls - stubs_at;
        TickCost& c = tick_cost[ticks_run];
        c.all = (u16) (all > 0xFFFF ? 0xFFFF : all);
        c.main = (u16) (main_us > 0xFFFF ? 0xFFFF : main_us);
        c.task = (u16) (task_us > 0xFFFF ? 0xFFFF : task_us);
        c.kind = (u8) tick_ran;
        c.stubs = (u8) (nst > 255 ? 255 : nst);
    }
    ticks_run++;
    if (steps_tick > steps_max) steps_max = steps_tick;
    steps_tick = 0;
}

// mean, p99 (nearest rank) and worst of the scenario step's per-tick cost, over the ticks of one kind; lane eng-sched3:
// of one part of it (field: 0 the whole step, 1 R101Main, 2 the task steps, 3 the rest, 4 the stub calls, a count)
static unsigned cost_field(const TickCost& c, int field)
{
    switch (field) {
    case 1: return c.main;
    case 2: return c.task;
    case 3: return c.all > c.main + c.task ? c.all - c.main - c.task : 0;
    case 4: return c.stubs;
    default: return c.all;
    }
}
static void sched_cost_line(const char* what, int kind, int field = 0)
{
    static u16 v[TICK_MAX];
    unsigned n = 0, worst_tick = 0;
    uint64_t sum = 0;
    const unsigned k = ticks_run < TICK_MAX ? ticks_run : TICK_MAX;
    u16 worst = 0;
    for (unsigned i = 0; i < k; i++) {
        if (kind >= 0 && tick_cost[i].kind != kind) continue;
        const u16 x = (u16) cost_field(tick_cost[i], field);
        v[n++] = x;
        sum += x;
        if (x > worst) worst = x, worst_tick = i + 1;
    }
    for (unsigned i = 1; i < n; i++) {   // insertion sort, after play
        const u16 x = v[i];
        unsigned j = i;
        for (; j && v[j - 1] > x; j--) v[j] = v[j - 1];
        v[j] = x;
    }
    const unsigned r = n ? (99 * n + 99) / 100 : 0;   // nearest rank: ceil(0.99 n)
    e1_log("E1 SCHED cost %s: ticks %u mean %lu us p99 %u us worst %u us (tick %u), over 100 us %u\n", what, n,
           (unsigned long) (n ? sum / n : 0), (unsigned) (n ? v[r - 1] : 0), (unsigned) worst, worst_tick,
           [&] { unsigned c = 0; for (unsigned i = 0; i < n; i++) c += v[i] > 100; return c; }());
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
    if (!scene) return;
    if (tick_cost) {
        sched_cost_line("all", -1);
        sched_cost_line("tasks waiting", 0);
        sched_cost_line("tasks running", 1);
        // lane eng-sched3: the split (stamps around the parts; "rest" is ScenarioMove's own work and TaskScheduler)
        sched_cost_line("split room main (R101Main)", -1, 1);
        sched_cost_line("split task steps (switch and task work)", -1, 2);
        sched_cost_line("split rest (scenario layer)", -1, 3);
        sched_cost_line("split stub calls (a count, not us)", -1, 4);
        unsigned w = 0;
        const unsigned k = ticks_run < TICK_MAX ? ticks_run : TICK_MAX;
        for (unsigned i = 1; i < k; i++)
            if (tick_cost[i].all > tick_cost[w].all) w = i;
        if (k)
            e1_log("E1 SCHED split at the worst tick %u: all %u us, room main %u us, task steps %u us, rest %u us, stub calls "
                   "%u; arm %s\n", w + 1, tick_cost[w].all, tick_cost[w].main, tick_cost[w].task, cost_field(tick_cost[w], 3),
                   tick_cost[w].stubs, arm_noscript == 1 ? "SCHEDN" : arm_noscript == 2 ? "SCHED0" : "SCHED");
    }
    // the stacks' high-water marks, every slot (lane eng-sched2): TaskSchedulerInit paints the pool with 0xB3 once
    // and nothing paints it again, so the untouched words above each slot's guard word give the most the slot used
    // over the whole run, the tasks that ended included
    unsigned pool = 0, used_all = 0, over_half = 0;
    for (unsigned i = 0; i < TASK_NUM; i++) {
        const TASK& t = Task[i];
        if (!t.pStack || !t.StackSize) continue;
        const u32* lo = (const u32*) (t.pStack - t.StackSize);
        const u32* p = lo + 1;
        while ((const u8*) p < t.pStack && *p == 0xB3B3B3B3u) ++p;
        const unsigned untouched = (unsigned) ((const u8*) p - (const u8*) (lo + 1));
        const unsigned used = (unsigned) t.StackSize - 4 - untouched;
        pool += (unsigned) t.StackSize;
        used_all += used;
        e1_log("E1 SCHED stack slot %u: bytes %u used %u (high water) guard %08x\n", i, (unsigned) t.StackSize, used,
               (unsigned) lo[0]);
        if (used * 2 > (unsigned) t.StackSize) {   // lane eng-sched3 (ruling 2): a slot over half its stack is reported
            over_half++;
            e1_log("E1 SCHED stack slot %u OVER HALF: used %u of %u bytes\n", i, used, (unsigned) t.StackSize);
        }
    }
    unsigned want = 0;   // lane eng-sched3: the pool against the engine's table (a fold of the original's sizes shows)
    for (unsigned i = 0; i < TASK_NUM; i++) want += GetStackSize((int) i);
    e1_log("E1 SCHED stacks: pool %u bytes (the engine's GameCube sizes %u: %s), high water summed %u bytes, slots over "
           "half their stack %u\n", pool, want, pool == want ? "same" : "DIFFERS", used_all, over_half);
    // the task steps (E1 SCHEDT: tick:slot:status/sleep>status/sleep:function, hex, eight a line)
    if (step_rec) {
        const unsigned k = step_n < STEP_MAX ? step_n : STEP_MAX;
        char line[400];
        for (unsigned i = 0; i < k; i += 8) {
            int o = snprintf(line, sizeof line, "E1 SCHEDT");
            for (unsigned j = i; j < k && j < i + 8; j++) {
                const SchedStep& s = step_rec[j];
                o += snprintf(line + o, sizeof line - o, " %x:%x:%x/%lx>%x/%lx:%lx", s.tick, s.slot, s.st0,
                              (unsigned long) s.sl0, s.st, (unsigned long) s.sl, (unsigned long) s.func);
            }
            e1_log("%s\n", line);
        }
        e1_log("E1 SCHEDT END steps %u recorded %u\n", step_n, k);
    }
}
#endif
