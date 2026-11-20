# eng-boss hand-back (milestone E2: the first Disc 1 boss on the engine), 2026-11-19

Lane `eng-boss` on `lane/eng-boss` from `origin/engine` 3ab6f8f57. Tiers on every number: **MODELLED** (nominal 200 MHz
SH-4 hwsim over Flycast hwtrace, as eng-e0 / eng-e0b), **Flycast** (guest timer, standard harness slots). No console
number exists. Evidence: `E:\RE4DC-Lanes\eng-boss` (runs, build, evidence, s).

## 1. The boss and why

**El Gigante in the village square (r119, em2b type 0).** The largest skinned body on Disc 1 (PS2 cast: 64 bones, 276
weight sets, 2,192 positions, 4,244 triangles), a short arena, and a fight Leon plays on foot: the E1 shell's hosted
player and handgun serve it unchanged, so the hosting step tests the boss's AI, not a new player mode. The lake fight
was not taken: its preset needs a start-point fix, and hosting it needs the boat player mode, the harpoon module and the
boat object as well as the boss. Its effect load (912 live) is the heavier services case and stays the next candidate.

## 2. Capture (logic outputs only, as eng-e0b)

- **Start point:** `s/fixtures/boss-fight-2.txt`: r119 entrance with no room flag, so the room script's own area-2
  trigger runs the appearance (`r119_EventGolemAppear`), the PS2 movie skipped by START in the movie pad script; god,
  source clock, 88 pad actions (aim and fire, strafe, back off). Two runs of the release-recipe reference on std1 /
  std2: every LT / LU line identical through tick 2,120.
- **Image:** release recipe + `M1_FRAME_CAPTURE=3` + `LOGIC_TRACE=1` (with per-enemy LE lines) + `DBG_WARP=1`
  (`s/capbuild.sh`). The r3 capture now accepts r119, takes a host-written first tick and buffer size (r119's heap 4
  cannot spare 384 KiB at the fight), and records the arena's non-Ganado enemy-table models as role 3.
- **Result:** 300 pictures, ticks 600-899 (hut C was destroyed at tick 554, so the scroll-object state is constant
  over the window). The capture run's logic trace equals the same image run without capturing on every LT / LU / LE /
  LL line (ticks 0-973); against the release-recipe reference only the render-side matrix digests (pm, em) differ.
- **Bake** (`bake/boss_pack.py`): the boss from the room's PS2 cast package (`bake/boss_model.py`: RE4NMR1 reader,
  position shift 2 folded into the inverse binds), Leon in the chapter-2 costume (`bake/leon_costume.py`: the PS2 pl08
  package's roles 0, 1, 8), haze and mist sprites cut by the release recipe's own rule (HAZE_SPRITE_CUT: 0x15, 0x48),
  scroll objects the room script hides in the window baked out of the world (destroyed hut C, the unbroken / broken
  roof alternates, 0x2C). Renderer: 384 weight sets per model (was 256), loader check to match.
- **Not drawn by the bench:** the three trees (GC texture with no static identity: refused), torches, the hut debris
  objects, the handgun model, the gate angles the room script sets.

## 3. Bench rows (step 0, full body; 25 timed pictures = 11..287 step 12 + Flycast worst 34)

| Tier | Pictures | Mean ms | p99 ms | Worst ms (picture) | Over 14 ms | Over 33.3 ms |
|---|---:|---:|---:|---:|---:|---:|
| MODELLED | 25 | 19.98 | 25.41 | 25.41 (47) | 20 | 0 |
| Flycast (VIS on) | 600 | 15.53 | 20.55 | 22.00 (35, lap 2) | 382 | 0 |
| Flycast (no VIS) | 600 | 15.53 | 20.54 | 22.18 (68, lap 2) | 383 | 0 |

MODELLED phases (24 pictures): setup + world 5.19, characters 9.91, punch-through 0.37, translucent world + hair 3.29,
effects 0.66, HUD 0.37. Pictures with El Gigante close: 21-25 ms; without him in view: 13-15 ms. Flycast: no presented
interval over 2 fields; the 5 ms delay control reads +5.02 ms. VIS changes nothing measurable in this open arena (full
vs culled stills: 1 picture, 1 pixel, peak 16). Light-pick test: 58 of 986 model-pictures differ (cross: 0.13%).

**Look** (source capture vs bench, Flycast stills, 25 timed pictures): MAE 13.85, 34.1% of pixels over 16 (cross:
8.60 / 21.0%). Main differences: the hut-break dust and smoke sheets (ids 0x00, 0x10) the bench draws all of while the
source declines most; trees, torches, debris and the handgun missing; Leon's lighting. Pairs:
`evidence\look\step0\NNN.png`.

## 4. Boss content steps (boss body-level rule: priced first; over budget, so levels built)

| Step | Body | Weight sets / positions | MODELLED mean / worst | Flycast mean / p99 / worst / over 14 | MAE vs step 0 (% > 16) | Sheet |
|---|---|---|---:|---:|---:|---|
| 0 | full | 276 / 2,192 | 19.98 / 25.41 | 15.53 / 20.55 / 22.00 / 382 | - | - |
| 1 | g50 (PS2 cast level the owner approved for the old path, Test 18) | 188 / 1,093 | 18.36 / 22.49 | 14.34 / 18.38 / 20.46 / 372 | 0.52 (1.4%) | `evidence\steps\step1-g50.png` |
| 2 | g50 + rigid skin (weights >= 0.75 to one bone, the rest to 1/4) | 130 / 1,093 | 18.14 / 22.25 | 14.17 / 18.07 / 20.16 / 372 | 0.53 (1.5%) | `evidence\steps\step2-g50-rigid.png` |
| x | full + rigid skin | 172 / 2,192 | 19.52 / 24.68 | 15.19 / 20.00 / 22.15 / 378 | 0.09 (0.2%) | `evidence\steps\stepX-full-rigid.png` |

Recommended: **step 1 (g50)**. It saves 1.6 ms mean and 2.9 ms worst MODELLED for a change the sheet barely shows.
Rigid skinning buys 0.2 ms more: not worth a look call. No g33: after g50 the boss is about 4 ms of the picture; what
keeps the fight over 14 ms is the world (5.2), the translucent world and hair (3.3) and Leon (about 3.5).

## 5. Hosting on the E1 shell (`make BOSS=1`)

**Closure** (`s/closure_boss.py`, eng-shell-map's lab33 call graph plus the overlay objects' symbol tables): seeds
em2b + r119 70,236 B code; variant B (E1 player already hosted, other behaviour stubbed) pulls 7 files / 36,266 B
(em_sub 21,554, emtree 5,396, em_set 4,888, emtorch 3,472, em_dm_val 492, rnd, dmg); 50 stub names; control (no r119)
4 files / 22,082 B. The image hosts `em2b`, `st1/r119`, `em_sub`, `em_set`, `dmg`, `em_dm_val`, `emtree`, `emtorch`,
`obj20` (oba collision), `route_ck` (route service, first form) and `game` (difficulty points).

**Engine side** (`engine/boss/`): room set-up (the reference's enemy list, the boss archive, `R119Init`), cEmMgr
construct / move in the original order, scenario tasks (KOS threads resumed once a tick by strict hand-off), the area-2
trigger fired at placement, an effect service (first form: requests recorded and counted, not simulated), scroll
objects as an engine visibility table (`SmdSetTrans` = the world-piece hide setter), the room save record, a handgun
magazine, GX projection queries, logged stubs. `bake/em_archive.py` puts the boss archive's 89 motion clips back in
place (the old port streams them from `dc/mot`; the engine reads no disc in play). Headless: the hosted image does not
draw yet (the drawing row is the bench's).

**Plays right** against the same capture/trace image's run of the same fixture (engine tick k = reference tick 184 + k,
900 ticks, Flycast; `s/boss_pr.py`). Compared: discrete events and positions, not the generator state.

| Check | Result |
|---|---|
| Boss routine (attack) sequence, kind and tick exact | 8 of 10 changes: 0 idle, 109 turn, 166 attack 0x0D, 317 attack 0x0E, 483 turn, 513 attack 0x0C, 764 turn, 794 attack 0x09; first difference at 868 |
| Boss Mot_frame, Mot_state, be_flag, hp exact | ticks 0-867 (hp 1000 throughout on both sides) |
| Boss position within 1 unit | ticks 0-484 (bit-identical to 110); worst 1,162 units by 900 |
| Hut C destroyed (room flag, scroll ids 3/8/9/0x2A/0x2B hidden) | tick 371 = reference 555, both |
| Leon routine word / Mot_state exact | ticks 0-377 / 0-420 |
| Leon position within 1 unit | ticks 0-129 (aim sway: the shared generator, as in E1) |
| Determinism | two engine runs: 4,978 trace lines identical |
| Control: every pad action one frame late | FAILS: Leon routine at tick 17, boss position at 376, 7 of 10 routine changes |

First divergences: Leon's angle moves 0.1 degree at the aim (generator draws differ: the hosted room draws less than
the reference room), Leon's knock-down sequence ends 1-3 ticks apart at tick 376, and the boss's choice at 868 follows
Leon's position. A difficulty-rank control occurred on the way: without game.cpp's points (Game_level 0 instead of 5)
the boss's walk speed differed and its frame diverged at tick 111.

**Budget rows of the hosted fight** (Flycast, headless, 900 ticks, NOTRACE; `s/budget.py`):

| Row | Mean | p99 | Worst (tick) | Over row budget |
|---|---:|---:|---:|---:|
| Behaviour (hosted, outside service entry points) | 1.41 | 4.73 | 15.44 (371, hut break) | 77 over 2 |
| Services (skeleton, collision entry points) | 5.06 | 8.16 | 9.87 (117) | 2 over 9 |
| Publication | 0 | 0 | 0 | 0 |
| Drawing | not drawn (bench: 15.53 / 20.55 / 22.00 Flycast) | | | |
| System | 0.03 | 0.03 | 1.92 | 0 |
| Busy tick (no drawing) | 6.49 | 11.33 | 20.71 (34) | 0 over 33.3 |

Behaviour arena high water 464,576 B (heap 4, 17 allocations, 0 failures). Stubs hit (900 ticks): ChkWindow 198,
SndCall 178, EspEstSetSelect 51, SetObj10 24, GetWaterCrossPos 24, cActionButton::set 23 (the dash-escape prompt),
EspSetEatEffect 12, QuakeExec 12, the event and chain calls once each. Effect requests: EstSet 60, EspDataLoad 3.

## 6. Staged discs (KEEP, SHA256SUMS beside them)

- `E:\RE4DC-Lanes\eng-boss\build\BOSS-BENCH-GDEMU`: the bench image with the El Gigante pack and VIS; schedule
  `c0 cn c0 c0dh` (default, no visibility, default, controls).
- `E:\RE4DC-Lanes\eng-boss\build\BOSS-HOSTED-GDEMU`: the E2 boss image (headless), report on serial.

## 7. Not done

- The hosted fight is not drawn (headless image); drawing it means the live boss through the actor pass (catalogue
  model 6) and a slimmer pack without recorded streams.
- Effects are recorded, not simulated or drawn; their generator draws are absent (the main plays-right limit).
- The parasite, dog and death events (outside the window), the movies, sound, the action-button QTE, item drops.
- Trees, torches, debris objects and the handgun in the bench; the effect selection the source applies (dust sheets).
- MODELLED rows of the hosted image; console numbers.
