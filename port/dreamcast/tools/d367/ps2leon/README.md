# ps2leon: PS2 and hybrid Leon render meshes (PS2_LEON test arms)

Lane ps2leon-20261010. Two better Leon render meshes for the coarse owner path (COARSE_LEON=1 ACTOR_TRANSACTION=1),
behind `PS2_LEON` (`game/ps2leon.mk`, default 0: no effect, the image is byte-identical):

| knob | arm |
|---|---|
| `PS2_LEON=0` | today's Leon (leon4k, play actor bundle) |
| `PS2_LEON=1 PS2_LEON_DIR=<arm-a>` | A: the full PS2 Leon (pl00 / wep02 from the PS2 disc at the GameCube roles' arcs) |
| `PS2_LEON=2 PS2_LEON_DIR=<arm-b>` | B: the PS2 Leon's triangle budget redistributed: legs to head/hair, then back/shoulders, then arms; every part reduced from the GameCube sections |

`PS2_LEON_DIR` is a space-free directory holding the arm's two generated headers, `ps2leon_runtime.h` (namespace
leon4k, the leon4k_runtime.h API plus the plan constants) and `ps2leon_hair_runs.h` (namespace leon_hair_runs). The
headers are private assets: re4-assets-private/ps2leon-20261010/arm-a and arm-b. Copy them to a path without spaces
(make uses the directory in `-I` and as a prerequisite).

Render only. Both arms keep the 119-bone skeleton, the bind table and source signatures (the game's GameCube model
infos), the eight roles and their immutable asset IDs, today's 512 atlas (ec255e66-76812316) and the hair colour /
mask images. The arms' UVs are mapped into the same atlas tiles, so every charbake texture variant applies unchanged.
Collision, animation, game state and AI read nothing here.

## Provenance of today's Leon

leon4k (leon-hair-v2, 3,989 triangles) is a reduction of the GameCube Leon, not of the PS2 Leon
(`provenance.py`). Of its 2,785 vertices, 48 % sit on a GameCube vertex and 32 % on a PS2 vertex (the PS2 and
GameCube meshes share many vertices); no vertex sits only on a PS2 vertex, while 445 sit only on GameCube vertices
(338 of them in the hair, which is the GameCube hair to 0.0001 mm). Its UVs follow the GameCube corners: per role,
10 to 68 % of its corners are within 0.1 texel of a GameCube corner, at most 1 % within 0.1 texel of a PS2 corner.
The PS2 Leon is 5,167 triangles as stored, 5,155 drawable (12 zero-area strip joints).

## Counts

Parts are bone regions (`leon_sources.bone_regions`): a triangle belongs to the part with the largest summed weight
over its corners.

| | today | A (PS2) | B (hybrid) | GameCube |
|---|---:|---:|---:|---:|
| head / face / hair | 2,295 | 1,768 | 2,197 | 4,038 |
| torso / back / shoulders | 653 | 995 | 1,135 | 1,734 |
| arms / hands | 741 | 1,468 | 1,531 | 2,274 |
| legs / feet | 300 | 924 | 299 | 1,155 |
| triangles | 3,989 | 5,155 | 5,162 | 9,201 |
| vertices (positions) | 2,785 | 3,115 | 3,368 | 5,536 |
| owner draw runs | 21 (9 with CHARBAKE_HAIR) | 8 | 9 | 74 GX batches |
| palette matrices | 665 | 298 | 615 | |
| transformed records | 3,660 | 4,545 | 4,489 | |
| plan palette / workspace bytes | 32,000 / 26,112 | 14,336 / 11,424 | 29,568 / 24,640 | |

Character data (play knobs, measured): coarse_actor.o A -3,752 bytes, B +11,976 bytes. The CHAR_DATA_BLOCK pads in
16 KiB steps: A keeps 442,368 bytes, B takes one more step (458,752 bytes), 16 KiB less heap 4.

## Regenerating the assets

Host Python (numpy, Pillow) and Blender 5.2, from this directory; paths in `leon_sources.py` (environment
PS2LEON_TREE, PS2LEON_WORK, RE4_PRIVATE, RE4_GC_ISO, RE4_PS2_ISO). Inputs: the GameCube debug disc 1, the PS2 USA
disc, re4-assets-private character-prototype-20260925 (tools, today's mesh.json, leon-source.json, the comparison
.blend), play-actor-bundle-20260928 and charbake-20261010/src (the atlas and hair images).

```
python analyze.py                     # per-role / per-part split of GC, PS2, today -> $WORK/analysis.json
python provenance.py                  # today's Leon against GC and PS2 -> $WORK/provenance.json
python build_arm_a.py $WORK/arms/a    # A: mesh.json from the PS2 sections
python mk_job_b.py $WORK/arms/b/job.json
blender -b --factory-startup --python bl_arm_b.py -- <character-prototype>/deliverables/leon-4k/leon-4k-comparison.blend $WORK/arms/b/job.json $WORK/arms/b
python snap_weights.py $WORK/arms/b/mesh-raw.json $WORK/arms/b/mesh.json 7 229   # (rename bl_arm_b's mesh.json to mesh-raw.json first)
python pack_arm.py <today mesh.json> $WORK/arms/today --today   # check: reproduces the play bundle's arrays
python pack_arm.py $WORK/arms/a/mesh.json $WORK/arms/a
python pack_arm.py $WORK/arms/b/mesh.json $WORK/arms/b
python preflight.py $WORK/arms/a $WORK/arms/b       # the owner path's admission checks, offline
python build_gc_mesh.py $WORK/arms/gc
python counts.py $WORK/counts.json
python mk_render_job.py $WORK/renders-job.json
blender -b --factory-startup --python bl_render.py -- $WORK/renders-job.json
python make_sheet.py                  # $WORK/sheet-ingame.png, $WORK/sheet-shape.png
```

In-game stills: `tools/d367/look/look.sh <column>` with `ARM=<route-build label>` (or the knobs, to build),
`SHOTS="r100start r101F"`, `GALLERY=$WORK/gallery`, `NOSHEET=1` (one Flycast at a time, discs deleted), then
`python make_dc_sheet.py $WORK/gallery <look gallery dir> $WORK/sheet-dc.png` (columns today / A / B beside the
GameCube frames, with the Leon close-up crops of shots.json).

B's targets are in `mk_job_b.py` (per role and part). B's hair takes 1,108 triangles; its weights are rounded to
1/256 (`snap_weights.py`, 216 palettes, at most 0.054 mm in the captured pose) so the hair chunk's workspace stays
within today's.

## Checks done (2026-10-10)

- `pack_arm.py --today` reproduces the play bundle: every array byte-equal except role 7's chunk blob i7_gx (same
  size and header, 108 bytes of one meshlet in another order; the owner path does not draw it, role 7 draws the hair
  runs), and the skeleton, chunk table, weights and hair runs equal.
- `preflight.py`: PASS for A and B (array limits, palettes <= 256, weights, strips <= 64 indices, meshlets, and
  the hair material_mask against the runs).
- Knob-off identity: PS2_LEON=0 builds equal their base commit byte for byte (play knobs and the default recipe).
- Both arms compile and link with no missing symbols (route-build.sh, the look gallery's play knobs).
- In game (Flycast stills r100start / r101F, hw model r101 fight): both arms draw on the owner path (the run log's
  `COARSE_LEON skin ... entries=` line, "leon pass 1 / 2" in the hw actor table).

Arm A's hair uses one material (hair colour 0, as the PS2 draws it). The transaction refuses a plan whose declared
materials are not all drawn by a run (coarse_actor_transaction.inc, 26), so under PS2_LEON the Leon and pl08 plans
declare the atlas plus the hair materials of the header's `material_mask` (A 0x2, B 0x6; pack_arm.py writes it).
Without that A falls back to the source path, which draws the GameCube model: check for the skin line before
judging a still or a cost.

Not done here (tester): hw ms of the other views, Flycast frame times, the STRICT logic traces (H2, bell), the s30
heap gate, New Game, the pl08 rooms, the console.

## Notes

- pl08 rooms (ACTOR_PL08): pl08 draws its own roles 0, 1 and 8 (body, jacket, role 8) and the arm's roles 2..7
  (knife, face, head, hands, hair); the plan constants cover both. Look for seams at the neck and wrists there.
- `PS2_LEON` needs `CHARBAKE_HAIR=0` (the arms bring their own hair runs) and `LEON_NATIVE_PIPE=0`.
- The hair runs are built as CHARBAKE_HAIR's (one restripified run per material). CHARBAKE_HAIR stays off in the
  play recipe because the console showed dark notched triangles on Leon's hair with it (02567f84; Flycast does not
  show them). Check the arms' hair on a console before judging them.
- A runtime switch between Leons is not built: every mesh compiled in costs about 235 KB of character data, and the
  owner path's immutable asset IDs cannot be rebound (a switch needs new ID ranges per arm). Build one disc per arm.
