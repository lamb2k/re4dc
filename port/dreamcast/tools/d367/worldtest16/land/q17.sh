#!/bin/bash
# q17.sh: test 17 terrain landing gate runs (w17trT / w17tmW on land17): STRICT r102/r108/r10a (stop 2000), still pairs
# (r102 merchant cave = the re-shoot, r108 c1, r10a c1), TEXCHK/LEON-GC + VRAM; o = without wt17terr, n = with.
cd /c/Flycast-Evidence/re4-dreamcast/wt16land-20261016/_tools
F=/root/probe/worldtest16-20261016/fix-t17
MAXP=${MAXP:-4}
J=()
for x in o n; do
  for s in st2 st8 sta; do J+=("t17-$s-$x|w17trT|$F/$s-$x.json|300|TRACE=1 RE4DC_LOG_STOP_TICK=2000"); done
  for s in still2 still8 stilla; do J+=("t17-$s-$x|w17trT|$F/$s-$x.json|60|TRACE=1 PERIOD=10"); done
  for s in tex2 tex8 texa; do J+=("t17-$s-$x|w17tmW|$F/$s-$x.json|60|X=1"); done
done
for j in "${J[@]}"; do
  IFS='|' read -r name lab fix secs env <<< "$j"
  while [ $(jobs -rp | wc -l) -ge $MAXP ]; do sleep 5; done
  ( bash retry.sh $name $lab $fix $secs $env > $name.retry.log 2>&1 ) &
  sleep 20
done
wait; echo Q17_DONE
