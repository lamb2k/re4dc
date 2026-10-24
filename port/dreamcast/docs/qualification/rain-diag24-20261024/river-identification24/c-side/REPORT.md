# First-stage river identification: bounded ambiguity

The current evidence does **not uniquely identify the user's scene**. `r100` is the strongest candidate only if “first stage” means the opening village-approach room: actual recovered room source contains bridge/ravine events and an explicit pond water-material setup. This is an evidence-backed candidate, not an assumption that the name means r100. If it means any Chapter 1/stage-1 river, r107, r10a and the later r10c/r10d/r10e channels remain distinct candidates. No arbitrary room has been selected for a runtime repair.

## Actual private-data inspection

Pinned source: `a7bffa9e318aa4143e97a32a5fbe7ae8e52838a1` in `/root/work/lanes/rain-diag24`, clean at inspection. Read all 29 actual PS2 AFS stage-1 room members r100 through r120: **107,802,720 bytes**, 0.622 seconds, 256 MiB address-space cap, 120-second command limit. The AFS table matches existing extraction provenance (`a7b0c37119f9ccabf8711ead7d83189065fe1d5df8c427cffe32022403ce3182`). Full ISO hash was not recomputed. Every member and EFF was hashed; all EFF record tables decoded with the existing bounded parser. Water-associated picture index and palette spans were hashed without conversion or asset output. `BINDINGS.json` records 18 actual source-file pins, 11 candidates' existing world SMD/TPL/material-index hashes and 428 existing effect-package bindings. All applicable existing extracted room-member hashes agree. r100 has an older independent source-input set, so no nonexistent extraction-manifest match is claimed.

Filter: world-rotated Esp08, one side >=5 m, texture f2/f7/fe/ef/c5. **This is a candidate superset, not a water classifier.** Dark f7 alone, noise and vertical c5 sheets can occur for other purposes. SST ambient and EST scripted counts stay separate. The exact private census is PS2-CENSUS.json; only its digest and compact hash metadata are preserved in Git.

| Room | Ambient SST / scripted EST candidates | Texture counts | Actual PS2 DAT SHA256 |
|---|---:|---|---|
| r100 | 0 / 0 | none | 75fe9de6fe15af37a454ae6d0a0667aec6a578a898afb5028bf79acf8b4b6441 |
| r106 | 1 / 0 | 0xf7:1 | b6a63ba847c8acd61132ff71bbb536037afafcf5be4ece50462e713a18da2cef |
| r107 | 2 / 0 | 0xfe:1, 0xf7:1 | 44cf88c5b7fd87fd414da97b7364dbff1178857006d8d6cdb698b7143af210bb |
| r108 | 2 / 0 | 0xfe:2 | 9fd0d93ec9e9a3bdd6ba9c65dabcc31cb1e8464a5559d26fd3d10ec702d9a414 |
| r10a | 4 / 0 | 0xfe:1, 0xf2:2, 0xf7:1 | a121349288f080ba5026ed3de218197366181952ad39269d219b9af1b21c6ed9 |
| r10b | 5 / 0 | 0xfe:2, 0xf2:2, 0xf7:1 | 34746c99c9140211c1927b1c31f3cad0780c2fc0d0b092b6f245a25b44536e3c |
| r10c | 14 / 4 | 0xc5:12, 0xef:3, 0xf7:2, 0xfe:1 | e72ce65989122f1c177f3767f1ade56f5a17e3e63eb79adc100e059a71ef7d40 |
| r10d | 4 / 0 | 0xfe:1, 0xf2:2, 0xf7:1 | e5f00bab2f5da831ed9a5d707e27662118669809cb6c9eabeba37d6e52d41db9 |
| r10e | 4 / 0 | 0xfe:2, 0xf7:2 | 6a2879d2686e677862eb15002d9a5c6ea9e22418c7b27a2e55075ed54f3e1d49 |
| r11a | 12 / 0 | 0xef:1, 0xf2:2, 0xf7:1, 0xc5:8 | 1c4a12c1ee60820c519cc588c6c50ba1767c16118a9cc4c6f110e0f263cf3fc6 |
| r11b | 13 / 0 | 0xfe:1, 0xf2:2, 0xf7:1, 0xc5:7, 0xef:2 | e8c8e01fd9b4a626a39ab2d1f2c625462384914ec5c164b50b1c6039c731389e |

## Ranked interpretation and code evidence

1. **r100, opening bridge/pond**: `src/st1/r100.cpp:193` invokes `setTexRender`; `:1429-1452` configures a 64x64 render target, blend source f7 and GameCube water objects 0 and 1. Bridge/ravine logic occurs at `:1366-1415`. Its actual PS2 EFF has **zero** filtered water rows, so “no Esp08 rows = no river” is false reasoning. This source is recovered GameCube-derived code, not newly disassembled PS2 water behavior. The GameCube objects 0/1 are **not** authenticated as PS2 placements 0/1; those PS2 indices name BIN129/130, and no reviewed GC-ID mapping identifies them as the same water objects. That mapping must be proven before implementation.
2. **r107, early lake-house basin**: `src/st1/r107.cpp:68-69,143-177` registers water effects, water OT and fish water height. Actual PS2 SST4 has noise/base rows. Ordinary route 1-2 reaches this before the 1-3 water path. The existing r107 geometry sheet shows a house-side basin; it is not a PS2 gameplay river screenshot.
3. **r10a, boulder/water path**: `src/st1/r10a.cpp:81,186-189` registers water-hit effects and updates water OT. Actual SST0 has fe/f2/f2/f7 layers. Its existing sheet includes broad shallow ground below wooden walkways; geometry-only renders do not prove the dynamic water look.
4. **r10c/r10d/r10e, later explicit rivers**: `water_ps2_ext.py:1-25` explicitly binds these mine/waterfall side-path rivers; `espgen45.cpp:649-673` dispatches exactly those rooms. r10c has 14 ambient water/waterfall candidates and four scripted c5 curtains; the converter deliberately excludes EST. Existing `fix-water-traps23/stills/r10c-river.png` shows the dam wheel; r10e-river.png shows the channel by wooden structures. Both were visually inspected here, with full image hashes in BINDINGS, and match the later-room descriptions. They do not identify the user's unnamed first-stage view. r10c rain is a separate lane task.
5. **r106/r108**: r106 has one ambient dark f7 plane; r108 has two fe planes. These are real data, but the texture IDs alone do not establish a river. The existing base water table excludes r106; this audit does **not** label that omission a confirmed runtime defect.
6. **r10b/r11a/r11b**: explicit lake/shore behavior, actual layered water; possible only if “river” loosely describes those scenes.

`espgen45.cpp:633-643` base WATER_PS2 covers r107/r108/r10a/r10b/r11a/r11b, and EXT covers r10c/r10d/r10e. Neither path covers r100. That coverage difference is established source behavior, not proof that the current r100 surface is visibly absent. Esp08 also serves fog/energy sheets (`esp08.cpp:1-6`), which is why an ID-only ranking cannot be promoted to a room decision.

## Smallest implementation claim

No shared runtime file is claimed. The smallest eligible next source task is a **r100-specific material provenance proof**, conditional on the opening bridge/pond being the intended landmark: identify actual PS2 SMD/BIN water parts and their complete material/TPL state, then trace those parts' accepted native draw path. Preserve source visibility, material alpha/blend, animation/scroll, and lifetime. Do not synthesize an Esp08 plane, broaden WATER_PS2_EXT to r100, or copy GameCube object IDs into the PS2 table without that proof. If the intended landmark is the water wheel or later mine channel, use the existing r10c/r10d/r10e path instead; no r100 change follows.

The missing information is exactly one scene/landmark binding among opening police-car bridge/pond, house-side fish basin, shallow boulder-path water, and later dam/mine channels. No new user permission is requested by this discovery report; root can bind an existing view or retain the ambiguity. No guest, SDK, staging, broad pack regeneration, cloud action, held-look decision, recipe, runtime or asset modification occurred.

Seven actual-parser synthetic controls passed (two positive; five malformed-boundary negatives). These validate the bounded reader, not runtime look, water emission or performance. Existing stills mix offline renders and Dolphin references; no fresh game or physical-console acceptance is claimed.
