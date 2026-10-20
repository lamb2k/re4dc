#!/bin/bash
# fx-hw.sh <arm label> <name> [count A:B] [stride]  (lane fx19): hwproject of one arm on the r101 cross (behave18's hwcross warp copy).
set -euo pipefail
L=${1:?}; N=${2:?}; WIN=${3:-700:759}; STRIDE=${4:-3}
TREE=/root/work/lanes/actorplan19/tree
T11=$TREE/port/dreamcast/tools/d367/test11
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/actorplan19-20261019
DD=/mnt/c/Flycast-Evidence/re4-dreamcast/_actorplan19-discs
B=/root/probe/lanes/route/out-$L
K=/root/work/lanes/actorplan19/k
W=${FXWARP:-$K/hwcross-warp.txt}
LOG=$K/hwstage; mkdir -p $LOG/fix "$EV" "$DD"
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('f','$T11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17R_PAYLOAD+',res18f,boss18g50')")
FIX=$LOG/fix/hw-$N.json
python3 $T11/t11-fix.py $L $FIX --base payload --data $D --warp $W > $LOG/fix-hw-$N.txt
E=$EV/hwmodel-$N
[ ! -e "$E" ] || { echo "$E exists"; exit 1; }
cd "$HW"
S="$HW/scenarios/ap19-$N"
[ ! -e "$S" ] || { echo "$S exists"; exit 1; }
python3 $TREE/port/dreamcast/tools/d367/stage_ext4/stage_scenario.py ap19-$N --arm candidate-route$L --programs "$HW/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $LOG/stage-hw-$N.json 2>&1 || { tail -5 $LOG/stage-hw-$N.json; exit 1; }
python3 -c "import json;d=json.load(open('$S/stage.json'));print(d['status'],d['disc_sha256'])"
DISC="$S/disc/disc.bin"
DBC=$DD/hwmodel-$N.bin
( while [ -f "$DISC" ]; do if [ -f "$DBC" ] && [ "$(stat -c %s "$DBC")" = "$(stat -c %s "$DISC")" ]; then sleep 3; rm -f "$DISC"; break; fi; sleep 2; done ) &
A=${WIN%:*}; Z=${WIN#*:}
echo "window $WIN stride $STRIDE"
set +e
HWM_EVROOT=$EV HWM_DISCS=$DD HWM_MINFREE_MB=5000 \
  bash $TREE/port/dreamcast/tools/hwmodel/hwproject.sh --name $N --disc "$DISC" --count $WIN \
  --trace $A:$Z:$STRIDE --drop-traces $B
rc=$?
set -e
rm -f "$DISC" "$DBC"; rm -rf "${S:?}"
cp $FIX $E/fixture.json || true; cp $W $E/warp.txt || true
echo "$L fixture=$FIX count=$WIN stride=$STRIDE" > $E/SCENE.txt
echo "done $N rc=$rc"
sed -n 1,8p $E/proj/projection.txt
