# eng-bench M1 handback, round 3

Renderer commit `863efd1e6`. The timing window covers drawing from resident tick inputs through PVR scene finish. PVR readiness waits and room load are outside the interval. Console drawing remains unmeasured.

## Absolute drawing budget

| Scene | Tier | Pictures | Mean ms | p99 ms | Worst ms | Over budget | Budget ms |
|---|---|---:|---:|---:|---:|---:|---:|
| cross | MODELLED | 25 | 45.759 | 54.319 | 54.319 | 25 | 10 |
| cross | Flycast guest timer | 300 | 43.523 | 50.207 | 53.947 | 300 | 20 |
| hayfork | MODELLED | 25 | 100.485 | 118.350 | 118.350 | 25 | 10 |
| hayfork | Flycast guest timer | 300 | 100.290 | 104.767 | 117.226 | 300 | 20 |

Model uses the nominal 200 MHz SH-4 simulator. The 20 ms comparator in the Flycast rows is the console target applied to guest-clock observations. Nearest-rank p99 equals the maximum at this model sample size. The staged Flycast rows use the first 300 pictures.

## MODELLED mean by drawing phase

| Phase | Cross ms | Hayfork ms |
|---|---:|---:|
| Setup and opaque world | 14.669 | 10.421 |
| Characters and modifier volumes | 27.363 | 84.282 |
| Punch-through world | 0.328 | 2.868 |
| Translucent world and hair | 2.369 | 1.773 |
| Effects | 0.714 | 0.828 |
| HUD | 0.314 | 0.311 |
| Scene finish | 0.002 | 0.002 |

## Windows and per-function profiles

- cross used pictures 1, 11, 23, 35, 47, 59, 71, 83, 95, 107, 119, 131, 143, 155, 167, 179, 191, 203, 215, 227, 239, 251, 263, 275, 287. The staged Flycast maximum was picture 1 (53.947 ms). The capture contains 111 distinct cameras. 9 model samples fall on camera changes.
- hayfork used pictures 11, 23, 35, 47, 59, 61, 71, 83, 95, 107, 119, 131, 143, 155, 167, 179, 191, 203, 215, 227, 239, 251, 263, 275, 287. The staged Flycast maximum was picture 61 (117.226 ms). The capture contains 100 distinct cameras. 10 model samples fall on camera changes.

- cross leading drawing functions, ms per sample: `native_actor_pass` 13.98, `native_world_pass` 7.50, `__fpclassifyf` 5.34, `fmaxf` 2.84, `clipped` 2.77.
- hayfork leading drawing functions, ms per sample: `native_actor_pass` 40.65, `__fpclassifyf` 18.70, `fmaxf` 9.91, `fminf` 9.72, `native_world_pass` 8.97.

Complete per-function profiles, including instruction-cache and data-cache costs, are in each room’s `full/functions.txt`, `world/functions.txt` and `characters/functions.txt` under the evidence directory. Each `timed-pictures.csv` records the seven phase spans, both still hashes and the matching logic tick.

The host replay of the same C selector supplies the meshlet counts in `world-piece-counts.csv`. The following ratios include input decode, selection, sky and masked hair charged in the respective intervals. They are inclusive workload ratios.

- cross selected 180?326 meshlets over the route. The three world-bearing model intervals averaged 77.9 microseconds per selected meshlet across the timed sample.
- hayfork selected 202?269 meshlets over the route. The three world-bearing model intervals averaged 65.2 microseconds per selected meshlet across the timed sample.

## Resident memory

| Room | Whole world bytes | Texture packages bytes | Model catalogue bytes | Recorded input tables bytes | Pack bytes | Live input scratch bytes | KOS allocated heap bytes | VRAM free bytes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cross | 1,424,536 | 1,860,520 | 289,556 | 4,155,912 | 7,743,584 | 86,260 | 9,314,620 | 3,093,064 |
| hayfork | 1,089,740 | 1,908,716 | 899,604 | 5,230,236 | 9,134,836 | 117,488 | 9,346,052 | 3,024,072 |

The boot reserves one 9,134,836-byte pack buffer for room changes. The linked span from the boot address through static storage is 1,016,220 bytes. Adding that span, 65,536 bytes below the boot address, and the sampled KOS heap gives cross 9.91 MiB of 16 MiB, hayfork 9.94 MiB of 16 MiB. This accounting excludes reservations outside those counters, including stack space. Video memory is separate. The rehearsal pack includes 300 recorded ticks. A live game would supply its own logic state and would have to budget that separately.

Heap 4 in the source room map spans 0x8c8ab500–0x8cfbf420 (7,421,728 bytes) in both reference snapshots. The source world mesh, placement and available strip-group files total 1,417,772 bytes at r101 and 1,085,960 bytes at r103. The native cell and placement bounds cover 223 placements at r101 and 134 at r103. The renderer loads the room before picture one and keeps the TA vertex buffer double-buffered.

## Coverage and controls

- cross considered 33–33 actor parts per picture and rejected 17–21 after runtime projection. The logic capture emitted 0 queued glyph records over 300 ticks.
- hayfork considered 148–148 actor parts per picture and rejected 28–135 after runtime projection. The logic capture emitted 0 queued glyph records over 300 ticks.
- The hayfork input includes all ten 34-joint barn props. Their geometry comes from the immutable source model parts. The bench projects shared model positions before part rejection. Source-side drawing was not timed or profiled.
- The private staged standard GDI booted both rooms for 600 pictures each. Clean-checkout boot bytes matched. The missing-pack build failed, and a deliberately invalid frame reference with a valid CRC was refused before drawing.
- The 5 ms delay control increased the paired cross guest-clock drawing time by 4.999 ms median and 4.992 ms mean over 300 pictures.
- The code uses the pinned SH4ZAM matrix load and FTRV operations. No SH4ZAM library kernel was added. The complete on-target cost of selection, projection and per-model lighting is included in the model traces.

## Visual and console status

Paired stills show the cross, flames, characters, scenery and moving hayfork view. Leon’s hair and lighting, the held weapon silhouette, the HUD mask and ammunition readout differ visibly from the source stills. Effect classes use a common native billboard path. Glyph replay has no natural on-screen sample in these windows. The packed model catalogue uses standard hand assets. Sprite-class specialization, exact masked HUD compositing, and character lighting parity remain open. Some selection, HUD and projection work repeats on unchanged input, so the timings include this repeated work. Owner visual approval and the 20 ms console measurement are outstanding. The actor rejection counts describe the native renderer. Historical game-side cull counts were not collected under the owner’s restriction on old-path profiling.

## Deliverables

- Staged disc: `E:\RE4DC-Lanes\eng-bench\build\M1-GDEMU-m1r3b\disc.gdi`. Track 3 SHA256 `e420b4cce94553be4cbdd2f0c21cf684071b18e05d3caf07f3467ae840092d98`. The neighbouring SHA256SUMS covers the descriptor and all three tracks.
- Boot SHA256 `077d5c10d6bee4f3f038e29f4ba2ff70e7e7e60c4c1dd4b991ab7c484fb32fbf`.
- Evidence: `E:\RE4DC-Lanes\eng-bench\runs\m1r3b-evidence`, with paired stills under each room’s `pairs` directory. The standard-disc observations are in `runs/m1r3b-standard`. Private capture and disc data stay in the lane.

Both scenes exceeded 10 ms on every timed picture. This is the final model-only handback under STEER-005. The staged image is available to the integrator for console measurement.
