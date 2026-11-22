# Lane eng-draw1: where the drawing time goes, and the options to halve it

Branch `lane/eng-draw1` from `engine` 7175cf5b2. Brief: `E:\RE4DC-Lanes\eng-draw1\BRIEF.md`. Status: finished, unaudited.
Measurement and design options only; no renderer redesign is merged from this lane.

- The account, cost per unit, the near plane fix, the ranked options and the recommendation:
  [DRAWING_COST_20261121.md](../DRAWING_COST_20261121.md).
- Measurement code (no change to the default picture): `engine/render/draw_cost.h`, `draw_cost.inc` (counters, phase
  stamps, run-time lab arms), hooks in `native_draw.inc`, `native_world.c`, `native_actor.inc`, `source_light.inc`,
  `native_layers.inc`, `native_scene.inc`; the bench's "/X" schedule tokens and DRAWLAB / DRAWLAB2 schedules
  (`engine/bench/main.c`); one call in `engine/core/frame.cpp` (the DC summary after play).
- Tools: `tools/engine/drawcost.py` (reads a console-disc serial log: the account, the interleaved lab arms, the 2 ms
  control), `tools/engine/fccycles.py` (what the calibrated tier charges for a code path, from Flycast's own rule).
- Lab arms (boot files, read when the pack opens): DLA (stage, copy, select, HUD repeated; pre-fix near plane), DLB
  (weight sets, normals lit, character emission repeated; the 2 ms control), DLC (option arms X world without a stage,
  V world copy v2, G near clamp), DLV (the census of invisible work: counts only). Bench: DRAWLAB, DRAWLAB2, DRAWLAB3
  (census and look pairs, with STILLS40), DRAWLAB4 (census alone); token /Z for the census.
- Controls: the 2 ms arm (above); the reader FAILS a drawn E1 scene without DC lines; fccycles.py --selftest; the
  census window must match the base still to the pixel (it found that the bench's drawing is not repeatable between
  windows; see the cost document, section 6).
- Control: arm D (2 ms inside the opaque world pass) reads +1.95 to +2.03 ms in every scene: PASS.
