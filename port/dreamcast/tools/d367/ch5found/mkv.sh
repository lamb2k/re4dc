#!/bin/bash
# sound fixtures (arm cx5vmW): the round-2 warp per room (r300: the door walk), island sound data + movies
set -e
L=/root/probe/lanes-20261016/ch5found; S=/root/probe/lanes-20261014/st3/fixtures
for r in "$@"; do
  src=$(ls -t $S/$r/*.armed.json | head -1)
  w=$L/fixtures/wp2/cx-$r-r2.txt; [ $r = r300 ] && w=$L/fixtures/wp/cx-r300-door.txt
  [ $r = r327 ] && w=$L/fixtures/wp2/cx-r327-cap.txt
  [ $r = r31d ] && w=$L/fixtures/wp2/cx-r31d-cap.txt
  ARM=cx5vmW bash /mnt/c/tmp/ch5/mkfix.sh v1 $w $r walk $src 2>&1 | tail -1
  python3 /mnt/c/tmp/ch5/addmov.py $L/fixtures/$r/cx-$r-walk-v1.armed.json
  python3 /mnt/c/tmp/ch5/addsnd.py $L/fixtures/$r/cx-$r-walk-v1.armed.json
done
