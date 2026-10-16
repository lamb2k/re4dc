#!/bin/bash
# fix-va.sh (WSL): bisect set Va = bake13 level 0 (+ its r4pw, ids, r4sg) with variant 5 = C11's ladder output L2.re4mesh
# itself (no 4 m batch, no strip groups, no 32 m spatial batch; no ps2-wv5.r4sg so level 5 draws without groups).
set -eu
T=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367; OUT=/root/probe/worldtest16-20261016/fix-land22
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w
B13="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"; C=/root/probe/worldtest16-20261016/rooms/r101-C11
S=(); for f in ps2-world.re4mesh ps2-world.r4pw ps2-world.ids ps2-world.r4sg; do S+=(--set "dc/native/r101/$f=$B13/$f"); done
python3 $T/test11/t11-fix.py w16mrT $OUT/still-va.json --base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP \
  --data cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh --warp $W/still-cross.txt "${S[@]}" \
  --set "dc/native/r101/ps2-wv5.re4mesh=$C/L2.re4mesh" --rm dc/native/r101/ps2-wv5.r4sg | tail -c 40
