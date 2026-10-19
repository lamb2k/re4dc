# scenario19: scenario discs (lane scenario19, 2026-10-19)

Narrow console discs that boot straight into one situation for the user to explore on GDEMU. They add to automated
testing, never replace it.

- `build.sh`: programs. `<LP>rP` = Test 19 recipe; `<LP>sP` = rP + DBG_WARP=1 (the shipped scenario program);
  `<LP>sC` = sP + CAST-GC census, TEX_CHECK=2, MCHECK_LEONGC, KOS_WATCH/KOS_SQUEEZE (check twin, never shipped).
- `disc.sh <label> <scenario.txt> <out dir> [extra warp lines]`: standard GD-ROM with the Test 18/19 data, the
  scenario as /dc/warp.txt and `speed=screen` as /dc/quality.txt. Check twins add `squeeze 49152 0`.
- One file per scenario (`<name>.txt`, warp-rig syntax, see game/dbgwarp_bridge.cpp header). The warp rig answers
  the card screen and skips the title itself, so a plain user disc needs no padscript; pad control is normal after.
- Scenarios: `farm-midfight.txt` (r103, one body, 4 live at cap, waves still to come).

Speed display numbers (pace.cpp vmu_window): fps x10 shown as fps, game speed % (ticks vs 30/s), CPU % of a
33.4 ms tick (work before the vblank wait; >100 = saturated).
