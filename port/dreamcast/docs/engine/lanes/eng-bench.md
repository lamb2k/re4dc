# eng-bench M1 handback, 2026-11-19

**Stopped at the renderer stop rule.** At the village cross, the matched nominal 200 MHz SH-4 model measured **60.804 ms for design A** and **52.597 ms for design B**. Both exceeded 13 ms. The console-entry threshold was 10 ms. No console run requested.

## Timing

Phase times and totals are milliseconds per picture. PT and TR are punch-through and translucent geometry. The count column gives pictures over 20 / 26 / 33.333 ms.

| Scene | Design / tier | Pictures | World | Actors | PT | TR | Effects | HUD | Mean | p99 | Worst | Over budget |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| r101 cross | A / Flycast | 600 | 8.062 | 40.290 | 0.211 | 0.001 | 0.025 | 0.055 | 48.649 | 56.999 | 61.071 | 600 / 600 / 600 |
| r103 hayfork | A / Flycast | 600 | 5.868 | 131.172 | 1.502 | 0.001 | 0.037 | 0.059 | 138.643 | 141.672 | 141.691 | 600 / 600 / 600 |
| r101 cross | B / Flycast, staged GDI | 600 | 8.059 | 34.088 | 0.213 | 0.001 | 0.024 | 0.056 | 42.446 | 50.217 | 51.606 | 600 / 600 / 600 |
| r103 hayfork | B / Flycast, staged GDI | 600 | 5.888 | 105.667 | 1.516 | 0.001 | 0.037 | 0.055 | 113.169 | 116.260 | 116.267 | 600 / 600 / 600 |
| r101 cross | A / hardware model | 5 | 11.018 | 49.327 | 0.267 | 0.004 | 0.078 | 0.106 | 60.804 | 65.874 | 65.874 | 5 / 5 / 5 |
| r101 cross | B / hardware model | 5 | 10.852 | 41.269 | 0.272 | 0.004 | 0.083 | 0.112 | 52.597 | 56.779 | 56.779 | 5 / 5 / 5 |
| r103 hayfork | A / hardware model | 5 | 8.245 | 165.883 | 2.113 | 0.005 | 0.055 | 0.099 | 176.405 | 176.723 | 176.723 | 5 / 5 / 5 |
| r103 hayfork | B / hardware model | 5 | 8.055 | 133.425 | 2.088 | 0.005 | 0.060 | 0.103 | 143.740 | 143.874 | 143.874 | 5 / 5 / 5 |

Flycast windows replayed the 300-picture input twice. Draw time starts after the PVR-ready wait and ends at submission. The staged image reported a mean ready wait below 0.001 ms in both rooms. Guest PMC rows rotated through events 25, 24, 04, 05 and 08 (hex). Flycast returned zero on all five.

Model rows use five full interpreter traces per scene and design at markers 20, 44, 68, 92 and 116. Guest timing stores identify replay pictures 19, 43, 67, 91 and 115. The model mean includes the whole traced picture. Phase spans run between guest timing-row stores, with setup charged to world. The nearest-rank sample p99 is the sample worst. The instruction totals agree with the trace recorder for every run.

## Builds and evidence

- Renderer commit 476d66b55bc8239e85f3b8621b5d2539f4722433 on lane/eng-bench. A expands mixed strips through triangles with M1_STREAM_STRIPS=0. B streams near-plane crossings, preserves visible strip runs and reuses composed bone matrices. Both comparison builds use the same source, captures, packs and lighting.
- Design B ELF SHA-256 62dc17496fa7a64952513a025f404a30c3f2fef7649f9196f391bf6bd227e4a4. Design A ELF SHA-256 6d0183e48e91da7c59e7318f3b9d807a0775b31ac8ff890c5247d578be7863c2.
- Private evidence root is E:\RE4DC-Lanes\eng-bench. The staged standard GDEMU image is build/M1-GDEMU/disc.gdi. SHA256SUMS alongside it covers the descriptor and all three tracks. Track 03 SHA-256 c6f18fda41e4de2c416411942f499fa895e5981deb4fffdbe66b690ac37624ce. Standard disc lint passed with zero violations. runs/bench-standard contains its two 600-picture Flycast windows.
- A clean local checkout with the pinned dependency and private pack path reproduced boot binary SHA-256 3bc5e226695d6cf7611bee07ce3729362b6644ae16072b953511456b47b07139. Missing packs stopped the build with the path diagnostic in build/missing-control.log. Changing a byte in the frame-list section of CROSS.PAK caused the guest to refuse it at the checksum gate, stage 91, before replay (runs/bench-corrupt).
- runs/eng-bench-cross-4 and runs/eng-bench-hayfork-4 each contain 300 contiguous picture records and 300 corresponding 640×480 stills, game frames 466–765. Record peaks were 42,028 and 104,624 bytes. The dropped-picture control failed on picture 2. Private packs are in build/cross-m1.pak and build/hayfork-m1.pak.
- The 5 ms busy-wait shifted mean draw time by +5.007 ms at the cross and +5.012 ms at hayfork. See runs/bench-b2/bench.log and runs/bench-delay-final/bench.log. KOS vertex double buffering was checked at startup.
- Model traces, observed phase-store cycles, per-frame rows and ELF copies are in runs/bench-model-matched-a, runs/bench-model-matched-b, runs/bench-model-matched-a-farm and runs/bench-model-final-farm.
- runs/still-pairs/cross.png and runs/still-pairs/hayfork.png pair pictures 1, 150 and 300. Full-size replay stills are in runs/bench-b2. The cross picture 150 ground shadow is missing. The cross skyline shows stray polygons, and Leon’s lighting differs in both rooms. Owner visual approval remains open.

## SH4ZAM and remaining scope

SH4ZAM advanced from 33fa485 to cff97e8 in a808450f3. The existing game build with GAME_SH4ZAM=1 linked with zero unresolved symbols. Both bench arms use upstream matrix primitives. The lane added no SH4ZAM kernel and measured no isolated library speedup.

The bench provides six replay phases, on-screen timing summaries, guest logs and rotating PMC rows. The optional QA-link phase knobs were omitted. Physical-console timings and owner visual acceptance remain open. The SD card was untouched.
