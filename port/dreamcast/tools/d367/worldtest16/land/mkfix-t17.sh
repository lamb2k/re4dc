#!/bin/bash
# mkfix-t17.sh (WSL): test 17 terrain landing fixtures on land17 (t15/int d7c4c0a3 + wt17terr). o = T15_DATA without
# wt17terr, n = T15_DATA (the branch's own line). ELFs w17trT (STRICT + stills) / w17tmW (TEXCHK, VRAM).
set -eu
TR=/root/probe/worldtest16-20261016/land17; T=$TR/port/dreamcast/tools/d367
OUT=/root/probe/worldtest16-20261016/fix-t17; mkdir -p $OUT
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w; SEG=$T/fullplay/segments
BASE="--base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP"
N=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA[len(m.T14_DATA)+1:])")
O=$(echo $N | sed 's/,wt17terr//')
echo "n: $N"; echo "o: $O"
for x in o n; do
  D=$N; [ $x = o ] && D=$O
  f() { python3 $T/test11/t11-fix.py $1 $OUT/$2-$x.json $BASE --data $D --warp $3 > $OUT/$2-$x.log; }
  f w17trT st2 $W/r102-strict.txt; f w17trT st8 $SEG/r108-warp.txt; f w17trT sta $SEG/r10a-warp.txt
  f w17trT still2 $W/r102-c2b.txt; f w17trT still8 $W/r108-c1.txt; f w17trT stilla $W/r10a-c1.txt
  f w17tmW tex2 $W/r102-c2b.txt; f w17tmW tex8 $W/r108-c1.txt; f w17tmW texa $W/r10a-c1.txt
done
grep -o "r10[28a]/ps2-wv5.re4mesh[^,]*" $OUT/still2-n.json | head -3; grep -c "ps2-wv5.re4mesh" $OUT/still2-o.json
ls $OUT/*.json | wc -l
