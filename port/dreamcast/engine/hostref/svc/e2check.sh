#!/bin/bash
# e2check.sh: the fight image's native service functions (lane eng-e2a) against the original on the PC reference.
#
#   RE4_TREE=<converted data tree> e2check.sh <out dir>
#
# re4ref odump (the original em_sub, dmg and area) and native (services/aim/em_hit.cpp, services/volumes/dmg_vol.cpp,
# services/volumes/area_vol.cpp) run the
# same inputs, wind off, motion keys
# decoded. Per row: e2_compare.py on the
# boundary log e2.txt (svc/e2_dump.cpp: every call the behaviour makes to those entry points, integers and flags exact,
# positions and lengths within 0.01 unit, squared distances within 0.01 unit of their root, angles within 0.01 degree;
# stated in the brief before the runs), outcome.py (kills, damage, ticks within the reader's tolerance, room clear) and
# plays_right.py (every trace field) on the two traces. Exercise rows also print e2_exact.py (the line tests against
# their definitions in double precision: a second opinion where the two differ, never a verdict).
#   fixtures   bell-ganado, bell-ganado-hit, bell-ganado-kill, bell-ganado-clear, shot-ganado, aimfire-ganado: must PASS
#   exercise   e2geom on bell-ganado and hill-ashley (the partner): every entry point on generated and planted inputs: must PASS
#   controls   (native only, on the bell-ganado exercise) hitwide, dmposmid, sphereshort; dmgwide (item 2); areawide (item 3): must FAIL
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build or a run is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "e2check: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
MD=$OUT/e2check.md
echo "| row | must | e2 boundary log | outcome | traces | result |" > "$MD"
echo "|---|---|---|---|---|---|" >> "$MD"
bad=0; missing=0
run() {   # run <dir> <bin> <fixture> [env...]
    local d=$1 bin=$2 fx=$3
    shift 3
    local ff=$PR/fixtures/$fx.txt
    [ -f "$HERE/aim_fixtures/$fx.txt" ] && ff=$HERE/aim_fixtures/$fx.txt
    [ -f "$ff" ] || { echo "e2check: no fixture $fx"; return 1; }
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B/$bin/re4ref" --tree "$TREE" --fixture "$ff" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] && [ -s "$d/e2.txt" ]
}
row() {   # row <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4
    python3 "$HERE/e2_compare.py" "$a" "$b" --json "$b/e2cmp.json" > "$b/e2cmp.txt" 2>&1
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
    local es=$(head -1 "$b/e2cmp.txt" | cut -c1-160)
    echo "| $name | $must | $es | $([ $o = 0 ] && echo PASS || echo FAIL) | $([ $p = 0 ] && echo PASS || echo FAIL) | $res |" >> "$MD"
    echo "$name: $res; e2 $es; outcome $([ $o = 0 ] && echo PASS || echo FAIL); traces $([ $p = 0 ] && echo PASS || echo FAIL)"
}
for fx in bell-ganado bell-ganado-hit bell-ganado-kill bell-ganado-clear shot-ganado aimfire-ganado; do
    run "$OUT/$fx/odump" odump $fx && run "$OUT/$fx/native" native $fx || { missing=1; echo "$fx: run failed"; continue; }
    row "$fx" PASS "$OUT/$fx/odump" "$OUT/$fx/native"
done
EX="RE4_SVC_EXERCISE=e2geom RE4_E2_BOXGEOM=1"
for fx in bell-ganado hill-ashley; do
    d=$OUT/ex-$fx
    run "$d/odump" odump $fx $EX && run "$d/native" native $fx $EX || { missing=1; echo "ex $fx: run failed"; continue; }
    row "exercise e2geom $fx" PASS "$d/odump" "$d/native"
    python3 "$HERE/e2_exact.py" "$d/odump" "$d/native" --json "$d/exact.json" | sed 's/^/    exact: /'
done
d=$OUT/ex-bell-ganado
for c in hitwide dmposmid sphereshort dmgwide areawide; do
    run "$d/ctl-$c" native bell-ganado $EX RE4_SVC_CONTROL=$c || { missing=1; echo "control $c: run failed"; continue; }
    row "control $c" FAIL "$d/odump" "$d/ctl-$c"
done
[ $missing = 1 ] && { echo "e2check: a run or a log is missing"; exit 2; }
[ $bad = 1 ] && { echo "e2check: a row did not end as it must ($MD)"; exit 1; }
echo "e2check: every row as it must ($MD)"
exit 0
