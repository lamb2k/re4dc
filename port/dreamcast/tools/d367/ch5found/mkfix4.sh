#!/bin/bash
# mkfix.sh <variant> <warp.txt> <room> <view> [st3 fixtures csv]: one armed island fixture for cx5amW (union pak, island resident lists)
set -e
L=/root/probe/lanes-20261016/ch5found
S=/root/probe/lanes-20261014/st3/fixtures
V=$1; W=$2; R=$3; VIEW=$4
SRC=${5:-$S/r300/cx-r300-walk-m1.armed.json,$S/r301/cx-r301-fight1-j1.armed.json,$S/r303/cx-r303-walk-m1.armed.json,$S/r304/cx-r304-walk-e3.armed.json}
ARM=${ARM:-cx5amW}
cp /mnt/c/tmp/ch5/c5merge.py $L/tools/
TOOLS=/root/probe/codex-ps2-assets-20261013/tree
CAND=$L/build/programs/candidate-route$ARM
D=$L/fixtures/$R; mkdir -p $D
PAK=${PAK-$L/vram/tex-ch5.pak} python3 $L/tools/c5merge.py /root/probe/lanes-20261016/ch3found/fix/t15-mW.json $SRC $D/cx-$R-$VIEW-$V.unarmed.json $CAND ${RES-$L/vram/resident-ch5.bin} --warp $W
[ -n "${EMX:-}" ] && python3 /mnt/c/tmp/ch5/emx.py $D/cx-$R-$VIEW-$V.unarmed.json $EMX
python3 $TOOLS/port/dreamcast/tools/d367/texchk/fixture_arm.py $D/cx-$R-$VIEW-$V.unarmed.json $D/cx-$R-$VIEW-$V.armed.json $ARM --candidate-dir $CAND | tail -1
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d['remove']=[x for x in d.get('remove',[]) if x not in d['replace']];json.dump(d,open(sys.argv[1],'w'),indent=1,sort_keys=True)" $D/cx-$R-$VIEW-$V.armed.json
