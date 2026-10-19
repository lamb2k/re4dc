# World18 scenery experiments

Private branch `codex/world18`, initially based on `t15/int` 7d7c05ab and merged
through cd2d6558 for the compiled-plan trial. This lane owns released-route
scenery only. Assets and camera logs remain private. Historical host experiments
and the later default-off runtime trial are separated below.

`cone_ceiling.py` measures existing meshlet/strip-group back-face rejection on
logged PS2CAM windows. It checks transform counts against the existing sgprice
model and checks every accepted cone against the constituent triangle faces.
The cone test uses a support bound with a conservative sphere. Cull-none parts
are excluded, and CCW/CW parts retain their respective sign. Rooms without
strip-group sidecars are assessed at the existing whole-meshlet unit.

The console-slope price uses the user's measured 1 ms per 1,000 world vertices.
The separate hwproject extrapolation uses the previously measured t2exact k0
transform/walk unit costs. Neither is a new console or runtime measurement.
Per-test overhead is reported as an explicit 100/200-cycle sensitivity range.

Initial r101 result, recovered 16.4 unreduced package and retained cam-cross
frames 500..794 (43 samples, requested 500..799, stride 7, LOD 5): static exact
ceiling 981 vertices/0.981 ms; conservative cones 508 vertices/0.508 ms gross.
At 585 eligible group tests/frame the test-cost sensitivity leaves +0.215 to
-0.077 ms. No runtime WORLD_CONE_CULL implementation is justified by this result.
Including dynamic/sky placements raises the optimistic exact ceiling to 1,034
vertices but conservative cones still only catch 518; dynamic source transforms
and activation were not recorded and these counts are not a qualified proposal.

The r101 Blender pilot is independent. It must preserve materials, textures,
source identities, landmarks, full detail inside 12 m, and RAM residency, pass
lostpart with zero flags, and receive the user's look decision before other rooms.

## r101 initial Blender assessment (2026-10-18)

No reduced game asset is accepted. This is a rejected first pilot, not M2
acceptance or a performance win. Official portable Blender 5.2.2 LTS was run
offline with factory settings. Input is the recovered unreduced 16.4 r101 world.

* `blender_export.py` checks a byte-identical R4IM read/write roundtrip. It exports
  all 535 clusters, 53,182 L0 triangles, UVs and ARGB1555 corner lighting. Blender
  coordinates remain relative to each grid origin to preserve quantized detail.
* `blender_planar.py` uses native Limited Dissolve only across coplanar edges
  with matching UV/lighting interpolants. It saves zero triangles.
* `blender_far.py` assesses protected Collapse in existing coarse LOD slots and
  the one cluster permanently beyond the walkable-area protection band. All
  vertices in those eligible slots are protected boundaries, seams, sharp edges,
  or small/thin pieces; no candidate was generated. Data Transfer code is present
  but was not exercised by an accepted candidate.
* `blender_techniques.py` verifies Blender's unmodified full six-u16 loop-corner
  identity and compares native techniques. Merge by Distance saves zero positions;
  loose Dissolve saves two triangles; Un-Subdivide removes 7,778 triangles but its
  diagnostic package FAILS lostpart with 1,947 of 4,494 pieces flagged over 393
  walk/door/sheet cameras. It must never be staged or treated as accepted.
* `package_repack.py` uses the existing stripifier/meshlet packer and verifies
  every unmodified level's oriented corner triangles. Its optional ordered exact
  repack preserves 707 levels but worsens the r101 500..794 camera window:
  transformed corners 19,069 -> 23,488, walked strips 4,464 -> 5,533. Fewer meshlets
  alone are not a performance result. Mesh plus groups grows by 1,248 bytes.

The package writer is diagnostic tooling; it does not change stagers or recipes.
No default-off runtime knob is introduced until there is a qualifying asset.
No Flycast speedup, new hwproject timing, VRAM gate, Disc 1 image identity, or
48 KiB squeeze result is claimed for these rejected candidates.

Private data and both Blender scenes are mirrored under
`world18-r101-20261018` with SHA256SUMS. Reports and the rejection sheet are under
`C:\Flycast-Evidence\re4-dreamcast\world18-20261018`. M1 is complete; a useful
M2 still needs targeted room/material work that passes every look and runtime gate.

## Compiled room-plan trial (I-005, 2026-10-19): STOP

`compiled_plan.py` writes R4SG v2 in the existing strip-group allocation. It
preserves the exact mesh/R4PW bytes and reconstructs every original group list;
small source-referencing descriptors and conservative cells reuse bounds,
ordered pass membership and exact-affine matrices. Source-owned moving/sky
placements retain their original path. Runtime integration is c90c8b91, reader
and host checks 79dabd7c, inventory 687bf92e. WORLD_PLAN defaults to 0 and is not
part of T15REC. No release has adopted it.

The final layered r101 input has 1,830 meshlets, 223 placements (202 immutable),
342 parts, 43 affine keys and 16 full-coverage conservative cells. Metadata is
117,152 B before/after; 117,052 B is used, including 6,528 B scratch. Host checks
cover 26,328 visibility combinations, four exact-key invalidations, thirteen
malformed/bounds cases and all 1,830 exact group sequences.

Same-executable w18p1rW v1-control/v2-candidate, r101 cross live cap4,
Fast/cap1, global frames480..525 stride3 (16 drawn one-tick samples): nominal
MODELLED work proxy **49.001081 -> 49.546355 ms**, a **0.545273 ms regression**.
Work proxy subtracts flat-self re4dc_pace_end and re4dc_vi_retrace_count from
the full trace. Both replay/symbol parity checks pass. The minimum required
gain was1.5 ms: stop before r103/r119; do not promote this path or infer a
console speedup. Affine concat saves0.102596 ms, but draw self adds0.365531 ms
and fine visibility call counts are essentially unchanged.

Partial qualification only: disabled diagnostic boot+14 overlays match the
original-source diagnostic reference; T15REC rP release identity was not run.
Geometry lostpart0/4494 over393 cameras. Frozen tick700 Off diagnostics have
fb0 pixel-identical and fb1 seven differing pixels. KOS48KiB fight2/10 cases
only, minimum free5688/5600 B. Both control and candidate show an unresolved
alive-id41/no-NMRS baseline finding. STRICT/decisions, complete residency,
remaining squeeze cases and console acceptance are not established.

Private evidence: C:\\Flycast-Evidence\\re4-dreamcast\\world18-20261018\\compiled-plan.
Private datasets worldplan18-input-20261018 and worldplan18-20261018 are
mirrored under re4-assets-private with SHA256SUMS. The final candidate metadata
SHA256 is c92f5f000fdae1c4cf7659fa774b8266c2f1e17323b848cca5a58d4be109f9b0.
The full result is WORLD18-COMPILED-PLAN-20261019.md in the workspace.

I-006/I-007's shared room-file design is in the world18 section of
ACTOR-RUNTIME-INTERFACE-20261018.md: one deterministic offline compile, a
versioned R4RC section container, shared base lattice and one room budget.
It is a design, not an implemented or accepted converter. Adding the current
80,272 B collision grid to a 100 B reserve fails zero-growth; r100s30 and
r101 need independent replacement-allocation proof. The unchanged performance
stop rule means the new drawing priority does not authorize rank2/farm work
after this failed trial.
