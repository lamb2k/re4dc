# eng-e0b hand-back (milestone E0: make the bench correct and console-ready), 2026-11-19

Lane `eng-e0b` on `lane/eng-e0b` from `origin/engine` 4e93e03a9 (renderer e28d7f2c2). Final code commit: see section 9.
Tiers: MODELLED = nominal 200 MHz SH-4 hwsim over Flycast hwtrace (same tool and windows as eng-e0); Flycast = guest
timer in the standard harness; no console number exists. Look numbers are Flycast stills against the source capture.

**Result.** Every audit item was worked; five are fixed, three partly (visibility on one unseen route, look parity,
counter calibration needs the console). The fixes cost drawing time: cross 14.22 -> 16.31 ms mean MODELLED, hay-fork
16.13 -> 18.78 (the source lighting rule is most of it). The staged disc measures a correct picture and reports every
raw row on screen, serial and in memory.

## 1. Per audit item

| Audit item | State | Evidence |
|---|---|---|
| Near-plane clipping error (s4) | **fixed** | `render/part_cull.h`: every sphere is tested while "out" or "inside" is still possible. `bench/test_part_clip.c` against the strip check: straddling two-bone part classed boundary (41 corners behind near); 20,000 random multi-bone parts, 0 disagreements. Control (E0 loop, `-DM1_PART_LOOP_E0`): straddle classed inside, 15,617 disagreements, FAIL. `evidence/clip-test.txt` |
| Unknown cells and heights draw everything (s2) | **fixed** | VIS2 cells carry a camera height band; outside the grid, unbaked cells and heights outside the band take the full set. Route 2 states: cross 214 mask / 86 height fallback; farm 247 / 21 height / 32 unbaked |
| Table fits a whole room (s2, s6) | **fixed** | 256 KiB budget: cross 258,004 B, farm 256,016 B (section 4) |
| Bake the whole reachable area (s2) | **fixed** | Domain from the room's geometry (floors, on-foot reachability), not the route; the route is only reported |
| Unseen route, threshold 9, control caught | **partly** | Farm 0/300; cross 8/300 (1-2 pixels each, peak delta 99, pictures 56-63 and 118). Wrong-entry controls caught on both routes (section 4) |
| Look parity (s5) | **partly** | MAE 9.89 -> 8.60 cross, 7.72 -> 6.20 farm; >16: 25.7% -> 21.0%, 17.7% -> 14.1% (section 3). Lighting rule, HUD mask, ammo readout, weapon by stance, effect blends: done. Pyre glow (filter03) and hair look: not |
| Console-ready measurement | **fixed** (counter split: **partly**) | Raw rows every picture, thresholds 14 / 33.3, presented-field intervals, A/B/A arms in one boot, delay and held-frame controls (section 6). Counter events added with a boot calibration; Flycast has no counters, so which event shows store-queue waiting is a console reading |
| Memory map (s6) | **fixed** | Texture copies no longer in RAM (resident buffer 9,134,836 -> 7,253,312 B); stack guard and high water; RAM and VRAM maps with 0 overlaps (section 5) |
| Prop roster (s1) | **not** (requirement written) | Section 7 |

## 2. 25-picture MODELLED table, before (e0fin) and after (e0b)

Pictures: cross 1, 11, 23 ... 287; hay-fork 11, 23 ... 287 and 61 (trace indices fixed: picture = timing row + 1).

| Scene | Build | Pictures | Mean ms | p99 ms | Worst ms (picture) | Over 7 | Over 14 |
|---|---|---:|---:|---:|---:|---:|---:|
| cross | e0fin (before) | 25 | 14.22 | 19.63 | 19.63 (1) | 25 | 14 |
| cross | e0b (after) | 25 | 16.31 | 22.03 | 22.03 (1) | 25 | 22 |
| hay-fork | e0fin (before) | 25 | 16.13 | 18.44 | 18.44 (83) | 25 | 25 |
| hay-fork | e0b (after) | 25 | 18.78 | 21.10 | 21.10 (83) | 25 | 25 |

Phase means after (before), MODELLED ms: cross setup+world 5.70 (5.51), characters 7.88 (6.20), PT world + hair 0.54
(PT 0.21; hair was in TR), TR 1.11 (1.43), effects 0.70 (0.65), HUD 0.38 (0.23). Hay-fork 5.50 (5.38), 9.30 (7.01),
2.07 (1.68), 0.72 (1.09), 0.81 (0.75), 0.38 (0.22). What each fix cost: source lighting +1.7 ms cross / +2.3 farm
(up to 8 lights per weight set, per-normal loop); HUD two-pass order and masks +0.15; VIS2 select and decode +0.2.
The clipping fix moved no measurable time. Rows: `evidence/timed/{cross,hayfork}-e0b.csv`, `evidence/timed/e0b.md`.

Flycast guest timer, 600 pictures, staged disc, default arm: cross 12.40 mean / 16.15 p99 / 17.25 worst (picture 1,
lap 1), 62 over 14, 0 over 33.3 (e0fin: 11.22 / 14.90 / 15.81, 46). Farm 14.66 / 17.83 / 18.20 (74, lap 1), 503 over
14, 0 over 33.3 (e0fin 12.92 / 15.53 / 16.58, 68).

## 3. Look

Source capture (game, Flycast) against the bench still at the 25 timed pictures per scene:

| Build | Cross MAE | Cross >16 | Farm MAE | Farm >16 |
|---|---:|---:|---:|---:|
| e0fin (before) | 9.89 | 25.7% | 7.72 | 17.7% |
| source lighting rule | 8.79 | 21.4% | 6.38 | 14.4% |
| e0b (final) | 8.60 | 21.0% | 6.20 | 14.1% |

Pairs: `evidence/look/e0b/{cross,hayfork}/NNN.png` (before: `evidence/look/before/`), numbers `look-e0b.json`.
- **Lighting**: the global 0.42 scale and top-three shortcut are gone. `render/source_light.inc` applies setModel2's
  selection (alive, kind mask xF vs EnableMask or parent, Type 4 skipped, kind on, SelectMask, colour, light-volume
  hit, 8 cap in array order) and LightSetModel's per-type light (constant, linear, quadratic, spot, parallel, spot
  quadratic, local ambient), ambient by mask plus AddAmb, GX diffuse clamp, material colour x TEV scale. Test: the
  engine's pick against the game's own pick, 7,948 model-pictures, 10 differ (0.13%, farm only; the game's pick is
  from its previous draw). No failing control was run for this test.
- **Capture** (the capture switch, extended): light array index, xF / Attribute / Priority / kind-enabled, spot A0
  and fade A1, parent; each model's light inputs; each effect's GX blend; the player's stance (PlGetWeaponNo). The
  recapture matches the eng-bench capture on every camera, actor record and still (300/300 per room, MAE 0.000).
- **HUD**: masked widgets use a texture baked from widget texture x mask alpha (`bake/dctex.py` decodes VQ / PAL4 /
  plain); masked backdrops first, deepest level first: the round ring and the ammunition digits now show (the digits
  were recorded all along; the ring covered them). Unlit digit segments read darker than the source.
- **Weapon**: Leon's knife part is drawn from the recorded stance (0x10 = knife in hand), not suppressed.
- **Effects**: each effect uses its own GX blend (16 + 4 additive records at the pyre). ID 0x46 is the screen
  filter driver (filter03 frame-alpha glow), never a sprite: still not drawn, so the pyre lacks its bright glow.
- **Hair**: the hair part already carries its mask in alpha; drawn alpha-tested. It still reads pale (scalp showing).

## 4. Visibility (VIS2)

Whole room, 2 m camera cells with a height band (floor + 0.7 to 2.8 m), on-foot reachability from the room's floors,
actor columns (2 m) over every floor column (the barn props stand where the camera never walks), 27 eyes per cell,
masks stored once (raw or run-length) and merged by intersection to the budget.

| Room | Grid / baked cells | Actor domain | Table | Budget | Kept after merge (instances / columns) | Hidden per route picture |
|---|---|---|---:|---:|---|---|
| cross | 83 x 64 / 4,022 | 13,267 cubes, 4,049 columns | 258,004 B | 262,144 | 92.8% / 73.9% | 77 of 549 instances |
| farm | 67 x 58 / 2,557 | 9,960 cubes, 3,084 columns | 256,016 B | 262,144 | 100% / 86.3% | 67 of 300 instances |

Bake 17.2 / 8.0 min (6 jobs, host). Pixel checks, culled vs full in one boot (Flycast stills, 300 pictures, any channel
over 9): route 1 (recorded) cross 0, farm 1 (picture 53, one pixel, delta 17); **route 2** (new camera path over ~36 m,
height +-0.9 m and a stretch 5 m up, a full turn; the bake never used any route): farm 0, **cross 8** (1-2 pixels on
pictures 56-63 and 118, peak 99: a small object seen through a gap the eye sampling misses). Controls (route cells
with their most-seen instance hidden): caught on 285 / 300 (route 1) and 88 / 76 (route 2) pictures. The barn props at
the hay-fork view are culled again (hay-fork picture 61: 20.68 ms MODELLED; with the first domain it was 45.5).
Evidence `evidence/vis/*.json`, tables `build/vis/`, controls `build/vis-bad*`, route 2 packs `build/route2/`.

## 5. RAM and VRAM map (Flycast, after room load = the low point; nothing is allocated while pictures run)

| | Cross | Farm |
|---|---|---|
| Program image (text..bss) | 0x8c010000-0x8c19a5dc (1.60 MB; 307 KB raw rows) | same |
| Heap blocks / overlaps | 115 / 0 | 185 / 0 |
| Pack resident buffer (no textures) | 7,253,312 | 7,253,312 |
| World runtime / logic state / actor runtime / visibility | 624,486 / 88,964 / 120,400 / 258,588 | 495,298 / 121,488 / 381,080 / 256,448 |
| System (KOS) | 93,526 | 93,526 |
| Heap top (sbrk) / free to stack | 0x8c9a8000 / 6,586,368 | 0x8c9cf000 / 6,426,624 |
| Kernel stack / high water / guard | 0x8cff0000-0x8d000000 / 9,756 B / intact | same |
| VRAM: vertex buffers | 0x000000-0x100000, 0x400000-0x500000 (32-bit area) | same |
| VRAM: OPB, tile matrix, frame buffers | 0x100000-0x110680 / 0x1106c8 / 0x112300 and set 1 at +0x400000 | same |
| VRAM: PVR buffers end / textures (64-bit area) | 0x350600 / 0x350620-0x50dde0, 1,814,368 B in 324 | 0x350600 / 0x350620-0x51eb60, 1,888,608 B in 160 |
| VRAM free / overlaps | 3,088,904 / 0 | 3,019,912 / 0 |

Textures stream into VRAM through the start of the resident buffer at load; the buffer then holds only the rest of
the pack. Disc reads during play: none (each window's room is read before its first picture). Flycast-measured; the
console prints the same lines.

## 6. The staged disc and how its console report is read

`E:\RE4DC-Lanes\eng-e0b\build\E0-GDEMU-e0b\` (SHA256SUMS inside): disc.gdi `025516557d49e1835e7eb8571e09244b64db190cf3981ead555c54b1924ca19f`,
track01.bin `8ffad7e33ae944b2e63a4bed060cfe64732afb8361a4ed79b411b179dd43b1af`, track02.raw
`15453e38e9c8e03d6e7854c2414f93e944b6059b4933847ebf735834407cec48`, track03.bin
`0973ce1afa95fd34894b468bdf257024a18114846feeee5a429ffa934e659c06`. Boot `1ST_READ.BIN` `63a34ce8b34d9d4499c7467f0077fc0e7a4ef60d8fc1bf74d1e56686b382f13b`
(clean checkout reproduces it).

One boot runs 11 windows of 600 pictures: `c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh` (cross / farm; arm 0 default, a OCRAM
stage, b 32-vertex loops: A/B/A in the same boot; last window = controls: 5 ms delay in every picture and picture 300
held 40 ms). About 3 minutes. Then the summary stays on screen.
- **Screen**, one line per window: `cX m12.40 p16.15 w17.25@1/1 62|0 f0` = room, arm, flag (n/d/h), drawing mean, p99,
  worst @ picture/lap, pictures over 14 | over 33.3 ms, presented intervals over 2 fields.
- **Serial** (`printf`): `CALIB` (three loops x ten events), `MEM` / `VRAM` / `MEMBLK` per room, `WINDOW` per window
  (adds PVR wait mean, flips, worst interval with picture/lap, mean PRFC0), and one `ROW w picture draw_us wait_us
  fields ev25 ev1 ev1_id vis` line per picture (600 x 11).
- **Memory** (QA link or debugger): `m1_rows[16][600]` (8 words: draw us, wait us, fields, PRFC0 = 0x25 operand-cache
  freeze cycles, PRFC1, its event id rotating every 100 pictures over 0x28 0x0d 0x22 0x24 0x29 0x13, vis state, pad),
  `m1_windows[16][20]`, `m1_calib[3][10]`, `m1_mem[2][48]`; addresses in `build/e0b-symbols.txt`.
- **Reading the counters**: CALIB's store-queue-to-TA row against its cache-miss row says which event grows with
  store-queue waiting; ROW ev25 is the cache stall. Flycast reads 0 for every counter.
- **Controls on the disc**: window 10 must read about +5 ms on every drawing row and one interval of 3+ fields at
  picture 1 of lap 2 (Flycast: +5.02 ms, 600/600 over 14, one interval of 4 fields there). Flycast run of the whole
  schedule: `runs/e0b-standard/` (table in STATUS.md).
- Corrupt frame list (valid CRC) refused at load (`bench-e0b-bad.iso`, stage 91); missing pack fails the build.

## 7. Prop roster: what a live registry must supply (E1)

The bench still takes props from the first capture's picture-1 templates found again in RAM. A live engine needs:
an object table filled by the hosted code's spawn and kill setters (never by draw output); per entry a stable asset
id (bake-time content id of the ModelData, not an address or fingerprint), the pack's model index for that id, the
bone matrices from the skeleton service, the light inputs (shape, parts, EnableMask, SelectMask, offset, size,
material colour, TEV group, AddAmb: the same 17 words as stream 9), visibility and hidden flags, and attachment. The
bake must cover every model the room's object and spawn tables can create, keyed by that id, so a spawn never meets
an unknown type. The bench replay can then carry spawn/despawn events instead of a fixed list.

## 8. Gates and controls (final image e0b)

| Gate | Result | Control |
|---|---|---|
| Clean build | clean checkout of the lane builds; boot bytes equal the staged 1ST_READ.BIN | missing pack stops the build |
| Replay | staged GDEMU disc: 11 windows x 600 pictures, no fault (Flycast) | corrupt frame list refused (91) |
| Timing rows | section 6 | delay +5.02 ms on 600/600 drawing rows; held frame 4 fields at picture 301 |
| Near-plane test | PASS | E0 loop FAIL |
| Visibility | route 2 farm 0, cross 8 pictures (1-2 px); route 1 cross 0, farm 1 (1 px) | wrong entry caught 285 / 300 / 88 / 76 |
| Look | MAE and >16 before/after, pairs | owner look call pending |
| Memory | 0 overlaps, guard intact | a broken guard stops the run (stage 93); this control was not exercised |

## 9. Deliverables

- Code: `lane/eng-e0b` (pushed). Key files: `render/part_cull.h`, `render/source_light.inc`, `render/native_*`,
  `bench/main.c`, `bench/memmap.h`, `bench/bake_vis.c`, `bench/test_part_clip.c`, `bench/r3_inputs.inc`, `bake/*`,
  capture record in `src/game/esp.cpp`. Lane doc `port/dreamcast/docs/engine/lanes/eng-e0b.md`.
- Private (not in Git): packs `build/packs/`, tables `build/vis/`, capture `runs/cap-*`, disc `build/E0-GDEMU-e0b/`.
- Log `STATUS.md`; scripts `s/`.

## 10. Not done

- Pyre glow: filter03 (frame-alpha glow, ID 0x46) needs a render-to-texture pass; not built. The flame core is darker.
- Hair still reads pale; Leon's lit colour cannot exceed the texture (GX overbright x TEV scale beyond 1 is clamped).
- Unseen cross route: 8 pictures with 1-2 pixel misses. Next: denser eyes or a larger query dilation near openings
  (re-bake about 25 min) and the same check again.
- Counter split of cache stall and store-queue waiting: needs the console's CALIB rows.
- Light-pick test has no failing control yet.
- Prop roster stays seeded (section 7).
- The fixes add about 2 ms MODELLED; no speed work was done (not a speed round).
- Noted: `E:\RE4DC-Lanes\eng-bench\runs\{game003,logic005props2}-*\track02.raw` disappeared at 15:37 (not removed by
  this lane); the collector now uses this lane's zero filler track.
