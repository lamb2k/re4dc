# Build 14 — cache-miss phase diagnostic

**Implemented, default off; console event qualification is pending.**
`PERF_PHASE_MISS` observes one fixed PRFC1 event at the existing Build 10 census
boundaries. It provides guarded software accounting and real target control
loops. It does not establish a console cache bottleneck, a world-rendering
speedup or a 30 fps result.

The observer itself is expensive enough to matter: a sampled transition costs
396 scalar model cycles before hardware register wait states and cache effects.
The explicit 1,000-edge and 5,000-edge scenarios below imply roughly 2.075 ms and
10.367 ms of observer work per drawn frame at an assumed 200 MHz. Those are
**hypothetical event-boundary populations**, not measured r101 populations.
The scalar costs cannot be subtracted as a portable phase constant; observer
accesses alter the workload and its cache behavior.

Validation base: `9b248c5b40a49e4c954ea834fdf665fdbbc314f0`.
Publication base: `fc53531852ed979394ff3aefb6fddbefcfa825fb`. The only
intervening change is a `KNOWN_ISSUES.md` documentation link; measured
sources and test inputs are unchanged. The publication preserves that update;
`tools/cloud/build14/receipts/publication-base.json` records the comparison.
Runtime dependency: landed `WORLD_CENSUS24`, with its existing supported world
path and QA requirements. No unmerged data-layout or meshlet implementation
is required. [Reproduction and console procedure](../../tools/cloud/build14/README.md).

## Event and ownership contract

| Build setting | KOS event | Meaning |
|---|---|---|
| `PERF_PHASE_MISS_EVENT=15` | `PMCR_OPERAND_CACHE_MISS_MODE`, 0x0f | Operand-cache miss occurrences |
| `PERF_PHASE_MISS_EVENT=37` | `PMCR_PIPELINE_FREEZE_BY_DCACHE_MISS_MODE`, 0x25 | Pipeline-freeze cycles associated with D-cache misses |

The event is fixed for an entire build/run. Run 15 and 37 separately with their
own controls. The diagnostic never manufactures simultaneous miss/stall
measurements, cache-miss rates without an access denominator, or average
miss latency from unlike windows.

The implementation uses only KOS `perf_cntr_config`, `perf_cntr_start`,
`perf_cntr_stop` and `perf_cntr_count`, always with **PRFC1**. PRFC0 remains
reserved even where wall time comes from TMU2. The higher-level KOS performance
monitor API is not used because it can disable the performance timer.
`PMC_ROW=1` is rejected explicitly: it already owns PRFC1.

Initial acquisition requires a stopped counter with no event and CPU-clock
mode. A stopped but configured foreign counter is not assumed free. The short
configuration/start/check sequence is protected with existing KOS IRQ helpers.
Pausing stops our counter while retaining its event signature. A restart
requires that exact stopped signature. Every sampled boundary checks the
running configuration before reading. Observable mode/clock/running-state
loss is sticky: the diagnostic ceases all further PRFC1 accesses in that
process, including stop/reconfigure attempts. It never disables a new owner.

KOS exposes configuration, not an ownership-token registry. An external owner
that changes and restores the same signature entirely between observations
cannot be detected. The Make conflict check and project ownership audit remain
part of the contract. The pinned `perf_cntr_config` treats either RUN bit as
running; the diagnostic follows that public API interpretation rather than
adding another raw register driver.

## Coherent reads and exclusive accounting

The pinned KOS driver reads high-low-high and retries a changing high word,
so a low-word rollover does not become a torn 64-bit read. No new SH4 assembly or
production linker rule is introduced. Counts are 48-bit. Modular deltas accept
a bounded wrap, while upper-bit contamination, backward monotonic time,
intervals over 60 seconds and implausibly large reset-like differences are
rejected. The generous plausibility ceiling is 1,024 counts per microsecond
with 1 ms of allowance; it is a corruption guard, not an event-frequency or
latency measurement. Accumulation/sample/wrap counters reject overflow.

The observer attaches to the census's validated transitions, tick completion,
window seal and pause/reset behavior. The existing nesting tokens remain the
authority. Effective same-bin nesting does not read PRFC1 again. There are no
new per-vertex callbacks or logs. The existing meshlet/strip/clip phase scopes
and inherited census overhead remain in the diagnostic workload.

Six paths times six phases, three explicit wait bins and a residual give 40
exclusive intervals. Every accepted delta is charged exactly once; their sum
equals the buffered total. The same census window supplies sequence, room,
full option/generation identity, logical ticks and actual drawn frames. A
census error invalidates the PMU window too. Fractional per-draw/tick means are
integer-rounded for display; the snapshot retains full 64-bit bin totals.

The counter is CPU-wide. Interrupts, other scheduled work, and observer memory
traffic can contribute during a world or wait interval. Exclusive intervals
are **not exclusive attribution to world instructions**. Qualification only
establishes event response; it does not remove those contaminants.

The first checked start/read establishes the interval origin; acquisition and
control work preceding that origin is excluded from PMU counts. Counts remain
continuous between complete ticks/windows. Buffered logging after a seal is
charged to the next residual interval. Pause, incomplete ticks and identity
changes discard a partial collection. Pause retains the previous sealed
snapshot; an explicit new control run discards the old PMU snapshot so it
cannot be presented with new qualification evidence.

## Controls that run on the target

While the game is paused on the census QA page, X allocates two aligned node
rings: 2 KB and 32 KB. It initializes one next-index word per 32-byte line. The
next node is 17 lines onward modulo the power-of-two ring size, making a full
permutation. Volatile dependent loads keep the next address dependent on the
previous result and prevent load elimination. No prefetch, cache flushing,
cache allocation-mode change, custom assembly or unrolling request is used.

Each measurement runs the same 4,096-load warmup and 8,192-load measured loop.
Eight pairs alternate resident/heavy order. Only the working-set footprint
differs. The peak requested buffer allocation is 34,816 bytes, plus allocator
metadata; buffers are freed before resuming gameplay. Allocation failure is
explicitly inconclusive. Interrupts remain enabled during the load population;
only short ownership/read operations use IRQ protection.

All eight pairs and no errors are required. The heavy minimum must exceed
four times the resident maximum plus 64 counts, and must reach 4,096 counts for
event 15 or 8,192 cycles for event 37. These conservative response criteria avoid
qualifying a zero/weak/noisy event. They do not certify an exact miss count,
miss penalty or counter accuracy under all workloads.

The QA page shows the status, min/upper-median/max for each population, the
threshold and all eight raw pairs on separate rows. Its existing wrapping and
pagination handles 320/640 widths. A truncated serial summary emits an explicit
`summary_overflow=1 full=QA` sentinel.

| State | Meaning |
|---|---|
| `UNRUN` | Target controls have not run; no PMU collection is started |
| `QUALIFIED` | This target run passed the stated response controls |
| `INCONCLUSIVE` | Insufficient response, incomplete controls or allocation failure |
| `SIMULATED` | A host fixture injected a passing response; never hardware qualification |
| `COUNTER_BUSY` | Initial counter signature was not free; no configuration was changed |
| `COUNTER_LOST` | Observable ownership loss; all future accesses cease |

`valid=1` additionally requires a complete sampled window with no accounting
or census errors. It does not certify frame pacing or uncontaminated world
attribution. A physical-console capture is required for a hardware result;
the implementation cannot authenticate which execution environment ran it.

## Public validation

Final evidence is in
[tools/cloud/build14/receipts](../../tools/cloud/build14/receipts).

| Gate | Result |
|---|---|
| Complete OFF `.ii` and object-byte identity |20 comparisons pass against an independent baseline archive |
| Enabled target configurations | Event 15, event 37, and standalone census/PVR observer composition pass |
| Make rejection controls |14 invalid knob/event/ownership/dependency selections refused |
| Linked observer hooks | All new PM14 hooks resolve in real TU partial links |
| PVR observer ownership | Exactly one `pvr_sync_stats` wrapper in each tested composition |
| Floating-point register risk | Both compiled observer cores contain 0 FPU instructions; external callees excluded |
| Host accounting/ownership controls |36 cases pass under ASan/UBSan, 18 per event |
| Pinned KOS read algorithm | Stable read and low-word rollover retry controls pass on the extracted actual function |
| Actual target instruction/access cases | Seven pass, including both dependent-load controls |
| QA page layout | Actual extracted framebuffer/page code, six-digit synthetic control values, 320/640 widths and 16/32-bit framebuffers |

The host cases cover exclusive nesting, same-bin no-read, drawn/tick
denominators, phase/tick continuity including log overhead, pause/control
restart, room/generation reset, stale scopes, foreign threads, busy/stolen
counter configurations, 48-bit wrap, reset/high-bit/clock faults, accumulation
overflow, no contrast, allocation failure, census faults and unrun state.
Synthetic responses are labelled `SIMULATED`, including in the QA capture.
No host result is presented as a physical PMU-event validation.

The target gates use real Make commands and generated project headers with
the public asset fallbacks. Toolchain: GCC 15.2.0 with KOS threads,
binutils 2.45.1, newlib 4.6.0, pinned KOS/SH4ZAM. The restored compiler's actual
hash and public-image provenance are recorded. It has matching component
versions but is not claimed to be the lost Build 10 compiler binary.

## Code, resident data and stack

Raw object sections, relative to the same recipe with the census on and PM14
off; these are not final linked-game heap/image deltas:

| Component | Executable bytes | Allocated bytes | Zero-fill bytes |
|---|---:|---:|---:|
| Census core, PM14 off |5,596|9,252|2,469|
| Census core, PM14 on |5,760|9,416|2,469|
| New PM14 core, event 15 |5,062|7,496|957|
| New PM14 core, event 37 |5,062|7,504|957|
| QA menu delta |−44|−76|0|
| Total delta, event 15 |**+5,182**|**+7,584**|**+957**|

The QA negative delta is a compiler/layout consequence of replacing the
footer branch, not a performance claim. `pace.o` receives no PM14 define.
The full PM14 TU's largest individual stack allocation is 360 bytes in
`run_controls`; the census core maximum remains 340 bytes and the QA maximum
remains 2,160 bytes. Individual `.su` sizes are not a whole call-chain stack
bound. The dynamic isolated target trace observes 104 bytes for a sampled edge
and 100 bytes for tick completion, including fixture argument marshalling.

## Actual target traffic and bounded cycle model

The cost fixture compiles the **production PM14 implementation, existing KOS
inline IRQ operations and pinned `perfctr.c` unchanged**. It supplies synthetic
state and PRFC1 register values, then interprets their actual SH4 opcodes.
No new interpreter opcode implementation was required. Only counter 1 register
addresses occur in the sampled traces: a 16-bit configuration read and three
32-bit high-low-high reads. The model does not generate hardware events.

| Case | Instructions | Warm-I cycles | Cold-I cycles | RAM load/store bytes | Distinct demanded RAM lines | Register read bytes |
|---|---:|---:|---:|---:|---:|---:|
| Sampled phase edge |368|396|776|360 /172|22|14|
| Same effective bin |80|93|194|82 /24|7|0|
| Unrun/inactive |42|60|141|58 /20|7|0|
| Complete tick |325|357|700|323 /164|22|14|
| Bounded 48-bit wrap |371|399|764|368 /172|22|14|
|2 KB control loop |40,975|32,788|32,832|32,782 /4|67|0|
|32 KB control loop |40,975|32,788|32,832|32,782 /4|1,027|0|

Each control loop performs exactly 8,192 dependent node reads /32,768 node-load
bytes. Their node demand sets are 64 versus 1,024 32-byte lines; the additional
three lines in the full trace are wrapper/stack/literal accesses. The equal
perfect-D model cycle count is expected: this model does not price the cache
misses that the physical controls are intended to expose.

Distinct lines and architectural load/store bytes are not cache fills,
writebacks or external-bus transactions. The cold-I column re-colds the
isolated fixture, not a game instruction footprint. PMU/MMIO wait states,
D-cache misses, bus contention, interrupts and external work are unpriced.
The fixture also includes argument marshalling, so these costs are bounded
synthetic call costs, not a calibrated subtraction for every real boundary.

For explicit hypothetical populations:

```text
modelled overhead ms =
  (sampled_edges * Cedge + same_bin_calls * Csame + completed_ticks * Ctick)
  / (CPU_MHz * 1000)
  + unpriced costs
```

| Assumptions per drawn frame at 200 MHz | Modelled observer ms | Unpriced register reads |
|---|---:|---:|
|1,000 sampled edges +200 same-bin calls +1 completed tick |2.074785|4,004|
|5,000 sampled edges +1,000 same-bin calls +1 completed tick |10.366785|20,004|

These scenarios exclude seal/formatting, initial acquisition, controls,
inherited census instrumentation and unpriced hardware effects. They are not
inserted into the measured 49.3 ms console frame and do not assert the actual
number of r101 boundaries. Use measured PM14 sample counts and the separately
observed tick/draw ratio to understand the collection's scale; retain the
limitations when interpreting its cache-event distribution.

## Remaining console evidence

Build and run the event 15 and event 37 controls on the physical console before
accepting either event's phase report. Record controls, event and full identity,
window/tick/drawn counts, errors and all relevant QA pages at the same r101
view. Compare ordinary observer-off timing with the diagnostic to establish
its perturbation. A qualified response can help decide where cache work is
concentrated; it does not independently prove that data-cache misses determine
the complete frame, nor that a data-layout candidate reaches the 2 ms world goal.

No complete game link, private asset test, emulator run or physical-console
measurement was performed for this handoff. All new artifacts are code,
synthetic fixtures, reports and compact public receipts.

## Primary implementation sources

- [Pinned KOS `perfctr.h`](https://github.com/KallistiOS/KallistiOS/blob/804b3195ebd1a06a27cc2b3a5eacf7a2429040a3/kernel/arch/dreamcast/include/dc/perfctr.h): event definitions/units, 48-bit counters, PRFC0 timer and PRFC1 ownership notes.
- [Pinned KOS `perfctr.c`](https://github.com/KallistiOS/KallistiOS/blob/804b3195ebd1a06a27cc2b3a5eacf7a2429040a3/kernel/arch/dreamcast/kernel/perfctr.c): configuration semantics, clear/start/stop, high-low-high retry and register addresses.
- [Pinned KOS cache definitions](https://github.com/KallistiOS/KallistiOS/blob/804b3195ebd1a06a27cc2b3a5eacf7a2429040a3/kernel/arch/dreamcast/include/arch/cache.h): 16 KB direct-mapped operand cache and 32-byte lines. These guide control footprints, not a claim about measured misses.
- [KOS performance-counter documentation](https://kos-docs.dreamcast.wiki/group__perf__counters.html) and [timer limitations](https://kos-docs.dreamcast.wiki/group__perf__counters__timer.html): supported public API and active-CPU-time versus wall-time distinction. The source pin above, rather than moving online documentation, is authoritative for this build.
