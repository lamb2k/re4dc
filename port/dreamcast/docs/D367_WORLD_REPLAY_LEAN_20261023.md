# World replay lean — 2026-10-23

**Base:** `451bed6faa2c37f7f9aa05d6fb1116ec64219ebc` on `t15/int`.
**Branch:** `codex/world-replay-lean-20261023`.
**Switch:** `SCENERY_REPLAY_LEAN=1`, default **0** in `game/scenery19.mk`.

The change removes repeated full emitter construction during queued world
replay and the temporary screen-memo key copies. At 500 eligible pieces in
ten 48-piece runs plus one 20-piece run, the **whole-frame model estimate is
1.68–1.93 ms saved**, depending on SUBMIT_BATCH and memo hits. This is a
synthetic SH-4 setup estimate with perfect D-cache; Flycast and console results
remain to be measured. No release setting is enabled.

## Implementation and audit

`ps2_pass::chunk_flush` constructs one emitter per nonempty run. Its narrow
`chunk_restart` clears per-part counters, binding flags, cache/prime state and
optional PVS pending state. Binding overwrites packet/destination/capacity;
clearing `cache` forces each part to revalidate the slab and rebuild vertex
constants. The gather buffer, streaming mode and clip setup are invariant
within the synchronous run.

Each row retains `part.cull=x.cull`, its material key, sky header, alpha/LUT
mode, part index, piece accounting and PVS placement. Four mesh UV bias/scale
floats are refreshed through a stable local `MeshPart`; the shared material
UV-offset reads are preserved. Each replay row copies its `mvq` once and omits the unused
selection-only `mv`, `cull_far` and `lod_scale` setup. Emission order, direct-end
and abort/accounting paths are retained. The production assembly confirms
**776-byte and 209-byte overlapping clears move from every row to once per
run**, plus a one-time 36-byte local part clear. This is 985 requested clear
bytes, not 985 distinct bytes.

`load_screen` compares the existing 80-byte memo key directly in three source
segments. It avoids the temporary copy and, on a hit, row construction. On a
miss it uses the same matrix arithmetic. Every call still reloads the matrix
after a potentially yielding bind. There is no new persistent cache.

The other requested opportunities are already covered by this base:

- `lean_inside` gives `cin=2`; that skips the meshlet box test. The resulting
  zero mask also skips strip-group selection. Numeric helper counters confirm
  zero calls through both fully-inside routes and calls in the partial control.
- Placement/view and quantization-grid concatenations are already outside
  the part loop. Test 22 already enables `SCENERY_SCREEN_MEMO`.

An additional inside-loop shortcut regressed the one-meshlet target case and
was removed. `scenery_chunk_select.inc` is byte-identical to the base. **No new
selection or placement-concat saving is credited.** Material binding, scratch
validation and the remaining necessary per-part state still execute.

## Cycles and data traffic

Actual SH GCC 15.2.0 instructions run in the scalar target interpreter and are
priced by the repository hardware model. The target fixture retains full
`MeshDraw` layout and replay code, replacing geometry with an observed boundary.
UI submission and matrix hardware-transfer bodies are excluded. Production
assembly independently confirms the dominant clear reduction; different
fixture register allocation/inlining can affect other instructions.

Below is **per piece, averaged over a 48-piece run**, with SELECT_ONLY=1.
Compare replay off/on within each SUBMIT_BATCH column pair: this fixture
excludes the lock/submission work that determines SUBMIT_BATCH's own benefit.

| Metric | Batch 0, replay 0 | Batch 0, replay 1 | Batch 1, replay 0 | Batch 1, replay 1 |
|---|---:|---:|---:|---:|
| Warm I-cache modeled cycles | 867.6 | 269.7 | 903.8 | 288.3 |
| Cold I-cache modeled cycles | 879.2 | 282.4 | 915.2 | 300.6 |
| Data load instructions | 137.0 | 76.6 | 142.0 | 81.7 |
| Data store instructions | 331.5 | 53.6 | 338.5 | 54.7 |
| Bytes read | 484.3 | 280.1 | 502.4 | 298.3 |
| Bytes written | 1,283.8 | 201.3 | 1,299.9 | 205.7 |
| Repeated 32-byte line touches | 50.9 | 32.4 | 52.9 | 34.4 |

Warm I assumes ideal instruction residency. Cold I starts an empty 8 KB
instruction cache once per run, then amortizes that run over its pieces; it
depends on synthetic code layout. Both assume perfect D-cache and exclude
SQ/DMA/interrupt and unrelated bus-contention costs; cold I includes the
model's instruction line-fill cost. A one-piece run has effectively no warm saving
(976→974 cycles, batch 0), more stores (374→384), and a cold-I regression
(1,485→1,529). At eight pieces, warm cost is 880.5→345.9 cycles/piece. Queue
occupancy therefore matters.

Loads/stores include stack, PC-relative literals and library helper accesses;
opcode fetches are excluded. An eight-byte move counts as one instruction.
Bytes are architectural accesses, not external-memory transfers. Line touches
sum distinct cached lines between geometry boundaries, with run entry/exit
apportioned; repeated intervals may count the same line again.

The **whole-run unique address footprint barely changes**: batch 0 is
197→199 lines; batch 1 is 201→202. The saving is repeated traffic, not a large
working-set reduction. These counts are neither measured misses nor cache
fills. In light of the supplied console result (halving D-cache cost +8.2 ms),
no proportional hardware cache-speedup claim is made. This change does not
reserve scratch RAM or change cache mode. Public-profile measured paths issue
zero PREF requests.

The separate screen-memo cost per call, batch 0, is:

| Metric | Hit, off→on | Miss, off→on |
|---|---:|---:|
| Warm modeled cycles | 461→302 | 728→654 |
| Cold modeled cycles | 732→451 | 973→951 |
| Loads / stores | 99/52→59/7 | 183/89→162/64 |
| Bytes read / written | 383/208→233/28 | 719/353→645/253 |
| Distinct 32-byte lines | 19→9 | 21→16 |

Warm memo costs match with batch 1. Its cold results differ with code layout;
all exact values and 0/1/2/8/20/48-piece results are in the JSON receipt.

## Whole-frame model estimate

Assumptions: 200 MHz, 500 chunk-eligible drawn pieces, ten full 48-piece queues
plus one 20-piece queue, one memo call per piece, all other frame work fixed.
The replay traces exclude memo work, so the following adds disjoint savings.

| SUBMIT_BATCH | Replay only | With all memo misses | With 50% memo hits | With all memo hits |
|---:|---:|---:|---:|---:|
| 0 | 1.493 ms | 1.678 ms | 1.784 ms | 1.890 ms |
| 1 | 1.537 ms | 1.722 ms | 1.828 ms | 1.934 ms |

For example, applying the batch-0/50%-hit **model delta** to the supplied
49.3 ms console reference projects **47.516 ms/frame**, about a 3.6% frame-time
reduction. This combines a supplied measured reference with a synthetic delta;
it is not a measurement of this branch. Neither eligibility, queue occupancy
nor hit rate was measured at r101 here. Cold-I sequence figures are not added
into a frame estimate. There is no extra credit for the two existing spikes.

## Production size and stack

Complete Test 22 `native_static` objects grow by **96, 96, 56, 68 executable
and allocated bytes**, respectively, for `(SELECT_ONLY,SUBMIT_BATCH)` =
`(0,0), (0,1), (1,0), (1,1)`. BSS/data allocation growth is zero. `native_ui`
objects are unchanged. These are relocatable-object measurements, not linked
disc size or room-memory headroom.

| Compiler-reported function frame | Replay off | Replay on | Delta |
|---|---:|---:|---:|
| Replay lambda, batch 0 | 848 B | 884 B | +36 B |
| Replay lambda, batch 1 | 852 B | 896 B | +44 B |
| `chunk_emit` | 136 B | 128 B | −8 B |
| `load_screen` | 196 B | 108 B | −88 B |
| `ps2_pass`, select 0 / 1 | 8,988 / 8,992 B | 8,988 / 8,992 B | 0 |

These are individual stack frames, not an observed maximum nested stack.

## Identity and exact-output evidence

The actual public Test 22 Make recipes were expanded separately for both
translation units. Executable flags are retained; debug records and
preprocessor line markers are omitted consistently to exclude source-line
metadata. Baseline sources and quote includes are read independently from
`451bed6f`. **All 32 absent/zero preprocessed-source and complete-object
comparisons pass**, covering both TUs and all four SELECT_ONLY/SUBMIT_BATCH
pairs. Enabled `native_ui` objects also remain identical.

| Enabled-path control | Result |
|---|---:|
| Bind/replay/UI boundaries, all switch combinations plus diagnostics | 2,288 paired comparisons |
| Actual admission/setup/capacity drains, all combinations plus PVS | 21,384 paired comparisons |
| Actual portable geometry, literal TA/accounting words in order, all eight combinations | 264 paired comparisons |
| Numeric selector/inside-helper activity | 832 comparisons |
| Bitwise screen matrices, 33 hits / 28 misses | 61 calls, 61 reloads |
| Target selector/replay/memo inputs, state and matrices | 72 case groups |
| Make defaults, eight combinations and dependency guards | 17 configurations × 2 TUs |

Controls cover material/cull/sky/UV changes, alpha and 4444 conversion, indexed
gather, partial/empty picks, near clipping, far/screen rejection, capacity
drains, acquisition failures, early/late aborts, PVS reset and balanced locks.
Transition/R11F owners, WORLD_AUTOSORT/UI_POLY_ORDER and foliage/trans-policy
paths are retained and exercised. Scratch pressure on the second acquired
part after a successful first part verifies the reset revalidates borrowing.
Texture acquisition deliberately clobbers the matrix to check post-bind
reloads; separate screen controls overwrite it before every call, including
33 memo hits.

The geometry suite uses host floating-point transform and a documented C SQ
adapter, while asserting unchanged production geometry bodies. It compares
every observed TA word; it does **not** establish full-game or hardware FTRV
output identity. Console/Flycast scene qualification remains necessary.

An existing limitation is preserved: base `ChunkPart` does not snapshot the
shared dynamic `Re4dcModelPart::uv_offset`. Owner code can change that field
before queued replay, and no general admission guard proves all such assets
ineligible. No production occurrence was established here. This patch retains
the baseline shared reads, avoiding an unrelated TA-output change; it does not
claim to repair that existing dynamic-UV issue.

Replay requires the direct PS2 chunk path and `WORLD_SCRATCH=0`; this preserves
the existing scratch lifetime. SUBMIT_BATCH retains its own additional guards.
No owner predicate or release knob is relaxed.

[Machine-readable receipts](D367_WORLD_REPLAY_LEAN_20261023.json) retain source,
object and original-receipt hashes, the combination results, traffic and model
tables. [Reproduction commands and tool scope](../tools/d367/world_replay_lean/README.md)
describe each control and the narrow test-helper provenance. No runtime or Git
parent from PR #56 or an old spike branch is included.
