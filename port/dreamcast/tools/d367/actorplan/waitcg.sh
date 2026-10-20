#!/bin/bash
# waitcg.sh <name>...: wait until each hwmodel-<name>/cg/cg.log exists (or its hw log shows a failure)
for n in "$@"; do
  for i in $(seq 1 175); do
    [ -s /mnt/c/Flycast-Evidence/re4-dreamcast/actorplan-20261015/hwmodel-$n/cg/cg.log ] && break
    grep -q -E "rc=[1-9]|exists|not staging|INVALID|Traceback" /root/probe/lanes-20261015/actorplan-k/hw/hw-$n.log 2>/dev/null && break
    sleep 10
  done
  echo "== $n"; tail -4 /root/probe/lanes-20261015/actorplan-k/hw/hw-$n.log
done
