# Animation sampling evidence

The lane report is
[BUILD8_ANIM_SAMPLE_LEAN_20261024.md](../../../docs/cloud/BUILD8_ANIM_SAMPLE_LEAN_20261024.md).
These tools require the existing public Make inputs, SH4 GCC/KOS headers, and
the repository's existing SH4 trace/pipeline model. They use no game data or
Flycast. Shared dependencies outside this directory are already present at base
`d5c1ceab`. Host differential checks also require a C++17 compiler; the sanitizer
mode uses its AddressSanitizer and UndefinedBehaviorSanitizer support.

## Published receipts

| Receipt | What it establishes |
|---|---|
| `build_receipt.json` | Independent archived-base identity: seven Make profiles, 28 absent/zero comparisons and six inactive-ON comparisons; complete production object sizes and relevant static stacks. |
| `sampler_receipt.json` | 138 paired executions of complete production sampler entries, including three formats, four key counts, exact/interval/wrap/clamp/history/error paths. |
| `pose_receipt.json` | 28 complete compiled `MotionMoveCore` cases plus two cases using the usual 10.6 `Seq.frame` path; all nine sampler call sites execute. |
| `traffic_receipt.json` | Selected per-axis and per-region demand traffic, separating key payload from parameters, history, stack and literals. Raw coverage is 39 sampler and 28 pose cases. |
| `runtime_receipt.json` | The separate host source/caller equivalence suite; see `check_runtime.py` for its format and qualification. |
| `rejected_lazy_decode_receipt.json` | Rejected source-level load deletion: compiler had already eliminated the work. The exact patch is retained. |
| `per_call_clamp_probe.json` | Rejected per-call admission placement: ordinary-call overhead before admission moved to once per pose. |

The raw receipts are hashed by the published compact receipts. They retain
full commands/model metadata and sampler output words; pose snapshots are
compared in memory and summarized by paired hashes. The compact copies retain
each case's paired hashes and principal metrics. The publisher checks that
the production objects used for target execution have the same hashes as the
independently compared build-control objects.

## Reproduce

Run from the repository root. Use fresh output directories; the builders fail
if their destination already exists. Set `task_cxx`, `task_kos`, `task_sdk` and
`task_evidence_dir` to your local paths. `task_sdk` supplies the normal SH4ZAM
headers; it does not select a different source checkout.

```sh
task_tools=port/dreamcast/tools/d367/anim_sample_lean
python3 "$task_tools/build_controls.py" --output "$task_evidence_dir/build" \
  --sh4-cxx "$task_cxx" --kos-root "$task_kos" --sdk-root "$task_sdk"
python3 "$task_tools/check_runtime.py" \
  --profile "$task_evidence_dir/build/absent-profile/motion-profile.json" \
  --output "$task_evidence_dir/runtime" --mode all
python3 "$task_tools/check_runtime.py" \
  --profile "$task_evidence_dir/build/absent-profile/motion-profile.json" \
  --output "$task_evidence_dir/runtime-sanitizer" --mode sanitizer
python3 "$task_tools/check_runtime.py" \
  --profile "$task_evidence_dir/build/absent-profile/motion-profile.json" \
  --output "$task_evidence_dir/runtime-negative" --mode negative
python3 "$task_tools/target_build.py" --output "$task_evidence_dir/target" \
  --sh4-cxx "$task_cxx" --kos-root "$task_kos" --sdk-root "$task_sdk"
python3 "$task_tools/target_run.py" \
  --build "$task_evidence_dir/target/target-build-controls.json" \
  --output "$task_evidence_dir/sampler"
python3 "$task_tools/pose_run.py" \
  --build "$task_evidence_dir/target/target-build-controls.json" \
  --output "$task_evidence_dir/pose"
python3 "$task_tools/sequence_run.py" \
  --build "$task_evidence_dir/target/target-build-controls.json" \
  --output "$task_evidence_dir/sequence"
python3 "$task_tools/traffic_regions.py" \
  --build "$task_evidence_dir/target/target-build-controls.json" \
  --output "$task_evidence_dir/traffic.json"
python3 "$task_tools/publish_receipts.py" \
  --build-controls "$task_evidence_dir/build/build-controls.json" \
  --target-build "$task_evidence_dir/target/target-build-controls.json" \
  --sampler-controls "$task_evidence_dir/sampler/target-controls.json" \
  --pose-controls "$task_evidence_dir/pose/pose-controls.json" \
  --sequence-controls "$task_evidence_dir/sequence/pose-controls.json" \
  --traffic-controls "$task_evidence_dir/traffic.json" \
  --output "$task_evidence_dir/published"
```

The three `check_runtime.py` commands write separate raw receipts. The checked-in
`runtime_receipt.json` summarizes their totals and hashes; the publisher command
above compacts the build and target-execution receipts.

`build_profile.py` expands the actual R21/Test22 Make recipe, current literal
CH2 assignments and public asset fallbacks for `src/game/motion.o`. The matrix
is public REG1, REG0, REG2, FAST2, no-prefetch, reference, and HF_ASM1. Debug
records are consistently omitted. Generated headers and effective OFF flags
are compared between the independent base and current source. The target
fixture uses the REG1 public profile.
The HF_ASM1 profile checks C++ compilation and OFF identity. Its host runtime
adapter calls the original C sampler; these checks do not execute or qualify
the actual HF_ASM kernel.

## Interpretation limits

`target_build.py` compiles the **complete production translation unit** and
links its retained functions into an evidence-only ELF. It does not reconstruct
the sampler or change the game linker. The resulting ELF executes in the
existing fail-closed scalar opcode interpreter. The only extra pose opcode is
a bounded camera-frame `FTRC` for finite inputs in `(-1,256)`, qualified by seven
small conversion controls. Scalar binary32 arithmetic is RN with DN enabled;
synthetic data avoids exceptional/denormal boundaries. This is not a claim of
general target floating-point or exception-status conformance.

The sampler probe enters actual `HermiteInterpolation`, or the private entry
for a frame already qualified for clamping. Admission cost belongs to the
complete pose probe. The two rejected candidate probes used a small
`fixture_sample` wrapper with extra global argument loads. Their baselines
must not be compared with the final direct-entry baseline; compare paired
arms within a receipt.

The pose probe executes the actual `MotionMoveCore` frame setup, per-pose
admission, lookup dispatch, all nine sample sites, histories and samplers.
Resident-key acquisition, model lookup, logging and unchanged angle/matrix
helpers are explicit typed fixture adapters. Their small adapter instruction
costs remain in both totals. The original I/O, lookup and math implementation
costs are excluded. The existing matrix-skip flag is set; `VecRadLimit` is a
no-op adapter on these bounded values. The fixture is not a general pose-math
oracle and does not include sequence advancement, hokan, IK or animation
outside `MotionMoveCore`.

Cycles are **model estimates** with perfect D-cache, no DMA and zero store-queue
cost. Warm prices use perfect I-cache; cold prices begin with the model's 8 KB
I-cache cold once per entire call/pose, at the synthetic ELF layout. Final
pipeline drain is not included. Do not multiply cold per-sample costs to obtain
a cold pose cost. Demand bytes/lines come from executed loads/stores; literals
are data loads, opcode fetches are excluded, and PREF requests are separate.
Lines are address-touch counts, not inferred fills, cache misses or bus traffic.
Adjacent traffic regions can share a line, so their line counts are not additive.

There is no captured animation census. Whole-frame estimates must be conditional
on actual sampled vectors/poses and the clamped share; world-part counts do not
supply that population.
