// gc_os.cpp (lane eng-sched1): the reference OS layer of the PC check: the GameCube OS thread rules the original
// scheduler was written for, on PC contexts (ucontext), one thread on the CPU at a time:
//   - strict priorities (lower number first); the running thread keeps the CPU until it blocks, suspends itself or
//     makes a higher-priority thread ready (no time slicing); the main thread is the SDK's default priority 16;
//   - a thread is created suspended; OSResumeThread to suspend count 0 makes it ready, and it runs at once when it
//     outranks the caller; OSSuspendThread takes it off the CPU or the ready list;
//   - OSSleepThread waits on a queue, OSWakeupThread readies every thread on it; a semaphore is a count and a queue
//     (wait: sleep while the count is not positive, then take one; signal: add one and wake the queue);
//   - OSExitThread ends the caller, OSCancelThread ends another.
// It is the SDK's documented behaviour, written for this check; it shares no code with the engine's layer.
#include <ucontext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef int32_t s32;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
typedef int BOOL;

extern "C" void re4dc_halt(const char* file, int line);
extern "C" void re4dc_log(const char* fmt, ...);

struct OSThreadQueue { struct OSThread* head; struct OSThread* tail; };
struct Ctx;
struct OSThread {
    Ctx* ctx;             // 0x000: this model's record in the context area
    u8 pad[0x2C8 - 4];
    u16 state;            // 0x2C8
    u16 attr;
    s32 suspend;          // 0x2CC
    s32 priority;         // 0x2D0
    s32 base;
    void* val;
    OSThreadQueue* queue; // 0x2DC
    u8 pad2[0x304 - 0x2E0];
    u8* stackBase;        // 0x304
    u32* stackEnd;        // 0x308
    s32 error;
    void* specific[2];
};
static_assert(sizeof(OSThread) == 0x318, "OSThread size");
struct OSSemaphore { s32 count; OSThreadQueue queue; };

enum { READY = 1, RUNNING = 2, WAITING = 4, MORIBUND = 8 };
struct Ctx {
    ucontext_t uc;
    OSThread* t;
    void* (*func)(void*);
    void* param;
    unsigned long long seq;   // ready order (FIFO within a priority)
    int ready;                // on the ready list
};
static OSThread g_main;
static Ctx g_mainCtx;
static OSThread* g_cur = &g_main;
static OSThread* g_all[64];
static int g_n;
static unsigned long long g_seq;

static void makeReady(OSThread* t) { t->state = READY; t->ctx->ready = 1; t->ctx->seq = ++g_seq; }
static OSThread* best()
{
    OSThread* b = 0;
    for (int i = 0; i < g_n; i++) {
        OSThread* t = g_all[i];
        if (!t->ctx->ready || t->suspend > 0) continue;
        if (!b || t->priority < b->priority || (t->priority == b->priority && t->ctx->seq < b->ctx->seq)) b = t;
    }
    return b;
}
static void switchTo(OSThread* next)
{
    if (next == g_cur) { g_cur->state = RUNNING; g_cur->ctx->ready = 0; return; }
    OSThread* prev = g_cur;
    g_cur = next;
    next->state = RUNNING;
    next->ctx->ready = 0;
    swapcontext(&prev->ctx->uc, &next->ctx->uc);
}
// The caller left the CPU (blocked, suspended or ended): the best ready thread runs.
static void reschedule()
{
    OSThread* n = best();
    if (!n) { re4dc_log("gc_os: no thread can run\n"); re4dc_halt("gc_os.cpp", __LINE__); }
    switchTo(n);
}
// A thread became ready: it runs at once when it outranks the caller (the caller stays ready, ahead of its equals).
static void preemptCheck()
{
    OSThread* n = best();
    if (n && n->priority < g_cur->priority) {
        makeReady(g_cur);
        g_cur->ctx->seq = 0;   // first among its equals
        switchTo(n);
    }
}
extern "C" void OSExitThread(void*);
static void entry(void)
{
    OSThread* t = g_cur;
    void* r = t->ctx->func(t->ctx->param);
    OSExitThread(r);
}

extern "C" {
void sched_os_tick(void) {}
void sched_os_report(char* out, unsigned n) { snprintf(out, n, "gc_os threads %d", g_n); }
void sched_os_boot(void)
{
    g_main.ctx = &g_mainCtx;
    g_mainCtx.t = &g_main;
    g_main.priority = g_main.base = 16;
    g_main.state = RUNNING;
    g_all[g_n++] = &g_main;
}
void OSPanic(const char* file, int line, const char* msg, ...)
{
    re4dc_log("OSPanic %s:%d: %s\n", file, line, msg);
    re4dc_halt(file, line);
}
int OSCreateThread(OSThread* t, void* (*func)(void*), void* param, void* stack, u32 size, s32 prio, u16 attr)
{
    Ctx* c = t->ctx;
    bool known = false;
    for (int i = 0; i < g_n; i++) known |= g_all[i] == t;
    if (!known) { c = (Ctx*) calloc(1, sizeof(Ctx)); if (g_n >= 64) re4dc_halt("gc_os.cpp", __LINE__); g_all[g_n++] = t; }
    memset(t, 0, sizeof(*t));
    memset(c, 0, sizeof(*c));
    t->ctx = c;
    c->t = t;
    c->func = func;
    c->param = param;
    t->priority = t->base = prio;
    t->attr = attr;
    t->suspend = 1;
    t->state = READY;
    t->stackBase = (u8*) stack;
    t->stackEnd = (u32*) ((u8*) stack - size);
    *t->stackEnd = 0xDEADBABE;
    getcontext(&c->uc);
    c->uc.uc_stack.ss_sp = (u8*) stack - size + 16;
    c->uc.uc_stack.ss_size = size - 16;
    c->uc.uc_link = 0;
    makecontext(&c->uc, entry, 0);
    c->ready = 1;
    c->seq = ++g_seq;
    return 1;
}
s32 OSResumeThread(OSThread* t)
{
    s32 prev = t->suspend;
    if (t->suspend > 0 && --t->suspend == 0 && t->ctx->ready) preemptCheck();
    return prev;
}
s32 OSSuspendThread(OSThread* t)
{
    s32 prev = t->suspend++;
    if (prev == 0 && t == g_cur) { makeReady(t); reschedule(); }
    return prev;
}
OSThread* OSGetCurrentThread(void) { return g_cur; }
void OSExitThread(void* val)
{
    g_cur->val = val;
    g_cur->state = MORIBUND;
    g_cur->ctx->ready = 0;
    reschedule();
    re4dc_halt("gc_os.cpp", __LINE__);   // an ended thread never runs again
}
void OSCancelThread(OSThread* t)
{
    t->ctx->ready = 0;
    t->queue = 0;
    t->state = MORIBUND;
}
void OSInitThreadQueue(OSThreadQueue* q) { q->head = q->tail = 0; }
void OSSleepThread(OSThreadQueue* q)
{
    g_cur->state = WAITING;
    g_cur->queue = q;
    g_cur->ctx->ready = 0;
    reschedule();
}
void OSWakeupThread(OSThreadQueue* q)
{
    for (int i = 0; i < g_n; i++) {
        OSThread* t = g_all[i];
        if (t->state == WAITING && t->queue == q) { t->queue = 0; makeReady(t); }
    }
    preemptCheck();
}
void OSInitSemaphore(OSSemaphore* s, s32 count) { s->count = count; s->queue.head = s->queue.tail = 0; }
s32 OSWaitSemaphore(OSSemaphore* s)
{
    while (s->count <= 0) OSSleepThread(&s->queue);
    return s->count--;
}
s32 OSSignalSemaphore(OSSemaphore* s)
{
    s32 c = s->count++;
    OSWakeupThread(&s->queue);
    return c;
}
BOOL OSDisableInterrupts(void) { return 1; }
BOOL OSRestoreInterrupts(BOOL l) { return l; }
}
