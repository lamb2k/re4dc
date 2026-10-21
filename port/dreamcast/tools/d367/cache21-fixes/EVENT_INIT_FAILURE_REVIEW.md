# Event initialization failure: exact cleanup boundaries

Read-only extension over `f37915daa7ca3a2edc6fffc1df9eb04372c8f37b`.
The independent transaction checkpoint `8ff45d69` and all earlier evidence stay
preserved. No runtime/header/Make/default/recipe change is made here.

## Actual-source results

`test_event_init_failure.py` reuses H064's selector and exact synthetic header
constructor. It executes actual Event constructor/destructor/init, CalMax*,
ExeFunc/ExeEndEvt, SetEvt/DelEvt, DatTbl methods, manager create/destroy/list
methods, EvtReadExec/EvtFree and data-unit command/free bodies. It also executes
the actual host-file wrapper chain and native unavailable PC backend.

The final suite completes **36 state cases per transaction arm**, with
EVD_ADMISSION_TXN0/1 showing the same failures. This includes the earlier31-case
checkpoint plus three shared-read controls and two valid-prior-owner controls.
The state run uses UBSan **with vptr excluded**. A separate strict control
retains the actual pool-lifetime diagnostic described below. This is not a clean
full-UBSan, gameplay, target or hardware result.

| Initialization stage | Actual failure cleanup |
| --- | --- |
| Invalid positive data pointer | init returns before pData/Name/table changes. A valid SetEvt(data) rejects this earlier; the direct init test does not run unsafe full deletion on an unbound header. |
| ModTbl.init allocation refusal | NumDatTbl96/pWorkNULL, pData set, Name still empty. DelEvt runs ExeEndEvt, performs96 null-table lookups/errors, destroys work, then attempts DelEvd(""). A newly registered parent and its bin references remain. |
| CalMaxCut invalid packet id | Name has been copied. DelEvt runs full end semantics, destroys work/table and deletes that named EVD. |
| CalMaxTotalFrame missing camera data | Actual GetBin fails through the actual native host-file refusal. Name is present, and the same full end/delete path runs. |
| Final CalMaxFrame refusal | Separately injected packet mutation after the successful unchanged CalMaxTotalFrame body. Immutable input has already passed the same scans, so this is a mutation/reader-contract negative control, not an independent ordinary-content failure. |
| Exhausted create | Separate control: no init, model-table allocation or event-end callback occurs. The earlier failed-create result must not stand in for init failure. |

Every init-failure path above that reaches DelEvt calls the actual normal
ExeEndEvt before the work ever begins: player reset/move, partner return, global
effect deletion, lighting/camera/message/shadow/font/sound/scenario teardown,
room end callback and SubScreenWait. External services are counted boundaries;
their real renderer/audio/device implementations are not run. The prior running
NowExeEvtName is cleared although the prior event work remains alive.

Later failures also leave all128 global EspEvModList entries erased. init clears
that view after model-table allocation but before validation. Allocation refusal
and exhausted create leave the seeded prior view intact. Simply avoiding DelEvt
does not undo this independent initialization side effect.

The owner matrix deliberately distinguishes:

- An unrelated prior EVD/bin owner: its parent, data pointer, debug owner and
  original references survive; a new failed parent leaks its own shared-bin
  increment in the early case, while later deletion drops that new increment.
- A reused same-name parent: later failure deletes its parent/bins and submits
  its debug owner for free while its prior event work is still alive. The late
  malformed-prior/dependency cases are forced fault controls, not claims that an
  immutable valid running stream fails a repeat scan.
- A complete **valid** prior parent plus a malformed new incoming header: source
  reuse selects the valid recorded owner and succeeds. Its registration/count
  remain unchanged. Do not validate/replace the wrong incoming generation.
- A valid prior event sharing the same pre-existing read during model-table
  OOM: ordinary flags free that exact prior backing through actual Mem_free_h
  while the prior work and EVD remain; flags2/0x40 retain it. Final free records
  pointer/heap and protects the page at the explicit heap boundary.

All failed EvtReadExec starts still return one. Ordinary flags remove ReadTbl and
free input; kept flags retain it, even after init has already run full event-end
semantics. EvtReadMram transport starts with an explicitly pre-existing ReadTbl
binding in this fixture. Actual EvtReadSub/SetRead/GetRead source is pinned to
show that existing and newly created reads differ; a fresh transport path is not
claimed executed here.

## Native missing-camera contract

Actual HDReadDebugAlloc -> hdRead_malloc -> file_open refuses both with source
host mode off and with0x20000 set. The current native PCopen/PCcreat stubs return
-1, so no debug allocation, disc read, asynchronous promotion or newly retained
camera file occurs in this selected Dreamcast path. A cleanup policy must not
invent such an I/O dependency. The earlier f379 tool-success transport control
tests a source API boundary; it is not evidence that current native host-file
loading succeeds or leaks in ordinary play.

## Split minimal implementation plan for root review

No part of this proposal is implemented or enabled:

1. Under a new default-off caller guard with an explicit transaction
   prerequisite, separate **never-started work abandonment** from normal event
   end. On init failure release only that work's allocated ModTbl/work and the
   exact carrier event binding accepted for it. Do not execute ExeEndEvt/DelEvt,
   clear a prior NowExeEvtName, unregister a reused parent, run an end callback
   or perform normal world/audio/scenario teardown. Cabin bound/audio callbacks
   occur after successful init; their accepted-binding boundaries need selected
   cabin tests before acceptance of a runtime successor.
2. Defer the128-entry EspEvModList reset to successful init validation/commit.
   The inspected GetFunc/Cal*/native refused host-file calls do not consume this
   view. This avoids overwriting a prior view on failure; a blind snapshot restore
   would require a separate concurrency/ownership guarantee. Preserve the same
   zeroed view before successful begin-pending publication.
3. In SetEvt(data), retain per-attempt EVD admission ownership. If downstream
   start fails, roll back only a new, still matching, untransferred complete
   admission. Use its saved header/name receipt, not the possibly unwritten work
   Name. Preserve a reused parent and its shared bin references. Do not double
   unregister a row already removed. A live other work/reader using that backing
   must keep its owner; generic generation/transfer/reset policy is not supplied
   by ChkDat or a matching address alone.
4. Handle failed EvtReadExec start separately from success/keep paths. Track
   whether this attempt created/acquired the read before requesting release;
   actual EvtReadSub can reuse an existing unit. Preserve prior/shared or refused
   reads and restore only this attempt's flag/state changes. Do not unconditionally
   EvtFree or BitOff prior state, and do not treat kept failure as success. The
   scenario start/end pairing and selected carrier refusal contract remain root
   architecture items, not assumptions justified by exhausted-create tests.

The independent local-abandon/commit boundary is narrower than whole reader or
reset ownership. Further runtime qualification needs separate failure tests for
accepted/refused cabin bindings, fresh versus pre-existing reads, seeded prior
status bits, immediate retry, prior live generations and successful begin/end.
The current host tests characterize the old behavior; they do not certify this
unimplemented repair.

## Lifetime and fixture limits

Strict UBSan stops in the actual cManager::destroy at `p->be_flag = 0` after
`delete p` in retained pool storage. Source pool delete does not free its slot,
but its C++ object lifetime has ended. The strict diagnostic is retained in the
receipt, not waived or called repaired. Only vptr is excluded for the separate
state-observation suite so later ownership/global effects can be measured.

Host projections are not target ABI. The prior native32 pointer-width/cast
adapters remain explicit; PFuncTbl and sized pool delete use host-width types.
The final-check wrapper renames only the actual total-frame definition binding
and injects the mutation after it returns. Source bodies/hashes and this test
binding are recorded. Negative32 mmap rules exclude ASan. No target object or
guest is rebuilt; earlier object/stack receipts remain their separate evidence.

Receipt: `event-init-failure-host.json`. Raw source/projections/commands/binaries,
strict diagnostic, the31-case checkpoint and earlier unsuccessful scaffolds are
preserved under
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/event-init` and
`/root/probe/cache21-event-init-host-20261021-*`.
No new runtime fix, gameplay occurrence/I/O/timing acceptance, full build, stage,
guest, recipe, release/issue or SD action. Root retains architecture/review;
Claude alone merges production, tags and publishes.
