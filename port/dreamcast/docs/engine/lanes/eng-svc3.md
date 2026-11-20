# Lane eng-svc3 (services round 3, PC-only), 2026-11-19

**Goal:** close what round 2 left open so the native services fit the 16 MB machine and are fully native: the motion
keys' memory, the cloth's math on SH4ZAM, native root motion, swept-sphere queries on the collision grid.
Full write-up: [../SERVICES.md](../SERVICES.md) sections 16 to 22. Tier of every number: PC; no timing.

## Result

- **Motion keys** (`bake/motion_keys.py`, `bake/motion_sets.py`, `services/skeleton/skel_mk.h`): pack RE4MK2, pose
  rows float32 or 16-bit (scale and offset a column), root and camera rows float32, no cold copy, per-room sets.
  16-bit rows: 1.17x the keys (float32 1.97x), bones within 0.14 u / 0.006 deg, traces PASS. Named-by-behaviour
  sets miss played clips; captured sets cost 0.10 to 0.25 MB a room. **Recommended: 16-bit rows for a per-room set
  from captured play, the keys resident** (rows for every clip of a fight room do not fit beside its keys).
- **Root motion and the decoder:** MotionGetSpeed, MotionGetPosition, the clock and MotionSetCore's start values
  native; a native key decoder serves fractional frames and clips outside the pack; skel.o references no motion.cpp
  symbol; the 36 B a bone key history is gone. Bit-identical on six fixtures, with and without a pack.
- **Cloth** (`services/cloth/cloth_kernel.{h,c}`, `pres_rng.h`): the chain's tick on SH4ZAM's primitives (FSRRA,
  FSCA on the SH-4), the volume tests native, passes fused exactly (Bundle_num + 1 instead of + 3). A true single pass
  was measured and rejected (links 11 to 54 u off). Wind off bit-identical; wind on the round-2 statistics; test and
  benchmark `make cloth_ktest`.
- **Collision:** the swept sphere on the grid (cells after every push, skipped polygons marked visited), exact; 32-bit
  masks for leaves of 8 entries or more: village square tables 544 -> 470 KB.

## Evidence

`E:\RE4DC-Lanes\eng-svc3\ev`: `controls\svc_controls.md` (52 rows), `motion\` (bytes per room, bake reports, sets,
per-room runs), `cloth\` (kernel test, SH-4 compile, one-pass and pass-order runs), `collision\` (seven shapes),
`cost\` and `census\` (ncensus with both packs). Scripts: `E:\RE4DC-Lanes\eng-svc3\s`.

## Not done

Real room captures for the per-room sets; PenClothMove2, the wind and the fallback still in pendulum.cpp;
HermiteInterpolation still in motion.o for the camera and shape units; grids for small unmasked leaves; a farm (em12)
fixture; timing (emulator lane).
