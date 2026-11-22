# Chapter 1 rooms through the engine's bake, and what each costs (lane eng-bake1, 2026-11-21)

Status: finished, unaudited. PC only: no emulator, no image, no pack-format change. Every number here is counted
from the baked data on the PC (tier: **count**, not a timing). Rooms are named by place where the project's
documents give a name; the others carry their room number only.

**In short.**
- Chapter 1 is 13 rooms; 12 have a world and all 12 bake (r120 is the intro movie). No bake failure is left.
- 3 rooms bake as **game packs** (village, farm, and the hill for comparison): they have a recording of the old game.
  The other 10 bake as **world packs** from offline data only: world, textures, sky, actor catalogue, visibility.
  They have no props, lights, HUD or effects, so they cannot go on a disc.
- Every pack passes the bake's checks, and every check fails on its control input.
- The 5 worst rooms for drawing, by the largest visible set: **the cabin (r109), the pool (r107), r105, r106 and the
  farm (r103)**. The cabin's largest view is 2.0 times the village's and 1.7 times the hill's.
  The model has the village drawing at 27 ms and the hill at 37 ms.
- Memory: every room fits its video-memory blocks as baked. In main memory the **farm** has 85 KiB left in its
  4,096 KiB room-pack block, before collision is added. Every other room has 631 KiB or more, but the world packs
  carry no props yet.
- Missing inputs: 10 rooms have no recording, so their props and recorded lights need a capture run of the old
  game (section 3).

## 1. The chapter 1 rooms and their bake inputs

**Which rooms.** Chapter 1 runs from the intro to the lake boss: the chapter ends in the room code
(`src/st1/r106.cpp:419` `SceSetChapterEnd(0, 3)`, door 3 to r104; `r105.cpp:650` `CHAPTER_1_2`; `r10b.cpp:359, 390`
`CHAPTER_1_3`, door 6 to r11b) and the door graph of the room archives
(`tools/d367/stage_route.py --stage 1 --exit r11b`, AEV door records read from the room archives; output kept in the
lane's evidence). In play order: r120 (intro movie, jumps to r100, `r120.cpp:99`), r100, r101, r103, r106 (1-1 end),
r104, r107, r105 (1-2 end), r102, r108, r109, r10a, r10b (lake boss, 1-3 end). Twelve rooms have a world; r120 has none.
The door graph also reaches r10e from r109 (door 3); the route documents count r10c and r10e as chapter 2-1 rooms,
so they are not in this list.

**What the bake reads, per room.** `room_bake.py --inputs` checks each:

| Input | Where | Offline? |
|---|---|---|
| World mesh and placements | `<disc>/native/rXXX/ps2-world.re4mesh`, `.r4pw` (`native_world.py:9-21`) | yes (converted PS2 data) |
| Strip groups | `ps2-world.r4sg` (optional, `native_world.py:23`) | yes |
| Sky | `ps2-sky.r4sk` (`native_world.py`, `pack_scene.py` Baker) | yes; a room with none now gets an empty sky |
| World textures | `<disc>/tex.pak`, keyed by the R4PW part keys (`pack_scene.py` `Baker.header`) | yes |
| Actor catalogue: Leon, five Ganado appearances, distance levels | `native/pl00`, `native/ganado`, the private static tables (`native_models.py`) | yes |
| Leon's cloth inverse binds | `leon-bind.bin` of a recording (`native_pack.py:44, 59`) | yes in effect: one file per costume (identical in the village and farm recordings; Leon's model data, not the room's) |
| Props (scenery models: barrels, carts, ...) | `extra-models.json` plus a RAM snapshot of the old game (`native_pack.py:47-53`, `native_extra.py:8`) | **no**: needs the old game's relocated room archive in RAM |
| Lights, Leon's light record, environment (fog, ambient), HUD layout | the first recorded picture, streams 2, 8, 7 and 5 (`core/draw_e1.c:3-4`, the E1 image's only use of the logic streams) | lights and fog: partly (the room's LIT cuts); the rest no |
| HUD digit pictures | a RAM snapshot (`hud_fix.py:181-185`) | yes in effect: the HUD is the same in every room; any snapshot serves |
| Camera seeds for the visibility | the recorded cameras (`bench/bake_vis.c:464-468`) | yes: the room's entry points (this lane) |
| Room cast (enemy types beyond the Ganado) | `native/rXXX/registry.re4nmr` | present for every room, **not read by the bake** today |

Per room (`room_bake.py --inputs`, run 2026-11-22; the actor catalogue, Leon's binds and the textures file are present for every room):

| Room | Ch | World sidecars | Strip groups | Sky | Textures found (of the world's keys) | Room cast file | Entry points | Areas and items | Recording of the old game |
|---|---|---|---|---|---|---|---|---|---|
| r120 | 1-1 | no | no | - | - | no | 0 | - | **no** |
| r100 (the first house) | 1-1 | yes | no | yes | 55 of 55 | yes | 2 | 64 | **no** |
| r101 (village) | 1-1 | yes | yes | yes | 109 of 109 | yes | 4 | 68 | yes |
| r103 (farm) | 1-1 | yes | no | yes | 52 of 52 | yes | 2 | 41 | yes |
| r106 | 1-1 | yes | no | yes | 42 of 42 | yes | 1 | 40 | **no** |
| r104 | 1-2 | yes | no | yes | 55 of 55 | yes | 2 | 48 | **no** |
| r107 (pool) | 1-2 | yes | no | yes | 50 of 50 | yes | 2 | 33 | **no** |
| r105 | 1-2 | yes | no | yes | 147 of 147 | yes | 2 | 54 | **no** |
| r102 | 1-3 | yes | no | no | 76 of 76 | yes | 2 | 27 | **no** |
| r108 (river) | 1-3 | yes | no | yes | 72 of 72 | yes | 2 | 35 | **no** |
| r109 (the cabin) | 1-3 | yes | yes | yes | 35 of 35 | yes | 3 | 23 | **no** |
| r10a | 1-3 | yes | no | yes | 42 of 42 | yes | 2 | 28 | **no** |
| r10b (lake) | 1-3 | yes | no | yes | 53 of 53 | yes | 1 | 24 | **no** |
| r11d (hill) | 2-3 | yes | no | yes | 34 of 34 | yes | 2 | 47 | yes |

r120 has no world (intro movie). The input that depends on capturing the old port in an emulator is the **recording**. Every other input is produced offline.

## 2. What the bake truly needs from a recording, and what is now offline

`room_bake.py <room>` is the one command. With a recording it bakes the game pack as before
(`native_pack.build`, `hill_pack.build`). Without one it bakes a **world pack** in the same NAT3 format from offline
data only, and runs the visibility, the checks and the census on it.

Now offline (no recording needed):
- world, materials, textures, sky, actor catalogue, distance variants and the catalogue tail: the same code as the
  game pack. Check: for the three rooms that have both, the world section is byte-identical between the two packs
  (village, farm and hill: identical (1,423,328, 1,089,740 and 795,704 bytes); every world-pack texture is also in the game pack).
- the visibility seeds: `bake_vis` grows the reachable floor from the pack's cameras (`bench/bake_vis.c:464-468`);
  the world pack's cameras are the room's entry points (every door of the stage whose destination is the room, its
  `dstPos`, plus r120's jump into r100). Check: grown from the entry points alone, the table covers the recorded
  cameras of the village, farm and hill in baked cells inside their camera bands: village 300 of 300, farm 300 of 300, hill 300 of 300 recorded cameras.
- Leon's cloth binds: one file per costume, taken once (chapter 1: the village recording's, byte-identical to the
  farm's). It could be derived from Leon's model offline; not done.

Still needs a recording, and why:
- **Props.** `native_pack.py:47-53` reads `extra-models.json` (which room models were drawn) and
  `native_extra.py:8` follows the models' ModelData, TPL and joint tables through a RAM snapshot of the old game.
  No offline converter from the room archive's object models to the catalogue format exists in `bake/`. The world
  packs here carry no props.
- **Lights.** The room's LIT holds several cuts (3 to 20 a room, below); the cut in force follows the player's light
  area at run time, and effects add lights (fires, torches). The recorded light set of picture 1 is larger than the
  room's cut 0 in every room that has both (village 24 against 15, farm 22 against 11, hill 27 against 15). So the
  LIT gives the static lights offline, not the set the game image reads today (`core/draw_e1.c:3`).
- **Leon's light record and the environment** (streams 8 and 7): the light volume, masks and the room status the
  game had at that tick (`bench/r3_inputs.inc` `m1r3_snapshot_light`). Fog type, start and end are in the LIT
  (offline); the record as a whole is not.
- **HUD layout** (streams 5 and 6): the widget table of the running cockpit; the same in every room, so one
  recording serves all rooms, but the bake reads it from the room's own recording today (`native_pack.py:148-152`).
- **Effects and their texture headers** (stream 3): what the recording saw (`native_pack.py:136-144`).
- **Camera and actor poses** (streams 0, 1, 4): the bench's replay only; a game image computes them live.

## 3. What a recording must contain (to brief a recording lane)

For each room without one (r100, r106, r104, r107, r105, r102, r108, r109, r10a, r10b), the old game in Flycast with the capture build (`bench/r3_capture.hpp`,
`bench/r3_inputs.inc`, `bench/read_capture.py`), Leon in normal play in the room:
- `picture-001.bin` to `picture-300.bin`: 300 consecutive ticks of the room (`LOG3`, the room's number, sequence 1 to
  300, tick +1 each); every picture carries the camera, actor poses, the HUD and the environment
  (`native_pack.py:123-124, 161-162` refuses a gap or a picture without them);
- the HUD on screen with the handgun in hand in picture 1, so the ammo digits are there for the HUD fix
  (`hud_fix.py:107-111`);
- `leon-bind.bin` (Leon's cloth binds, per costume);
- `resource-ram-NNN.raw`, a RAM snapshot taken in the room (the HUD fix and the props read it);
- `extra-models.json`, the room models drawn, with their addresses in that snapshot (props);
- the lights of the room's main light area in force (enter the room through its usual door); for the lake, both the
  dock and the boat.
Not needed for the bake: stills, `picture-NNN.json`, `resources/` (the M1 path only).

## 4. Bake results

Run 2 (2026-11-21, bake at commit `c90c5d235`, `room_bake.py --chapter1`, 4 jobs). Packs, tables and logs are in `E:\RE4DC-Lanes\eng-bake1\packs` (not in git), with the receipt in `receipt.json` (`--check-receipt`: OK on 2026-11-22). The merge of `origin/engine` after the run changed no bake input (`render/native_world.c`, `bench/bake_vis.c`; `bake/` gained only `weapon_model.py`).

| Room | Pack | Pack bytes | HUD verify | Seeded floor | Offline seeds cover the recording | Census | Floor cells / reachable / baked | Seeds in a baked cell / inside its band | Bake failures |
|---|---|---|---|---|---|---|---|---|---|
| r120 | none | - | - | - | - | - | - | - | no world: intro movie, jump to r100 |
| r100 (the first house) | world | 3935580 | FAIL (expected: world pack) | PASS | - | PASS | 5949 / 3467 / 4106 | 66 / 45 of 66 | none |
| r101 (village) | game | 8971708 | PASS | PASS | PASS 300/300 | PASS | 3925 / 3414 / 4027 | 300 / 300 of 300 | none |
| r103 (farm) | game | 11298376 | PASS | PASS | PASS 300/300 | PASS | 3037 / 2270 / 2557 | 300 / 300 of 300 | none |
| r106 | world | 3538504 | FAIL (expected: world pack) | PASS | - | PASS | 6101 / 3380 / 3909 | 41 / 28 of 41 | none |
| r104 | world | 2722260 | FAIL (expected: world pack) | PASS | - | PASS | 1758 / 301 / 604 | 49 / 35 of 50 | none |
| r107 (pool) | world | 3065228 | FAIL (expected: world pack) | PASS | - | PASS | 2064 / 306 / 531 | 32 / 16 of 35 | none |
| r105 | world | 3449080 | FAIL (expected: world pack) | PASS | - | PASS | 6527 / 6337 / 6608 | 56 / 31 of 56 | none |
| r102 | world | 2837340 | FAIL (expected: world pack) | PASS | - | PASS | 638 / 580 / 707 | 17 / 4 of 29 | none |
| r108 (river) | world | 3011820 | FAIL (expected: world pack) | PASS | - | PASS | 16826 / 16583 / 16988 | 37 / 0 of 37 | none |
| r109 (the cabin) | world | 3286504 | FAIL (expected: world pack) | PASS | - | PASS | 880 / 802 / 905 | 17 / 3 of 26 | none |
| r10a | world | 3191112 | FAIL (expected: world pack) | PASS | - | PASS | 4467 / 1910 / 2405 | 29 / 16 of 30 | none |
| r10b (lake) | world | 3051324 | FAIL (expected: world pack) | PASS | - | PASS | 17752 / 2524 / 2930 | 23 / 10 of 25 | none |
| r11d (hill) | game | 7759260 | PASS | PASS | PASS 300/300 | PASS | 661 / 129 / 212 | 300 / 300 of 300 | none |

**Each check's failing input** (`room_bake.py --controls`, `controls.json`):

| Check | Failing input | Result | Detail |
|---|---|---|---|
| seeded_floor | r10a, every seed moved 1 km and 50 m up | failed as it must | ['visibility: no reachable cell from the seeds'] |
| census_world table/pack match | village pack with the farm's table | failed as it must | exit 4 |
| offline_seeds_cover_recording | village cameras against the lake's table | failed as it must | {'pictures': 300, 'in_cell': 0, 'in_band': 0} |
| hud_verify on a world pack | r10b world pack | failed as it must | HUD fix missing: 0 of 0 digit widgets linked to the PS2 digit pictures (run bake/hud_fix.py as the bake's last |
| receipt check | receipt with the village pack's hash changed | failed as it must | /mnt/e/RE4DC-Lanes/eng-bake1/packs/r101.pak |

The HUD verify links 3 digit widgets in each game pack. Re-bake against the kept packs: the hill is byte-identical to `hill2-hud.pak`. The village differs only in the world section (1,208 bytes smaller): the old port's 14 baked live-object placements are left out. The farm differs in its texture, header and HUD sections: the kept `FARM.PAK` lacks the HUD fix and fails the verify.

## 5. The census

Counted from the baked data on the PC (tier: count). Distance level 0 of the whole room. "Staged vertices" are the vertices the renderer stages for a view after the baked visibility and the frustum, at the default view (the village recording's first camera). The view figures are over every baked cell's eyes, not a play route; only the three recorded rooms have a route. "Room content" leaves out the recording's logic streams.

| Room | Place | Ch | Pack | Triangles | Vertices | Strips | Meshlets | Materials | Textures | VRAM world KiB | VRAM catalogue, HUD, effects KiB | Pack KiB | RAM at load KiB | RAM at load, room content only KiB | Lights: LIT cut 0 / most in a cut / recorded | GameCube-sourced texture rows |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r120 |  | 1-1 | none | - | - | - | - | - | - | - | - | - | - | - | 3 / - / - | - | <!-- intro movie, jump to r100 -->
| r100 | the first house | 1-1 | world | 91792 | 130903 | 30815 | 2348 | 304 | 63 | 778 | 507 | 3843 | 3469 | 3465 | 20 / 20 / - | 1 |
| r101 | village | 1-1 | game | 50165 | 80461 | 19703 | 1534 | 342 | 457 | 710 | 1499 | 8761 | 7352 | 3299 | 15 / 15 / 24 | 39 |
| r103 | farm | 1-1 | game | 42292 | 71856 | 17560 | 1293 | 267 | 183 | 773 | 1906 | 11034 | 9061 | 4011 | 11 / 11 / 22 | 46 |
| r106 |  | 1-1 | world | 62212 | 90725 | 22662 | 1627 | 164 | 50 | 940 | 507 | 3456 | 2686 | 2684 | 6 / 14 / - | 1 |
| r104 |  | 1-2 | world | 38499 | 59856 | 14345 | 1176 | 219 | 63 | 465 | 507 | 2658 | 2105 | 2101 | 14 / 18 / - | 1 |
| r107 | pool | 1-2 | world | 39930 | 61210 | 14514 | 1099 | 231 | 58 | 575 | 507 | 2993 | 2422 | 2419 | 13 / 32 / - | 1 |
| r105 |  | 1-2 | world | 47096 | 66855 | 15473 | 1361 | 335 | 155 | 1058 | 507 | 3368 | 2357 | 2353 | 24 / 24 / - | 1 |
| r102 |  | 1-3 | world | 23262 | 27223 | 5519 | 515 | 134 | 84 | 843 | 507 | 2771 | 1617 | 1615 | 30 / 30 / - | 1 |
| r108 | river | 1-3 | world | 49552 | 71786 | 17259 | 1294 | 229 | 80 | 498 | 507 | 2941 | 2579 | 2576 | 22 / 56 / - | 1 |
| r109 | the cabin | 1-3 | world | 43046 | 64658 | 15939 | 1126 | 147 | 43 | 685 | 507 | 3209 | 2468 | 2467 | 13 / 14 / - | 1 |
| r10a |  | 1-3 | world | 41469 | 62180 | 14529 | 1213 | 372 | 50 | 845 | 507 | 3116 | 2319 | 2317 | 11 / 11 / - | 1 |
| r10b | lake (lake boss) | 1-3 | world | 43215 | 61153 | 14232 | 1164 | 201 | 61 | 753 | 507 | 2980 | 2272 | 2270 | 17 / 17 / - | 1 |
| r11d | hill | 2-3 | game | 35239 | 56934 | 13552 | 1110 | 310 | 259 | 418 | 1109 | 7577 | 6386 | 2298 | 15 / 17 / 27 | 31 |

| Room | Place | Baked cells | Largest view: staged vertices / triangles | View p99 / p90 / p50 staged vertices | Mean view staged vertices | Largest view without the table | Largest PVS vertices / triangles | Mean PVS vertices / triangles | Recorded route: mean / largest staged vertices |
|---|---|---|---|---|---|---|---|---|---|
| r100 | the first house | 4106 | 19403 / 13055 | 14976 / 10939 / 2168 | 4155 | 19403 | 126979 / 88333 | 99969 / 69586 | - |
| r101 | village | 4027 | 14054 / 8227 | 10677 / 7141 / 619 | 2184 | 15035 | 78383 / 48965 | 64772 / 40464 | 7032 / 11461 |
| r103 | farm | 2557 | 19522 / 11293 | 15273 / 10524 / 866 | 3246 | 19720 | 70334 / 41376 | 63793 / 37365 | 12036 / 14864 |
| r106 |  | 3909 | 20667 / 13119 | 16527 / 9222 / 550 | 2586 | 21116 | 87644 / 60301 | 51049 / 34344 | - |
| r104 |  | 604 | 18430 / 11619 | 15594 / 9547 / 1081 | 2982 | 21513 | 56906 / 36175 | 34893 / 22194 | - |
| r107 | pool | 531 | 24439 / 15948 | 21064 / 13847 / 2106 | 4847 | 29638 | 59742 / 38925 | 33998 / 22298 | - |
| r105 |  | 6608 | 21799 / 13854 | 12336 / 4754 / 423 | 1462 | 29284 | 61724 / 43445 | 37768 / 26393 | - |
| r102 |  | 707 | 8390 / 8032 | 7158 / 5174 / 1003 | 1856 | 8456 | 26932 / 22950 | 22870 / 19439 | - |
| r108 | river | 16988 | 4341 / 3088 | 1748 / 544 / 56 | 193 | 4341 | 70118 / 48218 | 47946 / 32806 | - |
| r109 | the cabin | 905 | 28364 / 18401 | 20163 / 9327 / 5 | 2003 | 28364 | 64658 / 43046 | 64571 / 42990 | - |
| r10a |  | 2405 | 18370 / 11661 | 13808 / 7209 / 1304 | 2495 | 18853 | 61047 / 40563 | 34444 / 23828 | - |
| r10b | lake (lake boss) | 2930 | 14163 / 9979 | 10748 / 5916 / 272 | 1578 | 14163 | 60579 / 42893 | 29006 / 20652 | - |
| r11d | hill | 212 | 16457 / 10302 | 14428 / 11988 / 6435 | 6471 | 18515 | 55155 / 34217 | 44438 / 27643 | 9828 / 10775 |

**World textures by format, KiB** (video memory):

| Room | ARGB1555 mip | ARGB4444 mip | RGB565 mip | VQ ARGB1555 | VQ ARGB1555 mip | VQ ARGB4444 | VQ ARGB4444 mip | VQ RGB565 | VQ RGB565 mip | world total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| r100 (the first house) | 88 | 381 | 8 | 0 | 0 | 0 | 0 | 36 | 264 | 778 |
| r101 (village) | 0 | 29 | 0 | 0 | 0 | 27 | 69 | 60 | 525 | 710 |
| r103 (farm) | 277 | 237 | 0 | 3 | 0 | 0 | 15 | 34 | 207 | 773 |
| r106 | 269 | 384 | 3 | 0 | 0 | 0 | 0 | 58 | 226 | 940 |
| r104 | 11 | 169 | 4 | 0 | 0 | 0 | 0 | 40 | 241 | 465 |
| r107 (pool) | 43 | 109 | 5 | 0 | 0 | 0 | 0 | 34 | 384 | 575 |
| r105 | 43 | 307 | 29 | 3 | 0 | 0 | 22 | 40 | 614 | 1058 |
| r102 | 11 | 160 | 13 | 0 | 0 | 12 | 31 | 27 | 588 | 843 |
| r108 (river) | 0 | 91 | 6 | 0 | 7 | 57 | 27 | 34 | 275 | 498 |
| r109 (the cabin) | 43 | 525 | 3 | 0 | 0 | 0 | 0 | 34 | 80 | 685 |
| r10a | 11 | 451 | 5 | 0 | 0 | 0 | 7 | 34 | 337 | 845 |
| r10b (lake) | 0 | 259 | 5 | 3 | 15 | 18 | 47 | 34 | 373 | 753 |
| r11d (hill) | 0 | 107 | 6 | 0 | 0 | 0 | 7 | 34 | 264 | 418 |

**GameCube-sourced texture rows** (package names `source`, `source-pair`):

| Room | GameCube-sourced rows in the world | in the catalogue, HUD, effects |
|---|---:|---:|
| r100 (the first house) | 0 | 1 |
| r101 (village) | 5 | 34 |
| r103 (farm) | 0 | 46 |
| r106 | 0 | 1 |
| r104 | 0 | 1 |
| r107 (pool) | 0 | 1 |
| r105 | 0 | 1 |
| r102 | 0 | 1 |
| r108 (river) | 0 | 1 |
| r109 (the cabin) | 0 | 1 |
| r10a | 0 | 1 |
| r10b (lake) | 0 | 1 |
| r11d (hill) | 0 | 31 |

One catalogue texture (64x128, VQ ARGB4444, `source-pair`) is in every pack. The village world still uses 5 GameCube-sourced textures. The rest of the game packs' rows are props, HUD and effects from the recording.

**The five worst rooms for drawing**, by the largest visible set (chapter 1 only):

| Rank | Room | Largest view staged vertices | p99 | p90 | Mean | Largest PVS vertices | Seeds inside their band | Against the village (27 ms) | Against the hill (37 ms) |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|
| 1 | r109 (the cabin) | 28364 | 20163 | 9327 | 2003 | 64658 | 3 of 26 | x2.02 | x1.72 |
| 2 | r107 (pool) | 24439 | 21064 | 13847 | 4847 | 59742 | 16 of 35 | x1.74 | x1.49 |
| 3 | r105 | 21799 | 12336 | 4754 | 1462 | 61724 | 31 of 56 | x1.55 | x1.32 |
| 4 | r106 | 20667 | 16527 | 9222 | 2586 | 87644 | 28 of 41 | x1.47 | x1.26 |
| 5 | r103 (farm) | 19522 | 15273 | 10524 | 3246 | 70334 | 300 of 300 | x1.39 | x1.19 |
| ref | r101 (village) | 14054 | 10677 | 7141 | 2184 | 78383 | 300 of 300 | x1.00 | x0.85 |
| ref | r11d (hill) | 16457 | 14428 | 11988 | 6471 | 55155 | 300 of 300 | x1.17 | x1.00 |

By the 99th percentile view the five are r107 (pool) 21064, r109 (the cabin) 20163, r106 16527, r104 15594, r103 (farm) 15273. By the largest view without the table (frustum only) they are the pool 29,638, r105 29,284, the cabin 28,364, r104 21,513 and r106 21,116.

**How far to trust these figures:**
- **Cabin (r109):** its table hides almost nothing (8.2 of 161 instances a cell). Its largest view equals the frustum-only figure, and half its cells see 5 vertices or fewer. The seeds sit inside the baked band in only 3 of 26 cases.
- **River (r108):** the reachable floor spreads over 16,583 cells of a 322 m by 225 m box. The seeds sit 8 to 21 m above the floor the bake finds, and none is inside its band. So the river's view figures (mean 193) describe ground below the playable path, not the path. Its PVS figures stand.
- **The other world packs:** 4 to 100% of seeds are inside their bands, and the view figures include cells the player may never stand in.
- The figures count vertices staged, not time. The 27 ms and 37 ms are the model's figures on the recorded routes (route mean 7,032 and 9,828 staged vertices). A room's drawing time also depends on fill, sorting and the actors, which this census does not count.

## 6. Memory

Budgets from the engine's proposed map (`SHELL_MAP.md:243-265`): room pack 4,096 KiB main memory; video memory 2,048 KiB world textures, 1,280 KiB character and 768 KiB effect, HUD and font textures. Counted as baked (tier: count).

| Room | Pack | Room content at load KiB (budget 4096) | Margin KiB | of which catalogue (actors, props) KiB | World textures KiB (budget 2048) | Catalogue, HUD, effect textures KiB (budget 2048) | Textures in VRAM KiB (budget 4096) |
|---|---|---:|---:|---:|---:|---:|---:|
| r100 (the first house) | world | 3465 | 631 | 1012 | 778 | 507 | 1285 |
| r101 (village) | game | 3299 | 797 | 1025 | 710 | 1499 | 2209 |
| r103 (farm) | game | 4011 | 85 | 2204 | 773 | 1906 | 2680 |
| r106 | world | 2684 | 1412 | 1012 | 940 | 507 | 1447 |
| r104 | world | 2101 | 1995 | 1012 | 465 | 507 | 971 |
| r107 (pool) | world | 2419 | 1677 | 1012 | 575 | 507 | 1082 |
| r105 | world | 2353 | 1743 | 1012 | 1058 | 507 | 1564 |
| r102 | world | 1615 | 2481 | 1012 | 843 | 507 | 1349 |
| r108 (river) | world | 2576 | 1520 | 1012 | 498 | 507 | 1004 |
| r109 (the cabin) | world | 2467 | 1629 | 1012 | 685 | 507 | 1192 |
| r10a | world | 2317 | 1779 | 1012 | 845 | 507 | 1352 |
| r10b (lake) | world | 2270 | 1826 | 1012 | 753 | 507 | 1260 |
| r11d (hill) | game | 2298 | 1798 | 1137 | 418 | 1109 | 1526 |

- **Video memory:** every room fits. The worst is r105 with 1,058 of 2,048 KiB of world textures. The farm has 1,906 of 2,048 KiB in the catalogue, HUD and effect blocks together. Its textures total 2,680 KiB, inside the 4,096 KiB the map gives textures.
- **Main memory:** every room fits the 4,096 KiB room-pack block as baked. But the block must also hold collision (being baked by eng-skel2), motions and effect data, which these packs do not count.
  - **The farm (r103)** has 85 KiB left. Its 52 catalogue models (props from the recording) take 2,204 KiB, against 1,012 KiB for the catalogue alone. It will not fit once collision is in unless the props shrink.
  - **The first house (r100)** has 631 KiB left with no props.
  - The other world packs have 1,412 to 2,481 KiB left, before props. The village's props add 13 KiB and the farm's add 1.2 MB, so a prop-heavy room could use most of that margin.

## 7. Not covered

- Props, recorded lights, the environment record, the HUD layout and effects for the 10 rooms with no recording.
  They need a capture run of the old game (section 3). The world packs are census and table inputs only.
- An offline prop converter (room archive object models to the catalogue format) does not exist in `bake/`.
- Leon's cloth binds are one file per costume, taken from the village recording, not derived offline.
- Collision (lane eng-skel2), motions and effect data are not in the memory figures.
- The visibility domain of the river (r108) and the cabin (r109). The reachable floor is grown below and away from
  the playable path. The fix belongs in `bench/bake_vis.c` (a floor search limited to the seeds' height band), which
  this lane does not own.
- Nothing here is a timing. No emulator or console run was made.
