# Build 18: r200 effect-queue admission and an existing spill tail

Date: 2026-10-26. Branch: `codex/fx-r200-entry-cap-20261026`.
Base: [`74154cae`](https://github.com/lamb2k/re4dc/commit/74154cae31b48ac6b15bfd6699a221da295cda63),
the newest `origin/t15/int` at final qualification. Work began on `ab31de24`;
the base was refreshed after Claude merged Builds 17, 19 and 20 plus the
portrait-hair update. The Build 18 runtime sources were unchanged by that
refresh; the public recipe and all qualification receipts were refreshed.
Issue: [#41](https://github.com/lamb2k/re4dc/issues/41).

## Finding

The reported `fx_dropped` counter identifies **byte exhaustion in the CPU
deferred frame queue**. It does not count Esp pool allocation failures, the
64-effect admission cap, texture misses, or the PVR hardware translucent
list filling. The same FIFO carries deferred model parts and effect packets;
effects reserve space for later UI/model work before using its spill arena.

The cheapest additional capacity is already allocated. A successful 24 KiB
room spill replaces the existing 8 KiB model-slab tail as the active spill,
but that original tail remains allocated. The default-off
`FX_R200_ENTRY_CAP=1` candidate lets r200 effects use that otherwise unused
tail when the active room spill cannot fit the submission. Under the current sizes this permits
**32 KiB total spill with 0 additional heap-4 or KOS heap allocation**.
It retains packet contents and FIFO order; additional previously refused
draws become visible. It does not increase the 64-effect cap or reduce the
UI/model reserves.

There is no private game data, current r200 capture or console available in
this environment. This is a source diagnosis of the named counter and a
selectable capacity candidate, not a claim that the current release still
loses 800 effects or that the candidate passes its appearance/FPS gates.

## The reported failures predate the room-spill implementation

The queue says `FX_ROOM_SPILL_KB=24` shipped from Test 19. The public records
and checked-in release recipes establish a different sequence:

| Evidence | What it establishes |
| --- | --- |
| [Test 20 retest, October 20](https://github.com/lamb2k/re4dc/issues/41#issuecomment-6295366465) | Build `26da4fe3`, `fx_dropped` 0 → 803 between recorded frames 1028 and 1628. |
| [Test 22 retest, October 22](https://github.com/lamb2k/re4dc/issues/41#issuecomment-6353589222) | Build `a2477bd2`, 827 effects skipped at entry. |
| [`a8546da0`, October 23](https://github.com/lamb2k/re4dc/commit/a8546da0dc7c71c3e4c08750b734d8c13c6a7963) | Introduces the `FX_ROOM_SPILL_KB` implementation, default off. |
| [`eb1fe953`, October 23](https://github.com/lamb2k/re4dc/commit/eb1fe95330d69f031a99a1d980d7ee146383308b) | Enables `FX_ROOM_SPILL_KB=24` in the recipe. |
| Committed Test 19/20/22 versus Test 23/24 release-knob files | The former do not contain that option; Test 23/24 do. |

Sources: [Test 20 knobs](../../tools/d367/test20/release-knobs.txt),
[Test 22 knobs](../../tools/d367/test22/release-knobs.txt),
[Test 23 knobs](../../tools/d367/test23/release-knobs.txt), and
[Test 24 knobs](../../tools/d367/test24/release-knobs.txt).
The public issue contains no newer retest proving that the current 24 KiB
room cell was allocated and exhausted. There may be a private run; its exact
program/knob hashes and allocation/queue logs are an owner question.
The committed [`mendezfx.mk`](../../game/mendezfx.mk) comment also records a
historical r200 need of **8 + 14.8 KiB**, which motivated the 24 KiB room cell.
That is the owner's recorded measurement, not a run reproduced here, and
strengthens the case for checking the current recipe before enabling more.

The 803/827 values are **cumulative refused submissions**, not a per-frame
capacity and not a count of live Esp objects. Do not size a pool as “800
sprites” from those totals, or derive an exact duration from the issue's
approximate description.

## The refusing sites and their limits

The source at the pinned base contains these `fx_dropped` increments:

| Consumer | Source site at base | Refusal |
| --- | --- | --- |
| Trimmed octagon, M3 octagon, ordinary sprite | `native_ui.cpp:8456`, `8497`, `8523`, in `re4dc_effect_sprite` | Required node/packet bytes fit neither the allowed primary space nor spill. |
| Laser line | `native_ui.cpp:8601`, `re4dc_effect_line` | Same byte-capacity test. |
| Native quad/strip and cloth row | `include/native_effect_strip21.inc:89`, `206` | Same arena exhaustion, with variable packet sizes. |
| Stage-one batch and haze batch | `native_effect_stage1_batch.inc:76`, `native_effect_haze_batch.inc:71` | Required batch cannot fit primary space or an already acquired spill. These paths do not acquire a spill themselves. |

Implementation references:
[`native_ui.cpp`](../../game/platform/native_ui.cpp),
[`native_effect_strip21.inc`](../../game/platform/include/native_effect_strip21.inc),
[`native_effect_stage1_batch.inc`](../../game/platform/include/native_effect_stage1_batch.inc),
[`native_effect_haze_batch.inc`](../../game/platform/include/native_effect_haze_batch.inc).
Line numbers above identify the unchanged base for history; use function names
in the candidate. The batch producers are not established as the reported
r200 source, but their shared queue ownership must remain consistent.

Ordinary admission is effectively:

```text
use primary only if:
  required + effect_margin <= primary_top
  primary_top - required - effect_margin >= max(8192, actual_UI_bytes)
otherwise use spill only if required <= remaining_spill_bytes
otherwise increment fx_dropped and refuse this rendered submission
```

There is no independent `deferred_count` ceiling here. The queue is a linked
FIFO whose backing arenas run out of bytes.

| Resource | Target limit or packet cost |
| --- | ---: |
| Primary frame arena | 26,624 B: 256 UI quads × 104 B |
| Minimum UI reserve | 8,192 B, or actual UI bytes when larger |
| Additional effect/model margin | 8,192 B by default (`FX_QUEUE_MARGIN=0` selects that default) |
| Maximum primary space available to effects before competing draws | 10,240 B |
| Original model-slab spill | 8,192 B by default |
| Current room spill | 24,576 B usable when its allocation succeeds |
| Ordinary sprite node + packet | 128 B: 32-byte aligned node + 96-byte packet |
| Octagon node + packet | 320 B |
| Laser node + packet | 192 B |
| Quad/strip node + packet | `32 × (vertex_count + 2)` B |
| Cloth row node + packet | `64 × (column_count + 1)` B |
| Separate sprite/quad/batch admission cap | 64 per native frame; refusal increments `fx_capped` |
| Source Esp slot | 336 B (`0x150`), with room-selected pool count |

The source Esp pool is managed by
[`PullEsp`](../../../../src/game/esp.cpp). Its dummy/refusal path logs
`ESP work full!!`; `ESP_POOL_DIAG` records `espd_refuse`. The actual r200
count is obtained from `ConsGetRoomValue(2)` and needs the owner's room data
or diagnostic log. Increasing that pool would cost 336 B per slot and would
address a different failure counter. Texture misses similarly increment
`fx_missing`, and the 64-effect cap increments `fx_capped`.

That cap applies to ordinary/octagon sprites, native quads and the two batch
paths. Laser lines and unclipped cloth rows neither test nor increment
`fx_count`; their queue capacity is bounded by bytes. Near-plane cloth
fallbacks call the capped quad path. Cloth rows also retain their existing
hardcoded 8,192-byte margin. The candidate preserves these distinctions.

## Where the memory comes from

The current `re4dc_model_deferred_storage` first tries the room cell and falls
back to the model-slab tail if allocation is refused. Its `tried` flag means
a refused room allocation is not retried during that room generation.

For `FX_ROOM_SPILL_KB=24`, the existing heap-4 charge is:

| Component | Bytes |
| --- | ---: |
| Usable room spill | 24,576 |
| Alignment allowance requested by spill owner | 32 |
| `Room4Cell` generation/ownership header | 32 |
| Allocator header + MAD tag | 64 |
| **Charged block before a possible absorbed fragment** | **24,704** |

The high allocator can absorb a final 32-byte fragment, giving a 24,736-byte
cell. This accounting follows
[`ui_bridge.cpp`](../../game/ui_bridge.cpp), `room_alloc4_high` and
`re4dc_static_alloc`. The current room spill gains 16,384 usable bytes over
the old 8 KiB tail but costs 24,704 heap-4 bytes; the original tail is still
part of the existing model slab.

That slab is allocated by the existing `ensure_model_storage`. Its packet,
preparation, spill and metadata ranges are disjoint: metadata begins after
`kModelDeferredSpillBytes`. The candidate neither enlarges the slab nor
forces its allocation to obtain a tail. A missing slab yields no extra
capacity. The candidate uses only the first **8,192 bytes**, even if an
existing `FRAME_QUEUE_SPILL_KB` setting has already enlarged the tail. It
does not move the metadata boundary or increase another arena's size.

**Heap reserve caveat grounded in source:** the existing static allocator
protects **81,920 B**, while the requested s30 acceptance floor is
**98,000 B**. A zero-new-allocation candidate does not prove that the current
24 KiB room allocation or a larger final binary meets the higher floor.
Keep the existing global allocation policy unchanged in this build, and
record the actual owner heap/cutscene gate. Static code/state growth is
reported separately from dynamic heap allocation.

## Why reuse is the cheapest additional-capacity candidate

| Option | New dynamic memory relative to the current 24 KiB room-spill recipe | Assessment |
| --- | ---: | --- |
| First reproduce on current recipe | 0 B | Necessary: public failures predate the room spill. It may already be sufficient. |
| Reuse the idle original 8 KiB tail for r200 effects | **0 B** | Adds 8 KiB usable overflow after a successful distinct room cell fills; candidate in this branch. |
| Increase room spill from 24 to 32 KiB | About +8,192 B heap 4 | Obtains the same extra payload while the old tail remains unused; poor first choice with a tight heap. |
| Reduce the effect margin | 0 B | Can move the refusal to later world/model work. It is not an exact restoration of reserved capacity. |
| Raise the 64-effect cap or grow Esp | Variable | Addresses `fx_capped`/`espd_refuse`, not the reported `fx_dropped`. |
| Merge or cull overlapping sprites | Depends on implementation | A visual approximation requiring a separate quantified pixel/appearance case; source proof does not establish which sprites are interchangeable. |

Reuse cannot help when the room-cell allocation failed and the original tail
is **already** the active spill. It also cannot create unbounded capacity or
remove PVR/rendering costs. Admitting formerly dropped effects adds draw work;
the owner must judge their appearance and frame cost.

## Candidate contract and diagnostics

`FX_R200_ENTRY_CAP` defaults to **0**. Enabling it requires a positive
`FX_ROOM_SPILL_KB` and `NATIVE_STATIC=1 EFFECT_SPRITES=1
D349_RENDERER_STACK=1 PVR_STREAM=1`; unsupported combinations stop at Make
and the native source has a matching compile guard. No release recipe is
changed. The existing live-room getter in `ui_bridge.cpp` is compiled for
this option, so the decision follows `pG->room_id`, not the last loaded world
package's room number.

Only a submission which would otherwise fail both its primary-space test
and active-spill test calls the new selector. Successful primary/room-spill
admissions retain their existing fast paths. The selector requires live
r200, a current-generation room cell, that exact cell as the active spill,
matching capacity, a valid cursor, and an already allocated, aligned,
disjoint model-slab tail. It never allocates, shrinks the UI/model reserves,
or lends an active fallback tail a second time. Batch paths still do not
acquire the room spill themselves.

The tail has one cursor for the existing deferred-queue lifetime. Selection
does not consume bytes: the existing producer reserves its packet exactly
once after any remaining validation. New nodes use the same FIFO and drain
as existing model/effect nodes. A room, generation, spill-owner or slab
change after the tail is bound poisons further tail admissions until the
existing queue reset; it cannot rewind storage underneath queued nodes.
`reset_deferred` resets the tail after normal drain or existing retirement.

With `FRAME_QUEUE_DIAG=1`, a bounded summary is emitted at queue reset even
when the extra capacity prevents every drop:

```text
FQDIAG r200_tail frame=... room=... used=.../8192 grants=... refused=... reasons=... peak=... queues=...
```

`used` is actual reserved bytes; `grants` counts successful storage
selections, including a batch that may subsequently fail another validation.
`refused` counts rejected tail selections, not source Esp objects. Unbound
attempts outside r200 are silent; leaving r200 after binding reports
`OwnerChanged`, so the selector's `OtherRoom` bit is not normally emitted.
`reasons`
is a bitmask of `1 << Result` in
[`fx_r200_entry_cap.h`](../../game/platform/include/fx_r200_entry_cap.h):

| Bit | Meaning |
| --- | --- |
| 1 / 2 | Wrong room / room closed |
| 3 / 4 / 5 | No room cell / stale generation / active spill does not match |
| 6 / 7 / 8 | No usable tail / invalid alignment or range / overlapping arenas |
| 9 / 10 | Invalid request size / active spill still has space |
| 11 / 12 | Extra tail exhausted / bound owner changed |

The summary covers the first 96 active queue lifetimes, then active queues
on frames divisible by 120; it adds no per-sprite log. The old general queue
peak excludes this third arena, so retain the new `used`/`peak` values too.
Logging the room at reset can show the destination after a transition; use
generation/retirement evidence with it rather than treating it as an
allocation-room proof.

## Synthetic packet and lifetime proof

**50 named cases pass in each of four ASan/UBSan builds**: integration
baseline, option absent, explicit 0 and enabled, for 200 case executions.
The fixture extracts the actual production provider, enqueue, packet,
model/UI admission, FIFO drain, reset and invalidation code. It runs real
strip/cloth projection and clipping with host floating point. Texture lookup,
heap-4 allocation, room lifecycle and PVR header compilation are controlled
shims; final model rendering is captured at its submit boundary. This is
synthetic runtime proof, not hardware packet-bit or private-scene proof.

The cases establish:

- All eight refusing sites and nine producer variants use the extra tail
  after a real 24 KiB synthetic room cell is consumed. Ordinary sprites,
  both octagons, laser, strip, cloth and three batch modes drain the same
  packet bytes as their successful non-overflow references.
- Actual model/effect interleaving retains FIFO order across primary,
  room-cell and tail storage; smaller model nodes can still use room-cell
  fragments. UI storage/reserves and model refusal behavior remain intact.
- A refused room allocation cannot reuse its already active slab tail;
  absent slab, missing spill, stale generation, room changes and invalidation
  refuse safely. A live room 201 with a stale loaded-world room 200 also
  refuses the r200 candidate.
- Exact fits, exhaustion and successive queue resets preserve ownership.
  Forty-two 192 B lasers plus one 128 B sprite fill 8,192 B exactly; the
  next laser refuses on bytes. Separately, the 65th ordinary sprite still
  refuses through the existing cap, not the tail capacity check.
- Three batches that fail late texture validation after tail selection
  consume no tail bytes, append no node and leave queued memory unchanged.

Baseline/absent/zero packet observations and 12 extracted preprocessed
production functions match. Nineteen enabled no-overflow, other-room and
cap observations also match baseline. The full target comparisons below
cover the production translation units beyond these host extraction seams.
The receipt records source hashes before/after, compiler identity, individual
cases and commands. LeakSanitizer is disabled because the sandbox cannot
inspect process tasks; ASan and UBSan are enabled throughout.

Reproduce from the repository root:

```sh
python3 port/dreamcast/tests/test_fx_r200_entry_cap.py \
  --base 74154cae31b48ac6b15bfd6699a221da295cda63 \
  --report /tmp/build18-host.json
```

## Target build and memory proof

The complete `native_ui.cpp` and `ui_bridge.cpp` translation units were
compiled with GCC **15.2.0**, repository-pinned KOS `804b3195` and SH4ZAM
`33fa4850`. The gate derives each unit's actual Make flags from the current
recipe, including native UI's final `-Os` and the bridge's `-O1`. It does not
substitute a small stand-in for either production translation unit.

**24 complete byte-identity comparisons pass**: three profiles × two units
× absent/explicit-zero × preprocessed source/whole ELF object. The profiles
are the public Test 24 recipe, queue diagnostic/log composition, and
`FX_ROOM_SPILL_KB=0` compatibility with the new option off. Debug records
are consistently omitted, all arms read source on stdin with the real
include directory retained, and no object bytes are normalized or stripped.

Both supported enabled profiles compile and link relocatably, resolving
the live-room getter exactly once. Enabling the option with zero room spill
is correctly rejected, as are option values 2 and -1. These are target
translation-unit/partial-link results, not a complete game ELF, disc image
or console run.

| Combined native UI + bridge raw-object delta | Recipe | Queue diagnostics |
| --- | ---: | ---: |
| Executable sections | +756 B | +1,068 B |
| Allocated sections, including zero-fill | +776 B | +1,212 B |
| Zero-fill state, already included above | +20 B | +44 B |
| New dynamic heap allocation | 0 B | 0 B |

The target `Tail` state is 20 B and temporary `Context` is 44 B. The real
`DeferredPart` is 20 B, rounded to a 32 B node; the complete production
layout probe establishes the packet/slab sizes in the earlier tables. The
65,536 B slab contains 12,288 B packet storage, 12,288 B preparation,
8,192 B spill and 32,768 B metadata in this recipe, with no separate static
lighting range. The new option adds no runtime assembly or linker change.

GCC's per-function stack frames change from 780 → 788 B for the effect
sprite producer, 456 → 464 B for the line producer, and 152 → 160 B for the
stage-one batch. The quad producer changes from 1,060 → 1,072 B and cloth
mesh from 7,200 → 7,204 B. Normal `reset_deferred` remains a 0 B frame; with queue
diagnostics its log path becomes 64 B. These are individual compiler frames,
not maximum whole-call-chain or task-stack measurements. The owner's final
link and stack/memory gates remain necessary; raw object-section deltas are
not an exact final-image or heap-budget prediction.

## Compiled selector cycles and data traffic

The independent helper gate executes the compiled production `Tail::select`
and `reset` using Make-derived SH4 flags. **All 22 cases pass**, including
invalid/overlapping ranges, failed-allocation alias, generation changes,
exact fits, exhaustion and reset. The caller fixture has explicit prebuilt
context and performs the single cursor decrement on acceptance; it does
not build packets or call the native room adapter.

| Helper case | Warm cycles | Cold-I cycles | Loads / stores | Read / written B | Distinct 32 B demand lines | Peak fixture stack B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First tail selection | 114 | 246 | 26 / 12 | 88 / 48 | 7 | 24 |
| First accepted reservation | 124 | 264 | 31 / 16 | 108 / 64 | 7 | 32 |
| Subsequent accepted reservation | 135 | 280 | 38 / 12 | 138 / 48 | 7 | 32 |
| Exhausted tail | 122 | 247 | 32 / 6 | 114 / 24 | 7 | 24 |
| Unbound other room | 40 | 113 | 10 / 6 | 35 / 24 | 5 | 24 |
| Failed room allocation, tail already active | 48 | 121 | 12 / 6 | 40 / 24 | 6 | 24 |
| Bound generation changes | 49 | 117 | 13 / 7 | 44 / 25 | 5 | 24 |
| Reset after drain | 8 | 43 | 0 / 5 | 0 / 17 | 1 | 0 |

Warm cycles use perfect instruction/data caches. Cold-I starts the model's
8 KiB instruction cache cold for that complete sequence, with data cache
still perfect. Counts include stack, fixture and literal-pool traffic;
instruction fetches are excluded from data demand lines. Distinct lines
depend on the synthetic placement and **are not measured misses or bus
transfers**. The receipt retains region counts, repeated demand visits,
instruction traces and model provenance. Helper fixture code is 518 B
executable / 674 B allocated, separate from the production object deltas.

### Native adapter, including its context setup

A second gate runs the **actual adapter from the unchanged complete native
UI object**, whose SHA-256 matches the enabled target-build object. Only its
local symbol's visibility is changed in a copy for fixture linking; its
instructions are unchanged. It retains real newlib `memset`, native globals
and the production selector. Explicit synthetic live-room/room-state
callbacks replace the owning game subsystems, and their instructions and
traffic are included and identified in the receipt. **All 10 cases pass.**

| Native adapter case | Warm cycles | Cold-I cycles | Loads / stores | Read / written B | Distinct 32 B demand lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| First tail selection | 249 | 492 | 57 / 46 | 204 / 169 | 13 |
| First accepted reservation | 261 | 517 | 62 / 49 | 224 / 181 | 14 |
| Subsequent accepted reservation | 273 | 508 | 69 / 45 | 254 / 165 | 14 |
| Exhausted tail | 257 | 464 | 62 / 40 | 226 / 145 | 13 |
| Unbound other room | 118 | 288 | 19 / 24 | 69 / 84 | 11 |
| Failed room allocation, tail already active | 189 | 374 | 42 / 40 | 152 / 145 | 12 |
| Bound generation changes | 190 | 342 | 43 / 41 | 156 / 146 | 12 |

The compiled production adapter's own stack frame is **92 B**. Combined
fixture stack peaks are 96 B for selection, 100 B for reservation, and
112 B for the continuous fill loop. Those include the fixture callers, not
the real producer/owner call chain. Native room lookup timing, the preceding
primary/spill checks, packet writes, FIFO drain, texture work, PVR/rendering,
logging and real data-cache stalls remain outside these timings. The
diagnostic profile is compiled but is not the timed profile.

**MODELLED whole-frame component:** assume a 200 MHz frame with primary and
room spill already consumed, and 43 extra-tail attempts from the uncapped
laser-line path. The continuous adapter fixture accepts 42 × 192 B
reservations, uses 8,064 B, leaves 128 B and refuses the next request. It
costs **11,559 warm / 11,833 cold-I cycles**, or **0.057795 / 0.059165 ms**,
with one cold-I start for the entire sequence. It records 2,916 loads,
1,854 stores, 10,716 B read, 6,771 B written and 14 distinct demand lines.
Those are admission-state/fixture accesses: the packet arenas are deliberately
unmapped and untouched by this cost fixture. Add the real lookup, queue-reset,
payload, drain, rendering and baseline frame costs before interpreting a
game frame. This figure is an overhead component, not total frame time or a
predicted FPS improvement.

The separate 128 B fill rows stress the selector up to 64 reservations and
one byte-capacity refusal. An ordinary sprite producer's 65th call stops at
the earlier cap, so that complete selector stress sequence is not presented
as a reachable ordinary-sprite frame.

## Reproduction and committed evidence

The [target-tool README](../../tools/cloud/build18/README.md) gives exact
commands for complete target builds, helper/native cost fixtures and compact
receipts. Each cost run freezes and rechecks its production/tool sources;
the model and toolchain hashes are retained. The isolated test linker and
symbol exposure are fixture work only; the game's linker is unchanged.

| Evidence | Receipt |
| --- | --- |
| 200 sanitized host case executions and packet/lifetime comparisons | [Host](BUILD18_FX_R200_ENTRY_CAP_20261026.host.json) |
| 24 complete off-identity comparisons, enabled compilation, sizes/layout | [Target](BUILD18_FX_R200_ENTRY_CAP_20261026.target.json) |
| 22 compiled production-selector cases and traffic | [Helper cost](BUILD18_FX_R200_ENTRY_CAP_20261026.cost.json) |
| 10 compiled native-adapter cases and reachable laser scenario | [Native cost](BUILD18_FX_R200_ENTRY_CAP_20261026.native-cost.json) |
| Compiler, public source archives and build provenance | [Toolchain](BUILD18_FX_R200_ENTRY_CAP_20261026.toolchain.json) |

## Owner evidence that decides adoption

Run the exact r10f → r200 entrance and truck sequence on the current recipe,
then the same build/data with only `FX_R200_ENTRY_CAP=1` added. Use separate
clean object directories and record resolved knobs, executable/overlay hashes,
room/heap generation and the actual source room. Keep the FX level, trim,
strip, haze, transparency and view options identical between arms.

Use the existing `FRAME_QUEUE_DIAG=1`, `FX_QUEUE_LOG=1` and `ESP_POOL_DIAG=1`
in both diagnostic arms, plus `WORLD_HOLE_DIAG`/`WHFIX` evidence. Retain the
`fx room spill` line with its `ok`/`refused` status. Distinguish:

1. **No new drops on the current baseline:** the older public evidence does
   not require a new release capacity setting.
2. **Room cell refused:** the active spill is the original tail, which the
   candidate must not hand out twice. Inspect free/largest heap cells and
   allocation timing before choosing another memory change.
3. **Room cell allocated and exhausted:** retain requested bytes, primary,
   room-spill and extra-tail usage, refused counts and packet types. Check
   that additional effects do not increase dropped world/model parts.
4. **A different counter rises:** investigate that distinct cap, texture or
   Esp pool rather than attributing it to this arena.

The owner must also run room exit/reentry, reset/save/load, source-draw end,
frame skip and sub-screen/movie transitions with the candidate. Check source
logic equivalence, FIFO/transparency appearance, frame timing and heap-4/KOS
peaks. Confirm the **98,000 B s30 floor** and the expected complete cutscene;
zero additional arena allocation is not a substitute for that run.

No GitHub issue reply, release/default change or merge is part of this build.
