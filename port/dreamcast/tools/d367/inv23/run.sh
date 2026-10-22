#!/bin/bash
# run.sh <base win> <twin label> <tag>   (Git Bash) runs inv100 + inv101 in parallel, 60 s, console Flycast
set -euo pipefail
BASE=${1:?}; TW=${2:?}; TAG=${3:?}
F=//wsl.localhost/Ubuntu-24.04/root/work/lanes/inv23/port/dreamcast/tools/d367/fullplay
S=$(cat //wsl.localhost/Ubuntu-24.04/root/probe/lanes/route/out-$TW/syms.txt)
EV='C:\Flycast-Evidence\re4-dreamcast\inv23'
FX='C:\Flycast-Evidence\re4-dreamcast\inv23\fixtures'
export RE4DC_EMU=console FP_NOLIMIT=1 RE4DC_GD_PROFILE=${GDP:-}
for sc in ${SCENES:-inv100 inv101}; do
  python $F/fp_run.py --base "$BASE" --warp "$FX\\$sc-warp.txt" --cap "$EV\\$TAG-$sc" --syms "$S" --seconds 60 --period 3 --name $TAG-$sc > /c/Flycast-Evidence/re4-dreamcast/inv23/fixtures/$TAG-$sc.out 2>&1 &
done
wait
echo done
