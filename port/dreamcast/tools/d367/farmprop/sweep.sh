#!/bin/bash
# sweep.sh <rooms...> (Git Bash): per room, the CAST-GC/TEXCHK check arm fp17mmW (PROP_GATE=1) and the =2 check arm
# fp17crW in parallel (2 Flycasts), 60 s, castgc census warps.
cd /c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/_tools
F=/root/probe/lanes-20261016/fp17/fix
for r in "$@"; do
  bash t-run.sh sw-$r-m fp17mmW $F/sm-$r.json 60 > sw-$r-m.log 2>&1 &
  sleep 20
  bash t-run.sh sw-$r-c fp17crW $F/sc-$r.json 60 > sw-$r-c.log 2>&1
  wait
  echo "$r $(tail -2 sw-$r-m.log | head -1) | $(grep -a '^PGATE' ../sw-$r-c/capture/run-output.txt | tail -1 | grep -o 'culled=[0-9]* .*')"
done
echo SWEEP_DONE
