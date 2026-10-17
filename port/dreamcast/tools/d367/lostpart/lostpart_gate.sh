#!/bin/bash
# lostpart_gate.sh <room> <original dir> <reduced dir> <walk.json> [level]   (Git Bash, Windows Python with numpy + Pillow)
# REQUIRED landing gate for a reduced PS2 world (2026-10-16, user: the reduction tool broke the r101 stake, pyre plank
# and fence rails silently). Checks <reduced dir>/ps2-wv<level>.re4mesh (+ its ps2-world.r4pw) against the original
# level 0 (<original dir>/ps2-world.re4mesh + .r4pw) with lostpart.py --cams --stamp. The stamp LOSTPART.txt lands next
# to the reduced mesh; tools/d367/test11/t11-fix.py refuses to stage any ps2-wv* file without a PASS stamp of the same
# sha256. Exit 0 = PASS (0 flagged pieces), 1 = FAIL. Results: <reduced dir>/lostpart/<room>.{txt,json,-flags.png}.
set -u
R=$1; O=$2; N=$3; W=$4; L=${5:-5}
here=$(cd "$(dirname "$0")" && pwd)
py=$(cygpath -w "$here/lostpart.py" 2>/dev/null || echo "$here/lostpart.py")
MSYS_NO_PATHCONV=1 python -X utf8 "$py" "$N/lostpart" --name $R --orig "$O/ps2-world.re4mesh" "$O/ps2-world.r4pw" \
  --red "$N/ps2-wv$L.re4mesh" "$N/ps2-world.r4pw" --walk "$W" --room $R --cams --stamp | tail -2
head -1 "$N/LOSTPART.txt"
grep -q ": PASS (" "$N/LOSTPART.txt"
