---
name: re4-dreamcast-console-benchmark-20261015
description: First console benchmark-disc result (10-15, test 12.1): CPU-bound, no disc waits, GPU 15-18 ms; console/Flycast CPU 1.39 (r101 actors) vs 1.23 (r100 house)
metadata:
  type: project
---

User's NTSC console + GDEMU ran the public benchmark disc 7b6bbd09 (test 12.1 + BENCHMARK) twice on 2026-10-15:
- r101 cross: 10.5 fps (min 8.9), CPU 47.1 ms/tick, GPU 18.5 ms, speed 71%, reads 0, wait 0.
- r100 house: 13.2 fps, CPU 37.4, GPU 15.1, speed 88%.
- Runs repeat within 1%.
- Flycast, same disc: CPU 33.8 / 30.4.

**Why it matters:** it settles the 10-15 hypotheses.
- CPU-bound.
- The GPU is not the limit (hardware fog fixed the mist fill).
- Disc reads are not the cause in these scenes.
- The console's extra cost grows with actor work (1.39 with Ganados vs 1.23 without), which points to memory latency in skinning/transform.

**How to apply:**
- Use console/Flycast CPU 1.39 for r101 fights and 1.23 for quiet interiors when projecting.
- Prioritise actor CPU work: Ganado skin/transform data layout, far-update rate, the object bake.
- Put a benchmark variant beside each perf candidate so the user's photo gives a console A/B.

Related: [[re4-dreamcast-benchmark-window]], [[re4-dreamcast-hwcal-console-result]].

**Goal (user 10-15 morning):** the r101 cross must reach 20 fps on real hardware (now 10.5). A Fable 5.1 xhigh reviewer is challenging the diagnosis and plan from current data (benchmarks + math libraries); report RE4DC-PERF-ALT-VIEWS-20261015.md.

**Correction (Fable review 10-15, RE4DC-PERF-ALT-VIEWS-20261015.md):** bench CPU is averaged over drawn AND skipped ticks. At the cross the console draws every 2nd tick (PACE_CAP=1 limit): one picture = drawn tick D (~74.5 ms, inferred) + skipped tick S (~20 ms, inferred) = 94.2 ms -> 10.5 fps. The "x1.39 memory latency on actors" story is NOT supported: console/model per drawn tick = 1.10; I-cache misses (134k/frame) dwarf D-cache (26k); top D-miss is the world transform. 20 fps real time needs D <= 40 (-46%); 20 fps in slow motion needs D <= 50. Exact levers priced at -11..-16 ms (LINK_ORDER regen for I-cache, clears removal, skip-tick trims, bake, native part list); +look/gameplay-equivalent levers -> D ~46-52 (14-15 fps real time, 19-21 slow motion). D<=40 needs fewer world vertices/parts in view (asset decision). Always name the pacing mode with any fps.

**User target (10-15 09:30):** "I really want 30 fps but ok with it slowing down to 20 fps at the cross if needed." Read as: 30 fps is the goal everywhere (drawn tick D <= 33 ms on the console); the r101 cross may drop to 20 fps worst case, game may slow there (option B: D <= 50 ms console with skips blocked, as Smooth does). Lanes report console D at the cross against 50 (floor) and 33 (goal).

**Bench A (ACTOR_MOVCA, a3db2b71) on console 10-15:** cross 10.5 fps (min 8.7), CPU 47.2, GPU 17.3, SPD 70; house 13.2 (12.7), CPU 37.4, GPU 15.1, SPD 88; KOS 118/126. = control (47.1/47.6, 37.4/37.5) within noise: write-allocate on actor scratch saves nothing measurable; hw model (-0.3) was right.
**Bench B (MEM_MOVCA, a3db2b71) on console 10-15:** cross 10.4 fps (min 8.9), CPU 47.4, GPU 18.0, SPD 70; house 13.0 (12.7), CPU 37.9, GPU 15.1, SPD 87; KOS 118/125. Slightly worse (house +0.5 ms) = hw model's +0.5. Both memlay arms parked: write misses are not the console bottleneck; the hw model's non-blocking write-miss charge is validated.
**User 10-15:** "speed group 1 should happen regardless" (exact items: test 13 bake/small savings, LINK_ORDER regen, clears removal, native part list for PS2 dynamic parts, census trims, double/presort). Owners: RC lead (13), approx->linkorder lane, memlay (ACTOR_NO_CLEAR), new lane/g1parts (part list + census + small fixes). Group 2/3 + bench v3 scope still pending the user's call; leanest v3 = add one r103 outdoor scene to v2 if cheap.
**User 10-15:** "i don't want to wait for a lot of game that doesn't exist yet" -> perf planning uses only released content (chapters 1-1..2-1). No castle/island benchmark scenes (Del Lago r10b IS released, ch 1-3: v3 scene 4), no waiting on unfinished chapters; the 30 fps budget count covers released route rooms only. Benchmarks: cross + house + r103 farm + Del Lago (v3).

**Console run of "v2" 03a4813a (10-15 ~10:30) — PACKAGING ERROR: scenes 1-2 were WIP farm views "FARM A230"/"FARM A190" (r103), not cross/house; page 3 = r101 cross frozen sweep.** Data (console, MEASURED):
- Farm A230: 6.0 fps (min 4.9), CPU 88.7 ms/tick, GPU 24.5, SPD 40, disc reads 37.9/s, WAIT ON DISC 161 ms/s, KOS 152. A190: 6.1, 84.4, 25.9, 41, 38.1/s, 163 ms/s.
- Farm per picture (1 drawn + 1.0 skipped): LOGIC 59.6 (~30/tick!), ACTOR PREP 4.9, ACTOR DRAW 27.8, WORLD DRAW 18.4 (A190 14.2), OTHER 28.6 (~ disc waits), WAIT 0.8, TOTAL 140 ms; drawn tick 99.4 + skipped 39.9; stall 26%; I-miss 217k (20% stall), D-miss 303k per picture.
- CORRECTION: page 3 "R101 CROSS" title was hard-coded; the sweep was FARM A270 (r103, frozen room frame 90). Farm frozen (every tick drawn): as shipped 25.3k verts, CPU 65.4, actor 24.6, world 18.2, GPU 29.4, ST 29%. No Leon: 18.6k, 58.6 (Leon ~6.8 ms, ~1.0 ms/1k). World 18.8 m: 17.4k, 58.8; world 12.5 m: 13.1k, 54.6 (world ~0.85-0.9 ms CPU per 1k verts). Half/no Ganados: verts unchanged (no Ganado in view at the frozen frame) -> CPU 63.3 (Ganado logic/prep ~2 ms).
Takeaways: r103 farm is the worst scene (6 fps) with heavy in-play disc reloads (VRAM rule gap) + logic ~30 ms/tick; ~26-29% of CPU is memory stall, I-cache ~20%.
**Motion streaming is game-wide (10-15):** farm r103 reads = Ganado motion-key cache thrash (archive 1.1 MB, hot set ~950 KB, MOTION_PRESSURE_BYTES cap 256 KB -> ~77 loads/s; VRAM fine). Castle r209: Zealot motion archive 1.36 MB through two 32 KB slabs, ~64 reads/s, 0.7 fps close-up (Flycast). Fix generically (per-room motion residency; cap vs compact encoding vs VRAM L2 cache), owned by the VRAM/crash lane. Benchmark tranches: 1 = v2 03a4813a (cross/house/sweep, on SD); 2 = farm A230 + Del Lago (weak monster view; warp-only fixture e409e042) + sweeps with Ganados + no-world; 3 = r209 castle (needs whole castle lane merged, separate program).
**Group 1 tally (10-15, MODELLED, cap 6 r101):** STATIC_OBJ_BAKE ~-3 (test 13); ACTOR_NO_CLEAR -0.8 (d270ca82); g1parts G1_DIAG_INLINE/G1_FP_UNSIGNED/G1_PRESORT_LAZY ~-0.3 (7979c550, all gates pass); native part list NO-GO (best 0.2-0.5); per-part repeated work ~0.2-0.4 (not built); LINK_ORDER regen pending. Exact group 1 ~ -4..-5 ms, far below the review's -11..-16. Bigger levers now: motion streaming (farm/castle disc reads), logic (Ganado ~0.85 ms each/tick, Leon cloth 1.5), triangles (~0.9-1 ms per 1k).
**LO-CTL (12.2 + bench v1, 12.2 code order) console 10-15:** cross 10.5 fps (min 8.9), CPU 46.9, GPU 18.0, SPD 71; house 13.1 (12.7), CPU 37.5, GPU 14.6, SPD 88; reads 0; KOS 118/125. = 12.1 benchmark within noise: 12.2 changed nothing for speed. Reference for the fixed LinkOrder A/B.

**Bench Part 1 CONSOLE (build 76f40d95 = 12.1 + bench, run 2, fast pacing, 10-15 ~12:30):**
- P1: cross 9.9 fps (min 8.5), CPU 50.3/tick, GPU 19.6, SPD 66; house 12.8 (12.7), CPU 38.5, GPU 14.6, SPD 86; reads 0.1/0.0, KOS 120/130. (~3 ms/tick above LO-CTL 46.9: bench counters or run variance.)
- P2 ms per picture (1 drawn + skipped): cross LOGIC 33.1 APREP 2.8 ADRAW 28.4 WORLD 19.1 OTHER 15.8 WAIT 0.6 = 99.8; house 45.8/1.8/12.4/7.2/9.6/0.6 = 77.4. D-cache stall share ~30% in EVERY bucket (both scenes).
- P3: cross DRAWN 76.4 + 1.0 skip x 22.9 ms, 33.2k verts/picture, 213 headers; house drawn 47.5 + 1.0 x 29.3 (house is LOGIC-bound: skip > half drawn), 9.4k verts, 79 hdrs. D-stall 30%/236k misses, I-stall 21%/162k (cross); house 30%/196k, 19%/115k. => ~50% of CPU time is cache stalls.
- P4 cross sweep frozen f1000, 5 Ganados, drawn every tick (vertk / CPU / actor / world / GPU): as shipped 41.0/72.0/35.7/18.9/17.2; half Ganado 35.2/65.2; no Ganados 31.4/60.4 (5 Ganados = 9.6k verts, 11.6 ms, ~2.3 ms each render); no Leon 34.3/64.5 (Leon 6.7k verts, 7.5 ms); world 18.8 m 37.3/68.1 (-3.9); world 12.5 m 33.1/64.1 (-7.9 ms, world 11.8); NO WORLD 26.7/49.0 (world = 14.3k verts, 23.0 ms CPU = 1.6 ms/1k incl. world fixed, GPU -6.5); NO EFFECTS 40.0/70.8 (effects only 1.2 ms CPU, 0.3 GPU); NO WORLD+FX 25.8/47.5. Marginal CPU/1k verts 1.0-1.2 (chars/world distance), GPU/1k 0.12-0.2 chars, 0.45 world.

**Bench Part 2 CONSOLE (76f40d95, run 1, fast pacing, 10-15):**
- P1: Del Lago 16.4 fps (min 12.7), CPU 33.9, GPU 16.5, SPD 97, reads 0.1, KOS 172; farm 5.8 (4.4), CPU 85.9, GPU 24.0, SPD 39, reads 34.6/s, WAIT 172 ms/s, KOS 152.
- P2 per picture: Del Lago LOGIC 26.7 APREP 1.8 ADRAW 13.8 WORLD 2.2 OTHER 15.4 WAIT 0.7 = 60.6; farm 65.0/4.9/27.0/17.8/26.8/0.8 = 142.3. Mem wait all 27% / 25%.
- P3: Del Lago drawn 42.3 + 0.8 x 22.7, 10.6k verts, 69 hdrs, D 27%/133k I 16%/73k; farm drawn 99.1 + 1.0 x 42.4 (logic ~32/tick: motion-key disc thrash, fixed by MOTION_COLD_POOL in T14), 30.1k verts, 212 hdrs, D 25%/301k I 18%/204k.
- P4 farm sweep frozen (vertk/CPU/actor/world/GPU): shipped 31.5/77.8/32.9/17.3/29.0; half Ganado 29.6/75.5; no Ganados 26.7/73.0 (5 Ganados only 4.8k verts, 4.8 ms here: far/small); no Leon 24.8/70.9 (Leon 6.7k, 6.9 ms); world 18.8 m 26.9/73.7; world 12.5 m 19.0/65.6 (-12.2 ms, GPU -3.1); NO WORLD 14.1/55.0 (world 17.4k verts, 22.8 ms CPU, GPU -14.0: farm GPU 29 ms is world fill); NO EFFECTS 30.5/77.3 (-0.5 CPU, -1.0 GPU); NO WORLD+FX 13.1/53.5. Farm frozen floor 53.5 ms at 13.1k verts vs cross 47.5 at 25.8k: ~20 ms farm-specific non-vertex cost (suspect streaming/other) -> remeasure after cold pool.
- Cross-scene: cache stalls 41-51% of CPU in every scene; effects cost <=1.2 ms CPU everywhere; world distance cut (12.5 m) = -7.9 cross / -12.2 farm.
