# Independent review: QA failure telemetry successor

**Disposition: clear for the bounded source/mock change at85bac7a7113816d3e8c9564d0c301ed4c670aa94.** A concrete exception-path telemetry gap in the first candidate was corrected during review. This is not guest qualification, launch approval, a timing repair or reconstruction of the earlier failed run's missing measurements.

Reviewed baseline `1bcbc5df33ed2f3b3dfaf376e06416b34f7176bb`; first candidate `368b92fab4fcfdc48c98061611a872fb5ec693f7`; corrected successor `85bac7a7113816d3e8c9564d0c301ed4c670aa94`, all in `/root/probe/codex-qa21-death-repair`. Review scope is the four owned qa21_nontrace_guest files: input-deadlines.py, inner-adapter.py, windows-backend.py and guest-supervisor-core.py.

## Finding corrected

The first candidate attached pulse telemetry to native-post and elapsed exceptions in Inputs._up. Its expire callback later called fail, so the existing test observed a complete record. Direct engine-up instead could reach controller stringification, and release_all could aggregate into a new RuntimeError without pulse attributes. Thus the record could be lost despite failure remaining fail-closed.

The successor invokes the existing failure callback immediately after attaching the record in **both** _up exception branches, before those wrappers can discard it. Three added focused cases cover direct native-up failure, release_all aggregation and elapsed failure after a successful native queue. The failure marker is already complete before the aggregate loses attributes. Held-input/capture refusal and cleanup behavior remain unchanged. The QA worker retains16 passing focused tests on each Windows/Linux platform; this reviewer read and hash-verified those receipts and did **not** rerun them or any broad/native-child tests.

## Numeric and input checks

Lease start, deadline, declared bound, key/reason, callback attempt/return and conservative queue-hold upper bound are preserved on the error object and first failure marker. If the native callback throws, the unavailable callback-return/hold values remain null; partial per-HWND PostMessageW intervals/results remain available. An already-exited UP is explicitly queued=false. A returned native queue is distinguished from game acknowledgement; this does not prove game delivery or repair a late queue.

Static AST comparison independently verifies complete Inputs.down (including timer margin/scheduling), __init__, up, expire, release_all, close and capture release unchanged. The actual late-bound comparison `queue_hold_upper_seconds > bound` is unchanged. Added clocks and metadata incur work but do not change the declared lease or guard expression; no exact wall-time identity or scheduler improvement is claimed.

The dedicated failure-publication lock serializes the first failure. JSON is written/closed at the pending path before os.replace publishes the final marker. Serialization/IO failure retains pending evidence and does not publish partial JSON under the final name. The existing fail callback sets STOP_REQUESTED and records failure before publication. Marker IO is outside the separate hardstop thread. It can delay an already-failed inner path; the independent captured private-job deadline remains armed and does not wait for that IO/input lock. No new deadline bypass or qualification promotion was found.

## Retained exit and cleanup checks

The new Windows reporter uses the backend's already retained guest handle and identity. It rechecks creation FILETIME against the pinned start, requires finalized signaled exit, obtains raw creation/exit/kernel/user FILETIMEs and exit code, then computes actual duration from exit minus creation. The live path provenance is the path checked when that handle was acquired; no new PID enumeration can substitute a recycled process. Existing retained_identity already handles a process exiting during a live path query.

Supervisor order is private-job stop, independent pipe/input cleanup and retained waits, final telemetry, job-empty verification, deadline join, then handle closure. Reporter failures remain explicit unavailable, mark qualification false and append cleanup errors without suppressing subsequent cleanup. The original failure/error remains; telemetry never changes a failed run into PASS. A reporter error can veto an otherwise passing result, consistently with fail-closed cleanup. Actual retained duration over47.5seconds is still refused. If job emptiness is not established, the hard deadline is not disarmed and live-thread handle closure remains refused.

Removing only the added reporter call/function from the supervisor yields the baseline monitor AST exactly. Removing only WindowsBackend.final_process_telemetry yields the baseline backend AST exactly. Supervisor timing/disk/evidence/global constants are unchanged. Controller, policy, observer, outer driver, PLAN, profile and old tools-manifest bytes are exact. These are21 independent static controls, not a general concurrency or Windows runtime proof.

## Launch seals and scope

The original profile SHA `8aae247a6c0998af06ffce2d16a3832bfaaaf99dbab1769fc75b32b1a2103d1b` and source-manifest SHA `3557c5224df6b3715d282d3deab5fff7557b1c2ec8273c7d0ea76c1f359a41c1` remain unchanged. All four modified tools mismatch that manifest. outer-driver validates the reviewed source hashes before importing the adapters/backend or spawning an inner process, so the old launch seal still refuses these modified tools. No reseal or allocation was performed here.

`review.json` pins the four code hashes, all unchanged controls, exact retained Windows/Linux test receipts, and old-manifest mismatches. `review_static.py` only reads pinned git blobs, parses AST and verifies hashes; it never imports QA modules or invokes their entrypoints/tests/backends. Its git subprocesses are read-only metadata operations. Total owned review metadata is below1MiB. No build, image write, guest, RAM/input action, runtime edit, production recipe, release, SD or third-party action occurred. Main's mipmap programme/staging work stays separate.
