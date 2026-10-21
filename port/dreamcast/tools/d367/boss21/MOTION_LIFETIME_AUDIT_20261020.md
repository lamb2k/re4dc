# H064: reset, borrowed FCV retirement and partial admission

This continues H062's eight cases on `codex/boss21-motion-lifetime-audit`, parent audit `368585a9`. Runtime source tested is exactly **d4a3b31fac3362937a3f21eaa874e07be94fd061**, exported from Git. Capacity `1f7c34e4` remains frozen and separate. No runtime code, package, recipe or geometry changed.

**Three previously source-visible defects are now reproduced with actual method bodies.** Eighteen ASan/UBSan motion/module cases (nine each with RESET_HEAP_FIX=0/1) pass their characterization assertions. A separate UBSan event executable reproduces partial admission and retry. Passing a characterization means the asserted defect or positive control occurred; it does not mean repaired behavior.

## Actual SDK reset result

`systemResetCheck` (main.cpp638) calls `systemSoftReset`710, which calls `MemClearAllHeap` before `systemResetCommon`668. The latter clears tasks and then calls `EmReadInit`. `MemClearAllHeap`536 and `MemDestroyHeap`394 destroy the descriptors. `InitModule` (read.cpp404) then calls native motion unbind **before** DLL_Unlink, effect/UI unbind and source archive free. Neither ordinary room retirement (`re4dc_room_leave`, ui_bridge397) nor `gameRoomMemInit`1507 is the soft-reset owner here. The reviewed preceding sound/debug operations do not supply a generic motion-retirement call; an arbitrary debug overlay callback is not modeled.

The host constructs a synthetic valid v2 archive in actual SDK heap4, binds its real native metadata/reserve, loads a key, then follows that destroy/unbind sequence. SDK release DEBUG=0, OSFREE_CHECK=0 is explicit. The complete real OSAlloc.c is compiled, with only platform/assertion definitions and the existing host cell-padding adaptation. A linker observer records invalid-owner frees and **forwards them to the real SDK**, rather than replacing its allocator policy.

| Actual-source control | Native frees after destruction | Source archive frees after destruction | Result |
| --- | ---: | ---: | --- |
| InitModule while heap is live | 0 | 0 | Owner remains valid; frees/coalescing pass. |
| MemClearAllHeap then InitModule, RESET_HEAP_FIX=0 | 2 | 1 | Disabled SDK descriptor is relinked despite size=-1. |
| Same, RESET_HEAP_FIX=1 | 2 | 0 | ModuleMemFree guards source free only; native defect persists. |
| Explicit native retire **before** heap destruction | 0 | 1 or0 | Positive test control; source free depends on reset fix. No runtime repair added. |

The two native frees are the real reserve and slot metadata. `motion_bridge.cpp22` frees their recorded SDK owner directly, bypassing ModuleMemFree. The separate room-cell stale-free guard in ui_bridge663 does not cover these allocations. OSFREE_CHECK is a diagnostic default0; enabling it changes the invalid-free outcome and was not tested here. This result does not assert an observed console reset failure or a crash from every invalid free.

With an active scoped FCV pin, ordinary InitModule hits the native pin guard before freeing anything. On the baseline reset sequence, heap destruction completes **before** that same unbind guard detects the pin. The test substitutes an exception for terminal `re4dc_missing` solely to inspect this boundary; actual production refusal does not continue. Host invocation establishes a missing generic ordering contract, not that this overlap occurred in gameplay.

The separate capacity candidate's `capacity_retire` drains marked overflow and blocks refill; it is not a complete generic binding/metadata/reserve retirement and must not be called a fix for this finding.

## Borrowers and admission

The real Re4dcMotionLease acquires a pin, switches the local table and restores the archive proxy when its scope ends. Actual unbind then removes the binding and frees its allocations. A retained caller header/table is still unchanged; a later acquire for that header returns no binding. The host deliberately does **not** run a source evaluator on freed archive bytes. Hence raw Work/subArc/callback lifetime still requires the producer's termination/generation contract; scoped pin safety alone does not close it.

A DLL boundary observer also confirms that the motion binding is already absent when epilog runs. This injected observer is not a selected gameplay epilog. H060's eleven selected empty epilogs remain a narrow positive fact, not proof that every borrower stops before native unbind.

Actual readEm (read.cpp440) with four occupied slots returns NULL with Disp_flg changed **0x12340800→0xfffff7ff**. Transport failure and success restore the original value. The transport is an external boundary stub; the full source readEm/pullEmModule decision is unmodified.

Actual EventMgr::SetEvd2870/SetBin2813 and DatTbl::SetDat3331/ChkDat3406 reproduce: a one-slot BinTbl accepts the parent and bin0, rejects bin1, and returns failure. After a second slot becomes available, retry returns success from the already registered parent without ever adding bin1. Complete admission, parent-capacity failure and bad-tag refusal are positive controls. Reusing an EVD name keeps its prior owner; duplicate bin registration keeps prior bytes and increments Count. This proves existing semantics, not that intentional name reuse is universally wrong. Generation replacement/refcount-safe rollback remains OPEN.

The event test retains the real signed-negative32-bit address guard by mapping synthetic data at0x90000000. UBSan runs; ASan cannot cover that ShadowGap address. EventMgr's required fields/method declarations are projected for host compilation; actual method bodies and event header/bin layouts are unchanged. Target class ABI is not certified.

Native bind's separate **reserve-allocation failure** is a positive cleanup control: at16000B free it allocates metadata and one fallback slab, fails the second, releases the partial binding, returns to the identical free total, and can bind after the test releases pressure. This is direct adapter retry only. The selected readEmData bind-refusal caller is terminal. DVD failure allocation cleanup, moved resize allocation and model-extra partial admission remain untested subcases.

## Eight-case continuation ledger

| Existing edge | Current classification | Remaining owner/next verification |
| --- | --- | --- |
| A03-OBJ12 | OPEN: MotionMove precedes dead-parent guard; deferred cart/destructor donors still possible. | Boss source audit: child update/destructor scheduling and donor-generation identity. |
| A03-OBJ16 | Local parent/emitter guard reviewed; installed player damage callback survives that local guard. OPEN. | Boss: stop callback/EndPlDamage or retain actual parent donor before retirement. |
| A07-FATAL | Normal Continue/door quiescence source-reviewed. Forced/intra-room interrupt OPEN. | Boss: selected callback/held prop termination through exceptional exits. |
| A08-RESET | Actual SDK host defect reproduced; runtime/gameplay acceptance OPEN. | Root reviews pre-destroy owner retirement, lease/task cancellation and generation-safe forget. A handle-live check alone cannot exclude handle reuse. |
| A08-INTRAROOM | Bell/cabin sleep2 and cannon free-before-yield remain OPEN. | Boss: two actual dieCheck passes, partner/child drain and callback suspension, not two scheduler sleeps. |
| A08-SLOTS | Actual readEm failure reproduction; repair unimplemented. | Root review: restore saved display flags on every return. |
| A08-EVENT-SHAPE | Type5 motion clear is not ShapeEnd; dead player's mode0 skips routine reset. OPEN. | Boss: selected live shape/header carrier termination or retention. |
| A08-EVDBINS | Actual partial-admission false-success retry reproduced; repair unimplemented. | Root review: transactional registration/rollback preserving prior shared owners and exact refcount deltas. |

H060's mode0 source and selected SH4 object proof remains intact. The separate ABI issue is nonzero modes collapsing to0, with two named mode2 exits r220162/r221557 still OPEN. This audit does not reinterpret mode0 teardown as absent.

## Evidence and reproduction

`motion-lifetime-host-receipt.json` pins29 reviewed functions, all exported source hashes, exact flags, commands' outputs and test hashes. Run:

```
python3 port/dreamcast/tools/d367/boss21/test_motion_lifetime.py --out /root/probe/<new-owned-directory>
```

Raw commands, generated source projections, binaries and logs remain in `/root/probe/boss21-lifetime-host-sealed`; a C evidence mirror preserves them. Earlier failed scaffolding attempts are retained separately. Existing34 structural tests and66-archive census are reused without a new asset/room scan; they are not claimed as rerun or as lifetime closure. No full build, target object, stage, guest, hardware run or gameplay screenshot was produced by this source-only checkpoint. Source coverage remains incomplete; the OPEN rows above remain active work.
