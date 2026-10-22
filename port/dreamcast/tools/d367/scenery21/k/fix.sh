#!/bin/bash
# fix.sh <arm label> <name> <warp file> [pad] (WSL): actorplan19 fixture, current data (T17R_PAYLOAD), payload base.
set -euo pipefail
LAB=${1:?}; N=${2:?}; WARPF=${3:?}
T=/root/work/lanes/scenery21
D367=$T/port/dreamcast/tools/d367
K=/root/work/lanes/scenery21-scratch/k
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs
mkdir -p "$K/fix"
D0=$(python3 - "$D367/test11/t11-fix.py" <<'PY'
import importlib.util as u, sys, os
s=u.spec_from_file_location('fixture',sys.argv[1]);m=u.module_from_spec(s);s.loader.exec_module(m)
print(m.T17R_PAYLOAD+",res18f"+os.environ.get('DX',''))
PY
)
RAW=$K/fix/$N.raw.json; FIX=$K/fix/$N.json
python3 "$D367/test11/t11-fix.py" "$LAB" "$RAW" --base payload --data "$D0" --warp "$WARPF" ${4:+--pad "$4"} > "$K/fix/$N.log" 2>&1
mv "$RAW" "$RAW.pre"
bash "$D367/ch2/ch2-gigante-g50.sh" "$LAB" "$RAW" --base "$RAW.pre" --base-label "$LAB" >> "$K/fix/$N.log" 2>&1
python3 "$D367/benchmark/fix-replace.py" "$RAW" "$WARPF" >> "$K/fix/$N.log" 2>&1
python3 "$D367/texchk/fixture_arm.py" "$RAW" "$FIX" "$LAB" --programs-dir "$RE4DC_PROGRAMS_DIR" >> "$K/fix/$N.log" 2>&1
echo "fix ok $FIX"
