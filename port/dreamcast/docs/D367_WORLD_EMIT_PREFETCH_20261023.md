# Build 5: world emit in data-cache order

Base: `20df6734578cacc7033bb32a660d4b466a7cfbe9` (`origin/t15/int` at build start). Branch: `codex/world-emit-prefetch-20261023`.

`SCENERY_EMIT_PREFETCH=1` is an exact render-only candidate, default **0**. It skips gather/prime for empty picks after the original bind and reserve checks, gathers only the selected indexed vertex span when dedup does not require all corners, and stages bounded RAM hints across the queued run. No new runtime assembly, linker changes, package layout, allocation, or draw sorting is added. The four Build 4 audit fixes and the release recipe are unchanged.

The current Make-derived public Test 22 profile includes the current `rr/recipe.conf` CH2 overrides, including `SCENERY_SELECT_ONLY=1`, `SCENERY_REPLAY_LEAN=1`, and `SCENERY_SUBMIT_BATCH=1`. Private actor build inputs use the existing public fallback settings; this does not change the world input format. Comparisons use this same profile in both arms.

The reported 7.42 -> 6.88 ms/tick r101 world measurement belongs to the already-landed changes. It is not a Build 5 result. Frame models below use **87 parts at r101 and 50 at r100**. Selected meshlets per part and indexed/partial/empty frequencies remain unknown.

## 1. What actually executes

The Make-derived public Test 22 profile includes current recipe overrides: SELECT_ONLY, REPLAY_LEAN and SUBMIT_BATCH=1, SCENERY_CHUNK=1, MESH_VP_SCHED=1, MESH_STRIP_LEAN=1 and PS2_WORLD_LEAN=23. Its world path is:

`ps2_pass -> chunk_select -> chunk_flush -> chunk_emit -> emit_pick -> transform_sched -> strips_lean -> walk_lean -> SQ`.

`chunk_submit.cpp` does **not** execute this path. Its `pref @sq` / `sq_flush` sends store queues; it is not RAM lookahead. That file is unchanged.

Existing `PREF_WALK` hints the next header during selection and next vertex/strip during replay, within a part. For indexed meshlets, its pool-base hint need not address the first referenced corner. The scheduled transform already requests source input +36 bytes, advancing 12 bytes/vertex. New hints target startup lines; they do not replace that interior stream or prove a latency benefit.

## 2. Data map in execution order

Let `V` be the meshlet's corner count, `N` its transformed count, `I` the indices in visited strips, `E` the indices actually sent, `S` the visited strips, `Cs` the screen-culled strips, `G` the strip-group count and `P` newly primed projected slots. These are per meshlet. A world **part is not a meshlet**; measured 87 r101 / 50 r100 parts must not be multiplied by an assumed meshlet count.

This maps the baseline path. Section 6 identifies the implemented changes; the unchanged transform and strip loops still have the traffic below.

| Order / path | Demand data | Size / useful bytes | Access order and repeated touches |
|---|---|---|---|
| Queue replay, once per part | `ChunkPart`: matrix, key, cull, sky, optional owner UV | matrix 48 B; material key 24 B; owner UV 8 B when enabled | Ordered queue traversal; original per-part ownership/order remains. |
| Replay UV, once per part | `MeshPart::uv_bias`, `uv_scale` | 16 B within a 36 B part record | Copied through replay_part/batch and into transform constants on first borrow. |
| First pick's bind | Material key, header cache slot, texture entry, owner/pass state | Header slot 40 B; outgoing header 32 B; four cached header words used | Header-cache hit still validates texture/owner state; variable set scan. Bound guard prevents a material lookup/header per strip or per subsequent pick. Do not invent a per-strip bind saving. |
| Every pick | `Pick {let,nr,gmask,lo,hi,pad}` | 8 B allocation, 6 B useful | Four aligned picks fit one 32 B line; current and lookahead can reread same queue line. |
| Every pick | `Meshlet` prefix: first_vertex, first_strip, strip_bytes, vertex_count, indexed flag | 16 B useful within a 28 B record; bounds occupy trailing 12 B | Prefix read around gather, prime, transform and strip setup. Selection has already read this table earlier; whether it remains resident is unknown. |
| Indexed v3 only | u16 pool-offset table immediately before strips | `2V` B | Sequential offsets, each selecting a 12 B source corner from the shared part pool. |
| Indexed v3 only | Shared-pool AoS12 corners -> gather scratch | `12V` B read + `12V` B written | Offset order can jump backward/forward through pool; all V are gathered even if N is a smaller selected range. Transform then rereads gather scratch. |
| Lazy prime if V exceeds watermark | flags/oargb of projected cache slots | `8P` B written | Two 4 B writes per 32 B slot; P distinct projected lines. Already amortized by PS2_WORLD_LEAN prime reuse. |
| Transform setup | `k.f` | 36 B read (nine float loads); other k pointer/mask fields read by compiled wrapper | Same constants loaded per transform; 36 B spans two lines for 4-byte-aligned storage. |
| Transform, nonindexed | AoS12 input `[lo..hi]` or full meshlet | `12N` B read in three u32 loads/vertex | Monotonic input stream; indexed case reads the gather scratch instead. |
| Transform | ARGB LUT high/low words | `8N` B read | Two scattered u32 accesses per vertex to two 1 KiB halves. Distinct lines depend on colors. A 32 B-aligned 2 KiB LUT has at most 64 lines; this is not 64 cold misses per meshlet. |
| Transform | Projected x,y,z,u,v,argb and outcodes | `24N` B + `N` B written | One 32 B projected line per vertex; six words written in the scheduled front/back order. Outcodes sequential, one byte each. |
| Partial pick only | Group strip-end fields `g[8*q+6]` | `2G` B useful within `16G` B records | Reads every group end in ascending q, even rejected groups, to recover each range's previous end. Bounds and per-group vertex limits are cold to emit. |
| Every visited strip | count byte + index bytes, then outcodes by index | `S+I` strip bytes, `I` outcode bytes | Index scan is sequential within each strip; outcodes are indirect. |
| Accepted strip | Same index bytes again + projected cache by index | `E` index bytes + `32E` cache bytes | Second pass over accepted indices, four 64-bit cache loads per reference, generally indirect cache order. Shared corners repeat lines across strips. |
| Accepted strip | SQ writes and EOL correction | `32E` bytes + four-byte EOL overwrite per emitted strip | Four 64-bit SQ stores/reference; one SQ `pref` sends each completed 32 B record. These are not cacheable output lines. |
| Depth crossing / oversize strip | `clip_strip` re-reads indexed source corners, current UV/material constants | Data dependent | Existing fallback recomputes corners/clipping; preserve as-is. Never claim the common-path byte formula covers clipping. |
| Part end | slot/counter state, direct/end batch | No new meshlet geometry reads | Same per-part accounting/order; submit batching may retain SQ lock across eligible parts. |

For a **screen-culled** strip, `walk_lean`'s branch delay slot additionally reads its first index once; depth-culled strips do not execute that read. Census/TA_HASH builds reread more data for diagnostics; production formulas exclude those intentional audit passes. SCENERY_DEDUP also adds its documented side tables and repeat-fill reads, so price it separately.

## 3. Lines and repeat formulas

For address `a` and byte count `b`, `L(a,b)=0` for b=0, otherwise `1+floor(((a mod32)+b-1)/32)`. These are demand footprints, **not cache misses**. Shared physical lines must be unioned, not summed.

- A 16-byte hot prefix at 28-byte stride touches 1–2 lines per record, averaging 1.375 isolated visits; eight aligned records occupy seven unique lines.
- Direct input: `L(first+12*lo,12*N)`. Indexed offsets: `L(offsets,2*V)`; pool lines are the union of the referenced 12-byte corner spans; scratch writes occupy `L(gather,12*V)`.
- Projected cache: N aligned 32-byte slots written. E emitted references to U distinct corners cause E−U repeated projected-line reads; every emitted slot was written earlier.
- Outcodes occupy `L(oc+lo,N)` lines; index reads are sequential but outcode/cache reads are indirect. Accepted indices are read twice without necessarily causing another miss.
- Partial emission reads G u16 ends at 16-byte stride: aligned G=4 uses 8 bytes from two lines; G=8 uses 16 bytes from four.
- LUT footprint is the union of indexed word addresses, at most 64 lines for the aligned 2 KiB table, not 64 misses per meshlet.

Core loop counts for N>0, excluding compiler setup/spills, clipping, dedup and diagnostic passes:

| Metric | Baseline count |
|---|---|
| Demand load instructions / bytes | `5N+9+S+2I+5E+Cs` / `20N+36+S+2I+33E+Cs` |
| Cacheable store instructions / bytes | `7N+2P` / `25N+8P` |
| SQ store instructions / bytes | `4E+emitted_strips` / `32E+4*emitted_strips` |
| Extra indexed gather | `4V` loads, `14V` read bytes, `3V` stores, `12V` written bytes |

EOL overwrites do not add outgoing vertex payload. Section 7 prices compiled phases separately.

## 4. Why the gather cuts are exact

Baseline `emit_pick` gathers all V corners and primes projected slots before rejecting `nr==0`. The new empty return follows the original bind, `borrow_gather`, `borrow`, and census setup, so material/owner failures and accounting still execute. Census records zero transformed corners. The prime watermark can remain lower: every later consumer still initializes missing flags/oargb before use. The original empty path already skipped transformation, so this saves gather/prime work only.

For partial indexed picks, the existing selector already guarantees every selected strip index lies in `[lo,hi]`. The new gather copies that span into the **same scratch slots**, preserving clipping and strip indices. All clipper and CPU backface variants consume selected-strip indices. SCENERY_DEDUP is the exception: its fill can read repeated-corner UV/color records outside the selected span. Repeat-bearing meshlets therefore retain full gather. Whole picks never consume lo/hi, and empty picks return before range arithmetic.

The source-level reduction is `4*(V-N)` loads / `14*(V-N)` read bytes and `3*(V-N)` stores / `12*(V-N)` written bytes. A hypothetical V=64,N=12 saves 1,352 B before hint/control costs; this is not an observed r101 shape. Source-pool line savings depend on offset locality, not simply N/V.

One-pick payload lookahead uses the current transform and strip walk as lead time. The existing transform's source model is about 36*N scheduled cycles; this is a rationale for the distance, not a measured memory-latency guarantee. A deeper lookahead could increase interference. Header hints precede current bind/borrow, so an already-bound or empty pick supplies little header lead. No future material, cull, owner, sky, UV or matrix state is installed early.

## 5. Offline repack proposals for local builder owner

The runtime reader keeps the existing data format. These are proposals for the local world builder owner; none is implemented here.

1. **Separate emit and bounds records:** a 16 B emit header `{u32 first_vertex, first_strip, strip_bytes; u16 vertex_count, strip_count}` in an aligned stream, and a 12 B bounds stream used by selection. Eight consecutive emit headers then occupy 4 lines instead of the current 7-line header stride footprint, a 43% metadata-line reduction for that run. Total record bytes remain 28/meshlet before section alignment. The loader must version and validate both streams; preserve identity/index/LOD/SG mappings. Alignment-only padding to 32 B would increase storage 14.3% and does not achieve the same stream compaction.
2. **Compact group end stream:** G u16 end offsets per meshlet beside its emit metadata, rather than striding across 16 B selection records. G=4 gives 8 useful bytes packed into up to 1 aligned line per isolated meshlet, and four meshlets per line if packed; existing aligned G=4 touches two SG lines per partial emit. Prefer replacing/splitting fields in the format to duplicating side tables if memory-neutral storage is required. Group bounds/ranges remain for selection, and empty/equal endpoints preserve exact semantics.
3. **Pool locality:** analyze actual indexed-v3 offset order and reuse before duplicating corners. Stable local vertex pools can cut gather jumps while preserving strips and TA order, but fully expanding shared meshlets costs roughly 10 extra stored bytes per formerly offset-only local corner (12 B vertex vs 2 B offset), before shared-pool lifetime accounting. Report room heap/door overlap and bytes saved per frame; do not adopt a memory-expanding layout on a guessed performance win. Original bounds, strip group ranges, SCDD/SCPS metadata and CRC dependencies need rebuilding and validation.

## 6. Implemented scheduling

`chunk_emit` hints the next hot header; after successful current bind/borrow, `emit_pick` hints its payload. `chunk_flush` seeds the first pick once. The `cpk+npk` bound permits lookahead across parts, including empty queued parts, without changing draw/end/failure order.

Each contiguous-range helper requests at most two backed 32-byte lines. Direct input starts at the selected vertex; indexed input hints the applicable offset range and the first actually referenced pool corner. It does not prefetch the whole scattered gather. Strip-start hints occur only for whole picks or a selected first group, with nonzero strip bytes.

When enabled, these hints replace `PREF_WALK` replay hints. Its selection hints/runtime mask and the transform's existing +36-byte stream hints remain unchanged. Fallback nonchunk paths, clipping arithmetic, TA order and Build 4 fixes are untouched. The gather/empty changes above provide the proven demand-traffic reduction; hints alone do not reduce demanded lines.

## 7. Verification and compiled cost

The checked-in [build receipt](../tools/d367/world_emit_prefetch/build_receipt.json), [geometry receipt](../tools/d367/world_emit_prefetch/geometry_receipt.json) and [target receipt](../tools/d367/world_emit_prefetch/emit_target_receipt.json) record commands, source/toolchain hashes, counts and scope. All **64 configurations × 3 complete translation units** pass: **768 absent/zero preprocessed-source and raw-object identity comparisons**, plus **256 enabled unaffected-TU identities**. The matrix crosses all five existing knobs with PREF_WALK, validates actual Make flags/generated headers and finishes with matching frozen source hashes. Artifact reuse leaves 524 unique compiler invocations; no comparison is omitted.

**Exact output:** 74,880 TA/accounting comparisons pass across all 32 combinations of SELECT_ONLY, SUBMIT_BATCH, REPLAY_LEAN, UV_SNAPSHOT and SELECT_LEAN2, plus PREF_WALK and census variants. The 130 synthetic cases include partial/clipped indexed picks, poisoned unused slots, dedup repeats outside the selected span, dynamic UV, cross-part lookahead and reserve/owner failures. ASan/UBSan adds 390 passing comparisons; ten guard-removal controls expose the intended faults. Prime-work counters may decrease; TA words, semantic accounting, census and lock boundaries match. The fixture executes production bodies with portable transform/SQ/FMAC edges and supplied picks. It does not execute the selection algorithms or qualify target floating-point rounding.

**Compiled phases:** 84 cases in four new-knob/PREF_WALK arms pass. These execute actual SH-4 gather/hint code and already-bound empty `chunk_emit`, without executing FTRV/FSRRA or timing complete nonempty emission. Warm means perfect I-cache; cold means an initially cold 8 KiB I-cache in a synthetic ELF. Both assume perfect D-cache, no DMA and no SQ bus cost. PREF gets no credited latency benefit.

| Synthetic case, per meshlet | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Loads / stores OFF → ON | Read / write bytes OFF → ON | Distinct demand lines OFF → ON |
|---|---:|---:|---|---|---:|
| Indexed gather V16, N4 | 445 → 159 | 533 → 260 | 101/49 → 45/14 | 330/196 → 141/56 | 27 → 18 |
| Indexed gather V64, N4 | 1,645 → 159 | 1,733 → 260 | 341/193 → 45/14 | 1,098/772 → 141/56 | 66 → 18 |
| Indexed gather V64, N32 | 1,645 → 859 | 1,733 → 960 | 341/193 → 185/98 | 1,098/772 → 561/392 | 66 → 50 |
| Empty indexed V64, already primed | 1,762 → 138 | 2,007 → 392 | 457/217 → 55/25 | 1,540/868 → 200/100 | 75 → 20 |
| Empty direct V64, already primed | 150 → 138 | 363 → 392 | 64/24 → 55/25 | 226/96 → 200/100 | 23 → 20 |

These totals include compiled setup, literals and stack. Line counts are address-set observations, not cache misses, and physical fixture alignment affects edge lines. V64/N32 demand line visits fall **534 → 283**, with repeat visits **468 → 233** after subtracting the distinct union. All those accesses stay within one line. The scattered pool still touches about 24 source lines despite halving its read bytes; gather scratch falls 24 → 12 lines. This motivates the pool-locality proposal.

Nonqualifying cases cost more: gather-only whole indexed picks add 6 warm cycles; direct picks add 5; a partial pick spanning all V adds 14. The new partial loop still rereads its high-bound queue byte; that repeats an already-demanded line. A positive next-pick hint adds **91 warm / 154 cold-I cycles for direct data**, or **112 / 215 for indexed data**, relative to the enabled empty-current control. It adds 85/99 demand-read bytes, 16/20 store bytes, 6/7 distinct lines and 5/6 PREF requests respectively. First-pick seeding also costs work. These controls measure overhead, not a demonstrated prefetch win.

Release-profile executable size is **68,016 → 68,592 B (+576 B)** for native_static, with no BSS change. `chunk_emit` grows 1,824 → 2,080 B; the new payload helper is 286 B; flush grows 32 B. `ps2_pass`, ordinary draw/run and selection function sizes stay unchanged. GCC's `chunk_emit` frame grows **128 → 140 B**; the positive-lookahead path peaks **128 → 160 B**, including the new helper. `ps2_pass` remains 8,992 B. Isolated gather-wrapper stack is a separate 4 → 12 B measurement, not the production call-path delta.

## 8. Whole-frame model — MODELLED, conditional

At 200 MHz, the V64/N32 gather saves 786 warm cycles. If there were **one eligible meshlet per measured part**, its gather contribution would be **0.342 ms/tick at r101 (87 parts)** and **0.197 ms at r100 (50 parts)**. This population is an illustration, not an observed room histogram. Multiply by the actual eligible meshlets per part; do not treat part counts as meshlet counts.

For that same illustrative population, charging one indexed lookahead at the measured 112-cycle incremental control cost per pick consumes about **0.049 / 0.028 ms**. Subtracting just that yields **0.293 / 0.169 ms** as an additive phase-budget estimate. First seeding, nonempty control/layout interactions and hints paid by every other nonqualifying pick remain outside this estimate. It is **not a measured or fully modeled net frame saving**. A population with no empty/partial indexed picks could regress in the perfect-D-cache model.

The general frame budget is the sum of actual gather/empty savings, minus fallback/control costs and hints on all affected picks, divided by 200,000 cycles/ms. No D-cache stall savings are assumed. Actual meshlet counts and eligibility, plus console cache behavior, are needed to replace this conditional estimate. The earlier measured 7.42 → 6.88 ms world result is not added to it.

## 9. Reproduction and local gate

From the repository root, run `world_emit_prefetch/build_controls.py` and `measure_target.py` with the SH-4 compiler, KOS root and public SDK paths recorded in their compact receipts. Run `check_geometry.py`, its `--smoke --sanitize` arm, and `verify_guards.py` with fresh output directories. The receipts preserve the exact invocations and full-result hashes; no private game data is required.

Preprocessing uses `-E -P`; debug records are consistently omitted from object comparisons, with executable flags derived from Make. Target fixtures use a synthetic link and trapped external edges. No full release image, Flycast run, console timing or leak-check result is claimed. Local gates should compare the same recipe and PREF_WALK mask, collect selected/empty/partial meshlet populations, and check TA/gameplay and console timing before release enablement. Questions are in the queue's **Open questions back to Claude** section.
