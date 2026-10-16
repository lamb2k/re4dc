# D367 OTHER accounting tools

These tools inspect retained hardware-model traces. They do not change a game
build, its assets, or console benchmark results.

```sh
O=port/dreamcast/tools/d367/other
E=/absolute/path/to/completed/hwmodel-run
A=/absolute/path/to/new/audit-directory
python3 "$O/build_frame_sim.py" --out "$A/simulator"
python3 "$O/replay.py" "$E" --out "$A/replay" \
  --simulator "$A/simulator/hwsim_cg_frames"
python3 "$O/account.py" "$E" --out "$A/account" --cg-dir "$A/replay" \
  --label 'build, scene, window, stride, and pacing mode'
python3 "$O/partition.py" --evidence "$E" --replay "$A/replay" \
  --account "$A/account" --out "$A/partition"
```

To qualify the instrumented simulator against an earlier unmodified replay:

```sh
python3 "$O/verify_replay.py" --original /path/to/original-replay \
  --exported "$A/replay" --out "$A/exporter-validation.json"
```

This verifies byte identity of the frame totals, per-PC counters and aggregate
call tree, and checks the raw-entry scanner against instruction/memory-event and
truncated-record fixtures.

Preserve the raw `trace-*.bin` files before the ordinary call-tree cleanup:
`ACTORPLAN_KEEP_TRACES=1` or `trace/keep.txt` is supported by the current CPU lane.
Replay does not delete or modify source evidence. It refuses to overwrite an
existing replay. `--prepare-only` resolves the ELF's watch symbols and records
the command without running it. `--summarize-only` rebuilds summaries from an
existing replay. The raw entry scanner is compiled with the local `cc` compiler.

`build_frame_sim.py` reads the existing nominal call-tree simulator source and
builds a separate copy in the output directory. The copied source and hashes are
retained. It exports per-frame call-node deltas and per-function PC charges while
preserving the original instruction model and complete trace order. Baseline
qualification compares `cgsim.frames.tsv`, `cgsim.pcs.tsv` and `cg.cg.tsv` against
the original simulator; these must remain byte-identical.

`replay.py` writes:

- `watch_names.tsv`, `command.json`, `inputs.txt`: exact replay inputs.
- `events.tsv`: watched completed calls, in return order; timings are inclusive.
  Do not add nested events together. Thread-stack reconstruction can lose returns;
  an absent completed return does not mean an absent call.
- `main_windows.tsv`: main-loop entry windows, including `TaskScheduler`,
  `Trans`, `Render`, and `iTaskScheduler`. These entries do not nest in the game
  loop. Incomplete return coverage produces a blank timing, never zero. Even
  matched entry/return counts are reconstructed spans, not exact benchmark phases.
- `raw_entries.tsv`: actual execution counts of watched entry PCs, independent
  of reconstructed calls. The scanner reads instruction-run records and ignores
  memory-event records.
- `trace_groups.tsv` and `drawn_image.txt` / `dropped_image.txt` /
  `ambiguous_image.txt`: drawn requires one `re4dc_ui_begin`, zero
  `re4dc_ui_begin_skip`, and a world draw entry; dropped requires the opposite
  begin calls and zero world draws. Other combinations remain ambiguous. These
  predicates apply to the fixed cross fixture, not arbitrary rooms or movies.
- Standard `cg.cg.tsv`, `cg.syms.txt` and `cgsim.frames.tsv` for self accounting.
- `cg.self_frames.tsv` and `cg.function_frames.tsv`: per-frame call-node self
  deltas and flat function PC charges from the isolated simulator.

The trace starts when `Frame_cnt` advances. Its prefix contains logic/preparation
N followed by Render_done/swap for N-1; its suffix starts at pace_begin and
contains the next loop's Render N. A console benchmark physical iteration instead
contains Render N-1 followed by logic/preparation N. Do not label a trace group's costs as
the console's drawn or skipped tick cost. A forced two-tick image-period cost can
be reconstructed from the two group means, with the sampling limitation stated.
Forced pacing also runs `iTaskScheduler` every iteration; production skip policy
can omit it. Report that cost separately.

For a verified forced-alternating fixture, add `--phase-config CONFIG.json` to
`replay.py`, then run:

```sh
python3 "$O/phases.py" --replay "$A/replay" --account "$A/account" \
  --out "$A/phases" --forced-alternating
```

The config must contain the exact `elf_sha256` and an `environment` object with
seven hexadecimal addresses: `OTHER_SEGMENT_ENTRY`, `OTHER_WAIT_LOOP_START`,
`OTHER_WAIT_LOOP_END`, `OTHER_WAIT_FUNC_START`, `OTHER_WAIT_FUNC_END`,
`OTHER_WAIT_CALL_PC`, and `OTHER_WAIT_RETURN_PC`. Audit them from the exact ELF's
disassembly. Ranges are half-open. The current recipe uses pace_begin as the
boundary, the pace_end polling loop as WAIT_LOOP, and vi_retrace_count's executed
instructions as WAIT_FUNC. Do not reuse addresses for another ELF. Replay checks
the SHA before running and stores the config with its outputs.

The exporter adds `cg.function_segments.tsv`, `cg.segment_counts.tsv`, and
`cg.wait_segments.tsv`. The last file distinguishes loop PCs, retrace instructions
reached from the loop's call site, and other retrace callers. It preserves each
charged PC's call context so delayed branch stalls keep the correct ownership.
The trace boundary must not start inside the watched callee. Bookkeeping, other
retrace callers, interrupts and unidentified waits are not subtracted.

`phases.py` requires one actual boundary per trace and exact reconciliation of
function segments and retrace caller shares. For forced alternation, physical
draw means combine drawn-image suffix with dropped-image prefix; physical skip
means combine dropped-image suffix with drawn-image prefix. These are population
means from separate samples, never adjacent measured tick pairs. They remain
nominal model values. The prefix of a physical skip prepares the next visible
image, so its preparation work is not automatically redundant.

Use `partition.py` to split the per-frame exports. Do not replay only a subgroup
to estimate its share of the original run: that changes the model's cache/timing
history. `--trace-list` remains available for explicit standalone diagnostics,
but such a replay is a new model run, not an exact partition.

`account.py` assigns every flat function row and every call-tree self node exactly
once, including unknown/root costs and waits. It checks the flat sums against
frame totals within the source report's four-decimal rounding bound and checks
call-tree self cycles against their frame totals within one CPU cycle. The
`account.py`'s `flat_*` outputs always describe the full evidence run; `call_*`
outputs describe the chosen `--cg-dir`, whose sample list/count are recorded.
`partition.py`'s `flat_functions.tsv` and `flat_categories.tsv` contain subgroup
PC self costs independent of reconstructed returns. Its `functions.tsv`,
`callers.tsv`, and `ownership.tsv` contain reconstructed call-node self costs;
tail calls may remain attached to the prior call node. Check the watch coverage.

Flat `wi_console` means the calibrated model projection, not a console timing.
The exports use the nominal 200 MHz model. Partition group totals also read the
original calibrated `console.frames.tsv`, while subgroup function costs remain
nominal. Never scale caller costs by a flat projection ratio, or mix inclusive
watch windows with self costs.

The category `pacing, retrace and idle routines` includes bookkeeping. Only the
narrow `phases.py` polling counters isolate the audited loop; do not subtract the
entire category as idle time. Polling includes the final successful condition
check, and is a diagnostic cost, not an accepted optimization saving.

Function categories describe implementation. The ownership report uses known
call ancestors and explicitly retains unresolved contexts. An ordinary t15
model build lacks benchmark phase markers; some preparation is inlined, source
model callbacks do not identify EmMgr membership in the exported call tree, and
game tasks switch KOS threads. Consequently these reports cannot reproduce the
console benchmark's exact OTHER phase. Console interrupts and other threads are
charged to the phase they interrupt, not universally to OTHER.


## Default-off benchmark ownership diagnostic

`OTHER_PROFILE=1` adds trace-visible NOP markers at the historical `76f40d95`
BENCH_PH boundaries and its guarded two-snapshot EmMgr membership rule. It does
not import unrelated benchmark behavior. The disabled arm must first pass
loadable-image and `_end` identity against its intended reference. The enabled
arm changes code layout and BSS; record those changes and matched-frame heap,
camera, simulation and geometry counters before interpreting its trace.

```sh
python3 "$O/replay.py" "$E" --out "$A/benchmark-original"
python3 "$O/replay.py" "$E" --out "$A/benchmark-replay" \
  --simulator "$A/simulator/hwsim_cg_frames" --benchmark-phases
python3 "$O/verify_replay.py" --original "$A/benchmark-original" \
  --exported "$A/benchmark-replay" --out "$A/benchmark-validation.json"
python3 "$O/bench_phases.py" --evidence "$E" --replay "$A/benchmark-replay" \
  --out "$A/benchmark-phases"
```

The phase exporter uses 0 logic, 1 preparation, 2 actor draw, 3 world draw,
4 OTHER and 5 wait tail. Phase 6 is diagnostic instrumentation. It resolves
marker PCs from the exact ELF, rejects incomplete marker sets and excludes marker
aliases from the function map. Traces must begin at the established Frame_cnt
cut, in phase4 before phase0; actor and instrumentation stacks start empty there.
The report verifies balanced stacks and one main logic/wait-tail marker per
sample. Deferred charges retain the phase of the charged instruction.

`bench_phases.py` reports every phase's disjoint function self costs and separately
lists OTHER's functions and categories. Its forced draw/drop group means are
sampled image groups, not physical-iteration labels or adjacent measured pairs.
It neither scales costs to the old console15.8 ms result nor claims a production
gain. Markers and bracketed snapshot/check work are isolated, but incidental
register/stack, cache and code-placement effects remain in this diagnostic build.
Qualify the exporter on this exact trace: the frame, PC and call-tree output must
remain byte-identical to the original host model. Keep hardware acceptance separate.
