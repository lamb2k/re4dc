#!/bin/bash
# fix-c6ng.sh (WSL): still fixture at the village cross with the r101 C6 set but no ps2-wv5.r4sg (the loader then draws
# level 5 without strip groups: "absent"), ELF w16mrT. Isolates the strip-group records for the fence-rail hunt.
set -eu
T=/root/probe/worldtest16-20261016/tree/port/dreamcast/tools/d367
C6=/root/probe/worldtest16-20261016/rooms/r101-C6/out; OUT=/root/probe/worldtest16-20261016/fix-land22
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w
S=(); for f in ps2-world.re4mesh ps2-world.r4pw ps2-world.ids ps2-world.r4sg ps2-wv5.re4mesh; do S+=(--set "dc/native/r101/$f=$C6/$f"); done
python3 $T/test11/t11-fix.py w16mrT $OUT/still-c6ng.json --base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP \
  --data cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh --warp $W/still-cross.txt "${S[@]}" --rm dc/native/r101/ps2-wv5.r4sg | tail -c 80
