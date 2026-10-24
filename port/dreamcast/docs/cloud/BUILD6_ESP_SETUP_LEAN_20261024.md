# Build 6: effect sprite setup

Branch `codex/esp-setup-lean-20261024`, based on
`a5e972e44096410253ad93164b84d92e3c22655a`. `ESP_SETUP_LEAN=0` by default.
The current public Make recipe is the baseline, including `FX_TRIM=1`, the
three accepted world setup options and the chapter-two recipe additions.
Both `FX_LEVEL=0` and `FX_LEVEL=3` are checked. Level 3 uses room level zero
plus the runtime Essential flag; it is not a different room-thinning level.

## Changes and contracts

1. **Share a header only between consecutive compatible queued sprites.**
   The existing texture/header cache already avoids compilation on a hit.
   This change also avoids copying and sending a redundant 32-byte header.
   Texture format/dimensions/address, blend, screen/depth/fog mode **and ARGB**
   must match. The cached header must belong to the actual preceding queued
   sprite. Ordinary, PS2 haze and stage-one batch producers participate;
   unassociated calls such as RTT capture break the association.
2. **Stop unconditional Essential cuts before matrix construction and
   projection.** Projection/animation cache updates and `ChannelSet()` still
   run. Layer limits still run at the original late point, after texture and
   geometry eligibility. Both original late frame stamps must already match,
   so the first eligible sprite in a frame keeps the original path. This
   preserves bucket resets through frame-counter rewinds and mode toggles.

The queued packet reservation remains 128 bytes: one node line and the
original 96-byte packet space. A continuation leaves the header slot untouched
and sends its original 64-byte body. It retains the same admission checks,
sprite cap, FIFO order, per-sprite screen overlay depth and number of send
calls. Queue reset forgets header ownership, including resets within a frame.
Neither source pointers nor textures acquire a new lifetime.

Header sharing is disabled with `TA_GUARD`, `TA_HASH`, `TA_BIN_DIAG` or
`TA_MATERIAL_DIAG`: their existing full-packet accounting remains exact.
The early Essential shortcut is disabled with `FX_TRIM_LOG`, `ESP_CENSUS` or
a defined `MIST_CUT`. It always leaves haze IDs 0x15/0x48, torch ID 0x0e,
temporary torch-glow draws and screen sprites on the original path. Hardware
fog feeds, torch/haze logs, RNG, motion, generators and effect-pool admission
are unchanged.

### What is exact

With header sharing active, the raw TA byte stream deliberately has fewer
repeated headers. The comparison contract is the ordered sequence of
**effective complete 32-byte header plus 64-byte sprite body**. Those words
and their order are unchanged. It is not a claim of literal byte-stream
identity when enabled. With the knob absent or zero, the complete source
preprocessing and raw object files must match the base.

The hardware permits this encoding. Sega's *Dreamcast/Dev.Box System
Architecture*, update 1999-09-03, §3.7.6.3, page 214, explicitly shows one
sprite global parameter followed by three independent textured sprite
parameters. §3.7.4.2, page 194, places packed ARGB in the sprite global
parameter. [Public manual](https://segaxtreme.net/resources/dreamcast-dev-box-system-architecture.184/download),
SHA-256 `e38df20df0a007fb6e25052b58e325852b05b841bb7d62f0459d28d2f9114ee6`.
No new runtime SH-4 assembly, runtime linker change or data-format change is used.

## Data traffic

| Queued sprite | Node lines | Packet lines written/read | TA bytes | Reservation |
|---|---:|---:|---:|---:|
| Original/full packet | 1 | 3 | 96 | 128 bytes |
| Matching continuation | 1 | 2 | 64 | 128 bytes |

Thus each continuation eliminates one distinct queue-data line, its header
stores, its drain reads and 32 bytes of TA input. It does not shrink the
queue allocation. The provenance and material-key checks add scalar traffic;
the compiled measurements below include that overhead. Demand lines are
architectural addresses touched, not measured cache misses.

## Measured compiled phases and limits

The target model uses perfect D-cache, no DMA contention and zero SQ transfer
cost. Warm/cold figures refer to I-cache state only. These are compiled
**phases**, not the entire effect tick or sprite emitter. Console benefit from
the eliminated demand line requires the local A/B gate.

`fx_packet`, including real texture-package access and the pinned KOS header
compiler, has identical results at both FX levels:

The KOS hardware-mode query is a constant retail-mode test seam; BIOS query
cost is excluded equally from both arms. Assertion failure stops the fixture.

| Packet case | Warm cycles, OFF → ON | Cold-I cycles, OFF → ON |
|---|---:|---:|
| Matching continuation | 341 → 308 | 669 → 618 |
| ARGB changes | 341 → 370 | 669 → 745 |
| Different preceding node | 341 → 368 | 669 → 757 |
| Queue head, material cache warm | 341 → 366 | 669 → 757 |
| Direct/unassociated packet | 341 → 361 | 669 → 753 |
| Material-key miss | 963 → 989 | 1,589 → 1,677 |

For the matching continuation, the complete sampled function changes:

| Architectural demand metric | OFF | ON |
|---|---:|---:|
| Load / store instructions | 78 / 37 | 74 / 32 |
| Bytes loaded / stored | 294 / 148 | 278 / 128 |
| Distinct 32-byte lines | 22 | 20 |
| Demand line visits | 115 | 106 |
| Repeated visits beyond first touch | 93 | 86 |

These totals include stack and PC-relative literal loads, not just packet
storage. A five-argument prototype touched 24 lines despite saving a packet
line. The retained four-argument form removes a stack argument and the
redundant predecessor-node read: allocations are monotonic until reset, and
reset clears ownership. The preceding node is never dereferenced to prove
what the cached producer identity already establishes. Counts depend on the
fixture's documented alignment/link layout; they are not DRAM byte counts.

The second target fixture begins **after `ChannelSet()`** and ends at entry
to `EspSpriteEmit()`. It executes the production scalar matrix-setup source
and filter. Four matrix routines and the emitter are explicit return seams:
their arithmetic, data accesses and projection/texture work are excluded.

| Common billboard setup phase | Warm cycles, OFF → ON | Cold-I cycles, OFF → ON |
|---|---:|---:|
| FX0, Essential disabled | 144 → 146 | 312 → 332 |
| FX3, primed unconditional cut | 144 → 92 | 312 → 225 |
| FX3, primed keep class | 144 → 196 | 312 → 419 |
| FX3, stamps not yet current | 144 → 208 | 312 → 455 |

The primed cut changes loads/stores **44/22 → 28/6**, bytes **143/88 → 86/24**,
line visits **66 → 34**, and repeated visits **54 → 22**. Its sampled distinct
line footprint stays **12 → 12**; effect-object lines fall **5 → 2**, while
classification reads other lines. The FX0 phase touches **12 → 13** lines,
and the primed keep phase **12 → 18**. Do not describe every early-filter call
as a data-line reduction. A successful cut also eliminates all four matrix
edges and entry to the emitter, whose costs this partial fixture does not
price. Kept sprites pay the checks.

All six packet cases compare equal effective TA words across OFF/ON and both
FX levels using the actual compiled KOS routines. Decoder controls cover
the extra unsigned-dimension conversion and memory-observer instructions
used by those samples, including known coordinates, depth and packed UVs.

### MODELLED whole-frame contribution from the priced phases

No r101 effect census was supplied. The following **hypothetical per-frame
mixes** apply the measured phase costs at 200 MHz; they are not r101 results.
Each assumes a warm material cache, one queue-head packet, the stated number
of matching continuations and ARGB changes for the remaining packets.
For the FX3 mixes with early cuts, one additional cut first takes the full
unprimed path and is rejected late; it produces no packet. The no-cut mix
contains keep classes with the class table already initialized. Matrix math
and emitter work eliminated by a cut are valued at **zero** here, since
they were outside the phase model. Queue traversal/drain dispatch, including
the new body-tag branch, D-cache misses and TA transfer time are also
unpriced. This is a contribution to a frame model, not a closed prediction
of the entire frame.

| Assumed frame | Warm model change |
|---|---:|
| FX0: 64 setup calls, 64 packets, 48 continuations | −0.00498 ms |
| FX3: 64 setup calls, 48 early + 1 late cut, 15 packets, 12 continuations | −0.009825 ms |
| FX3: 64 setup calls, 24 early + 1 late cut, 39 packets, 30 continuations | +0.000555 ms |
| FX3: 64 setup calls, no cuts, 64 packets, 48 continuations | +0.01102 ms |

Negative is less time. These figures expose the checks' cost when the option
does little. Add the unpriced saved matrix/emitter work for each actual cut
before interpreting a full-frame gain. Even with no cuts, each successful
header continuation still removes one queue line and 32 TA bytes; whether
that offsets extra checks on hardware is the local A/B question. World counts
of 87/50 parts are deliberately not used as sprite counts.
The isolated cold-I prices above are not multiplied into these frame figures:
doing so would assume the entire instruction cache becomes cold before every
sprite, which is not established by the available evidence.

## Size, stack and knob-off identity

Complete Make-derived translation units at both FX levels give the same
deltas:

| Object | Executable bytes, OFF → ON | Change |
|---|---:|---:|
| `esp_sub.o` | 38,496 → 38,664 | +168 |
| `native_ui.o` | 77,486 → 77,638 | +152 |
| `esp.o` / `esp_app.o` | 5,560 / 3,208, unchanged | 0 |

Total **+320 executable bytes, +8 initialized data bytes, 0 read-only/BSS
bytes**. These are object-section totals, not a final linked image.

| Compiler-reported stack frame | OFF → ON |
|---|---:|
| `EspCommonTrans` split body | 408 → 404 bytes |
| `EspCommonTrans` wrapper | 0 → 0 |
| `fx_packet` | 148 → 156 |
| `re4dc_effect_sprite` | 788 → 788 |
| Translucent drain | 836 → 836 |

Sampled nested packet peaks are 160 → 168 bytes for the material-cache hit
and 188 → 196 for its miss. Those are local call chains, not total game-task
stack high-water marks.

An independent archive of the exact base is compiled against the same public
Make settings. **32 comparisons pass**: four complete translation units ×
two FX levels × absent/explicit-zero × preprocessed source/raw object.
The explicit-zero compilation also defines `RE4DC_ESP_SETUP_LEAN=0` directly.
Preprocessing uses `-E -P`; debug information is omitted consistently.
Make flags/generated headers are identical with the knob off. Enabling it
adds only the target-specific define; eight further comparisons confirm
that `esp.o` and `esp_app.o` remain identical when enabled.

Four supplemental objects compile: the TA-hash/trim-log/census fallback and
the common-haze/RTT composition, each for `esp_sub` and `native_ui`. The
current recipe rejects certain guard/bin combinations because of its existing
headroom/resolution contracts; these are not disguised as valid release
builds. Their individual fallback branches are covered by the host tests.

Reproduction entry points and input hashes are in the
[build receipt](../../tools/d367/esp_setup_lean/build_receipt.json) and
[target receipt](../../tools/d367/esp_setup_lean/target_receipt.json).
Use `build_controls.py` for the independent archive/identity gate,
`measure_target.py build` then `run` for target phases, and
`target_controls.py` for decoder/known-packet controls. All take explicit
output/toolchain/SDK locations and need no game data.

## Correctness evidence

The production-extracted host fixtures pass ASan and UBSan at both requested
FX levels. Each native profile compares 378 observations and 349 emitted
sprites, including FIFO order, queue reservations/admission, counters, spill
failure, cap limits, aborts, screen-depth progression, texture/material
changes and all three queue producers. The enabled fixture has 166 matching
continuations and sends 5,312 fewer bytes; these synthetic coverage counts
are not a game population or forecast. The effective header/body trace is
identical (`b10da06ff29676ee68c373adce593921b6da9e0f0792ddd34e08e28670e51d49`).

Each Essential profile compares 1,054,827 observations across owner/texture
classes, protected fog/torch paths, screens, downstream rejects, layer-bucket
collisions and overflow, frame rewinds/wrap and runtime mode changes. Survivor
traces match. All four TA fallback controls and all three early-filter
fallback controls match their original paths. Five deliberate defects are
detected: missing color identity, missing predecessor identity, missing
queue-reset invalidation, missing frame-stamp gates and a rejected keep class.

These tests extract the changed production code; they do not reproduce its
selection algorithm in a second implementation. Texture resolution, PVR
header compilation and stream transport are explicit host shims. The early
filter suite controls the unchanged common-transform prefix and downstream
projection/admission boundaries; fog/mist/torch observations are seam
counters. They do not constitute a whole-emitter floating-point or gameplay
proof. The SH-4 packet samples separately use the actual KOS compiler.

See [runtime receipt](../../tools/d367/esp_setup_lean/runtime_receipt.json).
The final queue and Essential checks bind to the current source. A revision
that changed only one side reused the other side's results only after exact
dependency/profile hashes matched; all affected cases and negative controls
were rerun. A fresh run is supported by
`tools/d367/esp_setup_lean/check_runtime.py` with the two generated public
profiles. LeakSanitizer is excluded because sandbox `/proc` inspection is
unavailable; address/undefined-behavior sanitizers ran.

## Choices rejected

The baseline already caches compiled sprite headers, texture resolution and
the common OT projection/animation setup, and suppresses unused GX calls.
Those are not credited again here. `esp_app.cpp` contains application glue,
not a second repeated sprite setup loop to remove.

A camera-direction normalization memo was prototyped and removed. Its input
was already on the current stack; checking and reading a persistent memo
added a data line and copies. It would also require a floating-point control
mode invariant. A full camera/parent matrix memo would compare 24 float
inputs per use. A frame-only projection or viewport cache is invalid because
OT callbacks can change them within one frame, and viewport jitter can change
between renders. These caches were not retained merely for an instruction
saving. The accepted changes remove work and data transfers directly.

## Local acceptance and Build 5 context

No game data, Flycast run, console run, full link or disc was used here.
Object deltas do not establish the final linker/arena memory margin.
The local look/logic and hardware gates remain necessary before enabling the
knob. Sprite populations and identical-header run lengths at r101 have not
been supplied; world-part counts (87/50) are not sprite counts.

This base already contains the coordinator's Build 5 (`82d5f827`). It is
left untouched. The separately published `codex/world-emit-prefetch-20261023`
candidate has a narrower partial-gather assumption and should be reviewed
as an alternative, not stacked over the landed implementation. This build
does not depend on that candidate.
