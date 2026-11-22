# Lane eng-e2f: the fight image to zero, the knock-down seen (step 3, pass E2)

Status: **finished, unaudited** for items 1 to 5; items 6 to 8 wait for other lanes' merges (not started). Branch
`lane/eng-e2f` (from eng-e2d's bb1e9f219; origin/engine cd8b8762b merged, eng-fix1's corrections included). Every number
is the PC reference (hostref) or plain Flycast (slot std1, function checks); none is a timing.

## Link check (check_link.py with the split check), service functions per image

| Image | Start (bb1e9f219) | Now |
|---|---:|---:|
| default | 0 | 0 |
| SENDABLE=1 | 0 | 0 |
| FIGHT=1 | 30 (sce_at 17, em10 10, r101 1, cam_extra 2 split) | 10 (em10's ten, waiting on eng-skel1), split 0 |
| BOSS=1 | 29 | 29 (eng-e2c's; untouched) |

Controls (each FAILs): `SCEAT_ORIG=1` 10 -> 27 (sce_at's 17 back); `R101_VOICE_ORIG=1` 10 -> 11; `CAMX_INLINE=1` 10 -> 12
(2 split problems). Evidence `E:\RE4DC-Lanes\eng-e2f\ev\links`.

## Item 1: the fight image's GX answers (eng-e2d's change), before and after

What changed (eng-e2d, 444f3e70d): GXGetViewportv 640 x 480 -> 512 x 448 (the game's Screen, main_sub.cpp
ScreenReSize(512, 448)); GXGetProjectionv: a 640 / 448-aspect perspective of `pG->Cam.param.fovy` -> the camera
record's own terms (x cot / (4/3), y cot: the original's C_MTXPerspective of pG->Cam.ProjMat at 4/3).

Why the new answers are right: the screen rules test the projected point against 512 x 448 (em10ScreenInCk: 0 < x < 512,
0 < y < 448). With the old answers a point at view slope u = cot*x/z projected to x = 320(1 + 0.7u): "on screen" for u
in (-1.43, 0.86) where the true view is (-1.33, 1.33): the right 18 % of the real screen read as off screen and a strip
past its left edge as on; in y, 240(1 - v) against 448: v in (-0.87, 1) for the true (-1, 1), the bottom 7 % off. The new
answers give exactly the 4:3 frustum the GameCube drew, as the PC native build does (hostref/host_math.cpp), where
e2bcheck's XO rows compare em10ScreenInCk with the original's on three placements (PASS; its screencentre and screenhalf
controls FAIL).

What it moved in the fight scenes: nothing. A counter line (fight_trace.cpp `E2 SCREEN`: GX projections, em10's screen
checks, answers on screen, cut-ins) shows no screen test is made in any fight scene: 0 / 0 / 0 / 0 in FIGHT, FIGHTT,
FIGHTS, SHOT, SHOTNP, SHOTDMG, SHOTLATE. The same disc built with the old answers (local lab ref e2f-gxbefore,
a78924478, never pushed; only fight_stubs.cpp's two GX functions differ) against the new (e367d6235): 0 of 15,349 trace
and counter lines differ across the seven scenes; FIGHTS 23 stills, 0 differing pixels. shot_engine.py on the same
reference (before eng-fix1): 4 scenes as they must. Evidence `ev\item1` (ab.txt, the per-scene line files, shot-*.txt),
runs `runs\A1`, `runs\B1`.

## Item 2: sce_at's 17 service functions, the engine's

`services/scene/sce_at_svc.cpp`: SceAtInit (the room's AEV and ITA data checked and linked into the at-list, the system
record cleared), SceAtHitCheck (a record's hit bit), sceAtGetArea (the area carried by its parent's frame, SH4ZAM),
sceAtGetLadderPos, sceAtHitCheck (the area service's tests, the facing limit, the item's sight), SceAtItemHitCheck (three
sight lines on the effect collision), InScreenCheck, SceAtSetItemModel / sceAtSetItemModelParent / SceAtItemModelPtr /
sceAtCheckItemModelParent (the item model on its spot and its parent link), sceAtItemEffSet / sceAtItemEffDelete (the
item glow's kinds as two tables, started and stopped on the effect entry points), sceAtCheckItemEffectCol (a table), the
shadow area's handler (sceAtFunc_shd_disp). Logged stubs: itemZoom (it read the item's model from the disc inside play;
the engine refuses, the original's load-failure answer) and releaseModel (it undoes only itemZoom's model).

sce_at's statics (the system record SceAtSys, its pointer pS, the static shadow handler) are weak globals through
`services/scene/sce_at_weak.h`, force-included into the hosted unit (eng-e2c's r119 method): no source change; the
engine's SceAtInit points pS at the record. The object keeps every reference by symbol (no section-relative reference
but debug information).

PC check `hostref/svc/e2fcheck.sh` (new builds `make e2fodump e2fnative`, svc/svc.mk; boundary log svc/e2f_dump.cpp:
the room's 68 records and planted inputs from tick 30, every 5th tick; the item tables every 50th). The reference hosts
no scenario layer, so these two builds add sce_at's object (all its globals weak, the reference's stubs keep answering
the rest), the at-list (libgpu's original / at_list.cpp) and are linked above 0x80000000 (the at-list keeps a record's
address with the top bit set, as on the console). Result on the corrected reference (after eng-fix1): bell-ganado,
shot-ganado, bell-ganado-kill PASS (boundary log, outcome, traces; about 172,000 lines each); 14 controls FAIL, one per
function: atparent (sceAtGetArea), atfacing (sceAtHitCheck), screenmid (InScreenCheck), itemsight (SceAtItemHitCheck),
hitbit (SceAtHitCheck), glowkind (sceAtItemEffSet), itemcol (sceAtCheckItemEffectCol), itemlink (SceAtInit), ladderofs
(sceAtGetLadderPos), itemrot (SceAtSetItemModel), shdbit (the shadow handler), glowstop (sceAtItemEffDelete), modelptr
(SceAtItemModelPtr), parentscale (sceAtSetItemModelParent). sceAtCheckItemModelParent's row runs, but r101 has no
parent-giving record (type 0x14), so its walk finds none in both builds: no control can fail it with this room's data.
Evidence `ev\e2f-f` (before the merge), `ev\e2f-merged`.

## Item 3: r101_callGanadoVoice

`fight/r101_voice.cpp` (the engine's presentation loop: one of the square's ten voices, never the same twice, sound bank 6
from the square's centre, 75 to 120 ticks apart, both draws from the presentation generator, as eng-e2c's thunder) takes
the static's place through `fight/r101_weak.h` (force-included); r101 is now a SPLIT_NOIPA unit. Counted:
`E2 R101 voices`. The fight's behaviour stream no longer carries the task's two Rnd draws (the split's known
consequence); the PC reference hosts no room script. Link control R101_VOICE_ORIG=1: 10 -> 11.

## Item 4: cam_extra's two split problems

cam_extra is built without inlining in FIGHT=1 (SPLIT_NOINLINE_UNITS, as dmg), so the binocular widget's in-class
members are functions of their own; the seven that became visible (IdBinocular's and IDApplication's constructors,
IDApplication's destructors, move, quit, operator delete) are the widget's logged stubs in fight/fight_svc_stubs.cpp,
beside eng-e2d's (the constructors set the table pointer as the implicit ones do). Not reached in the fight. Control
CAMX_INLINE=1: the 2 split problems back.

## Item 5: the knock-down

Fixture `tools/plays_right/fixtures/knock-ganado.txt` (list entries 0x15 and 0x16, Leon turned to face them, six shots
from tick 480). PC reference (re4ref plain, after eng-fix1; the same before it): 0x16 takes 300, 300, 200 at ticks 502,
522, 542 and dies at 542 with 0x15 973 units away; the death registers the crash volume (odump e2.txt: `542 DS 3 2 ...
R1500 R800`) and the damage table's point test at 0x15 answers kind 3 the same tick (31 such answers); 0x15 is knocked
over (routine 0x3b, ticks 544 to 610, thrown about 5,000 units).

Engine scenes on the disc's build_console_disc.sh: KNOCK (the FIGHT image playing the fixture) and KNOCKNT (its control:
boot file DMGNOTICK, the damage table's tick not run). Disc from b6d2e3ade (merged head), plain Flycast std1, 5 of 5
scenes OK; judged by `shot_engine.py --fixture knock-ganado.txt --scenes KNOCK:PASS,KNOCKNT:FAIL:any --main KNOCK`
(evidence `ev\knock`):

- **KNOCK FAILS against the reference.** 0x16 dies on the same tick (542) but its second hit takes 360 on the engine
  (500 -> 140) where the reference takes 300 (500 -> 200): a different part of the body is hit (360 = 300 x 1.2); its
  death then takes another routine (engine 2,3; reference 2,4), the crash volume is not registered (E2 DMG: 20 records,
  2,980 tests, **0 hits**), and 0x15 is not knocked over (its routine unchanged through 610). Positions then part (max
  3,888 units, 0x16 at tick 614). The knock-down is therefore **not shown on the engine**.
- KNOCKNT fails too, but only because KNOCK does: with no crash volume on the engine its control cannot show anything
  yet. Its tick is off as designed (E2 DMG ticks 0 against 640).
- The first difference is the hit's part at tick 522: the enemy hit geometry (services/aim/em_hit.cpp, lane eng-e2a's)
  or the shot's line (the weapon aim) against the reference's, not the damage table. Request below; not fixed here (not
  this lane's files).

## Suites (PC, the merged head, ev\suites-2)
svc_controls 79, camcheck, refctl, e2check, e2bcheck, aim_check, controls 18, outcome_controls 35: every row as it must.

## Not done
Items 6 (after eng-e2c), 7 (after eng-skel1's entries), 8 (after eng-load1). The integrator's R2, R5, R7 (after eng-snd1).
