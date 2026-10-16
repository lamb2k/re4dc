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
