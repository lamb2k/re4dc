# Independent catalog review — 5ec379b02 BLOCKED

Frozen input: `5ec379b023a800a4e980108218b5242f4e2472ef`, parent `1d63cffe3a232c402418f2f2d919e7abae476957`. Source read from an immutable Git archive, never the mutable author tree. Author tree and origin branch were clean at this pin when checked. Runtime diff is exactly three files (disc/gate/index); two tracked test/doc files complete the unit. No reviewer runtime edits, SDK, target, guest, asset, catalog allowance, recipe or integration changes.

**Verdict: BLOCK this freeze.** The existing `test_runtime_index.RuntimeIndexTests.test_actual_disc_loader_and_texture_load_boundary` independently SIGABRTs because `re4dc_log` observes nonzero `io_depth`. Actual new `ensure_disc_catalog` keeps `Re4dcIoScope` alive when the missing-file branch calls unresolved. The failure is preserved in independent-existing-index.log/json. The second existing runtime-index method passes. Author independently reported the same broader-suite regression and is preparing a successor; passing focused controls do not clear this defect.

The same boundary needs examination for new read/contention/retirement paths: disc_failed calls retire_catalog, which invalidates epoch then immediately emits active-room unresolved diagnostics. A callback may invoke retirement while a read's I/O scope/guard is live. A successor must invalidate memory-only there and report via a safe drain. It must not silently erase a pending retirement fault at END, reset or new visit, and must preserve original visit attribution without migrating accepted prefixes. No global logger relaxation is acceptable. An inactive core-retire test does not exercise this logging edge.

## What independently passes

Original frozen test_catalog_defensive ran unchanged: six methods pass, including29 normal schedules, private seeded epoch exhaustion, six compiled SIGABRT mutants and absent/explicit0 parent/current stripped empty host-object identity. The original failure-body mutants compile before their expected runtime aborts. Read-only Git show in the tests resolves original object history through the archive's .git indirection; source code itself is the archive, not the author worktree. See focused-independent.log/json and run_focused.py.

Six additional actual-full-body wrapper schedules pass (actual-wrapper-policy-controls.cpp, independent-wrapper-policy.json, run_independent_wrapper.py):

1. During the disc ensure hash read, callback retires the core and installs a static replacement. Old install fails; wrapper disc_failed intentionally retires that replacement, leaves Failed and exact descriptor retained, repeated ensure does not reopen, and explicit safe retirement then fresh install succeeds.
2. During a Ready-state description read, callback core replacement survives; old description fails/clears output, old token is invalid, and the fresh replacement binds/describes as PS2.
3. Open failure is sticky with no descriptor, repeated ensure does not reopen, explicit retirement permits a fresh install.
4. Short total retains the exact descriptor until explicit safe retirement, then fresh install succeeds.
5. Seek failure invalidates the old token, clears failed description output, retains exact descriptor and refuses automatic reopen.
6. Negative read has the same sticky rejection/retry properties.

These controls did not assert logger I/O context; their green result is therefore limited and does not contradict the existing regression. All reviewer runs enforce RLIMIT_AS256MiB and one compiler job. Core dumps disabled. No claimed target scheduling, timing or SH4 programme identity.

## Source assessment and successor requirements

The complete seek/read DiscGuard prevents the former nested cursor substitution before another seek occurs. Contention invalidates authority instead of using another row. Retirement invalidates before attempting nonblocking close. Busy exactfd stays retained; returning old read does not auto-close/reset/reopen it. Explicit retry must acquire the guard, close successfully and enter FreshInstall, which is not Ready; failed close retains exactfd and Retired. Fresh pinned install is required before Ready. These states reject stale authority in the tested owner/callback schedules.

Core installation now uses local callback/extent/count/epoch, publishes only after full validation and generation check, and does not clear a successful callback replacement on an older core install failure. bind_checked returns only its captured current epoch. describe_checked clears output first, receives a temporary row and publishes only after generation/current-token recheck. Final18-bit epoch is an invalid permanent tombstone; retirement at the last admissible install cannot become indistinguishable or wrap authority.

**Important scope distinction:** preservation of a newer callback replacement is a core API guarantee in these schedules. The disc wrapper's failed own-service install deliberately invalidates all catalog authority, including such a replacement. This is failclosed, not stale positivity, but CATALOG24 documentation should state the distinction explicitly. Owner-only catalog API remains mandatory; nonblocking disc guard/atomics do not make plain core globals generally thread-safe. Current reachable dual-reader overlap remains unproved; original schedules are deterministic source counterexamples, not guest bugs. No terminal, Motion or full I001 acceptance follows.

Default gate absent/0 object checks establish empty stripped host identity for gate/disc. The modified index is included only within gate-enabled code. Actual target pricing, SH4 compilation/programme identity and current integration gates remain root-owned and unperformed by this reviewer. No resident catalog/digest table or allocation is introduced by this unit; changed state/local stack costs remain target-unpriced.

Before CLEAR of a successor: rerun protected-context logger assertions for missing file, short/negative seek/read, busy contention and active retirement during hash/header/rows/bind/describe; include retire/replacement and old-operation-abort schedules, END before pump and new-visit/reset attempts. Ensure pending explicit failure is retained and reported outside I/O/guard/protected callbacks; accepted prefix and saved token provenance must remain failclosed. Re-run the focused/mutant/OFF controls and the previously failing existing runtime-index test. Preserve this freeze and its failure as history.