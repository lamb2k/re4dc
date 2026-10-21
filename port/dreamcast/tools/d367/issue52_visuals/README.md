# Issue 52 material binding diagnostic

`audit.py` reads an explicitly selected little-endian source archive, source-coverage receipt and texture pack. It binds each requested BIN/TPL pair by exact archive SHA and original image index, follows `ModelPart.flags & 4` through the source mask, computes the existing `R4MPv001` pair key and records the selected member SHA and descriptor. Ambiguous/missing source indices and unequal colour/mask dimensions fail explicitly. Outputs must be new files.

Example: `python3 audit.py --archive private/r117.arc --coverage private/coverage.json --pack private/selected.pak --model 0x1f:0x20 --out private/result.json`.

This is read-only source/asset diagnosis. A supplied subset pack proves only its recorded members; it does not establish a full-pack hash, runtime alias selection, submission, appearance, performance or physical Dreamcast acceptance. No renderer or release switch changes.

Tests: `python3 -m unittest discover -s port/dreamcast/tests -p test_issue52_material_bindings.py -v`.
