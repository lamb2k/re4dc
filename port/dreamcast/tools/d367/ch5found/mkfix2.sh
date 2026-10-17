#!/bin/bash
# round 2: one armed fixture per room (arm cx5cmW, union pak), warp from fixtures/wp2, src = the room's newest st3 armed fixture
set -e
python3 /mnt/c/tmp/ch5/mkwarps.py
S=/root/probe/lanes-20261014/st3/fixtures
L=/root/probe/lanes-20261016/ch5found
for r in "$@"; do
  src=$(ls -t $S/$r/*.armed.json | head -1)
  ARM=cx5cmW bash /mnt/c/tmp/ch5/mkfix.sh r2 $L/fixtures/wp2/cx-$r-r2.txt $r walk $src 2>&1 | tail -2
done
