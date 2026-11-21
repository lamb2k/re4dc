# Lane eng-e1m: the engine's camera against the PC reference

Branch `lane/eng-e1m` from `engine` a62198717. Brief: `E:\RE4DC-Lanes\eng-e1m\BRIEF.md`. Status: finished, unaudited.
No timing claims: the Flycast runs are function checks; PC numbers are re4ref (hostref). SERVICES.md 48c.

## 1. Diagnosis

**What the data said first.** Lane eng-e1l's Flycast run against re4ref (`s/lag.py`, before any change): Leon's position
equal on every tick, but the engine's camera is not one tick of Leon's travel behind. While Leon runs (LEON tick 80,
58 units a tick) eye and target agree to 0.004; they part while Leon stands in the idle motion, which creeps him 0.04
to 0.19 units a tick (tick 2: 0.012 units, tick 11: 0.64, tick 40: 5.1), and come back when he moves off. So the
integrator's reading (a tick of travel: tick order or phase) did not hold on its face.

**The log.** Diagnosis lines `CD n=<CameraMove count> <tag> <words>` (`services/camera/eng_camera.h eng_cam_diag`),
written by the same service code on the image (CAMDIAG boot file, trace runs: into the trace) and on the PC native
build (`RE4_CAMDIAG`: `camdiag.txt`, `hostref/svc/svc4_dump.cpp`). At the start of CameraMove: `pl` Leon's position,
previous position and matrix; `qm` the shoulder camera's stored player matrix (`m_pl_mat`) and floor normal; `qs` its
state (search count, site, blend, angles, floor ratio, aim point), the smoothing's flag, ratio and state, the routine;
`gf` Status_flg, Debug_flg, Stop_flg, Leon's stat. Then each evaluation step's output: `bm` the base frame, `of` the
offset, `hc` the wall probe's camera, `si` the smoothing's target, `cm` the frame's camera. `s/cdcmp.py` aligns the two
on the CameraMove count (offset from Leon's position words) and names the first CameraMove and quantity apart.

**First apart** (Flycast disc c1, commit 711679497, against PC native `ev\d3`): on all three scenes the same,
CameraMove 3 = **tick 2**, tag `qm` word 11: **the shoulder camera's stored player matrix**, z translation. LEON:
engine 1999.926 (Leon at tick 1) against PC 1999.873 (Leon at tick 2), 0.0537 units; HILL 0.119; SHOT 0.0394. Leon's
own position and matrix (`pl`) are equal on both. On the image the stored matrix stays at tick 1's through the idle
(LEON: tick 1's matrix until tick 48, when he starts to walk) and follows Leon again once he runs; on the PC it takes his matrix every
tick. Everything after (base frame, smoothing target, the frame's camera) follows from it.

**Why.** The stored matrix is set by `cPlayer::move` (`src/game/player.cpp:358-423`) only when Leon moved:
`moved = 0` when his integer position is unchanged and `(stat & STAT_BE(0xFFFFFF00)) == STAT_BE(0x100)` (routine
0/0/1: standing). `stat` is the routine bytes r_no_0..3 as one word; the sources write the constants as GameCube
big-endian words and `STAT_BE()` byte-swaps them for the little-endian Dreamcast. The image always swaps
(`engine/host/e1_prelude.h`, as the old game's release recipe, STAT_ROUTINE_BYTES=1). The PC reference compiled the
same sources with `re4dc_prelude.h`, which swaps only under `RE4DC_STAT_ROUTINE_BYTES`, and hostref never defined it:
`gf` shows Leon's stat 0x01010000 (routine 0/0/1/1) on both, Debug_flg[0] 0 and Status_flg[0] 0x02000100 (no 0x20), so
on the PC the test read standing as not standing, `moved` was 1 every tick, and the shoulder camera was handed his
matrix every tick. **The reference was wrong, not the engine**: the image's camera holds still through the idle creep,
as the game does.

**The two tick orders** (no difference in order or log point):

| Step | Engine image (`core/main.cpp`) | PC reference (`hostref/replay.cpp`) |
|---|---|---|
| input | `e1_input_latch`, partner tick begin, `PadRead`, `Frame_cnt++` | exercise hook, fixture spawns / controls / hits, `PadRead`, `Frame_cnt++` |
| before the player | quake offset cleared, slow-motion rule; HILL: the partner's `EmMgr.move` | `UpdateNearClipDist` (ZNEAR 100), `EmMgr.move` (partner, enemies), post spawns |
| behaviour | `pPL->move()` (calls `setPlayerLocation` when he moved) | `pPL->move()` (the same, with the routine bytes unswapped before this lane) |
| objects | `ObjMgr.move` | `ObjMgr.move` |
| camera | `CameraMove`: controller decides, smoothing, record (`eng_cam`), frustum | `CameraMove` (wrapped) |
| camera log | `CAMLOG` from the record in the trace span after the tick | the `cam.txt` line right after `CameraMove` returns |
| after | FIGHT / BOSS: effects, DmgMgr; publish palette, HUD; finite check; draw from the record; pacer | `DmgMgr.move`; trace line |

The camera is evaluated after Leon's move in the same tick on both and logged after `CameraMove` on both; the picture
frames the tick's own Leon. Nothing in the tick order, the pacer, the field counter or the timing rows changed.

## 2. Fix

`engine/hostref/Makefile`: `STAT_BYTES ?= 1` puts `-DRE4DC_STAT_ROUTINE_BYTES=1` in the game include flags, so the
reference's routine tests read the bytes the image reads. `STAT_BYTES=0` builds the old reference in its own BUILD
folder (the check's control). The engine image is unchanged except the diagnosis lines (nothing without a sink: a
pointer test in CameraMove and in four evaluation steps) and the CAMEVERY lab arm (off unless its boot file exists).

## 3. Check: the engine's camera against the reference

`hostref/svc/camengine.sh` (lane eng-e1l), camcheck's bound stated before the runs: eye and target within max(0.01 unit,
2^-20 of the coordinate), roll and fov within 0.01 degree, decisions equal.

Flycast disc f1 (commit e251ae0ac; LEON, HILL, FIGHT, SHOT traced, stills), evidence
`E:\RE4DC-Lanes\eng-e1m\ev\cam-final\camengine.md`. "Before" is the same image against the old reference
(`STAT_BYTES=0`), which is what lane eng-e1l measured; the PC alone shows the same gap (old reference against the
fixed one, no engine involved).

| Scene (fixture) | Before (old reference): ticks over, worst eye / target | After (fixed reference): worst eye / target, share of the bound | PC alone: old reference against the fixed one |
|---|---|---|---|
| LEON (e1-route, seed 0) | 362 of 640; 82.8 / 42.5 units, first tick 2 (0.0107) | **PASS**, 640 ticks: 0.00097 / 0 (10%) | FAIL 82.8 / 42.5, first tick 2 |
| HILL (hill-follow) | 636 of 728; 5.96 / 5.96, first tick 2 (0.0224) | **PASS**, 728 ticks: 0.0039 / 0 (19%) | FAIL 5.96 / 5.96, first tick 2 |
| SHOT (shot-ganado) | 195 of 320; 116 / 42.5, first tick 3 (0.0248) | **PASS**, 320 ticks: 0 / 0 (0%) | FAIL 116 / 42.5, first tick 3 |

Decisions (area, cut, routine, blend frames) equal on every tick; roll and fov within 0.01 degree. The engine's camera
is the same before and after (its CAMLOG lines did not change): every number of the "before" column was the reference.
No SH-4 arithmetic residue needs a bound: the largest remaining difference is 0.0039 units (19% of camcheck's bound,
HILL tick 10, a hill coordinate near 21,000 where one float step is 0.002).

At the still ticks (the engine against each reference, eye / target, units; `ev\stills\` table from `s/stilltab.py`):
LEON 40: fixed 0.000004 / 0.000005, old 3.67 / 3.67; LEON 640: fixed 0.000006 / 0.00005, old 6.6 / 6.6; HILL 360: fixed
0.00005 / 0.00004, old 5.8 / 5.8; SHOT 40: fixed 0.000003 / 0.000002, old 3.66 / 3.66; SHOT 150 (aim start, not a
still tick): fixed 0.000004, old 115.8 / 42.5.

## 4. Picture

Flycast std1, the j1 ticks (stills 1, 40, 80, ... of each scene, and SHOT's), eng-e1i's packs, eng-e1j's threshold
stated before the run (a pair is the same picture when at most 0.5% of its pixels differ by more than 32 and the mean
absolute difference is at most 1.0; `s/picdiff.py`). f1 against lane eng-e1l's l1: **68 pairs, 0 moved**, every pair
0.000% (`ev\stills\f1-vs-l1.md`). The image's camera did not move, so no still moved: the picture already framed Leon
as the game does (the camera holds through the idle creep). Sheet `ev\cam\sheet-unchanged.jpg` (1400 x 1725): LEON 640,
HILL 360, SHOT 40, where the old reference had put the camera 6.6, 5.8 and 3.7 units elsewhere. No Flycast stills of
the old game exist at these ticks; none was made (old-port work).

## 5. Checks and their controls

| Check | Control | How it failed |
|---|---|---|
| camengine.sh after rows (engine against the reference) | the old reference (`STAT_BYTES=0`, build/hostref-gc) | FAIL on LEON (82.8 / 42.5, first tick 2), HILL (5.96, tick 2), SHOT (116 / 42.5, tick 3) |
| the same | lab arm CAMEVERY on SHOT (disc f2: the image hands the shoulder camera Leon's matrix every tick) | FAIL from tick 3 (0.0248, the old reference's first value), worst 5.09 units; against the old reference it is equal until tick 150 (the aim start, 120.6): the creep is the `setPlayerLocation` test, the aim start another routine-byte test |
| the same | ZCLIP0 (eng-e1l's l2 run, the same camera code) | HILL FAIL from tick 1 (109.6); LEON FAIL from tick 222 (68.5) |
| camnearer.py (after nearer than ZCLIP0) | arms swapped | FAIL: tick 222 LEON (0 against 68.5), tick 1 HILL |
| diagnosis lines (cdcmp.py) | (the control is the finding: they name tick 2, `m_pl_mat`) | - |

**ZCLIP0 on LEON** (a finding, not this lane's fix): with the game's distances zero the image's camera leaves the PC's
native build at the village houses from tick 222, where with them set (the default) the two agree. The diagnosis lines
(disc f2 against PC native zclip0, `ev\z0\cdcmp-z0-LEON.txt`): the base frame and the offset equal, the wall probe's
camera apart (player space z -1006 on the image, -642 on the PC): with zero width the three wall probes are one line,
and the collision query answers it differently on the two. Only the lab arm reaches it. camengine.sh's ZCLIP0 LEON row
is now "must FAIL" (it was "must PASS" on the assumption that the image matched elsewhere).

Existing PC checks on the fixed reference (`ev\chk-h1`): `camcheck.sh` every row as it must (native against the
original: e1-route eye 0.00097, hill-ashley 0.0078); `controls.sh` 18 rows; `outcome_controls.py` 35 rows;
`aim_check.sh` exit 0, its ctl rows failing, output identical to eng-e1l's; `svc_controls.sh` 78 rows. All as they
must. `shot_engine.py` was not run (it needs eng-e1k's SHOTNP / SHOTDMG / SHOTLATE scenes on the disc).

## 6. Lab arms, files

- Lab arms (boot files, none a default): CAMDIAG (diagnosis lines in the trace; trace runs only), CAMEVERY (control:
  Leon's matrix to the shoulder camera every tick). PC: `RE4_CAMDIAG=1` (native build), `STAT_BYTES=0` (old reference).
- Files: `services/camera/eng_camera.h`, `camera_svc.cpp`, `cam_eval.cpp` (diagnosis lines), `core/frame.cpp` (CAMDIAG
  sink), `core/main.cpp` (CAMEVERY), `hostref/Makefile` (STAT_BYTES), `hostref/svc/svc4_dump.cpp` (PC sink),
  `hostref/svc/camengine.sh` (old-reference and control rows; the ZCLIP0 LEON row's must), SERVICES.md 48c, this file.
  Nothing in `src/`, `include/`, `tools/plays_right/`, `allowed_original.txt`, `render/`, STATUS.md, HANDOVERS.md. No
  stub added; no original unit newly linked.

## 7. Not done

- Which routine-byte test chose the different shoulder offset at the aim starts (LEON 387, SHOT 150) on the old
  reference was not isolated (CAMEVERY shows it is not the `setPlayerLocation` one; with the define both agree).
- Every reference trace and fixture expectation made with the old reference by earlier lanes was made with the routine
  bytes unswapped; the PC checks above still end as they must, but other lanes' stored numbers were not re-derived.
- The ZCLIP0 LEON difference (the wall probe at zero width) is not diagnosed past the collision query.
- shot_engine.py not run; no console run; no timing.
