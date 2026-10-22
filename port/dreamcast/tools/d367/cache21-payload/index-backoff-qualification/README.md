# Main per-sector index retry candidate: source-host qualification

This separate namespace tests main's default-off per-sector backoff candidate. The unchanged baseline failing proof remains at `../index-backoff/`, sealed in1512350a49f8e8d605aea60a057b156dc06fec46. This worker changed tests/docs only. Main owns `texpack_index.inc`, architecture, SH4 identity checks and integration.

Qualified index SHA256: `bf95fea5f7bc4881fe438b7c57baea7dc086b34a059573185d6fea8170e02c1d` (14013bytes), captured from main's worktree parented at `edfe8f1765fbbd418235537e7b2f0b3b6aeab25d`. Frozen payload helper SHA256 `915601b92d8a9d10d763a377da6680c1579d39ad9109a1750f402fa3f8ed8f38`. The candidate adds two bitmap words plus64 deadlines under the existing guard and uses existing locked find/reset paths. A cleared bit makes a stored old deadline irrelevant. Tests copy the exact source before compiling it unchanged.

## Results

**3122 assertions OFF and10640 ON pass under UBSan** using the final `probe.cpp` and `run.py`. With two failed sectors A/B and healthy H over30frames:

| Guard | A read_file_range calls | B calls | H calls | Error logs |
| --- | ---: | ---: | ---: | ---: |
| OFF, retained original behavior |30|30|30|60|
| ON, candidate |1|1|1|2|

The table compares injected I/O failures and first-key mismatch refusal in both arms. ON also gives1/1/1 calls and2logs for enabled CRC-only refusal and mixed I/O/CRC. The same-frame A,B,A minimal case is OFF3calls/ON2calls. The original single-failure control remains one failed A call and one healthy H call over30frames in either arm. The guard-OFF non-first-row corruption control remains90 successful lookup reads with0errors because the optional sector CRC is disabled; no default-path integrity adoption is inferred.

New controls exercise:

- Every sector0..63 of a synthetically valid8192-member sorted index:64 failures, no extra reads before deadline,64 successful recoveries at the deadline, and each individual failure bit clears.
- Distinct31/32 bitmap words, independently staggered30-frame deadlines, and staggered deadlines spanning UINT wrap.
- Room reset clears all64 failure bits while leaving old deadline words stored; all64 sectors immediately recover despite those stale values.
- Full validated index re-publication clears all64 old failure bits and advances the existing payload epoch.
- Healthy sector2 remains admitted among63 failed sectors; repeating held failures and healthy lookups adds no reader calls and never creates an all-sector healthy gate.
- Largest8192-member index and ordinal8191 admitted; ordinal8192 rejected by the existing public payload gate;8193-member header refused before an index lookup.
- Failed attempted reads invalidate the sole sector buffer; held errors can retain a different valid cached sector. Failure outputs do not publish offsets/sizes/ordinals. This is not a stale-buffer fix.

The actual6501-member original sorted index is used for the initial alternating-failure tests; fresh prefix/virtual-size identities remain in `receipt.json`. The synthetic64-sector cap test allocates only its header/index, with virtual package extents and no package payload allocation/read. The source still validates its whole index before injection.

## Existing controls retained separately

`existing_suite.py` compiles the original policy, load, index and combined find/load fixtures against the exact same captured candidate index. All pass:

- 21,898 payload-policy assertions, unchanged31..60 UI-frame retry delay and2048-byte member maps.
- Actual extracted loader controls OFF/ON, including refusal/recovery and existing healthy/loose-path cases.
- Existing complete index suite OFF/ON: initialization spacing, header/index validation, absent/invalid media, room reset, frame wrap, cap and enabled ordinal/CRC controls.
- Combined find/load fixture still makes **60 index reads /122880 mocked index bytes in both arms**, payload opens60OFF/3ON,60healthy resident hits and3healthy first opens. That distinct healthy-index repeated-work limitation is unchanged.
- Reset after find, during open, new index publication, late success and epoch exhaustion controls pass. No broader cache/TA/owner lifetime closure is established.

`existing-regressions.json` binds those commands/source hashes/outputs. This unit supplements the earlier receipts and does not replace their observations.

## Evidence and scope

Private candidate: `C:/Flycast-Evidence/re4-dreamcast/cache21-payload-20261021/index-backoff-root-host-v1/receipt.json`, SHA256 `4b2c65ef8ddf502cb714e9081077670248b5aede557626e36468b2abfbd673c0`.

Private existing controls: sibling `index-backoff-root-regressions-v1/receipt.json`, SHA256 `cb3d2e856c37bfed076d8ce8e2d245765aa468a9104a5f8307eaa7f7261d7bd1`.

The two output namespaces total about1.7MB before receipts. Each compilation uses the shared buildslot, fresh18GiB+128MiB start and18GiB+64MiB runtime floors, exact owned PID/process-group identity,55-second and1MiB log limits, and20MiB output cap. Original failing receipts remain preserved in their own namespace.

All counters above are synthetic **read_file_range invocations**, not measured KOS low-level requests, drive transactions or actual transferred bytes. No normal-media occurrence, total-I/O/target performance improvement, SH4/object identity, full program, Flycast, release check or physical Dreamcast acceptance follows from these host tests. Main qualifies target object identity independently. No runtime/shared files, production recipes, staged assets or SD content were changed by this worker. The negative menu-window candidate remains disabled.

## Commands

```sh
python3 run.py --source /root/probe/codex-cache21-integration-next \
  --ref edfe8f1765fbbd418235537e7b2f0b3b6aeab25d \
  --working-index /root/probe/codex-cache21-integration-next/port/dreamcast/game/platform/include/texpack_index.inc \
  --pack /root/re4data/private/mipmap21-release21-pack-recovery-20261021/tex.pak \
  --out /path/to/fresh-candidate-output

python3 existing_suite.py --source /root/probe/codex-cache21-integration-next \
  --ref edfe8f1765fbbd418235537e7b2f0b3b6aeab25d \
  --snapshot /path/to/fresh-candidate-output --out /path/to/fresh-existing-output
```
