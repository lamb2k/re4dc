# Entry2 diagnostic design after integration rebase

Current integration base: **64a28a7bdc44312924b14414501b7d4ff1d2d032**. The source-only findings commit was rebased to **bbd7ad41032fb2dbc1a058b6578fc8af84334b6f** from **c71a8a973a321df183936898c631dc865b7be78f**, which remains at local `refs/codex-backups/damcause23-pre-rebase-20261022`. The before-rebase receipt is retained in the external damcause23 lane. Only the owned `codex/damcause23` remote was rewritten, with a lease for the exact former remote SHA. No runtime source changed.

Full CODEX-UPDATE, Addendum and Correction were reread. This lane remains issue52-only. It does not resume old QA adapters, mipmap recovery, texture pruning, castle guests or El Gigante research. Existing EM_READ_RETRY and NULL guards remain untouched. No build/image/guest/native-process query is allocated.

## Reuse the existing diagnostic, with explicit attribution

At current source, `platform/include/issue52_actor_diag.h` declares only integer-passing note/base functions. `platform/crash_screen.cpp:49-82` copies phase/frame/room/base/actor under an interrupt guard; its rendering path reads only copied integers. `platform/modules.cpp:527-538` obtains the base from the published st1_2 registry, without reading an actor or overlay header. Preserve these properties. Do not edit the protected overlay-guard/arena/texture diagnostics to obtain another base.

The current `ISSUE52_NOTE(3,em)` after entry2 creation already captures the returned actor. Phase4 after `setNoSuspend` distinguishes arrival beyond the photographed boundary. This is useful but does not classify a NULL refusal, establish slot ownership or preserve an intervening read result.

`src/game/sce_sys.cpp:228-285` changes `pCTask` around scenario scheduling and restores it across sleeps. `include/scheduler.h:24-45` exposes the source TASK pointer; its address and task number are not generation counters. Because `readEmData` can sleep, a single unqualified global pending flag is insufficient. A read result from another task must not be attached to entry2 merely because room10c or ID0x12 matches.

## Minimum first implementation, subject to exact-file allocation

Start with refusal classification and actor-address evidence. Defer any actor-vptr read until a trustworthy pool-lifetime predicate exists. There is no need to modify the gameplay guard, retry count, flags, return value or success path.

Proposed record, copied integers only, at most128 bytes:

```
attempt_serial, owner_task_address, begin_frame, end_frame;
room_at_begin, module_base_at_begin, module_base_at_end;
state;                 // empty, pending, completed, abandoned/invalid
entry_number, enemy_id, admission_reason, returned_actor;
read_seen, read_path;   // none, cached, miss (unknown stays unknown)
request_number, poll_result, read_reason;
```

`attempt_serial` is a collector serial, not a pool/module epoch. Task address and room number likewise must never be presented as owner-generation proof. The first implementation can establish refusal/read attribution without claiming those stronger lifetimes.

Begin a record only for `G_ROOM_ID==0x10c && no==2` in the actual `EmSetFromList2` call, immediately before its refusal checks. Store the source TASK identity and a fresh nonzero token in a local scope object. A matching nested hook must verify the token, source TASK identity and expected enemy ID before recording anything. A mismatch increments or sets a diagnostic-discard field; it must not change gameplay. Every normal return completes the record with its exact return address and directly observed reason. Use a single pending record for this single entry; if a new attempt supersedes it, explicitly mark the previous attempt abandoned instead of joining their observations.

Reasons directly available inside `EmSetFromList2` are ID/stage/room/already-set/zero-ID/dead/list-filter/alive-cap refusal, `EmCreate` returnedNULL, and successful return. Emit only the boundary actually observed. A NULL from `EmCreate` alone is **creation failed**, not automatically full pool or failed I/O. The existing alive-cap exemption remains unchanged.

If source review confirms the nested scope survives scheduler resume as expected, `cEmMgr::construct` can report `subArc==NULL` and initializer completion; `EmReadSearch` can report cached versus miss; `readEmData` can report absent file, actual request number and actual negative poll. Record signed values without translating them into a guessed cause. In particular real queue admission returns-2; synthetic-3 remains a separate negative-result control. The record is authoritative only for a matching completed attempt. A canceled task with no completion leaves an incomplete record; it does not prove that its last observed read caused anything.

A generic cManager hook is optional and should be postponed unless the actual creation-failed boundary needs finer classification. If allocated, report full scan versus failed preparation at the exact return sites; never derive full-pool failure from a later scan of changed slots. Avoid scanning actor contents or acquiring texture/allocator ownership.

## Caller context and cancellation contract to prove before runtime editing

The minimum implementation cannot silently introduce a C++ scope destructor requirement into a source task that is canceled without stack unwinding. Completed attempts are recorded by explicit return hooks; pending attempts remain incomplete on cancellation. A destructor may be a convenience for normal scope exit, but cannot establish cancellation cleanup. At the next entry2 begin, a serial change invalidates abandoned history. A root-approved room reset hook could invalidate the record, but it must not be guessed from same room number or base address.

Nested source hooks should consume a diagnostic token owned by the active entry2 scope, not discover ownership from a mutable global boolean. A precise implementation option is a bounded collector slot keyed by source TASK plus serial, with checked begin/attach/complete operations. Before using `pCTask` as a live caller identity, review native `TaskSchedulerMain`/sleep/resume ordering at this pinned base; source declaration alone is insufficient. If attribution cannot be proved, stop after direct refusal reasons and returned actor, leaving deeper read attribution unknown. This keeps the first unit useful and honest rather than adding an unproved causal chain.

## Crash display and later lifetime work

Keep the full original register and stack snapshot. Current `fault_detail` formats all sixteen registers in groups of four (`crash_screen.cpp:210-219`); any compact issue52 summary should include the already-copied actor address and explicitly saved r8 while respecting the fixed row budget and existing overlay identity row. Do not dereference a fault-time actor, vptr, manager slot, archive header or address0.

Actor first-word capture remains a second unit: require an allocated same-generation slot and a non-yielding live-owner point before copying its word, then record initial-move before/after state. No existing source TASK serial or module base proves a pool epoch. Do not add a speculative validity check that masks the original failure. A reporter-matched low-address word/console identity remains absent and is not replaced with a local emulator ROM.

## Proposed shared files, not yet edited or claimed

- `src/game/em_set.cpp`: narrow entry2 begin, explicit refusal/success completion, no guard changes.
- `port/dreamcast/game/platform/include/issue52_actor_diag.h`: integer-only API and diagnostic enums.
- `port/dreamcast/game/platform/crash_screen.cpp`: collector and compact rendering only, preserving fault context.
- After attribution proof only: `src/game/em.cpp`, `src/game/read.cpp`; optionally `include/cManager.h` for exact full/preparation reasons.

No modules.cpp modification is needed for the existing base query. No Makefile/recipe change is proposed. Diagnostics remain behind the existing experimental ISSUE52_ACTOR_DIAG condition. Root must confirm exact shared-file ownership before implementation. This is a concrete staged implementation contract, not a hardware cause or a compiled/runtime result.
