# Conservative all-front cone shortcut

**Status: disabled experiment; no game-speed improvement demonstrated.** The
revision removes the constant-depth restriction and an overly loose angular
bound, fixes queued cull-state lifetime independently of this switch, and adds
real asset-count and synthetic-camera checks. Those checks still find zero
useful shortcuts in the sampled assets. The grid cost results below are not
evidence of a frame-rate gain.

This extends the existing actor and scenery cone paths with a third outcome:
**front candidate**. A candidate is only sent to the existing lean emitter
after a second check proves that the *actual projected cache* has the same
strict facing sign as `CPU_BACKFACE=2` for every triangle in the group.

The updated integration base is `261c2e3bb098d830107766640fe2fedbd006ff98`
(`t15/int`), including PR54, its enabled CPU2 early-clip default, and the merged
`BACKFACE_ROOMS` hideout fix. The independent cull-only checkpoint is
`dd8981e8de6dadb94997795867c85e8ede9a876f`, directly atop that base without the
front-certificate experiment.
Feature-OFF identity is checked against that corrected baseline: the complete
PR deliberately changes the pre-fix world object even with the switch off. Existing
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

The fixed 256-index/64-strip/four-times-reuse rule is replaced by separate
empirical cost filters for the actor and world emitters. Let `V` be **all
scanned cache vertices**, `I` index references, and `S` complete strips:

| Path | Admit when |
| --- | --- |
| Actor | `16*I + 128*S > 4608 + 80*V` |
| World | `10*I + 168*S > 4800 + 65*V` |

The actor expression is divided by 16 in code. Both filters first require
`3 <= V <= 256`, `I <= 65535`, and `1 <= S <= I/3`, preventing overflow and
unsupported counts. They execute before lazy context preparation. There is
**no constant-depth or zero-extent gate**.

These filters select potential savings in the compiled target cost corpus.
For example, the new actor rule admits 36 vertices/150 indices/50 strips,
which the old rule excluded, while retaining the 25-vertex marginal case on
CPU2. The world coefficients come from its actual count-prefixed walkers,
not from the actor emitter. The extra four world index bits and holes in a
scanned vertex span are covered explicitly.

Neither rule guarantees a certificate or a speedup. A late numerical decline
pays for the proof and then CPU2. Acceptance fraction, adapter costs, memory
traffic and scene frame time still require measurement. The public room
census below remains **zero eligible groups under the revised policy**; the
filter is not loosened until known losing cases run merely to raise a counter.

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
intervals. For a signed lower axis projection `d`, it bounds the perpendicular
component by `sqrt_upper(norm2_upper(q) - square_lower(d))`. The stored axis
has length at most one, so `d` also underestimates projection onto its unit
direction; the subtraction therefore remains conservative. The angular
margin is `cos_lower*d - sin_upper*perpendicular_upper - |det(A)|*radius`.
Replacing the old `sin_upper*L1(q)` term removes its inherent 45-degree limit.
Tests require actual 45–80-degree cone geometry to pass along-axis and tilted
views, and require boundary cases to fall back.

Cone membership, the sphere radius, and the stored minimum normal
magnitude give a lower bound on the ideal projected area. Positive depth is
required for the entire raw-space box, including the transform error bound.
Uncertain determinant, sign, depth, or numerical range returns no certificate.

The second stage pairs each actual cached reciprocal `I_i` with its own raw
vertex. From the same rounded matrix used for that draw, it computes the
scalar approximation `d_i` to ideal depth `W_i` and observes

```
s_i = fl(fl(d_i * I_i) - 1)
R = upper(max_i |s_i| * (1 + 4*eps) + w_error*Imax + 4*eps + F).
```

Here `eps=2^-23`, `F=2^-120`, and `w_error` covers the scalar W dot. This
preserves the `W_i/I_i` correlation: ordinary depth variation no longer looks
like reciprocal approximation error. Direct unsigned world XYZ and indexed
signed actor XYZ both use the existing gathered/projected vertex order.
Incorrect reciprocal pairing is a required rejection control.

This requires no accuracy assumption for `FSRRA`. Bounds on X/Y transform
error, the reciprocal residual, and multiplication rounding give a coordinate
error bound. The raw AABB gives conservative ideal projected-coordinate spans;
adding the coordinate errors bounds the actual edge spans. The determinant
bound includes the target FSUB/FMUL/FMAC operations. The shortcut is allowed only when the
ideal area lower bound is strictly larger than the complete error bound.

The scan uses exact integer-to-float coordinate conversion, a scalar W dot,
and the observed residual per vertex; integer extrema accumulate reciprocal,
coordinate-validity and residual bounds. Four outlined scan variants avoid
per-vertex layout branches and reduce register spills. Loads remain aligned
and alias-safe. Context preparation caches `adj(A)*t` once per
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

Preparation evaluates scalar cofactors and encloses each determinant or
adjugate-translation sum by `64*eps*absolute_expanded_sum + F`, followed by
outward endpoints. Nonzero matrix coefficients must lie in `[2^-40,2^40]`.
This guard ensures that the inner products and cofactor differences cannot
flush before a later large multiplication; only the final products/sums need
the fixed flush allowance. Cone dot endpoints likewise use their uncancelled
absolute-sum bound. The supplementary exact-rational test evaluates these
envelopes in RN and RZ with DN flushing. On SH4, square roots explicitly use
scalar `FSQRT`, avoiding a software-library square root under strict flags.

## Dispatch and fallback

Both actor draw loops clear their shortcut state for every meshlet and consult
the existing `bf_on()` room/material policy before preparing a front context.
With `BACKFACE_ROOMS=1`, room-off draws perform no front proof or acceptance work;
check-mode admission counters still record the declined gate. The merged
scene-open room update and configured room list remain authoritative. A
successful certificate affects the CPU2 facing dispatch only after the
ordinary near and screen eligibility checks. The PVR header, vertex words,
strip parity, EOL bits, and existing lean copy implementation are retained.

Scenery prepares a context lazily, after cost admission, from the matrix
actually loaded after binding the part. Certified groups use the existing lean strip walker, retaining depth,
screen, capacity, clipping, counter, and store-queue handling. The queue-drain
scope now restores the pending part's `cull` on every exit, including aborts.
This fixes both capacity-triggered selection and ordinary/oversize fallthrough
for the existing backface path, regardless of the front switch. The regression
executes the actual production flush lambda and caller branches, and proves
that the original production bodies fail in both paths.

Existing all-back tests are not broadened by the helper's geometric `Back`
result. It is explicitly not an authorization for a new target-FMAC rejection.

### Diagnostics

The original `ABFCF` and `SCN21 front` attempt/candidate/accepted/bad counters
remain. Mode 2 adds gate counters, with no counter work in modes 0/1:

- Actor: seen groups, room/material/direct eligibility, missing ABC1/ABC2, cost,
  context, projected numerical failure and near/screen clipping. Geometric
  declines are the difference between attempts and candidates.
- World: pick-level material/metadata/context gates; retained-group denominator;
  invalid record, cost, prepare, facing/depth and projected numerical declines.

Counters are cumulative. Actor logs follow the existing 300-frame cadence;
world logs follow the 600-frame cadence. `bad=0` is meaningful validation only
when accepted groups are positive. Zero accepted groups also do not imply zero
overhead: failed attempts still execute work.

## Qualification results

The final qualification uses the corrected cull-state baseline `dd8981e8`.
The compact [evidence receipt](evidence.json) records source identities, stage
results, selected target costs, cache sensitivity and the negative asset checks.

| Gate | Result |
| --- | --- |
| Make configuration | 63 controls; strict helper flags, OFF inventory and room-policy coexistence |
| Numerical helper | 988 cases; 607 independent exact-rational depth, area and span checks |
| Accepted host certificates | 102 complete packet comparisons, all identical |
| Count admission | 82 actor/world assertions, including equality, overflow and measured marginal cases |
| RN/RZ scalar envelopes | 4,884 preparation intervals, 1,907 residual bounds, 2,618 cone dots and 610 perpendicular bounds **per rounding mode** |
| Scenery producer | 9 fixtures; default byte identity, optional counts, empty groups and LOD degeneracy |
| Actor caller | 290 scenarios / 2,818 assertions; ABC1 capacity preservation, both draw loops, room transitions and rejection counters |
| Scenery caller | 42 metadata controls; routing, packets, counters, clipping, room transitions and fallback |
| Cull-state lifetime | 147 production-body scenarios per front/room configuration, 882 total; both pre-fix negative controls fail as required |
| Compiled actor instructions | 172 complete packet comparisons, including four raw layouts; 28 FPSCR/admission controls |
| Compiled world instructions | 152 complete packet comparisons; all 30 rejected gated scenarios execute no proof arithmetic |
| Integer interpreter support | 264 unsigned multiply cases, 64 MACH-preservation cases and 94 compiler division-by-three cases |
| Full target translation units | Both renderers compile in modes 1/2 with room selection absent/on; absent/0 preprocessing and objects match the corrected baseline in both configurations |

The scalar envelope experiment uses exact rational arithmetic with RN/RZ and
DN flushing. It supplements the C++ tests; it is not exhaustive proof or target
execution in RZ. Actual compiled scalar opcode execution uses RN with DN=1.

### Modeled cost and limits

The newer accepted workloads are rotated, nonplanar grids with all three depth
coefficients nonzero. They exercise varying depth and actual geometric cones.
The actor fixture uses its existing lean copy and CPU2 assembly fallback. The
world fixture separately uses the actual count-prefixed world walkers, including
full 8-bit indices and scanned ranges containing unused vertices. Both include
admission, context preparation, proof construction, scanning, dispatch and copying.

| Path / rotated nonplanar workload | Groups | CPU2 cycles | Front cycles | Fewer modeled cycles |
| --- | ---: | ---: | ---: | ---: |
| Actor, 6×6 triangles | 1 | 11,371 | 9,328 | 18.0% |
| Actor, 8×8 triangles | 1 | 22,171 | 13,217 | 40.4% |
| Actor, 8×8 triangles | 6 | 132,766 | 73,182 | 44.9% |
| World, 6×6 triangles | 1 | 13,899 | 10,738 | 22.7% |
| World, 8×8 triangles | 1 | 27,051 | 15,962 | 41.0% |
| World, 8×8 triangles | 6 | 162,141 | 89,977 | 44.5% |
| World, 8×8 quad strips | 1 | 15,095 | 13,316 | 11.8% |

These are compiled-code pipeline estimates with perfect caches, no DMA, and no
SQ/bus/PVR timing. The six-group case repeats a group and amortizes preparation;
it is not a six-meshlet game capture. Metadata adaptation, matrix formation,
skinning, lighting and FTRV/FSRRA execution are outside these fixtures.

The separate cold 8 KiB direct-mapped instruction-cache replay exposes an
important limit: the rotated 6×6 actor case rises from 11,939 to 12,509 cycles
(**4.8% worse**) despite its perfect-cache saving. The rotated 8×8 actor case
falls from 22,739 to 16,398 cycles (27.9% fewer). The admission model therefore
does not guarantee a gain under cache pressure. These are the same sealed
instruction traces in one standalone ELF layout, with data traffic still
excluded; they do not establish full-game cache behavior.

Late numerical rejection remains expensive. The admitted, perturbed-reciprocal
64-vertex case increases from 18,445 to 27,743 modeled cycles (**50.4% more**)
while accepting no shortcut. The exact
baseline packets are retained, but failed proofs still cost time. This is why
lowering the cost gate solely to admit the sampled assets would not establish
an optimization. In the separate world fixture, rejected admission alone adds
36 modeled cycles for one group or 236 for six; native adapter work is excluded.

### Public asset checks: no useful hit demonstrated

The selected inputs come from the project's public
[Test22 build assets](https://github.com/lamb2k/re4dc/releases/tag/test-a2477bd2-20261022).
Only selected ZIP members were downloaded; their ZIP CRCs and individual SHA256
hashes were checked. The complete archive was not downloaded or hash-verified.
Geometry stays outside Git. The evidence receipt contains aggregate counts,
input hashes and outcomes.

The scenery census runs the actual producer and compiled `worth_front_world`
predicate. With four groups per meshlet:

| Room | Nonempty groups | Valid proof records | Cost-eligible groups | Added SCCF bytes |
| --- | ---: | ---: | ---: | ---: |
| r10c | 4,230 | 3,412 | 0 | 37,152 |
| r111 | 6,116 | 5,282 | 0 | 53,568 |
| r200 | 2,551 | 1,822 | 0 | 22,656 |
| **Total** | **12,897** | **10,516** | **0** | — |

A one-group-per-meshlet conversion also produces zero cost-eligible groups in
all three rooms. This is an asset/count census, not a camera acceptance or
frame-time measurement. The selected package does not supply the requested
r101-cross world input, so it does not replace that gameplay check.

Four actor groups from Leon and Ganado were also checked under nine synthetic
camera poses each. Their positions, indices and proof metadata came from the
actual converter and proof builder, using a **hypothetical enlarged conversion
buffer** to allow cone splitting. These are not claimed to be the assets or
poses active in a running game. The original public FE03 streams contain no
ABC1 tails; the original-capacity reconversion also did not produce them.

All 36 poses are strictly front according to the exact oracle. Even with cost
admission deliberately bypassed, **none receives a projected certificate**:
eight fail the geometric test and 28 fail the final numerical bound. All 72
baseline/diagnostic packet comparisons pass. The synthetic camera construction
and observed reciprocal cache do not model animation or target FTRV/FSRRA.
The experiment shows that removing constant depth alone has not solved the
practical acceptance problem.

### Memory and release status

The strict helper contains **12,456 executable bytes**, down from 14,340 in the
original PR. This is an object-text measurement, not a linked-game RAM delta.
The world front trailer format is unchanged and still has the room costs shown
above. The helper reduction does not resolve the reported approximately 1.3 KiB
headroom in the r100 cliff cutscene build.

No full-game link, Flycast scene, physical console, frame-time or r100 RAM gate
passed in this revision. The feature remains off by default and is not enabled
in a play recipe. The cull-state lifetime fix is independently useful; the
all-front experiment still needs a cheaper, less conservative proof that works
on representative game assets before release use can be justified.

## Reproduce qualification

Use a new output directory. The main tests generate synthetic geometry and
packets; they do not need or include game data.

```sh
python3 port/dreamcast/tools/d367/backface_cone_front/qualify.py \
  --output /tmp/re4dc-cone-front-check \
  --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/KallistiOS
```

To reproduce instruction-cache sensitivity from that run:

```sh
python3 port/dreamcast/tools/d367/backface_cone_front/icache_replay.py \
  --target /tmp/re4dc-cone-front-check/target \
  --output /tmp/re4dc-cone-front-icache
```

The qualified compiler is SH4 GCC 15.2.0, with KOS pinned at
`804b3195ebd1a06a27cc2b3a5eacf7a2429040a3` and the repository's pinned SH4ZAM
submodule initialized. Supplying `--kos-root` enables complete target
translation-unit builds for both renderers and the separate world target cost
fixture. Omitting it skips those gates. OFF identity uses the unconditional
cull-fix checkpoint; it does not assert that the complete PR leaves the old,
incorrect world object unchanged.

Individual entry points cover Make rules, numerical bounds, the RN/RZ scalar
envelopes, scenery production, actor integration, world integration and compiled
actor/world opcodes. `admission_study.py` explores triangle/quad/row strip costs;
`asset_census.py` accepts an external native room directory and publishes counts;
`asset_pose_study.py` accepts an external converted-group JSON file and publishes
synthetic-camera outcomes. Use each script's `--help` for its inputs. Asset files
and exported raw geometry should remain outside the repository.

The overall receipt records exact commands, source identities, stage results,
and evidence limits. The five public test prerequisites restored upstream by
PR54 originate from `2249d3cfa203a7bc679739379cb6d5668edb7ecc`;
`qualify.py` verifies their hashes. The primary target build enables
`SHZ_STRIP_EARLY_CLIP=1`, matching the updated CPU2 default. FPU exception-status
changes and traps are not emulated. Invalid PR/SZ bits are tested through the
production integer mode predicate without pretending an invalid FPU C ABI is
usable. Host fixtures, compiled-opcode execution, pipeline estimates, emulator
runs and physical-console measurements remain distinct evidence.
