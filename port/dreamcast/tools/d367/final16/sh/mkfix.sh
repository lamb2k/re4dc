#!/bin/bash
# mkfix.sh <variant> <warp.txt> <prep dir> <movies csv|-> [fx extra args]: one armed r332 fixture for arm $ARM (default f1mW)
# = ch5found16's island fixture recipe (c5merge: T15 mW data + the st3 lane's r332 room fixture + island pak tex-ch5c +
# resident-ch5b) + Saddler's data (fx.py) + the island sound data (ch5found's addsnd.py).
set -e
L=/root/probe/lanes-20261016/final16
C5=/root/probe/lanes-20261016/ch5found
S=/root/probe/lanes-20261014/st3/fixtures
V=$1; W=$2; PREP=$3; MOV=$4; shift 4
ARM=${ARM:-f1mW}
PY="/mnt/c/Game Dev/Emulators/final16-20261016/py"
TOOLS=/root/probe/codex-ps2-assets-20261013/tree
CAND=$L/build/programs/candidate-route$ARM
D=$L/fixtures/r332; mkdir -p $D
SRC=$S/r332/cx-r332-walk-e4.armed.json
U=$D/fx-r332-$V.unarmed.json; A=$D/fx-r332-$V.armed.json
PAK=${PAK-$C5/vram/tex-ch5c.pak} python3 $C5/tools/c5merge.py /root/probe/lanes-20261016/ch3found/fix/t15-mW.json $SRC $U $CAND ${RES-$C5/vram/resident-ch5b.bin} --warp $W 2>&1 | tail -1
[ "$MOV" = "-" ] && MOV=""
python3 "$PY/fx.py" $U --prep $PREP --movies "$MOV" "$@"
python3 $TOOLS/port/dreamcast/tools/d367/texchk/fixture_arm.py $U $A $ARM --candidate-dir $CAND | tail -1
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));d['remove']=[x for x in d.get('remove',[]) if x not in d['replace']];json.dump(d,open(sys.argv[1],'w'),indent=1,sort_keys=True)" $A
python3 "$PY/addsnd2.py" $A
python3 -c "import json,sys;r=json.load(open(sys.argv[1]))['replace'];print('em31',r.get('em/em31.drs'),'pak',r.get('dc/tex.pak'),'res',r.get('dc/resident.bin'),'warp',r.get('dc/warp.txt'));print('movies',sorted(k for k in r if k.startswith('dc/movie/r33')))" $A
