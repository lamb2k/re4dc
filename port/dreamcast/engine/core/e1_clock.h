/* The engine's clock (lane eng-clock1): every engine time read for the rows, the pacer and the reports.
   KOS's own conversion (arch/timer.h arch_timer_gettime: TMU2 count x 80 ns) is 0.25% short: TMU2 reloads each
   second from TIMER_PCK / 4 = 12,468,720 counts (kernel/timer.c timer_ms_enable, timer_prime(TMU2, 1, 1)), so a
   count is 80.2 ns; KOS's clock runs slow within each second and jumps 2,502,400 ns forward at the whole second.
   The engine converts the count at the reload's own rate: seconds plus count x 10^6 / 12,468,720 (fixed point,
   rounded down, so the value stays under the next whole second: monotonic across it). KOS is not changed.
   Readers: core/main.cpp, core/frame.cpp, core/draw_e1.c, core/partner.cpp, host/e1_wraps.cpp. Check: boot file
   GAPPROBE (core/e1_clock.cpp; tools/engine/clock_check.py). */
#ifndef E1_CLOCK_H
#define E1_CLOCK_H
#include <stdint.h>
#include <arch/timer.h>

#define E1_CLOCK_COUNTS 12468720u              /* TMU2 counts a second: KOS's reload, checked at boot */
#define E1_CLOCK_US_MUL 344459358u             /* floor(2^32 x 10^6 / 12,468,720) */
#define E1_CLOCK_NS_MUL 1345544370u            /* floor(2^24 x 10^9 / 12,468,720) */

/* microseconds since KOS started */
static inline uint64_t e1_clock_us(void)
{
    const timer_val_t t = __dreamcast_get_ticks();
    return (uint64_t) t.secs * 1000000u + (uint32_t) (((uint64_t) t.ticks * E1_CLOCK_US_MUL) >> 32);
}
/* nanoseconds since KOS started */
static inline uint64_t e1_clock_ns(void)
{
    const timer_val_t t = __dreamcast_get_ticks();
    return (uint64_t) t.secs * 1000000000u + (uint32_t) (((uint64_t) t.ticks * E1_CLOCK_NS_MUL) >> 24);
}

#ifdef __cplusplus
extern "C" {
#endif
void e1_clock_boot(void);     /* the reload check (log line E1 CLOCK) and the boot file GAPPROBE */
void e1_clock_fields(void);   /* GAPPROBE: 600 display fields, once the display is open (core/main.cpp) */
#ifdef __cplusplus
}
#endif
#endif
