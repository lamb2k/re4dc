#!/bin/bash
# c3g-grun.sh <room>... (Git Bash; lane ch3gate): rfp-run-one.py per castle room on private harness h-c3g, at most 2 Flycasts.
# "recovered-data gate, ch1-2 at current versions". rfp-run-one deletes each disc after its run (sha kept).
set -euo pipefail
export MSYS_NO_PATHCONV=1
export RE4DC_HARNESS=/mnt/c/Flycast-Evidence/re4-dreamcast/ch3gate-20261018/h-c3g
export WSLENV=RE4DC_HARNESS/u
H='C:\Flycast-Evidence\re4-dreamcast\ch3gate-20261018\h-c3g'
K=C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts
T=/root/probe/lanes-20261018/ch3gate/tree
OUT=/c/Flycast-Evidence/re4-dreamcast/ch3gate-20261018/runs; mkdir -p "$OUT"
SUF=${SUF:?}
for r in "$@"; do
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
  (rc=0; python $K/rfp-run-one.py --harness "$H" --room "$r" --stager stage-scenario.py --view gate --suffix "$SUF" --seconds 60 --min-free-gb 25 \
     --checker $T/port/dreamcast/tools/d367/texchk/cx_firstpass_check.py --tree $T \
     --fixture /root/probe/lanes-20261018/ch3gate/gfix2/$r/cx-$r-g.armed.json > "$OUT/$r-$SUF.json" 2>&1 || rc=$?
   echo "$r rc=$rc" >> "$OUT/$SUF.done") &
  sleep 5
done
wait
echo ALLDONE >> "$OUT/$SUF.done"
