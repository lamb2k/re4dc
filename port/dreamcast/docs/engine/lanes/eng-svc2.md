# Lane eng-svc2 (services round 2, PC-only), 2026-11-19

**Goal:** take the rest of the services row off the original code: offline motion keys, the bone history copy,
native cloth and a finer collision index, each proven against the original in re4ref.
Full write-up: [../SERVICES.md](../SERVICES.md) sections 10 to 15. Tier of every number: PC; no timing.

## Result

- **Motion keys** (`bake/motion_keys.py`, `services/skeleton/skel_mk.h`): a frame-major float32 row table per clip
  (the original's arithmetic, exact), a const table, the clip's keys as a cold section for fractional frames (0.2% of
  samples). Bones bit-identical as in round 1; key segments a tick 60 -> 3 for Leon; archive key reads 206 -> 11
  lines. Hot tables 1.84 times the clips: a memory decision for the engine image.
- **History:** kept for bone 0 and the bones code outside asked for (32 B each) instead of six rows of every bone;
  every known value bit-identical (hist.bin); updateOldPos 377 -> 71 lines a tick on door103.
- **Cloth** (`services/cloth`): the original hosted in re4ref first, then native Set / Move / Move3 / FixSet /
  FixClear on 64-byte link records and the skeleton's tables, random numbers from a per-chain presentation generator
  (owner: split). Wind off: bit-identical; wind on: statistics within tolerance, behaviour traces identical. Lines
  about 30% fewer; accesses 5 to 7% more (same operations).
- **Collision:** a per-leaf 2 x 4 x 8 cell grid; line queries test 44 to 68% fewer polygons, results bit-identical.

## Evidence

`E:\RE4DC-Lanes\eng-svc2\ev`: `controls\svc_controls.md` (37 rows) and per-fixture compare files, `cost\` (cost
tables, the no-grid counters), `census\`, `motion\` (bake summary, clip sizes). Scripts: `E:\RE4DC-Lanes\eng-svc2\s`.

## Not done

SERVICES.md section 15: the keys' size decision, root motion on the original decoder, SH4ZAM kernels and a
single-pass cloth, the grid for swept spheres, a farm Ganado fixture, timing.
