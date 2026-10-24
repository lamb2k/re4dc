# Rain QA: reuse authenticated OFF, build one fresh ON

This is a source-only continuation of the reviewed V3 kit. It does not retry or resume the old partial ON build. A separate root grant is required before the first SDK command. No SDK, Make query, bootstrap, staging or guest ran during preparation or the 26 host controls.

The old pair receipt is preserved at `/dev/shm/rain8ce-qa-pair-v1-2ykw93ke/qa-pair-result-v1/receipt.json`, SHA256 `e0356a185a2dafe1368b66c5b6dedfa7b2bbd664f24c8f342019a081ca5dcf55`. OFF completed in 131.666984 seconds with raw programme `e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5` and all 14 expected overlays. ON was interrupted by the unchanged release-priority predicate. This is an incomplete pair, not a failed programme-identity check or a helper acceptance claim.

`OFF-REUSE-PREPARATION.json` records a new exact static readback using the unchanged reviewed postbuild reader: ELF, main raw programme, all overlays, actual 568 compile / 449 link-object QA graph, dependencies, resolved profile and SDK/input identities must equal the original completed OFF receipt and postbuild JSON. `CONTRACT.json` additionally pins all 17,461 files of both original trees and their failed result directory. Any old-root drift refuses continuation. The old partial ON is explicitly non-fresh and cannot be used as the new arm.

New ON root: `/dev/shm/rain8ce-qa-on-cont-v1-eyihqhpk`. Its source was freshly exported from exact source `8ce5ee2d00027268c3e69c9c300b819c1b14c63f`, with pinned sh4zam `33fa4850cacb30dd0ad35485ef035526ec4ce782`: 7,746 files / 100,403,427 bytes. It has no programme, object, output, build log or command file yet. Original source, reference QA programme, original input/provider/dependency pins and all reviewed V3 members remain mandatory. The ON command/environment changes only the old ON path prefix to this fresh root. QA ON changes only `RAIN_R10C_DC=1` and `RAIN_R10C_DIAG=1`; reviewed normal QA flags and GC defaults remain fixed.

## Execution boundary

Deployment is the immutable C: folder `codex-lanes/rain-diag24/qa-on-continuation-v1`, adjacent to the unchanged `qa-pair-prep-v3` folder. The Git copy protects generic source and hash-only metadata; it is not a second deployable kit and carries no private source export or old-root inventory.

`execute.sh` is byte-identical to reviewed V3. The controller reuses V3 common/controller/postbuild sources by authenticated bytes and direct `compile`/`exec`; it never imports adjacent bytecode. Its isolated static-read child pins both the sealed controller SHA and the sealed contract SHA. Parent resource observations, release-priority predicate, canonical lease, one-of-two shared slot acquisition and whole owned-process-group cleanup are unchanged.

One entirely fresh ON arm is allowed, JOBS=1, 600 seconds including preflight/build/postchecks. Admission requires the lower Windows/WSL C: free space >=26 GiB and ongoing >=24 GiB, plus min(tmpfs available, MemAvailable) >=3 GiB at admission and >=512 MiB ongoing. The 2 GiB logical owned cap includes the old OFF, old partial ON, old result directory, reviewed V3 kit/host root, new ON root and this continuation kit. At preparation the sum was 479,271,250 bytes. Each live observation recounts the current sum. No relaxation or automatic retry occurs if release priority or any floor/cap fails.

The exact canonical source tree must remain clean at 8ce. Lock: `/tmp/d367-build-7d1f56a1729c.lock`. Exactly one of `/root/probe/d367-build.lock` or `/root/probe/d367-build2.lock` is acquired after root grant validation. No second SDK slot, unrelated canonical tree or SDK build is requested.

Root must create a new approved grant from `ROOT-GRANT-TEMPLATE.json`, assign a unique grant ID, and pin this final `KIT-SEAL.json`. Reusing the old pair grant is refused. After independent review and explicit allocation, root alone may invoke:

```sh
RAIN8CE_QA_ROOT_GRANT=/absolute/new/root-grant.json \
RAIN8CE_QA_GRANT_SHA256=<new-grant-sha256> \
RAIN8CE_QA_ALLOCATED=<CONTRACT.json-sha256> \
/bin/bash -p '/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24/qa-on-continuation-v1/execute.sh'
```

Only that future execution acquires a lease/slot or invokes the SDK. It preserves a fresh `continuation-result-v1/receipt.json` and resource journal on success or failure. It reauthenticates whole OFF before ON, then builds fresh ON, runs the original SH4 objcopy/nm/size commands and unchanged QA postbuild checks. Completed metadata labels OFF as reused with its original duration and ON as fresh; no new OFF build or guest/heap/visual/physical acceptance is implied.

## Host controls and preservation

26 controls passed at controller SHA `7acb2ba8cb63e31b22abc5efc76462d65bfffb5d50617aa9409df9c4c42e908b`. They include actual old OFF static readback, actual old partial ON refusal, whole source/input checks, malformed grant controls, release/cap refusals, bytecode/source drift, actual wrapper pre-grant refusal, and mocked complete/failing one-arm orchestration. Mocked SDK requests are intercepted and run no tools. Public temporary fixtures remain in RAM; all original outputs and fresh ON source remain unchanged.

Repeat controls only to a fresh output file (do not overwrite the sealed result):

```sh
ulimit -v 262144
timeout 120s /usr/bin/python3 -I -S -B \
 '/mnt/c/Game Dev/Emulators/codex-lanes/rain-diag24/qa-on-continuation-v1/host_controls.py' \
 --controller-sha256 7acb2ba8cb63e31b22abc5efc76462d65bfffb5d50617aa9409df9c4c42e908b \
 --output /absolute/fresh/reviewer/HOST-CONTROLS.json
```

`prepare.py` was single-use and must not be rerun in this frozen kit. The preparation receipt predates the narrow reader-source/contract pin hardening; the final 26-control run freshly rechecked actual OFF and both old/new inputs at the final controller SHA. The predecessor kit and failure receipt remain immutable. This continuation is not authorized to stage media or run a guest.
