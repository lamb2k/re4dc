#!/bin/bash
# mkfix-c16.sh (WSL): r101 C16 landing fixtures on t15/int + C16 (landA 37bcf721). o = the C4 set (WT16D override to
# world-r101-wt16-20261016), n = C16 (the new WT16D default). Data = the branch's own T15_DATA. ELFs w16crT / w16cmW.
set -eu
TR=/root/probe/worldtest16-20261016/landA; T=$TR/port/dreamcast/tools/d367
OUT=/root/probe/worldtest16-20261016/fix-c16; mkdir -p $OUT
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w; SEG=$T/fullplay/segments
PRIV="/mnt/c/Game Dev/Emulators/re4-assets-private"
BASE="--base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP"
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA[len(m.T14_DATA)+1:])")
echo "data: $D"
for x in o n; do
  if [ $x = o ]; then export WT16D="$PRIV/world-r101-wt16-20261016"; else unset WT16D; fi
  python3 $T/test11/t11-fix.py w16crT $OUT/stA-$x.json $BASE --data $D --warp $SEG/h2-warp.txt --pad $SEG/h2-pad.txt > $OUT/stA-$x.log
  python3 $T/test11/t11-fix.py w16crT $OUT/stB-$x.json $BASE --data $D --warp $SEG/bell-warp.txt > $OUT/stB-$x.log
  python3 $T/test11/t11-fix.py w16crT $OUT/stC-$x.json $BASE --data $D --warp $SEG/door103-warp.txt > $OUT/stC-$x.log
  python3 $T/test11/t11-fix.py w16crT $OUT/still-$x.json $BASE --data $D --warp $W/still-cross.txt > $OUT/still-$x.log
  python3 $T/test11/t11-fix.py w16cmW $OUT/tex-$x.json $BASE --data $D --warp $W/tex-cross.txt > $OUT/tex-$x.log
  grep -o "wv5.re4mesh[^,]*" $OUT/still-$x.json | head -1
done
ls $OUT/*.json | wc -l
