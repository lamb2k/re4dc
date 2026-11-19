# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19 13:00):** scope widened by the owner: all of the game in a native engine, original behaviour hosted on it (H-005). No work on the old path. M0 lab disc ready, waits for the SD card. eng-bench on its last model-only round. eng-shell-map started.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| M1 | Bench: cross and worst farm view on the native drawing path | Round 2 audited (like for like about -18 to -30% cross, -22 to -28% hay-fork, MODELLED). Round 3 running under STEER-005: logic outputs in, all drawing work at runtime on SH4ZAM, whole-room compact bakes, judged on the absolute budget (10 ms MODELLED, 20 ms console). Last model-only round | Not run |
| M2 | Engine shell: village and farm run on the engine, behaviour hosted | Groundwork: eng-shell-map (service boundary, memory map, M2 design) | Not run |
| M3 | Native services round 1 (effects, skeleton, collision); fights hold the floor | Not started | Not run |
| M4 | Disc 1 on the engine, bosses included | Not started | Not run |
| M5 | The rest of the game on the engine (Disc 2 and 3) | Not started | Not run |

## Benchmark, latest console numbers (Test 27.1, 2026-11-11, means only)

| Scene | fps | ms a picture |
|---|---:|---:|
| Village cross | 18.4 | 56 |
| Bell fight | 16.5 | 53 to 60 |
| Farm entry | 18.4 | 44 to 58 |
| Farm, hay-fork view | 10.4 | 96 |
| Farm, quiet view | 29.3 | 34 |
| Lake fight | not measured | |
| Castle hall | not measured | |

p99 and worst interval: never measured on console. The lab disc v2 reports them.

## Lanes

| Lane | Work | Branch | Agent | Evidence |
|---|---|---|---|---|
| eng-bench | M1 bench image | lane/eng-bench from engine 7c0f05711 | Codex gpt-6.2-astra medium, session 01a1f422-e8d6 | E:\RE4DC-Lanes\eng-bench |
| eng-shell-map | M2 groundwork, PC-only: SHELL_MAP.md (boundary inventory, frame, memory map, services ranked by console cost, M2 design, equivalence checks) | lane/eng-shell-map from engine | Codex gpt-6.2-astra medium | E:\RE4DC-Lanes\eng-shell-map |

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

## Waiting on the owner

- SD card in, then one evening with the console and DreamPi on: lab disc core tier (85 min) plus the bench disc.
