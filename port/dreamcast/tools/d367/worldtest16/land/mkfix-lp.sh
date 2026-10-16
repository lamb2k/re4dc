#!/bin/bash
# mkfix-lp.sh (WSL): in-game check of lost-part flags: r101 original world (crowd12 bake13 level 0, also as level 5) = o,
# shipped test 17 set C16 = n, at the r102 door arrival and the em15 set position. ELF w17trT, data = land17 T15_DATA.
set -eu
T=/root/probe/worldtest16-20261016/land17/port/dreamcast/tools/d367
OUT=/root/probe/worldtest16-20261016/fix-lp; mkdir -p $OUT
W=/mnt/c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools/w
B="/mnt/c/Game Dev/Emulators/re4-assets-private/crowd12-bake-20261015/r101-t13"
BASE="--base /root/probe/lanes-20261015/t14rc/fix/pkg-t14rcrP.json --base-label t14rcrP"
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA[len(m.T14_DATA)+1:])")
S=(--set "dc/native/r101/ps2-world.re4mesh=$B/ps2-world.re4mesh" --set "dc/native/r101/ps2-world.r4pw=$B/ps2-world.r4pw"
   --set "dc/native/r101/ps2-world.ids=$B/ps2-world.ids" --set "dc/native/r101/ps2-world.r4sg=$B/ps2-world.r4sg"
   --set "dc/native/r101/ps2-wv5.re4mesh=$B/ps2-world.re4mesh" --set "dc/native/r101/ps2-wv5.r4sg=$B/ps2-world.r4sg")
for v in door em15; do
  python3 $T/test11/t11-fix.py w17trT $OUT/$v-o.json $BASE --data $D --warp $W/lp-$v.txt "${S[@]}" > $OUT/$v-o.log
  python3 $T/test11/t11-fix.py w17trT $OUT/$v-n.json $BASE --data $D --warp $W/lp-$v.txt > $OUT/$v-n.log
done
grep -o 'r101/ps2-wv5.re4mesh[^,]*' $OUT/door-o.json $OUT/door-n.json
