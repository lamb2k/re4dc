#!/bin/bash
# Git Bash: actorplan19 gate runs, two Flycasts at a time.
set -euo pipefail
R=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/actorplan19/k/run.sh
F=/root/work/lanes/actorplan19/k/fix
E=/c/Flycast-Evidence/re4-dreamcast/actorplan19-20261019/_tools
pair() { # name-stem arm-stem secs stoptick
  local n=$1 a=$2 s=$3 t=$4
  RE4DC_LOG_STOP_TICK=$t bash $R tr-$n-k a9k$a $F/$n-k.json $s > $E/run-tr-$n-k.log 2>&1 &
  local p1=$!
  sleep 20
  RE4DC_LOG_STOP_TICK=$t bash $R tr-$n-p a9p$a $F/$n-p.json $s > $E/run-tr-$n-p.log 2>&1 &
  local p2=$!
  wait $p1 || true; wait $p2 || true
}
pairw() { # name arm secs
  local n=$1 a=$2 s=$3
  bash $R $n-k a9k$a $F/$n-k.json $s > $E/run-$n-k.log 2>&1 &
  local p1=$!
  sleep 20
  bash $R $n-p a9p$a $F/$n-p.json $s > $E/run-$n-p.log 2>&1 &
  local p2=$!
  wait $p1 || true; wait $p2 || true
}
for x in ${SET:-h2 bell door}; do
  case $x in
    h2) pair h2 rT 420 2000 ;;
    bell) pair bell rT 60 2000 ;;
    door) pair door rT 75 2000 ;;
    st101) pairw st101 hrW 60 ;;
    st103) pairw st103 hrW 60 ;;
    stleon) pairw stleon hrW 60 ;;
    m101) pairw m101 mW 60 ;;
    m103) pairw m103 mW 60 ;;
  esac
done
echo RUNS DONE $SET
