#!/bin/bash
# run1.sh <warp file> <run name> [seconds] [extra fp_run args]  (Git Bash; lane castle22)
set -euo pipefail
W=${1:?warp}; N=${2:?name}; S=${3:-60}; shift 3 || true
FP='\wsl.localhost\Ubuntu-24.04\root\work\lanes\castle22\tree\port\dreamcast\tools\d367\fullplay\fp_run.py'
BASE='C:\Flycast-Evidence\re4-dreamcast\castle22-20261022\base-k22a'
CAP="C:\Flycast-Evidence\re4-dreamcast\castle22-20261022\runs\$N"
python "$FP" --base "$BASE" --cap "$CAP" --syms "0x4238e0 0x4338e4 0x4338e0" --seconds "$S" --warp "$(cygpath -w "$W")" --name "$N" --align "$@" > "$(dirname "$W")/../log-$N.txt" 2>&1
echo "done $N rc=$?"
