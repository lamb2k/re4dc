# Exact ce034 recovery from retained bea

Source-only executor; no real recovery has run in this unit. Expected input is retained bea `046d03de7f092e7582e0f4cba0b5303bf4f99c3009aaa4ff625a2099ea8a9536`; expected restored image is `ce034ff75d5c6eb125a5036b5c55afa1805de1beac75711cd41b73f366d854ad`, exactly1,028,911,104B. Main must independently review and freshly admit execution.

Old/new small media receipts prove identical16 append LBAs/padded extents, original32 point tuples, fixture redirects, private room9338 bytes and total image length. The only directory-field differences are two RAW size entries: old3440040B versus new3439784B. All14 old overlays and old RAW remain available at receipt-bound paths. Source preparation reads JSON and stats only; it never opens an ISO or payload.

Execution copies bea read-only into ONE exclusive `.track03.recover-ce034.tmp` under the old actor/base directory, verifying the entire copied input SHA. It validates32 point preimages, unchanged descriptor lengths and room payload; writes the exact14 old overlays and old RAW with zero sector padding; writes all32 old16-byte point tuples; truncates to the exact target size; fsyncs and hashes the entire physical candidate. Only exactce034 may be published via an exclusive atomic hardlink to absent `track03.iso`, followed by removal of this executor's own temporary name. Both names briefly share one inode, not a second ISO allocation. Existing target/temp/receipt refuses a retry. Wrong hashes retain an unpublished candidate and diagnostic receipt. An error after link publication records target existence and remains failed until main diagnoses it.

No remaster, native-base materialization, extraction, ELF rewrite, deletion of any existing evidence or image, guest or source-media mutation. Existing ce sidecar and all other base members/receipts/logs/screenshots remain untouched. Full target SHA is the acceptance gate; no earlier source/model inference establishes restoration.

Run the miniature controls in WSL using `python3 -B test_recover.py`. They allocate only tiny disposable8KiB examples and test the actual copy/patch/hash engine, wrong source/target/payload/preimage/room/descriptor, bounds, stale/cap admission, source replacement, and atomic no-clobber publication. The actual-plan control reads JSON only. `make_plan.py` reconstructs the pinned local PLAN.json from retained small metadata and payload stats; preserve an existing plan rather than rerun it. It is committed source, while private PLAN/receipts stay local.

Default `python3 -B recover.py` prints the source plan identity and performs no recovery. Main's later admitted invocation is:

```
python3 -B /mnt/c/Game\ Dev/Emulators/codex-lanes/world-scratch23/recovery-actor-ce034-r2/recover.py --execute \
  --plan /mnt/c/Game\ Dev/Emulators/codex-lanes/world-scratch23/recovery-actor-ce034-r2/PLAN.json \
  --source-seal-sha256 SEALED_UNIT_SHA \
  --review REVIEW_JSON --review-sha256 REVIEW_SHA \
  --root-admission FRESH_ROOT_JSON --root-admission-sha256 ROOT_SHA
```

Review must contain `status:"CLEAR"` and `recovery_source_seal_sha256` equal to the exact local SOURCE-SEAL.json SHA. Executor validates all sealed files before image access. Admission must be<=60s old, cover the evidence tree, and reserve exactly oneISO+256KiB metadata under16GiB root/3,758,096,384B package caps,20,468,203,520B Cfloor plus60MiB guest reserve. Current free disk and remaining copy reserve are guarded during I/O. No internal census is performed. Both original actor tree lease and shared package lease are acquired nonblocking before validation/copy. Main owns concurrent resource admission and any later disposition of a failed candidate. Recovery receipt is new `oldactor/base/recovery-ce034-result.json`; no old receipt is overwritten.

Successor r2 preserves old seal a224 untouched. Publication now binds the physical-hash writer content stamp (device/inode/size/mtime), checks canonical literal-parent device/inode against the held directory before/after link, checks both literal TARGET and fd-relative TARGET against that verified writer, and stats the owned temporary via dirfd before its only unlink. Parent/target/temp substitution fails while preserving all names; a final literal check also precedes EXACT success. Hardlink ctime/link-count changes are expected, so content stamp excludes those fields. Package admission now also reserves the standing60MiB future guest, in addition to the root/Cfloor reserve. Exact current example2,662,713,861+1,028,911,104+262,144+62,914,560=3,754,801,669 fits package cap by3,294,715B.
