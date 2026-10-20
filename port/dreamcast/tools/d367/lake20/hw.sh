#!/bin/bash
# hw.sh <arm label> <name> <warp file> [count A:B] [stride]   (env PAD=<padscript>) (WSL; lane lake20, after scenery19 k/hw.sh): hwproject of
# one PACE_MODE=off build. Fixture: the Test 19.1 disc data line (rr/recipe.conf DATA) on the payload base + the warp.
set -euo pipefail
L=${1:?}; N=${2:?}; W=${3:?}; WIN=${4:-700:759}; STRIDE=${5:-3}
TREE=/root/work/lanes/lake20
D367=$TREE/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
EV=/mnt/c/Flycast-Evidence/re4-dreamcast/lake20-20261020
DD=/mnt/c/Flycast-Evidence/re4-dreamcast/_lake20-discs
B=/root/probe/lanes/route/out-$L
K=/root/work/lanes/lake20-scratch/k
mkdir -p "$K/fix" "$EV" "$DD"
export RE4DC_PROGRAMS_DIR=$HW/programs
export RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D367/rr/recipe.conf)"
RAW=$K/fix/hw-$N.raw.json; FIX=$K/fix/hw-$N.json
python3 "$D367/test11/t11-fix.py" "$L" "$RAW" --base payload --data "$DATA" --warp "$W" ${PAD:+--pad "$PAD"} > "$K/fix/hw-$N.log" 2>&1 || { tail -5 "$K/fix/hw-$N.log"; exit 1; }
python3 "$D367/benchmark/fix-replace.py" "$RAW" "$W" >> "$K/fix/hw-$N.log" 2>&1
python3 "$D367/texchk/fixture_arm.py" "$RAW" "$FIX" "$L" --programs-dir "$RE4DC_PROGRAMS_DIR" >> "$K/fix/hw-$N.log" 2>&1
E=$EV/hwmodel-$N
[ ! -e "$E" ] || { echo "$E exists"; exit 1; }
cd "$HW"
S="$HW/scenarios/lk20-$N"
[ ! -e "$S" ] || { echo "$S exists"; exit 1; }
python3 $D367/stage_ext4/stage_scenario.py lk20-$N --arm candidate-route$L --programs "$HW/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $FIX > $K/stage-hw-$N.json 2>&1 || { tail -5 $K/stage-hw-$N.json; exit 1; }
DISC="$S/disc/disc.bin"
DBC=$DD/hwmodel-$N.bin
( while [ -f "$DISC" ]; do if [ -f "$DBC" ] && [ "$(stat -c %s "$DBC")" = "$(stat -c %s "$DISC")" ]; then sleep 3; rm -f "$DISC"; break; fi; sleep 2; done ) &
A=${WIN%:*}; Z=${WIN#*:}
set +e
HWM_EVROOT=$EV HWM_DISCS=$DD HWM_MINFREE_MB=5000 \
  bash $TREE/port/dreamcast/tools/hwmodel/hwproject.sh --name $N --disc "$DISC" --count $WIN \
  --trace $A:$Z:$STRIDE --drop-traces $B
rc=$?
set -e
rm -f "$DISC" "$DBC"; rm -rf "${S:?}"
cp $FIX $E/fixture.json || true; cp $W $E/warp.txt || true
echo "$L count=$WIN stride=$STRIDE" > $E/SCENE.txt
echo "done $N rc=$rc"
sed -n 1,10p $E/proj/projection.txt || true
