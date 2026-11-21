# Lane eng-e2d: service code hidden by inlining, the PC native projection, the rest of the fight image (step 3, pass E2)

Status: **finished, unaudited** for items 1 and 2 and part of item 3; item 3's sce_at functions and item 4 (the
knock-down on the engine) not done (the brief's stop rule). Branch `lane/eng-e2d`. Every number is the PC reference
(hostref) or Flycast (plain build, a function check); none is a timing.

## Item 1: the split check, every image

`port/dreamcast/tools/engine/split_check.py` (replaces `game/em10_split_check.py`). The link check reads the map, so it
sees a function only as its own code section; a hosted unit can still carry a service function's code where the map
does not show it: inlined into a decision function, as a clone the callers call instead, or (for a function the engine
replaces by making the unit's copy weak) in what a caller of the same unit assumed about the body it saw (clobbered
registers, purity, memory effects, value ranges, propagated constants, argument layout, an identical-code merge).

For every hosted object a map loads, per unit:
1. the compiler's inlining report (`<object>.inl.txt`, `-fopt-info-inline-optimized`) exists, or the object's recorded
   command line (`.GCC.command.line`, `-frecord-gcc-switches`) names it (GCC writes no file when it inlined nothing);
2. no function the link check refuses for that unit (allowed_original.txt: exceptions, unreviewed name guards,
   ceilings, default deny) and no replaced function is inlined into a function the image keeps (unless that caller is
   itself refused or replaced);
3. no clone of one survives where the link check cannot see it;
4. a unit with a replaced function is compiled without the interprocedural optimisations (game/Makefile `SPLIT_NOIPA`,
   read back from the object).

A function is replaced when the object defines it and the map's cross reference names an engine object as its
definer; a COMDAT copy of a header inline the list allows, taken from an engine object that includes the same header,
is reported as an "ODR copy" (same source), not a replacement. `check_link.py` runs the split check on every map it
checks (no option skips it; not on another build's layout, `--orig-pattern`), and each problem counts as a service
function, `SERVICE(split)`. The per-object form (`--obj --unit --weak`) stops the build of em10.o (image and PC
reference, `--host`).

Build hook (game/Makefile): `SPLIT_REPORT` on every object compiled with ORIG_FLAGS (neither option changes code);
`SPLIT_NOIPA_UNITS` (objWep, pl_debug, cam_ctrl, cam_qfps, cam_extra, pl_sub, pl_npc, wep02, em_sub, dmg, em_set, game,
em2b, emtree, emtorch, obj20; fight.mk: em10, sce_com, sce_at); `SPLIT_NOINLINE_UNITS` (dmg: its cDmg::beginEvent had
the header-inline manager destroy inlined, which the engine's table replaces). Control only: `SPLIT_IPA=<unit>...`
(EM10_IPA=1 is SPLIT_IPA=em10/em10). Build flags changed for the boss image's units em2b, emtree, emtorch, obj20 (the
check requires them: each has manager members the engine pool defines under the original's names).

### Results per image (`E:\RE4DC-Lanes\eng-e2d\ev\split-a`, `split-c`, `split-f`)

"Before" is this head built with the old flags (SPLIT_IPA on every unit of the list but em10, which eng-e2b had
already fixed); the problems are split-check problems, the counts link-check service functions.

| Image | Split problems before | after | Link check before (sections) | after |
|---|---:|---:|---:|---:|
| default | 10 | 0 | 0 | 0 |
| SENDABLE=1 | 10 | 0 | 0 | 0 |
| FIGHT=1 | 42 | 2 | 43 | 28 + 2 split = 30 (item 3) |
| BOSS=1 | 18 | 0 | 26 | 29 |

What was found:
- **default and SENDABLE:** objWep's `Draw_line3d_222` (the shooting-range line's drawing) inlined into
  `cObjWep::drawLaserSight` and `cObjWep::satCheck`, both linked: the default image's "0" was not 0 in fact. And eight
  units with replaced functions under IPA (cam_ctrl 13, cam_qfps 6, cam_extra 1, objWep 3, pl_debug 1, pl_npc 2,
  pl_sub 2, wep02 2). Fixed by SPLIT_NOIPA: 0.
- **FIGHT:** besides the above, cam_extra's binocular and focus bodies inlined into the binocular and scope cameras
  (FocusAnimation::init / quit, IdBinocular's destructor: now visible as sections, +3), game's cGameSave::load inlined
  into GameContinue (and calcAddr, calcOffset: +2), sce_at's at-list walkers inlined into five decisions, sce_com's
  manager event walks (cManager<cEm/cObj/cDmg>::beginEvent / endEvent) inlined into SceEventStart / SceEventEnd, dmg's
  manager destroy in cDmg::beginEvent, the empty cEmWrap destructor in three room-script functions, and
  sceAtCheckItemEffectCol (+1, by the name guard). Fixed: SPLIT_NOIPA; the event walks are the engine's
  (`services/scene/scene_event.cpp`); dmg without inlining; `+st*/* cEmWrap::~cEmWrap` reviewed (its body is empty,
  include/em_wrap.h). Left: IdBinocular's in-class constructor and destructor inlined into CameraBinocular's (2 split
  problems; the binocular camera is not reached in the fight; its own stubs are item 3's).
- **BOSS:** five units with replaced manager members under IPA, dmg's destroy. Fixed: 0 split problems; three
  destructors that had been inlined are now visible sections (cEmTorch, cEmTree, cObjObaModel: 26 -> 29). Lane eng-e2c.

Controls (`ev\split-ctl`): `SPLIT_IPA=game/objWep` on the default image: link check FAIL, 3 split problems (the two
inlined Draw_line3d_222 copies and the flags); `FIGHT=1 EM10_IPA=1`: em10.o's build stops, 179 problems.

## Item 2: GetScreenPos on the PC native build

Cause: on the native build the camera service loads no GX projection (`CameraSetProjection` notes the type; the
renderer reads the camera record, `eng_camera.h`), so hostref's `GXGetProjectionv` answered the zeros nobody loaded
and `GXProject` put every point at the viewport's centre (256, 224). The original (`src/game/camera.cpp`
CameraSetProjection) loads `pG->Cam.ProjMat`, a perspective of the camera's field of view at 4/3, whose x and y terms
are the record's p00 and p11.

Fix (a reference-tool fix, not a reference change): `hostref/host_math.cpp` answers the record's projection terms
when the camera record is linked (the native build); the original's build links no record and keeps GXSetProjection's
answers. Proof the original's answers are unchanged (`ev\item2`): odump's e2b-diag XI lines identical before and after
(55 lines), its trace identical but for the fixture path in the header.

Check: e2b_dump writes `XO<v>` lines into the compared boundary log: the check's answer, the front flags and both
projected points, for the Ganado's root where it stands, at the camera's target (the screen's centre) and half way.
Native matches the original within the bounds (exercise e2b bell-ganado 7,210 / 7,210 lines). Controls: screencentre
(`RE4_SCREEN_CENTRE=1`, the zeros back): FAIL (worst 343.7 px); screenhalf FAILs again (before this lane it passed only
because the native projection put every point at x = 256).

The fight image (`fight/fight_stubs.cpp`) answered GX's queries with a 640 x 480 viewport and a 640 / 448 aspect, so its
screen rules (512 x 448) tested other points than the original's: it now answers the record and the 512 x 448 screen,
as the PC native build. (`boss/boss_stubs.cpp` has the same: lane eng-e2c.)

## Item 3 (part): the rest of the fight image

| Function(s) | Was | Now | File |
|---|---|---|---|
| libgpu ClearOTagR, AddPrim, DelPrim; sce_at sceAtSetOtStart, sceAtGetOtAddr | the scene attachments' list (an ordering table used as a container) | native | services/scene/at_list.cpp (libgpu not hosted) |
| cam_extra IdBinocular::init / move / quit, IDApplication::init, IdBinocular's destructors, FocusAnimation::init / move / quit | drawing (ID widget, screen filter) | logged stubs | fight/fight_svc_stubs.cpp |
| game cGameSave::load, save, checkAddr, calcOffset, calcAddr | save storage | logged stubs | fight/fight_svc_stubs.cpp |
| sce_com SceDebugDisp | debug print | the engine's: no text, the cursor advanced (counted) | fight/fight_svc_stubs.cpp |
| sce_com DebugTrg | debug trigger | the engine's 0 (counted) | fight/fight_svc_stubs.cpp |

Stub and call counts, Flycast B1 (plain build, slot std1: emu.cfg has no Dynarec.Enabled / Sh4Clock line, the defaults
dynarec on and 200 MHz; a function check, no timing; disc from e716c7b16, deleted after its run): IdBinocular::*,
IDApplication::init, IdBinocular's destructors, FocusAnimation::*, cGameSave::* (5): **0 calls** in every scene;
SceDebugDisp 1,480 and DebugTrg 862 calls in each FIGHT run (so they are the engine's bodies with the original's
effect, not stubs: the debug print's cursor write was added after this run, the image at the head links). The at-list
is exercised by every fight scene (sce_at walks it each tick). Scenes: FIGHT, FIGHTT, SHOT, SHOTNP, SHOTDMG, SHOTLATE OK;
FIGHTS (the stills scene) timed out because the runner was started without `--stills` (it waits for each still's
acknowledge): a runner error of this lane, not re-run. shot_engine.py: 4 scenes as they must (SHOT's life drop at tick
162, 800 -> 500, as the reference). Counters: E1 POOL full 0 bad_frees 0; E2 DMG 20 records, 6,204 tests, 0 hits.
Evidence `E:\RE4DC-Lanes\eng-e2d\ev\flycast-B1`.

Controls: `ATLIST_ORIG=1` (libgpu hosted, the walkers original): FIGHT 30 -> 35, FAIL; `FIGHT_STUBS_ORIG=1` (the
stubbed bodies original): 30 -> 46, FAIL (`ev\split-ctl`).

Not done: sce_at's 17 other functions (16 by the exceptions: hit and screen tests, area geometry, ladders, item effects
and models, shadow, SceAtInit; and sceAtCheckItemEffectCol by the name guard, visible since the split check); `r101_callGanadoVoice` is a static function (`_ZL`): no link-time
replacement reaches it without a change to src/ (a ruling is needed).

### What the default image needs to host the area check (lane eng-load1's request R1; not done here)

The door request should come from the hosted check, not a planted stub: `SceAtCheck()` then `ActBtn.move()` once a
tick at gameMainLoop's place (`src/game/game.cpp:820-821`, after CamCtrl.Check), `sceAtCheck_main` testing Leon's
front point against each area, `sceAtFunc_door` (`sce_at.cpp:1027-1087`) as decision code setting `Rno0 = 4`.
- **Hosted list** (`game/hosted.mk`, default image): `game/sce_at` (and `game/act_btn` for ActBtn.move, which uses the
  same list container: `ClearOTagR(m_ot, 16)`, so `services/scene/at_list.cpp`'s walk start must then take sce_at's
  table by name, not the last table cleared; its counter "at_list: another table" shows it), with
  `services/scene/*.cpp` built in the default image too (today fight.mk only). sce_at's own 17 service functions must
  be native first (they would otherwise show in the default image's count): the ones the check reaches are
  `sceAtHitCheck` / `SceAtHitCheck` (the area tests: eng-e2a's `services/volumes/area_vol.cpp` has the geometry),
  `SceAtInit` (the room's attachment data and the table), `sceAtGetArea`, `sceAtFunc_shd_disp` (shadow drawing: a
  setter or a stub), the item model and effect functions (`SceAtSetItemModel`, `itemZoom`, `sceAtItemEffSet`, ...:
  reached by item spots, not by a door).
- **Calls in the main loop** (core/, lane eng-load1's area): `SceAtInit` at room entry with the room's AEV data,
  `SceAtCheck(); ActBtn.move();` each tick after the camera's check. sce_at's callees in sce_com / game (the event
  brackets, `sceInLock`) are hosted already in FIGHT; in the default image sce_com is not hosted, so the door path's
  `SceEventStart` reaches would need sce_com too, or the door's event bracket checked against `sceAtFunc_door`'s body.
- **Check:** the DOOR scene's door firing from the hosted check on the ticks the planted stub used (eng-load1's
  `door_check.py`), with the planted stub's control.

Waiting on lane eng-svcspd1 (the skeleton and cloth entries eng-e2b requested):

| Function | Entry it needs |
|---|---|
| em10NeckMove | a bone's added rotation and its flag 0x40000000; a bone's local matrix post-multiplied by a rotation about z |
| em10WaistMove | a bone's added rotation and its flag |
| em10BombNeckMove | a bone's world matrix post-multiplied by a rotation about y; a bone's pose angles; a bone's scale |
| em10MouthPartsReset | a bone's pose angles |
| em10BowgunMove | a bone's scale (the weapon's bones) |
| em10ClawMove | a bone's scale; a bone's pose position |
| em10GatlingRollMove | a bone's pose position |
| em10ChainSet, em10BeltSet, Em1fClothSet | a cloth chain set-up entry (links, parents, limits, collision set) |

## Item 4: not done
