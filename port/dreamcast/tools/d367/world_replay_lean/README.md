# World replay lean controls

This lane qualifies `SCENERY_REPLAY_LEAN` against integration commit
`451bed6faa2c37f7f9aa05d6fb1116ec64219ebc`. The runtime starts from that commit,
including its independent SELECT_ONLY and SUBMIT_BATCH changes. The default is
zero. See [the report](../../../docs/D367_WORLD_REPLAY_LEAN_20261023.md) and its
[condensed receipts](../../../docs/D367_WORLD_REPLAY_LEAN_20261023.json).

## Reproduce

Run from the repository root with Python 3, host GCC/G++, GNU Make and `patch`,
the SH GCC 15.2.0 Dreamcast toolchain, the pinned KOS source, and the public SDK
headers used by the preceding Test 22 spikes. Each output directory must be new.
No game assets are required for these synthetic controls.

```sh
REPLAY_TOOLS=port/dreamcast/tools/d367/world_replay_lean
REPLAY_OUT=/tmp/re4dc-replay-lean-check
REPLAY_CXX=/path/to/sh-elf/bin/sh-elf-g++
REPLAY_KOS=/path/to/KallistiOS
REPLAY_SDK=/path/to/public-sdk

python3 "$REPLAY_TOOLS/build_controls.py" \
  --output "$REPLAY_OUT/production" --sh4-cxx "$REPLAY_CXX" \
  --kos-root "$REPLAY_KOS" --sdk-root "$REPLAY_SDK"
python3 "$REPLAY_TOOLS/verify_knobs.py" \
  --profile "$REPLAY_OUT/production/build-controls.json" \
  --output "$REPLAY_OUT/knobs"
python3 "$REPLAY_TOOLS/check_runtime.py" --output "$REPLAY_OUT/boundary"
python3 "$REPLAY_TOOLS/check_admission.py" --output "$REPLAY_OUT/admission"
python3 "$REPLAY_TOOLS/check_geometry.py" --output "$REPLAY_OUT/geometry"
python3 "$REPLAY_TOOLS/selection_controls.py" --output "$REPLAY_OUT/selection"

python3 "$REPLAY_TOOLS/target_build.py" \
  --output "$REPLAY_OUT/target" --sh4-cxx "$REPLAY_CXX" \
  --kos-root "$REPLAY_KOS" --sdk-root "$REPLAY_SDK" --batch-matrix
python3 "$REPLAY_TOOLS/target_run.py" \
  --build "$REPLAY_OUT/target/target-build-controls.json" \
  --output "$REPLAY_OUT/measure"
python3 "$REPLAY_TOOLS/measure_summary.py" \
  --target-controls "$REPLAY_OUT/measure/target-controls.json" \
  --output "$REPLAY_OUT/measure/summary.json" \
  --pieces 500 --batch-size 48 --mhz 200 --frame-ms 49.3
python3 "$REPLAY_TOOLS/measure_clear_audit.py" \
  --production "$REPLAY_OUT/production" \
  --target-build "$REPLAY_OUT/target/target-build-controls.json" \
  --objdump "${REPLAY_CXX%g++}objdump" \
  --output "$REPLAY_OUT/measure/production-clear-audit.json"
```

`build_controls.py` expands the actual Make recipes separately for
`native_static` and `native_ui`, using the public Test 22 configuration from
`world_submit_spike/build_profile.py` and `world_setup_spike/release_profile.py`.
It compares complete preprocessed translation units and complete objects for
baseline, knob absent and explicit zero, for all four SELECT_ONLY/SUBMIT_BATCH
pairs. Debug records and preprocessor line markers are omitted consistently;
source line numbers are not executable differences. Baseline quote includes
are restored from Git independently. The enabled arm supplies production
section sizes and compiler stack frames. It does not link a release image or
run its memory gates.

## What the controls execute

| Tool | Scope |
|---|---|
| `verify_knobs.py` | Make expansion for all eight switch combinations, default absence, invalid values and dependency guards |
| `check_runtime.py` | Actual UI ownership, bind/end, replay/reset and failure boundaries with controlled geometry |
| `check_admission.py` | Actual selection-only admission, ordinary setup, capacity drains and snapshots; visibility/emission edges are controlled, including PVS state |
| `check_geometry.py` | Production replay, borrow, gather, emit, clip and portable transform bodies on validated synthetic R4IM v1/v3 packages; every TA/accounting word compared |
| `selection_controls.py` | Existing numeric inside/partial selection and helper-call counters, plus bitwise screen memo keys and reloads |
| `target_run.py` | Actual compiled SH-4 setup/selector/memo instructions with an observed geometry edge and explicit external entry/return stubs |
| `measure_clear_audit.py` | Production and fixture assembly evidence for the constructor clears and their loop placement |

The geometry control uses host floating-point transformation and a C adapter
for the SH-4 SQ-only walk. It asserts source identity for unchanged production
geometry bodies; it does not execute hardware FTRV/FSRRA or a recorded room.
The texture-acquire control deliberately clobbers the matrix. Another control
allows the first piece to emit and then makes the second piece's scratch slab
too small, checking that emitter reuse revalidates the borrow.

The target fixture retains the full `MeshDraw` layout and actual replay code.
Only `emit_pick` is replaced with an observed, state-poisoning geometry edge.
The actual `load_screen` body runs; its `mat_load` boundary captures all 64
bytes while excluding the unchanged hardware transfer. UI submission and
geometry costs are excluded. Unsupported instructions, unmapped accesses and
unreviewed external calls fail closed. Production object sizes come from the
separate complete-TU gate, not this fixture.

## Model and traffic definitions

The existing `hwmodel/hwsim.c` prices retired target instruction traces.
Warm I means ideal instruction residency; cold I starts an empty 8 KB cache
once per complete fixture sequence. Both assume perfect D-cache and omit
unrelated memory-bus contention, SQ transfer, DMA and interrupt costs. Cold results
depend on the synthetic ELF layout. Neither result is a Flycast or console
measurement.

`memory_trace.py` counts architectural data loads/stores and bytes, including
stack traffic, PC-relative literals and helper library accesses. Instruction
fetches are excluded. Eight-byte moves count as one instruction. Cached,
uncached and SQ accesses are separate; PREF requests are not demand loads.
Bounded opcode controls check these distinctions and delay-slot attribution.

For replay, **per-piece line touches** are the sum of distinct cached 32-byte
lines between consecutive geometry edges, with prologue and exit apportioned
over the run. A line touched in several intervals is counted several times.
The **whole-run unique footprint** is a separate address union; it is not
divided by the piece count and described as per-piece footprint. Neither
quantity measures cache misses, cache fills or external memory traffic.

The frame projection uses ten 48-piece queues plus one 20-piece queue, one
memo call per piece, and explicit memo-hit scenarios. It credits only this
change. It assumes all 500 pieces qualify and all other work stays fixed;
queue occupancy, eligibility and memo-hit rate need scene measurements.

## Test-tool provenance

The integration base already includes the setup/submit fixture generators,
public profile and SH-4 strip interpreter. The narrowly copied scalar and
pipeline helper modules identify their original test-only commit in their
headers; this repairs a missing helper dependency after the two spikes were
cherry-picked without their earlier parent. No renderer code, certificate
path, PR #56 ancestry, or game assets are imported from that parent.

The additional interpreter operations are scalar operations used by the
compiled setup and newlib routines. There is no FTRV/FSRRA emulation. The
separate host geometry and complete production build gates establish the
other parts of the evidence.
