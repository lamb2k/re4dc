# V16 controller and 41/47.5-second supervisor review

Read-only Python AST parsing passed for the following inspected bytes; none were executed:

- v16 controller: `e956c990fc3ae06efde587c072cc5548eee8ad2eea73abef864854f66c02f393`.
- `guard-resume-41inner-47absolute-resources.py`: `70d7dc236ebd1161f856c77506c4251f713f5942890bf35149117a0d83d243fe`.
- `run-resume-41inner-47absolute-resource-guard.py`: `8cd81b3f96164b342eb7719233b1f509257dd9fa556c7cfb9ed3beaf4b9832b8`.

These are the original inspected revisions. Castle21 owns corrections and a subsequent review must use the new hashes. No guest, source/controller edits or process termination was performed by this review lane.

Launch blockers reported to castle21 and root:

1. The watcher has a `finally` that closes its handle and writes a receipt, but no exception path that safely closes/terminates and verifies the exact owned guest. A removed file during `rglob/stat`, disk query failure, window-count assertion or WM_CLOSE failure can exit the watcher while the guest remains alive. The watcher must remain responsible for the authenticated process on every post-acquisition exception path. A disappearing sampled file should be handled as a sampling race; other failures require an explicit owned cleanup outcome. Never broaden ownership to other processes.
2. The runner does not check watcher return status. If the driver returns or fails while the guest is still alive, it waits six seconds and then terminates the watcher itself, removing the independent guard. Its final STATUS text always claims no active guest. Retain supervision until authenticated guest exit or authenticated owned cleanup; require and inspect the guard result and process-exit evidence before reporting that no guest is active. A watcher failure must be visible.
3. The watcher calculates process age, then performs a full potentially unbounded filesystem traversal before checking its 47.1-second termination threshold. That check uses the pre-traversal age. Check and act on the deadline before potentially slow sampling, recompute afterwards, and retain the exact PID/path/creation-time safeguards. A path scan should not delay the only absolute-time enforcement path. Fault-test slow/failed sampling and missing-window/close-failure cases before treating the supervisor as qualified.
4. V16's 41-second process-age test is only at `transition(wanted)` for nonempty requests. An already-held input can continue through an inner held/ack/polling loop past 41 seconds without another transition. Its outer loops still measure elapsed time from `guest_started`, established after guest creation/loading. Poll a separate input deadline throughout active control loops and permit release/cleanup after that deadline. Do not make generic identity verification fail after 41 seconds: `transition(set())`, screenshots and exact cleanup still need identity checks. Anchor process age once from creation FILETIME and then advance it with a monotonic clock rather than repeatedly depending on adjustable wall time.

Confirmed changes: fast movement now checks actual lower-floor/region; the screenshot floor is 18 GiB + 64 MiB; the bell shot requires process age below 23 and callback below 25; the movement subsets share a 33-second `guest_started` bound and overall controller loops use 41. The pre-shot/callback checks improve budget feasibility but are not whole-guest time qualification. A bounded input deadline, bounded final capture and robust external owned supervision must compose correctly before asserting the absolute process limit.

Suggested verification is targeted supervisor fault injection: disappearing sample entry, forced disk-sampler exception, window enumeration/WM_CLOSE failure, driver failure while the exact test child is alive, and delayed sampler near the deadline. Verify child exit and guard return/result in each case; preserve failing receipts. This is a test recommendation, not a claim those tests were run here.
