#!/bin/bash
# fx.sh <arm label> <name> <warp file> (WSL; lane rigid20): Flycast fixture (Test 20 disc data line + the warp) for run.sh.
# Prints the fixture path.
set -euo pipefail
L=${1:?}; N=${2:?}; W=${3:?}
D367=/root/work/lanes/rigid20/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
K=/root/work/lanes/rigid20-scratch/k
mkdir -p "$K/fix"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=/root/re4data/private/rc19s-20261019
eval "$(grep '^DATA=' $D367/rr/recipe.conf)"
RAW=$K/fix/$N.raw.json; FIX=$K/fix/$N.json
python3 "$D367/test11/t11-fix.py" "$L" "$RAW" --base payload --data "$DATA" --warp "$W" > "$K/fix/$N.log" 2>&1 || { tail -5 "$K/fix/$N.log" >&2; exit 1; }
python3 "$D367/texchk/fixture_arm.py" "$RAW" "$FIX" "$L" --programs-dir "$RE4DC_PROGRAMS_DIR" >> "$K/fix/$N.log" 2>&1
echo "$FIX"
