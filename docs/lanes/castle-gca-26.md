# Lane castle-gca-26 (Disc 2 castle GC-ASSET, Test 26)

Branch `lane/castle-gca-26`, last merged with t15/int 56c8643a2. Disc 1 program and data unchanged by this lane.

**Result:** rr cycle 1102-0559-352687ac (RR_DISC2=1, quick tier): **PASS**, 38 checks. Disc 2 GC-ASSET PASS (not covered:
none), Disc 2 CAST-GC PASS, Disc 1 GC-ASSET PASS.

## Disc 2 GC-ASSET rows (r200-r208)
| run | rows |
|---|---|
| castle-disc2 1407 (before) | 77 |
| 25f77027 (m1) | 49 |
| 10d8bb02 (m2) | about 35 |
| ea74dde6 (m3) | 12 |
| 0b030add (m4) | 5, plus the r201 checkpoint miss |
| 843779a3 (after the t15/int merge, SKY_EVENT=2) | 19, all r200 |
| 352687ac | 0 |

## What was converted (all PS2 USA)
- **cgca26:** the castle rooms r201, r202, r204 and r208, and the castle enemies em19/1a/1b/1c/14.
  - Room objects: ps2_objects.py. The et1400 torch model is emptied where the PS2 deleted it.
  - Items and debris (ps2_items.py), and their pictures.
  - Enemy models: ps2_ganado_bins.py.
  - Sound banks: 457 of 476 samples PS2; the 19 kept GameCube samples are rows in sound-kept-gc.tsv.
- **pmcgca26:** PS2 motion for those files, em3b and the rooms.
- **cpic26:** 5 pictures as PS2 pixels under their keys: dfb309b8, 03d17402, e0330fec and 3ac7422f from em1b.dat, and 2c914a69 from r201.dat.
- **cpic26b:** the Zealot hood and robe pairs bc1a9802, ac23b5fe and ec7b1745. These had been baked from GameCube em11 colour and mask pictures.
  - They now carry the cast's PS2 picture sheet, fully opaque, because the PS2 draws these parts solid.
  - Each package keeps its ARGB4444 layout; only the texels and the CRC change (castlegca26/zpair.py).
  - Rev 1 re-encoded them as RGB565. The actor texture lease refused that, so the Zealots fell back to the GameCube draw path (CAST-GC r202, r203, r208).
- **cpic26c:** 19 r200 PS2-world picture keys as PS2 r200.dat pixels.
  - Their pak17 packages held GameCube pixels.
  - SKY_EVENT=2 (#60) widens the scripted-camera range, so the Disc 2 r200 gate visit now draws them.
  - 8b37c0d0 matched at NCC 0.985 (a PS2 256x256 picture under a 512x256 key) and needs a look check.
  - Disc 1 r200 binds the same keys and is unchanged here.
- **provenance-reviewed.tsv:**
  - 72c8acfd: exact bytes of ps2lib items.
  - 36645e3b: the Zealot cast atlas made by ps2_cast.py from PS2 em11. Its sha matches the castle18 manifest.
- **Allowlist:** 2 rows, owner castle-gca-26: the r204 et2500 window pane model and its picture d3bab4c3 (window decision 10-26).

## Harness and tooling changes
- castle_fixture.py:
  - D2_DATA sets go onto Disc 2 only.
  - A pack set applies only its pak-derived changed/added keys. Whole-pack replacement reverted newer Disc 1 pack keys.
- GC_ASSET_CKPT_FIRST (gc_asset_gate.mk; default 60, which emits no flag): the rr Disc 2 gate twin d2a uses 30. The gate build runs r201 at 3-6 fps, so a 60 s run missed the 60-frame checkpoint.
- EFM_PS2_CUT=2 in the Disc 2 program (build-disc2.sh): the r202 room-EFF debris the PS2 deleted.

## Recipe lines
- `D2_DATA="cgca26,pmcgca26,cpic26,cpic26b,cpic26c"` (recipe.conf; Disc 2 only).
- Stores: re4-assets-private {cgca26-20261101, pmcgca26-20261101, cpic26-20261102, cpic26b-20261102, cpic26c-20261102}; the manifest is committed.
- The pack sets chain: cpic26 is built over the composed Disc 2 pack, then cpic26b, then cpic26c. Regenerate them in order when an earlier set changes.

## Gameplay equivalence
d2cg census r200 to r208, control 1409ac5e (castle-disc2 1407) against 352687ac:
- Kill, alive, door and warp lines are identical on every common frame (0 differing; memory addresses masked).
- The r201 Garrador kill (watch frame 105, hp 0) is the same.
- Disc 2 cap 4 PASS (r200=4 r201=1 r202=4 r203=4 r204=0 r207=3 r208=4).

## Still pairs (Flycast captures)
- Sheet: C:\Flycast-Evidence\re4-dreamcast\castle-gca-26\stills\still-pairs-flycast.png. It covers r200, r201, r202, r204 and r208 at 30/40/50/57 s; left is the control, right is the lane.
- Most pairs show mean differences of 0-4.
- r208 at 40/50 s and r201 at 30 s catch different moments of the scripted event (load timing), not a look change.
- The Zealot fringes appear only at a distance; a close view still needs a reviewer look.

## Open
- Profile why the GC-ASSET gate build costs 450-630% CPU in r201 (follow-up; not chased).
- Disc 1 r200 draws the same 19 GameCube-pixel world keys whenever SKY_EVENT=2 widens a scripted camera there. A Disc 1 pack set is needed; it is out of this lane (Disc 1 unchanged).
- Look check: 8b37c0d0 (r200) and the solid Zealot fringes.
