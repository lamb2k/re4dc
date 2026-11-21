// e2c_co.cpp (PC side; lane eng-e2c): one coroutine for the boss exercise's scenario task (svc/e2c_dump.cpp: the room's
// thunder runs as a task that sleeps a tick at a time). start makes it, resume runs it until it yields, yield returns.
#include <ucontext.h>

namespace {
ucontext_t g_main, g_task;
alignas(16) unsigned char g_stack[64 * 1024];
void (*g_fn)();
void entry() { g_fn(); }
}   // namespace

extern "C" void e2c_co_start(void (*fn)())
{
    g_fn = fn;
    getcontext(&g_task);
    g_task.uc_stack.ss_sp = g_stack;
    g_task.uc_stack.ss_size = sizeof(g_stack);
    g_task.uc_link = &g_main;
    makecontext(&g_task, entry, 0);
}
extern "C" void e2c_co_resume() { swapcontext(&g_main, &g_task); }
extern "C" void e2c_co_yield() { swapcontext(&g_task, &g_main); }
