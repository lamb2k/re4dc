/* Controlled environment for the real KOS SQ/mutex/genwait/MMU code.
 * No interrupt, contention, waiter or MMU translation is introduced. The
 * interpreter supplies MMUCR/QACR/SR state; forbidden edges trap separately.
 */
#include <kos/thread.h>
int inside_int;
static kthread_t fixture_thread;
kthread_t *thd_current=&fixture_thread;
extern unsigned fixture_load_calls,fixture_stream_open_calls,fixture_fog_value;

void* fixture_load_control(const void* image,bool pin,const void* key) {
    (void)image;(void)pin;(void)key;
    ++fixture_load_calls;
    return NULL;
}
void fixture_scene_open_control(void) {
    ++fixture_stream_open_calls;
    __builtin_trap();
}
/* Same one-load getter body as native_ps2_world.cpp, in its own TU. */
unsigned re4dc_ps2_world_fog(void) { return fixture_fog_value; }

void fixture_kos_reset(void) {
    inside_int=0;
    fixture_thread.prio=fixture_thread.real_prio=10;
}
