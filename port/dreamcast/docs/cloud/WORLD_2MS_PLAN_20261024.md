# RE4 Dreamcast plan for a 2 ms world

Date: 2026-10-24. Status: research and implementation proposal; the 1–2 ms world budget is not yet proven on console.

This handoff preserves the researched plan and qualifies historical reduction results against [WORLD-NEXT.md](../WORLD-NEXT.md). The publication base is `t15/int` at `6958054abfa1b32eb5d370f782a6bbf9fd4f63c9`; the research snapshot named below remains pinned. Implementation follows the existing [cloud branch and handback rules](CLOUD_AGENT_QUEUE.md). The complete plan and source references are included here.

The objective is to bring the RE4 Dreamcast port to 30 fps while making the world a small part of the frame. The working definition of “essentially free” is **at most about 2 ms of world CPU work per drawn frame, with 1 ms as a stretch target**. That budget includes the complete visible scenery path. It is a design requirement to test, not a result already achieved.

The strategy is to build a convincing, much smaller visual representation of r101, compile it into cheap Dreamcast draw data, and prove the cost before extending the approach to other rooms. Preserve the recovered game’s collision, AI, progression, camera, interactions, and state. Retain the village’s recognizable structures and readable combat spaces.

The evidence baseline is the user’s 49.3 ms console result and repository snapshot `t15/int` at `9f6a25c61df6ad635c46e837b2371fc8b523ada6`, checked on 24 October 2026. The Sega NINJA Guide supplied with this request provides the primary historical rendering reference. Current KallistiOS documentation supplies the supported implementation guidance.

## The performance requirement

| Measure | Requirement or evidence |
| --- | --- |
| Current console frame | 49.3 ms, supplied by the user |
| 30 fps deadline at nominal 60 Hz | About 33.33 ms |
| Required recovery to reach that deadline | About 15.97 ms, or 32.4% |
| Working whole frame budget | About 31 ms before deliberate pacing, giving roughly 2.3 ms of margin |
| Required recovery to reach the working budget | About 18.3 ms |
| Proposed world CPU budget | About 2 ms per drawn frame; 1 ms stretch |
| GPU acceptance | Measure PVR work and waits separately; the integrated game must meet its presentation deadline |

World accounting includes scenery selection, bounds checks, transforms, clipping, material/header preparation, submission, near geometry, distant shells, and opaque, cutout, and translucent scenery. Include world-related replacement work even if it runs under a different profiler label. Dynamic doors and scenery interactions need explicit accounting so they cannot disappear from the comparison.

The old 19 October model assigns 19.1 ms to world drawing in a 47.8 ms frame. Going from 19.1 to 2 ms would remove 89.5% of that world cost. If that old allocation also applied to the 49.3 ms console frame, the arithmetic would be 49.3 − 19.1 + 2 = 32.2 ms. That is useful motivation, but it is not a current console prediction. It would also leave only narrow headroom.

The 7.42 → 6.88 ms world-meter figures use a different denominator. The current meter documentation states that its values are means per logic tick, including skipped and no-world ticks. Reconcile them with per-drawn-frame timing before setting a production budget. Do not combine those numbers with the old exclusive model categories.

Sources: [current cloud queue](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/cloud/CLOUD_AGENT_QUEUE.md), [world meter contract](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/tools/d367/pvs23/README.md).

## What the NINJA guide contributes

Page references below use the printed NGD number; the PDF page is eight higher.

| Guide pages | What Sega describes | Consequence for the port |
| --- | --- | --- |
| NGD 12–17, PDF 20–25 | Strips share adjacent triangle vertices. Indexed data reuses transformed vertices and saves storage; direct vertex streams improve sequential access but can duplicate storage and transforms. | Count transformed inputs and emitted strip corners separately. Compare layouts on actual geometry instead of assuming that direct or indexed data always wins. |
| NGD 125–126, PDF 133–134 | Chunk organizes vertex and polygon data into predictable streams and updates material state by differences. | Compile a compact draw stream offline and retain only the state changes needed at runtime. |
| NGD 128, PDF 136 | Converter flags remove identity translation, rotation, scale, and unnecessary matrix-stack operations. | Precompute static work where the existing ownership and transform contracts permit it. Camera-dependent projection remains necessary. |
| NGD 129, PDF 137 | Specialized chunk types select specialized processing routines. | A simple static prelit world should not pay for unrelated model features. |
| NGD 143, PDF 151 | IndexOffset controls an intermediate transformed-vertex buffer and permits reuse across related geometry. | Reuse is implemented by software; adopting a file extension does not create automatic GPU vertex reuse. |
| NGD 144–145, PDF 152–153 | Padded SH4 formats trade more input bytes for convenient matrix processing. Normals are unnecessary for vertex-color-only models with no lighting calculation. | Compare input bandwidth with decode cost. Do not enlarge already compact source vertices merely to resemble an old SDK layout. |
| NGD 162, PDF 170 | Strip records refer to the intermediate vertex buffer and can carry corner-specific attributes. | Position reuse and UV/material seams are separate design concerns. |

The guide’s direct-stream discussion is particularly relevant. It identifies the trade between sequential access and repeated transformation, not a universal winner. The proposed experiment should test that trade on the reduced static world.

“Chunk” in NINJA is a data and processing format. It is not synonymous with a spatial cell, a modern meshlet, or a guaranteed cache-sized batch. The current port already has its own chunk and meshlet machinery. A wholesale NINJA format conversion has no demonstrated advantage.

Reference: Sega NINJA Guide (`Ninja_GD.pdf`, privately supplied by the user).

## What is already implemented or closed

The current world path already selects meshlets, transforms a vertex into a reusable cache, walks strips, and submits through store queues. Its scheduled transform uses SH4 vector operations and input prefetch. Header caching, identity-transform elision, matrix memoization, and compatible batching already exist. The prelit world’s compact input records are 12 bytes and do not carry a conventional normal vector.

The world’s `SCENERY_CHUNK` path is distinct from the shared `chunk_submit` backend. Moving everything to the shared backend is not an established gain. The recipe records that `CHAR_CHUNK` and an earlier scenery deduplication mode were turned off after measuring slower. Newer offline deduplication work must be judged separately.

The current world supports up to 256 vertices per meshlet. Its transformed cache and outcodes require 8,448 bytes at that maximum, an indexed gather can require another 3,072 bytes, and the color LUT is 2,048 bytes. These capacities total 13,568 bytes before other data. This is not a measurement of simultaneous cache residency, but it is a concrete reason to inspect the active working set and address conflicts.

| Work | Current disposition |
| --- | --- |
| World setup trims | Enabled in the accepted recipe |
| Build 5 prefetch | Landed default off; console result pending |
| Alternative Build 5 narrower-gather branch | Not merged; requires dependency/enclosure validation |
| Builds 6–9 | Landed default off; effects, actor bytes, animation, and UI still require real workload qualification |
| CPU back-face culling | Closed after the reported console regression |
| Cache RAM scratch mode | Closed after the reported +8.2 ms regression |
| Small-piece merging | Closed after 63% vertex growth |
| Re-stripping the existing world | Closed after only 0.1% corner reduction |
| Old cluster PVS | Closed; current PVS23 is a separately guarded visibility experiment with no proven current console saving |

A guide mentioning one of these techniques is not a reason to repeat its failed experiment. A new test needs different data or a different mechanism and a measurable hypothesis.

Sources: [world cache path](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/room/mesh_fastpath.hpp), [scheduled transform](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/room/mesh_fastpath_sched.hpp), [world emitter](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/game/platform/native_static.cpp), [current recipe history](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/tools/d367/test15/t15-build.sh), [cloud queue](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/cloud/CLOUD_AGENT_QUEUE.md).

## Build the visual world inside the budget

### Preserve the playable shape

The first representation keeps the village layout, source collision, navigation, camera, doors, windows, ladders, events, and destructible states. New visual surfaces must still agree with collision and readable lines of sight. An unchanged collision mesh does not excuse visible walls that Leon can walk through or empty-looking spaces that block movement.

Use world-fixed low-polygon walls, roofs, ground, and major openings. They retain genuine depth and parallax as the camera moves. Keep dynamic doors, destructible objects, and other stateful parts independently owned.

Spend geometry on silhouettes, roof edges, building corners, important openings, steps, nearby barriers, and recognizable landmarks. Replace small surface relief with the existing wall, roof, ground, and prop textures. Retain original prelit appearance where possible.

### Reduce the far world much further

The historical Short 12.5 m plus far-shell option is a useful comparison candidate, not proof of a negligible world. Establish the current accepted configuration from the pinned recipe and resolved switches. The historical fsh6 cross test put the far shell alone at about 2.23 ms MODELLED, with 2,073 transformed vertices and 90 groups. Near opaque geometry and other world layers were additional work.

The new representation therefore needs a far layer materially cheaper than the existing shell, or a different allocation between near and far geometry. Simplify building mass and silhouettes deliberately, reduce unnecessary groups within visibility-safe regions, and preserve only the distant details that contribute at the actual display resolution.

Use the documented 12.5 m distance as a controlled comparison alongside the actual accepted baseline. Change distances only after measured geometry and readability evidence supports the change. Fog saves CPU work only when geometry is actually omitted from selection and submission.

### Reuse textures before adding baked images

The previous global atlas experiment failed on texture density and VRAM availability. The accepted shell instead reused resident texture keys with no additional texture allocation. Its main-memory residency still mattered enough to cause an enemy-spawn regression before the lifetime policy was repaired.

Keep repeating textures where possible. Small local bakes may be useful for a specific feature, but each needs a texture-memory and quality budget. Blender can bake surface appearance into textures or color attributes; the result must still use a material path the Dreamcast renderer already supports. Avoid multiplying baked lighting by the original lighting a second time.

Large flat screenshots of the village are not the default representation. Camera translation reveals parallax and hidden surfaces, while enemies and doors need correct depth. A billboard has the depth of its plane. Object impostors or backdrop planes are suitable only where their restricted viewpoint and depth behavior remain acceptable.

### Preserve quality while reducing geometry

The 16 October world test found automatic simplification damaged four of five rooms. Protecting entire bins recovered appearance but often recovered much of the cost. An intermediate C16 correction restored fence rails by protecting mesh 0x17, which had been fused with the house front.

The subsequent [WORLD-NEXT disposition](../WORLD-NEXT.md) withdrew all automatic reduced r101 sets. It records that Tests 16 and 17 shipped the unreduced crowd12 bake13/Test 14 world with WORLD_VERT off. C16 still flagged 1,511 of 4,494 pieces, approximately 470 visible from walk-path cameras, and none of the reduced sets had a lost-part PASS stamp. The intermediate fence repair is historical evidence, not an accepted reduced-world baseline.

Use that evidence to protect features rather than giant source bins. Start with selective planar cleanup and manual architectural reconstruction. Automatic terrain or rock reduction still requires validated classification and the existing loss and appearance gates: the earlier terrain-only classifier incorrectly included trees.

Preserve the existing lost-part validation and its hash-bound staging checks. For deliberately reconstructed topology, record a source-feature-to-replacement mapping and validate equivalent visible features explicitly. A reviewed replacement and a silently deleted piece are different outcomes; do not manufacture a PASS stamp, weaken the checker, or treat a successful visual spot check as full coverage. Establish and review the replacement-validation method before production staging. A diagnostic proxy is not an accepted production asset.

The older coarse-world path provides a reusable technical precedent, but its historical low cost does not establish present feasibility or acceptable appearance. The project previously rejected its coarse look. Reuse extraction, ownership, and rendering mechanisms; build a fresh visual candidate against the current accepted reference.

Sources: [world reduction results and correction](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/tools/d367/worldtest16/RESULTS.md), [far-shell results](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/lanes/farshell16.md), [far-shell lifetime repair](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/lanes/farshell17.md), [existing coarse-world mechanism](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/game/coarse_world.cpp), [Blender baking documentation](https://docs.blender.org/manual/en/4.4/render/cycles/baking.html).

## Compile cheap draw data offline

Use the current PS2 world extraction and package tooling as the authoritative starting point. The existing far-shell extractor already exports positions, UVs, final prelit colors, texture keys, and pass identity. Legacy house-shell scripts contain reusable components, but a legacy BIN output is not automatically a valid replacement for the current PS2/R4IM world.

The existing [WORLD-NEXT tooling inventory](../WORLD-NEXT.md) says that the complete R4IM v3 + R4PW to Blender and back round trip was not yet built. The far-shell extractor and legacy tools are reusable components, not proof that this full round trip exists.

The authoring pipeline is:

1. Export the exact current private world and stable source/placement identities.

2. Prove a current-format identity round trip before intentional simplification.

3. Reconstruct the selected geometry in a pinned Blender workflow.

4. Export evaluated, deterministically triangulated geometry with explicit UV, color, material, pass, and ownership mappings.

5. Extend the accepted converter/serializer to produce an alternate package.

6. Regenerate every CRC-bound sidecar and verify the runtime interpretation.

7. Measure the converted package in the actual game.

Record source hashes, Blender version, script versions, modifier settings, coordinate conventions, winding, texture mappings, output hashes, and converted runtime counts. Keep private meshes, textures, Blender scenes, and generated game packs local. Repository deliverables can contain code, authoring instructions, manifests without embedded game data, and evidence summaries.

Prefer selection data that can be scanned without touching vertex payloads. Arrange visible draw data in compact, predictable streams. Keep opaque, cutout, and translucent material behavior explicit. Precompute static placement work only when doing so does not violate owner state or create an unacceptable residency increase.

The proposed 28-byte meshlet-record split into 16 bytes of draw data and 12 bytes of bounds is a bounded layout experiment. It could reduce emission metadata traffic; it does not cut the total world payload by 43%. Selection may need both tables, and sparse selected IDs can weaken the benefit. Measure selection and emission together.

Do not make every layout experiment contingent on prefetch succeeding. Prefetch changes when data is requested; repacking changes what is requested and whether it must be copied. A failed prefetch test does not logically reject the repack hypothesis.

Sources: [current far-shell pipeline](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/tools/d367/farshell/README.md), [PS2 world converter](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/tools/ps2_world_r4im.py), [Build 5 traffic audit and layout proposal](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/cloud/BUILD5_SCENERY_EMIT_PREFETCH_20261023.md).

## Run two bounded renderer experiments

### Compare local indexed data with direct strips

Run the comparison on the same reduced geometry, material set, camera path, and clipping behavior.

| Variant | Purpose | Cost to watch |
| --- | --- | --- |
| Current shared-pool path | Matched control | Scattered input reads and full indexed gathers |
| Dense local vertices plus local strip indices | Avoid runtime gathering while retaining transformed-vertex reuse | Resident duplication across meshlets and any extra conversion cost |
| Sequential strip-corner input with direct transform and submission where valid | Avoid transformed-buffer traffic for favorable static geometry | Duplicate transforms, extra source bytes, clipping fallback, and larger data |

Use the existing format’s plain/local representation if it can express the candidate safely. Introduce a new version only when its representation requires one. Retain correct fallback behavior for unsupported geometry and camera cases.

A current concrete opportunity is that a nonempty partially selected indexed meshlet gathers all its vertices before transforming the surviving interval. Narrowing that gather requires proof that every strip, clipper, and deduplication dependency lies within the admitted range. The unmerged narrow-gather candidate must not be layered on top of the landed Build 5 implementation without that proof.

Choose by integrated console time, RAM, and actual traffic. The indexed variant may win where reuse is high; the sequential variant may win where reuse is low and intermediate traffic dominates. The guide supports testing both.

### Measure the useful chunk size

Test a small bounded set, such as 32, 64, 128, and the current maximum of 256 vertices, using equivalent geometry through the production exporter. These are experimental settings, not a claim that any one is optimal.

Smaller blocks can reduce the simultaneously active working set and improve culling. They can also increase headers, strip restarts, duplicated corners, and setup. Record those costs together.

The direct-mapped SH4 cache also makes relative buffer placement relevant. Alignment alone does not prevent two active arrays from repeatedly replacing each other. Preserve the full cache and measure conflicts rather than reopening cache-as-scratch.

Sources: Sega NINJA Guide (`Ninja_GD.pdf`, privately supplied by the user), NGD 16–17; [Build 5 audit](https://github.com/lamb2k/re4dc/blob/9f6a25c61df6ad635c46e837b2371fc8b523ada6/port/dreamcast/docs/cloud/BUILD5_SCENERY_EMIT_PREFETCH_20261023.md); [Renesas SH7750 hardware manual, Section 4](https://www.renesas.com/en/document/mah/sh7750-sh7750s-sh7750r-group-users-manual-hardware).

## Apply the Dreamcast guides selectively

| Guidance | Action for this project |
| --- | --- |
| Precompile polygon headers and cache invariant matrices | Audit exceptional remaining paths; these mechanisms already exist in the main renderer |
| Use store queues for small direct bursts | Keep the current direct path as the control |
| Consider DMA for sufficiently large transfers | Require a measured advantage after buffer construction, cache maintenance, bus contention, synchronization, and memory costs |
| Keep source data aligned and compact | Preserve valid alignment without padding every input record to the output packet size |
| Use SH4 vector instructions efficiently | Retain the established scheduled kernels unless a measured representation change requires a new kernel |
| Reduce state changes | Batch compatible visible work without destroying spatial rejection or transparency order |
| Retain correct clipping | Fast paths need proven conditions; near-plane and exceptional cases retain correct handling |

The maintained KOS Bruce’s Balls example, credited to BruceLeet and Falco Girgis, is a useful direct-submission reference. Its advertised polygon throughput comes from a favorable sphere benchmark and cannot become an RE4 world budget.

KOS distinguishes low-overhead SQ bursts from larger DMA transfers. Its DMA API requires aligned buffers and transfer sizes in multiples of 32 bytes, and callbacks run in interrupt context. Burst DMA holds the bus during transfer, so nonblocking submission does not guarantee that a CPU waiting for memory becomes faster. Compare the complete path.

Sources: [KOS Bruce’s Balls](https://kos-docs.dreamcast.wiki/bruces__balls_8c.html), [Store Queues](https://kos-docs.dreamcast.wiki/group__store__queues.html), [PVR DMA](https://kos-docs.dreamcast.wiki/group__pvr__dma.html), [DMA controller](https://kos-docs.dreamcast.wiki/group__dmac.html).

## The r101 proof sequence

### Gate 0 Establish one trustworthy baseline

Pin code, asset hashes, compiler and SDK, resolved recipe, display mode, world options, actors/effects, camera route, and logging configuration. Capture the current accepted cross and an adjoining traversal.

Report per drawn frame and per logic tick separately. Record total wall time, world phases, actors, effects, simulation, other work, explicit waits, and presentation cadence. Add transformed inputs, actual emitted corners, material/header counts, source traffic where observable, and peak RAM/VRAM. Reconcile the residual frame time rather than assuming that the small set of named model categories accounts for everything.

Start with 300–600 deterministic frames after warmup and a baseline/candidate/baseline sequence. Repeat only where noise or drift prevents a decision. Use buffered summaries rather than hot-loop logging.

### Gate 1 Prove the world cost floor

Build a deliberately sparse, opaque r101 proxy using the existing visual-only boundary. Retain broad building mass, ground, major openings, and approximate occlusion while source gameplay, actors, effects, collision, AI, and camera remain active. This is a diagnostic candidate, not the proposed shipping appearance.

Compare the existing world, this proxy, and a limited set of payload sizes. The comparison should establish the console cost of realistic materials and clipping, rather than extrapolating from untextured geometry.

Pass when the full world path fits the provisional 2 ms budget and the whole-frame result confirms that the saving matters. If the proxy already exceeds the budget, inspect fixed selection, packet, clipping, and submission costs before commissioning more art.

If the proxy meets 2 ms but the game still misses 30 fps, measure the remaining deficit and assign it to the dominant non-world costs. World work does not close that independent deficit.

A world-disabled arm can supplement this diagnosis. Removing all opaque scenery can change GPU overdraw and visibility, so its delta is not a guaranteed shipping saving.

### Gate 2 Restore one complete representative view

Choose the cross plus a short walk around a high-cost building. Restore recognizable roofs, walls, ground, fence rails, openings, and landmark shapes, using existing textures first.

Add detail by named groups and report each group’s incremental transformed inputs, emitted corners, headers, resident bytes, and measured cost. Target a proxy below 2 ms so detail has room to return. The remaining time budget is a spending limit, not a promise that all original details can fit.

Convert the measured cost curve into asset limits for the actual worst camera: maximum useful transformed vertices, emitted corners, material groups, and bytes. Enforce those limits on the converted package. A Blender triangle target alone is insufficient.

Pass when the reconstructed candidate fits the world budget, remains recognizable and readable during movement/combat, and produces no visual/collision mismatch.

### Gate 3 Integrate only measured wins

Qualify the existing disabled switch candidates and any successful new layout separately, then measure their combined build. The original recipe-versus-two-switch console pair can decide that combined candidate; isolate the switches if attribution or a regression makes it necessary.

Use actual admitted PVS23 cuts and net console time to decide whether visibility belongs in the tiny world budget. A loaded table or selected cell is not a cut. A broad new per-triangle occlusion system has no slot unless it demonstrably costs less than the work it removes.

Do not add standalone savings together. Geometry reduction changes the workload on which cache and setup optimizations operate.

### Gate 4 Qualify the playable route

Use the actual camera, movement, aiming, doors/windows, required destructive states, representative busy combat, and room exit/reentry. Check appearance at the shipping output resolution and in motion.

Report median, p95, p99, maximum observed work duration, and missed presentation deadlines. A good average or p95 alone does not prove stable 30 fps. Require the intended cadence on the defined qualification route, with load transitions identified separately.

Pass the existing gameplay, ownership, heap, texture, and movie checks relevant to the changed paths. Preserve the far-shell lifetime fixes and required enemy allocations.

Only then extend the approach to the next measured worst room.

## Measurement details that matter

CPU drawing and GPU rendering overlap. KOS scene completion closes submission; interrupt-driven rendering and page flips can occur afterward. Sum nonoverlapping CPU phases, but do not add GPU duration to that total or count a blocked readiness wait twice.

The +8.2 ms scratch result is strong evidence that cache capacity matters. It does not locate all stalls in world records or prove that a particular repack will recover them.

Current KOS exposes performance-counter events for cache misses and related stalls. If the project’s pinned SDK and existing counter ownership allow it, use a free counter for phase-boundary measurements. Verify the event with a simple cache-resident and miss-heavy control. Do not reconfigure the counter already used for timekeeping. If this instrumentation is unavailable, console A/B timing remains sufficient to start.

KOS’s performance-counter nanosecond timer counts active CPU cycles and stops during CPU sleep. It is suitable for bounded active phases but cannot alone establish across-frame wall time. Use an appropriate monotonic timer and actual presentation/VBlank measurements for the deadline.

Sources: [KOS scene submission](https://kos-docs.dreamcast.wiki/group__pvr__scene__mgmt.html), [performance counters](https://kos-docs.dreamcast.wiki/group__perf__counters.html), [performance timer](https://kos-docs.dreamcast.wiki/group__perf__counters__timer.html).

## Ownership and first deliverables

Keep one coordinator responsible for the baseline, integration, and console packages. Use one runtime lane and one private asset lane with separate owned files. Validation can run alongside those lanes where it does not compete for the same emulator or console. This plan does not change current lane ownership or enable unqualified release switches.

| Owner role | First deliverable | Decision it enables |
| --- | --- | --- |
| Measurement and integration | Reconciled current drawn-frame census and matched console baseline | Establish the true world opportunity and remaining frame costs |
| Private asset authoring | Current-format identity round trip and very cheap r101 proxy | Determine whether the proposed representation can fit 2 ms |
| Runtime optimization | Bounded local-indexed versus direct-stream comparison and chunk-size sweep | Choose the cheapest valid way to draw the reduced geometry |
| Visual qualification | Current reference, proxy, and reconstructed candidate on the same moving route | Decide which quality/performance trade is acceptable |
| Coordinator | Combined measured build with memory and gameplay evidence | Decide whether to expand beyond r101 |

The first hardware handoff should contain three matched representations: current accepted world, sparse feasibility proxy, and the first recognizable reconstruction. Include hashes, resolved switches, camera/input sequence, world counters, frame timing, presentation cadence, and memory observations.

No current console result proves that the required visual quality fits 1–2 ms. The decisive milestone is a playable r101 candidate that demonstrates those properties together. If the minimum acceptable reconstruction remains above the budget, document the specific cost/quality conflict and reallocate the frame budget explicitly. Do not continue an open-ended sequence of setup trims expecting them to resolve that gap.
