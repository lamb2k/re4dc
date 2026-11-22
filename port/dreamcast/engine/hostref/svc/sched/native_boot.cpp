// native_boot.cpp (lane eng-sched1): the PC check's native layer boot: KOS's model (kos_pc.cpp) with the main thread
// at the engine's priority (KOS PRIO_DEFAULT 10; SCHED_MAIN_PRIO=16 is the old port's setting, a row of its own),
// then the engine's layer (engine/core/os_threads.cpp os_threads_boot).
#include "kos_pc/kos.h"
#include "os_threads.h"
#include <stdlib.h>
#include <stdio.h>
extern "C" void sched_os_boot(void)
{
    const char* p = getenv("SCHED_MAIN_PRIO");
    kos_pc_boot(p && *p ? atoi(p) : 10);
    os_threads_boot();
}
extern "C" void sched_os_tick(void) { kos_pc_tick(); }
extern unsigned kos_pc_switches, kos_pc_preempts;
extern "C" void sched_os_report(char* out, unsigned n)
{
    unsigned c, r, p;
    os_threads_stats(&c, &r, &p);
    snprintf(out, n, "kos_pc switches %u timer pre-emptions %u; os_threads created %u reaped %u pending %u", kos_pc_switches,
             kos_pc_preempts, c, r, p);
}
