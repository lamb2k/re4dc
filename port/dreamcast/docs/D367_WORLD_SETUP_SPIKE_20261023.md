# World selection setup spike (2026-10-23)

Status: bounded spike complete. Target selection equivalence and modeled
setup/selection savings pass; the option remains off by default. No release
acceptance or r101 frame-time gain is claimed.

## Question and scope

The user asked for a spike on the highest-priority opportunity from the r101
performance analysis: remove repeated world-record preparation and replay work.
The baseline is commit `8c7226467dba68ac8ee16652accc10f683562685`.

This bounded first experiment removes the full emission context from eligible
world selection. The existing `SCENERY_CHUNK` path constructs a `MeshDraw` while
selecting a part, copies the selection into the existing queue, and constructs
another `MeshDraw` during emission. Selection itself needs only package,
camera/bounds, LOD and strip-group state. It does not bind a material, gather
corners, project vertices, clip strips or submit packets.

The spike extends that existing path. It does not introduce another renderer,
room package, persistent cache, visibility policy, or geometry reduction. The
same selection implementation and far-distance policy are shared by the
original and smaller contexts. The original emission path is retained.

## Required behavior

- A default-off build knob; compare the affected production object with the
  unchanged baseline using the same compiler and flags.
- Identical eligibility, cluster/LOD/group decisions, ordered semantic pick
  fields, and selection counters for the same inputs.
- Identical queue capacity and flush ordering, including cull/sky restoration.
- Borrow placement matrices only during synchronous selection. Queued records
  retain their original copied state and lifetime.
- Keep empty selections and zero-group picks on the original replay path.
  Removing them is a separate experiment because binding, result accounting
  and other side effects must be priced and preserved.
- Retain the original fallback for PVS/interior/check-mode/ineligible parts.
- Do not change transforms, strip walking, packet emission, gameplay, assets,
  build recipes or defaults.

## Evidence available in this environment

The retained GCC 15.2 SH-4 toolchain, KOS headers, instruction runner and timing
model permit compilation and bounded execution of actual production code.
The local asset subset is not a runnable r101 release disc, and no Flycast or
physical Dreamcast run is available in this environment.

Consequently, a target-code fixture can establish correctness for its tested
inputs and measure setup/selection instruction and modeled-cycle costs. It
cannot establish a village-cross frame-time gain, packet/framebuffer parity
for a complete game frame, or physical-console acceptance. Host wall-clock
timings are not a substitute for SH-4 measurements.

The supplied 616 pieces and approximately 3,400 cycles per piece are motivation
for the experiment. They are not treated as a verified current call count or
as the measured cost of this narrower selection-context construction.

## Implementation

`SCENERY_SELECT_ONLY=1` is accepted only with `SCENERY_CHUNK`. The default is
zero. Eligible parts use `ScenerySelector`, which borrows the placement matrix
and holds only the state read by selection. Its constructor initializes the
lazy-cache guards without clearing the coefficient arrays; the existing
coefficient builders fill those arrays completely before use.

`MeshDraw` and `ScenerySelector` include the same `scenery_chunk_select.inc`.
The original foliage/transparency far-distance adjustment is likewise shared
through `scenery_part_far.inc`. This avoids maintaining two copies of either
decision policy. Marked-color LUT preparation stays at its original selection
point. The eligible path still fills the same `ChunkPart` and `Pick` records;
the existing replay constructs the full emitter later.

An ineligible part falls through to the original full context and draw path.
It first pays for the smaller context and eligibility check. Correctness of
that dispatch is covered separately from eligible-selector cost; its runtime
frequency and net cost still require a scene measurement.

## Build and correctness results

The primary configuration is derived by Make from the Test22 public recipe,
with the public build's missing character/enemy asset overrides recorded in
the receipt. It includes the actual world options: lean mode 23, chunking,
lean strip-group selection, unit concatenation, screen memo, far LOD 4,
vertex alpha and nonempty LOD. CPU back-face mode is zero; the optional cone
and front-certificate paths are not enabled in the priced configuration.

The complete production translation unit is compiled with GCC 15.2 SH-4,
the KOS target ABI and the recipe's optimization flags. Debug records are
omitted for meaningful byte identity across moved source lines. This is not
a complete game link; KOS library patch guards and final disc memory gates
are not claimed to have passed.

| Production object property | Baseline | Enabled | Difference |
|---|---:|---:|---:|
| Executable section bytes | 67,040 | 67,264 | +224 |
| Allocated section bytes | 110,627 | 110,851 | +224 |
| Zero-fill/static BSS bytes | 17,212 | 17,212 | 0 |
| `ps2_pass` compiler-reported static frame | 8,988 | 8,992 | +4 |
| Replay lambda executable bytes | 848 | 848 | 0 |

The unchanged baseline, new source with the option absent, and new source
with explicit zero produce identical complete objects and preprocessed
source. The shared object SHA-256 is
`dd20d9ab5592c097567ebffb4f101edf4848c2768b232d06d37ba6a63681c865`.
Make control checks also pass for absent, zero, one, missing chunk support
and invalid value two.

The source-extracted queue harness passes 3,564 comparisons of the original
and new dispatch. It covers empty selections, zero-group picks, part/pick
capacity flushes, ordinary and oversized fallbacks, PVS/interior/LOD/group
admission, cull and sky restoration, marked LUT preparation, UV state,
foliage/transparency far narrowing and early/late aborts. The harness runs
the actual queue, flush and emission control bodies with controlled
selection and `emit_pick` boundaries. It does not assert pixel or packet
identity for a complete renderer frame.

The existing back-face world regression also passes after its extractor is
taught to expand the one shared selector include. No existing math or
emission implementation is replaced for that regression.

## Target execution and cost method

The target fixture includes the full production translation unit and links
the real `group_visible`, newlib and compiler-library code. Generated R4IMv2
and v3 inputs are adopted by production `MeshPackage::adopt`. No copyrighted
room assets are included. Placement preparation and the unchanged one-time
palette fill occur before the timed entries in both arms.

The two entries use production setup bodies and actual production types.
They are isolated compiler-generated wrappers, not the exact instruction
blocks inside `ps2_pass`. They compare ordered semantic pick fields,
selection statistics, output bounds and unchanged shared material state.
Unused whole-pick fields and padding are excluded from semantic equality.

All 52 deterministic cases pass, including empty parts, visible/rejected
bounds, near/far boundaries, partial and zero groups, multiple clusters,
nonempty LOD selection, indexed v3 packages, 320 meshlets, repeated plane
preparation, marked materials, reflected/sheared matrices and screen-edge
cameras. The priced profile does not enable the optional cone or front
certificate; its coexistence is not qualified by this target run.

The SH-4 instruction runner records executed target instructions, including
newlib routines and branch delay slots. The repository pipeline model prices
those traces. Both a one-call trace and a 32-call trace are checked. The
instruction-cache sensitivity run starts cold once per complete trace, so
the repeated run does not charge every part a fresh cold cache. Its link
layout is synthetic. Data-cache misses, data-bus contention, DMA and store
queue costs are not modeled here; cycle counts are estimates, not measured
console cycles.

Independent review caught and removed an artificial placement-state clear
from the original test wrapper before the final cost run. That preparation
already occurs outside the production part loop. The target runner's small
opcode/address adapters have separate focused controls and do not replace
the production renderer's arithmetic.

## Cost results and interpretation

The table reports old full-context setup versus the lightweight selector.
The perfect-cache columns price a single call. The I-cache columns are
per-call averages of a 32-call trace, initially cold once. All figures are
modeled cycles for setup plus selection, excluding queue replay and drawing.

| Synthetic case | Instructions, old → new | Perfect-cache cycles, old → new | Repeated I-cache cycles/call, old → new | Repeated I-cache speedup |
|---|---:|---:|---:|---:|
| Empty part | 1,158 → 264 | 860 → 228 | 876.3 → 333.8 | 2.62× |
| Whole part already inside | 1,426 → 514 | 1,058 → 415 | 1,123.0 → 527.2 | 2.13× |
| Whole part with bounds tested | 1,793 → 879 | 1,357 → 713 | 1,451.0 → 834.4 | 1.74× |
| Scalar visibility within eligible selection | 2,123 → 1,211 | 1,647 → 1,009 | 2,154.5 → 1,132.7 | 1.90× |
| Partially surviving strip groups | 3,318 → 2,391 | 2,625 → 1,974 | 3,039.7 → 2,117.0 | 1.44× |
| 320 visible meshlets | 7,168 → 6,894 | 5,524 → 4,881 | 5,589.0 → 4,993.2 | 1.12× |
| Marked material, UV offset, cull mode 1 | 1,812 → 898 | 1,379 → 738 | 1,514.9 → 901.4 | 1.68× |

Every case also improves in the single-call cold I-cache sensitivity run.
The cache-independent saving is a relatively stable **632–651 modeled
cycles per eligible selection**, while the percentage shrinks as selection
does more geometry work. This is the expected signature of removing a fixed
setup cost. Code placement affects the I-cache differences; they should not
be used as a prediction of the linked game's cache behavior.

The full context is 776 bytes and the small context is 392 bytes in this
configuration, but size alone is not the saving: the old wrapper executes
684 instructions inside real newlib `memset` and 148 inside `memcpy` on
each unmarked tested call. The new wrapper avoids those operations. For the
empty case, recorded target stores fall from 1,346 to 244 bytes. These are
executed stores, not measured external-memory traffic. The exact in-function
code generation and allocation in the real caller remain separately bounded
by the complete production object and stack results above.

This is a positive first slice of the world-setup opportunity, not evidence
of a 10× world or frame gain. For scale only, 640 cycles at an assumed
200 MHz is 3.2 microseconds. If all 616 user-reported pieces corresponded to
one eligible selection each, that would be about 1.97 ms per frame before
fallback overhead and real cache effects. Neither the 616-call mapping nor
the eligible fraction has been measured here. Applying that illustration to
47.8 ms would suggest roughly 1.04× for the frame, not 10×.

The next larger change must reduce **how many records are visited, prepared
and replayed**. This spike retains those visits, all selected geometry and
all emitter work. A real r101 capture should first establish counts and time
at those boundaries. Only then can a room-level batching or conservative
hierarchy experiment demonstrate that it removes the dominant work rather
than merely moving it. Existing active batching/culling must be included in
that baseline.

## Decision and remaining gates

Keep this implementation as a default-off experiment ready for a matched
r101 A/B run. Do not enable it in a release from these synthetic results.
The next scene qualification must resolve the eligible/fallback mix, total
world and frame time, final linked memory headroom, and complete rendered
output. Include a known tight-memory/cutscene view and a view that exercises
the ordinary fallback. The additional 224 object-code bytes do not establish
that a final console image fits its existing memory margin.

The independent implementation and tooling reviews found no remaining
blocker in this bounded scope. Default-off identity and queue/selection
equivalence are established for the documented configurations. No runnable
r101 image or console was present, so those game-level gates remain open.

## Evidence identities

The adjacent `D367_WORLD_SETUP_SPIKE_20261023.json` records compact results,
source and receipt hashes, all 52 target cases and all 14 cost pairs. Full
local receipts were retained in the following experiment directories:

- `backface-tools/world-setup-target-01/build-controls.json`: complete
  production object, preprocessing, code-size and stack checks.
- `backface-tools/world-setup-target-clean/build-controls.json`: fixture
  built from the final committed generator/template.
- `backface-tools/world-setup-run-04/target-controls.json`: 52 target checks
  and seven cost cases at one and 32 calls.
- `backface-tools/world-setup-queue-02/queue-controls.json`: 3,564 dispatch
  and replay-control comparisons.
- `backface-tools/world-spike-existing-controls-02/world-runtime-controls.json`:
  existing FRONT 0/1/2 and room 0/1 regressions, including 42 metadata cases.
- `backface-tools/world-setup-spike-controls-20261023/make-controls.json`:
  five Make knob controls.

The executed fixture ELF SHA-256 is
`d77b9dcad00722e699f90ada5247c4360d69f52614b29706168f8c89da902cb3`.
The fixture from the final generator produces a byte-identical ELF to the
one executed. Final generated fixture source SHA-256 is
`dbe0ae3df3c09f0dce1d743259f578af15bc630dad36d205459115c64b38971c`.

## Reproduction

From the repository root, choose new output directories for each command:

```sh
python3 port/dreamcast/tools/d367/world_setup_spike/generate_fixture.py \
  --output /tmp/world-setup-inputs

python3 port/dreamcast/tools/d367/world_setup_spike/queue_test.py \
  --output /tmp/world-setup-queue

python3 port/dreamcast/tools/d367/backface_cone_front/world_runtime_test.py \
  --output /tmp/world-setup-existing-controls

python3 port/dreamcast/tools/d367/world_setup_spike/build_target.py \
  --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/kos \
  --sdk-root /path/to/sh4zam-sdk \
  --fixture /tmp/world-setup-inputs/selection_fixture.cpp \
  --output /tmp/world-setup-target

python3 port/dreamcast/tools/d367/world_setup_spike/run_target.py \
  --elf /tmp/world-setup-target/selection.elf \
  --cases /tmp/world-setup-inputs/cases/cases.json \
  --warm-calls 32 --icache \
  --output /tmp/world-setup-run
```

The generated receipts contain exact commands, source/input identities,
compiler flags, output hashes, case results and timing-model settings.
Generated fixtures and their large synthetic buffers are test-only and are
not linked into the production object. No release default is changed.
