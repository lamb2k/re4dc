# M1 matched drawing profile

Five captured pictures per room (19, 43, 67, 91, 115). The unmodified game drawing path ran from the same pre-draw states as the record-verification runs. All ten verification records matched byte for byte. Recording was disabled for timing. The six scopes exclude game logic and presentation waits. The five-picture means below use the nominal 200 MHz SH7091 model.

| Room / phase | Strip bench B ms | Game ms | Difference ms |
|---|---:|---:|---:|
| cross World | 10.852 | 10.626 | +0.226 |
| cross Characters | 41.269 | 10.778 | +30.492 |
| cross PT | 0.272 | 0.732 | -0.460 |
| cross TR | 0.004 | 0.298 | -0.294 |
| cross Effects | 0.083 | 3.686 | -3.603 |
| cross HUD | 0.112 | 1.406 | -1.294 |
| cross Total | 52.593 | 27.526 | +25.067 |
| hayfork World | 8.055 | 6.081 | +1.974 |
| hayfork Characters | 133.425 | 34.755 | +98.670 |
| hayfork PT | 2.088 | 1.564 | +0.524 |
| hayfork TR | 0.005 | 0.169 | -0.165 |
| hayfork Effects | 0.060 | 6.741 | -6.681 |
| hayfork HUD | 0.103 | 0.368 | -0.266 |
| hayfork Total | 143.736 | 49.679 | +94.057 |

## cross World, strip bench B

Rows are exclusive symbol costs per sampled picture. Cycles are reconstructed from hwreport milliseconds (rounded to 20 cycles). I, DR and DW are mean instruction, data-read and data-write misses. Game and bench phase totals are above. Equivalent per-symbol differences are undefined across implementations.

| Function | Cycles | I | DR | DW | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 1,095,340 | 97.6 | 4504.2 | 140.0 | Per draw: resolve shared tables and submit material changes. Inlined strip loops bound, transform, clip, divide and emit corners. |
| __fpclassifyf | 449,080 | 2.2 | 46.0 | 0.0 | Per clamp operand: newlib checks the floating-point class. |
| fmaxf | 216,240 | 1.2 | 58.2 | 0.0 | Per corner/light diffuse clamp, or per strip-axis upper extent. |
| fminf | 214,700 | 1.6 | 59.8 | 32.2 | Per lit corner/channel upper clamp, or per strip-axis lower extent. |
| matrix | 82,720 | 22.6 | 283.8 | 187.8 | Compose or reload a screen matrix on each bone/pose switch. |
| L_store_long_loop | 63,260 | 0.2 | 0.0 | 494.8 | Clear aligned words in per-draw light initialization or kernel work. |
| L_store_byte_loop | 20,460 | 1.8 | 0.0 | 0.0 | Clear trailing bytes during initialization. |
| memset | 3,940 | 0.6 | 0.0 | 0.0 | Dispatch size/alignment-specific clearing. |
| L_dup_bytes | 3,280 | 1.6 | 0.0 | 0.0 | Expand a fill byte into a word. |
| L_al4both_loop | 2,940 | 0.0 | 77.4 | 0.0 | Copy aligned words, including headers or matrix storage. |

## cross Characters, strip bench B

Rows are exclusive symbol costs per sampled picture. Cycles are reconstructed from hwreport milliseconds (rounded to 20 cycles). I, DR and DW are mean instruction, data-read and data-write misses. Game and bench phase totals are above. Equivalent per-symbol differences are undefined across implementations.

| Function | Cycles | I | DR | DW | Work |
|---|---:|---:|---:|---:|---|
| __fpclassifyf | 2,321,960 | 0.8 | 92.4 | 0.0 | Per clamp operand: newlib checks the floating-point class. |
| shade | 2,211,880 | 19.0 | 2365.6 | 85.0 | Per submitted actor corner: rotate normal, evaluate every lamp and pack RGB. |
| fminf | 1,545,340 | 1.2 | 94.2 | 11.4 | Per lit corner/channel upper clamp, or per strip-axis lower extent. |
| render_phase | 985,700 | 98.6 | 2895.2 | 152.8 | Per draw: resolve shared tables and submit material changes. Inlined strip loops bound, transform, clip, divide and emit corners. |
| fmaxf | 783,960 | 0.4 | 89.2 | 100.0 | Per corner/light diffuse clamp, or per strip-axis upper extent. |
| matrix | 357,980 | 69.2 | 1638.0 | 560.0 | Compose or reload a screen matrix on each bone/pose switch. |
| L_store_long_loop | 14,540 | 0.0 | 0.0 | 68.0 | Clear aligned words in per-draw light initialization or kernel work. |
| maple_enum_dev | 2,660 | 2.0 | 9.2 | 0.0 | Periodic Maple device enumeration inside the sampled phase. |
| handler_irq9 | 2,500 | 16.2 | 13.0 | 3.6 | Asynchronous interrupt service within the drawing interval. |
| thd_schedule | 2,340 | 28.2 | 49.8 | 7.6 | KOS periodic thread scheduling. |

## hayfork World, strip bench B

Rows are exclusive symbol costs per sampled picture. Cycles are reconstructed from hwreport milliseconds (rounded to 20 cycles). I, DR and DW are mean instruction, data-read and data-write misses. Game and bench phase totals are above. Equivalent per-symbol differences are undefined across implementations.

| Function | Cycles | I | DR | DW | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 813,000 | 77.4 | 3047.8 | 52.0 | Per draw: resolve shared tables and submit material changes. Inlined strip loops bound, transform, clip, divide and emit corners. |
| __fpclassifyf | 351,180 | 2.0 | 43.0 | 0.0 | Per clamp operand: newlib checks the floating-point class. |
| fmaxf | 168,820 | 1.2 | 41.4 | 0.0 | Per corner/light diffuse clamp, or per strip-axis upper extent. |
| fminf | 167,560 | 1.2 | 39.0 | 29.0 | Per lit corner/channel upper clamp, or per strip-axis lower extent. |
| matrix | 62,640 | 13.4 | 190.4 | 114.0 | Compose or reload a screen matrix on each bone/pose switch. |
| L_store_long_loop | 26,600 | 0.0 | 0.0 | 280.4 | Clear aligned words in per-draw light initialization or kernel work. |
| L_store_byte_loop | 9,100 | 1.6 | 0.0 | 0.0 | Clear trailing bytes during initialization. |
| memset | 1,760 | 0.6 | 0.0 | 0.0 | Dispatch size/alignment-specific clearing. |
| L_al4both_loop | 1,500 | 0.0 | 41.0 | 0.0 | Copy aligned words, including headers or matrix storage. |
| L_dup_bytes | 1,480 | 1.6 | 0.0 | 0.0 | Expand a fill byte into a word. |

## hayfork Characters, strip bench B

Rows are exclusive symbol costs per sampled picture. Cycles are reconstructed from hwreport milliseconds (rounded to 20 cycles). I, DR and DW are mean instruction, data-read and data-write misses. Game and bench phase totals are above. Equivalent per-symbol differences are undefined across implementations.

| Function | Cycles | I | DR | DW | Work |
|---|---:|---:|---:|---:|---|
| __fpclassifyf | 7,227,800 | 1.0 | 465.2 | 0.0 | Per clamp operand: newlib checks the floating-point class. |
| shade | 6,820,200 | 48.6 | 9559.2 | 360.8 | Per submitted actor corner: rotate normal, evaluate every lamp and pack RGB. |
| fminf | 5,100,980 | 1.6 | 316.2 | 26.6 | Per lit corner/channel upper clamp, or per strip-axis lower extent. |
| render_phase | 3,625,420 | 263.6 | 12072.4 | 793.0 | Per draw: resolve shared tables and submit material changes. Inlined strip loops bound, transform, clip, divide and emit corners. |
| fmaxf | 2,098,720 | 0.4 | 389.6 | 420.2 | Per corner/light diffuse clamp, or per strip-axis upper extent. |
| matrix | 1,642,200 | 210.6 | 8149.0 | 2691.6 | Compose or reload a screen matrix on each bone/pose switch. |
| L_store_long_loop | 60,200 | 0.0 | 0.0 | 305.4 | Clear aligned words in per-draw light initialization or kernel work. |
| maple_enum_dev | 10,000 | 2.4 | 37.2 | 0.0 | Periodic Maple device enumeration inside the sampled phase. |
| L_movmem_start_even | 9,320 | 0.2 | 0.0 | 186.4 | Even-aligned compiler-generated block copy. |
| maple_driver_foreach | 7,560 | 13.6 | 34.6 | 0.0 | Periodic Maple driver enumeration. |

The cross world loop includes 11,425 divides, 11,262 prefetch instructions and 4,504 data-read misses per picture. Strip-bound libm comparisons and classification alone take 4.400 ms. Headers are already baked and relocated at load. Their copies and the selection table reads are included in the main loop. The profile cannot isolate a header-only cost.

Private evidence under the lane folder includes baseline003-{cross,hayfork}-timed, baseline003-cross-verify2, baseline003-hayfork-verify3 and the phase003-{0,1} directories under each bench-model run. Phase-filtered hwreport runs simulated the full instruction stream to preserve cache and dependency history.
