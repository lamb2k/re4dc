# MIST_CUT: what the outdoor alpha layers cost (lane mist16, 2026-10-16)

Knob `MIST_CUT=<mask>` (game/hwfog.mk; unset by default: no code, the play image is byte-identical). Code:
src/game/esp_sub.cpp (`re4dc_mist_cut`, `MistCutClass`, the haze branch of `EspSpriteEmit`) and
game/platform/native_static.cpp (`mistcut::world_part`, the PS2 world part loop). Render only: the generators, their
Rnd() draws, the effect pool and every effect's motion run as before; only the draw changes.

## Why

A tester (Esppiral, Discord 2026-10-16) patched the binary to turn off the alpha-blended mist / fog layers and reported a
large speed-up on a real console outside the first house (r100 woods), plus short frame drops that recover after a few
seconds. Our console benchmarks never covered r100 outdoors. The user later said the tester may have turned off every
world effect, not only mist.

## What is already in the release (test 14 / 15)

The PS2 cut of the camera haze is already on. The brief's premise ("EFFECT_PS2_HAZE is in no recipe") is wrong:

- The resolved knobs of the t15 warp arm: EFFECT_PS2_HAZE=1, EFFECT_PS2_STREAK=2, EFFECT_FADE_CLAMP=1,
  EFFECT_HAZE_LEAN=3 (M1: the GC mist sheets the PS2 deleted are not drawn; M3: in r100 / r101 / r103 only about
  30 % of the PS2 haze subset draws, alpha x1.5, and the fog table carries the rest of the veil), HW_FOG_HAZE=1 (rows
  r100 / r101 / r106 / r107 / r109: haze sprites deeper than 3 m become fog), PS2_FX_ROOMS / STAGE1 / POPULATION /
  ADDITIONS / ROOMS_EXT=1, FX_SPRITE_TRIM=2, FX_PS2_PACK=1.
- The boot log of every run says `ps2fx: PS (flags 7)` (LOOK_TOGGLE preset A: fade clamp + PS2 haze + PS2 streak).
- So in r100 / r101 / r103 the haze is already thinner than the PS2's (M3), and in five rooms the far haze is fog.

The arms were re-aimed (coordinator 10-16): A = today, then one bit per effect class off.

## Mask bits

| bit | class | what is not drawn |
|---|---|---|
| 1 | haze / mist | Esp15 camera haze (the near haze the fog rows keep) and any Esp48 mist sheet; the fog-table veil stays |
| 2 | world mist cards | translucent world parts that are mist: the grey fogged treeline band e967b886 (r10b texture 7, staged in r10b / r11b) |
| 4 | glows / streaks | room table (owner 0xd0) Esp0a / Esp0e: window glows, streaks, light shafts |
| 32 | dust / particles | the other room table (owner 0xd0) effects: dust, smoke, sparks |
| 8 | fire / torches | room EST owner 0x01 (r101's pyre), torch and lamp owners (0x5e..0x8c) |
| 64 | other effects | every other owner: shots, blood, sparks, splashes |
| 128 | water | Esp42 / Esp45 of any owner |
| 16 | diagnostic only | every translucent world part (foliage, leaf litter, ground blend overlays, shadow decals) |

Arms: A = T15REC, B = 1, C = 2, D = 3 (no alpha mist: B + C), E = 239 (every effect sprite and the mist cards),
F = 255 (E + no translucent world at all: the ceiling of "no alpha layers"), and one arm per class (4, 32, 8, 64, 128)
at the tester's view and the r101 cross.

Not covered by the mask (other draw paths): r11b's PS2 rain lines (RAIN_PS2), r10b's lake ripples (LAKE_RIPPLES), the
laser sight (Esp19), PS2_FX_ADDITIONS (r118 / r11c), the r100 house light shafts of EFFECT_PS2_STREAK=2. None of them is
on screen at the measured views except none (r100 / r101 outdoors).

RESULTS: see the sections below (filled in by the lane at the end of the run).

## Results (Flycast flycast6 TA stats per scene; GPU = MODELLED console, two fits; CPU = hw model console-fit, MODELLED)

Translucent screens (TR, screens of overdraw per frame) at the same frozen views. GPU fits (tools fit.py): hi = joint fit of
the r22g 10-05 rows + 12.1 bench (about 3.3 ms per TR screen), lo = bench-only fit (about 0.14 ms per screen). The two
disagree; quote both as bounds. Console A/B is the only proof (HW model trust policy).

| view | A today | B no haze | C no mist cards | D = B+C | E no effects | F E + no TR world |
|---|---|---|---|---|---|---|
| r100 woods path (tester) | 3.81 | 3.30 | 3.81 | 3.30 | 3.30 | 0.40 |
| r101 cross (bench) | 2.52 | 2.22 | - | 2.22 | 1.40 | 0.40 |
| r11b shore | 7.68 | 4.48 | 7.66 | 4.44 | 1.52 | - |
| r107 entry | 4.39 | 1.91 | - | 1.91 | 1.57 | - |
| r109 entry | 6.79 | 5.09 | - | 5.09 | - | - |

- There are no world mist cards in r100 / r101 / r103; the only one in chapter 1 is e967b886 (r10b / r11b). C changes nothing
  at the measured views except the r11b shore (-0.02).
- The r100 woods translucency is the PS2 world's brush / leaf cards (3.3 of 3.8 screens), not mist (0.5).
- CPU (r100 woods frames 400..519, work = frame minus the pacer wait): A 56.4, E 55.2 (instructions -0.03 %: the cut is draw
  only), F 49.4 ms (scenery -5.7). r100 outdoors is CPU-bound under both GPU fits (GPU 17..18 ms MODELLED).
- Gates: B and C STRICT + decisions MUST-IDENTICAL on h2 / bell (stop 2000), C also at r11b (700 ticks, 362 card parts
  cut); TEXCHK pass on every arm; knob-off identity; KOS squeeze 10/10 at MIST_CUT=1 (_end +1,664 B).

## FOLIAGE_TRIM (hwfog.mk; the follow-up the coordinator asked for, 10-16)

Alpha census of every translucent world part key in the 17 chapter 1 PS2 packages (mist-20261016/sh/census.py): no part is
near-invisible by texture; 26,234 of r100's 30,923 translucent vertices are near-binary cut-out cards. NEAR draws those in
the punch-through list within 12 m and drops them beyond (the fog ramp's far half); OFF drops the world translucent pass.
Keys with fewer than 10 % fully transparent texels are not cards (r109's walls are alpha 238 everywhere: they vanished at
NEAR in the first arm) and stay translucent.

| view | FULL TR / max layers | NEAR | OFF |
|---|---|---|---|
| r100 woods path | 3.81 / 17.2 | 1.89 / 8.1 | 0.93 / 7.3 |
| r100 start (ferns close) | 2.74 / 20.0 | 1.06 / 7.8 | 0.41 / 7.8 |
| r100 house approach | 2.81 / 12.8 | 1.38 / 6.1 | 0.52 / 5.9 |
| r101 cross (bench) | 2.61 / 12.8 | 2.33 / 11.8 | 1.62 / 9.9 |
| r109 entry | 6.79 / 22.1 | 6.79 / 22.1 | 2.11 / 9.3 (walls gone: OFF is not a look for r109) |
| r11b shore | 7.62 / 21.9 | 7.60 / 21.9 | 7.46 / 21.9 |

CPU work at the r100 woods (MODELLED): FULL 56.4, NEAR 55.5, OFF 52.5 ms. Moving cards to punch-through saves GPU (no blend,
no per-tile sort) but little CPU; only parts not drawn save CPU.

Gates (arm fM = the key table above, branch wip/mist16-20261016): STRICT + decisions MUST-IDENTICAL h2 / bell / door103 (stop
2000, padded reference fR); TEXCHK pass on all 7 views; knob-off identity (image f953228a = t15/int 0596b7ed); align logger
0 MISALIGN at r100 woods and r109 (FOLIAGE_TRIM=1 twin, interpreter, 240 s); KOS squeeze 10/10 at 48 KiB (fight min 10,848 B;
_end +2,048 B on the play recipe). Stills: mist-20261016/FOLIAGE-SHEET.png. Look not yet approved: NEAR loses the far leaf
litter beyond 12 m (r100 start view).
