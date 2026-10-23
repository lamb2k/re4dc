# Build 3: cheaper world selection — 2026-10-23

Base: `origin/t15/int`, `75229c8fa54d4a939095666036c8ee1c8f52e2fe`.
Branch: `codex/world-select-lean-20261023`.
Option: **`SCENERY_SELECT_LEAN2=1`**, default **0**, requires `SCENERY_CHUNK`.

## Result: model estimate

The main eight-meshlet/four-group case falls **6,846 → 5,864 warm-I cycles
(−14.3%)**, with **9,834 → 7,200 architectural data bytes (−26.8%)**. The
explicit 500-tested-meshlet example below saves **0.307 ms warm I / 0.346 ms
cold I**. This is a selection optimization priced on synthetic packages;
it is not a measured R101 frame-time improvement.

The following cases use the public Test 22 profile, all five earlier switches
on, `SCENERY_CONE=0`, runtime SG lean on, and the lightweight selector. Each
row is one complete part with one partial cluster and eight tested meshlets;
construction, first coefficient setup, cluster tests and exit are included.
The main case has twelve corners and four groups per meshlet, with one group
culled by one demanded side plane (mask `2`).

| Case | Warm-I cycles per cluster, off → on | Cold-I cycles per cluster, off → on | Data bytes, off → on |
|---|---:|---:|---:|
| One crossed plane, four groups | 6,846 → 5,864 | 8,432 → 7,325 | 9,834 → 7,200 |
| Two crossed planes, four groups | 7,480 → 6,762 | 9,052 → 8,283 | 10,634 → 7,760 |
| Five crossed planes, four groups | 11,063 → 10,393 | 12,611 → 11,893 | 14,902 → 9,436 |
| Two crossed planes, eight groups | 11,160 → 9,482 | 12,732 → 11,003 | 14,410 → 9,168 |
| Five crossed planes, eight groups | 17,815 → 16,185 | 19,363 → 17,685 | 22,326 → 11,804 |
| Meshlet boxes wholly inside; no group tests | 2,835 → 2,663 | 4,067 → 3,781 | 4,469 → 3,825 |
| Meshlet boxes outside; no group tests | 2,222 → 2,046 | 3,352 → 3,093 | 3,737 → 3,129 |

Divide each row by eight for its amortized per-meshlet cost. The main case is
**855.75 → 733 warm-I cycles** and **1,054 → 915.625 cold-I cycles per meshlet**.
To separate setup from repeated work, the one-plane/four-group family fits
`T_before = 846 + 432*C + 696*C*M` and
`T_after = 842 + 422*C + 575*C*M`, where `C` is clusters per part and `M` is
meshlets per cluster. This is an exact fit to the priced finite family, not
a general selector cost law. It gives **696 → 575 warm cycles per added
meshlet** and **432 → 422 cycles of fixed work per cluster**. Cold I does not
have the same linear fit. Directly adding eight-meshlet clusters in the
one-versus-eight-cluster cases costs **6,000 → 5,022 warm** and
**6,000 → 5,090 cold-I cycles per added cluster**.

### Data traffic

For the main one-cluster/eight-meshlet case:

| Architectural access | Off | On |
|---|---:|---:|
| Load instructions | 2,004 | 1,513 |
| Store instructions | 710 | 548 |
| Bytes read | 7,249 | 5,359 |
| Bytes written | 2,585 | 1,841 |
| Unique 32-byte data lines over the complete part | 88 | 86 |
| Repeated line touches across meshlet intervals | 345 | 319 |

In the same fitted family, each added meshlet costs **210 → 150 loads,
66 → 46 stores, 751 → 519 bytes read and 235 → 143 bytes written**. Fixed
cluster work costs **127 → 119 loads, 41 → 39 stores, 477 → 453 bytes read
and 164 → 156 bytes written**. The four-to-eight-meshlet difference adds
35.5 → 32.5 repeated line touches per meshlet, while the whole-run union adds
three lines per meshlet in both arms. Most of the saving is fewer accesses
to the same working set, not a proportional reduction in its unique size.
In the main case, stack reads fall 4,061 → 2,309 B and stack writes
2,357 → 1,613 B. Meshlet-header reads remain 112 B and cluster-header reads
20 B. Group-record reads fall 352 → 304 B while touching the same 16 lines.

### Sensitivity and whole-frame estimate

Two small-group cases regress: eight meshlets crossing two planes with two
groups cost **5,360 → 5,378 warm / 6,886 → 6,898 cold cycles**; crossing five
planes with one group costs **5,823 → 5,921 warm / 7,315 → 7,416 cold**.
Their bytes still fall 8,586 → 7,056 and 8,982 → 7,436. The five-plane/eight-group
case has slightly more store instructions (862 → 876), although total bytes
fall sharply. The no-group case has more repeated line touches (215 → 229).
Neither fewer stores nor fewer line touches is a universal claim.

Already-inside placement/cluster controls perform no meshlet box/group work
in either arm. Their small timing differences are caller/layout effects and
are not credited as newly skipped work. With `SCENERY_CONE=1`, the main case
costs 7,056 → 6,073 warm / 8,691 → 7,935 cold cycles and 10,032 → 7,410 data
bytes. Its target stack watermark rises **860 → 872 bytes**, compared with
**836 → 828 bytes** for cone off. These fixture watermarks are separate from
production function frames below; the target corpus does not price the
decreasing-strip-end compatibility fallback.

For an explicitly assumed **500 tested meshlets**, represented by 62 complete
eight-meshlet parts plus one four-meshlet part, all in the main four-group,
one-plane family: warm cycles are **428,514 → 367,132** and cold-I cycles are
**528,432 → 459,175**. At 200 MHz, that saves **0.306910 / 0.346285 ms**;
architectural accesses fall **615,598 → 450,952 bytes**. Applying that saving
arithmetically to the supplied 47.8 ms reference gives **47.49 / 47.45 ms**.
This is a whole-frame **model estimate with an assumed selection mix**.
The supplied count of roughly 500 drawn pieces does not establish 500 tested
meshlets, their plane masks or group counts. Do not multiply the entire
3.39 ms pool by this one case's percentage without that census. D-cache
miss savings are not included or inferred from these byte counts.

## Retained changes

The partial-cluster path now reads a meshlet's six packed u16 bounds directly.
The old caller converted them to two float arrays, stored those arrays on the
stack, and called an out-of-line helper that loaded them back. The new helper
keeps the same conversions, matrix expressions, plane order and comparison
thresholds. This removes 24 bytes written and 24 bytes read without
changing the world data format.

With the existing `SG_SELECT_LEAN` path active, strip-group selection retains
one plane's four coefficients and three corner offsets across the meshlet's
groups. A one-plane case uses a single group walk. A multi-plane case reads
strip ends during its first plane pass and collects vertex ranges during its
last; intermediate passes visit only groups still visible. Each group's
multiply/FMA/FMA/add sequence and first rejecting plane remain the same.

The helper returns the final mask, count and vertex range in one word, removing
temporary strip-range arrays and the subsequent mask reconstruction. The
existing scalar group path remains available when SG lean is compiled out or
its runtime switch is off. No per-part, per-cluster or per-frame cache is added.

The baseline already skips group tests when a meshlet's box is wholly inside,
skips both tests for `cin==2`, and caches `sg_coef`/`sg_coef_lean` per part.
Those are retained behavior, not savings attributed to this change.

## Code and stack cost

Complete `native_static` production objects, using the Make-derived Test 22
recipe and SH GCC 15.2.0:

| Five earlier switches | Executable bytes, off → on | Change |
|---|---:|---:|
| All off | 67,040 → 68,864 | +1,824 B |
| All on | 67,460 → 69,292 | +1,832 B |
| All 32 combinations | — | +1,824 to +1,840 B |

Read-only data (23,571 B), initialized data (2,800 B) and BSS (17,212 B)
are unchanged. No per-room allocation or asset-size increase is introduced.

The complete-TU compiler stack frames are `MeshDraw::chunk_select` 264 → 264 B
and `ScenerySelector::chunk_select` 260 → 256 B. `ps2_pass` is unchanged in
every composition. The original lean group helper uses 72 B; the new ordinary
single-plane and multi-plane helpers use 44 B and 48 B, with a zero-byte
dispatcher. The decreasing-strip-end compatibility fallback adds a 100-byte
frame before calling the original 72-byte helper. These are function-frame
figures, not a whole-program stack watermark or linked-disc memory check.

## Exactness and guards

For increasing nonempty strip ends, each returned strip range identifies one
unique group, so building its bit directly gives the same mask as the old
rescan. The runtime package validator also accepts decreasing ends; detecting
one reruns the original helper and reconstruction before publishing a result.
Empty groups, an all-empty meshlet, the whole-pick sentinel, untouched Pick
fields and zero-range picks keep their old behavior. Cone selection receives
the same Pick input and keeps its existing order and accounting.

The implementation keeps the existing volatile SG-switch decision points.
PVS, interior and quality admission guards, foliage/transparency policy, LOD
choice, cull and material state are unchanged. Equal ordered picks and vertex
ranges feed unchanged emission consumers; these controls do not claim a
captured gameplay TA stream.

The compiled SH-4 gate passes **1,008 paired comparisons** across 126 packages,
cone off/on, runtime SG off/on, and actual full/light selector contexts. It
compares the entire 2,560-byte Pick buffer and all 63 accounting words, retaining
speculative writes made before cone rejection. The cost subset passes another
48 pairs and the two inside-bypass controls another four. Their execution
results, instruction counts, traffic and stack observations agree with the
corresponding full-corpus runs. Build-source, runner and ELF hashes are checked
again at completion. This is compiled selection evidence; the unchanged
consumer proof above establishes the same inputs and ordering for emission.

### Completed host and build controls

| Gate | Coverage and result |
|---|---|
| Complete production objects | All 32 earlier-switch combinations × 3 TUs; 384 absent/zero identity comparisons and 128 enabled unaffected-TU identities pass |
| Surrounding guard objects | 12 complete world-TU profiles; 48 absent/zero identity comparisons pass |
| Make contracts | 123 configurations × 3 TUs pass, including invalid-value/dependency rejection and the existing PVS + submit-batch rejection |
| Host selection | 454 validated synthetic packages, 42 off/on profiles (84 compiled arms); 87,168 comparisons pass, including 14,528 independently asserted guarded rejections |
| Direct numeric helpers | 294,912 group and 98,304 box comparisons pass |
| ASan + UBSan | 160 packages, 640 selection comparisons pass |

Identity compares complete preprocessed TUs with `-E -P` and complete executable
objects with debug line records omitted consistently. Make flags and generated
headers are independently derived from an archive of the exact base and checked
against the current tree. The main matrix has 768 logical preprocessing/object
artifacts from 144 unique compiler invocations; identical compiler inputs are
explicitly deduplicated. Baseline/current and absent/explicit-CPP-zero arms
remain separate compilations. Production source hashes stay frozen through the
checks.

The host matrix executes the shared selector with all five prior-switch
definitions; complete-TU builds establish their compilation/composition. It
does not execute 32 queue/actor integration combinations. Tests compare complete
poisoned Pick storage, including padding and unused fields, plus counters and
eligibility. Nonfinite numeric controls are host-only. The target layer below
executes both actual full and lightweight selector contexts.

## Alternatives evaluated

- A packed-result-only variant saved cycles, but its scalar group path added
  spill traffic. The final scalar group path retains the original code.
- A plane-at-a-time variant with separate header and range sweeps reduced
  data accesses substantially but added loop cost. Folding those sweeps into
  the first and last plane passes improved its cycle cost.
- Routing very small multi-plane groups through a packed legacy fallback
  added calls, stack traffic and reconstruction cost. That trial was dropped.
- Reusing a cluster's raw plane distance or replacing the box calculation
  with combined grid-space planes was not adopted. It changes floating-point
  rounding near decision thresholds, and the validator does not establish
  child-bound nesting. The retained optimization shares loads while keeping
  the existing arithmetic.

## Data-layout follow-up

A meshlet header is 28 bytes, with 12 bytes of bounds at offset 16; a group
record is already 16 bytes. The local world-data owner could measure a
separate lossless bounds stream for rejected meshlets, or a sparse stream
that removes empty group records. Both add lookup/format costs, so neither is
assumed beneficial without a room census. Rounded or quantized bounds can
change exact picks near a plane; they would need a full-precision fallback
to meet this task's contract. This commit changes no asset format or builder.

## Reproduction and measurement scope

The complete production translation units use the Make-derived public Test 22
recipe and SH GCC 15.2.0. The target fixture executes real compiled selector
construction, cluster/LOD selection, box and group arithmetic in the retained
SH-4 instruction model. Package adoption and fixture reset/snapshot are outside
the timed entry; geometry transformation, TA submission and gameplay are not
part of this selection price.

Warm I assumes residency. Cold I starts an empty 8 KiB instruction cache once
per complete part sequence. Both models assume perfect D-cache and omit DMA,
bus contention, SQ-transfer cost and final pipeline drain. Bytes count architectural accesses,
including stack and literal pools; repeated and unique 32-byte line counts
are reported separately and are not cache-miss estimates. Cold-I costs depend
on the synthetic ELF layout. Flycast, console and linked-disc memory checks
remain with the integration measurements.

Commands and fixture boundaries are in
[the tools README](../tools/d367/world_select_lean2/README.md).
The [JSON evidence companion](D367_WORLD_SELECT_LEAN2_20261023.json) retains
receipt hashes, source/object identities, selected target measurements and
the complete finite-difference/model calculations.
