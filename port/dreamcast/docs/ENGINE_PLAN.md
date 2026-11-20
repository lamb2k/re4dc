# RE4 Dreamcast engine plan, version 2 (2026-11-19)

Status: **draft for the owner.** It follows the owner's directions of 2026-11-19 (section 9) and takes the approach of the F-Zero X Saturn engine line. The section 7 milestones replace the earlier M1 to M5 once approved; M0 is unchanged.

Every number is labelled: **console** (real Dreamcast, GDEMU), **MODELLED** (PC hardware model), **Flycast**, **emulator** (another project's emulator), or **estimate**.

## 1. Goal and bar

- **Goal:** all of the game in a new native Dreamcast engine, playable on a real console, from PS2 assets.
- **Floor:** 30 fps. At most two 60 Hz fields between presented pictures, judged on the worst interval, not the mean.
- **Correct means "plays right and looks right":** same kills, triggers, doors, waves, room clears and cutscenes; no desync or stuck events; the look approved by the owner from still pairs. Not bit-exact.
- **Never changed:** behaviour (collision results, event sequencing, game state, AI decisions), enemy cap 4, no GameCube assets.
- **Console decides.** Emulator and model numbers are filters. They under-read the console by 1.3 to 2 times.

## 2. What we learned on 2026-11-19

| Finding | Source |
|---|---|
| Drawing the same content more efficiently gains 18 to 30%, not 50% (MODELLED, audited) | Bench audit, `E:\RE4DC-Lanes\eng-bench\AUDIT-M1-R2.md` |
| The work the first bench skipped is where the time is: choosing what to draw (2.8 ms at the cross), light and model setup (1.2 to 3.9 ms), effect transforms (3.2 to 6 ms), skeleton (1.9 to 3.9 ms) | Same audit |
| F-Zero X Saturn: about 37 ms of its gain came from no longer hosting the original simulation (22.1 ms) and the "publication" layer that turns original state into draw data (17.3 ms). Native physics plus sprites cost 1.6 ms. Changing what is drawn bought the last 5 to 8 ms (emulator) | F-Zero coordinator, 11-19 |
| F-Zero has not run on hardware yet, and its second milestone misses the floor on 4.7% of intervals | Same |
| RE4 on console: about 60% of CPU samples are in our own port code, about 30% in the original game code; 53% of each picture is memory stall | Console session 11-11 and 11-12 |
| RE4 on console: ten props hidden behind a barn wall cost about 22 ms at the worst farm view | Console A/B 11-12 |

What it means: most of our frame is publication, the port code that converts the original game's objects into things to draw, every tick, for every part. A faster renderer under that layer cannot halve the frame. Removing the layer can.

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
6. **Vertical-slice milestones,** each ending in a console run (section 7).
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
- **The original decision code costs almost nothing:** 0.7 to 1.0 ms a tick. Hosting it is not the problem, and rewriting it would buy nothing.
- **Publication plus services are 32 of the 55 ms at the cross,** and 58 of the 95 ms at the worst view. That is where the frame is won.
- **Publication is flat:** 378 functions, the top 12 only about 30% of it. It cannot be tuned away function by function. It goes by design.
- **Services need the biggest real cut:** skeleton and collision are called from inside behaviour, 6.7 ms a tick at the cross.

Rule: a row over budget on console is that lane's problem before anything else moves.

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

## 7. Milestones

Each is a vertical slice that runs and is shown (stills, a short clip, frame numbers), proves one risk, and ends in a console run. Lanes run in parallel inside a milestone.

| # | Slice | Proves |
|---|---|---|
| **M0** | **Console truth.** The lab disc's core session: today's game with each part switched off. The bench disc in the same evening | The real budget split; the model's margin |
| **E0** | **Walkabout.** The engine image boots to the village. World, sky and lighting are drawn from the whole-room bake with runtime selection. The camera rides a recorded path through the village and the farm. No game code | The world fits its drawing row before any behaviour exists |
| **E1** | **Leon and Ashley.** The player on the engine in the village: native skeleton and skinning from the original animation data, native collision queries, the original player behaviour hosted through setters, HUD, aiming and shooting. Then Ashley's original partner code hosted, following Leon; the player hosting made generic so Ashley can be the controlled character in her castle section | Hosting works with no publication layer; the player and the partner at the floor; handling plays right |
| **E2** | **Fight and boss.** Four Ganados with the original AI hosted on native services, effects, the village fight and the farm, kills, waves and triggers. A first Disc 1 boss on the bench and then hosted, with boss body levels only if the fight is over budget | The floor under load; the services row holds; bosses fit the engine |
| **E3** | **Chapter.** Chapter 1 from the first room to the lake boss: room loading, doors, events, cutscene movies, items, the merchant, saves, sound; every Disc 1 boss fight on the engine | The whole loop, end to end; first engine release |
| **E4** | **Game.** The rest of Disc 1, then Disc 2 and Disc 3 by chapter, bosses included. Each chapter: bake, budget at first pass, no-warp play-through | All of the game in the engine |

Bench round 3 (running) is the start of E0: whole-room bakes and runtime selection exist; its recorded characters and effects carry into E1 and E2.

Stop rules:
- A milestone whose console run misses the floor does not get more tuning rounds on the model. It gets the profile, one fix, and another console run.
- If E0 cannot hold the world's drawing row on console after two genuinely different designs, the owner chooses between deeper content cuts and a lower floor.

## 8. Gates (per milestone, once, on the final image)

| Gate | Rule |
|---|---|
| **Frame floor** | Console, 600 pictures per scene: at most two fields between presented pictures. Report mean, p99, worst interval and count over budget. A passing p99 does not establish the floor. Before a console number, a model figure counts only if it fits half the row |
| **Plays right** | A reference build of the original code on the same inputs. Gameplay equivalence (owner 10-19 bar): same hits, damage, kills, spawn and wave order, triggers, door and event order, room clears, cutscenes, item and save state; no stuck events. Positions and angles within agreed tolerance where actors do the same thing. Generator state is not compared (it is split, section 3) |
| **Determinism** | Two runs with the same inputs give identical frame tables and state hashes. The engine's PC build matches its SH-4 build at checkpoints |
| **Looks right** | Owner-approved still pairs and clips against the PS2 original |
| **Memory** | RAM and VRAM maps with no overlap, stack guards, floors at the fight low point, no failed allocations |
| **Disc** | No disc reads during play; the GDEMU race gate |
| **Controls** | Every check ships with an input that makes it fail |
| **Old port untouched** | The release line still builds as it did |

## 9. Workflow

- **Branches:** `engine` is the integration line; lanes are `lane/eng-<topic>`; the release line (`t15/int`) takes hotfixes only.
- **Who does what (owner 11-19: "switch to opus to get this work done"):**
  - Lanes run as Claude Opus agents, briefed and steered by the integrator.
  - Codex gives one independent audit per milestone.
  - A lane number that is about to drive a decision gets an independent check first.
- **Lanes in parallel:** at most two lanes that build or run emulators, plus up to two PC-only lanes (bakers, analysis, PC tests). The machine is shared with other projects.
- **Messages and board:** numbered hand-overs (`H-NNN`) in `engine/HANDOVERS.md`; the board is `engine/STATUS.md`.
- **Briefs:** from the template and checklist in `engine/LANES.md`.
- **Console:** the owner boots; sessions run unattended over the QA link. Every milestone ends on the console.

## 10. What stops

- Any work to improve, re-measure or re-profile the old port's drawing or its switches.
- Reporting anything as a percentage of the old game.
- Model-only rounds beyond one per milestone.
- Building a native service "later": each milestone starts with its services native.
- A review round per change; identity and STRICT gates anywhere on the engine line.

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

## 12. Decisions needed from the owner

1. Approve the milestones E0 to E4 and the budget rows in section 4.
2. The content items in section 6 as a class, with the lowest step of each approved from still pairs.
3. The SD card and one console evening for M0 and the bench disc.
4. Hardware for an automatic console loop: do you have a Dreamcast broadband adapter or a serial cable, and a smart plug? If not, the loader can use the existing DreamPi link (slower: about 5 to 10 minutes per program).

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
