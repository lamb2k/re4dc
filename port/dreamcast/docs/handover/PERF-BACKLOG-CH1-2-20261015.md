# Performance backlog, chapters 1-1 to 2-3 (2026-10-15, evening)

Read-only analysis. Every ms is **MODELLED** (the console-calibrated norms model, `room-budget-20261015\budget.py`) unless the
row says **CONSOLE** (user's NTSC console, benchmark disc 76f40d95 = test 12.1 + bench, Part 1 run 2 and Part 2 run 1, fast
pacing). Recompute everything with `python -I room-budget-20261015\backlog.py --md`; the lever x room numbers are in
`PERF-BACKLOG-CH1-2-20261015.csv`. Per-room projections and the model itself: `ROOM-BUDGET-PROJECTION-20261015.md` (updated to
the same calibration).

Pacing used for every target: **30 fps = drawn tick D <= 33.3 ms with every tick drawn. The r101 cross fallback = D <= 50 ms with
skips blocked (Smooth / PACE_FLOOR 20): 20 fps in slow motion.** Under fast pacing a 50 ms drawn tick plus a ~22 ms skipped tick
is ~13.7 fps at ~91% speed, so the cross target only means "20 fps" with skips blocked. The console numbers quoted as "drawn tick"
are page-3 DRAWN x 0.95 (the PMC counters cost ~5%).

> **Update 10-15 (user):** play-time weighting removed; every room weighs the same (w_room = (1 + gap/10 ms) x 1.5 for the 3 heaviest). Section 4 scores now use the new weights (10-15 evening refresh, with the plain-words columns); the CSV, PERF-BACKLOG-PER-ROOM and the readiness page use the new ones. New top 8: A3, A2, C4, A2b, A6, A5, A9, B5 (was A3, A2, C4, A2b, A5, A9, A6, A1): A6 moves up two, and A1 (the r101-only bake) drops from 8th to 11th because r101 no longer gets its 8-minute weight. C8 far plane is a rule conflict, never scheduled. Tranches and the rooms-after numbers are unchanged.

## 1. Summary

1. **The console calibration moved the fixed costs, not the total.** The cross drawn tick is 72.6 ms CONSOLE (model 70.8). But the
   split is new: ~22 ms of every tick is logic + per-tick work that runs even when nothing is drawn (LOGIC 15.7 + 6.4 of effects
   move / trans / sound), the world pass has a fixed walk of 2-7 ms per room before any vertex, Leon costs 11 ms (3.4 logic + 7.5
   draw), and each alive Ganado costs ~1.15 ms of logic plus ~2.3 ms when drawn. Effects are only 1.2 ms of CPU. Before any world,
   Ganado or prop the drawn tick is already **30-34 ms**: the whole 30 fps budget.
2. **Cache stalls are half the processor.** D-cache stalls 25-30% and I-cache stalls 16-21% in every bucket of every scene
   (CONSOLE page 2/3). That is a whole-game lever worth 25-35 ms of a 75 ms tick, and no single lane owns it (section 6).
3. **No room reaches 30 fps with the levers that exist**; r102 is the only typical view under 33 ms today. The expected
   (confidence-discounted) result of landing every lever in this catalogue is **18 of 26 rooms under 50 ms (typical view) and 1
   under 33 ms**; at face value (every lever delivers its full number) it is 26 under 50 and 19 under 33. The truth is between.
4. **Three things dominate the ranking, and two of them are already built:** MOTION_COLD_POOL (r103 farm: ~34 ms of disc stalls per
   drawn tick, CONSOLE 5.8 fps), the small exact bundle (1.7 ms in every room), and the PS2 cast for the remaining GameCube
   characters (2.8-5.5 ms in 7 rooms, including every chapter 2-2/2-3 Ganado room). Then flat crowd/object lighting (1-1.6 ms,
   render-only, every room), the census trims, and the resident lists.
5. **The cross reaches ~53 ms expected / ~38 ms optimistic** after the whole catalogue, so the user's 50 ms fallback is a coin flip
   on the exact levers and a near-certainty only if the world LOD, the far-Ganado half rate and the I-cache work all land.
6. **Chapter 2-2/2-3 is denser than the village**: r11c (cabin siege, 72 ms typical / 100 worst, GameCube em13 and 9 sent at once),
   r113 and r111 (em17 GameCube, 67-68), r11d (68). Their first lever is conversion (PS2 cast) plus the PS2 cabin waves, not
   tuning. All 2-2/2-3 numbers are LOW confidence (lane packages, no Flycast or console timing except r200).

## 2. The model, in one screen (console-calibrated)

```
LOGIC/tick = L0 4.8 + 1.15 x Ganado-units + LEON 3.4            S (skipped tick) = LOGIC + T_SKIP 6.4
D (drawn)  = S + F 3.5 + 0.025 x package placements (world walk) + 1.0 x world k verts + 1.15 x character k verts
             + 1.2 x props/parts/UI k verts + FX 1.2
world k verts = 1.1 x projected on-screen (25 m far, 50 deg, typical = median of door/enemy-position views, worst = 90th pct)
characters   = Leon 6.7k + 1.9k per drawn PS2 Ganado (2 typical, 4 worst) or 4.3k per GameCube-model Ganado + bosses/Ashley
```

| Constant | Value | Pinned by (CONSOLE benchmark row) | Status |
|---|---|---|---|
| T_SKIP 6.4 ms | skipped tick minus LOGIC/tick | page 3 SKIP vs page 2 LOGIC: cross 22.9-16.55, house 29.3-22.9 (Del Lago 7.9, farm 9.9 with disc waits) | measured |
| K_GAN 1.15 ms per alive Ganado | cross LOGIC 15.7 (6.5 units) vs house 21.8 (~12 units assumed) | needs a live half / no Ganados row (the sweeps are frozen: AI off) | fitted, one assumption |
| LEON 3.4 ms logic | kept from the hw model | needs a live "no Leon" row | modelled |
| L0 4.8 ms | cross LOGIC minus the two above | falls out | derived |
| F 3.5 ms render fixed | compromise over cross / house / Del Lago | a "no props" sweep row would split F from props | fitted |
| world walk 0.025 ms x placements | house WORLD 7.2 (283 placements), cross ~6 (209), farm 2-4 (134), Del Lago <= 2 (126) | WORLD column at 0 verts, any scene | fitted |
| K_W 1.0 ms per 1k world verts | sweeps 18.8 m / 12.5 m: cross 1.00-1.05, farm 0.89-0.97 | sweep rows | measured |
| K_CHAR 1.15 ms per 1k | Leon 7.5 ms / 6.7k; 5 Ganados 11.6 / 9.6k (cross); farm Leon 6.9 | sweep rows no Leon / half / no Ganados | measured |
| K_OTHER 1.2 ms per 1k props | assumed = Ganado rate | none: add "no props" to benchmark v3 | assumed |
| FX 1.2 ms | cross no-effects -1.2, farm -0.5 | sweep row no effects | measured |
| disc stall per read 4.5 ms | farm 172 ms/s / 34.6 reads/s | page 1 READS / WAIT | measured |

Checks: cross model 70.8 vs CONSOLE 72.6; Del Lago 44.8 vs 40.2; house 54.3 vs 45.1 (interiors run 10-20% below the model);
farm 59.9 + ~34 ms stalls vs 94.1. The farm is also near the GPU budget (24-29 ms CONSOLE, world fill 14 ms): the only ch1-2 scene
where the PVR matters at 30 fps.

## 3. Per-room budgets (ms per drawn tick, typical view; "current / budget at the room's target")

Budget rule (formulaic): the fixed buckets get deep floors that the exact + render-only levers could reach (logic fixed 6.0,
Leon logic 2.5, render fixed 6.0, effects 1.0, disc 0); the remaining budget (33.3 or 50 minus those floors) is shared by the
variable buckets (Ganado logic, world, characters, props) in proportion to their current size. "Gap" is the typical D minus the
target; "After (exp.)" is the typical D after every scheduled lever at confidence-discounted value (section 5).

| Room | Ch | D typ / worst | Target | Logic fixed | Leon logic | Ganados/enemies logic | Render fixed | World verts | Character verts | Props/parts/UI | Effects | Disc stall | Gap typ | After (exp.) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r100 | 1-1 | 59.6 / 72.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 10.9 / 5.9 | 10.6 / 6.0 | 7.3 / 3.9 | 12.6 / 6.8 | 2.4 / 1.3 | 1.2 / 1.0 | 0.0 / 0.0 | 26.3 | 46.3 |
| r101 | 1-1 | 67.6 / 77.9 | 50 | 11.2 / 6.0 | 3.4 / 2.5 | 7.5 / 6.0 | 8.7 / 6.0 | 11.5 / 9.2 | 12.6 / 10.1 | 11.4 / 9.1 | 1.2 / 1.0 | 0.0 / 0.0 | 17.6 | 53.5 |
| r102 | 1-3 | 35.0 / 43.3 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 0.3 / 0.3 | 4.6 / 4.6 | 1.9 / 1.9 | 10.0 / 10.0 | 2.4 / 2.4 | 1.2 / 1.0 | 0.0 / 0.0 | 1.7 | 30.6 |
| r103 | 1-1 | 86.9 / 98.8 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 6.1 / 3.6 | 6.8 / 6.0 | 10.5 / 6.2 | 12.4 / 7.3 | 1.3 / 0.8 | 1.2 / 1.0 | 34.0 / 0.0 | 53.6 | 53.9 |
| r104 | 1-2 | 60.3 / 74.9 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 10.3 / 5.5 | 10.8 / 6.0 | 8.9 / 4.7 | 12.1 / 6.4 | 2.4 / 1.3 | 1.2 / 1.0 | 0.0 / 0.0 | 27.0 | 47.3 |
| r105 | 1-2 | 51.9 / 61.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 7.2 / 4.9 | 9.6 / 6.0 | 4.4 / 3.0 | 12.4 / 8.4 | 2.4 / 1.6 | 1.2 / 1.0 | 0.0 / 0.0 | 18.5 | 43.1 |
| r106 | 1-1 | 56.0 / 69.8 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 7.5 / 4.1 | 7.4 / 6.0 | 10.3 / 5.6 | 12.6 / 6.9 | 2.4 / 1.3 | 1.2 / 1.0 | 0.0 / 0.0 | 22.7 | 46.0 |
| r107 | 1-2 | 48.4 / 77.7 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 7.5 / 5.1 | 5.3 / 5.3 | 4.8 / 3.3 | 12.6 / 8.6 | 2.4 / 1.6 | 1.2 / 1.0 | 0.0 / 0.0 | 15.1 | 40.5 |
| r108 | 1-3 | 48.4 / 61.7 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 6.9 / 4.9 | 7.2 / 6.0 | 4.0 / 2.8 | 12.1 / 8.5 | 2.4 / 1.7 | 1.2 / 1.0 | 0.0 / 0.0 | 15.0 | 40.0 |
| r109 | 1-3 | 48.7 / 57.4 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 0.3 / 0.2 | 5.9 / 5.9 | 16.3 / 10.8 | 8.0 / 5.3 | 2.4 / 1.6 | 1.2 / 1.0 | 0.0 / 0.0 | 15.4 | 38.8 |
| r10a | 1-3 | 51.4 / 66.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 7.5 / 5.0 | 9.2 / 6.0 | 3.9 / 2.6 | 12.6 / 8.5 | 2.4 / 1.6 | 1.2 / 1.0 | 0.0 / 0.0 | 18.1 | 43.0 |
| r10b | 1-3 | 44.8 / 53.4 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 6.3 / 5.0 | 6.7 / 6.0 | 2.5 / 2.0 | 12.9 / 10.3 | 0.6 / 0.5 | 1.2 / 1.0 | 0.0 / 0.0 | 11.5 | 37.6 |
| r117 | 2-1 | 54.9 / 73.9 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 2.3 / 1.4 | 9.4 / 6.0 | 7.4 / 4.4 | 17.6 / 10.6 | 2.4 / 1.4 | 1.2 / 1.0 | 0.0 / 0.0 | 21.6 | 46.5 |
| r118 | 2-1 | 63.0 / 79.7 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 8.0 / 3.6 | 7.5 / 6.0 | 8.6 / 3.8 | 20.7 / 9.3 | 2.4 / 1.1 | 1.2 / 1.0 | 0.0 / 0.0 | 29.6 | 49.2 |
| r119 | 2-1 | 50.6 / 76.9 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 3.4 / 2.1 | 5.9 / 5.9 | 9.6 / 6.0 | 13.5 / 8.3 | 2.4 / 1.5 | 1.2 / 1.0 | 0.0 / 0.0 | 17.3 | 44.1 |
| r11a | 2-1 | 48.9 / 62.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 6.9 / 5.2 | 9.6 / 6.0 | 2.1 / 1.6 | 12.1 / 9.2 | 2.4 / 1.8 | 1.2 / 1.0 | 0.0 / 0.0 | 15.5 | 40.8 |
| r11b | 2-1 | 40.8 / 47.9 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 1.7 / 1.7 | 6.9 / 6.0 | 3.1 / 3.1 | 10.8 / 10.7 | 2.4 / 2.4 | 1.2 / 1.0 | 0.0 / 0.0 | 7.5 | 34.3 |
| r112 | 2-2 | 41.4 / 49.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 3.5 / 3.2 | 4.6 / 4.6 | 2.2 / 2.0 | 12.9 / 11.8 | 2.4 / 2.2 | 1.2 / 1.0 | 0.0 / 0.0 | 8.1 | 37.5 |
| r111 | 2-2 | 66.6 / 85.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 9.0 / 3.8 | 8.6 / 6.0 | 8.1 / 3.4 | 22.8 / 9.6 | 2.4 / 1.0 | 1.2 / 1.0 | 0.0 / 0.0 | 33.3 | 57.6 |
| r113 | 2-2 | 68.3 / 84.6 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 10.1 / 3.9 | 6.8 / 6.0 | 10.5 / 4.1 | 22.8 / 8.9 | 2.4 / 0.9 | 1.2 / 1.0 | 0.0 / 0.0 | 35.0 | 58.5 |
| r11c | 2-2 | 72.4 / 100.2 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 14.4 / 5.1 | 6.2 / 6.0 | 5.7 / 2.0 | 27.9 / 9.9 | 2.4 / 0.8 | 1.2 / 1.0 | 0.0 / 0.0 | 39.1 | 61.3 |
| r11d | 2-3 | 67.6 / 89.8 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 9.0 / 3.7 | 8.5 / 6.0 | 9.2 / 3.8 | 22.8 / 9.4 | 2.4 / 1.0 | 1.2 / 1.0 | 0.0 / 0.0 | 34.3 | 59.0 |
| r11e | 2-3 | 54.9 / 60.1 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 6.7 / 4.0 | 9.5 / 6.0 | 1.9 / 1.2 | 18.6 / 11.2 | 2.4 / 1.4 | 1.2 / 1.0 | 0.0 / 0.0 | 21.6 | 50.7 |
| r10f | 2-3 | 56.6 / 68.2 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 10.1 / 5.4 | 7.5 / 6.0 | 3.5 / 1.9 | 17.2 / 9.2 | 2.4 / 1.3 | 1.2 / 1.0 | 0.0 / 0.0 | 23.3 | 50.5 |
| r11f | 2-3 | 50.7 / 57.5 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 3.4 / 2.2 | 6.5 / 6.0 | 9.1 / 5.7 | 13.5 / 8.5 | 2.4 / 1.5 | 1.2 / 1.0 | 0.0 / 0.0 | 17.4 | 46.1 |
| r200 | 2-3 | 56.5 / 66.3 | 33 | 11.2 / 6.0 | 3.4 / 2.5 | 10.1 / 5.2 | 5.8 / 5.8 | 2.4 / 1.2 | 20.0 / 10.4 | 2.4 / 1.2 | 1.2 / 1.0 | 0.0 / 0.0 | 23.1 | 49.6 |

Notes on the rows:
- Ganado logic counts cap-6 peaks plus boss/animal units (r100 and r104 are the documented 9-alive exceptions; Del Lago 5.5
  units from the CONSOLE LOGIC 14.1 per tick; El Gigante and Mendez 3 units, a guess). In chapter 2-2/2-3 it also holds Ashley
  (2.4 ms, a guess) and Luis in r11c.
- Character vertices charge GameCube-model Ganados at 4.3k each (em11 r117, em17 r118 / r111 / r113, em13 r11c, em16 r11d,
  merchant r200): that is why the 2-2 rooms sit at 22-28 ms in that bucket. The published projection CSV draws them at the PS2
  size; backlog.py reconciles the two.
- r103's disc stall is CONSOLE-inferred (drawn 94 vs model 60); r117 (em11), r119 / r11e (em2b) and r11d (em16) have all-cold
  motion archives and may carry the same stall, unmeasured. Other rooms' in-play loads (r10b 53, r100 46, r105 24, r118 20) are
  scored as hitches, not added to D.
- r101's 11.4 ms of props/parts/UI is the measured 9.5k at the cross; other rooms carry an assumed 2k (the house, farm and lake
  measured 0.5-1.1k). r101 worst view (77.9) assumes 4 Ganados drawn (the frozen cross view had 5).
- 2-2/2-3 rows (r112..r200) are LOW confidence: the same projection code over the route-v7 lane packages (3-35 camera samples),
  enemy counts from CH22-ROUTE / ALIVECAP / the PS2 table survey, no timing except r200 (Flycast 28.2-28.7 fps with the truck
  fire, which agrees with a ~56 ms console tick at the usual 1.6 ratio).

## 4. Lever catalogue

"Game area" = the rooms or scenes a lever helps. "Work it cuts" = which part of each frame it makes cheaper: Game logic (AI, animation, collision), Drawing (preparing the picture), Disc waits, Graphics memory, Code layout (whole frame) or Pacing. "In plain words" says what it does without the jargon (source: room-budget-20261015/plain.py). Ranked by the score without play-time weighting.

Status: gated = built and gated, waiting to land; built = built, not gated; priced = measured or priced, not built; idea = new.
ms are console ms per drawn tick in the typical view, as a formula of room data (the CSV has every room's value, typical and
worst). Effort: S 1 d, M 3 d, L 8 d, land 0.5 d. Identity risk classes: exact (STRICT-identical), conversion (PS2 asset = a bug
fix by rule), render-approx (look judged on stills), logic-equiv (decisions-equivalent gate), logic-gameplay (user decides,
gameplay-equivalence evidence), rule-conflict (needs a standing rule changed: listed, never scheduled).

| # | Lever | Game area | Work it cuts | In plain words | Status | Buckets | ms per room (console, typical view) | Rooms | Effort | Identity risk | Look risk | Conf. | Depends on | Score |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A3 | MOTION_COLD_POOL=262144 (test 14 row 17): cold motion keys share the pressure pool, 0 disc reads in play | Rooms whose enemy animations did not fit in memory: the farm (r103, measured), also at risk r117, r119, r11d, r11e | Disc waits | Enemy animations were being re-read from the disc in the middle of a fight because they did not fit in memory, and the game stopped to wait for the disc (the farm's 5.8 fps). This keeps them in a shared memory pool so play never waits on the disc. | gated | disc_stall | 34.0: r103 CONSOLE drawn 94 vs model 60 = ~34 ms of stalls per drawn tick (172 ms/s waiting); all-cold archives (r117 em11, r119/r11e em2b, r11d em16) carry the same risk, unmeasured | r103 | land (0.5 d) | exact | none | 0.9 | test 14 | 452 |
| A2 | Small exact bundle: GAME_LQ_MEMO, LEON_FACE_LAZY, g1parts (diag inline, fp unsigned, presort lazy), ACTOR_NO_CLEAR | Every room | Drawing + a little game logic | A bundle of small exact clean-ups: stop recomputing things that did not change (lighting lookups, Leon's face when it is still), lighter graphics-chip setup per object, and skip an unneeded memory clear per character. Each is under 1 ms; together about 1.7 ms everywhere. Nothing on screen changes. Part already in test 13. | gated | render_fixed,leon | 1.7: 0.22+0.19+0.3+0.8 model x1.1 | all 26 | land (0.5 d) | exact | none | 0.8 | test 13/14 | 174 |
| C4 | Flat per-part lighting for the crowd and objects (PS2-like; decided acceptable for the budget mode) | Every room with crowds or objects | Drawing (characters, objects) | Light Ganados and objects with one light value per body part (as the PS2 did) instead of per point. Leon keeps his detailed lighting. Crowd shading looks a bit flatter. | priced | char_verts,props_verts | 1.0-1.6: avk_light_* 2.5 model: -1.5..-2 | all 26 | S (1 d) | render-approx | small-medium (crowd shading) | 0.6 | ACTOR_PROBE_LIGHT stays for Leon | 44 |
| C8 | Far plane 18.75 m (REJECTED by the user: PS2 draws farther; option on request only) | Every room | Drawing (world) | Pull the far draw distance in to 18.75 m. You rejected this (the PS2 draws farther); listed only so the number is visible. | priced | world_verts | 0.0-5.9: listed so the number is visible; not scheduled | all 26 | S (1 d) | rule-conflict | high (pop beyond PS2) | 0.7 | user | 31 |
| A2b | GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag): exact caches | Every room | Drawing | Remove leftover GameCube graphics bookkeeping the Dreamcast never uses (queries of GameCube graphics state, hooks, diagnostics). Nothing on screen changes. | priced | render_fixed | 0.8: ~0.7 model; never built for 13 (test 14 item 13) | all 26 | S (1 d) | exact | none | 0.6 | STRICT | 31 |
| A6 | LINK_ORDER regenerated for I-cache locality (lane linkord): placement only | Every room | Code layout (whole frame) | Rearrange where the program's code sits in memory so the busiest code stays in the CPU's small instruction cache. Same code, new order. Waits for your LINKORD2 console run: the first LinkOrder disc crashed on a disc-driver bug that is now fixed. | gated | render_fixed | 0.5: cross -0.8 / house +0.2 model; lottery; console run of LINKORD2 decides | all 26 | land (0.5 d) | exact | none | 0.4 | KOS_DISC_FIX (LINKORD2 console run pending: the first console disc crashed on a DMA race) | 26 |
| A5 | Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM rule): 0 in-play loads | Rooms that reload textures during play: village r101 and farm r103 done; boat r10b, r113, r11c next | Disc waits (short freezes) | Each room loads all its textures into graphics memory once when you enter, so walking around no longer triggers disc reads and texture swaps (the short freezes). This is the graphics memory rule. | gated | disc_stall | 0.2-2.7: scored as hitch pain (HITCH_MS per load), not throughput; r10b 53 loads + refusals | r100, r102, r104, r105, r106, r107, r108, r109, r10a, r10b, r118, r119, r11a, r11b, r112, r111, r113, r11c, r11d, r11e, r10f, r11f, r200 | S (1 d) | exact | none | 0.7 | test 13/14 (r101, r103 done); VRAM headroom in r113/r11c | 25 |
| A9 | PS2 cast for the remaining GameCube characters: em17 (r118/r111/r113), em13 (r11c), em11 (r117), em16 (r11d), merchant (r200) | Chapter 2 rooms that still draw GameCube-model characters (r111, r113, r117, r118, r11c, r11d) and the merchant (r200) | Drawing | Swap the remaining high-detail GameCube character models for the lighter PS2 models (about 2,400 fewer points per character). It is also a correctness fix: the target is PS2 models everywhere. | built | char_verts | 2.8-5.5: GC fallbacks are bugs by rule; 2.4k fewer vertices per drawn GC character | r117, r118, r111, r113, r11c, r11d, r200 | M (3 d) | conversion | PS2 mesh = the asset recipe; look sheets pending (Zealot pool) | 0.7 | ps2cast lane pools; em16 module link | 24 |
| B5 | Code size for the I-cache: -Os cold paths, hot kernels grouped (I-stall 21% CONSOLE = ~15 ms of a 76 ms drawn tick) | Every room | Code layout (whole frame) | The CPU spends about a fifth of its time waiting for program code to arrive from memory. Make rarely used code smaller and group the busy code so more of it fits in the instruction cache. | idea | render_fixed,logic_fixed | 3.0: lottery like LINK_ORDER; PMC page 3 I-stall 19-21% both scenes | all 26 | M (3 d) | exact | none | 0.3 | LINK_ORDER tooling; KOS_DISC_FIX | 19 |
| B4 | World pass walk lean: cell/PVS pre-rejection of placements and meshlets so the fixed walk (2-7 ms CONSOLE by room) shrinks | Every room; bigger rooms most | Drawing (world) | Before drawing the world, the game walks a list of every scenery piece, costing 2-7 ms even when little is visible. Pre-sort the scenery by area so pieces that cannot be seen are skipped sooner. Same picture. | idea | render_fixed | 0.4-2.5: world walk x 0.35; PS2_STRIP_GROUPS already took the per-vertex part | all 26 | M (3 d) | exact | none (same strips emitted) | 0.5 | Part 2 farm "no world" row confirms W0 | 15 |
| A1 | STATIC_OBJ_BAKE r101 (test 13): never-moving GC objects baked into the PS2 world package | Village (r101) only | Drawing | Objects in the village that never move (carts, fences, crates) are merged into the village scenery ahead of time, so the console draws them as part of the ground instead of as separate objects every frame. Already in test 13. | gated | props_verts | 3.3: -3.0 hw ms MODELLED x1.1 | r101 | land (0.5 d) | exact | none (shutter still shown) | 0.8 | test 13 RC | 13 |
| D1 | Far / off-screen Ganado AI + motion at half rate (park only when off screen and > N m) | The 17 rooms with Ganados | Game logic | Ganados that are far away and off screen think and animate every other frame instead of every frame. Nearby and visible ones are unchanged. It must prove kills, waves and triggers come out the same. This is the main game-logic lever. | idea | ganados | 1.7-4.0: PS2 did NOT do this; Sept variant failed decisions | r100, r101, r103, r104, r105, r106, r107, r108, r10a, r118, r11a, r111, r113, r11c, r11d, r10f, r200 | M (3 d) | logic-equiv | none by construction (pose hold <= 1 tick if one enters view) | 0.5 | decisions-equivalent gate: kills, waves, bell, s30 | 13 |
| B3 | UI OT caching: rebuild the HUD/letterbox quad list only when it changes (exact render) | Every room | Drawing | The on-screen HUD and letterbox bars are rebuilt from scratch every frame. Rebuild them only when they change. | idea | render_fixed | 1.5: ui 4.29 model ms in the hV6 profile | all 26 | M (3 d) | exact | none | 0.4 | TA hash identity | 13 |
| D2 | Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | Rooms with Ganados | Game logic | Cap 5 alive instead of 6. Against your cap-6 rule; never scheduled. | priced | ganados | 1.1: -1.15 logic per alive Ganado | r100, r101, r104, r105, r106, r107, r108, r10a, r118, r11a, r113, r11c, r10f, r200 | S (1 d) | rule-conflict | none | 0.8 | user | 12 |
| B6 | Data prefetch in the world transform and actor skin streams (D-stall 30% CONSOLE in every bucket = ~23 ms of 76) | Every room | Drawing (world + characters) | The CPU spends about 30% of its time waiting for data. Ask memory for the next points before they are needed (prefetch) in the world and character drawing loops. | idea | world_verts,char_verts | 1.0-2.7: 8% of the vertex buckets; PMC page 2 D-stall 27-34% per bucket | all 26 | M (3 d) | exact | none | 0.3 | memlay A/B showed write misses are not it; read-side PREF untested | 12 |
| A1b | STATIC_OBJ_BAKE in every room: 0.12 ms per bakeable etc object (boxes/racks/ladders/windows x bake share) | Every room | Drawing | The same trick as A1 in every room: fold crates, racks, ladders and windows that never move into the room scenery offline. | priced | props_verts | 0.5-1.8: r101: 13 of 24 objects = 3.0 ms -> 0.12 per listed object | r100, r102, r103, r104, r105, r106, r107, r108, r109, r10a, r10b, r117, r118, r119, r11a, r11b, r112, r111, r113, r11c, r11d, r11e, r10f, r11f, r200 | M (3 d) | exact | none | 0.5 | A1 + per-room SOB_DUMP captures | 10 |
| C5 | Reduced Leon render rig (merge face/finger bones for the draw only; logic rig unchanged) | Every room (Leon) | Drawing (Leon) | Draw Leon with fewer bones (face and finger bones merged) while his animation and gameplay skeleton stay the same. Risk: hands and face look stiffer. | idea | char_verts | 1.5: ALT-VIEWS 1-2 ms | all 26 | M (3 d) | render-approx | medium (hands/face) | 0.4 | palette builder | 10 |
| C1 | Offline world distance LOD: halve the vertices beyond 12 m, same 25 m far plane | Every room | Drawing (world) | Make a simpler version of far-away scenery offline: scenery beyond 12 m uses about half the points. Draw distance is unchanged. Fences and outlines in the distance may look different; you judge still pictures. | idea | world_verts | 0.0-4.8: b12 = projected vertices beyond 12 m | all 26 | L (8 d) | render-approx | medium (fences, outlines at distance; sheet per room) | 0.6 | converter LOD level per room; hw/sheet per room | 9 |
| B2 | Collision broadphase cache (scenery line queries per actor): identical answers, fewer leaf tests. **Lane uicoll 10-15: measured ceiling ~0.5 MODELLED (walk only; scenery collision 1.83 total, Ganados 0.22 per update), net 0.2-0.35; not built** (docs/lanes/uicoll.md) | Every room; more with enemies | Game logic | Every character asks "what scenery am I touching?" every frame. Keep a short list of the nearby scenery so the same answer is found with fewer checks. Identical results. | idea | logic_fixed,ganados | 0.4-1.2: collision 3.3 model ms, ~70% per-Ganado | all 26 | M (3 d) | exact | none | 0.4 | STRICT over the route | 7 |
| B8 | FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap 64 hit in r100/r106/r107/r109/r119) | Effect-heavy rooms (r100, r106, r107, r109, r119) | Drawing (effects) | Use the PS2's effect amounts (smoke, sparks, mist) in the rooms that hit the sprite limit. A small saving: effects are only about 1.2 ms. | idea | effects | 0.2-0.5: FX is only 1.2 ms CONSOLE at the cross | all 26 | S (1 d) | render-approx | small (PS2 counts) | 0.5 | FX lane recipes exist | 6 |
| C6 | Ganado far mesh + hands merged into the body at mid/far | Rooms with Ganados | Drawing (crowd) | Distant Ganados use a simpler mesh with the hands merged into the body. A small saving at cap 6. | priced | char_verts | 0.3: <= 0.3 at cap 6 (VILLAGE-LEVERS pricing) | r100, r101, r103, r104, r105, r106, r107, r108, r10a, r117, r118, r11a, r111, r113, r11c, r11d, r10f, r200 | S (1 d) | render-approx | small | 0.5 | ganado_far_runtime.h | 6 |
| A7 | r11c PS2 cabin: waves of 5 instead of 9 at once (PS2_ENEMY_ROOMS 0x40, built, not run) | Cabin fight (r11c) | Game logic + drawing | Use the PS2's cabin enemy waves: 5 attackers at once instead of the GameCube's 9 (the PS2 gives them more health instead). Fewer enemies to think about and draw. It changes how the fight feels, so you decide. | built | ganados,char_verts | 4.6: 4 fewer alive; worst view 2 fewer drawn | r11c | S (1 d) | logic-gameplay | none | 0.6 | cxac1/cxac0 fight-length runs; user: PS2 HP +200 is harder | 6 |
| C3 | Per-room vertex budget enforced by the converter: decimate the PS2 mesh until the typical view is <= 8k | Rooms with heavy scenery | Drawing (world) | Simplify a room's whole scenery mesh offline until a typical view is under about 8,000 points. The biggest visual risk; judged room by room. | idea | world_verts | 0.1-8.3: user 10-10: "we can reduce triangles from there" | r101, r103, r104, r106, r109, r118, r119, r111, r113, r11d, r11f | L (8 d) | render-approx | medium-high (whole-room decimation) | 0.5 | converter; sheets; user per room | 3 |
| C2 | Impostor cards / baked far band beyond 18.75 m (long sight lines: r107, r119, r117, r11c) | Rooms with long sight lines (r107, r119, r117, r11c) | Drawing (world) | Replace very distant scenery (beyond about 19 m) with flat pictures. A big saving where you can see far, with a risk of a flat-looking horizon. | idea | world_verts | 0.3-4.7: b18 = projected vertices beyond 18.75 m | r100, r101, r103, r104, r106, r107, r108, r10a, r10b, r118, r119, r11a, r11b, r111, r113, r11c, r11d | L (8 d) | render-approx | medium-high | 0.3 | VRAM for cards; converter | 3 |
| A8 | Hold-only cap in the 9-alive exception rooms (r100 s20 ambush, r104): defer sends, never park | Village ambush (r100 scene s20) and r104 | Game logic | These two scenes are allowed 9 Ganados (exceptions to cap 6). Instead, hold the extra enemies back until one dies (never removing anyone), so at most 6 are alive. | priced | ganados | 3.4: 3 x 1.15 logic; drawn count unchanged in a typical view | r100, r104 | M (3 d) | logic-gameplay | none | 0.6 | test 14 note; r100 W->ems pointer safety (errEm already checked) | 2 |
| B9 | Ashley native/lean path (2-2/2-3): fewer draw runs, lazy face | Chapter 2-2 / 2-3 (rooms with Ashley) | Drawing | Give Ashley the same lean drawing path Leon got (fewer draw calls; her face updated only when it moves). | idea | char_verts,ganados | 1.0: guess; Leon pair gave -1.74 | r112, r111, r113, r11c, r11d, r11e, r10f, r11f, r200 | M (3 d) | exact | none | 0.3 | PS2_ASHLEY=2 | 2 |
| E2 | Effect flipbooks + remaining 16-bit textures as PAL4/VQ in every room (r101 done): VRAM for the resident lists | Rooms short on graphics memory (r113, r11c, r10b, r119) | Graphics memory | Compress the remaining effect and 16-bit textures (the VQ/palette formats whose sheets you approved) so each room's full texture set fits in graphics memory. It makes room for A5 rather than saving CPU time. | built | disc_stall | 0.2: enabler, scored at a token value | r10b, r119, r113, r11c | S (1 d) | conversion | small (VQ sheets approved so far) | 0.8 | A5 in r113/r11c (VRAM FAIL) | 2 |
| D3 | r10f gondola riders: half-rate AI while riding (riders are exempt from the cap, up to 15 on the first ride) | Gondola ride (r10f) | Game logic | Ganados riding the gondolas think at half rate while riding (riders are exempt from the cap: up to 15 on the first ride). | idea | ganados | 1.7: worst = first ride | r10f | M (3 d) | logic-equiv | none | 0.4 | rider state machine; decisions check | 0 |
| F1 | PACE_FLOOR_FPS 20 (or Off) at the cross so Smooth does not alternate between skipping and blocked around D ~47-50 | Village cross (r101) | Pacing | When the frame rate hovers near 20, the game alternates between skipping frames and waiting, which looks like judder. Set the pacing floor so it stays steady. No fps gain; a smoother feel. | idea | logic_fixed | 0: 0 ms; a judder fix | - | S (1 d) | exact | feel only | 0.9 | none | 0 |

Already counted in the room numbers, so not levers here: PS2_CH1_ENEMY + cap 6 (test 13; the peaks in the table), hw fog, PS2
effect pack, PS2_STRIP_GROUPS / WORLD_LEAN, texture-ID LRU, skipped-tick trims (PACE_TRANS_SKIP). Checked and dropped: native
part list for dynamic parts (NO-GO, < 0.5 ms), memlay A/B (console: 0), sh4zam / approximate maths (< 0.5 ms, hygiene), per-model
setup caches (< 0.3), tier levers (nothing to work on at cap 6), TA buffer shrink (0 KB: VRAM-MAP), single-bank TA layout (VRAM
only, costs CPU/GPU overlap), letterbox cull (0.3%), PACE_CAP=2 (lower fps), half-rate effects move (RNG desync), half-rate cloth
(LEVEL 2, rejected).

## 5. Priority formula, ranked backlog, tranches

```
score(lever) = sum over rooms [ eff_ms(room) x w(room) ] x conf(lever) / ( effort_days x risk_factor )
eff_ms       = min(ms, gap) + 0.25 x max(0, ms - gap)        gap = D_typ - target (33.3; r101 50); the 0.25 is "stack every gain"
ms           = lever formula(room) x sqrt(room confidence)      (2-2/2-3 rooms count at ~0.6, the cross at 0.92)
w(room)      = play minutes x route share x (1 + gap / 10 ms) x 1.5 if among the three heaviest rooms
risk_factor  = exact 1.0 | conversion 1.0 | render-approx 1.3 | logic-equiv 1.6 | logic-gameplay 2.0 | rule-conflict 3.0
```

The sequence re-scores every remaining lever against the gaps left by the previous picks (greedy), first with 50 ms as every
room's target (stage 1), then the room targets. Tranche 1 is scope, not score: everything already built or gated lands first.
Tranches 2-4 cut the greedy order at ~15 / 20 / remaining effort-days. World-geometry levers (C1 / C2 / C3) overlap: the second
one taken counts half.

**Top 10 by static score (against today's gaps):** A3 1357, A2 733, C4 187, A2b 129, A5 119, A9 108, A6 108, A1 107, B5 81, B4 66
(C8 141 and D2 57 are rule conflicts: shown, not scheduled; D1 64 is next).

| Tranche | In plain words | Levers (in greedy order) | Effort | Rooms <= 50 ms typ (worst) | Rooms <= 40 typ | Rooms at target typ (worst) | Cross typ / worst | Farm |
|---|---|---|---|---|---|---|---|---|---|
| today | Where we are now | - | - | 8 / 26 (3) | 1 | 0 (0) | 67.6 / 77.9 | 86.9 |
| T1 land what exists | Land finished work: no more disc waits on the farm, small exact clean-ups, lighter PS2 enemy models, the village's baked objects, textures loaded once per room, a new code layout, PS2 cabin waves, texture compression. | A3 cold pool, A2 small bundle, A9 PS2 cast (7 rooms), A1 r101 bake, A5 resident lists, A6 LINK_ORDER (after LINKORD2), A7 r11c PS2 waves, E2 VQ | ~8 d | 12 (3) | 2 | 0 (0) | 63.7 / 74.0 | 62.0 |
| T2 cheap exact + the two whole-game bets | Cheap exact fixes plus two whole-game bets on the CPU caches: flatter crowd lighting, GameCube leftovers removed, smaller busy code, far Ganados thinking half as often, a faster world walk, prefetching. | C4 flat crowd/object lighting, A2b census trims, B5 I-cache code size, D1 far-Ganado half rate, B4 world walk lean, B6 data prefetch | ~14 d | 13 (4) | 4 | 1 (0) | 59.1 / 68.9 | 58.7 |
| T3 structural | Structural work: HUD caching, baked objects in every room, a lighter Leon drawing rig, simpler far scenery, a collision cache. | B3 UI OT cache, A1b bake everywhere, C5 Leon render rig, C1 world distance LOD, B2 collision broadphase | ~20 d | 18 (5) | 4 | 1 (0) | 55.2 / 63.5 | 54.9 |
| T4 remainder | The remainder: small crowd and effect trims, Ashley's lean path, far-scenery pictures, per-room vertex budgets, the hold-only cap, gondola riders. | C6, B8, B9 Ashley, C2 impostors, C3 vertex budget, A8 hold-only, D3 riders | ~27 d | 18 (5) | 5 | 1 (0) | 53.5 / 61.3 | 53.9 |
| optimistic (all at face value) | Every lever above at its full modelled saving, no discount | same set, no confidence discount | - | 26 (26) | 26 | 19 (7) | 37.7 / 42.1 | 27.7 |

Reading the table honestly:
- The expected line says the catalogue gets most rooms to the 20-fps-blocked floor and almost none to 30 fps; the optimistic
  line says 30 fps is reachable in 19 typical views if everything delivers. The difference is the confidence discount on the
  three big bets (B5, B6, C1) and on the 2-2/2-3 room data. The first console A/B of any one of B4 / B5 / B6 moves the whole
  table more than any other measurement.
- Rooms that stay above 50 in the expected view: r101 (53.5), r103 (53.9: the farm after the cold pool, plus its 24-29 ms GPU),
  the four GameCube-crowd rooms of 2-2/2-3 (r111, r113, r11c, r11d at 58-61: conversion + cabin waves are their only big levers
  until the whole-game bets land), r11e and r10f (50-51).
- "Stack every gain" is honoured by the 0.25 residual: a room already at target still earns a quarter credit, so whole-game
  levers (A2, C4, B5, B4, B6, B3) keep their rank above room-specific ones once the easy rooms are done.


> **Owners (10-15 evening):** T1 = test 14 RC lead (merging the gated items; LINK_ORDER waits for LINKORD2 on the console; PS2 cast continues in the ps2cast lane). T2 exact levers A2b, B4, B6 = lane t2exact (drawing). T2 D1 far-Ganado half rate = lane farhalf (game logic; decisions-identical first, otherwise offered as an option). B5 I-cache code size = lane t2exact too (console bench-disc variant on KOS_DISC_FIX). C1 world distance LOD = lane worldlod (largest unrejected lever at the cross; look judged on still pairs). Still unowned: C4 flat crowd lighting (needs a look sheet). **B3 UI OT cache + B2 collision broadphase cache = lane uicoll (user OK 10-15 evening).** **User 10-15: heavy rooms get a proactive, budget-driven far LOD** (converter gate; about 10k world vertices typical and 15k worst per view; LOD level per room set by the gap; far plane unchanged). The r119 look sheet sets the method first. Over budget: r119, r107, r117, r109, r106, r104, r103, r101, r100, r118 (r10a borderline). The same gate applies to every newly converted room. **User 10-15: buffer every room** assuming the Ganado logic improves (WORLD-BUDGET-BY-ROOM-20261015.md, "Buffered targets", 10% margin). Rooms that can't reach their target are cut to the look floor; no net heap growth.

## 6. Alternate views

**Is per-room budgeting the right frame?** Only half. The per-room table is right for the content levers (world geometry, props,
Ganado counts, GameCube fallbacks, disc stalls), which differ 10x between rooms. But the console pages say the drawn tick is
dominated by terms that are the same in every room: logic + per-tick work ~22 ms (of which Ganados ~7 at cap 6), Leon ~11, the
world walk 2-7, render fixed 3.5, and underneath all of it 40-50% cache-stall time. Those are whole-game levers and they are what
decides 30 fps. The per-room frame cannot see them because they are constants in the model. A better statement of the goal:
**"fixed per-tick cost <= ~20 ms (logic 12 + Leon 6 + render 2), then a per-view content budget of ~13 ms (about 10k vertices +
props) at 30 fps"**; rooms are then checked against the content budget only, which is what the converter can enforce.

**The ~50% stall share is the largest single number in the data and nobody owns it.** D-stall 25-34% and I-stall 16-21% in every
bucket, both scenes, ~300k D-misses and ~160-200k I-fills per picture (CONSOLE). Three different levers address it and all are
cheap to try on a bench disc: (1) code placement / size for the 8 KB I-cache (A6 regenerated, pending the KOS DMA fix; B5
-Os cold paths, hot kernels contiguous), (2) read-side prefetch in the two streaming loops (world transform, skin kernels: B6; the
memlay arms tried write-allocate, which the console rightly priced at 0), (3) fewer, larger data structures per part (the ~380 KB
of per-frame struct zeroing is already in A2). The honest expectation is 3-8 ms from the three together, with a wide band; the
honest risk is another LINK_ORDER lottery. A single "I-stall / D-stall per phase after each arm" console page settles it, and the
benchmark disc already prints it.

**What I would do differently.**
1. Stop treating the house as the independent check: it is logic-bound (29.3 ms skipped tick, ~12 alive uncapped on 12.1) and
   tells us about K_GAN, not about render. Re-run it on a cap-6 build so the Ganado-logic constant is pinned without an assumption.
2. Make the per-view content budget a converter gate now (C3's machinery) even before anyone decimates: every room's typical and
   worst views listed against ~10k world + props, so the 2-2/2-3 and castle conversions ship within budget instead of being
   tuned afterwards. r109 (16k typical), r106 / r103 / r113 (9.5-10.5k) and the lake / canyon worst views (r107 27k, r119 33k,
   r11c 21k) are the ones over it.
3. Put the far-Ganado half rate (D1) and the PS2 cabin waves (A7) in front of the user as a pair with their console ms, under the
   approximation rule: together they are worth 5-9 ms in the crowd rooms, more than any render idea short of the world LOD, and
   they are the only logic levers left after PS2 rules + cap 6.
4. Treat the GPU as a second budget for the farm class of view (24-29 ms CONSOLE, world fill 14): 30 fps there needs the fill cut
   as well, which the distance LOD and the hw fog already address; add GPU ms to the room table when Part 2's farm sweep is
   repeated after the cold pool.
5. Drop the morning model's conclusion that "props at the cross are the top lever": the console sweep could not isolate props
   (K_OTHER is assumed = Ganado rate), and A1's 3.3 ms is the only priced piece. Add a "no props" row to benchmark v3.

## 7. Uncertainties, and the console measurement that resolves each

| # | Uncertainty | Size | Resolves it |
|---|---|---|---|
| 1 | **Cache-stall levers (B5 / B6 / A6)**: 25-35 ms of stall per drawn tick is measured, the share any lever recovers is not (0-8 ms) | decides 30 fps vs 20 fps everywhere | LINKORD2 console A/B (pending the KOS DMA fix), then one bench disc per arm reading page 3 I-stall / D-stall |
| 2 | **Ganado logic per alive unit (1.15) and Leon logic (3.4)**: fitted with the house count assumed | +-3 ms in every crowd room; decides D1 / D2 / A8 value | live (not frozen) half / no Ganados and no Leon rows on a cap-6 build, LOGIC column (benchmark v3) |
| 3 | **The farm after MOTION_COLD_POOL**: is the 34 ms all stalls, or does the farm view carry ~20 ms of its own (frozen floor 53.5 vs cross 47.5)? plus its 24-29 ms GPU | r103 and every all-cold-archive room (r117, r119, r11d, r11e) | repeat Part 2 farm scene + sweep on the test 14 candidate |
| 4 | Props / parts / UI rate (K_OTHER assumed 1.2 per 1k; 9.5k at the cross, 0.5-2k elsewhere) | +-5 ms at the cross; A1b value | a "no props" sweep row (v3) |
| 5 | 2-2/2-3 rooms: lane packages, enemy counts, Ashley cost, no timing | +-20% on 9 rooms | one Flycast benchmark scene each for r11c (siege) and r113 once they run clean; console when released |
| 6 | Interior pessimism (house +20%, Del Lago +11%): the fixed-cost split between F, the world walk and props | budgets 5-10 ms too tight indoors | the same "no props" row plus a house sweep |

## 8. Files

- `PERF-BACKLOG-CH1-2-20261015.md` (this), `PERF-BACKLOG-CH1-2-20261015.csv` (kind = bucket / lever / lever_total / room_after;
  lever rows: ms = typical view, budget column = worst view, score, tranche, status, effort, risk, conf).
- `room-budget-20261015\backlog.py`: recomputes buckets, scores, sequence and the CSV from `ROOM-BUDGET-PROJECTION-20261015.csv`
  plus its constants (checked against the CSV at start). `python -I backlog.py --md` also prints the two tables above.
- `room-budget-20261015\budget.py` + `emit.py`: the norms model and the projection CSV/MD (console-calibrated constants, with the
  benchmark row that pins each). Change a constant there, rerun both, then rerun backlog.py.
- World projections for the 2-2/2-3 rooms were computed with the same `roomproj.py` code over the route-v7 lane packages read
  from WSL (`/root/probe/codex-ps2-*`); the per-room results are embedded in backlog.py (WORLD table) with their sample counts.

## Status update 2026-10-15 evening (coordinator)

| Item | Outcome | Next |
|---|---|---|
| Store-miss levers (MOVCA, SQ, PREF) | CLOSED. The console Bench A/B results refit the model to a store-miss cost of 0-5 cycles; the largest remaining lever is 0.13 ms. The refit is now hwproject's default "console" column (lane/storemiss 8aa745ab). | none |
| SG_SELECT_LEAN | CLOSED. Logic-exact, but the real pipeline saving is -0.18 ms (the rest of the -0.7 is code placement the model can't price), and it fails the KOS squeeze at leave100/leave103 (+1,728 B). | none |
| B5 HOT_COLD_SPLIT | PARKED. The t5cB/t5hB bench pair is kept on ext4. It goes on the console only if the LinkOrder D3-FIX vs D3-CTL A/B shows code layout moves console CPU. | wait for the D3 console result |
| .r4sg strip groups, more rooms | DEFERRED. 0.42-0.75 ms per room (r100, r103, r104, r106, r107, r108, r10b, r118, r119, r11b) at 19-123 KB heap 4 per room. Regenerate them from the world-vertex-ladder output per room, so the world meshes aren't converted twice. | with the world lane, per room |
| SLAB_PIN | PARKED (layout lever, never built). Branch lane/t2exact-slabpin da4bac57. | only with B5 |
| GANADO_LOD g70 | READY for test 15 (GANADO_LOD=1 LEVEL=2, LEON_LOD=0). -0.65 cross / -0.10 house, MODELLED on the old fit. _end +928 B. POC101's DETAIL row did not load the LOD packages: ignore that row. | t15/int recipe |
| SH4ZAM memset/copy (shz_memcpy everywhere) | In progress. Exact. Re-priced -0.60 cross / -1.05 house MODELLED on the refit, unconfirmed (Bench B caution). | gates on the kos-ports base |
| SH4ZAM from kos-ports, upstream v0.9.1 | Image-identical switch; landing in t15/int | t15/int |
| KOS_SBRK_LAST_PAGE | +4,096 B KOS (exact); all gates passed | t15/int recipe |
| LINK_ORDER (I-cache, ~20% of CPU) | First real console A/B pending: D3-FIX vs D3-CTL, SD slots 158-160. It fails the KOS squeeze at leave100/103 without KOS_SBRK_LAST_PAGE. | user's SD run |
| World vertex ladder r101 | Levels L0-L3 built; rendering checkpoint sheet requested by the user before any pricing | user's look verdict |
