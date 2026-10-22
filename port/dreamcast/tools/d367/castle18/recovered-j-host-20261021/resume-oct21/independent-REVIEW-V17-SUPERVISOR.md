# V17 / watcher v2 follow-up

Read-only review; AST parsing only, no execution or guest. `v17-v2-static-identity.json` pins the exact three inspected files. Controller SHA-256 is `9e1f3ed9d2f93d3c1f4a5d389a1572d93ad3bf5e6a0261f0b3f8c201ce43511b`; watcher v2 is `01115ee17a2c8aeaae9b3e60df07e57ba74308c99ede4669ba3a82693040015f`; runner v2 is `4444d2da2dc3c3ad3155011fd92cf4f6d5cea81831c920ea4c95192169fbc0c2`.

The revised exception cleanup, retained watcher lifetime, verified-exit receipt and return-status checks address the initial ownership/status failure paths. The controller anchors process age once and advances it monotonically; active reads poll its identity/deadline check. At 40.5 seconds it posts releases for tracked owned inputs and clears active state before raising, so subsequent identity checks remain usable for cleanup. This is a sensible margin; guest qualification and fault tests are separate.

One absolute-deadline blocker remains in watcher v2. It still performs synchronous `disk_usage`, recursive enumeration and `stat` between age checks. Checking before and after does not bound time spent inside the sampler. For example, a filesystem sampler beginning at process age 44.9 and stalling for three seconds cannot perform its next termination decision before age 47.9. This exceeds the claimed 47.5-second absolute bound even though the pre/post checks are present.

Add that slow-sampler case to fault testing. Keep filesystem work independent of the pure deadline/ownership loop, using a bounded asynchronous sampler or a separate authenticated deadline supervisor. Per-entry deadline checks bound enumeration progress but do not bound one blocked filesystem call. Retain exact PID/path/creation identity and exception-safe cleanup. No request to expand any time, disk, capture or guest limit is implied.

No further NameError or stage-dispatch issue was identified under this static review. Castle21 retains controller/supervisor changes, fault testing, execution and current authentic lineage.
