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

## FOLIAGE_OPTION: the Options row (test 15, user 10-16 "I approve near", "ship with full near and off then log the issue")

Options "FOLIAGE  FULL / NEAR / OFF" below View distance (option_rows.cpp, viewdist16 row pattern), T15REC group T15_T
(`FOLIAGE_TRIM=1 FOLIAGE_OPTION=1`; `T15_T=""` = control). Boots at Near; this boot only, like View distance. Warp line
`foliage 0|1|2` for stills. OFF keeps today's behaviour (no world translucent pass), which also removes the r109 cabin's
walls and floor: KNOWN_ISSUES row (open), fixed by the follow-up below.

Trap found on the way: `re4dc_foliage` was defined inside native_static.cpp's anonymous namespace, so its symbol was the
mangled `_GLOBAL__N_1` name. option_rows.cpp (also in an anonymous namespace) happened to link to it; dbgwarp_bridge.cpp's
`foliage` warp line linked to a generated stub (missing.txt `_re4dc_foliage` on the warp builds). Fixed in 23ef7a61 (file
scope, the same close/reopen pattern as re4dc_ps2_sky_header); missing.txt is empty again on every arm.

Final-arm gates (23ef7a61, recipe T15REC with T15_T, on t15/int 1a8d97aa): knob-off identity (T15_T="" rP vs t15/int rP:
image a93cb52c, 6 overlays identical); STRICT + decisions MUST-IDENTICAL at the default Near on h2 / bell / door103 (stop 2000,
padded control oCrT, PAD_T 2304; h2 aligned 1990 of 2001 ticks, capture ring gaps); TEXCHK pass on 8 runs; KOS squeeze
10/10 at 48 KiB on the final play recipe (fight min 14,168 B, door 16,616, leave 14,232, call 31,976); menu walk: the row
cycles NEAR -> OFF -> FULL -> NEAR and View distance FULL -> NEAR -> SHORT -> FULL (log `options: foliage ...`). Sheet:
mist-20261016/OPTIONS-SHEET.png (menu crops beside the r100 woods still at each setting).

## FOLIAGE Off follow-up: only the card keys (85128754)

Off first dropped the whole translucent world pass (the tester's patch), which removed r109's cabin walls and floor (alpha
238 surfaces). Now foliage_keys.inc has a class 4 (soft cards below the opaque level with cut-out holes: shadow strips,
mist, grass fades; 61 keys, drawn as before at Full and Near) and Off drops classes 1-4 only. Unlisted translucent parts
(surfaces without holes such as the cabin walls and floor, water, keys outside the chapter 1 census) and the vertex-alpha
overlays always draw. Near is unchanged (classes 1-3 keep their levels; the generator adds class 4 after them).

| view (Flycast TA) | FULL | NEAR | first OFF | OFF now |
|---|---|---|---|---|
| r100 woods path | 3.81 | 1.89 | 0.93 | 1.16 (GPU 9.7 ms MODELLED hi; first Off 8.9) |
| r100 start | 2.74 | 1.06 | 0.41 | 0.66 |
| r101 cross (world32) | - | - | - | 1.50 |
| r109 entry | 6.79 | 6.79 | 2.11 (walls gone) | 6.35 (walls and floor drawn) |
| r11b shore | 7.62 | 7.60 | 7.46 | 7.60 |

Gates (85128754 on t15/int 6b5bc9b0): knob-off identity (T15_T="" rP image 1b56f915 = 6b5bc9b0, 6 overlays); STRICT +
decisions MUST-IDENTICAL h2 / bell / door103 at Near (stop 2000, padded control, full tick range); TEXCHK 8/8; KOS squeeze 10/10 at 48 KiB
on the play recipe (fight min 14,712 B, door 17,160, leave 14,776, call 32,520). Sheet: mist-20261016/OFF-FIX-SHEET.png.

## HAZE_SPRITE_CUT: no haze / mist sprites (test 15.1 hotfix, lane nohaze16)

User 10-16: "i don't think we need those sprites at all", then "let's make off really mean off". Knob `HAZE_SPRITE_CUT=1`
(game/hwfog.mk; render only; default 0 = no code; recipe group `T15_HZ`): no haze / mist sprite is drawn in any room, at
every Foliage setting (it is not a menu choice). Cut in src/game/esp_sub.cpp `EspSpriteEmit`: every Esp15 camera haze
sprite (the PS2 recipe rows' near haze, after HW_FOG_HAZE has seen it, and every other Esp15), every Esp48 mist sheet, and
the r118 / r11c PS2 haze additions (sampled as before, no quad submitted). The distant haze stays as the PVR fog table:
the HW_FOG_HAZE rows (r100 / r101 / r106 / r107 / r109) and the EFFECT_HAZE_LEAN M3 veil (r100 / r101 / r103) are fed
before the cut, and every room keeps its own fog. Rooms whose haze was sprites only (r10b / r11b / r119 lake and shore,
r104, r11a and the other stage-1 rows without a fog row) keep their room fog but lose the near mist (a clearer look; the
user's call). Log: one `haze cut: room=...` line per room with the previous room's count. Ships with the Foliage Off
fix (85128754): Off leaves out every card key (classes 1-4, the mist card e967b886 is class 2) and the haze sprites.

Translucent screens (Flycast TA, flycast6, the same ticks in both arms; the r100 woods path view before its freeze, the
r101 cross bench view; test 15 = arm t15rcmW, 15.1 = t151mW, both with TEX_CHECK=2 / MCHECK_LEONGC=1). GPU ms are
MODELLED with the two fits above (hi about 3.3 ms, lo about 0.14 ms per TR screen), not console:

| view | Foliage | test 15 | 15.1 | change | GPU change MODELLED hi / lo |
|---|---|---|---|---|---|
| r100 woods path | Full | 4.05 | 3.91 | -0.14 | -0.46 / -0.02 ms |
| r100 woods path | Near (default) | 1.49 | 1.45 | -0.04 | -0.13 / -0.01 ms |
| r100 woods path | Off | 0.40 (first Off: no TR world) | 0.64 | +0.24 (walls, floors, water kept) | +0.8 / +0.03 ms |
| r101 cross | Full | 3.04 | 2.08 | -0.97 | -3.2 / -0.14 ms |
| r101 cross | Near (default) | 2.59 | 1.64 | -0.95 | -3.1 / -0.13 ms |
| r101 cross | Off | 1.77 | 0.82 | -0.95 | -3.1 / -0.13 ms |

At r100 the haze was already thin (EFFECT_HAZE_LEAN M3 + the HW_FOG_HAZE row): the sprites were 0.04-0.14 screens. At the
r101 cross they were about 0.95 screens (the camera haze plus an Esp48 mist sheet, tex cb). Haze sprites cut per room in
the gate runs (Flycast): r101 931 over the bell fixture, r104 588, r11a 2,852.

Gates (t15.1/rc, program 0a4ef1b4, image d0d6364a; evidence C:\Flycast-Evidence
e4-dreamcast
ohaze16-20261016):
knob-off identity (kP image 12dddcac + 6 overlays = test 15's kP); STRICT + decisions MUST-IDENTICAL h2 / bell / door103
(stop 2000) against the test 15 trace arm t15rcrT (h2 s30 340/340 both); KOS squeeze 10/10 at 48 KiB (fight min 12,248 B,
call 30,056, door 14,696, leave 12,312); GDEMU race 0/10; TEXCHK=2 + LEON-GC PASS r100 r101 r103 r107 r10b r118 r119 (wrap
0); release check t15rel.conf PASS (the comingsoon goal and the reset segment's r102 4 refusals / 61,312 B match test 15's
known rows) and the align crash suite PASS. _end -960 B against test 15 (8c4240f8 -> 8c423d38).
