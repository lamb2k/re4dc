#!/bin/bash
# kos.sh <tag> <arm> [scenes] (Git Bash): lane KOS 48 KiB squeeze check, same scenes/markers/criteria as
# fullplay/kos_squeeze.sh, run one at a time through g.sh fixtures.
set -euo pipefail
TAG=${1:?}; ARM=${2:?}; SCENES=${3:-"fight call door leave100 leave103"}
D=$(cd "$(dirname "$0")" && pwd)
E=/c/Flycast-Evidence/re4-dreamcast/engine19-20261019
K=/root/probe/lanes-20261019/engine19/k
SEG=/root/work/lanes/engine19/port/dreamcast/tools/d367/fullplay/segments
export RC19D=/root/re4data/private/rc19o2-20261019
declare -A WARP=( [fight]=kos-fight-warp.txt [call]=kos-call-warp.txt [door]=door103-warp.txt [leave100]=kos-leave100-warp.txt [leave103]=kos-leave103-warp.txt )
declare -A END=( [fight]='warp: alert at room frame' [call]='subscreen backing: open' [door]='phase=enter room=103' [leave100]='phase=enter room=100' [leave103]='phase=enter room=103' )
declare -A SECS=( [fight]=60 [call]=60 [door]=60 [leave100]=60 [leave103]=60 )
fail=0
for sc in $SCENES; do
  for lv in 49152:0 49152:1; do
    n=${lv%:*}; f=${lv#*:}; N=$TAG-$sc-$f
    MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash "$K/sq.sh" "$SEG/${WARP[$sc]}" "$K/$N-warp.txt" "$n" "$f"
    PURPOSE="engine19 kos squeeze $sc $lv" bash "$D/g.sh" $N $ARM $K/$N-warp.txt "" ${SECS[$sc]} > /dev/null 2>&1 || true
    R=$E/$N/capture/run-output.txt
    mn=$(grep -a "kos watch:" $R | sed 's/.*headroom=\([0-9]*\).*/\1/' | sort -n | head -1 || true)
    tp=$(grep -a "kos watch:" $R | sed 's/.*top=\([0-9]*\).*/\1/' | sort -n | head -1 || true)
    oom=$(grep -ac "Out of memory\|MISSING\|HALT" $R || true)
    held=$(grep -a "kos squeeze:" $R | head -1 | sed 's/.*held=\([0-9]*\).*/\1/' || true)
    end=$(grep -ac "${END[$sc]}" $R || true)
    ok=PASS; { [ "$oom" = 0 ] && [ -n "$mn" ] && [ "$mn" -ge 4096 ] && [ "$held" = "$n" ] && [ "$end" -ge 1 ]; } || { ok=FAIL; fail=1; }
    echo "$ok $N held=$held min_headroom=$mn min_top=$tp oom_lines=$oom end_marker=$end"
  done
done
[ $fail = 0 ] && echo "KOS SQUEEZE GATE PASS" || echo "KOS SQUEEZE GATE FAIL"
