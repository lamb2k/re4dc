# Build 2: actor setup lean — 2026-10-23

Base: `origin/t15/int`, `28da09802ed9ff6756529bab02978230983453be`.
Branch: `codex/actor-setup-lean-20261023`. Knob: **`ACTOR_SETUP_LEAN=0` by default**.
The separate world UV snapshot fix is a second commit on this branch.

**Result:** the repeated skinned-position/16-bit-normal lighting setup falls
from **278 to 200 model cycles per subsequent meshlet**, with **23 fewer data
loads, 22 fewer stores and 178 fewer bytes accessed**. The cache has a first-use
cost and adds 128 bytes to `Part`. An illustrative 64-part, 512-meshlet frame
saves **0.161 ms** from this setup, or **0.176 ms** when each part also constructs
fresh lights. These are model estimates with explicit workload assumptions,
not measured r101 or console gains.

## What changed, and what was already shared

Each `Part` now lazily retains the AVK position and light argument blocks,
kernel selection and eligibility. It fills invariant source pointers, screen/UV
constants, palette-table pointers, lighting pointers and alpha once. Each call
still refreshes records, count, record stride and output destinations. Palette
readiness remains live, and a partially completed lighting kernel keeps the
same direction-building/resume behavior. The cache cannot outlive the part.

With the existing `ACTOR_NO_CLEAR=1`, the `Lights` fields that `lights_reset`
always writes no longer receive a redundant constructor clear. The builder
already assigns the source-light pointer, so the later duplicate stores are
removed too. Fields not covered by that reset, including the statue exact-light
state, retain their original initialization. `ACTOR_NO_CLEAR=0` keeps its old
initializers.

The audit found no valid reason to rebuild or replace the existing higher-level
caches: `prime()` only initializes newly required cache entries; a grouped
window retains its primed count; `Frame` and `position_matrix()` already memoize
screen/skin matrices; `abc_part` runs once per part and `AbcEye` caches the last
palette. Hardware matrix-register loads must remain because position and light
passes overwrite the same registers. Source/bridge/owner validation, material
selection, streaming/commit/abort behavior and all geometry kernels are
unchanged. No frame-wide pointer-only light or palette cache is introduced.

## Compiled cost and memory traffic

The complete production translation unit is compiled with the **Make-derived
Test 22 public actor recipe**, SH GCC 15.2.0. A separate target fixture executes
the actual compiled setup and observes every AVK argument word and chosen
kernel. Its palette tables are prepared; geometry kernels are observed return
edges. Their unchanged arithmetic, argument reads and TA output are excluded
from these setup figures. Owner/material service and frame/palette cache misses
are also outside this isolated price.

Warm I assumes instruction residency. Cold I starts an empty 8 KiB instruction
cache once per complete part sequence, including the model's instruction-line
fill cost. Both use perfect D-cache and omit unrelated bus contention, DMA,
interrupt and SQ-transfer costs. Cold values depend on the synthetic ELF layout.

### Subsequent meshlets

Each row is one position/light pair after the first meshlet, derived from the
8- and 32-meshlet compiled traces. Loads/stores include stack and literal-pool
traffic; bytes are architectural accesses, not external memory traffic.

| Format | Warm cycles off → on | Loads off → on | Stores off → on | Loaded bytes off → on | Stored bytes off → on |
|---|---:|---:|---:|---:|---:|
| Skin, s16 normals | 278 → 200 | 84 → 61 | 56 → 34 | 313 → 223 | 224 → 136 |
| Rigid stride 8, s16 normals | 265 → 172 | 81 → 52 | 55 → 34 | 311 → 201 | 220 → 136 |
| Rigid stride 6, s16 normals | 261 → 172 | 80 → 52 | 55 → 34 | 307 → 201 | 220 → 136 |
| Skin, s8 normals | 289 → 203 | 85 → 62 | 55 → 34 | 316 → 226 | 220 → 136 |

### Part entry, first use and finite runs

Skinned s16-normal pairs, including the controlled Part construction, dispatch,
loop and return. The zero-meshlet row exposes entry cost; it is not a complete
actor submission. The light-constructor saving below is not included here.

| Meshlets in one part | Warm cycles off → on | Cold-I cycles off → on | Loads off → on | Stores off → on |
|---|---:|---:|---:|---:|
| 0 | 113 → 125 | 277 → 290 | 26 → 28 | 52 → 54 |
| 1 | 391 → 435 | 900 → 1,051 | 112 → 125 | 108 → 116 |
| 2 | 669 → 635 | 1,178 → 1,261 | 196 → 186 | 164 → 150 |
| 8 | 2,337 → 1,835 | 2,846 → 2,461 | 700 → 552 | 500 → 354 |
| 32 | 9,009 → 6,635 | 9,518 → 7,261 | 2,716 → 2,016 | 1,844 → 1,170 |

For a nonempty part with `M` such meshlets, the warm setup saving in this fixture
is **`78*M - 122` cycles**. A one-meshlet part costs 44 extra warm cycles and
151 extra cold-I cycles in this portion. Warm reuse pays back at two meshlets;
this cold layout requires more than two. A cone-rejected part never prepares
either argument block, but still initializes the two cache-state words.

Fresh local Lights construction plus the unchanged constant-light builder costs
**431 → 384 warm cycles**, **770 → 686 cold-I cycles**, **55 → 53 loads** and
**106 → 70 stores**. Loaded/stored bytes fall from **183/377 to 179/237**.
The ambient-only fast-light case gives the same 47-cycle warm saving. This
constructor credit applies once to a fresh Lights instance; `OneWindow` reuses
its two instances, so it cannot receive this credit for every chunk.

For context, unchanged `lights_reset` itself costs 50 warm cycles, 3 loads and
36 stores (12/140 bytes). A prepared `position_matrix` cache hit costs 29 warm
cycles, 6 loads and 1 store (21/4 bytes, including the fixture's stack save).
These are retained work, not additional claimed savings.

### Data-cache exposure

For the complete 32-meshlet skinned sequence, loaded/stored bytes fall from
**10,126/7,370 to 7,382/4,674**. Each subsequent complete meshlet touches
**25 → 22 distinct 32-byte lines**; summing successive meshlet intervals plus
entry/exit gives **811 → 721** touches over the run. A second, finer metric
summed separately between position and lighting kernel edges falls from
**1,196 to 1,014**; it counts a line again if both passes touch it.
The **whole-sequence unique address footprint increases from 31 to 33 lines**
(992 → 1,056 bytes). This is a real storage tradeoff, not a claim that fewer
stores automatically mean fewer cache misses. The supplied console half-cache
regression is why both figures are reported.

## Production code and stack

Executable-section totals from complete objects; data/BSS do not grow. These
are not linked-disc size or memory-headroom results.

| Direct / cone mode | Executable bytes off → on | Delta |
|---|---:|---:|
| 1 / 0, public actor profile | 60,320 → 60,096 | -224 |
| 1 / 1 | 67,928 → 67,760 | -168 |
| 1 / 2 | 68,620 → 68,452 | -168 |
| 0 / 0, compatibility profile | 42,076 → 42,084 | +8 |
| 0 / 1, compatibility profile | 48,752 → 48,812 | +60 |
| 0 / 2, compatibility profile | 49,436 → 49,612 | +176 |

Public direct/cone-0 compiler stack frames: `re4dc_actor_submit` **1,676 →
1,800 bytes**, `one_chunk.part.0` **1,088 → 1,216**, `pass_positions` **316 →
248**, `pass_lights` **292 → 248**, and `re4dc_actor_submit_chunks` **1,392 →
1,392**. These are individual frames, not a summed maximum call chain. `Part`
grows by 128 bytes; the controlled target pair's observed peak grows by 56
bytes because its former argument-block frames shrink.

Direct-off is derived through Make with the dependent transaction, grouped
submit and owner features disabled as its existing guards require. It is a
compatibility build, not a claim that all direct-on Test 22 options work with
direct submission disabled. The receipts list every override.

## Identity and exact-output evidence

- **24 off-identity comparisons:** exact integration baseline versus current
  knob absent and explicit zero, complete preprocessed TUs and executable
  objects, for direct 0/1 × cone 0/1/2. Make flags and generated headers match
  too. Preprocessor line markers and debug line records are omitted consistently.
- **Compiled setup:** all 67 target scenarios pass off/on comparisons of kernel
  selection, every argument word and controlled Part/light state. Four format
  families, position-only/light-only/paired calls and 0/1/2/8/32 meshlets are
  covered. Production AVK assembly is unchanged.
- **Hosted submission:** 1,176 paired scenarios across eight off/on pairs,
  comparing 3,434,688 ordered TA words and 120,129 separately tagged state
  words. The complete production actor TU runs with explicit
  scalar AVK/SQ adapters. Every emitted TA word, in order, and controlled
  ownership/result/kernel-call state are compared. Coverage includes ordinary
  submit, grouped `one_chunk`, clipping/rejection, partial lighting resumes,
  cache redirection, changing record stride, light/bake changes, frame eviction,
  missing workspace, capacity failures, packet flushes and direct aborts.
  The additional pairs cover AVK/N16 diagnostic mode 2 and `ACTOR_NO_CLEAR=0`.
  A 150-scenario diagnostic pair also passes AddressSanitizer/UBSan with the
  same output as the uninstrumented pair.

The hosted geometry test does not execute SH-4 FTRV/FSRRA. The target setup
comparison and unchanged kernel source establish its argument boundary; a real
gameplay trace, Flycast frame timing and console cache behavior remain for the
integration measurements. Reproduction commands and exact fixture boundaries
are in [the tools README](../tools/d367/actor_setup_lean/README.md); hashes,
configuration receipts and detailed tables are in [the JSON report](D367_ACTOR_SETUP_LEAN_20261023.json).

## Whole-frame model estimate

At 200 MHz, assume **64 qualifying parts with 8 skinned, s16-normal meshlets
each**, all using both AVK passes. The finite-run warm saving is
`64*(2337-1835)/200000 = 0.16064 ms/frame`. With a fresh local Lights instance
for all 64 parts, add `64*47/200000 = 0.01504 ms`, giving **0.17568 ms/frame**.
A grouped window receives only its actual constructor credit. Starting the
setup sequence cold for every part gives **0.1232 ms** saving before any light
constructor credit; that is a separate empty-cache scenario.

At the same 64 parts but 32 meshlets each, warm setup saving is **0.75968 ms**,
or **0.77472 ms** with 64 fresh Lights instances. Neither workload is asserted
to be the current r101 cross census. The 512-meshlet example would move a fixed
49.3 ms frame to about **49.12–49.14 ms** if every other cost stayed constant.
It does not turn the supplied 2.8–7.5 ms actor total into a measured gain.
Keep both new knobs default zero until the separate Flycast and console runs.
