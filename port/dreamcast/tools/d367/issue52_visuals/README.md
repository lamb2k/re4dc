# Issue 52 material binding diagnostic

`audit.py` reads an explicitly selected little-endian source archive, source-coverage receipt and texture pack. It binds each requested BIN/TPL pair by exact archive SHA and original image index, follows `ModelPart.flags & 4` through the source mask, computes the existing `R4MPv001` pair key and records the selected member SHA and descriptor. Ambiguous/missing source indices and unequal colour/mask dimensions fail explicitly. Outputs must be new files.

Example: `python3 audit.py --archive private/r117.arc --coverage private/coverage.json --pack private/selected.pak --model 0x1f:0x20 --out private/result.json`.

This is read-only source/asset diagnosis. A supplied subset pack proves only its recorded members; it does not establish a full-pack hash, runtime alias selection, submission, appearance, performance or physical Dreamcast acceptance. No renderer or release switch changes.

Tests: `python3 -m unittest discover -s port/dreamcast/tests -p test_issue52_material_bindings.py -v`.

## Opt-in lake floating-island candidate

`repair_lake_bark.py` fixes the reviewed r10b room BIN0x1e texture-index mismatch. PS2 image2 is bark and image3 is the stump; their retained GC materials are images4 and5. The original conversion placed406 bark triangles in the GC branch material (flags4, alpha mask3), leaving the opaque bark part empty. The exact original conversion reproduces the selected public BIN bytes.

The candidate calls the existing converter with map `{0:0, 2:4, 3:5}`. It requires the exact reviewed public Test21 DAR and exact original GC/PS2 BIN SHA256s, checks all529 triangles and retained material contracts, and verifies unrelated payload entries are unchanged. TPL/package keys and program bytes stay outside the repair. Output is disabled without `--enable-r10b-bark-map`; no staging recipe or default changes.

Example: `python3 repair_lake_bark.py --dar private/public-r10b.dar --gc-bin private/gc-1e.bin --ps2-bin private/ps2-1e.bin --out private/candidate/r10b.dar --report private/candidate/repair.json --enable-r10b-bark-map`.

Source validation produced candidate DAR SHA256 `8c84649bc5fc87a1b78336349e4ae8e9607440a48f90296458895bebb3db8566`, unchanged5808128B, with5079 changed bytes confined to BIN0x1e. Repaired Flycast appearance and physical Dreamcast acceptance remain open. Evidence/source receipts live in the private issue52-visuals-20261021 folder.
