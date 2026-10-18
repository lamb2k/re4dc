#!/bin/bash
# ch4regen gate runs (Git Bash): rfp-run-one.py per ch4 room on private harness h-rg4, 2 Flycasts at a time.
set -euo pipefail
export MSYS_NO_PATHCONV=1
export RE4DC_HARNESS=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4regen-20261018/h-rg4
export WSLENV=RE4DC_HARNESS/u
H='C:\Flycast-Evidence\re4-dreamcast\ch4regen-20261018\h-rg4'
K=C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts
T=/root/probe/lanes-20261018/ch4regen/tree
OUT=/c/Flycast-Evidence/re4-dreamcast/ch4regen-20261018/runs; mkdir -p "$OUT"
SUF=${SUF:?}
for r in "$@"; do
  while [ "$(jobs -r | wc -l)" -ge 2 ]; do sleep 5; done
  (rc=0; python $K/rfp-run-one.py --harness "$H" --room "$r" --stager stage-scenario.py --view walk --suffix "$SUF" --seconds 60 --min-free-gb 25 \
     --checker $T/port/dreamcast/tools/d367/texchk/cx_firstpass_check.py --tree $T \
     --fixture /root/probe/lanes-20261018/ch4regen/${GF:-gatefix2}/$r/cx-$r-${GT:-rg}.armed.json > "$OUT/$r-$SUF.json" 2>&1 || rc=$?
   echo "$r rc=$rc" >> "$OUT/$SUF.done") &
  sleep 5
done
wait
echo ALLDONE >> "$OUT/$SUF.done"
