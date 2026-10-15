#!/bin/bash
# hwq.sh <queue name> <label:name:scene> ...: run hw-model cost runs one after another (scene c = r101 cross 500:799,
# h = r101 house 1700:1999; 10 traced frames). Logs in scr/hw-<name>.log.
K=/root/probe/lanes-20261015/sh4zam
Q=$1; shift
for job in "$@"; do
  IFS=: read -r L N S <<< "$job"
  if [ "$S" = h ]; then
    HWWARP=$K/r101house-warp.txt bash $K/scr/zhwc.sh $L $N 1700:1999 30 > $K/scr/hw-$N.log 2>&1
  else
    bash $K/scr/zhwc.sh $L $N 500:799 30 > $K/scr/hw-$N.log 2>&1
  fi
  echo "$(date +%T) done $N rc=$?" >> $K/scr/hwq-$Q.log
done
echo "$(date +%T) queue $Q finished" >> $K/scr/hwq-$Q.log
