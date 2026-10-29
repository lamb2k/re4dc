# Build 35: exact drawn-tick window and bounded observer cost

`FALLBACK_WINDOW35=N` is an optional diagnostic for N=1 through 64. It is
independent of `FALLBACK_AUDIT35=1`, which adds 58 event reasons to the existing
FA29 collector. Both default to zero. The recommended first owner capture is
N=32, with the two existing audit collectors enabled and a matched control
capture. These counters do not establish a performance improvement.

## What one sample means

A window row is one completed logic tick whose pacing decision attempted a
draw. It is not a confirmed GPU presentation. The FA29 begin hook captures the
tick identity before `Frame_cnt` changes during the iteration. The end hook
uses the current DFA and FA29 count arrays, after DFA has sealed and before
another tick begins. It never inserts the retained previous drawn snapshot.

Completed skipped ticks increase `logic` and `skipped`, but their reason
values do not enter the window. `used` counts the retained drawn rows and is
the denominator for per-drawn-tick frequencies. A partially filled window
reports `full=0`; missing rows are not treated as zero observations.
`span_logic` counts completed logic ticks from the oldest retained drawn row
through the latest completed tick. `span_skip` counts the skipped ticks in
that interval, including skips after the latest draw.

An interrupted begin or a pause during an active tick increments `incomplete`
and drops that unfinished row. Pause freezes the existing window. Resume
clears the history and reports collecting until a new completed draw arrives.
Room changes and explicit restart/reset also invalidate old samples. Physical
ring slots are not cleared at reset: indices make old slots unreachable, and
each newly admitted row overwrites its complete count vector. Reset therefore
clears only the running sums and fixed metadata, independently of N.

FA29 events outside an active tick continue to update the existing room
counters. They do not enter a drawn row. The window's `outside_room` value
comes from the same immutable sealed FA29 snapshot as the completed tick,
not a worker-writable live value read after interrupt restoration. `FA29T`
remains a cumulative room total that includes skipped logic and asynchronous
work. It must not be divided by drawn ticks to claim per-draw frequency.

## Overflow and availability

Every row stores unsigned 32-bit reason counts. A uint64 running sum covers
all allowed N without overflow: the largest exact value is
`64 * UINT32_MAX = 274877906880`. Expiry subtracts the old row before adding
the new row.

A current DFA or FA29 counter saturation marks that particular drawn row
inexact. `satrows` counts the affected retained rows. The window becomes exact
again when they expire. The older FA29 room-total overflow flag remains sticky
by its original contract; it is deliberately not reused as window validity.
Room totals can saturate while the newly drawn row remains exact.

Completed logic/draw/skip/incomplete denominators use saturating uint64
arithmetic. Their saturation sets `count_overflow=1`, which prevents an exact
claim until reset. Unavailable data is shown as collecting/NA, not a valid
empty sample. A partial nonempty ring can be exact while `full=0`.

## Threading and locked work

The existing FA29 IRQ save/restore serializes game, disc and sound writers.
A drawn seal makes the current FA29 array immutable by setting `active=false`;
subsequent worker events reach room totals and the outside-tick count. The
ring update runs after `irq_restore`, on the game thread. It performs no
allocation, timer read, I/O or formatting.

The larger reason registry still increases existing locked memory work.
These structural byte counts concern the count arrays and structs; actual
instructions also read/write fixed metadata and stack:

| Existing operation | 33 FA29 reasons | 91 FA29 reasons |
|---|---:|---:|
| Clear current vector at begin | 132 B | 364 B |
| Drawn seal: current and totals copies combined | 264 B | 728 B |
| Copy sealed `Snapshot` to a caller | 300 B | 764 B |
| Clear complete `State` on room change or reset | 600 B | 1,528 B |

A room-change begin additionally performs the normal current-vector clear.
The post-IRQ ring arithmetic is separate from all these locked copies. The
bounded SH-4 cost fixture executes the real KOS status-register instructions
and reports the protected segment separately. It does not simulate interrupt
delivery, scheduling or physical interrupt latency.

## Static storage and QA capacity

The ring is compile-time static storage. It never borrows room/movie memory,
allocates, evicts resources or silently shortens N. Target layout receipts
agree with the host layout for these integer-only structures:

| Gap reasons | N | Total reasons | Row bytes | Ring bytes |
|---|---:|---:|---:|---:|
| Off | 1 | 166 | 680 | 2,080 |
| Off | 64 | 166 | 680 | 44,920 |
| On | 1 | 224 | 912 | 2,776 |
| On | 32 | 224 | 912 | 31,048 |
| On | 64 | 224 | 912 | 60,232 |

The exact struct formulas are `680*N + 1400` bytes without gap reasons and
`912*N + 1864` bytes with them. Separate object/link alignment may add padding.
The FA29 state increase is 928 bytes; an enabled window adds a separate
four-byte current-tick overflow marker. No window object is selected when
N=0. Both new controls off preserve the old objects byte for byte, as checked
by the target gate.

The maximum-width diagnostic fixture found that the old 24,576-byte snapshot
could truncate these added rows. One independent `FA35 || WINDOW35` guard
selects a 32,768-byte `g_diag` buffer. Existing off branches remain unchanged.
The effective selected buffer grows by 8,192 bytes. With QA_LINK, the selected
immutable reviewed `Snapshot<sizeof(g_diag)+384>` transport copy also grows by
8,192 bytes, for an effective QA-plus-transport increase of 16,384 bytes.
The legacy `Telemetry<sizeof(g_diag)+160>` copy is an alternative branch, not
a third simultaneous copy; supported new link configurations require the
reviewed transport. Object BSS and full-image linker allocation are separate
measurements. The target object gate reports its actual BSS; a complete game
link and room headroom capture remain owner gates. The ring is additional to
these QA buffers.

Five complete capacity profiles exercise gap-only, window-only, combined,
standalone and all diagnostic-composition cases. The largest actual generated
snapshot is 27,774 bytes. Reserving the full existing 3,071-byte non-audit
format block and appending a sentinel gives a conservative text bound of
27,927 bytes. Including its final NUL leaves 4,840 bytes unused in 32,768.
Each DFA/FA29 row fits the real 192-byte scratch. The fixture's larger
196-byte maximum row belongs to pre-existing actor/DSA formatting, which has
its own larger scratch.

The fixtures check every reason, max numeric widths, terminal NUL, trailing
sentinel, paging and byte-for-byte multipart reassembly. Five profiles each
exercise nine normal/delayed/refused transport scenarios, for 45 complete
reassemblies. These are software capacity checks, not network timing or
console screenshots.

## Reproduction and receipts

Run from the repository root with a fresh output directory for each command:

```bash
python3 -B port/dreamcast/tools/cloud/build35/window_host.py \
  --output "$OUT/window-host"
python3 -B port/dreamcast/tools/cloud/build35/window_host.py --sanitize \
  --output "$OUT/window-sanitized"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py \
  --output "$OUT/window-qa"
python3 -B port/dreamcast/tools/cloud/build35/window_qa.py --sanitize \
  --output "$OUT/window-qa-sanitized"
python3 -B port/dreamcast/tools/cloud/build35/window_cost.py \
  --output "$OUT/window-cost" --sh4-cxx "$SH4_CXX" \
  --kos-root "$KOS_ROOT" --sdk-root "$SH4ZAM_ROOT"
```

`SH4_CXX`, `KOS_ROOT` and `SH4ZAM_ROOT` must name the same pinned toolchain and
SDK used by the target identity gate. The cost fixture obtains real object
flags through Make. It compiles production TUs and address-metadata fixtures
separately and requires every production executable section to match before
executing any cost case. This guards against fixture-only inlining or altered
register allocation.

The actual collector/ring host fixture passes 366,954 checks in six profiles,
including an independent deque oracle, every reason, N=1/3/32/64, tick wrap,
skipped/current versus retained snapshots, worker events, interruptions,
reset/resume and saturation expiry. The same cases pass ASan/UBSan; leak
inspection is disabled because sandbox `/proc` traversal is unavailable.
The QA capacity/transport fixture also passes normal and sanitizer runs.

Source-bound receipts are `receipts/window-host.json`,
`receipts/window-sanitized.json`, `receipts/window-qa.json` and
`receipts/window-qa-sanitized.json`. Each contains hashes of the consumed
production implementation, registries and fixture/extraction code.

## Compiled SH-4 cost

The cost gate passes 118 bounded scenarios across the existing 33-reason
collector, 91-reason gap collector, independent N=1 window, and combined
N=32/N=64 windows. It uses actual KOS `stc`/`ldc` status-register instructions,
linked toolchain copy/clear routines and the existing qualified scalar
interpreter. No operation required a new interpreter qualification. Every
production executable section matched its metadata fixture byte for byte.
The source-bound result is `receipts/window-cost.json`.

All cycles below are **MODELLED**, with perfect data cache. Cold-I means one
initially cold 8 KiB instruction cache in the synthetic ELF layout. Loads and
stores are retired memory instructions; lines are distinct 32-byte operand
addresses including literals and stack. Neither is a measured cache miss.
The entry-to-return scope omits the caller's argument setup and call
instruction. The optional weak actor-reset callback is absent from the
fixture, and formatting/transport are outside its measured paths.

| Callee case | Existing 33 warm / cold-I cycles | Gaps 91 warm / cold-I cycles | Combined N32 warm / cold-I cycles |
|---|---:|---:|---:|
| Active `fa29::hit` | 88 / 153 | 90 / 154 | 106 / 184 |
| Outside-tick hit | 88 / 151 | 90 / 153 | 96 / 174 |
| Paused hit | 39 / 70 | 39 / 70 | 37 / 93 |
| Same-room begin | 149 / 236 | 236 / 328 | 295 / 473 |
| New-room begin | 438 / 536 | 873 / 959 | 1,841 / 2,016 |
| First drawn seal | 258 / 369 | 489 / 595 | 4,037 / 4,331 |
| Full-window drawn seal | — | — | 5,398 / 5,706 |
| Sealed snapshot copy | 194 / 258 | 426 / 478 | 426 / 503 |
| Collector and window reset | 305 / 360 | 653 / 707 | 1,589 / 1,688 |

The full N32 seal comprises the ordinary FA29 seal and post-IRQ window update.
Its protected region has 667 instructions, 830 loaded bytes and 778 stored
bytes; the isolated protected-segment model gives 468 warm cycles. The
corresponding old33 seal has 290 protected instructions, 366 loaded bytes and
314 stored bytes, modelled at 236 cycles. Segment scheduling starts at the
segment boundary, so these figures are not physical interrupt latency.
New-room combined begin's protected segment stores 1,916 bytes, including
metadata/stack effects, and models 844 warm cycles. The ring update never
executes with the IRQ mask set in any observed trace.

Direct window callees isolate the work added outside the protected collector:

| N32 window operation | Warm / cold-I cycles | Loads / stores | Loaded / stored bytes | Distinct lines | Observed stack |
|---|---:|---:|---:|---:|---:|
| Insert first draw | 3,516 / 3,689 | 719 / 696 | 2,858 / 2,781 | 123 | 40 B |
| Replace oldest draw | 4,877 / 5,064 | 1,396 / 1,144 | 5,564 / 4,573 | 123 | 40 B |
| Complete a skipped tick | 56 / 137 | 17 / 12 | 62 / 45 | 7 | 40 B |
| Reset sums and metadata | 928 / 973 | 4 / 469 | 14 / 1,864 | 61 | 0 B |

N64 has the same instruction/traffic results for these bounded cases because
one admission replaces one vector and reset ignores inaccessible old slots;
its memory footprint is larger. Different addresses/cache states in a game
can still change physical behavior. The active combined hit has 27 loads,
six stores, 92 loaded bytes, 24 stored bytes, six distinct lines and 16 bytes
of local stack. It is the shared cost floor for added event hooks. Slot/probe
accumulation and local hook branches are separate work, and a batched hit
amount does not imply a call per counted slot.

Compiler stack records give 40 bytes for the window end callee, 20 for the
FA29 end callee, and a 60-byte observed nested seal high-water mark. The
largest individual formatter frame is 64 bytes. The N32/N64 window object
contains 1,992 executable bytes, including unmeasured formatters; the combined
FA29 object contains 1,544 executable bytes versus 1,320 for old33. These
object values are not a whole-image size prediction.

For one explicit sensitivity example, assume 1,000 active hit calls, one
same-room begin and one full-window drawn seal per frame at 200 MHz, with
30 ms of other work. The combined collector/window pieces model 0.558465 ms,
giving a 30.558465 ms hypothetical whole frame. At the same 1,000-call count,
the old33 observer models 0.442035 ms: the equal-frequency delta is
0.116430 ms. This does not estimate how many additional Build35 hooks fire
in a real frame. The receipt includes a 10,000-call sensitivity as well;
its combined observer work is 5.328465 ms. Cold-I cases cannot be added to
construct a frame. Interrupt scheduling, physical cache misses, actual
workload frequencies, full-image RAM and matched console observer cost
remain unmeasured owner gates.
