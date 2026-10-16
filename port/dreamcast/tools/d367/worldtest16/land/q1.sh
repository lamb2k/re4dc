#!/bin/bash
# q1.sh: test 16 r101 world landing: STRICT (h2/bell/door103, stop 2000), stills at the cross, TEXCHK/LEON-GC (mW, 60 s). At most MAXP Flycasts.
cd /c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools
F=/root/probe/worldtest16-20261016/fix-land22
MAXP=${MAXP:-4}
J=()
for x in o n; do
  J+=("TRACE=1 RE4DC_LOG_STOP_TICK=2000|m-stA-$x|w16mrT|$F/stA-$x.json|400")
  J+=("TRACE=1 RE4DC_LOG_STOP_TICK=2000|m-stB-$x|w16mrT|$F/stB-$x.json|300")
  J+=("TRACE=1 RE4DC_LOG_STOP_TICK=2000|m-stC-$x|w16mrT|$F/stC-$x.json|300")
  J+=("TRACE=1 PERIOD=10|m-still-$x|w16mrT|$F/still-$x.json|60")
  J+=("X=1|m-tex-$x|w16mmW|$F/tex-$x.json|60")
done
for j in "${J[@]}"; do
  IFS='|' read -r env name lab fix secs <<< "$j"
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  ( env $env bash t-run.sh $name $lab $fix $secs > $name.log 2>&1 ) &
  sleep 20
done
wait; echo Q1_DONE
