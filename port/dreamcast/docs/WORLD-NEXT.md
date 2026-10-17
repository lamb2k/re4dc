# World geometry: next steps (2026-10-16)

User, 10-16: "use the previously optimized r101; we will come back to improving the world; we need to use Blender and
more sophistication".

Tests 16 and 17 ship the unreduced r101 world (crowd12 bake13, the test 14 world) with WORLD_VERT off. No automatic
reduction ships.

## Why we stopped

The per-vertex reduction (world32 and its successors) broke structure silently. The stake crossbar, a pyre plank
and the house-fence rails were found by eye. The lost-part check (`tools/d367/lostpart`) then found much more. Against
the r101 original, the sets flag:

| Set | Flagged pieces (of 4494) |
| --- | --- |
| Test 15 world32 | 1657 |
| Test 16 C4 | 1598 |
| C16 | 1511 |

- About 470 of the C16 flags are visible from the walk-path cameras: beams, planks, posts and boards across the
  village. The em15 beam and the fence boards by the door were confirmed in game.
- The terrain-only mode failed too, because its classifier calls trees terrain:
  - r108 and r10a lose branch tips;
  - r108 loses its 0x4e strips;
  - r102 gets a streak on its cave wall (not an open-border crack).

## Acceptance gate for any future world change

1. **Lost-part check: 0 flagged pieces** (`lostpart_gate.sh`). `t11-fix.py` stages no `ps2-wv*` file without a PASS
   stamp of the same sha256.
2. **Still pairs** at the room's sheet cameras and its worst walk-path views. The user judges the look.
3. **MODELLED ms**, then console ms at the benchmark views. A change that leaves less than about 1.5 ms p90 is not
   worth shipping.
4. **The usual data gates:** STRICT + decisions, TEXCHK/LEON-GC, VRAM, KOS squeeze and GDEMU.

## What manual (Blender) work would need

**Shared tooling first (not built yet):**
- An exporter and importer between R4IM v3 + R4PW and Blender. It must keep:
  - mesh, part and placement records;
  - texture keys, vertex colours (prelit) and UVs.
- Import must keep each part's texture and pass. Collision is a separate file and stays untouched.
- A per-room job list made from the lost-part JSON and `price_struct.py`: which meshes carry the cost, and where
  players look.
- Edits that pay off without losing silhouettes:
  - remove faces that are never seen (backs of walls against cliffs, undersides, faces inside other meshes);
  - merge coplanar wall panels whose texture tiles;
  - hand-made LODs for repeated props.
- Any thin feature (rail, plank, post, crossbar, branch) stays as it is.

**Room targets.** All ms are MODELLED (1.1 ms per 1k on-screen world TA vertices, on the price2 view samples). The
structure share is the share of world cost that is structure, not terrain.

| Room | World p90 / worst | Structure share | Where the cost is | Manual work |
| --- | --- | --- | --- | --- |
| r107 | 29.8 / 39.0 ms | 0.96 | Canyon sight lines: long views over the cliff houses and walkways | Faces hidden by the canyon walls; distant house backs; a far LOD for the cliff-top structures beyond about 25 m |
| r109 | 24.9 / 35.0 ms | 0.97 | The cabin: dense interior props and walls | Hidden faces inside and behind furniture; coplanar wall panels; prop LODs. Interior views, so silhouettes are close |
| r104 | 19.2 / 25.7 ms | 0.90 | Houses and fences around a fight area | House backs and roofs never seen from the walkable area; fence runs merged per texture, rails kept |
| r101 | (the cross: about 15 ms world) | high | 4494 pieces: houses, fences, the stake and pyre, baked props | The world32 cut only works if every flagged piece survives. Start from the C16 flag list: about 470 camera-visible pieces to keep exact, then rework the rest (house backs, roofs, hidden faces) by hand |

The next rooms are r106 and r103 (structure p90 about 17 ms each). r105 has one 28.7 ms worst view.

## Data and evidence

- Results: `tools/d367/worldtest16/WORLDTEST-INDEX.md` and `tools/d367/lostpart/README.md`.
- Evidence: `C:\Game Dev\Emulators\worldtest-20261016\lostpart\` (flag lists, thumbnails, in-game pair).
- The reduced sets stay in re4-assets-private (`world32-r101-20261016`, `world-r101-wt16*`,
  `world-terrain-wt17-20261016`) for comparison only. None has a PASS stamp.
