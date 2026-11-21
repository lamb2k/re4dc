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

## Not done

- No console run; no MODELLED figure.
- The old port on the hill and on the walked routes cannot be measured on a console with the existing discs (the lab
  disc has no hill preset and no route; the warp images log to RAM only).
- Engine stills are from eng-e1p's function images, not the timed console-disc images.
