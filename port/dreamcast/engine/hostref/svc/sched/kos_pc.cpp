// kos_pc.cpp (lane eng-sched1): KOS's thread calls on PC contexts for the PC check's native layer (kos_pc/kos.h).
#include "kos_pc/kos.h"
#include <ucontext.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" void re4dc_halt(const char* file, int line);

struct kos_pc_ctx {
    ucontext_t uc;
    void* (*fn)(void*);
    void* arg;
    unsigned long long seq;    // run-queue order
    unsigned long long wseq;   // genwait order
    int in_rq;
};
kthread_t* thd_current;
static kthread_t* g_all[96];
static int g_n, g_tid = 1, g_irq;
static unsigned long long g_seq, g_wseq, g_ms;
static unsigned g_jitter, g_rand;
unsigned kos_pc_switches, kos_pc_preempts;   // context switches; timer pre-emptions that took the CPU away

static void* bystander(void*);
static kthread_t* add(kthread_t* kt)
{
    if (g_n >= 96) re4dc_halt("kos_pc.cpp", __LINE__);
    g_all[g_n++] = kt;
    return kt;
}
static kthread_t* pick()
{
    kthread_t* b = 0;
    for (int i = 0; i < g_n; i++) {
        kthread_t* k = g_all[i];
        if (!k->pc->in_rq || k->state != STATE_READY) continue;
        if (!b || k->prio < b->prio || (k->prio == b->prio && k->pc->seq < b->pc->seq)) b = k;
    }
    return b;
}
static void run(kthread_t* next)
{
    if (!next) {
        fprintf(stderr, "kos_pc: no thread can run\n");
        re4dc_halt("kos_pc.cpp", __LINE__);
    }
    next->pc->in_rq = 0;
    next->state = STATE_RUNNING;
    if (next == thd_current) return;
    kthread_t* prev = thd_current;
    kos_pc_switches++;
    thd_current = next;
    swapcontext(&prev->pc->uc, &next->pc->uc);
}
static void trampoline()
{
    kthread_t* me = thd_current;
    void* r = me->pc->fn(me->pc->arg);
    thd_exit(r);
}

void kos_pc_boot(int main_prio)
{
    kthread_t* m = (kthread_t*) calloc(1, sizeof(kthread_t));
    m->pc = (kos_pc_ctx*) calloc(1, sizeof(kos_pc_ctx));
    m->tid = g_tid++;
    m->prio = main_prio;
    m->state = STATE_RUNNING;
    thd_current = add(m);
    const char* j = getenv("SCHED_KOS_JITTER");
    if (j && *j) {
        g_jitter = 1;
        g_rand = (unsigned) strtoul(j, 0, 0) | 1;
        static char stack[16384];
        kthread_attr_t a = {sizeof stack, stack, 10, "bystander", true, false};
        thd_create_ex(&a, bystander, 0);
        thd_pass();   // it runs to its first wait (equal priority: the main thread yields its turn once)
    }
}
kthread_t* thd_create_ex(const kthread_attr_t* a, void* (*fn)(void*), void* arg)
{
    kthread_t* k = (kthread_t*) calloc(1, sizeof(kthread_t));
    k->pc = (kos_pc_ctx*) calloc(1, sizeof(kos_pc_ctx));
    k->tid = g_tid++;
    k->prio = a->prio;
    k->pc->fn = fn;
    k->pc->arg = arg;
    getcontext(&k->pc->uc);
    k->pc->uc.uc_stack.ss_sp = (char*) a->stack_ptr + 16;
    k->pc->uc.uc_stack.ss_size = a->stack_size - 16;
    k->pc->uc.uc_link = 0;
    makecontext(&k->pc->uc, trampoline, 0);
    k->state = STATE_READY;
    k->pc->in_rq = 1;
    k->pc->seq = ++g_seq;
    return add(k);
}
void thd_block_now(irq_context_t*) { thd_current->pc->in_rq = 0; run(pick()); }
void thd_remove_from_runnable(kthread_t* k) { k->pc->in_rq = 0; }
int thd_add_to_runnable(kthread_t* k, bool front)
{
    k->pc->in_rq = 1;
    k->pc->seq = front ? 0 : ++g_seq;
    return 0;
}
void thd_schedule(bool front)
{
    kthread_t* me = thd_current;
    if (me->state == STATE_RUNNING) {
        me->state = STATE_READY;
        thd_add_to_runnable(me, front);
    }
    run(pick());
}
void thd_pass(void) { thd_schedule(false); }
void thd_exit(void* rv)
{
    (void) rv;
    thd_current->state = STATE_FINISHED;
    thd_current->pc->in_rq = 0;
    run(pick());
    re4dc_halt("kos_pc.cpp", __LINE__);
    for (;;) {}
}
// The record and its context are kept (a later thread never reuses them; the check runs minutes at most).
int thd_destroy(kthread_t* k)
{
    k->pc->in_rq = 0;
    k->state = STATE_ZOMBIE;
    k->wait_obj = 0;
    return 0;
}
int thd_join(kthread_t* k, void**)
{
    if (k->state != STATE_FINISHED) re4dc_halt("kos_pc.cpp", __LINE__);   // the layer joins finished threads only
    k->state = STATE_ZOMBIE;
    return 0;
}
int thd_set_prio(kthread_t* k, int prio) { k->prio = prio; return 0; }
int genwait_wait(void* obj, const char* msg, int)
{
    kthread_t* me = thd_current;
    me->state = STATE_WAIT;
    me->wait_obj = obj;
    me->wait_msg = msg;
    me->pc->wseq = ++g_wseq;
    me->pc->in_rq = 0;
    run(pick());
    return 0;
}
static int wake(void* obj, int all)
{
    int n = 0;
    for (;;) {
        kthread_t* b = 0;
        for (int i = 0; i < g_n; i++) {
            kthread_t* k = g_all[i];
            if (k->state == STATE_WAIT && k->wait_obj == obj && (!b || k->pc->wseq < b->pc->wseq)) b = k;
        }
        if (!b) return n;
        b->wait_obj = 0;
        b->wait_msg = 0;
        b->state = STATE_READY;
        thd_add_to_runnable(b, false);
        n++;
        if (!all) return n;
    }
}
int genwait_wake_all(void* obj) { return wake(obj, 1); }
int genwait_wake_one(void* obj) { return wake(obj, 0); }
// KOS's timer pre-emption, now and then (SCHED_KOS_JITTER): an interrupt wakes a bystander thread of priority 10 (the
// engine's main priority, above the tasks': a sound or disc thread), which takes the CPU from the running thread at
// once, runs, and waits again; the interrupted thread then goes on. Counted as a pre-emption when it took the CPU.
static int g_noise;
static unsigned g_noise_runs;
static void* bystander(void*)
{
    for (;;) {
        genwait_wait(&g_noise, "bystander", 0);
        g_noise_runs++;
    }
    return 0;
}
void kos_pc_tick(void)
{
    if (!g_jitter || g_irq) return;
    g_rand = g_rand * 1103515245u + 12345u;
    if (((g_rand >> 16) & 7) != 0) return;
    const unsigned before = g_noise_runs;
    if (genwait_wake_one(&g_noise)) thd_schedule(false);
    if (g_noise_runs != before) kos_pc_preempts++;
}
irq_mask_t irq_disable(void) { return g_irq++; }
void irq_restore(irq_mask_t m)
{
    g_irq = m;
    if (!m) kos_pc_tick();
}
void irq_enable(void) { g_irq = 0; }
int irq_inside_int(void) { return 0; }
uint64_t timer_ms_gettime64(void) { return ++g_ms; }
