#!/bin/bash
# stq14.sh (Git Bash): after hw queues J and K, STRICT pairs zt0rT vs zt7rT (GAME_SHZ_MEM mask 0 vs 7, t14/rc data), windows
# fight / bell / h2 / door103, stop tick 600, two Flycasts at a time (the pair of one window), then the zm eq reruns.
SCR=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261015/sh4zam/scr
D=/root/probe/lanes-20261015/sh4zam/adopt/port/dreamcast/tools/d367
Z=/c/Flycast-Evidence/re4-dreamcast/sh4zam-skin-20261015/_tools/zrunc14.sh
for q in J K; do until grep -q "queue $q finished" $SCR/hwq-$q.log 2>/dev/null; do sleep 30; done; done
waitspace() { for i in $(seq 1 120); do f=$(df -k /c | awk 'NR==2{print $4}'); [ "$f" -ge 19000000 ] && return 0; sleep 30; done; }
for s in fight bell h2 door103; do
  P=
  case $s in
    fight) W=$D/fullplay/segments/kos-fight-warp.txt ;;
    bell) W=$D/fullplay/segments/bell-warp.txt ;;
    h2) W=$D/fullplay/segments/h2-warp.txt; P=$D/fullplay/segments/h2-pad.txt ;;
    door103) W=$D/fullplay/segments/door103-warp.txt ;;
  esac
  for m in 0 7; do
    waitspace
    TRACE=1 STOP=600 PURPOSE="sh4zam-adopt GAME_SHZ_MEM STRICT $s: zt${m}rT (mask $m), stop 600" \
      bash $Z sm-$s-$m zt${m}rT $W 60 $P > $SCR/sm-$s-$m.log 2>&1 &
    sleep 45
  done
  wait
  echo "$(date +%T) $s: $(tail -2 $SCR/sm-$s-0.log | head -1) | $(tail -2 $SCR/sm-$s-7.log | head -1)" >> $SCR/sm.log
done
echo "$(date +%T) strict14 finished" >> $SCR/sm.log
