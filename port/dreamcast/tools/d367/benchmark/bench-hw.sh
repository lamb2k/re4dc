#!/bin/bash
# bench-hw.sh <scene> <arm label> <name> [count A:B] [trace stride]  (WSL): SH-4 hardware-model CPU breakdown of one
# benchmark arm (lane crowd12, 2026-10-14). The arm is a cost build: the W recipe + PACE_MODE=off PC_SAMPLER_BYTES=8192
# (every tick draws, so hw ms per frame = CPU per drawn frame), e.g. LP=c12h XON="PACE_MODE=off PC_SAMPLER_BYTES=8192"
# test11/t11-build.sh tW -> c12htW. Fixture as bench-run.sh (t11-fix.py, T11_DATA, benchmark-<scene>-warp.txt); staged
# with stage-ms-c.py, hwproject.sh --count A:B --trace A:B:S --drop-traces; disc deleted after. Default window: global
# frames 500:1399 (about room frames 300..1200), 15 traced frames. Then bench-split.py prints the subsystem split.
# Evidence: C:\Flycast-Evidence\re4-dreamcast\bench-20261014\hwmodel-<name>.
set -u
SC=$1; L=$2; N=$3
HERE=$(cd "$(dirname "$0")" && pwd)
HWW=$(grep -m1 "^# bench-hwwindow" "$HERE/benchmark-$SC-warp.txt" | awk '{print $3}')
WIN=${4:-${HWW:-500:1399}}; STRIDE=${5:-60}
T11=$(dirname "$HERE")/test11
TREE=$(cd "$HERE/../../../../.." && pwd)
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
EV=${BENCH_EV:-/mnt/c/Flycast-Evidence/re4-dreamcast/bench-20261014}
B=/root/probe/lanes/route/out-$L
LOG=/root/probe/bench-stage; mkdir -p $LOG/fix "$EV" /mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs
FREE=$(df -BG --output=avail /mnt/c | tail -1 | tr -dc 0-9)
[ "$FREE" -ge "${BENCH_MIN_GB:-18}" ] || { echo "C: has $FREE GB free: not staging"; exit 1; }
D=$(python3 -c "import re;print(re.search(r\"^T11_DATA = '([^']*)'\", open('$T11/t11-fix.py').read(), re.M).group(1))")
D=${BENCH_DATA:-$D}   # BENCH_DATA: the whole data set (e.g. T121_DATA's list), not T11_DATA
FIX=$LOG/fix/hw-$N.json
python3 $T11/t11-fix.py $L $FIX --data $D --warp $HERE/benchmark-$SC-warp.txt > $LOG/fix-hw-$N.txt || exit 1
python3 $HERE/fix-replace.py $FIX $HERE/benchmark-$SC-warp.txt >> $LOG/fix-hw-$N.txt || exit 1
E=$EV/hwmodel-$N
[ ! -e "$E" ] || { echo "$E exists"; exit 1; }
cd "$HW" || exit 1
S=/mnt/c/Flycast-Evidence/re4-dreamcast/_ms-stage/bench-$N
python3 /root/probe/lanes-20261005/ms/kit/stage-ms-c.py bench-$N --arm candidate-route$L --programs "$HW/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $LOG/stage-hw-$N.json 2>&1
python3 -c "import json;d=json.load(open('$LOG/stage-hw-$N.json'));print(d['status'],d['disc_sha256'])" || { tail -5 $LOG/stage-hw-$N.json; exit 1; }
DISC="$S/disc/disc.bin"
DBC=/mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs/hwmodel-$N.bin
( while [ -f "$DISC" ]; do if [ -f "$DBC" ] && [ "$(stat -c %s "$DBC")" = "$(stat -c %s "$DISC")" ]; then sleep 3; rm -f "$DISC"; break; fi; sleep 2; done ) &
FA=$(bash /root/probe/perf-20261004/kit/fa.sh $B/re4dc-game.elf | awk '{print $NF}')
A=${WIN%:*}; Z=${WIN#*:}
echo "frameaddr $FA window $WIN stride $STRIDE"
HWM_EVROOT=$EV HWM_DISCS=/mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs HWM_MINFREE_MB=${MINFREE:-15000} \
  bash $TREE/port/dreamcast/tools/hwmodel/hwproject.sh --name $N --disc "$DISC" --frameaddr $FA --count $WIN \
  --trace $A:$Z:$STRIDE --drop-traces $B
rc=$?
rm -f "$DISC" "$DBC"; rm -rf "$S"
cp $FIX $E/fixture.json 2>/dev/null; cp $HERE/benchmark-$SC-warp.txt $E/warp.txt 2>/dev/null
echo "benchmark-$SC $L count=$WIN trace=$A:$Z:$STRIDE" > $E/SCENE.txt
echo "done $N rc=$rc"
sed -n 1,8p $E/proj/projection.txt
python3 $HERE/bench-split.py $E
