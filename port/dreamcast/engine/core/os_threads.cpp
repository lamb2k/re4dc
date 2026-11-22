// The engine's OS thread layer (lane eng-sched1, plan 3.3 section 8 B2; SALVAGE_20261121.md row 6).
//
// LIFTED from the old port: port/dreamcast/game/platform/os.cpp, release line t15/int at a5aca9cf9 (the file's last
// change 3db050b06, 2026-10-15), the form every Test 27.x release shipped: its threads section (OSThread create,
// resume, suspend, exit, cancel; thread queues; semaphores) and its interrupt calls, with OSPanic. Kept as it was: the
// GameCube rules on the always-preemptive KOS scheduler (created suspended, parked off the run queue, a resumed thread
// that outranks the caller runs at once), the ageing reset (freshen), the reaping of finished KOS thread records.
//
// Left behind (H-032 "lift what works, adapt only what the new architecture needs"):
//   - the arena, heaps, time and stopwatches, calendar, reset, font, console queries, module link, KOS squeeze,
//     image check, fixture reads (not the thread layer; the engine owns memory, loading and the clock);
//   - native_motion and native_io: the I/O ownership depth (re4dc_io_begin / end / busy) and the motion lease checks in
//     OSExitThread and OSCancelThread. The engine opens and reads no file inside a picture (core/play_files.c counts
//     it), so no task can be inside a disc call when it is cancelled or parked; host/sched_host.cpp answers the
//     scheduler's one question (re4dc_io_busy) with 0;
//   - the crash screen's hooks and the crash tests (RE4DC_CRASH_SCREEN; plan B4 lifts the crash screen as its own lane),
//     the thread dump, the debug poisoning (RE4DC_DEAD_STACK_POISON) and the VMU debug ring;
//   - OSReport (the engine's: core/globals.cpp) and the per-creation log line (no serial printing inside a picture).
// Adapted: OSInit is os_threads_boot, which records the engine's main thread without changing its KOS priority (the old
// port set it to 16): the tasks (priorities 14 and 15) then never pre-empt the engine's main loop, and run only while
// it waits in the scheduler's hand-off (scheduler.cpp: the yield / resume semaphores). OSPanic halts through the
// engine's re4dc_halt. The stack report (old re4dc_threads_stack_report) returns its numbers (os_threads_stacks).
// The old file has no alarms (OSInitAlarm was empty) and none are added: the hosted scheduler uses none.
#include <kos.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "os_threads.h"

typedef signed long s32;
typedef unsigned long u32;
typedef unsigned short u16;
typedef unsigned char u8;
typedef int BOOL;
typedef s32 OSPriority;

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" void re4dc_halt(const char* file, int line);
// The engine's log buffers the lines written during play (core/globals.cpp); a panic prints them first, so the reason
// reaches the serial line before the halt. Weak: the PC check has no such buffer.
extern "C" void e1_log_flush(void) __attribute__((weak));

struct OSThreadQueue {
    struct OSThread* head;
    struct OSThread* tail;
};

// The SDK's OSThread is 0x318 bytes (an OSContext, then the fields the game's headers name: state at 0x2C8, suspend
// at 0x2CC, priority at 0x2D0 ...). The layer keeps its own bookkeeping in the context area, which nothing else reads,
// and maintains `state` / `suspend` for code that inspects them (scheduler.cpp iTaskSuspend reads state).
struct OSThread {
    kthread_t* kt;            // 0x000
    s32 gateCount;            // 0x004  positive: blocked on the gate until resumed
    void* (*func)(void*);     // 0x008
    void* param;              // 0x00C
    u8 pad[0x2C8 - 0x10];
    u16 state;                // 0x2C8
    u16 attr;                 // 0x2CA
    s32 suspend;              // 0x2CC
    OSPriority priority;      // 0x2D0
    OSPriority base;          // 0x2D4
    void* val;                // 0x2D8
    OSThreadQueue* queue;     // 0x2DC
    u8 pad2[0x304 - 0x2E0];
    u8* stackBase;            // 0x304
    u32* stackEnd;            // 0x308
    s32 error;                // 0x30C
    void* specific[2];        // 0x310
};
static_assert(sizeof(OSThread) == 0x318, "OSThread is the SDK's 0x318 bytes");

struct OSSemaphore {
    s32 count;
    OSThreadQueue queue;
};

enum { OS_THREAD_STATE_READY = 1, OS_THREAD_STATE_RUNNING = 2, OS_THREAD_STATE_WAITING = 4, OS_THREAD_STATE_MORIBUND = 8 };

static OSThread g_mainThread;
static OSThread* g_threads[32];
static int g_threadCount;
static unsigned g_created;

extern "C" {

void OSPanic(const char* file, int line, const char* msg, ...)
{
    char text[160];
    va_list ap;
    va_start(ap, msg);
    vsnprintf(text, sizeof(text), msg, ap);
    va_end(ap);
    re4dc_log("OSPanic %s:%d: %s\n", file, line, text);
    if (e1_log_flush) e1_log_flush();
    re4dc_halt(file, line);
}

// ---------------------------------------------------------------- threads
//
// GameCube thread semantics on the (always preemptive) KOS scheduler:
//  * priorities map one to one (both: lower number = higher priority); the game's tasks are 14 and 15;
//  * a suspended thread is off the run queue (KOS STATE_WAIT on g_gate, a marker no genwait queue holds), so it is
//    never picked; resuming puts it back and yields when it outranks the caller, the SDK behaviour that the scheduler
//    relies on (a resumed higher-priority thread runs at once, and the resumer continues only when it blocks or
//    suspends the resumer);
//  * a thread suspended while it sleeps in a queue/semaphore re-checks its count when it wakes and parks itself
//    (checkGate).
static int g_gate;

static OSThread* threadOf(kthread_t* kt)
{
    for (int i = 0; i < g_threadCount; i++) {
        if (g_threads[i]->kt == kt) {
            return g_threads[i];
        }
    }
    return &g_mainThread;
}

// KOS ages runnable threads: thd_calc_prio halves a thread's priority number for every 2^thd_ageing_ms_log2 ms since
// it was last scheduled in, so a thread parked for a while outranks everything the moment it becomes ready. The
// GameCube rules are strict priorities, so the age of a thread is reset whenever it becomes ready.
static void freshen(kthread_t* kt)
{
    if (kt != NULL) {
        kt->cpu_time.scheduled = timer_ms_gettime64();
    }
}

static void freshenReady(void)
{
    for (int i = 0; i < g_threadCount; i++) {
        kthread_t* kt = g_threads[i]->kt;
        if (kt != NULL && kt->state == STATE_READY) {
            freshen(kt);
        }
    }
    if (g_mainThread.kt != NULL && g_mainThread.kt->state == STATE_READY) {
        freshen(g_mainThread.kt);
    }
}

// The current thread leaves the CPU until its suspend count is zero.
static void parkSelf(OSThread* t)
{
    int old = irq_disable();
    while (t->suspend > 0) {
        kthread_t* me = thd_current;
        t->state = OS_THREAD_STATE_WAITING;
        me->state = STATE_WAIT;
        me->wait_obj = &g_gate;
        me->wait_msg = "os-suspend";
        thd_block_now(&me->context);
    }
    t->state = OS_THREAD_STATE_RUNNING;
    irq_restore(old);
}

// Takes another thread off the run queue (interrupts disabled by the caller).
static void parkOther(OSThread* t)
{
    kthread_t* kt = t->kt;
    if (kt == NULL) {
        return;
    }
    if (kt->state == STATE_READY) {
        thd_remove_from_runnable(kt);
        kt->state = STATE_WAIT;
        kt->wait_obj = &g_gate;
        kt->wait_msg = "os-suspend";
        t->state = OS_THREAD_STATE_WAITING;
    } else if (kt->state == STATE_RUNNING) {
        // Only from an interrupt that pre-empted kt: it leaves the CPU now.
        kt->state = STATE_WAIT;
        kt->wait_obj = &g_gate;
        kt->wait_msg = "os-suspend";
        t->state = OS_THREAD_STATE_WAITING;
        thd_schedule(false);
    }
    // STATE_WAIT inside a genwait: checkGate parks it when it wakes.
}

// Puts a parked thread back; returns 1 when the caller should yield to it.
static int unpark(OSThread* t)
{
    kthread_t* kt = t->kt;
    if (kt == NULL || !(kt->state == STATE_WAIT && kt->wait_obj == &g_gate)) {
        return 0;
    }
    kt->wait_obj = NULL;
    kt->wait_msg = NULL;
    kt->state = STATE_READY;
    freshen(kt);
    thd_add_to_runnable(kt, false);
    t->state = OS_THREAD_STATE_READY;
    if (irq_inside_int()) {
        thd_schedule(true);  // pre-empts the interrupted thread if kt outranks it
        return 0;
    }
    return kt->prio < thd_current->prio;
}

static void checkGate(OSThread* t)
{
    if (t->suspend > 0) {
        parkSelf(t);
    }
    t->state = OS_THREAD_STATE_RUNNING;
}

static void* threadEntry(void* p)
{
    OSThread* t = (OSThread*) p;
    t->state = OS_THREAD_STATE_RUNNING;
    void* r = t->func(t->param);
    t->state = OS_THREAD_STATE_MORIBUND;
    return r;
}

// Task threads end in thd_exit without a join (OSExitThread, or returning from the entry), which leaves the KOS thread
// record allocated in state FINISHED (about 1.6 KB of KOS malloc per task run). The scheduler recreates a slot's
// OSThread for its next task, so the finished record is joined there (a join of a FINISHED thread returns at once and
// frees it). One still running is parked here and joined once it has finished.
static kthread_t* g_reapPending[32];
static unsigned g_reapPendingCount, g_reaped;

static void reapFinished(void)
{
    if (irq_inside_int()) {
        return;
    }
    for (unsigned i = 0; i < g_reapPendingCount;) {
        kthread_t* kt = g_reapPending[i];
        if (kt->state == STATE_FINISHED) {
            thd_join(kt, NULL);
            g_reaped++;
            g_reapPending[i] = g_reapPending[--g_reapPendingCount];
        } else {
            i++;
        }
    }
}

static bool registered(const OSThread* thread)
{
    for (int i = 0; i < g_threadCount; i++) {
        if (g_threads[i] == thread) {
            return true;
        }
    }
    return false;
}

int OSCreateThread(OSThread* thread, void* (*func)(void*), void* param, void* stack, u32 stackSize, OSPriority priority, u16 attr)
{
    {
        // Only a registered OSThread's kt is a record this layer created.
        int old = irq_disable();
        const bool known = registered(thread);
        kthread_t* previous = known ? thread->kt : NULL;
        if (previous != NULL && previous != thd_current && previous != g_mainThread.kt) {
            if (g_reapPendingCount < sizeof(g_reapPending) / sizeof(g_reapPending[0])) {
                g_reapPending[g_reapPendingCount++] = previous;
            } else {
                re4dc_log("OSCreateThread: reap list full; KOS thread record %p leaks\n", (void*) previous);
            }
        }
        reapFinished();
        irq_restore(old);
    }
    memset(thread, 0, sizeof(*thread));
    thread->func = func;
    thread->param = param;
    thread->priority = priority;
    thread->base = priority;
    thread->attr = attr;
    thread->suspend = 1;
    thread->gateCount = 1;
    thread->state = OS_THREAD_STATE_READY;
    thread->stackBase = (u8*) stack;                       // the SDK takes the stack top
    thread->stackEnd = (u32*) ((u8*) stack - stackSize);
    *thread->stackEnd = 0xDEADBABE;  // OS_THREAD_STACK_MAGIC: scheduler.cpp StackOverflowCheck reads it
    kthread_attr_t a;
    memset(&a, 0, sizeof(a));
    a.stack_size = stackSize;
    a.stack_ptr = (u8*) stack - stackSize;
    a.prio = priority > 0 ? priority : 1;
    a.label = "re4-task";
    a.disable_tls = true;
    int old = irq_disable();
    thread->kt = thd_create_ex(&a, threadEntry, thread);
    if (thread->kt != NULL) {
        parkOther(thread);  // created suspended
    }
    irq_restore(old);
    if (thread->kt == NULL) {
        re4dc_log("OSCreateThread: thd_create_ex failed (stack %u)\n", (unsigned) stackSize);
        return 0;
    }
    g_created++;
    // One entry per OSThread: slots are recreated for every task run, and threadOf() treats an unregistered thread as
    // the main thread.
    old = irq_disable();
    if (!registered(thread)) {
        if (g_threadCount < 32) {
            g_threads[g_threadCount++] = thread;
        } else {
            irq_restore(old);
            OSPanic(__FILE__, __LINE__, "OS thread registry full");
        }
    }
    irq_restore(old);
    return 1;
}

s32 OSResumeThread(OSThread* thread)
{
    int old = irq_disable();
    s32 prev = thread->suspend;
    int yield = 0;
    if (thread->suspend > 0) {
        thread->suspend--;
        thread->gateCount = thread->suspend;
        if (thread->suspend == 0) {
            yield = unpark(thread);
        }
    }
    irq_restore(old);
    if (yield) {
        thd_pass();
    }
    return prev;
}

s32 OSSuspendThread(OSThread* thread)
{
    int old = irq_disable();
    s32 prev = thread->suspend;
    thread->suspend++;
    thread->gateCount = thread->suspend;
    if (thread->kt == thd_current && !irq_inside_int()) {
        irq_restore(old);
        parkSelf(thread);
    } else {
        parkOther(thread);
        irq_restore(old);
    }
    return prev;
}

OSThread* OSGetCurrentThread(void)
{
    return threadOf(thd_current);
}

void OSExitThread(void* val)
{
    OSThread* t = threadOf(thd_current);
    t->val = val;
    t->state = OS_THREAD_STATE_MORIBUND;
    thd_exit(val);
}

void OSCancelThread(OSThread* thread)
{
    if (thread->kt != NULL && thread->kt != thd_current) {
        int old = irq_disable();
        if (thread->kt->state == STATE_WAIT && thread->kt->wait_obj == &g_gate) {
            thread->kt->wait_obj = NULL;
            thread->kt->state = STATE_READY;
            thd_add_to_runnable(thread->kt, false);
        }
        thd_destroy(thread->kt);
        thread->kt = NULL;
        irq_restore(old);
    }
    thread->state = OS_THREAD_STATE_MORIBUND;
}

OSPriority OSGetThreadPriority(OSThread* thread)
{
    return thread->priority;
}

BOOL OSSetThreadPriority(OSThread* thread, OSPriority priority)
{
    thread->priority = priority;
    thread->base = priority;
    if (thread->kt != NULL) {
        thd_set_prio(thread->kt, priority > 0 ? priority : 1);
    }
    return 1;
}

void OSInitThreadQueue(OSThreadQueue* queue)
{
    queue->head = queue->tail = NULL;
}

void OSSleepThread(OSThreadQueue* queue)
{
    OSThread* t = threadOf(thd_current);
    t->queue = queue;
    t->state = OS_THREAD_STATE_WAITING;
    genwait_wait(queue, "os-queue", 0);
    t->queue = NULL;
    checkGate(t);
}

// After a wake: a woken thread that outranks the caller runs at once.
static void afterWake(void)
{
    if (irq_inside_int()) {
        thd_schedule(true);
    } else {
        thd_pass();
    }
}

void OSWakeupThread(OSThreadQueue* queue)
{
    int old = irq_disable();
    genwait_wake_all(queue);
    freshenReady();
    irq_restore(old);
    afterWake();
}

s32 OSEnableScheduler(void)
{
    return 0;
}

// ---------------------------------------------------------------- semaphores
void OSInitSemaphore(OSSemaphore* sem, s32 count)
{
    sem->count = count;
    sem->queue.head = sem->queue.tail = NULL;
}

s32 OSWaitSemaphore(OSSemaphore* sem)
{
    OSThread* t = threadOf(thd_current);
    int old = irq_disable();
    while (sem->count <= 0) {
        t->state = OS_THREAD_STATE_WAITING;
        genwait_wait(sem, "os-sema", 0);
    }
    s32 c = sem->count--;
    irq_restore(old);
    checkGate(t);
    return c;
}

s32 OSSignalSemaphore(OSSemaphore* sem)
{
    int old = irq_disable();
    s32 c = sem->count++;
    genwait_wake_one(sem);
    irq_restore(old);
    afterWake();
    return c;
}

// ---------------------------------------------------------------- interrupts
BOOL OSDisableInterrupts(void)
{
    return (BOOL) irq_disable();
}

BOOL OSEnableInterrupts(void)
{
    BOOL was = (BOOL) irq_disable();
    irq_enable();
    return was;
}

BOOL OSRestoreInterrupts(BOOL level)
{
    irq_restore((irq_mask_t) level);
    return level;
}

// ---------------------------------------------------------------- the engine's side
void os_threads_boot(void)
{
    g_mainThread.kt = thd_current;
    g_mainThread.priority = g_mainThread.base = thd_current->prio;
    g_mainThread.state = OS_THREAD_STATE_RUNNING;
}

void os_threads_stats(unsigned* created, unsigned* reaped, unsigned* pending)
{
    int old = irq_disable();
    reapFinished();
    *created = g_created;
    *reaped = g_reaped;
    *pending = g_reapPendingCount;
    irq_restore(old);
}

// The scheduler (TaskSchedulerInit) paints the owned stack pool with B3: the untouched words above the guard word are
// the bytes a slot has never used, over the slot's lifetime.
unsigned os_threads_stacks(struct OsStackMark* out, unsigned max)
{
    unsigned n = 0;
    for (int i = 0; i < g_threadCount && n < max; ++i) {
        OSThread* t = g_threads[i];
        if (!t->stackEnd || !t->stackBase) continue;
        const u32* p = t->stackEnd + 1;
        while ((const u8*) p < t->stackBase && *p == 0xB3B3B3B3) ++p;
        out[n].thread = t;
        out[n].bytes = (unsigned) (t->stackBase - (u8*) t->stackEnd);
        out[n].untouched = (unsigned) ((const u8*) p - (const u8*) (t->stackEnd + 1));
        out[n].guard = (unsigned) *t->stackEnd;
        ++n;
    }
    return n;
}

}  // extern "C"
