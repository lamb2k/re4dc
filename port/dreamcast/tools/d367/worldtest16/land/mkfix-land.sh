#!/bin/bash
# mkfix-land.sh (WSL): test 16 r101 world landing fixtures. o = t15/int data (wv32r101), n = test 16 data (wt16r101).
# Same ELF per arm kind (w16mrT trace, w16mmW TEXCHK/LEON-GC); only the r101 world files differ.
set -eu
TR=/root/probe/worldtest16-20261016/tree; T=$TR/port/dreamcast/tools/d367
OUT=/root/probe/worldtest16-20261016/fix-land22; mkdir -p $OUT
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w; SEG=$T/fullplay/segments
BASE="--base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP"
DN=cast15,glod,res16,snd16,res16h,vq16cs,water16h,wt16r101,fsh
DO=cast15,glod,res16,snd16,res16h,vq16cs,water16h,wv32r101,fsh
for x in o n; do
  [ $x = o ] && D=$DO || D=$DN
  python3 $T/test11/t11-fix.py w16mrT $OUT/stA-$x.json $BASE --data $D --warp $SEG/h2-warp.txt --pad $SEG/h2-pad.txt > $OUT/stA-$x.log
  python3 $T/test11/t11-fix.py w16mrT $OUT/stB-$x.json $BASE --data $D --warp $SEG/bell-warp.txt > $OUT/stB-$x.log
  python3 $T/test11/t11-fix.py w16mrT $OUT/stC-$x.json $BASE --data $D --warp $SEG/door103-warp.txt > $OUT/stC-$x.log
  python3 $T/test11/t11-fix.py w16mrT $OUT/still-$x.json $BASE --data $D --warp $W/still-cross.txt > $OUT/still-$x.log
  python3 $T/test11/t11-fix.py w16mmW $OUT/tex-$x.json $BASE --data $D --warp $W/tex-cross.txt > $OUT/tex-$x.log
done
ls $OUT/*.json | wc -l
