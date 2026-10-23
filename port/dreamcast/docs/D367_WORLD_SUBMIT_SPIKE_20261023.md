# D367 world submission ownership spike, 2026-10-23

Implemented as an incremental optimization behind a default-off knob. Long warm
batches reduce the measured CPU ownership-boundary cost, while isolated parts
and refusal-heavy sequences cost more. Keep the candidate and its reproducible
evidence for game qualification alongside the larger world-work reductions.

## Question and baseline

Can the existing PS2 world chunk replay save useful SH-4 work by retaining the
TA store-queue mutex across consecutive resident parts? The baseline is
`86c1b91a72a8d6d419cf9c5fa0c335ff3f552a9d`, including the preceding default-off
selection-setup spike. This experiment is independently default-off under
`SCENERY_SUBMIT_BATCH=1`. It does not turn on `SCENERY_SELECT_ONLY`.

The reported r101 world cost motivates the experiment, but no r101 camera,
complete playable disc, or physical-console measurement is available in this
workspace. Target instruction measurements and controlled renderer fixtures
must not be reported as measured frame-rate or r101 gains.

## Existing mechanism and bounded extension

The existing D349 frame owner already has the world header cache, direct TA
begin/end, texture pinning, scratch slab and chunk replay. The optional Leon
native pipe demonstrates retaining SQ ownership across synchronous actor runs.
This experiment extends the world begin/end mechanism; it introduces no new
material cache, package format, room allocation or renderer owner.

A stack token belongs to one `chunk_flush` invocation. Each replay emitter may
borrow it. A completed part retains the physical mutex, while still performing
its logical direct-end accounting immediately and setting `direct_open=false`.
The next compatible cache hit uses the same SQ base address. Each part still
submits its own header and vertices in their original order. Reusing the base
preserves the existing per-part 32,767-vertex address-window limit; no cumulative
SQ pointer is carried through the batch.

This saves ownership work only. MeshDraw preparation, material-key lookup,
resident-entry validation, header generation/copy, UV rules, matrix reload,
transformation, strip walking and per-part accounting still occur. The measured
world-piece setup cost cannot all be credited to this change.

## Contract locked before qualification

- Keep the original world direct-begin body and its existing header cache. Do
  not add a second cache scan to speculate about the next part.
- Keep sky, cull, fog, modifier-volume, texture representation and UV decisions
  per part. Keep every header, including a bound part with zero output vertices.
- Keep empty queued records and their accounting at replay time.
- Release the physical mutex before texture loads, scene/list transitions,
  unsupported callback paths, owner-failure handling, aborts and all replay exits.
- Preserve model-result accounting before direct-end accounting. Do not mark
  the next part submitted until its own header has reached the TA.
- Require the existing direct PS2 chunk path and header-cache mode 1. The first
  spike rejects `PS2_PVS`, `WORLD_SCRATCH` and `TA_GUARD` combinations pending
  separate qualification of their boundaries.
- Preserve absent/explicit-zero program bytes. Do not modify release defaults,
  game state, simulation, visibility decisions, materials or room assets.

## Correctness and build evidence

The complete `native_static.cpp` and `native_ui.cpp` translation units were built
with the real SH-4 GCC 15.2.0 toolchain and their separate Make-expanded public
Test22 profiles. For each translation unit, the parent baseline, absent knob and
explicit zero produced identical preprocessed source and object bytes. Debug
records were omitted from all arms; executable optimization flags were retained.
The compile-only environment uses the repository's exact PVR declaration patches
as a temporary header overlay. It does not qualify a linked KOS library or disc.

| Enabled-profile cost | Baseline | Candidate | Change |
|---|---:|---:|---:|
| `native_static` executable sections | 67,040 B | 67,068 B | +28 B |
| `native_ui` executable sections | 76,614 B | 76,986 B | +372 B |
| Static zero-fill storage, both objects | 169,590 B | 169,590 B | 0 B |
| `ps2_pass` static stack frame | 8,988 B | 8,988 B | 0 B |
| Chunk-flush static stack frame | 848 B | 852 B | +4 B |
| World-begin static stack frame | 384 B | 388 B | +4 B |

These are object sections and individual compiler-reported static stack frames,
not a complete linked image or a worst-case runtime stack/heap budget. There is
no new persistent allocation. The enabled code adds a borrowed pointer to each
emitter; ordinary emitters leave it null.

The source-extracted boundary fixture passed **572 comparisons**: 41 UI sequences
and 245 replay cases, each under ordinary and preflight-diagnostic profiles. It
executes the actual begin/end, emitter bind/end, chunk emit and queue flush bodies
with controlled external texture, owner, stream, SQ and geometry edges. The tests
compare emitted words/order, UV scales and capacity, counters, touches/pins,
refusals, failures and final queue state. They are host state/output controls,
not a full-renderer image or console test.

| Controlled sequence | Baseline lock/unlock pairs | Candidate pairs |
|---|---:|---:|
| Eight warm, different materials | 8 | 1 |
| Eight cold materials | 8 | 8 |
| Eight claimed-source transition parts | 8 | 8 |
| Eight parts with preflight diagnostics | 8 | 8 |
| Full 48-record warm replay | 48 | 1 |
| Full 48-record header-only replay | 48 | 1 |
| All-empty replay | 0 | 0 |
| Three 32,767-vertex parts, each rebased | 3 | 1 |

The matrix includes stale texture keys/addresses/dimensions, RECT21 adaptation
and refusal, cull/fog/sky/MV/UI changes, scene/list/logging boundaries, null
arguments, ordinary wrappers, empty gaps and failures before/after submission.
The owner audit found that a claimed source group's validity predicate may log
inside its walk. Both the emitter and UI entry release an idle token before that
predicate. Failure-after-header controls exercise both source and r11f owners.

The earlier selection/replay fixture still passes its **3,564 comparisons** with
this knob absent. Thirteen actual Make configurations, checked for both affected
translation units, accept absent/zero/one, wire the enabled flag to both units,
and reject invalid values or unsupported combinations.

## Target cost and acceptance

Twenty-one target controls execute compiled world boundary code and the actual
KOS uncontended `sq_lock`, `sq_unlock`, mutex, empty waiter queue and MMU code.
All target output headers and state agree. The table uses the repository's SH-4
pipeline model with perfect instruction/data caches and no external bus events.
Each successful part accounts for 25 vertices, but vertex transformation and
emission are deliberately outside this ownership-boundary trace.

Eight measured begin/end/helper bodies were also compared against the complete
production objects. End/account/close/wrapper sections are byte-identical.
Each begin section differs only in a relocation literal pointing to the same
verified `[0, 2, 3]` cull table. The provenance check normalizes that pointer;
it permits no differing executable instruction bytes.

| Complete controlled boundary sequence | Baseline cycles | Candidate cycles | Candidate minus baseline |
|---|---:|---:|---:|
| One warm part | 1,078 | 1,158 | +80 |
| Two warm parts | 2,121 | 2,050 | -71 |
| Eight warm parts | 8,379 | 7,402 | -977 |
| 48 warm parts | 50,099 | 43,082 | -7,017 |
| 48 warm parts, changing materials | 50,051 | 43,034 | -7,017 |
| 48 cache misses, each refusing the draw | 17,891 | 20,361 | +2,470 |
| 48 alternating hits/refusals | 33,971 | 36,609 | +2,638 |
| 48 frame-not-ready refusals | 5,795 | 7,305 | +1,510 |
| Ordinary non-batched direct end | 184 | 190 | +6 |

The 48-part warm boundary improves **14.0%**, saving 146.2 modeled cycles per part.
Its executed instruction count falls from 46,935 to 40,190. With the model's
instruction cache initially cold once for that complete sequence, the cycle
counts are 51,175 versus 44,286. The two-part case instead regresses slightly in
that cold-cache arm, 3,197 versus 3,254; the amortization threshold depends on
the surrounding instruction-cache state.

The marginal saving for each additional reused boundary is 151 modeled cycles.
If all 616 reported r101 parts qualified, ignoring finite batch ends and caller
overhead, `151 * 616 / 200,000,000` is **0.465 ms**. This is an optimistic
illustration within this CPU model, not measured r101 time or an absolute
hardware upper bound. Added replay/caller work and other direct-end users must
be included in a net game measurement.

A separate review of the actual production `native_static` objects counts
**22 added instructions per successful nonempty replay row, plus seven per
flush**, including delay slots and excluding called UI/KOS/libc bodies. The
row adds four cleared bytes. Empty rows add 13 instructions and do not bind.
The already-bound guard is byte-identical, and `chunk_emit` retains the same
instruction count/control flow; its changed encodings adjust field offsets.
These are explicit disassembly-path counts, not cycles to subtract directly
from the table above. The review's symbol hashes are pinned by
`target_static_review.py` so changed compiler output requires another review.

The main priced configuration is the Make-expanded public Test22 world profile;
its transition-owner predicate is compiled out. The separate host fixture forces
both source/r11f owner paths on to exercise failure boundaries. This does not
price or target-qualify those optional configurations. Controlled cold `load`
edges return refusal; their timings are not real successful texture-load costs.

The SH7091 manual section 4.6.3 specifies that a write to a queue still transferring
waits for that transfer. KOS's `sq_unlock` does not itself flush or wait. Reusing
the original base keeps the existing per-part address and queue-parity pattern.
The existing model explicitly prices STC from SR at two cycles and LDC to SR at
four, matching the instruction timing table; these operations are not generic
one-cycle stand-ins. Uncontended CPU pricing does not model SQ backpressure,
external memory/register-bus delays, DMA,
interrupts, scheduler latency or other threads waiting for SQ. A batch is bounded
by 48 records and 320 picks, not by a fixed wall-clock duration.

The spike is not release acceptance. A positive controlled result still needs
the actual r101 run lengths, hardware frame time, visual/TA comparison, STRICT
gameplay trace and existing low-memory route checks before enabling it.

## Reproduce and retained evidence

The [tool README](../tools/d367/world_submit_spike/README.md) gives the host,
production build, Make wiring, caller review and target-cost commands. The
[aggregate receipt](D367_WORLD_SUBMIT_SPIKE_20261023.json) retains the source and
object hashes, selected static stack frames, all 21 target cases, body-identity
proof, model assumptions, host controls and prior queue-regression result.
Generated objects, binaries and raw traces remain outside Git. No room or game
assets were added or changed.
