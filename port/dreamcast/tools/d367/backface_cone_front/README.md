# Conservative all-front cone shortcut

This extends the existing actor and scenery cone paths with a third outcome:
**front candidate**. A candidate is only sent to the existing lean emitter
after a second check proves that the *actual projected cache* has the same
strict facing sign as `CPU_BACKFACE=2` for every triangle in the group.

The integration base is `d1bc83cff32217a659f93acd5837a1ecc96ff6c3`
(`t15/int`), including PR54 and its enabled CPU2 early-clip default. Existing
all-back cone rejection already precedes vertex work;
this change adds the missing all-front shortcut. It does not replace the
skinning, transform, lighting, clipper, or store-queue implementations.

## Build and data selection

`BACKFACE_CONE_FRONT` defaults to `0`:

| Value | Behavior |
| --- | --- |
| `0` | Existing renderer; no certificate object or new caller definitions. |
| `1` | Certify eligible groups, then bypass their per-triangle CPU facing tests. |
| `2` | Also check every proposed shortcut with the target FSUB/FMUL/FMAC determinant; log and fall back on a mismatch. |

The new knob requires `CPU_BACKFACE=2`, `GAME_SH4ZAM=1`, and an enabled
existing cone path. For actors, use `ACTOR_BACKFACE_CONE=1` or its existing
check mode `2`. For scenery, use `SCENERY_CONE=1` (or `BACKFACE_CONE=1`) with
its existing `SCENERY_CHUNK` and strip-group prerequisites. Add these options
to a qualified local recipe; this change does not edit a play recipe.

The certificate translation unit is compiled separately with
`-O2 -fno-fast-math -ffp-contract=off`, after the ordinary compiler flags. Its
outward error bounds require separate floating-point operations. The rest of
the renderer keeps its existing arithmetic and build options.

### Actor metadata

The existing 16-byte `ABC1` cone records and tail remain intact. When the
converted stream has enough unused space, the new mode writes an optional
`ABC2` proof block immediately before the `ABC1` tail. It adds a 16-byte
header and 12 bytes per meshlet: a power-of-two lower bound on every triangle's
raw normal magnitude, tight XYZ extents, and padding.

The proof builder checks exact integer cross products at **every LOD**. A
degenerate triangle, short or malformed strip, incompatible palette, or
unprovable cone membership disables the shortcut for that meshlet. A capacity
shortage leaves the existing `ABC1` back cones available. It adds no separate
heap allocation.

### Scenery metadata

The scenery producer adds proof data only when explicitly requested:

```sh
python3 port/dreamcast/tools/d367/scenery21/scn21_build.py \
  INPUT_NATIVE_DIR OUTPUT_DIR --groups 4 --facing --front-proof r100
```

The optional `SCCF` trailer follows the unchanged, padded `SCCN` version-1
payload. It binds the proof to the mesh identity and the actual `R4SG` record
CRC. It carries conservative angle values, one power-of-two normal bound, and
16-bit index/strip counts per group. The reader cross-checks the counts against
the corresponding strip-byte span. Tight bounds already present in `R4SG`
supply the XYZ extents.
Missing, stale, truncated, or unsupported proof data uses the existing exact
facing path. Old readers ignore the trailer. Without `--front-proof`, the
producer's existing outputs are unchanged.

### Cost admission

A proof can cost more than the classifier work it saves. The initial version
did exactly that on small groups and long strips. The production admission
policy therefore requires all of the following before preparing cofactors:

- At least 256 index references and 64 complete strips.
- At least four index references per scanned cache vertex.
- Constant ideal W across the group's raw AABB: for each axis, the box extent
  or the actual transform's W coefficient must be zero.

These are performance filters, not replacements for either stage of the
certificate. They select the dense short-strip workloads with a useful margin
in the target model, and keep the measured unprofitable cases on CPU2. The W
filter deliberately restricts rotated and nonplanar geometry. It avoids paying
for a loose reciprocal bound when depth varies across a group.

Admission does not guarantee a certificate or a speedup. For example, a large
perturbation of actual reciprocals can still fail the second stage after the
proof work has been paid. Real asset hit rates, full caller costs, and scene
performance remain qualification requirements. More strip groups in the
producer can leave each group below the count threshold; the producer's counts
make that visible without changing the default grouping choice.

## Why an ordinary cone test is insufficient

A geometric all-front cone alone does not establish identical CPU2 output.
The old cone builders ignore zero-area triangles, while the exact CPU facing
classifier drops them. Copying a mixed group of front and degenerate triangles
would therefore change the submitted stream.

Even a nondegenerate integer triangle can change its computed facing sign
after transformation, projection, and the target determinant operations.
The mandatory regression uses raw points

```
A = (0, 0, 0)
B = (5363, 5362, 0)
C = (5362, 5361, 0)
X = 2.5*x + 327680
Y = -1.875*y + 245760
W = -z/128 + 1024
```

Its ideal projected area is positive, but the pinned target FMAC determinant
is negative. The shortcut must refuse it. Check mode is a diagnostic for the
proof and integration; production mode does not reclassify every triangle.

## Certificate

The helper reads the **actual rounded matrix** used by the vertex transform,
including the current actor palette. Let its X, Y, W rows define `A*p+t`, let
`c,r` be the raw-space bounding sphere, and let `n` be a drawn-winding raw
triangle normal. The homogeneous determinant is

```
n · (det(A)*p + adj(A)*t).
```

The implementation bounds `q = det(A)*c + adj(A)*t` with outward floating-point
intervals. Cone membership, the sphere radius, and the stored minimum normal
magnitude give a lower bound on the ideal projected area. Positive depth is
required for the entire raw-space box, including the transform error bound.
Uncertain determinant, sign, depth, or numerical range returns no certificate.

The second stage reads the actual cached reciprocals. With ideal depth in
`[Wlo, Whi]` and observed reciprocal in `[Imin, Imax]`, it bounds

```
R = max(|Wlo*Imin - 1|, |Whi*Imax - 1|).
```

This requires no accuracy assumption for `FSRRA`. Bounds on X/Y transform
error, the reciprocal residual, and multiplication rounding give a coordinate
error bound. The raw AABB gives conservative ideal projected-coordinate spans;
adding the coordinate errors bounds the actual edge spans. The determinant
bound includes the target FSUB/FMUL/FMAC operations. The shortcut is allowed only when the
ideal area lower bound is strictly larger than the complete error bound.

The cache scan uses integer ordering of positive reciprocal words and integer
X/Y validity checks. It performs no floating-point work per vertex and retains
word-aligned, alias-safe loads. Context preparation caches `adj(A)*t` once per
world chunk and reuses it while the current actor palette remains unchanged,
instead of rebuilding it for each group.

The FTRV allowance comes from the primary
[SH-4 Software Manual, section 6.6.1, printed page 129](https://www.renesas.com/en/document/mas/sh-4-software-manual).
The helper uses a wider bound and accepts only supported finite normal inputs
and zero. The analytic error bounds account for RN/RZ rounding and flushed tiny
results. On SH4, the entry points require `FPSCR.DN=1`, single precision,
32-bit moves, RN or RZ, and masked arithmetic exceptions. They decline an
unsupported mode without writing FPSCR. In particular, DN=0 can raise an
unmaskable FPU error on an intermediate denormal operand, so a mathematical
underflow allowance alone would not suffice. The pinned KOS startup selects
`0x00040000` (DN=1). The certificate does not substitute the different SH-4A
reciprocal specification for Dreamcast hardware behavior.

For review, let `eps=2^-23` and `F=2^-120=64*FLT_MIN`. Each nonnegative row
absolute bound has at most five rounding factors per contribution. Inflating
the computed sum by `1+128*eps` and adding `F` encloses it. The center-plus/minus-
extent depth expression has an error below `10*eps*H + 14*FLT_MIN`; the helper
uses `32*eps*H + F` before final outward rounding. The FTRV allowance is
`8*eps*H + F`. The axis-norm bound uses `1+16*eps` and `F`. These deliberately
loose envelopes avoid an interval adjustment after every elementary operation.

## Dispatch and fallback

Both actor draw loops clear their shortcut state for every meshlet. A
successful certificate affects the CPU2 facing dispatch only after the
ordinary near and screen eligibility checks. The PVR header, vertex words,
strip parity, EOL bits, and existing lean copy implementation are retained.

Scenery prepares a context lazily, after cost admission, from the matrix
actually loaded after binding the part. Certified groups use the existing lean strip walker, retaining depth,
screen, capacity, clipping, counter, and store-queue handling. Selection reads
the current part's authoritative cull key across a queued chunk flush; the
shared mutable part record may describe an older emitted part at that point.

Existing all-back tests are not broadened by the helper's geometric `Back`
result. It is explicitly not an authorization for a new target-FMAC rejection.

## Qualification results

The final run against `d1bc83cf` passed all seven stages. The compact
[evidence receipt](evidence.json) records source identities, build artifacts,
all 38 production-mode cost comparisons, and the separate cache replay.

| Gate | Result |
| --- | --- |
| Make configuration | 30 controls; strict helper flags and OFF object inventory |
| Numerical helper | 885 cases; 595 independent exact-rational depth, area and span checks |
| Accepted host certificates | 84 complete packet comparisons, all identical |
| Scenery producer | 9 fixtures; default byte identity, optional counts, empty groups and LOD degeneracy |
| Actor caller | 51 scenarios / 460 assertions; ABC1 capacity preservation and both draw loops |
| Scenery caller | 42 metadata-reader controls; routing, packets, counters, clipping and fallback |
| Actual compiled SH4 instructions | 133 complete packet comparisons and 28 FPSCR/admission controls |
| Full target translation units | Both renderers compile in modes 1/2; absent/0 preprocessing and non-debug objects match the base byte for byte |

### Measured cost and limits

The accepted workload is a real tessellated 8x8 grid: 64 cached vertices,
98 nonoverlapping triangles, and 294 references in 98 short strips. The cost
fixture includes one context preparation, admission, each proof and cache scan,
dispatch, the actual actor SQ copy, and the exact CPU2 fallback. The six-group
case reuses its context. These are compiled-code scheduling measurements, not
game, world-renderer, frame-time or console measurements.

| Workload | CPU2 cycles, perfect caches | Front mode cycles, perfect caches | Reduction | Reduction with modeled instruction cache |
| --- | ---: | ---: | ---: | ---: |
| Eligible grid, one group | 22,171 | 13,637 | 38.5% | 23.3% (22,698 to 17,418) |
| Eligible grid, six groups | 132,766 | 62,992 | 52.6% | 45.3% (133,728 to 73,193) |
| Sheared/translated grid, one group | 22,171 | 13,749 | 38.0% | 22.9% (22,698 to 17,490) |

The second cache model replays the same final instruction traces and ELF with
the repository model's cold 8 KiB direct-mapped instruction cache enabled.
Data-cache traffic, DMA and SQ bus costs remain excluded. The gain survives
this standalone link layout, but other renderer code can add cache pressure.
The strict helper object contains **14,340 executable bytes**; that footprint
is material. This replay does not establish full-game instruction-cache behavior.

The cost admission rule declines the small, long-strip, quad-strip and
depth-varying fixtures before preparing cofactors or scanning the cache.
In this driver, admission adds 11 modeled cycles for the small/long-strip cases
and 30 for the depth-varying grid. Those figures exclude native metadata adapter
work and must not be read as the entire renderer's rejection cost.

A deliberately perturbed reciprocal case passes admission but fails the
certificate: **18,445 to 28,159 cycles, a 52.7% increase**, with no bypass and
exact baseline output. The policy cannot guarantee a gain for every admitted
group. Representative asset hit rates and end-to-end scene measurements are
required before enabling the feature in a play recipe. The new knob remains
off by default.

## Reproduce qualification

Use a new output directory. The tests generate synthetic geometry and packets;
they do not need or include game data.

```sh
python3 port/dreamcast/tools/d367/backface_cone_front/qualify.py \
  --output /tmp/re4dc-cone-front-check \
  --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/KallistiOS
```

To reproduce the separate instruction-cache sensitivity from that run:

```sh
python3 port/dreamcast/tools/d367/backface_cone_front/icache_replay.py \
  --target /tmp/re4dc-cone-front-check/target \
  --output /tmp/re4dc-cone-front-icache
```

The qualified compiler is SH4 GCC 15.2.0, with KOS pinned at
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3` and the repository's pinned SH4ZAM
submodule initialized. Supplying `--kos-root` enables complete target
translation-unit builds for both renderers, including byte-for-byte OFF
comparisons against the integration base. Omitting it skips those full-TU
gates; it does not turn a host fixture into a renderer build.

Individual entry points cover the helper, scenery producer, actor caller,
scenery caller, Make rules, and compiled target opcodes. The overall receipt
records exact commands, source identities, stage results, and evidence limits.
The five public test prerequisites restored upstream by PR54 originate from
`2249d3cfa203a7bc679739379cb6d5668edb7ecc`; `qualify.py` verifies their hashes.

The target cost fixture combines the production certificate, the actual actor
lean-copy body, and the original CPU2 assembly fallback. It includes admission,
context preparation, proof construction, cache scanning, dispatch, and emitted
packet copying. It does not include native metadata adapters, matrix formation,
skinning, lighting, FTRV/FSRRA execution, or whole renderer execution. Synthetic
projected caches exercise observed reciprocals without inventing an FSRRA law.
The unchanged repository pipeline model uses perfect caches and no memory,
store-queue bus, PVR, or DMA events.

The primary target build enables `SHZ_STRIP_EARLY_CLIP=1`, matching the updated
CPU2 default. The new front shortcut remains off by default. The scalar opcode
fixtures execute RN with DN=1; RZ is covered by the analytic envelope and mode
admission controls, not by arithmetic emulation. FPU exception-status changes
and traps are not emulated. Invalid PR/SZ mode bits are tested on the production
integer mode predicate, without pretending an invalid FPU C ABI is usable.

Host arithmetic fixtures, execution of compiled target opcodes, pipeline
estimates, Flycast runs, and physical-console measurements are distinct gates.
This candidate must be measured in representative scenes before enabling it
in a play recipe. In particular, global reciprocal extrema lose correlation
when depth varies across a group, and proof overhead can exceed the classifier
work saved on small groups. Performance qualification must include context
preparation, the certificate, cache scanning, dispatch, and vertex copying.
