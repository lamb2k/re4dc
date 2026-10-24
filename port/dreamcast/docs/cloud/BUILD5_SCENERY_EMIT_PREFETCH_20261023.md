# Build 5: world emit data traffic

Base: `origin/t15/int`, `dc87c4658d65ba992d266e3cb1893ecd485da661`.
Branch: `codex/scenery-emit-prefetch-20261023`.
Knob: **`SCENERY_EMIT_PREFETCH=1`**, default **0**.

## Result and limits

This is an exact, default-off candidate for the r101 cross. It warms the
next selected meshlet's real inputs, including shared-pool vertices, and
avoids the unused indexed gather when all of a pick's groups were rejected.
Nonempty gathers hold the immutable vertex count outside the copy loop.

Prefetch adds instructions and requests existing data earlier. The cloud
model cannot price its data-cache benefit. It is therefore **not a measured
r101 speedup**. The scalar timings, architectural memory accesses, synthetic
frame sensitivity and pending console gate are separated below.

### Compiled SH-4 scalar measurements

All five preceding switches are enabled. OFF and ON execute actual compiled
target code, with costs assigned by the repository's pipeline model. Warm I
assumes instruction residency; cold I starts an empty instruction cache for
each named invocation. Both exclude data-cache miss latency. The gather
fixture uses a 96-vertex meshlet with reversed shared-pool offsets. A partial
pick selects vertices 24 through 47 but still gathers all 96 in both arms.

| Gather entry, one meshlet | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Load instructions OFF → ON | Store instructions OFF → ON | Bytes read OFF → ON | Bytes written OFF → ON | Distinct 32 B data lines OFF → ON |
|---|---:|---:|---:|---:|---:|---:|---:|
| Plain, whole/partial/empty | 30 → 32 | 124 → 101 | 13 → 13 | 0 → 1 | 46 → 48 | 0 → 4 | 8 → 10 |
| Indexed, whole or nonempty partial | 2,443 → 1,969 | 2,531 → 2,044 | 500 → 405 | 289 → 289 | 1,606 → 1,419 | 1,156 → 1,156 | 91 → 93 |
| Indexed, zero selected groups | 2,443 → 38 | 2,531 → 103 | 500 → 17 | 289 → 1 | 1,606 → 61 | 1,156 → 4 | 91 → 12 |

Counts include entry overhead, stack and literal loads. Plain entries return
the source pointer without copying vertices. Nonempty indexed gathering
saves **474 warm cycles (19.4%)** by holding the count outside the may-alias
copy loop: header loads fall from 100 to 4, removing 192 header-read bytes.
The net read saving is 187 bytes after the new pick check and literal access.
The copied source and destination still each occupy 37 lines, and the offset
stream occupies seven. Two extra literal/layout lines explain the increased
whole-entry union; this change does not shrink the nonempty vertex working
set. The zero-group case removes its 1,152-byte source read, 192-byte offset
read and 1,152-byte gather write entirely. Poisoned-buffer checks verify that
the enabled zero-group path performs no gather stores.

The next table prices replay/setup and lookahead around an explicit stub at
the geometry boundary. It excludes the gather, transform, strip walk and
binding internals. Each queue contains 32 pieces with one 96-vertex meshlet
per piece; the per-piece numbers are queue totals divided by 32, not 32
independent cold-cache invocations.

| Replay/setup, 32-piece queue | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Warm cycles/piece OFF → ON | Cold-I cycles/piece OFF → ON |
|---|---:|---:|---:|---:|
| Plain | 9,894 → 13,209 | 10,492 → 13,974 | 309.19 → 412.78 | 327.88 → 436.69 |
| Indexed | 9,894 → 13,240 | 10,492 → 13,986 | 309.19 → 413.75 | 327.88 → 437.06 |

| Same queue, architectural traffic | Loads OFF → ON | Stores OFF → ON | Bytes read OFF → ON | Bytes written OFF → ON | Demand-data line union OFF → ON | PREF requests OFF → ON | PREF line union OFF → ON |
|---|---:|---:|---:|---:|---:|---:|---:|
| Plain | 2,705 → 3,328 | 1,918 → 2,013 | 9,898 → 11,987 | 7,228 → 7,608 | 154 → 190 | 0 → 135 | 0 → 121 |
| Indexed | 2,705 → 3,359 | 1,918 → 2,013 | 9,898 → 12,049 | 7,228 → 7,608 | 154 → 221 | 0 → 135 | 0 → 121 |

These lookahead accesses move future demand earlier and add instructions.
The geometry stub does not consume the prefetched payload, so its table
cannot demonstrate saved cache misses or an integrated-emitter line union.
The JSON receipt also retains single-piece and eight-picks-per-piece
controls, per-region traffic and all 24 passed PREF-address assertions.

### Whole-frame figure: MODELLED sensitivity only

Use the queue's **47.8 ms** model reference and explicitly assume **500
one-pick pieces, 96 vertices each**, replayed as 15 queues of 32 and one of
20 at 200 MHz. Add the separately measured warm gather-entry deltas to the
warm replay/lookahead deltas. No data-cache benefit is credited.

| Assumed frame population | Replay delta | Gather delta | Net MODELLED delta | MODELLED reference + delta |
|---|---:|---:|---:|---:|
| All plain | +51,768 cycles | +1,000 cycles | +0.263840 ms | 48.063840 ms |
| All indexed, nonempty | +52,271 cycles | −237,000 cycles | −0.923645 ms | 46.876355 ms |
| All indexed, every tenth pick has zero groups | +50,062 cycles | −333,550 cycles | −1.417440 ms | 46.382560 ms |

This is arithmetic sensitivity, not a predicted r101 result: the actual
piece census and indexed/empty proportions are unknown, and the gather leaf
and replay boundary are measured separately rather than inside the complete
production emitter. Independently cold components must not be summed as a
real cold frame. The all-plain case explicitly exposes the instruction
regression that a console cache benefit would need to overcome.

## What changed

The make option is in [scenery19.mk](../../game/scenery19.mk), and the runtime
change is confined to
[native_static.cpp](../../game/platform/native_static.cpp).

1. Header hints run two **selected picks** ahead. A meshlet's 16-byte emit
   prefix may cross a 32-byte line because records have a 28-byte stride;
   both lines are hinted when necessary.
2. Payload hints run one selected pick ahead. An indexed meshlet hints its
   offset table and the vertex named by its first offset. The old
   `PREF_WALK` hint addressed the beginning of the part pool, which may not
   be referenced by that meshlet. A plain partial pick starts at `pk.lo`.
3. The first, at most, three plain vertices seed the already existing
   transform prefetch stream. Whole picks hint their first strip bytes;
   partial picks hint the group table instead of assuming group zero will
   be consumed.
4. The last pick can look ahead to the next queued part's first actual pick.
   The packed queue index handles intervening zero-pick parts. Nothing is
   hinted outside the current synchronous flush.
5. A zero-group indexed pick omits its unused gather. Its binding,
   ownership validation, borrow, cache prime, counters and return order
   remain unchanged. A nonempty indexed gather reads its immutable count
   once before the may-alias copy stores.

The new lookahead replaces `PREF_WALK` inside this emission loop when both
are enabled. Its other call sites are unchanged. No material/texture work
is moved across binds, and no SQ, scratch, matrix or dynamic-UV state is
retained for a future part. The selected order, transform arithmetic,
strip walk, clipping, and end/abort handling are unchanged.

### Why this prefetch distance

The existing scheduled transform streams three 12-byte records ahead.
The new header distance gives the current meshlet's transform and strip
work time to overlap the following header request; payloads are requested
one meshlet ahead to avoid filling the cache with a whole future meshlet.
The scheduled transform's source describes a roughly 36-cycle steady-state
vertex interval, so a current pick with `V` transformed vertices offers
approximately `36*V` model cycles plus strip work before the next payload
is consumed. Short or empty picks offer less lead. This is a reasoned
starting distance, not a claim that it hides a measured console latency.

### Why partial indexed gathers remain complete

Generated R4SG group ranges enclose each group's strip indices, and
`tools/d367/worldlean/sgcheck.py` can verify that fact. The runtime reader,
however, checks format and CRCs without proving that enclosure. Narrowing
a nonempty gather to `pk.lo..pk.hi` could change a clipper input for an
already admitted sidecar with an incorrectly narrow range. DEDUP also
reads duplicate attributes outside that interval. This candidate therefore
keeps the complete gather for every nonempty indexed pick, including
partial ones. A zero-group pick has no gathered-input consumer.

## Data audit

The audit starts with [chunk_submit.cpp](../../game/platform/chunk_submit.cpp).
Its `pref @sq` flushes store-queue output; it is not input-data prefetch.
The selected PS2 world path uses `MeshDraw::emit_pick`, the scheduled
transform and `strips_lean` instead of that shared backend.

| Stage | Input/output | Access pattern |
|---|---|---|
| Part setup | 16 B UV bias/scale, existing material key and matrix | Once per part; material binding is already outside the per-strip walk |
| Selected pick | 8 B | Selected order, not consecutive meshlet IDs |
| Meshlet header | First 16 B of a 28 B record | `first_vertex`, `first_strip`, `strip_bytes`, vertex count and indexed flag; bounds belong to selection |
| Plain source | 12 B per transformed vertex | Contiguous; a partial transform starts at `lo` |
| Indexed gather | 2 B offset + 12 B source read + 12 B gather write per copied vertex | Offset stream is sequential; referenced pool vertices may be scattered |
| Transform | 12 B input + two 4 B LUT reads per transformed vertex | Sequential source, potentially scattered LUT; 24 B projected fields + 1 B outcode written per vertex |
| Cache prime | 8 B per newly primed vertex | Flags and `oargb`; existing retained-prime behavior is preserved |
| Partial group walk | 2 B end offset from each 16 B group record | Bounds in these records are not used by emission |
| Strip acceptance | Count/index bytes and outcodes | Indices are scanned for outcodes, then accepted strips reread them for emission |
| Accepted output | 32 B projected-cache read and 32 B SQ write per emitted corner | Cache reads follow strip indices, including repeated vertices; SQ is not an operand-cache output line |
| Clipped output | Original source corners, UV and clip temporaries | Existing clipper and source read order |

For a nonempty contiguous range, define
`L(address, bytes) = ceil(((address & 31) + bytes) / 32)`.
For `V` transformed vertices, `G` gathered vertices, `I` accepted strip
indices, `S` accepted strips, and `P` newly primed entries:

- Plain source touches `L(source, 12*V)` lines and reads `12*V` bytes.
- LUT reads total `8*V` bytes across at most 64 lines in the 2 KiB LUT.
- Transform writes total `25*V` bytes; cache prime adds `8*P` bytes.
- Strip bytes occupy `S+I` unique bytes. The main accept path reads roughly
  `S+2*I` bytes because it scans indices for outcodes and again for output.
- Outcodes contribute `I` byte reads; projected-cache reads total `32*I`
  bytes across at most `V` aligned cache lines, often with repeated visits.
- Indexed gathering additionally reads `2*G` offset bytes and `12*G`
  potentially scattered pool bytes, writes `12*G` gather bytes, and the
  transform rereads `12*V` gathered-input bytes. `G` is the full meshlet
  count for every nonempty indexed pick, including partial ones. For a
  zero-group indexed pick, this candidate changes `G` from the full count
  to zero while `V` is zero in both arms.

These formulas describe architectural requests, not cache misses or
external-bus traffic. Alignment, shared pool offsets, strip reuse, LUT
values and cache residency determine the address union. The retained
receipts give exact line counts for the named synthetic cases, without
inventing an r101 meshlet distribution.

### Existing layout costs

For 4-byte-aligned 28-byte records, the 16-byte hot prefix crosses a line
for three of eight record positions: **1.375 independently counted lines
per record on average**. The entire record crosses for six of eight
positions. Consecutive records share lines, so the union is approximately
seven lines per eight records; the per-record sum must not be reported as
that union.

Vertices remain 12-byte records; the reader does not pad them to 32 bytes.
The transform writes a 32-byte projected record, which is reread in strip
order. The source gather and projected-cache revisit are real traffic,
not a second copy to be incorrectly excluded from the accounting.

## Offline repack proposal, not implemented

If the next console run supports a format experiment, separate the
meshlet table into two tables while preserving logical meshlet IDs:

| Proposed table | Record fields | Bytes |
|---|---|---:|
| Emit metadata | `u32 first_vertex, first_strip, strip_bytes; u16 vertex_count, strip_count` | 16 |
| Selection bounds | `u16 bounds_min[3], bounds_max[3]` | 12 |

Align the emit table to 32 bytes, putting two complete emit records on
each line. Eight consecutive emit records would then occupy four lines
instead of the current approximately seven. Total record data remains
28 bytes per meshlet, plus table alignment and the new version's header
metadata. Vertices, offsets, strips, meshlet IDs, draw order and materials
remain unchanged.

This needs a new, explicitly versioned R4IM contract with old-format
fallback. Do not reinterpret current v1/v2/v3 payloads. Define section
offsets, counts, overflow/alignment checks and CRC coverage before adding
the reader, and regenerate the CRC-coupled R4SG/room-file sections with
the private builder. A compact group-end table could likewise avoid
reading 16-byte selection records for their two-byte emit end offset.

Measure selection and emission together: selection can need fields from
both split tables, and selected IDs are not always consecutive. A four-
versus-seven-line contiguous example is not a whole-frame saving.
Separately validating each group's index enclosure at load time could
permit partial indexed gathering later. This candidate needs no repack,
new disc data, runtime assembly or linker change.

## Validation and reproduction

| Control | Result |
|---|---|
| Complete SH-4 production translation units, all 32 combinations of SELECT_ONLY, SUBMIT_BATCH, REPLAY_LEAN, UV_SNAPSHOT and SELECT_LEAN2 | PASS; native_static, native_ui and native_actor_fast |
| New knob absent and explicitly zero versus archived `dc87c465` | PASS; 384 byte-for-byte `.ii`/`.o` comparisons |
| Enabled knob leaves UI/actor preprocessing and objects unchanged | PASS; 128 comparisons |
| Make wiring, defaults, rejected dependencies and surrounding options | PASS; 128 configurations across three translation units |
| DEDUP=2 plus PREF_WALK=1 with all five prior switches enabled | PASS; 12 off identities, four unaffected enabled identities, enabled production compile |
| Source-extracted host emission, all 32 prior-switch combinations | PASS; 2,496 paired TA/accounting/SQ-lock comparisons |
| Same host emission with ASan and UBSan, all prior switches enabled | PASS; 78 paired comparisons |
| Actual target-instruction controls | PASS; 28 replay, six gather, ten matching 96-vertex population cases |
| Executed PREF addresses and ordering | PASS; 24 cases |

The production compiler is **SH GCC 15.2.0**. The Make-derived public
Test22 profile substitutes unavailable private assets and applies the
existing KOS PVR declaration patches to an isolated header overlay. It
does not build the private module manifest, patch a KOS library, or run
link guards. These boundaries and profile hashes are retained in the
receipt. Preprocessor line markers and object debug records are excluded
from identity comparisons; executable objects and the remaining complete
preprocessed text compare byte for byte. The 32-configuration run used
268 distinct compiler invocations, reusing artifacts only when the full
compiler input matched.

### Production code and stack size

These are complete `native_static.o` section sizes and compiler-reported
function stack frames, not a linked release or a measured call-stack peak.

| Surrounding configuration | Executable bytes OFF → ON | Allocated bytes OFF → ON | BSS bytes OFF → ON | `chunk_emit` stack OFF → ON | `ps2_pass` stack OFF → ON |
|---|---:|---:|---:|---:|---:|
| All five prior switches off | 67,040 → 67,820 | 110,627 → 111,407 | 17,212 → 17,212 | 136 → 144 | 8,988 → 8,988 |
| All five prior switches on | 69,292 → 70,008 | 112,879 → 113,595 | 17,212 → 17,212 | 128 → 136 | 9,376 → 9,376 |
| All five on, DEDUP=2 and PREF_WALK=1 | 72,044 → 72,648 | 115,783 → 116,387 | 17,236 → 17,236 | 128 → 136 | 9,376 → 9,376 |

Across the required 32 combinations, executable growth is **716–780 B**
and BSS is unchanged. The outlined flush lambda in the all-prior-off
configuration remains 848 B of stack. With all prior switches enabled,
the flush and emit helpers are inlined; `sizeof(MeshDraw)` remains 776 B
and `sizeof(ChunkPart)` remains 104 B. No new persistent buffers or heap
allocations are introduced.

For the all-prior-on configuration, the base, absent and explicit-zero
artifacts share these SHA-256 values:

```text
native_static.ii d19316d7dbf101e3a5dd3d24f2ead886d0fb4f540fe2db79ffec4c91adff4938
native_static.o  cc728646c35e4c66d5442cf606bd3ca27d51823160297f3b20170e62d7d11b24
```

The tested runtime source SHA-256 is
`30c25b2036b0126ada50601273b9f99c55bf4cb87f6ae5a95826075bd77ce7b0`.
The [portable JSON receipt](BUILD5_SCENERY_EMIT_PREFETCH_20261023.json)
retains the other configurations and the source/artifact identities.

The [reproduction tools](../../tools/cloud/build5/README.md) retain the
production source extraction and exact commands. The report's JSON
receipt records input/artifact hashes and the measured tables reported here.
The host emission control uses host floating point and a portable
adapter for the existing strip walk. Picks are controlled inputs, so its
32 macro combinations do not constitute end-to-end selector validation.
The SH-4 scalar control executes
compiled target instructions around an explicit geometry boundary and
executes gathering separately. It does not emulate FTRV/FSRRA, replay a
room, or model data-cache misses.

The remaining integration gate is the maintainer's knob-on r101 console
A/B, with matched view and actors, plus the usual STRICT/look and memory
checks before adoption. The cloud has not run Flycast, linked a release
image, or established physical-console acceptance. The option stays off.
