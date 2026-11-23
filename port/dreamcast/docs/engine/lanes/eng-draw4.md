# Lane eng-draw4: the characters' drawing kernels and three look choices (2026-11-22, brief H-032)

**Status: finished, unaudited.** Branch `lane/eng-draw4` from `lane/eng-draw3` 72ca57131, `origin/engine` merged
(28ad25ce7 at c43653f46, again at efc794db8 before hand-back).

Tier of every speed number: **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, slot fly1,
`Sh4Clock = 70`, `Dynarec.Enabled = yes` (each run's `emu.cfg.used`), all runs in one session (2026-11-22 07:28-09:05),
each step beside the base re-run on the same slot. The tier repeats itself: base runs r0a and r0b gave the same
timing to 0.01 ms. The standard build reads the engine 3 to 10% kinder. Budget row (ENGINE_PLAN section 4): drawing
14 ms; no scene passes it (best: FIGHT 22.96 ms mean with step 3b).

**What the model cannot see:** the graphics chip (TA vertex intake, ISP/TSP fill and sort), store-queue submission
timing (the SQ writes are charged as instructions only), cache and bus contention, disc timing. Pixel counts are
Flycast's (its FTRV/FMAC precision differs from the console's).

## Step 1: base (merged head 7c357dc87), twice
| Scene | drawing mean / p99 / worst ms | characters mean / p99 / worst |
|---|---|---|
| LEON | 26.25 / 31.39 / 31.58 | 12.40 / 12.79 / 15.24 |
| HILL | 36.63 / 41.97 / 42.19 | 24.74 / 28.16 / 30.54 |
| FIGHT | 23.59 / 30.81 / 30.99 | 10.52 / 15.19 / 17.53 |

Stills floor (r0a vs r0b, the same disc twice): 11 of 59 stills differ (up to 27 px; LEONS 360/480/520, HILLS
40/80/200, FIGHTS 280/640/720/880). r2 against r2b (step 3b's disc twice) shows other stills varying too (LEONS 1, FIGHTS
480, 720): the stills are not fully repeatable run to run; one floor pair does not find every varying still.

## Step 2: per kernel a picture (characters span, MODELLED; lab sets B and E, the "twice" arms)
| Kernel | LEON | HILL | FIGHT |
|---|---|---|---|
| emission (opaque; + hair in TR) | 3.61 (+0.49) | 8.11 (+0.51) | 2.71 (+0.42) |
| normals lit | 4.23 | 7.47 | 3.08 |
| skinning (positions) | 2.16 | 4.06 | 1.89 |
| weight sets (blend, project, set lights) | 1.10 | 2.36 | 1.01 |
| part classes and whole-character test | 0.22 | 0.40 | 0.06 |
| light pick | 0.08 | 0.12 | ~0 |
| submission | in emission (SQ stores charged as instructions; the queue's own time is not seen) | | |

New lab set E (boot file `DLE`: K skin twice, P light pick twice, C part classes twice, D 2 ms), run rk. The 2 ms
control read +1.96 to +2.04 ms in all six scenes (PASS).

## Step 3: exact steps
| Step | Commit | characters LEON / HILL / FIGHT (mean) | emission arm (hill) | stills vs base (floor r0b) |
|---|---|---|---|---|
| base | 7c357dc87 | 12.40 / 24.74 / 10.52 | 8.11 | - |
| 3a C: inside parts, no test a strip | ea689d6fa | 12.13 / 24.18 / 10.36 | 7.60 | 48/48 identical |
| 3b asm: strips walked in the kernel (`m1_emit_actor_run`), corners 4 to a block | 290602147 | **11.73 / 23.15 / 9.96** | 6.47 | r2: 46/48 (2 px HILLS 120, 7 px FIGHTS 480); r2b: 45/48 (11 px, 7 px) at other stills |
| 3c C: branch-free colour byte | c9e9f3a38, **reverted** c6fca26d2 | (with 3a, 3b) 12.21 / 24.36 / 10.32 | lighting arm 8.62 against 7.47: slower | 47/48 |

Step 3b drawing row: LEON 25.46 / 30.57 / 30.70, HILL 34.96 / 40.29 / 40.44, FIGHT 22.96 / 30.11 / 30.27 (mean / p99 /
worst). Step 3b sends the same vertex words in the same order as before (the corner macro is unchanged; only the walk
moved into the kernel). Its differing stills change from run to run (r2: HILLS 120; r2b: LEONS 1 and others), which reads
as the stills' own variation, but it is not 0 px proven on one floor pair. Why assembly: step 3a's C loop still paid a
call, a prologue and the C loop's blocks for each strip (strips average about six corners); 3b saves 0.40 / 1.03 / 0.40
ms more than 3a.

Steer H-032 (borrow proven old pieces): the skinning kernel already is the old port's (`re4dc_avk_pos_skin_u16`,
game/platform/avk_sh4.S, no difference to `origin/t15/int`). The old light kernels (`re4dc_avk_light_*_n16`) take at
most 3 lights, sum through FTRV and clamp at 255 after the material scale (the engine's rule is k x min(1, r)): not
0 px by construction, so a look arm, not an exact step; not measured. The old emitter copies pre-built 32-byte vertices
from a meshlet vertex cache (characters baked into that layout): a bake, not a kernel swap; not measured.

Controls: the 2 ms arm PASS in every run with set B (HILLT) and set E. The pixel comparison's control `PIXCTL` (one
blue step flipped on every character colour, services/actor_e1.inc): run rpx FAILS as it must (E1 0 of 29 identical,
FIGHTS 3 of 19). Step 3c's own failure is its timing (kept out).

## Step 4: look arms (boot files, off by default; each on the head with 3a and 3b; arm against r2)
| Arm | characters mean LEON / HILL / FIGHT | p99 | stills vs base | sheet |
|---|---|---|---|---|
| LVL detail levels by screen size (pack's PS2 levels, bench step 3) | 11.58 / 21.45 / 9.93 | 12.10 / 24.57 / 14.09 | E1 11/29 identical (Leon at level 1 on the hill: 13,329 px); FIGHTS 13/19 | `sheet\LVL-sheet-20261122.jpg` |
| LCAP at most 3 lights a character | 11.69 / 22.85 / 9.97 | 12.04 / 24.88 / 14.33 | 0 px on all compared stills | `sheet\LCAP-sheet-20261122.jpg` |
| LHALF lighting every other picture | 9.51 / 18.84 / 8.47 | 12.43 / 26.43 / 15.23 | E1 2/29, FIGHTS 4/19 (up to 30,778 px) | `sheet\LHALF-sheet-20261122.jpg` |

Notes: LVL only moved Leon (level 1 under 480 px: 180 pictures in LEON, 583 on the hill); the Ganados stayed at level
0 by its counters, yet FIGHTS differs by up to 2,098 px on a Ganado (unexplained). LHALF halves the mean but not the
worst picture (every character lights on the same picture); staggering characters across pictures is the next step.
LHALF costs memory (FIGHT arena margin -40,960 against -12,288 on the base).

## Findings
1. FIGHT is over its memory line on the base (arena margin -12,288): eng-mem1's.
2. drawcost.py reports "stamped spans exceed the drawing row" on 12-26 pictures a scene on the base; not this lane's
   change (reported to the drawing-account owner, eng-draw1's tool; not loosened).
3. HILLT reads FAILED in the selector ("image says timing, schedule says function") because the disc puts NOTRACE in its
   folder: a lane-disc artefact, its rows are complete.

## Files
Owned: render/native_actor.inc, render/stage_sh4.S, render/source_light.inc, services/actor_e1.inc. Outside the owned
list (measurement only, set E): render/draw_cost.h, render/draw_cost.inc, tools/engine/drawcost.py. No stubs, no
original unit linked. Images at efc794db8: default, BOSS, SENDABLE PASS check_link; FIGHT links, SERVICE 30 (the
engine's figure; this lane touches no service code).
