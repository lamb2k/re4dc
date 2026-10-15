# SH-4 hw model calibration against the console benchmark (2026-10-15)

Every number is labelled. **CONSOLE** means the user's NTSC console running benchmark build 76f40d95: Part 1 run 2 and
Part 2 run 1, fast pacing. **MODELLED** means hwsim, the SH-4 hw model, at nominal penalties, replaying interpreter
traces of the same shipped disc. **REPRICED** means MODELLED cycles with each modelled cache miss charged at the
console's measured stall per miss. **FLYCAST** means the dynarec run of the same disc. All values are ms of CPU per
picture (one drawn tick plus K skipped ticks) unless a row says per tick. The WAIT part is left out of "work".

## 1. Bottom line

1. **The model sees the same program the console runs.** Its cache-miss counts are within 2-12% of the console's PMC
   counts (performance counters), in all four scenes. Logic comes out within 2-11%.
2. **The model under-charges each miss.** The console stalls about 24-25 cycles per D-cache miss and 25-26 per I-cache
   miss. The model charges 9-10 and 19. Because of that, the render parts come out 16-28% low and the D-stall share is
   half the console's (10-13% against 25-30%).
3. **The skipped tick is modelled within the logic factor (x1.08-1.11).** CORRECTED 2026-10-15 (lane/skiptick): the
   first version of this report said a skipped tick cost about 7 ms more on the console than in the model. That was
   my framing error, not a console cost. My traced frames were cut at the room-frame counter (after Render, mid-loop),
   so the next picture's build (Trans: ACTOR PREP and part of OTHER) landed in the "drawn" tick. The benchmark splits
   at the main-loop iteration, where a skipped iteration builds the kept picture. Split the same way, the model gives
   skipped 21.1 / 26.4 / 20.8 / 39.1 ms against CONSOLE 22.9 / 29.3 / 22.7 / 42.4 (section 3b). There is no
   unmodelled wait and no free 7 ms.
4. **The model is conservative on geometry cuts.** Its savings from removing the world or Leon are 15-25% smaller
   than the console's. For close Ganados they are 37-46% smaller.
5. **The model cannot speak for cache or layout tricks, disc stalls, the GPU or pacing.** Those levers need a console
   A/B.

## 2. Method: the same binary, mapped to the benchmark's own parts

- **Same program.** `1ST_READ.BIN` on both shipped GDIs is byte-identical to `objcopy` of
  `/root/probe/lanes/route/out-p4B/re4dc-game.elf` (76f40d95, BENCHMARK=1, PACE_MODE=fast). The model traced the
  shipped Part 1 and Part 2 disc images themselves in the hwtrace interpreter.
- **Frame windows.**
  - The live scenes are framed on the bench's `g_room_frame` (physical 0c4234f4), the same room-frame windows the
    console measures: cross 300..1199, house 1210..1595, Del Lago 600..1499, farm 300..1199.
  - The sweeps are framed on `pG->Frame_cnt` (0c365924). Only the last pass is used, because ticks restart at each
    scene's soft reset.
- **Bench parts.** I wrote a private hwsim copy (`hwsim-ph.c`; the timing model is untouched). It splits cycles,
  I/D stalls and I/D fills by bench part.
  - It finds every `re4dc_bench_phase` / `push` / `iter` call in the trace and reads the part number from the r4
    immediate at the call site. The table of 320 call sites is generated from the disassembly.
  - The BenchActorDraw resume is handled as a stack pop.
  - Unknown marks: **0** in every run, so the attribution is exact. It is not a function-name mapping.
- **Drawn and skipped ticks.** A traced tick counts as drawn when its ACTOR DRAW + WORLD DRAW time exceeds 1 ms. The
  interpreter paces differently from the console (it draws 47-97% of ticks), so a picture is built as
  model D + K x model S, with K = the console's skips per picture.
- **Sweep rows.**
  - Rows are assigned by guest time: 6.5 s slots, the first 2.0 s dropped, medians.
  - The frozen state hash matches the Flycast run (cross b4882f3e, farm 4d63b689), so the console froze the same
    frame.
  - The cross NO WORLD+FX row fell outside the traced window and is missing.
- **Runs.** Six interpreter runs, at most 2 at once, inside trace slots. Wall time was 2.5 min (cross) to 12 min (a
  full disc), plus about 1 min of hwsim per variant.
- **Evidence.** `D:\Flycast-Evidence\re4-dreamcast\hwcal-20261015\hw-{cross,house,dellago,farm,sweep6,sweep7}`.
  - Model output is in `proj\*.phases.tsv`.
  - The traces of the four live scenes are kept for re-simulation. The sweep traces were dropped, and a list of them
    was kept.

## 3. Calibration table: live scenes (CONSOLE / MODELLED, and the ratio console/model)

| part | Cross | House | Del Lago | Farm (disc-bound) |
|---|---|---|---|---|
| LOGIC | 33.1 / 30.3 = **1.09** | 45.8 / 41.4 = **1.11** | 26.7 / 26.2 = **1.02** | 65.0 / 62.9 = 1.03 |
| ACTOR PREP | 2.8 / 2.5 = 1.10 | 1.8 / 1.6 = 1.10 | 1.8 / 1.6 = 1.10 | 4.9 / 4.4 = 1.11 |
| ACTOR DRAW | 28.4 / 22.2 = **1.28** | 12.4 / 10.1 = **1.23** | 13.8 / 10.8 = **1.28** | 27.0 / 22.4 = 1.20 |
| WORLD DRAW | 19.1 / 15.3 = **1.24** | 7.2 / 5.9 = **1.23** | 2.2 / 1.9 = 1.16 | 17.8 / 14.0 = 1.27 |
| OTHER | 15.8 / 12.7 = 1.25 | 9.6 / 8.7 = 1.11 | 15.4 / 13.6 = 1.13 | 26.8 / 23.5 = 1.14 |
| **work per picture** | 99.2 / 83.1 = **1.19** | 76.8 / 67.6 = **1.14** | 59.9 / 54.2 = **1.11** | 141.5 / 127.2 = 1.11 |
| drawn tick, frame-cut split (superseded, see 3b) | 76.4 / 66.9 | 47.5 / 45.3 | 42.3 / 41.3 | 99.1 / 93.1 |
| skipped tick (K), frame-cut split (superseded, see 3b) | 22.9 / 16.2 (1.0) | 29.3 / 22.3 (1.0) | 22.7 / 16.1 (0.8) | 42.4 / 34.1 (1.0) |
| D-stall % | 30 / 13 | 30 / 12 | 27 / 12 | 25 / 10 |
| I-stall % | 21 / 16 | 19 / 15 | 16 / 11 | 18 / 14 |
| D misses, k per picture | 236 / 221 = 1.07 | 196 / 182 = 1.08 | 133 / 136 = 0.98 | 301 / 285 = 1.06 |
| I misses, k per picture | 162 / 144 = 1.12 | 115 / 106 = 1.09 | 73 / 65 = 1.12 | 204 / 182 = 1.12 |
| stall cycles per D miss | 25 / 10 | 24 / 9 | 24 / 9 | 24 / 9 |
| stall cycles per I miss | 26 / 19 | 25 / 19 | 26 / 19 | 25 / 19 |

The work-per-picture and per-part rows do not depend on how a picture is cut into ticks, so they stand. Only the
drawn/skipped split above was cut at the wrong point; section 3b replaces it.

**Penalty band.** MODELLED "high" penalties put work per picture at 0.94-0.99 of the console, by over-charging logic
(+7..+12%). It brackets the console; it is not a fit.

## 3b. Drawn and skipped ticks split like the benchmark (corrected 2026-10-15)

The benchmark charges each main-loop iteration (re4dc_bench_iter to the next) to "drawn" or "skipped". Under
PACE_CATCHUP=2 the order is: Render (draws the picture built last iteration), logic, then Trans builds the next
picture. So a skipped iteration builds the picture that the next, drawn iteration renders, and a drawn iteration
followed by a skip builds a picture that is dropped (cheap: OTHER 0.8-1.6 ms, ACTOR PREP 0.1). Re-simulated with a
segment cut at the first re4dc_bench_iter of each traced frame (hwsim-seg, `iter_split.py`), MODELLED nominal, ms:

| scene (K) | iteration | LOGIC | APREP | ADRAW | WORLD | OTHER | WAIT | work | CONSOLE work | ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| cross (1.0) | drawn | 15.1 | 0.1 | 22.2 | 15.3 | 9.4 | 0.7 | 62.0 | 76.4 | 1.23 |
| | skipped | 15.3 | 2.5 | 0 | 0 | 3.3 | 0.1 | 21.1 | 22.9 | **1.09** |
| house (1.0) | drawn | 20.5 | 0.1 | 10.1 | 5.9 | 4.7 | 0.7 | 41.2 | 47.5 | 1.15 |
| | skipped | 20.9 | 1.6 | 0 | 0 | 4.0 | 0.5 | 26.4 | 29.3 | **1.11** |
| Del Lago (0.8) | drawn | 14.8 | 0.4 | 10.8 | 1.9 | 9.7 | 4.7 | 37.5 | 42.3 | 1.13 |
| | skipped | 14.3 | 1.6 | 0 | 0 | 4.9 | 21.6 | 20.8 | 22.7 | **1.09** |
| farm (1.0) | drawn | 32.1 | 0.1 | 22.4 | 14.0 | 19.6 | 0.6 | 88.1 | 99.1 | 1.12 |
| | skipped | 30.8 | 4.3 | 0 | 0 | 3.9 | 0.2 | 39.1 | 42.4 | **1.08** |

(The LOGIC column here is the per-iteration logic; section 3's LOGIC is per picture, so it is about twice this.)

- The skipped iteration is logic plus the next picture's build. Its console/model ratio (1.08-1.11) is the logic
  factor; nothing is left over for a wait.
- The drawn iteration carries the render parts, so it takes the render factor (1.12-1.23).
- The top of a skipped iteration (before logic) is 0.4-0.5 ms MODELLED. A "cheaper skipped tick" lever has at most
  about 1-1.5 ms MODELLED to take (the dropped picture's OTHER and that top), below the console's detection floor.
- The benchmark now shows this split on the console: lane/skiptick 63c3ea48 adds a last results page, "DRAWN AND
  SKIPPED TICKS BY PART" (code 5), disc label SKIPT. It is an optional confirmation that can ride with a tranche.
  FLYCAST run of that disc (cross, ms per tick, D / S): LOGIC 9.4 / 9.4, ACTOR PREP 0.7 / 1.7, ACTOR DRAW 16.7 / 0,
  WORLD 11.9 / 0, OTHER 7.0 / 2.2, work 45.7 / 13.3. The same shape: the skipped tick holds the next picture's
  ACTOR PREP and OTHER, and nothing else. Evidence: `C:\Flycast-Evidence\re4-dreamcast\skipt-20261015\`.

**REPRICED.** Here every modelled miss is charged D 24.5 and I 25.5 cycles, the CONSOLE stall per miss.

| part | console/repriced, four scenes |
|---|---|
| ACTOR DRAW | 0.95-1.02 |
| WORLD DRAW | 0.95-1.05 |
| LOGIC | 0.86-0.88 (logic is now over-charged) |
| skipped tick | (frame-cut split; superseded by 3b) |

**FLYCAST, for contrast.** Console/Flycast is 1.41-1.69 per drawn tick and 1.32-1.72 per skipped tick (frame-cut
split). The model removes most of that error.

## 4. Calibration table: the sweeps (frozen, every tick drawn; CPU per drawn tick)

Cross sweep, r101 frame 1000:

| row | CONSOLE | MODELLED | ratio | delta CONSOLE | delta MODELLED | delta ratio | delta REPRICED, ratio |
|---|---|---|---|---|---|---|---|
| as shipped | 72.0 | 55.2 | 1.30 | | | | |
| half Ganado | 65.2 | 51.6 | 1.26 | -6.8 | -3.7 | **1.85** | -4.7, 1.45 |
| no Ganados | 60.4 | 47.9 | 1.26 | -11.6 | -7.4 | **1.57** | -9.3, 1.25 |
| no Leon | 64.5 | 49.2 | 1.31 | -7.5 | -6.0 | 1.24 | -7.5, 0.99 |
| world 18.8 m | 68.1 | 52.0 | 1.31 | -3.9 | -3.3 | 1.19 | -4.1, 0.95 |
| world 12.5 m | 64.1 | 48.4 | 1.32 | -7.9 | -6.8 | 1.16 | -8.6, 0.92 |
| no world | 49.0 | 36.1 | 1.36 | -23.0 | -19.2 | 1.20 | -23.7, 0.97 |
| no effects | 70.8 | 53.6 | 1.32 | -1.2 | -1.6 | 0.73 | -2.3, 0.53 |
| no world+fx | 47.5 | not traced | | -24.5 | | | |

Farm sweep, r103 frame 150:

| row | CONSOLE | MODELLED | ratio | delta CONSOLE | delta MODELLED | delta ratio | delta REPRICED, ratio |
|---|---|---|---|---|---|---|---|
| as shipped | 77.8 | 65.7 | 1.18 | | | | |
| half Ganado | 75.5 | 63.3 | 1.19 | -2.3 | -2.4 | 0.97 | -3.2, 0.73 |
| no Ganados | 73.0 | 62.3 | 1.17 | -4.8 | -3.4 | 1.41 | -4.2, 1.15 |
| no Leon | 70.9 | 59.8 | 1.18 | -6.9 | -5.9 | 1.18 | -7.3, 0.95 |
| world 18.8 m | 73.7 | 63.0 | 1.17 | -4.1 | -2.7 | 1.51 | -3.1, 1.32 |
| world 12.5 m | 65.6 | 55.1 | 1.19 | -12.2 | -10.6 | 1.15 | -13.0, 0.94 |
| no world | 55.0 | 46.5 | 1.18 | -22.8 | -19.2 | 1.19 | -23.6, 0.96 |
| no effects | 77.3 | 63.8 | 1.21 | -0.5 | -1.9 | 0.26 | -2.5, 0.20 |
| no world+fx | 53.5 | 45.9 | 1.17 | -24.3 | -19.7 | 1.23 | -24.2, 1.01 |

The model also shows the farm's extra fixed cost.
- **MODELLED frozen OTHER** is 24 ms at the farm against 13 at the cross. The console's frozen floor is +20 ms at the
  farm.
- **MODELLED live farm.** About 9 ms per tick goes to a CRC32 over reloaded motion data (`native_motion.cpp:414`
  `load()` -> `net_crc32le`), plus memset. So the motion thrash costs CPU as well as disc waits, and MOTION_COLD_POOL
  removes both.

## 5. Answers

**Within ±10% with no correction:**
- LOGIC per picture: -2..-10%.
- ACTOR PREP: -9..-10%.
- The skipped iteration, split like the benchmark: -8..-10% (section 3b).
- D and I miss counts: -2..-11%.
- Logic-type deltas. The earlier memlay A/B fits too:
  - MODELLED: A -0.3, B +0.5.
  - CONSOLE: A 0, B +0.3..+0.5.
  - The 4 Oct calibration gave logic x1.07.

**Within ±10% after the part factors or repricing:** ACTOR DRAW and WORLD DRAW absolute values (±5%), and the
world-distance, no-world and no-Leon deltas (0.92-1.01 REPRICED; 1.15-1.24 raw, so x1.2 holds them within ±6%).

**Not within ±10%:**
- The drawn iteration, split like the benchmark: -11..-19% (it carries the render parts; section 3b).
- Render parts uncorrected: -14..-22%.
- Close-Ganado draw deltas: x1.6-1.85.
- Small deltas under 2 ms, such as effects (the model overstates them) and the farm's world 18.8 m row.

**Where the model is biased:**
- **Cache-heavy work:** yes, and it is the main bias. Miss counts are right, but each miss costs 2.5x as much D stall
  and 1.35x as much I stall on the console. Skinning, transform, world walk and part setup are all under-charged by
  about 20-25%.
- **Logic:** slightly under, x1.02-1.11. It is the best-modelled part.
- **Indoors:** no separate bias. The house drawn iteration is -13% against -19% at the cross, because the cross is
  more render-heavy.
- **Skipped ticks:** no bias. The "missing 7 ms" of the first version was the next picture's build, which my frame
  cut put in the drawn tick (section 3b). The backlog's T_SKIP 6.4 is that build too: it scales with the picture's
  content (actors, effects), it is not a fixed overhead.
- **Disc stalls:** not modelled. The trace replays Flycast's drive timing, so the farm's LOGIC match (1.03) is not
  evidence. Only the CPU side of a reload (CRC, decode) is modelled.
- **GPU:** not modelled at all (CPU only).

**Does it model D/I misses?** Yes. Both caches are simulated and the miss counts match the console. It does **not**
reproduce the stall shares: D 10-13% against 25-30%, I 11-16% against 16-21%, because the stall per miss is too low.

## 6. Correction factors (MODELLED nominal to CONSOLE)

| quantity | factor | range seen |
|---|---|---|
| LOGIC (absolute or delta) | x1.06 | 1.02-1.11 |
| ACTOR PREP | x1.10 | 1.10-1.11 |
| ACTOR DRAW | x1.25 | 1.20-1.28 |
| WORLD DRAW | x1.23 | 1.16-1.27 |
| OTHER, drawn tick | x1.15 | 1.11-1.25 |
| skipped iteration (split like the bench) | x1.09 | 1.08-1.11 |
| drawn iteration, whole (split like the bench) | x1.15 (x1.23 at the cross) | 1.12-1.23 |
| delta: world vertices/distance, Leon | x1.2 | 1.16-1.24 |
| delta: close Ganados drawn (cross) | x1.6 | 1.57-1.85 |
| delta: far Ganados (farm) | x1.0-1.4 | 0.97-1.41 |
| delta: effects | x0.5 (the model overstates) | 0.26-0.73 |
| delta: cache, layout or code-placement levers | no factor; console A/B | |

If you prefer one rule for the render parts: reprice every modelled miss at D 24.5 / I 25.5 cycles, which gives ±5%.
Then multiply LOGIC by 0.87.

## 7. Trust policy for the performance backlog (PERF-BACKLOG-CH1-2-20261015 lever classes)

| lever type (backlog class / affects) | examples | accept on | correction |
|---|---|---|---|
| exact work removal in logic (exact; logic_fixed, ganados) | A2 (LQ_MEMO, FACE_LAZY), B2 collision cache | **MODELLED** | x1.06 |
| exact work removal in render (exact; render_fixed, props_verts, UI) | A2b census, A1/A1b bake, B3 UI OT cache, B4 world walk | **MODELLED** (console only when the tranche disc runs) | x1.25 render, x1.15 OTHER |
| vertex/asset cuts and render approximations (render-approx, conversion) | A9 PS2 cast, C4 flat lighting, C6, C1/C3 LOD, C2, C5 | **both**: MODELLED sizes it (it is conservative), CONSOLE confirms anything of 3 ms or more, and every close-Ganado cut | x1.2 world/Leon, x1.6 close Ganados |
| logic approximations / gameplay (logic-equiv, logic-gameplay) | D1 half-rate AI, D3, A7 waves, A8 hold-only | **both**: MODELLED x1.06 for sizing; the approximation rule needs console ms plus the decisions gate | x1.06 |
| cache, code or data layout | A6 LINK_ORDER, B5 code size, B6 prefetch, memlay | **CONSOLE A/B only** (miss penalty x2.5 low; layout shifts between images) | none |
| disc, streaming, VRAM residency | A3 cold pool, A5 resident lists, E2 | **CONSOLE** page 1 READS + WAIT; a Flycast read count of 0 is an exact pre-screen | none |
| pacing, waits, TA submission, GPU | F1, TA DMA, fog/fill ("cheaper skipped tick": at most about 1-1.5 ms MODELLED, section 3b) | **CONSOLE only** | none |
| effects (B8) | FX_LEVEL | MODELLED overstates; count at most half | x0.5 |

**Five-line policy:**
1. Exact work-removal levers (logic or render) are accepted on MODELLED ms × factor (logic ×1.06, render ×1.25,
   OTHER ×1.15). Gains under 1 ms need no console (they are below the noise).
2. Geometry and asset levers are sized on MODELLED (conservative: the console gives ×1.2, close Ganados ×1.6). The
   console confirms anything of 3 ms or more before it is quoted as fps.
3. Logic approximations need both: MODELLED for sizing, CONSOLE ms plus the decisions gate to offer them (approximation
   rule).
4. Cache, layout and placement levers, disc and streaming, skipped-tick, pacing and wait levers, and GPU levers are
   accepted on a CONSOLE A/B only.
5. Write corrected numbers as "MODELLED-corrected". The console tranche disc is the only source of a CONSOLE ms.

## 8. The leanest console loop

**Noise (CONSOLE):**

| comparison | cross CPU/tick | house CPU/tick | reading |
|---|---|---|---|
| same disc, two runs (12.1 bench) | 47.1 / 47.6 | 37.4 / 37.5 | ≤1%: about ±0.3 ms |
| different images with no CPU change (control, Bench A, Bench B, LO-CTL) | 46.9-47.4 | 37.4-37.9 | ±0.3 ms |
| Part 1 run 2 (definitive bench) vs LO-CTL | 50.3 vs 46.9 | 38.5 vs 37.5 | **+3.4 / +1.0, and GPU +1.6.** Not noise: a different bench version. The model puts the bench's own code at 0.07 ms/tick, so part of the CPU shift is scene content (GPU moved too) and part is likely layout. Never compare across bench versions. |

- **Detection floor.** One run pair detects about 1 ms per tick (2 ms per picture) at 2σ. Repeat a disc only when
  its delta is under 2 ms per tick or its sign is surprising.

**Loop:**
1. **Model first, every lever.** Trace the cross and house scenes on the bench build: about 3 min of Flycast each,
   plus 1 min of hwsim-ph. That gives MODELLED per-part ms in the console's own parts. Class 1 (policy line 1) stops
   here.
2. **One disc per tranche, not per lever.** Put every class 2-4 lever of the tranche into one bench image as runtime
   toggles. One binary means no layout noise between arms, and the control is just the "all off" row.
   - Render-only toggles become extra sweep rows (6.5 s each, frozen frame). About 10 extra rows add about 1 min.
   - Logic or exact toggles run the live 30 s scene once per setting, chosen by the fixture.
3. **Separate images only where the lever is the layout** (LINK_ORDER, -Os, data layout).
   - Pair each such image with a control built from the same tree at the same time.
   - Run the control first and last in the trip, to bracket drift.
   - Use at most 2-3 such images per trip.
4. **Per SD trip:** one tranche disc plus at most 3 layout images. That is about 15-25 min of console time and one set
   of photos/CODE lines.
5. **Control reuse.** A control image is valid for as long as its base build is the one being compared. Re-running it
   once per trip costs about 5 min and catches drift; a new base needs a new control.

## 9. Model gaps, fixes and their cost (not built)

| gap | evidence | fix | cost |
|---|---|---|---|
| **1. D-miss stall too low (top gap):** 9-10 cycles per miss against 24-25 on the console; I 19 against 25-26 | miss counts match within ±12%; repricing the misses brings render parts to ±5% and world/Leon deltas to ±8% | In `hwsim.c` `oc_access`: an option that blocks a demand read miss for the full line (no critical-word early restart), or a per-miss latency fitted to 24.5. Then re-check logic, which is over-charged by 12-14% once repriced (look at the dep_load/branch charges). Optional: a pointer-chase / 16 KB code loop page on the next bench disc to measure the penalty directly. | about 1 day (option + re-sim of the 4 kept trace sets + 2 sweep re-runs of about 12 min each); +0.5 day for the microbenchmark page |
| 2. ~~About 7 ms per skipped tick, unmodelled~~ CLOSED 2026-10-15: not a gap | split like the bench, the skipped iteration is x1.08-1.11 (section 3b) | Done: the bench split page (lane/skiptick 63c3ea48, SKIPT disc) shows it on the console when it rides with a tranche | none left |
| 3. Close-Ganado draw ×1.45 even after repricing | cross half/no-Ganado rows | Check the TA/SQ back-pressure on the many small Ganado strips (the model only bands the SQ cost); compare the ACTOR DRAW D/I stall% on console pages | 0.5 day of analysis |
| 4. No disc-wait or GPU model | by design | Use console page 1 (READS, WAIT, GPU); Flycast read counts as a pre-screen | none |
| 5. Bench-part attribution is not in hwproject | built privately here | Upstream `hwsim-ph` (`--phase`) and `phase_sites.py` into hwproject, so every cost arm reports the console's parts | 0.5 day |

Tools and outputs:
- `D:\Flycast-Evidence\re4-dreamcast\hwcal-20261015\tools\`: hwsim-ph.c, mk_hwsim_ph.py, phase_sites.py,
  phase-sites.txt, run_hw.sh, hwrun.ps1, an.py, an_sweep.py, calib.py, calib2.py, gdi_extract.py.
- Full tables: `calib.md` (nominal/high/pen24/pen32) and `calib2.md` (REPRICED).

## 10. Miss-penalty fix (2026-10-15 evening, lane hwmodel-miss, branch tools/hwmodel-miss 37186a71)

Gap 1 of section 9 is built. hwsim `--console-fit` adds 4 cycles per I fill and 70 cycles per store that misses
(read-miss latency +0 fitted best: extra read latency raised logic as much as render). hwproject.sh now writes a
"console" what-if column next to nominal. Re-simulated on the four kept hwcal trace sets, console/model per part goes
from 1.02-1.28 to **0.91-1.05** (weighted RMS log error 0.153 -> 0.039); work per picture cross 96.9 vs 99.2 CONSOLE,
house 76.6 vs 76.8, Del Lago 62.9 vs 59.9, farm 144.1 vs 141.5. Stall per D miss 9-10 -> 18-22 (console 24-25).

**New trust-policy factors (MODELLED console-fit to CONSOLE):** LOGIC, ACTOR PREP, ACTOR DRAW, WORLD, OTHER all x1.0
(+-5%; Del Lago logic 0.91). Label these "MODELLED console-fit". The section 6 factors stay valid for nominal-only
numbers. Cache/layout/placement, disc, pacing and GPU levers remain console A/B only. Sweep deltas (x1.2 geometry,
x1.6 close Ganados) were not re-checked (sweep traces dropped).

Re-priced levers (ms per drawn tick, nominal -> console-fit): SH4ZAM memset/memcpy cross -0.50 -> -1.10, house
-0.86 -> -2.04; SG_SELECT_LEAN -0.70 -> -0.91; GC_CENSUS_TRIM -0.28/-0.37 -> -0.33/-0.28; B5 HOT_COLD_SPLIT cross
-0.33 -> -0.24 (layout: console only); Leon u70 cross -0.72 -> -0.97, house -0.11 -> -0.12; logic-waste arms move
<0.05; the ll-cross and g70 pairs show no change at all (fixture did not engage; re-run). Details and the lanes that
must re-run: port/dreamcast/docs/lanes/hwmodel-miss.md.
