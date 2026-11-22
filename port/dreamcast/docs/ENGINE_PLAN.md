# RE4 Dreamcast engine plan, version 3.3 (2026-11-20, amended 2026-11-21 and 2026-11-22)

Status: **approved by the owner on 2026-11-20** ("Ok update plan and get to work"), with "beyond the PS2 version" added as a goal and as step 6. Version 3 keeps version 2's budget, architecture and rules; its path is section 7, written after the retrospective ([engine/RETRO_20261120.md](engine/RETRO_20261120.md)). Version 3.1 adds the amendments below. Version 3.2 adds "The plan as of 2026-11-21", which the owner asked to have written down ("ok memoralize that plan and ensure the skill sare up to date"). Version 3.3 (2026-11-22) adds its section 8, "What we take from the old port", at the owner's word ("Integrate into the plan what we should copy or Integrate from the legacy port engine").

## The plan as of 2026-11-21 (version 3.2)

Start here. This is the current plan in short; the hand-overs (`engine/HANDOVERS.md`, H-019 to H-026) hold the detail and the owner's exact words. Where this section and an older section below disagree, this section wins.

### 1. What we are building

- **The replatform:** RE4 as a Dreamcast native port of the whole game (the owner: "Remember re-platform for Dreamcast native port.").
- **The player's test:** it plays like the GameCube version and runs as fast, at 30 pictures a second (the owner: "People that have played the GameCube version shouldn't have to think about game play choices it should just run as fast.").
- **The look:** the owner: "i want the raw stenghts of the syustem to stand out on a ps3 3d asseet foundation with native dreamcast code" (read: a PS2 3D asset foundation). The PS2 version is the baseline for shapes ("ps2 was primarily to establish hthe baseline geometric shapes etc."); its art is free to be reworked ("sure the ps2 aart can be rewporedm, tetouched, reatpined etc.", read: reworked, retouched, repainted). No GameCube assets (H-026.5).
- **Known departures from the GameCube version:** the enemy cap of 4; quick weapon select (the owner: "i want to keep quiock weapon switch"); one picture of input delay from the fixed-field pacer (H-026.3).

### 2. How it is judged until the end

- **No console disc until the replatform is complete** (H-021). A milestone's console run is deferred, not waived.
- **The calibrated tier:** the console-like Flycast build with its dynarec on at `Sh4Clock` 70, fitted on the old port's console benchmark means (H-023). Label: MODELLED (console-build dynarec at 70 MHz, calibrated on the old port).
- **It is a band** (H-025.3): the standard build fitted the same way reads the engine 3 to 10% kinder in pictures a second. Quote the 70 MHz figure as the pessimistic end and say the band.
- **Worst picture against the budget row,** not the mean. With every modelled number, list what the model cannot see: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing. Plain Flycast is for function checks only.
- **Status words:** "finished, unaudited"; after its audit and its model, "finished, modelled, not on console"; "done" only after the deferred console run.

### 3. Where we are on that model

Lane eng-cmp1's figures (`E:\RE4DC-Lanes\eng-cmp1\COMPARISON.md` section 10), merged. MODELLED (console-build dynarec at 70 MHz, calibrated on the old port); the band is 3 to 10% kinder for the engine.

| Scene | Old port: pictures a second, work a picture (mean) | Engine: pictures a second, work a picture (mean / worst) | Engine drawing / services (row 14 / 9 ms) | Game speed, old port / engine |
|---|---|---|---|---|
| Village route | 15.6, 62.4 ms | 28.9, 34.2 / 44.8 ms | 27.0 / 6.9 | 93% / 96% |
| Hill, Leon and Ashley | 11.3, 86.6 ms | 18.3, 55.0 / 63.1 ms | 36.8 / 17.8 | 76% / 61% |
| Fight at the cross | 16.4, 54.9 ms | 24.2, 37.1 / 53.6 ms | 25.6 / 10.6 | 97% / 81% |

- Neither side holds 30 a second in any of the three scenes. Drawing is about twice its row; services are over theirs on the hill and in the fight.
- When a picture is late the engine slows the game; the old port drops pictures and keeps game time (hill: 61% against 76%).
- The engine does not yet play sound, draw the burning pyre, barrels and other room objects, or handle items and enemy weapons; Leon's handgun is drawn in the first picture only. It runs three test scenes, not the game.

### 4. The tracks

States are from `engine/STATUS.md`. "Done when" is on the calibrated model.

| Track | What | Done when | State |
|---|---|---|---|
| Drawing | The account first, phase by phase. Invisible work first, pixel-identical options before picture-changing ones. Then rooms prepared for the console: lit offline, meshes and distance levels built for it, clean transparency, every pack with a receipt (H-023.1, H-026.5, H-026.6) | Drawing inside its 14 ms row on the worst picture | Lane eng-draw1 running |
| Services | The account by group, then fixes with play unchanged | Services inside the 9 ms row on the worst picture | Lane eng-svcspd1 running |
| Game time | When work for a picture overruns, the next tick runs without drawing, within a bound (H-025.2) | Game speed held in the benchmark scenes | Queued, after the drawing design |
| Native services | The fight image and the boss image to 0 original service functions | Link check 0 for FIGHT and BOSS | eng-e2a merged (fight 114 to 73, boss 57 to 26); lanes eng-e2b (fight) and eng-e2c (boss) running |
| Corrections, game settings, guards (H-026.2) | Built in now; then written into the engine line's copy of the original source, the old port's conditionals deleted by a pass proven by byte-identical objects | Corrections unconditional, settings in one file, guards counted at 0 | Lane eng-fix1 running; the source pass is its own lane after it |
| Chapter 1's systems | Lifted from the old port in the order of section 8 (B). From the salvage inventory (`engine/SALVAGE_20261121.md`): sound (the original driver hosted under the H-025.1 waiver with its cost ceiling), room-to-room loading and doors, the script scheduler, saves and the memory-card screen, the crash screen, route movies, items and the inventory (the 3 MB problem), old-game room recordings as a bake input | Each system working in the engine, judged by outcome against the reference | Lanes eng-snd1 and eng-load1 running; the scheduler, saves and crash screen, route movies, room recordings queued (H-025); items not started |
| Rooms | Every chapter 1 room through the bake, with a census; then the rest of the game by chapter | Every chapter 1 room baked, failures fixed or listed | Lane eng-bake1 running |
| The look | Leon's handgun; effects one at a time on a budget (gameplay feedback, then scene-defining, then ambient; the owner: "We should probably be selective with the effect layer if we are getting these gains without them."); Dreamcast look treatments for one room and for Leon chosen by the owner from still sheets (one variable per sheet, differing-pixel counts, modelled cost); enhancements that cost frame time (shadow volumes, bump mapping, anti-aliasing) only once the floor holds on the model | The owner's choices from stills | Lane eng-look1 running (the handgun, then the muzzle flash); the treatment sheets are next |
| Milestones and audits | One independent audit per milestone. E1's waits for a drawing design that fits its row on the model (H-023.2, H-022). The console run of every milestone is deferred to the end | Audit passed and model held: "finished, modelled, not on console" | E1 audit waiting on the drawing design |

### 5. How the work is run

- **As many lanes as are not redundant and the machine carries** (the owner: "Run as many as possible with an integration lane as long as they aren't redundant"; H-024). Each lane owns named files and one question; the lanes table in `engine/STATUS.md` is the register.
- **One integration lane** (`eng-int`) gates each handed-back lane to [engine/INTEGRATION_GATE.md](engine/INTEGRATION_GATE.md) with its gate script, and is the only one that merges into `engine`. A failed gate goes back to the integrator.
- **One common brief** for every lane ([engine/COMMON_BRIEF.md](engine/COMMON_BRIEF.md)); each lane's own brief adds its files and its question.
- **Emulator slots by lease** (a `LEASE.txt` held only while Flycast runs); `int1` is the integration lane's (H-026.7). Lanes are added only while the machine has room.
- **Working habits from the F-Zero line** (H-026.6): invisible work before content cuts; one variable per arm; a differing-pixel count on every still pair; a receipt on every baked pack; hand back at about 250 tool calls; a speed claim needs its base re-run in the same session.
- **The integrator** briefs, rules, reads each gate report and writes the hand-overs (`LANES.md`, the `re4dc-engine` skill).

### 6. Sizes

From the salvage inventory, in lane rounds (one briefed lane to its hand-back), low confidence: step 3 (fight and boss) 9 to 15 with the drawing redesign; step 4 (chapter 1 playable) 22 to 36; step 5 (the rest of the game) 30 to 55. Its three biggest unknowns:
1. Whether the redesigned renderer's packs still need per-room recordings of the old game, and how far the old port can reach (moves step 4 by about 5 and step 5 by about 10).
2. How many chapter 1 events have no PS2 movie and must run in real time.
3. RAM: chapter 1's 29 room modules plus the sub screen's 3 MiB, inside a map sized from E1. A shortfall forces module overlays or a sub-screen redesign.

### 7. Open with the owner

From `engine/STATUS.md`:
- Look, from still sheets when the owner chooses: the HUD, the near plane fix, the overall picture, old port beside engine; next, the Dreamcast look treatments for one room and for Leon.
- The release line: a hotfix candidate (Disc 2 builds module em1f's copy of em10 without the Ganado byte-order correction).
- El Gigante's lighter PS2 body: yes or no.
- Not asked: a console evening or the SD card.

### 8. What we take from the old port (version 3.3, 2026-11-22)

The owner, 2026-11-22: "I also appreciate your innovation but we should be borrowing things that work fine at a mechanical level from the old build pre re architecture." Then: "Integrate into the plan what we should copy or Integrate from the legacy port engine." (H-032, H-033.)

**The rule.** The old port (release line `t15/int`, read only) is the first place a lane looks. A part of it that works at a mechanical level is lifted and adapted, not written again. The inventory is [engine/SALVAGE_20261121.md](engine/SALVAGE_20261121.md) (54 rows); the row numbers below are its rows.

- **What "lift" means:** the old file is copied into the engine under the engine's name, with the form the Test 27.2 release shipped as one fixed path. Its build switches, debug hooks and old-renderer hooks (`re4dc_` calls) are removed. The head of the file names the old file, the commit and the release settings it carries. Nothing lands switched off.
- **Every lane brief** names the old-port part for its job, or says there is none. Every hand-back says what was lifted and from where, and gives a reason for anything written new where an old part existed.
- **Judged like everything else:** the gate, the calibrated model, the look from stills. A lifted part that is slower or wrong inside the engine is fixed or replaced, with the measurement.
- **What does not change:**
  - The original game's service code (skeleton, collision, effects, camera and the like) stays out of the engine image; the link check holds. The recorded waiver is the sound driver (H-025.1).
  - The old drawing path as a whole is not carried over and is not tuned. One proven routine from it may be lifted and measured inside the engine's renderer.
  - The old port stays buildable to the end of step 5: it is the bake's input, the recorder of rooms and the reference for outcomes.

**A. Already taken** (in `engine`, or handed back and at the gate)

| Part | Old port source | Row | State |
|---|---|---|---|
| Toolchain, KOS base and disc patches, disc table-of-contents fix | `kos-env.sh`, `patches/`, `gdrom_mount.cpp` | 1, 2 | In `engine` |
| Disc read safety (stuck transfer retry, sector-read fallback, drive-not-ready retry) | `platform/dvd_read_safe.cpp` | 3 | Lifted as `core/disc_safe.c`; at the gate with the memory train |
| Sound: Capcom's driver hosted, the AICA backend, the converted sound data | `src/game/snd*.cpp`, `platform/audio_aica.cpp`, `bgm/aica_str.dat`, banks | 20, 21, 22 | Lifted as `services/sound/`; at the gate with the memory train |
| The skinning routine | `platform/avk_sh4.S` | 9 | In `engine` |
| Converted PS2 assets as bake input: textures with mip maps, character packages, motion, sky, worlds | `tex.pak`, cast packages, `em/*.drs`, sky and world sidecars | 10, 12, 14, 17, 48 | In `engine` (the bake reads them) |
| Enemy spawn rules and the cap of 4 | `src/game/em_set.cpp`, room scripts | 38 | In the fight image; every other room as it is hosted |
| The released game's fixes inside the original code | 148 release settings in `src/` | 39 | In `engine` as corrections, game settings and guards (lane eng-fix1) |
| Disc building, the Flycast harness, the PC reference | `tools/d367/mkgdi.sh`, harness, `Makefile.host` | 51, 53 | In `engine` |

**B. Take next: none of these waits for the renderer.** In this order; each is one lane unless noted.

| # | Part | Old port source | Row | What changes on the way in |
|---|---|---|---|---|
| 1 | Room loading at the old port's speed | the old room read path in `platform/dvd.cpp`, `src/game/read.cpp` as reference; packs trimmed at bake | 4, 50 | A door load takes about 60 s in Flycast today because the whole pack, the recording included, is read and checked. The bake drops the recording rows; reads follow the old port's pattern (one pass, streamed). No GameCube queue |
| 2 | The script scheduler on the old thread layer | `platform/os.cpp` (thread section), `src/game/scheduler.cpp` hosted | 6 | Threads, queues and alarms only; the arena, font and reset parts stay behind. Room scripts and events wait on it (133 sites) |
| 3 | Room, enemy and weapon code modules | `platform/modules.cpp`, `tools/gen_modules.py` | 7 | Each module linked in the image with its starting data restored on a fresh link; sizes go into the memory map |
| 4 | The crash screen and the sampling profiler | `platform/crash_screen.cpp`, `pc_sampler.cpp` | 44, 45 | Needs only KOS. The only way to read a console fault without a cable: in before the deferred console run |
| 5 | Old-game recordings of every chapter 1 room; one hashed inventory of the converted data | the old port run by the warp rig; `/root/re4data/private` | 50, 54 | Ten chapter 1 rooms have no recording (lane eng-bake1). A function run of the old port, never tuned |
| 6 | The movie player and the PS2 route movies | `platform/native_movie.cpp`, `native_movie_stream.c`, `route_movie_bridge.cpp`, the call sites in `src/` | 23, 24 | One full-screen quad from the engine's renderer; the 86 old memory hooks removed. 45 movies cover chapter 1's story scenes, so fewer real-time events to host |
| 7 | Memory-card saves and the controller-screen display | `platform/card.cpp`, `vmu_store.cpp`, `vmu_dialog*`, `vmu_context.cpp`, `vmu_render.cpp`, `vmu_lcd.cpp` | 28, 29, 30 | The original save screen stays hosted over the old virtual card; the dialog is drawn by the engine |
| 8 | The QA menu, teleporter, QA link, warp rig and pad scripts | `qa_menu.cpp`, `qa_link.cpp`, `dbgwarp_bridge.cpp`, `tools/d367/warp.py`, `fullplay/`, `route/` | 42, 43 | Presets and fixture format carry; the hooks move to the engine's hosted room entry |
| 9 | The release gates | `fullplay/gdemu_gate.sh`, `kos_squeeze.sh`, `gc_port23`, `kit-check.sh`, `build-public.sh` | 52 | Disc race, memory squeeze, no-GameCube-asset count, contributor kit. Before the first engine release |
| 10 | The per-room fix list, as bake inputs and hosted-code settings | `CH-FIXES-CARRY.md` rows 1-5, 14, 16, 17, 19, 21, 23, 27-30 | 40 | Applied to each room as it is hosted or baked |

**C. Take when the renderer can hold them** (after the drawing row is met on the model, or as the named lane reaches them)

| Part | Old port source | Row | Note |
|---|---|---|---|
| Proven SH-4 routines, measured inside the engine's renderer beside the engine's own | `mtx_sh4.S`, `pwc_sh4.S`, `lnk*_sh4.S`, `lnw*_sh4.S`, `sk1_sh4.S`, `backface_sh4.S`, `pmc*_sh4.S` | 9 | Lane eng-draw4 now. The faster one with 0 differing pixels stays. This re-opens the inventory's "drop" for these files (H-033) |
| The sky as the graphics chip's background plane | `platform/native_sky.cpp` | 17 | Costs no geometry |
| Blob shadows under characters | `game/blob_shadow.cpp` | effects 7 | The cheap released method first; shadow volumes are step 6 |
| The released effect selection ("Essential") | `esp_sub.cpp` keep and cut table, `recipe.conf` | 16 | The order for effects one at a time: feedback, then scene-defining; glows, haze and mist stay out |
| Rain, the PS2 fire and flame sets, the halo cut | `RAIN_DC`, PS2 flame sets, `PS2_FIRE_HALO_CUT` | effects 8, 9, 11 | As each family is brought across |
| Each room's list of resident textures and the video-memory map as knowledge | `vram/resident/rXXX.tsv`, `VRAM-MAP-20261014.md` | 11 | The engine's renderer owns video memory; the lists say what a room needs |
| The button map and prompt pictures | `platform/pad.cpp` | 26 | With the menu and text renderer |
| Picture modes: anti-aliasing, 240-line modes, VGA | `platform/res_mode.cpp`, `vi.cpp` | 47 | Step 6 |
| The water and lake drawing | `native_water_ps2.inc`, `native_lake.cpp` | 19 | Reference only: the engine's water is new; the old look is the target |

**D. Not taken, and why**

| Part | Why |
|---|---|
| The GameCube drawing emulation, its caches and its 1,201 speed settings (`gx_stub.cpp`, `native_static.cpp`, `native_actor_fast.cpp`, `coarse_*`, link-order scripts) | It converts drawing calls each picture; it is the 34 to 96 ms a picture the replatform exists to leave (row 8) |
| The GameCube disc API shim and read queue | The engine's loader opens nothing in play (row 4); only its read pattern is a reference (B1) |
| The original movie front end | It parks 5 MiB in memory the Dreamcast does not have (row 25) |
| The inventory screens' memory trick (3 MiB packed into video memory) | Tied to the old renderer's video memory; the memory map's owner places those bytes (rows 35, 41). The screens' logic stays hosted |
| The old quality options, the call profiler, knob-off identity and STRICT | They tune or check the old renderer (rows 37, 45, 52) |

**Lanes this starts.** B2 (scheduler) and B4 (crash screen and profiler) start now: their files are new and overlap no running lane. B1 and B3 follow the memory train's merge (the same files). B5 to B8 start as the machine has room, B5 first (recordings are the long pole for bakes). The lanes table in `engine/STATUS.md` is the register.

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
- Strict Flycast is the console-like build (slots `E:\RE4DC-Lanes\eng-e1d\fly1` and `fly2`) with its dynarec on and the upstream option `[config] Sh4Clock` (MHz, default 200, upstream since v2.2; this project's builds are v2.7-14-g12bb43652) at the calibrated clock: 70 as fitted on the old port on 2026-11-21 (H-023). The interpreter ignores `Sh4Clock`, so it is not this tier (corrected the same day).
- The clock is calibrated on the old port. Its five benchmark scenes have real console means from Test 27.1: village cross 56 ms, bell fight 53 to 60 ms, farm entry 44 to 58 ms, farm hay-fork view 96 ms, farm quiet view 34 ms. The lowest clock any scene needs is the defensive clock; the spread across scenes says how far one factor can be trusted. Lane eng-cmp1 is producing the first calibration: see `engine/COMPARISON_20261121.md` when it lands.
- A figure passes its budget row on the model's worst case, not its mean. The half-row rule (section 8) holds for uncalibrated figures: plain Flycast, and the PC hardware model before it is re-fitted. A calibrated strict-Flycast figure is judged on its worst case against the full row, less a margin equal to the calibration's spread across the benchmark scenes; it must fit the row at the defensive clock, which is already the slowest clock any scene needs.
- Cost is also read from the code: the images' own per-picture counters and the PC hardware model.
- With every modelled number, list what the model cannot see: the graphics chip's fill and sort time, vertex submission through the store queues, memory bus contention, real disc timing.
- Speed work goes where the code and the model say the cost is, and is judged on the calibrated model. No speed claim rests on plain Flycast.

**E. The old port is a measuring stick.** It may be measured as a baseline beside the engine: same scenes, same tier, same measure, with what each side draws and runs stated. It is never tuned, profiled or fixed, and nothing chases exact agreement between the two. Customer-facing speed claims need a console number or an explicitly labelled model figure, and the owner's OK before anything is posted.

**F. Work that proceeds without the console** (H-020): native services for the fight and boss images; hosting of the systems chapter 1 needs (room loading, doors, items, sound, events); look items the owner approves from stills. At most two lanes; every merge through the integrator's gate. (The lane count is superseded by H-024: see the plan as of 2026-11-21 above.)

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

(see the plan as of 2026-11-21 above for the current order)

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
| 11-21 | "We should probably be selective with the effect layer if we are getting these gains without them." | Effects one at a time on a budget (H-023) |
| 11-21 | "Run as many as possible with an integration lane as long as they aren't redundant" | Lanes by ownership, one integration lane (H-024) |
| 11-21 | "i want to keep quiock weapon switch" | Quick weapon select stays, a game setting and a known departure (H-026.3) |
| 11-21 | "sure the ps2 aart can be rewporedm, tetouched, reatpined etc."; "ps2 was primarily to establish hthe baseline geometric shapes etc." | The PS2 version sets the shapes; its art may be reworked; no GameCube assets (H-026.5) |
| 11-21 | "i want the raw stenghts of the syustem to stand out on a ps3 3d asseet foundation with native dreamcast code" | Read as a PS2 3D asset foundation; the look built to show the Dreamcast's strengths (AGENTS.md) |
| 11-21 | "more slots is ok adjust based on computer utilization" | Slot `int1` for the integration lane; lanes by machine load (H-026.7) |
| 11-21 | "ok memoralize that plan and ensure the skill sare up to date" | The plan as of 2026-11-21 (version 3.2) |

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
