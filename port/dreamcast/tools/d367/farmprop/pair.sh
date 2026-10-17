#!/bin/bash
# pair.sh <tag> <armA> <armB> <scene>... (Git Bash): for each scene, run armA and armB in parallel (2 Flycasts), 60 s.
# Fixtures: /root/probe/lanes-20261016/fp17/fix/<letter>-<scene>.json where letter = the arm label's 5th character.
cd /c/Flycast-Evidence/re4-dreamcast/farmprop17-20261017/_tools
TAG=$1; A=$2; B=$3; shift 3
F=/root/probe/lanes-20261016/fp17/fix
fx() { local l=${1:4:1}; local f=$F/$l-$2.json; MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- test -s $f || f=$F/root/probe/lanes-20261016/fp17/fix/$l-$2.json; echo $f; }
for s in "$@"; do
  fa=$(fx $A $s); fb=$(fx $B $s)
  bash t-run.sh $TAG-$s-$A $A $fa ${SECS:-60} > $TAG-$s-$A.log 2>&1 &
  sleep 20
  bash t-run.sh $TAG-$s-$B $B $fb ${SECS:-60} > $TAG-$s-$B.log 2>&1
  wait
  tail -2 $TAG-$s-$A.log; tail -2 $TAG-$s-$B.log
done
echo PAIR_DONE
