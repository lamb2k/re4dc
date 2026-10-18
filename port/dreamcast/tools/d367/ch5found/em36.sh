#!/bin/bash
# em36 (regenerator / iron maiden) little-endian mirror with the current le_mirror (round 10 PTH qualification)
set -e
L=/root/probe/lanes-20261016/ch5found
T=$L/tree/port/dreamcast/tools
S=/root/probe/lanes-20261014/st3/deps2/source
W=$L/emprep3; rm -rf $W; mkdir -p $W/src/em
ln $S/em/em36.drs $W/src/em/em36.drs
echo em/em36.drs > $W/req.txt
python3 $T/le_mirror.py $W/src $W/out --require $W/req.txt > $W/em36.log 2>&1; echo "rc=$?"
tail -6 $W/em36.log | cut -c1-200
ls -la $W/out/em 2>/dev/null
