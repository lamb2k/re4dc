// The engine's OS thread layer (lane eng-sched1): the GameCube OS thread, queue, semaphore and interrupt calls the
// hosted scheduler (src/game/scheduler.cpp) makes, on KOS threads. Lifted from the old port; see os_threads.cpp's head.
#ifndef ENG_OS_THREADS_H
#define ENG_OS_THREADS_H
#ifdef __cplusplus
extern "C" {
#endif
// Records the engine's main thread as the OS layer's main thread (its KOS priority is kept). Before the first task.
void os_threads_boot(void);
// Per task stack (one OSThread a slot): bytes, untouched bytes (still the scheduler's 0xB3 fill), guard word.
// Returns the number of distinct stacks the layer has seen (at most `max`).
struct OsStackMark { const void* thread; unsigned bytes, untouched, guard; };
unsigned os_threads_stacks(struct OsStackMark* out, unsigned max);
// KOS thread records created, joined after they finished, and still waiting to be joined.
void os_threads_stats(unsigned* created, unsigned* reaped, unsigned* pending);
#ifdef __cplusplus
}
#endif
#endif
