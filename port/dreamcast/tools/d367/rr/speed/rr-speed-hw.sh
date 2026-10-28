#!/bin/bash
# rr-speed-hw.sh <label> <scene> <work dir> <evidence root> [window] [stride]   (WSL; lane guards28, 2026-10-28)
# One SH-4 hardware-model run (MODELLED) of cost arm out-<label>rW on speed/warps/<scene>.txt: payload fixture
# (t11-fix.py --base payload, the arm's own data line), staged with stage-scenario.py, hwproject.sh --count/--trace
# (default window global frames 700:759, stride 3: 20 traced frames, the perf-24b method), traces dropped, staged disc
# deleted after. Result: <evidence root>/hwmodel-<label>-<scene>/proj/projection.txt.
set -euo pipefail
X=${1:?label}; SC=${2:?scene}; W=${3:?work}; EV=${4:?evidence}
WIN=${5:-700:759}; ST=${6:-3}
HERE=$(cd "$(dirname "$0")" && pwd)
D367=$(dirname "$HERE"); D367=$(dirname "$D367")
TREE=$(cd "$D367/../../../.." && pwd)
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
B=/root/probe/lanes/route/out-${X}rW
N=$X-$SC
E=$EV/hwmodel-$N
[ ! -e "$E" ] || { echo "rr-speed-hw: $E exists"; exit 1; }
FREE=$(df -BG --output=avail /mnt/c | tail -1 | tr -dc 0-9)
[ "$FREE" -ge "${SPEED_MIN_GB:-12}" ] || { echo "rr-speed-hw: C: has $FREE GB free"; exit 1; }
set -a
# shellcheck source=/dev/null
[ -s "$W/$X.env" ] && . "$W/$X.env"
set +a
LOG=$W/stage; mkdir -p "$LOG" "$EV" /mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs
WARPF=$LOG/warp-$SC.txt
tr -d '\r' < "$HERE/warps/$SC.txt" > "$WARPF"
FIX=$LOG/fix-$N.json
python3 "$D367/test11/t11-fix.py" "${X}rW" "$FIX" --base payload --data "$(cat "$W/$X.data")" --warp "$WARPF" > "$LOG/fix-$N.txt"
python3 "$D367/benchmark/fix-replace.py" "$FIX" "$WARPF" >> "$LOG/fix-$N.txt"
S="$HW/scenarios/rrspeed-$N"
[ ! -e "$S" ] || { echo "rr-speed-hw: $S exists"; exit 1; }
cleanup() { rm -f "${S:?}/disc/disc.bin" "/mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs/hwmodel-${N:?}.bin"; rm -rf "${S:?}"; }
trap cleanup EXIT
( cd "$HW" && python3 stage-scenario.py "rrspeed-$N" --arm "candidate-route${X}rW" --programs "$HW/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture "$FIX" ) > "$LOG/stage-$N.json" 2>&1 || true
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['status'],d['disc_sha256'])" "$LOG/stage-$N.json" \
  || { tail -5 "$LOG/stage-$N.json"; exit 1; }
FA=$(python3 -c "import sys;print('%08x' % (int(open(sys.argv[1]).read().split()[3],16)+0x0c000000+64))" "$B/syms.txt")
A=${WIN%:*}; Z=${WIN#*:}
HWM_EVROOT=$EV HWM_DISCS=/mnt/c/Flycast-Evidence/re4-dreamcast/_bench-discs HWM_MINFREE_MB=${MINFREE:-5000} \
  bash "$TREE/port/dreamcast/tools/hwmodel/hwproject.sh" --name "$N" --disc "$S/disc/disc.bin" --frameaddr "$FA" --count "$WIN" \
  --trace "$A:$Z:$ST" --drop-traces "$B"
cp "$FIX" "$E/fixture.json"; cp "$WARPF" "$E/warp.txt"
echo "rr-speed $SC ${X}rW count=$WIN trace=$A:$Z:$ST data=$(cat "$W/$X.data")" > "$E/SCENE.txt"
grep 'hardware projection' "$E/proj/projection.txt"
