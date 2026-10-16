# Chapter 1 render POC, 2026-10-15

> Current snapshot: [physical-test handover, 2026-10-16 UTC](ch1-physical-validation-20261016.md). The final combined image saves 1.268 ms in the model; earlier image measurements below remain historical evidence.

## Result and scope

The isolated r101 POC combines a small, same-call actor preparation change with
the approved L2-fixed PS2 scenery, contiguous meshlet vertex storage and
conservative spatial batching. On the matched burning-cross benchmark, the
SH-4 **console-fit MODELLED** frame cost is **65.853 -> 61.352 ms** (-4.501 ms,
6.8%). This is neither a physical Dreamcast measurement nor a 30 fps result.
The bounded position/light fusion experiment was exact but slower and stays off.

Worktree `/root/probe/codex-ch1-render-20261015/tree`, branch
`codex/ch1-render-poc-20261015`. Builds, programs, assets and audit files are
outside the checkout in `/root/probe/codex-ch1-render-20261015/`.
Evidence is local at
`C:\Flycast-Evidence\re4-dreamcast\codex-ch1-render-20261015` (called E below).
Private assets, captures, extracted code and discs are not committed or uploaded.
All three new knobs default to zero. No release recipe is changed.

## Base and dependency choices

- Base: actorplan `a4d28b22c78156cfffee796d49ec6782ba3f31b4`, whose parent
  `cb4e24c6` already contains the T15 recipe and KOS fixes used by this experiment.
  The later consolidated handover's `c5ef4ade` adds pruning tools; those are
  unrelated to this POC. The shared checkout and other lanes remain untouched.
- Worldvert `713f931973ab6fac1ed70db5629840a90d56760f` branches from test13
  `1c79d543`. Import only its open-time `WORLD_VERT` loader and required converter
  helpers (`mesh_lod`, `ps2_world_far_lod`, `ps2_world_vert_ladder`, worldlod walk).
  The far-distance runtime policy and in-place runtime level swap are excluded.
- SH4ZAM-adopt `4d783211af833842baadb387d6b1c4551bc17967` shares `e2048df6`
  with actorplan. Its additional experiments are not required; retain the
  already-enabled native kernels and current ownership. In particular, do not
  reintroduce the closed SH4ZAM skinning or failed large Leon plan experiments.
- The consolidated handover identified
  `C:\Game Dev\Emulators\flycast-console`, verified at `41905914`, and the
  corresponding `flycast-console-bin` executable. It is for console-style
  crash reproduction, not timing. The measurements here use hwmodel; the
  correctness runs use the existing JIT Flycast, plus the alignment interpreter.

## Identical-switch investigation

The original ap0rW and ap1rW are both **on**: `build-r21.sh` sets
`ACTOR_PROOF_LEAN=1 ACTOR_MATERIAL_RECORD=1 ACTOR_BIND_REUSE=1`.
Resolved make values and compiler command lines agree. Replaying the compiler
commands with `-E` finds the enabled guards (`lean_serial`, Ganado bind reuse);
affected object disassembly, linked loadable images and staged scrambled
executables confirm the same path. ELF file hashes differ because of debug
paths, while `objcopy -O binary -R .stack` images are identical. No compiler,
linker or runtime path repair was warranted.

Fresh explicit off/on builds prove the difference:

| Build | Three switches | Loadable image SHA256 |
|---|---|---|
| cxas-offrW | 0/0/0 | b615f02fb67ee4e5f9f2e3a7a102e28df683599ab2959564c2da1ddcba4a4731 |
| cxas-onrW | 1/1/1 | d9cad4f66d813eb2999b46b58390db0bd755504fbc7856c71c9cfec87ef99d5c |

The on image exactly reproduces the two historical images. Historical staged
1ST_READ files both hash to
`78a71aeb3c6a304a00dede1b4f7bf186647310d7762fcb701287b848ae0eb127`.
The local audit retains preprocessing, compiler commands, disassembly and
ELF-to-staged-image checks. `tools/d367/actorplan/verify_pair.py` now rejects
identical resolved settings or loadable images; the historical pair fails and
the fresh pair passes. These existing switches' benefit is already in the
current baseline and must not be counted again as a new POC gain.

## Runtime and asset changes

`ACTOR_PLAN=1` retains a 20-byte, single-use Leon bind token from plan creation
to palette construction. Model identity, transaction, tick, binding revision
and lifetime guards must still agree. Otherwise it runs the original bind.
It also reuses the all-runs preflight performed during this same acquisition
for the unchanged first-submission subset while `ACTOR_PROOF_LEAN`'s lifetime
guard holds. Later OT passes still prove their state. Texture leases and pins,
stream checks, world transparency barriers, kernel qualification, clipping,
shared vertex caches and SQ ownership remain in place. There is no persistent
second plan, new arena, pose reuse across frames or source-state mutation.
`ACTOR_PLAN=2` executes the original checks as a diagnostic reference.

`ACTOR_ONEPASS=1` is a blocked driver around the existing AVK position and
lighting kernels, with 32 vertices per block. It preserves indexed reuse and
does not expand vertices into strip order. `=2` compares positions, UVs, colour,
outcodes and masks against the original passes. This bounded experiment does
not implement a new fused arithmetic kernel. Extra matrix/kernel setup and
lighting of subsequently culled meshlets can outweigh cache locality; the
measured result is slower, so the final stack uses **ACTOR_ONEPASS=0**.

`WORLD_VERT=1 WORLD_VERT_LEVEL=5` loads a prepared r101 package at room open,
using allocations sized from the original level-0 mesh and strip-group files.
Missing/oversized variants fall back to level 0. The POC changes render data
only; sidecar identities, collision, events and source placements stay intact.
Other rooms without a level-5 package use their original data.

The user accepted the inherited **L2-fixed** visual reduction for this POC
(third column of WORLDVERT-R101-L2FIX). The new `ps2_world_batch.py` extends the
existing R4IM reader/writer rather than introducing a format or renderer:

- Coalesce consecutive meshlets only inside the same part/material, cluster,
  LOD and 4 m spatial cell in every placement. Transparent parts are not batched.
  The merged bounds are conservative. This trades slightly coarser culling for
  fewer meshlets; it is not a visibility policy change.
- `--contiguous` copies each meshlet's unique vertices into contiguous offline
  storage, preserving reuse inside the meshlet. This removes the runtime indexed
  gather through the existing nonindexed fast path. It does not increase the
  number of transformations for that meshlet.
- Verify ordered full vertex attributes for every strip at every LOD before
  writing. Rebuild `.r4sg` with `ps2_strip_groups.py` and verify oriented triangle
  sets and group coverage afterwards. Mesh/material/cluster/palette identities
  are preserved.

| Local level | Meshlets | Package bytes | Purpose |
|---|---:|---:|---|
| 0 | original | 1,283,520 | Original baked r101 package |
| 1 | 1,335 | 907,520 | Inherited approved L2-fixed, indexed |
| 3 | 1,113 | 900,416 | 4 m batch, indexed |
| 4 | 1,335 | 902,240 | L2-fixed, contiguous only |
| 5 | 1,113 | 891,232 | 4 m batch plus contiguous |

The byte reduction is **not** a heap saving in this POC: level-0-sized blocks
are intentionally retained. The uninstrumented r101 heap4 after world loading
is 3,331,040 bytes in both the baseline and final cost arm. R101's inherited
portal-cell file rejects the package CRC in both baseline and candidate, so
this comparison does not claim a new portal-culling gain or loss.

## Measurements

All rows: T15_DATA, `benchmark-r101-t12` warp, Leon by the burning cross,
six live Ganados in the current T15 encounter, `LEON_LOD=0`, Ganado level 2,
full effects, `PACE_MODE=off PC_SAMPLER_BYTES=8192`, global frame window
500:799 sampled every 10 frames (30 samples). The filename's t12 is the warp
name, not a claim that the build or assets are test12. These are whole-frame
SH-4 **console-fit MODELLED** results, with no further residual multiplier.

| Cost arm | Stack | ms/frame |
|---|---|---:|
| cxas-offrW | Explicit existing-switch off control | 67.932 |
| cxas-onrW | Current enabled baseline | 65.853 |
| cxap1rW | Baseline + bounded ACTOR_PLAN | 64.888 |
| cxwv1rW | Plan + indexed L2-fixed | 64.743 |
| cxwv3rW | Plan + indexed L2-fixed + 4 m batch | 64.652 |
| cxwv4rW | Plan + contiguous L2-fixed | 61.605 |
| cxwv5rW | Plan + contiguous L2-fixed + 4 m batch | **61.352** |
| cxop1rW | Indexed batch stack + blocked ONEPASS | 64.925 |

Fusion loses 0.273 ms against its matched cxwv3 control. Contiguous storage
accounts for the main scenery gain: 3.138 ms versus indexed L2-fixed; batching
adds 0.253 ms on top of contiguous storage. The reduced indexed package alone
saved little CPU because the gather path raised `MeshDraw::draw` nominal self
cost from about 1.98 to 4.82 ms. The actor plan's directly identified owned setup
cost changes 4.770 -> 4.390 nominal ms; its whole-frame delta is 0.965 ms.
Instruction layout/cache effects and slight render call-count changes mean
the whole-frame delta must not all be attributed to the two removed checks.
Do not add nested call-tree costs or the existing-switch gain to the final gain.

Evidence directories `E/hwmodel-<arm-without-rW>-cross` contain each fixture,
warp, stage/payload identity, nominal and console-fit projections and nominal
call tree. Raw traces were removed after projection under the existing policy.

## Validation

- Fresh final all-off build `cxall0rW` directly reproduces cxas-on's loadable
  image SHA256 `d9cad4f6...` and `_end=8c427098`. Intermediate identities also
  hold: cxap0 equals cxas-on; WORLD_VERT=0 equals cxap1; ACTOR_ONEPASS=0 equals
  the preceding world stack. No missing symbols
  in the candidate builds. Final cost `_end=8c427458`, versus baseline
  `8c427098`: +960 bytes. Trace twins add +992 bytes. No extra actor arena.
- ACTOR_PLAN compare: 960/960 Leon bind reuse hits, zero disagreements;
  3,000 prepared preflight checks, zero failures. Plan 0/1/2 also pass the
  matched fight, bell-trigger and door traces.
- ONEPASS compare: 29,952 meshlets and 3,804,783 vertices checked, zero vertex
  or mask disagreements. Correctness is not a performance acceptance.
- Combined `cxfinalrT` versus baseline `cxtp0rT`: STRICT and MUST-IDENTICAL for
  819 fight frames, 487 bell-trigger frames and 1,190 door-route frames,
  with no missing trace ticks. Door103 reaches the door-demo end and r103.
  The bell trigger is moved from room frame 2400 to 240 in a matched local
  fixture so it actually runs within the short test. The unskipped run covers
  the handover into movie 10130, not the movie's complete playback.
- Initial H2 window: 244 frames STRICT and MUST-IDENTICAL through the r100
  house approach and s03 movie start. This alone is not a full H2 encounter gate.
- Additional matched source-owned movie-skip runs cover the H2 house Ganado,
  kill, s20 ambush and inventory opening: 1,067 trace frames STRICT and
  MUST-IDENTICAL, including 327 inventory-masked frames (740 unmasked).
  Bell continuation through movie 10130's source-owned skip and the subsequent
  call/inventory gives 977 frames STRICT and MUST-IDENTICAL, including 411
  masked frames. TEX_CHECK and LEON-GC pass both continuations. The skip presses
  wait for the existing `movie=1` fixture state; no movie/game completion code
  is changed. Evidence: `skip2-h2-{0,1}`, `skip2-bell-0`, `skip3-bell-1`.
  The first bell candidate staging attempt failed on a transient WSL connection
  error before execution; its separate retry is the cited candidate.
- TEX_CHECK=2 and LEON-GC pass all three combined route runs: no texture failures,
  metadata/VRAM changes or GC Leon fallbacks. Capacity/state/texture/wrap refusal
  counters are zero. The existing empty-draw counter is not a new refusal.
- Alignment interpreter: enabled `HWTRACE_ALIGN=1`, no MISALIGN records, r101
  loaded and rendering through global frame 600. Plain diagnostic KOS headroom
  bottoms at 56,992 bytes in this run.
- Asset proof before strip-group regeneration: 707 LODs, 16,757 strips,
  67,659 corners with identical ordered full attributes. After regeneration:
  all 1,335 storage-only and all 1,113 batched meshlets have identical oriented
  triangles and zero group faults.
- Frozen frame 400, accepted L2-fixed versus final batch: camera a2 has identical
  fb0 pixels; cross camera vc differs in 91/307,200 pixels, maximum channel
  difference 9. Both logs confirm the freeze. Captures and `look-check.json`
  remain in E. This is an automated comparison and agent inspection, not a new
  human appearance approval. Earlier freeze-700 captures never reached their
  freeze and are excluded.

The `cxsqjrW` diagnostic twin (`KOS_WATCH=1 KOS_SQUEEZE=1 WARP_JUMP=1`,
ELF prefix `ec8d2f7c01fbfb81`, `_end=8c42b1b8`) passes **all ten** 48 KiB
KOS-pressure runs. Each holds all 49,152 requested bytes, has zero OOM,
MISSING or HALT lines, exceeds the 4,096-byte headroom floor and reaches its
scene marker. Leave tests verify the destination entry occurs after r101.
TEX_CHECK and LEON-GC also pass all ten logs, with zero capacity, state,
texture or wrap refusal counters.

| Scene | Minimum headroom, one block | Minimum headroom, 4 KiB pieces |
|---|---:|---:|
| r101 cross fight | 10,712 | 10,624 |
| r100 radio/subscreen open | 40,232 | 40,128 |
| door103 | 17,312 | 17,224 |
| r101 fight then return to r100 | 10,912 | 10,824 |
| r101 fight then enter r103 | 10,912 | 10,824 |

Evidence: `E/kosj-<scene>-49152-<frag>` and
`E/squeeze-jump-summary.json`. An earlier `cxsqrW` diagnostic lacked
`WARP_JUMP`, logged an unknown `jump` line and never changed rooms in its four
leave tests. Those are invalid coverage, not accepted passes; the entire suite
was repeated with the corrected twin. The jump diagnostic changes the arena
fit boundary, so its headroom is reported for that exact image rather than
substituted for the cost build's memory layout.

This POC is not a release or physical-console acceptance. Full H2/s30 playback,
extended room coverage and console timing remain required before a Chapter 1
rollout. The targeted checks use the local `re4-dreamcast-testing` companion
workflow; a release still needs the broader release tier.

## Reproduce and continue

Use the existing private inputs; do not copy game data into Git. All commands
below run in WSL, with `R=/root/probe/codex-ch1-render-20261015` and `T=$R/tree`.

```sh
export T K=$R/logs ROUTE_OUT_ROOT=$R/builds
export ROUTE_PROGRAMS_DIR=$R/programs ROUTE_PROGRAMS_JSON=$R/programs.json
export ROUTE_REGISTRY_LOCK=$R/programs.lock
export BENCH_EV=/mnt/c/Flycast-Evidence/re4-dreamcast/codex-ch1-render-20261015
export BENCH_WORLD_LEVELS=$R/assets/r101
XON='PACE_MODE=off PC_SAMPLER_BYTES=8192' \
  bash "$T/port/dreamcast/tools/d367/actorplan/build.sh" NEWLABEL rW \
  ACTOR_PLAN=1 ACTOR_ONEPASS=0 WORLD_VERT=1 WORLD_VERT_LEVEL=5
bash "$T/port/dreamcast/tools/d367/actorplan/hw.sh" \
  r101-t12 NEWLABELrW NEWNAME-cross 500:799 10
```

Use fresh labels. The build wrapper uses the existing host build slot and
separate outputs; hw.sh now uses the existing ext4 stager directly, saves
fixture/warp/identity even when projection fails, and avoids the former fragile
sed-generated wrapper and `rc: unbound variable` failure.

Local test orchestration and retained commands are in
`C:\Game Dev\Emulators\_codex_ch1_20261015` (`gates.py`, `final-gates.py`,
`jump-gates.py`, `skip-gates.py`, `bell-retry.py`, and review scripts). They use
the existing harness with an isolated program root and unique scenario names;
normal captures are 60 seconds. Source trace runs use `trace_lock.sh`. Read each
run's own stage manifest and fixture; `RUN_COMPLETE_AWAITING_REVIEW` alone is
not a gate pass. The JSON reports in E contain the reviewed verdicts.

Level 1 is the reviewed package from
`PRIV/worldvert-20261015/r101-v2` in the worldvert work area. To reproduce the
new storage/batching result from it:

```sh
B='/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13'
python3 "$T/port/dreamcast/tools/ps2_world_batch.py" \
  "$R/assets/r101/ps2-wv1.re4mesh" "$R/assets/r101/new-flat.re4mesh" \
  --sidecar "$B/ps2-world.r4pw" --cell-mm 4000 --contiguous \
  --max-bytes 1283520 --report "$R/assets/r101/new-flat.json"
python3 "$T/port/dreamcast/tools/ps2_strip_groups.py" \
  "$R/assets/r101/new-flat.re4mesh" "$B/ps2-world.r4pw" \
  "$R/assets/r101/ps2-wv5.re4mesh" "$R/assets/r101/ps2-wv5.r4sg"
```

For further rooms, first repeat the asset identities, conservative spatial
bounds, strip-group proof, frozen visual check, matched cost and source-state
gates. Do not assume this r101 package or its 4.501 ms gain applies across
Chapter 1. The unimplemented larger asset-load actor plan remains a separate
experiment; this small proof does not establish its earlier 1.5-2.5 ms estimate.
