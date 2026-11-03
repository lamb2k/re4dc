#!/bin/bash
# lanelock.sh <command...>: run a heavy build / disc-staging step under one of the N build slots
# (/root/probe/lane-build-<i>.lock, i=1..N; N from /root/probe/lane-build-slots, default 3).
# Takes the first free slot; if all are busy, waits on them in turn. Flycast runs do NOT use this:
# they use the 16-slot trace_lock. (Coordinator, 2026-11-03.)
set -u
N=$(cat /root/probe/lane-build-slots 2>/dev/null || echo 3)
[ "$#" -gt 0 ] || { echo "usage: lanelock.sh <command...>"; exit 2; }
c=$(df --output=avail -BG /mnt/c | tail -1 | tr -dc 0-9)
e=$(df --output=avail -BG /mnt/e | tail -1 | tr -dc 0-9)
[ "${c:-0}" -ge 20 ] || { echo "lanelock: C: ${c}G < 20G, refusing"; exit 3; }
[ "${e:-0}" -ge 50 ] || { echo "lanelock: E: ${e}G < 50G, refusing"; exit 3; }
while :; do
  for i in $(seq 1 "$N"); do
    L=/root/probe/lane-build-$i.lock
    exec 9>"$L"
    if flock -n 9; then
      echo "lanelock: slot $i ($(date +%T)) $*" >&2
      "$@"; rc=$?
      flock -u 9; exec 9>&-
      exit $rc
    fi
    exec 9>&-
  done
  sleep 5
done
