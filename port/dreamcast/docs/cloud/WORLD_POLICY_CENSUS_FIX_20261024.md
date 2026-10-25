# World policy and census diagnostics follow-up — 2026-10-24

Branch: `codex/world-policy-census-fix-20261024`. Publication base:
`8c9921201bcb26fb5113c2dbee54d7cdf78bdc32` on `origin/t15/int`.
Validation base: `dd6b66b9523300181df8e0af8cbe8ece3bdc4be0`.
The intervening commit adds 51 queue-document lines only; runtime, tools and
validated inputs are identical. Its new owner answers are preserved below.
This is a bounded follow-up to the Build12 inbox, not another world-layout
candidate or a claim that world drawing has reached 2 ms.

## Outcome and current performance decision

Two missing diagnostics are addressed: the world converter can identify the
precise policy/group field that refuses, and WC24 can explain its existing
aggregate error count. A separate authenticated preparation tool can recover
an original-policy **control** from a known texture-key-remapped policy.
Successful ordinary converter output and all runtime OFF paths retain their
existing behavior. No play recipe is enabled by this change.

During this follow-up, the owner published a valid original-data control in
the [queue](CLOUD_AGENT_QUEUE.md), commit `dd6b66b9`. This supersedes the earlier
Build12 windows with `err=1200`. The owner's `ctl-olddata` uses the Test23
program at `2df0e2a8` and its original-policy DATA stack. All three valid arms
have `err=0`; both layouts were admitted without HALT/TEXCHK failure.

| r103 farm, Flycast MODELLED, q2–4 mean | Base | Local indexed SLI1 | Direct strips SDS1 |
|---|---:|---:|---:|
| World, microseconds per drawn tick | 9,637 | 9,591 | 11,059 |
| Transformed inputs per drawn tick | 11,328 | 11,328 | 12,406 |
| Heap 4 free, bytes | 3,723,520 | 3,670,688 | 3,594,336 |
| World delta | — | −0.046 ms | +1.422 ms |
| Extra heap use | — | 52,832 B | 129,184 B |

**SLI1 is a wash; SDS1 is rejected. Both remain default off and neither goes
to a console A/B.** The input counts above follow the owner's per-drawn table;
SDS1 has 12,406, not 11,328. These are owner-reported Flycast results, not a new
cloud run or console measurement. Private evidence remains at the owner's
`world2ms/b12old-1024` location. No private files are part of this patch.

The final inbox reply, `8c992120`, confirms that all 27 mip22-rekeyed rooms'
R4ID headers and the r101/r109 R4SG policy fields intentionally bind to the
pre-mip22 policy CRC. The qualified runtime resolves this lineage, while
ordinary offline conversion expects the physical CRC. The owner's
original-policy control makes those values agree. Thus the shipped source
bindings are deliberate; an offline physical-CRC refusal alone does not
establish stale sidecar data.

That reply also reports Build13 split-data admission with `err=0` in both
rooms, unchanged transformed-input and pick counts, and Flycast MODELLED
world costs of 9.637→9.737 ms at the farm and 13.938→14.118 ms at the cross.
The cache effect remains unpriced in Flycast and needs the console pair;
64 remains the meshlet-size default. Build14's UNRUN observer reports zero
samples and `valid=0`, while its hooks cost +1.114 ms world time at the cross
and +0.626 ms at the farm in those owner Flycast runs. This is separate from
the new error-bin core overhead model below. Counter qualification and the
physical-console perturbation remain pending.

## Policy fix: retain strict admission and recover a separate control

`scenery_data_variants.py` formerly reported several R4PW/R4SG header failures
as one `identity/CRC` error. Its new `--policy-diagnostics [0|1]` flag defaults
to zero and adds expected/actual field values. Absence and zero retain the old
errors. Valid outputs are identical with the flag absent, zero or one.

The owner-confirmed policy discrepancy has a specific cause: ordinary Build12
parsing compares R4SG byte 24 with the actual R4PW body CRC, while a qualified
`WORLD_RECT21` runtime may compare it with the certified **original** policy
CRC. This does not justify accepting a remapped policy under Build12's
`WORLD_RECT21=0` recipe. The ordinary converter remains strict, and neither
the runtime provenance helper nor its certificate/origin tables is edited.

`world_policy_provenance.py` reuses those committed records. Its default is
read-only inspection. Explicit `--prepare-original-policy=1 --out NEW_DIR`:

1. Validates genuine package and policy CRCs, extents and supported structure.
2. Requires the exact current runtime certificate, including room, physical
   policy CRC, whole-file FNV, mesh identity, sizes and counts.
3. Restores only the first eight key bytes of each material using the same
   one-step inverse map as the runtime. Unknown keys remain unchanged.
4. Computes the restored body CRC and requires the certified source CRC.
   Every non-key material byte, placement byte and unrelated header byte
   remains exact. Matching historical policy/mesh SHA256 pins are mandatory.
5. Fully validates any supplied source-bound R4SG against that restored
   policy and unchanged geometry, then copies its bytes exactly. A sidecar
   bound only to the remapped physical policy refuses.

The tool never stamps an expected checksum onto incompatible bytes, changes
a certificate, accepts a caller-supplied certificate, or rebinds R4ID/R4TC/PVS
proofs. Existing directories and source inputs are not overwritten. Optional
original-policy bytes must equal the reconstructed result and cannot authorize
an unknown input.

The historical SHA record covers matching r100/r103 source lineages. For r101,
where no original archive SHA is committed, the report explicitly says
“runtime certificate + exact inverse-map restoration; original archive SHA
unavailable.” This can produce a labeled control without claiming archived
byte identity. No actual private r101 recovery has been run here.

The output is a policy file and, when supplied and valid, its unchanged group
file. Original textures and the matching complete DATA/pack/resident stack
remain necessary. It does not recreate or qualify the owner's control disc.
Build11's separate noncanonical-index-placement issue is not changed.
Commands and precise checks are in the
[policy guide](../../tools/cloud/world_policy_fix/policy_README.md).

## Census fix: explain each existing error without hiding it

`WORLD_CENSUS24_ERRORS=1` requires `WORLD_CENSUS24=1`; the new knob defaults
to `0`. It keeps the original aggregate increments and timing rejection
semantics. An error is still an error, and the count is neither suppressed
nor reinterpreted as a bit mask.

There are 32 fixed bins keyed by reason, call site, render path, phase and
wait. Each stores its count and the first tick plus two scalar evidence words.
Further distinct bins accumulate in a visible spill count. Counts plus spill
reconcile with the original aggregate modulo its existing uint32 arithmetic;
wrap is explicitly reported. The original `Snapshot` ABI is unchanged.

Core causes include backwards clocks, unclosed or misordered scopes, depth
overflow, phase totals exceeding wall time and counter saturation. Renderer
guards distinguish incomplete/aborted passes, missing packages/cameras,
projection/depth failures, source/binding/entry rejection, stale deferred
receipts and shell availability/binding/scratch refusals. Branches tagged with
`ErrorDetail::first` preserve that failure's context before later phase
changes. General `ps2_pass` fallback/abort evidence is summarized at the
existing result guard and can carry its outer Selection context; it does not
claim the exact earliest failing inner phase.

The pre-existing guards each retain their original one-fault behavior. A
single failed operation can still be counted by more than one existing guard;
the site field makes those wrapper counts visible. The classification is not
a new count of unique causal incidents. Unclassified no-argument `fault()`
calls remain visible as `unspecified`.

Live bins accumulate directly into the active window. There is no diagnostic
bin clearing, copy or merge on an ordinary error-free tick. Window seal copies
the bounded result; pause, reset, identity change and abandoned partial ticks
follow the original census collection rules. The formatting/logging helper is
kept out of the ordinary finish function's stack frame.

At seal, `WC24E` prints one summary and at most 32 bin rows. It includes the
window sequence, room, total, spill, wrap, reconciliation result, reason/site,
path/phase/wait and first evidence. No per-vertex or per-error serial output is
added. The same evidence is paginated after the ordinary 25 WC24 QA rows;
PM14 rows follow it when enabled. Existing counter ownership is unchanged.

## Verification and cost evidence

The public policy receipt records 146 checks, 48 complete converter-return
comparisons, complete baseline/absent/zero/one CLI file identity, 44 actual
C++ provenance cases, 88 null/short-input checks and 800 actual C++ origin
lookups. Production certificates are exercised for public-data refusals;
positive certificate controls use an explicitly synthetic table with the
unchanged helper. They do not certify a private policy.

The actual-core host gate passes **58 paired OFF/ON comparisons**: 26 core
cases plus three PM14 compositions in each normal and ASan/UBSan mode. Every
declared original `Snapshot` field and aggregate is equal across the pair.
The controls cover bin/spill reconciliation, wrap, first evidence, ownership,
nesting, backwards clocks, phase overrun, abandoned partial ticks, pause,
reset, identity change and successive windows. PM14 keeps its existing
`CensusFault` propagation. Its synthetic counter responses remain SIMULATED.

The renderer annotation gate passes **38 cases in four builds** (OFF/ON,
normal/ASan/UBSan), each sealing an actual 300-draw census window. Actual
source-extracted guards and admission/refusal blocks preserve snapshot
fields, return totals and controlled external-call counts. Enabled runs
assert the reason/site/path/phase and first scalar evidence. Package,
binding, camera and shell-group edges are explicit adapters; geometry,
actual selection and PVR execution are excluded. ASan and UBSan pass;
LeakSanitizer is disabled because process enumeration is unavailable here.

Runtime identity, target costs and reproduction commands are recorded with
the final controls under
[`tools/cloud/world_policy_fix`](../../tools/cloud/world_policy_fix/).
All cycle figures there are **MODELLED** from actual SH4 instructions and
observed byte/line accesses, with deterministic clock/thread adapters. They
are not console timings or a model of real D-cache misses. The cost runner
refuses any accidental path into unpriced formatting.

No new runtime SH4 assembly or game linker changes are introduced. A synthetic
ELF linker script in the test runner only locates the audited instruction
fixture; it is not a game build change. Complete source hashes bind the
receipts to the tested code. Only public/synthetic inputs are committed.

### Complete target translation units

The pinned GCC 15.2.0 / binutils 2.45.1 / newlib 4.6.0 toolchain passes **44
complete preprocessed-source/object byte comparisons** against `dd6b66b9`.
These cover knob absent and zero in production, active census, census+PM14
and standalone-PVR-observer profiles. The same three enabled diagnostic
profiles compile and partially link with all census/PM14 hooks resolved and
exactly one PVR statistics wrapper. Nine invalid knob/dependency settings
refuse. Compiler-emitted census instructions use no FPU registers; external
callees are outside that static audit. No final game executable or disc is
linked by these public controls.

In the ordinary census target profile, enabling diagnostics changes the
compiled object sections as follows. These are object-section extents, not
a final linked-game size prediction.

| Object | Executable bytes OFF → ON | Allocated bytes OFF → ON | Extra zero-fill |
|---|---:|---:|---:|
| `native_static` | 69,672 → 70,556 | 113,267 → 114,151 | 0 |
| `native_ps2_world` | 1,984 → 2,188 | 2,607 → 2,811 | 0 |
| `world_census24` | 5,596 → 7,272 | 9,252 → 13,552 | 1,324 B |

The 1,324 bytes are a 652-byte live bin collection and 672-byte sealed error
snapshot. The original target `Snapshot` stays 852 bytes. Selected static
stack frames are `begin_tick` 340→348 B, `ps2_pass` 8,996→9,032 B,
`re4dc_ps2_mesh_draw` 20→60 B, shell draw 476→516 B and deferred world flush
24→36 B. The separate cold `errors_log` frame is 308 B and is allocated only
when called. These are per-function frames, not whole call-chain maxima.

### Actual instruction traffic and MODELLED cycles

The 24 target cases run both OFF and ON against the same synthetic state,
using the actual census implementation. First/repeated/spill cases check
exact bin bytes and preserved first evidence. Clear controls begin nonzero;
seal controls compare complete metadata and bins. Error-free phase/tick
cases also assert that diagnostic bin storage is not touched. Eighteen
XOR-immediate controls qualify the one additional scalar instruction needed
by this fixture runner; unsupported instructions still refuse.

The table reports OFF→ON. Loads/stores count executed memory instructions;
bytes are load/store byte totals; lines are the union of touched 32-byte
data lines including literals and stack. Cold-I starts an isolated synthetic
ELF with an empty instruction cache. Both cycle models assume a perfect
data cache.

| Probe | Warm cycles | Cold-I cycles | Loads/stores | Bytes read/written | Data lines | Peak fixture stack, B |
|---|---:|---:|---|---|---:|---:|
| Error-free enter/count/leave | 402→424 | 698→723 | 93/22→103/30 | 352/88→392/120 | 21→15 | 24→32 |
| Error-free completed tick | 1,306→1,318 | 1,634→1,647 | 380/212→383/214 | 1,506/845→1,520/853 | 57→56 | 296→308 |
| First typed fault | 68→146 | 133→320 | 16/4→34/18 | 58/16→130/72 | 9→15 | 12→44 |
| Repeat first bin | 68→145 | 133→294 | 16/4→34/12 | 58/16→130/48 | 9→15 | 12→44 |
| Repeat last of 32 bins | 68→424 | 133→573 | 16/4→65/12 | 58/16→254/48 | 9→34 | 12→44 |
| Spill distinct 33rd bin | 68→424 | 133→599 | 16/4→65/12 | 58/16→254/48 | 9→34 | 12→44 |
| Clear active window | 714→718 | 834→876 | 22/406→22/408 | 84/1,594→84/1,602 | 58→61 | 16→12 |

The extra empty/full error seal bookkeeping costs respectively 359/1,019
warm cycles and 482/1,164 cold-I cycles, with 18/188 and 181/348 loads/stores,
70/728 and 722/1,368 bytes, 30/50 lines and a 12-byte peak fixture stack.
Its OFF fixture is a 3-cycle no-op; the complete existing census seal,
formatting and serial writes are not included in those figures. Full reset,
untyped faults and inactive-owner paths are retained in the receipt.

Small line-union reductions in the no-error cases reflect changed synthetic
literal/stack placement. They are not a cache-miss saving: the same probes
actually execute more load/store instructions. There is no diagnostic bin
traffic in those normal core paths. The source-extracted renderer tag costs
are outside this core-only cycle model.

**MODELLED frame scenario:** assume 1,000 enter/count/leave probes, one
completed drawn tick, no skipped ticks, a seal every 300 draws, and a 200 MHz
CPU. Weighting the isolated warm deltas gives **+0.110066 ms** per frame with
no faults. Four repeated faults hitting the last of 32 bins, with a full seal,
give **+0.117197 ms**. The formula is
`(1000*22 + 12 + faults*356 + seal_delta/300) / 200000` milliseconds,
where `seal_delta` is 356 or 1,016. This is an explicit diagnostic-overhead
scenario, not a captured r101 population or a whole-game prediction. Renderer
tags, formatting/serial, hardware timer/IRQ costs, real memory waits and other
game work must be added. Cold-I probe costs are not additive per-hook frame
costs. No world speedup follows from these numbers.

## Owner hand-back

The qualified old-data result already closes the Build12 performance decision.
Use policy inspection or an explicitly prepared original-policy control only
when diagnosing another matched bundle; do not infer that it reconstructs the
qualified disc or revives the rejected layout.

For any future WC24 window with nonzero errors, enable the new diagnostic on
the same census build, collect the corresponding `WC24E` sequence and QA rows,
and repair the actual failing path or asset bundle. Any spill or wrap remains
visible. Retain an ordinary diagnostic-off run for the frame deadline, and do
not subtract these synthetic costs as a universal correction.

The wider 2 ms programme still needs private scene evidence and physical
console qualification. This follow-up makes policy failures and invalid
measurement windows explainable; it does not remove the world workload.
