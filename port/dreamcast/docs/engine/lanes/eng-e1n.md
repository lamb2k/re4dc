# Lane eng-e1n: the last camera evaluation, camera tracks on the key evaluator, HUD digits at draw time

Branch `lane/eng-e1n` from `engine` a864c690f. Brief: `E:\RE4DC-Lanes\eng-e1n\BRIEF.md`. Answers the third E1 audit
(`E:\RE4DC-Lanes\audit-e1c\AUDIT-E1C.md` sections 1 and 2) under rulings H-017.1 to H-017.5. Status: **finished,
unaudited**. Evidence: `E:\RE4DC-Lanes\eng-e1n\` (maps, ev, runs). Every number below is PC (re4ref) or Flycast; none is
a timing.

## 1. Evaluation out of the two hosted bodies (H-017.1)

**Which way, and why.** `src/` is not edited. The two functions differ:
- `CameraQuasiFPS::move` (cam_qfps.cpp:1226-1346) holds its decisions and the follow filter in one body: the 0.6
  lateral filter is inline arithmetic on two function statics between the wall probe and the two `PSMTXMultVec`. No
  link-level split can take inline arithmetic out of a compiled body, so the hosted copy cannot stay: **the function is
  weakened** (game/Makefile SPLIT_UNITS: cam_eval.cpp defines it) **and the engine's body calls the hosted
  decisions** (`checkCameraType`, `checkFBLR`, `calcDepressionRatio`, each the unit's own function) and the camera
  service (`calcBaseMatrix`, `calcOffset`, `hitCheck`, and the new `cam_shoulder_follow`).
- `CameraPushObject::move` (cam_extra.cpp:998-1088): every evaluation step is already a call (`PSMTXInverse`,
  `PSMTXMultVec`, `PSMTXIdentity`, `MtxRotAxisPosRad`, the `RE4DC_XM_POINT` macro is `PSMTXMultVec` in these images);
  the decisions (which door: id 0x41 / 0x44 / 0x46, alive, in front, within 4000, the nearest; whether to swing: the
  door's facing 45 to 135 degrees from Leon's; which side) are inline. So **the unit is split at link**: the hosted body
  stays and its five matrix calls are bound to camera-service entry points (`cam_mtx_inverse`, `cam_mtx_point`,
  `cam_mtx_dir`, `cam_mtx_identity`, `cam_mtx_turn_about`; objcopy `--redefine-sym` on cam_extra.o, the same in the PC
  native build, hostref/svc/svc.mk). The binding covers the unit's other camera bodies' matrix calls too (the scope's
  and the binocular's frames).

**How each body differs from the original.**

| Body | Original | Engine |
|---|---|---|
| `CameraQuasiFPS::move` | one body: type check, base matrix, the site's table pair by a four-case switch, look angles, offset blend, wall probe, then inline `p2.pos.x *= 1 - lr_rate; eff.x = eff.x * lr_rate + p2.pos.x` (and the target) on function statics, two `PSMTXMultVec`, roll 0, the walking ratio by a status switch, the smoothing snap, the debug frustum drawn as lines (debug_mode 0xF) | a composition: the three hosted decisions called; the site's tables as one rule (sites 0, 1 the ready table, 2, 3 the transition table; the odd sites the table's second row and the blend-from table's second side); the evaluation as service calls; the follow is `cam_shoulder_follow` (its own state, `ShoulderFollow` in the service: eye and target in player space as SH4ZAM vectors; x' = keep x + take new on x only, y and z taken; both points through the base frame by `frame_point`; roll 0, fov passed). The walking-ratio rule and the reset's snap are kept with the composition; the debug frustum is counted, not drawn. It runs the decisions in the original's order (the state each reads depends on it) |
| `CameraPushObject::move` | not rewritten: the hosted body | its matrix calls: `cam_mtx_inverse` (the frame's inverse from SH4ZAM's 3 x 3 adjugate over the determinant, `frame_inverse`; the SDK uses cofactors written out); `cam_mtx_point` / `cam_mtx_dir` (`frame_point` / `frame_dir` on SH4ZAM vectors); `cam_mtx_turn_about` (Rodrigues' turn of the unit axes by one sine / cosine pair, position pos - R pos; the original concatenates a translation, an axis-angle matrix and a translation) |

**Link check** (`tools/engine/check_link.py`, two new line kinds; `allowed_original.txt`):
`=game/cam_qfps CameraQuasiFPS::move* 0`, `=game/cam_extra CameraPushObject::move* 924` (size ceilings: an allowed
body over its ceiling is SERVICE), `-game/cam_extra PSMTXInverse PSMTXMultVec PSMTXMultVecSR PSMTXIdentity
MtxRotAxisPosRad` (a reference ban read from the map's cross reference table; the image links `-Wl,--cref`; a map
without the table fails the line). Controls (`E:\RE4DC-Lanes\eng-e1n\maps\item1`):
- `CAM_EXTRA=-DE1_CAM_ORIG_QFPS_MOVE=1` (cam_qfps's own body linked): **FAIL**, SERVICE 1 (1,256 B): `CameraQuasiFPS::move()`
  `SERVICE(ceiling 0 B)`.
- `CAM_PUSH_ORIG=1` (cam_extra calling the SDK's functions): **FAIL**, SERVICE 5: `references MtxRotAxisPosRad,
  PSMTXIdentity, PSMTXInverse, PSMTXMultVec, PSMTXMultVecSR`.

| Image | before (a864c690f) | after |
|---|---|---|
| default | PASS, 384 allowed (108,236 B), 0 service | PASS, 384 allowed (107,044 B), 0 service |
| SENDABLE=1 | PASS, 384 (108,236 B), 0 | PASS, 384 (107,044 B), 0 |
| FIGHT=1 | FAIL, 114 service (42,156 B) | FAIL, 114 service (42,156 B) (step 3) |
| BOSS=1 | FAIL, 57 service (17,192 B) | FAIL, 57 service (17,192 B) (step 3) |

In all four, `CameraQuasiFPS::move` (1,256 B) is gone from the hosted code and `CameraPushObject::move` (924 B) stays
(allowed, at its ceiling). The camera service's new entries are timed in group 6 (`CAM_SVC`).

**PC check** (`hostref/svc/camcheck.sh`, rows added for this lane's exercises; the bound unchanged: max(0.01 unit, 2^-20
x the coordinate), 0.01 degree, decisions equal; `ev\chk-i15\camcheck.md`): every earlier row as it must (e1-route
10% of its bound, hill-ashley 39%, bell-ganado 0%, square-follow 5%, door103-walk 0%, determinism exact, camblend 10%,
camrail 20%; the three controls FAIL). New:
- **exercise campush** (door103-walk, the walk to the farm door; svc4_dump.cpp): the push-object camera from tick 40 to
  140 and from 200 to the end (CamCtrl.startPushObject, as pl_push starts it). No actor of the room is a door, wall or
  window, so from tick 200 the first actor record other than Leon's is shown to the camera as a window (id 0x46, 1,500
  ahead and 600 right of Leon, facing across him) for the camera's move and restored after it: the door branch runs
  (149 moves, 149 turns about the target). **PASS, 348 ticks, worst 0** (bit-identical).
- control **caminv** (the push camera's player-frame inverse skipped): **FAIL** at tick 200 (eye 572 units; worst 2,980).
- control **camfollow** (the follow's rate 0.5 instead of 0.6, e1-route): **FAIL** at tick 66 (worst 7.55 units).
- svc_controls.sh: 79 rows as they must (78 + camslope, section 2). controls.sh 18, outcome_controls.py 35, aim_check.sh
  as before (ev\chk-i15).

## 2. Camera tracks on the motion-key evaluator (H-017.2)

**Conversion at load** (services/camera/camera_svc.cpp): when a `CameraMotion` is made on a camera motion file (the
camera data is loaded: the cut's export at a cut switch, an event's file), each part (eye, target, roll, fov) is
evaluated once for every integer frame 0 .. maxFrame by the skeleton's native key decoder (`skel_mk_decode`, an
exported wrapper of skel.cpp's `mk_decode`: the bracket by a binary search on the key frames, then the Hermite segment
in the original's arithmetic) into an `MkClip` (skel_mk.h) whose aux rows hold eight floats a frame (eye x y z, target x
y z, roll, fov in degrees; the last row each axis's last key, the answer at and past the end). Not offline in the bake:
the cut exports are made in play from the room's rail cuts, so the conversion is where the file appears.
**At run time** `CameraMotion::move` reads one row by the evaluator's row rule (`mk_row_of`, moved from skel.cpp to
skel_mk.h; flags 2 as the original's camera evaluation: past the end the last row), then the frame, the base matrix and
the clock as before. No history, no wrapped search, no key decoding per tick; the engine has no `HermiteInterpolation`.
A frame without a row (not an integer: every caller starts a camera motion at an integer frame and the clock steps
whole frames) is not decoded: the camera holds, counted. Accepted keys: each axis from frame 0, strictly rising (the
decoder answers as the original's history search there); not accepted, or the store full: the motion is not played
(ends at its first move, the camera held), counted and logged.

**How it differs from the original** (cam_motion.cpp, motion.cpp HermiteInterpolation): the original keeps a key
history per part and axis and, every move, searches forwards (or backwards, wrapping) from it for the bracket, decodes
the key pair's fields, blends, and converts the fov to degrees; the engine does all of that once per frame at the
making, with a binary search and no history, and the move is a row read.

**Memory** (where: the camera service's track store, `g_track_store`, 12,288 B static in every image; per live motion
96 B header + 32 B a frame, released when the motion is destroyed): LEON and HILL have no motion cut (0 B); FIGHT's cut
at the village cross (one rail cut exported, 122 rows, 122 moves): 4,000 B (`E1 CAMTRACK rows 488 moves 122 not-played
0 store peak 4000 of 12288 bytes`, Flycast); the PC camtrack exercise's two tracks 122 + 152 rows = 8,960 B. A track over the store is
refused and counted; the largest cut export (6 keys: 152 rows, 4,960 B) fits twice.

**Check, stated before running: camcheck's bound.** PC exercise camtrack (svc_controls.sh row; `ev\exr\camtrack`): 1,260
of 1,260 track moves **bit-identical** to the original (CT lines, hashes of the original's history skipped), 1,096 rows
converted, 0 refused; so the key segments hold the tracks exactly. The fight cut on Flycast: section 6.
Control **camslope** (one key's out-tangent 1.25 times steeper in the conversion): FAIL, first at call 625 (tick 32,
frame 21 of the uneven-key track), worst 29.6 units, 226 of 1,260 moves apart.

The exercise's direct evaluation of one track's keys at a sweeping frame (HermiteInterpolation called from
svc4_dump.cpp) is gone with HermiteInterpolation. The reference's facial shape keys (shape.cpp, linked in both PC
builds, not an engine service) reached it through the camera service's copy; in the PC native build they now use
`skel_mk_decode` through a weak adapter in svc4_dump.cpp (motion.cpp's own weak there; the reference build keeps
motion.cpp's). svc4_units.sh: 0 original functions kept.

## 3. The motion writer (H-017.3)

`HermiteExport` (cam_eval.cpp) checks the cut's key count (1 .. 26, the cut's frame table) and the file's size (36 +
4 x align4(6 + 42 n) bytes) against the motion buffer (0x440, cam_ctrl.cpp's CAMERA_MOTION_BUFFER_SIZE: the only buffer
the controller exports into) before writing anything. Refused: nothing written, the needed size returned (0 for a bad
count); the hosted callers compare it with their buffer and log the original's error message; the CameraMotion they
then make on the buffer is refused by the track service (the buffer is marked) and the controller leaves the cut at its
first move. Check (camcheck.sh rows; exercise camexport, a 7-key cut, 1,236 bytes, into a buffer between a 64-byte and a
256-byte guard pattern): engine **PASS** (returned 1,236, buffer untouched, guards intact, the motion ended at once);
control, the original writer on the same cut (odump): **FAIL** (buffer and trailing guard overwritten).

## 4. HUD digits at draw time (H-017.4)

`e1_hud_draw_tick` (services/draw.cpp) and its per-tick call (core/main.cpp) are gone. The renderer's HUD pass
(render/native_layers.inc `native_hud`) asks the live count once a picture (`hud_magazine_live`: the loaded count and
whether the equipped weapon shows it) and splits it into ones, tens and hundreds there, in the drawing row. Lab arm
HUDFREEZE (boot file, control): the count frozen at open. Check: section 6.

## 5. The PUB line (H-017.5)

`E1 PUB camera N light-view-misses N` (host/e1_svc_mem.cpp): the camera copy control (PUBCOPY now copies into a global
stream, `eng_pub_stream`: a real store) and the pictures a character was drawn without its light view
(services/actor_e1.inc). The selector (loader/selector.c, the PUB parse) fails a scene where either is not 0 or the
line is incomplete. The HUD and light-compare counters had no producer and are gone. Lab arm LIGHTMISS (boot file,
control): every character's light view refused. Check: section 6.

## 6. Flycast function check

Thresholds stated before the run (`E:\RE4DC-Lanes\eng-e1n\STATUS.md`): eng-e1j's still threshold (a pair is the same
picture when at most 0.5% of its pixels differ by more than 32 in a channel and the mean absolute difference is at
most 1.0); hudcheck fight 23 of 23, village and hill 36 of 36; the camera against eng-e1m's f1 (the engine's previous
key evaluator) and against the PC reference within camcheck's bound.

Disc **n1** (from 67cb5a42b: LEON, HILL, FIGHT, SHOT; traced; STILLS; eng-e1i's packs), Flycast std1, `runs\n1`:
- **4 of 4 scenes OK**; `E1 PUB camera 0 light-view-misses 0` in each; `E1 POOL full 0 bad_frees 0`; CAMREC 0
  non-finite.
- **Stills** against f1 (`ev\stills\n1-vs-f1.md`): **68 pairs (LEON 17, HILL 19, FIGHT 23, SHOT 9), 0 moved**, all 0.000%.
  The picture did not move.
- **The camera against f1** (`ev\fight-cut\camlog-n1-vs-f1.txt`, every CAMLOG tick): LEON 641, HILL 729, FIGHT 901,
  SHOT 321 ticks, **all bit-identical**; the fight cut's 121 motion-camera ticks (routine 5, ticks 127 on) bit-identical.
  f1's evaluator was HermiteInterpolation (eng-svc4), bit-identical to the original's on the PC camtrack exercise, so
  the cut agrees with the original's arithmetic. Control: n1's log with the first motion tick's eye x 0.05 further: FAIL
  (1 tick, 248% of the bound).
- **camengine.sh** against the PC reference (`ev\cam-n1\camengine.md`): LEON PASS (worst eye 0.00097, 10% of the
  bound), HILL PASS (0.0039, 19%), SHOT PASS (0); the PC zero-distance rows as they must. (No old-reference build in
  this worktree: its rows are not run; they belong to eng-e1o.)
- **hudcheck** (`ev\hud\n1-*.txt`): FIGHT 23 of 23 (SHOT 9 of 9 more), village and hill 36 of 36.

Disc **n2** (the same images; boot files FIGHT/PUBCOPY, FIGHT/HUDFREEZE, E1H/LIGHTMISS; STILLS), `runs\n2`: LEON OK;
**HILL FAILED** "PUB: camera copies 0, light-view misses 728" (LIGHTMISS); **FIGHT FAILED** "PUB: camera copies 900,
light-view misses 0" (PUBCOPY); hudcheck on FIGHT (HUDFREEZE, count frozen at 10): **FAIL, 22 of 23 wrong** (the first
still's magazine is 10); village and hill 36 of 36 (not frozen).

Both test discs were deleted after their runs (`cdisc\DELETED.txt`).

## 7. Shared files touched, lab arms, what was not done

- **Outside the brief's owned list, touched because the items need it:** `services/skeleton/skel.cpp` and `skel_mk.h`
  (`mk_row_of` moved to the header; `skel_mk_decode`, an exported wrapper of `mk_decode` that leaves the skeleton's axis
  counter alone), `tools/engine/check_link.py` (ceilings and reference bans), `host/e1_svc_mem.cpp` (the PUB line and
  the new CAMTRACK line), `core/e1_core.h` (the HUD draw step's declaration), `render/native_scene.h`.
- **Shared with eng-e1o:** `core/main.cpp` (the HUD call removed), `loader/selector.c` (the PUB parse only),
  `hostref/svc/camcheck.sh` (rows added for campush, caminv, camfollow, camexport; nothing else changed).
  `services/draw.cpp` reads two new boot files (HUDFREEZE, LIGHTMISS) in `e1_draw_open`, before play, as the others.
- **Lab arms (none is a default):** boot files HUDFREEZE, LIGHTMISS (new), PUBCOPY (now a real copy); re4ref controls
  camslope, camfollow, caminv; re4ref exercises campush, camexport; control builds `CAM_PUSH_ORIG=1`,
  `CAM_EXTRA=-DE1_CAM_ORIG_QFPS_MOVE=1`.
- **Not done / limits:** the campush exercise's door branch runs on a planted window (no fixture room has a door,
  wall or window actor near Leon); no fixture has Leon pushing an object in play. A camera track whose keys do not
  start at frame 0 and rise, or that does not fit the 12 KiB store, is not played (none in E1; event cutscene
  cameras of later rooms may need a larger store, sized then). The PC exercise camtrack no longer evaluates keys
  directly at a sweeping frame (the function it called is gone).
