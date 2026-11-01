# Build 24 world lane

This lane adds the default-off `SCENERY_CLIP_GATHER=1` candidate and guarded
`DRAW_SETUP_AUDIT` world/shell hooks. The integration base is
`a9fa0b8850f762acbf3ce49e86d7c24394df894b`. It does not claim measured farm FPS,
real cache misses, visual acceptance, or a complete hardware/game-state gate.

## Suspect and exact consumer boundary

The current release already uses `SCENERY_STREAM=1`, `MESH_CLIP_LEAN=1`,
`MESH_CLIP_ACCEPT=1`, `MESH_PRIME_LAZY=1`, `SCENERY_CHUNK=1`, and lean replay.
The Build 24 change does not claim these existing optimizations as new work.

`MeshDraw::emit_pick` transforms an indexed meshlet directly from its source
pool. A crossing/oversized strip subsequently needs local AoS12 corners for
`Emitter::clip_strip`. The old first `stream_gather()` copies all
`vertex_count * 12` bytes, even if that clip strip references only three local
corners. A 64-corner meshlet therefore moves 768 vertex bytes each direction;
the format's 256-corner limit moves 3072 each direction. A source-offset table
adds two read bytes per copied corner, before other loop/state accesses.

The candidate keeps the existing scratch and local indices. A 256-bit mask
records which local entries have been populated for the current pick. The mask
is cleared lazily on the first clipping consumer, then each distinct referenced
entry receives the original three 32-bit word moves. No additional source
vertex array, heap allocation, package owner, TA owner, material, primitive
order, source transform, cull rule, or lifetime is introduced. Target state is
36 bytes (32-byte mask plus a boolean and padding). A no-clip pick only resets
the boolean; it does not clear the mask or gather any vertex.

| Consumer or boundary | Proof obligation and treatment |
|---|---|
| R4IM adoption | `MeshPackage::adopt` validates aligned sections, even indexed offset-table locations, pool ranges, strip lengths, and every local index. The local index is a byte; the format admits 1–256 vertices. |
| `emit_pick` | Sets `stream_l` for indexed picks and calls `begin()` once per new pick. The mask survives all selected strip groups of that pick. Plain picks keep their original direct base pointer. |
| `strips_lean` | Calls the new gather for every clipped strip, even after its local `base` becomes non-null. The old absent/zero branch remains byte-for-byte source equivalent. |
| CPU backface mode 2 `strips_bf_sq` | Uses the same gather-before-clip boundary and exact local indices; direct/backface submission is unchanged. |
| Clipper homogeneous reject prepass | Reads only `base[index[i]]`. |
| Existing ring accept path | Reads only `base[index[i]]`, then keeps prepared vertices in its existing three-entry ring. |
| Existing short-strip prepared array | Reads only `base[index[i]]`, then uses its existing local array. |
| Legacy triangle fallback | Reads only three strip indices per triangle, preserving the original odd/even swap. |
| Palette / ARGB1555 / ARGB4444 / UV | Decoding uses the copied vertex itself; the source words are unchanged. |
| Offline deduplication mode 3 | Rejected when this candidate is enabled: `offline_position` may read `base[in.x]` beyond the strip's explicit indices. Existing modes 1/2 exclude indexed meshlets from their dedup table. |
| Prefetch path / old CPU backface mode 1 | Rejected with this candidate; their alternate consumer boundaries have not been qualified. |

The required controls are `SCENERY_STREAM=1`, `SCENERY_CHUNK=1`, `MESH_DIRECT=1`,
and `PS2_WORLD_MESH=1`; `SCENERY_EMIT_PREFETCH` must be 0, `SCENERY_DEDUP` must
not be 3, and `CPU_BACKFACE` must be 0 or 2. Both new feature controls default
to 0. Full translation-unit disabled identity is owned by the shared Build 24
build-controls gate, rather than inferred from the helper test.

## World diagnostic meanings

`re4dc_ps2_world_draw` and source-world draw enter WORLD OP/PT. The deferred
flush enters WORLD TR; nested `re4dc_ps2_mesh_draw` pass 1 moves PT back to
WORLD OP/PT, and pass 2 remains WORLD TR. `re4dc_far_shell_draw` enters SHELL.
The existing frame/thread and PMU owners remain with the shared diagnostic.

Work covers selection, preparation, transforms and other path setup. The
indexed gather and shared clipper enter Clip. Direct strip walks, packet
commits, and TA submission enter Submit. Shell's preparation stays Work and
its complete strip emission loop enters Submit. There are no clocks inside a
vertex loop; clipped triangle packet emission still causes bounded packet
submission scopes, so observer overhead must be qualified separately.

| Counter | Meaning in this lane |
|---|---|
| Parts | `Draw::run`, `MeshDraw::run`, or chunk replay calls, including a refused call. A source part split across replay chunks can be counted more than once. Shell counts admitted groups. It is not a unique-source-part census. |
| TrianglesIn | `n - 2` for strip inputs reaching selected traversal. Bounds-rejected/unselected source geometry is not included. |
| TrianglesOut | Emitted strip primitives, or the clipper's emitted triangle count. Includes degenerates and triangles later rejected by PVR depth/cull. This is not rasterized/visible geometry. |
| ClipTriangles | `n - 2` for strips handed to the clipper. |
| ClipRebuilds | Repeated source-corner transformations inside the clipper, including its homogeneous early-reject prepass. It is not a count of unique corners. |
| ClipStrips | Calls to `clip_strip`. |
| StreamGatherVertices | Actual source-to-local vertex copies. Full gather counts `vertex_count`; candidate gather counts only newly filled local entries. |
| XluSubmitted | Emitted primitive count for actual PS2 TR parts. PT stays in OP/PT. |
| XluViewOverlap | Conservative projected triangle bounding-box overlap with the viewport, on emitted triangles. The lean walk replays the same integer reject predicates after emission, then reads the existing projected cache. Clipped/buffered packets use their emitted vertices. |
| Unsupported | Marks unqualified alternate paths and incomplete output totals. It is not a reason to discard all measured wall time. |

Viewport overlap does not establish depth visibility, nonzero pixel coverage,
alpha-test survival, occlusion, or meaningful visual contribution. Winding
does not affect the bounding box. NaN comparisons conservatively retain the
triangle. Timing includes diagnostic overlap counting itself; A/B comparisons
must use the same observer arm.

The selected release's streamed lean path is the qualified world path. CPU
backface mode 2 marks translucent overlap unsupported because this diagnostic
does not replay its determinant/run splitting. Historical R4P rendering marks
the detailed counters unsupported. `SCENERY_DIRECT_STRIPS` fused emission and
`MESH_CLASSIFY` alternatives conservatively mark run/chunk entry unsupported,
because their complete separate Submit and overlap accounting is not covered.
The generic/non-lean compatibility paths also mark unsupported overlap when
appropriate. On an incomplete packet-producing call, the part scope marks the
counter totals unsupported, since staged output may not have been published.
The separate Models counter belongs to source model-dispatch hooks; it is not
a distinct-world-placement counter.

## Correctness evidence

`world_host.py` adopts 320 synthetic indexed R4IM v3 packages using the actual
reader. It runs exact source-extracted `corner`, `clip_vertex`, and `clip_strip`
bodies against a full gather and the production subset helper. Each of three
configurations (legacy fallback, lean short-strip reuse, and current ring
accept) performs 20,480 comparisons. All emitted packet scratch bytes, counts,
and clipping outcomes match: 61,440 clip-consumer comparisons per full run.

Cases include near/far edges, exact near depth, zero projection depth,
all four cull modes, source alpha and both packed colour modes, 3–255-corner
strips, local index 255, all 256 local corners across strips, repeated local
indices, aliased pool offsets, sparse/scattered source pool entries, multiple
strip groups, no-clip lazy resets, per-pick refresh, packet capacity refusals,
untouched local slots, canaries and malformed source-offset/alignment inputs.
The same configurations pass AddressSanitizer and UndefinedBehaviorSanitizer.

Host adapters use the same scalar projection on both sides instead of SH4
`fsrra`, and bounded scratch with explicit flush refusal instead of an actual
TA/SQ owner. They prove the gather's existing clip consumer boundary, not
console floating-point accuracy, complete renderer ownership, game-state
STRICT, or screenshot equivalence.

## Cost evidence and acceptance limit

`world_target.py` uses the pinned real SH4 compiler and current Make-derived
`native_static` flags. It extracts the production old/new gather method bodies
and old corner-copy loop, includes the production `Gather`, and preserves the
O2 mesh-method scope with the helper header's original Os context. The fixture
supplies known-indexed, already-resolved pool/offset pointers; package-loader
and header-resolution work is excluded. It executes actual target opcodes,
checks every target scratch vertex and untouched slot, records data traffic,
and prices the trace with perfect D-cache plus warm/initially cold I-cache.

The one-strip sparse case removes considerable copy traffic. High coverage,
many repeated clipped strips, or a long strip repeating a small index set can
regress because every input index still probes the mask. This is an A/B
candidate, not a universal win. The preserved receipt records the exact tested
crossover neighbors for 16-, 64-, and 256-vertex meshlets, full-coverage and
repeated-strip regressions, architectural loads/stores, distinct 32-byte lines,
stack, sections, tool hashes, and all model qualifications.

The final receipts are [world-host.json](receipts/world-host.json) and
[world-target.json](receipts/world-target.json). The target gate passes 34
synthetic cases, each run with the original and candidate body (68 target
executions). Example exact values follow; loads/stores include wrapper, stack,
mask, table and literal traffic in addition to the copied vertex words.

| Synthetic clipped-pick sequence | Warm cycles, original → candidate | Cold-I cycles, original → candidate | Total load bytes | Total store bytes | Distinct data lines |
|---|---:|---:|---:|---:|---:|
| 64 vertices, one three-corner strip | 1589 → 206 | 1664 → 322 | 1095 → 151 | 808 → 130 | 114 → 16 |
| 64 vertices, all 64 referenced once | 1589 → 2646 | 1664 → 2762 | 1095 → 1554 | 808 → 1106 | 114 → 118 |
| 256 vertices, one three-corner strip | 6197 → 206 | 6272 → 322 | 4167 → 151 | 3112 → 130 | 392 → 16 |
| 256 vertices, all 256 across two strips | 6206 → 10399 | 6281 → 10515 | 4168 → 6026 | 3112 → 4198 | 393 → 402 |
| 256 vertices, same three indices in 32 strips | 6385 → 3089 | 6472 → 3205 | 4198 → 2042 | 3112 → 750 | 395 → 21 |
| 256 vertices, 64 disjoint three-corner strips | 6577 → 9845 | 6664 → 9961 | 4230 → 7396 | 3112 → 4414 | 399 → 325 |

For the 64-vertex sparse row, source-vertex loads and gather stores separately
drop from 768 bytes each to 36 bytes each; table reads drop from 128 to 6 bytes.
For 256 vertices those same quantities drop from 3072/3072/512 to 36/36/6.
At full coverage, those three payload quantities are unchanged and the mask
adds overhead. These source offsets are synthetic scattered addresses; the
distinct-line counts depend on that chosen layout.

Exact single-strip crossover neighbors are executed, not interpolated:

| Meshlet size | Last tested winning unique coverage, warm | First tested loss, warm | Last tested winning coverage, cold-I | First tested loss, cold-I |
|---:|---|---|---|---|
| 16 | 8 corners: 406 < 437 | 9: 446 > 437 | 7: 482 < 512 | 8: 522 > 512 |
| 64 | 37 corners: 1566 < 1589 | 38: 1606 > 1589 | 36: 1642 < 1664 | 37: 1682 > 1664 |
| 256 | 152 corners: 6166 < 6197 | 153: 6206 > 6197 | 151: 6242 < 6272 | 152: 6282 > 6272 |

These are crossover points for this one-strip, distinct-index fixture, not a
runtime policy. Repeated strips add candidate calls/probes and change them.
No-clip picks execute 24 modeled warm cycles in both fixture arms (24 versus
26 instructions); the candidate adds the boolean store but no mask clear or
payload traffic. The candidate method's static frame is 20 bytes versus 8
for the original; observed wrapper-inclusive peak stack is 44 versus 32 bytes.
The separately stored emitter mask adds 36 bytes to candidate state. The tiny
linked fixture is 496 executable bytes, not an estimate of whole-game image
growth; the shared complete-TU build gate reports that separately.

At 200 MHz, the 64-vertex sparse row saves 0.006915 modeled milliseconds per
clipped pick; its full-coverage counterpart adds 0.005285 ms. A hypothetical
100 such picks would therefore save 0.6915 ms or add 0.5285 ms respectively,
before all excluded effects. No evidence in this fixture establishes that
either population occurs in the farm capture.

Distinct lines and load/store bytes are address-touch accounting, not measured
cache fills or bus traffic. Model cycles exclude D-cache misses, cache-bank
effects, DMA/interrupt contention, TA FIFO stalls, and clipping or transforms.
Converting cycles at 200 MHz describes only this synthetic sequence. Console
impact additionally requires measured counts of indexed picks that actually
clip and their reference coverage. A low asynchronous `gpu_avg` cannot rule
out CPU-side submission backpressure.

Pending acceptance is matched farm near-barn/near-body and distant captures
with fixes independently off/on, the same observer state, room/view/enemy
state and real console timing. The candidate remains default off until that
evidence supports it.

## Reproduction

From the repository root, choose fresh output directories. `B24_CXX`,
`B24_KOS`, and `B24_SDK` name the pinned compiler, KOS and SH4ZAM paths from the
shared toolchain receipt.

```sh
python3 port/dreamcast/tools/cloud/build24/world_host.py \
  --output /tmp/b24-world-host --sanitizer
python3 port/dreamcast/tools/cloud/build24/world_target.py \
  --output /tmp/b24-world-target --sh4-cxx "$B24_CXX" \
  --kos-root "$B24_KOS" --sdk-root "$B24_SDK"
python3 port/dreamcast/tools/cloud/build24/world_receipt.py \
  --input /tmp/b24-world-target/world-target.json \
  --output /tmp/b24-world-target-compact.json
```

The compactor interns identical traffic objects without changing measured
values, asserts that discarded uncached/SQ/prefetch entries are all zero, and
preserves the raw receipt hash. The full SH4 compile and disabled whole-object
identity command is in the shared Build 24 README.
