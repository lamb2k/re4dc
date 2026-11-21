#!/bin/bash
# e2bcheck.sh: em10's service functions made native (lane eng-e2b: services/em10/) against the original on the PC reference.
#
#   RE4_TREE=<converted data tree> e2bcheck.sh <out dir>
#
# re4ref odump (em10's original bodies) and native (the engine's) run the same inputs, wind off. Per row: e2_compare.py
# --log e2b.txt on the boundary log (svc/e2b_dump.cpp: every call to the sound and effect entry points made outside
# another service's call, and each live Ganado's presentation state and work camera at the start of every tick;
# integers exact, positions and lengths within max(0.01 unit, 2^-20 of the value)) and --log e2.txt (the enemy hit
# geometry's log, svc/e2_dump.cpp, where the blood em10 chooses arrives as EmDmBloodSet2), outcome.py (kills, damage, ticks
# within the reader's tolerance, room clear) and plays_right.py (every trace field) on the two traces.
#   fixtures   bell-ganado, bell-ganado-hit, bell-ganado-kill, bell-ganado-clear, shot-ganado, aimfire-ganado: must PASS
#   exercise   e2b on bell-ganado and shot-ganado: every function on planted inputs (svc/e2b_dump.cpp): must PASS
#   controls   (native only, on the bell-ganado exercise) voicebank, bloodswap, footpart (services/em10/em10_pres.cpp),
#              camease, screenhalf (em10_cam.cpp), handgrip, accnone, keepcap (em10_model.cpp): must FAIL the boundary log
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build or a run is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "e2bcheck: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
MD=$OUT/e2bcheck.md
echo "| row | must | e2b boundary log | outcome | traces | result |" > "$MD"
echo "|---|---|---|---|---|---|" >> "$MD"
bad=0; missing=0
run() {   # run <dir> <bin> <fixture> [env...]
    local d=$1 bin=$2 fx=$3
    shift 3
    local ff=$PR/fixtures/$fx.txt
    [ -f "$HERE/aim_fixtures/$fx.txt" ] && ff=$HERE/aim_fixtures/$fx.txt
    [ -f "$ff" ] || { echo "e2bcheck: no fixture $fx"; return 1; }
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B/$bin/re4ref" --tree "$TREE" --fixture "$ff" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] && [ -s "$d/e2b.txt" ]
}
row() {   # row <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4
    python3 "$HERE/e2_compare.py" "$a" "$b" --log e2b.txt --json "$b/e2bcmp.json" > "$b/e2bcmp.txt" 2>&1
    local e=$?
    # the blood em10's functions choose reaches the effect service through EmDmBloodSet2, which the enemy hit geometry's
    # boundary log records (e2.txt, svc/e2_dump.cpp): compared too, with the same bounds; the row takes the worse of the two
    python3 "$HERE/e2_compare.py" "$a" "$b" --log e2.txt --json "$b/e2cmp.json" > "$b/e2cmp.txt" 2>&1
    local e1=$?
    if [ $e1 = 2 ]; then e=2; elif [ $e = 0 ]; then e=$e1; fi
    python3 "$PR/outcome.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --json "$b/outcome.json" > "$b/outcome.txt" 2>&1
    local o=$?
    python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --quiet > "$b/pr.txt" 2>&1
    local p=$?
    [ $e = 2 ] && { missing=1; echo "| $name | $must | ERROR (no log) | | | ERROR |" >> "$MD"; echo "$name: ERROR"; return; }
    local got=PASS
    [ $e = 0 ] && [ $o = 0 ] && [ $p = 0 ] || got=FAIL
    local res="$got (as it must)"
    if [ "$must" = PASS ] && [ $got != PASS ]; then res="$got (MUST PASS)"; bad=1; fi
    # a control must fail its boundary log (the answer changed); the play may or may not move
    if [ "$must" = FAIL ] && [ $e = 0 ]; then res="PASS (MUST FAIL)"; bad=1; fi
    [ "$must" = FAIL ] && [ $e != 0 ] && res="FAIL (as it must)"
    local es="e2b.txt $(head -1 "$b/e2bcmp.txt" | cut -c1-160); e2.txt $(head -1 "$b/e2cmp.txt" | cut -c1-110)"
    echo "| $name | $must | $es | $([ $o = 0 ] && echo PASS || echo FAIL) | $([ $p = 0 ] && echo PASS || echo FAIL) | $res |" >> "$MD"
    echo "$name: $res; e2b $es; outcome $([ $o = 0 ] && echo PASS || echo FAIL); traces $([ $p = 0 ] && echo PASS || echo FAIL)"
}
for fx in bell-ganado bell-ganado-hit bell-ganado-kill bell-ganado-clear shot-ganado aimfire-ganado; do
    run "$OUT/$fx/odump" odump $fx && run "$OUT/$fx/native" native $fx || { missing=1; echo "$fx: run failed"; continue; }
    row "$fx" PASS "$OUT/$fx/odump" "$OUT/$fx/native"
done
EX="RE4_SVC_EXERCISE=e2b"
for fx in bell-ganado shot-ganado; do
    d=$OUT/ex-$fx
    # bell-ganado (300 ticks) also runs the accessory and destructor steps (tick 285 and 297)
    END=; [ $fx = bell-ganado ] && END=RE4_E2B_END=297
    run "$d/odump" odump $fx $EX $END && run "$d/native" native $fx $EX $END || { missing=1; echo "ex $fx: run failed"; continue; }
    row "exercise e2b $fx" PASS "$d/odump" "$d/native"
done
d=$OUT/ex-bell-ganado
for c in voicebank bloodswap footpart camease screenhalf handgrip accnone keepcap; do
    run "$d/ctl-$c" native bell-ganado $EX RE4_E2B_END=297 RE4_SVC_CONTROL=$c || { missing=1; echo "control $c: run failed"; continue; }
    row "control $c" FAIL "$d/odump" "$d/ctl-$c"
done
# lane eng-e2d: the PC native projection's fix (hostref/host_math.cpp) taken back: every point at the screen's centre,
# the screen check's XV lines must differ from the original's
run "$d/ctl-screencentre" native bell-ganado $EX RE4_E2B_END=297 RE4_SCREEN_CENTRE=1 || { missing=1; echo "control screencentre: run failed"; }
[ -s "$d/ctl-screencentre/e2b.txt" ] && row "control screencentre" FAIL "$d/odump" "$d/ctl-screencentre"
[ $missing = 1 ] && { echo "e2bcheck: a run or a log is missing"; exit 2; }
[ $bad = 1 ] && { echo "e2bcheck: a row did not end as it must ($MD)"; exit 1; }
echo "e2bcheck: every row as it must ($MD)"
exit 0
