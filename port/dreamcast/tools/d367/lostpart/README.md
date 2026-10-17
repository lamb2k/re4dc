# Lost-part check (required gate for reduced worlds)

The 2026-10-16 r101 world reductions lost the stake crossbar, a pyre plank and the house-fence rails. Nobody noticed
until someone looked by eye. This tool finds such losses automatically.

How it works:

- Every part of the original level 0 is split into connected pieces (by texture, then connectivity).
- Each piece is compared with the reduced world's triangles of the same texture:
  - silhouettes along X, Y and Z, plus a thin-feature check;
  - views from the walk-path cameras: door arrivals and enemy set positions, at 8 yaws each.
- A piece fails if it loses more than 10% coverage, loses a thin strip, or a camera loses at least 20 px of it.

- Run: `lostpart_gate.sh <room> <original dir> <reduced dir> <walk.json>` from Git Bash. It needs Windows Python
  with numpy and Pillow, and takes 20-90 s per room. It writes `LOSTPART.txt` next to the reduced mesh, plus a
  PASS/FAIL list and a thumbnail sheet.
- Gate: `test11/t11-fix.py` stages no `dc/native/<room>/ps2-wv*` file unless a `LOSTPART.txt` PASS stamp with the same
  sha256 sits beside it. Acceptance is 0 flagged pieces.
- `RE4DC_LOSTPART_WAIVE=1` is for A/B comparison fixtures only. It is recorded in the fixture provenance. A release
  never uses it.
- Validation on r101 (original = crowd12 bake13 level 0):

| Set | Flagged pieces (of 4494) | Stake crossbar | Pyre planks | Fence rails |
| --- | --- | --- | --- | --- |
| Original against itself | 0 (PASS) | pass | pass | pass |
| Test 15 world32 | 1657 | flagged | flagged | flagged |
| Test 16 C4 | 1598 | pass | pass | flagged |
| C16 | 1511 | pass | pass | pass |

  Every C16 flag checked in game was a real loss: the em15 beam and the door fence boards.
- Details and terrain results: `../worldtest16/WORLDTEST-INDEX.md`. Next steps: `docs/WORLD-NEXT.md`.
