# Build 10 — world phase census

Candidate: `WORLD_CENSUS24=1`, default **0**, based on `011d8dee`.
This implements Gate 0 of the [world 2 ms programme](WORLD_2MS_PLAN_20261024.md).
It is a diagnostic, with instrumentation overhead included in its timings.
No world geometry, material, selection policy, simulation, collision or
production recipe is changed.

## What is measured

The source main loop renders the previous tick's prepared image before
advancing the gameplay frame counter. Therefore the census owns a complete
**begin-of-loop to next-begin-of-loop interval**. The end marker confirms
that the tick completed; it does not truncate tail time. Restarted,
paused and incomplete ticks do not enter a new collection.

Each completed logic tick contributes once. A tick is drawn when the
native streaming path finishes at least one game scene; multiple scenes
increment a separate scene counter. Drawing intent is captured immediately
after the pace decision. This keeps skipped ticks, successful scenes,
present/discard requests and observed PVR page flips distinct.

Windows contain 300 drawn ticks by default (`WORLD_CENSUS24_WINDOW`, valid
range 300–600). There may be more logic ticks than drawn ticks. All work,
including world selection on skipped ticks, contributes to the window.
For a window total `X`, the per-tick mean is `X / ticks`; the amortized
per-drawn mean is `X / drawn`. This is the exact relationship to the old
[`WORLD_METER` per-tick denominator](../../tools/d367/pvs23/README.md).
The census reuses the existing selection/transform and output-accounting
sites, but does not consume the old meter's destructive `take` operation.

Every world interval belongs to one of six paths: near opaque, near
cutout, near translucent, far opaque, far cutout, far translucent. The
current shell draws opaque geometry; unused shell pass rows stay zero.
Common world source/texture preparation and camera/launch setup are
attributed to near opaque `Other`; shared deferred-pass query/flush
bookkeeping is near cutout `Other`. Nested pass and shell scopes replace
that attribution while they run. The shared
`re4dc_prepare_model_assets` registration path mixes actors and world; it
remains in the residual. It cannot be claimed as a saving in this world's
phase total without separately attributing its world work.

| Phase | Boundary and interpretation |
|---|---|
| Selection | World traversal and admitted meshlet/strip-group selection, excluding nested emission |
| Transform | Input gather/prime, transformed-cache fill and bulk position transformations |
| Clip | Clipping/rejection calculations and their repeated position transformations, excluding nested output submission |
| Header/material | Material/header preparation and actual direct header emission |
| Submit | Strip walk/classification, packet/SQ copies and successful output commit/accounting |
| Other | World-scoped work outside the five named subphases; retained rather than hidden in the residual |

Scopes partition time exclusively. A nested phase replaces its parent
until it returns; a nested explicit wait replaces world time. Main-thread
ownership prevents background-presenter calls from changing the active
world partition. These are elapsed intervals: interrupt/preemption time
inside a phase remains charged there. Scope epochs prevent stale scopes
from restoring state in a later tick. The hot census hooks use integer
state; target validation also checks their compiled implementation.

| Count | Meaning |
|---|---|
| Transformed inputs | Executed position transformations on geometry inputs, including repeated pretests/clipping work; excludes bounds and copied dedup tails |
| Emitted strip corners | Successful output-accounting corners, including generated clip output; excludes attempted/rejected inputs |
| Headers | Actually committed world polygon headers |
| Material changes | First header in a path/tick plus changes in its first four hardware control words; compared in submission order within that path |
| Indexed/plain picks | Retained selection records, or accepted fallback meshlets; shell groups are not R4IM meshlet picks |
| `nr == 0` picks | Retained empty strip-group selections, with the existing fallback equivalent |
| Strip inputs | Source corners walked, including clipped/rejected strips; a separate attempted-work metric |

Explicit PVR waits, vblank spins and pacing waits have separate exclusive
totals. The residual is signed:

```text
wall time = all world phases + explicit waits + residual
```

Residual includes the rest of gameplay/rendering, loop and diagnostic
overhead. Waiting inside uninstrumented library internals stays in the
enclosing world phase when one is active, or in the residual otherwise.
Public KOS wait calls are wrapped; calls resolved within the same KOS
translation unit need not pass through a linker wrapper. This is not a
claim to have separated every internal SDK wait. Displayed means are truncated integers;
the raw snapshot reconciles exactly.

## Presentation, lifetime and unsupported paths

The existing `pvr_sync_stats` observer is extended when available; otherwise
the census supplies the sole observer wrapper. Event 8 records actual page
flips, event 1 fields, and events 6/7 render start/completion. IRQ-side
collection does no formatting, allocation or logging. Thread-side access
masks interrupts for the short snapshot/reset. GPU events are an overlapping
presentation timeline, not extra exclusive CPU time. A flip interval belongs
to the window in which it ends.

The identity key includes room, view, PVS/world options, QA world overrides
and renderer residency epoch; the complete key is shown on the QA page.
Relevant transitions discard partial windows.
Opening QA preserves the last complete snapshot and stops collection;
resume starts a fresh collection, and events before its next begin are
ignored. A failed native pass, aborted submission, unsupported fallback or
attempted-but-refused shell marks the window with an error. Deliberately
disabled shell rendering is a recorded option, not a false error. Check
`errors == 0` before accepting a window.

`WORLD_CENSUS24` requires the actual streaming world path and QA menu.
Duplicate-work comparison modes are rejected. The Make include adds no
flags, objects or linker options when the knob is absent or zero. No new
runtime SH-4 assembly, data format or linker script is introduced.

## Output and use

One bounded serial line is emitted at each complete window. Full totals
remain in `Snapshot`; the QA **WORLD CENSUS** page displays both overall
denominators and the near/far × pass matrix, counts, waits, residual and
presentation cadence. The page wraps and paginates at both 640×480 and
320×240. Reporting cost is charged to the next measured interval. See the
[reproduction instructions](../../tools/cloud/build10/README.md).

## Evidence

The [validation receipt](../../tools/cloud/build10/validation-receipt.json)
records final source hashes, compiler pins, object hashes and control
results. All geometry and lifecycle
inputs are synthetic. The private r101 assets, emulator gameplay harness
and physical Dreamcast are not available in this environment.

The deterministic core control reconciles 600 logic ticks / 300 drawn
ticks: 89,400 µs wall, 15,600 µs world, 13,800 µs explicit waits and
60,000 µs residual. It also checks a second window, a deliberately skipped
first tick, nested waits, non-owner calls, stale scopes, pause/resume GPU
arming, identity changes, overflow and presentation gaps. Those numbers
are an oracle test, not game performance.

The pinned target gate passes **64 byte-for-byte OFF comparisons**: all
eight affected existing translation units, with the knob absent and
explicitly zero, across the production and standalone-observer profiles,
for both full preprocessed source and object bytes. Make flags, generated
headers, object membership and linker flags match the independently
archived `011d8dee` baseline. Enabled compilation and both relocatable
integration links pass, with exactly one stats/ready/render-done wrapper.
Fourteen invalid configurations are rejected. Both complete compiled
census cores contain zero FPU instructions; external callees are outside
that assembly scan. This is object/partial-link evidence, not a complete
game link or a patched-KOS runtime result.

The geometry matrix passed 624 paired cases across all eight combinations
of batching, replay and prefetch. A final-source production pair passed
78 cases after the entry-boundary and OFF-formatting corrections. Ordered
TA/accounting words and SQ ownership traces are identical with the census
zero/on; committed census corners and headers match an independent packet
parser. Both final output streams have SHA256
`3c9f730f64be429c80eb2923bdec07463cf267eee546c7966490d957061d50ce`.
The earlier 78-case sanitizer pair and final core controls pass address
and undefined-behavior checks; leak detection was disabled because the
managed environment cannot inspect `/proc` task state under ptrace.

These emitter controls do not execute world selection, far-shell loading,
or the owned source entry adapters. Those changes have source review and
full-TU compilation coverage; local execution remains necessary. The
actual QA renderer passes bounds/layout controls for both RGB565 and
32-bit framebuffers: 25 rows on one 640×480 page, or 38 wrapped rows on
four 320×240 pages. Synthetic captures were inspected and are not tracked.

### Diagnostic cycles and traffic — MODELLED

The [cost receipt](../../tools/d367/world_census24/target-cost-receipt.json)
uses a separate, unmodified production census object compiled with GCC
15.2.0, KOS threads, binutils 2.45.1, newlib 4.6.0, KOS `804b3195` and
SH4ZAM `33fa4850`. The Make-derived census profile's final optimization
flag is `-O1`. Synthetic callers execute through the established SH-4
interpreter and instruction/pipeline/traffic model.

| Operation | Warm-I cycles | Cold-I cycles | Loads | Stores | Distinct 32-byte data lines |
|---|---:|---:|---:|---:|---:|
| Outer world scope enter + leave | 357 | 626 | 68 | 16 | 16 |
| Nested phase scope enter + leave | 374 | 642 | 71 | 18 | 16 |
| Wait scope enter + leave | 361 | 629 | 71 | 18 | 17 |
| Phase switch | 177 | 385 | 33 | 9 | 13 |
| Active count | 88 | 197 | 21 | 5 | 9 |
| First or changed header | 277 | 433 | 68 | 17 | 14 |
| Unchanged header | 194 | 340 | 48 | 13 | 14 |
| Normal non-sealing tick boundary | 1,800 | 2,289 | 434 | 392 | 64 |
| Compiled 64-piece world-hook sequence | 102,156 | 102,603 | 20,964 | 5,084 | 27 |

The last row assumes three nested phase scopes, four standalone counts
and one header per synthetic piece, inside one outer scope. It performs
78,844 architectural load bytes and 20,336 store bytes. Its line count is
the union of actual data addresses, including stack and literal loads;
it is **not** a miss count, bus-transaction count, or renderer footprint.
The small union repeats many times. Warm I assumes perfect instruction
cache; cold I starts the model's 8 KiB cache once for the complete sequence.
Do not sum independently cold hook rows.

At an assumed 200 MHz, the compiled 64-piece hook sequence is **MODELLED
0.51078 ms warm / 0.513015 ms cold I**, excluding the separate tick boundary
and unpriced external edges. An explicit whole-frame arithmetic budget
using isolated caller prices is:

```text
per piece = 3 × 374 + 4 × 88 + 194 = 1,668 cycles
frame overhead = 1,800 + 357 + P × 1,668 + (P > 0 ? 83 : 0)
P = 64: 108,992 cycles = MODELLED 0.54496 ms at 200 MHz
```

`P = 64` and those hook frequencies are assumptions, not r101 counts.
The arithmetic budget differs from the compiled loop because its isolated
callers include different argument/call scaffolding and scheduling. The
receipt retains both; neither is a console prediction or a portable
constant to subtract from measured world time.

The actual pinned KOS microsecond conversion and `thd_current` reads are
included. Test-only raw clock, identity, log and formatting bodies are
explicitly excluded, as are real timer/MMIO latency, interrupts, scheduling,
D-cache misses, SDRAM/PVR contention and renderer work. Normal-tick pricing
does not cover the once-per-window formatting/seal path. Target snapshots
from all 15 cost cases seal 300 ticks/draws with expected counts, zero
errors and exact exclusive reconciliation. Two required interpreter
instructions have 368 boundary/alias/flag/traffic controls; the inherited
XOR and memory-accounting controls also pass. No new runtime assembly is
introduced; the synthetic link layout follows the existing target fixtures.

The census object has 5,596 executable bytes, 9,252 total allocated section
bytes and 2,469 BSS bytes in this profile. GCC reports local stacks of
4 bytes for enter, 8 for leave, 12 for count/header and 340 for begin-tick.
The interpreted call-chain peaks are 20 bytes for a scope pair, 28 for
a header and 348 for a normal tick, including the synthetic clock edge.
Those are object/fixture measurements, not a complete linked game's RAM or
interrupt-stack high-water mark. The release-memory gate remains local.
Across all changed production objects, including the core, raw section
growth is 9,120 executable bytes, 13,157 allocated bytes and 2,537 BSS bytes,
before final-link section garbage collection.

## Local hand-back

1. Use the accepted QA recipe, unchanged assets and camera route, with the
   census as the only added diagnostic; record all resolved flags and hashes.
2. Collect complete zero-error cross and farm windows. Retain `ticks`,
   `drawn`, all raw phase/count totals and actual-flip cadence. Confirm that
   the residual reconciles before comparing the 2 ms requirement.
3. Measure the diagnostic's console perturbation with a matched off/on
   pair. Neither host execution nor the scalar model prices D-cache misses,
   bus contention, the real timer call, formatting or PVR latency reliably.
4. Run local appearance, STRICT gameplay, transition/retirement and memory
   gates. This diagnostic does not claim a console speedup or 2 ms result.

The coordinator retains ownership of integration and release defaults.
