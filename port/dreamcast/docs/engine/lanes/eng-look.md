# eng-look hand-back (E0 look items and content candidates for the owner), 2026-11-19

Lane `eng-look` on `lane/eng-look` from `origin/engine` 4108bf18b (renderer = eng-e0b). Final image `lkg`, code commit
**26c3746c8** (pushed; the lane doc follows in the next commit). Tiers: **MODELLED** = nominal 200 MHz SH-4 hwsim over
Flycast hwtrace, the same tool, windows and pictures as eng-e0 / eng-e0b (24 regular pictures 11..287 plus cross 1 /
hay-fork 61, 25 per room); **Flycast** = standard-harness stills or guest timer. No console number exists. No step is
a default: every step is a run-time arm (`c0.L2`), step 0 is today.

**Result.** Hair fixed; the pyre glow built as an approximation (the capture cannot rate it); visibility re-baked with
conservative occluders (unseen-route misses 8 pictures -> 1 picture, 1 pixel); the light-pick test has a failing
control. Five content candidates, three steps each, with MODELLED tables, MAE against step 0 and a contact sheet per
step. The look work costs about 1 ms MODELLED at step 0 (Leon's hair layer). In these two scenes only character
levels (step 3: -0.45 / -0.48 ms) and the effect cap (-0.04 ms) buy time with no visible change; the world cap buys
0.4 to 3 ms but leaves holes; cards and baked lighting buy nothing here (the props they act on are tiny or hidden).

## 1. Look items, before and after

Flycast stills of the final image against the source capture (the old port running the game, eng-bench capture), the
25 timed pictures per room: MAE in RGB levels, and the share of pixels with any channel over 16.

| Build | Cross MAE | Cross >16 | Farm MAE | Farm >16 |
|---|---:|---:|---:|---:|
| e0b (before) | 8.60 | 21.0% | 6.20 | 14.1% |
| lkg with the glow off (`.G0`, same boot) | 8.47 | 20.7% | 6.00 | 13.8% |
| **lkg (after)** | **8.46** | **20.7%** | **6.00** | **13.8%** |

| Item | State | Evidence |
|---|---|---|
| **Leon's hair** | **fixed** | The bench drew the hair part with the hair image over the part's body-atlas UVs, alpha-tested: most of it was cut away and the scalp showed. Now as the source: the hair part with the body atlas (opaque), then the PS2 hair run (pack role 8: same positions and weights, the hair UVs, the hair colour image with its mask in alpha) blended in the translucent list, no depth write; every PS2 Leon level carries its own run. `evidence/look/zoom-hair-095.png` (source / before / after). Cost: about +0.95 ms MODELLED in the characters row (the hair positions are skinned and lit a second time for the run's own part streams; 986 more corners) |
| **Pyre glow** | **built, approximate; owner call** | filter03, driven by effect 0x46 (colour rgb x a / 255 = 30, 19, 9 at the pyre, doubled by its TEV scale), blurs the frame's alpha at quarter size and adds it in that colour; the alpha comes from effects with Tool_flg 0x8000 and not 0x200000 (about 3.5 such sprites a picture at the cross). Here each is drawn once more, additive (source alpha, one), 1.25 x its size, with a baked white texture of its blurred alpha (32 texels a side, 264 KB VRAM at the cross); overlapping glow sprites share their weight. Switch `.G0`. **The capture cannot rate it:** the source capture is the old port, whose GX immediate draws are stubs (`gx_stub.cpp` GXBegin, GXCopyTex), so it never drew filter03 (MAE 8.47 -> 8.46). The pyre still differs from the capture in the effect sprites themselves (flame core darker), not in the frame glow. Also from the source: effect colour x 4 with Tool_flg 0x80 and alpha x 4 with 0x20000 unless 0x40. `evidence/look/zoom-pyre-001.png` (source / before / glow on / glow off) |
| **Unseen-route visibility** | **improved, one pixel left** | VIS3: 48 eyes a cell (was 27), queries dilated 150 mm (60), conservative occluders (each depth pixel takes the farthest of its 3 x 3 neighbours, so an opening narrower than a pixel still shows what is behind it); 256 KiB budget kept (cross 256,212 B, farm 257,164 B); bake 31.4 / 15.7 min, 6 jobs. Threshold 9, full vs culled in one boot, 300 pictures: route 2 (unseen) cross **1 picture, 1 pixel, delta 17** (was 8 pictures, peak 99), farm 0; route 1 cross 0, farm 1 picture 1 pixel delta 17 (unchanged since e0b). Both single pixels sit inside a ground texture with no object missing (`evidence/vis/pixel-lkg-*.png`): a depth tie with a hidden cluster, not a seen object. Wrong-entry controls caught on 287 / 300 / 88 / 76 pictures (route 1 cross, farm; route 2 cross, farm). Hidden per route picture 76 / 62 instances (VIS2 77 / 67) |
| **Light-pick control** | **done** | Window flag `p`: the engine walks the room's lights backwards. Normal: cross 0 of 698 picks differ, farm 2 of 752. Control: cross 698 of 698, farm 752 of 752. Caught (`runs/lkg-look-*/lightpick-*.json`) |

## 2. Content candidates (MODELLED ms, 25 pictures per room; MAE vs step 0 over the same pictures, Flycast stills)

Step 0 (image lkg): **cross 17.34 mean / 23.22 worst (picture 1); hay-fork 19.56 / 22.09 (picture 83)**; all 25 over
14 in both rooms. Phases cross: setup+world 5.88, characters 8.83, PT 0.21, TR+hair 1.46, effects 0.62, HUD 0.33.
Contact sheets: `E:\RE4DC-Lanes\eng-look\evidence\contact\<step>.png` (1600 px wide, six pairs: the three timed
pictures per room that differ most from step 0, each labelled with room, picture and both MODELLED times).

**L, character distance levels** (PS2 levels where they exist: Leon A / lg65 / bd70 / u70, Ganado today / g85 / g70 /
g55, from the old port's LEON_LOD / GANADO_LOD packages; rigid fewer-bone variants for Ganado level 3 and the
34-bone props; projected radius with 10% hysteresis. Step 1: level 1 < 160 px, level 2 < 60. Step 2: 320 / 120 / 50.
Step 3: 480 / 160 / 70, rigid < 100.)

| Step | Cross mean / worst | Farm mean / worst | MAE cross / farm |
|---|---|---|---|
| 1 | 17.35 (+0.01) / 23.23 | 19.49 (-0.08) / 22.08 | 0.001 / 0.008 |
| 2 | 17.35 (+0.01) / 23.23 | 19.41 (-0.15) / 21.97 | 0.000 / 0.013 |
| 3 | 16.89 (-0.45) / 23.23 | 19.08 (-0.48) / 21.97 | 0.008 / 0.015 |

Only one Ganado is drawn at a time in these scenes (the far ones are culled); Leon takes lg65 at step 3 (404 of 600
pictures at the cross: the legs, mostly off screen). The rigid variants are never reached here.

**W, world distance cap and level shift** (step 1: one level coarser past 20 m; step 2: two levels past 15 m and at
most 48 pieces past 15 m; step 3: two levels past 10 m, at most 24 pieces past 10 m; ranked by projected size, 25%
hysteresis. A placement cap and an all-pieces cap were tried first and removed the ground / the pyre's post.)

| Step | Cross mean / worst | Farm mean / worst | MAE cross / farm |
|---|---|---|---|
| 1 | 17.35 (+0.00) / 23.22 | 19.57 (+0.00) / 22.10 | 0.001 / 0.000 |
| 2 | 16.96 (-0.38) / 22.36 | 18.01 (-1.56) / 21.19 | 0.186 / 1.424 |
| 3 | 15.16 (-2.18) / 20.37 | 16.48 (-3.08) / 19.68 | 3.579 / 5.527 |

**P, far props as flat cards** (8 views baked from the prop's first recorded pose, 256 x 128 atlas; cylindrical
punch-through billboard lit by one colour; step 1 < 24 px, step 2 < 48, step 3 < 96)

| Step | Cross mean / worst | Farm mean / worst | MAE cross / farm |
|---|---|---|---|
| 1 | 17.31 (-0.04) / 23.00 | 19.57 (+0.01) / 22.17 | 0.000 / 0.000 |
| 2 | 17.31 (-0.04) / 23.00 | 19.57 (+0.01) / 22.17 | 0.001 / 0.000 |
| 3 | 17.31 (-0.04) / 23.00 | 19.52 (-0.05) / 22.05 | 0.000 / 0.000 |

Cards replace only tiny props here (cross one 9 px prop, farm the 7 small one-bone props at step 3); the 34-bone barn
props are hidden by visibility. Cost: farm 0.86 MB of VRAM for 13 atlases.

**E, effect density cap** (step 1: drop sprites under 1.5 px and alpha under 3; steps 2 / 3: also keep only the 64 /
32 largest by area x alpha, 25% hysteresis)

| Step | Cross mean / worst | Farm mean / worst | MAE cross / farm |
|---|---|---|---|
| 1 | 17.30 (-0.04) / 23.21 | 19.52 (-0.04) / 22.10 | 0.008 / 0.002 |
| 2 | 17.30 (-0.04) / 23.21 | 19.53 (-0.04) / 22.09 | 0.008 / 0.002 |
| 3 | 17.30 (-0.04) / 23.20 | 19.53 (-0.03) / 22.12 | 0.059 / 0.003 |

About 12 sprites a picture are dropped at the cross by step 1; the cap of 64 never binds; 32 drops 3 more.

**B, baked static lighting** (the world already uses baked vertex colours; step 1: props whose pose has not changed
reuse their lit colours until the lights change; step 2: frozen at first sight; step 3: also every actor under 100 px
re-lit every 4th picture)

| Step | Cross mean / worst | Farm mean / worst | MAE cross / farm |
|---|---|---|---|
| 1 | 17.37 (+0.03) / 23.27 | 19.60 (+0.03) / 22.12 | 0.001 / 0.001 |
| 2 | 17.34 (-0.01) / 23.25 | 19.54 (-0.02) / 22.07 | 0.001 / 0.001 |
| 3 | 17.34 (-0.00) / 23.25 | 19.55 (-0.02) / 22.07 | 0.000 / 0.001 |

## 3. Recommended lowest step per candidate

| Candidate | Recommend | Why |
|---|---|---|
| L character levels | **step 3** | -0.45 / -0.48 ms MODELLED, no visible change on any sheet (MAE 0.015 at most) |
| W world cap and level shift | **none of these (step 0)** | Step 1 changes nothing; step 2 leaves holes in the farmhouse (sheet W2), step 3 removes it. Worth a rework: cap whole placements past the distance, or shift only clusters that have levels |
| P far-prop cards | **step 0 for now** | No gain in these scenes and 0.86 MB VRAM at the farm; revisit in a scene with mid-distance props |
| E effect cap | **step 2** | -0.04 ms with no visible change; step 3 drops flame sprites on the hanging body (sheet E3) |
| B baked lighting | **step 0** | No gain here; step 1 costs +0.03 ms (hashing) |

## 4. Gates and controls (image lkg)

| Gate | Result | Control |
|---|---|---|
| Clean build | clean checkout of 26c3746c8 builds; boot bytes e9b3cba4... equal the staged 1ST_READ.BIN | missing pack stops the build |
| Arms in one boot | every window of a schedule carries its own steps (`c0 c0.L1 c0.L2 c0.L3`: all runs above) | unknown arm `c0.Z1` refused, stage 94, nothing runs |
| Replay | 600-picture windows, all arms, no fault (Flycast); staged-disc schedule: section 5 | corrupt frame list refused, stage 91 |
| Timing | MODELLED tables above; staged disc delay window: section 5 | 5 ms delay window and held picture 300 (c0dh) |
| Visibility | unseen route at threshold 9: cross 1 picture / 1 pixel, farm 0 | wrong entry caught 287 / 300 / 88 / 76 |
| Light pick | 0 / 698 and 2 / 752 | backwards pick caught 698 / 698, 752 / 752 |

## 5. The staged disc

`E:\RE4DC-Lanes\eng-look\build\E0-GDEMU-lkg\` (KEEP and SHA256SUMS inside): disc.gdi
`025516557d49e1835e7eb8571e09244b64db190cf3981ead555c54b1924ca19f`, track01.bin
`8ffad7e33ae944b2e63a4bed060cfe64732afb8361a4ed79b411b179dd43b1af`, track02.raw
`15453e38e9c8e03d6e7854c2414f93e944b6059b4933847ebf735834407cec48`, track03.bin
`3c4dbc24e3558423ea5ac7d090a99eb770854e91dfdc9dd141bf2ca0cf349cea`. Boot 1ST_READ.BIN
`e9b3cba4c294938f9cada76bdc79b8e9e19f4b11c7a8e699d03277c3be0fcd83` (clean checkout reproduces it).

One boot runs 24 windows of 600 pictures (about 6 minutes): the E0 arms `c0 f0 ca c0 cb c0 fa f0 fb f0`, every
candidate's step 3 against step 0 `c0.L3 c0 c0.W3 c0.P3 c0.E3 c0.B3 c0 f0.L3 f0.W3 f0.P3 f0.E3 f0.B3 f0`, then the
controls `c0dh`. The screen shows the last 16 windows (the step is printed after each line); serial and memory rows
as eng-e0b, plus per window `m1_content_counts` and `m1_lod_models`. Any other mix: `/cd/SCHEDULE.TXT` (`c0.L2` etc.).

Flycast guest timer, whole schedule (drawing ms, 600 pictures, mean / worst, pictures over 14):

| Window | Cross | Farm |
|---|---|---|
| step 0 | 12.91 / 17.80, 172 | 15.15 / 20.03, 600 |
| L3 | 12.65 / 19.13, 172 | 14.73 / 18.93, 502 |
| W3 | 11.27 / 15.71, 30 | 12.65 / 15.98, 80 |
| P3 | 12.87 / 17.98, 86 | 15.11 / 19.03, 600 |
| E3 | 12.87 / 19.27, 168 | 15.12 / 19.71, 600 |
| B3 | 12.90 / 17.82, 171 | 15.13 / 18.69, 600 |
| arm a / arm b | 12.91 / 13.73 | 15.16 / 16.62 |

No picture over 33.3 ms and no presented interval over 2 fields in any window; control window c0dh: 17.92 mean
(+5.0 ms on every drawing row, 600 over 14) and one interval of 4 fields at picture 1 of lap 2. Memory guard intact
(no stage 93). Run: `runs/lkg-standard/`.


## 6. Not done

- The unseen-route check is not zero: one pixel on one picture (delta 17) at the cross, one at the farm (since e0b),
  both inside a ground texture; not chased further.
- Hair costs about 1 ms MODELLED: the hair run re-skins and re-lights the hair part's positions. Sharing the hair
  part's projected positions would remove most of it (not built: a second model round).
- The glow cannot be validated against the capture (the old port never drew it); the flame core still differs from
  the capture in the effect sprites themselves.
- World cap: no acceptable step built (see section 3).
- Cards are baked from the first recorded pose (animated props would freeze) and lit by one colour.
- No console numbers (the next step).
- Contact sheets are 3.5 MB PNGs each (1600 x 4074).
## How the steps are selected (one image, one boot)

- Every window of the bench's schedule names its room, its arm and, after a dot, content steps: `c0.L2`, `f0.W3.E1`.
  Items: L character distance levels, W world distance cap and level shift, P far props as cards, E effect density
  cap, B baked static lighting (steps 0-3, 0 = today), G the frame-alpha glow (1 = on, the default; `.G0` off),
  flag `p` = the light-pick test's control. `/cd/SCHEDULE.TXT` holds one line of tokens.
- An unknown token, flag, item or step refuses the whole schedule (stage 94, `SCHEDULE REFUSED at character n`):
  nothing runs. Control: `c0 c0.Z1`.
- Default schedule of the staged disc (24 windows, about 6 minutes): `c0 f0 ca c0 cb c0 fa f0 fb f0` (E0 arms),
  `c0.L3 c0 c0.W3 c0.P3 c0.E3 c0.B3 c0` and `f0.L3 f0.W3 f0.P3 f0.E3 f0.B3 f0` (each candidate's lightest step
  against step 0 in the same boot), then `c0dh` (the delay and held-picture controls).
- Per window the bench now also keeps `m1_content_counts[8]` (actors at level 0-3, rigid variants, cards, glow
  sprites, pieces or sprites dropped by a cap) and `m1_lod_models[64][6]` (per base model: level 0-3, rigid, card),
  printed on the WINDOW serial line.

## Files

- `render/content.h`: the step table (`m1_content`), counters.
- `render/content_actor.inc` (included by native_actor.inc): variant table (`LODV`, `CARD` in pack section 14
  after the sky words), level pick by projected size with hysteresis, baked-lighting cache, cards.
- `render/content_world.inc` (included by native_draw.inc): level shift setup and the distance cap.
- `render/content_fx.inc` (included by native_layers.inc): effect TEV scale, glow, density cap.
- Narrow hooks in `native_actor.inc` (hair pass role 8, variant pick, card branch, lighting cache), `native_draw.inc`
  (two lines), `native_layers.inc` (effect loop), `native_world.c` (level shift, one line), `native_scene.inc`
  (section 14 tail, glow header validation), `source_light.inc` (pick control).
- Bake: `native_models.py` (hair layer, PS2 levels, rigid variants), `native_pack.py` (variants, glow headers,
  cards), `native_cards.py` (card renderer). Bench: `main.c` (schedule grammar, 24 windows), `bake_vis.c`
  (`--eyes`, `--margin`, `--erode`).
