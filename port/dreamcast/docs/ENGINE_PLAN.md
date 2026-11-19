# RE4 Dreamcast engine plan (2026-11-19)

Status: **approved by the owner on 2026-11-19** ("get to work", then confirmed: "Yes, all 10 as recommended", for the ten decisions in hand-over H-001). SH4ZAM rule added the same day.
This plan replaces the performance sections of older plan documents. The release line and its rules stay as they are.

Every number is labelled: **console** (real Dreamcast, GDEMU), **MODELLED** (PC hardware model), **Flycast**, or **estimate**.

## 1. Goal and bar

- **Goal:** all of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets, with 30 fps as the floor at the benchmark scenes.
- **Correct means "plays right and looks right":** same kills, triggers, doors, waves, room clears and cutscenes; no desync or stuck events; still pairs for the look. Not bit-exact.
- **Never changed:** behaviour. Collision results, event sequencing, game state and AI decisions stay the same; the code that computes them may become a native engine service once it is proven to play the same. Enemy cap 4. No GameCube assets.
- **Console decides.** A modelled or emulator number is a filter, never a result.

## 2. Why the path changes

| Fact | Tier |
|---|---|
| Village cross: 18.4 fps, 56 ms a picture. It was 18.9 to 20.3 fps on 10-23 | console |
| Worst farm view: 10.4 fps at 70% game speed. Quiet farm view: 29.3 fps | console |
| 53% of every picture is the CPU waiting on memory. The model says 28% | console |
| About 60% of CPU samples are in the port's own code, about 30% in the original game code | console |
| 685 functions run in 6 s. No function is above 7% | console |
| Logic is 9.6 to 13.1 ms a tick. Drawing is about 41 ms a drawn picture at the cross | console |
| The graphics chip is 20% busy at the cross | console |
| 17 small-lever speed lanes from 11-10 to 11-17: one console-confirmed gain, at one view | console |
| 4 Ganados in a standalone demo: 3.03 ms. In the game: about 8 ms | console / MODELLED |

What that means:
- At one logic tick a picture, drawing has about 21 to 23 ms. It must halve at the cross and fall by about 70% at the worst view.
- The time is spread thin over a drawing path that grew as bridge layers on the GameCube's per-model, per-part structures. A world vertex crosses nine nested functions and is handled twice (transform to a RAM cache, then copy out). Characters add per-tick transaction and proof layers.
- That path was built as 1,181 build switches inside the legacy image, gated by byte identity with the previous build. Those gates protect the old path. No gate checks a frame time, and none runs on a console.
- More switches will not find 20 ms. A drawing path designed for an 8 KB instruction cache and a 16 KB data cache might, and the console can tell us in days.

## 3. Architecture

The engine is the program. The original game supplies behaviour, hosted on top of it. (Owner 2026-11-19: "I want all of the game in a new native improved engine", then chose "Engine owns everything, original behaviour hosted on it".)

| Layer | Runs | What it is |
|---|---|---|
| **Bake** | PC, offline | PS2 sources to room packs: world pieces in strip order, sorted by material, with ready-made chip headers and bounds; characters as bone-sorted streams with levels of detail; effect atlases; collision and room tables in engine form. Mip-mapped VQ and palette textures |
| **Engine core** | SH-4, new | The main loop, the pacer and the frame-time governor; the memory map (its own layout, not the GameCube's 13 MiB arena); room and disc loading; saves; audio; movies; the QA link and counters |
| **Engine services** | SH-4, new | Renderer (world, characters, effects, HUD; one tight loop per phase, one pass per vertex, straight to the chip); effect simulation; skeleton and pose; collision queries; object and actor tables; lights. Data-oriented, sized for an 8 KB instruction cache and a 16 KB data cache, math on SH4ZAM |
| **Behaviour** | SH-4, original code | Enemy AI, player, events, scripts, room code and puzzles, compiled against the engine's service interfaces. Behaviour is unchanged: same decisions, kills, triggers, waves and cutscenes |

**How the original code moves over.** It starts hosted as it is, calling thin adapters. Then each hot system behind it is replaced by a native service, one at a time, in the order the console profile gives. Each replacement is proven to play the same before the old code for it is deleted:
1. drawing (M1, M2);
2. effect simulation and transform;
3. skeleton, pose and inverse kinematics;
4. collision queries;
5. actor and object management, enemy body services (routes, foot placement);
6. whatever the console profile shows next.

Behaviour code itself (what an enemy decides, what an event does) is not rewritten. A system is replaced only when the console shows its cost, never on the model alone.

**Math and kernels: SH4ZAM** (owner 2026-11-19: "the engine needs to leverage sh4zam or improve upon it if there are shortcomings").
- Every engine kernel (transform, skin, light, clip class, matrix stack, vector and trig math) is built on SH4ZAM (`gyrovorbis/sh4zam`). The engine does not grow a second math library.
- The port pins SH4ZAM 33fa485 (2026-10-15). Upstream is 54 commits ahead (cff97e8, 2026-11-18). The engine line moves to current upstream first, then pins it.
- Where SH4ZAM falls short of what the engine needs (a missing primitive, a slower path on console, a precision gap), the engine improves it in SH4ZAM's own style, naming, header layout, tests and benchmarks. Each improvement is a candidate upstream pull request; posting one to `gyrovorbis/sh4zam` needs the owner's OK.
- Console facts to start from: SH4ZAM arms ran 1.25 to 1.32 times their MODELLED time on console against 1.10 for plain C (enemy demo, 10-19); per-triangle back-face culling with SH4ZAM was slower on console (15.4 against 18.9 fps, 10-23). Both point at memory traffic around the math, which the engine's data layout must fix, not at SH4ZAM's arithmetic.
- The port's existing SH4ZAM kernels (`sh4zam_skin.c`, `sh4zam_direct.c`, `sh4_approx.c`) are the starting point.

Two images are built from the engine line:
1. **Bench image.** The renderer plus a room pack plus recorded frame lists from the benchmark scenes. No game code. It boots in seconds, runs unattended over the QA link, and is the permanent console benchmark.
2. **Game image.** The engine with the original behaviour hosted on it. Old drawing and service code is removed as each native service lands, not switched off, so its bytes go back to the game.

**Carries over:** the PS2 asset pipeline and room packages; the SH-4 transform, skin and light kernels; store-queue submission; the pacer; the QA menu, QA link, lab disc, PC sampler and counter rows; the release harness jobs (boot, disc race, full-play, texture, memory); every gameplay fix (cap 4, PS2 spawn logic, the carry-forward list); audio, movies, saves.

**Replaced:** the world pass stack in `native_static.cpp`; the actor transaction, lease and owner-run layers; the 3D binders in `native_ui.cpp`; the GameCube heap layout and the SDK shims the behaviour code calls; then, service by service, the original effect, skeleton, collision and manager code; the switch surface in the Makefile; the determinism compiler settings (fused multiply-add off, `#line` pins).

**Behaviour code gets normal treatment:** an engine-owned memory map so program size stops changing game decisions; normal compiler settings (fused multiply-add on, -O2, link-time optimisation as a trial); code placed by console heat; presentation-only work skipped on ticks whose picture is dropped; idle Ganados staggered.

Why not something simpler: code layout alone gave 3 to 6.5% fewer instruction stalls and 0 fps (console). One 45-switch stack added 13.6 ms a drawn frame (MODELLED). Per-lever lanes have been inside the measurement noise since 11-12.

Why not a full rewrite of the behaviour: a sister project tried that and played one room after 692 commits. The behaviour code is where the game's rules live, and it is not where the time goes. The services under it are, and those are replaced.

## 4. Milestones

Each is a vertical slice that runs, is shown (stills, a short clip, frame numbers) and proves one risk. Estimates are lane-days of agent work and are **estimates**.

| # | Slice | Proves | Shown as | Estimate |
|---|---|---|---|---|
| **M0** | **Console truth.** Run the lab disc session that is already built. Add "off" arms (no world, no characters, no effects) so each part's cost is a subtraction on one build. Record mean, p99, worst interval | Where console time really goes; the model's margin | One console table for 6 scenes | 1 to 2 days + one owner evening |
| **M1** | **Bench: the cross and the worst farm view on the new renderer,** from recorded frame lists, on console | Drawing can fit about 20 ms on hardware | Clip, still pairs against the current build, console frame table | 5 to 8 days + one owner boot |
| **M2** | **Engine shell: the village and farm run on the engine.** Engine main loop and memory map, new renderer in, old drawing out, behaviour hosted through adapters, one tick a picture | The engine can host the original behaviour; the drawing gain survives in the game; gameplay stays equivalent | Play clip, console table, decisions check | 10 to 15 days |
| **M3** | **Native services, round 1: fights hold the floor.** Effect simulation, skeleton and pose, collision queries as engine services; governor; staggered Ganados. Bell fight, barn, lake fight | 30 fps under load; each service plays the same as the code it replaces | Fight clips, still pairs per governor step, equivalence report per service | 10 to 15 days |
| **M4** | **Disc 1 on the engine.** Every chapter 1 and 2 room re-baked, bosses included, a no-warp play-through, first release from the engine line | The whole pipeline, end to end | The release | 8 to 12 days |
| **M5** | **The rest of the game on the engine:** Disc 2 and Disc 3 rooms and bosses on the engine formats, budgets at first pass, a play-through per chapter; further native services as the console profile ranks them | All of the game in the new engine | Chapter by chapter | Sized per chapter after M2 |

M1 numbers (one table, 2026-11-19):

| Step | Bar |
|---|---|
| Console entry | Modelled drawing at the cross at or under 10 ms (half of the 20 ms target), absolute. The bench takes logic outputs only and does all drawing work itself. After at most three model rounds the bench goes to the console anyway |
| M1 pass | Console drawing at the cross at or under 20 ms per picture (p99), hay-fork reported |
| M1 stop | Console drawing at the cross above 26 ms after two genuinely different designs; the owner then chooses between content cuts and a lower floor |

Stop rules:
- **M1:** if the bench cannot draw the cross inside 26 ms on console after two distinct attempts, renderer work alone will not reach 30 fps at this content. The owner then chooses between content cuts and a lower floor. Nothing proceeds to M2 on hope.
- **Any milestone:** a failing gate gets two distinct hypotheses tested, then the blocker is written up. No tolerance is loosened to pass.

## 5. Gates

Per milestone, on the final image, once. Every check ships with an input that makes it fail.

| Gate | Rule |
|---|---|
| **Frame floor** | Console, benchmark scenes, 600 pictures each: report mean, p99, worst interval and count over 33.3 ms. Pass = p99 at or under 33.3 ms. Before a console number exists, an emulator or modelled figure counts only if it fits in half the budget |
| **Plays right** | Gameplay equivalence on the scripted routes: kills, triggers, doors, waves, room clears, cutscenes; no desync or stuck events. From M4, a no-warp play-through per chapter |
| **Determinism** | The same build with the same input script makes the same decisions twice. Build-to-build byte identity is not required |
| **Looks right** | Still pairs at fixed cameras against the PS2 reference and the previous release. The owner approves each governor step |
| **Memory** | Room heap at the fight low point, the 48 KiB system squeeze, VRAM map per room with no failed allocations |
| **Disc** | The GDEMU race gate, 10 seeds, 0 bad reads; no disc reads during play |
| **Assets** | No GameCube asset drawn or played, against the reviewed allowlist |

The fixed benchmark: village cross, bell fight, farm entry, farm hay-fork view, farm quiet view, lake fight, castle hall. Same presets, same enemies, cap 4. A gain that does not show on it does not merge.

Knob-off identity and STRICT stay available as debugging tools. They gate only hotfixes on the frozen release line.

## 6. What stops now

Owner (11-19): "I don't want to pile on improvement for old work - ensure we are following the guidance and lessons learned to go native."
- **No work to improve, re-measure or re-profile the old drawing path.** The new path is judged against the budget in absolute numbers, never as a percentage of the old game. The one console reading of today's game is the M0 core session (off arms), which sets the budget split.
- **No old-switch A/B on console.** The lab disc's backlog arms are not run.
- **Disc 2 on the old line:** only the play-through tool and the list of logic blockers carry over. Rendering, texture, memory and asset-row issues there are recorded, not fixed; the rooms are re-baked in M5.

- New default-off speed switches in the legacy image.
- Speed lanes judged only on the model, and chains of model-only follow-ups.
- Console discs staged without a session booked. The lab disc and the bench image replace per-idea discs.
- A review round per change.
- Identity and STRICT gates on measuring tools and on engine-line work.
- Shrinking the GameCube asset row count for rooms nobody has played. Asset rows are cleared when a room is re-baked for the new formats, once.
- Tuning the old drawing path. It ships hotfixes only.

Kept running: bug fixes on the release line; room entry and play-through work for Disc 2, one lane at a time.

## 7. Workflow

Full rules: [engine/LANES.md](engine/LANES.md).

- **Lines:** `engine` is the integration branch for this plan. The release line (`t15/int`) is frozen to hotfixes.
- **Lanes:** one owner, one branch, one build folder each. At most two build lanes plus one lab or release lane. PC-only lanes (bakers, host tests) are separate from lanes that need an emulator.
- **Merging:** the integrator merges a lane when its own gates pass. A change merges switched on, or it does not merge.
- **Audit:** one independent audit per milestone, by the agent that did not write the code. No review per change.
- **Hand-overs:** numbered, one per milestone or blocking question, with commit, image hashes, numbers with tiers, and the evidence path.
- **Console:** the owner boots; the session runs unattended over the QA link. Each milestone ends with a console run.

## 8. Owner decisions on record

| Date | Owner's words | Meaning |
|---|---|---|
| 10-12 | Measure the bottleneck before more assembly | Console profile first, simple fixes first |
| 10-14 | Releases are scope based, not time based | Milestones gate releases |
| 10-15 | "cap 4 for the zombies" (10-17) | Benchmarks at cap 4 |
| 10-19 | "Approximation is fine. Exact has been a hindrance to this product" | "Plays right" is the bar |
| 10-23 | "this game shouldn't have any game cube assets" | Asset gate stays |
| 10-28 | "we need a better loop to not miss these things" | Nothing lands switched off |
| 11-17 | Lab yes, 30 fps, governor OK, island in parallel | M0, the floor, M3 |
| 11-17 | "lets put the re4 work on hold for now" | On hold until this plan is approved |
| 11-19 | "get to work", then confirmed: "Yes, all 10 as recommended" | Plan approved; the recommended answers to all ten decisions in H-001 stand |
| 11-19 | "the engine needs to leverage sh4zam or improve upon it if there are shortcomings" | SH4ZAM is the engine's math and kernel base |
| 11-19 | "I don't want to pile on improvement for old work - ensure we are following the guidance and lessons learned to go native." | No work on the old path; the engine is judged on the absolute budget |
| 11-19 | "I want all of the game in a new native improved engine"; chose "Engine owns everything, original behaviour hosted on it" | The engine is the program; original AI, event and script code is hosted on it; hot systems become native services one at a time |
| 11-19 | Console session: "Later, prepare it and wait" | M0 lab disc is prepared; staging waits for the owner's SD card |

## 9. Sources

Console session 2026-11-11 and A/B 2026-11-12 (lane perf30); code read at 5fc47928c (Test 27.1); release harness `tools/d367/rr`.
