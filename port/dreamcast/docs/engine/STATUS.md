# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-20):** plan version 3 APPROVED by the owner (H-012). Current steps: 1 (console evening, waits for the owner's SD card) and 2 (pass E1). Two lanes running, both independent of timing. Everything is "finished, unaudited" until its audit and console run.

## Milestones

| # | Slice | State | Console run |
|---|---|---|---|
| M0 | Console truth (lab session) | Lab disc v2 READY (lane/lab33 dc1ca2809, disc from 03b6e57f2, E:\RE4DC-Lanes\lab33\final). Core tier 85 min, std 279 min | Waits for SD card |
| E0 | Walkabout and the drawing row (budget 14 ms console) | Console-ready disc E:\RE4DC-Lanes\eng-e0build\E0-GDEMU-e0b (renderer 1edab55a8, merged). MODELLED 25 pictures: cross 16.3 mean / 22.0 worst, hay-fork 18.8 / 21.1 (the source lighting rule added 1.7 to 2.3 ms). Fixed: near-plane clipping (with a test the old loop fails); visibility safe in unknown cells and heights, whole room in 256 KiB; texture copies released; raw rows per picture with A/B/A arms in one boot. Partly: look (MAE 8.6 cross / 6.2 farm; pyre glow and hair open); unseen cross route differs on 8 of 300 pictures by 1 to 2 pixels. Over budget on the model; content changes wait for the owner | Waits for SD card |
| E1 | Leon and Ashley on the engine | NOT PASSED (Codex audit H-011, E:\RE4DC-Lanes\eng-e1d\AUDIT-E1.md): original service units still linked (actor volumes, collision response, route checks, root-motion follower, model parts, camera and frustum, pad and rumble, math helpers, garment pose); per-picture conversions remain (palette repack, Ashley light record, camera and HUD repack); rumble draws from the game generator; heap 0 and heap 4 alias; village position fails the last 118 ticks unfed; serial prints inside timed rows; staged disc predates the lighting merge. Fixes: eng-svc4 (running, PC) and eng-e1e (queued, emulator) | Waits for SD card |
| E2 | Fight and boss | Fight at the cross runs on the engine (eng-e2, merged, FIGHT=1): Leon and four Ganados with original AI, native skeleton, collision and effects (effects bit-identical to the original on PC). Flycast: busy 16.71 ms mean, drawing 10.58, services 5.28. MODELLED: busy 24.11, drawing 13.94 (16.24 on fight pictures, over 14). Plays right holds for 7 of 16 events, then the AI takes different random choices because of the split; a reference with the same split is being built (eng-ref). El Gigante hosted. Discs E:\RE4DC-Lanes\eng-e2uild\E2-GDEMU-fight, eng-boss | Not run |
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
| eng-svc5 | Step 2 (E1), PC-only: native math helpers, garment pose, SDK math and allocator; strict plays-right reader | lane/eng-svc5 | Claude Opus | E:\RE4DC-Lanes\eng-svc5 |
| eng-e1f | Steps 1 and 2: presented fields in every scene of the console disc, El Gigante bench pack, enemy decision groups in the link check, village plays-right gaps, HUD compositing | lane/eng-e1f | Claude Opus | E:\RE4DC-Lanes\eng-e1f |

Closed: eng-e1d (Opus), handed back 11-20, merged (047589cf0). See the E1 row. Look calls open: Leon's chapter-2 body reads browner than the old game; Ashley's hair drawn opaque; props, ground light pool and handgun not drawn on the hill.

Closed: eng-e1d (Opus), handed back 11-20, merged (fded11182, resolved with eng-e2: draw order Ganados, Leon, Ashley; per-model palette check; per-character light records; FIGHT=1 keeps cloth stubs). The fight image now follows the aim-sway ruling, so its trace differs from eng-e2's run from tick 13 (identical for 900 ticks with AIMSWAY_PRESENT=1). Look calls open: Leon's chapter-2 body browner, Ashley's hair opaque, hill props and handgun not drawn.

Closed: eng-e2 (Opus), handed back 11-20, merged (d6e4969db). See the E2 row. Not hosted yet: doors, windows, ladders, Ganado weapons and carts, items, sound, event data. Still original service units: actor volumes, route checks, root-motion base, parts of model/motion/atari.

Closed: eng-svc3 (Opus, PC-only), handed back 11-19, merged with a link fix (b7a08259d, d12109859: E1 WEAK_motion extended; e1.elf links). RE4MK2 motion keys (float32 bit-identical; 16-bit bones within 0.14 u, traces pass); recommendation: 16-bit rows for a per-room clip set from captured play, 0.10-0.25 MB a room, since rows for all clips do not fit beside the keys. Cloth on SH4ZAM (11.3 KB, no libm; true one pass rejected, 11-54 u off; fused passes 3.5 vs 5.0 a step). Native root motion, bit-identical. Swept sphere on the grid, bit-identical; village square collision 544 -> 470 KB. 52 controls as they must. Open: enemy flails and wind setup still original pendulum code; per-room clip sets from real captures.

Closed: eng-e1c (Opus), handed back 11-19, merged (c4f938b5a). Leon image on the native skeleton and collision; original ik removed; presentation randomness on an engine generator; services in a fixed 1 MB region. Services before -> after: village Flycast 4.81 -> 2.33, MODELLED 6.85 -> 3.08; hill Flycast 12.29 -> 5.10, MODELLED 17.53 -> 6.80. Busy picture: village Flycast 15.93 -> 13.47 mean, MODELLED 21.21 -> 17.92; hill Flycast 19.87 -> 12.67, MODELLED 27.63 -> 17.42. El Gigante services 6.00 -> 4.48 Flycast. Cloth and facial keys are logged stubs for now (cloth does not swing). Integrator ruling: aim sway moves Leon and his shots, so it is behaviour and goes back on the original generator (eng-e1d). Disc E:\RE4DC-Lanes\eng-e1cuild\E1C-GDEMU-native.

Closed: eng-svc2 (Opus, PC-only), handed back 11-19, merged (cc0d1ccf5). Offline motion keys (bit-identical, key segments for Leon 60 to 3 a tick, but rows 1.84x the clips: Leon archives 1.26 to 2.55 MB); bone history cut to what behaviour reads (updateOldPos lines 377 to 71); native cloth on its own presentation generator (wind off bit-identical; wind on within 0.25 u of the original's chain distance); collision grid (polygon tests per line query down 44 to 68%, results bit-identical). 37 controls end as they must. PC counts only.

Closed: eng-e1b (Opus), handed back 11-19, merged (64b0211ba). Ashley's original partner code hosted on the engine (r11d hill, boot option HILL): with the old run's generator fed each tick, every field identical to re4ref for 729 ticks; against the old game (RESUMEA) Leon bit-identical 728 ticks, Ashley within 0.0117 units, routine exact; follow-distance control fails at tick 78. Flycast busy picture 19.46 / 26.74 ms (no world drawn); services over budget (11.86 ms: Ashley's cloth 3.55, motion 4.81, original code). Two full-field old-game fixtures recorded (hill, bell gate). Drawn as bone markers only: no Ashley mesh or r11d world bake yet. Fixed: E1 image link break after the look merge, empty punch-through list stall.

Closed: eng-boss (Opus), handed back 11-19, merged (f6af771dc). El Gigante (village square r119). Bench, full body: MODELLED 19.98 mean / 25.41 worst (characters 9.9, world 5.2, translucent 3.3); Flycast 15.53 / 22.00, no interval over 2 fields. Lighter PS2 body (g50): 18.36 / 22.49 MODELLED, MAE 0.52, sheet sent to the owner. Original boss AI and room script hosted on the E1 shell: attack sequence exact for 8 of 10 changes, motion, state and hp exact to tick 867, hut break on the same tick; hosted rows Flycast behaviour 1.41, services 5.06, publication 0. Effects recorded, not simulated. Discs E:\RE4DC-Lanes\eng-bossuild\BOSS-BENCH-GDEMU and BOSS-HOSTED-GDEMU.

Closed: eng-svc (Opus, PC-only), handed back 11-19, merged (bcc08c170). Native skeleton (SoA per actor, one parent-order pass in SH4ZAM XMTRX) and collision (flattened block tree, hot and cold polygon records) equal to the original units on six fixtures (bones equal as numbers, collision identical, plays-right pass); three controls fail as they must. Behaviour touches only 13 to 22 of Leon's 119 bone records. Skeleton memory accesses down 30 to 42%. Not yet in the E1 image; no SH-4 timing. Doc: SERVICES.md.

Closed: eng-look (Opus), handed back 11-19, merged (26c3746c8). Hair fixed (+1 ms MODELLED from re-skinning), pyre glow approximated, unseen-route visibility down to 1 pixel on 1 picture, light-pick control added. Step 0 MODELLED: cross 17.3 mean / 23.2 worst, hay-fork 19.6 / 22.1. Content steps barely move these two scenes: character levels L3 -0.45 ms (invisible), effect cap E2 -0.04 ms (invisible); world cap W2 -0.4/-1.6 ms and W3 -2.2/-3.1 ms leave visible holes; props as cards and baked lighting gain nothing here. Sheets sent to the owner. Disc E:\RE4DC-Lanes\eng-lookuild\E0-GDEMU-lkg.

Closed: eng-host2 (Opus, PC-only), handed back 11-19, merged (9dd87b9cb). re4ref now hosts Ashley (pl_npc, pl11: 37 KB code) and a Ganado (em10 and 8 files: 293 KB code); per-actor trace lines; 10 controls pass. Agreement with old-game traces (position only, every 4th tick): Ganado within 0.002 units over ticks 185-317 at the bell gate until the room event freezes it; Ashley within 0.018 units over ticks 185-289 at the r11d hill until the room's opening event. Needs two emulator fixtures recorded with full per-actor fields (listed in its hand-back).

Closed: eng-host (Opus, PC-only), handed back 11-19, merged (41c045240). re4ref: PC build of the 20-file player and camera closure; plays_right.py with tolerances and three failing controls (walk speed +2%, one generator call dropped, input one tick late: all fail as they must). Agreement with the old game's door103 walk: 323 ticks within tolerance, discrete fields exact, position bit-identical on 272 ticks. Found a real bug: cAtariInfo::init declared with float arguments first. Doc: PLAYS_RIGHT.md.

Closed: eng-loop (Opus, PC-only), handed back 11-19, merged (907bb1a24). Remote console loader over the DreamPi link: 16/16 host tests through a simulated bad line (loss, corruption, reorder, dead line, sender restart); corrupted or wrong-hash images refused before RUN. Measured uplink 1.36 KB/s; downlink never measured. Estimates at that rate: E0 bench 2.2 min deflated, game image 24 min, room packs 42 min (packs stay on disc). Disc E:\RE4DC-Lanes\eng-loop\disc (KEEP, SD-README). Next: Flycast proof run (queued for the next free emulator slot), then the owner adds it to the SD card once.

Closed: eng-e0b (Opus), handed back 11-19, merged (code 1edab55a8). Console report: one screen line per 600-picture window (mean, p99, worst, count over 14, count over 33.3, presented intervals over 2 fields); raw rows over serial and in memory tables.

Closed: eng-e0 (Opus), handed back 11-19, merged. Survey arms MODELLED (cross / hay-fork): default 13.9 / 15.9; cache-RAM staging 14.2 / 16.1; three short loops in C 15.4 / 18.5. Both arms are boot options on the disc for the console to judge.

Closed: eng-shell-map (Opus), handed back 11-19, merged (lane commit 673a891e9). Console budget rows at the cross, ms a picture: behaviour 1.6, services 15.5, publication 16.3, drawing 17.8, system 3.9. Open: heap census run for the behaviour arena size; worst interval per row.

Closed: lab33 (M0 tool), handed back 11-19. Integrator accepted its one open item: off arms moved quiet-farm logic by 0.13 to 0.17 ms/tick against a 0.125 ms repeat spread (Flycast). The A/A visit read as low, so visit order explains most of it, and the console session brackets every arm. Lake fight preset left out (it lands in the boat-death state).

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca.

Merged 11-20, finished, unaudited: eng-svc4 (7 of 10 service items native on the PC reference; integrator gate: three images link, 70/70 controls as they must, link check still FAIL 241 / 843 / 471 service functions until eng-e1e wires the services). Next: eng-svc5 (math helpers, garment pose, SDK math and allocator, strict plays-right reader) when a lane slot frees. Parked: wip eng-ref (local only).

Merged 11-20, finished, unaudited: eng-loop2 (loader checks pass in console-like Flycast; `tools/engine/build_console_disc.sh` builds one disc with six scenes and a selector; Flycast boot: 5 of 6 scenes run, El Gigante on the bench FAILED on a stale pack; integrator gate: default, FIGHT=1, BOSS=1 and SENDABLE=1 link, loader host tests 16/16, disc hashes verified). Console disc: `E:\RE4DC-Lanes\eng-loop2\cdisc\full` (KEEP); rebuild from `engine` before the evening. Open for the next image lane: re-bake the El Gigante bench pack; count presented fields in the E1-family images.

Merged 11-20, finished, unaudited: eng-e1e (native services wired into the image; heap overlap fixed; rumble on the presentation generator; publication copies removed; integrator gate: default, FIGHT=1, BOSS=1, SENDABLE=1 link; link check offenders 241 -> 98, 843 -> 677, 471 -> 321, still FAIL). Open: enemy and room-script units have no group in the allowed list (owner or integrator decision); village plays-right not closed (yaw differs from tick 424 on the PC reference; native GetWepTargetPos); HUD compositing fault; presented-field counter; El Gigante bench pack re-bake.

## Waiting on the owner

- The console evening: the SD card (step 1).
- Asset source for step 6 (beyond the PS2 version).
- El Gigante's lighter PS2 body: yes or no.
- C: is at 27 GB free (below the 40 GB line): Compact-WSL is the owner's admin step.
