# Read acquisition, reversal and retirement map

Source reference: `a8db82100`. This map supports main's next architecture review;
it adds no generation/lease/reset runtime. The three preceding default-off
repairs remain independent qualified source/object milestones.

| Operation | Existing producer and identity | Consumer/retirement | Contract still required |
| --- | --- | --- | --- |
| Fresh read | `cDataCtrl::setData/getNewUnit` creates an unused unit; `EventMgr::SetRead` publishes it in one of eight ReadTbl slots. It does not deduplicate file names. | `EvtReadSub` loads, `EvtReadExec` starts, `EvtFree/DelRead` retires. | A new slot is an admission, not a general reader lease. Receipt must identify the exact unit, slot, source owner and operation before a yielding load. |
| Existing preload | `EvtReadAram/EvtReadSub` leaves condition4 source backing and the same ReadTbl entry. | Later `EvtReadMram` legitimately promotes it; Count is unchanged. | Retain ordinary preload promotion. Existing Count cannot distinguish a preload owner, live reader or transferred attempt. |
| Direct MRAM reuse | Unit condition2, pointer, size, allocation owner; ReadTbl points at that unit. | Event initialization borrows header/bins; event completion or failure releases its own binding. | Reuse only a current compatible owner; do not overwrite another module role or run destructive transport while borrowed. |
| Prepared cabin | `native_event_file.cpp:re4dc_cabin_carrier_prepare` publishes generation before its reader can yield; current unit/range/allocation predicates validate identity. | Existing install/park/carrier-event and DMA APIs consume that generation. | Reuse this mechanism, not a second parallel cabin generation table. Map which generic event inputs lack an existing producer. |
| Event borrower | `re4dc_cabin_carrier_event` binds the exact accepted Event to current mram/module role. | Local start cleanup calls exact-event unbind; normal DelEvt unbinds before destruction. | Direct room EVS and generic read-backed events need their actual ownership mapped; merely seeing a live handle is insufficient. |
| Module exchange | `MemorySwap` plus existing cabin swap scope/token, heap/module/allocation identity. | `EvtFree` obtains reverse_token, swaps, verifies reverse_complete, then releases source role. | A prior swapped read must not be swapped again or have metadata reset. Reverse only an exact accepted exchange, with every Event/DMA reader gone. em!=0 remains outside the new bounded caller guard. |
| Unit clear/reset | Carrier `clear/reset` preflights current generation, readers, event role, allocations and overlap; source setClear honors refusal. | `cDataCtrl::initDataUnit` clears all32 unit descriptors; game callers currently continue after this void API returns. | Admission freeze, complete preflight, yielding callback coverage and failure propagation must cover the whole retirement epoch. |
| Heap replacement | Cabin before_heap/retire_heap validate affected ranges; `gameRoomMemInit` retires motion/effect/UI and replaces heap descriptors. | Room initialization later overwrites Event/Read tables and arrays. | Global reset preflight must precede the first destructive action, including weapon/overlay retirement. A lock around only descriptor erase is too late. |
| Event tool reset | ToolEvt suspends task0, then ToolCoreEvdDel clears EVD parents before bins. | Suspended work can still retain data references. | Suspension is not borrower retirement. Keep tool reset in the same ownership map; do not silently invent normal event-end semantics. |

The relevant existing implementations are `src/game/event.cpp`,
`src/game/datactrl.cpp`, `src/game/main_mem.cpp`, `src/game/game.cpp`,
`src/t_event/t_event.cpp`, and
`port/dreamcast/game/platform/native_event_file.cpp`. Generic generation or
whole-reset edits require main's reviewed producer/consumer/retirement contract
and shared-file claims. `read.cpp` remains read-only in this lane.

## Exact prior-ARAM allocation refusal

`test_aram_allocation_refusal.py` executes actual setLoadToMram, setCommand,
checkCommand, checkCondition, waitUseOk/isUseOk, allocation metadata and clear
bodies. Eight cases pass each with cabin0 and cabin1, under UBSan. Allocation
failure/install/heap/free and native carrier policies are explicit boundaries.
No transport/header/admission decision is replaced. These are synthetic source
controls, not a gameplay occurrence or target allocator acceptance.

For a prepared source unit (condition4, active/file flags5, no owned MRAM,
logical m_addr and dest, command/error/wait fields zero), the actual first
failed synchronous MRAM command changes exactly:

| Field | Before | After allocation refusal |
| --- | --- | --- |
| m_command | 0 | 1 |
| m_err | 0 | 1 |
| wait | 0 | 1 |
| dest | original logical address | 0 |

Actual waitUseOk sets m_wait to1 and retries checkCommand once before observing
the error: there are **two** refused allocations before the caller's failure
branch. All remaining projected unit bytes are identical: original condition,
logical address, size, flags, heap/allocation fields, file name and request id.
No install, DMA or free occurred. The old setClear then erases valid logical
source identity despite having no MRAM allocation to free. Retaining the unit
allows a successful actual retry, but m_err remains1 unless its owned delta is
restored. A first-load positive control uses actual setMallocInfo and final
release. A condition4 unit with pre-existing owned MRAM is an explicit exclusion.

A bounded repair therefore needs the exact unchanged original descriptor and
owner receipt, and restoration of this attempt's **dest** delta in addition to
command/arg/wait/m_wait/error. Restoring only m_err or keeping ReadTbl is
insufficient. Do not restore a stale snapshot after transfer, replacement,
partial installation or owned-MRAM change. Source allocator calls, diagnostic
and recovery callbacks, and carrier admission must be audited for yielding or
reentrancy before treating a local comparison as a complete epoch contract.

Receipt `aram-allocation-refusal-host.json` pins the actual source and methods.
Raw proof: `C:/Flycast-Evidence/re4-dreamcast/cache21-callers-20261021/aram-refusal-host-03`.
No runtime refusal repair, broad generation state, reset serialization, target
build, guest, console, recipe, release or SD change is included in this map.
