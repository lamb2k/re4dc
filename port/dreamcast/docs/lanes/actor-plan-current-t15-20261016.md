# Existing actor plan on the current T15 stack, 2026-10-16

`ACTOR_PLAN=1` was already active before this lane. This audit adds **no runtime
change and no incremental speedup**. The matched current-base experiment found
PLAN1 slower than PLAN0 by **1.905530 ms/frame in the SH-4 console-fit model**.
This does not establish a physical-console result or authorize a default change.
The small reuse mechanism is implemented; a general prepared props/accessory
record is not implemented by it.

## Exact comparison

Source: `3e303c5ecdcd993b14b22d540994708ecdd6a306`, including the prior CPU lane.
This lane uses `/root/probe/codex-actor-t15-20261016/tree`. The source was clean
for all builds and captures. Both arms use T15 data, `benchmark-r101-t12`, the
r101 burning-cross scene, source frames 500..799 sampled every ten frames
(30 samples), `PACE_MODE=off`, full Leon (`LEON_LOD=0`), g70 Ganado level 2,
`ACTOR_ONEPASS=0`, `WORLD_VERT=1 WORLD_VERT_LEVEL=5`, and
`MOVIE_WORLD_ARENA=1 MOVIE_WORLD_ARENA_S30=1`.

The level-5 filename selects the already-approved L2-fixed geometry packaged
contiguously with 4 m batches. It is not a new lower-detail geometry setting.

| Arm | Program | ELF SHA256 | Model cycles / 30 samples | Model ms/frame |
| --- | --- | --- | ---: | ---: |
| PLAN0 | `cxt16a0rW` | `088f26bb0fa22374da3f27de5f01838bc8cbf9ecb934ae24948a5e2e30ffe5cc` | 357,090,632 | 59.515105 |
| PLAN1, existing stack | `cxt16baserW` | `1f98fe56859c114ad09a818dd4b6f33658c42c73d11229186ec5ad9428cef8c6` | 368,523,811 | 61.420635 |

The independently rebuilt PLAN1 `cxt16a1rW` has different non-loadable ELF
metadata but exactly the same loadable bytes and all six overlays as
`cxt16baserW`. Its ELF SHA256 is
`f0b772fe31f5990fd2b9e72cc94709d9880b9ae5699f3efa914056c7ca23c5db`;
the shared loadable-byte SHA256 is
`483424f1b159902a4fa01c6d4556d66974e156b0f6b773077da3f4ad016e0555`.
Build settings differ only in `ACTOR_PLAN`; the two affected compilation units
differ only in `RE4DC_ACTOR_PLAN`. All builds report zero missing bytes.

All 30 matched samples were slower with PLAN1 (median +1.925515 ms, range
+0.693905..+2.557055 ms). All 2,621 payload entries match except the main image
and its six overlays; warp bytes and source-frame sample IDs match. The
Flycast binary, emulator configuration and both log/sampler readers also match
byte for byte. The common
camera, actor, culling and geometry counters agree. Raw diagnostic differences
are six heap readings and five `PS2LEAN dyn_fast` readings: PLAN1 makes three
additional fast negative pointer-hash exits per frame after startup. Those
counter differences are recorded, not hidden as an identical-counter claim.

The model attributes -0.254896 ms to base execution and +0.490394 ms to
instruction misses, +1.807546 ms to demand data misses, and +0.055855 ms to
prefetch waits; the remaining dependency, branch, SQ and uncached terms sum to
-0.193369 ms. Executed instructions fall by approximately 63,184 per sampled
frame. This is a complete-image cost result; it does not isolate an individual
cache-conflict cause. Cache/layout/GPU changes still require the separate
physical-console A/B gate.

## What the existing plan covers

The implementation reuses a 20-byte, single-use Leon bind proof keyed to the
model, transaction, source frame, lifetime and binding revision. Current model,
list, part and role checks remain, with the original bind as fallback. It also
reuses acquisition preflight for an unchanged first-pass subset while the
existing lifetime token remains held. That preflight reuse applies to admitted
owned transactions, including registry plans; the Leon bind token is specific
to Leon. Current workspace, skin and texture checks, scene pins, world
barriers, `one_chunk` qualification, ordered submission and post-submit checks
remain. `ACTOR_PLAN=2` recomputes the original proofs and reports disagreements.

Relevant implementation is in `coarse_actor_owner_leon.inc`,
`coarse_actor_transaction.inc`, and
`platform/include/native_actor_owner_runs.inc`. `ACTOR_PROOF_LEAN`,
`ACTOR_MATERIAL_RECORD` and `ACTOR_BIND_REUSE` were already enabled; their
earlier no-op audit was not repeated. The rejected larger `ACTOR_DRAW_PLAN`
and `ACTOR_ONEPASS` trials were not repeated either.

The current nominal model attributes owned setup at 4.682280 ms for PLAN0 and
4.506562 ms for PLAN1. Leon bind calls fall from two to one per frame
(0.273904 to 0.140640 ms), and preflight calls from 7.733 to 4.367
(0.059066 to 0.034794 ms). These are attribution rows, not an isolated algorithm
saving: completed owned draw counts differ (4.7 versus 4.6 per frame) because
the reconstructed call tree can be interrupted or affected by tail calls.
Do not add nominal components to the console-fit whole-frame result.

The per-part props/accessory path through `re4dc_draw_model_part` is outside
that transaction reuse. It already has `MODEL_DRAW_PLANS=1`, which caches
topology in the existing packet slab, plus the existing position, preparation,
room-strip, slab-latch and stream-fix mechanisms. It is not a per-info material
or descriptor plan. Current nominal per-part setup is 1.535671 ms for PLAN0 and
1.559094 ms for PLAN1, over about 30.2 part calls/frame. This includes mandatory
current lighting, packet/SQ work and per-meshlet bookkeeping. It is not a
1.56 ms removable budget, and it does not justify a new fixed arena under the
measured >=2 ms ceiling rule. A props extension remains separate, unimplemented
work; this audit does not close it.

## Image and heap accounting

| Measurement | PLAN0 | PLAN1 | PLAN1 minus PLAN0 |
| --- | ---: | ---: | ---: |
| Text bytes | 2,711,916 | 2,712,524 | +608 |
| Data bytes | 657,936 | 657,936 | 0 |
| BSS bytes | 922,680 | 922,680 | 0 |
| `_end` | `8c428f58` | `8c4291b8` | +608 |
| Room-entry heap4 free | 7,581,952 | 7,577,856 | -4,096 |
| Room-entry KOS free | 5,608 | 9,096 | +3,488 |
| Heap4 free at source frame 600 | 727,712 | 723,616 | -4,096 |
| Heap4 free at source frame 720 | 726,752 | 722,656 | -4,096 |

The same -4,096-byte heap4 delta appears at all six matched checkpoints:
120, 240, 360, 480, 600 and 720. `ARENA_FIT=1` with the unchanged 196,608-byte
reserve rounds the fitted heap in 4 KiB steps. The additional KOS free bytes are
redistribution across this boundary, not extra memory. The separately
instrumented STRICT pair has +640 text/end bytes and unchanged data/BSS.

## Behavior, route and pressure gates

The current-fixture behavior and bounded pressure checks below pass. These
checks do not turn the unfavorable modeled PLAN1 cost into an adopted speedup.

- PLAN2 current fixture: PASS. 840 bind checks/hits, zero bind disagreements;
  3,000 preflight checks, zero disagreements; TEXCHK and LEON-GC pass.
- Fight PLAN0/1: PASS. 917 STRICT records, MUST-IDENTICAL decisions, no trace
  gaps/errors or NULs. Identical TA contexts include all 300 source frames
  500..799. TEXCHK, LEON-GC and all eight world-file hashes pass; runtime logs
  confirm `WORLDVERT want=5 loaded=5`.
- Full bell PLAN0/1: PASS. 2,002 STRICT records (473 under the existing
  `TRACE_SS_MASK`) and 2,002 MUST-IDENTICAL decision records;
  2,002 matching TA contexts over 2,001 source frames. Both arms complete
  `terminal=1 id=10130 frames=1331/1331`, retire the movie, and CLEAR/DELETE
  `r101s30.evd`. TEXCHK, LEON-GC, world hashes and runtime `loaded=5` pass.
  Both reach controlled source stop tick 2000 with reader exit 0, at 209.52
  seconds for PLAN0 and 210.92 seconds for PLAN1. The 240-second value is a cap,
  not a required minimum after that source stop.
- Door to r103 PLAN0/1: PASS. 2,002 STRICT records (473 under `TRACE_SS_MASK`),
  2,002 MUST-IDENTICAL decision records, no logic gaps or drift, and 1,998
  matching TA contexts through frame 2001. Neither arm emits a TA row at source
  frames 182..184; there are no unmatched contexts within the shared span.
  Both enter r103 and report `loadind: room 103 shown`, then reach controlled
  source stop 2000. TEXCHK, LEON-GC, world hashes and runtime `loaded=5` pass.
- 48 KiB pressure matrix: PASS, all ten runs across five segments, each
  contiguous and fragmented. Global minimum observed KOS headroom is
  7,264 bytes while holding the full 49,152 bytes.

| Pressure segment | Endpoint | Contiguous minimum KOS headroom | Fragmented minimum KOS headroom | Result |
| --- | --- | ---: | ---: | --- |
| Fight | r101 alert | 7,352 B | 7,264 B | PASS |
| Radio call | r100 subscreen open | 36,872 B | 36,768 B | PASS |
| Door | r103 displayed | 13,952 B | 13,864 B | PASS |
| Leave to r100 | r100 entry after r101 | 7,552 B | 7,464 B | PASS |
| Leave to r103 | r103 entry after r101 | 7,552 B | 7,464 B | PASS |

Each pressure run must hold all 49,152 requested bytes, reach its endpoint,
retain at least 4,096 bytes of observed KOS headroom, and pass the fixture,
TEXCHK, LEON-GC and fatal/NUL checks. These are headroom/behavior checks, not
performance measurements.

Movie TA rows are compared by `(source frame, present mode)` because playback
freezes the source frame and repeats presentation quads. Every repeated hash
and its count is retained; any different hash within one context fails. Equal
quad hashes do not certify decoded picture contents or presentation cadence,
and host repetition counts are reported separately.
The bell and door pairs each contain 473 masked logic records that omit swapped
subscreen-backed actor,
player and object fields under `TRACE_SS_MASK`; globals and matching mask state
still compare. They are not 2,002 unmasked state comparisons. Full movie
completion and event-retirement markers are checked independently.
Both bell arms report 1,305 pictures shown, 26 dropped, two late and one audio
underrun in this Flycast JIT run. These values are retained as limits on the
capture; they are not console movie-quality or cadence acceptance.

The first PLAN2 capture used a Windows UNC symlink that silently omitted the
world overrides. Its proof rows are not current-fixture acceptance; the run is
retained as `plan2-diagnostic` with a rejected-wrong-world-fixture status. The
accepted `plan2-current` uses the actual assets directory, eight prelaunch
payload hash checks, and runtime `loaded=5` verification. The cost captures
used WSL fixture paths and were unaffected.

The first bell-1 run was cancelled during the coordinator hold handoff after
its child outlived the wrapper. It is retained as `cancelled-plan-bell-1`, with
the owned process interval 14:56:33.526515..14:57:42.218053 UTC and explicit
rejection. Accepted full-bell paths are `plan-bell-full-0` and `plan-bell-full-1`. The private
runner now rejects early emulator exits even when the underlying runner labels
them completed. Its initial wall-duration check also rejected normal stop-tick
completion, so both full-bell stages were finalized after their children exited
and all source-stop/movie checks passed. The original reports are unchanged and
each has a finalization note. No rejected or cancelled run is used for acceptance.

These are Flycast/model gates. Physical-console timing, cache/DMA acceptance,
full H2 routing, decoded movie quality and console movie cadence remain
separate gates. No package, SD card, release or default was changed.

The pressure radio-call segment starts in r100 and stops at subscreen open,
where the call takes its memory; it does not prove call closure. It checks all
staged r101 world-file hashes, but does not require a runtime r101 load. The
other four pressure segments must load the exact r101 world. The door segment
must display r103; each leave segment must enter its destination after r101.

## Reproduction and evidence

Private evidence root:
`C:\Flycast-Evidence\re4-dreamcast\codex-actor-t15-20261016`.
The inherited PLAN1 cost evidence is
`C:\Flycast-Evidence\re4-dreamcast\codex-cpu-t15-20261016\hwmodel-cxt16base-cross`.
The matching PLAN0 cost capture is `hwmodel-cxt16a0-cross`. Raw instruction
traces are retained. Machine-readable summaries are `build-identity.json`,
`current-control-audit.json`, `current-model-comparison.json`,
`current-memory-comparison.json`, `actor-plan-scope.json`,
`plan2-current-summary.json`, and the final route/pressure summaries.

The exact build/capture/check scripts and command outputs are retained under
`C:\Game Dev\Emulators\_codex_actor_t15_20261016`. Builds use the existing
`tools/d367/actorplan/build.sh` and its build-slot wrapper, with isolated
`ROUTE_OUT_ROOT`, `ROUTE_PROGRAMS_DIR`, registry and logs. The private
`build-acceptance.sh` has cost, diagnostic, strict and squeeze modes. The common
extra settings are:

```sh
R=/root/probe/codex-actor-t15-20261016
export T=$R/tree K=$R/logs
export ROUTE_OUT_ROOT=$R/builds ROUTE_PROGRAMS_DIR=$R/programs
export ROUTE_PROGRAMS_JSON=$R/programs.json ROUTE_REGISTRY_LOCK=$R/programs.lock
export XON='PACE_MODE=off PC_SAMPLER_BYTES=8192 MOVIE_WORLD_ARENA=1 MOVIE_WORLD_ARENA_S30=1'
for n in 0 1; do
  bash "$T/port/dreamcast/tools/d367/actorplan/build.sh" cxt16a$n rW \
    ACTOR_PLAN=$n ACTOR_ONEPASS=0 WORLD_VERT=1 WORLD_VERT_LEVEL=5
done
```

Use `rT` with `MCHECK_LEONGC=1 TEX_CHECK=2 TA_HASH=2` for the matched STRICT
pair. PLAN2 uses `MCHECK_LEONGC=1 TEX_CHECK=2`. The pressure arm also adds
`KOS_WATCH=1 KOS_SQUEEZE=1 WARP_JUMP=1`. Capture scripts stage T15 data, the
matching executable and all six overlays, the exact warp, and all eight world
files; stage manifests must pass before capture. Fight uses a 90-second cap,
door 180 seconds, and full bell 240 seconds with trigger frame 240 and no skip
pad. The controlled source stop is tick 2000. Pressure pairs are staggered,
with no more than two owned children and unchanged global limits. Existing
queue limits and applicable trace guards are unchanged. Captures still require
the coordinator's explicit emulator window.
