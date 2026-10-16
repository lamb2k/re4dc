#!/bin/bash
# retry.sh <name> <label> <fixture> <secs> [env...]: t-run.sh, retried (new name suffix) while C: is below the stage floor.
N=$1; L=$2; FX=$3; S=$4; shift 4
for i in $(seq 1 40); do
  n=$N; [ $i -gt 1 ] && n=$N-r$i
  env "$@" bash t-run.sh $n $L $FX $S > $n.log 2>&1
  if grep -q "stage failed" $n.log || grep -q "Capacity guard" /c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/$n/run-stdout.txt 2>/dev/null; then
    H="/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/scenarios"
    rm -rf "$H/route-wl-$n" "$H/route-wl-$n-run-stdout.txt"; [ -d ../$n ] && mv ../$n ../_failed/$n-capfail; mv $n.log $n-capfail.log; sleep 90; continue
  fi
  tail -3 $n.log; exit 0
done
