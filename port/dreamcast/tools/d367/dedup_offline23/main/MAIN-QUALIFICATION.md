# QA23 Dedup qualification milestone (af09f0a2)

Done: The default-off dedup unit passes source review, target link, exact OFF image identity, three exact frozen-view pixel comparisons, KOS 48 KiB fight squeeze, three-room TEXCHK/CAST-GC/LEON-GC and GDEMU seed1. Frozen source af09f0a2, reviewed runtime e66ec61e4; main support 40a2bc15f.
Doing now: Preserving complete gate evidence and preparing current-integration review. New origin/t15/int28da09802 merged without conflicts into separate daabb0dba; the tested af09 source/tree remains untouched.
Next: Finish instrumented movie fragment, final private console QA packaging, current-integration qualification and full H2 heap-floor check.
Blocked / Needs the user: Full H2 requires resolving the handover's <=60-second run cap; physical console timing remains pending.
Shared-file changes: No production recipe changes. Runtime files are frozen in af09; separate merged next branch is read-only under integration review. Main owns source changes; no overlapping worker edits.

## Gate evidence, frozen af09

- OFF objcopy image matches e17 baseline:3655e448838402af86097f8cf848e5f35b0f81312b1805dd003348edb31fc050.
- ON diagnostic reproduction equals ordinary ON image:f23774e1ae98c9b30c107ed34d3ec5a3e5cf78c03d38c4622fd158d9e72323c7.
- r101 cross, r103 farm and r100 forest at tick330:0 different pixels out of307200, unmasked. JSON pins source fixtures and stills. All screenshots inspected.
- Ordinary console-mode s30 fragment OFF/ON:340/340 uploaded/presented, restored1, heap_before140448 both; ON re-admits SCNDEDUP3 after movie, extra_heap0. This is post-ambush coverage, not full H2 or the ~94KiB current full-route floor.
- Instrumented KOS48 fight: contiguous held49152, minheadroom6056/top3904; fragmented held49152, minheadroom6120/top3136. Both no OOM/HALT/FAULT/MISSING and alert reached. Source gate judges total headroom>=4096; largest-block figures included.
- TEXCHK5/5 logs pass (census3rooms plusKOS2); CAST-GC125censuslines/7room-modelrows,0unallowedGC/MIXED; NOT-DRAWN59alivelistlines,0alive-neverdrawn; LEON-GC3/3pass.
- GDEMUconsole profilegdemu, jitter20000, seed1: r101->r103 reached,0badreads/stops, both rooms use alternate packages. Race correctness only, not hardware timing.
- No console performance measurement. Offline camera transform counts:cross-10.56%,farm-19.62%; not ms gains.

## Integration and remaining limits

Current origin/t15/int moved from e17af64a to28da09802 during qualification. Separate branch wip/dedup-offline23-next-20261023 holds daabb0dba96e55a047fda9135e5fb9aad91d1c4f, including SCENERY_REPLAY_LEAN and disabledFX fixes. This branch is pushed and under source review, not build/runtime-qualified. Do not transfer af09 gate results to it.

The first r1 launcher accidentally selected ordinary Flycast and had a malformed capture path/CR. All evidence remains preserved and marked preliminary. WSLENV+Windows preflight verifies consolemode for r2/r3/gate runs; capture-identity-pins.json hashes each actual executable. Crossr2 froze too early and is superseded by exacttick330r3 look checks. A freeze-triggered no-new-frame alarm in the early capture is not a dedup crash; r3 stops8seconds after freeze.

Private evidence:C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023. Standard-layout Off/On QA media currently in /root/work/lanes/dedup-offline23-main/stage-{off,on}/gdemu. Not copied to SD or published. Final disc path/README pending.
