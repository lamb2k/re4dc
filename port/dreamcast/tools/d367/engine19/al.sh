#!/bin/bash
# al.sh <A|B> <tag> (Git Bash): align-logger (hwmodel interpreter, HWTRACE_ALIGN=1) run of a whole bench disc.
set -euo pipefail
X=${1:?}; TAG=${2:?}
F=//wsl.localhost/Ubuntu-24.04/root/work/lanes/engine19/port/dreamcast/tools/d367/fullplay
C='C:\Flycast-Evidence\re4-dreamcast\engine19-20261019\'$TAG-b$X
cd $F
python fp_run.py --disc 'C:\Game Dev\Emulators\RE4DC-Bench-T19-WallCheck-5edfcd12-s4\'$X'\gdemu' --cap "$C" \
  --syms "$(cat //wsl.localhost/Ubuntu-24.04/root/probe/lanes/route/out-e19b$X/syms.txt)" --seconds 3600 \
  --stop 'bench: results screen' --grace 30 --name $TAG-b$X --align | tail -1
E=/c/Flycast-Evidence/re4-dreamcast/engine19-20261019/$TAG-b$X
grep -a "bench: scene .* end\|bench: code" $E/run-output.txt | cut -c1-160
echo "halt/fault/oom=$(grep -a -c 'HALT\|FAULT\|Out of memory' $E/run-output.txt || true) align_lines=$(grep -v -c 'hwtrace init' $E/hwtrace.log || true)"
rm -f $E/track0* $E/disc.gdi
