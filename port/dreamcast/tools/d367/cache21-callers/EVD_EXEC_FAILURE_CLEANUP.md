# Bounded direct-read failed-start cleanup

`EVD_EXEC_FAILURE_CLEANUP=1` defaults zero and requires
`EVD_START_ROLLBACK=1` (and its transaction/start-cleanup prerequisites).
This first unit covers `em == 0` after EvtReadMram succeeds and SetEvt fails.
Module exchange (`em != 0`) and EvtReadMram's own destructive load-failure
cleanup retain their existing paths and remain open defects/contracts.

Before reading, EvtReadExec records whether the exact read already existed,
its unit/slot/module metadata, and the two status bits/system bit it changes.
After failed direct-read start it returns zero immediately: no waiting for a
prior running name, cancel fade, kept-event success or unrelated camera return.
It pairs exactly its own SceEventStart through actual SceEventEnd and restores
only the selected masks, preserving unrelated bits changed during transport.
The real source brackets are nest-counted; a prior event keeps its counter and
camera state. Successful starts keep their existing source path.

A prior read is never freed by this branch. Its exact still-matching slot/unit
regains its earlier readEm bytes. A fresh registration can be freed only if it
still names the returned address, has the original single temporary/non-debug
reference, and no live Event or published EVD/bin points into its backing range.
The branch calls actual EvtFree, including native clear refusal. Refusal retains
the read for retry and still returns failure. A changed/shared registration is
retained conservatively. This is not a general acquisition/generation/ABA or
concurrent reset system; a real acquisition/reversal receipt remains next.

## Source qualification

`test_event_exec_failure.py` executes actual EvtReadSub/EvtReadMram,
setCommand/checkCommand/waitUseOk/waitLoadOk/setClear, both SetEvt overloads,
table admission/deletion, manager full-slot creation, EvtFree, IsAliveEvt and
SceEventStart/End bodies. OFF controls pass146 cases with cabin0 and cabin1.
ON passes153 cabin0 and154 cabin1 cases. The matrix covers nine independent
flags, fresh/prior registrations, MRAM/ARAM-to-MRAM input, nested/plain scenario
state and previously set/unset masks. Additional controls cover:

- A prior running event name without waiting, exact prior read/count/readEm
  snapshots, and an immediate retained-read retry into a free work slot.
- Unrelated flag updates during transport, retained live Event/EVD/bin backing,
  an injected fresh registration reference transfer, and clear refusal/retry.
- Unchanged em!=0 false-success/keep behavior and the still-destructive internal
  EvtReadMram failure path, as explicit negative scope controls.

Transport completion (`setLoadToMram`) and synthetic module-buffer exchange are
external boundaries. Actual target allocator/install/ARAM carrier conversion
is not accepted by those controls. Native carrier refusal policy is a boundary;
actual EvtFree/setClear refusal propagation executes. Event::init is a positive
boundary in this focused exhausted-create suite; actual initialization failure
and carrier cleanup were qualified separately in the prior rollback/init
receipt. Scenario actor/world/key/damage/camera/audio services are counted or
no-op boundaries around the actual bracket bodies. Definitions are renamed
only to count entries. ABI adapters and exact original/executed body hashes are
recorded. This suite uses UBSan; it does not execute the manager post-delete
destruction path whose prior strict diagnostic remains open.

The prior debug-input cleanup suite also passes19 cases per OFF/ON arm with
the new failure guard off after the fixture extension. Prior receipts remain
immutable; new outputs have distinct directories and hashes.

## Object qualification and limits

`qualify_event_start_rollback_sh4.py --exec-failure-pair` compares whole actual
SH4 event.o against `dfc0cf972`, with earlier rollback selected in transaction1
arms. All four disabled identities pass across transaction0/1 and cabin0/1.
Default and explicit zero compiler commands match; invalid values and missing
prerequisites reject. Selected PPC source preprocessing is identical.
Enabled text grows620B; data4/BSS640 are unchanged. EvtReadExec's static frame
grows52 to80B; existing SetEvt(data)40, SetEvt(name)32/36, init16 and admission752
frames are unchanged. No whole-stack high-water guarantee is inferred.

Source SHA `34c724861a23c11934598009be70f5d36431dbfc430c90691ca3163e7b2952f7`.
Receipts `event-exec-failure-host.json` and `event-exec-failure-sh4.json` pin
source, commands, selected bodies and objects. Raw mirrors:
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/exec-failure-{host-05,sh4-01}`.
Earlier scaffolds remain preserved. No full-program/overlay identity, guest,
screenshot, gameplay I/O/timing, physical Dreamcast, recipe, release or SD gate
is claimed. Main owns review/integration and Claude owns production publication.
