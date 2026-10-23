# Room interior visibility, lane interior-vis23

`prepare.py` pins an existing room mesh, effective physical policy, original
policy, placement IDs, conversion report and retained camera logs. It exports
the reviewed geometric proof helpers from commit
`fcf49c1dc788734799baadfe4147005f8d3338ff` to private scratch, recording their
exact hashes. It uses the historical instance order and R4PV v1 format.

Only camera-containing X/Z cells get a domain. The emitted Y interval encloses
the recorded camera heights plus an outward rounded configurable margin.
Every unsampled grid cell, out-of-Y camera, invalid package or missing runtime
receipt falls back to drawing all. PCCULL integer eyes choose domains only;
exact PS2CAM matrices are needed for selected-corner replay.

`certify.py PRIVATE` reuses continuous interval geometry proofs, replays every
clear bit from exact current source geometry, and emits the existing R4PV
format. It limits dependency panels to the runtime's current single-LOD cohort
and sixteen-panel maximum, retains the ordinary source placement prefix, and
emits a private certificate only when at least one panel has a useful proof.
An absent optional r4tc file is omitted from input hashes; no descriptor is
invented. Every adaptation and helper hash is recorded.

All outputs, package bytes, matrices, recovered coordinates and certificates
are private. Do not run these tools into a Git checkout. A successful geometry
replay is not actual runtime admission, selected transformed vertices, timing,
pixel correctness or console acceptance. Current runtime source, opacity,
numeric and emitted-prefix guards remain mandatory. No shared runtime or
recipe file is changed by these tools.

`replay.py` reads exact captured PS2CAM matrices and replays opaque baked-pose
placement/cluster/meshlet selection and the current LOD policy. Its output is
explicitly a host replay, with source-state and boundary limitations. It must
not be described as an instrumented target transformed-corner count. The
initial r10d capture uses source e9bf7e323 and programme label iv23e9bf7camrW;
later runtime repairs or integration changes do not retroactively qualify it.

Conditional source/target and single-triangle switches are research cohorts.
They retain the authenticated dynamic classification and record unsupported
runtime assumptions. In particular, original fresh-state liveness checks can
disagree with an already cached moved affine in the same UI frame; conditional
research output stays unadmitted until the reviewed runtime repair, exact
geometry coverage, real emitted receipts and target pixels pass together.

`inventory.py` performs the I-002 AREA-first package census. It records current
mesh/policy identities, full-detail opaque workload, dynamic-ID counts and
existing recovered-source visibility actions. This is a workload ordering,
not a ranking of actual PVS yield. It does not classify every room as indoor
or authorize generic outdoor PVS. Current area::kRooms covers r107; r109's
intact/broken hut setup and r111's camera-dependent house toggle already use
source dynamic bindings and must be checked before adding another table.


Material qualification controls (host only):

- `material_checks.py --evidence <private-dir>` extracts the actual `opaque_ready`
  body, actual texture constants/format conversion, the immutable rect21 adapter,
  real pinned KOS context/compiler/enum/bitfield definitions, and the actual
  TEX_MIP_DADJ wrapper. It runs the existing state negatives plus the authenticated
  r10d descriptor positive and every descriptor/key/alpha/top-drop/cache negative
  across eight rect21/cache/shadow configurations. Eight full translation-unit
  PVS0 preprocessing comparisons must equal the pre-patch source. The existing
  synthetic host stubs remain useful state controls, not real header-bit proof.
- `shadow_checks.py` extracts the actual cold material context and both final
  direct hot/cold modifier blocks with the real KOS compiler/context and mip
  wrapper. The 96 checks establish that each optional receiver mutation is
  exactly command bit7; bit6 remains clear and every ISP/depth/blend/sampler word
  stays equal. This qualifies cheap-shadow color scaling in the current source
  path without disabling ordinary MV_SHADOWS. It does not claim base headers
  equal final receiver headers or supply target/pixel acceptance.

Both tools compile temporary fixtures in `/dev/shm`; no game assets are in Git.
The shadow test leaves its generated source fixture in RAM for independent
review. A future KOS, material-context, post-header, cache, or receiver-mode change
requires repeating this qualification. Neither tool admits a visibility table or
claims target cuts, milliseconds, pixel equality, or physical console behavior.
