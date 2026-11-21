# Lane eng-cmp1: old port against the new engine, same scenes, same Flycast

2026-11-21. Status: **finished, unaudited.** Brief: `E:\RE4DC-Lanes\eng-cmp1\BRIEF.md`. Result:
[COMPARISON_20261121.md](../COMPARISON_20261121.md) (numbers and scope; the stills stay out of git:
`E:\RE4DC-Lanes\eng-cmp1\ev\stills\sheet-cmp1.jpg`). Every number is a Flycast number.

## What was done

- The console disc `20261121-cc3d39e6a` run whole three times in the standard harness Flycast (slot std1); LEON, HILL
  and FIGHT read from the images' own ROW lines.
- The old port built once as the release recipe's warp twin with two logging switches that already exist
  (`PACE_HOLD_LOG=2`, `GAME_TICK_LOG=1`; image A), and once without the per-iteration log (image B), objects in RAM,
  run on the engine scenes' own warp fixtures (eng-e1 village route, eng-e1b hill, eng-e2 fight) three times each in
  slot std2. No old-port code, recipe or tuning was changed; nothing was profiled beyond the game's own stamps.
- `port/dreamcast/tools/engine/cmp_rows.py`: one reader for both sides (shown-picture interval in fields and work a
  picture, waits excluded; pictures 41 to 640 on the engine, the same ticks on the old game's clock). Five controls
  (`E:\RE4DC-Lanes\eng-cmp1\s\ctl.py`) move as they must.

## Findings worth keeping

- Flycast is deterministic for both discs: three runs give identical figures, so "spread" here is 0 and says nothing
  about console variation.
- In this Flycast both sides present about 30 pictures a second (both pacers cap at 30); the old port runs 1.6 to 1.7
  times faster here than on the console (Test 27.1 console means). The gain shows in work a picture, not in pictures a
  second, in this emulator.
- The engine's scenes do less than the old port's: see the scope tables. The fight diverges after the first hits (no
  kill on the engine, `E2 EVENTS kill 0`), and the old port's worst fight picture (317 ms) falls on the reference's
  kill tick.
- The old port's `setup` stamp (Render_before, pad read, Render) holds its drawing submission: 15.5 to 19.2 ms a tick
  in these scenes in Flycast.

## Item 6 (owner input 2026-11-21): Flycast calibrated on the old port

- The console-like build's interpreter (`Dynarec.Enabled = no`) ignores `Sh4Clock` (identical figures at 100, 130, 200).
  Both dynarec builds honour it but differ by about 1.45x at 200 MHz on the old port; each needs its own clock.
- One clock matches the old port's four heavy console spots within about 3% in each build (console build 70.9 to 75.7
  MHz, standard 104 to 110); the quiet view needs more (97.5 / 125.4). Defensive clock: the console build's dynarec at
  Sh4Clock 70 (the MODELLED tier).
- MODELLED, same scenes: old port 15.6 / 11.3 / 16.4 pictures a second, engine 28.9 / 18.3 / 24.2 (village / hill /
  fight). At their own defensive clocks the two builds agree on the old port within 2.4% and disagree on the engine by 6
  to 10%: the calibration does not transfer cleanly to the engine's code; quote the console-build figures as the
  pessimistic end of a band.

## Not done

- No console run.
- The old port on the hill and on the walked routes cannot be measured on a console with the existing discs (the lab
  disc has no hill preset and no route; the warp images log to RAM only).
- Engine stills are from eng-e1p's function images, not the timed console-disc images.
