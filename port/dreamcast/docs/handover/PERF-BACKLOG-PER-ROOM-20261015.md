# Performance backlog per room, chapters 1-2 (2026-10-15, MODELLED, console-calibrated)

Derived from PERF-BACKLOG-CH1-2-20261015.csv. Every room weighs the same in the ranking (play-time weighting dropped 10-15); the gap to target still raises a room's weight. Per room: current projected drawn frame by cost, every speed-up that helps it ranked by ms saved there (typical view; worst in brackets), and the result after all scheduled tranches. Targets: 33.3 ms (30 fps); 50 ms for the r101 cross. "not scheduled" = conflicts with a rule (far plane, cap 5).

## r100  now ~59.6 ms -> after all tranches 46.3 ms (worst 55.9), gap to target 13.0 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 10.92/5.86, render_fixed 10.57/6.0, world_verts 7.28/3.9, char_verts 12.65/6.78, props_verts 2.4/1.29, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 4.02 (4.02) | 2 | idea | logic-equiv |
| A8 Hold-only cap in the 9-alive exception rooms (r100 s20 ambush, r104) | 3.45 (3.45) | 4 | priced | logic-gameplay |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B4 World pass walk lean | 2.48 (2.48) | 2 | idea | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 2.30 (2.30) | 1 | gated | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 1.90 (7.96) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 1.90 (6.09) | 3 | idea | render-approx |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.59 (2.63) | 2 | idea | exact |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.52 (6.37) | 4 | idea | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| A1b STATIC_OBJ_BAKE in every room | 1.20 (1.20) | 3 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 1.16 (1.16) | 3 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.50 (0.50) | 4 | idea | render-approx |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |

## r101  now ~67.6 ms -> after all tranches 53.5 ms (worst 61.3), gap to target 3.5 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 7.47/5.99, render_fixed 8.73/6.0, world_verts 11.51/9.22, char_verts 12.65/10.14, props_verts 11.4/9.14, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| C8 Far plane 18.75 m (REJECTED by the user | 5.86 (10.51) | not scheduled | priced | rule-conflict |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 4.69 (8.40) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 4.35 (7.07) | 3 | idea | render-approx |
| C3 Per-room vertex budget enforced by the converter | 3.51 (3.51) | 4 | idea | render-approx |
| A1 STATIC_OBJ_BAKE r101 (test 13) | 3.30 (3.30) | 1 | gated | exact |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.93 (2.76) | 2 | idea | exact |
| B4 World pass walk lean | 1.83 (1.83) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.92 (0.92) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r102  now ~35.0 ms -> after all tranches 30.6 ms (worst 37.2), gap to target -2.8 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 0.34/0.34, render_fixed 4.58/4.58, world_verts 1.91/1.91, char_verts 10.0/10.0, props_verts 2.4/2.4, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| A1b STATIC_OBJ_BAKE in every room | 0.96 (0.96) | 3 | priced | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 0.95 (1.62) | 2 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.42 (0.42) | 3 | idea | exact |
| B4 World pass walk lean | 0.38 (0.38) | 2 | idea | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 0.02 (3.58) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.01 (2.38) | not scheduled | priced | rule-conflict |

## r103  now ~86.9 ms -> after all tranches 53.9 ms (worst 63.1), gap to target 20.5 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 6.09/3.59, render_fixed 6.85/6.0, world_verts 10.46/6.16, char_verts 12.42/7.31, props_verts 1.32/0.78, effects 1.2/1.0, disc_stall 34.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A3 MOTION_COLD_POOL=262144 (test 14 row 17) | 34.00 (34.00) | 1 | gated | exact |
| C1 Offline world distance LOD | 4.20 (7.46) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 3.81 (10.32) | not scheduled | priced | rule-conflict |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 3.04 (8.25) | 4 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C3 Per-room vertex budget enforced by the converter | 2.46 (2.46) | 4 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.83 (2.78) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 1.72 (1.72) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| A1b STATIC_OBJ_BAKE in every room | 1.68 (1.68) | 3 | priced | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.17 (1.17) | 2 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.82 (0.82) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r104  now ~60.3 ms -> after all tranches 47.3 ms (worst 58.0), gap to target 14.0 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 10.35/5.47, render_fixed 10.78/6.0, world_verts 8.94/4.72, char_verts 12.07/6.38, props_verts 2.4/1.27, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 4.02 (4.02) | 2 | idea | logic-equiv |
| A8 Hold-only cap in the 9-alive exception rooms (r100 s20 ambush, r104) | 3.45 (3.45) | 4 | priced | logic-gameplay |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C1 Offline world distance LOD | 2.90 (7.57) | 3 | idea | render-approx |
| B4 World pass walk lean | 2.55 (2.55) | 2 | idea | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 2.50 (10.14) | not scheduled | priced | rule-conflict |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 2.00 (8.11) | 4 | idea | render-approx |
| A1b STATIC_OBJ_BAKE in every room | 1.80 (1.80) | 3 | priced | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.68 (2.85) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 1.12 (1.12) | 3 | idea | exact |
| C3 Per-room vertex budget enforced by the converter | 0.94 (0.94) | 4 | idea | render-approx |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.30 (0.30) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r105  now ~51.9 ms -> after all tranches 43.1 ms (worst 50.9), gap to target 9.8 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 7.24/4.88, render_fixed 9.57/6.0, world_verts 4.42/2.98, char_verts 12.42/8.36, props_verts 2.4/1.62, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| B4 World pass walk lean | 2.13 (2.13) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.35 (2.12) | 2 | idea | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 1.20 (1.20) | 1 | gated | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.90 (0.90) | 3 | idea | exact |
| C1 Offline world distance LOD | 0.89 (3.53) | 3 | idea | render-approx |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 0.73 (4.90) | not scheduled | priced | rule-conflict |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r106  now ~56.0 ms -> after all tranches 46.0 ms (worst 56.1), gap to target 12.7 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 7.47/4.06, render_fixed 7.4/6.0, world_verts 10.32/5.6, char_verts 12.65/6.87, props_verts 2.4/1.3, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| C1 Offline world distance LOD | 3.22 (7.53) | 3 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C3 Per-room vertex budget enforced by the converter | 2.32 (2.32) | 4 | idea | render-approx |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| C8 Far plane 18.75 m (REJECTED by the user | 2.25 (9.80) | not scheduled | priced | rule-conflict |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.84 (2.94) | 2 | idea | exact |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.80 (7.84) | 4 | idea | render-approx |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.36 (1.36) | 2 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.92 (0.92) | 3 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.84 (0.84) | 3 | priced | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.50 (0.50) | 4 | idea | render-approx |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.20 (0.20) | 1 | gated | exact |

## r107  now ~48.4 ms -> after all tranches 40.5 ms (worst 61.8), gap to target 7.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 7.47/5.08, render_fixed 5.28/5.28, world_verts 4.81/3.26, char_verts 12.65/8.59, props_verts 2.4/1.63, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.40 (3.74) | 2 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 1.32 (1.32) | 3 | priced | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.92 (0.92) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C1 Offline world distance LOD | 0.76 (11.74) | 3 | idea | render-approx |
| B4 World pass walk lean | 0.62 (0.62) | 2 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.50 (0.50) | 4 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.35 (13.38) | not scheduled | priced | rule-conflict |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 0.28 (10.70) | 4 | idea | render-approx |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.25 (0.25) | 1 | gated | exact |

## r108  now ~48.4 ms -> after all tranches 40.0 ms (worst 50.0), gap to target 6.7 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 6.9/4.85, render_fixed 7.2/6.0, world_verts 3.99/2.81, char_verts 12.07/8.49, props_verts 2.4/1.69, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 1.33 (7.04) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 1.33 (5.42) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.29 (1.29) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.29 (2.35) | 2 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.06 (5.63) | 4 | idea | render-approx |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.88 (0.88) | 3 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.84 (0.84) | 3 | priced | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r109  now ~48.7 ms -> after all tranches 38.8 ms (worst 44.9), gap to target 5.5 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 0.34/0.23, render_fixed 5.88/5.88, world_verts 16.27/10.8, char_verts 8.05/5.34, props_verts 2.4/1.59, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| C3 Per-room vertex budget enforced by the converter | 8.27 (8.27) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 4.83 (9.58) | 3 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.95 (2.63) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B4 World pass walk lean | 0.83 (0.83) | 2 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 0.75 (5.39) | not scheduled | priced | rule-conflict |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.50 (0.50) | 4 | idea | render-approx |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.42 (0.42) | 3 | idea | exact |

## r10a  now ~51.4 ms -> after all tranches 43.0 ms (worst 54.4), gap to target 9.7 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 7.47/5.05, render_fixed 9.2/6.0, world_verts 3.89/2.63, char_verts 12.65/8.54, props_verts 2.4/1.62, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| B4 World pass walk lean | 1.99 (1.99) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.32 (2.53) | 2 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 1.02 (5.68) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.96 (6.82) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.92 (0.92) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 0.77 (5.46) | 4 | idea | render-approx |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r10b  now ~44.8 ms -> after all tranches 37.6 ms (worst 44.1), gap to target 4.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 6.32/5.05, render_fixed 6.65/6.0, world_verts 2.54/2.03, char_verts 12.88/10.28, props_verts 0.6/0.48, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 2.65 (2.65) | 1 | gated | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 1.39 (5.57) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 1.33 (4.59) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.23 (1.92) | 2 | idea | exact |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.11 (4.45) | 4 | idea | render-approx |
| B4 World pass walk lean | 1.10 (1.10) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.84 (0.84) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.48 (0.48) | 3 | priced | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| E2 Effect flipbooks + remaining 16-bit textures as PAL4/VQ in every room  | 0.20 (0.20) | 1 | built | conversion |

## r117  now ~54.9 ms -> after all tranches 46.5 ms (worst 61.1), gap to target 13.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 2.3/1.38, render_fixed 9.45/6.0, world_verts 7.37/4.43, char_verts 17.59/10.58, props_verts 2.4/1.44, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (5.52) | 1 | built | conversion |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B4 World pass walk lean | 2.08 (2.08) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.00 (3.52) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (1.60) | 2 | priced | render-approx |
| A1b STATIC_OBJ_BAKE in every room | 1.56 (1.56) | 3 | priced | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.56 (0.56) | 3 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 0.05 (9.71) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.03 (0.08) | not scheduled | priced | rule-conflict |

## r118  now ~63.0 ms -> after all tranches 49.2 ms (worst 60.0), gap to target 15.9 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 8.05/3.62, render_fixed 7.47/6.0, world_verts 8.56/3.84, char_verts 20.7/9.3, props_verts 2.4/1.08, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (11.04) | 1 | built | conversion |
| C8 Far plane 18.75 m (REJECTED by the user | 3.88 (8.33) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 3.37 (6.15) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 3.11 (6.66) | 4 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.34 (3.68) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.39 (1.39) | 2 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 1.00 (1.00) | 1 | gated | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.96 (0.96) | 3 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.84 (0.84) | 3 | priced | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C3 Per-room vertex budget enforced by the converter | 0.56 (0.56) | 4 | idea | render-approx |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r119  now ~50.6 ms -> after all tranches 44.1 ms (worst 64.0), gap to target 10.8 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 3.45/2.14, render_fixed 5.88/5.88, world_verts 9.65/5.98, char_verts 13.45/8.35, props_verts 2.4/1.49, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C1 Offline world distance LOD | 2.72 (13.67) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.85 (3.95) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C3 Per-room vertex budget enforced by the converter | 1.65 (1.65) | 4 | idea | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B4 World pass walk lean | 0.83 (0.83) | 2 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.64 (0.64) | 3 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.50 (0.50) | 4 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.34 (15.17) | not scheduled | priced | rule-conflict |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 0.27 (12.14) | 4 | idea | render-approx |
| E2 Effect flipbooks + remaining 16-bit textures as PAL4/VQ in every room  | 0.20 (0.20) | 1 | built | conversion |

## r11a  now ~48.9 ms -> after all tranches 40.8 ms (worst 51.2), gap to target 7.5 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 6.9/5.23, render_fixed 9.55/6.0, world_verts 2.13/1.62, char_verts 12.07/9.16, props_verts 2.4/1.82, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| B4 World pass walk lean | 2.12 (2.12) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.14 (2.23) | 2 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.88 (0.88) | 3 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.84 (0.84) | 3 | priced | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 0.41 (5.62) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 0.39 (4.43) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 0.33 (4.50) | 4 | idea | render-approx |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r11b  now ~40.8 ms -> after all tranches 34.3 ms (worst 39.2), gap to target 0.9 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 1.72/1.7, render_fixed 6.93/6.0, world_verts 3.15/3.1, char_verts 10.81/10.66, props_verts 2.4/2.37, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 1.81 (6.30) | not scheduled | priced | rule-conflict |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.45 (5.04) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 1.36 (4.35) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.20 (1.20) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.12 (1.68) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.52 (0.52) | 3 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.48 (0.48) | 3 | priced | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.40 (0.40) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r112  now ~41.4 ms -> after all tranches 37.5 ms (worst 44.4), gap to target 4.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 3.55/3.25, render_fixed 4.6/4.6, world_verts 2.2/2.01, char_verts 12.88/11.78, props_verts 2.4/2.19, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.21 (1.85) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.48 (0.48) | 3 | idea | exact |
| B4 World pass walk lean | 0.38 (0.38) | 2 | idea | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| C1 Offline world distance LOD | 0.03 (3.10) | 3 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.02 (2.08) | not scheduled | priced | rule-conflict |

## r111  now ~66.6 ms -> after all tranches 57.6 ms (worst 71.7), gap to target 24.3 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 8.96/3.79, render_fixed 8.62/6.0, world_verts 8.06/3.41, char_verts 22.77/9.63, props_verts 2.4/1.01, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (11.04) | 1 | built | conversion |
| C8 Far plane 18.75 m (REJECTED by the user | 3.50 (10.88) | not scheduled | priced | rule-conflict |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C1 Offline world distance LOD | 2.90 (7.18) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 2.80 (8.70) | 4 | idea | render-approx |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.47 (3.98) | 2 | idea | exact |
| B4 World pass walk lean | 1.79 (1.79) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 1.72 (1.72) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.86 (0.86) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| C3 Per-room vertex budget enforced by the converter | 0.06 (0.06) | 4 | idea | render-approx |

## r113  now ~68.3 ms -> after all tranches 58.5 ms (worst 70.7), gap to target 25.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 10.1/3.94, render_fixed 6.75/6.0, world_verts 10.48/4.09, char_verts 22.77/8.87, props_verts 2.4/0.94, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (11.04) | 1 | built | conversion |
| C8 Far plane 18.75 m (REJECTED by the user | 4.05 (8.67) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 3.64 (6.70) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 3.24 (6.93) | 4 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.66 (3.96) | 2 | idea | exact |
| C3 Per-room vertex budget enforced by the converter | 2.48 (2.48) | 4 | idea | render-approx |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B4 World pass walk lean | 1.14 (1.14) | 2 | idea | exact |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.94 (0.94) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| E2 Effect flipbooks + remaining 16-bit textures as PAL4/VQ in every room  | 0.20 (0.20) | 1 | built | conversion |

## r11c  now ~72.4 ms -> after all tranches 61.3 ms (worst 79.8), gap to target 28.0 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 14.36/5.08, render_fixed 6.2/6.0, world_verts 5.71/2.02, char_verts 27.95/9.89, props_verts 2.4/0.85, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (11.04) | 1 | built | conversion |
| A7 r11c PS2 cabin | 4.60 (14.49) | 1 | built | logic-gameplay |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 4.02 (4.02) | 2 | idea | logic-equiv |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.69 (4.92) | 2 | idea | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 2.24 (9.46) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 2.21 (8.98) | 3 | idea | render-approx |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 1.80 (7.57) | 4 | idea | render-approx |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B2 Collision broadphase cache (scenery line queries per actor) | 1.23 (1.23) | 3 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 1.20 (1.20) | 3 | priced | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| B4 World pass walk lean | 0.94 (0.94) | 2 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| E2 Effect flipbooks + remaining 16-bit textures as PAL4/VQ in every room  | 0.20 (0.20) | 1 | built | conversion |

## r11d  now ~67.6 ms -> after all tranches 59.0 ms (worst 76.2), gap to target 25.7 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 8.96/3.69, render_fixed 8.48/6.0, world_verts 9.21/3.79, char_verts 22.77/9.37, props_verts 2.4/0.99, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| A9 PS2 cast for the remaining GameCube characters | 5.52 (11.04) | 1 | built | conversion |
| C1 Offline world distance LOD | 3.24 (8.95) | 3 | idea | render-approx |
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 2.64 (10.51) | not scheduled | priced | rule-conflict |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 2.56 (4.33) | 2 | idea | exact |
| C2 Impostor cards / baked far band beyond 18.75 m (long sight lines | 2.11 (8.40) | 4 | idea | render-approx |
| B4 World pass walk lean | 1.74 (1.74) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 1.72 (1.72) | 2 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C3 Per-room vertex budget enforced by the converter | 1.21 (1.21) | 4 | idea | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.86 (0.86) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r11e  now ~54.9 ms -> after all tranches 50.7 ms (worst 54.8), gap to target 17.3 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 6.65/4.01, render_fixed 9.48/6.0, world_verts 1.93/1.16, char_verts 18.63/11.22, props_verts 2.4/1.45, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B4 World pass walk lean | 2.09 (2.09) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.64 (2.06) | 2 | idea | exact |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.70 (0.70) | 3 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.13 (3.65) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 0.08 (2.99) | 3 | idea | render-approx |

## r10f  now ~56.6 ms -> after all tranches 50.5 ms (worst 59.9), gap to target 17.1 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 10.1/5.42, render_fixed 7.53/6.0, world_verts 3.51/1.88, char_verts 17.25/9.25, props_verts 2.4/1.29, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| D3 r10f gondola riders | 1.72 (5.17) | 4 | idea | logic-equiv |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.66 (2.59) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| B4 World pass walk lean | 1.41 (1.41) | 2 | idea | exact |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| C1 Offline world distance LOD | 1.00 (3.72) | 3 | idea | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 0.96 (3.07) | not scheduled | priced | rule-conflict |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.94 (0.94) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r11f  now ~50.7 ms -> after all tranches 46.1 ms (worst 51.8), gap to target 12.8 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 3.45/2.17, render_fixed 6.53/6.0, world_verts 9.08/5.7, char_verts 13.45/8.45, props_verts 2.4/1.51, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.80 (2.34) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C1 Offline world distance LOD | 1.61 (4.54) | 3 | idea | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| C3 Per-room vertex budget enforced by the converter | 1.08 (1.08) | 4 | idea | render-approx |
| B4 World pass walk lean | 1.06 (1.06) | 2 | idea | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.00 (1.00) | 2 | priced | render-approx |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| C8 Far plane 18.75 m (REJECTED by the user | 0.77 (4.24) | not scheduled | priced | rule-conflict |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.64 (0.64) | 3 | idea | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |

## r200  now ~56.5 ms -> after all tranches 49.6 ms (worst 58.0), gap to target 16.2 ms
Cost now (ms / budget): logic_fixed 11.2/6.0, leon 3.4/2.5, ganados 10.1/5.23, render_fixed 5.75/5.75, world_verts 2.41/1.25, char_verts 20.01/10.36, props_verts 2.4/1.24, effects 1.2/1.0, disc_stall 0.0/0.0

| Speed-up | ms saved here (worst) | Tranche | Status | Risk |
|---|---|---|---|---|
| B5 Code size for the I-cache | 3.00 (3.00) | 2 | idea | exact |
| A9 PS2 cast for the remaining GameCube characters | 2.76 (2.76) | 1 | built | conversion |
| D1 Far / off-screen Ganado AI + motion at half rate (park only when off s | 2.30 (2.30) | 2 | idea | logic-equiv |
| B6 Data prefetch in the world transform and actor skin streams (D-stall 3 | 1.79 (2.58) | 2 | idea | exact |
| A2 Small exact bundle | 1.70 (1.70) | 1 | gated | exact |
| C4 Flat per-part lighting for the crowd and objects (PS2-like; decided ac | 1.60 (2.20) | 2 | priced | render-approx |
| B3 UI OT caching | 1.50 (1.50) | 3 | idea | exact |
| C5 Reduced Leon render rig (merge face/finger bones for the draw only; lo | 1.50 (1.50) | 3 | idea | render-approx |
| D2 Cap 5 instead of 6 (AGAINST the cap-6 rule; needs the user) | 1.15 (1.15) | not scheduled | priced | rule-conflict |
| B9 Ashley native/lean path (2-2/2-3) | 1.00 (1.00) | 4 | idea | exact |
| B2 Collision broadphase cache (scenery line queries per actor) | 0.94 (0.94) | 3 | idea | exact |
| A2b GC render census removals (#3 GX getters, #11 coarse hooks, #12 diag) | 0.80 (0.80) | 2 | priced | exact |
| B4 World pass walk lean | 0.79 (0.79) | 2 | idea | exact |
| A1b STATIC_OBJ_BAKE in every room | 0.72 (0.72) | 3 | priced | exact |
| A6 LINK_ORDER regenerated for I-cache locality (lane linkord) | 0.50 (0.50) | 1 | gated | exact |
| A5 Resident texture list per room + ROOM_CHANGE_EVICT + CORE_PIN (VRAM ru | 0.50 (0.50) | 1 | gated | exact |
| C1 Offline world distance LOD | 0.30 (3.01) | 3 | idea | render-approx |
| C6 Ganado far mesh + hands merged into the body at mid/far | 0.30 (0.30) | 4 | priced | render-approx |
| C8 Far plane 18.75 m (REJECTED by the user | 0.24 (3.95) | not scheduled | priced | rule-conflict |
| B8 FX_LEVEL dial / PS2 effect recipes in the saturated rooms (sprite cap  | 0.20 (0.20) | 4 | idea | render-approx |
