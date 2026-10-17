#!/bin/bash
# mkfix.sh <arm label> <out json> <warp file> (WSL): fixture on the test 17 data set (t11-fix.py T17V_DATA), armed with
# texchk/fixture_arm.py (every candidate overlay of the arm).
T=/root/probe/lanes-20261016/farmprop17/port/dreamcast/tools/d367
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T17V_DATA)")
mkdir -p $(dirname $2)
export RE4DC_RESIDENT_STRICT=1
python3 $T/test11/t11-fix.py $1 $2.raw.json --data $D --warp $3 > $2.log 2>&1 &&
python3 $T/texchk/fixture_arm.py $2.raw.json $2 $1 --programs-dir "$HW/programs" >> $2.log 2>&1 && echo "fix ok $2" || { echo "fix FAILED $2"; tail -5 $2.log; }
