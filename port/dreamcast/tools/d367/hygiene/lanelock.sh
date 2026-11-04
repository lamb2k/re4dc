#!/bin/bash
# lanelock.sh <command...>: run a heavy build / disc-staging step under one of the N build slots
# (/root/probe/lane-build-<i>.lock, i=1..N; N from /root/probe/lane-build-slots, default 3, re-read every pass so a
# raised N reaches jobs already waiting). Takes the first free slot; if all are busy, waits on them in turn.
# Flycast runs do NOT use this: they use the 16-slot trace_lock. Wrap BUILDS, not whole test cycles: a cycle that
# holds a slot through its Flycast runs starves every other lane (11-03: jobs waited > 1 h at 83% CPU, 0 compiles).
set -u
[ "$#" -gt 0 ] || { echo "usage: lanelock.sh <command...>"; exit 2; }
c=$(df --output=avail -BG /mnt/c | tail -1 | tr -dc 0-9)
e=$(df --output=avail -BG /mnt/e | tail -1 | tr -dc 0-9)
[ "${c:-0}" -ge 20 ] || { echo "lanelock: C: ${c}G < 20G, refusing"; exit 3; }
[ "${e:-0}" -ge 50 ] || { echo "lanelock: E: ${e}G < 50G, refusing"; exit 3; }
while :; do
  N=$(cat /root/probe/lane-build-slots 2>/dev/null || echo 3)
  for i in $(seq 1 "$N"); do
    L=/root/probe/lane-build-$i.lock
    exec 9>"$L"
    if flock -n 9; then
      echo "lanelock: slot $i/$N ($(date +%T)) $*" >&2
      "$@"; rc=$?
      flock -u 9; exec 9>&-
      exit $rc
    fi
    exec 9>&-
  done
  sleep 5
done
