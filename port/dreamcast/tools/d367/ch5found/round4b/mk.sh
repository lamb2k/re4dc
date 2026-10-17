#!/bin/bash
# mk.sh <arm> <variant> <warp> <EMXPREP> : r307 fixture with em36 from prepem/<EMXPREP>-em36 (round 4 B)
set -e
L=/root/probe/lanes-20261016/ch5found; S=/root/probe/lanes-20261014/st3/fixtures
A=$1; V=$2; W=$3; export EMXPREP=$4 EMX=em36
export PAK=$L/vram/tex-ch5c.pak RES=$L/vram/resident-ch5b.bin
r=r307
src=$(ls -t $S/$r/*.armed.json | head -1)
ARM=$A bash /mnt/c/tmp/ch5/mkfix4.sh $V $W $r walk $src 2>&1 | tail -1
python3 /mnt/c/tmp/ch5/addmov.py $L/fixtures/$r/cx-$r-walk-$V.armed.json >/dev/null
python3 /mnt/c/tmp/ch5/addsnd.py $L/fixtures/$r/cx-$r-walk-$V.armed.json
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));r=d['replace'];print('em36',r.get('em/em36.drs'),'mot',sum(1 for k in r if k.startswith('dc/mot/') and 'em36' in r[k]))" $L/fixtures/$r/cx-$r-walk-$V.armed.json
