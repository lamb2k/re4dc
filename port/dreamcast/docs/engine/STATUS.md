# Engine line status

Only the integrator edits this file. Keep it under 80 lines.

**State (2026-11-20, evening):** plan version 3 APPROVED by the owner (H-012); technical decisions are the integrator's (H-013, rulings in H-014). Current steps: 1 (console evening, waits for the owner's SD card) and 2 (pass E1). One lane running. The machine stalled for seven hours on 11-20 (WSL disk file at the NTFS fragment limit, H-014): builds go to RAM, C: is checked before every build. Everything is "finished, unaudited" until its audit and console run.

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
| (no lane) | Step 2: the E1 audit by Codex, read-only, on the commit after this merge; brief and report in `E:\RE4DC-Lanes\audit-e1b` | - | Codex | E:\RE4DC-Lanes\audit-e1b |

Closed: eng-e1d (Opus), handed back 11-20, merged (fded11182, resolved with eng-e2: draw order Ganados, Leon, Ashley; per-model palette check; per-character light records; FIGHT=1 keeps cloth stubs). The fight image now follows the aim-sway ruling, so its trace differs from eng-e2's run from tick 13 (identical for 900 ticks with AIMSWAY_PRESENT=1). Look calls open: Leon's chapter-2 body browner, Ashley's hair opaque, hill props and handgun not drawn.

Closed: eng-e2 (Opus), handed back 11-20, merged (d6e4969db). See the E2 row. Not hosted yet: doors, windows, ladders, Ganado weapons and carts, items, sound, event data. Still original service units: actor volumes, route checks, root-motion base, parts of model/motion/atari.

Closed: eng-svc3 (Opus, PC-only), handed back 11-19, merged with a link fix (b7a08259d, d12109859: E1 WEAK_motion extended; e1.elf links). RE4MK2 motion keys (float32 bit-identical; 16-bit bones within 0.14 u, traces pass); recommendation: 16-bit rows for a per-room clip set from captured play, 0.10-0.25 MB a room, since rows for all clips do not fit beside the keys. Cloth on SH4ZAM (11.3 KB, no libm; true one pass rejected, 11-54 u off; fused passes 3.5 vs 5.0 a step). Native root motion, bit-identical. Swept sphere on the grid, bit-identical; village square collision 544 -> 470 KB. 52 controls as they must. Open: enemy flails and wind setup still original pendulum code; per-room clip sets from real captures.

Closed: eng-e1c (Opus), handed back 11-19, merged (c4f938b5a). Leon image on the native skeleton and collision; original ik removed; presentation randomness on an engine generator; services in a fixed 1 MB region. Services before -> after: village Flycast 4.81 -> 2.33, MODELLED 6.85 -> 3.08; hill Flycast 12.29 -> 5.10, MODELLED 17.53 -> 6.80. Busy picture: village Flycast 15.93 -> 13.47 mean, MODELLED 21.21 -> 17.92; hill Flycast 19.87 -> 12.67, MODELLED 27.63 -> 17.42. El Gigante services 6.00 -> 4.48 Flycast. Cloth and facial keys are logged stubs for now (cloth does not swing). Integrator ruling: aim sway moves Leon and his shots, so it is behaviour and goes back on the original generator (eng-e1d). Disc E:\RE4DC-Lanes\eng-e1cuild\E1C-GDEMU-native.

Closed: eng-svc2 (Opus, PC-only), handed back 11-19, merged (cc0d1ccf5). Offline motion keys (bit-identical, key segments for Leon 60 to 3 a tick, but rows 1.84x the clips: Leon archives 1.26 to 2.55 MB); bone history cut to what behaviour reads (updateOldPos lines 377 to 71); native cloth on its own presentation generator (wind off bit-identical; wind on within 0.25 u of the original's chain distance); collision grid (polygon tests per line query down 44 to 68%, results bit-identical). 37 controls end as they must. PC counts only.

Closed: eng-e1b (Opus), handed back 11-19, merged (64b0211ba). Ashley's original partner code hosted on the engine (r11d hill, boot option HILL): with the old run's generator fed each tick, every field identical to re4ref for 729 ticks; against the old game (RESUMEA) Leon bit-identical 728 ticks, Ashley within 0.0117 units, routine exact; follow-distance control fails at tick 78. Flycast busy picture 19.46 / 26.74 ms (no world drawn); services over budget (11.86 ms: Ashley's cloth 3.55, motion 4.81, original code). Two full-field old-game fixtures recorded (hill, bell gate). Drawn as bone markers only: no Ashley mesh or r11d world bake yet. Fixed: E1 image link break after the look merge, empty punch-through list stall.

Closed: eng-boss (Opus), handed back 11-19, merged (f6af771dc). El Gigante (village square r119). Bench, full body: MODELLED 19.98 mean / 25.41 worst (characters 9.9, world 5.2, translucent 3.3); Flycast 15.53 / 22.00, no interval over 2 fields. Lighter PS2 body (g50): 18.36 / 22.49 MODELLED, MAE 0.52, sheet sent to the owner. Original boss AI and room script hosted on the E1 shell: attack sequence exact for 8 of 10 changes, motion, state and hp exact to tick 867, hut break on the same tick; hosted rows Flycast behaviour 1.41, services 5.06, publication 0. Effects recorded, not simulated. Discs E:\RE4DC-Lanes\eng-bossuild\BOSS-BENCH-GDEMU and BOSS-HOSTED-GDEMU.

Closed: disc2-play, handed back 11-19 (lane/disc2-play 0ceab4ea7). Carries: a no-warp play-through tool driven by in-game pad scripts (r200 to r202 to r207 from a cold load, crank and cannon set, locked-door control works) and one open progress item: the r207 sword puzzle timed out, script or logic not yet told apart. 50 of 50 room entries, 8 memory-squeeze cases and the disc race passed on the old line; its rendering, texture and memory findings are recorded as old path, not carried.

Older closed lanes (eng-e0, eng-e0b, eng-shell-map, eng-host, eng-host2, eng-loop, eng-svc, eng-look, lab33): see this file's history.

## Run-time lab arms (lab disc v2)

noworld, nochars, nofx, nohud, nodraw, aa; std tier adds fix4, all31, charvis2, ps31, leon2, leon3, spawn4, movca. Engine images: PACETMU (the old timer pacer with automatic flip, to compare input feel and gaps), LATEPIC (control: one held picture). HUDOLD (the HUD with one blend for every widget, as before eng-e1h). POOLCTL (control: a forced double free in the fight, the scene must be marked failed).

Merged 11-20, finished, unaudited: eng-svc4 (7 of 10 service items native on the PC reference; integrator gate: three images link, 70/70 controls as they must, link check still FAIL 241 / 843 / 471 service functions until eng-e1e wires the services). Next: eng-svc5 (math helpers, garment pose, SDK math and allocator, strict plays-right reader) when a lane slot frees. Parked: wip eng-ref (local only).

Merged 11-20, finished, unaudited: eng-loop2 (loader checks pass in console-like Flycast; `tools/engine/build_console_disc.sh` builds one disc with six scenes and a selector; Flycast boot: 5 of 6 scenes run, El Gigante on the bench FAILED on a stale pack; integrator gate: default, FIGHT=1, BOSS=1 and SENDABLE=1 link, loader host tests 16/16, disc hashes verified). Console disc: `E:\RE4DC-Lanes\eng-loop2\cdisc\full` (KEEP); rebuild from `engine` before the evening. Open for the next image lane: re-bake the El Gigante bench pack; count presented fields in the E1-family images.

Merged 11-20, finished, unaudited: eng-e1e (native services wired into the image; heap overlap fixed; rumble on the presentation generator; publication copies removed; integrator gate: default, FIGHT=1, BOSS=1, SENDABLE=1 link; link check offenders 241 -> 98, 843 -> 677, 471 -> 321, still FAIL). Open: enemy and room-script units have no group in the allowed list (owner or integrator decision); village plays-right not closed (yaw differs from tick 424 on the PC reference; native GetWepTargetPos); HUD compositing fault; presented-field counter; El Gigante bench pack re-bake.

Merged 11-20, finished, unaudited: eng-svc5 (strict plays-right reader `outcome.py`, failing closed, 30/30 controls; native math helpers, 55 functions bit-identical on 20,000 inputs each; native garment pose; integrator gate: svc_controls 76/76, plays_right controls 18/18, mathtest and garmenttest pass and their controls fail, 0 original functions kept in those units). Not built: SDK math, allocator, float library (written, in `E:\RE4DC-Lanes\eng-svc5\stage`). Open: the dying Ganado's skinning palette differs between reference and native from tick 241 / 204.

Merged 11-20, finished, unaudited: eng-e1f (fields between presented pictures in every E1 image and in the selector summary; El Gigante bench pack fixed in the baker; enemy decision units and room scripts in the allowed list with 141 service functions kept out and a name guard; integrator gate: default, FIGHT=1, BOSS=1, SENDABLE=1 link; link check service functions 98 / 204 / 154 / 98, still FAIL; guard control refuses em10FootSe). Flycast controls not re-run by the integrator. Found: the frame pacer is not tied to the display, 3-field gaps with no late picture (Flycast: village 5, hill 3, fight 29 per 600); the PC reference clamps the stick and the engine did not (cause of the village yaw split at tick 424). Not done: native aim (written, not built), shot-and-hit fixture, HUD fault, disc rebuild.

Merged 11-20, finished, unaudited: eng-e1g (pictures released on a fixed display field: intervals over two fields 5 / 3 / 29 -> 0 per 600 in village, hill, fight, Flycast, at the cost of one picture of input delay, about 33 ms; engine pad clamp, village 641/641 ticks against the PC reference; native aim, SDK math and heap linked; float library is the toolchain's, not bit-identical, judged by outcome on 8 fixtures; integrator gate: four images link, link check service functions 6 / 116 / 65 / 6, svc_controls 76/76, sdktest and alloctest pass and their controls fail, laser-sight control 6 -> 8). Flycast runs not re-run by the integrator. Found: `svc_controls.sh` exits 0 with an empty table when the odump build is missing.

Merged 11-20, finished, unaudited: eng-e1h (default and sendable images link no original service code: link check service functions 6 / 116 / 65 / 6 -> 0 / 109 / 59 / 0; cEm and cLight tables on the engine pool; laser sight drawn by the renderer, 93 lines in the village and 333 lines with 67 dots in the fight, Flycast; shot-and-hit fixture shot-ganado, Ganado 0x14 800 -> 500 on the PC reference and the native build; dying-Ganado squash made native, palette difference 0 on four fixtures; the four control scripts exit 2 on a missing build, fixture or row; integrator gate: four images link, the link control fails on pl_sub createBack, pooltest passes and both its controls fail, svc_controls 77/77, controls.sh 18/18, outcome_controls 28/28, shot and skinning controls fail as they must). **HUD not fixed**: digits garbled, lens dark (lane eng-e1i). Flycast runs not re-run by the integrator. Found by the integrator: wep02 links the cObj manager template (createBack, destroy, memClear) under its unit allowance (H-015.1).

Merged 11-20, finished, unaudited: eng-e1i (HUD: ammo digits read the live magazine, gauge frame and lens laid out as in the old game; causes were in the HUD data and layout: digit pictures cut wrong, rotation read as radians, padded pictures drawn whole, draw order; the lens needs no screen copy; the cObj table on the engine pool, and the allowed list now rejects every manager-template body in an allowed unit: default and sendable 0, fight 109, boss 58; a scene with a pool refusal is marked failed by the selector; integrator gate: four images link, the link control fails with 2 functions, pooltest and its controls, svc_controls 77/77, controls.sh 18/18, outcome_controls 28/28, the digit check re-run on the lane's Flycast stills: fight 23/23 and village plus hill 36/36 read right, the control cut 23/23 wrong). The console disc needs the packs in `E:\RE4DC-Lanes\eng-e1i\packs` (the disc script's defaults). Open: the EMPTY sign and no-weapon HUD states are not drawn; a thin dark line crosses the bullet icon on the hill; Follow-up merged the same night: `tools/engine/hudcheck.py` and `bake/hud_fix.py --verify`; the pack scripts refuse a pack without the HUD fix; images byte-identical to 00effae99, so the console disc `E:\RE4DC-Lanes\console-disc\20261120-00effae99` stands.

## Waiting on the owner

- HUD look: the still sheet `E:\RE4DC-Lanes\eng-e1i\ev\hud\hud-sheet.jpg` (old game, before, after) needs the owner's yes.
- Input feel on the console: the fixed-field pacer adds one picture of delay; the PACETMU arm is the comparison.
- The console evening: the SD card (step 1).
- Asset source for step 6 (beyond the PS2 version).
- El Gigante's lighter PS2 body: yes or no.
- Disk space (H-014): C: and D: are 97% full. The cure for the WSL disk file is a fresh copy, which needs about 420 GB free on one volume or a new drive. No Compact-WSL until then.
