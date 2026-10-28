# Build29 source sweep and runtime diagnostics

The Build29 main handback is `docs/cloud/handbacks/build-29.md`. The generated
source appendix is `docs/cloud/handbacks/build-29-sweep.md`. This document covers
the source inventory and `FALLBACK_AUDIT29`; the scanner/converter documentation
in this directory describes the separate offline data work.

## Build and scope

`FALLBACK_AUDIT29` defaults to **0**. Enabling it requires `QA_MENU=1` and
`DRAW_FALLBACK_AUDIT=1`. For a modem/link build, also select
`QA_LINK=1 QA_LINK_REVIEW28=1`; Make rejects the old link producer for this larger
snapshot because its fire-and-forget DIAG path can lose parts. `QA_LINK=0` works
with or without the review knob. Nothing enables these knobs in a release
recipe.

The DFA dependency reuses its existing paged diagnostics and keeps the old
133-reason draw audit intact. Build29 adds its own guarded blocks in shared
files, a separate diagnostic buffer, and new object-specific defines. It does
not widen another feature's `#if` condition. Recovered source and platform
files restore their original logical line numbers after the added blocks, so
`__LINE__` in allocation diagnostics and KOS lock macros remains identical when
the knob is absent or zero. The target gate compares complete preprocessed
source and objects; it does not normalize away those differences.

The new production code counts observations. It changes no gameplay state,
collision predicate, event order, asset admission decision, I/O request,
rendering output or audio conversion result. No production assembly or linker
layout is added. The target cost fixture links existing compiled code at a
synthetic address and executes the native KOS IRQ instructions; that fixture
layout does not enter the game image.

## Counter interpretation

The core holds **33 unsigned saturating counters**. `FA29T` rows are cumulative
for the current room. They include work on skipped game ticks and asynchronous
disc/audio workers, and must **not** be divided by drawn ticks to claim
per-drawn-tick costs. The header says `totals=room` and
`totals_not_per_draw=1`. The `outside_tick` field counts instrumentation events
outside the active game interval; it does not sum their byte amounts.

`FA29D` rows preserve the last completed interval whose pacing decision allowed
a draw attempt. A skipped tick updates room totals but leaves this prior interval
and `draw_tick` visible. These are game begin/end intervals and pacing decisions,
not proof of a finished PVR scene or physical display flip. Asynchronous events
that occur inside that interval are included, as the header explicitly states.

The first room/tick arms collection. Before then, observations are ignored.
Changing room or a game reset clears room counters and the actor attribution
table. Opening the QA menu pauses collection, drops an unfinished interval, and
leaves the prior sealed snapshot readable; closing it resumes at the next game
begin. The actor table uses the game-thread-only `collecting()` predicate so
it obeys the same pause/unarmed boundaries. Device-worker observations use the
IRQ-protected `hit()` API rather than that predicate.

The core uses a short KOS IRQ save/restore section for updates and snapshot
sealing. It performs no allocation, log output, formatting or timer read per
hit. Overflow clamps a counter at `UINT32_MAX` and sets the saturation flag.
Formatting reads the immutable completed snapshot on the game/QA thread.
The units below are deliberately different; several reasons overlap.

| Rows | Units and what they count |
|---|---|
| `mot_miss`, `mot_bytes` | Missing motion keys and their requested byte sizes; not successful transfer bytes. |
| `mot_fast_retry`, `mot_read_retry` | Keys declining fast read, then actual retry attempts. |
| `anim_layout`, `anim_history` | Three-channel sampler groups declining layout or history fast paths. |
| `col_line_walk`, `col_sphere_walk`, `col_memo` | Pieces whose bounded line walk declined, tagged deep sphere nodes, and failed line-query reuse. One node/piece may involve many polygons. |
| `cloth_gx` | Sheets declining native cloth to the source GX dispatch. The GX compatibility sink does not produce a successful native image. |
| `esp_scan`, `efm_scan` | Visited source slots after map/owner fast path failure. Espgen and EspDelete have existing check-mode counters and are explicitly separate inventory rows. |
| `tex_miss`, `tex_evict` | Resident lookup misses and actual instrumented victim evictions. A miss alone does not establish thrashing. |
| `tex_guard`, `tex_slot`, `tex_pack`, `tex_refuse` | Instrumented load refusal sites and overlapping narrower classifications. These are missing/admission-refused visual work, not successful slow rendering. |
| `tex_no_block` | Terminal package failure with the PVR allocation error, not every intermediate failed retry. |
| `tex_reopen`, `tex_meta` | Package reopens for VRAM or streamed metadata failure. The separate headroom eviction loop can retire entries without a reopen. |
| `disc_bytes`, `disc_pio`, `disc_stream` | Logical requested sector bytes, physical selected PIO request bytes, and stream retry bytes. They can describe overlapping attempts. |
| `snd_convert` | Input bytes taking runtime sample decode/ADPCM conversion rather than a preconverted bank marker. |
| `snd_read`, `snd_read_fail` | Stream-cache requested bytes and failed reads; no successful-playback claim. |
| `snd_under` | Missing stream halves; this is starvation, not a slow decoder success. |
| `snd_main`, `snd_pend_full` | Driver steps run on the main-thread fallback and immediate callbacks caused by a full completion queue. |
| `gx_vertices`, `gx_list` | Immediate vertices and display-list bytes discarded by the compatibility GX sink. They complement the GC-ASSET gate and do not identify an asset's source provenance. |
| `ot_pool_full` | Rejected primitive/ordering-table entries; no successful fallback draw. |

The parent Build29 actor attribution adds up to 32 relevant model/info/part keys,
two compact rows per key, latest lighting/material context, exact-vertex and
setup counts, and explicit spill/saturation totals. Its scope is the current
room, not the previous drawn tick. The offline scanner must join those identities
and live context before naming the Ganado, pitchfork, hay or barn prop responsible
for the queue's observed exact-light work. Package flags alone do not prove the
runtime material scale, effective fourth light or normal basis.

## Reproducible sweep boundary

`source_sweep29.py` enumerates tracked and unignored source under `src/` and
`port/dreamcast/`, reads every matching C/C++/assembly/include/definition file,
and records a path/hash/size/line manifest. Discovery records retain every
matching keyword/dispatch candidate line. Files are classified as recovered
game/library, port runtime, shared native runtime, vendor, public placeholder,
tool/test or standalone demo/probe; a demo candidate is not silently counted as
a live chapter path.

`source_catalog29.py` supplies the reviewed split groups, physical source
anchors, recipe knobs, trigger/outcome classification, MODELLED structural
cost/traffic, chapter reachability qualification, existing/new counters and
offline evidence limits. The generator fails if an anchor or recipe knob goes
missing. It resolves all references to the inherited 133 DFA and new 33 FA29
registry symbols into `draw-reason-sites.tsv`.

This is a whole-source discovery manifest and a documented review, **not** a
proof that a keyword search recognizes every semantic branch. For example,
`em_sub.cpp` random-item fallback selects a gameplay outcome, an assertion or
owner abort is a failure rather than successful work fallback, and a recovered
MPEG lookahead decoder is not evidence that the native movie player executes it.
The table distinguishes those cases and names instrumentation gaps instead of
claiming every source candidate was dynamically measured.

The Make query records 1088 `?=` knobs, including all `GAME_`, motion, cloth,
collision, sound, GC-ASSET and drawing families. Values come from the existing
public build command, not guesses based on knob defaults. Public missing-data
overrides still apply: for example the tracked CH2 recipe asks for
`NMR_POOL_LOD=1`, while the buildable public command resolves it to 0. Neither a
recipe value nor a source branch establishes actual chapter 1-2 package
admission or frequency.

The generated receipt files are:

| File | Evidence |
|---|---|
| `receipts/coverage-summary.json` | Scope, discovery expressions, corpus digest, counts, dispositions, limitations. |
| `receipts/coverage-manifest.jsonl` | Every walked file, SHA256, size, lines, candidate count and reviewed group references. |
| `receipts/source-candidates.tsv` | Keyword/dispatch discovery lines; reviewed-file membership is not blanket branch acceptance. |
| `receipts/source-splits.tsv` | The reviewed table with exact public Make values and explicit chapter/data uncertainty. |
| `receipts/draw-reason-sites.tsv` | Stable166 registry reasons and current source references. |
| `receipts/recipe-values29.json` | Three actual Make profiles, all queried values, recipe input and source hashes. |

## Numeric observer evidence

`counter_cost29.py` compiles the unchanged core with the actual target recipe,
then executes 14 synthetic states on the existing SH-4 model. These values price
the observer, not the original slow paths. Both instruction-cache arms assume
perfect D-cache;32-byte lines are distinct architectural addresses touched,
including literals and stack, not hardware fill counts. Interrupt mask
save/restore instructions execute and restoration is checked; interrupt delivery,
scheduling, firmware and device waits are not simulated.

| Core operation | MODELLED warm/cold-I cycles | Loads/stores | Distinct32 B data lines | Observed fixture stack |
|---|---:|---:|---:|---:|
| Active hit, amount 1 or 8192 | 101 /177 |21 /7 |7 |20 B |
| Outside active tick |101 /175 |20 /7 |6 |20 B |
| Paused /unarmed hit |52 /94;55 /97 |7 /4;9 /4 |4 |20 B |
| Saturating active hit |103 /179 |23 /9 |8 |20 B |
| Begin same room |163 /258 |20 /46 |10 |28 B |
| Begin new room |452 /549 |27 /206 |23 |28 B |
| Seal drawn interval |271 /388 |98 /83 |23 |12 B |
| Seal skipped interval |171 /278 |57 /47 |17 |12 B |
| Read valid snapshot |208 /275 |86 /79 |26 |16 B |

The independent production core object has 1320 executable bytes,3060 allocated
bytes including 600 zero-fill bytes. Its compiler-local maximum stack is 60 B in
formatting; `hit` is 16 B, begin 24 B, end 8 B and snapshot 12 B. The fixture stack
column includes the wrapper and reached callees and must not be confused with
the compiler's per-function local figure. Actor table and QA/link storage are
separate and included in the main handback's target object budgets.

At200 MHz, assuming 30 ms of other work and 1000 active hits plus one same-room
begin and one drawn seal, the **MODELLED whole frame is 30.50717 ms**, with
0.50717 ms of observer overhead. At10000 hits those assumed figures become
35.05217 ms and 5.05217 ms. These are sensitivity examples, not measured chapter
hit rates or an optimization gain. They exclude formatter/link time, the weak
actor-reset callback and real data-cache/device/interrupt costs. A paired
observer-off console run remains necessary for performance acceptance.

## QA, link and host proof

`test_audit29.py` compiles the actual core with a host mutex substituting for KOS
IRQ exclusion. It checks unarmed/pause/reset/room boundaries, the retained drawn
interval under skips, asynchronous totals, all 33 saturated reasons, invalid
enum/format bounds, actor reset calls and 160000 concurrent worker updates.
Normal and ASan/UBSan runs pass. LeakSanitizer is disabled because this sandbox
cannot perform its process-task traversal; the core itself allocates no memory.

`test_qa29.py` extracts the unchanged production `snap_diag`, row loops, `addf`
and paging functions. It uses the real DFA/DSA/FA29/actor formatters, maximum
unsigned fields, all 32 actor rows, DSA top 8 models, WORLD_METER rows, a 63-byte
build name,23-byte preset and 20 complete 72-column log lines. The actual base
contributes 2944 bytes. A second stronger capacity test reserves the full 3071
pre-audit bytes and appends a sentinel:

| Profile | Actual full snapshot | Conservative base +sentinel | Remaining24 KiB headroom |
|---|---:|---:|---:|
| FA29+DFA+actor table |17313 B |17466 B |7109 B |
| Above +AL25+DSA/XLU |23543 B |23696 B |879 B |
| Above +DSA/OCC |24126 B |24279 B |296 B |

The intentionally over-wide actor stress sets even bounded flag/path words to
`UINT_MAX`, producing 9174 B versus the real bounded-field 9156 B maximum. Every
draw/FA29 field, final actor row and final log remains present. Actual paging
visits every non-header character. Review28 T and D snapshots reconstruct
exactly under initial refusal and 50/300/2000 ms drains with the 2400-byte queue
cap; maximum datagram is 1130 B. Old T is retained as a component regression
case only. The old unbounded/fire-and-forget D producer is not accepted for
FA29 link builds. Both normal and ASan/UBSan composition tests pass.

These host fixtures prove bounded formatting/transport state machines and
counter semantics. They do not simulate a modem, PVR image, console input,
real-room assets, hardware cache misses or logic-equivalence traces.

## Re-run

Run from the repository root with new output directories. `FA29_CXX`,
`FA29_KOS` and `FA29_SDK` name the same pinned compiler, KOS and sh4zam trees used
by the main target gate:

```sh
python3 port/dreamcast/tools/d367/fallback_scan/test_audit29.py --sanitize
python3 port/dreamcast/tools/d367/fallback_scan/test_qa29.py \
  --sanitize --output "$FA29_OUT/qa"
python3 port/dreamcast/tools/d367/fallback_scan/counter_cost29.py \
  --output "$FA29_OUT/cost" --sh4-cxx "$FA29_CXX" \
  --kos-root "$FA29_KOS" --sdk-root "$FA29_SDK"
python3 port/dreamcast/tools/d367/fallback_scan/recipe_values29.py \
  --output "$FA29_OUT/recipes" --kos-root "$FA29_KOS" --sdk-root "$FA29_SDK"
python3 port/dreamcast/tools/d367/fallback_scan/source_sweep29.py \
  --recipe "$FA29_OUT/recipes/recipe-values29.json" --output "$FA29_OUT/sweep" \
  --markdown "$FA29_OUT/build-29-sweep.md"
```

The compactor keeps all numeric results and source/object hashes, removes
repeated command arrays and substitutes local path prefixes only in receipt
text. It records the raw receipt's SHA256. It never transforms production code
or objects for the absent/zero identity comparison.
