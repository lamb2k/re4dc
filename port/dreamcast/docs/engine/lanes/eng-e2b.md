# Lane eng-e2b: the Ganado's own service functions (step 3, pass E2, continuing lane eng-e2a's items 4 and 5)

Status: **finished, unaudited** for item 1 as far as it can go without lane eng-svcspd1 (30 of em10's 40 functions
native; the 9 skeleton and cloth functions wait for that lane's entries); items 2 to 4 not done (the brief's stop rule:
hand back after item 1). Branch `lane/eng-e2b`. Every number here is the PC reference (hostref) or Flycast (plain
build, function checks); none is a timing. Write-up of the service: SERVICES.md section 50.

## Link check, service functions per image

| Image | Before (ce7fd1a44) | After |
|---|---:|---:|
| default | 0 | 0 |
| SENDABLE=1 | 0 | 0 |
| FIGHT=1 | 73 (28,500 B) | 43 (13,128 B) |
| BOSS=1 | 26 | 26 (not touched: lane eng-e2c) |

Left in FIGHT=1: em10 10 (em10NeckMove, em10BombNeckMove, em10WaistMove, em10BowgunMove, em10ClawMove,
em10GatlingRollMove, em10MouthPartsReset, em10ChainSet, em10BeltSet; and Em1fClothSet, see "Found"), sce_at 18,
cam_extra 6, game 3, libgpu 3, sce_com 2, r101 1. Link control: `EM10_ORIG=<name>` keeps that original linked (the
engine's copy made weak): `EM10_ORIG=_Z10em10FootSeP5cEm10` FAILs (em10 21 functions).

## Item 1: em10's 40, as classified by lane eng-e2a (docs/engine/lanes/eng-e2a.md, item 4)

| Class | Functions | Where now |
|---|---|---|
| presentation: sounds and voices | Em10SetSeTbl, em10CallVoiceSe, em10CallVoiceSe2, em10BreathSe, em10CsawSignSe, em10SetDamageVoice, em10BehindSeCk, em10FootSe, em10WepSeEffSet | `services/em10/em10_pres.cpp`: calls to the sound entry points (SndCall, SndStop, Ctrl11*), the weapon's setters |
| presentation: effects | em10BloodSet, em1cBloodSet, em10KickHitMark, em10SetDmWaterEff, em10SetWaterEff | `em10_pres.cpp`: the effect service's entry points (EstSet, EmDmBloodSet2, EspGetEstAddr, EspEstSetSelect); no effect drawing |
| presentation: camera | em10CamMove, em10CamMove2, em10CamMoveAshley, em10CamMoveCri, em10CamMoveTakeaway, em10SetCampos2 | `em10_cam.cpp`: one cut-in routine; the camera service frames it (CameraSetOrientationUp) and shows it (CamCtrl.m_pExtraCamera) |
| view | em10ScreenInCk | `em10_cam.cpp`: the math service's projection (GetScreenPos) |
| model | em10ModelInit, em10SetAccesory, em10HandSet, em10HeadSet, em10ClothPartsSet, em10GoodsPartsSet, em10SackSet | `em10_model.cpp`: the model service (ModInfoMgr.create, addModel, swapModelInfo), the object factory (SetObj12) |
| motion | em10BlendMotSet | `em10_model.cpp`: the motion service (MotionSetCore) |
| lifetime | cEm10::~cEm10 (D0, D1, D2) | `em10_model.cpp`: the owned objects back to EmMgr / ObjMgr (the engine pool) |
| skeleton and cloth | em10NeckMove, em10BombNeckMove, em10WaistMove, em10BowgunMove, em10ClawMove, em10GatlingRollMove, em10MouthPartsReset, em10ChainSet, em10BeltSet | not moved: the skeleton has no entry to set a bone's added rotation, pose angles, scale or to post-multiply its local matrix (requests below) |

### How each rewritten group differs from the original

- **Sound numbers and voices:** a voice kind is one row of a 4 x 19 table copied in one move (the original: four
  switch arms of 19 stores); a model type's voice bank is a 26-entry table (the original: a 26-case switch); the voice,
  second voice, breath and damage voice share three helpers (stop, rate, breath timer) instead of repeating the calls.
  The presentation draws are the engine generator's `eng_pres_u8` in the original's order (the split images already
  drew them there through the e1_present section).
- **Chainsaw tell, "behind you":** the conditions as one predicate each (NaN-safe as the original's early returns).
  em10BehindSeCk's breath timer still draws the behaviour generator (see below).
- **Footsteps:** one row per step number (sound, foot part, chain rattle) for the village and the claw types, the claw
  types' landing sounds as a two-entry table; the original is two switches with the calls in each arm.
- **Weapon sound set:** one row per weapon kind (none, hit, fall, throw) for the 17 kinds; the original is a switch with
  the seven setter calls repeated in five arms.
- **Blood:** a weapon id is a class by one 46-entry table per variant (em10, the parasite-headed em1c) and one choice
  of effect by class, armour, range, water and the big-effect lock; the original is two nested switches per variant with
  the water / range / lock choice written out in each arm (about 100 EmDmBloodSet2 calls). The blast's sprites take the
  hit part's frame inverse from `camera/cam_math.h` (adjugate) instead of PSMTXInverse; their part number is the part's
  low byte less one (the original reads byte [1] of the big-endian s16, which on a little-endian machine is the high
  byte: unreachable in both builds, EspGetEstAddr is a stub in the fight image and the PC reference).
- **Cut-in cameras:** one routine (`cut_in`: ease from the game camera by the math service's PosToPos, shake, the
  wall pull through the effect collision's line test, framing, hand-over) and a table per shot family (the critical
  hits with their second region form, the hold on Ashley, the grab's two eyes, the take-away); the original is six
  functions with the ease, wall pull and framing written out in each. Points through a frame are SH4ZAM vectors
  (`frame_point`), not PSMTXMultVec. The shake is three presentation draws an axis as fRand1_1 forms them.
- **Screen check:** a loop over the root and the head.
- **Model parts:** one wear routine (model info made, swapped in or added); the accessories are rule tables per body
  group (flag bit, two model files as a motion-table slot or an archive entry, destination, the head hidden, a hung
  object's kind and place), applied in order; the hands a pose table with the grip and mirror rules; the original is a
  switch per group with each accessory written out through two macros. em10GoodsPartsSet does not write through a
  refused model info (the original does).
- **Blend:** the same two motion-service calls with the choice made once.
- **Destructor:** the owned objects given back through one template in the original's order (the pool's free order
  decides later slots).

### Draws on the behaviour generator kept as they are (a reference change would be needed, H-016.8)

| Function | Draw | Today | What a move to the presentation generator needs |
|---|---|---|---|
| em10BehindSeCk | `Rnd() % 120` (the breath timer after the call) | behaviour, both builds | the PC reference splitting it (hostref PRESENT_EM10 gains em10BehindSeCk's own draw: its native body would draw `eng_pres_u8`), with EM10_SPLIT-style control build and a refctl row; outcome must hold (the draw shifts the behaviour stream by one per call) |
| em10HeadSet | `Rnd() & 3` (the bent-neck head) | behaviour, both builds | the same; the head variant is a look, not a decision, but the draw changes every later behaviour draw |
| em10SetCampos2 | `Rnd() & 1` (the throw-off eye's side) | behaviour, both builds (not in the split list) | the same |

## The split: em10's bodies weak, and no copy left in a caller

em10.o is compiled from `src/` unchanged; the engine's 30 functions are linked by making em10's own bodies weak
(`game/fight.mk` EM10_NATIVE; the PC reference: `hostref/svc/svc.mk` WEAK_em10). That only works when every call reaches
the global symbol. Under the default -O2 GCC had partially inlined or fully inlined em10NeckMove, em10ClawMove,
em10GatlingRollMove, em10HandSet, em10MouthPartsReset, em10ClothPartsSet, em10GoodsPartsSet and em10SackSet into decision
functions (cEm10::move, the damage and event routines, em10ModelInit, em10_R1_Trade): 181 reports
(`E:\RE4DC-Lanes\eng-e2b\ev\em10-default-flags-split-check.txt`). Those copies were inside allowed functions, so the
link check could not see them. em10.o is now compiled with the interprocedural optimisations off (EM10_NOIPA:
no inlining of non-inline functions, no partial inlining, no clones, no IPA register allocation, pure/const, mod-ref,
value range or ICF), and `game/em10_split_check.py` refuses the object when the compiler's own report
(-fopt-info-inline-optimized) shows an inlining of any of the 40, a clone of one exists, or a listed symbol is not weak.
Control: `EM10_IPA=1` (the old flags): FAIL, 8 clones. em_sub.o and dmg.o (lane eng-e2a's weakened units) showed no
inlined copy of their weakened functions (checked the same way); they get -fno-ipa-ra.

## The PC reference change (H-016.8): em10SetDamageVoice's voice

`src/em10/em10.cpp` 362-367 declares an int view of em10CallVoiceSe for em10SetDamageVoice with the label
`asm("_em10CallVoiceSe")` on non-PowerPC targets: on the SH-4 that is em10CallVoiceSe's own symbol, so the console
image voices a living Ganado's hit. On the i386 PC the label is a different symbol, which `hostref/host_actor_stubs.cpp`
answered with a generated stub: the reference never voiced it. `hostref/Makefile` EM10_VOICE=1 binds the label to
em10CallVoiceSe (objcopy --redefine-sym on em10's object; the source unchanged); EM10_VOICE=0 is the old reference, a
control build only. Row in `hostref/svc/refctl.sh` (em10voice): the fixed reference voices the hit (C11s calls 1 on
bell-ganado-hit); the old one's e2b log against the fixed FAILs; the outcome PASSes (presentation only).

## Check (PC): `hostref/svc/e2bcheck.sh`

odump (em10's original bodies) and native (the engine's) on the same inputs, wind off:
- the boundary log `e2b.txt` (`svc/e2b_dump.cpp`): every call to the sound entry points (SndCall, SndStop, the ctrl11
  slots under both names, the ctrl12 locks) and the effect entry points (EstSet, EspGetEstAddr, EspEstSetSelect) made
  outside another service's logged call; at the start of every tick each live Ganado's presentation state (sound
  numbers, voice, breath and chainsaw timers, water and chain waits, hand pose, step number, model parts as pool slots
  with their flags, hung objects and weapons, cap kind, blend state, the work camera and its eye) and the extra camera;
  the live character and object record counts;
- the enemy hit geometry's log `e2.txt` (where the blood em10 chooses arrives as EmDmBloodSet2);
- `outcome.py` and `plays_right.py` on the traces.
Bounds: `e2_compare.py` (integers exact; positions and lengths within max(0.01 unit, 2^-20 of the value)), unchanged;
`--log NAME` added to read another log of the same form.

Rows: the six fight fixtures PASS; exercise e2b on bell-ganado and shot-ganado PASS (every function on planted inputs:
voice kinds on every model type, muted and not, the chainsaw near and far, "behind you", each step number on a village,
claw and flail Ganado, every weapon kind's sound set, every weapon id's blood with and without armour, near and far, on
the body, the head with the parasite out and the parasite-headed type, the kick mark, water, every cut-in shot and
region with and without shake, the take-away, the throw-off eye, the screen check against its rule, the hand poses and
grips, the head and lost head, the aiming blend, the village accessories, the destructor). Controls, each FAILs:
voicebank, bloodswap, footpart, camease, screenhalf, handgrip, accnone, keepcap.

The screen check is judged against its rule on each build's own projection: the PC native build's GetScreenPos
projects every point to the screen centre (256, 224) where the original's answers vary (`e2b-diag.txt`): the two
builds' projections cannot be compared (a request below).

### Not covered on the PC
- The wall pull's hit branch (no effect-collision piece in the village); the accessories of the zealot, soldier and
  gatling groups, the merchant's coat and goods and the sack (types the village has not; read against the source only);
  the blast's 0x88 sprites (EspGetEstAddr a stub); every water effect (CheckInWater 0 in the village).

## Flycast function check (plain Flycast, slot std2: dynarec on, 200 MHz by default; function checks, no speed claim)

Test disc A1 from 9d64cca3e (the code of the final head; deleted after its run, note in the lane folder's
cdisc\DELETED.txt): FIGHT, FIGHTS, FIGHTT, SHOT, SHOTNP, SHOTDMG, SHOTLATE, 7 of 7 OK under the strict selector.
shot_engine.py: 4 scenes as they must (SHOT the reference's life drop at tick 162, 800 -> 500; SHOTNP, SHOTDMG,
SHOTLATE FAIL). FIGHT stills against lane eng-e2a's A1 (picdiff.py, the threshold stated before: 0.5% of pixels over 32,
mean 1.0; prediction written before the run: none may move): 23 pairs, 0 moved, every pair 0.000% of pixels over 32 and
a mean difference of 0.000. Counters: E1 POOL full 0 bad_frees 0 in every scene; E2 DMG 20 records, 6,204 tests, 0 hits
(no Ganado dies beside another in these scenes). SetObj12 (the hung-object factory em10SetAccesory calls) is an
existing stub of the fight image (4 calls at spawn).

## Item 4 (not done): the knock-down on the engine
bell-ganado-clear on the PC reference registers 13 crash volumes (kind 3, radius 1,500, height 800) and tests them 1,405
times with 0 hits: no Ganado is knocked over by another's death in that fixture, so it cannot show the damage table on
the engine. A fixture with two Ganados within 1,500 units when one dies is needed first.

## Stubs
None added.

## Requests
- **eng-svcspd1 (skeleton, cloth):** skeleton entries for em10's skeleton work, each on a bone of an actor's table:
  (1) set a bone's added rotation (SK_RX..RZ) and its flag 0x40000000 (em10NeckMove, em10WaistMove); (2) post-multiply a
  bone's local matrix by a rotation about z (em10NeckMove's finger) and its world matrix by a rotation about y
  (em10BombNeckMove); (3) set a bone's pose angles (em10MouthPartsReset, em10BombNeckMove, em10HeadSet's neck tilt, today
  through getPartsPtr); (4) set a bone's scale (em10BowgunMove on the weapon's bones, em10BombNeckMove, em10ClawMove);
  (5) set a bone's pose position (em10ClawMove, em10GatlingRollMove). Cloth: a chain set-up entry taking the chain's
  description (links, parents, limits, collision set) for em10ChainSet / em10BeltSet and Em1fClothSet.
- **camera / math service owner:** GetScreenPos on the PC native build answers the screen centre for every point.
- **eng-e2c (boss units):** em2b's weakened functions may sit inlined in its decision functions as em10's did: build
  em2b.o with EM10_NOIPA-style flags and run game/em10_split_check.py's method on it.
