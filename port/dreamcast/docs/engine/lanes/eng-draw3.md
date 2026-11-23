# Lane eng-draw3: the characters' drawing, rebuilt to cost what the job needs

Branch `lane/eng-draw3` (from `lane/eng-draw1` 9b729a729). Brief: `E:\RE4DC-Lanes\eng-draw3\BRIEF.md`. Status: finished,
unaudited. Evidence and the full hand-back: `E:\RE4DC-Lanes\eng-draw3\HANDBACK.md` (runs, tables, pixel counts, sheet).

Tier of every speed figure: MODELLED (console-build dynarec at 70 MHz, calibrated on the old port), slot fly1 (and fly2
on 11-21), each step beside its base on the same slot in the same session. The model does not see the graphics chip (TA
and ISP/TSP fill and sort), store-queue submission, cache, bus contention or disc timing; worst pictures measured before
the clock fix (H-029.1) may carry +2.5 ms in one picture a second.

## What is in the default path (pixel-identical steps)
- Step 1 (E3) and 1b: a boundary part's strips are tested once after skinning (codes reused by the emission); a part with
  dropped strips lights only its kept strips' normals; a part with none lights its whole range (no per-corner listing);
  Leon's knife part is not skinned or lit out of the knife stance.
- Step 2 (C1 light kernel, C3 weight sets): one block per normal and light (d + |d| times the halved colour, exactly the
  clamped product), weight-set blend unrolled by count, single-bone sets copied, the view-projection loaded once per
  character.
- Step 3 (fixed cost per model): the sphere-against-frustum tests without a branch per plane; the picture's frame set-up
  (frustum, view-projection, light order) once a picture rather than once per character.
- Taken back: step 2b (four-light FTRV dot products): the hill scenes timed out, 2 pixels differed, +24 KB static.

## Look arm, not the default: CB (character back-face culling)
Boot file `CBCULL` (read when the pack opens). A strip is one-sided when every edge of its triangles is shared within
the model and it is not hair (roles 7, 8). Closed parts get the chip's culling mode in their header; in boundary parts an
all-back one-sided strip is dropped before lighting and emission. The still sheet and its pixel counts are for the owner.

## Controls
- The 2 ms arm (boot set DLB, scene HILLT) must read +2 ms in the opaque world pass (drawcost.py "control D").
- `tools/engine/wepcheck.py`'s pixel rule: boot file `WEPSHIFT` (services/weapon_draw.inc, wired in 6d89f148c) draws the
  weapon 400 mm off while its box stays put; rule 2 must fail on every still where the weapon is on screen.
- Pixel counts: every LEONS, HILLS, FIGHTS and BENCH still against the previous step, compared only where two base runs
  agree to the pixel (the floor).

Results, numbers and what was not done: see the hand-back.
