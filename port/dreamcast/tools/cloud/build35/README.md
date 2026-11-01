# Build 35: fallback events and exact drawn-tick windows

Both controls default to zero. `FALLBACK_AUDIT35=1` adds 58 reasons after the
existing 33 FA29 reasons. `FALLBACK_WINDOW35=N` independently selects a fixed
ring of the last N completed draw-attempt ticks, where N is 1 through 64.
Both require `QA_MENU=1 DRAW_FALLBACK_AUDIT=1 FALLBACK_AUDIT29=1`. A link build
also retains the existing `QA_LINK_REVIEW28=1` requirement. No release recipe
enables these diagnostics.

## Interpreting counts

The registry in `game/platform/include/fallback_audit35.def` supplies stable
labels and units. Counts of different units overlap; they are not a workload
total or a time estimate.

- Cloth spring calls count the algorithm that actually runs. Comparison mode
  can run both algorithms. Grid points and chain links are separate measures;
  required simulation is not an optimization failure.
- Front texture hits/builds/refusals/source calls are separate events. A cache
  lookup can hit and the subsequent swap admission can still refuse. Flushes
  count materialized textures. `ft_reset` counts capacity resets, not ordinary
  room changes. Build 34 descriptor refreshes count as builds.
- Effect scan counters count actual scalar slot visits. A mapped call can
  later visit scalar slots after a generation change; a stale event requires
  such a visit. Map selection is not proof the entire call remained mapped.
  Empty owner results and zero-owner queries have their own reasons.
- Collision source/fast units are `list_runs`: one list-pipeline invocation,
  not one event for each of its three internal passes. Overflow reasons mean
  an optimized representation refused; they do not mean collisions were lost.
- Motion binary/linear are compile-time alternatives. `mot_probes` includes
  the binary-search equality check. A missing binary key does not trigger a
  runtime linear retry. Found records, missing keys and unbound calls differ.
- Skin deferral counts include positive pending-palette, native skin and face
  deferrals. CPU counts begin only when the vertex skin call will execute;
  failed allocations and pointer errors are excluded. Morph is a subset of
  CPU skin work. Native admission failures can also have CPU events. Palette
  reasons count positive matrix counts, not calls or weight influences.

`FA29T` remains a room total including completed logic, skipped logic and
asynchronous events outside the active tick. With a window enabled, `F26W`
and `FA29W` sum only completed ticks whose pacing decision attempted a draw.
They make no assertion about GPU presentation. `used` is the denominator for
per-drawn-tick frequency. `full=0` is a partial ring, not an implied zero for
missing samples. `span_logic` and `span_skip` include completed skipped ticks
since the oldest retained draw, including those after the latest draw.
Incomplete ticks and outside-tick room activity are reported separately.

The 64-bit sums are exact for up to 64 unsigned 32-bit inputs. A saturated
input marks its row inexact until that row expires. This is independent of
the sticky old room-total saturation flag. Counter-overflow metadata prevents
an exact claim after a denominator saturates. Pause freezes the sample; resume
starts a new capture interval; a room/restart reset invalidates old samples.
Old ring slots are unreachable until rewritten, so reset clears the sums
without scanning all N slots. Ring updates happen after interrupts are restored.

## Bounded storage and transport

The ring has fixed static storage and makes no allocation. It never borrows
room memory or silently lowers N. All 224 reasons together use 896 bytes per
row plus 16 bytes of row metadata, 1,792 bytes of sums and bounded scalar state.
Window-only builds retain the existing 166 reasons and therefore use less.
The target receipt reports actual BSS, text and stack, including ABI alignment.

Maximum-width QA values require more than the old 24 KiB snapshot. Either new
control selects a separately guarded 32 KiB buffer. Its effective increase is
8 KiB; an enabled link's immutable transport copy adds a further 8 KiB. The
maximum-fields capacity test reserves the full existing non-audit formatting
block and checks a trailing sentinel. Every audit row must fit its existing
192-byte scratch, and the complete snapshot must survive multipart delivery,
backpressure and reassembly. These buffers are distinct from the ring.

## Event verification in trans.cpp

From the repository root, use fresh output directories:

```bash
python3 -B port/dreamcast/tools/cloud/build35/trans_events.py --output "$OUT/trans-events"
python3 -B port/dreamcast/tools/cloud/build35/trans_events.py --sanitize \
  --output "$OUT/trans-events-sanitized"
```

Ten profiles cover 105 scenarios / 689 assertions per run: front cache 0/1,
native skin disabled/eager/lazy, pending palettes, face deferral, and existing
`SKIN_CENSUS=0/1`. The fixture extracts the complete production
`commonScreenMatSub`, cache helpers and all three native texture-init blocks.
External allocation, defer admission, matrix and skinning edges are controlled
doubles. Palette tests execute the actual admission/event prefix up to the
arithmetic loop. This tests event placement and multiplicity; it is not a
matrix arithmetic oracle, full game replay or image equivalence result.

The host and ASan/UBSan receipts record the exact consumed source, headers,
templates and extraction hashes. Leak inspection is disabled because sandbox
`/proc` traversal is unavailable. Whole-TU compilation on the pinned SH-4
toolchain is a separate gate.

## Window lifecycle and complete QA transport

```bash
python3 -B port/dreamcast/tools/cloud/build35/window_host.py --output "$OUT/window-host"
python3 -B port/dreamcast/tools/cloud/build35/window_host.py --sanitize \
  --output "$OUT/window-sanitized"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py --output "$OUT/window-qa"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py --sanitize \
  --output "$OUT/window-qa-sanitized"
```

The actual DFA/FA29/window collectors are checked in six profiles with an
independent bounded-ring oracle and serialized worker writers. Each run has
366,954 assertions. It covers every reason, partial/full windows, N=1/3/32/64,
tick wrap, skipped/incomplete/outside work, pause/resume/room/restart and
saturation expiry. The IRQ shim checks synchronization but does not model KOS
interrupt latency.

The QA fixture uses actual snapshot/format/paging bodies and the existing
reviewed transport implementations. Five compositions cover maximum-value
gap-only, window-only and combined N=32/64 rows, actor attribution and
DSA/XLU/OCC rows. Each run verifies 45 complete transport reassemblies,
including delayed and refused writes. The largest generated snapshot is
27,774 bytes; a full 3,071-byte reserve for the non-audit formatter plus a
trailing sentinel gives a 27,927-byte conservative bound. Including its final
terminator leaves 4,840 bytes in the 32,768-byte buffer. Every DFA/FA29 row fits
192 bytes. Larger pre-existing actor/DSA rows use their own larger scratch.

## Target identity gate

Use a fresh `OUT` and absolute paths to the pinned compiler, KOS, SH4ZAM and
toolchain receipt. Set `BASE_COMMIT` to the integration base recorded in the
hand-back. The public fixture's `NMR_POOL_LOD=0` override is applied equally to
control and candidate because the private generated LOD asset is unavailable.

```bash
python3 -B port/dreamcast/tools/cloud/build35/build_controls.py \
  --baseline "$BASE_COMMIT" --output "$OUT/target" \
  --sh4-cxx "$SH4_CXX" --kos-root "$KOS_ROOT" \
  --sdk-root "$SH4ZAM_ROOT" --toolchain-receipt "$TOOLCHAIN_RECEIPT"
```

The matrix compares raw preprocessor output and target objects with both new
controls absent and explicitly zero. It also checks disabled Make definitions,
object selection and link flags. Enabled profiles cover current and scalar
algorithm alternatives, existing comparison/census modes, independent N=1,
combined N=32 and maximum N=64. Invalid values and missing dependencies must
fail at Make evaluation. Relocatable links resolve all new audit hooks; KOS
libraries, private assets and complete game images are outside this cloud gate.

See `docs/cloud/handbacks/build-35.md` for qualified receipts, actual cost
figures, complete-image commands and the matched-state console tour. The
diagnostics measure frequency and have observer cost; they authorize no
optimization promotion or speed claim by themselves.

## Qualified target result

The final matrix on `b7c321300a12de206c692793d4b3e41ffec03d27` passes all
136 raw disabled comparisons, all six enabled compile/link arms and all
16 Make rejection probes. The compact target receipt binds 192 consumed
source/build inputs and hashes of the complete scratch evidence.

The following deltas use the same inherited QA/DFA/FA29 profile with Build35
absent at the integration control. They sum the selected target objects,
including read-only/data sections in allocated bytes; they are not a linked
whole-game image size.

| Composition | Units included | Text delta | Allocated delta | BSS delta |
|---|---|---:|---:|---:|
| Gap counters, window 0 | Ten changed existing TUs | +1,172 B | +19,867 B | +17,312 B |
| Window 1, gap counters 0 | QA and three collectors | +1,956 B | +20,689 B | +18,468 B |
| Gap counters and window 32 | All eleven TUs | +3,092 B | +53,104 B | +48,364 B |
| Gap counters and window 64 | QA and three collectors only | +1,944 B | +81,140 B | +77,548 B |

The seven gameplay hook objects are identical between the gaps-only and
combined 32 arms. Their BSS growth is zero. The QA snapshot and its multipart
transport together add 16,384 bytes of BSS. The new window object contains
2,080 bytes of BSS for 166 reasons at N1, 31,048 bytes for 224 reasons at N32,
and 60,232 bytes for 224 reasons at N64. These diagnostics require private
room-memory qualification before their console tour; they allocate no heap
storage themselves.

The largest local frame increases among normal-recipe changed TUs are
`at_mod` 408→412 bytes and FA29 formatting 60→64 bytes. Per-function increases
are retained in the receipt, including motion acquire 60→68, EspgenMove 56→68,
EspDelete 44→56 and MakeWeightPalette 0→16 bytes. The window collector's largest
local frame is 64 bytes; its end-tick function uses 40 bytes. The QA menu's
maximum local frame remains 3,092 bytes. These numbers do not include callers'
frames or unpriced operating-system/interrupt overhead.
