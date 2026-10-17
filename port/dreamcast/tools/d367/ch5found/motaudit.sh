#!/bin/bash
# motion-consumer survey of the island enemies (which calls receive their ARC motion pointers)
cd /root/probe/lanes-20261016/ch5found/tree/src
for e in "$@"; do
  echo "== $e"
  grep -ho 'Mot[A-Za-z0-9_]*(\|Motion[A-Za-z0-9_]*(\|maxFrame\|->frame_max\|getMotFrame[A-Za-z]*(' $e/*.cpp | sort | uniq -c | sort -rn | head -16
  echo "-- ARC() not in modelInit/ModInfo/SetObj16/MotionSet*/EspDataLoad lines:"
  grep -n 'ARC(' $e/*.cpp | grep -v 'modelInit\|ModInfoMgr\|SetObj16\|MotionSet\|EspDataLoad\|MotSet\|#define' | head -20 | cut -c1-200
done
