#!/usr/bin/env bash
set -euo pipefail
D=/root/work/lanes/stat-bytes23-complete-scratch/guest-slots
mkdir -p "$D"
while :; do
 for N in 0 1 2; do
  exec 6>"$D/slot-$N.lock"
  if flock -n 6;then
   "$@"
   exit $?
  fi
  exec 6>&-
 done
 sleep 2
done
