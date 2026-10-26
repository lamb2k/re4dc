#!/bin/bash
# run1.sh <warp file> <run name> [seconds] [extra fp_run args]  (Git Bash; lane castle22, fixed castle31 10-26)
# Env: BASE (Windows path of the fp_master base dir), EVD (Windows evidence root), SYMS (syms line of the build),
#      ALIGN=1 adds --align (hwmodel interpreter: slow, crash checks only).
#      FPDIR (a C: dir holding a copy of fullplay/fp_run.py; Windows Python mangles \\wsl.localhost script paths).
set -euo pipefail
W=${1:?warp}; N=${2:?name}; S=${3:-60}; shift 3 || true
: "${BASE:?BASE}" "${EVD:?EVD}" "${SYMS:?SYMS}" "${FPDIR:?FPDIR}"
FP="$FPDIR/fp_run.py"
[ -f "$FP" ] || { echo "copy fullplay/fp_run.py to $FPDIR first"; exit 2; }
CAP="$EVD\\runs\\$N"
rc=0
python "$(cygpath -w "$FP")" --base "$BASE" --cap "$CAP" --syms "$SYMS" --seconds "$S" --warp "$(cygpath -w "$W")" \
  --name "$N" ${ALIGN:+--align} "$@" > "$(dirname "$W")/log-$N.txt" 2>&1 || rc=$?
echo "done $N rc=$rc"
