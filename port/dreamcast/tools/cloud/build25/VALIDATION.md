# Build 25 validation and cost evidence

Base: `7acd7d8fd6a828d4e596fdb57516a0655b4dc032`. The new runtime control
remains default off. The hand-back and owner questions are in
[`CLOUD_AGENT_QUEUE.md`](../../../docs/cloud/CLOUD_AGENT_QUEUE.md).

## Target identity and compilation

[`build_controls.py`](build_controls.py) uses the existing Build18 restricted
recipe reader and Build24 target helpers. It obtains flags from the actual
Make rules; it does not replace the renderer with copied test arithmetic.
The toolchain is the Build24 pinned OCI compiler, GCC 15.2.0 / binutils
2.45.1 / newlib 4.6, with KOS `804b3195` and sh4zam `33fa4850`. Every
restored compiler executable is checked against the previous pinned hashes.

[`receipts/target-off.json`](receipts/target-off.json) records **32** exact
byte comparisons: four translation units, QA_LINK 0 and 1, absent and explicit
zero, each as complete preprocessed source and complete object. Debug records
and line markers are omitted in the same way in every arm. The units are
`native_actor_fast.cpp`, `native_model.cpp`, `native_static.cpp` and
`qa_menu.cpp`; the native chunk include belongs to the actor unit's closure.

The complete OFF and ON proofs were rerun after rebasing onto the newly landed
`ACTOR_LIGHT_CAP`, barn diagnostics and QA link changes. No target artifacts
or runtime-source hashes from the earlier integration base are reused.
The receipts capture 133 actual source/Make inputs for OFF and 137 for ON.

[`receipts/target-on.json`](receipts/target-on.json) records six successful
enabled compositions: public recipe, QA_LINK, probe off, legacy light controls
off, setup/bytes/clip reuse enabled, and `ACTOR_LIGHT_CAP=1` with
`BARN28_DIAG=1`, `DRAW_SETUP_AUDIT=1` and QA_LINK. Relocatable links resolve the new
lighting hooks. Actor/model/static objects contain no old exact/directional
vertex-light pass, AVK light call, or source/actor lighting evaluator reference.
The cap composition also disables `GIGANTE_LIGHTS`, checking that FAST_ONLY
supplies its own bounded fold without retaining the old cap fallback helpers.
Empty, `2`, and multiword knob values are rejected by Make. The enabled knob
requires the existing native fast actor implementation.

These are full translation-unit proofs. They are **not** a final linked game,
whole-image identity proof, private-asset build, emulator scene or console run.
The public profile mirrors `NMR_POOL_LOD=0` across every arm because its private
Ganado asset dependency is unavailable. No release recipe is changed.

## What the SH4 fixtures execute

[`cost_build.py`](cost_build.py) includes the complete production actor source
in an adapter that supplies synthetic input records. The old arm executes
`ACTOR_EXACT_FAST=1`; both arms explicitly hold the newly landed
`ACTOR_LIGHT_CAP=0`. The new arm executes the actual bounded part fold and
`pass_fast_only`. The reference source evaluator is linked only for ordinary
reference dependencies; unused sections are discarded by the fixture link.
There is no production assembly or linker change.

Each of five cases runs with 16, 64 and 128 input vertices:

- A material that uses vertex RGB.
- A material scale below the old fast-fold cap requirement.
- Eight significant lights.
- The unclamped diffuse material mode.
- Leon's marked source record with a low material scale that formerly declined
  the probe, now using his live probe.

Every old fold is checked to decline; every new fold is checked to accept.
The actual public snapshot reports `fallback_parts=0` and the corresponding
former-decline reason. All vertex alpha bytes are preserved. The new colour
pass reads **no position or normal input**. Fixed colour stays constant; vertex
RGB retains per-vertex variation, including a zero channel.

The fixtures use rigid zero-position inputs, unit +Z normals, and lights
exactly one unit from each position. This deliberately limits the old
approximate reciprocal operation to the previously qualified `FSRRA(1)` case.
It does not validate general hardware reciprocal bits or a game's appearance.
The scalar interpreter's existing positive finite FTRC operation is admitted
over the wider range needed by Q16 gain, with eight accept and four refusal
controls. NaN, infinity, negative and signed-overflow inputs remain refused.

Both target arms use the public `ACTOR_PROBE_LIGHT=1` profile. Probe mode 2
requires the private `PS2_GANADO_DIR`; the fixture does not fabricate it.
The separate runtime host tests cover the mode-2 Ganado probe, fill and toggle
policy. Synthetic actor-identity functions are compiled separately so the
real caller's branch and call remain present. Their small stub instructions
are counted; the production model-identity lookup is unpriced and hook calls
are reported explicitly.

The old and new pass adapters construct the same `Part` and retain varying
vertex alpha. Constant-alpha draws can have lower cost. Mesh conversion,
deformation, position projection, clipping, submission, devices and draw-list
traversal are outside these fixtures.

## Cycles per piece

Numbers are **MODELLED**, at SH4 instruction level, with perfect D-cache.
Cold figures start the 8 KiB I-cache cold **for the named piece** and depend
on the synthetic link layout. They are not hardware time or a whole-frame
speedup. Setup and pass are separately priced; do not add their cold figures
and call that a single cold-cache execution.

At **128 inputs per part**, values are warm / cold-I cycles:

| Synthetic case | Old fold + exact preparation | New part fold | Old exact vertex pass | New colour pass |
|---|---:|---:|---:|---:|
| Vertex RGB | 971 / 1,386 | 1,880 / 2,673 | 102,380 / 103,173 | 11,922 / 12,142 |
| Material scale | 985 / 1,410 | 1,884 / 2,665 | 100,853 / 101,690 | 3,987 / 4,204 |
| Eight lights | 2,182 / 2,948 | 3,949 / 4,776 | 168,978 / 169,821 | 3,987 / 4,204 |
| Unclamped diffuse | 979 / 1,394 | 1,850 / 2,619 | 98,549 / 99,386 | 3,987 / 4,204 |
| Leon low material | 1,017 / 1,490 | 1,884 / 2,734 | 100,427 / 101,326 | 3,987 / 4,204 |

The new fold can cost more than an early old decline; it removes the much
larger repeated light work that followed the decline in these cases. This
comparison does not show that every already-fast material gets faster.

## Loads, stores and 32-byte lines

These are executed architectural operand accesses, including stack and
literals. Unique lines are **not cache misses**; line visits count repeated
demand accesses, not memory-bus transfers. Opcode fetches are excluded.

For the 128-input **vertex pass**, excluding the separately priced fold:

| Case / arm | Load instructions | Store instructions | Unique 32-byte lines | Demand line visits |
|---|---:|---:|---:|---:|
| Vertex RGB, old exact | 20,986 | 3,061 | 268 | 24,047 |
| Vertex RGB, new multiply | 2,090 | 177 | 191 | 2,267 |
| Material scale, old exact | 20,471 | 3,060 | 267 | 23,531 |
| Material scale, new flat | 683 | 178 | 191 | 861 |
| Eight lights, old exact | 32,706 | 3,775 | 284 | 36,481 |
| Eight lights, new flat | 683 | 178 | 191 | 861 |

The three-light vertex-RGB **fold** changes from 231 loads / 336 stores /
57 unique lines / 567 line visits to 288 / 162 / 36 / 450. The eight-light
fold changes from 514 / 480 / 77 / 994 to 629 / 317 / 45 / 946. Thus the
data benefit comes primarily from eliminating per-vertex geometry/light
reads, with a smaller setup footprint as well. Per-region evidence and the
16/64-input cases are retained in
[`receipts/target-cost.json`](receipts/target-cost.json).

## Code and stack sizes

These are independently compiled target objects under the public QA recipe,
not linked-image deltas:

| Unit | Original executable bytes | Enabled bytes | Delta |
|---|---:|---:|---:|
| Native actor fast | 60,676 | 50,540 | −10,136 |
| Native model | 14,400 | 10,584 | −3,816 |
| Native static | 71,108 | 70,664 | −444 |
| QA menu | 12,438 | 12,918 | +480 |
| **Sum** | **158,622** | **144,706** | **−13,916** |

Total allocated object bytes change by −12,834; BSS changes by +1,056
(actor counters +36, model −4, QA snapshot capacity +1,024). Alignment,
section collection and final linker layout can change final-image deltas.

The compiler reports 520 bytes for the old `build_lights` frame and 268 for
`fast_only_lights`; 716 for `pass_lights_exact` and 44 for `pass_fast_only`.
The `Lights` object shrinks from 568 to 168 bytes. Observed fixture peaks,
including caller frames, are 944→284 bytes for the ordinary fold/preparation
and 880→184 bytes for the vertex pass. Those caller-inclusive figures are
different quantities from a function's `.su` static frame. Leon's new probe
fold fixture reaches 272 bytes. Code/stack details and compiler commands are
in the target receipts and
[`receipts/cost-build.json`](receipts/cost-build.json).

## Explicit whole-frame sensitivity

**MODELLED synthetic scenario:** assume 30.0 ms of all other work, unchanged
between arms, plus 42 copies of the 128-input material-scale light fixture:

`T_frame = ASSUMED 30.0 ms + 42 × T_light(128 inputs)`.

The old light subtotal is 21.38598 ms; the new subtotal is 1.23291 ms.
The corresponding synthetic whole-frame totals are **51.38598 → 31.23291 ms**.
These are intentionally stated assumptions, not the measured farm, village
or chapter 1–2 workload. No measured room frame total or character budget is
used. Actual frame change, fallback frequencies, transformed inputs, D-cache
behavior, appearance and gameplay equivalence remain local-owner checks.

## Reproduction

Use a fresh output directory for each command. Substitute the local pinned
compiler, KOS, SDK and compiler receipt paths:

```sh
python3 port/dreamcast/tools/cloud/build25/build_controls.py \
  --output /tmp/al25-target --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/kos --sdk-root /path/to/sh4zam \
  --toolchain-receipt /path/to/toolchain.json
python3 port/dreamcast/tools/cloud/build25/cost_build.py \
  --output /tmp/al25-cost-build --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/kos --sdk-root /path/to/sh4zam
python3 port/dreamcast/tools/cloud/build25/cost_run.py \
  --build /tmp/al25-cost-build/cost-build.json --output /tmp/al25-cost-run
```

The committed compactor preserves all numeric evidence while interning repeated
flags/dependencies and retaining relevant stack entries with the full `.su`
hash. Raw receipts and executable traces stay in the run directory. Host
runtime/bake controls and the QA datagram contract are separate tests; none
substitutes for the owner's private stills, gameplay, full-image or console gates.
