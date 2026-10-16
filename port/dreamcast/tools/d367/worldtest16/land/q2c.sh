#!/bin/bash
# q2c.sh: r101 C16 landing gate runs (ELFs w16crT / w16cmW on landA 37bcf721): STRICT h2/bell/door103 (stop 2000), the
# cross still pair, TEXCHK/LEON-GC; o = C4 data, n = C16. retry.sh re-runs a run refused by the C: floor. At most MAXP.
cd /c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools
F=/root/probe/worldtest16-20261016/fix-c16
MAXP=${MAXP:-4}
J=()
for x in o n; do
  J+=("c-stA-$x|w16crT|$F/stA-$x.json|400|TRACE=1 RE4DC_LOG_STOP_TICK=2000")
  J+=("c-stB-$x|w16crT|$F/stB-$x.json|300|TRACE=1 RE4DC_LOG_STOP_TICK=2000")
  J+=("c-stC-$x|w16crT|$F/stC-$x.json|300|TRACE=1 RE4DC_LOG_STOP_TICK=2000")
  J+=("c-still-$x|w16crT|$F/still-$x.json|60|TRACE=1 PERIOD=10")
  J+=("c-tex-$x|w16cmW|$F/tex-$x.json|60|X=1")
done
for j in "${J[@]}"; do
  IFS='|' read -r name lab fix secs env <<< "$j"
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  ( bash retry.sh $name $lab $fix $secs $env > $name.retry.log 2>&1 ) &
  sleep 20
done
wait; echo Q2C_DONE
