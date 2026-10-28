# Build 26 — draw fallback inventory and two clipping candidates

Branch `codex/draw-fallback-audit-20261028`; base `origin/t15/int`
`9a66e3fce8899f69378f12b5f9517f297f1fa314`. Claude owns merging and the
private console/appearance/gameplay gates. Build 25 was published first as
`ee9a5c4126fdabfc272951995ee8570013b9d52a`; it is not part of this integration
base. This branch does not silently stack or duplicate its lighting change.

## Result and evidence boundary

`DRAW_FALLBACK_AUDIT=1` adds per-reason counters to world/model/effect/texture
paths (133 reason bins) and publishes the **last completed game tick** on QA Diagnostics and
QA_LINK `T` rows. The independent `ACTOR_CLIP_FRONT26` and
`SCENERY_CLIP_INDEXED26` knobs address two concrete near-camera clipping
costs. All three default to **0**; no existing recipe is enabled.

The queue provides aggregate barn timings, not per-reason incidence or a
ranked chapter 1–2 trace. No private game data or console is available here.
Consequently these are **provisional clipping candidates**, selected from the
recorded clip work and inspected source. They are not represented as the two
largest measured chapter 1–2 fallbacks. The counters and concrete candidates
are ready for the owner's required run; ranking and enablement remain open.

## Inventory and how to read it

- [World, shells, legacy R4P and chunk paths](BUILD26_WORLD_AUDIT_20261028.md).
- [Actors, generic models, skinning, light, clipping and batching](BUILD26_MODEL_AUDIT_20261028.md).
- Texture, effects, shared packet submission and sort paths are listed below.
- The three `platform/include/draw_fallback_*.def` registries give the exact
  telemetry labels and units. A unit is an item, corner, triangle, attempt,
  decline or drop as stated; it is not always a model or a completed draw.

The inventories distinguish executed slow work, an admission decline that
may lead to another path, and an abort/drop. These cannot be added into a
single "fallback percentage." Nested counters overlap: a legacy model can
also miss a shade cache, clip triangles and use buffered submission. A zero
may mean no occurrence, a disabled path, or a path not exercised by that tick.
Source reachability is not a claim that a private chapter asset uses a path.

Costs that depend on unprovided mesh sizes, cache state, source hashes,
texture sizes or storage latency are given structurally, with unpriced terms
identified. They are not invented numeric cycle measurements. The compiled
counter and clipping fixtures below are the numerical MODELLED evidence.

### Texture, effect and shared submission inventory

Recipe values are taken from the public recipe plus `build-r21.sh`, resolved
by Make in the validation receipt. Diagnostic override values belong to the
explicit composition, not the release recipe.

| Split / knob | Slow trigger and counter | Work and data cost per item | Chapters 1–2 / remedy |
|---|---|---|---|
| `UI_HANDLES` | Handles disabled: `tex_nohandle`; nonrepresentable base/mask descriptor: `tex_shape` | `image_key` and full entry search; keying may scan identity/source tables or source bytes. Indexed masks, malformed palette shapes and dimensions outside the direct-handle contract cannot use a direct descriptor hit. Numeric I/O/hash cost is unpriced. | Public recipe enables handles. Descriptor-specific incidence requires data. Convert unsupported image/mask forms offline; preserve palette/identity invalidation. |
| `UI_QUAD_LEAN`, direct handles | No qualifying descriptor/stamp/live-palette hit in either enabled way: `tex_handle` | One or two 32-byte handle lines, then full resolve. Stale entries, hash collisions, changed descriptors and palette invalidation can all trigger it. | Two-way mode is enabled in the recipe. Source comments document r101 collision pressure before that fix. Count remaining misses before adding associativity. |
| `UI_PALETTE_SLOTS` | Missing/wrong-size palette copy or unequal live word: `tex_palette` | Compares up to 512 palette bytes and its retained copy; on mismatch, the full resolve may follow. A failed palette probe is a subset of attempted handle validation, not a separate completed load. | Recipe uses 32 slots; historical r101 HUD collisions are documented in the source. Mutable palette content must still be revalidated; no stale-palette shortcut is proposed. |
| Resident texture entry / `TEX_RESIDENT`, `TEX_PACK` | After resident lookup and fail-fast refusals, first package open/upload pipeline: `tex_open` | Entry/identity search plus metadata/open and pixel upload; bytes depend on the package. Disc wait, VRAM fencing, bounded eviction retries and allocation failure are unpriced device terms. The counter is a load attempt, not upload success or each retry. | Any chapter can first see a texture, evict it or enter a room. Preload qualified packages and improve residency/layout; never count missing/budget/fragment-latched early refusals as completed uploads. |
| `ESP_SPRITE_FAST` header cache | Texture/size/address/blend/screen key differs, or cache disabled: `fx_header` | Rebuilds a PVR sprite context/header, one 32-byte output header. Cached hits retain the same header semantics. | Common sprites occur throughout the route; exact run census is private. Group only already-consecutive compatible source-order sprites. |
| `ESP_SETUP_LEAN` | Batching absent, including disqualification by `TA_GUARD`, `TA_HASH`, `TA_BIN_DIAG`, `TA_MATERIAL_DIAG`, or no native sprite support: `fx_setup_off` | Writes/copies the 32-byte header instead of a body-only node. Existing queue capacity is deliberately unchanged. | Recipe default is off. This audit preserves the existing diagnostic restrictions; enable separately only after the existing gates. |
| `ESP_SETUP_LEAN` run eligibility | Batching compiled but predecessor ownership, key, screen or colour differs: `fx_batch_break` | Full header node; body-only path saves one 32-byte header write and submission read. A standalone/RTT call has no queue predecessor and cannot inherit a header. | Can occur whenever source OT changes sprite state or interleaves models. Offline reorder is not assumed safe for translucency. |
| Native sprite / common GX effect work | Common effect reaches normal-matrix/GX setup after native sprite eligibility/fast-return handling: `fx_legacy` | Matrix inverse/transpose, GX state and any remaining primitive work; expensive operations are not timed by the cheap counter. A rejected fast sprite that returns without drawing is not counted here. | Nonfast common effects can occur; custom effect functions are separate renderers, not failed `EspSpriteEmit` calls. Qualify data/semantics before conversion. |
| Opaque/direct versus deferred translucent model | Accepted deferred snapshot: `model_defer` | Copies word-differenced view/light state into the bounded frame queue, later restores it and dispatches the model again. `COPY_LEAN` removes repeated scans; `BRIDGE_LEAN` changes the word-copy implementation. | Barn's recorded translucent geometry establishes translucent work, not this bin's exact count. Order, masks and depth policy still require deferral. |
| Frame queue versus spill | Successful `deferred_spill` selection: `queue_spill`; native sprite subset `fx_spill` | Additional tail storage locality; same bytes of admitted view/packet data. Rejected allocations and the separate r200 tail adapter are excluded. Post/effect/model bins overlap the general spill counter. | Queue pressure is plausible and source-documented, but a route trace must establish incidence. Offline packet reduction or existing exact body-only sharing is preferable to larger heaps. |
| Direct TA output versus buffered packet copy | `stream_send`: `submit_copy` | Copies `bytes/32` packet lines through the existing SQ/PVR submission and acquires/releases its lock. One call is one packet, not one triangle. Device/SQ stalls are unpriced. | Common for effects, UI and fallback packets. Native actor/world direct writers are inventoried separately. No new SQ/IRQ policy is introduced. |
| Model/PS2 header cache | Cache miss or a special uncached model header: `packet_header`; source/native UV scale differs: `packet_uv` | Compiles a PVR polygon header or requests exact UV preparation; numeric cost depends on the packet path. | Can occur on first use or changes in pass/blend/depth/wrap/mask/cull/fog. Keep exact header keys and scale checks. |
| `COPY_LEAN`, `BRIDGE_LEAN` | Copy-lean-off snapshot attempt: `queue_repeat`; words compared on byte-copy path: `queue_wordcopy` | Copy lean off normally scans view words twice once a basis exists; its first basis-less snapshot scans once. Word comparisons include size scans before allocation and attempts later refused. Bridge lean avoids tiny unaligned libc copies. These are setup attempts/work, not extra geometry or proof of admission. | Both knobs resolve to 1 in the recipe. Off compositions remain observable; no default changes. |
| `G1_PRESORT_LAZY` versus immediate sort-mode write | Immediate KOS request: `sort_rewrite`, including single-bank fallback; a genuinely changed lazy flush: `sort_changed` | Existing KOS tile-matrix rewrite, about 600 uncached tile records at 640×480; CPU/device wait cost is unpriced. Recipe value is 1. Lazy mode coalesces requests only where the existing double-buffer ownership contract permits it. | World autosort and UI presort transitions occur in ordinary rendering. Preserve blend order and bank ownership; no speculative sorting change is made. |

`tex_shape`, `tex_handle`, `tex_palette`, `tex_nohandle` and `tex_open` describe
different layers. In particular, a full resolve may find a resident entry and
perform **no** upload. `fx_header`, `fx_setup_off` and `fx_batch_break` similarly
describe header compilation versus header emission; they are not disjoint.

## Tick, menu and telemetry contract

The audit begins at the existing main-loop tick boundary, records the
pacing draw decision, and seals only at the completed-tick boundary. A new
room invalidates the previous room's snapshot. Menu entry stops collection
and retains the last completed snapshot; menu exit waits for the next tick.
Reset clears validity. Paused or incomplete ticks never masquerade as a
completed one. Counters saturate at `UINT32_MAX` and set an overflow bit.

`F26 seq=... tick=... room=... drawn=... overflow=... items_per_tick=last_complete`
is followed by compact rows of four named counters. `drawn` records the draw
attempt decision, not proof of a successful PVR presentation. It also exposes
zero-work paced ticks. QA telemetry requests a sample once per second, after
the previous snapshot has been accepted by the link. Backpressure can extend
this interval. A single sample can miss a transient event; retain repeated
rows and match their tick/room identifiers. There is no hidden lifetime average.

The production core and actual QA row/part formatter pass host and ASan/UBSan
checks for lifecycle, all 133 bins, saturation, maximum decimal counts and
14 framing cases. The new rows occupy 3,424 bytes at maximum values; the
longest row is 110 bytes and maximum tested datagram is 1,130 bytes. A sealed
snapshot is 552 bytes.

The enlarged snapshot exceeds link28's 2,400-byte bulk queue admission cap.
The old burst sender would lose later parts even from an empty queue. Under
`DRAW_FALLBACK_AUDIT` only, a bounded producer now retains one immutable
snapshot and retries its unaccepted part at most once every 50 ms. It advances
only after acceptance, keeps sequence/timestamp/part count stable, and cancels
on disconnect. The existing full-size telemetry buffer is reused; command
receive still precedes each send attempt. Transport admission and heap guards
are unchanged. This repairs delivery of this build's enlarged `T` snapshot;
the separate Build 28 review remains responsible for other link traffic.
Telemetry refresh also preserves the viewed Diagnostics page; reading a
counter page for longer than one second no longer resets subsequent paging.

The actual producer passes 21 backpressure cases with 50/300/2,000 ms drain
cadences and initial heap refusals: 593 attempts, 518 refusals, maximum queued
bytes 2,263, exact eventual payload reconstruction, no pending-snapshot
overwrite, and fresh identity after cancellation. These are bounded host
policy simulations, not modem throughput measurements. A continuously refusing
transport cannot deliver a snapshot; retries remain bounded and visible in
the existing bulk-skip count. Formatting cases also exercise the original
part formatter through an accepting transport.

The hot `hit` operation uses fixed static storage: no heap, clock, formatting,
locks or IRQ changes. Its single-writer contract is the game/render thread;
transport/presenter threads do not format or mutate counters. The Diagnostics
buffer is 7,168 bytes standalone (old 3,072), or 12,288 alongside DSA (old
8,192). QA_LINK's existing static telemetry copy follows that size. This is
an observable diagnostic BSS cost, not a heap allocation or a release change.

## Two independent fixes

`SCENERY_CLIP_INDEXED26=1` borrows the authenticated indexed package's immutable
vertex pool and u16 offsets directly during the synchronous clip call. The
same corner decode, transform, scalar clipping and packet order run without
first gathering the entire meshlet into staging storage. This is intended to
be exact. It is limited to the supported streamed/direct chunk configuration;
Make rejects incompatible prefetch/backface/dedup modes. It composes with
Build 24's clip-gather control, which becomes unnecessary for these corners.

`ACTOR_CLIP_FRONT26=1` uses the existing projected cache for wholly-front
triangles within a crossing strip. Actual near/far crossings retain source
reconstruction and the current clipper. It checks indices, depth outcodes,
finite coordinates and visibility before emission, preserves strip parity,
colour/alpha and UV16 packet semantics, and composes with `ACTOR_CLIP_REUSE`.
It is a **render approximation**: cached transform/reciprocal rounding can
change subpixel coordinates and boundary culling relative to scalar
reconstruction. No pose, AI, events, collision or source geometry is changed.

No new production SH-4 assembly or linker script work is used.

## Qualification and numerical costs

Final source-bound receipts are in
[`tools/cloud/build26`](../../tools/cloud/build26). Target/compiler scope,
public-profile overrides and exact commands are recorded there. Public
translation-unit/helper proofs do not establish a full private linked image,
Flycast route behavior, hardware cache misses or console timings.

**Final target gates PASS:** 200 exact comparisons cover ten existing
translation units × QA_LINK off/on × five disabled-control arms (absent,
each of three controls explicitly zero, and all zero) × complete preprocessed
source/complete target object. Compiler debug records and preprocessor line
markers are consistently excluded; compared bytes are not normalized or
stripped. Make flags and complete game/platform object lists also match.
Seven enabled compositions compile and resolve all new audit hooks, including
DSA + XLU + QA_LINK + the old setup/bytes/clip/gather/effect optimizations.
Final source/dependency closure was rechecked after the last QA page fix.

See [target-off.json](../../tools/cloud/build26/receipts/target-off.json),
[target-on.json](../../tools/cloud/build26/receipts/target-on.json) and
[production-metrics.json](../../tools/cloud/build26/receipts/production-metrics.json).
The public profile mirrors `NMR_POOL_LOD=0` in both arms because the selected
chapter-2 LOD assets are private. The pinned GCC/KOS/SDK provenance and exact
reproduction method are in [VALIDATION.md](../../tools/cloud/build26/VALIDATION.md).

Geometry/contract qualification passes **61,440 exact world packet/status
comparisons** (including ASan/UBSan), **128 world admission combinations**,
**640 world dispatch cases**, and **four actor configurations × 3,940 cases**
in both normal and sanitized runs. The actor fixture also checks all seven
APLAN miss mappings and invalid-kind bounds. These synthetic cases exercise
the production functions, not private chapter frequency or hardware rounding.

Production object sizes use the individual fix profiles against the actual
baseline object, with public flags held equal. They are pre-link object
measurements, not a final executable-size promise.

| Object / composition | Executable bytes OFF → ON | Allocated section bytes OFF → ON | BSS change |
|---|---:|---:|---:|
| `native_actor_fast`, actor fix only | 60,676 → 61,836 | 75,434 → 76,597 | 0 B (12,991 B retained) |
| `native_static`, world fix only | 71,108 → 72,068 | 114,930 → 115,890 | 0 B (17,345 B retained) |
| `qa_menu`, audit with QA_LINK=0 | +488 B | See target receipt | +4,096 B |
| `qa_menu`, audit with QA_LINK=1 | +732 B | See target receipt | +8,228 B |

The linked synthetic actor-cost fixture grows by 1,088 executable bytes;
the enabled production `Part` layout grows by 4 B. The world acquisition
fixture contains 956 executable bytes across its three arms. These fixture
sizes are separate from the production object deltas above.

For QA_LINK, the compiler's local `link_pump` frame grows from **2,264 to
2,708 B**. Telemetry formatting/step are inlined; `snap_diag` stays **2,280 B**
and new `diag_rows` uses **176 B**. These are local frames, not measured
combined stack peaks. The single pending snapshot reuses the previous static
telemetry copy; its metadata accounts for the remaining BSS increase.
World clipping's local frame is 560 → 572 B; actor clipping's is 556 → 684 B
with a 36 B classifier frame. The execution-fixture peak values below cover
their stated call paths separately.

Across the complete measured object set, audit only adds **6,072 B text /
14,676 B allocated including 5,200 B BSS** with QA_LINK off; with QA_LINK on
it adds **6,316 B text / 19,053 B allocated including 9,332 B BSS**. Both
fixes alone add **2,120 B text / 2,123 B allocated / 0 B BSS**. Audit plus
both fixes with QA_LINK adds **8,440 B text / 21,180 B allocated including
9,332 B BSS**. These are sums before linker garbage collection, not final
image or runtime memory measurements.

The cost evidence is in [counter-cost.json](../../tools/cloud/build26/receipts/counter-cost.json),
[world-source-cost.json](../../tools/cloud/build26/receipts/world-source-cost.json)
and [actor-front-cost.json](../../tools/cloud/build26/receipts/actor-front-cost.json).

The actual counter core has 14 target execution cases. The following are
architectural loads/stores and distinct 32-byte data lines, including stack
and literal loads; they are not hardware cache-miss or bus-transaction counts.
Warm costs assume perfect instruction/data caches. Cold-I costs start an
8 KiB instruction cache cold for the individual sequence while retaining the
perfect-data-cache assumption; do not sum individual cold costs into a frame.

| Counter operation | Warm cycles | Cold-I cycles | Loads | Stores | 32-B lines | Observed peak stack |
|---|---:|---:|---:|---:|---:|---:|
| One active hit | 20 | 51 | 5 | 1 | 3 | 0 B |
| One hit adding 24 items | 19 | 50 | 5 | 1 | 3 | 0 B |
| Begin, same room | 295 | 370 | 20 | 145 | 25 | 12 B |
| Seal completed tick | 336 | 418 | 153 | 143 | 41 | 8 B |
| Copy sealed snapshot | 315 | 405 | 146 | 140 | 38 | 8 B |

The audit core object has **768 B executable code**, **5,310 B allocated
sections including 1,104 B BSS**. Its static compiler stack frames are 8 B
for begin, 4 B for seal/snapshot and 48 B for formatting; the observed peaks
above include callees. Formatting, modem transport and data-cache stalls
are unpriced by the hot-counter fixture.

| Bounded fix window | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Loads OFF → ON | Stores OFF → ON | 32-B lines OFF → ON | Peak stack OFF → ON |
|---|---:|---:|---:|---:|---:|---:|
| World, 64 vertices / three consumed corners | 1,686 → 140 | 1,813 → 228 | 367 → 44 | 209 → 15 | 116 → 12 | 48 → 44 B |
| Actor, 64 skin vertices / one near vertex / 61 front triangles, reuse off | 99,057 → 27,971 | 99,758 → 29,082 | 26,942 → 7,286 | 10,222 → 4,634 | 158 → 308 | 720 → 904 B |

The world window runs the actual gather/accessor with a common synthetic
six-u16 consumer; package resolution, decode, projection, clip mathematics
and TA are excluded. Its 42 cases include sparse, dense, aliased and repeated
corners. Partial gathering is separately priced in the world report.

The actor window runs the real `Part::clip_strip`, source reconstruction,
projection and new cached packet writes across **18 cases × four arms**.
The shared clip callback checks its prepared inputs and returns zero; its
clip mathematics, old packet writes and TA are excluded. The ON path really
writes the cached packets, so its **line count increases** and the two arms'
output-write scope differs. This table must not be read as a complete draw
cost or as an overall data-traffic improvement. Peak stack also increases.
With existing `ACTOR_CLIP_REUSE=1`, the same warm case is 40,051 → 28,047
cycles. The forced all-near control regresses: 99,057 → 105,925 cycles with
reuse off, and 40,051 → 57,569 with reuse on. That eligibility overhead and
the hardware rounding approximation are reasons to keep the new knob off
until the owner ranks and checks real inputs.

**Whole-frame MODELLED sensitivity, 200 MHz:** assume 30 ms of omitted work
held constant in both arms, ten of the actor skin-strip cases above and 100
of the world three-corner cases. The priced OFF windows plus that assumed
remainder total **35.795850 ms**. Both fixes plus 1,000 counter hits and one
begin/seal total **31.571705 ms**, a **4.224145 ms MODELLED** difference.
The counts and remainder are assumptions, not chapter observations; old
clip/output work, real cache misses, SQ/device costs and telemetry cadence
are not inferred from this figure. Separately, audit-only sensitivity is
30.000000 → **30.103155 ms MODELLED** for 1,000 hits, or **31.003155 ms** for
10,000 hits, with the same assumed 30 ms remainder. These are sensitivity
calculations, not claimed barn frame rates.

## Owner questions and required local hand-back

1. Run `DRAW_FALLBACK_AUDIT=1` with both candidate fixes off in the barn/yard
   and chapter 1–2 route. Retain complete `F26` parts, the matching DSA rows,
   image/asset hashes and knob snapshot. Which reasons actually fire, and
   which dominate cost after accounting for units and overlapping bins?
2. Rank the two candidates against that evidence. If other reasons dominate,
   use the documented conversion/approximation proposals instead of calling
   these the measured top two. Re-run the relevant OFF/ON pair with identical
   input/camera captures and the owner's gameplay/still gates.
3. Merge Build 25 separately and reconcile the intentional light-path overlap.
   The fast-only build's zero invariant must stay zero; legacy light-decline
   counters must not be mistaken for executed vertex lighting in that build.
4. Run full knob-off image identity, private-asset compositions, s30/heap/VRAM
   and console checks. Diagnostic BSS and observer work are included in this
   report; real data-cache/SQ/device penalties remain outside the instruction
   model. Claude owns merges and release enablement.
