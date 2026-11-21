// The engine's clock (lane eng-clock1, core/e1_clock.h): the boot check of KOS's TMU2 reload and the boot file
// GAPPROBE, a diagnostic lab arm before play (from lane eng-skel1's probe, commit 8daaee5dd).
// GAPPROBE: (1) a tight loop on a clock lists every gap over 0.2 ms, with the second it fell in, first with interrupts
// on (with a known 3 to 4 ms spin at 0.5 s: the probe's own control) and then off; it runs on the engine's clock and
// then on KOS's own conversion (timer_ns_gettime64: the control, which must show the 2.5 ms jump at each whole second);
// (2) 600 display fields (about 10 s): the TMU2 count read once at each field's start, converted both ways, with the
// span and the shortest and longest field. Judged by tools/engine/clock_check.py on the serial log.
#include "e1_kos.h"
#include "e1_engine.h"
#include "e1_clock.h"
#include <arch/irq.h>
#include <dc/pvr.h>
#include <stdio.h>

namespace {
uint64_t eng_ns() { return e1_clock_ns(); }
uint64_t kos_ns() { return timer_ns_gettime64(); }   // KOS's conversion, count x 80 ns (the control)

void gap_run(const char* arm, const char* tag, uint64_t (*clk)(), uint64_t len_ns, bool irq_off, bool spin)
{
    irq_mask_t old = 0;
    if (irq_off) old = irq_disable();
    const timer_val_t r0 = __dreamcast_get_ticks();
    uint64_t t0 = clk(), prev = t0;
    uint32_t n = 0, iters = 0;
    uint64_t at[16], gap[16];
    bool spun = false;
    for (;;) {
        const uint64_t t = clk();
        iters++;
        if (t - prev > 200000 && n < 16) {
            at[n] = prev - t0;
            gap[n] = t - prev;
            n++;
        }
        prev = t;
        if (spin && !spun && t - t0 > 500000000ull) {
            spun = true;
            const uint64_t m0 = timer_ms_gettime64();   // a 3 to 4 ms spin on KOS's millisecond clock
            while (timer_ms_gettime64() - m0 < 4) {
            }
        }
        if (t - t0 >= len_ns) break;
    }
    const timer_val_t r1 = __dreamcast_get_ticks();
    if (irq_off) irq_restore(old);
    e1_log("E1 GAPPROBE %s %s: %lu ms, %lu reads, %lu gaps over 0.2 ms, crosses %lu whole seconds%s\n", arm, tag,
           (unsigned long) (len_ns / 1000000), (unsigned long) iters, (unsigned long) n,
           (unsigned long) (r1.secs - r0.secs), spin ? ", spin control at 0.5 s" : "");
    for (uint32_t i = 0; i < n; i++)
        e1_log("E1 GAPPROBE %s %s gap %lu us at %lu.%06lu s from the start\n", arm, tag, (unsigned long) (gap[i] / 1000),
               (unsigned long) (at[i] / 1000000000ull), (unsigned long) (at[i] / 1000 % 1000000));
    fflush(stdout);   // each arm's lines out before the next (a diagnostic: where a run stops)
}

// vid_waitvbl's wait (the display's sync status: in a field's blanking, then out of it), bounded at 100 ms
bool wait_field()
{
    const uint64_t t0 = e1_clock_us();
    while (!(PVR_GET(PVR_SYNC_STATUS) & 0x01ff))
        if (e1_clock_us() - t0 > 100000) return false;
    while (PVR_GET(PVR_SYNC_STATUS) & 0x01ff)
        if (e1_clock_us() - t0 > 100000) return false;
    return true;
}
int gap_probe_on;
}

// after the display is open (core/main.cpp, before the first tick): 600 fields, the count converted both ways
extern "C" void e1_clock_fields(void)
{
    if (!gap_probe_on) return;
    enum { kFields = 600 };
    uint64_t e_first = 0, k_first = 0, e_prev = 0, k_prev = 0;
    uint32_t e_min = ~0u, e_max = 0, k_min = ~0u, k_max = 0, e_maxat = 0, k_maxat = 0;
    if (!wait_field()) { e1_log("E1 CLOCKSPAN no display fields (100 ms without one)\n"); return; }
    for (uint32_t i = 0; i <= kFields; i++) {
        if (i && !wait_field()) { e1_log("E1 CLOCKSPAN no display fields (100 ms without one)\n"); return; }
        const timer_val_t r = __dreamcast_get_ticks();
        const uint64_t e = (uint64_t) r.secs * 1000000u + (uint32_t) (((uint64_t) r.ticks * E1_CLOCK_US_MUL) >> 32);
        const uint64_t k = (uint64_t) r.secs * 1000000u + (uint64_t) r.ticks * 80u / 1000u;   // KOS's conversion
        if (!i) { e_first = e_prev = e; k_first = k_prev = k; continue; }
        const uint32_t de = (uint32_t) (e - e_prev), dk = (uint32_t) (k - k_prev);
        if (de < e_min) e_min = de;
        if (de > e_max) { e_max = de; e_maxat = i; }
        if (dk < k_min) k_min = dk;
        if (dk > k_max) { k_max = dk; k_maxat = i; }
        e_prev = e;
        k_prev = k;
    }
    e1_log("E1 CLOCKSPAN %u fields: engine span %lu us, field min %lu max %lu (field %lu); kos span %lu us, field min %lu "
           "max %lu (field %lu)\n", (unsigned) kFields, (unsigned long) (e_prev - e_first), (unsigned long) e_min,
           (unsigned long) e_max, (unsigned long) e_maxat, (unsigned long) (k_prev - k_first), (unsigned long) k_min,
           (unsigned long) k_max, (unsigned long) k_maxat);
    fflush(stdout);
}

extern "C" void e1_clock_boot(void)
{
    const uint32_t tcor2 = *(volatile uint32_t*) 0xffd80020;   // TMU2's reload (KOS timer.c: TIMER_BASE + TCOR2)
    const uint32_t tpsc2 = *(volatile uint16_t*) 0xffd80028 & 7;   // TCR2's prescaler: 0 is Pck / 4
    const bool ok = tcor2 == E1_CLOCK_COUNTS && tpsc2 == 0;
    e1_log("E1 CLOCK TMU2 reload %lu counts, prescaler %lu: engine converts at %lu a second: %s\n", (unsigned long) tcor2,
           (unsigned long) tpsc2, (unsigned long) E1_CLOCK_COUNTS, ok ? "OK" : "MISMATCH");
    file_t f = fs_open("/cd/GAPPROBE", O_RDONLY);
    if (f < 0) return;
    fs_close(f);
    uint32_t s0 = 0, ms0 = 0;
    timer_ms_gettime(&s0, &ms0);
    e1_log("E1 GAPPROBE start at %lu.%03lu s of KOS time\n", (unsigned long) s0, (unsigned long) ms0);
    gap_run("engine", "irq-on", eng_ns, 2200000000ull, false, true);
    gap_run("engine", "irq-off", eng_ns, 1200000000ull, true, false);
    gap_run("kos", "irq-on", kos_ns, 2200000000ull, false, true);
    gap_run("kos", "irq-off", kos_ns, 1200000000ull, true, false);
    gap_probe_on = 1;   // the field span follows when the display is open (e1_clock_fields)
}
