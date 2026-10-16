#!/bin/bash
# qlp.sh: in-game stills for the lost-part check (r101 original vs C16 at the r102 door and em15). w17trT, 60 s, PERIOD 10.
cd /c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools
F=/root/probe/worldtest16-20261016/fix-lp
for v in door em15; do for x in o n; do
  while [ $(jobs -rp | wc -l) -ge 2 ]; do sleep 5; done
  ( TRACE=1 PERIOD=10 bash retry.sh lp2-$v-$x w17trT $F/$v-$x.json 60 TRACE=1 PERIOD=10 > lp2-$v-$x.retry.log 2>&1 ) &
  sleep 20
done; done
wait; echo QLP_DONE
