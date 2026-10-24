#include "native_motion.h"
#include "native_io.h"
// Dolphin OS interface over KallistiOS: threads, thread queues, semaphores,
// interrupts, time, stopwatches, arena/heaps (heaps are the SDK's own OSAlloc.c
// compiled in platform/sdk), reset, font, console queries.
//
// Threading model. The game's scheduler (src/game/scheduler.cpp) is
// cooperative: one OSThread per task slot, created suspended, resumed by the
// main thread, handing control back with OSSuspendThread(parent) /
// OSResumeThread(parent) / OSSleepThread(queue) / OSSignalSemaphore. KOS is
// preemptive, so the GameCube rules are reproduced with priorities (tasks
// outrank the main thread and run as soon as they are resumed) and by taking
// a suspended thread off the run queue; see the threads section.
#include <kos.h>
#include <malloc.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "re4dc_platform.h"
#include "pc_sampler.h"
#include "include/gc_asset_gate.h"

typedef signed char s8;
typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed long s32;
typedef unsigned long u32;
typedef signed long long s64;
typedef unsigned long long u64;
typedef float f32;
typedef int BOOL;
typedef s64 OSTime;
typedef u32 OSTick;
typedef s32 OSPriority;

struct OSThreadQueue {
    struct OSThread* head;
    struct OSThread* tail;
};

// The SDK's OSThread is 0x318 bytes (an OSContext, then the fields the game's
// headers name: state at 0x2C8, suspend at 0x2CC, priority at 0x2D0 ...). The
// platform keeps its own bookkeeping in the context area, which nothing else
// reads, and maintains `state` / `suspend` for code that inspects them.
struct OSThread {
    kthread_t* kt;            // 0x000
    s32 gateCount;            // 0x004  positive: blocked on the gate until resumed
    void* (*func)(void*);     // 0x008
    void* param;              // 0x00C
    u32 nativeIoDepth;        // 0x010: guarded filesystem scopes
    u8 pad[0x2C8 - 0x14];
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

struct OSSemaphore {
    s32 count;
    OSThreadQueue queue;
};

struct OSStopwatch {
    const char* name;
    u32 hits;
    OSTime total;
    OSTime min;
    OSTime max;
    OSTime last;
    BOOL running;
    u32 _padding;
};

struct OSCalendarTime {
    int sec, min, hour, mday, mon, year, wday, yday, msec, usec;
};

enum { OS_THREAD_STATE_READY = 1, OS_THREAD_STATE_RUNNING = 2, OS_THREAD_STATE_WAITING = 4, OS_THREAD_STATE_MORIBUND = 8 };

static OSThread g_mainThread;
static OSThread* g_threads[32];
static int g_threadCount;
#if RE4DC_GC_ASSET_GATE
// Diagnostic terminal stop only. IRQ-guarded on this single SH4. No new task
// can cross admission after all existing tasks reach known platform waits.
static unsigned gcasset_os_terminal,gcasset_os_creating,gcasset_os_late;
struct GcAssetOsCreation {
    bool live;
    GcAssetOsCreation(){
        const int old=irq_disable();
        live=!gcasset_os_terminal && gcasset_os_creating!=~0U;
        if(live)++gcasset_os_creating;else gcasset_os_late=1;
        irq_restore(old);
    }
    ~GcAssetOsCreation(){
        if(live){const int old=irq_disable();--gcasset_os_creating;irq_restore(old);}
    }
};
#endif


extern "C" {

// ---------------------------------------------------------------- reporting
void OSReport(const char* fmt, ...)
{
    char line[256];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);
    re4dc_log("%s", line);
}

#if RE4DC_VMU_DEBUG_SLOT
extern "C" void re4dc_dbgslot_ring(unsigned kind, unsigned a, unsigned b);
#endif
void OSPanic(const char* file, int line, const char* msg, ...)
{
    va_list ap;
#if RE4DC_VMU_DEBUG_SLOT
    re4dc_dbgslot_ring(4, (unsigned) line, 0);
#endif
    printf("OSPanic %s:%d: ", file, line);
    va_start(ap, msg);
    vprintf(msg, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
    re4dc_set_stage(0xDEAD0001ul);
    irq_disable();
    for (;;) {
    }
}

// ---------------------------------------------------------------- threads
//
// GameCube thread semantics on the (always preemptive) KOS scheduler:
//  * priorities map one to one (both: lower number = higher priority); the
//    main thread is OS_PRIORITY_DEFAULT 16, the game's tasks 15 (a task above
//    15 is waited for on the scheduler semaphore by the game itself);
//  * a suspended thread is off the run queue (KOS STATE_WAIT on g_gate, a
//    marker no genwait queue holds), so it is never picked; resuming puts it
//    back and yields when it outranks the caller, the SDK behaviour that
//    the scheduler relies on (a resumed higher-priority thread runs at once,
//    and the resumer continues only when it blocks or suspends the resumer);
//  * a thread suspended while it sleeps in a queue/semaphore re-checks its
//    count when it wakes and parks itself (checkGate).
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

// The current thread leaves the CPU until its suspend count is zero.

// KOS ages runnable threads: thd_calc_prio halves a thread's priority number
// for every 2^thd_ageing_ms_log2 ms (128 ms at HZ 100) since it was last
// scheduled in, so a thread parked for a while outranks everything the moment
// it becomes ready and the next tick pre-empts the game task mid-frame (the
// task then sleeps on pCTask after the scheduler reset it: the title.dat
// stall). The GameCube rules are strict priorities, so the age of a thread is
// reset whenever it becomes ready and every vblank while it waits its turn.
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

extern "C" void re4dc_threads_freshen(void)
{
    int old = irq_disable();
    freshenReady();
    irq_restore(old);
}

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
#if RE4DC_GC_ASSET_GATE
    if(gcasset_os_terminal && t!=&g_mainThread){
        // A semaphore/queue waiter can wake after the stop snapshot. It must
        // never return from this platform boundary into source game work.
        const int old=irq_disable();
        for(;;)genwait_wait(&gcasset_os_terminal,"gcasset-terminal",0);
        irq_restore(old);
    }
#endif
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

// Task threads end in thd_exit without a join (OSExitThread, or returning
// from the entry), which leaves the KOS thread record allocated in state
// FINISHED: about 1.6 KB of KOS malloc per task run, and the KOS heap has a
// few KB of headroom. The scheduler recreates a slot's OSThread for its next
// task, so the finished record is joined there (a join of a FINISHED thread
// returns at once and frees it). One still running is parked here and
// joined once it has finished.
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

#if RE4DC_GC_ASSET_GATE
// Call from a finished game-frame boundary, after stopping external producers.
// A generic KOS WAIT is not proof: only the exact platform waits whose return
// passes checkGate are accepted. No task is cancelled or parked mid-operation.
extern "C" unsigned re4dc_gcasset_os_frame_boundary(){
    if(irq_inside_int() || !g_mainThread.kt || thd_current!=g_mainThread.kt)return 0;
    const int old=irq_disable();
    const bool ready=!g_mainThread.nativeIoDepth && !re4dc_motion_thread_busy(thd_current);
    irq_restore(old);return ready?1U:0U;
}
extern "C" unsigned re4dc_gcasset_os_quiesce(unsigned* blocked){
    if(!re4dc_gcasset_os_frame_boundary()){if(blocked)*blocked=~0U;return 0;}
    const int old=irq_disable();unsigned mask=0;
    if(gcasset_os_creating || gcasset_os_late)mask=~0U;
    // A reused OSThread slot may still retain its prior KOS record until it
    // finishes. It is no longer in g_threads: never infer its idle state from
    // the replacement record or cancel it to manufacture quiescence.
    for(unsigned i=0;i<g_reapPendingCount;++i)
        if(g_reapPending[i] && g_reapPending[i]->state!=STATE_FINISHED)mask=~0U;
    for(int i=0;i<g_threadCount;++i){
        const OSThread* t=g_threads[i];const kthread_t* kt=t->kt;
        if(!kt || kt==g_mainThread.kt || kt->state==STATE_FINISHED)continue;
        bool waiting=false;
        if(kt->state==STATE_WAIT && kt->wait_obj && !t->nativeIoDepth && !re4dc_motion_thread_busy(kt)){
            waiting=(kt->wait_obj==&g_gate && t->suspend>0) ||
                (gcasset_os_terminal && kt->wait_obj==&gcasset_os_terminal && kt->wait_msg && !strcmp(kt->wait_msg,"gcasset-terminal")) ||
                (kt->wait_msg && !strcmp(kt->wait_msg,"os-queue") && t->queue && kt->wait_obj==t->queue) ||
                (kt->wait_msg && !strcmp(kt->wait_msg,"os-sema"));
        }
        if(!waiting)mask|=1U<<unsigned(i);
    }
    if(!mask)gcasset_os_terminal=1;
    if(blocked)*blocked=mask;
    irq_restore(old);return mask?0U:1U;
}
#endif

extern "C" void re4dc_os_thread_stats(unsigned* registered_threads, unsigned* reaped, unsigned* pending)
{
    int old = irq_disable();
    reapFinished();
    *registered_threads = (unsigned) g_threadCount;
    *reaped = g_reaped;
    *pending = g_reapPendingCount;
    irq_restore(old);
}

int OSCreateThread(OSThread* thread, void* (*func)(void*), void* param, void* stack, u32 stackSize, OSPriority priority, u16 attr)
{
#if RE4DC_GC_ASSET_GATE
    GcAssetOsCreation creation;
    if(!creation.live)return 0;
#endif
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
    re4dc_log("OSCreateThread: tid %d prio %ld stack top %p size %u\n", (int) thread->kt->tid, (long) priority, stack,
              (unsigned) stackSize);
    // One entry per OSThread: slots are recreated for every task run, and
    // threadOf() treats an unregistered thread as the main thread.
    old = irq_disable();
    if (!registered(thread)) {
        if (g_threadCount < 32) {
            g_threads[g_threadCount++] = thread;
        } else {
            irq_restore(old);
            re4dc_missing("OS thread registry full");
        }
    }
    irq_restore(old);
    return 1;
}

s32 OSResumeThread(OSThread* thread)
{
    int old = irq_disable();
    s32 prev = thread->suspend;
#if RE4DC_GC_ASSET_GATE
    if(gcasset_os_terminal){gcasset_os_late=1;irq_restore(old);return prev;}
#endif
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

void* re4dc_io_begin()
{
    int old = irq_disable();
    OSThread* owner = threadOf(thd_current);
    ++owner->nativeIoDepth;
    irq_restore(old);
    return owner;
}

void re4dc_io_end(void* ptr)
{
    int old = irq_disable();
    OSThread* owner = (OSThread*) ptr;
    if (owner != threadOf(thd_current) || owner->nativeIoDepth == 0)
        re4dc_missing("native I/O owner mismatch");
    --owner->nativeIoDepth;
    irq_restore(old);
}

int re4dc_io_busy(const void* ptr)
{
    int old = irq_disable();
    int busy = ((const OSThread*) ptr)->nativeIoDepth != 0;
    irq_restore(old);
    return busy;
}

void OSExitThread(void* val)
{
    OSThread* t = threadOf(thd_current);
    if (t->nativeIoDepth || re4dc_motion_thread_busy(thd_current)) re4dc_missing("thread exit during motion lease");
    t->val = val;
    t->state = OS_THREAD_STATE_MORIBUND;
    thd_exit(val);
}

void OSCancelThread(OSThread* thread)
{
    if (thread->kt != NULL && thread->kt != thd_current) {
        int old = irq_disable();
        // A KOS read can yield inside a source evaluation. Let its bounded
        // native resource scope finish before thd_destroy discards its stack.
        // Hold IRQ exclusion across the final zero-busy check and destruction.
        while (thread->nativeIoDepth || re4dc_motion_thread_busy(thread->kt)) {
            thread->suspend = 0;
            thread->gateCount = 0;
            unpark(thread);
            irq_restore(old);
            thd_pass();
            old = irq_disable();
        }
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

#if RE4DC_CRASH_SCREEN
extern "C" volatile int re4dc_crashtest_block;

// Crash screen (scheduler.cpp re4dc_task_brief): the KOS state of an OSThread's thread, -1 without one;
// *tid its KOS tid.
extern "C" int re4dc_os_thread_kstate(const void* thread, int* tid)
{
    const kthread_t* kt = ((const OSThread*) thread)->kt;
    *tid = kt ? (int) kt->tid : 0;
    return kt ? (int) kt->state : -1;
}
#if RE4DC_CRASH_TASK_DETAIL
// CRASH_TASK_DETAIL: an OSThread's KOS thread (0 without one).
extern "C" void* re4dc_os_thread_kt(const void* thread)
{
    return ((const OSThread*) thread)->kt;
}
#endif
#endif

s32 OSSignalSemaphore(OSSemaphore* sem)
{
#if RE4DC_CRASH_SCREEN
    // crashtest.txt "block" (test discs only): the next game task that signals blocks forever instead,
    // so the main thread hangs in its os-sema wait for that task (the issue #2 shape).
    if (re4dc_crashtest_block == 1 && threadOf(thd_current) != &g_mainThread) {
        re4dc_crashtest_block = 0;
        re4dc_log("CRASH_SCREEN test: task tid %d blocks\n", (int) thd_current->tid);
        semaphore_t never;
        sem_init(&never, 0);
        sem_wait(&never);
    }
    if (re4dc_crashtest_block == 2 && threadOf(thd_current) == &g_mainThread) {
        re4dc_crashtest_block = 0;
        re4dc_log("CRASH_SCREEN test: main tid %d sleeps for 120000 ms\n", (int) thd_current->tid);
        thd_sleep(120000);
    }
#endif
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

// ---------------------------------------------------------------- time
OSTime OSGetTime(void)
{
    // microseconds -> 40.5 MHz ticks
    u64 us = timer_us_gettime64();
    return (OSTime) (us * 81 / 2);
}

OSTick OSGetTick(void)
{
    return (OSTick) OSGetTime();
}

static const int kDaysBeforeMonth[12] = {0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334};

static int isLeap(int y)
{
    return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
}

void OSTicksToCalendarTime(OSTime ticks, OSCalendarTime* td)
{
    // ticks since 2000-01-01 00:00:00
    s64 secs = ticks / RE4DC_TIMER_CLOCK;
    s64 rem = ticks - secs * RE4DC_TIMER_CLOCK;
    td->usec = (int) (rem * 1000000 / RE4DC_TIMER_CLOCK) % 1000;
    td->msec = (int) (rem * 1000 / RE4DC_TIMER_CLOCK);
    s64 days = secs / 86400;
    int sod = (int) (secs - days * 86400);
    td->sec = sod % 60;
    td->min = (sod / 60) % 60;
    td->hour = sod / 3600;
    td->wday = (int) ((days + 6) % 7);  // 2000-01-01 was a Saturday
    int year = 2000;
    for (;;) {
        int len = isLeap(year) ? 366 : 365;
        if (days < len) {
            break;
        }
        days -= len;
        year++;
    }
    td->year = year;
    td->yday = (int) days;
    int mon = 11;
    while (mon > 0 && days < kDaysBeforeMonth[mon] + (mon > 1 && isLeap(year) ? 1 : 0)) {
        mon--;
    }
    td->mon = mon;
    td->mday = (int) days - kDaysBeforeMonth[mon] - (mon > 1 && isLeap(year) ? 1 : 0) + 1;
}

OSTime OSCalendarTimeToTicks(OSCalendarTime* td)
{
    s64 days = 0;
    for (int y = 2000; y < td->year; y++) {
        days += isLeap(y) ? 366 : 365;
    }
    days += kDaysBeforeMonth[td->mon] + (td->mon > 1 && isLeap(td->year) ? 1 : 0) + td->mday - 1;
    s64 secs = days * 86400 + td->hour * 3600 + td->min * 60 + td->sec;
    return secs * RE4DC_TIMER_CLOCK + (s64) td->msec * (RE4DC_TIMER_CLOCK / 1000) + (s64) td->usec * RE4DC_TIMER_CLOCK / 1000000;
}

// ---------------------------------------------------------------- stopwatches
void OSInitStopwatch(OSStopwatch* sw, const char* name)
{
    sw->name = name;
    sw->hits = 0;
    sw->total = 0;
    sw->min = 0x7FFFFFFFFFFFFFFFLL;
    sw->max = 0;
    sw->last = 0;
    sw->running = 0;
}

void OSResetStopwatch(OSStopwatch* sw)
{
    OSInitStopwatch(sw, sw->name);
}

void OSStartStopwatch(OSStopwatch* sw)
{
    if (!sw->running) {
        sw->running = 1;
        sw->last = OSGetTime();
    }
}

void OSStopStopwatch(OSStopwatch* sw)
{
    if (sw->running) {
        OSTime d = OSGetTime() - sw->last;
        sw->total += d;
        sw->hits++;
        if (d < sw->min) sw->min = d;
        if (d > sw->max) sw->max = d;
        sw->running = 0;
    }
}

// ---------------------------------------------------------------- arena
static void* g_arenaLo;
static void* g_arenaHi;

void* OSGetArenaLo(void) { return g_arenaLo; }
void* OSGetArenaHi(void) { return g_arenaHi; }
void OSSetArenaLo(void* lo) { g_arenaLo = lo; }
void OSSetArenaHi(void* hi) { g_arenaHi = hi; }

// ---------------------------------------------------------------- misc OS
#ifndef RE4DC_IO_PROBE
#define RE4DC_IO_PROBE 0
#endif
#if RE4DC_IO_PROBE
extern "C" void re4dc_ioprobe_run(void);
#endif
#if defined(RE4DC_IMAGE_CHECK) && RE4DC_IMAGE_CHECK
#include <dc/biosfont.h>
#include <dc/video.h>
#include <dc/maple.h>
#include <stdio.h>
#include <string.h>
#include <malloc.h>
extern char ic_start[] __asm__("_start");  // the linker symbols by their assembler names
extern char ic_etext[] __asm__("_etext");
extern char ic_edata[] __asm__("_edata");
namespace {
char g_ic_lines[16][80];
int g_ic_n;
void ic_line(const char* s)
{
    if (g_ic_n < 16) {
        strncpy(g_ic_lines[g_ic_n], s, 79);
        g_ic_lines[g_ic_n][79] = 0;
        ++g_ic_n;
    }
    re4dc_log("image check: %s\n", s);
}
void ic_draw()
{
    if (!vram_s) return;
    for (int i = 0; i < g_ic_n; ++i)
        bfont_draw_str(vram_s + (40 + i * 26) * 640 + 24, 640, true, g_ic_lines[i]);
}
unsigned ic_crc(const unsigned char* p, unsigned n)
{
    unsigned c = 0xFFFFFFFFu;
    while (n--) {
        c ^= *p++;
        for (int k = 0; k < 8; ++k) c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
    }
    return ~c;
}
void image_check()
{
    char b[96];
    const unsigned base = (unsigned) (uintptr_t) ic_start, et = (unsigned) (uintptr_t) ic_etext,
                   ed = (unsigned) (uintptr_t) ic_edata;
    snprintf(b, sizeof(b), "IMAGE CHECK code %08x-%08x crc %08x", base, et,
             ic_crc((const unsigned char*) ic_start, et - base));
    ic_line(b);
    int o = snprintf(b, sizeof(b), "maple units:");
    for (int pt = 0; pt < MAPLE_PORT_COUNT; ++pt)
        for (int u = 0; u < MAPLE_UNIT_COUNT; ++u)
            if (maple_state.ports[pt].units[u] && o < (int) sizeof(b) - 14)
                o += snprintf(b + o, sizeof(b) - o, " %c%d=%08x", 'A' + pt, u,
                              (unsigned) (uintptr_t) maple_state.ports[pt].units[u]);
    ic_line(b);
    ic_draw();
    file_t f = fs_open("/cd/1ST_READ.BIN", O_RDONLY);
    if (f < 0) {
        ic_line("1ST_READ.BIN: open failed");
    } else {
        const unsigned kBuf = 32768;
        unsigned char* buf = (unsigned char*) memalign(32, kBuf);
        unsigned pos = 0, bad_code = 0, bad_data = 0, nfirst = 0, first[4] = {0, 0, 0, 0}, fcrc = 0xFFFFFFFFu;
        ssize_t r = 0;
        while (buf && (r = fs_read(f, buf, kBuf)) > 0) {
            for (ssize_t i = 0; i < r; ++i, ++pos) {
                fcrc ^= buf[i];
                for (int k = 0; k < 8; ++k) fcrc = (fcrc >> 1) ^ (0xEDB88320u & (0u - (fcrc & 1u)));
                const unsigned a = base + pos;
                if (a >= ed) continue;
                if (*(const unsigned char*) (uintptr_t) a != buf[i]) {
                    if (a < et) {
                        ++bad_code;
                        if (nfirst < 4) first[nfirst++] = pos;
                    } else {
                        ++bad_data;
                    }
                }
            }
        }
        fs_close(f);
        free(buf);
        snprintf(b, sizeof(b), "file %u bytes crc %08x read %d", pos, ~fcrc, (int) r);
        ic_line(b);
        snprintf(b, sizeof(b), "mismatch code %u data %u", bad_code, bad_data);
        ic_line(b);
        if (nfirst) {
            snprintf(b, sizeof(b), "first code offsets %x %x %x %x", first[0], first[1], first[2], first[3]);
            ic_line(b);
        }
    }
    ic_draw();
    thd_sleep(10000);
}
}  // namespace
#endif
#if defined(RE4DC_KOS_SQUEEZE) && RE4DC_KOS_SQUEEZE
extern "C" void re4dc_kos_squeeze(void);  // below
#endif
#if defined(RE4DC_SH4ZAM_SELFTEST) && RE4DC_SH4ZAM_SELFTEST
extern "C" void re4dc_zam_selftest(void);  // platform/sh4zam_selftest.c (SH4ZAM_SELFTEST=1, test builds only)
#endif
void OSInit(void)
{
    static int done;
    if (done) {
        return;
    }
    done = 1;
    re4dc_fault_init();
    re4dc_set_stage(1);
#if defined(RE4DC_IMAGE_CHECK) && RE4DC_IMAGE_CHECK
    image_check();
#endif
    // KOS threads are always preemptive (thd_set_mode is a no-op in this
    // KOS); the game's cooperative hand-offs work because every game thread
    // blocks in a platform primitive until the scheduler resumes it.
    g_mainThread.kt = thd_current;
    g_mainThread.priority = g_mainThread.base = 16;  // OS_PRIORITY_DEFAULT
    thd_set_prio(thd_current, 16);
    g_mainThread.state = OS_THREAD_STATE_RUNNING;
    re4dc_mem_init();
#if defined(RE4DC_KOS_SQUEEZE) && RE4DC_KOS_SQUEEZE
    re4dc_kos_squeeze();  // KOS_SQUEEZE=1 (Makefile, diagnostic): hold part of what the arena left to KOS
#endif
    g_arenaLo = (void*) re4dc_mem.arena_lo;
    g_arenaHi = (void*) re4dc_mem.arena_hi;
    re4dc_log("OSInit: arena %08lx-%08lx (%lu KB)\n", re4dc_mem.arena_lo, re4dc_mem.arena_hi,
              (re4dc_mem.arena_hi - re4dc_mem.arena_lo) / 1024);
    re4dc_pcs_start();  // PC_SAMPLER=1 only; empty inline otherwise
#if defined(RE4DC_SH4ZAM_SELFTEST) && RE4DC_SH4ZAM_SELFTEST
    re4dc_zam_selftest();  // SH4ZAM_SELFTEST=1: "ZAMTEST" ulp lines, before any game code
#endif
#if RE4DC_IO_PROBE
    re4dc_ioprobe_run();  // no-op unless /cd/dc/ioprobe.txt exists
#endif
}

void OSInitAlarm(void) {}

// Boot diagnostics: where every game thread is parked (saved PC of each KOS
// thread, and the interrupted PC for the running one); called from the
// vblank handler while the boot is being traced.
extern "C" void re4dc_task_dump(void) __attribute__((weak));  // game-side task table (scheduler.cpp)

void re4dc_threads_dump(void)
{
    irq_context_t* cur = irq_get_context();
    if (re4dc_task_dump) re4dc_task_dump();
    re4dc_log("threads: running %s pc=%08lx pr=%08lx\n", thd_current ? thd_current->label : "?",
              cur ? (unsigned long) cur->pc : 0ul, cur ? (unsigned long) cur->pr : 0ul);
    for (int i = 0; i < g_threadCount; i++) {
        OSThread* t = g_threads[i];
        if (t->kt == NULL) {
            continue;
        }
        re4dc_log("  thread %d os %p tid %d kos-state %d wait %s%p os-state %d suspend %ld pc=%08lx pr=%08lx\n", i,
                  (void*) t, (int) t->kt->tid, (int) t->kt->state,
                  t->kt->wait_obj == &g_gate ? "gate " : "", t->kt->wait_obj, (int) t->state, (long) t->suspend,
                  (unsigned long) t->kt->context.pc, (unsigned long) t->kt->context.pr);
        // Return addresses left on the thread's stack (no frame pointers: a
        // scan for text addresses between the saved SP and the stack top).
        if ((t->kt->state == STATE_WAIT || (t->kt == thd_current && cur)) && t->stackBase != NULL) {
            extern char re4dc_etext[] __asm__("_etext");  // the linker's end-of-text symbol
            irq_context_t* context = t->kt == thd_current && cur ? cur : &t->kt->context;
            u32* sp = (u32*) (context->r[15] & ~3u);
            u32* top = (u32*) t->stackBase;
            char line[400];
            int n = 0;
            line[0] = 0;
            for (; sp >= t->stackEnd && sp < top && n < 32; sp++) {
                u32 v = *sp;
                if (v >= 0x8c010000u && v < (u32) re4dc_etext && (v & 1) == 0) {
                    snprintf(line + strlen(line), sizeof(line) - strlen(line), " %08lx", (unsigned long) v);
                    n++;
                }
            }
            re4dc_log("    stack:%s\n", line);
        }
    }
}

// Source TaskSchedulerInit paints the owned stack pool with B3. Report the
// lowest untouched prefix across the slot's lifetime, once per unique slot.
void re4dc_threads_stack_report(void)
{
    for (int i = 0; i < g_threadCount; ++i) {
        OSThread* t = g_threads[i];
        bool seen = false;
        for (int j = 0; j < i; ++j) if (g_threads[j] == t) seen = true;
        if (seen || !t->stackEnd || !t->stackBase) continue;
        const u32* p = t->stackEnd + 1;
        while ((const u8*)p < t->stackBase && *p == 0xB3B3B3B3) ++p;
        re4dc_log("native stack: slot=%p bytes=%lu untouched=%lu guard=%08lx\n", t,
                  (u32)(t->stackBase - (u8*)t->stackEnd), (u32)((u8*)p - (u8*)t->stackEnd),
                  *t->stackEnd);
    }
}

u32 OSGetConsoleType(void)
{
    return 0x00000003;  // retail-class console: no dev mode (bits 0xF0000000 clear)
}

u32 OSGetConsoleSimulatedMemSize(void)
{
    return 0x01800000;  // the game divides its FST size out of a 24 MB figure
}

u32 OSGetResetButtonState(void) { return 0; }
u32 OSGetProgressiveMode(void) { return 0; }
void OSSetProgressiveMode(u32 on) { (void) on; }
static u32 g_soundMode = 1;
u32 OSGetSoundMode(void) { return g_soundMode; }
void OSSetSoundMode(u32 mode) { g_soundMode = mode; }
void OSSetSaveRegion(void* start, void* end) { (void) start; (void) end; }

typedef void (*OSErrorHandler)(u16 error, void* context, ...);
OSErrorHandler OSSetErrorHandler(u16 error, OSErrorHandler handler)
{
    (void) error; (void) handler;
    return NULL;
}

void OSResetSystem(int reset, u32 resetCode, BOOL forceMenu)
{
    re4dc_log("OSResetSystem(%d, %lx, %d)\n", reset, resetCode, forceMenu);
    arch_exit();
}

// Fonts: the ROM font is not available; the game falls back to its own text.
int OSInitFont(void* fontData) { (void) fontData; return 0; }
u16 OSGetFontEncode(void) { return 0; }
char* OSGetFontTexture(const char* string, void** image, s32* x, s32* y, s32* width)
{
    *image = NULL; *x = 0; *y = 0; *width = 0;
    return (char*) string + (*string ? 1 : 0);
}

// Known RELs use compiled native entry points; unknown IDs fail explicitly.
// A fresh link restores the module's pristine .data and zeroes its .bss
// (platform/modules.cpp); a relink after OSUnlink keeps them. The source's
// separate bss buffer is unused by the resident modules.
extern "C" int re4dc_module_bind(void* header);
extern "C" int re4dc_module_unbind(void* header);

BOOL OSLink(void* module, void* bss)
{
    (void) bss;
    return re4dc_module_bind(module);
}

BOOL OSUnlink(void* module)
{
    return re4dc_module_unbind(module);
}

// Room-lifecycle audit (game/ui_bridge.cpp): KOS malloc headroom is free
// chunks plus what sbrk may still take below the kernel stack (mm_sbrk's
// limit); the source arena memalign leaves only a few KB of it.
void re4dc_kos_heap_state(unsigned* free_chunks, unsigned* used, unsigned* break_room)
{
    const struct mallinfo mi = mallinfo();
    const uintptr_t brk = (uintptr_t) sbrk(0);
    const uintptr_t limit = _arch_mem_top - THD_KERNEL_STACK_SIZE;
    *free_chunks = (unsigned) mi.fordblks;
    *used = (unsigned) mi.uordblks;
    *break_room = brk < limit ? (unsigned) (limit - brk) : 0;
}

unsigned re4dc_vram_free(void)
{
    return (unsigned) pvr_mem_available();
}

#if defined(RE4DC_KOS_SQUEEZE) && RE4DC_KOS_SQUEEZE
// KOS_SQUEEZE=1 (Makefile; diagnostic, test builds only): hold part of the KOS heap for the whole run.
static void* g_squeeze[64];
int re4dc_fixture_read(const char* path, char* buffer, unsigned size);  // below
void re4dc_kos_squeeze(void)
{
    unsigned bytes = RE4DC_KOS_SQUEEZE_BYTES, frag = RE4DC_KOS_SQUEEZE_FRAG;
    static char text[2048];
    const int n = re4dc_fixture_read("/cd/dc/warp.txt", text, sizeof(text) - 1);
    if (n > 0) {
        text[n] = 0;
        for (char* line = text; line && *line;) {
            char* next = strchr(line, '\n');
            if (next) *next++ = 0;
            if (!strncmp(line, "squeeze ", 8)) {
                unsigned b = 0, f = 0;
                const int got = sscanf(line + 8, "%u %u", &b, &f);
                if (got >= 1) { bytes = b; frag = got >= 2 ? f : 0; }
            }
            line = next;
        }
    }
    unsigned f0 = 0, u0 = 0, b0 = 0, f1 = 0, u1 = 0, b1 = 0, pieces = 0, held = 0;
    re4dc_kos_heap_state(&f0, &u0, &b0);
    if (bytes && !frag) {
        if ((g_squeeze[0] = malloc(bytes)) != nullptr) { held = bytes; pieces = 1; }
    } else if (bytes) {
        void* gap[64] = {};
        const unsigned want = bytes / 4096 < 64 ? bytes / 4096 : 64;
        for (unsigned i = 0; i < want; ++i) {
            if (!(g_squeeze[i] = malloc(4096))) break;
            held += 4096; ++pieces;
            gap[i] = malloc(4096);
        }
        for (unsigned i = 0; i < want; ++i) free(gap[i]);
    }
    for (unsigned i = 0; i < pieces; ++i) memset(g_squeeze[i], 0x5a, frag ? 4096 : held);  // really in use
    re4dc_kos_heap_state(&f1, &u1, &b1);
    re4dc_log("kos squeeze: held=%u requested=%u frag=%u pieces=%u headroom %u -> %u (free %u -> %u, break %u -> %u)\n",
              held, bytes, frag, pieces, f0 + b0, f1 + b1, f0, f1, b0, b1);
}
#endif

// Optional disc fixture (test-only inputs such as /cd/dc/roomcycle.txt);
// bytes read, or -1 when the file is absent.
int re4dc_fixture_read(const char* path, char* buffer, unsigned size)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) {
        return -1;
    }
    const ssize_t n = fs_read(f, buffer, size);
    fs_close(f);
    return (int) n;
}

// DBIsDebuggerPresent: the hang detector halts after 3600 idle vsyncs when no
// debugger is attached; keep it armed like retail.
BOOL DBIsDebuggerPresent(void) { return 0; }

#if defined(RE4DC_DEAD_STACK_POISON) && RE4DC_DEAD_STACK_POISON
// DEAD_STACK_POISON=1 (mcheck.mk; debug only): 0xA5 below a blocked task thread's saved stack pointer (its dead
// stack) down to its guard word. Called by the main thread while the task waits on its resume semaphore.
void re4dc_poison_task_stack(OSThread* thread)
{
    if (thread == NULL || thread->kt == NULL || thread->kt == thd_current) return;
    kthread_t* const k = thread->kt;
    const unsigned lo = (unsigned) (uintptr_t) k->stack, sp = k->context.r[15];
    if (!lo || sp < lo + 64 || sp > lo + k->stack_size) return;
    for (volatile unsigned* w = (volatile unsigned*) (lo + 16); w < (volatile unsigned*) ((sp - 32) & ~3U); ++w)
        *w = 0xA5A5A5A5U;
}
// The calling thread's own dead stack: `bytes` below 256 bytes under this frame (bounded by its stack when KOS
// knows it). No calls while filling.
void __attribute__((noinline)) re4dc_poison_own_stack(unsigned bytes)
{
    volatile unsigned probe = 0;
    const unsigned sp = (unsigned) (uintptr_t) &probe, hi = (sp - 256) & ~3U;
    const unsigned lo = (unsigned) (uintptr_t) thd_current->stack;
    unsigned from = hi - bytes;
    if (lo && from < lo + 16) from = lo + 16;
    if (from >= hi) return;
    for (volatile unsigned* w = (volatile unsigned*) from; w < (volatile unsigned*) hi; ++w) *w = 0xA5A5A5A5U;
}
#endif

}  // extern "C"
