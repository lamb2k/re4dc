# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19 17:15):** E0 bench round done on Opus and merged; Codex audit running. Next step for E0 is the console. Plan version 2 waits on the owner (H-006). M0 lab disc and the E0 bench disc both wait for the SD card.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| E0 | Walkabout and the drawing row (budget 14 ms console, 7 ms MODELLED entry) | eng-e0 (Opus, renderer e28d7f2c2, merged): all drawing work at run time, MODELLED 25 pictures: cross 14.2 mean / 19.6 worst (was 45.4), hay-fork 16.1 / 18.4 (was 99.7). Flycast 600 pictures: 11.2 / 15.8 and 12.9 / 16.6. Not at the 7 ms entry line; the round rule says console next. Baked visibility conservative on 300 of 300 pictures. Disc: E:\RE4DC-Lanes\eng-e0uild\E0-GDEMU-e0fin. Open: hair, HUD mask, ammunition readout; visibility table only covers the recorded route. Codex audit: AUDIT-E0.md pending | Waits for SD card |
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

Closed: eng-e0 (Opus), handed back 11-19, merged. Survey arms MODELLED (cross / hay-fork): default 13.9 / 15.9; cache-RAM staging 14.2 / 16.1; three short loops in C 15.4 / 18.5. Both arms are boot options on the disc for the console to judge.

Closed: eng-shell-map (Opus), handed back 11-19, merged (lane commit 673a891e9). Console budget rows at the cross, ms a picture: behaviour 1.6, services 15.5, publication 16.3, drawing 17.8, system 3.9. Open: heap census run for the behaviour arena size; worst interval per row.

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

## Waiting on the owner

- Plan version 2: approve milestones E0 to E4, the budget rows, and the content look calls as a class.
- SD card in, then one evening with the console and DreamPi on: lab disc core tier (85 min) plus the bench disc.
