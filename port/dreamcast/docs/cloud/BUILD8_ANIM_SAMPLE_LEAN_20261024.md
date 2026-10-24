# Build 8: animation sampling

Base: `d5c1ceab9e06461462669b3ce1d28a379747a74a` (`origin/t15/int`).
Branch: `codex/anim-sample-lean-20261024`. Knob: `ANIM_SAMPLE_LEAN=1`, default **0**.
The release recipe, native motion residency and the four audit fixes are unchanged.

## Decision

`MotionMoveCore` selects a sampler **once per pose**. When the frame is at or
past `maxFrame` and the existing flags select clamping rather than wrapping,
common aligned formats 0/5/6 can read their three final values through a small
stateless helper. Other poses keep the original sampler. Per-joint history
flags, camera channels, flips, error handling and diagnostic comparisons remain
live. Invalid histories delegate the complete call to the original register
sampler, which owns its existing fallback.

This optimizes ended/clamped poses. It does not reduce animation frequency,
change interpolation, cache a pose across ticks or change quaternion/matrix
math. No data-format, allocation, assembly or game-linker change is added.

## What the audit found

The actual sampler is in [src/game/motion.cpp](../../../../src/game/motion.cpp):
`HermiteInterpolation` selects `hermiteReg`/`hfReg` for the common formats.
[native_motion.cpp](../../game/platform/native_motion.cpp) manages motion-key
residency and I/O. It is not the interpolation hot loop.

The current public recipe already enables `GAME_HERMITE_FAST=1`,
`GAME_HF_INLINE=1`, `GAME_HF_PF=1` and `GAME_HF_REG=1`, with
`GAME_HF_ASM=0` and FP contraction disabled. Searches start from the per-axis
history; common layouts are specialized; values/tangents stay in registers;
and the next axis/joint header is prefetched. These are existing savings.

| Data | Size / access |
|---|---|
| `HermitePrm` | 20 bytes on target: frame, maximum, flags, format and key pointer |
| History | Three u16 indices, six bytes per sampled vector |
| Output | Three f32 words, 12 bytes |
| Each axis header | u16 key count followed by `2N` frame bytes |
| Format 0 payload | `12N` bytes: f32 value/in-tangent/out-tangent |
| Format 5 payload | `6N` bytes: s16 value/in-tangent/out-tangent |
| Format 6 payload | `4N` bytes: s16 value and two s8 tangents |

Each axis walks to its next header using the count and format stride. The
ordinary sampler reads frames from its saved history, selects an exact key or
interval, decodes the selected values, and stores output/history. Clamping
already avoids the frame search. The accepted opportunity is avoiding its
general sampler setup, rollback state and repeated control/stack accesses;
the final-value payload itself was already minimal in compiled code.

Actual unique lines depend on axis lengths, key/history/output alignment and
the compiled stack. A six-byte history can touch two lines, and three separated
axis headers need not share any line. Receipt line counts use executed addresses,
not payload bytes divided by 32.

### Rejected attempts

1. **Delete unused endpoint decodes.** At source level the exact-key and clamp
   arms assign four scalars but return only the first. GCC already removed the
   three unused decodes: seven target profiles had zero size delta, and 33
   complete-call probes had zero cycle/traffic gain. The rejection receipt
   retains the tested patch and hashes. The original assignments remain.
2. **Check for clamping at every sample.** A dedicated helper reduced a public
   type-5/eight-key clamped call from 183 to 163 warm cycles and 141/66 to 91/36
   read/write bytes. But ordinary calls gained 13 cycles, looping calls 18,
   and the clamped probe still touched 14 unique lines. It needed roughly
   40% clamped calls to repay ordinary-call overhead. This dispatch was dropped;
   eligibility now belongs to `MotionMoveCore`, once per pose.

Both rejected-candidate probes entered a small fixture wrapper with extra
argument/global loads. The final sampler probe enters the compiled function
directly. Compare OFF/ON within each receipt, not absolute baselines between
these different entry fixtures.

Other rejected directions: equal endpoints/one key do not prove a constant
channel under the existing tangent, rounding and exhausted-search behavior;
type 15 leaves tangents unchanged; persistent decoded caches need residency
generation handling; and skipping quaternion normalization changes matrix
rounding and state. The repository also records earlier `HERMITE_FLAT`,
`GETPOS_MEMO`, `MOTION_LEASE_LEAN` and `GAME_HF_ASM` attempts as measured and
dropped. None is reintroduced or credited as a new gain.

## Exactness argument

`MotionMoveCore` assigns frame, maximum and flags bits 1/2 before choosing the
sampler. None changes in the joint loop; only history bit 3 changes per joint.
Every one of its nine sample sites uses the selected entry: five camera channels
and four bone-channel branches. Root-speed/position queries and motion-setting
calls continue to use the original public entry.

For admitted non-wrapping frames, all three original axes select their last
value and do not update history. The helper uses the same format-specific
conversion and preserves the next-axis PREF. `idx >= n` matches the original
`idx > n-1`; history-ignore mode supplies index zero. Failure delegates to the
complete original `hfReg`, preserving history, error logs, return values and
the later `hermiteFast` fallback. It may recompute earlier outputs, as that
fallback already does. Actual callers use disjoint key, history and output
storage. Odd addresses and other formats keep the existing path.

The HFR and HERMF diagnostic bodies are shared through compile-time sampler
selection, so they still compare outputs, history and return values. PPC,
non-Dreamcast and non-register-sampler configurations retain their old path.
The claim concerns sampled words and caller state, not general floating-point
exception-status or trap-trace equivalence.

## Compiled cost, identity and output evidence

The reproducible commands and receipts are in
[tools/d367/anim_sample_lean](../../tools/d367/anim_sample_lean/README.md).
They compile the complete production translation unit using Make-derived
R21/Test 22 public inputs, current literal CH2 assignments and public asset
fallbacks. These are **model estimates**, at 200 MHz with perfect D-cache,
no DMA and zero store-queue cost. Warm prices assume perfect I-cache. Cold-I
prices start the model's 8 KB I-cache cold once per complete call/pose at the
synthetic ELF layout. They are not console miss or frame-time measurements.

### Demand traffic and complete caller cost

The final sampler matrix has **138 paired compiled executions**; the complete
caller matrix has **30 paired poses**. All output/history snapshots match.
Normal public sampler entries have identical warm cycles and demand traffic
throughout the sampler matrix; their cold-I costs can differ with code layout.

Representative type-5/eight-key, three-axis calls:

| Call | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Load/store bytes OFF → ON | Distinct 32-byte data lines OFF → ON | Repeated line visits OFF → ON |
|---|---:|---:|---:|---:|---:|
| Clamped, valid history | 176 → 140 | 333 → 238 | 125/66 → 59/36 | 13 → 12 | 43 → 17 |
| Clamped, ignored history | 158 → 134 | 287 → 232 | 107/66 → 53/36 | 13 → 11 | See receipt |
| Clamped, invalid history | 526 → 608 | 899 → 1,038 | 359/248 → 409/276 | 20 → 21 | See receipt |
| Ordinary interval | 446 → 446 | 681 → 679 | 167/102 → 167/102 | 15 → 15 | Unchanged |

The invalid-history case deliberately shows the cost of taking the exact
original fallback after admission. Every call is not faster.

**Key-payload reads do not shrink:** the valid clamped case still loads 12 key
bytes across six key-data lines. Parameter reads fall from 21 to 13 bytes,
history reads from 12 to six, stack reads/writes from 64/54 to 20/24, and literal
reads from 16 to eight. Stack demand falls from two distinct lines to one.
These region counts can share physical lines and must not be added as if
disjoint. The benefit is repeated control/stack traffic, not a key-data cache.

The complete compiled `MotionMoveCore` probe includes admission, function-pointer
selection/calls, register spills, all nine sampling sites and the real sampler.
Unchanged residency, lookup, logging and angle/matrix calls are explicit typed
fixture adapters; their small instruction costs remain in both arms. Original
I/O/lookup/math implementation costs are excluded. The existing matrix-skip flag
is set, and bounded angle values use a no-op `VecRadLimit` adapter. Sequence
advancement, hokan, IK and animation outside this function are not included.

| Complete pose | Warm cycles OFF → ON | Cold-I cycles OFF → ON | Load/store bytes OFF → ON | Distinct data lines OFF → ON | Demand line visits OFF → ON | Peak stack OFF → ON |
|---|---:|---:|---:|---:|---:|---:|
| T5, one vector, ordinary | 685 → 692 | 1,294 → 1,295 | 409/219 → 409/219 | 39 → 38 | 187 → 187 | 176 → 176 B |
| T5, four vectors, ordinary | 2,383 → 2,381 | 3,014 → 3,020 | 1,245/580 → 1,233/568 | 68 → 67 | 563 → 557 | 176 → 176 B |
| T5, 16 vectors, ordinary | 9,184 → 9,146 | 9,815 → 9,785 | 4,611/2,032 → 4,551/1,972 | 186 → 185 | 2,075 → 2,045 | 176 → 176 B |
| T5, one vector, clamped | 415 → 386 | 946 → 850 | 367/183 → 301/153 | 38 → 36 | 157 → 130 | 176 → 132 B |
| T5, four vectors, clamped | 1,303 → 1,157 | 1,856 → 1,657 | 1,077/436 → 801/304 | 57 → 55 | 443 → 329 | 176 → 132 B |
| T5, 16 vectors, clamped | 4,864 → 4,250 | 5,417 → 4,750 | 3,939/1,456 → 2,823/916 | 145 → 143 | 1,595 → 1,133 | 176 → 132 B |
| T5, 16 vectors, ordinary, usual 10.6 `Seq.frame` | 9,196 → 9,158 | 9,818 → 9,793 | 4,613/2,032 → 4,553/1,972 | 186 → 185 | 2,076 → 2,046 | 176 → 176 B |
| T5, 16 vectors, clamped, usual 10.6 `Seq.frame` | 4,876 → 4,262 | 5,420 → 4,758 | 3,941/1,456 → 2,825/916 | 145 → 143 | 1,596 → 1,134 | 176 → 132 B |

Other rows use the supported direct-frame input. The two usual `Seq.frame`
controls establish the same deltas through normal 10.6 conversion. The 16-vector
clamped T0/T5/T6 cases save 726/614/678 warm cycles, 1,464/1,656/1,784 demand bytes
and 414/462/494 line visits, with two/two/three fewer distinct lines. T5 repeated
line visits fall from 1,450 to 990; the 462 total-visit reduction includes the two
distinct lines. Shared stack addresses mean these unique-line reductions are not
additive across a frame.

For the direct-frame T5/16-vector clamp, executed load/store instructions fall
from 1,195/400 to 892/241; the ordinary counterpart falls from 1,483/592 to
1,468/577. The receipts retain instruction counts for every case, separately
from byte totals and line visits.

Counts are architectural demand loads/stores and executed 32-byte addresses.
Opcode fetches are excluded; literals are data loads; PREF requests are recorded
separately. They do not establish cache fills, misses or external bus traffic.
Scalar target execution uses the existing fail-closed interpreter, RN binary32
with DN enabled, and synthetic inputs away from exceptional boundaries. A bounded
camera `FTRC` adapter has seven conversion controls. This is not general SH-4
floating-point or exception-status conformance.

### Object size, stack and knob-OFF identity

An independent archive of exact base `d5c1ceab` was compared with this branch.
**All 28 comparisons pass:** absent and explicit-zero knob, full `-E -P`
preprocessing and raw production objects, across REG1, REG0, REG2, FAST2,
no-prefetch, reference and ASM1 profiles. Debug records are consistently omitted.
Generated headers and effective OFF Make flags match. The six additional
inactive-ON source/object comparisons pass for REG0, reference and ASM1.

| Profile | Executable bytes OFF → ON | Delta |
|---|---:|---:|
| Public REG1 | 16,620 → 17,048 | +428 B |
| REG2 diagnostic | 16,756 → 17,524 | +768 B |
| FAST2 diagnostic | 16,668 → 17,456 | +788 B |
| No prefetch | 16,604 → 16,984 | +380 B |
| REG0 / reference / ASM1 | Unchanged | 0 B |

Data and BSS deltas are zero. `MotionMoveCore` static stack remains 108 bytes;
the normal public sampler entry remains zero. General T0/T5/T6 sampler frames
use 68/68/56 bytes; new clamped leaves use 24/24/20. Complete T5 clamped-pose peak
stack falls from 176 to 132 bytes. The target-executed production object hashes
are verified against the build-control zero/ON objects.

### Exact output and caller-state controls

The separate host suite compares seven Make-derived profiles plus a public-profile
ASan/UBSan repetition: **1,687,296 paired sampler cases and 18,440 paired actual
caller poses**, comparing **52,527,168 observation words** (210,108,672 bytes).
They are sampled output/history/caller-state observations, not TA words. Both
sanitized arms pass. All nine actual caller sites enter the private sampler when
the independent pose predicate permits it. Normal public entry calls explicitly
assert that they stay on the original path, including clamped input.

Coverage includes flags 0–15, alignments 0–3, common/fallback types, unequal axis
counts, exact/interior/clamped/wrapped/reverse frames, valid single-key axes,
invalid histories on each axis, defined later-axis exhaustion, ignore-history,
same-address key rewrites and defined signed-zero/NaN/infinity value payloads.
Caller cases include camera channels, main/blend work, linked/contiguous parts,
mirror lookup, missing/skipped parts and inactive motion. The production
`getPartsPtr` and `VecRadLimit` execute in this host suite; matrix helpers are
recorded deterministic edges and native residency is a pass-through adapter.
The host ASM edge uses the original C sampler, not target assembly.

All HFR/HERMF mismatch counters remain zero and 56 periodic diagnostic messages
match. Three actual-caller negative controls detect a wrong final-key read,
missing invalid-history fallback and forced clamp admission. Zero-key axes and
first-axis exhaustion with uninitialized prior state are excluded because they
have pre-existing undefined behavior. The evidence establishes the stated
code-level equivalence, not full asset, quaternion/matrix or hardware coverage.

The measured `motion.cpp` SHA-256 is
`63e72196ab98e230d3dd14b7ad7328433a63e44d4c0406227374cd9a5b522a8f`.

## MODELLED whole-frame contribution

No animation population or clamp-rate capture is available. The reported 1.45 ms
animation cost does not establish the fraction of ended poses; 87/50 world-part
counts are unrelated. For a census of pose classes, sum each class's matched
warm-cycle delta and divide by 200,000 to obtain milliseconds at 200 MHz.

For **16 hypothetical poses of 16 sampled type-5 vectors each**:

| Synthetic mix | MODELLED warm time saved | Demand bytes removed | Demand line visits removed |
|---|---:|---:|---:|
| All clamped, valid histories | 0.04912 ms | 26,496 | 7,392 |
| Half clamped, half ordinary | 0.02608 ms | 14,208 | 3,936 |
| All ordinary | 0.00304 ms | 1,920 | 480 |

Sixteen ordinary **single-vector** poses instead cost 0.00056 ms more and save
no demand bytes. Invalid histories can also regress, as the explicit control
shows. Cold-I pose costs are supplied for sensitivity, not added per sample.
These figures describe the measured code phases under synthetic populations;
they are not a predicted r101 frame gain. Console A/B and a real pose census
decide whether to enable this small candidate.

## Open questions back to Claude

1. Can the animation census count sampled vectors per pose and classify clamped,
   ordinary and wrapping poses at r101 and in the piled-body farm case?
2. Does console A/B confirm that reduced sampler stack/traffic repays the
   once-per-pose dispatch cost in the measured mix?
