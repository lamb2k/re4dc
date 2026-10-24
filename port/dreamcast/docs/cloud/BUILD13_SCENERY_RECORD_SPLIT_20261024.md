# Build 13 — meshlet-size sweep and separate emit/bounds records

Date: 2026-10-24. Candidate: `SCENERY_RECORD_SPLIT=1`, default **0**.
Validation base: `origin/t15/int` at
`9b248c5b40a49e4c954ea834fdf665fdbbc314f0`, including landed Builds 10–12.
Publication base: `fc53531852ed979394ff3aefb6fddbefcfa825fb`. The only
intervening change is a `KNOWN_ISSUES.md` documentation link; every measured
source and test input is unchanged. The publication preserves that update;
`tools/cloud/build13/receipts/publication-base.json` records the comparison.
Branch: `codex/scenery-record-split-20261024`. The coordinator owns merges.

This implements the Build 13 entries in the [cloud queue](CLOUD_AGENT_QUEUE.md)
and [world plan](WORLD_2MS_PLAN_20261024.md). It does not establish a 2 ms world,
a console cache-miss reduction, or an accepted replacement for r101.

## Result and decision

The existing builder already supports a meshlet vertex limit of 3–256 and
defaults to 64. This build qualifies **32, 64, 128 and 256** through that real
exporter. It leaves the default and existing packing algorithm unchanged.
Larger limits reduce setup and repeated vertex work in the public fixture,
but alter strip order and culling granularity. The order-changing translucent
variants require separate appearance acceptance.

The new physical representation is explicit **R4IM v4**: each existing
28-byte meshlet record becomes a 16-byte emit record plus a 12-byte bounds
record. The two tables are individually aligned to 32 bytes. This changes
which lines emission needs; it does not eliminate 12 bytes per meshlet or
reduce total world payload by 43%. Selection can consume both tables, and
sparse selected IDs can remove the emission-locality advantage.

The split converter preserves every logical record, vertex/index/strip byte,
ordered corner, material, source identity, placement and LOD at a given size.
The ordinary v1/v2/v3 `MeshPackage` implementation remains unchanged. The new
world-only reader uses the split tables directly; it does not rebuild a
28-byte array each frame or allocate a temporary reconstructed package.

**Target and packet evidence:** 32 raw OFF `.ii`/object identity comparisons,
25 target cost cases, and 1,993 normal layout/fallback packet comparisons
plus 390 inherited cases pass. A separate active-census ASan/UBSan primary
run passes 1,249 layout/fallback and 78 inherited comparisons. Dense emit
lines decrease, but selection/accessor work can increase. The candidate
remains off pending complete-world console and appearance qualification.

## Runtime boundary and pairing

`SCENERY_RECORD_SPLIT` is independent of `SCENERY_EMIT_PREFETCH`. Primary
cost comparisons use prefetch 0; composition is a separate compile/output
gate. Existing select-only, lean-replay, batched-submit, UV-snapshot and
lean-selection choices remain independently selectable.

The runtime looks for `ps2-world-split.re4mesh` beside the original world,
retaining ordinary `ps2-world.r4pw` placement/material policy. The candidate
records the actual ordinary mesh body CRC and extent. The loader verifies
those against the original file header, then checks the candidate's own
physical CRC and reader validation before admission. Missing alternates and
pinned ownership/movie cases retain the ordinary path. Read the actual
`SCNSPLIT` admission and `PS2SG` result rather than inferring admission from a
requested build flag.

Use the matched comparison overrides:

```text
PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0
```

Both control and candidate use the same original-policy assets for that
comparison. Keep `PS2_INTERIOR_ACTORS` consistent with its existing enemy
visibility dependencies. Mesh-bound world-reduction, interior, PVS, cone,
piece-state and deduplication certificates are not impersonated or rebound.
Build 12 local-indexed/direct-strip composition is explicitly rejected at
Make and C preprocessor boundaries; it needs a new versioned lineage
contract and its own validation. Build 12 behavior remains intact when
record splitting is absent or 0.

The original gather allocation, transformed-vertex cache, clipping and
submission ownership remain available. No heap saving is claimed from the
record split. Gameplay, AI, collision, source state and existing retirement
mechanisms are outside the changed representation.

## Binary and tooling contract

The [tool README](../../tools/cloud/build13/README.md) gives the complete
schema and commands. The 80-byte main header and 32-byte LOD header remain;
the main version is 4. `meshlet_offset` locates Emit16;
`reserved[1]` locates Bounds12; `reserved[2:4]` hold the original body CRC and
extent. Bounds begins at `align32(emit_offset + 16 * meshlet_count)`.
The physical CRC covers bytes `[80:]` as in the ordinary format.

The standalone converter accepts the final ordinary package after any
supported existing grouping pass. It retains the complete original raw
index/strip section, including nonsequential `first_strip` placement. It
does not assume the canonical per-meshlet index order that blocked the
owner's first private Build 11 r101 attempt. A public nonsequential-offset
control proves that narrower property; private Build 13 admission remains
unrun.

Only R4SG is rebound after validating its original mesh/policy binding,
group boundaries, index and bounds enclosure. Its supplied record payload
is byte-identical. Without a source R4SG, the tool uses the existing
consecutive preserve-order grouping policy. Unknown siblings, appended
runtime tables, incompatible reserved words, stale proofs and unsupported
sidecars fail closed. It issues no lost-part or visibility PASS certificate.

The converter and reader enforce the u16 global meshlet-ID limit and the
part's aggregate selected-Pick reservation, including the maximum level
size of every referenced cluster. They retain the original conservative
part-pool separation rule. The ordinary runtime's 262,144-byte group-file
cap remains relevant before the theoretical 65,536-meshlet limit.

## Meshlet-size sweep through the production exporter

The public source is a valid full-wrapper-v5 package with three wavy
20 × 12 grids, OP/PT/TR materials, twelve cluster levels and two placements.
The actual `SpanPackage` reader admits the generated source, and the actual
ordinary `MeshPackage` reader admits each exported size. No recovered asset
or private capture is included.

### Resident data, every LOD included

| Vertex limit | Resident meshlets | Ordinary mesh bytes | Split mesh bytes | Strip headers | Stored vertex records | Repeated stored records within parts | Sum of local vertex inputs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 75 | 21,312 | 21,344 | 95 | 1,386 | 666 | 1,514 |
| 64 | 27 | 15,488 | 15,520 | 62 | 1,020 | 300 | 1,148 |
| 128 | 18 | 13,056 | 13,056 | 62 | 840 | 120 | 968 |
| 256 | 12 | 11,456 | 11,456 | 62 | 720 | 0 | 848 |

These are resident all-LOD totals, not work in one frame. R4SG bytes are
4,832 / 1,760 / 1,184 / 800 respectively; R4PW is unchanged. The split adds
32 / 32 / 0 / 0 padding bytes without changing the 28-byte logical payload.

### One unique mesh at LOD0, every part visible

| Vertex limit | Meshlet setup calls | Strip headers | Submitted corners | Local transformed inputs |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 66 | 66 | 1,386 | 1,386 |
| 64 | 18 | 33 | 1,320 | 1,020 |
| 128 | 9 | 33 | 1,320 | 840 |
| 256 | 3 | 33 | 1,320 | 720 |

Drawing both public placements would double these work counts and visit
six parts. It does not double the unique physical data-line footprint.
Six polygon headers is an upper bound for that synthetic workload, not an
observed header-cache result. Meshlet count and polygon-header count are
different quantities.

The 32-vertex case adds 33 strip segments and 66 corners relative to 256.
The separate 401-corner strip control produces 14 / 8 / 4 / 2 segments and
427 / 415 / 407 / 403 corners, preserving winding with exactly two repeated
corners at each added restart. All twelve part/cluster/LOD oriented-triangle
multisets agree across sizes. At 32/64/128, the three LOD0 ordered streams
differ from 256, including the translucent part. Their ordered TA/appearance
identity is not claimed. Within any one size, record splitting preserves
ordered streams exactly.

## Architectural traffic and target scope

The offline dense-record address audit shows:

| Vertex limit | Ordinary emit-prefix lines | Split emit lines | Ordinary full-record lines | Split emit + bounds union |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 66 | 38 | 66 | 67 |
| 64 | 24 | 14 | 24 | 25 |
| 128 | 16 | 9 | 16 | 16 |
| 256 | 11 | 6 | 11 | 11 |

These are 32-byte address unions, not measured cache misses, transfers or
latency. Per-record line sums and sparse-ID cases are separate in the
[layout receipt](../../tools/cloud/build13/layout-receipt.json).

The target harness compiles the actual full renderer translation unit with
Make-derived flags, retains the real selection and replay setup, and treats
`emit_pick` geometry as an observed external edge. Transform, clipping, TA,
GPU and D-cache latency are excluded. A separately labelled metadata probe
reads all sixteen logical emit bytes through production accessors and writes
four test observation words. Its cycles are probe cycles, not the renderer's
emission time. Selection-plus-probe traffic uses a true address union and
distinct instruction ordinals, without double-counting shared lines.

The comparison distinguishes ordinary knob-off, knob-on ordinary fallback,
and knob-on split storage. It includes dense, sparse, reverse-order,
bounds/partial-group and empty-retained-range controls, plus all twelve
production-exporter part/size cases. The actual R4PW keys, dimensions, pass,
cull and vertex-alpha mark feed the exporter cases. Source/candidate logical
identity, source hashes and group payload equality are validated before
timing.

### Final target results

All **25 cases pass**: thirteen synthetic cases and twelve real exporter
part/size cases. Each timing entry below is **ordinary / enabled ordinary
fallback / split**. Warm scheduling assumes perfect I/D caches and no
DMA, SQ service or memory-bus cost. The complete receipts also give cold
8 KiB I-cache results, dynamic instructions and every traffic region.

| Case | Selection warm cycles | Replay/setup warm cycles | Metadata-probe warm cycles |
| --- | ---: | ---: | ---: |
| One fully inside pick | 411 / 477 / 442 | 1,046 / 989 / 988 | 43 / 79 / 73 |
| Partial group range | 1,845 / 1,912 / 1,874 | 1,046 / 989 / 988 | 43 / 79 / 73 |
| 320 fully inside picks | 4,877 / 11,004 / 9,374 | 4,874 / 4,817 / 4,816 | 8,018 / 11,882 / 9,962 |
| Six picks with repeated plane tests | 4,720 / 4,907 / 4,829 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 |
| 32 dense metadata IDs | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 |
| 32 sparse metadata IDs | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 |
| Exporter 64, part 0, six picks | 534 / 695 / 635 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 |
| Exporter 256, part 0, one pick | 464 / 530 / 495 | 1,046 / 989 / 988 | 43 / 79 / 73 |

The 32-ID dense/sparse/reverse controls first run the same actual selector
over 64 inside meshlets, then install a declared 32-ID replay/probe list.
Their selection cost is not the cost of discovering only 32 visible IDs.
Indexed cases have the same setup costs because geometry/gather is outside
this fixture; this is not evidence that indexed and plain emission cost the
same.

At 320 dense picks, the metadata union falls from **280 to 160 lines**,
while selection rises from **4,877 to 9,374 warm cycles**. The enabled
ordinary fallback costs 11,004 selection cycles and still touches 280
metadata lines. At 32 sparse IDs the union falls only from 40 to 32 lines,
versus 28 to 16 for dense IDs. For six picks requiring repeated plane tests,
emit-prefix lines fall from 5 to 3 but the combined selection/metadata union
remains **6 lines**. A partial one-meshlet group can grow from one combined
line to two. These results keep accessor/selection overhead and bounds traffic
visible; the split is not accepted as a performance win.

### Traffic and cold-I example

The real 64-vertex exporter, part 0, gives the following phase counts.
Each row starts its own cold-I run; cold figures must not be added and
called one cold frame. Loads/stores and read/write bytes are cached RAM
demand accesses. Lines are the union of all touched RAM, including stack
and harness state, rather than just the meshlet metadata.

| Phase / arm | Warm / cold-I cycles | Loads / stores | Read / write bytes | 32-byte RAM lines |
| --- | ---: | ---: | ---: | ---: |
| Selection, off | 534 / 1,096 | 158 / 105 | 601 / 366 | 42 |
| Selection, on ordinary | 695 / 1,369 | 201 / 109 | 768 / 382 | 47 |
| Selection, on split | 635 / 1,271 | 189 / 107 | 718 / 374 | 44 |
| Replay/setup, off | 1,106 / 1,717 | 190 / 395 | 692 / 1,508 | 63 |
| Replay/setup, on ordinary | 1,049 / 1,667 | 198 / 343 | 714 / 1,315 | 65 |
| Replay/setup, on split | 1,048 / 1,666 | 200 / 343 | 718 / 1,315 | 64 |
| Metadata probe, off | 168 / 212 | 37 / 24 | 136 / 96 | 15 |
| Metadata probe, on ordinary | 264 / 368 | 68 / 31 | 255 / 124 | 18 |
| Metadata probe, on split | 228 / 320 | 63 / 31 | 233 / 124 | 15 |

The selected metadata itself occupies 5 / 5 / 3 lines in this example.
The metadata probe writes observation words and includes accessor costs; it
is a bounded consumption/traffic experiment, not a replacement measurement
of the actual transform and emit kernel.

### Explicitly MODELLED whole-frame scenario

Assume 200 MHz, the public mesh at LOD0 in both placements, a separate
selection and replay/setup invocation for each of the six part visits, and
**30 ms of assumed other work** including every excluded geometry, gameplay
and rendering cost. Price the measured warm selection and replay/setup
only: `30 ms + 2 * sum(three parts' cycles) / 200,000`. The observer probe
is excluded. The imposed 30 ms is not measured and deliberately does not
estimate transform changes between sizes.

| Vertex limit | Off setup cycles for six visits | Split setup cycles for six visits | MODELLED frame off | MODELLED frame on ordinary | MODELLED frame on split |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 12,336 | 13,938 | 30.06168 ms | 30.07392 ms | 30.06969 ms |
| 64 | 9,840 | 10,098 | 30.04920 ms | 30.05232 ms | 30.05049 ms |
| 128 | 9,372 | 9,378 | 30.04686 ms | 30.04827 ms | 30.04689 ms |
| 256 | 9,060 | 8,898 | 30.04530 ms | 30.04557 ms | 30.04449 ms |

This is an arithmetic setup-only scenario, **not r101, not a complete world
measurement and not a 30 fps qualification**. At the existing 64 default,
split setup is 258 cycles worse across these six visits (0.00129 ms in this
model). A console benefit would have to recover that overhead through actual
cache behaviour and the full emit path. The larger-size fixtures also change
ordered geometry and visibility granularity; their smaller setup totals alone
do not accept a new size.

### Code, stack and memory

Complete matched production translation-unit compilation gives:

| Metric | Split 0 | Split 1 |
| --- | ---: | ---: |
| `native_static.o` executable section bytes | 62,510 | 66,860 |
| Allocated section bytes | 91,358 | 97,026 |
| Zero-fill bytes | 17,067 | 17,067 |
| Largest individual function stack | 8,880 | 8,896 |
| `ps2_open` stack | 592 | 684 |
| Selector stack | 260 | 236 |
| `chunk_emit` stack | 128 | 132 |

These are per-function compiler stack values, not an entire game call-chain
bound. Resident payload and R4SG sizes appear above; no temporary full AoS
copy is allocated, and the existing gather storage is retained.

## Reproducibility, identity and limits

The builder gate compares the normal mesh, R4PW and JSON byte-for-byte with
the pinned baseline for absent split, explicit 0 and explicit default 64.
Both landed Build 12 flags also retain their normal and alternate bytes and
reports with split absent/0. Combining them with split 1 rejects before
source access or output.

The final tools receipt covers 21 malformed/stale/unsupported inputs, two
early mixed-format flag refusals, ordinary v2/v3, supplied spatial-group
output, preserved raw index placement, strict lineage and strip parity.
It records actual host process times/RSS as conversion evidence only.

The actual-reader controls pass **23 cases** both normally and with
ASan/UBSan: ordinary/split admission at all four sizes plus malformed
layout, source binding, capacity, ownership, and checksum-correct invalid
R4SG ranges and bounds. An invalid R4SG keeps the valid v4 package on the
whole-meshlet path. A present invalid mesh alternate rejects the native PS2
package; it is not counted as ordinary candidate admission.

The complete target gate passes **32 raw `.ii`/object OFF identity
comparisons**, two unaffected `native_ui` ON identities, four enabled
profiles (primary, composed, eager and active census), and **21 Make
rejections**. Absent/0 identity includes both already-landed Build 12 enabled
profiles. All active-census hooks resolve in a partial link and the census
core contains zero FPU instructions. A final linked game image is outside
this public source fixture.

The source-extracted production geometry gate passes **1,993 layout/fallback
comparisons plus 390 inherited comparisons** across five bounded profiles.
The primary matrix is four sizes × thirteen scenarios × three passes × four
LODs, comparing ordinary knob-off, enabled ordinary fallback and enabled v4
within each size. An independent active-census ASan/UBSan run passes **1,249
layout/fallback plus 78 inherited comparisons**. All ordered TA/accounting
words and SQ lock/unlock counts agree; primary output digests also agree
between the ordinary and census/sanitizer runs.

Every one of the 48 size/pass/LOD inside-view cases emits nonempty geometry
(16–924 corners), as do the near/far clipping cases. Primary positive coverage
includes 254 near-clipped strips, 254 far-clipped strips, 562 screen-culled
strips, 936 indexed picks, 648 nonempty partial picks and 48 actual low-tail
reserve-abort unwinds. Offscreen and `nr==0` cases emit no geometry. The
low-tail case proves the existing refusal after header submission, one abort
and balanced SQ ownership. A checksum-correct malformed R4SG is refused and
then produces exactly the same packets as the missing-group whole-meshlet
fallback. This is not a cross-size order claim, a full-scene selector test,
or an SH4-vector bit-exact proof: picks/cameras are controlled and host
floating-point kernels stand in for target vector instructions.

The target interpreter needs `DIV0U` for the compiler's untimed package
validation helper. The local test-only extension implements exactly that
instruction and checks all eight incoming M/Q/T combinations, preservation
of other state, one retired instruction and zero data traffic. `DIV1`
remains unsupported and fails closed. This follows the
[Renesas SH-4 Software Manual](https://www.renesas.com/en/document/mas/sh-4-software-manual),
section 9.18, printed page 238. It adds no runtime assembly.

Reproduction commands and the full case table are in
[target-cost evidence](../../tools/cloud/build13/target-cost-evidence.md).
The checked-in cost-build, target-costs and target-controls receipts use the
existing lossless `RE4DC_COMPACT_RECEIPT1` encoding; expansion retains every
metric, command, tool hash and source hash, with the raw receipt SHA256 and
extent recorded. Reader and layout receipts are also committed.

No new runtime assembly or linker work is introduced. The cost fixture
reuses established test-only return/trap and link infrastructure. Compiler,
SDK, flags, source hashes, code/stack and model settings are recorded in the
target receipts. Modelled scheduling and architectural line touches do not
measure Dreamcast data-cache conflicts, bus stalls, SQ service or a complete
game frame.

## Owner handoff

1. Generate matched ordinary/split packages from the **actual final** private
   ordinary world. Keep source and output hashes, source identity and R4SG
   admission. Do not silently drop extra companions to satisfy the tool.
2. Collect the selected-ID density, size/reuse/partial-pick distribution and
   both complete world and frame time. The Build 10 drawn-frame denominator
   is the common accounting contract; do not scale every meshlet by an
   indexed-gather fixture when most admitted picks are already plain.
3. Test the size variants separately from splitting. Check translucent order,
   camera motion, bounds/clipping and source-feature visibility before any
   quality decision. Retain the 64 default until a measured accepted size
   wins on the real workload.
4. Run matched console baseline/candidate/baseline, RAM and ownership/room
   transition checks, appearance and STRICT gameplay gates. Compare the
   combined selection/emission result. Neither fewer emit lines nor a
   smaller synthetic setup total alone accepts this switch.

The owner has reproduced Build 11's public gate but reported two private
bundle refusals: noncanonical per-meshlet index placement at r101 and stale
R4ID binding at r103. Those remain explicit separate follow-ups; this build
does not repair a stale release companion or claim private Blender success.
The route to an essentially free world still includes the plan's sparse
feasibility proxy and deliberate visual reconstruction, followed by console
measurement of the complete world path.
