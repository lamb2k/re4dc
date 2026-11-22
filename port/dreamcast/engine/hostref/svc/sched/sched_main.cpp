// sched_main.cpp (lane eng-sched1): the PC check's harness. The original scheduler (src/game/scheduler.cpp), the
// scenario layer (src/game/sce_sys.cpp) and the village room script (src/st1/r101.cpp), compiled unchanged, run
// a fixed number of ticks in the original's order (sce_sys ScenarioRoomInit once, then each tick ScenarioMove: the room
// main, the event manager, the scenario tasks; then TaskScheduler's slots 0..3), over one of two OS layers:
//   reference  gc_os.cpp, the GameCube OS rules (strict priorities, run until block) and libgpu.cpp's list (original);
//   native     the engine's lifted layer (engine/core/os_threads.cpp, unchanged) over kos_pc.cpp (KOS's thread calls
//              on the PC), and the engine's list (engine/services/scene/at_list.cpp).
// Everything else the units reach is a generated zero stub (sched_stubs.cpp) whose calls are the run's outcome.
//
// Trace (stdout file given as argv[2]): one line per task step (the scheduler's TaskSchedulerMain, wrapped), one line
// per stub call, the final state. Lab controls (environment, never a default): SCHED_CTL=nowait (TaskSleep returns at
// once), SCHED_CTL=reverse (each new task linked at the tail of its ordering bucket: the tasks run in reverse order).
#include "types.h"
#include "global.h"
#include "main.h"
#include "main_mem.h"
#include "scheduler.h"
#include "sce_sys.h"
#include "room_data.h"
#include "db_log.h"
#include "player.h"
#include "pl_npc.h"
#include "datactrl.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <unistd.h>

extern "C" int printf(const char*, ...);
static FILE* g_out;
static unsigned g_tick;
static int g_ctl;   // 1 nowait, 2 reverse
static unsigned long long g_hash = 1469598103934665603ull;
static void mix(const void* p, unsigned n)
{
    const unsigned char* b = (const unsigned char*) p;
    for (unsigned i = 0; i < n; i++) g_hash = (g_hash ^ b[i]) * 1099511628211ull;
}

// ---- the stubs' calls: the run's outcome (what the script asked of the rest of the game, in order)
extern "C" void sched_os_tick(void);   // a pre-emption point (native layer with SCHED_KOS_JITTER; the reference: none)
extern "C" void host_stub_hit(const char* name)
{
    if (!g_out) return;   // static construction (cSceSys's members), before the run
    sched_os_tick();
    fprintf(g_out, "S %u %s\n", g_tick, name);
    mix(name, strlen(name));
}

// the engine's list (at_list.cpp) reports through the engine's stub counter
// (an engine diagnostic, not a call of the script's: an "E" line, outside the outcome)
extern "C" void e1_stub_hit(const char* name, int arg)
{
    if (g_out) fprintf(g_out, "E %u %s %d\n", g_tick, name, arg);
}

// ---- game state the units read (zeroed storage: the village after the bell, nothing loaded)
alignas(32) static unsigned char g_global[sizeof(GlobalWork)];
alignas(32) static unsigned char g_sys[0x4000];
alignas(32) static unsigned char g_save[0x10000];
alignas(32) static unsigned char g_pl[0x4000];
alignas(32) static unsigned char g_log[64];
GlobalWork* pG = (GlobalWork*) g_global;
SystemWork* pSys = (SystemWork*) g_sys;
cLogPtr pLog = {(cLog*) g_log};
cPlayer* pPL = (cPlayer*) g_pl;
cSubChar* pSUB = 0;
cRoomData RoomData;

// The room table, as far as this check hosts rooms: the village's init and main (roomdata.cpp's table, engine form).
void R101Init();
void R101Main();
void cRoomData::execInitFunc(u16 room) { if (room == 0x101) R101Init(); }
void cRoomData::execMainFunc(u16 room) { if (room == 0x101) R101Main(); }
// The room's save record (flags the script reads and sets: RsfCheck / RsfSet), zeroed: a first visit.
alignas(32) static u8 g_room_save[0x100];
u8* cRoomData::getRoomSavePtr(u16) { return g_room_save; }

void* mem_alloc(u32 size, const char*, int, int, int) { return aligned_alloc(32, (size + 31) & ~31u); }
void* mem_calloc(u32 size, const char*, int, int, int) { return calloc(1, (size + 31) & ~31u); }
extern "C" void memset_asm(void* d, int c, u32 n) { memset(d, c, n); }
extern "C" void memclr_asm(void* d, u32 n) { memset(d, 0, n); }
extern "C" void re4dc_log(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}
extern "C" void re4dc_halt(const char* file, int line)
{
    fprintf(g_out, "HALT %s:%d tick %u\n", file, line, g_tick);
    fflush(g_out);
    _exit(3);
}
extern "C" void OSReport(const char* fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    va_end(ap);
}
extern "C" int re4dc_io_busy(const void*) { return 0; }
extern "C" void GXSetCurrentGXThread(void) {}
extern "C" void GXDrawDone(void) {}
void DbMenuRestoreStopFlag() {}

// The data loader's records (datactrl.cpp, engine form): each named file gets a zeroed unit, never loaded (the room
// script asks for its event data; its size reads 0 and its load never completes).
alignas(32) static unsigned char g_units[32][sizeof(cDataUnit)];
static unsigned g_nunits;
cDataUnit* cDataCtrl::setData(char* name)
{
    host_stub_hit("cDataCtrl::setData(char*)");
    return g_nunits < 32 ? (cDataUnit*) g_units[g_nunits++] : (cDataUnit*) g_units[31];
}

// ---- the OS layer's boot (gc_os.cpp or os_threads.cpp)
extern "C" void sched_os_boot(void);
extern "C" void sched_os_report(char* out, unsigned n);

// ---- the task steps: every TaskSchedulerMain call from the scenario layer and from TaskScheduler
extern "C" void __real_TaskSchedulerMain(TASK* t);
extern "C" void __wrap_TaskSchedulerMain(TASK* t)
{
    const unsigned slot = (unsigned) (t - Task);
    const unsigned st0 = t->Status, sl0 = t->SleepCtr;
    __real_TaskSchedulerMain(t);
    fprintf(g_out, "T %u %u %02x/%u %02x/%u %p\n", g_tick, slot, st0, sl0, (unsigned) t->Status, (unsigned) t->SleepCtr,
            (void*) t->pFunc);
    unsigned v[4] = {slot, st0, (unsigned) t->Status, (unsigned) t->SleepCtr};
    mix(v, sizeof v);
}
extern "C" void __real__Z9TaskSleepi(int frames);
extern "C" void __wrap__Z9TaskSleepi(int frames)
{
    static unsigned spins;
    if (g_ctl == 1) {   // control: the wait returns at once (a task polling on it never hands back)
        if (++spins > 200000) {
            fprintf(g_out, "STUCK tick %u: a task never handed back (TaskSleep returned at once %u times)\n", g_tick, spins);
            fflush(g_out);
            _exit(4);
        }
        return;
    }
    __real__Z9TaskSleepi(frames);
}
// control: a new task at the tail of its bucket (AddPrim adds at the head), so the walk meets the tasks reversed
extern "C" void __real_AddPrim(u32* ot, u32* prim);
extern "C" void __wrap_AddPrim(u32* ot, u32* prim)
{
    if (g_ctl != 2) { __real_AddPrim(ot, prim); return; }
    u32* link = ot;
    while ((*link & 0x80000000u) && *link != 0xFFFFFFFFu) link = (u32*) (*link | 0x80000000u);
    prim[0] = *link;
    *link = (u32) (uintptr_t) prim;
}

int main(int argc, char** argv)
{
    const unsigned ticks = argc > 1 ? (unsigned) atoi(argv[1]) : 600;
    g_out = argc > 2 ? fopen(argv[2], "w") : stdout;
    if (!g_out) return 2;
    setvbuf(g_out, 0, _IOLBF, 0);   // a run that halts or crashes keeps its trace up to there
    const char* ctl = getenv("SCHED_CTL");
    g_ctl = ctl && !strcmp(ctl, "nowait") ? 1 : ctl && !strcmp(ctl, "reverse") ? 2 : 0;
    fprintf(g_out, "# sched_main %s ticks %u control %s\n", SCHED_LAYER, ticks, ctl ? ctl : "none");
    sched_os_boot();
    pG->room_id = 0x101;
    TaskSchedulerInit();
    ScenarioInit();
    g_tick = 0;
    ScenarioRoomInit();
    for (g_tick = 1; g_tick <= ticks; g_tick++) {
        pG->Frame_cnt++;
        ScenarioMove();
        TaskScheduler();
    }
    // final state: the room's flags and the scenario system, the task table
    mix(pG->Room_flg, sizeof(pG->Room_flg));
    mix(g_room_save, sizeof(g_room_save));
    // the scenario system's task records (their links and task pointers are addresses, which differ between the two
    // programs: each record as its slot, running and cancel marks)
    for (unsigned i = 0; i < 13; i++) {
        const ScePrim& p = SceSys.prim[i];
        int v[3] = {p.task ? (int) (p.task - Task) : -1, p.running, p.cancel};
        mix(v, sizeof v);
        fprintf(g_out, "F prim %u task %d running %d cancel %d\n", i, v[0], v[1], v[2]);
    }
    unsigned live = 0;
    for (unsigned i = 0; i < TASK_NUM; i++) {
        unsigned v[3] = {i, Task[i].Status, Task[i].SleepCtr};
        mix(v, sizeof v);
        live += Task[i].Status != 0;
        fprintf(g_out, "F task %u status %02x sleep %u\n", i, (unsigned) Task[i].Status, (unsigned) Task[i].SleepCtr);
    }
    fprintf(g_out, "F live %u room_flg", live);
    for (unsigned i = 0; i < sizeof(pG->Room_flg) / 4; i++) fprintf(g_out, " %08x", (unsigned) pG->Room_flg[i]);
    fprintf(g_out, "\nF room_save");
    for (unsigned i = 0; i < 16; i++) fprintf(g_out, " %02x", g_room_save[i]);
    fprintf(g_out, "\nF hash %016llx\n", g_hash);
    char os[200];
    sched_os_report(os, sizeof os);
    fprintf(g_out, "# os %s\n", os);
    fclose(g_out);
    _exit(0);
}
