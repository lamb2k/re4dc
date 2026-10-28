# Build 26 world and static drawing audit

Date: 2026-10-28. Base: `9a66e3fce8899f69378f12b5f9517f297f1fa314`.
Build 25 was published separately as `ee9a5c41`; its runtime changes are not
assumed to be integrated into this base. The two new controls relevant here
are `DRAW_FALLBACK_AUDIT=1` and `SCENERY_CLIP_INDEXED26=1`, independently
default **0**. Claude owns integration and console acceptance.

## Findings and evidence boundary

The active streamed indexed world path still stages a complete meshlet into
a local corner array when its first strip needs clipping. The clipper then
decodes those same immutable records. `SCENERY_CLIP_INDEXED26` removes that
staging step: the existing clipper reads the original pool through its local
16-bit offset table. All corner decoding, coordinate arithmetic, UV and alpha
handling, strip winding, clipping decisions, packet results and publication
order remain shared. There is no new asset format, assembly, linker change,
allocation, persistent cache, gameplay change or approximation in this fix.
See [the implementation](../../game/platform/native_static.cpp) and
[the two-pointer accessor](../../game/platform/include/scenery_clip_indexed26.hpp).

The Make-resolved public recipe has `SCENERY_SELECT_ONLY=1`,
`SCENERY_REPLAY_LEAN=1`, `SCENERY_SUBMIT_BATCH=1` and `SCENERY_STREAM=1`, but
**`SCENERY_SELECT_LEAN2=0`**. `SCENERY_UV_SNAPSHOT`, `SCENERY_EMIT_PREFETCH`,
`SCENERY_CLIP_GATHER`, `SCENERY_LOCAL_INDEXED`, `SCENERY_DIRECT_STRIPS` and
`SCENERY_RECORD_SPLIT` also resolve to 0. Availability in the source does not
establish that a build uses an optimization. This audit does not change those
existing recipe selections. Recipe provenance is the Build 26
`recipe-values.json` receipt produced from the actual public Make invocation,
using the release knob list plus the current ordered `CH2` assignments. The
public build substitutes `NMR_POOL_LOD=0` and excludes unavailable private
actor assets; it is not a reconstruction of every private DIAGLINK disc.

The queue records actual r103 first-barn WORLD OP/PT work/clip/submit of
11,595/1,191/4,498 microseconds per drawn tick. That establishes that clipping
work occurred in the captured category. It does **not** establish how much
was full gathering, which meshlets were involved, or that this candidate is
the first or second largest console fallback. No chapter 1–2 assets or
console counter trace were supplied here. The new counters are the instrument
for the owner to obtain that ranking. The measured category and the new
source-level redundancy support this candidate, not a claimed console win.
See [the queue's Fast paths section](CLOUD_AGENT_QUEUE.md).

## Reading the inventory

`R` below is the resolved public recipe value. A runtime branch and a
compile-time alternative are distinguished explicitly. A compile-time 0
cannot produce runtime refusals of code that is absent. A missing optional
asset may select an ordinary representation at room load and remain there
for all subsequent ticks; a zero last-tick loader counter would not establish
that the alternate was admitted.

`U` means **unpriced**: no current-base, bounded target instruction trace for
that complete operation is claimed. It never means zero cost. This applies
to warm/cold cycles, executed loads/stores and distinct 32-byte lines unless
a row or the cost section supplies them. `G(V)` is the full indexed gather of
V records: its payload is V 16-bit offset loads, 3V 32-bit record loads and
3V 32-bit stores, plus loop/context traffic. `C(n)` is the existing clipper
for an n-corner strip, whose cost depends on near/far crossings and culling.
`E(n)` is emission of n cached 32-byte vertices, including eight SQ words per
vertex; exact bus stalls are not priced. These are work definitions, not a
claim that data-line misses are proportional to byte counts.

Chapter evidence uses the following terms:

- **Reachable:** the public code accepts this route/condition and the room
  registry contains the relevant chapter rooms. Frequency and asset-specific
  admission remain unmeasured.
- **Conditional:** a different knob, optional file, quality/view setting or
  failure is required; it is not demonstrated in the captured barn frame.
- **Compiled out:** the resolved public route does not execute that branch.

The generated [world room registry](../../game/platform/include/ps2_world_rooms.inc)
lists r100/r101/r103 and the chapter route rooms through r11f, alongside stage
2 coverage. The numeric stage-2 room prefix is not used as a substitute for
chapter numbering. The registry proves package validation provenance at its
generation, not the contents of a privately packed disc today.

## Selection, representation and per-part setup

Primary source: [native_static.cpp](../../game/platform/native_static.cpp),
[shared chunk selector](../../game/platform/include/scenery_chunk_select.inc),
[LEAN2 selector](../../game/platform/include/scenery_select_lean2.inc),
[scenery build rules](../../game/scenery19.mk).

| Split / R | Condition selecting ordinary work | Per-item work and MODELLED cost | Chapter 1–2 evidence / counters |
|---|---|---|---|
| `SCENERY_CHUNK=1` | `chunk_ok` refuses a package without LOD, check mode bit 8, more than 8 strip groups, a PVS set, interior mode, or Standard impostor cluster exclusions. A part with more than 320 meshlets also cannot enter the 320-pick queue. | Ordinary `MeshDraw::run`, cluster/meshlet selection and per-part context; U per part, then the ordinary geometry work below. | Reachable. The r100 interior path can refuse chunks while doing useful portal culling. Exclusive first-reason bins `w_chunk_lod/check/groups/pvs/cell/impost/cap`. A chunk refusal is not a return to GC by itself. |
| Chunk queue capacity | 48 queued parts or the next part would exceed 320 picks. | Drain the existing synchronous queue and continue; U per drain. It is batching fragmentation, not a slow geometry fallback. | Reachable by population; no invented frequency. Existing chunk replay/counter work records the resulting parts. |
| `SCENERY_SELECT_ONLY=1` | The small selector cannot queue the part; or knob 0. | Construct the full emitter and use its selection/run methods; U per full context. | `w_select_old` counts actual full world emitter contexts, including refusals when the knob is 1. |
| `SCENERY_SELECT_LEAN2=0`, `SG_SELECT_LEAN=1` | Recipe omits LEAN2. Enabled LEAN2 also calls its range fallback for zero masks or decreasing nonempty strip ends. | Ordinary bounds preparation and temporary range building instead of packed final Picks. U current-base per selection. Historical Build 13 gives 411 warm cycles for one fully inside ordinary selection and 1,845 for a partial-group fixture; these are bounded historical examples, not universal prices. | Reachable by compile selection. `w_sg_ranges` counts either actual range-builder function. `w_sg_order` additionally identifies LEAN2's malformed non-monotonic-end fallback; the package validator does not forbid that sequence. |
| `SCENERY_REPLAY_LEAN=1` | Knob 0 constructs a full emitter for every queued part. Non-chunk parts never enter this optimization. | Repeated initialization, matrix copies and clip setup; U per part on this base. | `w_replay_old` is the actual legacy replay setup, separate from `w_select_old`. |
| `SCENERY_SUBMIT_BATCH=1` | No replay batch owner, ordinary world part, texture/header/owner/pass edge that must release the batch, or knob 0. | Single direct bind/end and SQ ownership work; U per bind, plus texture work when required. | `w_submit_single` counts the actual unbatched PS2 bind attempt. Detailed material/cache/texture/SQ reasons are in the shared submission audit, not inferred here. |
| `SCENERY_UV_SNAPSHOT=0` | Compile-time selection only; it does not dynamically fall back. | No stored per-queued-part UV snapshot. Enabled mode adds two float snapshots and restoration across drains. It is a correctness/ownership composition control, not a universally faster branch; U. | Transition/R11F owner modes are 0 in the measured public recipe. No new behavior is introduced here. |
| `SCENERY_SCREEN_MEMO=1` | No previous matrix, or any bit of mvq/projection/viewport key differs; knob 0 always rebuilds. | Existing screen matrix construction and 64-byte matrix write/reload; key is 80 bytes. U per rebuild; `w_screen_rebuild` counts the full construction after either memo-return point. | Reachable on camera/placement changes. A memo hit still reloads XMTRX after binding can yield. |
| `SCENERY_UNIT_CONCAT=1` | Placement 3x3 is not exactly identity; knob 0 uses the general matrix product. | Ordinary 3x4 concatenation, 12 output floats; U per placement matrix. `w_place_matrix` counts actual products, including non-lean configurations. | Public rule comments record r103 134/134 identity placements, r100 180/283 and r101 15/223. Those are historical source annotations, not this run's census; dynamic/root matrices can differ. |
| `PS2_WORLD_LEAN=23` | Placement not proven wholly inside, matrix/sky cases requiring the ordinary visibility test, or the corresponding bit disabled. | World-plane test, then placement/cluster/meshlet box tests as required; U per tested bound. Correctly clipped/intersecting geometry requires this work. | Reachable near walls/edges. Successful culls and inside shortcuts are not counted as fallback. Bit 8 diagnostics are absent at R=23. |
| `MESH_LOD=1`, `PS2_WORLD_NONEMPTY_LOD=1` | No package LOD metadata, or compile-time LOD disabled. A chosen empty PS2 level is replaced by an existing nonempty level. | Flat scan of the part's meshlets (`w_mesh_no_lod`), U per part plus per meshlet work. Nonempty selection increases geometry intentionally to avoid holes. | Conditional on package format/LOD. No fake cost assigned to an empty level as a desirable fast path. |
| `SCENERY_FAR_LOD=4`, quality LOD | Projection error/depth chooses a finer level; quality setting changes threshold. | More selected meshlets/vertices; U total because source counts are absent. This is normal quality work, not a failed optimization. | Reachable near camera. Existing far-LOD output approximation is unchanged. |
| `SCENERY_LOCAL_INDEXED=0` | When enabled: alternate absent, protected owner/movie room, or alternate cannot validate/adopt. | Base representation and indexed gather/stream path. U load cost; G(V) if a base indexed meshlet reaches an eager gather. | Conditional. Owner exclusions explicitly include r100/r11f and source-owned r200 under their relevant modes. Alternate identity/CRC failure is not silently treated as a successful fast asset. |
| `SCENERY_DIRECT_STRIPS=0` | Enabled direct representation still requires PS2 direct SQ owner, authenticated SDS1 kind, a full pick, wholly inside bounds, all strips within slab limit, and no conflicting diagnostic/backface mode. | Cached transform/strip path on refusal. `w_direct_kind/edge/cap/diag` counts executed admission reasons. Partial picks take the existing selected path without attempting the fused call. U per meshlet, then G/C/E as applicable. | Conditional on alternate data and changed build. No new direct-path claim for the active recipe. |
| `SCENERY_RECORD_SPLIT=0` | Enabled mode permits ordinary base fallback when split alternate absent/protected; the adapter reads the ordinary 28-byte record. | 16-byte bounds + 12-byte emit split only for admitted v4. Historical 320-pick metadata union 280→160 lines, selection 4,877→9,374 warm cycles; enabled base fallback 11,004 cycles. This is not an accepted general speed win. | Conditional. See [Build 13 report](BUILD13_SCENERY_RECORD_SPLIT_20261024.md); synthetic/exporter receipts do not establish current chapter incidence. |
| `SCENERY_EMIT_PREFETCH=0` | Compile-time selection; enabled nonempty partial indexed picks still gather all corners because R4SG enclosure is not certified. Empty picks skip its unused gather. | Existing prefetch scheduling differs; G(V) for its actual gather, counted in `w_gather_full`. U net per pick; prior cross/forest results in the queue did not establish a win. | Compiled out, incompatible with active `SCENERY_STREAM=1`. |
| `SCENERY_DEDUP=0` | Mode 2: missing/stale SCDD, room/format/CRC/range failure, or no table entry; mode 3: no authenticated byte-neutral alternate or no repeats. Mode 1 is rejected by Make. | Transform all original positions instead of unique positions plus repeat fill; U per excess vertex. It does not select a different light or clip evaluator. | Conditional. Missing table is a room-load admission; all ordinary transform work still appears in the renderer's vertex census. Mode 3 is incompatible with the new direct indexed clip fix. |
| `SCENERY_CONE=0` | Missing/stale SCCN, package mismatch, unsuitable cull mode, singular inverse, or no valid cone for a group. | Keep ordinary strip groups and their geometry; U retained group. | Conditional. This is conservative no-cull behavior; not a claim that the group was hidden. |
| `SCENERY_PIECE_STATE=0` | Missing SCPS/current package slot, stale slot/texture/VRAM/header identity. | Existing header-cache set lookup instead of direct slot; U lookup; shared material/header audit owns actual miss bins. | Conditional on section and build. No new cache authority is introduced. |
| `SCENERY_ENCODING=1`, `SCENERY_N256=0`, `WORLD_VERT=0`, `WORLD_RECT21=1` | File/encoding/alternate selection at load; no valid alternate retains ordinary data or declines the load according to its validator. | Format-dependent vertex/header traffic, U per loaded/drawn record. Rect21 texture keys retain original policy provenance. | These are data-selection/validation controls, not per-strip recovery to old rendering. Existing output changes and owner exclusions remain intact. |

## Transform, strip, clipping and transparency

Primary sources: [MeshDraw and Emitter](../../game/platform/native_static.cpp),
[shared chunk backend](../../game/platform/chunk_submit.cpp),
[fast transform](../../room/mesh_fastpath.hpp),
[shared triangle clipper](../../room/pvr_geometry.cpp).

| Split / R | Ordinary-path trigger | Per-item work / cost | Evidence / attribution |
|---|---|---|---|
| `MESH_FASTPATH=1` | Knob 0 uses per-strip corner preparation. Missing LUT or insufficient borrowed slab refuses rather than secretly running the old path after SQ publication. | Scalar preparation for each strip occurrence; U. Cache refusal costs are U and may abort if a header is already published. | `w_cache_lut/cap` have unit `refusal`, not completed slow work. This distinction corrects the older comment saying “per-corner path.” |
| `SCENERY_STREAM=1` | Ordinary non-chunk `MeshDraw::meshlet` calls `corners`; streamed indexed picks normally defer it, but the first clipping strip requires it with both clip fixes 0. Plain records need no gather. | G(V); `w_gather_full` counts actual copied records, not attempted indexed picks. | Reachable on indexed chapter world data; current source itself documents R4IM v3 world pools. Exact scene count unknown. |
| `SCENERY_CLIP_GATHER=0` | Enabled mode tracks referenced local indices and copies only first uses across clipped strips. It is bypassed when the new indexed clip accessor is enabled. | Partial gather pays index/mask probes and 12-byte copies; `w_gather_clip` counts copies. Historical full-coverage/repeated-index cases can regress. | Conditional optimization from Build 24; no automatic enabling. |
| **`SCENERY_CLIP_INDEXED26=0`** | New default-off fix. At 1, `stream_l` authenticates the current indexed pick; otherwise the unchanged pointer source is used. | Existing C(n), directly reading pool[offset[local]], with zero gather copies for that indexed clip path. New target cost is reported separately. | Exact fix. Active recipe already satisfies the stream/direct/PS2 prerequisites. Both plain and non-streamed paths stay on the original typed pointer. |
| `MESH_PRIME_LAZY=1`, lean bit 4 | First use of additional entries, different cache address, failed debug prime validation, or knob 0. | Prime flags/offset-color words for required entries, or all 256 when eager; two 32-bit stores per entry. U cycles; writes lie on one 32-byte projected-record line each. | Reachable normal cache lifecycle. No extra zero/prime is introduced by Build 26. |
| `MESH_CLASSIFY=0` | All transforms generate outcodes. Enabled classification chooses screen-only/no-check transforms for wholly inside bounds; crossing bounds retain all checks. | Source comment estimates about 8 cycles/vertex for outcodes; no new current-base warm/cold trace is claimed. Projected cache is 256×32 B plus outcodes. | Compile choice, not a runtime decline in R=0. |
| `MESH_VP_SCHED=1` | Compile-time ordinary kernel, diagnostic=2 double evaluation, or diagnostic=3 runtime selector choosing the old kernel. | Same transform outputs, different scheduling; U per vertex on this base. | Active scheduled kernel. Diagnostic workloads are not silently included in a production speed claim. |
| `MESH_STRIP_LEAN=1` | No SQ destination, checks other than All, diagnostic old-path selection, or knob 0. | General C strip walk (`w_strip_general`), U per meshlet plus E(n)/C(n). Some classified paths do less checking; “general” does not universally mean slower. | Reachable in alternate configurations; actual selected path is counted. |
| Direct / buffered output, `MESH_DIRECT=1` | The emitter uses a packet destination instead of SQ. | Stage 32-byte vertices then packet commit; `w_submit_buffer`, U per strip and downstream submission. | Counted only at actual buffered writes, not successful culls. |
| Depth / capacity clip admission | Any near/far outcode and no common rejecting depth plane, or n exceeds the sink limit. The strip can also be wholly outside one screen edge; depth admission is evaluated first. | C(n). `w_clip_depth` and `w_clip_cap` are exclusive per Emitter call, with capacity precedence. `chunk_clip_depth/cap` count actual non-null callbacks in the shared backend. | Reachable near the camera. Common-depth culls are not fallback. Null callback drops are not counted as executed clip callbacks. |
| `MESH_CLIP_LEAN=1` | At 0, every triangle rebuilds three corners. At 1, the frustum pretest can reject the whole strip; otherwise up to 16 corners can use the once array when the accept ring is disabled. Longer strips retain the per-triangle path in that mode. | `w_clip_rebuild` counts actual scalar corner transforms, including pretest; general path 3(n−2), once array n plus pretest. U transform cycles; exact accesses depend on decoded fields. | Actual work, including work done before a later refusal; not a completed-triangle count. |
| `MESH_CLIP_ACCEPT=1` | A triangle crosses near in the ring path; mode 0 or diagnostic runtime old selection calls the shared clipper on accepted triangles too. | Accepted ring triangles use packed/reused words; crossing triangles call shared clipping. `w_clip_project` counts actual authoritative calls, excluding the optional mode-2 comparison call. U per triangle. | Reachable. Accepted and crossing triangles retain original visibility/alpha math. |
| Screen/guardband handling | Native strip paths reject common screen-outcode planes; otherwise accepted depth strips are sent to the PVR, including screen-edge crossings. The scalar clipper still performs its original XY visibility and near/far tests. | Accepted strips E(n), near crossings C(n). There is no independent world “guardband material fallback” in these functions. | Audit does not count screen-edge crossings as exact CPU clipping unless the actual depth/capacity call runs. Model/GX guard/clip paths are inventoried by the model lane. |
| `CPU_BACKFACE=0` | Mode 1/2 conditional cull/depth/alpha/room restrictions keep the ordinary emitter; mode 2 has its own accepted-triangle SQ walk. | U determinant/run-splitting work; clipped strips still use C(n). | Compile-time off in this recipe. New indexed clip supports 0/2, rejects unqualified 1. |
| `PS2_VERTEX_ALPHA=1` | Marked parts use ARGB4444 and source alpha; unmarked parts use ARGB1555/material alpha. | LUT or scalar decode of existing color; no per-vertex lighting. U per corner. | The marked path does **not** leave streaming, LEAN replay or the shared clipper. Both alpha states are covered by the geometry controls. |
| OP/PT/TR, `WORLD_AUTOSORT=1` | Pass/material selects translucent queue/list; soft alpha remains translucent, and screen coverage can increase near camera. | Native path remains the same geometry machinery; extra PVR overdraw/sort work is U. | The queue's MODELS XLU count cannot be assigned to world clipping. Counts of translucent draws are not automatically fallback counts. |
| `FOLIAGE_TRIM=2`, `TRANS_POLICY=3`, `FOLIAGE_NEAR_FIX=1`, pass mask=1 | Unlisted keys, vertex-alpha overlays or retained soft materials keep their authored pass; part-specific near cut can invalidate a placement-inside shortcut. | Ordinary selection/draw of retained geometry; U. These controls intentionally change visibility/pass appearance. | Public policy comments identify chapter-1 foliage, r109 walls/floor, r10b/r11b mist. Build 26 changes none of these policy outputs. |

## World route, ownership and GC fallback

The PS2 draw entry does **not** try legacy R4P drawing after an R4IM failure.
`PS2_WORLD_MESH` is a compile-time route selection. A declined R4IM draw
returns to the caller's existing source/coarse policy; a negative return after
publication is an abort. Likewise, `re4dc_static_submit` is probed for many
generic model parts. Ordinary `!static_geometry` parts are excluded from
`w_gc_owner` so their normal route is not reported as a lost world owner.
Sources: [PS2 world entry](../../game/platform/native_ps2_world.cpp),
[static submit](../../game/platform/native_static.cpp),
[generic model dispatch](../../game/platform/native_model.cpp).

| Split / R | Trigger / selected work | Cost / chapter evidence / counter |
|---|---|---|
| `PS2_WORLD_DRAW=1`, `PS2_WORLD_MESH=1`, `PS2_WORLD_ROOMS=2`, registry=1 | Unsupported/unregistered room, no camera, missing/rejected package, invalid projection/far, or unsuccessful native pass. Claimed-owner loss uses the existing fail/abort contract. | U per decline; **no completed fallback cost inferred**. `w_ps2_package/camera/projection` and `w_native_decline` label admission outcomes. Registered chapter rooms are reachable. |
| `COARSE_SCENERY_FALLBACK=1`, `COARSE_SAT_SCENERY_ONLY=1` | Missing native ownership can keep source scenery; covered world avoids drawing collision-piece scenery. | U actual source-render cost, counted at the model/GX execution sites in the other lane. A world decline and source work may overlap; do not add them as disjoint parts. |
| `PS2_WORLD_DYNAMIC=1`, `PS2_WORLD_PARTS=1`, root pose=1 | Unmapped/unqualified live source placement/part, hidden/moved source, root witness/capacity condition. | Existing dynamic affine, qualified source fallback or hide/abort policy; U per candidate. Correct source ownership takes precedence over batching. |
| Source owner=1, transition/R11F owner=0 | Source-owned r200 preparations and current camera/material state; optional transition/R11F routes require their complete binding proof and current owner. | U; invalid claimed owner is not called a cheap successful draw. Their optional branch code is compiled out in the public recipe. |
| Source texture prepare/VQ/mip=1, `PS2_PRELOAD_LEAN=1` | Missing preparation/cache/owner proof or cold texture retains resolve/upload/rebuild work. | U per material/upload. Shared UI/material audit supplies actual execution reasons; no second texture resolver is added here. |
| World fog source=1, fog latch/sky/far options | Unknown/stale source fog or override selects existing fallback far/tint, sky uses its own far rule. | U bounds/fog setup; usually a policy parameter selection, not a geometry-path fallback. Existing appearance remains unchanged. |
| `PS2_PVS=0`, `PS2_INTERIOR_CULL=1` | PVS absent/inactive; interior file missing/stale/lent, outside supported room/subcell, or conservative portal intersection cannot hide geometry. | Retain ordinary geometry. U per retained bound/part. An active interior/PVS selector can itself disable chunk batching (`w_chunk_cell/pvs`). |
| GC `NATIVE_STATIC=1`, `NATIVE_MESH=1` | Static source lacks info/part/owner, binding lookup, valid current mesh package or matching material/source layout. | Native admission returns 0. `w_gc_owner/locate/package/material`, unit decline. Actual generic GX/model cost is U and counted by its execution lane. |
| Legacy compact static route (`NATIVE_MESH=0`) | Material already declined this frame; effective source vertex alpha cannot be represented by opaque package; invalid projection/depth; changed world transform has noninvertible old matrix. | `w_gc_cached/alpha/projection/transform`, unit decline. Not active at R=1. A moved valid object simply pays its matrix work. |
| Static mesh color preparation | A shared part is not yet marked lit. Existing `light_part` prepares colors once; no current lighting pointer can intentionally suppress an unlit replay under its existing contract. | U first-use lighting/record writes. R4IM PS2 world is already prelit and does not enter this GC light path. Build 25 is separate and not assumed merged. |
| Static reserve/bind/run failure | Reserve fails before draw; zero result permits fallback; negative result aborts after publication. | `w_gc_reserve` and `w_native_decline` are declines; `w_cache_*` are refusals. Existing aggregate abort counters remain authoritative. Never convert a negative abort into a counted successful source fallback. |
| Tree impostor / Standard quality | No impostor record, draw after PT flush, below switch depth, queue full, corner crosses near, or unsupported partial grove record. | Keep actual mesh/cluster work; U per retained mesh/tree. Whole-object and Standard per-tree predicates are both in `mesh_impostor`/`tree_quad`. |
| Standard / original asset admission | Missing/unqualified Standard package/texture/part proof restores ordinary package, or declines native owner as existing code specifies. | Cold I/O/validation and subsequent different geometry, U. Current private asset coverage cannot be inferred from source. |

## Legacy R4P and far shell

These are distinct routes, not an assumed chain of automatic fallbacks.
See [native_ps2_world.cpp](../../game/platform/native_ps2_world.cpp) and
[far_shell.inc](../../game/platform/far_shell.inc).

| Split / R | Trigger / selected work | Cost, counter and chapter reachability |
|---|---|---|
| Legacy R4P, `PS2_WORLD_MESH=0` | Explicit alternate build route; qualified original r101 source package required. | Compiled out of the selected route. R4P routines may remain in intermediate objects and be removed by final section collection. Not a cause of active R4IM barn fallback. |
| `PS2_WORLD_KERNEL=0` | In R4P mode, no optimized kernel: each surviving group uses scalar vertex ring and six-plane triangle clipper. | U per group/triangle; `w_r4p_general`, `w_r4p_clip6`. |
| R4P kernel 1/2 | A group is not proved wholly inside six planes; retained group takes full triangle clipping. Mode2 also compares old decisions. | U C6(T); `w_r4p_clip6`. Only qualified r101 alternate build, not active chapter-1 barn recipe. |
| R4P kernel 3/4 | Near/far crossing takes two-plane clip path; screen crossings use projected vertices/PVR and common-screen reject. | U C2(T); `w_r4p_clip2`. Normal clipping work is authoritative, diagnostic checks are extra. |
| R4P light/color cache; color-all=0 | Missing cache/owner/range entry or uncached color attribute. Crossing vertex path computes its own source color/normal lighting. | U per corner. `w_r4p_unlitcache` counts actual cache-miss color production; `w_r4p_normal` counts normal lighting in draw vertex preparation (not startup cache baking). |
| R4P bounds/group cache | Invalid/missing cache or owner sends each group through checked table-record decode instead of direct in-place cached access. | U per group; `w_r4p_checked`. |
| R4P kernel4 strip batching | Strip exceeds 64 corners. | Per-triangle projection/emission with winding instead of one strip; U, `w_r4p_longstrip`. |
| R4P admission/incomplete return | Owner/read attempt, source qualification, bad projection/far or incomplete pass. | `w_r4p_owner/proof/projection/incomplete`, unit decline. Incomplete can follow partial publication, so it is not a completed slow draw. |
| `FAR_SHELL=1`, mode default1 | View not Short, missing file/room match, movie loan, yielded heap, mode off/price arm, or unavailable camera. | No shell; existing fog/cut policy applies. This is not a software fallback renderer. r103 is explicitly cited in source as an example without a shell file. |
| Shell v2 levels | Cell depth picks fine/coarse level; own tight bounds still cull selected group. | More/fewer vertices according to existing approximation; U per group. |
| Shell material/scratch refusal | Direct begin fails or scratch cannot contain group's corners. | Group is refused; `w_shell_refused` unit decline. No buffered-shell fallback exists. |
| Shell near crossing | Any strip corner fails `w > near*1.01`. | Whole strip is deliberately dropped; `w_shell_near` unit drop. **There is no shell CPU clipper.** This preserves the existing shell approximation. |
| Shell accepted emission / hash diagnostic | Normal path copies cached 32-byte vertices to SQ. TA_HASH diagnostic routes equivalent words through the hash helper. | E(n), U bus cost. Diagnostic hash overhead is not interpreted as a production geometry fallback. |

## Counter contract and interpretation

[draw_fallback_world.def](../../game/platform/include/draw_fallback_world.def)
defines **57 world/static/shared-chunk reasons**. All additions to production
sources are under `#if RE4DC_DRAW_FALLBACK_AUDIT`; absent/zero compilation
contains no `hit`, observer array or audit helper. The shared core owns tick
sealing, pause/reset, snapshot, saturation and formatting; the root Build 26
report documents QA Diagnostics and QA_LINK transport.

The word `part` is an attempted logical rendering item, not a unique actor.
`corner` measures a specific operation, not unique mesh vertices. In
particular a clip pretest and the clip ring can both rebuild the same source
corner. `w_gather_full`/`w_gather_clip` count copies actually performed;
with indexed clip enabled those counters must be zero **for that indexed
streamed clipping operation**, though unrelated ordinary gathers can remain.

Chunk refusal predicates are counted in original short-circuit order:
no LOD, check mode, group count, PVS, interior, impostor exclusion, then queue
capacity. Only one reason is attributed to that admission. Capacity has
precedence over depth when a strip satisfies both conditions. Actual clip,
rebuild and project-call counters are additive stages and must not be summed
as disjoint input geometry. SG malformed-order and range-builder counts also
overlap by design. A shell decline/drop and a GC/PS2 admission decline are
explicitly distinguished from executed slow work. Non-null callback failure
still counts its executed clip attempt; a null callback does not.

Hot clip loops accumulate rebuilt/projected counts locally and write the
global counters at function exit, including early exits. Shell counts also
aggregate at draw exit. Other events are at the actual branch once per
part/meshlet/strip or, only on the legacy R4P route, per relevant corner or
triangle. No hot path formats strings, samples a clock, allocates memory,
loads assets, locks or transmits QA_LINK packets because of this observer.

## Validation, traffic and owner hand-back

[world_host.py](../../tools/cloud/build26/world_host.py) reuses the earlier synthetic authenticated
R4IM fixture and extracts the current production decoder/`clip_strip` body.
It compares full-gather input with direct indexed input using the real shared
`pvr_geometry.cpp`. All **61,440 comparisons pass**, including an
AddressSanitizer/UndefinedBehaviorSanitizer run: scattered offsets, aliased
local IDs, repeated indices, all 256 local slots across strips, 3–255 corner
strips, degeneracy, exact near, behind near, beyond far, zero projected depth,
all cull states, material/per-vertex alpha, ARGB1555/4444, nontrivial UV
bias/scale and packet refusal before/after publication. Compared output is
return status, used/output counts, clip statistics and every packet byte.
The projection adapter is scalar `1/abs(z)` for both arms; it does not emulate
SH4 FSRRA. The bounded packet sink is not a real TA owner or console test.

[world_audit_sites.py](../../tools/cloud/build26/world_audit_sites.py) executes the production chunk admission and shared
strip dispatch bodies. **128 selector combinations and 640 strip cases
pass**, covering first-refusal precedence, common-depth/common-screen culls,
depth/capacity precedence, actor-index masking, missing callback, callback
returns 0/−1, successful direct routing and disabled observation.
The committed [sanitized geometry receipt](../../tools/cloud/build26/receipts/world-host-sanitized.json)
and [site receipt](../../tools/cloud/build26/receipts/world-sites.json) bind
these results to the final source/extracted-body hashes and exact commands.

Independent current-source SH4 preprocessing with the actual QA profile and
`-E -P` is byte-identical to the base for all three changed TUs when both new
knobs are absent: `native_static` SHA256
`6d7a819989ee28465e72682b2fb93348c91477627e73b4d4929e93b9630e771b`,
`native_ps2_world` `7e6151b757772c7dcd9e590f75bba130c92d2cc8ce80036229055b9fe77dd8ac`,
`chunk_submit` `aeee15eec8d1c7c76ac716b383bb51c211f9afaa36a6be34c4c9708768bca144`.
The shared validation receipt supplies complete object identity, explicit-zero
arms, enabled composition and target section/stack results. Preprocessor line
markers and debug line metadata are excluded consistently; no final linked
game image or emulator/hardware acceptance is claimed by these host controls.

### Traffic removed by indexed clipping

Let V be meshlet corners, R be actual local-record reads by the scalar clip
pretest/ring/triangle path, and D be the decoded field-load bytes retained by
that path. Full staging adds **14V load bytes and 12V store bytes** before
the consumer's D. Direct indexing adds **2R offset bytes**, preserves the
consumer's field bytes, and makes **zero gather stores**. These are logical
payload counts; the target receipt separately counts actual instructions,
context/stack/literal traffic and addresses. Reused local indices can make
R large, and repeated direct pool reads can have worse locality than the
local array. A zero-copy implementation does not guarantee every dense strip
is faster.

For 64 corners the staging step alone touches 128 offset bytes, 768 pool
bytes and 768 scratch bytes; for 256 it is 512/3,072/3,072 bytes. The scratch
array spans 24 or 96 aligned 32-byte lines. Pool records can straddle lines,
and scattered offsets can touch far more source lines than a contiguous
byte-count estimate. Direct access only touches referenced offset/pool lines;
it does not release the existing gather allocation, because other paths
still use the same authenticated package's allocation.

For context, Build 24's exact full-gather fixture cost 1,589 warm / 1,664
cold-I cycles for a 64-corner sparse clipped pick, and 6,197 / 6,272 for a
256-corner sparse pick. Its total loads/stores were 1,095/808 and 4,167/3,112
bytes, touching 114 and 392 distinct lines in that deliberately scattered
fixture. These values include its wrapper and exclude clipping; they are
historical controls, not new current-base net gains. See
[the original world notes](../../tools/cloud/build24/world_notes.md).

### Current target source-acquisition cost

The frozen SH4 [source-acquisition fixture](../../tools/cloud/build26/world_source_cost.py)
and [target receipt](../../tools/cloud/build26/receipts/world-source-cost.json)
execute the actual production full/partial gather bodies and indexed accessor
with already-resolved package pointers. Every arm feeds the same synthetic
six-u16 sum/store consumer and produces identical results. This measures a
**bounded acquisition window**, including its wrapper and consumer; it excludes
the production decoder, projection, clip mathematics, packet emission and TA.
All 42 cases pass. The columns below are dynamic scalar load/store instruction
counts, distinct 32-byte cached data lines and observed peak stack bytes;
line counts are footprints, not cache misses.

| Meshlet / consumed corners | Source arm | Warm cycles | Cold-I cycles | Loads | Stores | 32-byte lines | Peak stack bytes |
|---|---|---:|---:|---:|---:|---:|---:|
| 64 / 3, one strip | Full gather | 1,686 | 1,813 | 367 | 209 | 116 | 48 |
| 64 / 3, one strip | Partial gather | 294 | 452 | 70 | 41 | 17 | 60 |
| 64 / 3, one strip | Indexed | 140 | 228 | 44 | 15 | 12 | 44 |
| 256 / 3, one strip | Full gather | 6,294 | 6,421 | 1,327 | 785 | 394 | 48 |
| 256 / 3, one strip | Indexed | 140 | 228 | 44 | 15 | 12 | 44 |
| 256 / 64, one strip | Full gather | 7,758 | 7,885 | 1,754 | 846 | 403 | 48 |
| 256 / 64, one strip | Indexed | 1,909 | 1,997 | 532 | 76 | 99 | 44 |
| 256 / 96, same three corners in 32 strips | Full gather | 9,022 | 9,149 | 2,009 | 878 | 408 | 48 |
| 256 / 96, same three corners in 32 strips | Indexed | 3,457 | 3,545 | 1,005 | 139 | 27 | 44 |

For the 64/3 control, full gather loads/stores 1,162/836 bytes, partial
gather 214/158, and indexed access 122/60. The 956-byte executable fixture
contains all three arms; its total allocated size is 1,048 bytes with no
zero-fill section. These are fixture sizes, not a claimed production code
delta. Compiler static frames are 40 bytes for the full wrapper plus its
8-byte gather callee, 40 plus 20 for partial, and 44 for indexed. The complete
production object/stack changes are reported by the shared Build 26 target
gates. No new persistent allocation is introduced by the indexed accessor.

Warm cycles use the repository scheduling model with perfect I/D caches.
Cold-I starts with an empty instruction cache; D-cache is still perfect.
Neither includes memory-bus stalls, SQ/DMA cost or final completion drain.
The footprint reduction is therefore evidence of removed memory work, not
an estimate of data-cache miss latency.

**MODELLED whole-frame contribution, assumed 100 independent 64/3 clipped
picks at 200 MHz:** this acquisition window changes from 0.843 to 0.070 ms
warm, a **0.773 ms saving**. Summing 100 separately cold-I windows gives
0.9065 to 0.114 ms, a 0.7925 ms saving; that pessimistic reset assumption
is not a continuous frame cache simulation. No observed chapter-1/2 frequency
is assigned to 100 picks. Remaining clipping and frame work are unpriced,
so these are neither total-frame times nor measured console gains. They must
remain separate from the 1,191 microseconds of console clip-category time.

No per-branch unpriced entry above is replaced by a fictional zero. The owner
should rank actual `w_gather_*`, `w_clip_*`,
`w_chunk_*`, matrix setup, generic model/GX and shared texture/header rows
under the same r101/r103/chapter route scenes before deciding which knobs
to enable. Dense/repeated-index cases, graphics appearance and STRICT logic
remain local acceptance gates.
