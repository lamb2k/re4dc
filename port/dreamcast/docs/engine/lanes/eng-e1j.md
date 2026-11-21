# Lane eng-e1j: the camera as one native service, no per-tick conversion

Branch `lane/eng-e1j` from `engine` 736751764. Brief: `E:\RE4DC-Lanes\eng-e1j\BRIEF.md`. Answers the second E1 audit
(`E:\RE4DC-Lanes\audit-e1b\AUDIT-E1B.md` sections 2, 3, 6; rulings H-016.1 and H-016.2). Status: finished, unaudited
(per item below).

## 1. The camera units, function by function

Rule used to sort them. A **decision** chooses: a camera mode, a cut, a routine, a target or offset table, a site, a
state, or the target and eye a routine wants from the player's state and the stick. A **service** evaluates: it
blends or smooths camera parameters, fits, evaluates or searches a spline, tests containment, probes lines of sight,
builds a frame or a matrix, or relocates and reads the camera data. Debug drawing is a logged stub. The default image
links 63 camera functions (FIGHT=1 links 83: the binocular camera and four cam_sys helpers more); every one is below.

### cam_ctrl (the controller)

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| CamCtrlShoulderSetAim, CamCtrlShoulderSetSearchFrame | 20, 12 | decision | setters of the shoulder camera's aim and delay |
| CameraControl::CalcAim | 84 | decision | the aim point: player plus the cut's offset |
| CameraControl::Check | 436 | decision | area check, attach check, the fall camera's state |
| CameraControl::CoreDataRead, RoomDataRead | 36, 56 | decision | install the data (call the relocation) |
| CameraControl::LerpDataSearch | 92 | decision | which blend record a transition uses |
| CameraControl::LowerBinocular, endScope, startPushObject, endPushObject | 144, 156, 56, 168 | decision | mode changes |
| CameraControl::Move, Move [clone .part.0] | 52, 760 | decision | runs the routine of r0, then hands the result to the blend, the smoothing and the frame (services) |
| CameraControl::areaHitCheck | 1076 | decision | which area and cut is active (calls the containment test) |
| CameraControl::checkAttachCamera, registAttachCamera, deleteAttachCamera | 524, 100, 56 | decision | which motion-attached camera holds |
| CameraControl::getCameraDirection, getCameraPitch, resetCameraAngle, getTrajectory | 16, 4, 16, 68 | decision | getters and resets of decision state |
| CameraControl::r0_Debug, r0_Fix, r0_Free, r0_Pan, r0_RailBehind, r0_RailPan, r0_Track | 788, 180, 1540, 304, 3016, 372, 324 | decision | each routine chooses its eye and target from the player and the stick (they call the rail, probe and smoothing services) |
| CameraControl::roomInit, switchCamera | 596, 992 | decision | room start; the cut switch picks the routine |
| CameraControl::Comeback, CutCall, HoldBinocular, IsMotionEnd, SetBinocularRange (FIGHT=1) | 64, 144, 116, 36, 16 | decision | script calls and mode changes |
| **CameraInterpolation::move** | 264 | **service** | blends eye, target, roll, fov over the remaining frames |
| **CameraSmooth::move** | 300 | **service** | quake compensation and exponential smoothing |
| **areaHit** | 184 | **service** | containment of a position in an area (facing range, then the polygon test) |
| **area_hit_p3, area_hit_pN** | 316, 376 | **service** | point in polygon (cross products; crossing count) |
| **cameraHitCheck** | 864 | **service** | the camera's line-of-sight probe: three collision queries, the nearest hit, the partner's cylinder |
| **searchRail** | 528 | **service** | the rail parameter nearest the aim point |
| **CameraControl::calcAddr, cameraDataVersion** | 384, 376 | **service** | relocation of the camera data file, its version read |
| HermiteExport, Parametrize, BSpline, debugDrawRail | (native since eng-svc4) | service | rewritten in this lane (section 2) |

### cam_qfps (the shoulder camera)

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| bindAreaCamera, bindDefaultCamera | 464, 168 | decision | which offset table each type uses |
| calcDepressionRatio | 240 | decision | pitch and yaw look angles from the weapon and the stick |
| checkCameraType | 648 | decision | the transition and ready types from character and weapon |
| init, setAreaData, setBlendCount, setBlendData, setFloorRatio, setPlayerLocation | 204, 668, 24, 180, 12, 44 | decision | state and table set-up |
| move | 1256 | decision | chooses the site and composes the services below; its lateral follow rate (lr_rate) is a tuning rule kept with it |
| **calcBaseMatrix** | 1256 | **service** | the player-space frame: search delay, overrides, floor tilt, crouch drop |
| **calcOffset** | 932 | **service** | blends the offset tables (old to new, up / mid / down by pitch), turns them by the yaw |
| **hitCheck** | 2216 | **service** | the wall probe: three lines from the close point, the nearest hit, the frustum-edge probes |
| **offsetCorrection (both)** | 252, 100 | **service** | keeps each table's close point behind the player |

### cam_extra and cam_sys

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| CameraAttachedToMotion ctor / dtor, CameraLookAt ctor / move / dtor, CameraPushObject ctor / move / dtor | 20 to 924 | decision | each picks its eye and target (the hand it looks at, the push direction, the door to swing round); they call the probe service |
| CameraBinocular ctor / move / setRange / dtor (FIGHT=1) | 652, 776, 36, 76 | decision | the binocular's zoom and aim from the stick |
| CameraAttachedToMotion::move | (native since eng-svc4) | service | rewritten in this lane |
| **IdBinocular::init / move / quit / dtor, IDApplication::init, FocusAnimation::move** (FIGHT=1) | 344, 1412, 204, 4, 4, 212 | **service** | the binocular's ID widget and the focus blur: drawing, not camera decisions |
| **cam_sys, every function** (CameraGetRoll, CameraRotAxisPosRad, CameraSetOrientationZeroRoll, CameraTargetRot in FIGHT=1; the rest unlinked or native) | 132, 108, 648, 212 | **service** | orientation, roll, turns, dolly, distance: camera maths; the unit is no longer allowed |

### Debug

| Function | Bytes | Kind | Why |
|---|---:|---|---|
| **scrHitCheck(cPlayer*) [clone .part.0]** (pl_debug) | 256 | **service** | a scenery ray drawn as debug lines: a logged stub |

### The gap made visible (control)

`allowed_original.txt` now refuses the services above (exception lines, cam_sys not allowed). The baseline maps
(`engine` 736751764 built unchanged, `/dev/shm/eng-e1j/base-*`) against the new list (evidence
`E:\RE4DC-Lanes\eng-e1j\ev\item1`):

| Image | Before (old list) | Baseline map, new list |
|---|---|---|
| default | PASS, SERVICE 0 of 399 | **FAIL**, SERVICE 15 (8,604 B): the 14 camera services and scrHitCheck |
| SENDABLE=1 | PASS, SERVICE 0 of 399 | **FAIL**, SERVICE 15 (8,604 B) |
| FIGHT=1 | FAIL, SERVICE 109 (41,580 B) | FAIL, SERVICE 134 (53,464 B): 25 camera / debug more |
| BOSS=1 | FAIL, SERVICE 58 (18,796 B) | FAIL, SERVICE 73 (27,400 B): 15 more |

## 2. The camera service

One engine service owns the camera (`services/camera/`: `camera_svc.cpp`, `cam_eval.cpp`, `cam_math.h`,
`eng_camera.h`). Its state is the renderer's camera record, `EngCamera eng_cam`: the view matrix (rows right, up,
look; translation -R eye), the six projection terms the renderer uses, the viewport and far plane (the first 26 words,
the renderer's stream layout), then the camera it evaluated (eye, target, roll, fov). `CameraMove` writes it once a
tick after the hosted controller (`CamCtrl.Check`, `CamCtrl.Move`: decisions) has chosen the camera. The behaviour
chooses through the controller and reads back what it needs (`pG->Cam`: the parameters, the frame `mat`, up, look,
right, the distance). `pG->Cam.v_mat` and `ProjMat` are no longer written: their two engine readers, the laser line
and `GetScreenPos`, read `eng_cam.view`; the hosted reader `localCoordTest` is debug code behind a debug flag.

Arithmetic (`cam_math.h`): SH4ZAM's `shz_vec3_t` and `shz_mat3x4_t` (a frame: right, up, look, position columns),
SH4ZAM's element-wise operations and its 3 x 3 adjugate; exact roots and true divisions; libm's sin, cos, tan and
atan2. The approximate SH-4 paths (FSRRA, FSCA, FTRV) are not used: the camera's frame turns the stick into Leon's
walking direction, so the PC check and the console must compute the same camera. No SH4ZAM routine was missing; the
submodule is unchanged (no commit on `re4dc/eng-svc5`).

### How each rewritten function differs from the original

| Function | Original | Engine form |
|---|---|---|
| CameraSetOrientationRoll / ZeroRoll / Up (cam_sys) | look, right, up from unnormalised crosses, rolled by an axis-angle matrix (PSMTXRotAxisRad), each normalised after | look normalised first, right = (look.z, 0, -look.x) normalised, up = look x right, the roll as one sine / cosine pair (right cos + up sin, up cos - right sin) |
| CameraGetRoll, CameraRotAxisPosRad, CameraTargetRot, CameraCamposRot, CameraDolly, Camera*Distance, CameraSetWithRoll (cam_sys) | a matrix inverse and products; MtxRotAxisPosRad | the zero-roll frame's x row through the frame (no inverse); Rodrigues' turn on vectors (no matrix) |
| CameraMove (camera.cpp) | pG->Cam's look-at matrix (C_MTXLookAt) and a 4 x 4 perspective (C_MTXPerspective), which a draw step then copied | the record written in place: the frame from eye, up, target, transposed; the six terms in closed form |
| VIEW::initPerspective / orientation (view.cpp) | planes from three corners each (cross products), the bounding sphere by a 3 x 3 circumsphere solve | the planes' normals in closed form of the half-angle tangents, the sphere centred on the axis (one equation) |
| CameraInterpolation::move, CameraSmooth::move (cam_ctrl) | PSVECScale / PSVECAdd per field | one weighted mix over the parameter block's eight lanes (the target left weighted, as the original leaves its caller's) |
| areaHit, area_hit_p3 (cam_ctrl) | the inner wedge of two opposite corners (cross products of corner vectors) | the inner side of every edge (one 2D cross per edge) |
| area_hit_pN (cam_ctrl) | slope-intercept intersections of each edge with the line x - z = c, bounded by its x and z ranges | the crossing's parameter along the edge in [0, 1) ahead of the position; the same rule for the axis-parallel edges the data was laid out against (they never count) |
| cameraHitCheck (cam_ctrl) | three queries, nearest by PSVECDistance, the partner's info copied through a pinned register | the nearest of three hits by squared distance; the partner's body test on the ground plane in squared form |
| searchRail (cam_ctrl) | a segment pass, then a key pass inside one of two branches | one key pass, one segment pass, one decision |
| Parametrize (cam_ctrl) | dense n x n collocation from a full de Boor-Cox table, LU inverse, eight matrix-vector products, ten heap buffers | the basis on its span only (The NURBS Book A2.2), the tridiagonal collocation solved by elimination without pivoting for the eight channels at once, on the stack |
| BSpline (cam_ctrl) | the Camera cleared, the full n-term basis, eight accumulations over every control point | the span's k + 1 basis values, a dot product per channel over k + 1 control points; only the parameter block written |
| HermiteExport (cam_ctrl) | stores through casts, a byte-copy macro | a small writer; the eight channels from one accessor; the same file format (the keyed-track service reads it) |
| CameraAttachedToMotion::move (cam_extra) | the model's matrix inverted, the target corrected in model space | a plane test on the model's axes (normal = x axis x y axis; no inverse) |
| CameraQuasiFPS::calcBaseMatrix (cam_qfps) | an Euler matrix (RotMatrix) for the search yaw, column copies, PSVEC crosses | the yaw frame from one sine / cosine pair, frames as SH4ZAM 3 x 4 columns |
| CameraQuasiFPS::calcOffset (cam_qfps) | VecLinearCombination per field, a rotation matrix for the yaw | one eleven-number mix per site; the yaw as a sine / cosine pair |
| CameraQuasiFPS::hitCheck (cam_qfps) | PSMTXInverse per hit, eight PSVEC steps per probe, debug lines | the frame's inverse once (adjugate / determinant), one probe helper, the side probes as one routine for both signs |
| offsetCorrection (cam_qfps) | normalise the line, compare lengths | the line's parameter s at z = -320, moved when s > 1 |
| CameraControl::calcAddr, cameraDataVersion (cam_ctrl) | a strncmp chain; per-field casts | the version from the fourth character; one relocation functor |
| debugDrawRail; scrHitCheck (pl_debug) | debug drawing | counted (rail); a logged stub (`host/e1_stubs.cpp`) |
| HermiteInterpolation, CameraMotion (keyed tracks) | (lane eng-svc4's bodies) | not rewritten in this lane (not named by the audit; checked by the camtrack exercise) |

### Link check (default and SENDABLE must pass)

| Image | engine 736751764, old list | baseline, new list (control) | this lane |
|---|---|---|---|
| default | PASS, 0 service of 399 | FAIL, 15 (8,604 B) | **PASS, 0 service of 384** |
| SENDABLE=1 | PASS, 0 of 399 | FAIL, 15 (8,604 B) | **PASS, 0 of 384** |
| FIGHT=1 | FAIL, 109 (41,580 B) | FAIL, 134 (53,464 B) | FAIL, 115 (43,760 B): of the camera units only the binocular's ID widget and the focus blur (6, 2,180 B), with the fight's 109 step-3 functions |
| BOSS=1 | FAIL, 58 (18,796 B) | FAIL, 73 (27,400 B) | FAIL, 58 (18,796 B): no camera function |

`game/Makefile`: `camera/cam_eval` in the round-4 services, cam_qfps a split unit, `-I` SH4ZAM; `hosted.mk`: cam_sys
not hosted; pl_debug's scrHitCheck weak and the unit built `-fno-partial-inlining` (cPlayer::debugMove then calls the
symbol, not a local clone). The hosted callers reach the native bodies through relocations (`sh-elf-objdump -dr` on
cam_ctrl.o and cam_qfps.o: Move, areaHitCheck, the r0 routines, CameraQuasiFPS::move and bindAreaCamera call the
symbols; none is inlined).

### The PC check (camcheck)

`hostref/svc/camcheck.sh` (and `camcheck.py`): re4ref odump (the original camera units) against native (the camera
service) on the same inputs, wind off; the frame's camera of every tick (`cam.txt`, `svc4_dump.cpp`): eye and target
within **0.01 unit** per axis, roll and fov within **0.01 degree** (stated before the first run), and the controller's
decisions (area, cut, routine, blend frames left) equal. Evidence `E:\RE4DC-Lanes\eng-e1j\ev\cam3\camcheck.md`.

| Row | Must | Result | Worst eye / target (units); roll / fov (deg) |
|---|---|---|---|
| e1-route (the village route) | PASS | PASS, traces PASS | 0.00025 / 0; 0 / 0 |
| hill-ashley (the hill) | PASS | PASS, traces PASS | 0.0098 / 0; 0 / 0 |
| bell-ganado (the fight fixture) | PASS | PASS, traces PASS | 0 / 0; 0 / 0 |
| square-follow (probes past Ashley) | PASS | PASS | 0.00098 / 0 |
| door103-walk | PASS | PASS | 0 / 0 |
| determinism (exact) | PASS | PASS | 0 |
| exercise camblend (two 30-tick cut blends) | PASS | PASS | 0.00024 / 0 |
| exercise camrail (631 rail fits, searches, evaluations) | PASS | PASS | 0.00195 / 0.00196; 8.5e-7 / 7.7e-6 |
| control: smoothing off | FAIL | FAIL at tick 1 (eye 0.032; worst 1,240) | |
| control: cut blend off (camblend) | FAIL | FAIL at tick 100 (blend frames 29 against 0; worst 864) | |
| control: rail parameter 0.25 on (camrail) | FAIL | FAIL at tick 10 (eye 237) | |

No fixture reaches a cut blend or a rail (the counters: blends 0, rails 0 on every fixture); the two exercises plant
them, the same calls in both builds. The hill's 0.0098 is five float steps at x = 21,069 (the step there is 0.00195):
the original takes its wall-probe hits back into player space with a full matrix inverse (rotation times the point plus
a translation, which cancels), the service subtracts the frame's position first. The bound holds; a relative bound
would be the sturdier one for rooms far from the origin.

Two faults found on the way:
- **The PC reference's rail was wrong.** cam_ctrl.cpp's BSpline calls the basis through math_sub.h's floats-first alias
  (`de_Boor_CoxF(n, knot, t, k, out)` -> `asm("de_Boor_Cox")`). The PowerPC and the SH-4 pass floats and integers in
  separate registers, so the alias reaches the right arguments there; i386 passes them on the stack in order, so on the
  PC t and k arrived swapped and the reference's rail always evaluated at its first key. `hostref/prep.py` writes the
  call in the function's own order in the host copy (the call the PowerPC makes). The SH-4 image was never affected.
- **The image has no near or far plane.** ZNEAR and ZFAR are zero in every E1 image (`host/e1_stubs.cpp` storage;
  main.cpp's 100 / 1,000,000 never run): the shoulder camera's side probes have zero width and no near offset there
  (the reference has 100), and the projection's depth terms are not numbers. The record keeps both as they are, so the
  picture does not move; setting them changes behaviour and picture, for a later lane with a still pair.

The service-check table (`svc_controls.sh`, lanes eng-svc to eng-e1h) compares the round-4 boundary log bit for bit;
the camera's lines and the probes it makes now differ by float steps, so its reference-against-native rows compare the
log within 0.01 (hashes of float state are marked `h` in `svc4_dump.cpp` and skipped there); determinism and every
control stay bit for bit. Result: 77 rows, every row as it must (`E:\RE4DC-Lanes\eng-e1j\ev\svcctl\svc_controls.md`).

## 3. No per-tick conversion

- **The camera:** the renderer reads the service's record in place (`core/draw_e1.c`: `scene.state[0] = &eng_cam`
  once at open; every pass reads the camera stream from there). `e1_camera_draw_tick` (48 bytes and six terms copied
  a tick) and its call in `core/main.cpp` are gone; the CAMSTALE lab arm now freezes the record itself.
- **The HUD's four words:** the renderer read only the stance (word 3, the knife part); it now reads it from the game
  state when it draws (`hud_stance_live` -> `PlGetWeaponNo()`, `render/native_actor.inc`), the bench keeps the pack's
  word. Life, maximum and weapon were not read by the renderer: no longer written. The ammo digits stay as lane eng-e1i
  left them (the HUD's own state, set once a tick: the brief's "as it already does for the digits").
- **A character's light record:** the behaviour writes the light inputs directly (em10's damage flash writes the
  material colour, parts show and hide by be_flag, the room status word), so there is no setter to hang a record on.
  The record is the model itself: the light rule reads each input in place through a view of addresses
  (`services/light_view.h`, `services/draw.cpp e1_light_view`, `render/source_light.inc` `LI_*`; gathered for the
  picture as the skeleton views are). The light service of lane eng-e1e (`e1_light_service_tick`: a 14-word snapshot and
  compare per character per tick, a 17-word record on change) is gone: **0 compares**. Leon keeps the pack's record.
- **The counter line** `E1 PUB camera N hud N light-compares N (light view misses N)` (host/e1_svc_mem.cpp) and the
  selector (`loader/selector.c`, the PUB line only): a non-zero count or a missing line fails the scene.

## 4. Row attribution

Every camera service entry point the hosted controller calls is timed as service work (`CAM_SVC`, `cam_math.h`,
through `host/e1_wraps.cpp`'s `e1_svc_enter / leave`; nested calls once), in a new group 6, `E1_SVC_CAMERA`
(`core/e1_core.h`). After this lane, of the ROW line's columns:
- `tick`: input latch end to the tick's end (behaviour plus services, as before);
- `svc`: every service entry point's time, the camera's included (group 6), plus the skeleton's palette publication;
  the selector's behaviour row is `tick - svc`, so the camera's evaluation is no longer in it;
- `cam`: CameraMove whole (the controller's decisions and the camera service); its service part is in `svc` too;
- `smot`, `scloth`, `sparts`, `scol`, `sfx`: groups 1 to 5 as before (the camera's group is not a ROW column: the ROW
  format belongs to core/frame.cpp; the per-entry `E1 SVC <name> us .. calls .. group 6` lines give it);
- `sparts` no longer holds the light service (gone).
Not moved: the ammo digits' split (`e1_hud_draw_tick`, three divisions a tick, after `e1_svc_end`) stays in the
remainder. Flycast (not a timing), same disc layout as eng-e1i's d1: services row mean 3,392 / 8,704 / 5,815 us
(LEON / HILL / FIGHT) against d1's 3,344 / 8,668 / 5,768 with the same tick means (3,484 / 8,853 / 6,713): the camera's
evaluation, 36 to 48 us of Flycast time a tick, moved from the behaviour's remainder into services. The pacer and the
field counter are not touched.

## 5. Flycast function check

Disc `j1` (from 7e2329cb2: LEON, HILL, FIGHT; eng-e1i's packs; STILLS), Flycast std1, `E:\RE4DC-Lanes\eng-e1j\runs\j1`:
3 of 3 scenes OK, 600 rows each, `E1 PUB camera 0 hud 0 light-compares 0` in each, `E1 POOL full 0 bad_frees 0`, Leon's
light check 0 of 12 fields. Stills at eng-e1i d1's pictures, pixel comparison (`s/picdiff.py`; threshold stated before
the run: a pair is the same picture when at most 0.5% of its pixels differ by more than 32 in a channel and the mean
absolute difference is at most 1.0): **59 of 59 pairs the same**, worst 0.001% of pixels, mean 0.006
(`ev/stills/j1-vs-d1.md`). The picture did not move. FIGHT also ran a motion-camera cut through the service
(HermiteExport 1, CameraMotion::move 122).

Controls, disc `j2` (the same images; boot files E1/CAMSTALE, E1H/LIGHTCTL, FIGHT/PUBCOPY; `runs/j2`):
- **PUBCOPY** (a forced copy of the camera record once a tick): FIGHT reports `E1 PUB camera 900` and the selector marks
  it **FAILED** ("conversions per tick: camera 900, hud 0, light compares 0"); LEON and HILL OK.
- **CAMSTALE** (the record keeps its next camera: `records 2` / `1`): LEON 15 of 17 stills moved (pictures 1 and 40,
  before the camera has moved, stay), HILL 19 of 19.
- **LIGHTCTL** (characters lit with a black material, HILL only): HILL picture 1, where CAMSTALE's camera still equals
  the live one, moved by Ashley alone (0.97% of pixels; her legs dark behind Leon, `ev/stills/hill1-j1-j2.png`).
- **The pixel check's own control:** j2's stills against j1's: 34 of 59 pairs MOVED, exit 1 (`ev/stills/j2-vs-j1.md`);
  FIGHT's 23 the same (PUBCOPY does not change the picture).

## 6. Lab arms and controls (none is a default)

Image boot files: CAMSTALE (now freezes the service's record), LIGHTCTL (black material through the light view), PUBCOPY
(new), PALCTL and HUDOLD (unchanged). LIGHTSTALE is gone (there is no record left to keep stale). re4ref environment:
`RE4_SVC_CONTROL=camsmooth|caminterp|camrail` (new), `camfov`, `camroll` (kept); `RE4_SVC_EXERCISE=camblend|camrail`
(new).

## Shared files touched

`core/draw_e1.c` (the camera stream pointer, the comment), `core/main.cpp` (the camera call), `core/e1_core.h` (the
camera group, the draw-tick declaration), `loader/selector.c` (the PUB line), `host/e1_stubs.cpp` (scrHitCheck's stub),
`services/laser.cpp` and `services/math/math_svc.cpp` (the view matrix from the record; outside the brief's list, one
line each).

## 7. Addendum (after the merge of engine 6f27a2db4, lane eng-e1k)

### 7.1 The camera check's bound, relative to the coordinate (stated before the re-run)

The absolute 0.01 unit is five float steps at x = 21,069 (the hill), where a float's step is 0.00195; in a room further
from the origin it would be fewer. The new bound, stated before running: each eye and target coordinate within
**max(0.01 unit, 2^-20 x |the reference's coordinate|)**; 2^-20 is about 9.5e-7, eight float steps at any magnitude (a
float's step is 2^-23 to 2^-24 of its size), so the bound is the same number of float steps in every room, and near
the origin the absolute 0.01 governs. At x = 21,069 it is 0.0201. Roll and fov stay within 0.01 degree; the decisions
equal. `camcheck.py --rel` (default 2^-20), `camcheck.sh` (CAM_REL); the report gives the worst share of the bound used.

Re-run on the merge (`E:\RE4DC-Lanes\eng-e1j\ev\addendum\camcheck.md`), every row as it must: e1-route 2% of its bound,
hill-ashley 49% (0.0098 against 0.0201), bell-ganado 0%, square-follow 10%, door103-walk 0%, camblend 2%, camrail 20%;
determinism exact; the controls FAIL as before (smoothing off at tick 1, cut blend off at tick 100, rail parameter at
tick 10).

### 7.2 What the service-check table loosened, and the correction

The first hand-back's `svc_controls.sh` gave the reference-against-native rows `svc4_compare.py --tol 0.01`: every line
of the round-4 boundary log within 0.01, not only the camera's. Bones, queries, palette and traces (`svc_compare.py`,
`plays_right.py`) were not touched. Corrected: those rows now take `--camera-tol 0.01`, which loosens only the camera's
lines (the camera kinds CM, VP, OR, OU, CT, HI, CA, HX, BS, PZ, and every line logged while CameraMove runs, its tick
token marked "c" by `svc4_dump.cpp`: the camera's own probes EH, OH, OB); every other line is compared bit for bit
again. Control `pos005` (Leon's model 0.005 unit along x at tick 100) in that mode must FAIL.

Result on the merge (`ev\addendum\svc_controls.md`): 78 rows (77 + pos005), every row as it must. e1-route's native row:
11,590 of 11,590 lines equal, 7,564 of them camera lines, 1,592 equal only within 0.01; every other line bit for bit.
pos005: FAIL; its first svc4 difference is the AT line of tick 100 (x c5a09ef9 against c5a09eef, 0.005 unit: inside the
first hand-back's 0.01 loosening, so that mode would have passed it on the boundary log), queries over 0.01 from tick 103;
bones stay within their unchanged 1-unit bound (0.116), as before.

### 7.2b Re-confirmed on the merge

Link check: default and SENDABLE=1 PASS 0 of 384; FIGHT=1 114 service (42,156 B), BOSS=1 57 (17,192 B) (GetWepTargetList2
went native with eng-e1k). `svc_controls.sh` 78 rows, `controls.sh` 18, `outcome_controls.py` 35, `camcheck.sh`,
`aim_check.sh`: every row as it must (`ev\addendum`). Flycast std1, disc k1 (LEON, HILL, FIGHT, timing-run records under
eng-e1k's stricter selector): 3 of 3 OK, intervals > 2: 0, PUB 0 in each; disc k2 adds FIGHT/PUBCOPY: FIGHT FAILED
"conversions per tick: camera 900".

### 7.3 ZNEAR and ZFAR (not changed here; queued by the integrator)

- **Set:** in the E1 images nowhere: `host/e1_stubs.cpp:53` defines them as zero storage. The original sets 100 and
  1,000,000 in `src/game/main.cpp:663-664` (not linked). The PC reference sets them in
  `engine/hostref/replay.cpp:95` (ZNEAR 100) and `:238-239` (100, 1,000,000).
- **Read (image):** `services/camera/camera_svc.cpp:233, 241` (the frustum, `VIEW::init / move`), `:343, 346, 349` (the
  record's depth terms and far plane; 0 far falls back to the renderer's 18,750); `services/camera/cam_eval.cpp:606, 609`
  (the shoulder wall probe's side width and near offset); hosted `src/game/cam_ctrl.cpp:1345` (the camera's water
  clamp; GetWaterHeight is stubbed 0 in E1). The original's `src/game/cam_qfps.cpp:770, 790` and `view.cpp:35, 45` are
  the same reads in the units the service replaced.
