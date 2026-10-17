#!/bin/bash
# t16-build.sh <arm>...: test 16 build arms (t16/rc, 2026-10-16; scope C:\Game Dev\Emulators\TEST16-SCOPE.md).
# Test 16 (user 10-16, "slice test 16 into two"): t15/int e22bf562 + lane/nohaze16 0a4ef1b4 (the test 15.1 haze-sprite
# removal). Its recipe T16REC is test15/t15-build.sh's T15REC at this commit, which already holds every test 16 group:
#   test 15 (6b5bc9b0) groups T15_2 .. T15_T, the 15.1 group T15_HZ (HAZE_SPRITE_CUT=1), and the test 16 groups
#   T15_RS (RADIO_SUB_RT=1, radio subtitles follow the voice); NOT T15_FS (FAR_SHELL=1): coordinator decision (a) 10-16,
#   the far shell moves to test 17 (it loads r100's far-shell.fsh, 122 KB of heap 4, at room entry at every View distance,
#   and the r100 s30 movie then ran out of heap 4: 2 Ganados not spawned in every diagnostic arm; t16rc evidence h2-rW);
#   the option A disc reads (T14_DISC = DISC_COMPAT=1 DISC_READ_FALLBACK=3 DISC_LAND_SPIN_MS=20) and the PS2 water in
#   r10b / r11b (WATER_PS2_ROOMS default 0x3f) are defaults of this tree; the Foliage Off fix is code under FOLIAGE_OPTION.
# Data: T16_DATA in test11/t11-fix.py (= T15_DATA of e22bf562 without the far shells fsh: water16i + vq16w, the r101
#   world version C wt16r101). Package: test16/t16-package.sh (standard GD-ROM layout).
# Arms (as t15-build.sh): rP release play, rW warp, mW warp + TEX_CHECK=2 + MCHECK_LEONGC=1, rT trace, kP / kW / kT
#   knob-off (no test 15 / 16 knobs). Test 16 adds:
#   qP / qT / qW  the test 15.1 program on this tree: T16REC with the test 16 changes off (T15_FS="" T15_RS="", test 15's
#            T14_DISC, WATER_PS2_ROOMS=0x17). qP's objcopy -R .stack image must equal test 15.1's (d0d6364a) with all six
#            overlays (knob-off identity: the test 16 delta is behind its knobs); qT is the STRICT reference for rT.
# Env: T (tree, default /root/probe/lanes-20261016/t16rc/tree), K (logs, default /root/probe/lanes-20261016/t16rc),
#      LP (label prefix, default t16rc), XON (extra knobs, test only), PAD_T / PAD_K.
set -u
export T15_FS=${T15_FS-}   # test 16: no far shell (decision (a)); T15_FS=FAR_SHELL=1 builds it for test 17 work
# test 16: r101 without the world32 vertex reduction (user 10-16 "use the previously optimized r101": the reduced world
# loses ~1,500 structure pieces, lostpart checker): no WORLD_VERT, and T16_DATA keeps the pre-world32 r101 world (bake13).
export T15_WV=${T15_WV-}
D=$(cd "$(dirname "$0")" && pwd)
export T=${T:-/root/probe/lanes-20261016/t16rc/tree} K=${K:-/root/probe/lanes-20261016/t16rc} LP=${LP:-t16rc}
Q15=(env T15_FS= T15_RS= T15_AC= "T14_DISC=DISC_COMPAT=1 DISC_READ_FALLBACK=0" "T15_W=WATER_PS2=1 WATER_PS2_ROOMS=0x17" LP=${LP}q)
# qP is test 15.1 exactly (WORLD_VERT on, as 15.1 shipped); qT / qW run on the test 16 data (pre-world32 r101), so they
# keep WORLD_VERT off like rT (WORLD_VERT is render only: STRICT on vs off in its landing, world32-land-20261016).
for x in "$@"; do case $x in
  qP) "${Q15[@]}" "T15_WV=WORLD_VERT=1 WORLD_VERT_LEVEL=5" bash $D/../test15/t15-build.sh rP ;;
  qT) "${Q15[@]}" T15_WV= bash $D/../test15/t15-build.sh rT ;;
  qW) "${Q15[@]}" T15_WV= bash $D/../test15/t15-build.sh rW ;;
  # test 16.1 (hotfix, 10-17): sP / sT / sW = test 16 exactly (T15_AC="": cap 6, animals). sP's image must equal test
  # 16's d551dab2 with its overlays (knob-off identity of ANIMALS_OFF + cap 4); sT is the STRICT reference for rT.
  sP|sT|sW) T15_AC= LP=${LP}s bash $D/../test15/t15-build.sh r${x#s} ;;
  # test 16.3 (hotfix, 10-17): T15REC adds T15_VP (VRAM_PAGES_VQ_ONLY=1) and T15_GD (GANADO_ATLAS_DROP=3), both render
  # only. oP = rP with both off: its image must equal test 16.2's (a8cf395d, f214bd94) with its overlays (knob-off
  # identity). Data T163_DATA (motion hot flags zr17m / zr17b, resident.bin res163).
  oP|oT|oW) T15_VP= T15_GD= LP=${LP}o bash $D/../test15/t15-build.sh r${x#o} ;;
  # test 16.4 (hotfix, 10-17): T15REC adds T15_FN (FOLIAGE_NEAR_FIX=1) and T15_LF (LAKE_FAR=30000 LAKE_FAR_SHORE=45000),
  # both render only. wP = rP with both off: its image must equal test 16.3's (61df55c6) with its overlays (knob-off
  # identity); wT is the STRICT reference for rT.
  wP|wT|wW) T15_FN= T15_LF= LP=${LP}w bash $D/../test15/t15-build.sh r${x#w} ;;
  *)  bash $D/../test15/t15-build.sh $x ;;
esac; done
