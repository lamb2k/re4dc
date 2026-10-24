# Modelled meter matrix — source7a3af776

One accepted serial capture per arm/scene, requested40s with exact-child55s bound. Frozen source/profile, original fixture, console executable, staged programme/all14overlays/base track03 identity were bound before launch. Runtime standard lod_px5 with FAR_LOD4=20 and cap4 recipe were retained. Timing profiles have CENSUS0, WORLD_METER1, GAME_TICK_LOG60, PHASE_METER1 and PC_SAMPLER0; PVS0, batch1, SELECT_ONLY1, REPLAY_LEAN1, UV_SNAPSHOT0, DEDUP0 and actor setup/backface controls unchanged.

All eight accepted captures report RUN_COMPLETE/errors[], reader_exit0, guardfalse and observed guest lifetime<=55s; accepted lifetimes are disjoint. Full wrapped PT records are required. The common contiguous set in each scene is13 complete windows, frames352–1131 inclusive,780ticks, wholly inside[300,1140). Means are weighted by each window's n. `world=wopq+wxlu+wshell`; setup/cpu/wall overlap these costs and are not added to world.

| MODELLED world ms/tick | R off | L selector | E emitter | B both |
|---|---:|---:|---:|---:|
| b1 r101 cross |6.861000|6.770923|6.938308|6.848385|
| s2 r100 forest |5.749077|5.747154|5.800462|5.798846|

| MODELLED world delta ms/tick | L−R | E−R | B−R | B−L−E+R |
|---|---:|---:|---:|---:|
| b1 |−0.090077|+0.077308|−0.012615|+0.000154|
| s2 |−0.001923|+0.051385|+0.049769|+0.000308|

This single matched tick-window matrix indicates essentially nil B effect at cross and a small modelled forest regression. It supplies no reason to enable either switch. It is not a physical-console measurement, FPS uplift, statistical confidence interval, image-equivalence result, runtime gate or recipe admission. Tick-window world standard deviations are approximately1.04–1.07ms at b1 and0.0343–0.0345ms at s2; those within-scene temporal variations are not independent-run uncertainty. Exact per-window means and setup/cpu/wall context remain in meter-summary.json. Wall is approximately33.447ms/tick in every arm and must not be presented as a measured world saving.

Accepted b1 directories: R-m-b1-q2, L-m-b1-q2, E-m-b1-q1, B-m-b1-q1. Accepted s2 directories: all R/L/E/B-m-s2-q1. Initial R/L-b1-q1 overlap is preserved and excluded; see PROTOCOL-EXCLUSIONS.md. No failed capture is silently relabeled. Remaining stills, diagnostic/gate rows and physical-console pair belong to integrating owner; these captures provide no combined renderer/PVS/interior-affine claim.

Evidence: C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover\7a3af776\runtime-support\meter-summary.json, per-cap raw logs/bounded-launch/run-result, and launch-receipts. Source-owned parser controls and runtime census evidence are separate.

The capture verifier's actual-log positive plus six RAM-only negative controls reject wrong runtimeLOD, wrongroom, census contamination, missing wrappedPT fields, fired durationguard and incorrectmeter knob. Future runtime-support launches should use qualified-run-v2.sh, which additionally serializes this worker before taking shared3-slot and global16 locks; v2 passed shell syntax checking but was not used for the sealed captures. v1 and exact used sequences remain preserved.