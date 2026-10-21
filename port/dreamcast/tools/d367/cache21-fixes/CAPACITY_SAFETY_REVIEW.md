# Frozen motion-capacity safety review

Candidate reviewed: `1f7c34e4fc7a72222fd99c81afe66d08f890aa9e`, parent
`d4a3b31fac3362937a3f21eaa874e07be94fd061`. Its runtime, flags, assets and
recipes remain unchanged. This commit adds review tests and evidence only.
Neither the independent display-state repair nor the window hold repair enables
or imports this candidate. Root must settle the allocation/retirement contract
before a capacity runtime repair or final combined qualification.

The original exact-size benefit remains reproducible: 72,224 bytes of K05 demand
retain three loads/zero evictions with the same 64,832-byte packed reservation
and 262,144-byte aggregate overflow cap. That host result does not establish
universal allocation feasibility, a generic reset fix or gameplay acceptance.

## Actual-source findings

| Edge | New actual-source/SDK evidence | Remaining contract |
| --- | --- | --- |
| Caller interrupt mask | Raw SR masks `0x10` through `0xe0` pass `can_wait_required`; only `0xf0` is refused. Required allocation with another thread's pins reaches `thd_pass` under `0x10`, `0x80` and `0xe0`. | Refuse caller-masked requests before waiting; define any exception explicitly. The current comment promises refusal for masked critical sections and its predicate does not provide that. |
| Native static reserve preflight | Actual `re4dc_static_alloc(1024)` refuses at 65,664 bytes free without entering reclamation. Explicit overflow drain restores 83,168 bytes; the identical request then succeeds under the unchanged 80 KiB source reserve. | Feasibility/reclaim must precede a required native admission while preserving its reserve and ownership policy. Do not remove the reserve to hide this gap. |
| High placement | Actual high-placement request 1,700,416 bytes fails with total 2,013,888 and largest 1,692,224; it makes no reclamation request. Explicit overflow drain lets the same actual high allocator succeed. | The high-cell path needs a compatible transaction for the required placement. A generic low-address `mem_alloc` retry does not implement its layout contract. |
| Held reset | Actual `MemClearAllHeap` refuses through `re4dc_missing` before any SDK heap destruction while held. | This is explicit refusal, not a completed reset. Define how source tasks/readers/held backing drain or cancel before destruction. |
| Generic reset | With the hold released, capacity retirement drains overflow but leaves binding metadata and reserve allocations. Subsequent actual unbind forwards two native frees into a destroyed SDK descriptor. | Generic binding/archive/borrower retirement must happen before descriptor destruction, with generation-safe stale-owner handling. The overflow retire API is not that mechanism. |
| Admission during teardown | A deterministic boundary observer between capacity retirement and actual `OSDestroyHeap` admits a new archive. Real bind clears `capacity_retiring`; later unbind forwards four native frees after destruction. | Serialize admission against the complete teardown epoch. Short SDK list IRQ guards and a flag that any new bind clears do not establish that epoch. This is an injected interleaving, not evidence that gameplay took it. |

The raw-SR adapter follows the actual local pinned KOS interface: `arch_irq_disable`
returns the complete SR and restores `(mask & 0xefffff0f) | 0xf0`; restore writes
the saved SR. Source hashes for `arch/irq.h` and `kernel/thread/thread.c` are in
the receipt. The old fixture represented only unmasked/fully masked nesting.
The new `thd_pass` exception is a boundary observer that stops a masked wait so
its state can be inspected. No SH-4 scheduler deadlock or physical-console
failure is claimed. KOS `thd_pass` manually reschedules; whether a particular
masked owner can progress does not excuse violating its caller critical section.

The SDK free observer forwards the invalid-owner frees into the real release
allocator, as H064 did. It does not substitute a refusing allocator. Raw-SR and
device/thread boundaries are modeled; source allocation, native motion/bridge,
native high-cell placement, reserve preflight and heap-clear bodies are actual.
All results above are ASan/UBSan host characterization, not repaired behavior.

## Positive controls and source-reader limits

The original candidate's K05, simultaneous pins/pointer stability, other-thread
required-pin wait, lock-busy/inflight read, eight concurrent required allocators,
new-binding metadata/reserve admission, fragmentation/original failure, aggregate
cap, failed read/hold/strict-v3 retirement and same-evaluator/full-mask refusal
controls are rerun unchanged in the raw-SR fixture and pass. These test bounded
candidate-owned operations. They do not prove general concurrent suspension,
heap destruction, shared `CurrentHeap` switching or raw borrower cancellation.

All 28 original source-contract rows match their pinned hashes, including the
seven evaluator lease scopes. The selected attach-camera helpers update fixed
tables; the reviewed DVD callback updates queue flags. The lease scopes and
selected decoder/math/log helpers do not establish a complete transitive call
graph. Formatting/console/KOS work remains distinct from source SDK allocation.
Do not infer that every future helper/callback or error path is a finite,
allocation-free evaluator merely because these source hashes match.

Scoped leases protect a table only through their final use. They do not clear
retained Work/header/callback pointers, certify owner generations or prove that
all source borrowers stop before archive free. H064's child/callback/event-shape,
intra-room and forced-interrupt lifetime cases remain independent. No lifetime
row is closed by an overflow marker, a live handle number or these host tests.

## Evidence and next architecture decision

`test_capacity_review.py` exports the exact candidate through H064's existing
source export, preserves the existing capacity fixture and extraction, then
compiles additional test entry points. Runtime bodies are unchanged. A host-only
raw-SR service adapter replaces the binary nesting adapter; two linker boundary
observers forward to the actual SDK. The candidate's existing source-contract
checks run before compilation. The fixture, actual source, projections, headers,
commands, binary and outputs are retained in the private mirror.

```
python3 port/dreamcast/tools/d367/cache21-fixes/test_capacity_review.py --out /root/probe/<owned-new-output>
```

Receipt: `capacity-safety-review-receipt.json`. Private raw proof:
`C:/Flycast-Evidence/re4-dreamcast/cache21-fixes-20261021/capacity-review`.
Earlier failed scaffolding remains preserved separately. No new target object,
full build, stage, guest, screenshot, hardware, release/issue or SD action ran.
The candidate's earlier SH-4 object qualification retains its original scope.

Root's architecture review should define: refusal for masked/same-reader
contexts; required native feasibility and placement under the existing budget;
admission suspension across a generation; and full pre-destroy reader/owner
retirement. The current candidate stays separate/default-off until those bounds
and the final selected source/program/asset/gameplay gates are qualified.
