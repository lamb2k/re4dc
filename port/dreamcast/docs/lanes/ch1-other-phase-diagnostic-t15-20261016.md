# Test15 OTHER ownership diagnostic — 2026-10-16

`OTHER_PROFILE=0` is the default. This is an ownership diagnostic, not an accepted
runtime optimization or a console performance result. The disabled loadable image
is byte-identical to the original forced-skip arm. The enabled build retains the
same Test15 L2 world geometry (WORLD_VERT_LEVEL=5 package), g70 Ganados, full PS2
Leon, actor plan, input script and 43-sample frame window 500:799:7.

Runtime source base: `3e303c5e`; host-accounting prerequisite: `39c82e3a`.
Arms: `cxoth0rW` disabled and `cxoth1rW` enabled. Matched settings include
`ACTOR_PLAN=1 ACTOR_ONEPASS=0 WORLD_VERT=1 WORLD_VERT_LEVEL=5 PACE_FORCE=2
PACE_MODE=fast PC_SAMPLER_BYTES=8192 MOVIE_WORLD_ARENA=1
MOVIE_WORLD_ARENA_S30=1`; complete make settings are preserved with each build.

## Phase contract

Markers copy the authoritative BENCH_PH boundaries from `76f40d95`, without its
unrelated benchmark or pacing changes: 0 main TaskScheduler logic; 1 both actor
preparation regions; 2 coarse actor draw and EmMgr-member ModelRender calls; 3
coarse world and scroll OT; 4 residual OTHER; 5 tail/wait after DRAW REMAIN.
The guarded two-snapshot EmMgr membership check compares stored addresses by
value, so Render never dereferences the prior tick's alive list. Snapshot and
membership work is bracketed separately. Phase 6 contains those brackets and
the marker NOP instructions. It is not a production phase.

Each raw trace begins at the Frame_cnt update in phase4, immediately before the
phase0 marker. Host attribution resets to phase4 with empty diagnostic/actor
stacks at that trace boundary. All samples contain one phase0 and one phase5
marker, and end in phase4 with balanced stacks and no marker errors. Phase4 is set again
after pace_begin in the next main iteration. Function self charges retain the
phase of the charged instruction, including deferred branch/memory charges.
Interrupt and KOS-thread charges retain the phase they interrupt, matching the
wall-clock phase timer's ownership semantics.

The function map excludes inline marker aliases. The full ordered trace replay
retains the instruction model's state across samples. The exporter is qualified
against the original simulator with identical frame, per-PC and call-tree outputs.
Every benchmark phase/function charge reconciles exactly with per-frame self cost.

## Diagnostic results

All values below are nominal instrumented-model milliseconds. The image groups
are the images prepared after Frame_cnt and rendered next; they are not physical
draw/skip iterations. The pair column adds means of distinct sampled groups, not
adjacent measured pictures. No value is scaled to the historical 15.8 ms console
OTHER result or compared as an optimization gain.

| Phase | Drawn-image mean | Dropped-image mean | Sum of group means |
|---|---:|---:|---:|
| logic | 14.718020 | 14.111553 | 28.829572 |
| actor preparation | 1.659083 | 0.042898 | 1.701982 |
| actor draw | 13.923759 | 0.000000 | 13.923759 |
| world draw | 13.838225 | 0.000000 | 13.838225 |
| OTHER | 9.701346 | 1.154459 | 10.855806 |
| wait tail | 14.959861 | 5.786645 | 20.746506 |
| instrumentation | 0.083624 | 0.011549 | 0.095172 |

Largest nonoverlapping OTHER function self costs in the sum of group means:

| Function | Nominal self ms |
|---|---:|
| `EspCommonTrans.part.0` | 0.552417 |
| `Ps2fxClass(cEsp*)` | 0.482155 |
| `EspTrans` | 0.400667 |
| `re4dc_actor_submit` | 0.276643 |
| `re4dc_prepare_model_assets` | 0.260996 |
| `(anonymous namespace)::resolve(Re4dcUiImage const&, Re4dcModelPart const*, bool)` | 0.228891 |
| `clearOtWork` | 0.225021 |
| `re4dc_effect_sprite` | 0.217999 |
| `idSysMove02` | 0.206725 |
| `re4dc_line_leaf2` | 0.199726 |
| `re4dc_avk_pos_skin_s16` | 0.180146 |
| `ExecOt` | 0.168498 |
| `idSysMove03` | 0.166694 |
| `re4dc_draw_id_quad` | 0.162991 |
| `ModelRender(cModel*)` | 0.156654 |

Heuristic implementation-family totals within OTHER (exact function ownership does not imply every semantic family is known):

| Family | Nominal self ms |
|---|---:|
| actor submit | 2.541984 |
| effects setup+submit | 2.165238 |
| shared image and material helpers | 0.917124 |
| unclassified | 0.774582 |
| effects update | 0.706077 |
| ordering tables and primitive allocation | 0.500995 |
| collision | 0.441554 |
| shared copies and clears | 0.438673 |
| kos/sound/idle | 0.432031 |
| shared math and formatting | 0.339582 |
| skinning | 0.275347 |
| world submit | 0.238612 |
| UI submission and bridge | 0.212766 |
| packet setup and submit | 0.171495 |
| PVR and store queue helpers | 0.150381 |
| fog and haze | 0.140492 |
| GX state and command stubs | 0.133222 |
| KOS scheduling and synchronization | 0.077711 |
| player/scene/other logic | 0.057407 |
| interrupts and device service | 0.055651 |
| frame scheduling self | 0.047286 |
| audio | 0.033828 |
| pacing, retrace and idle routines | 0.003237 |
| motion/animation | 0.000530 |

Instrumentation changes instruction placement, cache behavior and some stack and
register use. Bracketed diagnostic work is identified, but subtracting it does
not reconstruct production timing. No savings claim follows from these rows.
Shared copies, fog, packet and UI helpers are assigned only their self charges
inside phase4; their costs in other phases remain with those owners.
Phase2 follows EmMgr membership, so non-EmMgr ModelRender paths and Render_before
asset work legitimately remain OTHER. Implementation-family labels such as
`actor submit` describe shared model code, not benchmark phase ownership.
This accounting did not establish a new exact repeated-work optimization for
adoption; existing rejected UI/OT and store-queue/cache experiments stay closed.

## Build and scene checks

Disabled loadable SHA256: `f5d8e2570bd52e03b1de8484f0133b398aafb0a29fe72fb27b21329bc44964da`. Enabled ELF SHA256: `d1b8cffcf52c31d81466293a3f0cae10d94803ee7c8a75998416091aed03fd59`.

Enabled image/text +896 bytes, BSS +2080 bytes, data unchanged; `_end` `8c429c38` (+2976 bytes). No runtime allocation was added.

The payload manifest has 2621 files; only 1ST_READ.BIN and six rebuilt overlay payloads differ. Warp bytes, WORLDVERT and Ganado asset identity match. 29/32 complete matching-frame counter rows match after separating heap and Vblank values. The remaining three rows differ only in PS2LEAN dyn_fast: +660/+2100/+3540 at frames 240/360/480, exactly 12 extra negative-filter hits per presented image. Camera, actor, geometry and native input/emitted counts match.

The existing dyn_fast counter records the 64-bit address-hash filter in native_static.cpp:3824/5224, not geometry emission. Its changed hit count is consistent with the diagnostic heap-address shift. The counter difference is retained; full counter identity and production timing equivalence are not claimed.

At room entry, KOS free is 9384 -> 6408 bytes (-2976), with used/break unchanged. Heap4 start/end both move +2976 bytes; total 7601952 and free 7577856 bytes are unchanged. KOS largest free block is unavailable in this fixture's logs; VRAM/AICA largest values are not substitutes. Exact ranges and all allocator rows are preserved in JSON.

| Heap free sample | Reference bytes | Diagnostic bytes | Delta |
|---|---:|---:|---:|
| native model DIAGNOSTIC: frame=120 | 4969504 | 4969504 | 0 |
| native model DIAGNOSTIC: frame=240 | 720000 | 720000 | 0 |
| native model DIAGNOSTIC: frame=360 | 723808 | 723808 | 0 |
| native model DIAGNOSTIC: frame=480 | 722656 | 722656 | 0 |

These scene checks establish matching capture provenance, not a full STRICT gate
or physical-console acceptance. The production arm is protected by exact disabled
image identity. No publishing, release, SD copy, residency or geometry change.

## Evidence and reproduction

Full result: `/root/probe/codex-other-t15-20261016/audit/profile-result.json`.
Raw trace: `C:/Flycast-Evidence/re4-dreamcast/codex-other-t15-20261016/hwmodel-cxoth1-cross`.
Builds, marker disassembly, payload/counter audit and model qualification are retained
under the isolated lane's `audit` directory. `tools/d367/other/replay.py
--benchmark-phases` resolves markers from the exact ELF; `bench_phases.py` produces
the phase/function accounting. The companion JSON preserves the exact results.
