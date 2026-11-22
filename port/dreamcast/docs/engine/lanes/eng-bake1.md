# eng-bake1 hand-back (2026-11-22)

**Status: finished, unaudited.** This lane ran on the PC only: no emulator, no image change and no pack-format change. Every number here is a **count** from the baked data, not a timing.

Branch `lane/eng-bake1`, head: see the end of this file. The full census is in `port/dreamcast/docs/engine/ROOM_CENSUS_20261121.md`.

## The point
- **Chapter 1:** 13 rooms; 12 have a world and all 12 bake. r120 is the intro movie and has no world. No bake failure is left.
- **Game packs (3):** the village (r101) and the farm (r103), plus the hill (r11d) for comparison. These rooms have a recording of the old game.
- **World packs (10):** built from offline data only. They have no props, lights, HUD or effects, and the HUD verify refuses them by design.
- **The 5 worst rooms for drawing**, by the largest visible set:

  | Room | Staged vertices | Against the village | Against the hill |
  |---|---:|---:|---:|
  | the cabin (r109) | 28,364 | x2.02 | x1.72 |
  | the pool (r107) | 24,439 | x1.74 | x1.49 |
  | r105 | 21,799 | x1.55 | x1.32 |
  | r106 | 20,667 | x1.47 | x1.26 |
  | the farm (r103) | 19,522 | x1.39 | x1.19 |
  | village (r101), reference | 14,054 | x1.00 | x0.85 |
  | hill (r11d), reference | 16,457 | x1.17 | x1.00 |

  The model has the village drawing at 27 ms and the hill at 37 ms. By the 99th-percentile view the worst five are the pool, the cabin, r106, r104 and the farm.
- **Memory:**
  - Video memory: every room fits as baked.
  - Main memory: the farm has **85 KiB** left of its 4,096 KiB room-pack block. Its props alone take 1.2 MB, and collision is not counted yet. It will not fit once collision is added unless the props shrink.
  - Every other room has 631 KiB or more left, but the world packs carry no props.
- **Missing input:** the 10 rooms without a recording need a capture run of the old game in an emulator for their props, recorded lights, environment and effects. That run is another lane's or the integrator's. What the capture must contain is in section 3 of the census document.

## Per room
| Room | Pack | Bakes | Checks | Why it is not a game pack |
|---|---|---|---|---|
| r120 | none | - | - | no world (intro movie, jumps to r100) |
| r100 the first house | world | yes | pass | no recording |
| r101 village | game | yes | pass (HUD 3 widgets, seeds 300/300) | - |
| r103 farm | game | yes | pass (HUD 3 widgets, seeds 300/300) | - |
| r106 | world | yes | pass | no recording |
| r104 | world | yes | pass | no recording |
| r107 pool | world | yes | pass | no recording |
| r105 | world | yes | pass | no recording |
| r102 | world | yes | pass (empty sky: the PS2 gives none) | no recording |
| r108 river | world | yes | pass | no recording; its view figures cannot be trusted (below) |
| r109 the cabin | world | yes | pass | no recording; its table culls almost nothing (below) |
| r10a | world | yes | pass | no recording |
| r10b lake | world | yes | pass | no recording |
| r11d hill (chapter 2-3, comparison) | game | yes | pass (HUD 3 widgets, seeds 300/300) | - |

## Per brief item
1. **Room list and inputs:** done. Every room's input status is in census section 1, re-read on 2026-11-22.
   - The earlier report of 33 missing textures for r104 was a fault in the inputs check, now fixed.
   - Only the recording depends on an emulator run. Everything else is offline.
2. **One command per room:** `room_bake.py <room>` and `--chapter1`. Census section 2 lists, with file and line, what still needs a recording:
   - props: `native_pack.py:47-53`, `native_extra.py:8`;
   - lights and the environment: `core/draw_e1.c:3`;
   - the HUD layout: `native_pack.py:148-152`;
   - effects: `native_pack.py:136-144`.
3. **Run over every room:** done (run 2, 2026-11-21, bake at commit `c90c5d235`).
   - Packs are in `E:\RE4DC-Lanes\eng-bake1\packs`. The run log is `logs\ch1.log` and ended rc=0 for all 13 rooms.
   - Fixes made in the bake earlier in this lane:
     - an empty sky for r102;
     - `--ram` for the village;
     - the old port's baked live objects left out;
     - visibility seeds from every area and item.
   - Re-bake against the kept packs:
     - the hill is byte-identical;
     - the village differs only in its world section, by the 14 live objects;
     - the farm differs from `FARM.PAK`, which lacks the HUD fix.
   - Today's additions: pack receipts (`receipt.json`; `--check-receipt` OK), and a new control for the seed-coverage check (below).
4. **Census:** `ROOM_CENSUS_20261121.md`, sections 4 and 5. It covers:
   - triangles, vertices, strips, meshlets, materials and textures;
   - video-memory KiB by format;
   - pack bytes and RAM at load;
   - visible sets: largest, p99, p90, p50 and mean, with and without the table;
   - PVS largest and mean, and the recorded route where one exists;
   - lights;
   - GameCube rows.
5. **Memory:** census section 6 (above).

## Checks and their failing inputs
All checks are in the repository, in `port/dreamcast/engine/bake/room_bake.py --controls`. Results are in `packs\controls.json` and `logs\controls.log`. Every row read "failed as it must":

| Check | Failing input | How it failed |
|---|---|---|
| seeded floor | r10a with every seed moved off the floor | no reachable cell |
| census_world table/pack match | the village pack with the farm's table | exit 4 |
| offline seeds cover the recording | the village cameras against the lake's table | 0 of 300 |
| HUD verify | r10b world pack | refused |
| receipt check | a receipt with the village pack's hash changed | mismatch |

The seed-coverage control used to compare the village cameras against the farm's table, and it **did not fail**. The farm and the hill share the village's world coordinates. The check therefore tests that a camera sits in a baked cell, not which room baked that cell. The control now uses the lake, and `NATIVE.md` says what the check does not test.

## How far to trust the figures
- **River (r108):** the reachable floor covers 16,583 cells of the whole box. The seeds sit 8 to 21 m above the floor the bake finds, and none is inside its band. Its view figures (mean 193 staged vertices) describe ground below the playable path. Its PVS figures stand.
- **Cabin (r109):** the table hides 8.2 of 161 instances a cell, and half its cells see 5 vertices or fewer. Its largest view equals the frustum-only figure.
- **The fix** belongs in `bench/bake_vis.c`, which I do not own: limit the floor search to the seeds' height band.
- **All world packs:** the view figures are taken over every baked cell, not over a play route. Only the three recorded rooms have a route.

## Muzzle flash (integrator item 3): report only, no effects built
In `em/wep02.drs` (test24 release tree) there are 8 TPLs. Log: `logs\wep02tex.log`.

| TPLs | Images | Package in `tex.pak` |
|---|---|---|
| 0 and 4 | 128x88 x2 | `ps2-source` |
| 1 and 5 | 64x64 x2 | `ps2-source` |
| 2 | 64x64, 128x64 | `source` (GameCube) |
| 3 | 32x32, 16x16 | `source` (GameCube) |
| 6 and 7 | - | no package |

The PS2-sourced packages for the flash pictures exist. I did not map these TPLs to the effect texture numbers 30, 33 and 34.

## Requests for other lanes
- **Owner of `bench/bake_vis.c`:** limit reachability to the floor band of the seeds (r108, r109).
- **A recording lane:** captures of the 10 rooms, per census section 3.
- **eng-draw1:** the census is your input.
- **eng-skel2:** collision is not counted here. The farm has 85 KiB left for it.

## Stubs, original units, image
None. No image was built or changed.

## Files touched
All inside my owned list:
- `port/dreamcast/engine/bake/room_bake.py`
- `port/dreamcast/engine/bench/NATIVE.md`
- `port/dreamcast/docs/engine/ROOM_CENSUS_20261121.md`
- `port/dreamcast/docs/engine/lanes/eng-bake1.md`

## Disk
Packs and logs on E: total about 76 MB, well under the 5 GB the brief allows. No discs.

## Not done
- Props, lights, HUD and effects for the 10 rooms without a recording; they need captures.
- An offline prop converter.
- Leon's cloth binds derived offline.
- The visibility domain fix for the river and the cabin (not my file).
- Collision, motions and effect data in the memory figures.
- Nothing here is timed.
