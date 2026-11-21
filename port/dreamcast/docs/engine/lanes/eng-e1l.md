# Lane eng-e1l: the game's near and far distances, the renderer's planes, the engine's camera against the reference

Branch `lane/eng-e1l` from `engine` a84256c07. Brief: `E:\RE4DC-Lanes\eng-e1l\BRIEF.md`. Status: finished, unaudited.
No timing claims: the Flycast runs are function checks; PC numbers are re4ref (hostref).

## 1. ZNEAR and ZFAR are game state, set where the engine sets up the game

`core/globals.cpp` (`projection_init`, called by `e1_globals_init` at boot, before any room is read) sets ZNEAR 100,
ZFAR 1,000,000 and the ORTHO bounds (240, -240, -320, 320): the values of the original's `systemScreenInit`
(`src/game/main.cpp:663-668`, not linked). The six were zero storage in `host/e1_stubs.cpp`; they are defined there no
more. Readers: the view frustum and its bounding sphere (`camera_svc.cpp` VIEW, at room init and when the fov or the
far plane changes), the shoulder camera's wall probe (side width `ZNEAR tan(fov / 2) 4 / 3` and near offset,
`cam_eval.cpp:606, 609`), the water clamp (`cam_ctrl.cpp:1345`, behind GetWaterHeight, a stub returning 0 in E1).
Every image (default, SENDABLE, FIGHT=1, BOSS=1) runs `e1_globals_init`. The report says
`E1 PROJECTION game ZNEAR 100 ZFAR 1000000; renderer near 100 far 18750`.

Lab arm **ZCLIP0** (boot file): ZNEAR and ZFAR stay zero, as every E1 image had them before this lane. Not a build switch.

## 2. The renderer's planes are its own; the record is finite

The record's depth terms (p22 = -n / (f - n), p23 = -f n / (f - n)) and its far plane (word 25) now come from the
renderer's own constants, `ENG_RENDERER_NEAR` 100 and `ENG_RENDERER_FAR` 18,750 (`services/camera/eng_camera.h`), not
from the game's ZNEAR / ZFAR. The draw distance is unchanged (18,750 before, when ZFAR 0 fell back to it, and now) and
never 1,000,000. The near plane is the original's 100: the game's own projection clipped there.

**What was wrong before.** With ZNEAR = ZFAR = 0 the record's `k = 1 / (ZFAR - ZNEAR)` was infinite and p22 = -0 x
infinity, p23 likewise: not numbers, in every E1 image since E1 began (the first E1 lane's log already printed
`proj ... -2147483648/1000`, `E:\RE4DC-Lanes\eng-e1\runs\e1a-11\serial.txt:67`). The renderer reads its near plane as
`p23 / (p22 - 1)` (`render/native_draw.inc:209`, `native_actor.inc:305`, `native_world.c:93, 288`,
`native_layers.inc:69, 244`, `content_actor.inc:163`, `fight/fight_draw.inc:67`, `services/actor_e1.inc:124`), so every
near-plane comparison there was false: no near clipping of the world or the characters, the world frustum's near plane
never culled, and the world's level choice (`z + near`) never took a coarser level. The E0 bench draws from its packs' own camera streams, not
this record (their depth terms were not decoded here).

**The check.** At the end of every tick (`core/main.cpp`, in the trace span: outside the behaviour and services rows)
`eng_cam_check_tick` tests every word of the record, the renderer's 26 and the evaluated eye, target, roll and fov, for an
infinity or a not-a-number by its exponent bits (the renderer and the game are built `-ffast-math`, where `isfinite`
may fold). The report's line `E1 CAMREC ticks N non-finite N (first tick T word W bits B) near N far N`
(`host/e1_svc_mem.cpp`); the selector (`loader/selector.c`) marks an E1-family scene FAILED when the non-finite count is
not 0 or the line is missing ("camera record not finite: ..." / "no E1 CAMREC line in the report"). It runs in every
image (there is no separate debug build of the E1 images; the cost is 34 integer tests a tick in the trace span).

Lab arm **RNEARFAR** (boot file, the check's control): the renderer's far plane is set to its near, so the depth terms
divide by zero.

Control, Flycast disc l2 (`E:\RE4DC-Lanes\eng-e1l\runs\l2\serial.txt`): SHOT with RNEARFAR reports
`E1 CAMREC ticks 320 non-finite 320 (first tick 1 word 17 bits ff800000)` (word 17 is p22, minus infinity) and the selector
marks it **FAILED** "camera record not finite: 320 of 320 ticks (first tick 1)"; LEON, HILL and FIGHT on the same disc
OK with `non-finite 0`. Disc l1 (the head): 4 of 4 scenes OK, `non-finite 0` in each.

## 3. The engine's camera against the PC reference

**The log.** Trace runs only (no NOTRACE file): each tick the image prints the record as `CAMLOG t=<tick> e=<eye>
g=<target> r=<roll> f=<fov> d=<area>,<cut>,<routine>,<blend frames left>` (bit patterns; `core/frame.cpp`,
`camera_svc.cpp eng_cam_trace_line`). `hostref/svc/camengine.py` turns one scene's lines into a `cam.txt` in
`svc4_dump.cpp`'s form over the reference's ticks (the engine's tick t is the reference's tick t; a missing or repeated
tick, or a value not finite, stops it). `hostref/svc/camengine.sh <out> <after serial> [<before serial>]` runs re4ref
odump (the original camera units) on each scene's fixture and compares with `camcheck.py`:
LEON with `e1-route` at seed 0 (the image's route starts the generator at 0, as lane eng-e1g's comparison), HILL with
`hill-follow` (the image's hill scene: the same resume and 728 ticks; `hill-ashley` is another play, Leon 2.8 units
apart at tick 0 and 5,642 by tick 586), SHOT with `shot-ganado` (the FIGHT image plays that file).

**The bound, stated before the runs:** camcheck's, eye and target within max(0.01 unit, 2^-20 x the reference's
coordinate), roll and fov within 0.01 degree, the controller's decisions equal.

**Before and after.** "Before" is the lab arm ZCLIP0 on this lane's image; its camera is the base image's
(origin/engine a84256c07, disc b1) bit for bit on every tick of LEON, HILL, FIGHT and SHOT (the trace's camera hashes,
`s/camhash.py`). Flycast discs l1 (after) and l2 (before); evidence `E:\RE4DC-Lanes\eng-e1l\ev\cam-a4\`.

| Scene (fixture) | Before: ticks over the bound, worst eye / target | After: ticks over the bound, worst eye / target | Ticks the fix changed | There, worst distance before / after |
|---|---|---|---|---|
| LEON (e1-route, seed 0) | 425 of 640; 175 / 42.5 units | 362 of 640; 82.8 / 42.5 units | 143 (222..391) | 175 / 82.8; over 10 units on 54 ticks before, 5 after; over 50 on 38 before, 3 after (387..390, the same in both arms) |
| HILL (hill-follow) | 682 of 728; 110 / 5.96 | 636 of 728; 5.96 / 5.96 | 139 (1..139) | 110 / 1.92; over 10 units on 91 ticks before, 0 after |
| SHOT (shot-ganado) | 195 of 320; 116 / 42.5 | 195 of 320; 116 / 42.5 | 0 | - |

So neither arm meets camcheck's bound on any scene. **Where the fix changes the camera it moves it onto the
reference:** at the village houses (sampled ticks 222 to 250 and 326 to 340: before 15 to 175 units off, after at most
0.154; `ev\cam-a3\leon-window.txt`) and on the hill from its first tick (before 109.6 units off, after 0.002). On HILL after is at least as near on all 139 changed
ticks (`camnearer.py` PASS); on LEON on 111 of 143: the other 32 (ticks 355..391) are farther by at most 0.004 units
(the row is FAIL by its stated rule, all ticks; not loosened).

**What is left, and is not this lane's.** Every scene drifts off the reference while the camera moves and comes back to
it at rest, identically before and after (LEON tick 2: eye and target both 0.0107 apart, tick 40: 3.67, tick 100: 0;
eye and target displaced by the same vector, so the camera's base point, not its aim, differs; decisions equal
throughout). The largest such ticks are aim starts (LEON 387: 82.8, the shoulder camera's transition, fov 45.22 against
45.28; SHOT 150: 116). On the PC the camera service against the original units passes the same bound on camcheck.sh's
fixtures (e1-route, hill-ashley, bell-ganado, square-follow, door103-walk; unchanged, `ev\chk-h1`), so the difference is
most likely in the image (the SH-4 build of the service or its inputs, such
as Leon's matrix from the native skeleton, which `plays_right` does not compare); not diagnosed here. Proposal for the
backlog: a lane that logs the shoulder camera's inputs (the player location matrix, the floor normal, the offsets) in
the image and on the PC and finds the first one apart.

**PC rows (made first, `ev\pc1`):** re4ref with ZNEAR / ZFAR zero (`RE4_SVC_CONTROL=zclip0`, `svc4_dump.cpp`) against the
reference as it is: e1-route, shot-ganado, bell-ganado, square-follow, door103-walk identical bit for bit; hill-ashley and
hill-follow FAIL from tick 1 (eye 17.2 units, target equal: the shoulder camera's side probes, 62 units wide at fov 50,
meet the hill). On the image the zero distances matter more: its zero arm changed the camera at the village
houses (LEON, ticks 222..391) where the reference's zero arm did not (either the native probe treats a zero width
differently from the original, or the image's drifted camera is nearer the wall there; not separated), and on the hill
its first-tick eye is 110 units off where the reference's zero arm is 17.

**Final link check at the head** (`E:\RE4DC-Lanes\eng-e1l\logs\f-*.list.txt`; `origin/engine` a84256c07 is in the
branch, nothing to merge): default PASS, 0 service of 384; SENDABLE=1 PASS, 0 of 384; FIGHT=1 FAIL, 114 service
(42,156 B) of 910; BOSS=1 FAIL, 57 (17,192 B) of 530: the step-3 lists as on `engine`, unchanged. All four link.

**camengine.sh rows** (`ev\cam-a4\camengine.md`): PC e1-route PASS, hill-follow FAIL, shot PASS (each as it must); after
LEON, HILL, SHOT FAIL (must PASS: not met, above); before HILL FAIL (the control, as it must), before LEON and SHOT FAIL
(must PASS: not met, the same drift); nearer HILL PASS, nearer LEON FAIL (must PASS: not met by 0.004 units on 32
ticks); controls with the arms swapped FAIL on both (as they must). Exit 1.

## 4. Picture

Flycast std1, the j1 ticks (stills 1, 40, 80, ... of each scene), eng-e1i's packs, eng-e1j's threshold stated before the
run (a pair is the same picture when at most 0.5% of its pixels differ by more than 32 and the mean absolute difference
is at most 1.0; `s/picdiff.py`). Discs: b1 (origin/engine a84256c07), l1 (this lane), l2 (this lane with ZCLIP0 in LEON,
HILL, FIGHT; RNEARFAR on SHOT), each traced with stills (function runs). Evidence `E:\RE4DC-Lanes\eng-e1l\ev\stills\`,
pairs and sheets `ev\cam\`.

| Pair | Pairs | Moved |
|---|---|---|
| b1 against eng-e1j's j1 (the base has not moved since j1) | 59 | 0 |
| l1 against j1 | 59 | 49 |
| l2 against b1: the renderer's near plane only (the camera is the base's bit for bit) | 59 | 48 |
| l1 against l2: the camera only (the same renderer) | 59 | 4: LEON 240, HILL 1, 40, 80 |

**The camera moved four stills,** each where the camera now meets a wall as the reference does: LEON 240 (the stone
house; before 94 units off the reference, after 0.15), HILL 1, 40, 80 (the hill; before 110, 109, 104 units off,
after 0.002, 0.05, 0.000). Sheet: `ev\cam\sheet-camera.jpg` (1400 x 2284).

**The renderer's near plane moved 48,** which the brief did not expect: with a near plane that was not a number the
renderer drew triangles through the camera plane unclipped and dropped others. Before: HILL 1 a pink slab and a log
across the view, FIGHT 520 a wall smeared over the whole picture, LEON 1 Leon's handgun and the hanging body's head
missing, LEON 120 the body's hand and feet missing; after, they are drawn as the pack has them. Far world pieces now
take the level their distance picks (HILL 400: braces), as the E0 bench does. Sheet (six of the 48):
`ev\cam\sheet-renderer.jpg`; every pair `ev\cam\pairs\renderer-*.png` (before | after | difference x 4). This is a look
change for the integrator to show the owner; no stills of the old game on Flycast at these ticks were at hand.

## 5. Checks and their controls

| Check | Control | How it failed |
|---|---|---|
| E1 CAMREC, selector (Flycast) | RNEARFAR on SHOT, disc l2 | FAILED "camera record not finite: 320 of 320 ticks (first tick 1)", word 17 bits ff800000 |
| camengine.sh before / after (Flycast against PC) | ZCLIP0 on HILL, disc l2 | FAIL from tick 1, eye 109.6 units (after: first over the bound at tick 2, 0.022 units, the drift of section 3, so under the bound this control does not separate the arms; camnearer.py does) |
| camnearer.py | arms swapped, LEON and HILL | FAIL: tick 222 (68.5 against 0.0015), tick 1 (110 against 0.0019) |
| PC zclip0 rows | (the rows are the PC's own control of where the distances reach) | hill-follow FAIL tick 1 eye 17.19 |
| picdiff.py (eng-e1j's) | l2 against b1 | 48 of 59 MOVED, exit 1 |

Existing PC checks on the head (`ev\chk-h1`): `camcheck.sh` every row as it must, `controls.sh` 18 rows,
`outcome_controls.py` 35 rows, `aim_check.sh` exit 0 with its ctl rows failing, `svc_controls.sh` 78 rows; every row as
it must.

## 6. Lab arms (boot files; none is a default) and files touched

ZCLIP0 (the game's distances zero), RNEARFAR (the renderer's far plane equal to its near). re4ref:
`RE4_SVC_CONTROL=zclip0`. Shared files: `core/globals.cpp`, `core/main.cpp`, `core/frame.cpp`, `host/e1_stubs.cpp`,
`host/e1_svc_mem.cpp`, `loader/selector.c`, `services/camera/camera_svc.cpp`, `services/camera/eng_camera.h`,
`hostref/svc/svc4_dump.cpp`; new `hostref/svc/camengine.py`, `camengine.sh`, `camnearer.py`. The ORTHO bounds moved with
ZNEAR / ZFAR (set to the original's values; no linked reader). Nothing in `src/`, `include/`, `tools/plays_right/`,
`allowed_original.txt`. No stub added; no original unit newly linked.

## 7. Not done

- The engine's camera does not meet camcheck's bound against the reference on any scene, before or after (section 3):
  a drift common to both arms, not diagnosed (backlog proposal above).
- The renderer's look change (48 stills) needs the owner's look check; no old-game stills at these ticks.
- No console run; no timing claims.
