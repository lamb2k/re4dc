# Prepared world and character draw experiments, 2026-10-16

Both bounded experiments were implemented and measured independently against
the current Chapter 1 POC. Both were slower as complete images, so their source
patches are archived locally and the runtime tree is restored. The physical
packages and the accepted POC configuration remain the same. See
[ch1-physical-validation-20261016.md](ch1-physical-validation-20261016.md) for
their compatibility evidence and pending physical-console gate.

## Matched cost result

**SH-4 console-fit model, not physical-console timing.** T15 data,
`benchmark-r101-t12`, burning cross, source frames 500..799 sampled every tenth
frame (30 samples), pacing off, full PS2 Leon jacket (`LEON_LOD=0`), Ganado
level 2, and the inherited six-alive rule. Assets are identical between arms;
only the executable and its six linked overlays differ.

| Arm | Setting | Total cycles over 30 samples | Model ms/frame | Change |
| --- | --- | ---: | ---: | ---: |
| `cxfmc1rW` | Current POC | 367,419,838 | 61.236640 | Reference |
| `cxwpb1rW` | Prepared world records | 371,330,834 | 61.888472 | +0.651833 ms |
| `cxdp1rW` | Prepared character submission | 374,291,960 | 62.381993 | +1.145354 ms |

Neither is a speedup. The rows are independent trials; the world prototype was
removed before the character builds. No combined result is claimed.

All builds start at local source commit `f4308c48` plus their saved patch.
Reference ELF SHA256:
`74b11a54409298bbfcc195e683ae79827195f34c51f05f3ad1837a9498d48098`.
World ELF:
`5e55395bdd3f9cdcff30cbf9923732d00251b6c4fb3a7c34de35d5409b5386d4`.
Character ELF:
`f5b2ccade90014813e62aef5df181ca402d5ca2fa7ca869d78237bd2517b8c11`.

## World trial

The existing R4IM loader already validates the scenery package once. The new
`WORLD_DRAW_PLAN=1` prepared mesh grid constants, material keys, float bounds,
and vertex/strip pointers from that validated package. Camera-dependent
arithmetic, visibility, strip order and geometry were unchanged.

This r101-only plan used 68,904 bytes of the 392,288 unused bytes between the
reduced file and the retained level-0 allocation boundary. It did not allocate
another heap block. Indexed packages or insufficient capacity kept the original
path. Retirement cleared all borrowed pointers. The existing native renderer,
package format and ownership mechanism were reused.

`WORLD_DRAW_PLAN=2` ran the original descriptor calculations beside each use.
The 60-second diagnostic reported zero mismatches through 943,231 bounds,
302,623 vertex-pointer, 249,438 strip-pointer, 114,381 key and 83,159 mesh checks.
The host test checked all 2,194 records, guard words, insufficient capacity,
alignment, null metadata and indexed fallback under ASan/UBSan. Host pointers
are wider, so its plan size was 77,808 bytes.

This establishes descriptor agreement in the exercised scene, not full-route
or physical acceptance. The additional records and changed code layout did not
pay back in the complete model result. No full release gate was run for this
rejected version. The initial build had an unsigned pointer-type mismatch;
the successful `cxwpb1rW`/`cxwpb2rW` builds corrected it. The failed build remains
preserved separately.

## Character trial

Character geometry already uses native meshlets and immutable chunk proofs.
`ACTOR_DRAW_PLAN=1` therefore extended the existing qualified owned submission:

- Read the current skin/source entry through the already validated skin lease,
  using the lookup used by the earlier Leon pipeline, without its retained plan.
- Calculate current projection limits once per submission.
- Reload material fields only when the ordered material changes.

The existing all-runs preflight, texture pinning, world barriers, kernel order,
clipping and post-submit lease checks remained. No extra heap storage, geometry,
palette, frame owner or persistent light/pose cache was added. Current pose and
lighting still came from the source every frame. Both baseline and candidate
loaded the same L5 package; the logged r101 heap after world/strip-group loading
was 3,322,848 bytes in both cost arms. The image `_end` increased by 608 bytes.

The `ACTOR_DRAW_PLAN=2` diagnostic compared the prepared skin/source and
projection values with the original qualification, and compared the complete
loaded part record with the original loader. It reported 53,313 checks over
17,771 runs, 9,601 material reuses, and zero mismatches or fatal errors.

The independent 60-second traced fight pair used `cxfm1rT` versus `cxdt1rT`:
842 ticks were STRICT, with MUST-IDENTICAL decisions, no trace gaps or NULs,
TEXCHK passing, and LEON-GC passing with zero fallback frames. This is bounded
fight coverage, not new full H2/bell, cache/DMA, memory-pressure or console
acceptance. The candidate was already rejected on cost, so those wider gates
were not repeated.

The nominal call-tree model attributed 4.522544 ms of owned actor setup to the
reference and 4.217934 ms to the candidate, a 0.304610 ms reduction. Complete
nominal instruction-cache penalties rose from 9.159 to 10.065 ms, including
2.096 to 2.683 ms in unchanged scenery code. This is consistent with sensitivity
to code placement; it does not isolate one cache-conflict pair. Call counts vary
slightly between cost captures, so the component delta is not proof of the
entire algorithm's isolated saving. Nominal components must not be added to the
console-fit totals above.

## Reproduction and preserved evidence

Local roots:

- `R=/root/probe/codex-ch1-render-20261015`
- `Q=C:\Game Dev\Emulators\_codex_ch1_20261015`
- `E=C:\Flycast-Evidence\re4-dreamcast\codex-ch1-render-20261015`

The source archives are `R/audit/world-draw-plan-rejected` and
`R/audit/actor-draw-plan-rejected`, each with checksums. World preparation has a
`runtime.patch` plus `world_draw_plan.hpp`; place the latter in
`port/dreamcast/room` when reproducing. Character preparation is one
`runtime.patch`. Apply either to an isolated checkout of `f4308c48` and use fresh
build/run labels. The two archives are also copied under
`Q/prepared-draw-experiments`, with the executed recipes and JSON reports.
Existing private assets and the local toolchain are required; no assets are
part of these source patches.

Executed recipes in `Q`:

- World: `build-world-plan.sh`, `build-world-plan-retry.sh`,
  `world-plan-host.cpp`, `world-plan-host.sh`, `measure-world-plan.sh`,
  `review-prepared-world.py`.
- Character: `build-actor-draw-plan.sh`, `build-actor-draw-trace.sh`,
  `measure-actor-draw-plan.sh`, `actor-draw-strict.py`,
  `review-actor-draw-strict.py`, `review-prepared-actor.py`.

Disabled builds `cxwp0rW` and `cxdp0rW` both reproduce the reference loadable
program byte-for-byte, SHA256
`94550178666d7f798a896ca95d80671ed35e2c7c5c6c706d6404b813cfb69ed7`.
`E/prepared-world-experiment-summary.json`,
`E/prepared-actor-experiment-summary.json` and
`E/actor-draw-strict-summary.json` record the results. Model evidence is under
`E/hwmodel-{cxfmc1,cxwpb1,cxdp1}-cross`; diagnostic captures are
`E/world-plan-diag` and `E/actor-draw-plan-diag`.

The next performance experiment should isolate the observed instruction-cache
cost before adding more prepared records. The current evidence does not justify
promoting either prototype or extending the scenery conversion to another room.
