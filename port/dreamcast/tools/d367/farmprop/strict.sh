#!/bin/bash
# strict.sh (Git Bash): STRICT + decisions trio, off (fp17orT) vs on (fp17qrT), stop tick 2000, 2 Flycasts at a time.
cd /c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/_tools
F=/root/probe/lanes-20261016/fp17/fix
for st in a b c; do
  secs=300; [ $st = a ] && secs=400
  ( TRACE=1 RE4DC_LOG_STOP_TICK=2000 bash t-run.sh st$st-o fp17orT $F/st$st-o.json $secs > st$st-o.log 2>&1 ) &
  sleep 20
  TRACE=1 RE4DC_LOG_STOP_TICK=2000 bash t-run.sh st$st-q fp17qrT $F/st$st-q.json $secs > st$st-q.log 2>&1
  wait
done
for st in a b c; do
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash /mnt/c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/_tools/strict2.sh \
    /mnt/c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/st$st-o/capture/run-output.txt \
    /mnt/c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/st$st-q/capture/run-output.txt st$st 2>&1 | cut -c1-220
done
echo STRICT_DONE
