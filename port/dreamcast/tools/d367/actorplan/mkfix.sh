#!/bin/bash
# mkfix.sh <arm label> <out json> <warp file> [pad] (WSL): fixture on the T15 data set (t11-fix.py T15_DATA)
T=/root/probe/lanes-20261016/actorplan17/tree/port/dreamcast/tools/d367
D=$(python3 -c "import importlib.util as u;s=u.spec_from_file_location('t','$T/test11/t11-fix.py');m=u.module_from_spec(s);s.loader.exec_module(m);print(m.T15_DATA)")
P=""; [ -n "${4:-}" ] && P="--pad $4"
mkdir -p $(dirname $2)
python3 $T/test11/t11-fix.py $1 $2 --data $D --warp $3 $P > $2.log 2>&1 && echo "fix ok $2" || { echo "fix FAILED"; tail -5 $2.log; }
