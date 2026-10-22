# PVS23 runtime and measurement unit

This unit imports the existing WORLD_METER implementation and its off-layout
correction, then adds a QA PVS toggle, safe table admission and identity-bound
measurement. It adds no second timer, asset conversion, meshlet PVS or AREA
expansion. Production recipes are unchanged.

## Build handoff

Use the current approved QA recipe, with these explicit overrides:

```
WORLD_METER=1 PS2_PVS=1 PS2_PVS_DEFAULT=0
CPU_BACKFACE=0 ACTOR_BACKFACE=0 VRAM_ROOM_ARENA=0
QA_MENU=1 GAME_TICK_LOG=60 FAR_SHELL=1 VRAM_PAGES=1
MESH_FASTPATH=1 MESH_VP_SCHED=1 MESH_LOD=1 PS2_WORLD_ROOMS=2
PVS23_CERTIFICATES=/absolute/private/path/pvs23_certificates.inc
```

No scratch implementation is imported or enabled. Keep all other source and
assets fixed; preserve Full as the visual reference and record the active
Options View. For the off-program gate use `WORLD_METER=0 PS2_PVS=0`, with the
other approved control flags identical. Off source-token identity passes;
target object/program identity remains a separate main-owned gate. The generated
certificate is a private, explicit build input: record its path and SHA256 in
the programme manifest. No recovered coordinates or private certificate are
tracked here. Without the include knob, the generic guards refuse every table.

## Measurement contract

Timing and count rows are **means per logic tick**, including skipped/no-world
ticks. They measure attempted CPU work, not successful display or framebuffer
visibility. `strip_input` preserves the old `stats.vertices` deltas: repeated
strip indices and rejected strip input are included. Shell `shell_sent` remains
the shell's submitted strip-vertex counter.

`TRANSFORMED / INSIDE VIEW` has separate OPQ, PT and TR rows. Transformed counts
are the actual number of inputs processed by vertex-cache transform calls,
including repeated work across calls and the enclosing surviving group interval.
Reuse of one transformed corner in several submitted strip indices adds no
transform count. Deduplicated copied tails add no transform arithmetic count.
Generic non-cache world fallbacks and shell transforms are outside this count.
Unsupported non-fastpath and comparison-transform builds show N/A.

Inside View reuses the renderer's outcodes for those transformed input corners.
All-check masks include screen plus near/far; screen-only/none variants already
have the renderer's conservative interior depth/full-frustum proof. No second
projection or reciprocal loop is added. These are input corners classified in
the frustum. Crossing triangles may have **zero** input corners inside while
their clipped primitives still cover the screen. Generated clipping vertices,
material/alpha/depth rejection, rasterized pixels and framebuffer survivors are
not counted. Zero inside corners is not proof of invisible geometry.

Completed windows bind room, Options View, PVS mode, opaque/XLU/shell QA overrides
and package generation. A changed key immediately makes the prior snapshot N/A.
Room reload and menu resume invalidate the generation, including a same-room
teleport. The first boundary tick establishes a new wall-time basis and is
discarded entirely; no fabricated zero wall sample enters a window. The next
configured number of measured tick intervals seals the snapshot, with frame
range, tick count and sequence. Paused menu time is excluded after resume.

The extra outcode-read loop and per-call accounting run under WORLD_METER in
both PVS arms. Instrumentation overhead is still an open target/console gate;
it must not be presented as zero or as an uninstrumented performance gain.

## Conservative admission contract

The R4PV **v1 format is unchanged**. Loader bounds use widened arithmetic,
finite grid extents, zero padding, bounded instance/cell/set counts, valid cell
Y ranges and exact instance offsets. Missing, malformed or stale data draws all.
The setter clears cached selection immediately, and a same-frame camera change
cannot reuse an old cell. Every selection call rechecks the proof frame guard
before a cached result can return.

CRC equality alone does not admit an old sampled table. Both optional proof
hooks must exist and return true:

```
int re4dc_pvs23_table_guard(unsigned room, const void* file, unsigned bytes,
                          unsigned mesh_crc, unsigned mesh_bytes,
                          unsigned physical_policy_crc);
int re4dc_pvs23_frame_guard(unsigned room, const float view[12],
                          const float projection[7], const float viewport[6],
                          float near_distance, float far_distance);
```

They have C linkage; the generic implementation authenticates the complete table
CRC/bytes, mesh and physical policy against the private descriptor. The initial
cohort also validates every dependency's placement, part, cluster, single LOD,
meshlet and corner references. The data proof covers the actual serialized eye
cell expanded by its declared error budget, all target LOD bounds, and actual
opaque coplanar triangle pairs sharing cache endpoints. Earlier targets remain
visible: all clear bits follow the global source-placement prefix.

Geometric cell selection alone cannot hide anything. Each required panel must
be observed in a successful **whole** kChecksAll meshlet/pick. Each exact
oriented source triangle must belong to a strip no larger than the actual
post-borrow emitter limit, with no depth-plane crossing or common screen-plane
rejection. The strip was therefore sent unchanged; unrelated strips may clip
or cull. High outcode bits are don't-care and are masked. Cached panel positions
are finite, within +/-4096 screen units and have a strong front-facing area
margin. Partial strip-group picks publish no
receipt. Pending receipts carry the actual frame/scene epoch and commit only
after end_direct succeeds. Read-only material admission then requires the exact
pinned resident RGB565 texture, complete upload, matching opaque depth-writing
header, storage/list readiness and valid source ownership. No loading, pinning,
eviction, list change or draw reordering is added by that predicate.

Each later placement checks the committed prefix and current scene identity;
both source placements and the target placement must still be at their baked
live pose under existing hide/AREA/place/dynamic rules. A replaced/discarded
scene, camera/projection/viewport/near/far change, package generation change,
missing receipt or failed guard draws normally. A part-success result alone is
never accepted as proof that its panel drew. The current qualified recipe keeps
SCENERY_CHUNK=1, PIECE_STATE/DEDUP/CONE=0, HW_LEAN=1, MESH_STRIP_LEAN=1 and
PS2_STRIP_GROUPS=1. Unsupported combinations draw all without changing knobs.

The frame guard uses the actual float eye selector and a bounded double inverse,
finite well-conditioned rigid view, normal-or-zero operands, supported FPSCR
PR=0/RM=0 or1 with exception enables off, 640x480 perspective projection and
bounded near/far. It caches the numeric result by the complete view state,
frame, FPSCR and package generation. Its absolute affine/grid/screen envelope
uses gamma128 with u=2^-23 and reciprocal allowance rho=2^-18; uncancelled row
operands remain in the bound. World and eye uncertainty must fit the private
certificate budget or the frame draws all. These are bounded private-QA
engineering allowances for the existing SH7091/HW_LEAN chain, not universal
formal verification. Matched actual pixel paths and console correctness remain
required. Sampled camera paths alone cannot prove geometric visibility.

The boot menu distinguishes ON / GUARDED from ON / DRAW ALL. QR reports the
geometric cell separately from source-prefix masks, boot receipt commits and
actual admitted placement/cluster cuts. PS2PVS logs expose the same actual cut
counters; loading a table or selecting a cell is not a gain measurement.

## Host gates and remaining work

Run `python3 port/dreamcast/tools/d367/pvs23/host_checks.py`. It compiles extracted
actual PVS admission/selection and native meter functions, executes actual
tick_log window code with controlled clocks, and tests the geometry helper with
ASan/UBSan. Cases cover missing proof hooks, stale/missing/overflow/nonfinite/
invalid-cell/padding/instance data, same-frame toggle/camera changes, live-guard
refusal and all seven identity fields. It parses the complete QA translation
unit with host platform declarations. Off preprocessed source tokens match the
imported meter baseline. `opaque_checks.py` executes the exact UI eligibility
body with cached/cold headers, read-only snapshots and failure controls.
`proof_checks.py --private <private-root>` executes the actual generic guards
against the real private mesh/table inputs, including stale identity, bad FPSCR,
numeric/liveness failures, upper outcode don't-care bits, missing/wrong triangles,
prefix completion and replacement-scene invalidation. Screen transcripts are
synthetic, and target FPSCR/material/scene reads are explicit host substitutes.
No host result is a target build, actual camera/pixel or linked-program proof.

Main still owns source review/integration, exact off program, target overhead,
KOS 48 KiB, r100 s30 heap 4, approved PVS/data proof integration, fixture state,
on-screen layout, console-mode guest captures and QA23-PVS packaging. Matched
r101 fog/house and r100 safety photos and physical-console acceptance remain
open. The sealed r109 metadata package is a separate later arm.
