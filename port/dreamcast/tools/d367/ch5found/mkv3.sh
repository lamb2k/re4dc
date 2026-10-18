#!/bin/bash
# round 3 VRAM fixtures (arm cx5vmW): pak tex-ch5b (+ the r311/r327 pair), resident-ch5b (r329/r31d/r327 lists)
set -e
L=/root/probe/lanes-20261016/ch5found; S=/root/probe/lanes-20261014/st3/fixtures
export PAK=$L/vram/tex-ch5b.pak RES=$L/vram/resident-ch5b.bin
for r in "$@"; do
  src=$(ls -t $S/$r/*.armed.json | head -1)
  w=$L/fixtures/wp2/cx-$r-r2.txt
  [ $r = r327 ] && w=$L/fixtures/wp2/cx-r327-cap.txt
  [ $r = r31d ] && w=$L/fixtures/wp2/cx-r31d-cap.txt
  ARM=cx5vmW bash /mnt/c/tmp/ch5/mkfix.sh x3 $w $r walk $src 2>&1 | tail -1
  python3 /mnt/c/tmp/ch5/addmov.py $L/fixtures/$r/cx-$r-walk-x3.armed.json >/dev/null
  python3 /mnt/c/tmp/ch5/addsnd.py $L/fixtures/$r/cx-$r-walk-x3.armed.json
done
