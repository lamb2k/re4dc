#!/bin/bash
# aim_check.sh (lane eng-e1g): the native weapon-target query (services/aim/aim.cpp) against the original on the PC
# reference. Needs `make aimchk` (svc.mk) and RE4_TREE.
#
#   RE4_TREE=<converted data tree> aim_check.sh <out dir> [fixture ...]
#
# Per fixture, the aimchk build runs three arms: orig (the behaviour gets the original's answer; both answers are
# compared on every call: aim.txt, aim-diff.txt), native (the behaviour gets the native answer) and ctl (native answer
# under the control RE4_AIM_CONTROL=grow: every enemy box and capsule 25% larger). The shot fixtures (aimfire-*) run
# with a magazine (RE4_AIM_MAG=10) and add the arm nomag (the reference's empty magazine: no shot fires).
# Verdicts: calls  PASS when every call's return, enemy and surface attribute agree (hit points are reported: the
#                  native form is the engine's, not the original's arithmetic);
#           outcome / traces  outcome.py and plays_right.py of each arm against orig.
# The controls must FAIL: ctl on calls where an enemy box is in the line (aim-ganado, aimfire-ganado), nomag on
# outcome (the shots change the run).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
shift
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=$ROOT/build/hostref/aimchk/re4ref
PR=$ROOT/port/dreamcast/tools/plays_right
run() {   # run <fixture> <arm> [env...]
    local fx=$1 arm=$2
    shift 2
    local d=$OUT/$fx/$arm ff=$PR/fixtures/$fx.txt
    [ -f "$HERE/aim_fixtures/$fx.txt" ] && ff=$HERE/aim_fixtures/$fx.txt
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B" --tree "$TREE" --fixture "$ff" --out "$d/trace.txt" \
        --log "$d/run.log" 2> "$d/err.txt" || { echo "re4ref failed: $d"; return 1; }
}
calls() {   # calls <dir>: PASS / FAIL on the per-call comparison
    awk '/^aim calls/ {for (i = 1; i < NF; i++) v[$i] = $(i + 1);
         print ((v["ret_diff"] + v["em_diff"] + v["attr_diff"]) ? "FAIL" : "PASS") " (calls " v["calls"] ", return differs " v["ret_diff"] ", enemy " v["em_diff"] ", attribute " v["attr_diff"] ", hit point max " v["max_point"] " units)"}' "$1/aim.txt"
}
for fx in ${*:-e1-route bell-ganado-hit aim-ganado aimfire-ganado}; do
    mag=0
    case $fx in aimfire*) mag=10 ;; esac
    run "$fx" orig RE4_AIM_MAG=$mag
    run "$fx" native RE4_AIM_USE=native RE4_AIM_MAG=$mag
    run "$fx" ctl RE4_AIM_USE=native RE4_AIM_CONTROL=grow RE4_AIM_MAG=$mag
    arms="native ctl"
    if [ $mag != 0 ]; then run "$fx" nomag; arms="native ctl nomag"; fi
    echo "$fx orig: calls $(calls "$OUT/$fx/orig")"
    for a in $arms; do
        python3 "$PR/outcome.py" "$OUT/$fx/orig/trace.txt" "$OUT/$fx/$a/trace.txt" --tolerances "$PR/tolerances.json" \
            --json "$OUT/$fx/$a/outcome.json" > "$OUT/$fx/$a/outcome.txt" 2>&1
        oc=$?
        python3 "$PR/plays_right.py" "$OUT/$fx/orig/trace.txt" "$OUT/$fx/$a/trace.txt" --tolerances "$PR/tolerances.json" \
            --quiet > "$OUT/$fx/$a/pr.txt" 2>&1
        pr=$?
        echo "$fx $a: calls $(calls "$OUT/$fx/$a"); outcome $([ $oc = 0 ] && echo PASS || echo FAIL); traces $([ $pr = 0 ] && echo PASS || echo FAIL)"
    done
done
