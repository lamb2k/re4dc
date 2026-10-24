# Build 7: character vertex and palette bytes

Base: `d5c1ceab9e06461462669b3ce1d28a379747a74a` (`origin/t15/int`).
Branch: `codex/actor-bytes-lean-20261024`. Knob: `ACTOR_BYTES_LEAN=1`, default **0**.
The release recipe and the four audit fixes are unchanged.

## Decision and limits

The current AVK kernels already retain position matrices and lighting directions
across bone runs. Build 7 does not add another palette cache. It initializes a
part's constant ARGB only up to the largest visible meshlet prefix used so far,
instead of writing that same word for every meshlet. The exact integer headroom
fold is applied once to this constant. Per-vertex alpha keeps the existing path.

This removes repeated four-byte stores and, when applicable, the second
read/modify/write colour pass. **It does not remove the distinct vertex-cache
lines:** positioning and emission still need them. It changes neither source
records nor the generated assembly. A larger input-line reduction needs an
offline repack; a proposal is below.

The new colour high-water starts at zero for **each Part**, including parts
sharing a coarse submit window. Cache flags have a longer lifetime and cannot
serve as the colour-validity marker. `ACTOR_MOVCA=1` compiles the original path,
because position write allocation cannot preserve an evicted cache line's ARGB.

## Data map: what one meshlet reads

Sources: [actor implementation](../../game/platform/native_actor_fast.cpp),
[generated AVK kernels](../../game/platform/avk_sh4.S),
[character chunk adapter](../../game/platform/native_actor_chunk.inc).

| Data | Bytes | Read order and lifetime |
|---|---:|---|
| Blob header | 32/part | Stream offsets and meshlet count, before the meshlet loop |
| Meshlet header | 8/meshlet | Counts, first tuple and index-list offset |
| Optional LOD header | 8/meshlet | Selected record prefix and index-list offset |
| Tuple | 6/vertex | Three u16 indices: position, normal, UV; position and light passes revisit it |
| Optional tuple fields | +2 each | Colour index and baked colour |
| Skinned source position | 8/vertex | Three s16 coordinates and a palette ID, indirectly through the tuple |
| Source UV | 4/vertex | Two raw s16/u16 values, independently indexed |
| Source normal | 8 N16 / 4 small | Three s16/s8 components and a palette ID, in the later light pass |
| Original pose palette | 48/entry | Frame preparation input |
| Prepared position matrix | 64/entry | Once per position-palette run; two aligned 32-byte lines |
| Prepared light directions | 48/entry | Once per normal-palette run; two lines at the table's 16-byte alignment |
| Readiness | 2/entry | One byte each for position and light preparation |
| Lighting colour matrix | 64/call | Loaded into XMTRX once per light-kernel call |
| Small-normal lookup | 1,024 total | Three float reads per small-normal vertex; N16 does not use it |
| Transformed vertex cache | 32/vertex | Position writes xyzuv; light writes ARGB; emit reads in index order |
| Outcodes | 1/vertex | Position writes, then reduces and consults for clipping |
| Strip/index stream | 1/reference | Walked in original strip order; repeated indices revisit cached vertices |

The per-frame palette workspace is `114 * entries` bytes before 32-byte
allocation rounding. The maximum meshlet cache is 4,224 bytes (128 vertices and
128 outcodes), or 132 aligned lines. For `N` used vertices it needs `N` vertex
lines and `ceil(N/32)` outcode lines. Headers, input streams, palettes and output
are additional. Indirect source indices determine the actual input-line set;
dividing payload bytes by 32 is only a lower bound for dense, aligned data.

The emit order is header/counts, tuple-driven position/UV pass, outcode decision,
flags high-water, light/colour pass, optional colour fold, then strip emission or
clipping. Source tuple lines are revisited by the two passes, and the same vertex
cache lines are visited by position, colour and indexed emission. Build 7 removes
only eligible colour visits after the first initialized prefix.

### Recurring compiled-kernel accesses

These are steady kernel iterations, excluding call setup, palette switches,
tail/lookahead, outcode reduction, optional postprocessing and TA emission.

| Path | Loads | Load bytes | Stores | Store bytes |
|---|---:|---:|---:|---:|
| Position + UV | 10 | 20 | 6 | 21 |
| N16 lighting | 5 | 10 | 1 | 4 |
| Small-normal lighting | 8 | 18 | 1 | 4 |
| Position + N16 lighting | 15 | 30 | 7 | 25 |
| Position + small-normal lighting | 18 | 38 | 7 | 25 |

Position's 20 read bytes include four bytes of current tuple indices and four
more for future prefetch addresses, eight position bytes and four UV bytes. Its
steady iteration also issues three PREF instructions. N16 lighting reads the
normal index and eight normal bytes; small lighting substitutes four normal
bytes plus twelve lookup bytes. Thus logical input payload is 26 bytes for N16
or 22 for small normals, while recurring instruction bytes are higher.

Add 64 read bytes on a position-palette change; light directions read 48 bytes
initially and 36 on subsequent normal-palette switches (the fourth components
are no longer needed). The old non-AVK `ACTOR_LIGHT_ASM` path reloads a direction
and clamp per vertex; that is not the public AVK path and is not a new saving.

Already present: converter bone sorting, LOD-prefix ordering, once-per-frame
position-table preparation, per-part AVK argument/dispatch reuse under
`ACTOR_SETUP_LEAN`, flags/oargb prefix priming, and the optional `CHAR_CHUNK`
deduplication path. None is credited again.

The unchanged, Make-built kernels were also executed on restricted synthetic
32-vertex address fixtures. One N16 palette run reads 1,378 bytes and writes 896
bytes across both calls, including argument, stack and lookahead accesses. It
touches 78 distinct demand lines. Scattering only the source indices raises
that to 152 lines with the same instruction/byte counts: position alone goes
62 to 112, lighting 58 to 82. These per-pass line sets overlap.

| Unchanged 32-vertex N16 fixture | Position warm / cold-I cycles | Light warm / cold-I cycles | Read / written bytes | Combined demand lines |
|---|---:|---:|---:|---:|
| One palette, dense inputs | 1,268 / 1,583 | 1,203 / 1,475 | 1,378 / 896 | 78 |
| Four eight-vertex palette runs | 1,367 / 1,714 | 1,308 / 1,615 | 1,828 / 944 | 88 |

For the tested even N16 sizes `N=8,32,128`, one-run kernel traffic is `30N + 418` read
bytes and `25N + 96` written bytes. Each additional paired position/normal
palette switch adds 150 read and 16 written bytes, including readiness,
argument and stack accesses beyond the palette payload itself. These formulas
describe the qualified opcode fixtures, not odd-count tails or all renderer paths.

This is an address/control audit, not hardware FP conformance. Its adapter
admits only diagonal zero/one FTRV matrices, bounded integer FIPR operands and
an explicitly pinned FSRRA input/result of one. It executes the actual kernel
opcodes for addresses and branches, safely away from clipping boundaries.
General skinning/lighting correctness is outside this fixture's claim.

## Compiled measurements and exactness

The public Make recipe supplies the actor settings; no private recipe is
substituted. `ACTOR_SETUP_LEAN=0/1`, `ACTOR_DIRECT=0/1` (Make's
`NATIVE_ACTOR_DIRECT`) and
`ACTOR_BACKFACE_CONE=0/1` form eight target configurations. DIRECT=0 uses the
existing Make compatibility overrides for features that require direct submit.
All other target flags and generated headers come from Make.

The model assumes a 200 MHz SH-4, perfect D-cache, no DMA and zero store-queue
cost. Cold-I numbers are isolated phase entries; they are not multiplied by
every meshlet for a frame prediction. Synthetic target wrappers use the complete
production Part type with fixture inputs, then extract the
retained-colour setup, colour and half-post blocks. Unchanged lighting calls are
explicit return edges. Observer calls keep all constructor stores live, including
some production optimization may omit, and create artificial alias/register
boundaries. Position, flags priming, selection, emission, debug light toggling
and unchanged dynamic-light arithmetic are excluded. These are **compiled
phase costs**, not the complete actor draw cost.

Representative SETUP=0 generic-submit phase results (OFF -> ON):

| Part's visible meshlets / colour mode | Warm cycles | Cold-I cycles |
|---|---:|---:|
| 1 x 32, flat | 209 -> 221 | 407 -> 467 |
| 4 x 32, flat | 533 -> 338 | 731 -> 597 |
| 6 x 64, flat | 1,085 -> 472 | 1,283 -> 731 |
| 4 x 32, constant half-post | 1,853 -> 353 | 2,079 -> 610 |
| 6 x 64, constant half-post | 4,985 -> 493 | 5,211 -> 750 |
| 4 x 32, per-vertex alpha | 1,804 -> 1,819 | 1,959 -> 2,016 |
| 4 meshlets, dynamic light edge | 265 -> 276 | 411 -> 455 |

Once the prefix is initialized, an additional 32-vertex flat meshlet costs
108 -> 39 warm cycles in this wrapper; half-post costs 438 -> 42. A zero-meshlet
flat part's constructor/setup costs 97 -> 113 cycles, so repeated meshlets are
needed to repay setup in the ordinary flat case. The two production call-site
fragments and SETUP=0/1 are compared across 40 target sequences. The kernel
address audit separately covers 72 constrained fixtures.

| Phase | Load instructions | Store instructions | Read bytes | Written bytes | Unique demand lines | Repeated line touches |
|---|---:|---:|---:|---:|---:|---:|
| 4 x 32 flat | 118 -> 85 | 190 -> 93 | 360 -> 272 | 748 -> 360 | 46 -> 46 | 262 -> 132 |
| 6 x 64 flat | 210 -> 119 | 456 -> 133 | 580 -> 364 | 1,806 -> 514 | 78 -> 78 | 588 -> 174 |
| 4 x 32 half-post | 250 -> 90 | 318 -> 92 | 888 -> 292 | 1,260 -> 356 | 46 -> 46 | 522 -> 136 |
| 6 x 64 half-post | 600 -> 126 | 840 -> 132 | 2,140 -> 392 | 3,342 -> 510 | 78 -> 78 | 1,362 -> 180 |

One demand touch is a memory access to a line; repeated touches subtract the
unique demand-line count from all touches. For example, 4 x 32 flat has
308 -> 178 total touches. They are **not measured cache misses**. The counts
include constructor, metadata and stack traffic, not just ARGB stores. Different
real stack alignment/register allocation can change the surrounding line set.

For eligible visible meshlet sizes `n_i`, original colour stores total
`sum(n_i)`; the new path writes `max(n_i)`. It saves four bytes and one repeated
vertex-line visit per eliminated store. A constant half-post part also removes
its original per-meshlet colour load/store pass. Metadata and setup overhead
are included separately in the compiled phase measurements. Culled meshlets
perform no colour work in either arm.

### Full translation-unit size and OFF identity

| SETUP | DIRECT | CONE | Executable bytes OFF -> ON | Generic-submit stack OFF -> ON |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 42,076 -> 41,624 | 2,100 -> 2,044 |
| 0 | 0 | 1 | 48,752 -> 48,856 | 2,184 -> 2,188 |
| 0 | 1 | 0 | 60,320 -> 60,652 | 1,676 -> 1,684 |
| 0 | 1 | 1 | 67,928 -> 68,356 | 1,728 -> 1,736 |
| 1 | 0 | 0 | 42,084 -> 42,156 | 2,164 -> 2,172 |
| 1 | 0 | 1 | 48,812 -> 49,000 | 2,244 -> 2,256 |
| 1 | 1 | 0 | 60,096 -> 60,448 | 1,800 -> 1,812 |
| 1 | 1 | 1 | 67,760 -> 68,152 | 1,852 -> 1,864 |

No initialized-data or BSS increase. In the direct target fixtures, `Part` grows
116 -> 120 bytes, or 244 -> 248 with SETUP. Coarse `re4dc_actor_submit_chunks` stack remains 1,392
bytes in all direct configurations. The current direct/no-cone profile adds
332 executable bytes and eight generic-submit stack bytes. The other rows show
the compiler's output under each configuration.

An independent archive of the exact base was compiled with the same Make-derived
flags. All **32 comparisons** pass: eight configurations x absent/explicit-zero
x complete `-E -P` preprocessing/raw object. Debug information is consistently
omitted. The new definition appears only on the actor TU when enabled; generated
headers and other Make flags remain identical.

Supplemental target gates compile CHAR_CHUNK=1/2 (each +412 executable bytes)
and the supported DIRECT=0 UV16 profile (+148). MOVCA=1 has identical full
preprocessing and raw objects even with BYTES enabled (60,184 executable bytes
in both arms), proving the complete compile-time fallback. These four profiles
add eight zero-versus-base comparisons and two MOVCA ON-versus-base comparisons.

### Output comparisons

The complete actor TU, with recorded host AVK/store-queue/platform adapters,
passes 18 paired configurations: SETUP=0/1 x DIRECT=0/1 x CONE=0/1/2, five
bounded extras (AVK/N16 check mode, NO_CLEAR=0, MOVCA, UV16, CHAR_CHUNK), and one
ASan/UBSan pair. In total **3,253 paired scenarios** compare 12,795,456 TA words,
317,925 controlled-state words and 39,010 ownership events exactly.

Focused coverage includes increasing/decreasing prefixes through 128 vertices,
collapsed and culled meshlets, clipping, per-vertex alpha, colour changes across
32 new Parts and 32 new frames, coarse windows sharing scratch, UV16 packing and
CHAR_CHUNK expansion with repeated positions/different UVs. The direct diagnostic
fixture verifies nine actual half-post Parts and 2,262 expected final-colour
vertices, including five chunks in one window. Three deliberately broken variants
(skipped growth, inherited window colour prefix, omitted half-post fold) all fail
the expected ARGB assertions.

These are synthetic exact-output checks with explicit host adapters. They do
not replace the integration lane's console, Flycast or gameplay gates. Commands
and compact receipts are in [actor_bytes_lean](../../tools/d367/actor_bytes_lean/).

## MODELLED whole-frame contribution

For `P` matching parts and a measured setup/colour phase saving of `C` warm
cycles per part, the conditional frame contribution is `P*C/200000` ms.
Positive savings below mean less time; the count is an **explicit hypothetical
64 parts**, not an observed r101 actor mix.

| Hypothetical frame population | MODELLED warm saving |
|---|---:|
| 64 eligible parts, one 32-vertex meshlet each | **-0.00384 ms** (slower) |
| 64 eligible parts, four 32-vertex meshlets each | 0.06240 ms |
| 64 eligible parts, six 64-vertex meshlets each | 0.19616 ms |
| 64 eligible half-post parts, four 32-vertex meshlets each | 0.48000 ms |
| 64 dynamic-lit parts, four meshlets each | **-0.00352 ms** (slower) |

The four-by-32 flat case saves 24,576 ARGB store bytes across that hypothetical
frame; the six-by-64 case saves 81,920. These are colour-payload savings, not
guaranteed cache misses or memory-bus writes: positioning already dirties the
same vertex lines. A real mixed frame must include singleton/ineligible overhead
and the measured eligible populations before making a net prediction.

The measured 87 world parts at r101 and 50 at r100 are **not actor populations**
and are not used to scale this change. The reported 7.5 ms actor cost likewise
does not establish how many parts have constant lighting.

## Offline repack proposal (not implemented)

Preserve the existing tuple order, exact LOD prefixes, local strip indices and
translucent draw order. Replace indirect input payload with two dense streams:

| Stream | Proposed content | Bytes/tuple |
|---|---|---:|
| Position/UV | Raw s16 xyz and the two raw UV words | 10 |
| Normal | Raw s16 xyz, or raw s8 xyz | 6 or 3 |
| Optional | Existing colour-index and baked-colour words | 2 each |

An eight-byte joint-run entry can hold a u16 tuple count, u16 position-palette
ID, u16 normal-palette ID and u16 flags/reserved word. A meshlet's run offset and
count belong in the versioned layout metadata. Preserve each palette independently
across adjacent joint runs whose other palette changes; a selected LOD prefix
may end within a run. The builder must define and validate palette ID ranges,
run counts, prefix termination and readable tail padding.

Two streams suit the two existing passes: an interleaved 16-byte vertex would
make each pass revisit all input lines. With dense N16 inputs and no sharing,
the current logical payload is `26N` bytes; the proposal is `16N + 8R`, for `R`
joint runs. Ideal source-line visits across the two passes fall from about `N`
to `N/2`, plus run-table reads/alignment. Small-normal payload becomes `13N + 8R`
instead of `22N`. These are **layout estimates**, not a game census or cache-miss
prediction. A separate run per tuple can erase much of the benefit.

The builder must also measure total resident memory: multiple UV tuples and
meshlets currently share source positions/normals. Dense streams duplicate
that data, and retaining the original arrays for other paths can increase RAM.
Report both peak room memory and hot render lines before choosing the format.

Acceptance requires a new version/CRC contract; unchanged raw UV sign mode and
bits; unchanged normal precision/scaling and invalid-palette handling; equivalent
`world_of`/near-clipping inputs; exact strip/LOD order; and at least the kernel's
two readable lookahead records with valid indexed payload. Mutable, morphed or
materialized sources need a generation-correct rebuild or the original fallback.
Validate TA words and clipping decisions against the current reader before
adopting the layout. No reader or data-format change is part of Build 7.

## Open questions back to Claude

1. Can the actor census give constant-light/no-vertex-alpha parts, visible meshlet
   counts and vertex-prefix sizes per part, including how often `half_post` is set?
   Those quantities turn the conditional model into an r101 estimate.
2. Does matched console A/B show a benefit from removing colour writes while
   retaining the same unique cache lines? The scalar model cannot answer that.
3. For a builder-only repack experiment, how much source sharing must remain
   resident for clipping, mutable models and fallback draws? That decides whether
   the proposed input-line reduction fits the existing memory budget.
