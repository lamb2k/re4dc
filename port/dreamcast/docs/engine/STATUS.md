# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-19):** plan approved by the owner. `engine` branch created. Lanes lab33 (M0) and eng-bench (M1) running. M0 console session waits for the owner's SD card.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | lab33 running: lab disc v2. Session waits for the owner's SD card | Not run |
| M1 | Bench: cross and worst farm view on the new renderer | eng-bench running | Not run |
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

p99 and worst interval: never measured.

## Lanes

| Lane | Milestone | Branch | Started | Agent | Evidence |
|---|---|---|---|---|---|
| lab33 | M0: lab disc v2 (off arms, A/A, p99 and worst rows) | lane/lab33 from lane/lab32 aa622c2e5 | 11-19 09:08 | Codex gpt-6.2-astra medium, session 01a1f422-e8ce | E:\RE4DC-Lanes\lab33 |
| eng-bench | M1: bench image, SH4ZAM to upstream, frame-list capture, bake, renderer | lane/eng-bench from engine 7c0f05711 | 11-19 09:08 | Codex gpt-6.2-astra medium, session 01a1f422-e8d6 | E:\RE4DC-Lanes\eng-bench |

Next lane when lab33 hands back: one Disc 2 room lane (enter and play-through), decision 6.

## Run-time lab arms

None on the engine line yet.

## Waiting on the owner

The decisions listed in hand-over H-001.
