// game/scheduler: the cooperative task scheduler — 18 task slots (TASK), each an OS thread with
// its own stack, run one after another by the main thread every frame (TaskScheduler ->
// TaskSchedulerMain); a task runs until it calls TaskSleep / TaskExit, which hand control back.
// Slot 0 is the game, 1 debug / sub screen / movie tasks, 4 the background (ISR) task, 5..17 the
// scenario tasks (sce_sys). Task flags decide whether a slot keeps running during events and the
// sub screen. (D:/Bio4/Prog/scheduler.cpp)
#include "types.h"
#include "global.h"
#include "main_mem.h"
#include "db_log.h"
#include "eprintf.h"
#include "os_vi.h"
#include "scheduler.h"

extern "C" {
void OSReport(const char* msg, ...);
BOOL OSDisableInterrupts(void);
BOOL OSRestoreInterrupts(BOOL level);
void GXSetCurrentGXThread(void);
}
void DbMenuRestoreStopFlag();

TASK Task[TASK_NUM];
static OSSemaphore Sema;
TASK* CTASK_MAIN = (TASK*) -1;
TASK* pCTask = CTASK_MAIN;
OSThread* pParentThread;
static int iTask_exec_flg = 0;

#if !defined(__PPC__)
#include "native_io.h"
// KOS may schedule a caller before a newly resumed child has entered its
// hook, or after the child yields for I/O. A counted dispatch/yield handshake
// preserves the source run-until-sleep contract in both orders. A separate
// resume token also prevents a wake being lost before the child starts waiting.
// The interrupt-driven task retains its independent source scheduling path.
static OSSemaphore nativeTaskResume[TASK_NUM];
static OSSemaphore nativeTaskYielded[TASK_NUM];
static TASK* NativeExecutingTask()
{
    OSThread* self = OSGetCurrentThread();
    for (u32 i = 0; i < TASK_NUM; ++i) {
        if (&Task[i].Thread == self) return &Task[i];
    }
    OSPanic(__FILE__, __LINE__, "Task operation outside a game task");
    return NULL;
}
static void NativeYieldTask(TASK* t)
{
    if (t != &Task[TASK_ISR]) OSSignalSemaphore(&nativeTaskYielded[t - Task]);
}
#endif

void TaskKill(TASK* t);

// Boot: gives every task slot its stack (one allocation, filled with 0xB3 for the usage check),
// number and thread queue; the scheduler semaphore starts at 0.
void TaskSchedulerInit()
{
    u32 total = 0;
    u8* stack;
    u32 i;

    for (i = 0; i < TASK_NUM; i++) {
        Task[i].StackSize = GetStackSize(i);
        total += Task[i].StackSize;
    }
#line 48 "D:/Bio4/Prog/scheduler.cpp"
    stack = (u8*) MEM_ALLOC(total, 1, 13);
#if defined(RE4DC_GAME) && !defined(__PPC__)
    OSReport("Native task stacks: slots=%u bytes=%u floor=%u\n", TASK_NUM, total, 0x3000);
#endif
    memset_asm(stack, 0xB3, total);
    for (i = 0; i < TASK_NUM; i++) {
        Task[i].Task_no = i;
        Task[i].Status = 0;
        Task[i].pStack = stack + Task[i].StackSize;
        Task[i].suspend_cnt = 0;
        OSInitThreadQueue(&Task[i].Queue);
        stack = Task[i].pStack;
    }
    OSInitSemaphore(&Sema, 0);
    iTask_exec_flg = 0;
}

// Kills every task (game reset).
void TaskAllClear()
{
    u32 i;

    for (i = 0; i < TASK_NUM; i++) {
        TaskKill(i);
    }
    iTask_exec_flg = 0;
}

// Stack bytes for slot `no`: 0x3000 for slot 2 (the main game task), 0x2000 for 0..4, 0x1800 above.
u32 GetStackSize(int no)
{
#if defined(RE4DC_GAME) && !defined(__PPC__)
    // KOS fs_hnd_open -> fs_normalize_path retains two PATH_MAX=4096
    // arrays at once (8248 bytes including their saved registers). Source
    // 6/8 KiB stacks cannot hold that call chain. Keep the existing owned
    // stack pool; give every native task a 12 KiB floor for callers/IRQs.
    // High-water telemetry, not successful I/O alone, qualifies this floor.
    (void) no;
    return 0x3000;
#else
    if (no == 2) {
        return 0x3000;
    }
    if ((u32) no > 4) {
        return 0x1800;
    }
    return 0x2000;
#endif
}

// Once per frame from the main thread: runs every slot except the ISR one in order (slot 2 first
// restores the debug menu's stop flag); debug_mode 6 prints the stack usage.
#if defined(RE4DC_MODEL_WALK_CHECK) && RE4DC_MODEL_WALK_CHECK
extern "C" void re4dc_ot_check_task(unsigned slot);  // model_asset_bridge.cpp (debug only)
#endif
#if defined(RE4DC_DEAD_STACK_POISON) && RE4DC_DEAD_STACK_POISON
extern "C" void re4dc_poison_task_stack(OSThread*);  // platform/os.cpp (debug only)
#endif
void TaskScheduler()
{
    u32 i;
    TASK* t;

    pParentThread = OSGetCurrentThread();
    for (i = 0, t = Task; i <= TASK_ISR; i++, t++) {
        if (i == TASK_ISR) {
            continue;
        }
        if (i == 2) {
            DbMenuRestoreStopFlag();
        }
        pCTask = t;
        TaskSchedulerMain(t);
#if defined(RE4DC_MODEL_WALK_CHECK) && RE4DC_MODEL_WALK_CHECK
        re4dc_ot_check_task(i);
#endif
    }
    pCTask = CTASK_MAIN;
    if (pG->debug_mode == 6) {
        stackUsedCheck();
    }
}

// Runs one task for this frame: skipped while an event holds non-event tasks (Status_flg[1]
// 0x10000000 vs flag bit1) or the sub screen holds (Status_flg[0] 0x100000 vs bit2); TASK_EXEC
// creates and starts its thread, TASK_SLEEP counts down and wakes it, TASK_RUN resumes it; the
// main thread then waits (semaphore for priority > 0xF tasks) until the task sleeps / exits.
void TaskSchedulerMain(TASK* t)
{
    if ((pG->Status_flg[1] & 0x10000000) && !(t->flag & 2)) {
        return;
    }
    if ((pG->Status_flg[0] & 0x100000) && !(t->flag & 4)) {
        return;
    }
    switch (t->Status) {
    case TASK_EXEC:
#if !defined(__PPC__)
        if (t != &Task[TASK_ISR]) {
            OSInitSemaphore(&nativeTaskResume[t - Task], 0);
            OSInitSemaphore(&nativeTaskYielded[t - Task], 0);
        }
#endif
        OSCreateThread(&t->Thread, t->hook, (void*) t->arg, t->pStack, t->StackSize, t->Priority, 1);
        t->Status = TASK_RUN;
        OSResumeThread(&t->Thread);
        GXSetCurrentGXThread();
        break;
    case TASK_SLEEP:
        t->SleepCtr--;
        if (t->SleepCtr != 0) {
            return;
        }
        t->Status = TASK_RUN;
#if !defined(__PPC__)
        if (t != &Task[TASK_ISR]) OSSignalSemaphore(&nativeTaskResume[t - Task]);
        else
#endif
        OSWakeupThread(&t->Queue);
        GXSetCurrentGXThread();
        break;
    case TASK_RUN:
        OSResumeThread(&t->Thread);
        GXSetCurrentGXThread();
        break;
    default:
        return;
    }
#if defined(__PPC__)
    if (CTASK->Priority > 0xF) {
        OSWaitSemaphore(&Sema);
        GXSetCurrentGXThread();
    }
#else
    if (t != &Task[TASK_ISR]) {
        OSWaitSemaphore(&nativeTaskYielded[t - Task]);
        GXSetCurrentGXThread();
    }
#endif
    StackOverflowCheck(t);
#if defined(RE4DC_DEAD_STACK_POISON) && RE4DC_DEAD_STACK_POISON
    if (t != &Task[TASK_ISR] && (t->Status == TASK_RUN || t->Status == TASK_SLEEP)) re4dc_poison_task_stack(&t->Thread);
#endif
#if defined(RE4DC_MODEL_WALK_CHECK) && RE4DC_MODEL_WALK_CHECK
    // MODEL_WALK_CHECK (debug only): the slot's stack high water. TaskSchedulerInit filled every stack with
    // 0xB3; the untouched words above the guard word are the bytes this slot has never used. A slot that
    // reaches 0 ran into the slot below it (slots are contiguous, slot k-1's stack top is slot k's guard).
    {
        static u32 hwm_free[TASK_NUM];
        static bool hwm_init;
        if (!hwm_init) {
            for (u32 i = 0; i < TASK_NUM; ++i) hwm_free[i] = ~0u;
            hwm_init = true;
        }
        const u32 slot = (u32) (t - Task);
        const u32* p = (const u32*) (t->pStack - t->StackSize);
        const u32 guard = p[0];
        u32 n = 0;
        for (++p; n + 1 < (t->StackSize >> 2) && *p == 0xB3B3B3B3u; ++p) ++n;
        if (n * 4 < hwm_free[slot]) {
            hwm_free[slot] = n * 4;
            if (n * 4 < 0x1000)
                OSReport("MWC stack slot=%u free=%u guard=%08x bottom=%08x frame=%u\n", (unsigned) slot, (unsigned) (n * 4),
                         (unsigned) guard, (unsigned) (t->pStack - t->StackSize), (unsigned) pG->Frame_cnt);
        }
    }
#endif
}

// Debug: prints how much of each task stack has been touched (bytes no longer 0xB3).
void stackUsedCheck()
{
    u32 i;
    int y = 0x24;

    eprintf2(9, 0x10, 0x22, 0x24, 0, 6, "   SIZE REST");
    for (i = 0; i < TASK_NUM; i++) {
        u32* p = (u32*) (Task[i].pStack - Task[i].StackSize);
        u32 n = 1;
        p++;
        while (n < (u32) (Task[i].StackSize >> 2) && *p == 0xB3B3B3B3) {
            n++;
            p++;
        }
        y += 0x10;
        eprintf(0x10, y, 0, 6, "%02d %4x %4x %08x", i, Task[i].StackSize, n * 4, Task[i].pStack - Task[i].StackSize);
    }
}

// Panics when the guard word at the bottom of the task's stack was overwritten.
void StackOverflowCheck(TASK* t)
{
    if (*(u32*) (t->pStack - t->StackSize) != 0xDEADBABE) {
        OSReport("***************************************\n");
        OSReport("Stack overflow in Thread %d !!\n", t->Task_no);
        OSReport("***************************************\n");
        OSPanic("D:/Bio4/Prog/scheduler.cpp", 217, "End of biohazard4");
    }
}

// Thread entry of every task: suspends the scheduler thread, sets the GQR registers for the
// paired-single loads, and calls the task function with its argument.
void* TaskExec_hook(void* value)
{
#if defined(__PPC__)
    if (ParentThread() != NULL) {
        OSSuspendThread(ParentThread());
    }
#else
    TASK* t = NativeExecutingTask();
    if (t == NULL) return NULL;
#endif
#if defined(__PPC__)
    asm("li 3, 4\n"
        "oris 3, 3, 4\n"
        "mtspr 914, 3\n"
        "li 3, 5\n"
        "oris 3, 3, 5\n"
        "mtspr 915, 3\n"
        "li 3, 6\n"
        "oris 3, 3, 6\n"
        "mtspr 916, 3\n"
        "li 3, 7\n"
        "oris 3, 3, 7\n"
        "mtspr 917, 3"
        :
        :
        : "r3");
#endif
    GXSetCurrentGXThread();
#if defined(__PPC__)
    CTASK->pFunc((int) value);
#else
    t->pFunc((int) value);
    // Normal return leaves TASK_RUN for cSceSys's completion/unlink check.
    NativeYieldTask(t);
#endif
    return NULL;
}

// Starts `func(arg)` in slot `prio` (fails with an error when the slot is busy): the thread is
// created on the next scheduler pass; flag 6 (skipped by events and the sub screen), priority 0xF.
TASK* TaskExec(int prio, TaskFunc func, int arg)
{
    TASK* t;

    if (TaskStatus(prio) != 0) {
        pLog->err(0, 0, "TASK DON'T EXEC : level %d", prio);
        return NULL;
    }
    t = &Task[prio];
    t->hook = TaskExec_hook;
    t->pFunc = (void (*)(int)) func;
    t->Status = TASK_EXEC;
    t->arg = arg;
    t->flag = 6;
    t->Priority = 0xF;
    return t;
}

// Called from a task: yields for `frames` frames — the scheduler thread resumes, the task thread
// sleeps on its queue until TaskSchedulerMain wakes it.
void TaskSleep(int frames)
{
#if defined(__PPC__)
    if (frames == 0) {
        return;
    }
    CTASK->SleepCtr = frames;
    CTASK->Status = (CTASK->Status & TASK_SUSPEND) | TASK_SLEEP;
    if (ParentThread() != NULL) {
        OSResumeThread(ParentThread());
    }
    if (CTASK->Priority > 0xF) {
        OSSignalSemaphore(&Sema);
    }
    OSSleepThread(&pCTask->Queue);
    if (ParentThread() != NULL) {
        OSSuspendThread(ParentThread());
    }
    GXSetCurrentGXThread();
#else
    TASK* t = NativeExecutingTask();
    if (t == NULL || frames == 0) return;
    t->SleepCtr = frames;
    t->Status = (t->Status & TASK_SUSPEND) | TASK_SLEEP;
    if (t == &Task[TASK_ISR]) {
        OSSleepThread(&t->Queue);
    } else {
        NativeYieldTask(t);
        OSWaitSemaphore(&nativeTaskResume[t - Task]);
    }
    GXSetCurrentGXThread();
#endif
}

// Called from a task: replaces itself with `func(arg)` in the same slot (started next frame) and
// ends the current thread.
void TaskChain(TaskFunc func, int arg)
{
#if defined(__PPC__)
    CTASK->hook = TaskExec_hook;
    CTASK->pFunc = (void (*)(int)) func;
    CTASK->Status = TASK_EXEC;
    CTASK->arg = arg;
    if (ParentThread() != NULL) {
        OSResumeThread(ParentThread());
    }
    if (CTASK->Priority > 0xF) {
        OSSignalSemaphore(&Sema);
    }
    OSExitThread(&pCTask->Thread);
#else
    TASK* t = NativeExecutingTask();
    if (t == NULL) return;

    t->hook = TaskExec_hook;
    t->pFunc = (void (*)(int)) func;
    t->Status = TASK_EXEC;
    t->arg = arg;
    NativeYieldTask(t);
    OSExitThread(&t->Thread);
#endif
}

// Called from a task: frees the slot and ends the thread (the scheduler thread resumes).
void TaskExit()
{
#if defined(__PPC__)
    TASK* t = pCTask;

    t->Status = TASK_NONE;
    t->suspend_cnt = 0;
    if (ParentThread() != NULL) {
        OSResumeThread(ParentThread());
    }
    if (CTASK->Priority > 0xF) {
        OSSignalSemaphore(&Sema);
    }
    OSExitThread(&pCTask->Thread);
#else
    TASK* t = NativeExecutingTask();
    if (t == NULL) return;
    t->Status = TASK_NONE;
    t->suspend_cnt = 0;
    NativeYieldTask(t);
    OSExitThread(&t->Thread);
#endif
}

// Kills the task in slot `prio`.
void TaskKill(int prio)
{
    TaskKill(&Task[prio]);
}

// Kills a task: a sleeping / suspended thread is cancelled; a running one (the caller itself)
// exits; slot freed.
void TaskKill(TASK* t)
{
    if (t->Status == 0) {
        return;
    }
    switch (t->Status & ~TASK_SUSPEND) {
    case TASK_NONE:
    case TASK_EXEC:
        break;
    case TASK_SLEEP:
        OSCancelThread(&t->Thread);
        break;
    case TASK_RUN:
#if defined(RE4DC_GAME) && !defined(__PPC__)
        // Native disc I/O can yield while this source status is still RUN.
        // Only the actual executing owner may exit itself. A different task
        // must use the cancellation drain before its stack can be destroyed.
        if (OSGetCurrentThread() == &t->Thread) TaskExit();
        else OSCancelThread(&t->Thread);
#else
        if (t->Status & TASK_SUSPEND) {
            OSCancelThread(&t->Thread);
        } else {
            TaskExit();
        }
#endif
        break;
    }
    t->Status = TASK_NONE;
    t->suspend_cnt = 0;
}

// Suspends slot `task` (counted; TASK_SUSPEND bit).
void TaskSuspend(int task)
{
    TASK* t = &Task[task];

    t->suspend_cnt++;
    t->Status |= TASK_SUSPEND;
}

// Undoes one TaskSuspend; the task runs again when the count reaches 0.
void TaskSignal(int task)
{
    TASK* t = &Task[task];

    if (t->suspend_cnt == 0) {
        return;
    }
    t->suspend_cnt--;
    if (t->suspend_cnt != 0) {
        return;
    }
    t->Status &= ~TASK_SUSPEND;
}

// Status of slot `prio` (0 = free).
u8 TaskStatus(int prio)
{
    return Task[prio].Status;
}

// The model a task works on (the current task when t is NULL) — read by the scenario / camera.
void SetTaskModelPtr(void* model, TASK* t)
{
    if (t == NULL) {
        CTASK->pModel = model;
    } else {
        t->pModel = model;
    }
}

// From the main loop after the CPU work of the frame (main.cpp): lets the background task slot
// (TASK_ISR) run in the time left before the vsync, when one is active.
void iTaskScheduler()
{
    BOOL lv = OSDisableInterrupts();

    if (iTask_exec_flg == 1) {
        TASK* t = &Task[TASK_ISR];
        pParentThread = NULL;
        pCTask = t;
        t->Status &= ~TASK_SUSPEND;
        TaskSchedulerMain(t);
        pCTask = CTASK_MAIN;
    }
    OSRestoreInterrupts(lv);
}

// Starts `func` in the interrupt-driven slot (decompression / loading in the background); only
// one at a time. Returns NULL when busy.
TASK* iTaskExec(TaskFunc func)
{
    TASK* t;
    int flg = iTask_exec_flg;

    if (flg == 0) {
        iTask_exec_flg = 1;
        t = TaskExec(TASK_ISR, func, 0);
        t->Priority = flg;
        return t;
    }
    return NULL;
}

// Kills the ISR task.
void iTaskKill()
{
    iTask_exec_flg = 0;
    TaskKill(&Task[TASK_ISR]);
}

// Called from the ISR task: ends it.
void iTaskExit()
{
    iTask_exec_flg = 0;
    TaskExit();
}

// From the VI retrace callback: suspends the background task's thread if it is still running so
// the main thread gets the CPU back for the next frame.
void iTaskSuspend()
{
    if (iTask_exec_flg == 1) {
        TASK* t = &Task[TASK_ISR];
        if (t->Thread.state == 2) {
#if !defined(__PPC__)
            // Native synchronous DVD I/O may yield while holding KOS locks.
            // Parking its owner here can deadlock the frame that resumes it.
            if (re4dc_io_busy(&t->Thread)) return;
#endif
            t->Status |= TASK_SUSPEND;
            OSSuspendThread(&t->Thread);
        }
    }
}

// 1 while an ISR task runs.
int iTaskStatus()
{
    return iTask_exec_flg;
}

#if !defined(__PPC__)
#include "re4dc_platform.h"
// Diagnostics: the task table as the scheduler sees it (platform thread dump).
extern "C" void re4dc_task_dump(void)
{
    re4dc_log("tasks: pCTask %p parent %p itask %d\n", (void*) pCTask, (void*) pParentThread, iTask_exec_flg);
    for (u32 i = 0; i < TASK_NUM; i++) {
        TASK* t = &Task[i];
        if (t->Status == TASK_NONE) continue;
        re4dc_log("  task %lu status %02x sleep %d prio %d thread %p\n", (unsigned long) i, (unsigned) t->Status,
                  (int) t->SleepCtr, (int) t->Priority, (void*) &t->Thread);
    }
}
#if RE4DC_CRASH_SCREEN
// Crash screen (issue #2): one "slot:status/tid" item per busy slot; tid "x" = its thread has finished,
// "-" = none. The slot whose yield (Y) or resume (R) semaphore is `wait` (the main thread's wait object)
// is marked. A task that ended without TaskExit / TaskSleep shows here even though its thread is gone.
#include <stdio.h>
extern "C" int re4dc_os_thread_kstate(const void* thread, int* tid);
extern "C" void re4dc_task_brief(char* out, unsigned size, const void* wait)
{
    unsigned n = 0;
    out[0] = 0;
    for (u32 i = 0; i < TASK_NUM && n + 16 < size; ++i) {
        TASK* t = &Task[i];
        const char* mark = wait == &nativeTaskYielded[i] ? "Y" : wait == &nativeTaskResume[i] ? "R" : "";
        if (t->Status == TASK_NONE && !*mark) continue;
        int tid;
        const int st = re4dc_os_thread_kstate(&t->Thread, &tid);
        if (st < 0) n += snprintf(out + n, size - n, " %lu:%02x/-%s", (unsigned long) i, (unsigned) t->Status, mark);
        else if (st == 0 || st == 5)  // STATE_ZOMBIE / STATE_FINISHED
            n += snprintf(out + n, size - n, " %lu:%02x/x%s", (unsigned long) i, (unsigned) t->Status, mark);
        else n += snprintf(out + n, size - n, " %lu:%02x/%d%s", (unsigned long) i, (unsigned) t->Status, tid, mark);
    }
}
#if RE4DC_CRASH_TASK_DETAIL
// CRASH_TASK_DETAIL (issue 21): the thread of the slot whose yield / resume semaphore is `wait`, or 0.
extern "C" const void* re4dc_task_waited(const void* wait, int* slot)
{
    for (u32 i = 0; i < TASK_NUM; ++i) {
        if (wait == &nativeTaskYielded[i] || wait == &nativeTaskResume[i]) {
            *slot = (int) i;
            return &Task[i].Thread;
        }
    }
    return 0;
}
#endif
#endif
#endif
