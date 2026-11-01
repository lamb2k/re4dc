# Build28 validation

## Final raw target qualification: PASS

The final integration base is
`568c357656efbec468db06a282c1f79caebaa725`. Against its independent `git archive`,
the complete changed translation units pass **56 absent/zero raw preprocessed
and object comparisons**, **nine enabled compositions**, and **eight additional
raw comparisons** proving that review28 stays inert with `QA_LINK=0`.
All compiler inputs are unmodified production bytes; no syntax overlay or
preprocessed/object byte normalization is used. This is a changed-TU proof,
not a complete game-image or console acceptance claim.

The initial base `8a55a9d5` contained three malformed menu directives. Upstream
fixed exactly those directives before the required final rebase. The final
raw matrix supersedes the earlier explicitly conditional syntax qualification;
the primary receipts below all name the corrected final base and report `PASS`.

## Qualification scope

The compiler is the pinned GCC 15.2.0 / binutils 2.45.1 toolchain, with KOS
`804b3195` and SH4ZAM `33fa4850`. Executable hashes are checked against the
existing Build24 toolchain receipt. All flags come from Make and the retained
public recipe reader. `NMR_POOL_LOD=0` is a validation-only override, mirrored
on both sides because private Ganado assets are unavailable.

The full raw matrix covers `QA_LINK=0/1` ×
`DRAW_FALLBACK_AUDIT=0/1` × `DRAW_SETUP_AUDIT=0/1`, with XLU enabled alongside
DSA, plus `BENCHMARK=1, QA_MENU=0, QA_LINK=1`. It respects actual Make selection:
menu alone with link off; menu plus transport with link on; benchmark plus
transport on a link benchmark. No transport target is invented for a release
configuration that excludes it.

The completed raw matrix contains **56 absent/zero preprocessed/object
comparisons, nine enabled compositions, and eight additional preprocessed/object
comparisons** showing that `QA_LINK_REVIEW28=1` stays inert when `QA_LINK=0`.
Every check passed. Release Make checks leave all three reviewed console TUs
excluded. Empty, `2` and multiword review-knob assignments are rejected. The
final [OFF receipt](receipts/target-off.json) and
[ON receipt](receipts/target-on.json) record completion, toolchain provenance,
Make selection and source closure. The benchmark/transport raw proof is part
of this same full matrix.

## Actual RECORD sort costs

[sort-cost.json](receipts/sort-cost.json) prices real generated SH4 instructions.
The old insertion loop is extracted verbatim and checked against integration.
The new arm calls the actual adaptive `sort_ticks` helper: insertion work is
bounded before the constant-space heap fallback. Inputs and sorted outputs are
checked exactly. This excludes RECORD formatting, game callbacks, diagnostic
refresh, packet handling and socket/PPP work.

| Input | Arm | Warm cycles | Cold-I cycles | Loads | Stores | Distinct 32-byte data lines | Peak fixture stack |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 128 ascending | Old | 1,414 | 1,456 | 257 | 128 | 18 | 4 B |
| 128 ascending | New | 1,422 | 1,504 | 261 | 132 | 18 | 20 B |
| 128 reverse | Old | 57,548 | 57,591 | 8,258 | 8,256 | 18 | 4 B |
| 128 reverse | New | 25,757 | 25,896 | 3,040 | 1,600 | 18 | 20 B |
| 1,800 ascending | Old | 19,806 | 19,848 | 3,601 | 1,800 | 227 | 4 B |
| 1,800 ascending | New | 19,814 | 19,896 | 3,605 | 1,804 | 227 | 20 B |
| 1,800 nearly sorted | Old | 19,813 | 19,856 | 3,602 | 1,801 | 227 | 4 B |
| 1,800 nearly sorted | New | 19,825 | 19,904 | 3,606 | 1,805 | 227 | 20 B |
| 1,800 reverse | Old | 11,342,712 | 11,342,755 | 1,620,902 | 1,620,900 | 227 | 4 B |
| 1,800 reverse | New | 531,421 | 531,560 | 61,844 | 28,560 | 227 | 20 B |

The nearly sorted case swaps only the two central adjacent elements. The large
reverse case is fully executed; its cost is not extrapolated. The bounded sort
fixture grows from 78 to 328 executable bytes. These wrapper-object sizes are
separate from the complete production-TU section deltas.

The initial plain heapsort candidate took 490,334 warm cycles on the ascending
1,800-element input. That concrete regression led to the adaptive implementation
above. The final ascending penalty is eight cycles; nearly sorted adds twelve.
The final reverse case adds a bounded insertion prefix before its heap fallback.

**MODELLED whole-frame sensitivity:** assume an unchanged 30 ms for all omitted
work and exactly one sort on a RECORD completion tick. At 200 MHz, reverse
1,800 changes `30 + 11342712 / 200000 = 86.713560 ms` to
`30 + 531421 / 200000 = 32.657105 ms`. Ascending changes
30.099030 to 30.099070 ms; nearly sorted changes 30.099065 to 30.099125 ms.
These are synthetic completion-tick totals, not regular-frame FPS or a sampled
distribution of actual recorded ticks.

## Actual transport-ring costs

[ring-cost.json](receipts/ring-cost.json) compiles the exact production `Ring`
and datagram-limit enum with the real transport flags. The 26 cases cover
accepted enqueue/dequeue, wraparound, full/empty queues, the 1,200-byte boundary,
oversize refusal and whole-datagram retirement when the receive destination is
too short. No external service body is replaced or executed by these methods.

| Operation | Arm | Warm cycles | Cold-I cycles | Loads | Stores | Distinct 32-byte data lines | Peak fixture stack |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Put 1,100 B | Old | 6,639 | 6,694 | 1,114 | 1,104 | 74 | 4 B |
| Put 1,100 B | New | 6,657 | 6,722 | 1,118 | 1,105 | 74 | 8 B |
| Put 1,200 B | Old | 7,239 | 7,294 | 1,214 | 1,204 | 80 | 4 B |
| Put 1,200 B | New | 7,257 | 7,322 | 1,218 | 1,205 | 80 | 8 B |
| Get 1,100 B | Old | 9,946 | 10,018 | 1,114 | 1,103 | 74 | 8 B |
| Get 1,100 B | New | 9,948 | 10,018 | 1,115 | 1,103 | 74 | 8 B |
| Get 1,200 B | Old | 10,846 | 10,918 | 1,214 | 1,203 | 80 | 8 B |
| Get 1,200 B | New | 10,848 | 10,918 | 1,215 | 1,203 | 80 | 8 B |
| Put oversize 1,201 B | Old accepts | 7,245 | 7,300 | 1,215 | 1,205 | 80 | 4 B |
| Put oversize 1,201 B | New refuses | 15 | 36 | 3 | 0 | 2 | 0 B |
| Get 1,130 B into 512 B | Old truncates | 7,745 | 7,817 | 526 | 515 | 37 | 8 B |
| Get 1,130 B into 512 B | New discards whole | 43 | 110 | 14 | 3 | 5 | 8 B |

The last two pairs intentionally change the observable result. Valid-packet
checks add 18 warm cycles to enqueue and two to dequeue in these fixtures.
Combined wrapper code grows from 254 to 296 executable bytes; the 16-byte
layout descriptor makes allocated totals 270 and 312 bytes. Production storage
is reported separately.

For one 1,130-byte enqueue and one 16-byte dequeue, the same assumed 30 ms
remainder gives **30.035045 → 30.035145 ms MODELLED**, a 20-cycle increase.
This excludes modem transmission, PPP, scheduler waits and network allocation;
it is not a transport-pump deadline or end-to-end latency estimate.

## Meaning and limits of the numeric evidence

Warm timing uses perfect instruction/data caches; cold-I starts an isolated
8 KB instruction cache empty while keeping the data cache perfect. Counts
include real opcode data accesses, stack and literal-pool loads. Distinct
32-byte lines are a footprint, not measured cache fills, writebacks or bus
transactions. The sort reduces repeated accesses sharply while touching the
same unique input lines. No D-cache miss benefit is invented.

Completed cost rows are retained after the final rebase only after freshly
compiled object **and ELF** hashes match exactly. The old sort fragment is
also checked against the final integration source. Receipts name the ancestor
base and source receipt hashes; both arms' code identities and all numeric
results are unchanged. New cases execute normally. Reproduction does not
require reuse: omitting `--reuse` executes the complete case set.

Hardware sessions, KOS heap squeeze, redial soak, lost-packet behavior and owner
playtests remain distinct from these public fixtures.

## Complete production sections and local stack

[production-metrics.json](receipts/production-metrics.json)
compares each enabled profile with its matching integration configuration.
All objects come from the final raw matrix above. These are complete
selected-TU section deltas before final linking/garbage collection.
Allocated totals include code, read-only data, initialized data and BSS; do not
add the BSS column a second time.

| Selected configuration | Added executable | Added allocated total | Added BSS |
| --- | ---: | ---: | ---: |
| QA_LINK=0, all four DFA/DSA settings | 0 B | 0 B | 0 B |
| QA_LINK=1, DFA=0, DSA=0 | 2,696 B | 3,264 B | 300 B |
| QA_LINK=1, DFA=0, DSA=1/XLU=1 | 2,708 B | 3,276 B | 300 B |
| QA_LINK=1, DFA=1, DSA=0 | 2,464 B | 3,000 B | 268 B |
| QA_LINK=1, DFA=1, DSA=1/XLU=1 | 2,464 B | 3,000 B | 268 B |
| QA_LINK=1 benchmark, no QA menu | 1,608 B | 1,648 B | 36 B |

The transport contributes 1,152 executable, 1,183 allocated and 27 BSS bytes
in each enabled configuration. The benchmark TU contributes 456 executable,
465 allocated and nine BSS bytes. `Snapshot::kind` defaults to zero: `begin`
sets the actual kind before use, so the otherwise-zero snapshot stays in BSS
instead of placing its full text storage in initialized data.

| Compiler local frame | Before | After |
| --- | ---: | ---: |
| QA `link_pump`, DFA off | 2,648 B | 3,092 B |
| QA `link_pump`, DFA on | 3,092 B | 3,092 B |
| QA `record_tick` | 456 B | 456 B |
| Transport `hang_up` | 16 B | 24 B |
| Transport `re4dc_qalink_start` | 8 B | 8 B |
| Transport `re4dc_qalink_send` | 8 B | 8 B |
| Transport `re4dc_qalink_send_bulk` | 24 B | 24 B |
| Largest transport local frame | 248 B | 248 B |
| Largest benchmark local frame | 2,968 B | 3,108 B |

Local frames are not a full call-chain, IRQ or console stack watermark. Inlined
helpers are included in their callers; their small standalone cost-fixture
frames must not be added mechanically to these production figures.

## Reproduction

Run from the repository root with fresh output directories. These commands
use the final integration base and the normal raw gate. The historical
`--syntax-control` option is not used for the corrected source or any final
receipt.

```sh
B28_CXX=/workspace/scratch/206a5d423cac/toolchain/restored/opt/toolchains/dc/sh-elf/bin/sh-elf-g++
B28_KOS=/workspace/scratch/206a5d423cac/toolchain/kos
B28_SDK=/workspace/scratch/206a5d423cac/toolchain/sh4zam
B28_TOOLCHAIN=/workspace/scratch/206a5d423cac/toolchain/toolchain.json
B28_BASE=568c357656efbec468db06a282c1f79caebaa725
B28_OUT=/tmp/build28-qualification

python3 port/dreamcast/tools/cloud/build28/build_controls.py \
  --output "$B28_OUT/off" --baseline "$B28_BASE" --only off \
  --sh4-cxx "$B28_CXX" --kos-root "$B28_KOS" --sdk-root "$B28_SDK" \
  --toolchain-receipt "$B28_TOOLCHAIN"

python3 port/dreamcast/tools/cloud/build28/build_controls.py \
  --output "$B28_OUT/on" --baseline "$B28_BASE" --only on \
  --sh4-cxx "$B28_CXX" --kos-root "$B28_KOS" --sdk-root "$B28_SDK" \
  --toolchain-receipt "$B28_TOOLCHAIN"

python3 port/dreamcast/tools/cloud/build28/sort_cost.py \
  --output "$B28_OUT/sort" --baseline "$B28_BASE" \
  --sh4-cxx "$B28_CXX" --kos-root "$B28_KOS" --sdk-root "$B28_SDK"

python3 port/dreamcast/tools/cloud/build28/ring_cost.py \
  --output "$B28_OUT/ring" --baseline "$B28_BASE" \
  --sh4-cxx "$B28_CXX" --kos-root "$B28_KOS" --sdk-root "$B28_SDK"

python3 port/dreamcast/tools/cloud/build28/production_metrics.py \
  --off "$B28_OUT/off/target-controls.json" \
  --on "$B28_OUT/on/target-controls.json" \
  --output "$B28_OUT/production-metrics.json"
```

`compact_receipt.py --input RAW --output NEW` retains statuses, exact identity
hashes, numeric evidence and source provenance. Compaction does not alter
compiler artifacts or change a gate's qualification status.
