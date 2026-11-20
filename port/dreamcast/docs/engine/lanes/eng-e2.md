# eng-e2 hand-back (E2: the four-Ganado village fight on the engine, native effects), 2026-11-19

Lane `eng-e2` on `lane/eng-e2` from `origin/engine` 28189e752; merged `origin/engine` 7869ba2ff (eng-e1c: native
skeleton and collision in the image; eng-svc3) during the lane. Tiers: **Flycast** = guest timer, standard harness
Flycast (std slots); **MODELLED** = nominal 200 MHz SH-4 hwsim over a Flycast hwtrace (fly slot); **PC** = the effect
check. No console number. Evidence: `E:\RE4DC-Lanes\eng-e2` (`runs`, `build`, `s`, `STATUS.md`, `HANDBACK.md`).
Owner steer of 2026-11-19 ("Split it") applied: presentation randomness on engine generators, plays right judged on
gameplay events, no original service code in the image where a native service exists.

## 1. What runs (`make -C port/dreamcast/engine/game FIGHT=1`, `game/fight.mk`)

The engine image boots into the village square (r101) at the cross, the old game's fight fixture: Leon on his original
player code, the room's original set-up spawning the Ganados at cap 4, their original AI, the room script's waves and
camera-cut event, the native effect service, all drawn by the engine renderer.

| Part | Where | What |
|---|---|---|
| Hosted behaviour (src/ unchanged) | `game/fight.mk` FIGHT_SRCS | em10 (Ganado library) + em15_set (village square set file), em_set (list and creator), em_sub, dmg, em_dm_val, st1/r101 (room script), sce_com, sce_at, area, em_wrap (room-script sends, find-player), game (difficulty points), libgpu (ordering tables) |
| Behaviour knobs | `game/fight.mk` | the release recipe's enemy rules, which are the game's behaviour now: cap 4 (ALIVE_CAP=4, r101 through R101_ALIVE_CAP=4 with capped waves, park), chapter 1 PS2 rules (PS2_ENEMY_RULES, PS2_ENEMY_ROOMS 0x33f), ANIMALS_OFF. Every other knob off |
| Room set-up | `fight/fight_e2.cpp` | gameRoomInit's order: chapter 1 list (etc/emleon00.esl) with the PS2 USA rows (stage.cpp's list patch), effect data (core owners 0 / 0xD1, the room's EFF), areas (SceAtInit), EmSetRoomInit; then ScenarioRoomInit on tick 1 (the old run's enemy timeline): R101Init, a scheduler pass, EmSetFromList (cap 4), SceAtRoomSet. Same 4 Ganados as the old game (types 4/3/4/0, positions, life, order) |
| Scenario tasks | `fight/fight_e2.cpp` | one KOS thread per task, strict hand-off; a pass runs every waiting task once and restarts from the head after each run (cSceSys::scheduler), so a task created this pass runs this pass |
| Ganado module | `fight/fight_e2.cpp` | em/em15 with its 158 motion clips' keys linked in place (no disc read in play); the archive pointer kept across the module init (the value-initialising construct zeroes it in this build) |
| Route (pad) | `fight/route_fight.cpp`, `acts_cross.inc` | the fixture's acts with the warp rig's semantics (actions cut by events), god, ammo rule, the fixture's goto |
| Services | merged eng-e1c wiring | skeleton and collision native (`services/skeleton`, `services/collision`); cloth and shape keys stubbed (no native service); original units still linked as in E1: cMotBase, atariInfo / at_mod / at_sub (actor volumes), route_ck (routes), parts of model/motion/atari |
| Effects | `services/effects/fx.cpp` (new) | section 2 |
| Presentation randomness | `game/fight.mk` PRESENT_em10/em10 | the Ganado's voice, breath and chainsaw sound timers, blood-effect choice and camera moves in `e1_present` (engine generator); the effect service has its own generator |
| Drawing | `fight/fight_draw.inc` | the village bake; Leon and the Ganados through the E1 actor pass from their native skeleton tables (palette checked per model; character level picked by on-screen size, owner default step 3); the effect sprites from the SoA arrays (density cap step 2); the HUD |
| Pack | `fight/pack_trim.py` | the village pack with its nine recorded streams cut to picture 0 (the image reads no other): 4.89 MB, RAM part 2.57 MB (was 6.6); FXMAP.BIN: 170 (texture, pattern) -> material header rows from all 300 recorded pictures |
| Room data | `core/loader.cpp` (E2_FIGHT) | r101.arc reduced to the 17 sections the fight reads (1.1 MB of 1.85 MB stay on the disc) |

Shared files touched (narrow, E2_FIGHT only or additive): `core/draw_e1.c`, `services/render_e1.c`, `core/loader.cpp`,
`host/e1_engine.h` (arena), `host/e1_wraps.cpp` (three exported accounting calls), `core/e1_core.h` + `core/frame.cpp`
(effects service group, ROW `sfx`), `host/e1_stubs.cpp` (three stubs guarded), `game/Makefile` / `hosted.mk` (FIGHT).
E1 and BOSS images build after the merge.

## 2. Native effect service and its equivalence check

**Design** (`services/effects/fx.h`, `fx.cpp`): the engine bodies of EstSet, EspDataLoad / Release, EspGetEstAddr,
EspEstSetSelect, EspSetEatEffect, the deletes. Effect tables read in place from the EffData the hosted code registers;
packed Dreamcast records (ESQ tables) decoded when a sequence spawns them. Sequence players (espgen10's frame: model
check, parts or offset matrix, records spawned on their Set_time). Sprites in SoA rows (position, speed, acceleration,
damping, angle, angle speed, sizes, colour and multipliers, counters, texture animation), one kernel per field group over
the dense live range in the original's per-sprite order (release, motion, size, angle, colour envelope, life,
animation), dead sprites compacted by swap. Seeds from the engine generator (xorshift); per-sprite spreads from that
seed with the original's per-instance LCG. Not simulated: per-id SetFreeWork extras (ribbons, trails, lights; every id
moves as the plain sprite), nested generators (Kind 1), effect models (ids 0xFC-0xFF), room SST effects.

**Check** (PC, `services/effects/check`, `fxcheck`): the original effect functions copied verbatim with knobs off
(`orig_extract.py`: EspSeqSet, cEsp::CommonMove / ColorUpdate / AnmMove / ApplyMatrix, PullEsp / PushEsp / operator
new, espgen10_Update / EspgenDataSet, fRandSeed1_1, esp00's plain sprite) against `fx.cpp`, both fed the same EffData
from the disc tree and the same effect starts with the same seeds (the 85 EstSet calls of an engine fight run's report),
compared every tick by spawn order: count, position (0.01 unit), size, alpha, life, pattern.

| Input | Ticks equal | Bit-identical | Sprites | Most live |
|---|---|---|---|---|
| native image run `n2-t1` | 901 / 901 | 901 | 264 | 20 |
| first-form image run `f1t-3` | 901 / 901 | 901 | 267 | 17 |
| Control: one sprite never spawned (drop=5) | FAIL at tick 1 (9 / 8 live) | | | |
| Control: gravity x 1.01 | FAIL at tick 27 (7.65 units) | | | |

Ids spawned in the fight (native run): 0x00 plain sprite 508 (covered by the check), 0x01 strip 4, 0x0b 14, 0x11 30,
0x46 glow driver 1 (moved as plain sprites: approximation, look only). Generator draws: none from Rnd by construction.

## 3. Plays right (gameplay events; positions 1 unit and yaw 1 degree while the actors do the same thing)

Old game: the eng-e1b reference image (release recipe + LOGIC_TRACE + LE lines, Flycast) on fixture
`s/fixtures/cross-fight16-warp.txt` (r101 fight from the bell-gate warp, god, ammo rule, aim and fire every 12 frames,
two turns, a facing goto at room frame 561). Old run `runs/ref-cross-16`: 4 spawns, hits t=25 / 49 / 73 / 456 / 576,
**kill t=624**, a capped spawn t=710, wave 1 t=37 and its camera cut 127-249, wave 2 t=249 (engine ticks, old = 184 + k).
Tool `s/fight_pr.py`.

| Comparison | Gameplay events equal | First divergence | Positions |
|---|---|---|---|
| Native image, no feed (`n2-t1`) | 7 of 16: 4 spawns, hit 25 (800->650), wave 1 at 37, hit 49 (650->500); camera cut 127-249 and wave 2 at 249 also on the old ticks | old hit at 73 (500->320) has no engine counterpart: the engine's Ganado walks elsewhere (positions apart from tick 11); engine hits at 264 and 312 instead, no kill in 900 ticks | Leon 787/900 within 1 unit (first out 763), yaw 717/900; walking Ganado to tick 10; standing Ganado 900/900 |
| Same, diagnostic generator feed (`n2-feed`) | 6 | hit 2 one shot late (73 vs 49) | walking Ganado to tick 48 |
| First-form image (original skeleton units), no feed (`final-t1`) | 6 (wave tick convention aside) | same third-hit divergence | |
| Control: every pad action one tick late (`n2-ctl`) | 4 | FAIL: first hit at 26 instead of 25 | |
| Checker controls (old vs doctored old, `s/doctor.py`) | old vs old PASS; kill not credited FAIL at the kill (t=624); first hit one tick late FAIL at t=25 | | |
| Determinism: the native image twice | 5,410 trace lines identical | | |

Cause of the divergence, by elimination: the engine starts the fight on the old run's state (same Ganados, same hits and
damage, same waves and event timing), and the walking Ganado leaves 1 unit of the old run's path at tick 11. With the
split, the old run's effects draw the game generator (3 draws a sequence start, plus per-effect draws) and the engine's
do not, so the AI's numbers differ from the first effect start; the feed arm gives the old run's state at each tick
start and moves the departure to tick 48 (the old effects also draw inside the tick). Not hosted that can also matter:
room ETC objects (doors, windows, ladders, racks), the Ganados' held weapons (SetWeapon), room controllers 11 / 12
(Ctrl12Ck 7,220 calls answer 0), items, sound (section 6).

## 4. Budget rows (ms a picture; budget behaviour 2, services 9, drawing 14, system 3.5, busy 33.3)

Flycast, 600 pictures 41-640, NOTRACE, drawn (`runs/n3-a`, native image; `runs/final-a`, first form):

| Row | Native: mean | p99 | worst (picture) | over row | First form: mean | p99 | worst | over |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Behaviour | 0.80 | 7.85 | 29.86 (249) | 17 | 0.70 | 7.63 | 29.71 (249) | 18 |
| Services | **5.28** | 9.16 | 9.29 (548) | 17 | 7.58 | 12.39 | 14.48 | 250 |
| - motion (skeleton) | 2.93 | 4.13 | 6.56 | | | | | |
| - cloth | 0.00 | | | | | | | |
| - parts + palette (skeleton) | 0.99 | 1.44 | 1.47 | | | | | |
| - collision (cores, volumes, routes) | 1.32 | 4.02 | 4.14 | | | | | |
| - effects (native service) | **0.04** | 0.39 | 0.42 | | | | | |
| Publication | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Drawing | 10.58 | 15.28 | 15.50 (628) | 42 | 10.63 | 15.33 | 15.38 | 47 |
| System | 0.04 | 0.03 | 2.45 | 0 | 0.04 | 0.06 | 2.72 | 0 |
| **Busy picture** | **16.71** | 28.27 | 47.44 (249) | 1 | 18.95 | 30.35 | 49.99 | 3 |

- Over their rows (Flycast): **drawing** (42 pictures over 14), **services** (17 over 9, worst 9.29), **behaviour**
  (17 over 2: the pictures where the hosted code prints to serial: wave reports, first stub calls; the worst, picture
  249, is wave 2's report and its capped sends), **busy** (1 picture over 33.3: picture 249, 47.4 ms, over two fields).
- Half-budget rule (no console number): services 5.28 Flycast is over half its row (4.5); busy 16.71 just over 16.65.

### 4a. MODELLED (nominal 200 MHz SH-4 hwsim over a fly1 hwtrace of the same NOTRACE image, 25 pictures 41-617 step 24, `runs/model-n3`, `s/msplit.py`)

| Row | Mean | Worst (picture) | Over |
|---|---:|---:|---|
| Tick (behaviour + services + glue) | 10.13 | 43.65 (496) | |
| - skeleton (native service) | 3.01 | | |
| - cloth | 0.00 | | stubbed |
| - collision (native cores + original volumes, routes) | 0.90 | | |
| - effects (native service) | **0.06** | | |
| - behaviour (hosted game code) | 0.92 | | |
| - engine glue (scheduler, copies, wraps) | 1.63 | | |
| - maths library (matrices, sin/cos; shared by skeleton and behaviour) | 1.03 | | |
| - system (serial) | 2.57 | | 1.93 of it is `scif_write`: the logging stubs' first-call lines on pictures 41 and 496 |
| Drawing | 13.94 (fight pictures 16.24) | 19.74 (544) | **19 of 25 over 14** |
| Busy | 24.11 (median 25.41; fight pictures 28.78) | 59.84 (496) | 2 of 25 over 33.3 (41, 496: serial lines) |

The five camera-cut pictures (137-233) draw 4-5 ms with no actor ticks; the 20 fight pictures carry the numbers.
Over in MODELLED: **drawing** (the fight's pictures at 15-19.7 ms against 14) and **busy** only on the two pictures
with serial lines. Services 3.97 MODELLED is inside its 9 ms row and under half of it.

## 5. Memory (Flycast, native image)

Image 0x8c010000-0x8c2c47e8; KOS heap after the pack 0x8c9be000 (room sections, core, player, weapon, pack 2.57 MB);
the Ganado module 1.13 MB + motion keys 1.83 MB at tick 1; behaviour arena 0x8cd80000-0x8cec0000 (1.25 MB, high water
838,720 B, 17 allocations, 0 failures); services region 0x8cec0000-0x8cfc0000 (skeleton pool 256 KB, 105,248 B used in 6
tables; collision tables 470,240 B); kernel stack 0x8cff0000. Overlaps 0. A first build with the arena at 0x8cd80000 and
the whole room archive overlapped the arena with the motion keys (reboot loop at the first picture): fixed by the room
archive reduction.

## 6. Stubs hit (native run, 900 ticks) and what they stand for

Behaviour-relevant: Ctrl12Ck 7,220 / Ctrl12Set 216 (room controller 12), Ctrl11 sound 230, cItemMgr::check 900,
SceExecCheckCondition 899, SetWeapon 3 and SetObj12 4 (Ganado weapons and carts not created), getRoomEtc* (doors,
racks, ladders, windows, breakables: none), ChkWindow 83, GetEm10EyeEffectEnable 4, EmReadSearch 1 (the event module
reservation), SetObj10 30 (shell casings). Presentation: SndCall 181, SndStop 452, streams, HUD (Cockpit, IDSystem),
lights, shape keys 4,665, Leon's cloth 779. Events: event data units empty (the camera cut is the hosted camera code's).

## 7. Staged disc

`E:\RE4DC-Lanes\eng-e2\build\E2-GDEMU-fight` (native image n3, boot option NOTRACE; KEEP, SHA256SUMS,
SHA256SUMS.boot, DISC_LINT PASS standard profile): disc.gdi 025516557d49..., track03.bin 7d1567552c8c...,
1ST_READ.BIN 9738b04defbc... The same ELF ran the Flycast rows above from its ISO form (`n3-a`). One boot: the fight (900 ticks), then the report on serial (ROW lines with the services
split, GE gameplay events, FXCALL effect starts, stub counts, memory).

## 8. Not done

- Kill on the engine: the engine's fight diverges at the old run's third hit (section 3), so the kill and the capped
  spawn after it do not happen in 900 ticks. Gameplay equivalence through the kill needs the generator-dependent AI
  path to match, which the split rules out by design; the checker's kill control is shown on the old trace.
- Effects: per-id behaviours (strips, trails, glow filter), nested generators, effect models, room SST effects, the
  blood decals' look check against the PS2; the effect texture map covers the 170 sprite pictures the cross capture saw.
- Not hosted: room ETC objects, Ganado weapons and carts, room controllers 11 / 12, items, sound, event data (movies).
- Original units still linked: actor volumes (atariInfo, at_mod, at_sub), route_ck, cMotBase, parts of model / motion /
  atari (no native service yet); cloth and shape keys stubbed.
- Console numbers: none (MODELLED and Flycast only).
- The farm and the bell fight; El Gigante on this image.
