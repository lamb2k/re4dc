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


`enclosure_probe.py <package-dir> --eye X Y Z [--target X Y Z]
--opaque-only --out <private.json>` pins cardinal rays and one optional sight line
onto actual L0 mesh triangles. Use it to authenticate a camera fixture's floor,
roof, nearby walls and source window anchor. It records part/pass/cull and input
hashes and does not require numpy. Rays ignore face culling; selected poses,
LOD, material residency, holes between sampled directions and continuous portal
coverage are unqualified. It is never a visibility certificate or a cut table.


The r111 `policy_migration.py` verifier admits exactly one pinned provenance
transition for offline preparation. It preserves the original conversion report,
proves identical mesh/material/source-owner identities, lists every changed byte
and coefficient, and bounds the three changed affine matrices over the complete
uint16 quantization cube using exact fractions. Later proofs always use the exact
current policy. The historical ISO membership receipt is indirect evidence; the
raw ISO is absent and is not re-read. No tolerance replaces any equality guard.

`prepare.py --policy-migration-iso-receipt <historical-receipt>` re-verifies the
final copied mesh/policy/IDs, copied original policy, copied conversion report and
room identity. It refuses stale append metadata. Only the pinned helper's exact
report-policy assertion and provenance metadata are adapted for this known pair;
all placement, part, key-chain and geometric checks remain. Both original and
adapted helper hashes and the complete attestation enter private receipts/meta.
`policy_migration_checks.py` exercises 11 unknown-input negatives;
`prepare_migration_checks.py` runs the real bridge baseline plus copied-report,
copied-original, wrong-room, stale-append and ordinary-no-migration negatives.
This bridge establishes input provenance only; every geometric, runtime, material,
source-state, pixel and target-image qualification remains independently required.


Bounded source-LOD research: `eligibility.py --selected-source-lods <replay.json>`
can select each source cluster's most frequent actually selected level and retain
its full material prerequisites. `certify.py --selected-source-lod-witnesses`
uses that exact source meshlet geometry while retaining target bounds over every
LOD. Its independent replay checks the chosen source level and exact meshlet
vertices; generated descriptors fail compilation without a separately reviewed
runtime capability. Current runtime still refuses multi-LOD source clusters.
The r111 house cohort produced no additional cuts from this experiment, so no
runtime guard extension is proposed. This research option never claims admission.

I-003 house-interior research (no runtime or data admission):

- `portal_inventory.py` prices exact owner/placement/part/meshlet cohorts on
  requested recorded cameras. The effective LOD divisor and resolved profile
  receipt are required; each view agrees with the separate SG count selector.
  Per-part bounds include all source LODs. Owner IDs may span several buildings,
  exterior skins or moving parts; no interior/static classification is inferred.
- `surface_components.py` inspects one placement and explicit source LOD using
  exact grid-edge connectivity. It never welds nearly equal seam positions.
  Nonmanifold edges, winding conflicts and open boundaries remain visible
  diagnostics. A component or closed edge graph does not establish a cell.
- `component_recut_price.py` prices complete-strip component children while
  retaining every original twelve-byte corner attribute and winding. It verifies
  the original ordered triangle stream after reconstruction. Grouped child draw
  order, coplanar tie behavior, all-LOD house membership, portal visibility and
  target pixels remain unqualified. Cross-component strips stay fallback. The
  hypothetical hide-every-view price includes full retained child corner work,
  extra meshlet draws and retained-original room geometry/SG storage. It must
  never be reported as actual hidden work or measured time.
- `boundary_portal_price.py` treats every unresolved boundary cycle as an opening
  enclosed by its padded world AABB, including floor, roof and seam cycles. Bad
  edge degree, nonmanifold topology or inconsistent winding fails open. Camera
  all-openings-out is only a prerequisite; exact shell closure/orientation,
  material/source state, all-LOD target membership and numeric receipts remain
  required before any runtime cull proposal.

The current r101 cross study uses 43 historical t2exact camera matrices and
explicit divisor 20 (quality 5 times SCENERY_FAR_LOD 4), with the stable corrected
selection helper at world-merge23 commit 4cf3b40d2353076bbf7487da00b6614a07683b7d.
All source geometry, coordinates, camera records and results remain private.
Actors, outdoor occlusion policy and shared runtime/builders are untouched.

`component_recut_price.py` also prices a dedicated retained-remainder alternative
for each component. It removes only that component's complete strips, retains
all other source strips in their original order, compacts their exact corner
bytes, and verifies the retained ordered triangle stream again. One such variant
at a time needs at most one remaining draw per original meshlet. This is distinct
from the generic component atlas's extra-draw estimate. See
`PORTAL-RESEARCH-PLAN.md` for the source-only review boundary and unqualified
cell closure, all-LOD membership, runtime/metadata and pixel requirements.


Current r10d source lemma: `lod_surface_audit.py` binds exact current integration,
resolved profile and original/current ownership provenance, intersects oriented
source triangles over each cluster's independently selectable LODs, then audits
unwelded edge topology. `surface_mesh.py` is a small read-only decoder;
`check_surface_mesh.py` checks all decoded source records against the preserved
reference. Fifteen focused core controls and five actual source/profile pin
negatives exercise mixed LODs, empty fallback, cracks, winding, duplicates,
ownership and fail-open behavior. See `LOD-SURFACE-LEMMA.md` for the bounded result.
Closed graph prerequisites never admit an enclosure or runtime cut.
