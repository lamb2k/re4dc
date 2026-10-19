#!/bin/bash
# strict.sh <tag> <scene...> (Git Bash): STRICT pairs e19krT vs e19wrT (OCCL room files), one Flycast at a time.
set -euo pipefail
TAG=${1:?}; shift
D=$(cd "$(dirname "$0")" && pwd)
S=/root/work/lanes/engine19/port/dreamcast/tools/d367/fullplay/segments
E=/c/Flycast-Evidence/re4-dreamcast/engine19-20261019
export RC19D=/root/re4data/private/rc19o2-20261019
export RE4DC_LOG_STOP_TICK=${STOP:-1600}
for sc in "$@"; do
  pad=""; [ "$sc" = h2 ] && pad=$S/h2-pad.txt
  for arm in k w; do
    N=$TAG-$sc-$arm
    W=$S/$sc-warp.txt; case $sc in cross*|farm*) W=/root/probe/lanes-20261019/engine19/k/$sc-warp.txt;; esac
    PURPOSE="engine19 STRICT $sc arm e19${arm}rT stop $RE4DC_LOG_STOP_TICK" bash "$D/g.sh" $N e19${arm}rT $W "$pad" 60 | tail -1
  done
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- python3 /root/work/lanes/engine19/port/dreamcast/tools/game30/logic_trace_diff.py \
    --align frame /mnt/c/Flycast-Evidence/re4-dreamcast/engine19-20261019/$TAG-$sc-k/capture/run-output.txt \
    /mnt/c/Flycast-Evidence/re4-dreamcast/engine19-20261019/$TAG-$sc-w/capture/run-output.txt > $E/$TAG-$sc-diff.txt 2>&1 || true
  echo "== $sc"; tail -4 $E/$TAG-$sc-diff.txt
  grep -a "ENEMYVIS r1.. tests\|INVISPCO" $E/$TAG-$sc-w/capture/run-output.txt | tail -2
done
