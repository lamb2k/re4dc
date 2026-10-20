#!/bin/bash
# kos_squeeze.sh <base dir> <twin out label> <evidence dir> [levels] [scenes]   (Git Bash; tools/d367/fullplay)
# KOS out-of-memory gate (2026-10-15, user: make the console OOM check automatic). Runs a KOS_SQUEEZE twin base
# (fp_twin.sh <release out> <lab> KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1, then fp_master.sh ... <twin>) through
# fight (r101 cross, benchmark-r101-v3), call (radio call 0 replayed in r100 after s40, kos-call-warp.txt) and door
# (door103: post-bell call, the r103 door, r103 entry), leave100 / leave103 (the fight, then at room frame 450 the
# room changes to r100 / r103: r101's KOS use carried into the next room load; added 10-15 for 12.1), every level in parallel per scene, each run 60 s wall (door 75 s) on JIT
# Flycast with FP_NOLIMIT=1. A "squeeze <bytes> <frag>" line is prepended to each warp fixture: the twin holds that
# much KOS from boot (KOS_SQUEEZE, platform/os.cpp). Levels default "49152:0 49152:1" (the release gate: 48 KiB as one
# block and as 4 KiB pieces). Prints one line per run: min headroom, min top block (largest block), OOM lines
# ("Out of memory" / MISSING / HALT), the scene events reached; GATE PASS when every run has 0 OOM lines,
# min headroom >= 4096 and reached its scene's end marker.
# EVAL_ONLY=1: judge existing <evidence>/kos-<scene>-<bytes>-<frag> runs without running Flycast.
# Example: kos_squeeze.sh 'C:\Flycast-Evidence\...\_discs\sqtwin' fpsqW 'C:\Flycast-Evidence\...\kos-t12'
here=$(cd "$(dirname "$0")" && pwd)
BASE=${1:?base}; TW=${2:?twin label}; EV=${3:?evidence}; LEVELS=${4:-"49152:0 49152:1"}; SCENES=${5:-"fight call door leave100 leave103"}
export FP_NOLIMIT=1
S=$(cat //wsl.localhost/Ubuntu-24.04/root/probe/lanes/route/out-$TW/syms.txt)
EVU=$(cygpath -u "$EV"); mkdir -p "$EVU/fixtures"
declare -A WARP=( [fight]=$here/segments/kos-fight-warp.txt [call]=$here/segments/kos-call-warp.txt
                  [door]=$here/segments/door103-warp.txt [leave100]=$here/segments/kos-leave100-warp.txt
                  [leave103]=$here/segments/kos-leave103-warp.txt )
declare -A END=( [fight]='warp: alert at room frame' [call]='subscreen backing: open' [door]='phase=enter room=103'
                 [leave100]='phase=enter room=100' [leave103]='phase=enter room=103' )
# Per-scene wall limit. door is 75 s (10-16, lane s30movie16): its r103 entry marker lands ~57-60 s into the run,
# so a 60 s capture could stop two log lines short of it. That is a harness limit, not a game fault.
declare -A SECS=( [fight]=60 [call]=60 [door]=75 [leave100]=60 [leave103]=60 )
fail=0
for sc in $SCENES; do
  for lv in $LEVELS; do
    n=${lv%:*}; f=${lv#*:}; L=kos-$sc-$n-$f
    { echo "squeeze $n $f"; tr -d '\r' < "${WARP[$sc]}"; } > "$EVU/fixtures/$L-warp.txt"
    [ "${EVAL_ONLY:-0}" = 1 ] || python "$here/fp_run.py" --base "$BASE" --warp "$(cygpath -w "$EVU/fixtures/$L-warp.txt")" --cap "$EV\\$L" --syms "$S" --seconds ${SECS[$sc]:-60} \
      --name $L > "$EVU/fixtures/$L.out" 2>&1 &
  done
  wait
  for lv in $LEVELS; do
    n=${lv%:*}; f=${lv#*:}; L=kos-$sc-$n-$f; R=$EVU/$L/run-output.txt
    mn=$(grep -a "kos watch:" $R | sed 's/.*headroom=\([0-9]*\).*/\1/' | sort -n | head -1)
    tp=$(grep -a "kos watch:" $R | sed 's/.*top=\([0-9]*\).*/\1/' | sort -n | head -1)
    oom=$(grep -ac "Out of memory\|MISSING\|HALT" $R)
    held=$(grep -a "kos squeeze:" $R | head -1 | sed 's/.*held=\([0-9]*\).*/\1/')
    end=$(grep -ac "${END[$sc]}" $R)
    ok=PASS; { [ "$oom" = 0 ] && [ -n "$mn" ] && [ "$mn" -ge 4096 ] && [ "$held" = "$n" ] && [ "$end" -ge 1 ]; } || { ok=FAIL; fail=1; }
    echo "$ok $L held=$held min_headroom=$mn min_top=$tp oom_lines=$oom end_marker=$end"
  done
done
[ $fail = 0 ] && echo "KOS SQUEEZE GATE PASS" || echo "KOS SQUEEZE GATE FAIL"
