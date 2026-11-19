# eng-e0 hand-back (milestone E0, drawing row), 2026-11-19

Lane `eng-e0` on `lane/eng-e0` from `68510dd38`. Final code commit `e28d7f2c2` (renderer), hand-back docs commit listed at the end.
Every number is labelled. MODELLED = nominal 200 MHz SH-4 hwsim over Flycast hwtrace, same tool and window as round 3.
Flycast = guest timer in the standard harness. No console number exists yet.

**Result: the ordered list (steps 1 to 7) is done; the cross did not reach 7 ms MODELLED.**
Cross went from 45.4 to 14.2 ms MODELLED (mean, 25 pictures); hay-fork from 99.7 to 16.1. Both are still over the
7 ms console-entry line and over the 14 ms drawing row on MODELLED, on every timed picture. Next step per the brief: console.

## 1. Per-phase table, MODELLED, before and after each step

24 pictures, 12..288 step 12 (the round 3 pictures without picture 1 / 61; those are added in section 2).
Over = pictures over 7 ms MODELLED (all 24 at every step). World = setup, selection and opaque world; Chars = characters
and modifier volumes; PT+TR = punch-through and translucent world plus hair; FX+HUD = effects and HUD.

| Step | Scene | Mean | p99 | Worst | Over 7 | World | Chars | PT+TR | FX+HUD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Start (round 3 code rebuilt) | cross | 45.37 | 52.01 | 52.01 | 24 | 14.32 | 27.36 | 2.66 | 1.03 |
| | hay-fork | 99.70 | 106.94 | 106.94 | 24 | 10.34 | 83.57 | 4.68 | 1.11 |
| 1 Build settings | cross | 31.41 | 37.76 | 37.76 | 24 | 13.27 | 14.77 | 2.59 | 0.78 |
| | hay-fork | 55.32 | 61.74 | 61.74 | 24 | 9.81 | 40.09 | 4.57 | 0.84 |
| 2 Characters on SH-4 kernels | cross | 24.38 | 31.23 | 31.23 | 24 | 14.07 | 6.75 | 2.79 | 0.77 |
| | hay-fork | 24.60 | 39.13 | 39.13 | 24 | 10.33 | 8.52 | 4.92 | 0.83 |
| 3a Selection masks, group ranges | cross | 19.92 | 25.37 | 25.37 | 24 | 10.28 | 6.75 | 2.13 | 0.77 |
| | hay-fork | 23.68 | 38.88 | 38.88 | 24 | 10.05 | 8.53 | 4.28 | 0.81 |
| 3b Colours at load, signed loads | cross | 18.10 | 22.14 | 22.14 | 24 | 8.81 | 6.71 | 1.82 | 0.75 |
| | hay-fork | 20.52 | 35.61 | 35.61 | 24 | 7.93 | 8.45 | 3.35 | 0.80 |
| 3c FPU-pair strip copy, SQ flush | cross | 17.19 | 20.72 | 20.72 | 24 | 8.02 | 6.72 | 1.70 | 0.75 |
| | hay-fork | 19.41 | 34.42 | 34.42 | 24 | 7.12 | 8.45 | 3.05 | 0.80 |
| 3d Aligned pack reads | cross | 15.97 | 19.22 | 19.22 | 24 | 6.78 | 6.74 | 1.71 | 0.75 |
| | hay-fork | 19.03 | 34.06 | 34.06 | 24 | 6.73 | 8.46 | 3.05 | 0.79 |
| 3f SH-4 world stage + actor emitter | cross | 14.94 | 17.98 | 17.98 | 24 | 6.54 | 6.06 | 1.59 | 0.74 |
| | hay-fork | 17.54 | 31.11 | 31.11 | 24 | 6.26 | 7.69 | 2.80 | 0.79 |
| 4 Change flags | cross | 13.83 | 18.34 | 18.34 | 24 | 5.32 | 6.02 | 1.61 | 0.89 |
| | hay-fork | 17.20 | 31.35 | 31.35 | 24 | 5.78 | 7.64 | 2.83 | 0.94 |
| 5 Baked visibility | cross | 13.75 | 18.26 | 18.26 | 24 | 5.22 | 6.12 | 1.60 | 0.81 |
| | hay-fork | 15.85 | 18.23 | 18.23 | 24 | 5.36 | 6.84 | 2.78 | 0.87 |
| 6 Arms (default arm 0) | cross | 13.90 | 18.45 | 18.45 | 24 | 5.29 | 6.10 | 1.63 | 0.87 |
| | hay-fork | 15.93 | 18.33 | 18.33 | 24 | 5.37 | 6.84 | 2.79 | 0.93 |
| 7 Look (final image) | cross | 14.00 | 18.55 | 18.55 | 24 | 5.29 | 6.20 | 1.63 | 0.88 |
| | hay-fork | 16.06 | 18.44 | 18.44 | 24 | 5.37 | 6.96 | 2.79 | 0.94 |

What each step was:
1. `-ffast-math -mfsca -mfsrra -DNDEBUG -flto -fipa-pta`, `-Os` default with `render.c` and `native_world.c` at `-O2`,
   `-Wdouble-promotion`. No libm in any loop: inline min/max/clamp, float to byte through a signed conversion
   (float to unsigned was a libgcc call), `fsrra` for 1/w, no `__ctzsi2`. `fminf`, `fmaxf`, `__fpclassifyf`, `sinf`, `cosf`
   are no longer linked.
2. Characters: bone matrices composed once per actor; per-part position and normal streams sorted by weight set (built at
   load); whole actor rejected by spheres around bone origins; each part rejected, or marked fully inside, by per-bone
   spheres before any skinning; only the weight sets of visible parts blended, projected (4 `ftrv`) and light-folded
   (lamps moved into each weight set's space once); positions on `re4dc_avk_pos_skin_u16`.
3. World: meshlets are at most 96 vertices already (histogram in evidence). Selection tests only the planes a parent box
   straddles; each strip group has its own staged vertex range (cross stages 7.6 k instead of 12.0 k vertices a picture);
   vertices staged once as TA vertices and copied per strip corner; inside meshlets take no tests, boundary meshlets test
   per strip and clip only strips that cross the near plane. The fixed cost per meshlet was a `memcpy` per pack field read
   (10,000 libc calls a picture) and a memory-clobbering store-queue flush: both gone. `render/stage_sh4.S` holds the
   world stage loop (two vertices interleaved, `movca.l` line allocation) and the actor strip emitter (64-bit pair moves).
   Headers are precompiled at load and sent only on change (unchanged from round 3). One idea measured and dropped: actor
   corners through a unique-corner stage (+0.3 ms, 48 KB stage misses).
4. Change flags: an unmoved camera keeps last picture's selection, order and placement matrices (cross world 3.6 ms on
   unmoved pictures, 5.6 to 9.9 moving). A HUD layout flag cost +0.14 ms because the widget state changes every picture,
   and was removed. Static light setup was already per change (fog table).
5. Baked visibility, below.
6. Arms, below.
7. Look, below.

Selection and setup (inside "World"): `native_prepare_world` 0.79 ms cross, 0.31 hay-fork (mean over moving and unmoved pictures).

## 2. Final image, timed pictures (25 per scene, as round 3) and Flycast replay

| Scene | Tier | Pictures | Mean ms | p99 ms | Worst ms (picture) | Over budget |
|---|---|---:|---:|---:|---:|---:|
| cross | MODELLED | 25 | 14.22 | 19.63 | 19.63 (1) | 25 over 7 |
| cross | Flycast guest timer | 600 | 11.22 | 14.90 | 15.81 (1) | 46 over 14 |
| hay-fork | MODELLED | 25 | 16.13 | 18.44 | 18.44 (83) | 25 over 7 |
| hay-fork | Flycast guest timer | 600 | 12.92 | 15.53 | 16.58 (95) | 68 over 14 |

Pictures: cross 1, 11, 23 ... 287 (picture 1 is round 3's Flycast-worst and the first, cold, picture); hay-fork 11, 23 ...
287 plus 61 (round 3's worst). Both include the moving-camera stretches (pictures 59 to 155). Mean by phase, MODELLED,
25 pictures: cross world 5.51, characters 6.20, PT 0.21, TR 1.43, effects 0.65, HUD 0.23; hay-fork 5.38, 7.01, 1.68,
1.09, 0.75, 0.22. Against the proposed split (world 5, characters 6, effects+HUD 1.5, selection 1.5): characters and
world are at the split, translucent (hair, foliage) and the per-picture input decode (0.30) are not budgeted.
Per-picture rows: `evidence/final/{cross,hayfork}/timed-pictures.csv`.

## 3. Top 10 functions, MODELLED, ms a picture (24 pictures)

| Cross world | ms | Cross characters | ms |
|---|---:|---|---:|
| m1_stage_world | 1.39 | native_actor_pass | 2.77 |
| copy_strips | 0.89 | m1_emit_actor_strip | 1.74 |
| native_prepare_world (selection, inlined) | 0.79 | re4dc_avk_pos_skin_u16 | 1.09 |
| stage_range (boundary meshlets, C) | 0.64 | emit_part | 0.30 |
| clipped | 0.40 | native_shadows | 0.09 |
| native_piece | 0.34 | model_lights | 0.07 |
| clip_strips | 0.30 | column_scale | 0.05 |
| native_update (input decode) | 0.30 | memmove | 0.02 |
| native_world_pass | 0.10 | projection_grid | 0.01 |
| compose | 0.06 | sq_fast_cpy | 0.01 |

| Hay-fork world | ms | Hay-fork characters | ms |
|---|---:|---|---:|
| m1_stage_world | 1.83 | native_actor_pass | 3.34 |
| copy_strips | 1.11 | m1_emit_actor_strip | 1.83 |
| clipped | 0.61 | re4dc_avk_pos_skin_u16 | 1.12 |
| stage_range (boundary meshlets, C) | 0.45 | emit_part | 0.30 |
| clip_strips | 0.34 | column_scale | 0.11 |
| native_update (input decode) | 0.33 | native_shadows | 0.09 |
| native_prepare_world | 0.31 | model_lights | 0.07 |
| native_piece | 0.21 | memmove | 0.02 |
| native_world_pass | 0.07 | sq_fast_cpy | 0.01 |
| compose | 0.04 | pvr_prim | 0.01 |

`native_actor_pass` holds the inlined bone composition, sphere tests, weight-set blend, light fold and normal lighting
(per-line: blend 0.38, light fold 0.45, normals 0.21 at the cross). Store-queue bursts are about 14 cycles each in the
model, so the corner copies are near their floor (world about 30 cycles a corner, actors about 34). Full tables with
cache and stall columns: `runs/e0fin-{cross,hayfork}/{full,world,characters}/functions.txt`.

## 4. Baked visibility (step 5)

- Offline: `bench/bake_vis.c` (host, 10 s a room). Camera cells 500 mm square over the route. For each visited cell, depth
  renders of the opaque world (6 faces, 192 px) from a 4 x 4 x 2 sample grid plus every route camera in the cell. Hidden:
  cluster instances (placement x cluster; cross about 110 of 549, farm about 85 of 300) and 2 m actor cubes. Queries are
  dilated 60 mm and pass on depth ties. Table files `CROSS.VIS` (89,004 B) and `FARM.VIS` (52,436 B) beside the packs.
- Runtime: hidden clusters skip selection; an actor is skipped when every cube its bone-sphere box touches is hidden (the
  barn props behind the wall at the hay-fork view). Hay-fork worst went 31.35 to 18.23 ms MODELLED.
- Check (Flycast, all 300 pictures, both scenes): full set (`/cd/NOVIS`) vs culled: 0 pictures differ by more than 16
  levels. Run-to-run noise of the harness (full vs full) is 1 to 15 levels on about 90 pictures, so 16 is the threshold.
- Control: a table with the most route-visible cluster instance of each cell marked hidden: caught, cross 46 pictures,
  farm 300 pictures. Evidence: `evidence/vis/*.json`, `build/vis*/`.

## 5. Survey arms (step 6), MODELLED, run-time boot options in one image

| Arm | Cross mean / worst | Hay-fork mean / worst |
|---|---:|---:|
| 0 (default): one stage loop per vertex, SH-4 asm | 13.90 / 18.45 | 15.93 / 18.33 |
| (a) world stage in operand-cache RAM (`/cd/ARMA`: `dcache_toggle_ocram`, 8 KB `__ocram` stage; model run with `--oc-kb 8` and OCRAM as one-cycle RAM) | 14.19 / 18.89 (+0.29) | 16.12 / 18.60 (+0.18) |
| (b) three short loops over 32-vertex blocks (`/cd/ARMB`, C) | 15.35 / 21.05 (+1.45) | 18.46 / 21.07 (+2.53) |

The model halves the data cache for everything else under arm (a); the console decides. ISOs:
`build/bench-e0s6a-arma*.iso`, `bench-e0s6a-armb*.iso` (same code as the final image apart from step 7).

## 6. RAM per room (Flycast, measured after load, final image)

| Room | Whole world (pack) | World runtime added at load | Textures (pack copy; resident in VRAM) | Model catalogue | Recorded inputs (bench only) | Visibility table | Live input scratch |
|---|---:|---:|---:|---:|---:|---:|---:|
| cross | 1,424,536 | 624,474 | 1,860,520 | 289,556 | 4,155,912 | 89,004 | 86,260 |
| hay-fork | 1,089,740 | 495,286 | 1,908,716 | 899,604 | 5,230,236 | 52,436 | 117,488 |

World runtime = staged-order remap (2 B a staged vertex), TA colours (4 B), group ranges and meshlet records
(cross 97,979 staged vertices, 4.5% duplicated across groups; farm 79,169). Heap in use after load: cross 10,149,028 B,
farm 10,275,908 B, of which the shared pack buffer is 9,134,836 B; the rest (actor runtime streams, world runtime,
visibility, input scratch) is 1.01 MB cross and 1.14 MB farm. Static span from the boot address 1,229,052 B (up from
1,016,220: actor pools, 8 KB stage). Total about 11.5 MB of 16 MB in both rooms. VRAM free 3,093,064 B cross, 3,024,072 farm.
Against the engine map (4,096 KB room pack): world + world runtime + models + visibility = 2.43 MB cross, 2.54 MB farm,
within it; textures belong to the VRAM row. The recorded inputs are the bench's logic stand-in and are not engine RAM.

## 7. Look (step 7) and still pairs

Still pairs at all 25 timed pictures per scene, source capture | E0 bench, labelled with the MODELLED ms:
`evidence/final/{cross,hayfork}/pairs/NNN.png`. Probes and calibration: `evidence/look/`.
- Fixed: the knife blade beside the handgun was Leon's role-2 part (the knife in hand, probe `weapon-zoom.png`); it is no
  longer drawn (the game shows it only in the knife stance, which the recorded inputs do not carry).
- Improved: actor lighting. The round 3 linear fold was 1.4x to 2.2x brighter than the source on Leon. A clamped
  per-lamp form was tried and was too directional (0.38x to 1.07x); the linear fold scaled by 0.42 gave the lowest error
  (frame MAE 8.81 against 10.4 to 10.7, Leon-region ratio 0.66x to 1.37x over six pictures). Owner look approval pending.
- Not fixed: Leon's hair (the role-7 hair part draws as a smooth cap: it needs the masked hair pair, colour texture plus
  alpha mask, combined at bake time); the HUD mask (widgets carry a mask texture key that the single-texture draw ignores:
  needs a baked composite or a two-pass mask) and the ammunition readout (the count is not in the recorded HUD inputs:
  needs the capture switch to record it). Leon is drawn in front of the barn post at hay-fork picture 61 as in round 3.

## 8. Gates and controls (final image)

| Gate | Result | Control |
|---|---|---|
| Clean build | clean checkout of `e28d7f2c2` builds; boot bytes equal the staged `1ST_READ.BIN` | missing pack: build stops with "M1 missing native packs in PRIVATE_PACK_DIR" |
| Replay | standard GDEMU disc: cross 600 then farm 600 pictures, no fault (Flycast) | corrupt frame list (out-of-range camera reference, valid CRC): refused at load, stage 91 |
| Timing rows | guest-timer rows as above | 5 ms busy-wait (`/cd/DELAY5`): +5.001 ms median, +5.005 mean over 600 cross pictures |
| Baked visibility | 0 of 300 pictures differ in both scenes | wrong table entry caught (cross 46, farm 300 pictures) |
| Still pairs | 25 per scene at the timed pictures | owner look approval pending |
| Memory | section 6 | |

## 9. Deliverables

- Staged disc: `E:\RE4DC-Lanes\eng-e0\build\E0-GDEMU-e0fin\disc.gdi` with `SHA256SUMS` beside it:
  disc.gdi `025516557d49e1835e7eb8571e09244b64db190cf3981ead555c54b1924ca19f`,
  track01.bin `8ffad7e33ae944b2e63a4bed060cfe64732afb8361a4ed79b411b179dd43b1af`,
  track02.raw `15453e38e9c8e03d6e7854c2414f93e944b6059b4933847ebf735834407cec48`,
  track03.bin `5ec2b260d7dda2b462d807d5ab7eb348fe81e547b8b706c6efecd787c683ad65`.
  Boot (1ST_READ.BIN) `5068d91916fdfca3f562cbcc690d051342ac5d7fb76aff293a15ee99ccc61918`. Boot options on the disc: none
  (default arm 0, visibility on). Arm and control ISOs in `build/` (`bench-e0fin-delay.iso`, `bench-e0fin-bad.iso`,
  `bench-e0s5a-{full,bad}-*.iso`, `bench-e0s6a-arm{a,b}*.iso`).
- Code: `lane/eng-e0`, renderer `e28d7f2c2`. Private packs, tables, discs and captures stay in this folder.
- Evidence: `E:\RE4DC-Lanes\eng-e0\evidence\` (final, vis, look), runs under `runs\`, log `STATUS.md`.

## 10. Not done

- Cross at or under 7 ms MODELLED: not reached (14.2). The remaining time is spread: world stage and copies (about 3 ms),
  actor skinning and emission (about 5.6 ms), selection (0.8), clipping (0.7), translucent world and hair (1.4), input
  decode (0.3). The next levers are content items from plan section 6 (world and character distance levels, which would
  cut the vertex counts the kernels are already near the floor on) and a console profile.
- Console numbers: none (the next step).
- Hair, HUD mask and ammunition readout: see section 7 (bake and capture changes).
- The visibility table covers the cells the recorded route visits; other cells draw everything.
- Arm (a) is modelled with a simple OCRAM rule added to the observer (`bench/model_profile.py`); how much the halved data
  cache costs on hardware is the console's question.
