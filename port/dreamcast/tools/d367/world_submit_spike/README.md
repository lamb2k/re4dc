# World submission ownership spike

Default-off `SCENERY_SUBMIT_BATCH=1` retains the existing TA store-queue mutex
across compatible parts within a synchronous world chunk replay. Every part
keeps its own header, vertex order, UV rules, texture pin and logical accounting.
The implementation rebases to the ordinary SQ address at every part.

Read [the result and contract](../../../docs/D367_WORLD_SUBMIT_SPIKE_20261023.md)
before interpreting the numbers. This is an incremental CPU candidate; the
tools do not establish a real r101 frame gain or qualify a console build.

## Reproduce

Run from the repository root. Use fresh output locations to preserve evidence.
Supply the existing SH-4 compiler, pinned **unpatched KOS source headers**, and
SH4ZAM SDK. The tools apply the required repository PVR header patches to a
temporary overlay without changing KOS. No game data is used by these fixtures.

```bash
SPIKE_CXX=/path/to/bin/sh-elf-g++
SPIKE_OBJDUMP=/path/to/bin/sh-elf-objdump
SPIKE_KOS=/path/to/kos
SPIKE_SDK=/path/to/sh4zam-sdk
SPIKE_OUT=/tmp/re4dc-world-submit-check
```

Host state/output controls extract the production UI begin/end, emitter bind/end,
chunk emit and queue flush bodies. The controlled external edges instrument
unsafe calls, packet order, counters, material state and physical lock balance.

```bash
python3 port/dreamcast/tools/d367/world_submit_spike/check_runtime.py \
  --output "$SPIKE_OUT/host"
```

Compile both complete production translation units under their individual
Make-expanded public Test22 profiles. Compare the parent baseline with the
absent knob, explicit zero and enabled candidate. This checks object and
preprocessed-byte identity, executable/storage size and static stack frames.

```bash
python3 port/dreamcast/tools/d367/world_submit_spike/build_target.py \
  --sh4-cxx "$SPIKE_CXX" --kos-root "$SPIKE_KOS" --sdk-root "$SPIKE_SDK" \
  --output "$SPIKE_OUT/production"

python3 port/dreamcast/tools/d367/world_submit_spike/verify_knobs.py \
  --build "$SPIKE_OUT/production/build-controls.json" \
  --output "$SPIKE_OUT/knobs"

python3 port/dreamcast/tools/d367/world_submit_spike/target_static_review.py \
  --build-dir "$SPIKE_OUT/production" --objdump "$SPIKE_OBJDUMP" \
  --output "$SPIKE_OUT/caller-review"
```

The caller review counts explicitly inspected paths in the production object.
It pins symbol hashes to the reviewed GCC output and refuses different output
until its address spans are reviewed again. Its counts are instructions, not
cycles, and cannot be directly subtracted from the separate UI cycle table.

Build isolated target traces. The full UI translation unit supplies the real
hot cache/begin/end implementation and types. Real KOS SQ, mutex, empty-waiter
queue and MMU code is linked, along with the actual packet and texture getter
code. Texture loading and scene opening are explicitly controlled edges;
unreviewed scheduler, logging and other unavailable paths trap.

```bash
python3 port/dreamcast/tools/d367/world_submit_spike/target_build.py \
  --sh4-cxx "$SPIKE_CXX" --kos-root "$SPIKE_KOS" --sdk-root "$SPIKE_SDK" \
  --output "$SPIKE_OUT/target"

python3 port/dreamcast/tools/d367/world_submit_spike/target_run.py \
  --build "$SPIKE_OUT/target/target-build-controls.json" \
  --output "$SPIKE_OUT/cost" --icache

python3 port/dreamcast/tools/d367/world_submit_spike/target_code_identity.py \
  --production "$SPIKE_OUT/production" --target "$SPIKE_OUT/target" \
  --output "$SPIKE_OUT/code-identity.json"
```

The target runner executes actual SH-4 instructions using the existing setup
spike interpreter and pipeline model. It adds focused SR/OR instruction controls
needed for KOS interrupt masking. Reports distinguish executed instructions,
modeled CPU cycles and an initially cold instruction-cache arm.

## Boundaries of the result

- The cost fixture measures ownership boundaries, not geometry transformation,
  emission, complete world replay or a frame. Successful parts account for 25
  vertices without pricing those vertices' processing.
- A cold texture edge returns refusal. Miss-control costs are not successful
  texture-load timings and exclude file I/O.
- D-cache is perfect. There are no external bus delays, SQ backpressure, IRQ,
  DMA, scheduler contention or audio-waiter events.
- The primary measured profile compiles transition-owner predicates out. Host
  controls separately force source/r11f owner branches on; this is not their
  target performance qualification.
- The complete production OFF gate is separate from the controlled target
  fixture. Exact repository PVR header patches are applied only to a temporary
  declaration overlay. The KOS library/link guards and full-game link are not
  bypassed or claimed as passed.
- `PS2_PVS`, `WORLD_SCRATCH` and `TA_GUARD` are rejected by the initial candidate.
  Header-cache mode 1 and the existing direct PS2 chunk path are required.

Keep new outputs outside Git. Commit source, tools and aggregate receipts only.

For a separate game qualification build, append `SCENERY_SUBMIT_BATCH=1` to the
usual build recipe. Keep `SCENERY_SELECT_ONLY` and other knobs fixed between the
comparison arms. Measure the r101 cross with resident textures, then transitions
and short/miss-heavy runs; retain the normal visual, STRICT and memory gates.
