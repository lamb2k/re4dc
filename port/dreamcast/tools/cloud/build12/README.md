# Build 12: local vertex data and sequential strip inputs

This directory contains public controls for two default-off world-data
experiments. Read the [Build 12 report](../../../docs/cloud/BUILD12_SCENERY_DATA_VARIANTS_20261024.md)
for the measured tradeoffs and remaining local-owner acceptance. The
validation base is `057e00a248c9ed473d0b3377a0ce14b0b2f5186d`, which includes
Build 10's world census. Publication uses the newer integration commit
`4efca35b98cdcdd845122c279321b848b621e029`; its only difference is coordinator
queue documentation. The publication-base receipt records that all target and
builder inputs remain identical and that those upstream answers are preserved.

## Runtime contract

| Make knob | Candidate file | Representation and execution |
| --- | --- | --- |
| `SCENERY_LOCAL_INDEXED=1` | `ps2-sli1.re4mesh` | Expand each shared-pool gather offline into dense, local 12-byte vertices. Keep existing local strip indices and the ordinary transform-cache emitter. |
| `SCENERY_DIRECT_STRIPS=1` | `ps2-sds1.re4mesh` | Expand strip corners in their existing order. Qualified whole meshlets transform directly into the current store-queue slot using the existing transform kernel. |

Both knobs default to `0` and are mutually exclusive. These are ordinary prelit
R4IM v3 plain/local meshlets with an explicit `SLI1` or `SDS1` header marker,
not a new file version or a replacement renderer. The generic `MeshPackage`
definition and ABI are unchanged. The converter accepts supported prelit v2/v3
inputs and preserves the source mesh, policy, quantization, surfaces, LOD
choices, material/texture identities, colors and UVs.

SDS1 splits only between existing complete strips when a local meshlet would
exceed 256 vertices. No existing strip is split or reordered. Child meshlets
retain the parent's conservative bounds and original part/LOD membership.
Optional R4SG records are mapped from the supplied, validated source groups:
same group membership and selection bounds, with new byte ends/local ranges.
Do not run a strip-reordering tool on an SDS1 candidate. Its sequential index
invariant is checked before runtime admission.

The loader keeps the standard `ps2-world.re4mesh` and `ps2-world.r4pw` paths.
When requested, it looks for the alternate next to them. The candidate's
source CRC/extent must match the actual standard header; its physical body CRC,
ordinary package ranges, dense local ranges and bound enclosure are checked
separately. SDS1 also requires sequential indices that consume every local
vertex exactly once. Existing SDO3 or other alternate encodings are outside
this conversion's input contract. Both converter and reader reject more than
65,536 meshlets: queued picks store absolute IDs in 16 bits. Sequential
expansion cannot wrap a new meshlet ID onto an earlier meshlet.
They also bound each part's worst selected population by its reserved pick
capacity: sum the largest level of each referenced cluster and require that
sum to fit `part.meshlet_count`. Individually in-range overlapping clusters
cannot overrun the part-sized selection reservation.

The fused path requires a supported perspective camera, an admitted SDS1 PS2
world, the ordinary direct SQ owner, a full pick, the existing lean/scheduled
transform configuration, and a conservative bound entirely inside all screen
and depth planes. Strip sizes are checked before any direct write. Partial
picks, empty picks, clipping, oversized strips, unsupported kernels, unmarked
packages and TA-hash/CPU-backface diagnostics retain the existing path. The
SQ owner, material/header sequence, direct-account totals and fallback cache
allocation remain shared with that path.

The 3,072-byte gather allocation remains reserved. A avoids its gather traffic;
B also avoids transformed-cache traffic on its fast path. Neither statement
is a heap-capacity saving. Sequential expansion can enlarge payload residency
and increase transforms when strip vertices repeat. The constrained target
controls show that the reused per-corner kernel's setup and spills can make B
more expensive even after it removes transformed-cache traffic.

## Matched configuration and admission

Both control and candidate need the following adjustments to the current
release recipe:

```text
PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0
```

Keep the source policy and its original texture mapping matched to those
settings. Texture-remapped release assets are outside this experiment's
accepted input. Disabling a feature only on the candidate is not a layout
comparison. Keep the actor-visibility configuration required by the recipe;
`PS2_INTERIOR_ACTORS` is distinct from the world-cell knob above.

The Make fragment additionally rejects `WORLD_VERT`, `SCENERY21_AB`, scenery
dedup, SCCN cones, SCPS piece state and PVS combinations. Existing physical
mesh certificates are not rebound to the source fingerprint. `WORLD_RECT21`
is explicitly rejected; no substitute certificate or policy-lineage API is
introduced by this build. The source-placement OCCL path keeps its unchanged
R4PW/source identity contract.

Pinned packages keep their base representation: r11f under the movie arena
or r11f-owner modes, r100 under the S30 movie arena mode, and r200 under the
source-owner mode. A missing alternate also retains the standard package.
The `SCNVAR` log records `requested`, `admitted`, physical `actual_crc`, source
CRC, package bytes and the retained gather reserve. Record the successful
admission row with a measurement. An `admitted=base` run is a fallback control,
not a candidate performance result. Invalid candidates follow the existing
native load-refusal/fallback behavior.

Record the `PS2SG` row too: candidate mesh admission does not imply group
admission. The existing R4SG loader's maximum is 262,144 bytes; expansion can
cross it or exhaust the available sidecar allocation. Require `groups=ok` for
both grouped arms, or use matching whole-meshlet controls when groups are
absent/rejected. A different selection path is not a layout-only timing pair.

## Produce an alternate without rebuilding LODs

Run commands from the repository root. The input paths below are placeholders
for the local owner's existing matched packages. The output directory must be
new; the standard mesh and policy are not overwritten.

```sh
python3 port/dreamcast/tools/scenery_data_variants.py \
  /path/r101/ps2-world.re4mesh /path/r101/ps2-world.r4pw \
  --source-groups /path/r101/ps2-world.r4sg \
  --scenery-local-indexed --out /tmp/r101-sli1

python3 port/dreamcast/tools/scenery_data_variants.py \
  /path/r101/ps2-world.re4mesh /path/r101/ps2-world.r4pw \
  --source-groups /path/r101/ps2-world.r4sg \
  --scenery-direct-strips --out /tmp/r101-sds1
```

Each directory contains its alternate mesh, the remapped alternate R4SG when
supplied, a conversion report and `SHA256SUMS`. Stage the alternate beside the
unchanged standard files; the shared policy keeps its standard filename. When
no source R4SG is supplied, no alternate groups are fabricated. Use the same
whole-meshlet setup in the matching control.

The existing `ps2_world_r4im.py` builder also accepts mutually exclusive
`--scenery-local-indexed` / `--scenery-direct-strips` options. It writes the
standard primary mesh/policy unchanged and adds the selected alternate beside
that output. The exact-blob postprocessor above is preferred when preserving
an existing package and its strip-group decisions.

## Build 10 census composition

SDS1's eligibility work is Selection. Its fused transform-and-SQ loop is
charged as **one exclusive Transform interval, including its direct output
work**. This is not a pure transform column comparable with a cached arm's
Transform column alone. Compare total world time and relevant combined phases.
No per-corner clock call or estimated transform/submit split is introduced.

The successful fused path counts its actual transformed inputs and walked
strip inputs once. The existing central direct-account path counts actual
emitted corners once; existing material/header hooks retain their ownership.
Clipping/partial/diagnostic fallback keeps the original phase/counter hooks.
The census remains fully compiled out when absent or zero.

## Public controls

All generated geometry is synthetic. New output directories are required for
each run so receipts remain bound to the source hashes recorded at start/end.

```sh
python3 port/dreamcast/tools/cloud/build12/check_layout.py \
  --output /tmp/b12-layout
python3 port/dreamcast/tools/cloud/build12/check_emitter.py \
  --output /tmp/b12-emitter-off
python3 port/dreamcast/tools/cloud/build12/check_emitter.py \
  --census --output /tmp/b12-emitter-census
python3 port/dreamcast/tools/cloud/build12/check_emitter.py \
  --census --sanitize --output /tmp/b12-emitter-census-sanitized
python3 port/dreamcast/tools/cloud/build12/check_emitter.py \
  --reader-capacity-only --output /tmp/b12-reader-capacity
```

`check_layout.py` covers exact ordered corner bytes, mesh/part/LOD remaps,
original R4SG membership/bounds, metadata and malformed-input controls. It
also invokes the real existing world builder to check absent-option identity
and additional alternate output without changing the primary mesh/policy.

`check_emitter.py` reuses Build 5's source-extracted production emitter,
gather/borrow, clipping, replay and controlled TA/SQ/header sink. Its four
converted shapes include repeated corners, unused vertices and the `limit`
case with 255+3 strip corners, which requires multiple SDS1 child meshlets.
The 60 scenarios per shape cover OP/PT/TR, two LOD levels, inside/near/far/
offscreen geometry, partial groups, empty picks, oversized-strip fallback,
mirrored and nonuniform matrices, and changing material/UV snapshots.

Each run verifies 480 base/candidate TA-word and external-accounting pairs,
156 comparisons over the existing 78 unmarked cases, and seven malformed
files through the actual C++ adoption/variant validator and extracted CRC.
The TA-hash control proves the diagnostic fallback does not use fused writes.
Changed internal meshlet/batch counts are recorded rather than called equal.
The reader-only control admits eight small converted A/B packages and an
ordinary valid 65,536-meshlet SDS1 package, then requires the specific capacity
refusal for 65,537 meshlets. A second boundary admits overlapping clusters
with at most 160 selected picks in a 161-meshlet part, then rejects two
161-meshlet cluster selections that would append 322 picks into that
reservation. It can also run with `--sanitize`. This bounded control records
the final capacity guards without repeating the geometry matrix; the receipt
preserves that amendment and the original geometry hashes.

With `--census`, Build 10's real core runs inside an active world/tick scope.
Its existing independent packet observer verifies corner/header totals,
failure accounting and an exact exclusive phase/residual partition. The
fully fused cases also require `Transformed == StripInputs == Corners` and a
Transform interval. Compare `unmarked_output_sha256` and
`variant_output_sha256` between census-off/on receipts to verify the observer
has not changed any TA/accounting output. ASan/UBSan covers the same current
code; leak detection is disabled because managed process inspection is not
available in the test environment.

The target controls require the pinned KOS compiler/SDK described in the
report. Set the three task-specific variables to the local compiler, KOS and
SH4ZAM paths:

```sh
python3 port/dreamcast/tools/cloud/build12/build_controls.py \
  --sh4-cxx "$B12_SH4_CXX" --kos-root "$B12_KOS_ROOT" \
  --sdk-root "$B12_SH4ZAM_ROOT" --output /tmp/b12-target-build
python3 port/dreamcast/tools/cloud/build12/target_cost.py \
  --sh4-cxx "$B12_SH4_CXX" --kos-root "$B12_KOS_ROOT" \
  --sdk-root "$B12_SH4ZAM_ROOT" --output /tmp/b12-target-cost
```

`build_controls.py` compares complete preprocessed bytes and target objects
against the integration base for absent/zero knobs, checks Make dependencies
and refusals, compiles supported candidate configurations, and checks actual
census/QA composition. `target_cost.py` executes constrained real SH4 kernel
opcodes to count architectural memory traffic and synthetic warm/cold I-cache
cost. Its FP controls qualify identity-matrix FTRV and reciprocal input 1
only. It assumes perfect D-cache, no DMA and zero SQ service cost. It cannot
establish general FTRV/FSRRA equivalence, data-cache-miss savings or console
frame time.

Compact final public receipts are in [receipts](receipts). The
`compact_receipts.py` helper losslessly interns repeated data;
`expand_receipt(json.load(...))` restores the original parsed JSON. Source and
extracted-body hashes, exact output digests, per-case observations and original
detailed-receipt hashes are retained.
The controls do not execute private game assets, full filesystem/movie
retirement, a complete game link, a PVR frame or a gameplay trace. Console
timing, look/STRICT acceptance, package residency and transition behavior
remain the local owner's gates before selecting either representation.
