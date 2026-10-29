# Current-source architecture review: next engine phase

**2026-10-29 progress:** DONE: reviewed current world, actor, material-binding and simulation source after the first EF implementation slices; identified the remaining architectural constraints and bounded continuations below. NEXT: continue the existing engine owners with these source-defined changes, then compare their output and total cost. No runtime implementation, enabled-image acceptance or performance gain is claimed by this documentation commit.

**Reviewed integration:** origin/t15/int at **255964fdc7d22a61acff1ef59734a36ec91ebff0**.
**Related plan:** [existing engine backlog](ENGINE-FIX-BACKLOG-20261029.md) and [local handover](HANDOVER-SYSTEMIC-PERFORMANCE-20261029.md).
**Question answered:** do the next improvements require another budgeting exercise, or does current source identify architecture to fix first?

## 1. Decision and scope

**Continue architecture and native coverage work first. Keep the existing memory and frame targets; a new global budget or asset-reduction pass is not a prerequisite.**

Current source supplies concrete counterexamples: a valid native actor can lack presentation authority when a particular source-preparation ledger did not run; a refused palette registration can still consume primitive storage; a part with 321 stored meshlets cannot use a 320-pick fast path even if only one meshlet survives; actual texture dimensions can become known after dependent UV work; and existing optimized subsystems do not yet compose across the intended producer combinations.

These are actionable relationships among identity, preparation, capacity and completion. Lowering texture resolution or geometry counts would not repair those relationships. Existing hard limits remain acceptance constraints, and memory accounting belongs in each implementation slice. Choosing additional retained-cache capacity, visual approximation or a final scene workload still requires a later tradeoff.

This review inspected selected current implementation paths across world rendering, native actors and source preparation, generic native packets and materials, collision, effects, cloth and motion, together with current queue/owner status and relevant recipes. It extends the earlier broad source audit. It is not a claim to have executed every room, inspected every private asset, or read every source line again. Findings distinguish source-proven behavior from proposed designs and unknown runtime incidence.

The recommendations evolve current native packages, actor records, leases, texture entries, world plans and ordered simulation structures. They preserve recovered game behavior, material and callback order, current pose, retirement, RNG and required simulation.

## 2. Start from the work already integrated

The current [queue][QUEUE] records first bounded slices of EF01, EF02, EF03, EF05, EF06, EF07 and EF08. Do not repeat their original first-commit instructions as if nothing has landed.

| Item | Current integrated slice | Remaining obligation relevant here |
|---|---|---|
| EF01 | Bounded immutable NMR actor source spans | Other producer/mutation classes and presentation lifetime remain separate work |
| EF02 | Opt-in corrected real public/private producer path; seven actual FE arrays bound for a certified link | Production assets and live acceptance were not promoted by that work |
| EF03 | Strip/cloth native outcome propagation | Complete additional native families and preserve atomic publication across new producers |
| EF05 | SOB heap/allocation incarnation checked before retained-state use | Source-content authority, sibling retained state and enabled acceptance remain |
| EF06 | PS2 header upload-incarnation slice | Prepared material binding before dependent geometry is an additional boundary |
| EF07 | Owner-scoped plan invalidation with lease/probe/wrap handling | No implication that all other caches now have precise mutation authority |
| EF08 | Queued non-stream world completion | Stream and clip variants still do not compose with it |

The queue distinguishes build/OFF-identity results from live and console acceptance. In particular, the broad ALL ON profile keeps portal completion separately parked because stream/clip combinations are unsupported. This review does not promote it or reopen unrelated failed memory judgments.

## 3. Ranked continuation

The ranking reflects correctness, dependency and architectural reach, not predicted milliseconds. Existing EF owners keep their scope; the local coordinator assigns any additional actor-lifecycle or simulation slice through the current queue. These are not new Build-number assignments.

| Order | Bounded work | Existing foundation / backlog relationship |
|---|---|---|
| 1 | Transactional skin registration; establish general actor presentation authority for a selected class | Existing skin reservations, actor ledger/leases and Leon direct presentation; extends actor lifecycle beside EF01/03/04 |
| 2 | Resumable ordered world selection, preserving whole-part completion | EF09; uses EF03 outcomes and EF08 receipts |
| 3 | Extend portal completion through the current stream producer, then qualified clip variants | Finish EF08, retaining unsupported guards until each contract exists |
| 4 | Resolve actual native binding before UV-dependent emission | Existing texture entries/leases and packet owner; continuation beside EF04/06/11/12 |
| 5 | Publish precise world source/material mutation authority; reuse prepared relationships | EF09, following the lifetime/identity principles of EF01/05/07 |
| 6 | EFM slot-class identity, distinct collision-body dirtiness, resumable line traversal | Three bounded simulation continuations; separate from renderer EF12 |
| 7 | Route-specific scratch and prepared skin-table reuse | Lower-priority EF09/14 policy extensions; retain current workspace limits first |

Independent work can proceed concurrently under the current single-writer rule for shared files. Keep completing the remaining material/primitive coverage already assigned to EF04/11/12/13; these findings do not replace that backlog.

## 4. Actor presentation needs its own current-image authority

### What the source establishes

Regular actor transaction identity returns no candidate when the source actor or render ledger is inactive. When active, the ordinary route requires SourceHandled membership. ModelRender separately suppresses the front-native fallback for a registry-owned actor under NMR_NO_GC_FRONT. The registry recognizes that owner by model address and serial. These states can therefore yield an existing native owner without a native presentation candidate. [Identity and nomination][ACTOR_ID] [Fallback guard][ACTOR_GUARD] [Registry owner][ACTOR_OWNED]

This is an explicitly documented transition case, not a conjectured crash: native_model_registry.mk describes the door-demo image where no emTrans ran and the guard draws nothing rather than entering a removed source-asset path. The same file and source_actor_owner_hooks.inc already provide LEON_NO_GC_FRONT=2: Leon receives a small current-image presentation record and the ordinary native transaction when the general source ledger is inactive. [Existing policy and Leon extension][ACTOR_POLICY] [Leon presentation record][LEON_ID]

### Intended invariant and first slice

A valid native actor's presentation must be decided from its live owner, an explicitly valid pose/material state and this image's presentation choice. Whether simulation or source geometry preparation advanced is a separate fact.

Generalize the existing Leon presentation mechanism to one selected registry actor class. Reuse the same sticky source/native choice, owner generations, frame/room/primitive identities, role/material proofs, palette/workspace leases and original OT callbacks. Establish how a valid last pose survives an image without a preparation tick; never retain a pointer merely because its address is unchanged.

Required source state callbacks remain authoritative. In particular, commonScreenMatSub also advances material frames and UV state. Rendering an additional image must not advance those again, and avoiding source geometry allocation must not skip them. [State update semantics][ACTOR_STATE]

### Comparison after the change

Exercise inactive-ledger and paused/stopped images, first image after a transition, two passes, material animation, room retirement, owner address reuse and a genuinely unavailable pose. Verify complete presentation, current state, callback cadence and emitted order. Preserve an explicit refusal when authority cannot be established.

This is an actor lifecycle continuation beyond the first bounded geometry-span slice. Adding an outcome enum alone cannot supply presentation authority. Its purpose is coverage and correct ownership; no FPS benefit is assumed.

## 5. Make preparation transactional and demand-driven

### 5.1 Reserve skin admission before consuming palette storage

skinDeferPending and the eager/lazy deferral variants allocate palette bytes through re4dc_prim_tail before calling re4dc_actor_skin_register. Registration can refuse because the registry is full or an owned entry conflicts. GetPrimBuff advances the primitive cursor and the tail API provides no rollback. A refused pending deferral then enters CPU preparation. Thus refusal can retain palette storage for the rest of the primitive lifetime without publishing a usable deferred entry. [Deferral order][SKIN_DEFER] [Pending path][SKIN_PENDING] [Register refusals][SKIN_REGISTER] [Monotonic allocator][PRIM_TAIL] [CPU continuation][SKIN_FALLBACK]

ACTOR_SKIN_RESERVE already reserves empty keys for nominated native owners before source preparation. A successful applicable reservation avoids full-registry refusal for that key; it does not remove the later palette allocation. The refusal case applies to deferrals without such a successful reservation and to other admission failures. [Existing key reservation][SKIN_RESERVE]

The first slice is small: reuse or provisionally reserve registration under the existing owner, allocate only after admission, then publish. If allocation fails, release only a provisional reservation created by this attempt; preserve an earlier native-owner reservation and any existing lazy entry. Preserve replacement semantics and native-owner conflicts. A casual allocator rewind is unsafe if another allocation can intervene.

Test full registry, owner conflict, allocation failure, replacement and fallback. A refusal before publication must leave no new unused palette allocation. This fixes an ownership contract without increasing the memory budget.

### 5.2 Defer representation-specific palette storage until the consumer is known

The ordinary source-prepared transaction deliberately runs original source callbacks before choosing native ownership at the OT callback. Native actor acquisition later uses its own mapped palette arena. For that route, a source deferred-palette allocation can survive after the native representation is chosen. The source and native weight-group layouts can differ, so their byte arrays are not interchangeable. Early coarse tickets can avoid some source preparation. Skin-key reservations protect registry priority; they do not defer or eliminate source palette allocation. This finding does not claim every actor skins twice. [Source callback contract][ACTOR_SOURCE_PATH] [Native acquisition][ACTOR_ACQUIRE] [Registry layout contract][ACTOR_LAYOUT]

After transactional registration, retain the smallest bounded deferral recipe until the consumer is selected, where the lifetime can be proved. Separate state advancement from source/native geometry preparation. Reuse current early tickets, source ledgers, palette arena and skin leases. Source fallback must still materialize the correct current pose, including any state that a callback could change.

Compare primitive high-water use, materialization counts and full cost afterward. Exact memory retained and incidence are not established by the source review.

## 6. World selection should be bounded by the next page of work

### What the source establishes

ps2_pass has 48 queued contexts and 320 picks. Both selection routes require the entire part's stored meshlet count to be at most 320 before calling chunk_select. The selector takes an output pointer but no capacity or continuation cursor; its general contract requires room for the entire part. [Queue and admission][WORLD_QUEUE] [Selector interface][WORLD_SELECT] [Second admission path][WORLD_ADMIT2]

A valid part with 321 meshlets and one visible meshlet fails this admission. It falls through to d.run. With SCENERY_STREAM, this also loses the existing indexed transform without a gather, which lives in emit_pick; the ordinary meshlet route gathers corners. This is a source-defined execution-size cliff, not proof that current retail data frequently crosses it. [Streamed emission][WORLD_STREAM] [Immediate fallback][WORLD_ADMIT2] [Ordinary meshlet gather][WORLD_GATHER]

### Intended invariant and first slice

Keep the same bounded pick storage. Select surviving meshlets in ordered pages, emit a complete page, then continue from an explicit cluster/LOD/meshlet cursor. Admission should depend on the next bounded unit of selected work.

Retain placement, material, UV and view snapshots across pages and preserve source encounter order. When the part is an occlusion witness, aggregate completion over the entire part. No page alone grants whole-part authority. A failure after publication aborts under EF03 semantics; it must not replay previously published geometry through a fallback.

This is an EF09 extension with EF08/EF03 integration. It needs neither a larger stack queue nor content simplification. It does not reduce resident package memory: SCENERY_STREAM is an indexed transform/emission path, not demand loading of room geometry.

### Comparison after the change

Use 319, 320 and 321+ stored meshlets with zero/one/all surviving; LOD boundaries; surviving clusters spanning pages; a final empty page; bind refusal and abort midway; and a multi-page witness. Compare ordered packets and complete-part outcomes before timing.

## 7. Finish feature composition and give prepared world facts precise validity

### 7.1 Portal completion and the primary world producer

The new WORLD_PORTAL_COMPLETION guard still rejects SCENERY_STREAM, SCENERY_CLIP_GATHER and SCENERY_CLIP_INDEXED26. Runtime admission also declines cone, piece-state, dedup and CPU-backface variants. The integrated first slice proves queued whole-source output; the immediate path grants no witness. [Compile restriction][PORTAL_GUARD] [Queued completion][PORTAL_QUEUE] [Runtime exclusions and authority][PORTAL_RUNTIME]

This is unfinished EF08. Extend current Ticket/Completion through one additional producer at a time, beginning with the intended stream path. Completion must account for actual source coverage, cull/clip outcomes, material/view/source state, publication and queue ownership. Retain ordinary draw-all behavior when a conservative witness cannot be established.

Do not delete guards to make the configuration compile. Do not require a private portal asset to implement the producer contract: current synthetic fixtures can cover empty/clipped/partial output, pre-publication refusal, later abort and targets encountered before witness completion. Authored cells and console look/cost comparisons follow.

The [Build 31 handback][B31_CURRENT] records the current ALL ON incompatibility. The older Test24 release recipe is not the later ALL ON configuration; read resolved knobs for the actual candidate.

### 7.2 Validate invariant relationships at their actual mutation boundary

With completion enabled, same_scene scans all witness materials through completion_sources_current. activate runs before each placement's portal test; while a candidate is valid it checks same_scene, and after the required receipts are complete it also scans sources, which walks witness placement/source relationships. Capture, finish and membership checks add more repeated work. Placement view setup also precedes the portal rejection that could avoid it. [Authority scans][PORTAL_RUNTIME] [Placement preparation order][WORLD_PLACE]

Complete EF09 by preparing direct witness membership and immutable placement bounds in the existing world plan, and publishing precise source/material/content incarnations. Once every relevant mutation is covered, validate invariant relationships once per incarnation and keep inexpensive current-generation checks at use. Current camera/projection and completion authority remain live.

This is not permission to memoize by package pointer or remove source checks prematurely. Hidden/moved source objects, live material changes, same-address reloads, movie borrowing, retirement and between-pass changes all need a defined publisher. Unknown authority keeps current conservative validation. Each replacement for current validation must identify every protected field and every mutator, including in-place content/material changes, and define generation wrap or exhaustion. Image/scene receipt resets and current opaque-binding readiness remain checked at use; a package or content generation cannot replace them.

The first slice should carry a real producer mutation into one existing prepared consumer. Then move conservative rejection ahead of avoidable view-dependent setup where its current proof permits. Compare decisions, output, validation work and total setup cost.

## 8. Prepare the actual material binding before dependent geometry

### What the source establishes

Generic native packet reservation estimates UV scale from source dimensions and default padded texture dimensions. Actual texture resolution/loading and final dimensions occur in packet_begin. Builder::bind can therefore discover a changed UV scale after emission preparation, flag restart_uv and rerun the emission walk before any publication. Binding may also yield, so the current code marks matrix state dirty. [Tentative reservation][MODEL_RESERVE] [Late binding][MODEL_BIND] [Explicit UV restart][MODEL_REPLAY] [Texture resolution][UI_BIND] [Final scale][UI_SCALE]

The current restart is a correctness safeguard. Some position transforms survive it through the existing 64-entry position cache; the finding is not that every transform is necessarily repeated. The architectural opportunity is to establish a dependency before work that depends on it.

### Intended invariant and first slice

After safe input/material validation and cheap visibility rejection, resolve the actual native material into a bounded prepared binding: upload incarnation, effective texture dimensions/UV scale, pass/blend/wrap state and residency/lease authority. Then perform UV-dependent clipping/emission. Separate potentially yielding preparation from publication through the existing packet owner.

Reuse texture Entry and current actor texture leases; no new resource manager or universal material graph is needed. Preparation must not load every culled object. If I/O can retire source/owner data, revalidate before use; if the bound upload changes, reject or reprepare before publication. Preserve RTT and baked-texture scale overrides.

This extends the boundary beside EF06's already-landed header incarnation and the EF04/11/12 coverage routes. Test alternate actual dimensions, eviction/reload at the same address, wrap refusal, yield/retirement, RTT overrides and failed preparation. Compare effective UVs, clipping, headers and order, then replay counts and full cost.

### Material semantics remain existing coverage work

Current reserve accepts a restricted material vocabulary; masked input requires same-coordinate, equal-resolution, zero-reference composition into the supported native texture representation. Other TEV/alpha-test policies are explicitly marked as gaps in source. [Material capability checks][MODEL_RESERVE]

Keep completing named required material operations through existing converter recipes and native part descriptions in EF04/11/12. Use exact native execution, equivalent offline preparation or an explicit approved visual policy as appropriate. A valid unsupported operation is a coverage task; malformed input remains a refusal. This review does not establish which uninspected private assets require each omitted operation or promise literal execution of every source GPU feature.

## 9. Three concrete simulation continuations

These are structural optimizations, not newly demonstrated gameplay correctness defects. Their source rationale is enough to implement a bounded candidate. Existing source fallback currently preserves correctness; frequency and speed benefit remain comparison questions.

### 9.1 EFM class identity should survive an ordinary alive-list deletion

EFM already indexes mapped ObjMgr slots of classes 4, 5 and 9. Its validity token is the alive-list generation. EfmDeleteSub destroys a matching object; destroy/deleteList increments that generation. EfmDelete consequently switches to a full scan of all remaining slots, and the next call rebuilds the class index. The index describes slot mapping/type, while its token describes a broader alive-list relationship. [EFM index and fallback][EFM] [Manager destruction][MANAGER]

Extend the existing manager/slot lifecycle with mapping/class incarnation, or update the existing index at the exact lifecycle hooks. Keep alive generation for consumers that need alive order. Cover reconstruction, failed construction that changes bytes, address reuse, backing replacement, push/pop/free and nested callbacks that can alter future slots. Removing the generation check alone would be incorrect.

Preserve source slot order, filter globals and callback semantics. Test multiple deletions, nested deletion and creation, frozen/pushed pools and the current >64-entry refusal. Compare visited effects/final state, then rebuilds, scanned slots and total cost. This is a simulation indexing slice; it does not replace EF12's primitive/material coverage.

### 9.2 Collision dirtiness should describe distinct changed bodies

Eligibility wrappers append every flag/radius eligibility change to one global 64-write ring. Each candidate cache consumes a sequence range. More than 64 intervening writes forces source recollection, even when the changes concern only a few repeated bodies. The apply routine reads each body's current state, so historical repeated writes are not themselves required replay events. Current comments already describe repeated dead-Ganado radius toggles. [Mutation wrappers][ATARI_DIRTY] [Candidate maintenance][ATARI_CACHE]

Use existing manager/list identities for distinct dirty bodies or per-body eligibility revisions. Preserve each consumer's independent progress, slot incarnation and source-ordered candidate insertion. A global clear-on-read bit is insufficient because the enemy and object consumers can query at different times. Coalesce only between the same consumer's query boundaries; any query that should see an intermediate state still must.

Retain conservative recollection for unknown storage or bounded-storage refusal. Test repeated changes to one body, >64 distinct bodies, both consumers, return-to-original-state toggles, absent/dead bodies, reuse and reorder. Reuse GAME_ATCHK_CACHE=2's ordered-source comparison. Raising the ring size alone would move the threshold without changing the dependency.

### 9.3 Line traversal should resume after a bounded group of leaves

The native line walker first gathers all overlapping leaves into a 64-entry array. More than 64 leaves or more than 16 nested chains refuses that walk; the caller returns to recursive source traversal. The sphere walker already has continuation state and processes ordered leaves incrementally. [Line contract and fallback][LINE_WALK] [Existing sphere continuation][SPHERE_WALK]

Adapt the current continuation pattern to line queries, retaining overlap arithmetic, polygon kernels, source order, transforms, polyBit handling and result semantics. Start by eliminating the 64-leaf gather/restart limit. Keep deep-chain reference fallback until a separate depth representation is justified; the first slice needs no replacement SAT format. If depth fallback is reached after a page has been consumed, continue from the unprocessed subtree with the existing query state; do not replay the processed prefix. Alternatively, establish the depth refusal before processing any polygons.

Test 64/65+ leaves, no hit, repeated polygons, multiple and moving pieces, depth boundaries and final hit outputs. Extend existing GAME_LINE_WALK=2 / GAME_LINE_WALK_PF=2 comparisons to page transitions. The line source explicitly states that its traversal reads no state written by leaf evaluation, supporting ordered incremental consumption.

The pinned build-r21 recipe enables these simulation switches, but make defaults are zero. Bind actual candidate comparisons to the current resolved knobs and overrides. [Recipe][RECIPE]

## 10. Lower-priority policy questions to keep bounded

### Route-specific scratch

MeshDraw::borrow reserves the maximum projected cache/outcode tail and requires 328 packet slots, even before the cache-free sequential direct-strip route is attempted. The same routine also prepares UV/material transform constants. Separate constant preparation from route-specific scratch admission, then request only the proven route's bounded workspace through the current owner. [Borrow and direct-route setup][WORLD_SCRATCH] [Emission call order][WORLD_STREAM]

The direct-strip route is separately gated and excluded from the stream profile; do not label it the current ALL ON bottleneck. With MESH_PRIME_LAZY enabled, priming is limited to needed entries and can be retained across parts; reservation size is not equivalent to bytes touched. [Profile exclusion][WORLD_PROFILE] Test small slabs, tiny/max meshlets, clipping fallback, tail overlap and retained-prime invalidation. Compare before changing workspace policy.

### Prepared skin-table reuse

The actor frame cache keeps only one skinned table live: preparing B explicitly invalidates A's table and resets shared workspace. A legal A -> B -> A order therefore cannot retain A's prepared table across B. Both ordinary and grouped submission have this rule. [Single-table lifetime][ACTOR_TABLE]

Separate owner/pose/view validity from transient scratch if a bounded reuse policy can improve the existing workspace. Do not reorder translucent or source passes. Additional retained capacity is a real tradeoff, so this is lower priority than presentation and transactional preparation. The source supports a reuse limit, not a claim that a larger cache is automatically better.

## 11. Existing work to preserve

The review confirms important machinery is already present:

- Indexed world transforms, scheduled native kernels, clipping variants and SQ emission exist. Complete their contracts and composition.
- Actor FE decoding and native continuation exist; an AVK specialization miss does not by itself imply a dropped actor.
- ESP and ESPGEN already use mutation-aware live maps; EFM's different identity is the specific new concern.
- Cloth already computes each spring once while preserving force-add order. EF11 concerns its native rendering representation.
- Common animation layouts already have specialized interpolation kernels. Generic fallback is not automatically a defect.
- The hardcoded source-world UV IDs examined here belong to the bounded r200 transition adapter; they are not evidence of a whole-game UV bug.

[World source][WORLD_STREAM] [Actor continuation][ACTOR_KERNEL] [Effect live maps][ESP_LIVE] [Generator live map][ESPGEN_LIVE] [Cloth spring reuse][CLOTH] [Motion kernels][MOTION]

## 12. Delivery and acceptance

Continue from newest integration through the current local coordinator, one branch per assigned build. Preserve default-off behavior and absent/zero identity. Every implementation commit builds and updates its assigned build handback with a dated DONE / NEXT / BLOCKED line. Shared native_ui/native_model/trans/manager headers need explicit writer ownership.

The next implementation decision is the smallest producer-to-consumer correction above, not a fresh whole-game census. For each slice, establish the invariant, implement it, exercise its failure/lifetime/order boundaries, then compare equivalent output and full cost. Coverage repairs can add legitimate rendering; correctness repairs remain necessary even when they cost time. Optimizations may be revised or parked if their total cost does not improve.

Private data is needed for actual package regeneration and real-content look coverage; a console is needed for hardware cost and acceptance. When those are reached, put exact local commands and the expected comparison in the current assigned handback and continue independent code work. Existing private-input/QA commands remain in the linked handover and owner records. No new command is invented here for an implementation that does not yet exist.

After these contracts and native coverage are working together, remaining visible geometry, alpha coverage, resident data, cache capacity and quality policy can be budgeted against the actual supported workload. Budgeting then answers a concrete quantity/tradeoff question. It does not substitute for the source-defined fixes in this review.

## Source links

All code links below are pinned to the reviewed integration. Runtime configuration must still be bound to the candidate being compared.

[QUEUE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/docs/cloud/CLOUD_AGENT_QUEUE.md#L72-L81
[ACTOR_ID]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/include/source_actor_owner_hooks.inc#L75-L172
[ACTOR_GUARD]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L2978-L2987
[ACTOR_OWNED]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/coarse_actor_owner_registry.inc#L1144-L1151
[ACTOR_POLICY]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/native_model_registry.mk#L572-L602
[LEON_ID]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/include/source_actor_owner_hooks.inc#L53-L73
[ACTOR_STATE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L1952-L1989
[SKIN_DEFER]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L5926-L5955
[SKIN_PENDING]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L6006-L6057
[SKIN_REGISTER]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_actor_fast.cpp#L5862-L5904
[PRIM_TAIL]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L5569-L5624
[SKIN_FALLBACK]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L1993-L2030
[ACTOR_SOURCE_PATH]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/trans.cpp#L837-L847
[ACTOR_ACQUIRE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/coarse_actor_transaction.inc#L324-L460
[ACTOR_LAYOUT]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/native_model_registry.mk#L62-L65
[WORLD_QUEUE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L8140-L8155
[WORLD_SELECT]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/include/scenery_chunk_select.inc#L48-L143
[WORLD_ADMIT2]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L8601-L8775
[WORLD_STREAM]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L4088-L4134
[PORTAL_GUARD]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L114-L121
[PORTAL_QUEUE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L8251-L8286
[PORTAL_RUNTIME]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/include/world_portal29_runtime.inc#L24-L184
[WORLD_PLACE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L8476-L8536
[B31_CURRENT]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/docs/cloud/handbacks/build-31.md#L445-L471
[MODEL_RESERVE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_ui.cpp#L7385-L7433
[MODEL_BIND]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_model.cpp#L330-L349
[MODEL_REPLAY]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_model.cpp#L1039-L1106
[UI_BIND]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_ui.cpp#L7529-L7605
[UI_SCALE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_ui.cpp#L7730-L7758
[EFM]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/esp_efm.cpp#L84-L221
[MANAGER]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/include/cManager.h#L157-L179
[ATARI_DIRTY]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/include/atariInfo.h#L9-L60
[ATARI_CACHE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/at_mod.cpp#L329-L519
[LINE_WALK]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/atari.cpp#L1370-L1744
[SPHERE_WALK]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/atari.cpp#L835-L1056
[RECIPE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/tools/d367/build-r21.sh#L115-L155
[WORLD_SCRATCH]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L3246-L3335
[ACTOR_TABLE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_actor_fast.cpp#L1954-L1968
[ACTOR_KERNEL]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_actor_fast.cpp
[ESP_LIVE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/esp.cpp#L624-L665
[ESPGEN_LIVE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/espgen.cpp#L549-L583
[CLOTH]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/cloth.cpp#L346-L357
[MOTION]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/src/game/motion.cpp#L1649-L1685
[SKIN_RESERVE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/include/native_actor_skin_reserve.inc#L1-L38
[WORLD_GATHER]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/platform/native_static.cpp#L3360-L3390
[WORLD_PROFILE]: https://github.com/lamb2k/re4dc/blob/255964fdc7d22a61acff1ef59734a36ec91ebff0/port/dreamcast/game/scenery19.mk#L109-L125
