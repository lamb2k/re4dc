# Build 14 — `PERF_PHASE_MISS`

Default-off diagnostic for a **single fixed PRFC1 event** at the landed
`WORLD_CENSUS24` phase boundaries. It does not change world data, visibility,
gameplay or rendering decisions. Counter qualification on a physical console
is still required. The implementation and limitations are in the
[Build 14 report](../../../docs/cloud/BUILD14_PERF_PHASE_MISS_20261024.md).

## Build and use

Add these overrides to the normal supported recipe:

```text
WORLD_CENSUS24=1 PERF_PHASE_MISS=1 PMC_ROW=0 PERF_PHASE_MISS_EVENT=15
```

`WORLD_CENSUS24` already requires the QA menu and supported PS2 streaming
world path. Its usual dependencies and duplicate-work mode refusals remain.
The diagnostic does not force those unrelated settings on silently.

| Event selection | Pinned KOS event | Reported unit |
|---|---|---|
| `PERF_PHASE_MISS_EVENT=15` | `PMCR_OPERAND_CACHE_MISS_MODE`, `0x0f` | Occurrences |
| `PERF_PHASE_MISS_EVENT=37` | `PMCR_PIPELINE_FREEZE_BY_DCACHE_MISS_MODE`, `0x25` | Freeze cycles |

Make a separate otherwise matched build/run for event 37. There is no automatic
rotation, multiplexing, simultaneous measurement or inferred cycles-per-miss
value. `PRFC0` has no diagnostic configuration option and is never touched.

1. Enter the normal in-game QA menu and open **WORLD CENSUS**.
2. Press **X** while paused to run the cache controls. Page through the appended
   PM14 rows. Record the event, status, resident/heavy ranges and all eight raw
   pairs. The menu wraps long rows over additional pages at 320 and 640 widths.
3. A successful on-target response is labelled `QUALIFIED`. A zero/weak/noisy
   response is `INCONCLUSIVE`. Host injected responses are `SIMULATED` and can
   never make `valid=1`. `COUNTER_BUSY` or `COUNTER_LOST` blocks further access
   to the counter in that process; resolve the competing owner and restart.
4. Resume at the chosen fixed room/view. A fresh census collection uses the
   configured 300–600 actual drawn-frame window, with ticks separately counted.
   There is one buffered PM14 summary per sealed census window. PM14 and WC24
   use the same sequence, room and full option/generation identity.
5. Record the sealed QA phase matrix, raw reconciliation totals, samples,
   wraps and errors. A qualified control response does not override a census
   fault or invalid counter sample. Pause drops the partial collection and
   retains the previous sealed snapshot. Running new controls discards the old
   PM14 snapshot so it cannot be paired with new qualification evidence.
6. Repeat in the separate event 37 run with matched state/camera and verify its
   own controls. Physical-console captures are required for hardware claims.

The controls temporarily allocate **34,816 aligned bytes**: 2 KB resident plus
32 KB miss-heavy nodes, excluding allocator metadata. Both run the same
dependent volatile-load loop, 8,192 measured loads per sample, with 4,096 warmup
loads. Eight pairs alternate order. Buffers are freed before gameplay resumes.
No cache-mode or cache-flush operation is performed.

Qualification requires all eight pairs, no errors, and:

```text
heavy_min > 4 * resident_max + 64
heavy_min >= 4096  for event15
heavy_min >= 8192  for event37
```

These are conservative response gates, not estimates of misses per line or
memory latency. Allocation failure and insufficient contrast are explicit
inconclusive results. Repeating controls is an explicit QA action.

## What the counts mean

The six world paths and six phases, three wait bins, and residual form an
exclusive **interval** partition. The SH4 counter is CPU-wide: other threads,
interrupts, observer stack/data accesses, and work during waits can contribute.
The partition does not make those events exclusively attributable to world
code. Same-bin nesting does not read the PMU again; there are no new per-vertex
hooks or hot-loop logs. Inherited census instrumentation remains active.

The observer is intrusive. The bounded target model prices one sampled edge
at 396 cycles before MMIO wait states and cache effects. Its illustrative
1,000-edge population costs about 2.075 ms per drawn frame at an assumed 200 MHz;
the 5,000-edge population costs about 10.367 ms. **Those populations are scenarios,
not r101 measurements.** Costs cannot be subtracted as a portable phase
constant. Use observer-off console timing for the play build's frame deadline.

## Reproduce the public gates

The scripts require a fresh output directory for every run. No private assets,
fake target headers, complete game executable or emulator session is used.
The authoritative baseline is `9b248c5b40a49e4c954ea834fdf665fdbbc314f0`.

```bash
B14_CXX=/tmp/re4dc-sdk-20261024/rootfs/opt/toolchains/dc/sh-elf/bin/sh-elf-g++
B14_KOS=/tmp/re4dc-sdk-20261024/kos
B14_SH4ZAM=/tmp/re4dc-sdk-20261024/sh4zam
B14_SDK_RECEIPT=/tmp/re4dc-sdk-20261024/verification.json

python3 port/dreamcast/tools/cloud/build14/run_controls.py \
  --output /tmp/b14-reproduce-host --kos-root "$B14_KOS" --sanitize

python3 port/dreamcast/tools/cloud/build14/build_controls.py \
  --output /tmp/b14-reproduce-target --sh4-cxx "$B14_CXX" \
  --kos-root "$B14_KOS" --sdk-root "$B14_SH4ZAM" \
  --toolchain-receipt "$B14_SDK_RECEIPT"

python3 port/dreamcast/tools/cloud/build14/target_cost.py \
  --output /tmp/b14-reproduce-cost --sh4-cxx "$B14_CXX" \
  --kos-root "$B14_KOS" --sdk-root "$B14_SH4ZAM"

python3 port/dreamcast/tools/cloud/build14/qa_render_check.py \
  --output /tmp/b14-reproduce-qa
```

Substitute your installation paths while retaining the recorded pins:
GCC 15.2.0/KOS threads, binutils 2.45.1, newlib 4.6.0,
KOS `804b3195ebd1a06a27cc2b3a5eacf7a2429040a3`,
SH4ZAM `33fa4850cacb30dd0ad35485ef035526ec4ce782`.

The restored toolchain is a verified public prebuilt of those versions. Its
actual executable hashes and restoration receipt are recorded; it is not the
lost Build 10 compiler binary. The target gate derives complete real Make
commands, archives the baseline independently and uses the existing public
asset fallbacks and PVR declaration overlay.

Final [receipts](receipts) are losslessly interned with the already-landed
`../build12/compact_receipts.py`. `expand_receipt()` recovers the full parsed
JSON. Detailed metrics, per-region traffic, commands, source/binary hashes,
stack records and full-receipt SHA256 values are preserved. Generated objects,
register fixtures, traces and screenshots remain outside Git.
