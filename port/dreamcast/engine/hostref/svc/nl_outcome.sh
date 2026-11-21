#!/bin/bash
# nl_outcome.sh (lane eng-e1g): the engine's float library (newlib's float functions, which libmtest shows are not
# bit-identical with the game's fdlibm) judged by outcome. Needs `make native nlnative` (svc.mk) and RE4_TREE.
#
#   RE4_TREE=<converted data tree> nl_outcome.sh <out dir> [fixture ...]
#
# Per fixture: the native build (the game's fdlibm) and the nlnative build (newlib) on the same inputs, cloth wind off;
# outcome.py (kills, damage, spawns, triggers, clears, positions within tolerance) and plays_right.py (traces within
# tolerance) of nlnative against native. Control: nlnative with RE4_SVC_CONTROL=mathmuku (every turning step 5% larger)
# on bell-ganado must FAIL.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
shift
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=$ROOT/build/hostref
PR=$ROOT/port/dreamcast/tools/plays_right
run() {   # run <build> <fixture> <dir> [env...]
    local b=$1 fx=$2 d=$3
    shift 3
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B/$b/re4ref" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" || echo "re4ref failed: $d"
}
row() {   # row <fixture> <name> <must> <a dir> <b dir>
    local fx=$1 name=$2 must=$3 a=$4 b=$5
    python3 "$PR/outcome.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --json "$b/outcome.json" > "$b/outcome.txt" 2>&1
    local oc=$?
    python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --fields p,a,mf,ms,ps --quiet > "$b/pr.txt" 2>&1
    local pr=$?
    local got=PASS
    [ $oc -ne 0 ] && got=FAIL
    echo "| $fx | $name | $must | $got$([ "$got" = "$must" ] && echo ' (as it must)' || echo ' (WRONG)') | traces $([ $pr = 0 ] && echo PASS || echo FAIL) | $(head -1 "$b/outcome.txt" | cut -c1-160) |"
}
echo "| Fixture | Check | Must | Outcome | Traces | Detail |"
echo "|---|---|---|---|---|---|"
for fx in ${*:-door103-walk e1-route bell-ganado bell-ganado-hit bell-ganado-kill bell-ganado-clear hill-ashley square-follow}; do
    run native "$fx" "$OUT/$fx/native"
    run nlnative "$fx" "$OUT/$fx/nl"
    row "$fx" "newlib float functions" PASS "$OUT/$fx/native" "$OUT/$fx/nl"
done
fx=bell-ganado
run nlnative $fx "$OUT/$fx/nl-mathmuku" RE4_SVC_CONTROL=mathmuku
row $fx "control: turning steps 5% larger" FAIL "$OUT/$fx/native" "$OUT/$fx/nl-mathmuku"
