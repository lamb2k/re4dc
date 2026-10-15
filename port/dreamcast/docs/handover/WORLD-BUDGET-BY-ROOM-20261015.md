# World vertex budget by room, chapters 1-2 (2026-10-15 evening, MODELLED)

Question (user): which rooms need world-vertex reduction toward a target, and which have no Ganados so the world is all that matters?

Model: console-calibrated room budget (room-budget-20261015/backlog.py), ~1.1 ms per 1k world vertices. Fixed costs are assumed cut to their floors (logic overhead 6 ms, Leon logic 2.5, render setup + world walk 6, effects 1, disc waits 0). Ganado logic, characters and props are as they are today (GameCube-model enemies included where they still appear). "Budget" = the world vertices left for the frame after everything else. A negative budget means the room misses the target even with no world at all.

## Answer in plain words

- **30 fps in a room with Ganados is not reachable by world cuts alone.** Ganado thinking plus the characters themselves (Leon 6.7k + ~1.9k per visible Ganado) already use the whole 33 ms in every fight room, even with the fixed costs at their floors. In fight rooms the realistic near-term target is 20 fps, and the world budget there is about 3-13k vertices.
- **Rooms with few or no Ganados are where world reduction pays most.** The world is nearly the whole frame there, so cutting it moves the frame rate directly: r109 (14.8k typical / 22.6k worst; 30 fps needs ~6.5k), r119 (worst view 32.6k; 20 fps needs ~14k), r117 (worst 24k; 20 fps ~11k). r102, r11b and r112 are already close.
- **Group C rooms need character/logic work before world cuts help:** the r101 cross worst view, r118, r111, r113, r11c, r11d, r10f, r200. Most of chapter 2 still shows GameCube-model enemies there (the PS2 cast lane fixes that), and the far-Ganado half rate (D1) targets them.

## Table (k = thousands of world vertices on screen)

| Group | Room | Ch | Ganado units | World typ / worst | World budget at 30 fps | World budget at 20 fps (typ / worst) | Worst-view cut for 20 fps |
|---|---|---|---|---|---|---|---|
| A. Few/no Ganados: world is the lever; 30 fps reachable with a world cut | r109 | 1-3 | 0.3 | 14.8k / 22.6k | 6.5k | 21.7k / 21.7k | -1.0k (to 21.7k) |
| A. Few/no Ganados: world is the lever; 30 fps reachable with a world cut | r112 | 2-2 | 1.0 | 2.0k / 9.3k | 0.3k | 15.5k / 15.5k | none |
| A. Few/no Ganados: world is the lever; 30 fps reachable with a world cut | r11b | 2-1 | 1.5 | 2.9k / 9.3k | 2.6k | 17.8k / 17.8k | none |
| A. Few/no Ganados: world is the lever; 30 fps reachable with a world cut | r102 | 1-3 | 0.3 | 1.7k / 9.3k | 5.9k | 21.1k / 21.1k | none |
| A. Few/no Ganados: world is the main lever | r119 | 2-1 | 3.0 | 8.8k / 32.6k | none | 13.9k / 13.9k | -18.7k (to 13.9k) |
| A. Few/no Ganados: world is the main lever | r117 | 2-1 | 2.0 | 6.7k / 24.0k | none | 11.1k / 11.1k | -12.9k (to 11.1k) |
| A. Few/no Ganados: world is the main lever | r11f | 2-3 | 3.0 | 8.2k / 14.4k | none | 13.8k / 13.8k | -0.6k (to 13.8k) |
| B. Ganado room: world cut reaches 20 fps | r107 | 1-2 | 6.5 | 4.4k / 27.0k | none | 11.5k / 7.6k | -19.4k (to 7.6k) |
| B. Ganado room: world cut reaches 20 fps | r106 | 1-1 | 6.5 | 9.4k / 17.9k | none | 10.9k / 6.9k | -11.0k (to 6.9k) |
| B. Ganado room: world cut reaches 20 fps | r104 | 1-2 | 9.0 | 8.1k / 17.4k | none | 8.8k / 4.8k | -12.6k (to 4.8k) |
| B. Ganado room: world cut reaches 20 fps | r103 | 1-1 | 5.3 | 9.5k / 16.3k | none | 13.3k / 9.4k | -7.0k (to 9.4k) |
| B. Ganado room: world cut reaches 20 fps | r100 | 1-1 | 9.5 | 6.6k / 14.4k | none | 7.8k / 3.8k | -10.6k (to 3.8k) |
| B. Ganado room: world cut reaches 20 fps | r10a | 1-3 | 6.5 | 3.5k / 13.3k | none | 10.9k / 6.9k | -6.3k (to 6.9k) |
| B. Ganado room: world cut reaches 20 fps | r108 | 1-3 | 6.0 | 3.6k / 11.7k | none | 11.9k / 8.0k | -3.8k (to 8.0k) |
| B. Ganado room: world cut reaches 20 fps | r11a | 2-1 | 6.0 | 1.9k / 10.4k | none | 11.9k / 8.0k | -2.4k (to 8.0k) |
| B. Ganado room: world cut reaches 20 fps | r105 | 1-2 | 6.3 | 4.0k / 8.8k | none | 11.3k / 7.3k | -1.5k (to 7.3k) |
| B. Ganado room: world cut reaches 20 fps | r11e | 2-3 | 3.7 | 1.8k / 6.5k | none | 6.2k / 6.2k | -0.3k (to 6.2k) |
| B0. Ganado room: no world cut needed for 20 fps | r10b | 1-3 | 5.5 | 2.3k / 10.2k | none | 13.4k / 13.4k | none |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r11c | 2-2 | 10.4 | 5.2k / 21.5k | none | none / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r11d | 2-3 | 5.7 | 8.4k / 19.6k | none | 0.3k / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r101 | 1-1 | 6.5 | 10.5k / 15.9k | none | 2.7k / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r111 | 2-2 | 5.7 | 7.3k / 15.5k | none | 0.3k / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r113 | 2-2 | 6.7 | 9.5k / 15.4k | none | none / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r118 | 2-1 | 7.0 | 7.8k / 14.0k | none | 3.0k / none | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r10f | 2-3 | 6.7 | 3.2k / 9.8k | none | 4.3k / 0.3k | - |
| C. Ganado room: world cut alone cannot reach 20 fps (characters/logic first) | r200 | 2-3 | 6.7 | 2.2k / 7.2k | none | 2.0k / none | - |

Caveats: the worst view assumes 4 Ganados drawn at once; Ganado units count the cap-6 peak plus boss/animal units (r100 and r104 are the documented 9-alive exceptions). World vertex counts are projected from the PS2 world data, and lane worldlod re-measures them from camera captures. Generator: tmp worldbudget.py + worldbudget_md.py (job dir); rows CSV room-budget-20261015/world_budget_rows.csv (today's fixed costs).

## Buffered targets (user 10-15: "lets assume we will improve ganado logic, we still should buffer the rooms")

Assumptions:
- Ganado logic improves: far, off-screen Ganados run at half rate (D1), which saves 0.575 ms per alive Ganado beyond 2.
- Fixed costs are at their floors, as above.
- A 10% buffer: the frame is budgeted at 30 ms for 30 fps and 45 ms for 20 fps, so denser moments and model error still fit.

Rule:
- Every room is cut to its buffered target.
- Where the target is below what the look allows (or the room cannot reach it with world cuts alone), the room is cut to the **look floor** set by the r119 / r101 sheets. Every ms still counts there once the character and logic work lands.
- Rooms already under target are left alone.

| Room | Ch | Ganado units | World now typ / worst | Buffered 20 fps target (worst view) | Cut needed | Buffered 30 fps target | Plan |
|---|---|---|---|---|---|---|---|
| r119 | 2-1 | 3.0 | 8.8k / 32.6k | 9.9k | -22.7k | none | cut to target |
| r107 | 1-2 | 6.5 | 4.4k / 27.0k | 5.4k | -21.6k | none | cut to the look floor (target out of reach by world alone) |
| r11c | 2-2 | 10.4 | 5.2k / 21.5k | none | -21.5k | none | cut to the look floor (target out of reach by world alone) |
| r11d | 2-3 | 5.7 | 8.4k / 19.6k | none | -19.6k | none | cut to the look floor (target out of reach by world alone) |
| r117 | 2-1 | 2.0 | 6.7k / 24.0k | 6.5k | -17.5k | none | cut to the look floor (target out of reach by world alone) |
| r101 | 1-1 | 6.5 | 10.5k / 15.9k | none | -15.9k | none | cut to the look floor (target out of reach by world alone) |
| r111 | 2-2 | 5.7 | 7.3k / 15.5k | none | -15.5k | none | cut to the look floor (target out of reach by world alone) |
| r113 | 2-2 | 6.7 | 9.5k / 15.4k | none | -15.4k | none | cut to the look floor (target out of reach by world alone) |
| r118 | 2-1 | 7.0 | 7.8k / 14.0k | none | -14.0k | none | cut to the look floor (target out of reach by world alone) |
| r104 | 1-2 | 9.0 | 8.1k / 17.4k | 3.9k | -13.5k | none | cut to the look floor (target out of reach by world alone) |
| r106 | 1-1 | 6.5 | 9.4k / 17.9k | 4.7k | -13.2k | none | cut to the look floor (target out of reach by world alone) |
| r100 | 1-1 | 9.5 | 6.6k / 14.4k | 3.2k | -11.2k | none | cut to the look floor (target out of reach by world alone) |
| r103 | 1-1 | 5.3 | 9.5k / 16.3k | 6.5k | -9.8k | none | cut to target |
| r10f | 2-3 | 6.7 | 3.2k / 9.8k | none | -9.8k | none | cut to the look floor (target out of reach by world alone) |
| r10a | 1-3 | 6.5 | 3.5k / 13.3k | 4.7k | -8.5k | none | cut to target |
| r200 | 2-3 | 6.7 | 2.2k / 7.2k | none | -7.2k | none | cut to the look floor (target out of reach by world alone) |
| r108 | 1-3 | 6.0 | 3.6k / 11.7k | 5.5k | -6.2k | none | cut to target |
| r109 | 1-3 | 0.3 | 14.8k / 22.6k | 17.1k | -5.5k | 3.5k | cut to target |
| r11a | 2-1 | 6.0 | 1.9k / 10.4k | 5.5k | -4.9k | none | cut to target |
| r11f | 2-3 | 3.0 | 8.2k / 14.4k | 9.8k | -4.6k | none | cut to target |
| r11e | 2-3 | 3.7 | 1.8k / 6.5k | 2.5k | -3.9k | none | cut to target |
| r105 | 1-2 | 6.3 | 4.0k / 8.8k | 5.0k | -3.8k | none | cut to target |
| r10b | 1-3 | 5.5 | 2.3k / 10.2k | 10.6k | none | none | none needed for 20 fps |
| r112 | 2-2 | 1.0 | 2.0k / 9.3k | 11.0k | none | none | none needed for 20 fps |
| r11b | 2-1 | 1.5 | 2.9k / 9.3k | 13.2k | none | none | none needed for 20 fps |
| r102 | 1-3 | 0.3 | 1.7k / 9.3k | 16.5k | none | 2.9k | none needed for 20 fps; 30 fps needs a cut to 2.9k |

**User 10-15: rooms with no Ganados are not cut.** The buffer exists because Ganado logic is uncertain, and these rooms have none. r102, r112, r11b and r109 stay untouched: r109 would need only ~1k off its worst view to make 20 fps without the buffer. r119 (El Gigante) and r117 (enemies + Ashley) are not Ganado-free and keep their targets.
