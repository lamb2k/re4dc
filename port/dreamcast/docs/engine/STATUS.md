# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19 14:00):** plan version 2 (the F-Zero X approach) written and waiting on the owner (H-006). Lanes run as Claude Opus agents; Codex audits. M0 lab disc ready, waits for the SD card.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| E0 | Walkabout: engine image, world from the whole-room bake, recorded camera path | eng-bench round 3 running (Codex session finishing its round; next round on Opus): whole-room bakes village 1.42 MB, farm 1.09 MB; logic-only capture works. Last model-only round | Not run |
| E1 | Leon on the engine, behaviour hosted through setters, no publication layer | Groundwork done: SHELL_MAP.md merged (measured budget rows, boundary, memory map, E1 link closure 22 files / 104 KB code, 175 engine entry points, order and risks) | Not run |
| E2 | Fight: four Ganados on native services | Not started | Not run |
| E3 | Chapter 1 end to end, lake boss, first engine release | Not started | Not run |
| E4 | The rest of the game, by chapter | Not started | Not run |

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
| eng-bench | E0 start: bench round 3 | lane/eng-bench | Codex gpt-6.2-astra (this round), then Claude Opus | E:\RE4DC-Lanes\eng-bench |

Closed: eng-shell-map (Opus), handed back 11-19, merged (lane commit 673a891e9). Console budget rows at the cross, ms a picture: behaviour 1.6, services 15.5, publication 16.3, drawing 17.8, system 3.9. Open: heap census run for the behaviour arena size; worst interval per row.

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

## Waiting on the owner

- Plan version 2: approve milestones E0 to E4, the budget rows, and the content look calls as a class.
- SD card in, then one evening with the console and DreamPi on: lab disc core tier (85 min) plus the bench disc.
