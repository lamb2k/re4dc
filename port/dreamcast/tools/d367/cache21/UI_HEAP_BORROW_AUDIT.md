# UI heap ownership: source audit, 2026-10-22

The main cache audit checked the actual Manual-UI ownership boundary after the
fixed-programme Flycast observer attempt reached Playing Manual 2 but failed
qualification. This establishes a reader precondition, not a new game defect.

The current cache candidate and the exact QA source c57ff60f have byte-identical
bridge files:

- parts_bridge.cpp SHA256 616bcfd7b1606ed0b47a36791b183e6bf1476bfe61b687f2b3652e613536d35f
- sscrn_bridge.cpp SHA256 eb704d519337b4349fc069b11fd9aea7825831f5048a4fd5980b81f857a703ab

The screen borrows the 3 MiB pStFnt window. Room pool headers and player storage
can reside there. parts_bridge freezes demand-pool slot tables outside that
window before reuse; raw addresses remaining in pPL/EmMgr do not imply that
their world objects remain available while the screen owns the bytes. Native
workAt uses sparse slot pointers after the 64-byte header, so a diagnostic must
not substitute contiguous base-plus-size indexing.

At swap open, sscrn_bridge.cpp calls re4dc_model_detach_retained_storage before
packing/reusing the window. In native_model.cpp the renderer-stack implementation
clears the retained pointer and invalidates the prepared batch. The room's heap
keeps ownership; inventory heap 12 cannot reacquire that room cache. This is a
source-level ordering check, not complete proof for every cache/feature arm.

Close restores packed/raw spans, computes their hash, closes backing, thaws
the pool copies, restores message state, forgets dead-heap motion residency and
invalidates UI sources. The optional actor certificate path unparks only when
the restored hash equals the opening hash. These boundaries must remain part
of future cache lease/epoch and diagnostic domain contracts.

Actual QA programme 52190ed2 / ELF248dd4aa reached the Manual 2 screen. Of164
retained observer rows,161 were valid and3 invalid; a final teardown-invalid
row was not evidence that the whole run was invalid. The later terminal state
and independent typed UI/global fields can establish UI ownership. Stored HP
does not establish actor liveness, and gameplay inputs still require the
appropriate restored world/player ownership. The observer's contiguous-pool
assumption and retained-exit bookkeeping are being repaired separately. The
actual run remains unqualified; no crash cause is inferred.

This necessary RAM restore is distinct from the disabled experimental menu
texture-window restoration. That candidate's measured extra102 low-level
requests /168032 bytes remain a negative result; no performance improvement
is claimed or guard enabled here.

Remaining main audit work includes other cache borrowers/leases across these
boundaries, archive/reset epochs and a normal-entry proof for gameEnding's
direct room reset. Normal door and soft-reset drain ordering has been reviewed;
that does not close every heap/pending-I/O path. No additional runtime fix was
justified by this bounded source audit. Existing Event lifetime repair f3149dfc7
and its source/host/object evidence remain unchanged; target qualification is
separate.

Follow-up borrower review, same ef2340456/runtime f3149dfc7 source:

The renderer reacquisition guard is concrete: ui_bridge.cpp
re4dc_model_retained_storage rejects requests without preparation_owner,
current heap4 and active heap4; the movie loan also returns null before
latching an allocation attempt. The renderer's detached retained pointer
therefore cannot simply reacquire the room cache from current heap12.
Source SHA256 ui_bridge.cpp:
426a06c09524c21b6246a818aac130c58bd9fab44fe4d4959f9e8e3042b21f69.

Motion hold is set before pool freeze and before memset of the3MiB window.
Close restores the spans before thaw, and forget_dead_heaps recounts under
Locked before clearing hold. Those are verified ordering boundaries, not a
whole-archive lifetime proof. Its recount reads record(b,i)+4 after validating
slot/data allocation ownership; b.records itself points into the bound
archive. The next independent caller trace must establish whether archive
and slot owners can diverge across UI/reset/ending, and handle-reuse limits.
No reachable normal-path counterexample was established by this read alone.
Source SHA256 native_motion.cpp:
5a4b3c64f98815772021bed83ff1ef5e8b302243002df587991c89bfe49bb58d;
motion_bridge.cpp:
80176e91b5442422bb801bcf3c6063b6a23629723df25ab318a02ef0355842a5.

A separate fault-containment question remains: close computes restore hash
before thaw/recount but reports a mismatch after them. This is a review
question about a failed restore, not evidence of an observed corrupt restore
or the cause of issue52. No runtime patch or guard/default changed here.

Disposition after follow-up: the conditional restore-fault containment question
above is fixed in the separate default0 source candidate26bc3e787; see
SS_RESTORE_VALIDATE_FIRST.md and independent caller review58ecc175c. Source/
host checks do not establish target acceptance. The normal co-owner archive
trace found no live-slot/dead-archive recount witness during ordinary UI close.

The same independent37-check/35-function trace identified a separate reset
contract: diedemo decline can select systemSoftReset, which clears all heaps
before systemResetCommon/EmReadInit subsequently unbinds motion archives.
Motion release_binding uses captured allocation headers/heap handles; the
RESET_HEAP_FIX module-free wrapper does not cover motion_free. An already
closed screen does not add retirement via SubScreenExitCore. A loaded MTC
binding is the prerequisite. This is a source-path finding, not an observed
runtime failure or cause of issue52. Main next implementation unit must qualify
an ordered reset prephase: restore an active borrowed UI while its room heap
still exists, quiesce readers/native consumers, retire motion before all-heap
destruction, and retain ownership on refusal. A blind retire call in
MemClearAllHeap cannot handle the active-UI ownership boundary safely.
