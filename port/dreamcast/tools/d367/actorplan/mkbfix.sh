#!/bin/bash
# mkbfix.sh <arm label> <out json> <warp file> (WSL): a benchmark-scene fixture on the T15 data set, built as hw.sh builds
# it (t11-fix.py T15_DATA -> benchmark/fix-replace.py -> texchk/fixture_arm.py), for a plain Flycast run (t-run.sh).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
D367=$(cd "$HERE/.." && pwd)
HW=${RE4DC_HARNESS:-/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1}
PD=${ROUTE_PROGRAMS_DIR:-$HW/programs}
D=${BENCH_DATA:-$(python3 - "$D367/test11/t11-fix.py" <<'PY'
import importlib.util as u, sys
s=u.spec_from_file_location('fixture',sys.argv[1]);m=u.module_from_spec(s);s.loader.exec_module(m)
print(m.T15_DATA)
PY
)}
mkdir -p "$(dirname "$2")"
RAW=$2.raw.json
python3 "$D367/test11/t11-fix.py" "$1" "$RAW" --data "$D" --warp "$3" > "$2.log" 2>&1
python3 "$D367/benchmark/fix-replace.py" "$RAW" "$3" >> "$2.log" 2>&1
python3 "$D367/texchk/fixture_arm.py" "$RAW" "$2" "$1" --programs-dir "$PD" >> "$2.log" 2>&1
echo "fix ok $2"
