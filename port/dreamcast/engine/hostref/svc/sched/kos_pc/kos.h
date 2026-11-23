// kos.h for the PC check (lane eng-sched1): the KOS thread calls the engine's OS layer (engine/core/os_threads.cpp)
// makes, with the fields it reads, so that file compiles on the PC unchanged. kos_pc.cpp runs them on PC contexts with
// KOS's rules: priority run queue (lower number first, FIFO among equals), thd_pass to the back of its priority,
// genwait queues woken in wait order, a created thread ready at once. SCHED_KOS_JITTER=<seed> (environment) adds
// KOS's timer pre-emption: at each interrupt restore and each stub call, now and then, the running thread is put to
// the back of its priority and the best ready thread runs (thd_schedule from the timer).
#ifndef SCHED_KOS_PC_H
#define SCHED_KOS_PC_H
#include <stdint.h>
#include <stddef.h>

typedef int irq_mask_t;
typedef struct { uint32_t r[16]; uint32_t pc, pr; } irq_context_t;
enum { STATE_ZOMBIE = 0, STATE_RUNNING = 1, STATE_READY = 2, STATE_WAIT = 3, STATE_FINISHED = 4 };
struct kos_pc_ctx;
typedef struct kthread {
    int tid;
    int prio;
    int state;
    void* wait_obj;
    const char* wait_msg;
    struct { uint64_t scheduled; } cpu_time;
    irq_context_t context;
    struct kos_pc_ctx* pc;   // the model's own record
} kthread_t;
typedef struct {
    size_t stack_size;
    void* stack_ptr;
    int prio;
    const char* label;
    bool disable_tls;
    bool create_detached;
} kthread_attr_t;

extern kthread_t* thd_current;
kthread_t* thd_create_ex(const kthread_attr_t* attr, void* (*fn)(void*), void* arg);
void thd_block_now(irq_context_t* ctx);
void thd_remove_from_runnable(kthread_t* kt);
int thd_add_to_runnable(kthread_t* kt, bool front);
void thd_schedule(bool front_of_line);
void thd_pass(void);
void thd_exit(void* rv) __attribute__((noreturn));
int thd_destroy(kthread_t* kt);
int thd_join(kthread_t* kt, void** rv);
int thd_set_prio(kthread_t* kt, int prio);
int genwait_wait(void* obj, const char* msg, int timeout);
int genwait_wake_all(void* obj);
int genwait_wake_one(void* obj);
irq_mask_t irq_disable(void);
void irq_restore(irq_mask_t m);
void irq_enable(void);
int irq_inside_int(void);
uint64_t timer_ms_gettime64(void);
// the model's boot: the calling (main) context becomes a KOS thread of priority `main_prio`
void kos_pc_boot(int main_prio);
// a pre-emption point outside the layer (the harness's stub calls)
void kos_pc_tick(void);
#endif
