# Reproduce source-only terminal controls

Frozen runtime: `1d63cffe3a232c402418f2f2d919e7abae476957` in existing Git objects at `/root/work/lanes/gc-port23`. Do not use a mutable working tree. No SDK or guest is involved. No payload assets are included in this folder.

The runners expect these immutable RAM snapshots:

- `/dev/shm/gc-static-review1d63/source`: `git archive` of frozen `port/dreamcast/game`, `port/dreamcast/room`, `port/dreamcast/tools/d367/gc_port23` (about8.7MiB, not a clone).
- `/dev/shm/gc-terminal-next1d63/source`: selected frozen `src/game` and header source files listed in source-pins.json; use `git show COMMIT:path` to materialize original bytes.

Example reconstruction under Linux Python: invoke `git archive COMMIT port/dreamcast/game port/dreamcast/room port/dreamcast/tools/d367/gc_port23`, read the returned tar into `tarfile` and extract only into the checked RAM directory. For each source-pins.json source row missing from that snapshot, write `subprocess.check_output(['git','-C',repo,'show',commit+':'+path])` beneath the second RAM source directory. Assert every materialized source byte SHA against source-pins.json. The pin generator additionally compares the actual snapshot bytes to Git and records Git blob IDs. It uses the original external coverage/profile paths and read-only KOS provider paths, so do not overwrite its original source-pins receipt during a later changed-profile reproduction; preserve a separate receipt.

Run each `run_*counterexample*.py` sequentially from WSL Python. Each sets RLIMIT_AS to256MiB and invokes one compiler at a time. The two first runners use the host loader explicitly for noexec RAM binaries. No root SDK slot or target command is required. Outputs are their adjacent C++ fixtures and JSON receipts; copy original receipts before a successor rerun. These controls assert frozen1d63 counterexamples, not desired successor behavior. A repaired source should invert the relevant negative assertions in a separate test.

The generated C++ files preserve the exact extracted actual function bodies and mocked provider schedules for inspection. Their SHA is bound in receipts. They are not replacement runtime source. The final manifest binds these durable review artifacts, while source-pins.json binds original runtime/provider inputs. A normal control plus deterministic forced schedule does not demonstrate that the forced overlap is reachable in a target guest.