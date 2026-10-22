# Preserve visible geometry when a generated LOD is empty

`PS2_WORLD_NONEMPTY_LOD=1` keeps a visible PS2 world cluster on its nearest finer
nonempty level after the existing projected-error selection. It defaults to 0,
requires `MESH_LOD=1` and `PS2_WORLD_ROOMS=1` or `2`, and changes no recipe.

## Confirmed data and selection gap

The exact published r117 mesh has SHA256
`9ebda56af48a05bc5242d258e380a2f86f259f60a0acd1912d695af80ea0e704`.
It is byte-identical to the retained generated
`t11-20261014/blackps2/r117/ps2-world.re4mesh`. Its generation receipt lists
LOD errors `24,48,96,192,384`, minimum gain `0.4`, UV guard `0.002`, and at most
four levels. These are converted alternate geometry levels, rather than room
script visibility commands.

Stand material `5cef311a-c8764724` is already classified for punch-through.
Native mesh 9 part 14 has level 17 with nine meshlets and zero error, followed by
level 18 with zero meshlets and error `86.73419952392578`. Mesh 10 part 16 has the
same pattern at levels 20 and 21. The supporting opaque parts retain their base
geometry. Both stand meshes' referenced vertices fit their mesh bounds.

The original simplifier permits a whole component to disappear below its error
radius, and the converter retains the empty generated level. The runtime then
selects that level once

`error * sqrt(matrix_scale) * projected_pixels / (quality_lod_px * FAR_LOD) <= nearest_cluster_depth`.

Here `matrix_scale` is the maximum squared row norm of the modelview matrix and
`projected_pixels` is the maximum of the horizontal/vertical projection scale.
The unchanged QA fixture uses quality error 5 and `SCENERY_FAR_LOD=4`. The view
depth changes as the camera turns. Picking an empty alternate removes the stand
card geometry even while the original visibility state remains drawn.

The full material cohort is broader than these stands. Exact matching of the
reporter's near-stand camera remains open; the source/data defect is confirmed
independently. A bounded unchanged QA visit captured the entry aisle without
source hide/move switches and did not match the reporter's viewpoint.

## Guarded repair

The ordinary error-based choice runs first in both `MeshDraw::draw_clusters`
and `MeshDraw::chunk_select`. For PS2 world draws only, a selected empty level
steps toward finer levels until a nonempty one is found, or reaches the base.
Finer levels satisfy the existing error policy. An authored empty base remains
empty; the guard invents no geometry. Source native mesh draws and all existing
visibility, culling, transforms, materials, alpha policy and distances remain.

The helper bounds its input before reading a level. Runtime cluster counts are
also validated by the existing package open contract. The root-pose repair is
a separate switch and commit.

When an affected stand instance would otherwise be empty, this candidate
restores nine meshlets with 546 referenced corners. This is a correctness cost,
not a performance improvement. Target submissions, whole-frame cost and look
remain unmeasured.

## Checks and open gates

`test_ps2_nonempty_lod.py` compiles both actual selector blocks, the actual
projection/modelview error-scale formula and the helper under sanitizers. It
covers threshold equality and its adjacent float, several coarser empty levels,
nonempty levels, empty bases, no valid candidate, bounds, reflected/scaled
matrices, unchanged source draws, default/explicit zero, and make validation.

Actual SH4 compilation with retained QA flags passes. Default/zero
native_static preprocessing and stripped object match the original control
exactly. ON adds 236 bytes to that stripped object; scroll is unchanged.
Private source/data/provenance and compiler receipts are under
`C:/Flycast-Evidence/re4-dreamcast/issue52-objects-20261021/`.

Full matched program/overlay identity, candidate target camera transitions,
submitted geometry and memory counters, look, broader regressions and physical
Dreamcast acceptance remain open. No target image has been staged for this
candidate.
