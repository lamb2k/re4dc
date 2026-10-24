# Build 5 controls

`SCENERY_EMIT_PREFETCH`, base `dc87c4658d65ba992d266e3cb1893ecd485da661`.
See [the report](../../../docs/cloud/BUILD5_SCENERY_EMIT_PREFETCH_20261023.md).

Run from the repository root with Python 3, host GCC/G++, GNU Make, the
pinned SH GCC 15.2.0 toolchain, KallistiOS headers and the public SDK headers
used by the earlier cloud controls. No private game data is used. Each
output directory must be new.

```sh
BUILD5_TOOLS=port/dreamcast/tools/cloud/build5
BUILD5_OUT=/tmp/re4dc-build5
BUILD5_CXX=/path/to/sh-elf/bin/sh-elf-g++
BUILD5_KOS=/path/to/KallistiOS
BUILD5_SDK=/path/to/public-sdk

python3 "$BUILD5_TOOLS/build_controls.py" \
  --output "$BUILD5_OUT/production" --sh4-cxx "$BUILD5_CXX" \
  --kos-root "$BUILD5_KOS" --sdk-root "$BUILD5_SDK"
python3 "$BUILD5_TOOLS/build_controls.py" --quick \
  --knob SCENERY_DEDUP=2 --knob PREF_WALK=1 \
  --output "$BUILD5_OUT/dedup-pref" --sh4-cxx "$BUILD5_CXX" \
  --kos-root "$BUILD5_KOS" --sdk-root "$BUILD5_SDK"
python3 "$BUILD5_TOOLS/verify_knobs.py" \
  --profile "$BUILD5_OUT/production/build-controls.json" \
  --output "$BUILD5_OUT/knobs"
python3 "$BUILD5_TOOLS/check_geometry.py" --output "$BUILD5_OUT/geometry"
python3 "$BUILD5_TOOLS/check_geometry.py" \
  --output "$BUILD5_OUT/sanitized" --sanitize
python3 "$BUILD5_TOOLS/target_cost.py" build \
  --output "$BUILD5_OUT/target" --sh4-cxx "$BUILD5_CXX" \
  --kos-root "$BUILD5_KOS" --sdk-root "$BUILD5_SDK"
python3 "$BUILD5_TOOLS/target_cost.py" run \
  --build "$BUILD5_OUT/target/cost-build.json" \
  --output "$BUILD5_OUT/cost"
python3 "$BUILD5_TOOLS/check_prefetch.py" \
  --build "$BUILD5_OUT/target/cost-build.json" \
  --output "$BUILD5_OUT/prefetch.json"
python3 "$BUILD5_TOOLS/project_frame.py" \
  --build "$BUILD5_OUT/target/cost-build.json" \
  --costs "$BUILD5_OUT/cost/cost-controls.json" \
  --prefetch "$BUILD5_OUT/prefetch.json" \
  --work "$BUILD5_OUT/frame" --output "$BUILD5_OUT/cost-summary.json"
```

## Evidence boundaries

- `build_controls.py`: complete Make-derived preprocessing and SH-4
  objects, absent/explicit-zero identities against the archived base,
  all 32 combinations of SELECT_ONLY, SUBMIT_BATCH, REPLAY_LEAN,
  UV_SNAPSHOT and SELECT_LEAN2, enabled compilation and section/stack
  sizes. Unchanged actor/UI translation units are checked as well.
  The focused second invocation also compiles DEDUP=2 with PREF_WALK=1.
- `verify_knobs.py`: real Make wiring, defaults and rejected dependencies,
  including compatibility with PREF_WALK and DEDUP.
- `check_geometry.py`: actual source-extracted emission, gather, replay,
  borrow and clipping bodies; validated synthetic plain/indexed R4IM,
  empty/one/repeated/reversed picks, partial groups, near clipping,
  dynamic UV, queue pressure and failure behavior. Every TA/accounting
  word and SQ-lock result is compared across off/on.
- `target_cost.py`: actual compiled SH-4 replay/lookahead with an observed
  geometry edge, plus a separate production scalar-gather entry. The
  existing interpreter and pipeline model fail on unsupported opcodes.
  FTRV/FSRRA and full geometry are outside this cost measurement.
- `check_prefetch.py`: actual emitted PREF addresses checked against the
  adopted package records. It verifies next selected IDs, indexed first
  offsets, plain partial starts, header line straddles, cross-part hints,
  payload suppression for empty picks, ordering and allocation bounds.
- `project_frame.py`: portable cost evidence plus an explicitly assumed
  500-piece population (15 queues of 32 and one of 20), all with 96 vertices.
  It prices plain, indexed, and indexed-with-10%-empty populations, adding
  separate gather-entry deltas to actual replay/lookahead deltas. This is
  a sensitivity calculation against the supplied 47.8 ms reference at
  200 MHz; it is not a measured r101 census or integrated emitter timing.

Warm I assumes instruction residency. Cold I starts an empty instruction
cache for each named fixture sequence and depends on its synthetic ELF
layout. Both omit data-cache miss latency, bus contention, real TA/SQ
transfer, interrupts and unrelated frame work.

Loads/stores count architectural instructions and bytes, including stack
and literals. PREF requests are separate from demand accesses. Distinct
32-byte lines are address unions, not misses. Per-piece sums and whole-run
unions are explicitly different quantities. No number here is a measured
r101 frame-time improvement.
