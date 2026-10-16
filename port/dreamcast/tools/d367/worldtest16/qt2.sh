#!/bin/bash
# qt2.sh: worldtest16 B still runs (A current | T terrain-only), arm w16mrT, 60 s, shots every 10 s, at most MAXP at once;
# a run refused by the C: stage floor / capacity guard is cleaned and retried after 90 s (up to 40 times).
cd /c/Flycast-Evidence/re4-dreamcast/worldtest-20261016/_tools
H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/scenarios"
MAXP=${MAXP:-2}
one() { n=$1; fx=$2
  for i in $(seq 1 40); do
    TRACE=1 PERIOD=10 bash t-run.sh $n w16mrT $fx 60 > $n.log 2>&1
    if grep -q "stage failed" $n.log || grep -q "Capacity guard" /c/Flycast-Evidence/re4-dreamcast/worldtest-20261016/$n/run-stdout.txt 2>/dev/null; then
      rm -rf "$H/route-wt-$n" "$H/route-wt-$n-run-stdout.txt"; mkdir -p ../_failed
      [ -d ../$n ] && mv ../$n ../_failed/$n-capfail-$i
      mv $n.log $n-capfail-$i.log; sleep 90; continue
    fi
    return
  done; }
for c in "$@"; do for a in A T; do
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  one t-$c-$a /root/probe/worldtest16-20261016/fix-terrain/$c-$a.json &
  sleep 15
done; done
wait; echo QT_DONE
