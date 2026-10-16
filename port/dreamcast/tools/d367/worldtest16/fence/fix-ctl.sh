#!/bin/bash
# fix-ctl.sh (WSL): controls at the village cross on ELF w16mrT with the t15/int data set:
#  still-ctlA = pre-world32 world (bake13 level 0, no variant 5: WORLDVERT loaded=0) -- phase 1's arm A on today's build;
#  still-c9l0 = the C9 set without its variant 5 (loaded=0: the spatially batched level 0 of C9).
set -eu
T=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367; OUT=/root/probe/worldtest16-20261016/fix-land22
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"; C9=/root/probe/worldtest16-20261016/rooms/r101-C9/out
BASE="--base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP --data cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh --warp $W/still-cross.txt"
S=(); for f in ps2-world.re4mesh ps2-world.r4pw ps2-world.ids ps2-world.r4sg; do S+=(--set "dc/native/r101/$f=$B13/$f"); done
python3 $T/test11/t11-fix.py w16mrT $OUT/still-ctlA.json $BASE "${S[@]}" --rm dc/native/r101/ps2-wv5.re4mesh --rm dc/native/r101/ps2-wv5.r4sg | tail -c 40
S=(); for f in ps2-world.re4mesh ps2-world.r4pw ps2-world.ids ps2-world.r4sg; do S+=(--set "dc/native/r101/$f=$C9/$f"); done
python3 $T/test11/t11-fix.py w16mrT $OUT/still-c9l0.json $BASE "${S[@]}" --rm dc/native/r101/ps2-wv5.re4mesh --rm dc/native/r101/ps2-wv5.r4sg | tail -c 40
