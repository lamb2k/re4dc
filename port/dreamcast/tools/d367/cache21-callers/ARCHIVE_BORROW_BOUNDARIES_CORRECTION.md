# Corrected model borrow / wait boundaries and source task dispatch

This supersedes the reserve/begin labels in `ca2ea1924`. The original source
snapshot, JSON and script are preserved. The error was in my static slice:
`packet_reserve` was bounded by `packet_commit`, which included separate
preparation/header helpers and the full `packet_begin`. The old successful
assertions therefore did not substantiate their function labels.

`audit_archive_borrow_boundaries.py` balances braces after masking comments and
literals. It checks exact bodies and records their line spans. Ten relevant
complete source objects are byte-identical between
`836a72425d4f753a7b0ef0f3509716621942b461` and current selected
`c57ff60f0f462fdd2c419883b0258963504d756a`: native_ui, native_model,
native_draw_plan_owner, scheduler, main, game, read, dvd, texture_package and
room_storage. The new receipt contains blob IDs, SHA-256 and 23 passing static
conditions. This is source inspection, not C++ execution or target validation.

## First through last borrowed reads

1. `native_model.cpp` submission reads/materializes source info and validates
   numeric RAM ranges. After constructing the local Builder it calls
   `re4dc_model_packet_reserve` at line849. Reserve (`native_ui.cpp:6152`) checks
   state, may `memalign`/log through `ensure_model_storage:6083`, and returns
   scratch capacity/default UV scale. It contains no texture resolve/load and no
   `stream_select`. Allocator/service preemption is possible, but no explicit
   DVD/TA wait is invoked by reserve itself.
2. Draw-plan acquisition may allocate/cache copied topology; its lease protects
   that cache arena. With no plan, `b.walk(false)` reads original GX opcodes,
   corner indices and verifies UV/color ranges before emitting. With a plan,
   later `walk_plan` still computes original source corners. This source access
   is **before** first texture/TA binding.
3. `emit()` walks source stream/positions/normals/UV/colors and builds private
   native vertices. When capacity requires a flush, `append_triangle:469/476`
   or `room_strip:500` calls `Builder::flush:281`. Flush first calls
   `Builder::bind:268`; if not already bound, bind calls `packet_begin`.
   Consequently first bind may be **inside** a part, after earlier source reads
   and before later source reads. A part which fits privately instead binds only
   after its emitted walk completes.
4. `packet_begin` first reserves scratch/state again (unless its reviewed coarse
   reservation handoff applies), then calls texture resolve/load. A hit can be
   immediate; a miss can key/hash the source image/palette, read a package via
   `fs_open/seek/read`, upload chunks, evict an entry and fence prior VRAM use.
   `Package::close`/upload replacement can call `re4dc_pvr_vram_fence`→
   `present_fence`. Storage's try-lock/bounce ownership covers its own buffer,
   not the originating model/archive. No claim is made that every texture load
   waits or that the texture pixels necessarily reside in the model archive.
5. After texture resolution, packet_begin checks `stream_aborted`, computes its
   pass and calls `stream_select`. An unopened stream enters `stream_open:1906`:
   configured `present_fence`, `pvr_scene_begin`, list admission and optional
   steady/RTT paths may wait. An existing different pass finishes/begins a list.
   SQ lock acquisition and native PVR submission also have synchronization
   boundaries. Optional source-world guards are checked after selection; there
   is no generic archive epoch assertion or generic abort recheck there. Begin
   builds the header and returns success. A fatal native service diagnosis does
   not return; fallthrough after such refusal remains compatibility-only.
6. `bind` sets `bound=true`. If true UV scale differs, it asks the caller to
   restart before a new chunk is published. At top level the caller may re-enter
   `emit()`, rereading source bytes. If called by first midchunk flush, accepted
   bind leads to commit and the source walk continues afterward.
7. Later flushes call bind again but return immediately when `bound` is true;
   they do **not** repeat texture load/packet_begin. They do call commit→
   `stream_send:2073`→SQ lock/native packet submission; stream_send can reopen
   if `stream_scene` is false. Source reads can continue after those boundaries.
   Submitted packets contain copied native vertices, not source positions or
   GX corner pointers. A plan lease or submitted texture frame pin does not turn
   the later source cursor into an archive allocation lease.
8. Final `packet_commit` follows all accepted geometry reads, except the explicit
   UV restart above; source info/texture/model global state can still be accessed
   in result/profiling hooks. This audit traces generic native_model's explicit
   service boundaries. It does not prove all optional actor/static conversion or
   profiling callees nonyielding and does not equate a function's synchronous
   signature with a scheduling exclusion.

## Retirement state and actual dispatch

`re4dc_ui_retire_room:4820` first retires actor/draw-plan/deferred metadata. When
`stream_scene` is true it sets `stream_aborted=true;stream_retire=true` and avoids
waiting against main's unfinished list. When false it fences/quiesces and then
clears sources/identity views/model entry state **without** setting stream_aborted.
Thus even a new abort check after a wait would not prove same-owner/range/epoch
continuity; this unit proposes no such repair.

The real source scheduler narrows which interleavings can occur:

- `main.cpp:286` runs `TaskScheduler`, then source transforms/draw preparation
  (`IdSys.trans`, `Trans`, later DrawOTag); it schedules the independent ISR slot
  afterward at line352. Native source tasks have KOS threads, but ordinary tasks
  are not freely dispatched whenever main blocks in a service.
- `TaskSchedulerMain` waits `nativeTaskYielded[slot]` for **every non-ISR task**.
  `TaskSleep` signals yielded and blocks on its explicit resume semaphore;
  normal return/exit also signals completion. A child file-service wait does not
  automatically signal source yielded. Main remains blocked instead of starting
  the next ordinary task.
- `GameTask` (`game.cpp:259`) dispatches gameRoomInit/gameEnding through its
  state table, then calls TaskSleep(1). The two actual gameRoomMemInit call sites
  are gameRoomInit:502 and gameEnding:1193. This is an ordinary game task route,
  not an ISR entry. Model/UI draws inside an ordinary task likewise run while
  main waits for that task's yield; another ordinary task is not independently
  resumed by a TA wait.
- The independent `iTaskExec` sites are source DVD reading and the old room
  decode site. `ReadAreaData`'s `iTaskExec(decodeData)` is in the **PPC branch**;
  native rooms use already-decoded DAR payloads. Counting that decode as a
  current native background retirement path would be wrong.
- Native DVD ISR `DvdReadProc`→`Dvd.ReadProc` runs queued reads, completion and
  source request lifecycle, then exits its ISR task. It can allocate/write its
  admitted destinations, and native DVD locks/counters have their documented
  exact scope. No direct gameRoomMemInit call was found on that audited entry
  chain. This is not a full proof that every destination or request callback
  cannot overlap a source archive; exact request/range reachability remains a
  separate contract question.

Therefore the source contains borrowing across legitimate wait points, but this
unit has **not established a normal room-retirement dispatch during those waits**.
The earlier concurrency comment is not enough to prove that precise route.
Arbitrary callback injection or calling retirement from a service mock cannot
close that gap. No gameplay use-after-free, repair sufficiency, whole epoch
ownership, reset acceptance or performance result is claimed.

Evidence mirror `archive-borrow-boundaries01`: selected source snapshots and
`receipt.json` total858,145B before copying this correction/tool. Together with
the prior unit and their mirrors, fresh outputs remain below20MiB. No runtime or
shared edits, compiler/build/link/stage/guest. All earlier fixtures/receipts and
default-off guards remain unchanged. Main owns architecture/integration and
Claude retains production merge/release ownership.
