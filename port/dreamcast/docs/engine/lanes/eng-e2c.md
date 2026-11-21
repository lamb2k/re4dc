# Lane eng-e2c: the boss image's remaining original service code (step 3, pass E2)

Status: **in progress**. Branch `lane/eng-e2c` from `lane/eng-e2a` ce7fd1a44. Every number here is the PC reference
(hostref) or Flycast (plain build, function checks); none is a timing.

## Start (BOSS=1 built from ce7fd1a44)

Link check: 499 original functions kept, 26 service functions (5,936 B): em2b 18, obj20 3, r119 3, emtree 1, emtorch 1.

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
