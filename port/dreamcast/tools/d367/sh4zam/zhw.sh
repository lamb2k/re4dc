#!/bin/bash
# hw.sh <arm label> <name> [count A:B] [trace stride]  (WSL; lane sh4zam-direct 2026-10-15): SH-4 hardware-model CPU breakdown of
# one cost arm (PACE_MODE=off PC_SAMPLER_BYTES=8192) on the r101 cross benchmark scene (r101cross-warp.txt), test 13
# data (T121_DATA). Copy of tools/d367/benchmark/bench-hw.sh with the 12.1 data and this lane's warp; evidence
# D:\Flycast-Evidence\re4-dreamcast\sh4zam-20261015\hwmodel-<name>; disc deleted after.
set -u
L=$1; N=$2
WIN=${3:-500:1099}; STRIDE=${4:-60}
K=/root/probe/lanes-20261015/sh4zam
W=${HWWARP:-$K/r101cross-warp.txt}
TREE=/root/probe/lanes-20261015/sh4zam/tree
T11=$TREE/port/dreamcast/tools/d367/test11
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
EV=/mnt/d/Flycast-Evidence/re4-dreamcast/sh4zam-20261015
B=/root/probe/lanes/route/out-$L
LOG=$K/hwstage; mkdir -p $LOG/fix /mnt/d/Flycast-Evidence/re4-dreamcast/_sh4zam-discs
D=r119c,em29,fbec,r100tr4,smx101,sg101,t12tex,objs12b,merchant,items12,acc12d,blackps2w,t121tex,objs13d,ashley13,bake13,t13tex
FIX=$LOG/fix/hw-$N.json
python3 $T11/t11-fix.py $L $FIX --data $D --warp $W > $LOG/fix-hw-$N.txt || exit 1
E=$EV/hwmodel-$N
[ ! -e "$E" ] || { echo "$E exists"; exit 1; }
cd "$HW" || exit 1
S=/mnt/c/Flycast-Evidence/re4-dreamcast/_ms-stage/sz-$N
python3 /root/probe/lanes-20261005/ms/kit/stage-ms-c.py sz-$N --arm candidate-route$L --programs "$HW/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $LOG/stage-hw-$N.json 2>&1
python3 -c "import json;d=json.load(open('$LOG/stage-hw-$N.json'));print(d['status'],d['disc_sha256'])" || { tail -5 $LOG/stage-hw-$N.json; exit 1; }
DISC="$S/disc/disc.bin"
DBC=/mnt/d/Flycast-Evidence/re4-dreamcast/_sh4zam-discs/hwmodel-$N.bin
( while [ -f "$DISC" ]; do if [ -f "$DBC" ] && [ "$(stat -c %s "$DBC")" = "$(stat -c %s "$DISC")" ]; then sleep 3; rm -f "$DISC"; break; fi; sleep 2; done ) &
FA=$(bash /root/probe/perf-20261004/kit/fa.sh $B/re4dc-game.elf | awk '{print $NF}')
A=${WIN%:*}; Z=${WIN#*:}
echo "frameaddr $FA window $WIN stride $STRIDE"
HWM_EVROOT=$EV HWM_DISCS=/mnt/d/Flycast-Evidence/re4-dreamcast/_sh4zam-discs HWM_MINFREE_MB=${MINFREE:-15000} \
  bash $TREE/port/dreamcast/tools/hwmodel/hwproject.sh --name $N --disc "$DISC" --frameaddr $FA --count $WIN \
  --trace $A:$Z:$STRIDE --drop-traces $B
rc=$?
rm -f "$DISC" "$DBC"; rm -rf "$S"
cp $FIX $E/fixture.json 2>/dev/null; cp $W $E/warp.txt 2>/dev/null
echo "$(basename $W) $L count=$WIN trace=$A:$Z:$STRIDE data=T13_DATA" > $E/SCENE.txt
echo "done $N rc=$rc"
sed -n 1,8p $E/proj/projection.txt
python3 $TREE/port/dreamcast/tools/d367/benchmark/bench-split.py $E
