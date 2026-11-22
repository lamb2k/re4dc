# Lane eng-clock1: the engine's clock (lane eng-skel2, item 1; 2026-11-21)

Status: finished, unaudited.

## The fault
KOS's nanosecond clock jumps 2,502,400 ns forward once a second. TMU2 reloads every second from
`TIMER_PCK / 4` = 199,499,520 / 16 = 12,468,720 counts (`kernel/arch/dreamcast/kernel/timer.c` line 72 `TIMER_PCK`,
`timer_ms_enable()` `timer_prime(TMU2, 1, 1)`), while `arch_timer_gettime()` values each count at 80 ns
(`kernel/arch/dreamcast/include/arch/timer.h` lines 262-265, `time.ticks * 80`). On a console at 199.4995 MHz a count
is 80.2 ns, so within each second KOS's clock runs 0.25% slow and catches up with a 2.5 ms jump at the whole second.
Every engine time read (`timer_us_gettime64`) carried it: a MODELLED worst picture could hold +2.5 ms once a second.
KOS is not patched (an upstream change needs the owner's OK); this is the finding to report if the owner agrees.

## The fix
`core/e1_clock.h`: `e1_clock_us()` / `e1_clock_ns()` read KOS's seconds and TMU2 count once
(`__dreamcast_get_ticks`) and convert the count at the reload's own rate (count x 10^6 / 12,468,720, fixed point,
rounded down: monotonic across the second). Readers switched: `core/main.cpp` (the tick's rows), `core/frame.cpp` (the
pacer's wait column, the PACETMU lab arm, the LATEPIC control), `core/draw_e1.c` (drawing row, MODELLED stamps),
`core/partner.cpp` (characters), `host/e1_wraps.cpp` (services row, SVCPROF account). Boot line `E1 CLOCK`: TMU2's
TCOR2 read back (12,468,720 at Pck / 4: OK, else MISMATCH).
- No game-time or behaviour path reads the clock: the default pacer waits on the vblank field count; the image links
  no OSGetTime. Not switched (other images, their owners told): `bench/main.c`, `demo/edemo_main.c` (timing reports,
  same artefact), `loader/*.c` (millisecond timeouts only).

## Tiers
On Flycast the engine clock reads every interval 0.25% long (the emulator's peripheral clock is 50 MHz, 200 / 4, so a
TMU2 count is exactly 80 ns there and KOS's second of 12,468,720 counts lasts 0.9975 emulated seconds): MODELLED
figures after this fix are 0.25% conservative. On the console it is exact. The clock is not scaled for the emulator.

## Proof (boot file GAPPROBE, `core/e1_clock.cpp`; checker `tools/engine/clock_check.py --tier flycast|console`)
Run clkQ-std (plain Flycast, function only), image 241ec32bc:
- engine clock, interrupts on, 2.2 s across 2 whole seconds: one gap, the probe's own spin control (3,884 us);
  interrupts off, 1.2 s across 1 second: no gap.
- control, KOS's conversion, interrupts on: 2,502 us gaps at 0.385 s and 1.385 s.
- 600 fields: engine span 10,034,234 us (field 16,721-16,728 us); KOS's 10,034,148 us (field 16,678-19,186 us: the
  jump). Expected on Flycast 10,010,000 x 12,500,000 / 12,468,720 = 10,035,111 us: within one field. Control of that
  row: `--tier console` on this Flycast log (10,010,000 expected, 24 ms off) FAILS; `--judge kos` FAILS.
- A KOS-conversion arm with interrupts off stopped the Flycast run twice (runs clkA2-std, clkP-std; not explained); it
  was dropped: the control needs only the jump, which the interrupts-on arm shows.
