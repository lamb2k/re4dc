#!/bin/bash
# fix-c5.sh (WSL): still fixture at the village cross with the r101 C5 set (C4 + fence vertex box), ELF w16mrT.
set -eu
T=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367
C5=/root/probe/worldtest16-20261016/rooms/r101-C5/out; OUT=/root/probe/worldtest16-20261016/fix-land22
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w
S=(); for f in ps2-world.re4mesh ps2-world.r4pw ps2-world.ids ps2-world.r4sg ps2-wv5.re4mesh ps2-wv5.r4sg; do S+=(--set "dc/native/r101/$f=$C5/$f"); done
python3 $T/test11/t11-fix.py w16mrT $OUT/still-c5.json --base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP \
  --data cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh --warp $W/still-cross.txt "${S[@]}" | tail -c 80
