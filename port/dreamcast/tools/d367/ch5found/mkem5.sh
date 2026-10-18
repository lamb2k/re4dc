#!/bin/bash
# round 3 item 3 fixtures (arm cx5vmW): island pak tex-ch5c (= tex-ch5b + the prepared island enemies' textures),
# resident-ch5b, the prepared em36 / em39 / em3a / em32 / em3d archives (variant $V)
set -e
V=${V:-e4}
L=/root/probe/lanes-20261016/ch5found; S=/root/probe/lanes-20261014/st3/fixtures; P=$L/prepem
ls $L/build/programs/candidate-routecx5vmW/ | grep -c ovl
if [ ! -f $L/vram/tex-ch5c.pak ]; then
  python3 /mnt/c/tmp/ch5/pakadd.py $L/vram/tex-ch5c.pak $L/vram/tex-ch5b.pak $P/tex-em*/*.re4tex
  python3 $L/tree/port/dreamcast/tools/d367/texpack.py --verify $L/vram/tex-ch5c.pak | tail -1
fi
export PAK=$L/vram/tex-ch5c.pak RES=$L/vram/resident-ch5b.bin
for spec in "$@"; do
  r=${spec%%:*}; export EMX="$(echo ${spec#*:} | tr , ' ')"
  src=$(ls -t $S/$r/*.armed.json | head -1)
  w=$L/fixtures/wp2/cx-$r-r2.txt
  ARM=cx5vmW bash /mnt/c/tmp/ch5/mkfix4.sh $V $w $r walk $src 2>&1 | tail -1
  python3 /mnt/c/tmp/ch5/addmov.py $L/fixtures/$r/cx-$r-walk-$V.armed.json >/dev/null
  python3 /mnt/c/tmp/ch5/addsnd.py $L/fixtures/$r/cx-$r-walk-$V.armed.json
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(sys.argv[2],[k for k in d['replace'] if k.startswith('em/em3')],[k for k in d.get('remove',[]) if k.startswith('em/em3')])" $L/fixtures/$r/cx-$r-walk-$V.armed.json $r
done
