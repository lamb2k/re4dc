# Lane eng-cloth2: the owner's skirt choice (option B) as the default

Status: **finished, unaudited** (2026-11-22). Branch `lane/eng-cloth2`, from `lane/eng-cloth1` 618cf5d43, merged with
`engine` fd79cc1db. Brief: H-032 ("Ok option B").

## What changed

- **Ashley's skirt runs two constraint passes; the original runs four.** This is the default, with no switch and no
  boot file. Every other chain keeps its passes.
  - `services/cloth/cloth.h` defines `CLOTH_IS_SKIRT` (48 links, 11 volumes, left neighbours, no right ones) and
    `CLOTH_SKIRT_PASSES` (2).
  - `cloth.cpp` `kernel_step` clamps the skirt's `Bundle_num` to it. This is the same rule as eng-cloth1's arm B.
- **The look arms are removed:** CLOTHCAP, CLOTHHALF, CLOTHFAR, CLOTHFAR0 and CLOTHPASS2. With them go:
  - their boot-file reading;
  - the kernel's capsule tests and held-tick step (`cloth_k_hold`);
  - `ClothKCap`, the `cap` / `nCap` fields and the chain's `phase` field.
  - No image keeps an arm symbol.
- **The PC reference runs the skirt the same way.** This is a reference change (H-017.8); its cause is the owner's
  look choice.
  - `hostref/svc/ref_skirt.cpp` wraps `PenClothMove` and `PenClothMove3` in the odump build (`--wrap`).
  - The wrapper gives the skirt two passes for the call and restores `Bundle_num` afterwards.
  - The original source is `src/game/pl_cloth.cpp` (Bundle_num = 4) and `pendulum.cpp`'s constraint loops; `src/`
    is not edited.
  - `SKIRT_PASSES=4` builds the old reference. `REF_VARIANT` ends in `-skirt2` / `-skirt4`, so a build folder from
    before this change is refused (make it fresh).
- **New control `RE4_SVC_CONTROL=skirtpass4`** (`cloth_control_skirt4`) puts the native skirt back at four passes.

## Checks

PC suites on e7bd1403e, run in `E:\RE4DC-Lanes\eng-cloth2\ev\pc-m1`, with a fresh reference build:

| Suite | Rows | Result | New rows |
|---|---|---|---|
| `refctl.sh` | 26 | every row as it must | five skirt rows (below) |
| `svc_controls.sh` | 80 | every row as it must | control `skirtpass4` on hill-ashley: FAIL as it must, 211459/240000 bones bit-identical |

The hill-ashley rows of `svc_controls.sh` compare native with the reference bit for bit, the skirt included:
240000/240000 bones with the wind off.

The five new `refctl.sh` rows, all on hill-ashley:

| Row | Must | Got | Detail |
|---|---|---|---|
| Native against the fixed reference | PASS | PASS | 240000/240000 bones bit-identical |
| Old reference (`SKIRT_PASSES=4`) against the fixed one | FAIL | FAIL | 211459/240000 bones bit-identical |
| Old against fixed, every bone but the skirt's 48 links (`svc_compare.py --skip-skirt`) | PASS | PASS | 211200/211200 bones bit-identical |
| Old against fixed, behaviour trace byte for byte | PASS | PASS | 4205 lines |
| Native at four passes (`skirtpass4`) against the old reference | PASS | PASS | 240000/240000 bones bit-identical |

The last row shows that the pass count is the whole difference between the old and new behaviour.

The other suites:

- `camcheck.sh`, `controls.sh` (18 rows), `outcome_controls.py` (35 rows) and `aim_check.sh`: every row as it must.
- `speed_controls.sh`: every row as it must. Its `clothbound` control on hill-ashley gives FAIL as it must
  (197120/240000).
- `cloth_key_test.sh`: the key gives PASS; both of its controls give FAIL as they must.

## Cost

Tier: **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**. Run on slot fly2, all three in one
session. Pictures 41 to 640, ms a picture, mean / p99 / worst.

The three builds:

- **Base** 849901182: 618cf5d43 merged with fd79cc1db, four passes. A local branch only, not pushed.
- **Base + arm:** the same build with the CLOTHPASS2 boot file.
- **Head** e7bd1403e.

The base and the head differ only in this lane's files.

| Scene | Build | Cloth | Services (9 ms row) |
|---|---|---|---|
| HILL | base | 5.31 / 5.56 / 5.62 | 13.73 / 15.66 / 17.20 |
| HILL | base + CLOTHPASS2 arm | 4.17 / 4.39 / 4.42 | 12.60 / 14.51 / 16.12 |
| HILL | **head** | **4.21 / 4.45 / 4.48** | **12.63 / 14.57 / 16.14** |
| LEON (village) | base | 1.58 / 1.66 / 1.69 | 5.66 / 7.39 / 10.11 |
| LEON (village) | head | 1.58 / 1.67 / 1.70 | 5.67 / 7.40 / 10.12 |

- **Hill:** the head saves 1.10 mean and 1.12 p99 on the cloth, and 1.10 mean on the services. eng-cloth1 measured
  4.21 / 4.39 for B.
- **The services row is still over its 9 ms on the hill:** 12.63 mean, 16.14 worst.
- **The head reads 0.03 to 0.06 ms dearer than the arm on the same tree.** LEON is 0.01 dearer too, where no code
  path changed. The likely cause is code placement after the removal, but this is not traced.
- **Village:** unchanged within 0.01 ms.
- **What the model cannot see:** the graphics chip's fill and sort time, vertex submission through the store queues,
  cache and bus contention, and real disc timing. The standard build reads the engine 3 to 10% kinder.

## Look

Flycast stills (plain, slot std2), not console. HILLS and LEONS, 36 still pairs.

| Comparison | HILLS | LEONS |
|---|---|---|
| Head against base | 17 of 19 stills differ; 219 differing pixels mean, 1051 max, median 21 | 6 pixels in 1 still |
| Head against base + arm | 0 in every still | 6 pixels in 1 still |
| Base against base + arm | same as head against base | 0 |

- **HILLS:** every differing pixel is on the skirt's hem. The stills with the most differences (pictures 80 and 200)
  were checked by eye. The bounding boxes are in `ev\px-head-vs-base.json`.
- **LEONS:** the 6 pixels are in picture 1 (tick 1), 4 to 9 levels each, five at the right screen edge. LEONS has no
  Ashley, and the PC check holds Leon's chains bit-identical, so this is not the skirt. It is not traced. The head is
  a different binary (`m1_state` moved from 8c110184 to 8c1100c4).

## Links

Images on the head, link check per image:

| Image | Original functions kept | Result |
|---|---|---|
| Default | 407 | SERVICE 0, PASS |
| BOSS | 501 | PASS |
| SENDABLE | 407 | PASS |
| FIGHT | 859 | SERVICE 30, FAIL |

FIGHT's result is identical to `engine` fd79cc1db with the same tool (same service list). The lane adds no original
function.

## Not done

- Nothing ran on the console; that run is deferred with the replatform.
- The LEONS tick-1 pixels and the 0.03 ms placement difference are not traced.
- The census build keeps the original's four passes for the skirt. It counts calls and is not a comparison.
