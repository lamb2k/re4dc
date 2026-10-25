# Build 13 target-cost reproduction

Actual SH4 selection/replay setup plus a bounded 16-byte metadata probe.

The complete native_static.cpp translation unit is compiled with Make-derived
flags. Only emit_pick's geometry body is an observed boundary: transform,
clipping, TA and cache-miss latency are excluded. The separate metadata probe
consumes every logical emit field using the production reader, then writes four
test-only observation words. Its cycles are probe cycles, not renderer time.
Combined metadata lines are the union of actual selector reads and that full
16-byte consumption; they are neither cache fills nor a 43% world-byte saving.
The established Build 5 test-only return stubs/linker layout are reused. No
runtime SH4 assembly or linker change is introduced.

Primary paired flags: `SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1
SCENERY_SUBMIT_BATCH=1 SCENERY_UV_SNAPSHOT=1 SCENERY_SELECT_LEAN2=1
SCENERY_EMIT_PREFETCH=0 PREF_WALK=0 PS2_INTERIOR_CULL=0 WORLD_RECT21=0
FOLIAGE_MIP24=0`. The cost build records the entire Make-expanded profile.

```sh
python3 port/dreamcast/tools/cloud/build13/layout_controls.py \
  --out /tmp/b13-layout --receipt /tmp/b13-layout/layout-controls.json
python3 port/dreamcast/tools/cloud/build13/target_cost.py build \
  --output /tmp/b13-cost-build \
  --sh4-cxx /tmp/re4dc-sdk-20261024/rootfs/opt/toolchains/dc/sh-elf/bin/sh-elf-g++ \
  --kos-root /tmp/re4dc-sdk-20261024/kos \
  --sdk-root /tmp/re4dc-sdk-20261024/sh4zam \
  --override PS2_INTERIOR_CULL=0 --override WORLD_RECT21=0 --override FOLIAGE_MIP24=0
python3 port/dreamcast/tools/cloud/build13/target_cost.py run \
  --output /tmp/b13-cost-run --build /tmp/b13-cost-build/cost-build.json \
  --fixtures /tmp/b13-layout/fixtures.json
```

Paths to the pinned SDK are installation examples. Use the compiler/KOS/SH4ZAM
versions and hashes recorded in the build receipt. The output directory must
not already exist; intermediate ELF, traces and generated public packages
are left outside the repository. The build/run source-hash guard refuses stale
compiler fixtures. The checked-in receipts expand with
`tools/cloud/build12/compact_receipts.py::expand_receipt`.

## All warm case costs

Every cell is ordinary / enabled ordinary fallback / split. Metadata-probe
cycles are observer work, not production geometry cost. Each case passes
selection semantics, replay edges/state, and ordered emit-field equality.

| Case | Selection | Replay/setup | Metadata probe | Emit lines | Selection + metadata line union |
| --- | ---: | ---: | ---: | ---: | ---: |
| whole-inside | 411 / 477 / 442 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 1 |
| whole-tested | 711 / 776 / 741 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 1 |
| scalar-box-fallback | 996 / 1,067 / 1,032 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 2 |
| partial-groups | 1,845 / 1,912 / 1,874 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 2 |
| zero-retained-groups-pick | 1,808 / 1,877 / 1,839 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 2 |
| many-meshlets | 4,877 / 11,004 / 9,374 | 4,874 / 4,817 / 4,816 | 8,018 / 11,882 / 9,962 | 280 / 280 / 160 | 280 / 280 / 160 |
| repeated-plane-cache | 4,720 / 4,907 / 4,829 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 | 5 / 5 / 3 | 6 / 6 / 6 |
| plain-dense-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 28 / 28 / 16 | 28 / 28 / 16 |
| plain-sparse-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 40 / 40 / 32 | 40 / 40 / 32 |
| plain-reverse-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 28 / 28 / 16 | 28 / 28 / 16 |
| indexed-dense-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 28 / 28 / 16 | 28 / 28 / 16 |
| indexed-sparse-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 40 / 40 / 32 | 40 / 40 / 32 |
| indexed-reverse-32 | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 | 28 / 28 / 16 | 28 / 28 / 16 |
| exporter-32-part0 | 758 / 1,223 / 1,083 | 1,298 / 1,241 / 1,240 | 568 / 856 / 724 | 19 / 19 / 11 | 19 / 19 / 11 |
| exporter-32-part1 | 758 / 1,223 / 1,083 | 1,298 / 1,241 / 1,240 | 568 / 856 / 724 | 20 / 20 / 12 | 20 / 20 / 12 |
| exporter-32-part2 | 758 / 1,223 / 1,083 | 1,298 / 1,241 / 1,240 | 568 / 856 / 724 | 20 / 20 / 11 | 20 / 20 / 11 |
| exporter-64-part0 | 534 / 695 / 635 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 | 5 / 5 / 3 | 5 / 5 / 3 |
| exporter-64-part1 | 534 / 695 / 635 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 | 6 / 6 / 4 | 6 / 6 / 4 |
| exporter-64-part2 | 534 / 695 / 635 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 | 6 / 6 / 3 | 6 / 6 / 3 |
| exporter-128-part0 | 492 / 596 / 551 | 1,070 / 1,013 / 1,012 | 93 / 153 / 135 | 3 / 3 / 2 | 3 / 3 / 2 |
| exporter-128-part1 | 492 / 596 / 551 | 1,070 / 1,013 / 1,012 | 93 / 153 / 135 | 3 / 3 / 2 | 3 / 3 / 2 |
| exporter-128-part2 | 492 / 596 / 551 | 1,070 / 1,013 / 1,012 | 93 / 153 / 135 | 3 / 3 / 2 | 3 / 3 / 2 |
| exporter-256-part0 | 464 / 530 / 495 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 1 |
| exporter-256-part1 | 464 / 530 / 495 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 1 |
| exporter-256-part2 | 464 / 530 / 495 | 1,046 / 989 / 988 | 43 / 79 / 73 | 1 / 1 / 1 | 1 / 1 / 1 |

### Final target results

All **25 cases pass**: thirteen synthetic cases and twelve real exporter
part/size cases. Each timing entry below is **ordinary / enabled ordinary
fallback / split**. Warm scheduling assumes perfect I/D caches and no
DMA, SQ service or memory-bus cost. The complete receipts also give cold
8 KiB I-cache results, dynamic instructions and every traffic region.

| Case | Selection warm cycles | Replay/setup warm cycles | Metadata-probe warm cycles |
| --- | ---: | ---: | ---: |
| One fully inside pick | 411 / 477 / 442 | 1,046 / 989 / 988 | 43 / 79 / 73 |
| Partial group range | 1,845 / 1,912 / 1,874 | 1,046 / 989 / 988 | 43 / 79 / 73 |
| 320 fully inside picks | 4,877 / 11,004 / 9,374 | 4,874 / 4,817 / 4,816 | 8,018 / 11,882 / 9,962 |
| Six picks with repeated plane tests | 4,720 / 4,907 / 4,829 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 |
| 32 dense metadata IDs | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 |
| 32 sparse metadata IDs | 1,293 / 2,556 / 2,206 | 1,418 / 1,361 / 1,360 | 818 / 1,226 / 1,034 |
| Exporter 64, part 0, six picks | 534 / 695 / 635 | 1,106 / 1,049 / 1,048 | 168 / 264 / 228 |
| Exporter 256, part 0, one pick | 464 / 530 / 495 | 1,046 / 989 / 988 | 43 / 79 / 73 |

The 32-ID dense/sparse/reverse controls first run the same actual selector
over 64 inside meshlets, then install a declared 32-ID replay/probe list.
Their selection cost is not the cost of discovering only 32 visible IDs.
Indexed cases have the same setup costs because geometry/gather is outside
this fixture; this is not evidence that indexed and plain emission cost the
same.

At 320 dense picks, the metadata union falls from **280 to 160 lines**,
while selection rises from **4,877 to 9,374 warm cycles**. The enabled
ordinary fallback costs 11,004 selection cycles and still touches 280
metadata lines. At 32 sparse IDs the union falls only from 40 to 32 lines,
versus 28 to 16 for dense IDs. For six picks requiring repeated plane tests,
emit-prefix lines fall from 5 to 3 but the combined selection/metadata union
remains **6 lines**. A partial one-meshlet group can grow from one combined
line to two. These results keep accessor/selection overhead and bounds traffic
visible; the split is not accepted as a performance win.

### Traffic and cold-I example

The real 64-vertex exporter, part 0, gives the following phase counts.
Each row starts its own cold-I run; cold figures must not be added and
called one cold frame. Loads/stores and read/write bytes are cached RAM
demand accesses. Lines are the union of all touched RAM, including stack
and harness state, rather than just the meshlet metadata.

| Phase / arm | Warm / cold-I cycles | Loads / stores | Read / write bytes | 32-byte RAM lines |
| --- | ---: | ---: | ---: | ---: |
| Selection, off | 534 / 1,096 | 158 / 105 | 601 / 366 | 42 |
| Selection, on ordinary | 695 / 1,369 | 201 / 109 | 768 / 382 | 47 |
| Selection, on split | 635 / 1,271 | 189 / 107 | 718 / 374 | 44 |
| Replay/setup, off | 1,106 / 1,717 | 190 / 395 | 692 / 1,508 | 63 |
| Replay/setup, on ordinary | 1,049 / 1,667 | 198 / 343 | 714 / 1,315 | 65 |
| Replay/setup, on split | 1,048 / 1,666 | 200 / 343 | 718 / 1,315 | 64 |
| Metadata probe, off | 168 / 212 | 37 / 24 | 136 / 96 | 15 |
| Metadata probe, on ordinary | 264 / 368 | 68 / 31 | 255 / 124 | 18 |
| Metadata probe, on split | 228 / 320 | 63 / 31 | 233 / 124 | 15 |

The selected metadata itself occupies 5 / 5 / 3 lines in this example.
The metadata probe writes observation words and includes accessor costs; it
is a bounded consumption/traffic experiment, not a replacement measurement
of the actual transform and emit kernel.

### Explicitly MODELLED whole-frame scenario

Assume 200 MHz, the public mesh at LOD0 in both placements, a separate
selection and replay/setup invocation for each of the six part visits, and
**30 ms of assumed other work** including every excluded geometry, gameplay
and rendering cost. Price the measured warm selection and replay/setup
only: `30 ms + 2 * sum(three parts' cycles) / 200,000`. The observer probe
is excluded. The imposed 30 ms is not measured and deliberately does not
estimate transform changes between sizes.

| Vertex limit | Off setup cycles for six visits | Split setup cycles for six visits | MODELLED frame off | MODELLED frame on ordinary | MODELLED frame on split |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 12,336 | 13,938 | 30.06168 ms | 30.07392 ms | 30.06969 ms |
| 64 | 9,840 | 10,098 | 30.04920 ms | 30.05232 ms | 30.05049 ms |
| 128 | 9,372 | 9,378 | 30.04686 ms | 30.04827 ms | 30.04689 ms |
| 256 | 9,060 | 8,898 | 30.04530 ms | 30.04557 ms | 30.04449 ms |

This is an arithmetic setup-only scenario, **not r101, not a complete world
measurement and not a 30 fps qualification**. At the existing 64 default,
split setup is 258 cycles worse across these six visits (0.00129 ms in this
model). A console benefit would have to recover that overhead through actual
cache behaviour and the full emit path. The larger-size fixtures also change
ordered geometry and visibility granularity; their smaller setup totals alone
do not accept a new size.

### Code, stack and memory

Complete matched production translation-unit compilation gives:

| Metric | Split 0 | Split 1 |
| --- | ---: | ---: |
| `native_static.o` executable section bytes | 62,510 | 66,860 |
| Allocated section bytes | 91,358 | 97,026 |
| Zero-fill bytes | 17,067 | 17,067 |
| Largest individual function stack | 8,880 | 8,896 |
| `ps2_open` stack | 592 | 684 |
| Selector stack | 260 | 236 |
| `chunk_emit` stack | 128 | 132 |

These are per-function compiler stack values, not an entire game call-chain
bound. Resident payload and R4SG sizes appear above; no temporary full AoS
copy is allocated, and the existing gather storage is retained.

## Interpreter and controls

The target instruction interpreter adds only `DIV0U` (opcode `0x0019`) for
the untimed GCC division initializer used by package adoption. Eight cases
cover every incoming M/Q/T combination, other-state preservation, exactly
one retired instruction and no demand access. Unsupported DIV1 remains a
hard failure. Semantics follow the
[Renesas SH-4 Software Manual](https://www.renesas.com/en/document/mas/sh-4-software-manual), section 9.18,
printed page 238. Existing test-only traps/stubs/link placement are reused;
no production assembly or linker change is added.

The existing eight opcode-traffic controls pass. Demand accesses exclude
instruction fetch; PC-relative literal loads remain data; delay-slot accesses
are counted once; an 8-byte move remains one instruction; address wrap and
SQ classification are explicit. PREF requests are separate from demand
loads. Combining selector/probe events rebases dynamic instruction ordinals
and computes an address union, preserving separate loads to a shared line.

All 25 cases are public/synthetic. There is no private world, final game link,
console cache model, bus/SQ service model, or full geometry cost in this gate.
