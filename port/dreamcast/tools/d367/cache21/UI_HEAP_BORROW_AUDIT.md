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
