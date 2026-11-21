#!/bin/bash
# e2c_check.sh (lane eng-e2c): the boss image's native service entry points (services/boss/) against the original
# (src/em2b) on the PC reference.
#
#   RE4_TREE=<converted data tree> e2c_check.sh <out dir>
#
# The reference does not host El Gigante, so its entry points are exercised (RE4_SVC_EXERCISE=e2cboss, svc/e2c_dump.cpp)
# on planted giants at fixed ticks of two fixtures; re4ref odump (the original em2b.cpp) and native (the engine bodies)
# make the same calls. Per row: e2_compare.py (lane eng-e2a's comparator and bounds, unchanged) on the boundary log
# e2c.txt (integers and flags exact; positions, lengths within max(0.01 unit, 2^-20 of the value), angles within 0.01
# degree), outcome.py (kills, damage, ticks within the reader's tolerance, room clear) and plays_right.py (every trace
# field) on the two traces: the exercise changes the play (the squash, the event camera's slot is put back) the same way
# in both builds.
#   exercise   e2cboss on bell-ganado (Leon and four Ganados) and hill-ashley (Leon and Ashley: the partner watched):
#              must PASS
#   controls   (native only, on the bell-ganado exercise) bosscam (event cameras' eye 1% further), bossquake (the
#              nearest quake band 4500), bossneck (the neck's damping 0.85), bossblend (the blend weight / 255): must FAIL
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build or a run is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "e2c_check: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
MD=$OUT/e2c_check.md
echo "| row | must | e2c boundary log | outcome | traces | result |" > "$MD"
echo "|---|---|---|---|---|---|" >> "$MD"
bad=0; missing=0
run() {   # run <dir> <bin> <fixture> [env...]
    local d=$1 bin=$2 fx=$3
    shift 3
    local ff=$PR/fixtures/$fx.txt
    [ -f "$ff" ] || { echo "e2c_check: no fixture $fx"; return 1; }
    mkdir -p "$d/e2c"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 RE4_SVC_EXERCISE=e2cboss "$@" "$B/$bin/re4ref" --tree "$TREE" \
        --fixture "$ff" --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] && [ -s "$d/e2c.txt" ] \
        && ln -sf ../e2c.txt "$d/e2c/e2.txt"
}
row() {   # row <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4
    python3 "$HERE/e2_compare.py" "$a/e2c" "$b/e2c" --json "$b/e2ccmp.json" > "$b/e2ccmp.txt" 2>&1
    local e=$?
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
    local es=$(head -1 "$b/e2ccmp.txt" | cut -c1-240)
    echo "| $name | $must | $es | $([ $o = 0 ] && echo PASS || echo FAIL) | $([ $p = 0 ] && echo PASS || echo FAIL) | $res |" >> "$MD"
    echo "$name: $res; e2c $es; outcome $([ $o = 0 ] && echo PASS || echo FAIL); traces $([ $p = 0 ] && echo PASS || echo FAIL)"
}
for fx in bell-ganado hill-ashley; do
    d=$OUT/ex-$fx
    run "$d/odump" odump $fx && run "$d/native" native $fx || { missing=1; echo "ex $fx: run failed"; continue; }
    row "exercise e2cboss $fx" PASS "$d/odump" "$d/native"
    # what the exercise reached (both builds alike when the row passes)
    echo "    calls: $(grep -v '^#' "$d/native/e2c.txt" | awk '{print $2}' | sort | uniq -c | awk '{printf "%s %s, ", $2, $1}')"
done
d=$OUT/ex-bell-ganado
for c in bosscam bossquake bossneck bossblend; do
    run "$d/ctl-$c" native bell-ganado RE4_SVC_CONTROL=$c || { missing=1; echo "control $c: run failed"; continue; }
    row "control $c" FAIL "$d/odump" "$d/ctl-$c"
done
[ $missing = 1 ] && { echo "e2c_check: a run or a log is missing"; exit 2; }
[ $bad = 1 ] && { echo "e2c_check: a row did not end as it must ($MD)"; exit 1; }
echo "e2c_check: every row as it must ($MD)"
exit 0
