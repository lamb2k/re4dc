# Lane eng-cloth1: cloth that costs what the console can pay

Status: **finished, unaudited** (2026-11-22). Branch `lane/eng-cloth1`. Brief: `E:\RE4DC-Lanes\eng-cloth1\BRIEF.md`.
Evidence: `E:\RE4DC-Lanes\eng-cloth1` (runs, ev, look). Tiers: MODELLED = console-build Flycast, dynarec on, `Sh4Clock`
70 (calibrated on the old port), slot fly2; plain Flycast stills on std1/std2 are look checks, never timings.

## Is cloth presentation only?

Static search of the behaviour code for reads of cloth-moved bones: the player characters (Leon, Ashley, Luis, Ada)
read none (hurt boxes, camera, weapons and partner code read parts 0-0x18, 0x1D/0x1E, 0x20/0x21, none a cloth bone).
Four enemy chains are read by behaviour: em31 type 0 hurt boxes on em31ClothP2 bones, em35 type 1 hurt boxes on its
tail chain, em32's last form hurt boxes on em32_cloth_parts, em10's flail (link 10's attack check). None of them runs
through the native cloth service in the images today. Step 1 is exact for every chain; the look arms touch Ashley's
skirt only (48 links, 11 volumes). PC reference: every arm leaves the behaviour trace byte-identical (hill-ashley).

## Step 1: the same cloth, cheaper (the default)

`services/cloth/cloth_kernel.c`: the parallel volume test reads a 16-byte table of the tick's volumes (centre,
radius) built once a tick; spheres out of reach of the link pair are passed over by a register-only scan (reach
r(1 + 1/len) + 1, widened 0.1% and 2 units for rounding); the call's set-up (normalisation, division) is made only
once a volume is in reach, and the original's first rejection is made in the scan with the same operations in the same
order; the remaining tests go through the original arithmetic (`par_one`). The plain volume test takes the link's
length at its first hit. The old bound (eng-svcspd1 fix 2) is gone. Scan: about 20 SH-4 instructions a sphere passed
over (was about 40, 9 of them stack spills and reloads).

Results are unchanged to the bit:
- PC reference, native against the original (odump), wind off: hill-ashley 240000/240000 bones bit-identical.
- The engine against itself (before / after), five fixtures (door103-walk, e1-route, bell-ganado, hill-ashley,
  square-follow), wind on and off: every bone and query bit-identical, traces byte-identical.
- Flycast stills (plain), `engine` f0732e6a2 against the merged lane 82edff078, LEONS and HILLS: 0 differing pixels
  in 36 of 36 pairs.

Speed, `engine` f0732e6a2 (old kernel) against the merged lane 82edff078, same session, slot fly2, pictures 41-640
(MODELLED, console-build dynarec at 70 MHz, calibrated on the old port), ms a picture, mean / p99 / worst:

| Scene | Cloth before | Cloth after | Services row before | Services row after |
|---|---|---|---|---|
| HILL | 6.95 / 7.16 / 9.49 | 5.31 / 5.59 / 8.03 | 15.38 / 18.25 / 19.21 | 13.74 / 17.08 / 18.70 |
| LEON (village) | 1.91 / 1.99 / 2.02 | 1.58 / 1.65 / 4.05 | 6.01 / 7.87 / 10.45 | 5.67 / 8.76 / 10.09 |

The clock artefact (H-029 finding 1: +2.5 ms in one picture a second, about 20 of the 600 pictures) is not fixed on
`engine` yet, so p99 and worst carry it; the means are the comparable figures (LEON's cloth worst 4.05 and the
services p99 rise are that artefact landing on a cloth or services picture). Yesterday's pair (98a5694b0 / 2047d5ace)
read the same to 0.01 ms.

Checks, on the merged head 82edff078 with a fresh reference build (`E:\RE4DC-Lanes\eng-cloth1\ev\pc-merged2`):
- `services/skeleton/speed_controls.sh`: row `clothbound` (the skip bound 40 units short) FAILs as it must on
  hill-ashley (197119/240000 bones bit-identical); every other row as it must.
- `hostref/svc/svc_controls.sh`: 79 rows as they must (hill-ashley wind off 240000/240000 bones bit-identical against
  the original). `refctl.sh`, `camcheck.sh`, `controls.sh`, `outcome_controls.py`, `aim_check.sh`: every row as it must.
- `services/cloth/cloth_key_test.sh` (the (PenCloth, model) key and the release entries): key PASS; controls
  `CLOTH_KEY_CONTROL_OLD` and `CLOTH_RELEASE_CONTROL` FAIL as they must.
- Images: default 384 original functions kept, SERVICE 0, PASS; BOSS 479, PASS; SENDABLE 384, PASS; FIGHT 850 kept,
  SERVICE 43, FAIL, the same as `engine` f0732e6a2 with the same tool (the 43 are H-029's hidden cases, eng-e2d's).

## Other changes on the branch

- Chains keyed by (PenCloth, model) (6feceed7e; also on `lane/eng-cloth1-key` from `engine`): El Gigante's chained
  form sets one PenCloth up on two models. A full table gives up the chain stepped least recently.
- Release entries `cloth_release_all()` (room change) and `cloth_release_model(m)` (acf8bf80c). Nothing calls them
  yet: the room change is the loader's.

## Step 2: look options (run-time lab arms, not the default)

Boot files read at the first chain set-up (PC reference: `RE4_SVC_CLOTH_ARM`); each changes Ashley's skirt only; with
none present every result is unchanged.

| Arm | What | Hill cloth mean / p99 (MODELLED) | Gain on step 1 (mean) | Differing pixels a still, hill (mean / max over 728) |
|---|---|---|---|---|
| (none) | step 1 | 5.36 / 5.57 | - | 0 |
| CLOTHCAP | runs of leg spheres as 3 capsules | 5.19 / 5.34 | 0.17 | 406 / 1699 |
| CLOTHPASS2 | two constraint passes instead of four | 4.21 / 4.39 | 1.15 | 205 / 2210 |
| CLOTHHALF | stepped every other tick, held between | 3.95 / 5.53 | 1.41 | 762 / 4822 |
| CLOTHFAR | every fourth tick when over 6 m away or behind the camera | never fires on the hill | 0 | 0 |
| CLOTHFAR0 | the far rule at distance 0 (every fourth tick always) | 3.26 / 5.56 | 2.10 | 1091 / 6323 |

Arms measured on c26dab655 against its own no-arm run (h0); the arm code is unchanged since. CLOTHHALF and CLOTHFAR0
lower the mean but not p99: the stepped ticks cost what they did. CLOTHHALF and CLOTHFAR0 also change pixels on both
characters' hair in the Flycast stills (about 20% of their differing pixels, in 95 of 100 sampled ticks), although on
the PC reference only the skirt's bones move: not traced (renderer side); it must be explained before either lands.

## What the model cannot see

The graphics chip's fill and sort time, vertex submission through the store queues, cache and memory bus contention,
real disc timing. The tier charges instructions; the standard build reads the engine 3 to 10% kinder.
