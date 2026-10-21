# A11 direct archive borrows and quiescence boundaries

Read-only selected-source qualification at `836a72425d4f753a7b0ef0f3509716621942b461`
(preceding integration source `a18f2cf60faa25266271b2c33a6c7c8b0f3e3c1f`).
The snapshot uses Git objects, so it excludes root's current em10 working changes.
No runtime/shared source, knob, program, asset or production recipe changed.
Main owns the archive/reset contract and integration decisions. Payload's independent
registration/capacity/real-asset census remains separate.

## Result and limits

The archive borrower set extends beyond CABIN event/DMA readers and beyond GPU
packets. Effect records, texture identity metadata and model views retain source
addresses. Their registries/revision checks and cache-arena leases do not form a
common archive read lease. This supports the already-open A11 range contract; it
does not establish another observed gameplay fault or justify a generic reset fix.

One concrete source ordering gap deserves a target scheduling reproduction:
`native_ui.cpp:6380` tests `stream_aborted` **before** `stream_select`, whose
`stream_open` can wait for presenter/TA ownership. There is no generic abort
recheck between that selection and successful packet reservation. The caller
subsequently reads the source geometry. Ordinary room retirement explicitly
permits a source task to retire while main owns an unfinished TA list, clears
archive metadata, and marks the stream aborted. This is a candidate interleaving,
not proof that a real room task can reach destructive retirement during that
particular wait. Existing source-world owner checks may reject their covered
world inputs; they must not be generalized to all enemy/player/model inputs.
No injected callback is counted as ordinary scheduling evidence.

## Direct borrows, publication and retirement

All paths below refer to the pinned source; line numbers are source identities,
not addresses or timing measurements.

| Borrower | Publication and later source read | Retirement and remaining condition |
|---|---|---|
| Effect EST/SST/path/model/texture registries | `eff_sys.cpp:710..717,749,855,876,918..922` publishes texture headers, animation/TPL, sequence/path and model pointers. `EspTexSet:571` reads the retained header; `EspGetEstAddr:758` returns a retained sequence. | `EspDataRelease:529` decrements registrations; with `flag=1` and another registration it returns before any release. Registration count is not a controller lease. |
| Effect native sequence binding | `native_effect.cpp:156..163` stores archive/table pointers. `record_ref:178` first reads the head count, then finds the binding. | `unbind:166` reads table counters then clears its descriptor. It does not retire source controllers. |
| Effect record reference | `native_effect.cpp:192` returns an even/raw reference directly; an odd/compact reference searches a current binding and decodes into caller scratch. Source controllers can retain head/ref across updates. | An even/raw reference is not invalidated by native unbind. An odd reference without a binding reaches nonreturning `re4dc_missing`; no later publication is reachable from that refusal. Retiring the binding alone is insufficient evidence that raw/head users stopped. |
| External texture identity metadata | `texture_package.cpp:119..165` validates then retains `data_` and `native+32`. `record:171` and `lookup:180` reread those bytes; palette lookup also reads its caller palette. `native_ui.cpp:2599` searches room/core/option/player/weapon/enemy identity views. | UI unbind clears views and calls source/owner invalidation. `SourceIdentityTable::clear` clears metadata only. Cached uploaded package metadata and VRAM are separately owned and can survive source retirement; their continued residency is not an archive borrow. |
| Actor archive ownership metadata | `actor_lifetime.inc:131` adopts original archive spans and revision-linked asset/info records; `model_bridge.cpp:90` can return original position/normal arrays. Transaction/converted actor paths have additional ownership checks and workspace storage. | `archive_retire:126` revokes registry entries/revisions. This does not scan an in-flight generic `Re4dcModelPart`, and converted/private arrays must not be falsely classified as archive ranges. |
| Deferred model views | `native_ui.cpp:564..604,7008` retains a compact view whose geometry/stream/material pointers can still address source data; lighting is copied. `finish_source_draws:8475` restores a view, removes its queue node, then calls model submission. | `reset_deferred:711` clears queued views; owner reset calls `invalidate_pending:8614`, which aborts when a queue or drain is active. That also covers the last-node drain case: an empty queue alone does not bypass the `draining_parts` test. |
| Synchronous native model submission | `native_model.cpp:822..899` validates numeric ranges, reserves a texture/packet, then reads GX stream/positions/normals/UV/colors through walks or a draw plan. Texture misses and TA opening may yield before those reads. | Source-world guards cover configured world owners. Numeric RAM checks are not allocation/revision proof. The post-`stream_select` generic abort gap above is distinct from queued-view invalidation. |
| Draw-plan cache | `native_draw_plan_owner.cpp:17..40` retains owner spans and stream/source pointers beside copied topology. `acquire_plan` validates owner ranges before incrementing `leases`. | `reset_draw_plans:60` defers cache-arena reset while leased, but unbind/retire still removes source-owner descriptors. `leases` protects cached plan storage, not the source archive allocation. |
| GPU packets and uploaded textures | `native_ui.cpp:6500` submits copied native packets and pins the uploaded texture entry for that frame. `texture_package.cpp:63` copies native payload bytes into VRAM. | Presenter/TA/VRAM fences protect submitted packets and GPU uploads. They do not by themselves drain a CPU model walk, effect controller or identity-table lookup. |

The concrete source overwrite chain remains `EvtRead:2550..2656` →
`EspEmDataSwapPush` → `EspDataRelease(owner,1,0)` → `MemorySwap(mod->pArc,...)`.
The earlier sealed actual-source lifetime controls at `0463a8dc7` show that
registrations greater than one retain EST/model/texture pointers across the
overwrite, and a later actual lookup reads changed bytes. The controller controls
at `0b45c8252` show permanent/event bits that can remain active. Those controls
establish the conditional contract failure; they do not establish a normal route
with that exact owner count, still-live overlapping controller and swap. The
first-forward receipt checks carrier/unit/module/heap identity, not this broader
borrower census. No new callback or global-generation fixture was added here.

## Native services and counters: what is actually quiescent

| Service / counter | Exact boundary | What it does not establish |
|---|---|---|
| `OSThread::nativeIoDepth` | `platform/os.cpp:417..445`; begin/end use IRQ-protected owning-thread nesting. `OSCancelThread:453` waits for the target's native I/O/motion work; `scheduler.cpp:556` avoids ISR suspension of a native I/O owner. | It is not a global admission freeze, archive-range count, or lock against another KOS/source task. It must not be inferred from the word synchronous. |
| DVD source-step owner/depth | `platform/dvd.cpp` `dvd_step_begin/end` serialize the shared source DVD header, admit same-owner nesting, and use bounded waits for a foreign owner. `Re4dcDvdBorrowScope` carries that boundary. | Unrelated effect/model/UI consumers do not acquire it. |
| Nominal async DVD read | `platform/dvd.cpp:369` performs `fs_open/seek/read/close` synchronously within `Re4dcIoScope`, then invokes its completion callback before that scope ends. File services/retries can yield. | No separate DVD worker owns the returned source buffer afterward. The callback is part of the protected call; a fabricated later callback is not this implementation. |
| Native package reader | `room_storage.cpp:28..47,104..146` `ReaderGuard` try-lock and `bounce_busy` protect the shared bounce buffer; `fs_open` and chunked `fs_read` may yield. Each package-at-offset has its own file position. | The mutex does not claim the archive which requested the texture, source geometry, or native UI global state. Native UI `load` has no local `Re4dcIoScope` around its whole model caller. |
| CABIN carrier event counter | `native_event_file.cpp:511..515` brackets source event walking; exact current carrier/event identities and allocation predicates gate supported event-module transport/retirement. | It is not entered by generic native effect decode/texture/model reads. Unsupported modules/ranges remain outside this local contract. |
| CABIN DMA scope and per-carrier readers | `native_event_file.cpp:568..650` captures request/generation/type/range; admission increments a carrier reader; exact complete/cancel release decrements it. `src/game/dvd.cpp:1225..1400` owns admission/copy/completion/cancel. | A partial native request can retain backing/readers; `MemorySwap` returning failure is not rollback. Counters are not a census of raw archive readers. |
| ARQ adapter | `platform/audio_stub.cpp:246,262` generic flush is empty; post records fields, the AICA path performs its adapter transfer and invokes callback synchronously. | The SDK async name does not prove an independent generic ARAM DMA thread. Native CABIN transport has its separate explicit request lifecycle. |
| Movie scopes | `native_movie.cpp` movie readers/world token and cabin movie epochs gate their exact arena/payload users; UI handoff checks `draining_parts`, closes deferred work and fences submitted work. | Movie handoff is not acquired around every archive consumer. |
| Presenter/GPU counters | `native_ui.cpp` presenter request/resolved counters and `present_fence`; the async pipeline has corresponding KOS pending state. Worker resolves submitted PVR work/VRAM. | No retained source geometry is consumed by that worker; conversely its completion does not mean a main/source-task CPU borrow finished. |

`gameRoomMemInit:1507` calls motion/effect/UI retirement before heap replacement,
but earlier weapon/overlay mutations and whole-reset refusal propagation remain
main's open audit. Do not promote this local ordering to whole-reset acceptance.
Current `platform/mem.cpp:215` diagnostic logs and loops on `thd_sleep(1000)`:
fallthrough after native fatal refusal is only a returning-diagnostic compatibility
control, as qualified separately in `FORWARD_DIAGNOSTIC_QUALIFICATION.md`.

## Evidence

`audit_archive_borrow_paths.py` snapshots 25 complete Git source objects and
records blob IDs and SHA-256 hashes. Its 26 assertions check exact source order,
direct pointer publication, retirement/counter scope and fatal service semantics.
They are static source checks, not execution of those C++ bodies. The resulting
receipt is `archive-borrow-paths01-receipt.json`; complete immutable snapshots
are mirrored under the lane evidence directory `archive-borrow-paths01`.
Fresh output: 1,339,886 bytes, below the total 20 MiB cap. No compiler, target
build, link, stage, guest or asset conversion ran. Existing source fixtures and
their old receipts were preserved unchanged. Flycast, release and physical
Dreamcast acceptance are all open; no performance claim is made.

Next concrete qualification for main: reproduce the reserve/TA-wait retirement
ordering with the real source task entry, configured owner guards and exact
allocation range; capture the first resumed CPU source access. Until then keep
it a scheduling-window candidate. The already-saved A11 archive contract remains
the architecture authority; no Count-as-lease or speculative parallel generation
table is proposed by this unit.
