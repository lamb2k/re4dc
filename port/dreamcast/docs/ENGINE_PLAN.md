# RE4 Dreamcast engine plan, version 3.1 (2026-11-20, amended 2026-11-21)

Status: **approved by the owner on 2026-11-20** ("Ok update plan and get to work"), with "beyond the PS2 version" added as a goal and as step 6. Version 3 keeps version 2's budget, architecture and rules; its path is section 7, written after the retrospective ([engine/RETRO_20261120.md](engine/RETRO_20261120.md)). Version 3.1 adds the amendments below.

Every number is labelled: **console** (real Dreamcast, GDEMU), **MODELLED** (PC hardware model), **Flycast**, **emulator** (another project's emulator), or **estimate**. (amended 2026-11-21, see Amendments: the tiers are now those in D below.)

## Amendments 2026-11-21 (version 3.1)

This section records the owner's directions of 2026-11-21 and the integrator's reading of them (hand-overs H-019 to H-021). It stands pending the owner's word if any reading is wrong. Where it disagrees with a sentence below, it wins; those sentences carry the mark "(amended 2026-11-21, see Amendments)" and are kept as written.

The owner's words that day:
1. On comparing with the old port: "We don't want to get stuck in the exact loop and we need a brand new architecture. But customers need to know how much faster the game will run."
2. On the console: "I don't want to look at a disc until we've coloelrter the replatforming - you can tell by the code where complexity is. You can also use a stricter emulator build for Flycast look that up so you can do Your own defense modeling." The integrator reads "coloelrter" as "completed" and "defense" as "defensive"; that is a reading.
3. On what the work is: "Remember re-platform for Dreamcast native port."
4. On gameplay: "What makes the most sense? People that have played the GameCube version shouldn't have to think about game play choices it should just run as fast."

What they mean for this plan:

**A. What this is.** The work is the replatform: re-platforming RE4 as a Dreamcast native port of the whole game. Progress is reported as how much of the game is re-platformed (native and playable in the new engine) and what is left, before audit or tooling detail. A finished milestone is a part, not the replatform.

**B. The player's test.** It must play like the GameCube version and run as fast (30 fps).
- The original AI, event and script code stays hosted for decisions, because that is what keeps play identical, and it is cheap (under 1 ms a picture in Flycast). Everything that does the heavy work is native.
- A decision function goes native only where the model shows it is hot, and then the outcome check must show play unchanged.
- "Behaviour code itself is not rewritten" stands as the default. The only exception is the one above (a decision function the model shows hot, with the outcome check proving play unchanged), and each such case needs an integrator ruling in HANDOVERS.md.
- Known departures from the GameCube version are kept on a short list: the cap of 4 enemies (owner 2026-10-17; to revisit when the model shows headroom, the owner's call) and the fixed-field pacer's one picture of input delay.

**C. No console until the replatform is complete.**
- Nobody asks the owner for a console evening, an SD card or a date while steps 2 to 5 are under way, and reports do not list it under what the owner must do.
- A milestone's console run is deferred, not waived.
- Status words: "finished, unaudited"; after its audit and its model, "finished, modelled, not on console"; "done" only after the deferred console run.
- Step 1 (the console evening) is deferred to the end of the replatform, or to whenever the owner asks for it.

**D. The defensive model replaces "the console decides" for now.**
- Tiers, each number labelled: **console**; **MODELLED (strict Flycast, calibrated)**; **MODELLED (PC hardware model)**; **Flycast** (plain, function checks only); **estimate**.
- Strict Flycast is the interpreter build (`Dynarec.Enabled = no`; slots `E:\RE4DC-Lanes\eng-e1d\fly1` and `fly2`) with the upstream option `[config] Sh4Clock` (MHz, default 200, upstream since v2.2; this project's builds are v2.7-14-g12bb43652).
- The clock is calibrated on the old port. Its five benchmark scenes have real console means from Test 27.1: village cross 56 ms, bell fight 53 to 60 ms, farm entry 44 to 58 ms, farm hay-fork view 96 ms, farm quiet view 34 ms. The lowest clock any scene needs is the defensive clock; the spread across scenes says how far one factor can be trusted. Lane eng-cmp1 is producing the first calibration: see `engine/COMPARISON_20261121.md` when it lands.
- A figure passes its budget row on the model's worst case, not its mean. The half-row rule (section 8) holds for uncalibrated figures: plain Flycast, and the PC hardware model before it is re-fitted. A calibrated strict-Flycast figure is judged on its worst case against the full row, less a margin equal to the calibration's spread across the benchmark scenes; it must fit the row at the defensive clock, which is already the slowest clock any scene needs.
- Cost is also read from the code: the images' own per-picture counters and the PC hardware model.
- With every modelled number, list what the model cannot see: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing.
- Speed work goes where the code and the model say the cost is, and is judged on the calibrated model. No speed claim rests on plain Flycast.

**E. The old port is a measuring stick.** It may be measured as a baseline beside the engine: same scenes, same tier, same measure, with what each side draws and runs stated. It is never tuned, profiled or fixed, and nothing chases exact agreement between the two. Customer-facing speed claims need a console number or an explicitly labelled model figure, and the owner's OK before anything is posted.

**F. Work that proceeds without the console** (H-020): native services for the fight and boss images; hosting of the systems chapter 1 needs (room loading, doors, items, sound, events); look items the owner approves from stills. At most two lanes; every merge through the integrator's gate.

**What this supersedes:**
- Step 1 in section 7 (the console evening first): deferred to the end of the replatform, or whenever the owner asks.
- "The console decides" (sections 1, 3, 7, 9 and 10): read as the defensive model until the deferred console run.
- The gates in section 8: judged on the model meanwhile; the console run of each milestone is owed at the end.
- Section 12, decisions 1 and 4 (the console evening date, the console loop hardware): deferred to the end of the replatform.
- The "Done when" cells of steps 2 to 4 and section 3 item 6: met on the calibrated model; the console run is deferred.
- Step 6: starts once chapter 1 holds the floor on the calibrated model and runs beside step 5 as planned; each enhancement is still approved by the owner from still pairs or a clip; its console confirmation is deferred with the rest.

## 1. Goal and bar

- **Goal:** all of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets.
- **Then surpass the PS2 version** (owner 2026-11-20: "surpass the ps2 version with surreal Dreamcast strength enhancements"), using what this console does better. It comes after the floor is held, never instead of it (step 6 in section 7).
- **Floor:** 30 fps. At most two 60 Hz fields between presented pictures, judged on the worst interval, not the mean.
- **Correct means "plays right and looks right":** same kills, triggers, doors, waves, room clears and cutscenes; no desync or stuck events; the look approved by the owner from still pairs. Not bit-exact.
- **Never changed:** behaviour (collision results, event sequencing, game state, AI decisions), enemy cap 4, no GameCube assets.
- **Console decides.** Emulator and model numbers are filters. They under-read the console by 1.3 to 2 times. (amended 2026-11-21, see Amendments)

## 2. Where we are (2026-11-20)

| What | Before | Now | Tier |
|---|---:|---:|---|
| Drawing work, village cross | 34.1 ms (old game: drawing plus publication) | 17.3 ms | console vs MODELLED |
| Services, hill, Leon and Ashley | 17.5 ms (original units) | 6.8 ms | MODELLED |
| Whole picture, village, Leon alone | 56 ms (old game at the cross) | 18.6 ms | console vs MODELLED |
| Whole picture, hill, Leon and Ashley | | 30.5 ms mean, 3 of 25 over 33.3 | MODELLED |
| Whole picture, four-Ganado fight | 56 ms (old game) | 24.1 ms, drawing 16.2 in fight pictures | console vs MODELLED |

- **Built:** the bench renderer; Leon, Ashley, four Ganados and El Gigante running their original behaviour on the engine; native skeleton, collision queries, cloth, animation keys and effects; the plays-right reference and tools; a remote console loader (PC-tested only).
- **Passed (audited):** E0, on the model only.
- **Not passed:** E1. The audit (H-011) found original service code still linked, small per-picture conversions, rumble on the game's random numbers, a heap overlap, and a stale disc.
- **Never done:** a console run of the engine. Every engine number is MODELLED or Flycast, and the model has under-read the console by 1.3 to 2 times.
- **The open risk:** drawing is over its 14 ms row in every scene on the model, and the cheap content steps saved only 0.5 ms.

What the two days taught us (full list in the retrospective):
- Hosting the original decisions is nearly free (under 1 ms a tick). The time is under them.
- Drawing the same content better gains 18 to 30%. Removing publication and replacing services gains far more.
- Audits catch what lane summaries miss. Three audits, three corrections.
- Without the console we drift: more lanes, more model rounds, more checking against the old game.
- (2026-11-21) The lesson stands. The guard while the console run is deferred is the calibration against the old port's real console numbers, the worst-case rule and the listed blind spots, and the deferred run still has to happen before anything is called done.

## 3. The approach

Same as F-Zero X, adapted to "original behaviour hosted on the engine" (the owner's choice).

1. **A whole-frame budget first,** with the hosted original as its own rows (section 4). Every lane reports against its row. Nothing is reported as a percentage of the old game.
2. **No publication layer.** Engine state is draw state.
   - Actors, effects and world pieces live in engine tables in the form the renderer reads.
   - Behaviour code changes them through thin setters (position, animation and time, flags, spawn, kill). It never hands the engine an object to convert.
   - The skeleton is evaluated once, straight into the matrices the skinning uses.
   - Effects are simulated in arrays that are submitted as they are.
3. **Host only the decisions.** What an enemy decides and what an event does stays original code. Everything under it (drawing, effects, skeleton, collision queries, object and actor tables, memory, loading) is the engine's, native from the start of each milestone, not migrated later.
   - **No original service code enters the engine image** (owner 2026-11-19, "Split it"). A hosted character uses the native engine service or a logged stub, never the original service unit "for now".
   - **Random numbers are split.** The original generator serves behaviour only (AI, damage, spawns, game logic). Presentation randomness (effects, cloth, aim and camera sway) comes from an engine generator, so native effects and cloth are designed for the Dreamcast, not copied call for call.
4. **Content built for this console,** with the owner approving the look (section 6). Not the PS2 content drawn one for one.
5. **A separate engine image** on the `engine` branch. It is not a set of switches in the old port. The old port is frozen.
6. **Vertical-slice milestones,** each ending in a console run (section 7). (amended 2026-11-21, see Amendments: each ends on the calibrated model; console run deferred)
7. **Plays right against a reference,** with tolerances agreed before each checkpoint (section 8).
8. **SH4ZAM for all math and kernels,** improved in its own style where it falls short.

## 4. Whole-frame budget (33.3 ms a picture, one logic tick a picture)

Measured on console (session 2026-11-12, Test 27.1, cap 4): each row's share of the profiler samples times that capture's ms a picture. Method, function lists and the rule for each borderline function are in [engine/SHELL_MAP.md](engine/SHELL_MAP.md) section 0. These are means; the samples are too few for a worst interval per row.

| Row | What it is | Cross | Bell fight | Hay-fork view | Quiet farm | Budget |
|---|---|---:|---:|---:|---:|---:|
| Behaviour (hosted original) | AI decisions, player, events, scripts | 1.6 | 1.6 | 1.5 | 0.7 | 2 |
| Services | Skeleton and pose, effect simulation, collision queries, managers | 15.5 | 17.9 | 26.3 | 13.0 | 9 |
| Publication | Original state converted to draw data: selection, light and model setup, effect transforms, per-part bookkeeping | 16.3 | 17.5 | 31.4 | 8.7 | 0 by design |
| Drawing | Transform, light, clip, submit | 17.8 | 19.7 | 30.6 | 9.0 | 14 |
| System | KOS, audio, link, idle | 3.9 | 4.3 | 5.6 | 2.9 | 3.5 |
| Margin | Headroom for the worst interval | | | | | 4.8 |
| **Total** | | **55.1** | **61.1** | **95.4** | **34.4** | **33.3** |

What the measurement says:
- **The original decision code costs almost nothing:** 0.7 to 1.0 ms a tick. Hosting it is not the problem, and rewriting it would buy nothing. (Read with Amendments B: behaviour code is not rewritten by default; the one exception is a decision function the model shows hot, with the outcome check proving play unchanged, each case ruled by the integrator in HANDOVERS.md.)
- **Publication plus services are 32 of the 55 ms at the cross,** and 58 of the 95 ms at the worst view. That is where the frame is won.
- **Publication is flat:** 378 functions, the top 12 only about 30% of it. It cannot be tuned away function by function. It goes by design.
- **Services need the biggest real cut:** skeleton and collision are called from inside behaviour, 6.7 ms a tick at the cross.

Rule: a row over budget on console is that lane's problem before anything else moves. (amended 2026-11-21, see Amendments)

## 5. Architecture

| Layer | What it is |
|---|---|
| **Bake** (PC) | PS2 sources to room packs: whole-room compact world with per-piece bounds and baked visibility per cell; characters as bone-sorted streams with distance levels; effect atlases; collision and room tables in engine form; mip-mapped VQ and palette textures. First whole-room bakes: village 1.42 MB, farm 1.09 MB |
| **Engine core** | Main loop, pacer, frame-time governor, its own memory map, room and disc loading, saves, audio, movies, QA link and counters |
| **Engine services** | Renderer, effect simulation, skeleton and pose, collision queries, actor and object tables, lights. Data laid out for an 8 KB instruction cache and a 16 KB data cache |
| **Behaviour** | Original AI, player, event, script and room code, compiled against the engine's interfaces |

Two images: the **bench** (engine plus recorded inputs, no game code, the permanent console benchmark) and the **game** (engine plus behaviour).

## 6. Content for this console (owner look calls)

The graphics chip is 20% busy at the cross. The CPU is the limit. So spend the chip and save the CPU. Each item is shown as a still pair, and the owner approves the lowest step.

| Item | What changes | Why |
|---|---|---|
| Baked visibility per cell | Pieces, props and enemies that cannot be seen from a cell are not processed | Ten hidden props cost about 22 ms at one view (console) |
| Distance levels for characters and props | Fewer vertices and bones with distance; far props as flat cards | Characters are vertex bound |
| Distance cap and world levels | A stable ranked cap on world pieces with hysteresis | F-Zero's cap and level shift bought its last margin |
| Effects | Density caps; simulate only what can be seen | About 400 effects live, about 20 drawn |
| Shadows and lights | Baked where the scene is static; chip shadows only near the camera | Per-part light setup is a publication cost |
| Texture detail over vertex detail | Detail moves into textures and alpha, which the chip handles | The chip has headroom |

Results so far (lane eng-look, MODELLED, owner's choice 11-19 "Lets go with best options"): character levels step 3 and effect cap step 2 are engine defaults (about 0.5 ms together, no visible change). The world distance cap left holes in the farmhouse and needs a rework; flat cards and baked lighting gained nothing in the two bench scenes. Baked visibility is in, whole room in 256 KiB.

## 7. The path from here

One milestone at a time. Each ends with an audit and a console run, and only then is it done. (amended 2026-11-21, see Amendments)

| Step | What | Done when | Rough size (estimate) |
|---|---|---|---|
| **1. Console evening** (amended 2026-11-21, see Amendments) | The owner's SD card and one evening: today's game with each part switched off (lab disc, about 85 minutes), then one engine disc with the bench, Leon and Ashley, the fight and El Gigante | We have console numbers for every budget row and the model's real error | One evening; one lane round beforehand to build the single engine disc and finish the loader's proof |
| **2. Pass E1: Leon and Ashley** | Fix the audit's list (H-011): no original service code, no per-picture conversion, rumble, the heap overlap, the village check, the look differences | Link check clean; Codex audit passes; console run holds the floor in the village and on the hill (amended 2026-11-21, see Amendments: on the calibrated model; console run deferred) | 4 to 6 lane rounds |
| **3. Pass E2: fight and boss** | The four-Ganado fight complete (a kill, doors, weapons, items, sound in the fight); El Gigante drawn with his events; drawing brought inside its row by whatever step 1 shows is needed | Outcome check passes (same kills, damage, waves, triggers); audit passes; console floor in the fight and the boss fight (amended 2026-11-21, see Amendments: on the calibrated model; console run deferred) | 8 to 12 lane rounds |
| **4. E3: chapter 1 playable** | Room loading, doors, events, cutscene movies, items, the merchant, saves and sound, from the first room to the lake boss | A no-warp play-through on console at the floor; the owner plays it; first engine release (amended 2026-11-21, see Amendments: on the calibrated model; console run deferred) | 20 to 30 lane rounds |
| **5. E4: the rest of the game** | Chapter by chapter: bake, host, budget, play-through, release. Disc 1, then Disc 2, then Disc 3, bosses included | Each chapter released | Sized per chapter after step 4 |
| **6. Beyond the PS2 version** | Enhancements that spend the graphics chip and video memory, not the CPU (table below). Starts once chapter 1 holds the floor on console; then runs beside step 5, one enhancement at a time | Each enhancement approved by the owner from still pairs or a clip, with the console floor still held (amended 2026-11-21, see Amendments: starts once chapter 1 holds the floor on the calibrated model and runs beside step 5 as planned; each enhancement still approved by the owner from still pairs or a clip; its console confirmation is deferred with the rest) | Sized per enhancement |

A lane round is one briefed lane to its hand-back; they took one to three hours on 11-19. These sizes are low-confidence estimates.

**What step 1 decides.** The console drawing number at the cross sets the next move (amended 2026-11-21, see Amendments):

| Console drawing at the cross | What it means | Next |
|---|---|---|
| At or under 14 ms | Drawing fits | Steps 2 and 3 as written |
| 14 to 20 ms | Over, within reach | One lane on drawing (frame-time governor, reworked world levels) alongside step 2 |
| Over 20 ms | The drawing design is short | A drawing redesign round before hosting more; the owner chooses between deeper content cuts and a lower floor if two designs miss |

**When the console is not available,** work moves to things whose value does not depend on timing: hosting game systems (doors, items, events), tools, the play-through script. No speed tuning on the model. (amended 2026-11-21, see Amendments)

**Step 6 candidates.** The chip is about 20% busy at the village cross and about 3 MB of video memory is free in a whole room on the bench, so these fit where the console has room. Order is by expected effect for the cost; the console decides each.

| Enhancement | What the player sees | Costs |
|---|---|---|
| Sharper textures | More texture detail than the PS2's 4 MB of video memory allowed; mip-mapped, so less shimmer | Video memory. Needs the asset decision below |
| True shadow volumes | Real character and prop shadows on the ground and walls, where the PS2 used blobs | Chip; a little CPU per caster |
| Sorted transparency | Smoke, fire, water and hair layered correctly | Chip only |
| Anti-aliasing and 480p VGA | Cleaner edges, progressive picture on a VGA box | Chip fill |
| Bump-mapped surfaces | Stone, wood and metal that catch the light | Chip, video memory, some CPU per lit object |
| Memory-card screen | Health or ammo on the controller's screen | Almost nothing |

The asset decision: the owner's rule is PS2 assets only, and the PS2 set is the lower-detail one. Sharper textures and models need either reworked or upscaled PS2 art, or the GameCube originals that the rule forbids today. The other five rows need no asset change.

**Milestone contents** (unchanged from version 2):

| # | Slice |
|---|---|
| **E0** | Walkabout: the world drawn from the whole-room bake. Done on the model; console pending |
| **E1** | Leon and Ashley on the engine: native skeleton, collision and cloth; original player and partner behaviour hosted; HUD, aiming and shooting. (The player host with Ashley as the controlled character is proven in E4 with her castle section: H-016.4) |
| **E2** | Fight and boss: four Ganados with original AI on native services and effects; a first Disc 1 boss |
| **E3** | Chapter 1 end to end, every Disc 1 boss fight, first engine release |
| **E4** | The rest of the game by chapter |

**Backlog** (owner asks and open items not in the current step; the integrator proposes where each fits):
- Ashley as the controlled character (her castle section, E4).
- The lake fight as a boss scene (needs Leon's boat mode).
- Per-room animation clip sets from real play captures.
- Enemy flails and wind setup as native cloth.
- Disc 2 play-through from the r207 sword puzzle on.
- Test 28 on the release line (the lake-fight fixes), when a tester reading comes back.
- The automatic console loop beyond the loader (smart plug, broadband adapter), if the owner has the hardware.

## 8. Gates (per milestone, once, on the final image) (amended 2026-11-21, see Amendments)

| Gate | Rule |
|---|---|
| **Frame floor** | Console, 600 pictures per scene: at most two fields between presented pictures. Report mean, p99, worst interval and count over budget. A passing p99 does not establish the floor. Before a console number, a model figure counts only if it fits half the row (amended 2026-11-21, see Amendments: half the row holds for uncalibrated figures, plain Flycast and the PC hardware model before it is re-fitted; a calibrated strict-Flycast figure is judged on its worst case against the full row, less a margin equal to the calibration's spread across the benchmark scenes, and must fit the row at the defensive clock) |
| **Plays right** | A reference build of the original code on the same inputs. Gameplay equivalence (owner 10-19 bar): same hits, damage, kills, spawn and wave order, triggers, door and event order, room clears, cutscenes, item and save state; no stuck events. Positions and angles within agreed tolerance where actors do the same thing. Generator state is not compared (it is split, section 3) |
| **Determinism** | Two runs with the same inputs give identical frame tables and state hashes. The engine's PC build matches its SH-4 build at checkpoints |
| **Looks right** | Owner-approved still pairs and clips against the PS2 original |
| **Memory** | RAM and VRAM maps with no overlap, stack guards, floors at the fight low point, no failed allocations |
| **Disc** | No disc reads during play; the GDEMU race gate |
| **Controls** | Every check ships with an input that makes it fail |
| **Old port untouched** | The release line still builds as it did |

## 9. Workflow

- **Branches:** `engine` is the integration line; lanes are `lane/eng-<topic>`; the release line (`t15/int`) takes hotfixes only.
- **Who does what:** lanes run as Claude Opus agents, briefed and steered by the integrator. Codex audits each milestone, and any number about to drive a decision.
- **Work in progress:** one milestone at a time, at most two lanes. New scope goes to the backlog in section 7, not into a new lane.
- **Done means audited and run on the console.** Until then a lane's status is "finished, unaudited", and that is how it is reported to the owner. (amended 2026-11-21, see Amendments)
- **Merge gate, checked by the integrator, not taken from the lane's summary:**
  - the link check passes (no original service symbol outside the allowed list);
  - the lane's controls are re-run;
  - every image still links;
  - the rules in section 3 hold.
- **Plays right by outcome.** A scripted player runs on the engine and on the reference; kills, damage, waves, triggers, events and time to clear are compared, with positions within tolerance where actors do the same thing. No tick-exact matching with the old game.
- **One console disc.** A single engine disc is rebuilt from `engine` for each console session. Lanes do not stage discs for the console. (amended 2026-11-21, see Amendments: one disc on the shelf, rebuilt when a milestone closes on the model)
- **Console cadence.** Each milestone's console run is booked with the owner before the milestone starts. The remote loader makes later runs card-free once it is proven. (amended 2026-11-21, see Amendments)
- **Records:** numbered hand-overs (`H-NNN`) in `engine/HANDOVERS.md`; the board is `engine/STATUS.md`; briefs from the template and checklist in `engine/LANES.md`.

## 10. What stops

- Any work to improve, re-measure or re-profile the old port's drawing or its switches.
- Reporting anything as a percentage of the old game, or as done before its audit and console run.
- Model-only speed rounds: one per milestone at most, none while the console is unavailable. (amended 2026-11-21, see Amendments)
- Linking original service code to get something running. Each milestone starts with its services native.
- More than two lanes, more than one milestone, or a new lane for a new idea.
- Tick-exact matching with the old game; identity and STRICT gates anywhere on the engine line.
- A disc per lane.

## 11. Owner directions on record

| Date | Owner's words | Meaning |
|---|---|---|
| 10-12 | (paraphrase) Measure the bottleneck before more assembly | Console profile first |
| 10-19 | "Approximation is fine. Exact has been a hindrance to this product" | Plays right is the bar |
| 10-23 | "this game shouldn't have any game cube assets" | PS2 assets only |
| 11-17 | Lab yes, 30 fps, governor OK | M0, the floor, look steps |
| 11-19 | "get to work", confirmed "Yes, all 10 as recommended" | Engine line approved |
| 11-19 | "the engine needs to leverage sh4zam or improve upon it if there are shortcomings" | SH4ZAM is the math base |
| 11-19 | "I don't want to pile on improvement for old work - ensure we are following the guidance and lessons learned to go native." | No old-path work |
| 11-19 | "I want all of the game in a new native improved engine"; chose "Engine owns everything, original behaviour hosted on it" | The engine is the program |
| 11-19 | "we should take the same approach as the fzero session" | This version of the plan |
| 11-19 | "Update instructions and switch to opus to get this work done" | Lanes on Claude Opus; agent files updated |
| 11-19 | "What can we do ahead of me making changes on my end I'm not home and want progress", then "Lets do it" | Four lanes on work needing neither console nor owner calls: E1, look and content steps, PC reference, console loader |
| 11-19 | "we should have leon ashleyh and boses plus neon or ashley on the engine" (read as: Leon, Ashley and the bosses on the engine, with Leon or Ashley as the player) | E1 adds Ashley as partner and the player hosting generic for Ashley; E2 adds a first boss; E3 every Disc 1 boss |
| 11-19 | "Lets go with best options" (on the still sheets) | Character levels step 3 and effect cap step 2 are engine defaults; world cap, prop cards and baked lighting stay at full detail |
| 11-19 | "Is the approach drifting to porting existing code or true architecture for Dreamcast", then "Split it" | No original service code in the engine image; random numbers split between behaviour and presentation; plays right judged on gameplay equivalence |
| 11-20 | "Why did we drift instead of gains - create a clear concise handover and stop al lanes" | All lanes stopped; handover written |
| 11-20 | "We made good progress. Do a retrospective as an Eng team ... then write an updated plan from here to meet our goal" | The retrospective and this version of the plan |
| 11-20 | "Update agent .md and skills and codex.md to improve performance based on the retro"; "Can't we delete the old skills? We should still keep the teleporter / warp or autonomous testing rig" | Agent files rewritten; skills re4dc-engine, -lane, -audit and re4dc-test-rig; old skills removed |
| 11-20 | "Do we have in our plan to surpass the ps2 version with surreal Dreamcast strength enhancements", then "Ok update plan and get to work" | Plan version 3 approved; beyond the PS2 version is a goal and step 6; work resumes at steps 1 and 2 with at most two lanes |
| 11-21 | "We don't want to get stuck in the exact loop and we need a brand new architecture. But customers need to know how much faster the game will run." | The old port is a measuring stick, never tuned (Amendments E; H-019) |
| 11-21 | "I don't want to look at a disc until we've coloelrter the replatforming - you can tell by the code where complexity is. You can also use a stricter emulator build for Flycast look that up so you can do Your own defense modeling." | Read as "completed" and "defensive": no console until the replatform is complete; the defensive model (Amendments C and D; H-021) |
| 11-21 | "Remember re-platform for Dreamcast native port." | The work is the replatform; progress reported as how much of the game is re-platformed (Amendments A) |
| 11-21 | "What makes the most sense? People that have played the GameCube version shouldn't have to think about game play choices it should just run as fast." | The player's test: plays like the GameCube version, runs as fast (Amendments B) |

## 12. Decisions needed from the owner

1. **The console evening:** when the SD card can go in. It is step 1, and nothing is done until it has run on the console. (amended 2026-11-21, see Amendments: not asked while the replatform is under way)
2. **Asset source for step 6:** keep PS2-only (five of the six enhancements still apply), allow reworked or upscaled PS2 art, or allow GameCube originals for textures and models.
3. **El Gigante's lighter PS2 body** (sheet sent 11-19): yes or no.
4. **Hardware for an automatic console loop:** a Dreamcast broadband adapter or serial cable, and a smart plug, if you have them. (amended 2026-11-21, see Amendments: deferred to the end of the replatform)

## 13. What open-source Dreamcast projects do that we do not (survey, 2026-11-19)

Sources: the GTA III / Vice City ports (DCA3), Doom 64 and Wipeout for Dreamcast, the N64 decompilation ports, DMS-Engine, Simulant and GLdc, KallistiOS 2.1 to 2.2, SH4ZAM's own tips page, and the dreamcast.wiki hardware notes. Fps claims in those sources are their authors' own. Links are in `engine/SURVEY_20261119.md`.

Checked against our build first:
- **Data cache:** a KallistiOS bug (late 2023 to mid 2024) left programs with half the data cache. We are not affected: our KallistiOS is 2.2.2 and its cache default has the full 16 KB on.
- **Already have:** store-queue submission, double-buffered vertex buffer, console performance counters, an on-console sampling profiler, compact vertices, offline conversion.

| # | Gap | What the others do | Where it goes |
|---|---|---|---|
| 1 | **No automatic console loop** | One project power-cycles the console with a smart plug, uploads the new program over the network loader, and logs to a file. Program changes never need a card swap | Tooling lane, before E1. Needs the owner's hardware answer (section 12) |
| 2 | **Vertex staging in cache RAM, sized right** | DCA3 freezes half the data cache as an 8 KB work area, runs each stage in place over a meshlet of at most 128 vertices, and submits from it. Our earlier trial (bigger pieces, old port) lost 8.2 ms on console | E0 arm on the bench, console decides |
| 3 | **Small stage loops over small blocks** | Several small loops (positions, then lights, then UVs) over blocks of about 32 vertices, not one big per-vertex loop | E0 arm |
| 4 | **Clip class per meshlet by bounding sphere** | Outside: skipped. Inside: a no-clip loop. Only boundary meshlets clip | E0 (partly built in round 3) |
| 5 | **Compiler settings** | Size-optimised everywhere with speed-optimised hot files, link-time optimisation, fast math, no debug asserts. DCA3 was within 1 fps of full speed-optimised at nearly 1 MB less code. Watch for slow double-precision paths | Engine build from E0. Our old port had none of these |
| 6 | **Store-queue waits counted apart from cache stalls** | A queue flush can wait up to 500 bus cycles when the chip is busy; interleave work between flushes | M0 session: add the counter events that separate the two |
| 7 | **Stall counters per subsystem** | KallistiOS 2.2 scope probes count two chosen events per code block | Engine core from E0 |
| 8 | **Memory hygiene rules** | 32-byte-aligned matrices; co-used data within 2 KB; no two hot buffers 16 KB apart (they evict each other) | Bake and engine tables |
| 9 | **Compacting VRAM allocator** | Evict least used, defragment with a move callback, report largest free block | Engine core, E3 |
| 10 | **Disc streaming by DMA** | KallistiOS 2.2 has interrupt-driven disc reads with a completion callback | Engine core, E3 |
| 11 | **Lights in model space** | Move each light into model space once per draw, so normals are never transformed | E1 characters |
| 12 | **Emulator as a rule checker** | Every hardware mistake found becomes an emulator assert; a PC build runs under memory checkers | E1 onward |

Not found anywhere: a Dreamcast project that documents baked visibility, portals or occluders. Our baked visibility per cell (section 6) has no public model to copy; it is ours to build and prove.
