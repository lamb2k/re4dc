# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19 21:30):** owner away ("What can we do ahead of me making changes on my end I'm not home and want progress"). Four Opus lanes started on work that needs neither the console nor an owner decision; their results feed the console evening and the look approvals. Plan version 2 waits on the owner (H-006).

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| E0 | Walkabout and the drawing row (budget 14 ms console) | Console-ready disc E:\RE4DC-Lanes\eng-e0build\E0-GDEMU-e0b (renderer 1edab55a8, merged). MODELLED 25 pictures: cross 16.3 mean / 22.0 worst, hay-fork 18.8 / 21.1 (the source lighting rule added 1.7 to 2.3 ms). Fixed: near-plane clipping (with a test the old loop fails); visibility safe in unknown cells and heights, whole room in 256 KiB; texture copies released; raw rows per picture with A/B/A arms in one boot. Partly: look (MAE 8.6 cross / 6.2 farm; pyre glow and hair open); unseen cross route differs on 8 of 300 pictures by 1 to 2 pixels. Over budget on the model; content changes wait for the owner | Waits for SD card |
| E1 | Leon on the engine, behaviour hosted through setters, no publication layer | eng-e1 (Opus) running: core loop and memory, actor table with native skeleton, collision, player and camera hosted, scripted village route; plays-right against the old game's trace. eng-host (Opus, PC-only) building the PC reference | Not run |
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
| eng-e1 | E1 first slice: Leon on the engine in the village | lane/eng-e1 | Claude Opus | E:\RE4DC-Lanes\eng-e1 |
| eng-look | E0 look items and content candidates (steps with phone-size still sheets for the owner) | lane/eng-look | Claude Opus | E:\RE4DC-Lanes\eng-look |
| eng-host | PC-only: PC build of the player code and the plays-right tool | lane/eng-host | Claude Opus | E:\RE4DC-Lanes\eng-host |

Closed: eng-loop (Opus, PC-only), handed back 11-19, merged (907bb1a24). Remote console loader over the DreamPi link: 16/16 host tests through a simulated bad line (loss, corruption, reorder, dead line, sender restart); corrupted or wrong-hash images refused before RUN. Measured uplink 1.36 KB/s; downlink never measured. Estimates at that rate: E0 bench 2.2 min deflated, game image 24 min, room packs 42 min (packs stay on disc). Disc E:\RE4DC-Lanes\eng-loop\disc (KEEP, SD-README). Next: Flycast proof run (queued for the next free emulator slot), then the owner adds it to the SD card once.

Closed: eng-e0b (Opus), handed back 11-19, merged (code 1edab55a8). Console report: one screen line per 600-picture window (mean, p99, worst, count over 14, count over 33.3, presented intervals over 2 fields); raw rows over serial and in memory tables.

Closed: eng-e0 (Opus), handed back 11-19, merged. Survey arms MODELLED (cross / hay-fork): default 13.9 / 15.9; cache-RAM staging 14.2 / 16.1; three short loops in C 15.4 / 18.5. Both arms are boot options on the disc for the console to judge.

Closed: eng-shell-map (Opus), handed back 11-19, merged (lane commit 673a891e9). Console budget rows at the cross, ms a picture: behaviour 1.6, services 15.5, publication 16.3, drawing 17.8, system 3.9. Open: heap census run for the behaviour arena size; worst interval per row.

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

Queued for the next free emulator slots: eng-boss (first boss on the bench, then hosted), then the loader's Flycast proof.

## Waiting on the owner

- Plan version 2: approve milestones E0 to E4, the budget rows, and the content look calls as a class.
- SD card in, then one evening with the console and DreamPi on: lab disc core tier (85 min) plus the bench disc.
