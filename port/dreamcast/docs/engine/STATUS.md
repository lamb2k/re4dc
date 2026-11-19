# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19 10:30):** plan approved. M0 lab disc v2 is ready and waits for the owner's SD card. eng-bench (M1) is at the renderer step. disc2-play (game track) started.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| M1 | Bench: cross and worst farm view on the new renderer | eng-bench: SH4ZAM at cff97e8 links clean; capture 300 pictures + stills at both scenes; packs baked; renderer next | Not run |
| M2 | Drive: village and farm in the game image | Not started | Not run |
| M3 | Fights hold the floor | Not started | Not run |
| M4 | Disc 1 on the engine line | Not started | Not run |
| M5 | Disc 2 and 3 rooms on the new formats | Not started | Not run |

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
| disc2-play | Disc 2 chapters 3-1 to 4-4: merge ch32 + ch4, inventory, no-warp play-through tooling, 3-1 first | lane/disc2-play from t15/int a5aca9cf9 | Codex gpt-6.2-astra medium | E:\RE4DC-Lanes\disc2-play |

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

## Waiting on the owner

- SD card in, then one evening with the console and DreamPi on (core tier first, 85 min).
