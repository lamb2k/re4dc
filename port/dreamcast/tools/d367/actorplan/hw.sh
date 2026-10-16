#!/bin/bash
# hw.sh <scene> <arm label> <name> [count A:B] [stride] (WSL)
# Uses the T15 fixture and existing ext4 stager. Override T, K, BENCH_EV,
# ROUTE_OUT_ROOT, ROUTE_PROGRAMS_DIR and ROUTE_PROGRAMS_JSON for an isolated lane.
# ACTORPLAN_CALLTREE=0 drops raw traces after hwproject; default also runs cg.sh.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
T=${T:-$(cd "$HERE/../../../../.." && pwd)}
K=${K:-/root/probe/lanes-20261015/actorplan-k}
D367=$T/port/dreamcast/tools/d367
HW=${RE4DC_HARNESS:-/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1}
EV=${BENCH_EV:-/mnt/c/Flycast-Evidence/re4-dreamcast/actorplan-20261015}
B=${ROUTE_OUT_ROOT:-/root/probe/lanes/route}/out-$2
REGISTRY=${ROUTE_PROGRAMS_JSON:-$HW/programs-route.json}
export RE4DC_PROGRAMS_DIR=${ROUTE_PROGRAMS_DIR:-$HW/programs}
export RE4DC_STAGE_ROOT=${RE4DC_STAGE_ROOT:-$K/stage}
export RE4DC_DISCCACHE=${RE4DC_DISCCACHE:-0}
export PRUNE_AUTO=0
N=$3; WIN=${4:-500:799}; STRIDE=${5:-10}
WARPF=${BENCH_WARP:-$D367/benchmark/benchmark-$1-warp.txt}
E=$EV/hwmodel-$N
SCENARIO=actorplan-hw-$N
S=$HW/scenarios/$SCENARIO
test ! -e "$E" && test ! -e "$S"
mkdir -p "$K/hw" "$K/fix" "$EV"
D=${BENCH_DATA:-$(python3 - "$D367/test11/t11-fix.py" <<'PY'
import importlib.util as u, sys
s=u.spec_from_file_location('fixture',sys.argv[1]);m=u.module_from_spec(s);s.loader.exec_module(m)
print(m.T15_DATA)
PY
)}
FIX=$K/fix/$N.json
EXTRA=()
if [ -n "${BENCH_WORLD_LEVELS:-}" ]; then
  shopt -s nullglob
  for f in "$BENCH_WORLD_LEVELS"/ps2-wv*.re4mesh "$BENCH_WORLD_LEVELS"/ps2-wv*.r4sg; do
    EXTRA+=(--set "dc/native/r101/$(basename "$f")=$f")
  done
  [ "${#EXTRA[@]}" -gt 0 ] || { echo 'BENCH_WORLD_LEVELS has no level files'; exit 1; }
fi
python3 "$D367/test11/t11-fix.py" "$2" "$FIX" --data "$D" --warp "$WARPF" "${EXTRA[@]}" > "$K/hw/fixture-$N.log"
python3 "$D367/benchmark/fix-replace.py" "$FIX" "$WARPF" >> "$K/hw/fixture-$N.log"
python3 "$D367/stage_ext4/stage_scenario.py" "$SCENARIO" --arm candidate-route$2 --programs "$REGISTRY" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture "$FIX" > "$K/hw/stage-$N.json"
python3 - "$K/hw/stage-$N.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));assert d['status']=='STAGED_PAYLOAD_IDENTITY_PASS'
print(d['status'],d['disc_sha256'])
PY
FA=$(bash /root/probe/perf-20261004/kit/fa.sh "$B/re4dc-game.elf" | awk '{print $NF}')
DROP=(); [ "${ACTORPLAN_CALLTREE:-1}" = 1 ] || DROP=(--drop-traces)
rc=0
HWM_EVROOT=$EV HWM_DISCS=$EV/_discs HWM_MINFREE_MB=${MINFREE:-10000} \
  bash "$T/port/dreamcast/tools/hwmodel/hwproject.sh" --name "$N" --disc "$S/disc/disc.bin" \
  --frameaddr "$FA" --count "$WIN" --trace "${WIN%:*}:${WIN#*:}:$STRIDE" "${DROP[@]}" "$B" \
  > "$K/hw/hw-$N.log" 2>&1 || rc=$?
if [ -d "$E" ]; then
  cp "$FIX" "$E/fixture.json"
  cp "$WARPF" "$E/warp.txt"
  cp "$S/stage.json" "$E/stage.json"
  cp "$S/payload-manifest.json" "$E/payload-manifest.json"
  printf 'benchmark-%s %s count=%s trace=%s:%s data=%s\n' "$1" "$2" "$WIN" "$WIN" "$STRIDE" "$D" > "$E/SCENE.txt"
  # Only this invocation's verified, reconstructible disc. Preserve all reports.
  sha256sum "$S/disc/disc.bin" > "$S/disc.sha256"
  rm -f "$S/disc/disc.bin"
fi
tail -8 "$K/hw/hw-$N.log"
[ "$rc" = 0 ] || exit "$rc"
if [ "${ACTORPLAN_CALLTREE:-1}" = 1 ]; then bash "$HERE/cg.sh" "$E"; fi
python3 "$D367/benchmark/bench-split.py" "$E"
