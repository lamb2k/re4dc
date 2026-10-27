# Build 24 — draw setup audit and exact clipping experiments

2026-10-27 · base `a9fa0b8850f762acbf3ce49e86d7c24394df894b` (`origin/t15/int`)
· branch `codex/draw-setup-audit-20261027`.

This handback adds `DRAW_SETUP_AUDIT`, `ACTOR_CLIP_REUSE` and
`SCENERY_CLIP_GATHER`. All three default to **0**, independently. The fixes
remove repeated work without changing the intended drawing output. No release
recipe, world package, gameplay policy, assembly implementation or production
linker layout is changed. Console acceptance remains with the local owner.

The assignment and existing console readings are in the
[cloud queue](../../../docs/cloud/CLOUD_AGENT_QUEUE.md#drawing-on-hardware-added-2026-10-27).
They are evidence supplied with the assignment, not measurements made by this
build. The farm's 5–6 fps problem is **not yet explained or claimed fixed**.

## First correction: what the old setup number includes

In [`main.cpp`](../../../../../src/game/main.cpp), the loop calls
`ProcessTickInit()` **before** `Render_before()`, `ClearOTagR`, `PadRead`,
`DebugControl`, `Render()` and the `ProcessTickGet(4, "RENDER SETUP")` marker.
[`debug.cpp`](../../../../../src/game/debug.cpp) makes that marker elapsed time
since `ProcessTickInit`. Therefore the old setup residual is not a measurement
of `Render()` alone. In particular,
[`Render_before`](../../../../../src/game/main_sub.cpp) calls the native frame
begin, which can contain PVR/presentation waits. The queue's attribution of
`Render_before` to time outside TOTAL needs this correction; its historical
readings have not been rewritten.

The new observer records both the inclusive legacy setup interval and the
actual inclusive `Render()` call. Its exclusive `FRAME BEGIN` bucket separates
`Render_before` from drawing work. It also measures the full loop
begin-to-next-begin interval, including work outside the old TOTAL. Differences
of old rolling averages do not establish where a current frame stalled.

The reported near-bodies `gpu_avg=16 ms` does not rule out CPU-side store-queue
or TA FIFO waits. Those occur while submitting work and need their own timing.
Likewise, clipping and source reconstruction also execute in an emulator; the
hardware-specific suspects are cache/bus cost, queue backpressure and possible
alignment exceptions, rather than a known console-only clipping branch.

## Source audit and predictions to test

| Suspect and source site | Mechanism and expected scaling | Evidence and disposition |
|---|---|---|
| Actor clip reconstruction: `native_actor_fast.cpp`, `Part::clip_strip`, `world_of`, `Records` | A depth-crossing strip rebuilds three world/projected vertices for each input triangle. A strip of `n` corners performs `3(n−2)` preparations, repeatedly gathering position records, skin palette data, projected UV/colour and opacity. More bodies and more near-plane crossings can raise this independently of enemy AI. Hardware cache/bus penalties amplify the repeated traffic. | Concrete redundant work. Exact rolling reuse is experiment 1. It affects clipped strips only; ordinary accepted strips retain their existing fast path. A mostly three-corner population can fail to benefit. |
| Indexed scenery gather: `native_static.cpp`, `MeshDraw::emit_pick`, `stream_gather`, `corners`, `strips_lean` / `strips_bf_sq` | `SCENERY_STREAM=1` transforms from the shared pool. The first clipped strip then gathers **all** local vertices, even when the clipper reads only a small subset. Each gathered corner reads a 16-bit offset and three 32-bit source words, then writes three words to the existing local array. Near walls can trigger this gather; a sparse, scattered pool can touch many otherwise unnecessary lines. | Concrete redundant traffic. Experiment 2 fills only referenced local slots, once each per selected meshlet. Dense/repeated-strip cases can regress because every index pays a mask probe. |
| Clip expansion and submission bursts: actor `Part::put/strip`, world `Emitter::clip_strip`, `re4dc_ta_put`, `native_ui.cpp` direct/packet/batch entry points and `stream_send` | Depth clipping produces independent output triangles, breaking strip reuse and increasing 32-byte TA vertex traffic. Large nearby polygons can create bursts and CPU waits even when GPU rendering is short. Work can move between CLIP and SUBMIT without changing output count. | Instrumented separately. No FIFO bypass, SQ ownership change, relaxed capacity check, draw reordering or batching policy change. Current recipe already enables `MESH_CLIP_LEAN`, `MESH_CLIP_ACCEPT` and `SCENERY_SUBMIT_BATCH`; these are not new fixes. |
| Cache competition: actor per-info preparation, palettes, source records, `Re4dcModelPart`; world pool offsets, 12-byte records, projected cache and outcodes | Each model/part touches descriptors and matrices, then walks source and transformed arrays. More visible models and indexed pools increase working-set competition and reuse distance. A 12-byte vertex can straddle 32-byte lines. The world projected cache is about 8 KiB before outcodes and other state. | Both fixes report architectural memory accesses and lines. Unique lines are not cache misses. Actor reuse reduces repeated accesses but does not prove a smaller working set; the fixture touches one extra line. World sparse gathering demonstrably reduces the gathered source/destination footprint. PM14 events on hardware must settle cache impact. |
| Per-frame list, matrix and light work: `trans.cpp` `ModelRender`, `trans_ot.cpp` `ExecOt`, actor preparation, `native_model.cpp`, deferred-view restore | Model callbacks, material setup, view/light snapshots, matrix/palette preparation and queue traversal scale with submitted parts. Deferred translucent nodes also include sprites, water, UI and post effects. | `ExecOt` walks an already-built linked ordering table; this audit found no new per-frame sort inside it. MODEL timing covers model callbacks and actual deferred model work. Non-model deferred nodes remain RENDER OTHER. Generic GX fallback is timed and marked `unsupported` because its detailed native topology census is unavailable. |
| Alignment traps: R4IM reader in `room/instanced_mesh.hpp`; word moves in world gather; actor source/record/palette loads | A genuinely misaligned halfword/word access can behave differently on SH-4, with severe cost if serviced by an exception path. More accesses would amplify such a defect. | No offending address or measured exception was found. R4IM adoption checks section/index bounds and offset alignment; its 12-byte records use four-byte-aligned word copies. Actor paths check ranges/strides, but those checks are not a proof for every source pointer. Keep this as an unconfirmed audit item, not a diagnosed cause; no speculative pointer masking or exception-handler change. |
| Far shell: `far_shell.inc`, `re4dc_far_shell_draw` | Group selection, per-vertex projection and strip submission grow with accepted shell groups. Camera-dependent setup repeats, but there is no evidence that this explains the bodies-specific slowdown. | Separate SHELL timing/counts; no shell geometry, projection, range or rejection policy change. |
| Frame start and residual: `Render_before`, native frame begin, loop pacing/present | Render/TA readiness waits can make the old setup residual large. Pacing and work after setup can also explain why fps and the old per-tick TOTAL are not reciprocals. | Separate FRAME BEGIN plus outside-named-work residual and full wall interval. These are elapsed CPU-side intervals, not pure CPU execution or GPU time. |

The day/night and near/far observations justify prioritising these paths but do
not distinguish them. Flycast's motion/heap/body-logic/VRAM checks are useful
negative evidence **on Flycast**; they do not eliminate all hardware I/O,
memory or scheduling behaviour.

## What `DRAW_SETUP_AUDIT=1` reports

The implementation is in [`draw_setup_audit.cpp`](../../../game/draw_setup_audit.cpp)
and its [header](../../../game/platform/include/draw_setup_audit.h). It requires
`QA_MENU=1 WORLD_METER=1 PVR_STREAM=1`. The Make fragment rejects unsupported
prerequisites. It does not require either fix, or PMU instrumentation.

The QA **Diagnostics** snapshot adds 38 rows next to the existing world-meter
rows. Long rows wrap; left/right (or up/down) changes pages. X retains the
existing QR snapshot. Existing world-meter and DSA rows have their own windows;
do not silently combine measurements from different snapshots.

| Display | Meaning |
|---|---|
| `WORLD OP/PT`, `WORLD TR`, `SHELL`, `MODELS` | Exclusive native world opaque/punch-through, world translucent, shell and model-list paths. Nested world work replaces its parent model attribution. Shared deferred world-dispatch overhead is in WORLD TR; actual PT draws select WORLD OP/PT. |
| `FRAME BEGIN`, `RENDER OTHER`, `OTHER DRAW` | `Render_before`; other setup/Render work including non-model deferred nodes; drawing hooks reached outside a named parent. Untimed categories are retained in the outside residual. |
| `WORK / CLIP / SUBMIT` | Three mutually exclusive phases within each path. Clipping can temporarily enter submission, so output stores/flushes are not double-counted as clip time. Work contains selection, transforms, material preparation and other non-clip/non-submit work; use existing WORLD_CENSUS24 for its finer world breakdown. |
| Inclusive setup and `Render()` | Microseconds per logic tick, with separate whole-loop wall mean/max. These are inclusive spans and must not be added to the exclusive table. |
| Models / parts | Models are source `ModelRender` callback invocations, not distinct actor identities. Parts are native submission/replay attempts; retries, declined actors and chunk splits can contribute additional attempts. World placements are not added to the model callback counter. |
| Triangles IN / OUT | Raw window totals from native paths. IN is topology reaching selected strip traversal; OUT is CPU-produced topology after clipping/rejection, including packet staging or direct output later abandoned/discarded. Counts can include degenerate or hardware-culled primitives and are not pixel coverage or proof of TA consumption/presentation. |
| Clip triangles / rebuilds / strips; gathered vertices | Work reaching clip strips, source/projected reconstructions, strip invocations and copied indexed-world corners. Actor triangles count attempted per-triangle clipping, including a final capacity refusal. World clip triangles count strip input topology; a reject prepass can avoid some triangle calls. |
| XLU sent / view-overlap | Translucent **triangles**, using the same CPU-produced/staged definition as OUT, with a conservative projected viewport/common-plane overlap check. This is not the number of visible pixels, depth-visible triangles or distinct translucent objects. |
| `unsupported` | A coverage qualification. Generic GX/R4P fallback, unsupported alternative direct/classify/backface paths, incomplete world staging or unmatched alternate actor output must not be interpreted as a complete native geometry census. Actor staging followed by a later abort does not necessarily set this counter. Time still remains accounted. |

Windows seal after **300 drawn ticks**, configurable to 300–600. A drawn tick
contains at least one completed streamed PVR scene, including a scene later
discarded; it is not a display flip. `scenes` separately counts multiple scene
finishes. `ticks`, `attempts`, `skip`, first/last tick and the identity are shown.
All ticks in the window contribute elapsed time and counts, including skipped
or failed work. Thus `us/drawn tick = raw window us / drawn`, while setup/wall
use `ticks`. This keeps catch-up cost visible without confusing logic cadence
with presentation cadence.

The identity is room, view distance, PVS, opaque/translucent policy, shell
policy and renderer epoch. Main's room is authoritative. Identity changes,
reset and menu boundaries discard unfinished windows. Menu time is excluded;
the last sealed window survives an ordinary pause. Epoch/depth checks reject
stale or misordered scopes, foreign-thread hooks do not read the PMU, and clock
reversal/overflow/incomplete scopes remain visible errors. Named phase time
plus outside time must reconcile to the raw wall interval.

There is no heap allocation or per-vertex timer/PMU read. Counts use integer
updates. Same-path/same-phase nested scopes avoid extra clock/PMU samples.
Formatting occurs for one bounded summary at window seal, or for the paused QA
snapshot; no drawing-loop logging is added. Translucent overlap checks do add
diagnostic CPU work, which is why a matched observer-off run is required.

### Optional cache events

Add `WORLD_CENSUS24=1 PERF_PHASE_MISS=1` and select event 15 or 37 using the
existing `PERF_PHASE_MISS_EVENT`. Run the existing PM14 control page first.
Event 15 is the operand-cache-miss experiment; event 37 is the operand-cache
stall-cycle experiment documented by Build 14. These are separate builds/runs,
not simultaneous independent measurements.

DSA reads the existing PM14 PRFC1 owner through a guarded read-only API. It
never starts, stops, resets or takes ownership of a counter. The timekeeping
counter is untouched. Owner generation, event/clock configuration, thread,
pause state, control qualification, plausible counter deltas and wrap handling
are retained. A discontinuity is a gap; unrun/unqualified events display NA.
Synthetic controls stay **SIMULATED**, never QUALIFIED. Samples are CPU-wide
and include observer/interrupt work; they are not perfectly isolated misses
caused solely by the named function.

## Exact fix 1: `ACTOR_CLIP_REUSE=1`

[`actor_clip_reuse.hpp`](../../../game/platform/include/actor_clip_reuse.hpp)
maintains the existing three clipping corners and three opacities. After each
successful triangle it retains the two overlapping corners with the correct
strip parity and prepares only the next corner. It does not allocate a
strip-sized cache or change float expressions, projection, UV16 conversion,
lighting, alpha, clipping, output order, capacity checks or ownership.

For an uninterrupted strip, preparations fall from `3(n−2)` to `n`. Early
refusal stops before preparing the next corner. Useful diagnostic controls
for valid strips, including an aborting final triangle, are:

```
OFF: ClipRebuilds = 3 * ClipTriangles
ON:  ClipRebuilds = ClipTriangles + 2 * ClipStrips
```

The [actor notes](actor_notes.md) and receipts give the full cases and pricing.
The scalar fixture executes compiled SH-4 preparation/control instructions
using the production `Part::clip_strip`, `world_of` and projection bodies. Its
observed clipper edge returns zero output to isolate the changed reconstruction
work; common clipping arithmetic, TA/device waits and real D-cache misses are
excluded. Full clipping/output equality is checked separately by the host
fixture.

| Near-crossing fixture | Warm cycles OFF → ON | Cached loads OFF → ON | Cached stores OFF → ON |
|---|---:|---:|---:|
| Rigid, 64 corners | 78,025 → 32,998 | 21,356 → 9,355 | 9,849 → 4,985 |
| Skinned, 64 corners | 99,043 → 40,038 | 26,937 → 11,148 | 10,221 → 5,113 |

A three-corner strip regresses by 23 modeled warm cycles (rigid) or 14
(skinned). The fixture's peak stack rises from 716 to 736 bytes and its unique
32-byte data-line footprint rises by one. The justified claim is fewer
repeated preparations and accesses, **not** fewer unique actor lines or a
measured cache-miss reduction. Far-depth forced-clip controls prove semantics;
ordinary far-depth strips normally use the existing fast path and are not
evidence of a shipping speedup.

## Exact fix 2: `SCENERY_CLIP_GATHER=1`

[`scenery_clip_gather.hpp`](../../../game/platform/include/scenery_clip_gather.hpp)
adds a 256-bit local-slot mask plus a lazy-initialisation flag (36 bytes of
state) to `MeshDraw`. For every clipped strip it copies only unseen referenced
local slots into the **existing** gathered array, preserving original indices
and the same three aligned word moves. The mask resets for each new selected
meshlet and persists across its strip groups. Direct transformations keep
reading the shared pool. Plain meshes keep their original base.

Every indexed-stream clipping consumer is covered: `strips_lean` and the
`CPU_BACKFACE=2` path. Their clipper reads only `base[index[i]]`, including the
homogeneous reject prepass, ring acceptance, short-strip reuse and fallback.
The feature requires `SCENERY_STREAM=1 SCENERY_CHUNK=1 MESH_DIRECT=1
PS2_WORLD_MESH=1`, `SCENERY_EMIT_PREFETCH=0`, `SCENERY_DEDUP!=3` and
`CPU_BACKFACE=0` or `2`. DEDUP=3 is excluded because its offline-position
consumer can read a different local slot. No builder/data-format change is
needed.

The [world notes](world_notes.md) contain the exact traffic, stack/code and
crossover table. A 64-vertex meshlet with one three-corner clipped strip saves
most of the gather. Full coverage regresses: the same copies now also pay mask
tests. More clipped strips with duplicate indices further lower the crossover.
The current recipe has reverted the n256 world pack; 64-vertex examples are
therefore primary, while 256-vertex controls cover the reader's maximum.

For `N` local vertices, `U` distinct referenced local slots and `K` inspected
clip indices, the copied vertex payload changes from `12N` bytes read plus
`12N` written to `12U` plus `12U`. Offset reads change from `2N` to `2U`, with
`K` byte-index reads and mask traffic added. Alignment, straddling and pool
spacing determine the distinct 32-byte lines; the receipts count those actual
addresses rather than dividing bytes by 32. Mask state is stack-local, not an
extra persistent world buffer.

## Measured fixture results and validation scope

Final target-gate and cost receipts are listed below. All timing in these
receipts is **MODELLED**, with perfect D-cache, warm or initially cold I-cache,
and no console/device claim. The pinned SH-4 compiler is GCC 15.2.0 with KOS
threads; binutils is 2.45.1. The public toolchain image is
`maishuji/dc-kos-image@sha256:aed8f106bccd705a554acf19ab224ef4d05f7d66f669ab8031872e458a9132fe`.
KOS is `804b3195ebd1a06a27cc2b3a5eacf7a2429040a3` plus the three repository PVR
patches; SH4ZAM is `33fa4850cacb30dd0ad35485ef035526ec4ce782`. The
[toolchain receipt](receipts/toolchain.json) records the restored compiler and
its local musl launch wrappers.

The public Make-derived compile uses the existing assetless fallback flags.
The current recipe sets `NMR_POOL_LOD=1` while that fallback disables
`GANADO_LOD`; this combination is rejected by Make. Validation therefore sets
`NMR_POOL_LOD=0` **in both base and candidate arms**. This is a validation-only
adjustment, not a recipe correction or private-asset validation.
Debug records are omitted consistently from both sides of the identity gate,
as in the existing Build 18 profile reader; comparisons cover the complete
preprocessed output and complete resulting ELF object bytes. They do not claim
identity of a final linked game image or of path/line-dependent debug records.

### Semantic and output controls

| Gate | Result and evidence |
|---|---|
| Actual observer + actual PM14 owner | 36 deterministic cases in both ordinary O2 and ASan+UBSan builds: exclusive reconciliation, inclusive setup/Render, skips, pause/reset/identity, stale/misordered scopes, wrong thread, missing completion, clock reversal, nesting overflow, invalid enum, unrun PMU, counter loss and 48-bit wrap. Counter starts/stops remain with the existing owner. [Normal](receipts/core-controls.json), [sanitized](receipts/core-controls-sanitized.json). |
| QA rendering | Actual diagnostic pagination/font and actual sealed observer rows at 320×240 and 640×480, 16/32-bit framebuffer modes. All guards pass; the synthetic snapshot wraps to 7 and 2 pages respectively. Captures were inspected for readable text/footer. [Receipt](receipts/qa-render.json). |
| Actor output | Packet and direct modes, 3,766 and 3,774 cases per OFF/ON arm, respectively; each configuration includes 8,130 helper controls. Ordinary and ASan+UBSan arms match full emitted TA, ownership and state bytes. [Receipt](actor_receipt.json). |
| World consumer output | 320 packages, 20,480 comparisons each in fallback/lean/ring-accept modes: 61,440 total, repeated under ASan+UBSan. Actual reader, exact production clip consumers and bounded host projection/sink adapters. Scratch output words, counters, outcomes and canaries match. [Receipt](receipts/world-host.json). |
| Actor scalar target | 25 compiled SH-4 reconstruction cases; every prepared vertex/opacity byte matches. Near/far controls, rigid/skinned/source stride-6 and lengths 3–128. [Actor receipt](actor_receipt.json). |
| World scalar target | 34 cases / 68 OFF/ON executions; exact scratch/untouched-slot checks, sparse/full/repeated strips, no-clip and executed crossover neighbours. [Receipt](receipts/world-target.json). |
| Observer scalar target | 16 cases covering time-only and synthetic PMU-reader arms. Actual core instructions; real hardware timer, PMU, thread/identity services, formatting and adapters are outside the priced edge. [Receipt](receipts/observer-cost.json). |

### Complete target compilation and disabled identity — PASS

The [target receipt](receipts/target-controls.json) covers 11 translation units:
main, trans, native UI, native static, native actor, generic native model,
native PS2 world, QA menu, PM14, WORLD_CENSUS24 and the new observer. In the
applicable QA and QA+PMU profiles, absent and explicit-zero controls match the
pinned integration base in **36 complete preprocessed outputs and 36 complete
ELF objects**. No new observer object is admitted when its knob is off.

All six enabled compositions compile their complete translation units and
relocatably link with the new audit hooks resolved: audit alone, actor fix
alone, world fix alone, audit plus both fixes, audit plus PMU event 15, and
audit plus both fixes and PMU event 37. Eleven invalid Make configurations are
rejected. This is a source/build composition gate, not a final executable or
game-state/console test.

The public assetless profile excludes the dying-actor FIFO branch. A
[supplemental gate](receipts/fade-controls.json) therefore compiles the real
complete native UI translation unit with exactly
`RE4DC_ACTOR_GANADO_DEATH_FADE=1` added to all compared arms. It adds **four**
passing absent/zero source/object comparisons, for **76 total** across the two
gates, and verifies that the enabled tagged-node ModelList hook is present.
This explicit compile-only override does not qualify a private-asset recipe
or death-fade runtime behaviour.

The [object summary](receipts/object-summary.json) compares matched relocatable
groups before final executable garbage collection. Deltas below are bytes
against the corresponding QA or PMU baseline; allocated bytes include code,
data and zero-fill. They are not final game image growth:

| Enabled composition | Executable delta | Allocated delta | Zero-fill delta | Matched base |
|---|---:|---:|---:|---|
| Audit | +7,856 | +17,628 | +8,455 | QA |
| Actor fix | +156 | +156 | 0 | QA |
| World fix | +264 | +264 | 0 | QA |
| Audit + both fixes | +7,928 | +17,700 | +8,455 | QA |
| Audit + event 15 | +9,444 | +19,238 | +8,480 | PMU |
| Audit + event 37 + both fixes | +9,404 | +19,206 | +8,480 | PMU |

The PMU baseline uses event 15, so the event-37 row also includes that selector
change; it is not an isolated comparison of the fixes against event 37.

In the full target objects, actor clipping's old 556-byte static frame becomes
a 460-byte reuse frame and a 108-byte preparation-lambda frame (468 bytes for
the reuse frame with audit). These frames cannot be interpreted as independent
whole-program peak-stack totals. `native_static`'s largest compiler-reported
frame rises from 9,008 to 9,040 bytes with the world fix; actor TU maximum
remains 2,388 bytes. Existing large renderer frames remain a console stack
headroom check. No claim is made that fixture peak-stack accounting replaces
that check.

### Warm/cold cycles and traffic for the world gather

This is the already-resolved gather method, including fixture wrapper/stack,
mask, index/table and literal traffic. Pool/header resolution, transforms,
clipping and TA work are excluded. Distinct lines depend on the synthetic
scattered-pool addresses.

| Synthetic pick | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Load bytes OFF → ON | Store bytes OFF → ON | Distinct 32-byte lines OFF → ON |
|---|---:|---:|---:|---:|---:|
| 64 vertices, 3 referenced once | 1,589 → 206 | 1,664 → 322 | 1,095 → 151 | 808 → 130 | 114 → 16 |
| 64 vertices, all referenced once | 1,589 → 2,646 | 1,664 → 2,762 | 1,095 → 1,554 | 808 → 1,106 | 114 → 118 |
| 256 vertices, 3 referenced once | 6,197 → 206 | 6,272 → 322 | 4,167 → 151 | 3,112 → 130 | 392 → 16 |
| 256 vertices, all across two strips | 6,206 → 10,399 | 6,281 → 10,515 | 4,168 → 6,026 | 3,112 → 4,198 | 393 → 402 |

For one distinct-index strip on a 64-vertex meshlet, the warm model wins at
37 referenced vertices and loses at 38; cold-I wins at 36 and loses at 37.
Repeated-strip populations change this boundary. This is not a runtime
threshold or a scene recommendation. The gather method's compiler frame is
8 → 20 bytes, wrapper-inclusive peak stack 32 → 44 bytes, and the caller's
mask state adds 36 bytes. See world notes for all 34 cases and the full-TU gate
for actual object growth.

### Observer cost must be budgeted

These are actual compiled core instructions with small deterministic service
stubs. A cold-I case starts an 8 KiB instruction cache empty for the complete
case. Data cache is perfect in both arms. `L/S` counts architectural cached
accesses; lines are distinct 32-byte data lines, not fills/misses.

| Core operation | Time-only warm / cold-I cycles | L/S; lines | With synthetic PMU warm / cold-I cycles | L/S; lines |
|---|---:|---:|---:|---:|
| Enter changed path | 188 / 418 | 44 / 13; 15 | 379 / 785 | 102 / 48; 24 |
| Leave changed path | 175 / 385 | 39 / 12; 13 | 373 / 758 | 97 / 47; 25 |
| Change phase | 163 / 379 | 38 / 12; 12 | 361 / 735 | 96 / 47; 23 |
| Aggregate count update | 108 / 272 | 24 / 7; 12 | 108 / 247 | 24 / 7; 12 |
| Finish prior tick and begin next | 3,771 / 4,237 | 750 / 643; 88 | 4,042 / 4,687 | 835 / 702; 95 |

Production core executable bytes are 4,508 without PMU and 4,952 with PMU;
zero-fill state is 3,335 / 3,356 bytes. Its largest compiler-reported frame is
320 bytes. The modeled next-tick call chain peaks at 336 / 384 bytes. These
exclude the caller hooks and existing PM14 implementation. The QA snapshot
buffer grows from 3,072 to 8,192 bytes only in audit builds (plus a four-byte
page index). Full object deltas are in the target receipt.

### Whole-frame examples — **MODELLED**, hypothetical populations

The assignment requires a whole-frame figure. These scenarios state the
assumed population explicitly; none is a measured farm frame or fps estimate.
Use 200,000 cycles per millisecond at 200 MHz:

| Assumed work per drawn tick | MODELLED warm impact |
|---|---:|
| 32 rigid near-clipped actor strips, each 64 corners | `(78025−32998) × 32 / 200000` = **7.20432 ms less reconstruction** |
| 100 indexed 64-vertex picks, each one three-corner clip strip | `(1589−206) × 100 / 200000` = **0.6915 ms less gather work** |
| Both of those populations, observer off | **7.89582 ms less priced work**; excludes shared clipping, rendering and real cache/device effects |
| 100 indexed 64-vertex picks, each full coverage | `(2646−1589) × 100 / 200000` = **0.5285 ms more gather work** |
| Observer: 1,000 changed-path scope pairs, 200 phase changes, 2,000 count updates, one completed tick | **3.076855 ms** time-only core; **5.22121 ms** with synthetic PMU reader |
| Observer: five times those scope/phase/count calls, one completed tick | **15.308855 / 26.02521 ms** respectively |

The observer figures additionally exclude actual timer/PMU/OS service costs,
translucent overlap traversal, adapter bookkeeping, periodic formatting,
interrupts and memory/bus contention. They show that measurement overhead can
be material, especially in a highly clipped scene. Do not subtract these
hypothetical figures from the console readings. Use actual paired observer-off
measurements and the real window populations before accepting either fix.

## Console run requested from the owner

1. Use the current farm-barn27 QA recipe/data and the same daytime room/save,
   camera, body population, view distance, PVS, world-pass and shell settings.
   Capture near barn/bodies and approximately 20 m away, then r101 cross as a
   control. Do not combine different pack or corpse states in one comparison.
2. Baseline: all three new controls 0. Record existing fps/pacing/QA data.
   Diagnostic: `DRAW_SETUP_AUDIT=1`, fixes 0. Wait for a completed 300–600 drawn
   tick window at each stationary view and capture all Diagnostics/QR pages.
   Require the intended identity, zero errors and a reconciled wall sum. Read
   `unsupported` before interpreting detailed counts.
3. Run actor reuse alone, world gather alone, then both, with diagnostic on
   for explanatory counts. Preserve draw order/output with the owner's
   gameplay, image and TA-equivalence gates, including death fade and camera
   crossings. A failure/refusal should retain the old safe behaviour.
4. Repeat the performance pairs with **DRAW_SETUP_AUDIT=0**. A reduction in an
   instrumented bucket alone is not performance acceptance. Pay special
   attention to short actor strips and dense/repeated world clipping, where
   the modeled tradeoff is adverse.
5. For cache attribution, use separate event-15 and event-37 diagnostic
   builds, run PM14's resident/miss-heavy controls on the console, and record
   QUALIFIED status, samples, gaps and wraps. The prior emulator's inconclusive
   PMU results are not hardware qualification.

Interpret the result by mechanism: FRAME BEGIN growth points toward readiness
waits; MODEL CLIP plus reconstruction counts toward actor reuse; WORLD CLIP
plus gathered vertices toward indexed gather; SUBMIT growth with output
expansion toward TA/SQ bursts. If those stay small while MODEL WORK grows,
investigate descriptor/palette/light preparation and its misses next. The
exclusive outside residual keeps an unexplained remainder visible.

No setting is promoted automatically. Claude owns the merge; the local owner
decides whether either fix should be enabled after the console pairs.

## Reproduction

Run from the repository root. Output directories must not already exist.
These use synthetic/public inputs only:

```sh
python port/dreamcast/tools/cloud/build24/run_core.py --output /tmp/b24-core
python port/dreamcast/tools/cloud/build24/run_core.py --output /tmp/b24-core-san --sanitize
python port/dreamcast/tools/cloud/build24/qa_render_check.py --output /tmp/b24-qa
python port/dreamcast/tools/cloud/build24/actor_host.py --output /tmp/b24-actor
python port/dreamcast/tools/cloud/build24/actor_host.py --output /tmp/b24-actor-san --sanitizer
python port/dreamcast/tools/cloud/build24/world_host.py --output /tmp/b24-world
python port/dreamcast/tools/cloud/build24/world_host.py --output /tmp/b24-world-san --sanitizer
```

Supply the pinned compiler/KOS/SH4ZAM and toolchain receipt using your local
paths, then run the complete Make-derived gate and scalar observer model:

```sh
python port/dreamcast/tools/cloud/build24/build_controls.py \
  --output /tmp/b24-target --sh4-cxx "$B24_CXX" --kos-root "$B24_KOS" \
  --sdk-root "$B24_SDK" --toolchain-receipt "$B24_TOOLCHAIN_RECEIPT"
python port/dreamcast/tools/cloud/build24/target_cost.py \
  --output /tmp/b24-observer-cost --sh4-cxx "$B24_CXX" \
  --kos-root "$B24_KOS" --sdk-root "$B24_SDK"
```

Actor/world notes describe their scalar pricing commands and assumptions.
Receipts retain source hashes, compiler/command provenance and fixture limits.
No game asset, generated object/ELF, framebuffer capture or private console
recording is part of this change.
