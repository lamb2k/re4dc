# RE4 Dreamcast: alternate views on the 20 fps village plan (critical review, 2026-10-15)

Analysis only. No builds, no runs, no commits. Every number is labelled MEASURED (console), FLYCAST (emulator),
MODELLED (SH-4 hw model) or INFERRED (arithmetic on the above). Sources are cited by path and line.

## Plain-English summary (for a non-programmer)

1. **The console is doing exactly what the model said it would.** At the burning cross the console draws a frame, then
   runs one "silent" game step without drawing to catch up, then draws again. One drawn step costs about 74 ms of
   processor time and one silent step about 20 ms, so a picture appears every ~95 ms: 10.5 fps. The hardware model
   predicted ~67 ms for the drawn step. That is a 10% miss, the same as on the 4 October calibration. The story that
   "the console is 37% slower than the model and the model's gains don't show up" came from reading an fps counter
   by eye and comparing a *drawn step* with a *whole frame*; it does not survive the benchmark disc's numbers.
2. **"20 fps" has been used to mean two different things.** 20 fps *at full game speed* needs the drawn step under
   ~40 ms on the console (it is 74 now: nearly half must go). 20 fps *in slow motion* (the game at 2/3 speed) needs
   it under 50. The "50 ms hardware-model gate" in the plan buys the slow-motion version, or ~14 fps at full speed.
   The user should pick which "20" is meant; the plan currently promises the first and is engineered for the second.
3. **The silent step matters more than people think.** At 20 fps real time the game runs 30 logic steps and 20 drawn
   frames a second, so every millisecond saved in game logic is worth 1.5 ms saved in drawing. Nobody is working on
   logic right now; all lanes are on drawing.
4. **Memory, yes; but probably *instructions*, not data.** The only console counter run so far (4 Oct) shows the
   processor missing its instruction cache five times more often than its data cache while drawing. The in-flight
   "memory layout" work targets data. Benchmark v2 (already built) reads both counters per part of the frame; run it
   on the console before building any more layout arms. A cheaper, exact lever (re-generating the code placement
   file, which is still the 5 October profile) is sitting unused.
5. **Faster maths won't do it.** All matrix-multiply calls together cost ~0.7 ms of a 67 ms frame, sine/cosine less
   than that. Bruce's FSCA/FTRV commits and the sh4zam library would save well under 1 ms per frame and would break
   the "same decisions" guarantee if used in game logic. They are a code-size and tidiness item, not a speed item.
6. **The honest total.** Everything exact and structural that can be named adds up to about 12-17 ms off the drawn
   step on the console (74 to ~60: ~12.5 fps real time). Adding the levers the user has now allowed (gameplay
   equivalent, judged on look) gets to roughly 48-52 ms (~14-15 fps real time, or 20 fps in slow motion). Nothing on
   the list reaches 40 ms. Reaching 20 fps real time at the cross would need a different village (fewer world
   vertices and parts in that view), not more tuning.

## 1. Frame budget at the cross, reconstructed

### 1.1 What the benchmark disc measures
`port/dreamcast/game/bench.cpp` (677229c8) lines 24-31: FPS = drawn frames / vblanks x 59.94; SPD = game ticks per
(vblanks/2), i.e. 100% = 29.97 ticks/s; CPU = mean of the game's own "PROCESS CPU" stamp (`tick_log.cpp` `cpu` =
ticks[2]) over all ticks, drawn and skipped alike; GPU = mean ISP_START to render-done per render.

What "CPU" contains (`src/game/main.cpp` 255-365): `Render()` (the previous tick's OT, i.e. all actor/world
submission) runs BEFORE the `RENDER SETUP` stamp, then TaskScheduler (logic), Trans(), DrawOTag (UI), then the
`PROCESS CPU` stamp; the vblank wait comes after. So CPU is the whole tick's processor work and excludes waits.
In Flycast on the same disc the split is visible (`C:\Flycast-Evidence\re4-dreamcast\benchpub-r1-7b6bbd09\run-output.txt`
lines 3030-3040, PT rows): total 33.5 = setup 21.2 (= Render of the previous tick) + logic 9.6 + trans 2.4 + post 0.03;
`cpu` 33.3 = total. `PHASES:` rows (same file) give logic 8.2, fx move 1.4, fx trans 1.2, objs 1.0, other 0.3.

### 1.2 Pacing: what a frame is
`pace.cpp` 1-28 and 174-187: logic ticks on a 29.97 Hz anchor clock; a tick that starts >= 2 vblanks behind skips
its draw (`want_skip`: `lag < 2 -> 0`); at most `PACE_CAP` = 1 consecutive skip (`pace.mk` 79), so the worst pattern
is drawn, skipped, drawn, skipped: 2 ticks per picture; lag beyond that is dropped (slow motion). The recipe runs
`PACE_CATCHUP=2 PACE_MODE=fast` (`tools/d367/README.md` 47; v2 drops ModelTrans on a dropped image). Players default
to Smooth (`PACE_FLOOR_FPS ?= 15`, `pace.mk` 81): a skip is allowed only if present-to-present stays <= 66.7 ms.

### 1.3 Console numbers (MEASURED, memory note re4-dreamcast-console-benchmark-20261015, disc 7b6bbd09)
r101 cross: 10.5 fps, SPD 71%, CPU 47.1 ms/tick, GPU 18.5, reads ~0, wait 0-1 ms/s.
- ticks/s = 0.71 x 29.97 = 21.3; drawn/s = 10.5; ticks per picture = 2.03. The pacing is at its cap: every picture
  is one drawn tick D plus one skipped tick S, and the surplus lag is dropped (hence 71%).
- D + S = 2 x 47.1 = 94.2 ms of CPU per picture; wall per picture 95.2 ms. About 1 ms of non-CPU time per picture:
  **CPU-bound by arithmetic, not by assumption.** GPU (18.5) overlaps (kos-async pipeline, fence waits 160 ms over
  960 frames in Flycast, `native pipeline:` line 3034).
- r100 house: 13.2 fps, 88%, 37.4: ticks per picture = 2.0 again (cap-limited); D + S = 74.8.

### 1.4 Splitting D and S (INFERRED)
Page 1 cannot split D from S. Two independent anchors:
- FLYCAST, same disc: 18.6 fps, 98%, 868 ticks / 550 drawn (63% drawn), CPU 33.8; PT max 50.5. S_fc ~ logic 9.6 +
  trans 2.4 + ~0.5 = 12.5; D_fc = (33.8 - 0.37 x 12.5) / 0.63 ~ 46. (hwproject's own "Flycast-charge" for the
  cap-6 build is 47.4: `bench-20261014\hwmodel-hV6-r101\proj\report.txt` line 1.)
- MEASURED on the console on 4 Oct (`/root/probe/hwcal-v/CONSOLE-RESULTS-20261004.md`): LOGIC (gameMainLoop, every
  tick) P50 = 18.3 ms with 6 Ganados, model/Flycast logic ratio 1.54, console/model 1.07. With cap 6 (6 alive) the
  skipped tick is logic + trans + leftovers: **S_console ~ 20 ms (18-23)**.
- Therefore **D_console ~ 94.5 - 20 = 74.5 ms (72-77)**. Console/Flycast per drawn tick ~ 1.6; per skipped tick ~ 1.6.
- MODELLED drawn tick for the cap-6 recipe: 67.51 (`hwmodel-hV6-r101\proj\report.txt`). **Console/model = 1.10**,
  inside the 4 Oct calibration (1.07 logic, 0.95-1.06 render). The model's "what-if high" (81.2) brackets it.

### 1.5 What 20 fps requires (INFERRED from the pacing rule; GPU is not a term)
Let L = logic+trans per tick (S), R = render CPU per drawn tick (D - S). At full speed the CPU must fit
30 L + f R <= 1000 ms/s, where f = pictures per second.
| Meaning of "20 fps" | Condition | Console today | Needed change |
|---|---|---|---|
| 20 fps at 100% game speed (Fast pacing, pattern D D S) | 30 S + 20 R <= 1000; with S = 20: **D <= 40** | D ~ 74.5 | **-34.5 ms (-46%)**, i.e. a drawn tick ~5 ms *faster than Flycast on the host PC today* |
| 20 fps at 67% speed (slow motion; Off pacing, or Smooth with skips blocked) | D <= 50 | 74.5 | -24.5 (-33%) |
| The plan's gate "benchmark-r101 <= 50 ms hw model" | D_model <= 50 -> D_console ~ 55 | 67.5 model | pair 75 -> **13.3 fps real time**, or 18 fps slow motion |
| 15 fps at 100% speed (pattern D S) | D + S <= 66.7 -> D <= 46.7 | 74.5 | -28 |
Every 1 ms off S is worth 1.5 ms off R at the 20 fps steady state (30 L vs 20 R), and S is where nobody is working.

### 1.6 Where our own arithmetic does not add up
1. **Drawn-tick ms read as a frame period.** VILLAGE-LEVERS-20261014.md line 239: "the model (~66 ms ~ 15 fps)". With
   catch-up pacing a picture costs D + S; 66 model + ~18 model skip = ~84 model -> ~92 console -> ~11 fps. The
   console's 10.5 fps is the model's prediction, not a contradiction of it. hwcal's PREDICTIONS.md (section
   "Important: r21v paces with PACE_MODE=fast") already said to compare pair means; the lever doc dropped it.
2. **"Console/Flycast 1.39 with actors vs 1.23 quiet, so actor work costs more on the console"** (memory note
   re4-dreamcast-console-benchmark-20261015; VILLAGE-LEVERS 388). Both ratios are averages over different drawn/skip
   mixes: Flycast's house draws every tick (30 fps, 480/480), the console's house draws half. Per drawn tick the
   house ratio is ~1.8-1.9 (D_fc 30.4 vs D_console ~57; S_fc 11.3 from the PHASES rows at lines 4446-4497) and the
   cross ratio ~1.6. The sign is the opposite of the conclusion. The r100 house is an interior with 4-5 Ganados; it is
   not an "actor-free" control.
3. **"The model is uniformly ~37% optimistic; scale by x1.37"** (VILLAGE-LEVERS 239). Derived from the user's eye
   reading of the fps counter on preview 2 (12.5 fps at the cross with 0 alive) plus an assumed skip tick. The
   benchmark disc, read by its own code, gives 1.10 with 6 alive. If both readings are right, the under-charge sits
   in the *non-actor* part of the frame (world, objects, effects), again the opposite of the memory-layout premise.
   The x1.39 used to project test 13 (VILLAGE-LEVERS 389) should be x1.1 until benchmark v2 says otherwise.
4. **Console CPU per tick on 5 Oct and 15 Oct are the same number.** r22g fight C (`D:\Flycast-Evidence\re4-dreamcast\
   console-r22g-20261005\CONSOLE-RESULTS.md`): CPU 142% x 33.37 = 47.4 ms/tick, pair 94.8. Benchmark 10-15: 47.1,
   pair 94.2. Different scenes (house fight, 3 drawn, GPU 53 vs cross, cap 6, GPU 18.5), so not a strict A/B, but
   20 model ms of claimed gains since (86.9 -> 67.5 on r101) have not produced a console pair that differs from the
   r22g fight. The 4 Oct GAN6 window (r21v) was ~110 ms per pair (LOGIC 18.3 + MCYR 75 ms), so there is progress
   against *that* image; it is smaller than the model's delta suggests. Benchmark v2 at the same spot decides.
5. **The gate is for the wrong quantity.** TEST12-SCOPE.md 36 sets "r101 at 20 fps = 50 ms per drawn frame, CPU and
   GPU each <= 50". With pacing, "per drawn frame" is D + S, and S alone is 20. The gate as written is 13-14 fps.

## 2. Challenging "CPU-bound, memory latency in actor skinning"

CPU-bound: confirmed (1.3). "Memory latency": plausible but the *kind* and *place* are unproven. Candidates, with the
evidence we already hold and the single cheapest measurement that settles each:

| Hypothesis | Supports | Contradicts | Settles it |
|---|---|---|---|
| A. D-cache latency on skinned-vertex data (the memlay premise) | hw-only census: transform_sched 3,400 D-misses/frame top, avk_pos_skin_u16 1,050 (RE4DC-HW-ONLY-COSTS-20261015.md "Top operand-cache miss pcs") | The top D-miss pc is the **world** transform, not skinning. Model dmiss for actors+render-side = 4.4 of 67.5 ms (`report.txt` breakdown: actors 1.2, game-render-side 3.3); even at 2x real latency the actor share is ~2.5 ms. Console 4 Oct: D-REND 26k misses/drawn frame vs I-REND 134k | Benchmark v2 page 2 (4fe2957e `bench.cpp` 94-96: events 0x25 D-stall cycles, 0x24 I-stall cycles, 0x04/0x05 misses, per LOGIC / ACTOR PREP / ACTOR DRAW / WORLD DRAW / OTHER). Prediction: ACTOR ST% (data) < 15%, WORLD higher. |
| B. I-cache: 8 KB cache, ~145k I-fills per drawn frame (hw projection) = 4.6 MB of code fetched per frame | 4 Oct console: I-REND 103-147k vs D-REND 20-26k; model charges imiss 10.6 vs dmiss 9.1 ms at only ~14.6 cycles per fill; the per-part fixed cost of ~58 us (= 11,600 cycles per part, ~112 parts, VILLAGE-LEVERS 217) is the signature of a long call chain evicting itself (OT -> GX emulation -> lighting setup -> native, census rows 1-4 at VILLAGE-LEVERS 337-340); `LINK_ORDER` in the recipe is still the 5 Oct profile (`build-r21.sh` 126: `r22-fsca-c3-8k.ld`), stale against a renderer that was rewritten since | Nothing measured contradicts it | Same v2 page 2: I-stall% per phase. Cheap lever if confirmed: `ordgen_c3.py` from the hV6 profile (exact, placement only; Sept measured -1.25 ms on logic alone, README 68 warns of a few-tenths lottery) |
| C. Game logic, not render | S ~ 20 console ms per tick = 60% of the processor at 30 Hz; logic IPC on console 0.48 (hwcal page 2 IPCL) = memory-bound code; EmMgr.move 4.5 Flycast (~7 console) for 6 alive | It is not what makes the *drawn* tick 74; it is what makes 20 fps need D <= 40 | v2 LOGIC row (console ms, ST%); the Phases disc logic row |
| D. TA / store-queue back-pressure | 25,700 SQ flushes (820 KB) per combat frame; model charges 1.3-3.1 ms and does not model FIFO stalls (HW-ONLY-COSTS "Suspects" 2); TA input 1.09 MB/frame in the cross view vs 0.85 at the wall | Benchmark wait rows ~0; 4 Oct FENCE 0.1 | v2 WORLD DRAW: high ms with low ST% = stalls that are neither cache kind -> SQ/TA. Also PACE `reg_avg_us` (scene open to last list in) on the Phases disc |
| E. FPU mode / denormals / traps | - | Ruled out by the observer: DN=1 everywhere, 0 denormal inputs, 0 TRAPA, 0 misaligned (HW-ONLY-COSTS "Ruled out"); 3,000 accidental double ops in `re4dc_model_packet_reserve` ~0.15 ms | Already settled; fix the double (free) |
| F. vsync / pacing quantisation | fps = drawn / vblanks; a 94.5 ms pair lands on 5 or 6 vblanks (12 / 10 fps) -> 10.5 | With catch-up the CPU does not wait on vblank when behind (`main.cpp` 353-361, `pace_end`), so no time is lost, only judder. At the 20 fps point the D D S pattern presents at 50 / 50 / 67 ms | Not a cause. Note: in the players' default Smooth mode the 66.7 ms floor blocks skips at the cross (94.5 > 66.7), so players see **~13.4 fps at ~45% speed** there, not 10.5 at 71%. Any "20 fps" statement must name the mode |
| G. KOS, IRQs, sound, GD-ROM | AICA driver ~0.25 ms/tick in Flycast (`aica:` line 3033); G2 writes 200-400/frame, 11,500 in alert frames (bank upload); music stream 12-24 GD reads/s through DMA + driver; maple poll per vblank | Benchmark reads ~0/s, wait 0-1 ms/s; model kos-idle 1.8 | Phases "other" + disc rows. Expect < 2 ms per pair; not the gap |
| H. The measurement itself | "CPU" averages drawn and skipped ticks; SPD is cap-limited (71% is a consequence of PACE_CAP=1, not an independent reading); the r22g VMU "CPU %" is the same quantity | The two console runs repeat within 1% | Use v2 TOTAL (per drawn frame) and LOGIC (~S) instead of page 1's average; stop quoting SPD as evidence |
| I. GPU | 18.5 ms; FSAA on/off changed nothing (TEST12-SCOPE 16) | Fits 50 ms with room; overlaps | Settled: not a term until D < ~25 |

Verdict: the CPU-bound diagnosis stands; "latency in actor skinning" is the least supported of the memory
stories. The data we have points at instruction fetch across the whole render path and at the world transform's
data stream before it points at actor skinning. One console run of benchmark v2 (already built, RE4DC-Benchmark-v2\
README.txt) answers A, B, C and D at once; the memlay arms (`/root/probe/lanes-20261015/memlay/bench/logs-build.txt`:
MEM_MOVCA=1, ACTOR_MOVCA=1) should wait for it.

## 3. Alternate strategies, judged by console ms at the cross

Reference: D_console ~ 74.5 (S ~ 20, R ~ 54.5). Target for 20 fps real time: D <= 40. Costs are MODELLED unless marked.

### 3.1 Scheduling and rates
- **Decoupling render from logic** is already in: catch-up pacing renders at 1/2 the tick rate when behind. The
  arithmetic 30 S + 20 R <= 1000 is the whole story; no schedule rearrangement removes work. A fixed "render at 20,
  logic at 30" differs from today only in judder, not in CPU.
- **Logic at a lower fixed rate with interpolation**: not available. RE4 is a fixed 30 Hz step with no delta time
  (animation frames, motion, timers are per tick); a 20 Hz tick changes every outcome. Rejected on identity and on
  "equivalent" grounds alike.
- **PACE_CAP=2** (3 ticks per picture): raises game speed toward 100% at the cross but *lowers* fps (3 ticks per
  picture). Measured 10-09 and declined (README 47). Correct decision for an fps goal.
- **Cheaper skipped tick (exact, small):** v2 already drops ModelTrans on a dropped image. Still running on a skipped
  tick: EspTrans 1.15 Flycast (~1.8 console), objTrans remainder, DrawOTag of UI that is never presented. Gating
  EspTrans/UI on `re4dc_pace_drop_models` is render-only: **-1.5..-2 ms per skipped tick** (10 skips/s at the
  target = 2% of the processor). STRICT: EspTrans writes nothing gameplay reads? Must be checked (Esp is shared RNG;
  the *move* must stay, the *trans* is what to gate).

### 3.2 Logic (S), now allowed to be "equivalent" (coordinator 10-15)
- **Far / off-screen Ganado AI and motion at half rate** (the user's new class). PS2 did NOT do this (PS2-ENEMY-CODE-
  DIFF-20261015.md "Answer in one paragraph": no update-rate, LOD or throttle anywhere global; its cuts are fewer
  actors). Our cap 6 is already below the PS2's 9 starters. Saving: EmMgr.move ~7 console ms per tick for 6 alive, of
  which the 3-4 off-screen ones ~4; half rate -> **-2..-2.5 ms per tick = -3..-4 per picture (INFERRED)**. Gameplay:
  wave/bell triggers are count-based (unaffected); arrival timing of the parked ones shifts by up to one tick;
  grabs/hits on a parked Ganado must not be possible (park only when > N m and off screen, as ACT_CAP_FAR_M did).
  The Sept variant failed the decisions gate; under the new rule it passes if the scripted outcomes match.
- **Approximate skeleton maths in logic** (`GAME_SKEL_FTRV ?= 0`, `game30.mk` 1215, exists and is off): PSMTXConcat
  0.73 model ms per frame in total; the logic share is maybe half: **-0.2..-0.3 per tick**. Changes bone positions in
  the last bits: hit zones, IK, attach points. Not worth the gate.
- **Collision and cloth**: collision 3.3 model, cloth ~1 (census row 7). Cloth is game state (parts chain, shared RNG):
  keep exact. The scenery line-query kernels are already asm (lnk/lnw). No equivalent-but-cheaper collision exists
  that keeps "no stuck events".
- **Effects move (EspMove 1.4 Flycast)**: shared RNG; half-rate = desync risk through RNG consumption. Keep exact.
Sum of the logic levers worth taking: **-2..-3 ms per tick, -3..-4.5 per picture.**

### 3.3 Render (R)
- **World (scenery 15.8 model: transform 5.6, walk/emit/visibility/clip 9.3).** The transform is already a software-
  pipelined FTRV + FSRRA loop (`port/dreamcast/room/mesh_fastpath_sched.hpp` 2-9, MESH_VP_SCHED=1 in build-r21.sh 152):
  sh4zam offers nothing faster there. The walk/emit side is the larger half and is per-strip/per-meshlet overhead.
  Pre-transform rejection is done (PS2_STRIP_GROUPS). Remaining levers: (a) **offline distance LOD of the room mesh**
  (not a draw-distance cut, which the user ruled out): coarser meshlets beyond ~12 m with the same 25 m far plane:
  -3..-6 model, visible, needs a sheet; (b) cell PVS -0.7..-2 (dropped as too small; it is small); (c) fewer, larger
  meshlets to cut per-strip overhead: priced at <= 3% each (VILLAGE-LEVERS 168). The world column is near its floor
  *for this geometry*; the geometry is the lever.
- **GC-path parts (~100 parts x ~58 us fixed ~ 6 ms model + per-vertex).** STATIC_OBJ_BAKE (-3.0, test 13) takes the
  never-moving ones. Doors (28 parts), accessories (18), items (15), racks (12), weapons (11) still go through
  ModelRender -> OT -> GX state -> per-model light setup -> native (census rows 1-4 ~ 2.8 ms + row 8). A native part
  list for PS2-converted dynamic parts that skips the GX/OT chain is exact for rendering (same floats) and is the
  item most likely to be I-cache-bound: **-3..-4 model (-3.5..-4.5 console)**, medium confidence, 2-4 KB of code.
- **Leon (~8.5 model).** The single biggest actor item and the least understood ("mostly animation, bone matrices,
  per-palette work", VILLAGE-LEVERS 241). Benchmark v2's "Leon hidden" row gives the console number directly. Options
  once known: LEON_NATIVE_PIPE (exact, -2.2 on GC Leon, off because of probe lighting), a render-only reduced bone
  set (face/finger bones merged for the draw, not for logic): -1..-2, look risk at the hands/face.
- **Flat per-part lighting for the crowd and objects** (decided acceptable for the budget mode, d367 skill
  "Decided: flat Ganado lighting yes"): avk_light_* kernels 2.5 model -> **-1.5..-2**, look change, render-only.
- **Memory-layout arms A/B** (MOVCA on scratch + prefetch normals; memset/memcpy): ceiling = actor dmiss 1.2 + the
  skin kernels' share of render-side dmiss (~1.5) = ~2.7 model; a 4 KB scratch reused per part mostly stays in the
  16 KB D-cache, so MOVCA's write-allocate saving is uncertain. **-0.5..-2 model**, 50% confidence. The memset
  (380 KB/frame of struct zeroing, `L_store_long_loop` 0.87 model, 2,400 D-misses) is better *removed* than
  accelerated: an sh4zam memset8 still writes 380 KB.
- **Far-Ganado impostors / baked poses / skin caching**: at cap 6 about one Ganado is drawn and it is near; the mid/far
  tiers already exist (82% / 45% of near tris); priced at <= 0.3 ms (VILLAGE-LEVERS 306-321). Not a lever here.
- **Skinning on fewer bones (Ganados)**: pre-blended matrix per vertex group already; rigid binding priced < 0.1.
- **Effects render** (Ps2fx/EspTrans/EspCommonTrans ~1.7 + sprite emit): trims are in (FX_SPRITE_TRIM=2); the rest is
  look. GPU side is solved (hw fog).
- **TA submission by DMA instead of store queues**: removes 1.3-3.1 model ms of SQ flush cost only if the CPU is
  stalling on the FIFO (hypothesis D). Decide after v2.
Sum of render levers that are exact or already-approved-look: bake 3 + part list 3.5 + link order 1-2 + memset/
presort/double 0.7 + memlay 0.5-2 = **-9..-11 console**; plus look-change levers (world LOD 3.5-7, flat lighting
1.5-2, Leon rig 1-2) = **-6..-11**. Total render: **-15..-22 console ms**.

### 3.4 What the PS2 did, as evidence
- Vertex transform and skinning on VU1, in parallel with the CPU; the DC has no equivalent: our SH-4 pays what the
  PS2's second processor paid. The PS2's frame rate is not evidence that this geometry fits one SH-4.
- Fewer actors per room, smaller pools, Easy-only cuts; no update-rate or LOD changes (PS2-ENEMY-CODE-DIFF).
- Same draw distance as GC (ZFAR 1e6, VILLAGE-LEVERS 173); we already draw less (25 m).
- 512-wide output and a blur filter (memory re4-dreamcast-smoothness): irrelevant to CPU.
So "what the PS2 cut" is already taken (cap 6 < 9) or impossible (VU1). The remaining PS2-sourced lever is that its
world meshes are low-poly: the LOD we need must be made offline from them.

## 4. The maths-library question

Call-count evidence (`hwmodel-hV6-r101\proj\report.txt`, top functions, MODELLED, cap 6, per drawn frame):
- `PSMTXConcat` 0.73 ms (the hand-scheduled 90-cycle asm, `mtx_sh4.S`, removed by Bruce's 8e769a9dd8). sh4zam's
  compact 3x4 `load_apply_store` is reported at 77 cycles cached by its author (re4-research\sh4zam-audit-20260925\
  AUDIT.md section 3): -15% of 0.73 = **-0.1 ms**, and it is "Not bit-identical to C_MTXConcat" (commit text), so
  every logic caller (skeleton, attach points, hit zones) leaves STRICT.
- `re4dc_sincosf` is not in the top 30 (each < 0.46 ms); fe2aed7945 moves it to FSCA (`shz_sincosf`, ftrc + fsca,
  "Not bit-exact", 952 -> 56 bytes). Gain **< 0.2 ms**; code size -0.9 KB is the real benefit.
- FSRRA is already used for 1/w in the world loop (`mesh_fastpath_sched.hpp` 5); FTRV is already used for skinning
  (`re4dc_pwc_ftrv_run` 1.03) and the world transform.
- sh4zam memory ops: MOVCA/fmov.d copies address `copies` 2.25 model ms. The copies are the problem, not their speed.
- XMTRX matrix stacks / fused transforms: our skeleton already pre-blends; palettes 0.92 model (census row 6).
Bruce's statement ("validates by being exact; to gain from sh4zam you need to be happy with approximations") is
true of libm precision and false about where our time goes: the top costs are vertex and part counts and cache
behaviour (sections 2-3). Classifying his commits as SH4_APPROX_RENDER / SH4_APPROX_LOGIC is reasonable hygiene
(render-side use is free of the gate), but as a performance item it is **< 0.5 ms per drawn frame combined**, under
1% of D, and the LOGIC half costs the decisions gate for ~0.1 ms. Take the code-size win, do not spend lanes on it.

## 5. Ranked plan to the cross target, with what to stop

Baseline: D_console 74.5 (INFERRED), S 20, pair 94.5, 10.5 fps. Console ms are model ms x 1.1 unless MEASURED.

| # | Step | Console ms on D | Conf. | Risk | Confirming evidence |
|---|---|---|---|---|---|
| 0 | **Run benchmark v2 (4fe2957e) on the console; read page 2.** Gives D (TOTAL), S (LOGIC), I-stall vs D-stall per phase, Leon / Ganado / world rows. Rewrite section 1.4 with measured D and S. | 0 (it decides #4, #5, #8) | - | none | the photo |
| 1 | **Re-state the target in pacing terms and get the user's pick**: 20 fps real time = D <= 40; 20 fps slow-motion = D <= 50; 15 fps real time = D <= 46. Replace the "50 ms hw model" gate with a pair gate (D + S <= 66.7 for 15 fps; 30 S + 20 R <= 1000 for 20). Name the pacing mode in every fps claim. | 0 | - | none | this doc, sections 1.5-1.6 |
| 2 | Exact, cheap, in test 13: STATIC_OBJ_BAKE (in flight, -3.0 model), LQ_MEMO + FACE_LAZY + census trims (-1.1), fix the `double` in `re4dc_model_packet_reserve` and `pvr_set_presort_mode` every frame (-0.2..-0.4) | **-4.5..-5** | high | none (STRICT gated) | hw diff + v2 A/B disc |
| 3 | **Regenerate LINK_ORDER from the hV6 profile** (`ordgen_c3.py`; exact, placement only; the recipe's file is the 5 Oct image) | -1..-3 | medium | "few-tenths lottery" (README 68): build 2-3 candidates, keep the best; may change nothing | v2 I-stall%; hw imiss column |
| 4 | Cheaper skipped tick: gate EspTrans / UI OT on dropped images (render-only) | -1.5..-2 per skipped tick (= -1.5..-2 on the pair) | medium | STRICT check that Esp trans writes nothing logic reads | STRICT pair + v2 |
| 5 | Native part list for PS2-converted dynamic parts (doors, racks, items, accessories, weapons) bypassing ModelRender/OT/GX/light-setup | -3.5..-4.5 | medium | render identity only (same floats); +2-4 KB code; KOS headroom | hw function rows for rows 1-4 and 8 of the census; v2 ACTOR DRAW |
| 6 | Memory-layout arms A/B: **only if v2 shows D-stall >= I-stall in ACTOR PREP**; otherwise park | -0.5..-2 | low-medium | none (render-only, =2 compare) | v2 page 2, the arms' own A/B discs |
| 7 | Look-change render levers (user judges a sheet): flat lighting for crowd + objects (-1.5..-2); render-only reduced Leon rig (-1..-2) | -2.5..-4 | medium | look at the hands/face, crowd shading | sheets + v2 |
| 8 | **World distance LOD offline** (keep 25 m, coarser meshlets beyond ~12 m, from the PS2 meshes) | -3.5..-7 | medium | visible; must be sheeted vs PS2 | hw world column; v2 WORLD DRAW |
| 9 | Gameplay-equivalent logic (user decides per case): far/off-screen Ganado AI+motion at half rate | -2..-2.5 per tick = -3..-4 per pair | medium | arrival timing shifts <= 1 tick; must park only when off-screen and > N m; kills/waves/bell count-based so unchanged | decisions-equivalent gate: same kills, waves, bell frame +-30, s30; no stuck Ganado |
| 10 | TA DMA submission instead of SQ (only if v2 WORLD DRAW shows stall-free ms far above model) | -1..-3 | low | pipeline change; TA double buffer | v2 |

Running totals (INFERRED): #2-#6 exact = **-11..-16** -> D ~ 59-64, pair ~ 80-84, **12-12.5 fps real time**;
+ #7-#9 = **-9..-15 more** -> D ~ 46-52, pair ~ 68-72, **14-15 fps real time**, or 19-21 fps in slow motion
(Off/Smooth-blocked). **D <= 40 is not on this list.** The gap (~6-12 ms) is only closable by drawing less in that
view: fewer parts and world vertices at the cross than the PS2 package has, which is a village-asset decision for the
user, not a lane item.

Stop or demote:
- The memlay lever's bench discs (arms A and B) until v2 page 2 is read: they aim at the smaller memory term on the
  current evidence (section 2, A vs B).
- "Approximate maths" as a perf lane: < 0.5 ms (section 4). Keep the classification knobs as hygiene.
- Projecting with x1.37-1.39 and quoting SPD as a finding (section 1.6, items 2-3 and H).
- Treating "benchmark-r101 <= 50 ms hw model" as the 20 fps gate (1.6 item 5).
- Per-model setup caches and far-Ganado meshes at cap 6 (<= 0.3 ms each, already priced).
- Re-profiling: the hV6 function table plus one v2 console run is enough to run this plan to its end.

## Appendix: numbers used
- Console benchmark 10-15 (MEASURED): cross 10.5 / 10.4 fps, min 8.9 / 8.5, CPU 47.1 / 47.6, GPU 18.5 / 17.6, SPD 71 / 70,
  reads 0.0 / 0.1 per s, wait 0 / 1 ms/s, KOS min 118 KB; house 13.2, 37.4, 15.1, 88%.
- Flycast same disc (FLYCAST, benchpub-r1-7b6bbd09\run-output.txt 5800-5801): cross 18.6 fps, 868 ticks / 550 drawn /
  1767 vblanks, CPU 33.8, GPU 7.5 (not a PVR model), SPD 98%; house 29.9, 480/480/960, 30.4, 100%.
- hw model cap 6 (MODELLED, hwmodel-hV6-r101\proj\report.txt): 67.51 [58.0 .. 81.2]; pipe 47.2, imiss 10.6, dmiss 9.1;
  areas: game-render-side 23.75, scenery 15.80, actors 11.25, game-logic 7.80, ui 4.29, copies 2.25, kos-idle 1.80,
  ta-submit 0.57; insns/frame 10.78 M; top: transform_sched 5.64, walk_lean 2.56, avk_pos_skin_u16 2.46, MeshDraw 1.95,
  Part::whole 1.45, group_visible 1.42, actor_submit 1.28, avk_pos_skin_s16 1.05, pwc_ftrv_run 1.03, avk_light_skin_n16
  1.00, L_store_long_loop 0.87, line_leaf2 0.82, PSMTXConcat 0.73.
- Console 4 Oct hwcal (MEASURED, /root/probe/hwcal-v/CONSOLE-RESULTS-20261004.md): GAN6 LOGIC P50 18.3, MCYR 15.0 M cycles
  (75 ms), D-LOGIC/D-REND/I-LOGIC/I-REND = 45.2k / 26.4k / 24.3k / 134.4k per frame; FENCE 0.1; logic IPC 0.48.
- hw-only census (FLYCAST observer, RE4DC-HW-ONLY-COSTS-20261015.md): per combat frame 100k OC read misses, 29.5k write
  misses, 48.6k write-backs, 22.4k prefetch fills, 25.7k SQ flushes (820 KB), FPU DN=1, 0 denormals, 0 traps.

## Follow-up 10-15 (coordinator's grouped table; goal now 30 fps elsewhere, cross allowed 20 fps slow-motion = D <= 50 with skips blocked)

Corrections to the table (console ms on D, baseline D ~75 INFERRED, 72-77):
- **Skipped-tick trims (1.5-2) do not count at the cross any more.** With skips blocked every tick is drawn, so they save
  nothing there (they still help the 15-30 fps transition elsewhere). Group 1 without them: 10-15 -> D ~60-65.
- **Far-Ganado half rate is -2..-2.5, not 3-4.** My 3-4 was per *pair* (two ticks); with every tick drawn it is per
  tick = on D. It is "not visible" only because the parked ones are off-screen by construction; the risk is gameplay
  timing (arrival within a tick) and a one-tick pose hold if one enters view mid-interval. Gameplay-equivalent, not
  invisible: it belongs in group 2 as the coordinator placed it, with the decisions-equivalent gate.
- **World distance LOD beyond ~12 m: medium look risk, not small.** The PS2 meshes are already low-poly; a second
  decimation step at distance is a visible edge/silhouette change (fences, the well, house outlines). 3.5-7 holds
  (v2 page 3: 0.60-0.70 ms per 1k vertices in Flycast; ~1.0-1.2 on the console, see below) if ~4-6k of the world's
  ~14-21k transformed vertices sit beyond 12 m and are halved. A vertex-by-distance histogram from the LEAN counters
  settles the share before anyone decimates.
- **Lower-poly Leon 2-4 is overstated:** 5.1k -> 4k tris is ~1.5k vertices = ~1.5 console ms by the page-3 rate; light-p3
  priced it at -0.5..-0.7 because Leon's cost is bones/palettes. Put 1-2, and only with a reduced render rig.
- Group 3 "fewer props/scenery ~0.7-1 per 1k vertices": agree; console ~1.0-1.2 per 1k (section 1.4 ratio 1.6).

Q2, group 1 (no skip trims) + world LOD + far-Ganado half rate: **-15.5..-24.5 -> D 50.5-59.5.** Reaches D <= 50 only
if every item lands at the top of its range at once. **Probability ~25-30%.** What makes it fall short, in order:
(1) stacking: the memory-stall floor stays when "cheap" pipeline work is removed, so individually measured savings
add to less than their sum (the 10-15 crowd12 rounds showed this: -0.9 targeted became -0.4 total); (2) the LINK_ORDER
lottery gives ~0; (3) the native part list's I-cache premise fails and it gives 1-2 not 3.5-4.5; (4) the far-vertex share
beyond 12 m is under a third; (5) S (~20) is untouched except by the Ganado item, and with skips blocked it is a fifth
of every D.

Q3, best next pick if short (quality per ms): **flat per-part lighting for crowd and objects (1.5-2, render-only,
PS2-like, already accepted for the budget mode)**; then the render-only reduced Leon rig (1-2); then far plane 20 m
(-2..-3, visible pop beyond PS2, the user ruled it out before); cap 5 (-1.2 per alive on S) last, against the cap-6 rule.

Q4, what the page-3 rate adds. 34.7k vertices x 0.65 = ~22.5 of Flycast's ~46 ms drawn tick is per-vertex; the rest is
per part/per frame. Console factor: use the per-drawn-tick ratio **~1.6 (1.0-1.1 ms per 1k vertices)**, and expect the
world's share nearer 1.2 (its transform is the top D-miss pc) until v2 page 2 is read on the console. Two consequences:
- The cross at D <= 50 with S ~20 leaves R <= 30: at ~1.1 ms per 1k, about 15-18k vertices plus ~10 ms of fixed cost.
  Today's cross draws 34.7k. **D <= 50 is a content budget of roughly half the current vertices in that view** unless the
  fixed costs (parts, UI, copies, I-cache) fall first; the plan above does both and still only just reaches it.
- **30 fps elsewhere (D <= 33 at every tick drawn) is the harder goal.** Quiet outdoor views are ~50 today (the wall at
  19.9 fps = 3 vblanks). With S ~15-18 in quiet views, R <= 15-18 = about 8-12k vertices per view plus fixed costs.
  That is a per-view vertex and part budget for the whole route, not a village tuning item; the group-1 items are
  cross-specific (parts, Ganados) and the world LOD is the only one that helps every view. Recommend: state 30 fps as
  "vertex budget ~10k + fixed <= 10 ms per view" and have objs count every route room's views against it from the
  LEAN counters before promising it.
- Pacing note: with Smooth's 15 fps floor the cross flips between skipping (pair ~67, 15 fps real time) and blocked
  (20 fps slow motion) around D ~47-50; set PACE_FLOOR_FPS to 20 (or Off) for the user's intended behaviour and so the
  two modes do not alternate inside one second.

### Correction (coordinator, 10-15, after the memlay lane's findings)
- The skipped-tick trims are already in the 12.1 recipe (PACE_CATCHUP=2 + PACE_TRANS_SKIP=4063: EspTrans render half,
  CtrlMgr.trans, ShadowTrans, ClothDraw, TexRender, IdSys, cMes.Trans, DrawOTag, Render(), ModelTrans on dropped images;
  only FilterTrans bit 32 unset). Plan item #4 and the group-1 row "skipped-tick trims 1.5-2" are withdrawn; the
  remaining S is logic, and only the far-Ganado item touches it.
- memlay arms (MODELLED, benchmark-r101-t12 cap 6): A -0.3 ms, B +0.5 ms. Plan item #6 is parked: count memlay at 0
  (-0.3 at best); keep only the memset *removal* (0.5-1) from "clears + memlay".
- Revised group 1: bake + small savings 4.5-5, LINK_ORDER regen 1-3 (lottery), native part list 3.5-4.5, memset removal
  0.5-1 = **9.5-13.5 -> D ~61.5-65.5**. With world LOD (3.5-7) and far-Ganado half rate (2-2.5): **-15..-23 -> D 52-60.**
  Probability of D <= 50 at the cross from that set: **~15-20%** (was 25-30%). The shortfall reasons in Q2 stand; the
  logic tick (~20 of every D with skips blocked) is now the largest untouched term, so if the user wants the cross at
  20 fps slow-motion with reasonable odds, one more item from Q3 (flat crowd/object lighting 1.5-2) or a logic item
  (cap 5: -1.2 per alive) has to join the set, and v2 page 2 must confirm the part-list premise before it is built.
