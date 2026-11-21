# Lane eng-e2c: the boss image's remaining original service code (step 3, pass E2)

Status: **finished, unaudited** for 23 of the 26 functions (6 groups); the room's thunder (3) is not done and needs a
ruling (below). Branch `lane/eng-e2c` from `lane/eng-e2a` ce7fd1a44, `origin/engine` f161f4184 merged. Every number here
is the PC reference (hostref) or Flycast (plain build, function checks); none is a timing.

## Link check, service functions per image

| Image | Start (ce7fd1a44) | After presentation (fc3cd939f) | After pose (957661db9) | Final (f34b92cf0, merged 1858344ad) |
|---|---:|---:|---:|---:|
| default | 0 | | | 0 |
| SENDABLE=1 | 0 | | | 0 |
| FIGHT=1 | 73 | | | 73 |
| BOSS=1 | 26 (5,936 B) | 19 | 15 | 3 (432 B: r119_ThunderMove, r119_ThunderFlagOn, r119_ThunderFlagOff) |

Link controls (each must FAIL; each does, one more service function): `E2C_ORIG=__Z10em2bFootSeP5cEm2b` (presentation, 16),
`E2C_ORIG=__Z12em2bNeckMoveP5cEm2b` (pose, 16), `E2C_ORIG=__ZN5cEm2bD1Ev` (lifetime, 8), `OBA_ORIG=1` (object: obj20
hosted again, 11 with the push), `E2C_ORIG=__Z12em2bObaHitCkP5cEm2b` (hit check, 8). Logs: `E:\RE4DC-Lanes\eng-e2c\link\`.

## The PC check (hostref `svc/e2c_check.sh`, new)

The PC reference does not host El Gigante, so every group is exercised (`RE4_SVC_EXERCISE=e2cboss`, `svc/e2c_dump.cpp`)
as lane eng-e2a's e2geom was: at fixed ticks of bell-ganado (Leon and four Ganados) and hill-ashley (Leon and Ashley) a
giant is planted (a live actor's model header, so its parts are that actor's, and a cleared giant work) and the entry
points are called; odump links the original (`prep.py copyg`: em2b.cpp's register-keeping barriers widened from "r" to
"g" for i386, no code), native the engine bodies. The boundary log e2c.txt is compared by lane eng-e2a's
`e2_compare.py`, unchanged; outcome.py and plays_right.py compare the two traces. Requests the entry points make are
logged by --wrap (QuakeExec, SndCall, MotionSetCore, SetChain, the chain object's setChain and setParent) and through
hooks in the existing wrappers (EstSet in e2_dump.cpp, PenClothSet in svc_dump.cpp); the motion set-up, the chain object
and the cloth set-up are not run on a planted giant. Harness devices, both builds alike: the projection the on-screen
test asks for is the file's own (the reference's native build has none: below); the giant's virtual table is a strong
empty table (its entries would pull all of em2b into the link; the destructor only stores its address).

Final run (`E:\RE4DC-Lanes\eng-e2c\ev\e2c-g5e\`): bell-ganado 22,187 of 22,187 lines identical; hill-ashley 47,306 of
47,306 within the bound (27,101 identical; worst P 0.0079, R 0.0078: the escape camera's pull-in and the stamp camera,
from the two builds' camera, which differs by up to 0.002 unit there); outcome and traces PASS on both. Controls, each
FAIL: bosscam (event camera's eye 1% further: P 29.5), bossquake (nearest band 4500: R 2), bossneck (damping 0.85: A 2.47
degrees), bossblend (weight / 255: the weight's bits), bossheld (the third chain kept: 3 lines), bossoba (ground clamp
1500: P 1,778), bosspush (2900 apart: P 100), bossrope (rope iterations 99: 6 lines).

What the exercise reached (native log, bell-ganado / hill-ashley): event cameras 91 / 191 of each kind, the escape
camera's pull-in 0 / 191 (both branches), quake requests 1,456 / 3,056 (from 1,274 / 2,674 direct calls and the feet's), foot
calls 728 / 1,528 over the 32 combinations (landing or not), on-screen tests 11,111 / 23,982 (in and out of the window, behind the eye),
neck turns 1,080 / 2,280, blends 180 + 180 / 380 + 380, squashes 29 / 62 (with the routine tests that do not squash),
destructor rows 5 / 11, oba objects 4 (on a part, on an origin, alone, on a parent released at tick 70: released with
it) moved 811 / 1,711 times, pushes 135 / 285 moved, set-ups of every form and room 224's manager with and without one.

Found: in the PC reference's native build `GetScreenPos` answers the picture's centre for every point:
`GXGetProjectionv` (host_math.cpp) returns the last `GXSetProjection`, which the native camera service never calls. The
image is not affected (boss/boss_stubs.cpp computes the projection from the camera); any PC check of a screen test on the
native build reads nothing (for the integrator: sce_at's InScreenCheck in the fight image, cam_extra).

## How each group differs from the original

- **Presentation and view** (`services/boss/em2b_pres.cpp`: em2bBlowCamMove, em2bStampCamMove, em2bEscapeCamMove,
  em2bParasiteAtkCamMove, em2bQuakeSet, em2bFootSe, em2bInScreenCk). An event camera is an eye and a target placed in
  Leon's frame (cam_math.h frame_point, SH4ZAM types) or blended from the game camera, finished in one place (up, the
  distance, the frame by the camera service's CameraSetOrientationUp, the controller's extra-camera slot); no
  PSMTXMultVec, no PosToPos at rate 1 (the escape camera takes the points themselves), the pull-in is 250 short of the hit
  along the unit line (no VECNormalize / scale / add chain). The quake's strength is a table of distance bands. A foot
  landing is a table row (foot part by sound key, the mirrored motion an exclusive-or) and the same requests to the sound
  entry point (stays a call), the effect setter and the quake. The on-screen test asks the camera's projection for the
  root part and tests a window 300 wider on every side, written so a comparison with no answer counts as inside, as the
  original's chain of returns does.
- **Pose** (`services/boss/em2b_skel.cpp`: em2bNeckMove, em2bBlendMotSet, plBlendMotSet, em2bScaleCompress). The watched
  part from a table of the three watchers; the damped angle applied through the skeleton's mailbox (the neck part's added
  rotation); the original's unused transform of the target's point and its unused hand-out of part 4 are not made. One
  blend set-up for both callers (the main and blended motion on the motion service, weight |rate| / 256, the hokan count,
  the sequence frame wrapping at the clip). The squash is the skeleton service's skel_compress_y (as em10ScaleCompress).
- **Lifetime** (`services/boss/em2b_life.cpp`: cEm2b's destructor, cEmTree's and cEmTorch's). The held objects are one
  table of the work's slots, each released through the object pool when alive; the original released a tentacle without
  the alive test (the engine's pool refuses a dead record and counts a bad free, which fails a scene). The tree's and the
  torch's destructors are empty in the original (one `rts`, from the object) and the engine's: no PC row for these two (the
  object's disassembly is the evidence).
- **Object** (`services/boss/oba_obj.cpp`: SetObaModel, cObjObaModel::move and its implicit destructor; game/obj20 not
  hosted). The object on the object pool, the core archive's empty model through the model service, its cylinder an
  actor volume; the follow is the parent part's frame applied to the offset with the ground clamp, by kind in a switch.
- **Hit check** (oba_obj.cpp: em2bObaHitCk). Walks the character pool's slots, keeps this giant 3000 from each other
  giant in battle on the ground plane (unit line by SH4ZAM, no VECNormalize), the skeleton re-places its parts.
- **Set-ups** (`services/boss/em2b_setup.cpp`: em2bClothSet, em2bShortRopeSet, em2bChainSet, em2bTexrenderInit). Each
  pendulum chain is a row of one table of chain descriptions (the engine's copy of the original's data) written whole into
  the work's chain record; the three arm chains are one loop. The requests are the original's in the same order:
  PenClothSet (a logged stub in the boss image), SetChain and the chain object's setChain / setParent / setParent2 (logged
  stubs: the chain object kind is not in the boss image), Ctrl12GetTexRenderEm2b (a stub: none; refused and counted).

## Existing suites (PC, on the merged head 1858344ad: `E:\RE4DC-Lanes\eng-e2c\ev\suites-final\`)

svc_controls 79 rows, camcheck, refctl, controls 18, outcome_controls 35, aim_check (its controls fail), e2check (lane
eng-e2a's 14 rows) and e2c_check: every row as it must.

## Flycast function check (plain Flycast, slot std2: dynarec on, SH-4 200 MHz by default; no speed claim)

Two test discs with the repository's build_console_disc.sh, scenes BOSS-BENCH and BOSS: B0 from the lane's start
(ce7fd1a44) and B1 from its head (1858344ad); both deleted after their runs (`cdisc\DELETED.txt`).
- Both: 2 of 2 scenes OK under the strict selector; BOSS 600 rows, disc in play 0 opens / 0 reads / 0 sectors, camera
  tracks converted in play 0, `E1 POOL full 0 bad_frees 0`.
- The BOSS scene's behaviour against the start (engine against itself, `s\cmp_boss.py`, addresses of load buffers
  masked: the image grew): the 66 effect requests with their ticks, the 112 E2 lines (tasks, room, hidden scroll pieces
  with their ticks), the 75 stub lines and the pool line identical. Only the Flycast tick figures moved (services p99
  7.54 to 7.53 ms; behaviour worst at tick 48 vs 76, 0.34 ms both), which are not claims.
- The boss bench: its four rows identical between B0 and B1 (C0 15.44 / 20.34 / 22.41, Flycast); the bench image does
  not contain this lane's code.
- The head's call counts in the 900-tick scene (`runs\e2c-counts-B1.txt`): blow camera 50 (the catch), quakes 11 (all
  requested), foot landings 10, neck turns 902, blends 117, oba objects 6 made and 5,406 moves, push tests 902 (no other
  giant: no push), the tree's empty destructor 1, rope chain asked 1 (the stub answers none), screen tests 0, squashes 0,
  giant released 0 (the giant does not die in the window).
- Not run: a control for this engine-against-itself comparison (an image whose behaviour moves, for example eng-boss's
  BOSS_EXTRA=-DE1_CONTROL_SHIFT=1, must make it differ); the PC check is this lane's control-backed evidence.

## Stubs

None added. The set-ups keep calling the existing logged stubs (PenClothSet, SetChain, cObjChain::setChain, setParent,
setParent2, Ctrl12GetTexRenderEm2b, QuakeExec); the image's report gains three `E2C BOSS` lines with every native entry
point's call count (Flycast counts below).

## Not done: the room's thunder (r119_ThunderMove, r119_ThunderFlagOn, r119_ThunderFlagOff)

1. **They cannot be replaced by symbol.** The three are `static` in r119.cpp; R119Init passes the task by its section
   (`.text._ZL16r119_ThunderMovev`), not by a symbol, so weakening does not redirect it. A way that edits no source: the
   r119 object compiled with a force-included `asm(".weak __ZL16r119_ThunderMovev")` (and the two callbacks), so the
   assembler keeps the references symbolic and an engine body takes their place. That is a new build mechanism: it needs
   the integrator's OK.
2. **The generator.** ThunderMove draws its interval (240 to 385 ticks) from Rnd, the behaviour generator, in the old port
   and in this image, from the task's first run (tick 1). Presentation must draw from the engine generator; moving the
   draws shifts the boss's behaviour stream from tick 1 against the old port's reference. Ruling wanted: move it (and
   accept the boss's plays-right drift, judged by outcome) or keep the timer as the room script's decision (a "+" reviewed
   line, its two light callbacks thin setters).
3. In this image the thunder's effect, sound and tool-state callbacks are already engine stubs (EstSet recorded,
   SceSndCallThunder and EffSetToolStateCallBack empty): FlagOn / FlagOff are never called.

## Drawing El Gigante in the hosted scene: what it would need (not done; waits for the renderer redesign)

1. A draw record for the hosted giant in the actor pass (the catalogue's model 6, as the bench draws it), skinned from the
   native skeleton's palette (64 bones; the renderer's 384 weight sets a model, raised by eng-boss), at the owner's chosen
   body level (g50 recommended by eng-boss).
2. A live pack for r119: the room's world and visibility, El Gigante's and Leon's chapter-2 models, without the bench's
   recorded matrices and streams (bake/boss_pack.py in a live mode).
3. The BOSS scene drawn (no HEADLESS), the scroll-object table (boss_stubs.cpp e2_smd_hidden) read by the world pass so
   the destroyed hut and roofs disappear.
4. The rope between the neck parts: a chain object kind and the cloth service in the boss image (both stubs today:
   SetChain answers none); request to lane eng-svcspd1 for the cloth entry points.
5. Trees (a GameCube texture without a static identity: refused by the bench), torches, hut debris, the handgun (lane
   eng-look1), foot shadows (Em2b_fs_tbl is a table no one draws).
6. Effects: requests are recorded, none drawn (dust, quake shake, hut-break sheets); each to be added on its own budget.
7. The budget: the bench's El Gigante drawing is over the 14 ms row (eng-boss, MODELLED uncalibrated: 19.98 mean / 25.41
   worst full body, 18.36 / 22.49 g50); the hosted scene would add the live skinning and the world: lane eng-draw1's
   options first.

## Item 1: the 26 functions, classified (before any code change)

Call sites are from the hosted objects' relocations (`sh-elf-objdump -dr` of the boss image's em2b, obj20 and r119
objects): every em2b function below is reached through its global symbol (no inlined copy in a caller), so an engine
body of the same name replaces it when the hosted copy is made weak. The r119 functions are `static` and their callers
name their sections, not symbols (see the thunder row).

| Function | Bytes | Callers (hosted) | Class | Where it goes |
|---|---:|---|---|---|
| em2bBlowCamMove | 248 | plem2b_CatchHand, plem2bDmBlow | presentation (the catch / blow event camera) | engine composition of the event camera; frame by the camera service (CameraSetOrientationUp), the controller's extra-camera slot |
| em2bStampCamMove | 304 | plem2b_dm_Stamp | presentation (event camera) | as above |
| em2bEscapeCamMove | 560 | plem2bDashEscape | presentation (event camera pulled in to a scenery hit) | as above; the line of sight through the collision service (EatMgr) |
| em2bParasiteAtkCamMove | 324 | plem2b_AtkParasite | presentation (event camera) | as above |
| em2bQuakeSet | 176 | FootSe, Kick, Punch, Stamp, HouseBreak, ScrollBreak | presentation (camera quake scaled by the camera's distance) | quake setter (QuakeExec: an engine stub today, counted) |
| em2bFootSe | 296 | cEm2b::move | presentation (foot sound, dust, quake, chain rattle) | sound entry point (SndCall, stays a call), effect setter (EstSet), the quake above |
| em2bInScreenCk | 112 | em2bAtkRtnCk, em2bAtkRtnCkDebug | view (root part on screen; feeds the attack choice) | the camera's projection (GetScreenPos, the math service) |
| em2bNeckMove | 280 | cEm2b::move | skeleton (the head's damped turn to the target) | skeleton mailbox: part 3's added rotation |
| em2bBlendMotSet | 204 | em2b_R1_Walk, em2b_R1_Stamp | skeleton (two-motion blend set-up) | motion service (MotionSetCore), the model's blend work |
| plBlendMotSet | 184 | plem2b_Strangle | skeleton (the player's neck-motion blend in the strangle) | motion service, as above |
| em2bScaleCompress | 172 | cEm2b::move | skeleton (the dying body squashed vertically) | skeleton service (skel_compress_y, as em10ScaleCompress) |
| em2bClothSet | 260 | em2b_R0_Init (type 1) | cloth (the chained form's arm cloth set-up) | cloth service (PenClothSet: a logged stub in the boss image) |
| em2bShortRopeSet | 380 | em2b_R0_Init (type 0: this arena's giant) | cloth and object (the rope chain object between the neck parts) | chain object (SetChain: a logged stub) and cloth service |
| em2bChainSet | 668 | em2b_R0_Init (type 3) | cloth and object (three arm chains) | as above |
| em2bObaHitCk | 336 | cEm2b::move | hit check (pushes this giant 3000 from another live giant) | hit geometry on the engine's character pool |
| em2bTexrenderInit | 152 | em2b_R0_Init | drawing (room 224's texture-render manager; returns at once elsewhere) | renderer (none yet): refused and counted outside room 224 too |
| cEm2b::~cEm2b (D1 204, D0 12) | 216 | the pool (virtual destructor) | lifetime (releases the parasite, tentacle and chain objects) | the pool |
| cEmTree::~cEmTree | 4 | the pool | lifetime (empty) | the pool |
| cEmTorch::~cEmTorch | 4 | the pool | lifetime (empty) | the pool |
| SetObaModel | 300 | em2b_R0_Init (six leg volumes), em2b_R1_Die_Event | object (an invisible collision model following a parent's part) | object pool, model service, actor volumes |
| cObjObaModel::move | 320 | the object table's move | object (follows the parent, collision update) | as above |
| cObjObaModel::~cObjObaModel | 4 | the pool | lifetime (empty) | the pool |
| r119_ThunderMove | 200 | R119Init (scenario task) | presentation (thunder every 240 to 385 ticks: effect and sound requests); draws Rnd on the behaviour generator | see the note below |
| r119_ThunderFlagOn | 156 | ThunderMove (tool-state callback) | presentation (two hut lights brightened) | light table setters |
| r119_ThunderFlagOff | 76 | ThunderMove (tool-state callback) | presentation (the two lights back) | light table setters |

Note on the thunder: the three functions are `static` in r119.cpp and R119Init passes the task by its section, so an
engine body cannot take their place by symbol (as em2b's can) without a change to how r119.cpp is compiled. Its
interval draws are on the behaviour generator in the old port and in this image; moving them to the presentation
generator changes the behaviour stream from the task's first run (tick 1). Both points go to the integrator before the
group is touched.
