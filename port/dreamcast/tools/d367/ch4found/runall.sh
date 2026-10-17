#!/bin/bash
# runall.sh <harness dir name> <fixture tag> <suffix> <parallel> rooms... (Git Bash): rfp-run-one.py per room, N at a time.
HN=$1; H="C:\\Flycast-Evidence\\re4-dreamcast\\ch4found-20261016\\$1"; TAG=$2; SUF=$3; N=$4; shift 4
K=C:/Users/lambd/.claude/skills/re4-room-firstpass/scripts
OUT=/c/tmp/ch4/runs; mkdir -p $OUT
export MSYS_NO_PATHCONV=1
for r in "$@"; do
  while [ $(jobs -r | wc -l) -ge $N ] || [ $(tasklist 2>/dev/null | grep -ci flycast) -ge ${FLYMAX:-8} ]; do sleep 5; done
  (python $K/rfp-run-one.py --harness "$H" --room $r --view walk --suffix $SUF --seconds ${SECS:-60} --min-free-gb ${MINFREE:-18} --checker ${CHECKER:-/root/probe/lanes-20261016/ch4found/tree/port/dreamcast/tools/d367/texchk/cx_firstpass_check.py} \
     --tree /root/probe/lanes-20261016/ch4found/tree \
     --fixture /root/probe/lanes-20261016/ch4found/fixtures/$r/cx-$r-$TAG.armed.json > $OUT/$HN-$r-$SUF.json 2>&1;
   echo "$r rc=$?" >> $OUT/$HN-$SUF.done) &
  sleep 5
done
wait
echo ALLDONE >> $OUT/$HN-$SUF.done
