#!/bin/bash
# e2fcheck.sh: sce_at's service functions made native (lane eng-e2f: services/scene/sce_at_svc.cpp) against sce_at's
# original bodies on the PC reference.
#
#   RE4_TREE=<converted data tree> e2fcheck.sh <out dir>
#
# re4ref e2fodump (sce_at's original bodies, libgpu's at-list) and e2fnative (the engine's, services/scene/) run the same
# fixtures with the exercise of svc/e2f_dump.cpp (the room's attachment data set up, then every function on the room's
# records and planted inputs from tick 30, every 5th tick). Per row: e2_compare.py --log e2f.txt on the boundary log
# (integers exact, positions within max(0.01 unit, 2^-20 of the value), angles within 0.01 degree), and outcome.py and
# plays_right.py on the two traces (the exercise puts every record back: the play must not move).
#   fixtures   bell-ganado, shot-ganado, bell-ganado-kill: must PASS
#   controls   (e2fnative, on bell-ganado) atparent, atfacing, screenmid, itemsight, hitbit, glowkind, itemcol, itemlink,
#              ladderofs, itemrot, shdbit, glowstop, modelptr, parentscale (services/scene/sce_at_svc.cpp): must
#              FAIL the boundary log
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build or a run is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
for bin in e2fodump e2fnative; do
    [ -x "$B/$bin/re4ref" ] || { echo "e2fcheck: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
MD=$OUT/e2fcheck.md
echo "| row | must | e2f boundary log | outcome | traces | result |" > "$MD"
echo "|---|---|---|---|---|---|" >> "$MD"
bad=0; missing=0
run() {   # run <dir> <bin> <fixture> [env...]
    local d=$1 bin=$2 fx=$3
    shift 3
    local ff=$PR/fixtures/$fx.txt
    [ -f "$ff" ] || { echo "e2fcheck: no fixture $fx"; return 1; }
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B/$bin/re4ref" --tree "$TREE" --fixture "$ff" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] && [ -s "$d/e2f.txt" ]
}
row() {   # row <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4
    python3 "$HERE/e2_compare.py" "$a" "$b" --log e2f.txt --json "$b/e2fcmp.json" > "$b/e2fcmp.txt" 2>&1
    local e=$?
    python3 "$PR/outcome.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --json "$b/outcome.json" > "$b/outcome.txt" 2>&1
    local o=$?
    python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --quiet > "$b/pr.txt" 2>&1
    local p=$?
    [ $e = 2 ] && { missing=1; echo "| $name | $must | ERROR (no log) | | | ERROR |" >> "$MD"; echo "$name: ERROR"; return; }
    local got=PASS
    if [ "$must" = PASS ]; then
        [ $e = 0 ] && [ $o = 0 ] && [ $p = 0 ] || got=FAIL
    else
        [ $e = 0 ] || got=FAIL   # a control must fail its boundary log (the answer changed)
    fi
    local res="$got (as it must)"
    if [ $got != "$must" ]; then res="$got (MUST $must)"; bad=1; fi
    local first
    first=$(grep -m1 -E 'first difference|differ' "$b/e2fcmp.txt" | cut -c1-160)
    echo "| $name | $must | $([ $e = 0 ] && echo same || echo "differs: ${first//|//}") | $([ $o = 0 ] && echo PASS || echo FAIL) | $([ $p = 0 ] && echo PASS || echo FAIL) | $res |" >> "$MD"
    echo "$name: $res (e2f $e outcome $o traces $p)"
}
for fx in bell-ganado shot-ganado bell-ganado-kill; do
    run "$OUT/$fx/odump" e2fodump "$fx" || { echo "$fx odump: run failed"; missing=1; continue; }
    run "$OUT/$fx/native" e2fnative "$fx" || { echo "$fx native: run failed"; missing=1; continue; }
    row "$fx" PASS "$OUT/$fx/odump" "$OUT/$fx/native"
done
for c in atparent atfacing screenmid itemsight hitbit glowkind itemcol itemlink ladderofs itemrot shdbit glowstop modelptr parentscale; do
    [ -d "$OUT/bell-ganado/odump" ] || break
    run "$OUT/ctl-$c" e2fnative bell-ganado RE4_SVC_CONTROL=$c || { echo "control $c: run failed"; missing=1; continue; }
    row "control $c" FAIL "$OUT/bell-ganado/odump" "$OUT/ctl-$c"
done
# the boundary log's size: an empty exercise would compare equal
for fx in bell-ganado shot-ganado bell-ganado-kill; do
    [ -f "$OUT/$fx/odump/e2f.txt" ] && echo "lines $fx: $(wc -l < "$OUT/$fx/odump/e2f.txt") ($(grep -c ' HC ' "$OUT/$fx/odump/e2f.txt") HC, $(grep -c ' ES ' "$OUT/$fx/odump/e2f.txt") ES, $(grep -c '^IN ' "$OUT/$fx/odump/e2f.txt") records)" | tee -a "$MD"
done
[ $missing = 1 ] && exit 2
exit $bad
