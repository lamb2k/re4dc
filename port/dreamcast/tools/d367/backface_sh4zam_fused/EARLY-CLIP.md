# Early depth exit for the SH4ZAM world strip walker

## Scope and status

Base: `46623a9e7c393f0fd33c45a36598295e662a3d39`.

`BACKFACE_EARLY_CLIP=1 CPU_BACKFACE=2 GAME_SH4ZAM=1` enables a render-only
optimization. `BACKFACE_EARLY_CLIP` defaults to **0**. This branch does not
change a play recipe or establish a whole-game speedup.

The linked commit computes every facing determinant for a short world strip
even when an early vertex has already made clipping inevitable. This change
returns that strip to the existing clipper immediately. Accepted strips keep
the same floating-point determinant, strip order, parity repair, vertex words,
and terminal flags. No transform or skinning work is saved by this change.

The disabled preprocessed assembly and both disabled trace/nontrace kernel
objects are byte-identical to the base. Enabled nontrace kernel text grows
from 8,160 to 8,352 bytes, **+192 bytes**. There is no new persistent buffer or
allocation. Whole-program identity and memory qualification remain separate
gates.

## Why the shortcut is exact

The `codes=1` specialization has three existing entry conditions:

1. The strip has at most 64 indices.
2. Its index count does not exceed the caller's limit.
3. Its first referenced outcode satisfies `(first & 63) == 0`.

The last condition proves that the AND of all outcodes cannot contain a
depth or screen bit. A later depth bit must therefore select clipping;
neither all-depth nor all-screen rejection can take precedence. The remaining
vertices cannot change that answer.

The enabled scan replaces the two instructions accumulating `all` and `any`
with a depth-mask test and conditional exit. `r2` holds the constant mask 3.
Local exit islands keep conditional branches in range; the original public
epilogue restores the ABI and returns the original count-byte cursor. Earlier
strips retain their counters and output. The crossing strip writes nothing to
the store queues, including uncommitted writes.

When the scan completes without a depth crossing, the final all/any/limit
decision is redundant and is skipped. First-outcode depth/screen cases,
oversized strips, and long-strip fallback retain the original decision order.
The separate long-code gate still initializes `all` to 255. Actor paths do
not use the initial `r2` value before assigning their own scratch value.

## Executed-instruction benchmark

These are actual linked SH4 instructions executed by the existing bounded
host interpreter, with trace callbacks disabled. They include the complete
public caller. They are **not cycles, hardware time, or game FPS**. Geometry
is synthetic; no real-scene distribution is implied. Index positions are
zero-based.

| One 64-index strip | Base instructions | Enabled | Instructions removed |
| --- | ---: | ---: | ---: |
| Depth crossing at index 1 | 1,772 | 180 | 89.84% |
| Depth crossing at index 2 | 1,772 | 192 | 89.16% |
| Depth crossing at index 3 | 1,772 | 220 | 87.58% |
| Depth crossing at index 7 | 1,772 | 318 | 82.05% |
| Depth crossing at index 31 | 1,772 | 926 | 47.74% |
| Depth crossing at index 63 | 1,772 | 1,740 | 1.81% |
| All front | 2,901 | 2,900 | 1 instruction |
| All back | 1,827 | 1,826 | 1 instruction |
| Mixed retained runs | 3,427 | 3,426 | 1 instruction |
| First screen flag, otherwise eligible | 3,234 | 3,230 | 4 instructions |
| All depth / all screen / oversized | unchanged | unchanged | 0 |

The earliest crossing has a **9.844x instruction-count ratio**. It eliminates
all 434 counted determinant operations. Accepted 32-strip batches save 32
instructions. Branch scheduling and code layout still matter, so the same
dynamic instruction streams were also checked with the existing pipeline
model below.

## Pipeline scheduling comparison

`early_clip_cost.py` exports every executed instruction, including delay
slots, to the unchanged `tools/hwmodel/hwsim.c`. It checks both instruction
counts and the model's fetched opcode bytes. The ELF metadata alone is
aliased into the model's RAM address range; executable bytes are unchanged.

These are **synthetic pipeline-only cycles** with perfect instruction/data
caches and no memory, SQ-bus, or DMA events. They do not measure a scene,
frame time, emulator speed, or physical console performance. The model stops
at the final instruction issue and omits the shared return-completion drain.

| One 64-index strip | Base modeled cycles | Enabled | Reduction |
| --- | ---: | ---: | ---: |
| Depth crossing at index 1 | 1,251 | 196 | 84.33% |
| Depth crossing at index 31 | 1,251 | 689 | 44.92% |
| Depth crossing at index 63 | 1,251 | 1,215 | 2.88% |
| All front | 2,134 | 2,123 | 0.52% |
| All back | 1,324 | 1,313 | 0.83% |
| Mixed retained runs | 2,644 | 2,633 | 0.42% |

The earliest crossing has a 6.383x modeled pipeline-cost ratio. Each accepted
pattern also saves 352 modeled cycles across 32 strips. This scheduling check
found no regression in those accepted cases. It does not establish that
CPU_BACKFACE=2 beats CPU_BACKFACE=0; the original failed performance gate in
README.md remains open.

The checked-in [early-clip-evidence.json](early-clip-evidence.json) records
the compiler and source identities, comparison counts, object hashes, full
instruction benchmark, and pipeline results.

## Reproduction

The original commit omitted five test prerequisites. This patch restores
them byte-for-byte from its recorded source commit `2249d3cfa`:

- `backface_sh4_kernel/object_test.py`
- `backface_sh4_kernel/build_oracle.py`
- `backface_sh4_kernel/oracle.cpp`
- `backface_sh4_kernel/include/dc/pvr.h`
- `backface_sh4_actors/check_actor_dispatch.py`

Use the pinned clean SH4ZAM submodule and GCC 15.2.0 / binutils 2.45.1.
The qualification script accepts `SH4_CC`, `SH4_CXX`, `SH4_LD`, and
`D367_BUILD_LOCK` for an installation outside the maintainer's default paths.
Its compiler-selected arithmetic and float-argument ABI checks remain
mandatory. Outputs must be new directories.

```bash
git submodule update --init port/dreamcast/game/third_party/sh4zam
export SH4_CC=/path/to/sh-elf/bin/sh-elf-gcc
export SH4_CXX=/path/to/sh-elf/bin/sh-elf-g++
export SH4_LD=/path/to/sh-elf/bin/sh-elf-ld
export D367_BUILD_LOCK=/path/to/owned-build-slot.lock

BACKFACE_EARLY_CLIP=0 bash port/dreamcast/tools/d367/backface_sh4zam_fused/qualify.sh /absolute/new/off
BACKFACE_EARLY_CLIP=1 bash port/dreamcast/tools/d367/backface_sh4zam_fused/qualify.sh /absolute/new/on
python3 port/dreamcast/tools/d367/backface_sh4zam_fused/early_clip_test.py \
  --baseline /absolute/new/off --candidate /absolute/new/on \
  --report /absolute/new/early-clip.json
python3 port/dreamcast/tools/d367/backface_sh4zam_fused/early_clip_cost.py \
  --baseline /absolute/new/off --candidate /absolute/new/on \
  --output /absolute/new/pipeline
```

Compare both OFF kernel objects with objects built from the original pinned
patch when validating the source change itself. Use a fresh `OBJDIR` for each
full-game knob arm; do not reuse an immutable overlay after a patch change.

## Qualification boundaries

Both the original baseline and enabled candidate pass the original 29,572
opcode/oracle comparisons and 64 additional FPSCR/mode controls. The new
focused suite passes 4,836 further comparisons, including 96 early-exit
FPSCR controls. That is **34,408 candidate comparisons plus 64 separate
mode controls**. The compiler arithmetic/ABI check, determinant DAG check,
host actor dispatch check, and materialization repeatability/drift controls
also pass. Recompiling the final repacked patch reproduces all four tested
OFF/ON and trace/nontrace objects byte-for-byte.

The host checks cover exact emitted words, strip winding, short/long and
actor EOL boundaries, both cull signs, trace callbacks, high outcode bits,
prefix output, additive counters, the clipping stop pointer, all-depth
precedence, no SQ stores before clipping, register preservation, and FPSCR
restoration. The new focused test includes every interior crossing position
of a 64-index strip and 96 early-exit mode controls.

Before enabling this in a play build, obtain matched scene measurements,
whole-program OFF identity, STRICT gameplay replay, framebuffer comparison,
KOS squeeze / s30 memory gates, and physical console timing. The current
kernel receives already-projected vertices, so it cannot solve the cost of
transforming or skinning geometry that should have been rejected earlier.

## Larger structural opportunity from modern renderers

The more substantial next experiment belongs in the existing world
`SCENERY_CONE` and newer actor `ACTOR_BACKFACE_CONE` lane. The latter is already
present upstream after this base, beginning at `245a67a1`; do not create a
second cone implementation or import unrelated integration changes here.

Extend the existing coarse decision to three outcomes:

| Certified result | Work to perform |
| --- | --- |
| Entire cluster back-facing | Reject before transformation, skinning, lighting, and submission. |
| Entire cluster front-facing | Transform normally, then use the existing lean copy without per-triangle facing tests. |
| Mixed or uncertain | Use the current exact kernel and clipping fallback. |

The all-front certificate is a proposed application of conservative cone
geometry, not an already-verified API or measured RE4DC gain. It needs proof
for source cull mode, determinant/handedness, perspective sign, near-plane
crossings, animation, and numerical error. Near a bound, fall back. A static
bind-pose cone is not automatically valid for blended skeletal deformation.

Tune grouping against total work, not rejection percentage: splitting can
increase duplicate transformed vertices, descriptor storage, and conversion
fallbacks. Measure original ordering, split ordering with culling disabled,
and split ordering with culling enabled as separate arms. Preserve material
boundaries and the existing private-asset workflow.

Primary references, consulted 2026-10-23:

- [AMD GeometryFX cluster culling](https://gpuopen.com/learn/geometryfx-1-2-cluster-culling/):
  CPU coarse rejection before fine processing, with explicit CPU-overhead tradeoffs.
- [meshoptimizer](https://meshoptimizer.org/): meshlet construction, normal-cone
  bounds, and tradeoffs between reuse and culling quality.
- [Meshlet size tradeoffs, Arseny Kapoulkine](https://zeux.io/2023/01/16/meshlet-size-tradeoffs/):
  smaller groups can cull better while increasing repeated vertex transforms.
- [Conservative Meshlet Bounds for Robust Culling of Skinned Meshes](https://www.cg.tuwien.ac.at/research/publications/2021/unterguggenberger-2021-msh/):
  conservative bounds must account for deformation. Publication abstract and
  author explanation reviewed; detailed paper equations are not qualified here.
- [Intel MaskedOcclusionCulling](https://github.com/GameTechDev/MaskedOcclusionCulling):
  useful occlusion research, but its SIMD-oriented desktop implementation is
  not a drop-in SH4 solution. Price any scalar adaptation against the existing
  PVS, room occluders, and cone tests before introducing a depth rasterizer.
