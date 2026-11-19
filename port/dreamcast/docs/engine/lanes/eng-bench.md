# eng-bench M1 handback, 2026-11-19

**STEER-003 hand-back condition met.** The indexed renderer reduced mean modelled drawing at the cross from 27.526 to 13.298 ms (51.7%) and at hayfork from 49.679 to 27.023 ms (45.6%). The cross remains above the brief’s 10 ms console-entry threshold.

Renderer and capture source commit `deb10de2c09f59fc6b92dd31e3cdf13b28265741` on `lane/eng-bench`.

## Matched SH7091 model

Nominal 200 MHz, five pictures per room (19, 43, 67, 91, 115). The difference is indexed minus game. Times are milliseconds per picture. The nearest-rank p99 is the largest of these five samples. Counts use 20, 26 and 33.333 ms.

| Scene | Tier / path | World | Actors | PT | TR | Effects | HUD | Mean | p99 | Worst | Over 20 / 26 / 33.333 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cross | indexed / model | 5.343 | 6.414 | 0.160 | 1.241 | 0.067 | 0.075 | 13.298 | 14.328 | 14.328 | 0 / 0 / 0 |
| cross | game / model | 10.626 | 10.778 | 0.732 | 0.298 | 3.686 | 1.406 | 27.526 | 34.333 | 34.333 | 5 / 1 / 1 |
| cross | Difference | -5.283 | -4.364 | -0.572 | 0.943 | -3.620 | -1.331 | -14.227 | -20.005 | -20.005 | -5 / -1 / -1 |
| hayfork | indexed / model | 3.958 | 20.844 | 1.066 | 1.028 | 0.045 | 0.083 | 27.023 | 27.296 | 27.296 | 5 / 5 / 0 |
| hayfork | game / model | 6.081 | 34.755 | 1.564 | 0.169 | 6.741 | 0.368 | 49.679 | 49.913 | 49.913 | 5 / 5 / 5 |
| hayfork | Difference | -2.123 | -13.912 | -0.498 | 0.858 | -6.697 | -0.286 | -22.656 | -22.617 | -22.617 | 0 / 0 / -5 |

The capture and timing runs restored the same pre-draw states in the interpreter. Verification reproduced each original picture record byte for byte. Recording was disabled before each timed draw. The same nominal simulator ran through the complete guest trace, including intervening work that affects cache state. Drawing totals exclude game logic and presentation waits. The bench charges modifier-volume submission to characters and masked hair to TR. The game profiles modifier volumes in effects.

Cross character draw is 6.414 ms against 10.778 ms for the matched game scope (−4.364 ms). It also clears the steer’s separate 8.8 ms character target. Hayfork retains the ten barn props and all submitted actor records. Its character draw still takes 20.844 ms against the matched 34.755 ms (−13.911 ms).

## Staged Flycast replay

Each staged image replayed the 300 pictures twice. This tier compares both bench images on Flycast’s guest timer. The 600-picture comparison uses the earlier staged strip renderer as its reference. The matched-game comparison is the five-picture model table above.

| Scene | Tier / path | World | Actors | PT | TR | Effects | HUD | Mean | p99 | Worst | Over 20 / 26 / 33.333 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cross | Indexed / Flycast | 3.261 | 3.948 | 0.093 | 0.731 | 0.015 | 0.033 | 8.090 | 9.997 | 11.486 | 0 / 0 / 0 |
| cross | Strip B / Flycast | 8.059 | 34.088 | 0.213 | 0.001 | 0.024 | 0.056 | 42.446 | 50.217 | 51.606 | 600 / 600 / 600 |
| cross | Difference | -4.798 | -30.140 | -0.120 | 0.730 | -0.009 | -0.023 | -34.356 | -40.220 | -40.120 | -600 / -600 / -600 |
| hayfork | Indexed / Flycast | 2.386 | 13.986 | 0.625 | 0.608 | 0.022 | 0.035 | 17.668 | 20.094 | 20.241 | 11 / 0 / 0 |
| hayfork | Strip B / Flycast | 5.888 | 105.667 | 1.516 | 0.001 | 0.037 | 0.055 | 113.169 | 116.260 | 116.267 | 600 / 600 / 600 |
| hayfork | Difference | -3.502 | -91.681 | -0.891 | 0.607 | -0.015 | -0.020 | -95.501 | -96.166 | -96.026 | -589 / -600 / -600 |

## Profiles and visual evidence

- Full ten-row per-function tables for world and characters in both rooms and both designs are in `port/dreamcast/engine/bench/PROFILE.md`. Each row records exclusive cycles, instruction misses, data read/write misses and the work performed. The original design repeats shading on strip corners and calls libm for strip bounds and colour clamps. The indexed design uses separate bone-sorted position and normal streams, shared per-picture bone matrices and projected positions, the existing skinned and rigid SH-4 position kernels, and the n16 light kernels. Part colour, direction, alpha and material bindings come from the source draw.
- The baker removes empty world pieces and marks the pieces wholly in front of the near plane for each recorded view. Material headers are baked, texture addresses are relocated at load and sequential strip reads use prefetch. Boundary pieces still clip. Indexed emission, matrix composition and skinned positions remain the leading costs at hayfork.
- Three new still pairs per room are in `runs/mat003-pairs/{cross,hayfork}.png`. Full-size images are in `runs/mat003-smoke` and `runs/eng-bench-{cross,hayfork}-4`. Cross picture 150 shows the contact shadows on the ground. Picture 1’s sampled skyline patch matches every RGB pixel and its hair patch matches 99.95%. Six full gameplay-area RGB mean absolute differences range from 0.258 to 0.721 on the 0–255 scale. `pixel-comparison.txt` lists per-picture results. Owner visual approval is pending.
- Original captures cover game frames 466–765. The matching supplements in `runs/mat003-{cross,hayfork}` compare the original camera, effective pick fields, actor transforms, palettes, source lights, texture keys, effect and HUD records on all 600 pictures. They add the actual fog registers, sky far depth, modifier packets, paired texture keys, submission lists and per-part light folds. Private baked packs are in `build/indexed`.
- Timing evidence under `E:\RE4DC-Lanes\eng-bench` includes `runs/baseline003-{cross,hayfork}-timed`, `baseline003-cross-verify2` and `baseline003-hayfork-verify3`. The strip profiles are in `runs/bench-model-matched-b` and `runs/bench-model-final-farm`. The indexed profiles are in `runs/mat003-model-cross` and `runs/mat003-farm`. Each phase003 directory retains hwreport symbol tables and miss counts. `build/final-bars003.json` holds the per-picture totals.

## Disc and controls

- Private staged standard GDEMU image `build/M1-GDEMU-mat003/disc.gdi`. Its `SHA256SUMS` covers all four files. Track 03 SHA-256 `b1389e7804f4303f6a596e53ae62ba596548a502c3523bf2b60a581b2bcdff33`. The disc passed standard lint and both 600-picture Flycast windows (`runs/mat003-standard`).
- Renderer ELF SHA-256 `33de2a79aebc940dc9dcc079c4ce36cff1cccc924bf894004a0e4d6abae51e87`. The clean checkout reproduced the boot binary SHA-256 `7c0fa5d750f0ec837c774018470b875df5e4aa8bc3ab91239b17859f71aac1a1`. The missing-pack build refused to proceed. A corrupted frame-list index with a recomputed valid CRC was refused by guest validation before replay (stage 91, `runs/mat003-bad`).
- With the 5 ms delay enabled, mean Flycast draw times at cross and hayfork were 13.098 vs 8.090 (+5.008) ms, 22.664 vs 17.664 (+5.000) ms. The original dropped-picture control refused picture 2. Guest PMC events 25, 24, 04, 05 and 08 returned zero in Flycast. Model miss counts come from the nominal SH7091 simulator.
- SH4ZAM remains pinned to cff97e8 (previously 33fa485). The compatibility game build linked with zero unresolved symbols. The indexed design reuses existing game assembly alongside upstream SH4ZAM matrix helpers. There is no isolated SH4ZAM speedup claim.

## Remaining scope

Console timing and owner visual acceptance remain open. The optional QA-link phase switches were omitted. The staged image is local to the lane.
