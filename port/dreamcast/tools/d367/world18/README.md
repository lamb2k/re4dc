# World18 scenery experiments

Private branch `codex/world18`, based on `t15/int` 7d7c05ab. This lane owns
released-route scenery only. Assets and camera logs remain private; no release
recipe or runtime switch is changed by these host tools.

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
