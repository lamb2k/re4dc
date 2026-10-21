# Failed event-start admission rollback

`EVD_START_ROLLBACK=1` (default zero) requires both `EVD_ADMISSION_TXN=1`
and `EVD_START_CLEANUP=1`. The candidate starts from integration `892c10dd`
plus the preserved cleanup qualification `93b0074f`, merged as `32172f542`.
The earlier transaction and cleanup receipts and implementations stay intact.

The original outer `SetEvt(data)` admits the complete EVD and its bins before
starting an Event. Exhausted work slots or failed initialization return zero
while leaving the new parent/bin references published. An ordinary outer
`EvtReadExec` can subsequently free that backing and still return success.

The candidate remembers whether the parent existed before this synchronous
source call. After failed creation/initialization, it removes only its new
parent still matching the incoming address, event type, single reference,
temporary flags and non-debug ownership. Actual `DelEvd` drops the admitted bin
references, preserving existing shared bin backing and counts. A prior complete
parent remains byte-exact, including when its address matches the incoming data.
Successful starts and ordinary explicit completion keep their existing paths.

This uses the existing serialized source admission contract and immutable input
header. It introduces no generation/lease system, reset serialization, general
concurrent admission or same-address ABA guarantee. Changed/removed/transferred
rows do not qualify for rollback. No input allocation is freed by this repair.

## Source evidence

`test_event_start_rollback.py` executes actual table admission, both SetEvt
overloads, exhausted manager creation, caller and data-unit release bodies.
Fifteen cases each with rollback OFF/ON cover eight outer flags, prior running
work, different/same-address prior parents, direct retry, shared temporary and
permanent bin owners, and the still-open tool input cleanup case. Event init is
an explicit successful boundary in this focused suite. Input transport, pool
construction/list attachment and final allocator free are explicit boundaries.

`test_event_rollback_init.py` executes actual Event initialization, local work
destruction, manager/table bodies and carrier/cabin callbacks. OFF and ON each
pass 23 cabin-off cases and 43 cabin-on cases with each completion-handoff
setting. Eight added outer-overload cases cover model-table refusal, invalid
packet, missing camera and injected final-scan mutation, each with new/reused
parents. Complete pre-admission parent/bin snapshots are restored on failure;
prior work/name and all 128 effect-model pointers survive, and an immediate
valid retry succeeds. The final mutation is a synthetic immutable-input
violation, not an ordinary gameplay occurrence claim.

The init state suite uses UBSan excluding vptr and retains separate strict OFF
and ON runs that stop at the existing manager post-delete `p->be_flag` write.
It is not a clean full-sanitizer result. Host64 projections and the previous
native32 pointer-width adapters are documented in the receipts. ASan is
incompatible with the negative32 mappings needed for the actual address guards.

## Object evidence

`qualify_event_start_rollback_sh4.py` compares complete actual SH4 event objects
against the exact merge base, for transaction 0/1 and cabin 0/1. Default and
explicit zero compiler commands match; every disabled object matches its
baseline byte-for-byte after stripping debug paths. Invalid knob values and
missing prerequisites reject; selected PPC source preprocessing is identical.
Enabled transaction1 objects add 152 text bytes, with data/BSS unchanged.
SetEvt(data)'s static frame grows 24 to 40 bytes; init/name/admission frames stay
unchanged. These are object/static-frame checks, not full-program identity or
whole-stack high-water measurements.

Exact receipts and raw commands/source/binaries are mirrored under
`C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021`. No full linked
program/overlay, guest, screenshot, hardware, gameplay-I/O/timing, recipe,
release or SD acceptance is claimed.

## Remaining caller contracts

`EvtReadExec` still masks failed starts, can wait on prior work, and can preserve
status/read state through kept flags. `EvtReadSub` can overwrite an existing
read's module/swap metadata or clear its backing after a load refusal. Read
ownership, scenario pairing, debug-input admission failure, reset retirement
and general generation/transfer policy require separate implementation and
qualification. This bounded rollback does not certify them.
