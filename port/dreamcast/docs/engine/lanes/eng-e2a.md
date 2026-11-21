# Lane eng-e2a: the fight image's original service code made native (step 3, pass E2)

Status: **finished, unaudited** for items 1 to 3; items 4 and 5 not started (the brief's stop rule: hand back after item 3
when the list is long). Branch `lane/eng-e2a`. Every number here is the PC reference (hostref) or Flycast (plain build,
slot std2, function checks); none is a timing. Write-up of the services: SERVICES.md section 49.

## Link check, service functions per image

| Image | Before (cc3d39e6a, H-017) | After item 1 | After item 2 | After item 3 |
|---|---:|---:|---:|---:|
| default | 0 | 0 | 0 | 0 |
| SENDABLE=1 | 0 | 0 | 0 | 0 |
| FIGHT=1 | 114 (42,156 B) | 95 (31,448 B) | 80 (30,088 B) | 73 (28,500 B) |
| BOSS=1 | 57 | 41 | 26 | 26 |

Left in FIGHT=1: em10 40, sce_at 18, cam_extra 6, game 3, libgpu 3, sce_com 2, r101 1. Link controls (each fails):
`EMSUB_ORIG=EmYarareDisp` and `EMSUB_ORIG=PlBombHitCk` (em_sub 1), `DMG_ORIG=1` (dmg 16, the tick at its ceiling of 0),
`AREA_ORIG=1` (area 7).

## Item 1: em_sub's hit geometry (19 functions), `services/aim/em_hit.cpp`

How it differs from the original:
- A hit box is read once into a world volume (the part's frame on SH4ZAM types through `camera/cam_math.h`; the capsule's
  ends and radius, or the box's anchor) instead of rebuilding points per test through the SDK matrix calls.
- Line against capsule: no rotation matrix to the axis (the original builds one from acos and an axis rotation, then
  inverts it); the along / across split is a dot product with the unit axis, each end sphere's entry and the side's
  point come from the nearest approach (no difference of large squares). The game's definition is kept on purpose
  (SERVICES.md 49.1): the side point h back along the segment, and an axis within 0.01 rad of vertical taken as vertical.
- Line against box: slabs in the box's own coordinates (the axes' adjugate, relative to the frame's position) instead of
  six quads with a plane and four edge cross products each; a mirrored frame takes the exit, as the original's face rule
  does there.
- Quad: one plane and four edge signs in a loop, the crossing from a (the original normalises the normal and crosses
  from b).
- Sphere touches: the volume service's existing tests (AtSphereCapsuleCk, At_box_sphere_ck); the facing choice written
  as one replacement rule.
- Damage position: the hit's coordinates by the frame's adjugate inverse (identity when singular), the across part
  scaled to the radius and the along part held to the length; no matrix inverse call.
- Attack, line-attack and blast compositions call the hosted decisions; their inline decision statements are listed in
  SERVICES.md 49.2 and the originals held at a ceiling of 0.
- Blood: the place computed, then the effect service's setter (EstSet); no effect drawing moved. The scatter (rnd) draws
  from the presentation generator; the fight never asks for it (0 calls on every fixture).
- Debug boxes and the attack sphere's debug drawing: counted, nothing drawn.

Check (`hostref/svc/e2check.sh`, PC): six fixtures within the bound (all lines); exercise e2geom bell-ganado 27,135 of
27,136 lines within the bound and 1 by the double-precision rule, hill-ashley 58,098 of 58,106 and 8 by the rule (the
engine at most 0.0018 from the double-precision answer, the reference up to 0.057); outcome and traces PASS. Controls:
hitwide, dmposmid, sphereshort, hitnudge FAIL. The fixtures' own play reaches only CheckInWater, EmYarareDisp and
EmDmBloodSet2: every other entry point is covered by the exercise only.

## Item 2: the damage volumes (15 functions), `services/volumes/dmg_vol.cpp`

How it differs: the table on the engine pool (`pool.h`, a refused double free or full table counted, as cEm / cObj);
records built in place; the tick frees released records in the same tick (the original over its next two sweeps); point
tests as a height band and a ground radius, or the math service's quad test; DmgMgr constructed by the engine file (the
hosted object's static initialiser removed). `set` and `beginEvent` stay hosted.

Found: the fight image never made DmgMgr's table nor ticked it; every registration was refused, so no Ganado was ever
knocked over by another's crash (em10SetCrash / em10CrashCk, kind 3). The PC reference makes 20 records and ticks them
after the camera. Fixtures it changes: bell-ganado-clear (13 registrations on the PC); any engine run where a Ganado
dies near another (FIGHT, SHOT). Now made at room load (`fight/fight_e2.cpp`) and ticked after the camera
(`fight/fight_trace.cpp`). Check: fixtures within the bound with the table logged after every registration and tick;
control dmgwide FAILs.

## Item 3: the scenario areas (7 functions), `services/volumes/area_vol.cpp`

How it differs: the quad test as two opposite corner wedges through the camera's ground-edge test (`camera/area_edge.h`,
now shared with `cam_eval.cpp`; the sign of the product difference equals the original's product comparison, so the
flags are bit-exact); the cylinder by an exact root as the original; the inside point as two lerps at the same two
behaviour draws; the default area by one table of corner signs. game/area is not hosted in the fight image. The view
check's cone test stays the image's generated stub (0), as before. Check: area rows of the exercise (60 records, 2,940
point tests, centres, inside points, view checks with the cone's question) within the bound; control areawide FAILs.

## Item 4 (not started): em10's 40 service functions, classified

| Function | Class | Where it goes |
|---|---|---|
| Em10SetSeTbl, em10WepSeEffSet | presentation (sound and effect tables) | sound / effect setters |
| em10BreathSe, em10CallVoiceSe, em10CallVoiceSe2, em10CsawSignSe, em10SetDamageVoice | presentation (voices, breath, chainsaw sound; already on the presentation generator) | sound setters |
| em10BehindSeCk | presentation (a voice when behind the player) with a turn test; draws Rnd on the behaviour generator in both builds today | sound setter; the generator split needs a reference change with its control |
| em10BloodSet, em1cBloodSet | presentation (blood choice, already split) | effect setters (EstSet), no drawing |
| em10FootSe, em10KickHitMark, em10SetDmWaterEff, em10SetWaterEff | presentation (footsteps, hit marks, water) | sound / effect setters |
| em10CamMove, em10CamMove2, em10CamMoveAshley, em10CamMoveCri, em10CamMoveTakeaway, em10SetCampos2 | presentation (the camera during grabs and kicks) | camera service entry points |
| em10NeckMove, em10BombNeckMove, em10WaistMove, em10BowgunMove, em10ClawMove, em10GatlingRollMove, em10MouthPartsReset | skeleton work (bone turns and part poses; claw and gatling also start a sound) | native skeleton service |
| em10BlendMotSet | skeleton (motion blend set-up) | skeleton / motion service |
| em10ChainSet, em10BeltSet | skeleton (cloth chains) | cloth service |
| em10ModelInit, em10SetAccesory, em10HandSet, em10HeadSet, em10ClothPartsSet, em10GoodsPartsSet, em10SackSet | skeleton / model (accessory parts, model info swaps; HeadSet draws Rnd for the head variant) | model service |
| em10ScreenInCk | view (on-screen test) | camera service |
| cEm10::~cEm10 | lifetime | the pool |

## Item 5 (not started)

sce_at 18 (item models and effects, areas, ladder positions, on-screen checks), cam_extra 6 (the binocular widget and
focus blur: drawing), game 3 (save), r101 1 (the Ganado voice call), sce_com 2 (debug), libgpu 3 (primitive lists).

## Stubs

None added. The view-cone test (geometry.cpp) is the fight image's existing generated stub.

## Flycast function check (plain Flycast, slot std2: dynarec on, 200 MHz by default; function checks, no speed claim)

Test discs from 81686c67e (deleted after their runs, notes in the lane folder's cdisc\DELETED.txt):
- A1 (LEON, HILL, FIGHT, FIGHTS, HILLT): 5 of 5 scenes OK under the strict selector (600 rows, 0 disc access in play,
  PUB 0, POOL full 0 bad_frees 0). FIGHT: E2 EMHIT water 2,428, dmpos 5, bloods 5 (scatter 0), every other entry 0;
  E2 DMG table 20 records, 6,204 tests, 0 hits (no Ganado died in the scene, so no crash volume); E2 AREA 1,773 tests,
  23 inits, eye tests 0. hill_engine.py: every row as it must (Leon and Ashley 729 of 729 ticks; its control FAILs).
- FIGHT stills against lane eng-e1p's A2 (picdiff.py, threshold stated before: 0.5% of pixels over 32, mean 1.0): 23
  pairs, 0 moved. Stated before the run: stills could move only after a Ganado's death (the damage table); none died.
- B1 (SHOT, SHOTNP, SHOTDMG, SHOTLATE): 4 of 4 OK; shot_engine.py: 4 scenes as they must (SHOT the reference's life
  drop at tick 162, 800 -> 500; the three controls FAIL).
