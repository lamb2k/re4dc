# Actor setup lean controls

`ACTOR_SETUP_LEAN` is an off-by-default optimization of
`platform/native_actor_fast.cpp`, based on integration commit
`28da09802ed9ff6756529bab02978230983453be`. See the
[report](../../../docs/D367_ACTOR_SETUP_LEAN_20261023.md) and its
[condensed receipts](../../../docs/D367_ACTOR_SETUP_LEAN_20261023.json).

## Reproduce

Run from the repository root with Python 3, host GCC/G++, GNU Make and `patch`,
the SH GCC 15.2.0 Dreamcast toolchain, KOS and the public SDK headers used by the
Test 22 controls. Output directories must be new. The fixtures contain synthetic
geometry and do not require game assets.

```sh
ACTOR_TOOLS=port/dreamcast/tools/d367/actor_setup_lean
ACTOR_OUT=/tmp/re4dc-actor-setup-check
ACTOR_CXX=/path/to/sh-elf/bin/sh-elf-g++
ACTOR_KOS=/path/to/KallistiOS
ACTOR_SDK=/path/to/public-sdk

python3 "$ACTOR_TOOLS/build_controls.py" \
  --output "$ACTOR_OUT/production" --sh4-cxx "$ACTOR_CXX" \
  --kos-root "$ACTOR_KOS" --sdk-root "$ACTOR_SDK"
python3 "$ACTOR_TOOLS/check_runtime.py" --output "$ACTOR_OUT/runtime"
python3 "$ACTOR_TOOLS/check_runtime.py" --output "$ACTOR_OUT/sanitizer" --sanitizer
python3 "$ACTOR_TOOLS/target_build.py" \
  --output "$ACTOR_OUT/target" --sh4-cxx "$ACTOR_CXX" \
  --kos-root "$ACTOR_KOS" --sdk-root "$ACTOR_SDK"
python3 "$ACTOR_TOOLS/target_run.py" \
  --build "$ACTOR_OUT/target/target-build-controls.json" \
  --output "$ACTOR_OUT/measure"
python3 "$ACTOR_TOOLS/production_audit.py" \
  --build "$ACTOR_OUT/production/build-controls.json" \
  --output "$ACTOR_OUT/production-audit" --sh4-cxx "$ACTOR_CXX"
```

`build_profile.py` expands the actual Make recipe for `native_actor_fast.o`.
It reuses the integration branch's public Test 22 recipe helpers, but obtains
the actor flags independently of the world flags. `ACTOR_DIRECT` comes from
`NATIVE_ACTOR_DIRECT` in the generated header. Direct-off is a compatibility
profile: Make requires its dependent transaction, grouped-submit and owner
features to be disabled. Every override is recorded. Direct-on uses the public
actor profile, with cone mode varied independently.

`build_controls.py` materializes the exact integration tree with `git archive`
and expands its Make recipe as well. Baseline, current knob absent and explicit
zero must have identical normalized compiler flags, generated headers, complete
preprocessed translation units and complete executable objects. Debug line
records and preprocessor line markers are omitted consistently. Direct 0/1 and
cone 0/1/2 are compiled with the option enabled too. Section sizes and compiler
stack frames come from these complete production objects, not the fixtures.
`production_audit.py` emits verbose assembly and reassembles it byte for byte
to the qualified objects, checks pinned source hashes, and verifies Make rejects
an invalid knob value. The report's constructor-store findings refer to this
production assembly as well as the isolated traces.

## Correctness boundaries

The host fixture includes the complete production actor translation unit. Its
explicit platform adapters expose the AVK argument ABI on the host, implement
the unchanged kernels' contract through scalar geometry, and replace SH-4
store-queue transport with ordinary memory copies. The actual submission,
`one_chunk`, frame preparation, light building, meshlet decisions, clipping,
packet flushing and accounting execute. All emitted TA words are compared in
order, along with controlled ownership/result events and kernel-call order.
This is a test of setup and state equivalence; it is not a hardware floating
point or gameplay trace test.

The compiled SH-4 fixture includes the production translation unit verbatim.
The real AVK wrappers execute against prepared palette tables. At each assembly
kernel boundary, the observer compares the selected kernel and every argument
word, normalizing only equivalent pointer addresses between binaries. The edge
then reports successful completion. Geometry computation, the kernels' own
argument reads and TA submission are excluded from this setup-only price.
Unsupported instructions, unmapped memory and unexpected external calls fail
closed; FTRV and FSRRA are not approximated by the scalar interpreter.

The cache belongs to one `Part`. It never survives a chunk, a source-light
change, a frame-cache eviction or a model change. It stores invariant pointers
and scalars, not a copy of palette data. Palette-ready bytes remain live.
Record stride, records/count and cache output pointers refresh at every call,
including diagnostic destination redirects and partial lighting resumes.
Matrix register loads remain in the unchanged kernels.

## Cost and traffic definitions

The existing `hwmodel/hwsim.c` prices retired target instruction traces. Warm I
assumes instruction residency. Cold I begins with one empty 8 KiB instruction
cache per complete fixture sequence and includes the model's instruction-line
fill cost; it is sensitive to the synthetic link layout. Both use perfect
D-cache and omit unrelated memory-bus contention, SQ transfer, DMA and interrupt
costs. These are model estimates, not Flycast or Dreamcast timings.

Architectural loads/stores and bytes include stack traffic and PC-relative
literal loads, excluding instruction fetches. An eight-byte memory move counts
as one instruction and eight bytes. Cached, uncached and SQ accesses are
separate; PREF is a request, not an observed demand miss or cache fill.

Repeated line touches sum the distinct cached 32-byte address lines in each
successive whole-meshlet interval, with entry/exit included. A separate, finer
metric splits at every observed kernel edge, counting a line again when both
position and light passes touch it. The whole-run unique footprint is reported
separately as one address union; none is a cache-miss count. No console speedup
is inferred from bytes saved alone.

Part creation, first-meshlet setup and later meshlets are priced separately.
The local Lights constructor/fold saving is also separate: a grouped window
can reuse an existing Lights instance, so it must not receive that saving once
per chunk. Whole-frame examples state their assumed part and meshlet counts
and do not claim to be a current r101 census.
