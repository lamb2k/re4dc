# Lane eng-e2g: why a shot hit another part; the knock-down seen; the boss image's split check folded (step 3, pass E2)

Status: **finished, unaudited** for item 1 (the shot's part, the knock-down) and the boss items of item 2; the other
items of item 2 wait for lanes eng-skel1, eng-load1 and eng-snd1 to merge (not started). Branch `lane/eng-e2g` (from
eng-e2f's 67cbe6d91; origin/engine d2a7ee30d merged). Every number is the PC reference (hostref) or plain Flycast (slot
std1, a function check); none is a timing.

## Item 1: the shot that hit another part

Fixture `knock-ganado` (Ganados 0x15 and 0x16, six shots from tick 480). Reference: 0x16 takes 300, 300, 200 and dies
at tick 542; its crash volume knocks 0x15 over (routine 0x3b). Engine before this lane (eng-e2f's K2): 300, **360**,
140; another death routine; no crash volume; 0x15 stays up.

### Cause, by elimination (first differing quantity)

1. **The generator is not it.** The fight scene seeds the fixture's value (`seed 0d37`; the village's unseeded
   generator, `core/partner.cpp`, is another scene's). Engine trace (K2) against the reference, every tick: `rng=` and
   the draw count agree on ticks 0 to 521; Leon's position and angle and both Ganados' positions agree through 522.
   The first difference is at 522, the damaged tick itself (life 200 against 140); the generator then parts (989b/9
   against e54d/10) as a consequence. Evidence `ev\before\rng_cmp_K2_vs_ref.txt`.
2. **The muzzle line and the part positions are not it.** On the PC, the aim check's build (the native services
   throughout) with only the shot list's answer switched reproduces both outcomes: the original's list gives 300, 300,
   200 and the knock-down (its trace equals plain re4ref's, ticks 500 to 529), the native list gives 300, 360, 140, no
   knock-down: exactly the engine's fault, on identical inputs.
3. **The shot list is.** Shot call 3, frame 521, the same line and the same part matrices: the original's list takes
   box #1 (part 2, the body capsule) at 2983.15 units; the native's took box #0 (part 5, the head capsule, width 160,
   height 110, radius 164.2) at 2885.09 units. Evidence `ev\before\orig\aimlist-diff.txt`, `ev\before\boxes.txt`.

Why: the line truly crosses the head capsule (it passes 17 units from its axis); the native test (`services/aim/aim.cpp`
`capsule_entry`) answered by true geometry. The original's `emLineCapsuleCrossCk` (`src/game/em_sub.cpp` 757-869) has its
own rule: both end-sphere crossings (local height 68.2 and 60.2 on an axis of 112.9) lie inside the axis span, so they are
left to the side test (lines 819-832); the side test builds its entry point by stepping back the half-chord along the
segment, not across the axis (lines 845-848), which for this steeply tilted head axis lands at local height -35.8,
outside the span: rejected (line 853). The original misses the head and the shot hits the body.
Step by step: `ev\before\capsule_frame521_box0.txt` (`s\capsule.py`).

### Fix (integrator's ruling: `services/aim/aim.cpp` to this lane)

Which part a shot hits is gameplay, so the shot takes the part the game takes. Lane eng-e2a's enemy hit geometry already
answered the game's rule natively (`em_hit.cpp` `capsule_in`, `cube_in`, proven by e2check); the shot list kept its own
true-geometry copies. Now one rule in one place:
- `services/aim/hit_shape.h`: `sphere_in`, `capsule_in`, `cube_in` moved there from `em_hit.cpp`, unchanged but for two
  points: `cube_in` counts a mirrored frame through an optional argument, and the capsule's near-vertical test takes the
  game's own angle (`acosf` of the unit axis's y against 0.01 and PI - 0.01, single precision) instead of a fixed
  cosine 0.99995 (the property check found an axis generated at 0.0099 rad that the fixed cosine put on the other side:
  1 in about 6,000 near-vertical cases). The rule and why it is not true geometry are written in the header.
- `services/aim/aim.cpp`: `aim_part_entry` (exported for the PC check) answers each hit box by those tests; the
  true-geometry body stays only as control truegeom (`aim_control` 2). `em_hit.cpp` uses the shared tests.
- SH4ZAM types throughout (camsvc's `v3`, `Frame`, `shz_mat3x3_adjugate`); no original code linked.

### Proof

- **Property check** `hostref/svc/aimprop.cpp` (`make aimprop`, a row of `aim_check.sh`): `aim_part_entry` against the
  plain build's own `em_sub.o` (`emLineCapsuleCrossCk`, `emLineCubeCrossCk`, with `sub2.o`'s `LineSphereCrossCk`) on
  generated cases, seeded and repeatable: per seed 40,000 single segments in seven kinds (random; steep: along the
  axis within 20 degrees, the case the head met; grazing an end sphere at 98-102 % of the radius; aimed at the span's
  ends; starting inside; near-vertical axes within 0.02 rad of up or down; mirrored part frames), a quarter of the
  random ones boxes, and 10,000 groups of 2 to 6 boxes (the box each rule chooses). Verdict on each: same hit or miss,
  same box, distance from the segment's start within 1 unit (the shot list's bound). Result: seeds 20261121, 1, 777,
  31337, 4242, 99: **PASS** (240,000 segments, 60,000 groups; worst distance 0.14 unit, a graze). The row runs three
  seeds. **Control truegeom: FAIL**, all 8 rows: 285 of 10,000 groups choose another box, up to 922 units apart.
  First run: 26 failures, all "starts inside" on a box of height 0 (a flat box has no inside; a start on its plane is
  decided by rounding in either form): that kind no longer draws a zero height for a box; zero heights stay in the
  other kinds. Evidence `ev\aimcheck`.
- **aim_check.sh** (PC): knock-ganado joins the default fixtures. Before the fix its shot list FAILED (box 1, frame 521);
  now orig and native PASS (calls, shot lists, outcome, traces), ctl FAILS. The other fixtures as before.
- **Engine (plain Flycast std1, disc K1 from 9144792c7, before the sort change of b7bc02715, which moves only exact
  ties and leaves every aim_check row as it was):** KNOCK **PASS**, identical to the reference (641 ticks, both
  Ganados, position and yaw maxima 0.0000; 0x16 300, 300, 200, dies at 542; 0x15 knocked, routine 0x3b; E2 DMG: 31
  point-test hits, 43 records expired). KNOCKNT (the damage table's tick not run) **FAILS for its own reason** (judge
  reason "knock", new: the same hits, amounts and kills, a body moved otherwise after the kill): every life drop and the
  kill as the reference's, 0x15 knocked as well, but its volume never expires (0 expired; 75 point-test hits against 31)
  and 0x15 is moved again: 21.9 units off at tick 614. The runner also marks KNOCKNT "pool refused: full 50" (the
  never-freed records fill the table's pool), the same cause.
  The four SHOT scenes on the same disc against the corrected reference: SHOT PASS (identical: position and yaw maxima
  0.0000), SHOTNP, SHOTDMG, SHOTLATE FAIL as they must, each for its own reason. FIGHT ran (OK); its hit, kill and
  aim records (GE, E2 EVENTS, E1 AIM, E2 EMHIT, E2 DMG lines) are line for line those of eng-e2f's K2 before the fix, as
  are SHOT's: no shot of theirs changes part. Evidence `ev\knock` (summary.txt, knock_engine.txt, shot_engine.txt), run
  `runs\K1`; disc deleted (cdisc\DELETED.txt).

### Would the other fight checks have caught it?

Yes, the shot-list row of `aim_check.sh` (both answers on every shot, box by box) catches exactly this, but none of its
fixtures had a shot whose line crosses a capsule near the original's refusal (shot-ganado, aimfire-ganado: the same box
and distance on every shot); the outcome checks (SHOT, FIGHT, the bell fixtures) pass for the same reason. Added: the
knock-ganado fixture in aim_check.sh's list and the property row, which tests the rule itself away from any fixture's
luck (its control fails on 8 of 8 rows).

### Does the old port agree?

The old port runs the original `emLineCapsuleCrossCk`, so on this fixture it hits the body as the reference does; the
engine now answers by the same rule, proven equal on the property check, so they agree on the part by construction
(within the 1-unit distance bound; the near-vertical angle by the same acosf).

### Other native geometric tests (listed, not changed: for a sweep)

A survey of every native hit, overlap and crossing test in `services/` (collision, actor volumes, the enemy hit
geometry and attacks, the damage volumes, the areas, the math helpers, the scene attachments, the camera's areas, the
boss, the routes) against the original it replaces found **no other test that answers by true geometry where the
original has its own acceptance rule**: each copies the original's operations or re-derives the same rule (strictness,
first-hit or nearest, thresholds kept). Differences found:
- **Tie order of the blast list:** `services/aim/em_hit.cpp` 567-572 (`GetWepTargetListBomb`) sorts nearest first with a
  stable insertion sort; the original (`src/game/em_sub.cpp` 1659-1670) uses an exchange sort that swaps entry i with any
  later nearer entry j. With exactly equal distances the order differs (e.g. distances A2, B2, C1: original C, B, A;
  native C, A, B); which targets are listed is the same. Not changed (eng-e2a's file).
- The same sort in this lane's shot list (`aim.cpp` `GetWepTargetList2`, original em_sub.cpp 1473-1484): **changed** to
  the original's exchange sort (b7bc02715); aim_check.sh every row as before.
- Rounding-level only (the same rule written another way; can differ only at an exact edge): `services/volumes/dmg_vol.cpp`
  99 (`cDmgCyl::hitCheck`, `p.y - c.y > h` for `p.y > c.y + h`); `services/camera/cam_eval.cpp` 142 and 154
  (`area_hit_p3`, `area_hit_pN`: the same half-planes from another base corner; a ray through a vertex) and 128 / 177
  (squared distances for `PSVECDistance`).
- Unsure: `services/math/math_svc.cpp` 611 `GetScreenPos` projects with `eng_cam.view` (built from eye, target and up,
  camera_svc.cpp 344) where the original uses `pG->Cam.v_mat`; the screen checks are as faithful as those two matrices
  are equal, not proven here.
- Still original code (not native, so not compared): the melee `GetWepTargetList`, `emBoxAtCk`, `emLineAtCk2`,
  `EmAtkLineHitCkSub`. Presentation and culling tests were not surveyed.

## Item 2

- **The boss image's split check, folded** (`tools/engine/split_check.py` rule 5, from eng-e2c's
  `game/r119_split_check.py`, now removed): no section of a hosted unit refers to a replaced function's own code
  section (a function's own sections, such as its jump tables in `.rodata.<symbol>`, may name its code). eng-e2c's rule 3 (a thunder callee called from elsewhere) is the compiler's inlining report in the general
  check. `boss.mk` runs `split_check.py --obj` on r119.o with the three thunder symbols, and st1/r119 is a SPLIT_NOIPA
  unit: on the merged head, before this, the image's split check counted **1** (the replaced thunder in a unit compiled
  with the interprocedural optimisations). Controls on the object (`ev\r119ctl`): without the force-included header, 6
  problems (3 not weak, 3 section references); with the interprocedural optimisations, 1; as built, 0.
- **The boss stubs' GX answers:** `boss/boss_stubs.cpp` GXGetViewportv 512 x 448 (the game's Screen) and
  GXGetProjectionv from the camera record, as eng-e2d did for the fight (was 640 x 480 and a 640 / 448 aspect).
- Not started (dependencies not in `origin/engine`): the ten em10 functions on eng-skel1's entries and the cloth service
  in FIGHT=1; the area check hosted in the default image (eng-load1); R2, R5, R7 (eng-snd1); the Flycast call counts of
  eng-e2f's stubs on a merged image.

## Link check, service functions per image

| Image | Before (merged head e00494a12) | After |
|---|---:|---:|
| default | 0 | 0 |
| SENDABLE=1 | 0 | 0 |
| FIGHT=1 | 10 (em10's ten), split 0 | 10, split 0 |
| BOSS=1 | 1 (split: r119) | 0, split 0 |

Control R119_ORIG=1 (BOSS=1): 3 (the thunder's three back). Evidence `ev\links`.

## Suites (PC: ev\suites-1 on 9144792c7, ev\suites-2 on b7bc02715)

svc_controls 79, camcheck, refctl, e2check, e2bcheck, e2fcheck, aim_check (with the new rows), controls 18,
outcome_controls 35: every row as it must; against eng-e2f's last run (ev\suites-2) no row's result or number moved (only
output paths differ). e2check's enemy hit geometry, now on the shared tests, is line for line the same. suites-2
(the sort and rule 5) the same again.

## Files touched outside the owned list

`services/aim/em_hit.cpp` and `services/aim/hit_shape.h` (eng-e2a's: the shape tests moved into the shared header, no
rule changed but the near-vertical angle; e2check line for line the same); `tools/engine/build_console_disc.sh` (a
comment: the knock control's reason); `services/boss/r119_weak.h` (a comment).
