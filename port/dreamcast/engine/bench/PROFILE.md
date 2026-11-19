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

## Indexed renderer

The same ten game pictures and hwmodel configuration were used for both implementations. The renderer ran from commit `deb10de2c`. Times below are per picture. Modifier-volume submission falls in the bench character interval and in the game effects interval. Masked actor parts fall in the bench translucent interval. The drawing total includes all six intervals in both runs.

| Room / phase | Indexed ms | Game ms | Difference ms |
|---|---:|---:|---:|
| cross World | 5.343 | 10.626 | -5.283 |
| cross Characters | 6.414 | 10.778 | -4.364 |
| cross PT | 0.160 | 0.732 | -0.572 |
| cross TR | 1.241 | 0.298 | +0.943 |
| cross Effects | 0.067 | 3.686 | -3.620 |
| cross HUD | 0.075 | 1.406 | -1.331 |
| cross Total | 13.298 | 27.526 | -14.227 |
| hayfork World | 3.958 | 6.081 | -2.123 |
| hayfork Characters | 20.844 | 34.755 | -13.912 |
| hayfork PT | 1.066 | 1.564 | -0.498 |
| hayfork TR | 1.028 | 0.169 | +0.858 |
| hayfork Effects | 0.045 | 6.741 | -6.697 |
| hayfork HUD | 0.083 | 0.368 | -0.286 |
| hayfork Total | 27.023 | 49.679 | -22.656 |

### cross world

| Function | Mean cycles | I misses | DR misses | DW misses | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 936,860 | 248.8 | 3823.4 | 68.0 | Indexed strip classification, projected-corner and UV gathers, SQ emission, light-direction setup and phase dispatch. World uses material-ordered draws, preclassified pieces and streamed boundary strips. |
| matrix | 83,420 | 28.6 | 307.8 | 202.6 | Compose a pose or bone with the view and projection for this picture. |
| clipped | 36,360 | 30.6 | 24.6 | 73.6 | Clip a boundary triangle against the near plane and emit its surviving polygon. |
| L_al4both_loop | 3,000 | 0.0 | 74.6 | 0.0 | Aligned longword copy, including header and matrix transfers. |
| memcpy | 1,480 | 49.2 | 0.0 | 0.0 | Dispatch block copies. |
| L_cleanup | 840 | 49.2 | 0.0 | 0.0 | Copy the tail of a block. |
| L_even | 700 | 41.2 | 0.0 | 0.0 | Align a block copy. |
| handler_irq9 | 560 | 4.0 | 2.0 | 2.0 | Interrupt service within the sampled scope. |
| L_al4both | 540 | 41.2 | 0.0 | 0.0 | Alignment setup before word copies. |
| open_picture | 500 | 5.0 | 11.8 | 2.2 | Read picture spans and its atmosphere and modifier-volume bindings. |

### cross characters

| Function | Mean cycles | I misses | DR misses | DW misses | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 826,780 | 285.2 | 10190.2 | 796.2 | Indexed strip classification, projected-corner and UV gathers, SQ emission, light-direction setup and phase dispatch. World uses material-ordered draws, preclassified pieces and streamed boundary strips. |
| re4dc_avk_light_skin_n16 | 176,820 | 191.4 | 1652.2 | 2692.8 | Light each unique part normal through its bone directions and the captured part colour matrix. |
| re4dc_avk_pos_skin_u16 | 171,100 | 35.4 | 794.2 | 2625.2 | Transform each distinct skinned position in the shared pose pool. |
| matrix | 93,620 | 22.2 | 421.8 | 409.2 | Compose a pose or bone with the view and projection for this picture. |
| re4dc_avk_pos_rigid_u16 | 3,860 | 25.0 | 5.2 | 83.0 | Transform each distinct rigid position. |
| L_al4both_loop | 2,520 | 0.0 | 44.4 | 21.8 | Aligned longword copy, including header and matrix transfers. |
| handler_irq9 | 760 | 5.2 | 3.2 | 2.0 | Interrupt service within the sampled scope. |
| memcpy | 580 | 13.8 | 0.0 | 0.0 | Dispatch block copies. |
| mutex_unlock | 560 | 11.0 | 6.6 | 1.2 | Release a KOS lock inside the interval. |
| L_cleanup | 440 | 11.8 | 0.0 | 0.0 | Copy the tail of a block. |

### hayfork world

| Function | Mean cycles | I misses | DR misses | DW misses | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 689,720 | 148.8 | 2875.8 | 64.8 | Indexed strip classification, projected-corner and UV gathers, SQ emission, light-direction setup and phase dispatch. World uses material-ordered draws, preclassified pieces and streamed boundary strips. |
| matrix | 65,020 | 18.8 | 230.6 | 187.6 | Compose a pose or bone with the view and projection for this picture. |
| clipped | 30,500 | 30.8 | 21.0 | 69.8 | Clip a boundary triangle against the near plane and emit its surviving polygon. |
| L_al4both_loop | 1,420 | 0.0 | 40.0 | 0.0 | Aligned longword copy, including header and matrix transfers. |
| memcpy | 780 | 26.0 | 0.0 | 0.0 | Dispatch block copies. |
| open_picture | 460 | 5.0 | 11.0 | 1.6 | Read picture spans and its atmosphere and modifier-volume bindings. |
| L_cleanup | 380 | 26.0 | 0.0 | 0.0 | Copy the tail of a block. |
| L_even | 360 | 21.8 | 0.0 | 0.0 | Align a block copy. |
| L_al4both | 280 | 21.8 | 0.0 | 0.0 | Alignment setup before word copies. |
| __dreamcast_get_ticks | 220 | 2.0 | 3.6 | 0.0 | Read the guest clock at the phase boundary. |

### hayfork characters

| Function | Mean cycles | I misses | DR misses | DW misses | Work |
|---|---:|---:|---:|---:|---|
| render_phase | 2,693,940 | 597.6 | 18620.2 | 3046.2 | Indexed strip classification, projected-corner and UV gathers, SQ emission, light-direction setup and phase dispatch. World uses material-ordered draws, preclassified pieces and streamed boundary strips. |
| matrix | 643,540 | 165.2 | 3120.6 | 2706.0 | Compose a pose or bone with the view and projection for this picture. |
| re4dc_avk_pos_skin_u16 | 604,580 | 57.8 | 3184.2 | 9238.8 | Transform each distinct skinned position in the shared pose pool. |
| re4dc_avk_light_skin_n16 | 177,880 | 201.4 | 1670.2 | 2713.8 | Light each unique part normal through its bone directions and the captured part colour matrix. |
| L_al4both_loop | 7,480 | 0.0 | 161.4 | 20.2 | Aligned longword copy, including header and matrix transfers. |
| L_store_long_loop | 7,300 | 0.8 | 0.0 | 0.0 | Clear aligned storage. |
| re4dc_avk_pos_rigid_u16 | 3,380 | 38.0 | 13.2 | 35.0 | Transform each distinct rigid position. |
| handler_irq9 | 2,580 | 19.0 | 9.6 | 6.4 | Interrupt service within the sampled scope. |
| memcpy | 2,420 | 58.4 | 0.0 | 0.0 | Dispatch block copies. |
| thd_schedule | 1,860 | 29.2 | 30.4 | 3.6 | KOS periodic thread scheduling. |

The original per-corner clamp/classification and per-strip libm bounds helpers left the top ten. The baker strips out empty world draws, groups by material and classifies the entire selected piece against the recorded near plane. Fully forward strips emit directly. Intersecting pieces keep a runtime bounds test and clipper. Store-queue headers are precompiled and relocated once on load. On hayfork the remaining character cost is concentrated in indexed emission and part setup, followed by matrix composition and the skinned position pass. All captured actor parts, including barn-interior props, remain in the frame lists.

Full symbol tables with dependency-stall and cache columns are in the two indexed run folders, under phase003-0 and phase003-1. The game and bench implement different functions, so the phase and total tables give the comparable differences. The five-picture model has no calibrated mapping to physical frame rate.
