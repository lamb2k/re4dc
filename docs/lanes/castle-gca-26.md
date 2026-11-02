# Lane castle-gca-26 (Disc 2 castle GC-ASSET, Test 26)

Branch `lane/castle-gca-26` off t15/int ef5cf5fb. Disc 1 program and data unchanged (Disc 1 image fbc7f41403d3b1eb on every lane commit).

## Disc 2 GC-ASSET rows (r200-r208)
| run | rows |
|---|---|
| castle-disc2 1407 (before) | 77 |
| 25f77027 (m1) | 49 |
| 10d8bb02 (m2) | ~35 |
| ea74dde6 (m3) | 12 |
| 0b030add (m4) | 5 + r201 visit-3 checkpoint miss |

Left (no PS2 source found by NCC search of r201/r204/em1b/core.dat): r201 72c8acfd (ITM picture, best 0.97, ambiguous); r202 36645e3b (castle cast registry atlas 1024x512) and bc1a9802; r208 ac23b5fe and ec7b1745 (resident.bin keys).

## What was converted
- cgca26: castle room archives r201/r202/r204/r208: ETM + room BIN pairs PS2 (ps2_objects.py; et1400 torch emptied where the PS2 deleted it), items + debris (ps2_items.py), PS2 pictures (ps2_objects_tex.py, ps2_items_tex.py), em19/1a/1b/1c/14 PS2 BINs (ps2_ganado_bins.py), sound banks PS2 PCM (457/476 samples; 19 rows in sound-kept-gc.tsv).
- pmcgca26: PS2 motion for those archives, em3b and the rooms (ps2_motion_prepared.py).
- cpic26: 5 pictures as PS2 pixels under GC keys (em_eff_pics.py): dfb309b8, 03d17402, e0330fec (em1b.dat), 3ac7422f (em1b.dat), 2c914a69 (r201.dat).
- Allowlist +2 rows, owner castle-gca-26: r204 et2500 pane model and its picture d3bab4c3 (window decision 10-26).

## Recipe lines
- recipe.conf: `D2_DATA="cgca26,pmcgca26,cpic26"` (Disc 2 only, castle_fixture).
- Disc 2 program: build-disc2.sh exports `EFM_PS2_CUT=2`.
- Stores: /root/re4data/private/{cgca26-20261101,pmcgca26-20261101,cpic26-20261102}. cpic26 is made from the composed Disc 2 pack: regenerate when cgca26/pmcgca26 change.

## Gameplay equivalence
d2cg census r200-r208, control 1407 vs lane: alive lists and kill frames identical on common frames (em1b Garrador kill frame 100 same). Disc 2 cap 4 PASS.

## Open
- Disc 1 GC-ASSET 0100 unbound-accepted-payload 23 in this lane's RR_HOME (no baseline there); Disc 1 image unchanged, so believed base/harness, not proven.
- Still pairs not made.
