# Old Dreamcast port vs new engine: same three scenes, same Flycast (2026-11-21)

Copy of `E:\RE4DC-Lanes\eng-cmp1\COMPARISON.md` without the stills. Lane note: [lanes/eng-cmp1.md](lanes/eng-cmp1.md).

Lane eng-cmp1, 2026-11-21. Status: **finished, unaudited.** Every number in this file is a **Flycast** number (the
standard harness Flycast, below) unless a line says "console". Nothing here was measured on a Dreamcast.

## What the owner needs from this page

- **In Flycast both sides show about 30 pictures a second on these scenes.** Both are held to 30 by their pacers, and
  this Flycast runs the old port about **1.6 to 1.7 times faster than a real Dreamcast** (old port, village: 29.6 here
  against 18.4 on the console; fight: 27.9 against 16.5). So pictures a second in Flycast cannot show the gain.
- **Work per picture shows it.** The new engine needs **16.1 / 25.8 / 17.8 ms** of processor work a picture on average
  (village / hill / fight) where the old port needs **26.0 / 33.5 / 25.6 ms**: 1.6x / 1.3x / 1.4x less. Its slowest
  picture is **21 / 31 / 27 ms** against **94 / 75 / 317 ms**.
- **The engine does less in these scenes** (no sound, no pyre fire, no room objects such as barrels and the crate, no
  item handling, no facial animation, no enemies at all on the village route and the hill; full list in section 5).
  The ratios are therefore not a like-for-like speed-up and must not be sold as one.
- **The console evening can produce the same table on hardware** for the engine (all three scenes) and for the old port
  at the cross and the bell fight start spots (not the hill): about 25 minutes with two discs already staged (section 8).

## 1. The table (Flycast, three runs a side, pictures of engine ticks 41 to 640)

| Scene | Side | Pictures in window | Pictures a second shown | Interval between shown pictures, fields: mean / p99 / worst | Intervals over 2 fields | Work a picture, ms: mean / p99 / worst | Work over 33.3 ms |
|---|---|---:|---:|---|---:|---|---:|
| Village route (r101) | old port | 593 | **29.64** | 2.02 / 4 / 5 | 36 | **25.99** / 61.28 / 93.82 | 57 |
| | new engine | 600 | **29.97** | 2.00 / 2 / 2 | 0 | **16.07** / 18.74 / 20.94 | 0 |
| | old / engine | | 0.99 | | | **1.62** / 3.27 / 4.48 | |
| Hill (r11d, Ashley) | old port | 596 | **29.78** | 2.01 / 3 / 4 | 25 | **33.46** / 47.93 / 75.33 | 235 |
| | new engine | 600 | **29.97** | 2.00 / 2 / 2 | 0 | **25.77** / 29.80 / 30.97 | 0 |
| | old / engine | | 0.99 | | | **1.30** / 1.61 / 2.43 | |
| Fight at the cross (r101) | old port | 577 | **27.93** | 2.15 / 6 / 19 | 46 | **25.56** / 102.25 / 317.36 | 54 |
| | new engine | 600 | **29.97** | 2.00 / 2 / 2 | 0 | **17.79** / 24.60 / 27.06 | 0 |
| | old / engine | | 0.93 | | | **1.44** / 4.16 / 11.73 | |

- Old port: pictures and intervals from image B (the per-picture flip log only); work from image A (the same plus the
  game's per-iteration stamps). Image A's own intervals, for comparison: 591 / 586 / 575 pictures, 29.54 / 29.27 / 27.81
  pictures a second, worst 6 / 4 / 19 fields: its log costs the old port up to half a picture a second (hill), so the
  interval columns use B.
- **Run-to-run spread: 0.** The three runs of each side gave identical figures to the last digit (engine: eng-1, eng-2,
  eng-3, and the integrator's own run of the same disc; old port: A1 to A3 and B1 to B3; one more old-port run in the
  engine's slot, std1, also identical). Flycast is deterministic in emulated time for these discs, so three runs check the
  reading, not timing noise. A console will vary; this table says nothing about how much.
- Pictures a second = 59.94 / mean interval in fields. "Work over 33.3 ms" counts pictures whose work alone does not fit
  a 30 Hz picture.

## 2. How far this Flycast is from the console (old port only)

| Scene | Old port, Flycast (this lane) | Old port, **console** (Test 27.1, 2026-11-11, STATUS.md, means only) | Flycast / console |
|---|---|---|---|
| Village | 29.64 pictures a second, interval mean 33.7 ms (village route, Leon walking) | 18.4 fps, 56 ms a picture (village cross benchmark spot) | **1.61x** |
| Fight | 27.93 pictures a second, interval mean 35.8 ms (the four-Ganado fight) | 16.5 fps, 53 to 60 ms a picture (bell fight benchmark) | **1.69x** |
| Hill | 29.78 | not measured on the console | - |

The console rows are the benchmark spots, not these exact routes (same room and start spots; on the console Leon stood
there). The ratio is the first measure of trust: this Flycast shows the old port 1.6 to 1.7 times faster than it is on
the console, and caps both sides at 30, so its pictures a second hide most of the difference. There is no console number
for the new engine, and nothing on this page predicts one.

## 3. How each number was obtained

**New engine.** The console disc `E:\RE4DC-Lanes\console-disc\20261121-cc3d39e6a` (origin/engine cc3d39e6a; SHA256SUMS:
track03.bin d1d87e87..., PROG/E1.BIN a816fd7c..., PROG/FIGHT.BIN f7ad10ec...) booted whole in the slot (six scenes
a boot; LEON, HILL and FIGHT used), serial line captured. Each scene's own `ROW` lines, pictures 41 to 640:
- interval = the row's `fields` (the vblank count between this picture's flip and the previous one);
- work = `frame - wait - pvr` (the frame less the pacer's wait and the wait for the graphics chip): the selector's
  "busy" row. The reader's figures equal the disc's own `CDISC SUM ... busy` lines (village 16.07 / 18.74 / 20.93).
- One picture a tick: picture n is engine tick n.

**Old port.** No existing old-port disc could play these scenes and log per picture (STATUS.md of this lane), so two
images were built, once each, with switches that already exist and only log:
- image A: the release recipe (`tools/d367/rr/recipe.conf` CH2 + `test15/t15-build.sh` T15REC = Test 27.1 +
  CHAPTER_END_HOLD=1, i.e. Test 27.2) as the release's own warp twin (t15-build.sh arm rW, `route-build.sh`), plus
  `DBG_WARP=1 PC_SAMPLER=0 PACE_HOLD_LOG=2 GAME_TICK_LOG=1`, from engine cc3d39e6a's tree (its old-port source differs from
  Test 27.2's only in default-off M1 capture code). ELF sha256 `1c8f6ae56c72e6c6...`, disc track 3 `b53d7af9cab86cb7...`;
- image B: the same without `GAME_TICK_LOG` (intervals only), ELF `a0ae5fd6e9b03aab...`, track 3 `f293f4ce99190a3a...`;
- disc data: the eng-bench pristine release data tree (as every old-game reference disc since 11-19), warp and pad files
  at fixed sectors (`base-oldA`, `base-oldB`);
- interval = the flip field of each presented picture minus the previous one's (`PACE pic ... flip=`, pace_present.cpp,
  written at the flip by the vblank handler);
- work = the game's own stamp `remain` (`PT f=... remain=`, tick_log.cpp): the time from the iteration's start to DRAW
  REMAIN, i.e. all logic and drawing before the vblank wait (src/game/main.cpp). When the pacer dropped a picture (image A: 9 / 14
  / 25 pictures in the window), the next shown picture carries both iterations' work. The old port's wait for the
  graphics chip, if any, is inside `remain` and not separated; its own report puts the chip's render at 7.5 ms a picture
  (`PACE vmu ... gpu_avg_us=7502`) and a finished scene's wait to start rendering at 2 µs (`wait_avg_us=2`), so the chip was not the limit.
- window: pictures made in game frames 225 to 824 (village, fight) and 413 to 1012 (hill): the engine's ticks 41 to 640
  on the old game's clock (engine tick n = old frame n + 184 on the village and fight fixtures, n + 372 on the hill,
  the calibration of lanes eng-e1, eng-e1b and eng-e2, tied to the fixtures' act clock: the first act of each fixture fired on the expected frame here; Leon was placed at frames 185 to 187).
- reader: `port/dreamcast/tools/engine/cmp_rows.py` (logs only). Controls (`s\ctl.py`): one picture line removed gives one
  picture fewer and one more long interval; one iteration 50 ms slower moves the mean by 50 ms / pictures; the work lines
  removed leave every picture without work; one engine row repeated refuses the scene; one engine row at 3 fields adds
  one interval over two. 5 of 5 move as they must.

**Flycast.** Both sides in the lane slots `E:\RE4DC-Lanes\eng-e1d\std1` (engine) and `std2` (old port): the same
`flycast.exe` (v2.7-14-g12bb43652, sha256 64491C00...), the same `emu.cfg` settings (framebuffer emulation on, vsync
off, serial console on, region 1, cable 3; the two files differ only in key order). Inactive desktop, no input sent.

## 4. Every way the scenes differ between the sides

| | Old port | New engine |
|---|---|---|
| **Start (all)** | warp rig: boot, title skipped, room loaded through the game's own room load, Leon placed at frame 185 to 187 | the image loads the room and places Leon at tick 0 |
| **Input (all)** | the fixture's act lines on the game's pad clock (pad frame = frame - 171) | the same moves as a pad script on the engine's clock (tick k = pad frame 13 + k) |
| **Random numbers** | warp start: fresh generator, one generator for everything | fixed seed 0x0d37 (hill) / the room's; presentation randomness on the engine's own generator (owner's split) |
| **Debug label** | the warp build draws "A: Current" in the top left for the first second (visible at village tick 80 and fight tick 40) | none |
| **Village enemies** | the room's Ganados are alive, moved 100 m away by the fixture (`emaway`): their AI and animation run every tick (EmMgr.move 2.8 ms a tick on average), they are not on screen | no Ganados: none loaded |
| **Hill opening** | the room's opening event plays (frames 185 to 370), then the window starts | the scene resumes after it (Leon and Ashley placed as the old run had them at frame 372) |
| **Hill enemies** | the hill's four Ganados (enemy list 1, cap 4) are alive about 26 m away and run every tick (EmMgr.move with Ashley 6.5 ms a tick) | none |
| **Fight outcome** | the old port's worst picture is frame 808 (317 ms, 285 ms of it in EmMgr.move), the tick at which the old-game reference of lane eng-e2 recorded its first kill (tick 624); the next wave follows | the engine's Ganados take other random choices (eng-e2: from tick 11; the owner's random split): this run logs E2 EVENTS spawn 4, hit 5, kill 0, **no kill in 900 ticks**, so the engine window never pays for a death |
| **Ammo** | HUD reads 10, 10, 08 at ticks 40, 400, 600 (the fixture's `ammo` line) | HUD reads 09, 06, 04 at the same ticks |
| **Camera** | the game's camera | the engine's camera service (checked against the PC reference); framing differs by a few pixels in the stills |
| **Window** | pictures made in the 600 game frames; a dropped picture means fewer than 600 | exactly 600 pictures, one a tick |
| **Image** | release recipe + warp rig + two log switches (image A); image B without the per-iteration log | the console disc's timing images (NOTRACE) |

## 5. What each side draws and runs in those pictures

Sources: the stills (section 6), the engine's own `E1 STUB` and `E1 draw` lines in the serial log of these runs, the
old port's phase stamps (`PT` lines, means over the window), STATUS.md and the eng-e2 hand-back.

### Village route (r101, Leon alone, 640 ticks)

| Item | Old port | New engine |
|---|---|---|
| World | the PS2 village, scenery streaming, its own far LOD | the village bake (`CROSS.PAK`, 32 catalogue models) with its visibility file |
| Draw distance | the game's far plane and far-LOD shell | the renderer's own far plane, 18,750 units |
| Leon | PS2 rig, cloth, hair, facial shape keys | PS2 model on the native skeleton, cloth on the native service; **facial shape keys not drawn** (`ShapeMove` / `ShapeEnd` stubs) |
| Hanging body | drawn | drawn (catalogue model) |
| Ganados | alive far away, running (not on screen) | **none** |
| Burning pyre (fire, smoke) | drawn and animated (still at tick 80) | **not drawn** (room effect sets not hosted) |
| Action prompt ("A CHECK") | shown near the pyre | **none** |
| HUD | ammo gauge | ammo gauge, read live |
| Laser sight | yes | yes (renderer) |
| Sound | music, ambience, footsteps (SndWatcher 0.3 ms a tick) | **none** (`SndCall` stub) |
| Shadows | no measurable shadow work (ShadowTrans 0 µs) | none |
| Room objects (doors, windows, ladders) | hosted | **not hosted** (`ChkWindow` stub) |
| Processor time, mean a tick | drawing submission 15.5 ms, logic 7.3, transforms 2.7 | drawing 12.5 ms, logic and services 3.5 |

### Hill (r11d, Leon and Ashley, 728 ticks)

| Item | Old port | New engine |
|---|---|---|
| World | the PS2 hill path | the hill path pack (`HILL.PAK`, 30 catalogue models) |
| Barrels and props | drawn (right of the scaffold) | **not drawn** |
| Ground light pool | drawn | **not drawn** |
| Leon, Ashley | both, cloth, facial keys | both (Ashley from the catalogue), cloth (3.5 ms a tick) and motion (3.6 ms) on the native services, **no facial keys** |
| Ganados | four alive about 26 m away, running | **none** |
| Doors, ladders | hosted | **not hosted** (`DoorOpenCk`, `SubLadderClimbCk`, `SceAtCheckLadder` stubs) |
| Sound | yes | **none** |
| HUD | Leon and Ashley gauges | the same |
| Camera far plane | the game's | the log says "camera from the camera service's record (far 0)" on this scene (not checked further) |
| Processor time, mean a tick | drawing submission 19.2 ms, logic 9.9 (EmMgr.move 6.5), transforms 3.6 | drawing 16.9 ms, logic and services 8.8 |

### Fight at the cross (r101, four Ganados, 900 ticks)

| Item | Old port | New engine |
|---|---|---|
| Ganados | four (cap 4) with the PS2 chapter 1 rules, waves, AI | the same four from the original room script and AI, waves 1 and 2, the wave-1 camera cut |
| Ganado weapons | hosted | **not hosted** (`SetWeapon` stub) |
| Ganado eye effect | hosted | stub (`GetEm10EyeEffectEnable`) |
| Kills and deaths | the reference's first kill falls in the window (the 317 ms picture, section 4) | **no kill in 900 ticks** (E2 EVENTS kill 0) |
| Blood, muzzle flash, smoke | the game's effects (big muzzle flash at tick 600) | the native effect service (sprites from 170 pictures); no effect models, no room effect sets |
| Items | item manager (drops, pickups) | **not hosted** (`cItemMgr::check`, `ItemGetBinTplAddr` stubs) |
| Room objects (crate, doors, windows, ladders, racks, breakables) | drawn and hosted (the crate right of the post at tick 400) | **not hosted** (`getRoomEtc*` stubs) |
| Crows | hosted (PS2_CROW=1 in the recipe; not checked on screen) | **off** ("animals off: r101 entry ... not spawned") |
| Room controllers 11 / 12 | hosted | stubs |
| Hanging cloth (pendulum) | hosted | stub ("cloth: no native service") |
| Sound and music | yes (SndWatcher 0.3 ms) | **none** (`SndCall`, `SndStrReq`, `SndRoomStrStart` stubs) |
| HUD during the camera cut | hidden | **shown** (tick 200) |
| Processor time, mean a tick | drawing submission 15.5 ms, logic 6.5, transforms 2.5 | drawing 11.9 ms, logic and services 5.8 |

**What the engine does not have at all yet** (whole game): sound and music, doors, windows, ladders and other room
objects, items, event data and cutscenes, enemy weapons and carts, room effect sets (fire, the pyre), facial animation,
hanging-cloth physics, crows and animals, every room except the village square, the hill path and El Gigante's arena,
and the hosted game outside these three scripted scenes.

## 6. Still pairs

Kept out of git (game pictures). Sheet: `E:\RE4DC-Lanes\eng-cmp1\ev\stills\sheet-cmp1.jpg`; full-size pairs `ev\stills\pair-*.png`.
Old port: this lane's run A1 of each scene (the frame buffer KOS was showing, read from Flycast's video memory). Engine:
lane eng-e1p's function run A2 (images E1.BIN b104b052... / FIGHT.BIN f64c1f59..., commit d5c28a62e), not the timed
console-disc images.

## 7. What can be said

**Three sentences a customer could be told today, each true as written:**
1. "In the emulator, on three test scenes from chapters 1 and 2, the new engine needs 16 to 26 milliseconds of processor
   work per picture on average where the current Dreamcast version needs 26 to 33, and its slowest picture takes 21 to
   31 milliseconds against 75 to 317."
2. "In the emulator, the new engine showed all 1,800 measured pictures on time at 30 a second on those three scenes,
   while the current Dreamcast version showed 27.9 to 29.8 pictures a second with stalls of up to a third of a second."
3. "The new engine does not yet play sound or draw the burning pyre, barrels and other room objects, and it does not yet
   handle items; so far it runs three test scenes, not the game."

**One sentence that must not be said yet:** "The new engine runs at 30 frames a second on a real Dreamcast" (or any
"N times faster on Dreamcast"): there is no console number for the engine, and this Flycast is 1.6 to 1.7 times kinder
than the console to the old port.

## 8. For the console evening: the same table on hardware

On the SD card (both already staged with KEEP files; nothing staged by this lane):
- **New engine:** the console disc `E:\RE4DC-Lanes\console-disc\20261121-cc3d39e6a`. One boot runs the six scenes in
  about 11 minutes (679 s in Flycast; the scenes have fixed tick counts) and shows the summary pages; the LEON, HILL and FIGHT
  rows give busy (work) mean / p99 / worst and the count of shown-picture intervals over two fields with the worst (0
  over two means every interval was two fields: 29.97 a second). The pages must be photographed, or the reports (with
  every ROW) collected through the console loop.
- **Old port:** the lab disc v2 `E:\RE4DC-Lanes\lab33\final` (lane/lab33 03b6e57f2: the release recipe with the LAB32 picture windows and the QA link; its build line also names LEON_LOD knobs, not checked against Test 27.1 here).
  Over the DreamPi: `python lab32_session.py --pi re4pi --scenes cross,bell --arms aa --nm nm.txt --out <new folder>`
  (dry run: three control-byte windows at each scene, "about 9 min" by the tool's own estimate). The cross preset
  places Leon at the village route's start spot (-7914, 2000) and the bell preset at the fight's (-7914, -254), but
  Leon stands idle: the console windows are the start spots, not the walked route or the scripted fight. The lab disc
  gives game-clock intervals (ms) and draw-phase and logic times, not the `remain` stamp, so the work column will be the
  lab's phases, labelled as such.
- **Not possible on the console with what exists:** the old port on the hill (no lab preset) and on the walked routes
  (the warp images of this lane log to RAM only; a GDEMU console has no reader for it).
- Time: about 25 minutes of console time for both (11 + 9 plus boots and the DreamPi link), on top of whatever the
  M0 lab session already runs (its core tier includes these control windows: if it runs, its cross and bell control
  rows already serve).

## 9. Not done, not verified

- No console run (by design). No MODELLED figure used.
- The old port's console numbers are means from STATUS.md at the benchmark spots, not these routes; p99 and worst were
  never measured on the console.
- The engine stills are from eng-e1p's function images, not the timed console-disc images (section 6).
- Image A adds a per-iteration log (formatted after the iteration's timing point, so outside `remain`); image B shows it
  costs the old port 0.1 to 0.5 pictures a second, so the interval columns use B. Its effect on `remain` itself (cache
  disturbance) is not measured.
- Not checked: fog and colour grading differences beyond what the stills show; the hill camera record's "far 0" line.
- Runs: engine eng-1, eng-2, eng-3 (`runs\eng-*`), old port `runs\vil-A1..3`, `hill-A1..3`, `fight-A1..3`, `*-B1..3`;
  `ev\table.json` holds every run's figures.
