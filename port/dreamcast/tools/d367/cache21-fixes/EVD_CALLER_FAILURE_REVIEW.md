# Event creation failure and static caller stack review

Read-only runtime review over transaction checkpoint
`8ff45d690397203e428c7215aadd0f2017ace7ec`. That clean checkpoint remains in
`/root/probe/codex-cache21-event-admission`. This branch adds tests, source pins
and review only; no runtime ownership change is implemented or enabled.

## Confirmed failed-create path

The selected actual source executes this sequence:

1. `EvtReadExec` obtains an event file and calls `SetEvt(data)`.
2. `SetEvt(data)` completes `SetEvd((char*)hdr, hdr, 0, 2)`, then calls
   `SetEvt(name)`.
3. With both event slots occupied, actual `cManager<Event>::create(int)` returns
   zero. Both SetEvt overloads return failure without unregistering the new EVD.
4. `EvtReadExec` ignores the failed creation. Ordinary flags wait for the prior
   running key, call `EvtFree`, and eventually return **one**. Kept flags 2/0x40
   return one earlier, preserving the read and event status despite no new event.
5. In the selected resident/em0/immediate-command case, actual `EvtFree` drops
   ReadTbl and actual data-unit `setCommand -> checkCommand -> setClear ->
   checkMallocRelease` sends the input allocation to `Mem_free_h`. EvdTbl and both
   BinTbl entries still advertise that allocation. Actual `GetEvd` returns it.

This is a forced failure-path characterization, not evidence that ordinary play
reaches full event slots or that it causes the measured reload traffic.

`test_event_caller_failure.py` passes 12 cases each with EVD_ADMISSION_TXN 0/1.
Cases include eight flag values, waiting through an existing running-event key's
completion, a pre-existing complete parent, direct failed-create/free-slot retry,
and tool GetEvd read/admission failure. Exact H064 declarations/constructor and
selector are reused, with actual SetEvt overloads, actual create/full decision,
actual IsAliveEvt, actual EvtReadExec/EvtFree and actual data-unit release bodies.
No success/failure or release predicate is replaced with a model.

Host boundaries are explicit: class layout, manager allocation/constructor/list,
Event::init positive control, input transport, scenario/camera services and final
heap free. The free boundary records the actual pointer/heap then protects its
page; GetEvd still returns that protected address. The prior event's completion
at SceSleep is a boundary, not a simulated complete ExeEndEvt/DelEvt sequence.
The release case uses condition2, em0, no cabin owner, and
`DC.m_nblock_read_stop == 0`.

Two native32/host64 ABI adaptations are pinned explicitly: GetRead uses a
pointer-width local for its actual table/slot lookup, and EvtReadExec's sole
`(void*)addr` signed-int conversion becomes `(void*)(u32)addr` to retain native32
address bits rather than host64 sign extension. Actual policy bodies otherwise
remain unchanged. Original and executed-body hashes are separate. UBSan only is
used because the original negative-address guard requires the ASan ShadowGap
mapping. The unavailable host32 development headers and earlier scaffold faults
are retained privately; they are not acceptance evidence.

## Narrow proposal for architecture review

These are proposals, not runtime edits:

- `SetEvt(data)` records whether this call created a new complete EVD. If the
  later `SetEvt(name)` fails, unregister **only** that new, still matching parent
  and its successfully admitted child references. Skip a prior resident owner or
  a row already removed by the existing init-failure DelEvt path. This relies on
  the transaction's complete admission and the existing serialized source call.
- `EvtReadExec` treats failed SetEvt as failure and follows an explicit failure
  cleanup path even for flags2/0x40. Release its owned read through real EvtFree;
  preserve a refused/leased read for its existing retry contract rather than
  pretending release succeeded. Clear only the failure state's scenario/status
  state and return zero. Preserve the successful keep-event paths.
- The tool GetEvd must free a newly debug-read buffer after failed SetEvd only
  when the transaction guarantees the failed attempt did not retain it. Adding
  unconditional Debug_free to the old disabled partial-admission path would
  leave its published parent dangling. This cleanup needs that explicit guard
  prerequisite or an equivalent ownership receipt.

The prior complete-parent test proves unconditional DelEvd on create failure is
unsafe: it would delete another resident owner. Same-name replacement,
same-address ABA, whole-room/reset teardown and general reader-generation policy
remain separate. Selected cabin refusal/lease paths need their own qualification
before a runtime successor is accepted. No architecture approval is inferred
from this proposal.

## Actual SH4 static stack evidence

The sealed cabin1 enabled event object/source hash is rechecked and copied
read-only. Additional current Make objects are only `db_log.o`, `game.o` and
`scheduler.o`, compiled with `-fstack-usage`, valid route/native/audio controls
and `DVD_READ_SAFE=1` (which supplies the existing no-op door diagnostic header).
The initial unsupported minimal game-object control is retained separately.
No complete program, overlay or guest is built.

| Function | Static bytes |
| --- | ---: |
| SetEvd | 752 (baseline/OFF44) |
| SetEvt(data) / SetEvt(name) | 24 / 36 |
| EvtReadExec / SetEvs / GetEvd | 52 / 40 / 292 |
| SetBin / DatTbl::SetDat | 20 / 52 |
| gameRoomInit | 64 |
| cLog::err / verr / add | 80 / 24 / 304 |

The compiler prints vararg names as `)` in `.su`; err's actual disassembly saves
PR4 and subtracts76, confirming80. Object relocation/disassembly output verifies
the selected real call edges. Native GetStackSize has static frame0 and returns
12,288 bytes for every source task.

Known source-frame sums are 900 bytes for EvtReadExec -> SetEvt(data) -> SetEvd ->
SetBin -> SetDat; 928 for gameRoomInit -> SetEvs -> that admission chain; and1116
for GetEvd -> that chain. The deepest source logging path adds408 **once**, giving
1308/1336/1524 before unmeasured outer callers, libc/printf/device routines and
IRQ/OS frames. These are partial static subtotals, not stack-use measurements,
whole-call-chain maxima or remaining-stack guarantees. A source failure's layered
logs occur sequentially; their frames must not all be added together.

SetEvt(name) is called after SetEvd returns, so its36-byte frame does not overlap
the752-byte admission frame on that path. GetEvd completes HDReadDebugAlloc before
SetEvd; deep file-open temporaries similarly do not overlap this admission.
Dynamic target high-water for actual route callers remains open. The existing
12KiB floor alone does not qualify every call chain.

Receipts: `event-caller-failure-host.json`, `event-caller-stack.json`. Raw source,
adaptations, commands, logs, objects, disassembly and earlier scaffolds are under
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/event-callers`.
Small-object floors remain16GiB+128MiB start/16GiB+64MiB stop with bounded logs;
no full-build guard was lowered. No gameplay/read-volume/timing or hardware
acceptance, runtime fix, recipe, release/issue or SD change is claimed. Root owns
the ownership decision and integration; Claude alone merges/tags/publishes.
