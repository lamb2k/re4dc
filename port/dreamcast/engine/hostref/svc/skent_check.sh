#!/bin/bash
# skent_check.sh (lane eng-skel1): the skeleton's bone entries and the native chain object against the original on the
# PC reference (svc/skent_dump.cpp).
#
#   RE4_TREE=<converted data tree> skent_check.sh <out dir>
#
# odump (the original's statements on the records; game/obj1d.cpp) and native (the entries; services/cloth/chain.cpp)
# run the same fixture with the same exercise, wind off, motion keys decoded (RE4_SVC_MK=none). Per row:
#   bones   every bone of every model, every tick (the chain objects included) equal as numbers (svc_compare.py's
#           equal_bones: +0 and -0 alike), and svc_compare.py's own collision and history checks at its bounds
#   log     skent.txt (every value read back, float bits) identical
#   play    outcome.py and plays_right.py on the two traces
# Rows:
#   skent bell-ganado, skent shot-ganado, skchain bell-ganado: must PASS
#   effect  odump with the skent exercise against odump without it: must FAIL (the exercise changes the bones)
#   controls (native, RE4_SVC_CONTROL): entflag (the flag never set), entpost (r x M), entpose (angles x / z swapped),
#           enthist (old2 read as old) on skent bell-ganado; chainmid (the hung link at its first offset) on skchain
#           bell-ganado: each must FAIL
#   colrel bell-ganado: the reference against native leaving and entering the room's collision at tick 100
#           (col_room_release, col_bake_all): the release leaves 0 pieces and 0 room bytes, the bake as many as before,
#           the queries and bones within svc_compare.py's bounds: must PASS; control colkeep (the first piece kept with
#           its tables): must FAIL
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build, a run or a report is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "skent_check: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
MD=$OUT/skent_check.md
echo "| row | must | bones | log | play | result |" > "$MD"
echo "|---|---|---|---|---|---|" >> "$MD"
bad=0; missing=0; rows=0
run() {   # run <dir> <bin> <fixture> [env...]
    local d=$1 bin=$2 fx=$3
    shift 3
    local ff=$PR/fixtures/$fx.txt
    [ -f "$ff" ] || { echo "skent_check: no fixture $fx"; return 1; }
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_MK=none RE4_SVC_CLOTH_WIND=0 "$@" "$B/$bin/re4ref" --tree "$TREE" --fixture "$ff" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] && [ -s "$d/pal.bin" ]
}
row() {   # row <name> <must> <ref dir> <test dir> [nolog]
    local name=$1 must=$2 a=$3 b=$4 nolog=${5:-}
    rows=$((rows + 1))
    python3 "$HERE/svc_compare.py" "$a" "$b" --json "$b/compare.json" > "$b/compare.txt" 2>&1
    local c=$?
    # judged on svc_compare's counts, not its verdict: every bone equal as a number in every tick (equal_bones: +0 and
    # -0 alike), none missing, no collision query over its bound, every known history value equal. (Its axis angle
    # reads 90 degrees between two identical bones whose scale the exercise sets to 0, the bowgun's hidden arrows.)
    if [ $c -le 1 ] && [ -s "$b/compare.json" ]; then
        python3 -c 'import json,sys; j=json.load(open(sys.argv[1])); b=j["bones"]; k=j["collision"]; h=j["history"]; print("bones equal %d of %d (bit-identical %d), collision over %d, history max %g" % (b["equal_bones"], b["bones"], b["bit_identical_bones"], k["over"], h["max"])); sys.exit(0 if b["equal_bones"]==b["bones"] and b["missing"]==0 and k["over"]==0 and h["max"]==0 else 1)' "$b/compare.json" > "$b/equal.txt"
        c=$?
    fi
    local l=0 lmsg="-"
    if [ -z "$nolog" ]; then
        if [ ! -s "$a/skent.txt" ] || [ ! -s "$b/skent.txt" ]; then l=2; lmsg="no skent.txt"
        elif cmp -s "$a/skent.txt" "$b/skent.txt"; then lmsg="identical $(wc -l < "$b/skent.txt") lines"
        else l=1; lmsg="first difference: $(diff "$a/skent.txt" "$b/skent.txt" | head -2 | tail -1 | cut -c1-120)"; fi
    fi
    python3 "$PR/outcome.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" > "$b/outcome.txt" 2>&1
    local o=$?
    python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --quiet > "$b/pr.txt" 2>&1
    local p=$?
    if [ $c -gt 1 ] || [ $l = 2 ] || [ ! -s "$b/compare.txt" ]; then
        missing=1; echo "| $name | $must | ERROR | $lmsg | | ERROR |" >> "$MD"; echo "$name: ERROR"; return
    fi
    local cs; cs=$(head -3 "$b/compare.txt" | tr '\n' ' ' | cut -c1-200)
    local got=PASS
    [ $c = 0 ] && [ $l = 0 ] && [ $o = 0 ] && [ $p = 0 ] || got=FAIL
    local res="$got (as it must)"
    [ "$got" != "$must" ] && { res="$got (MUST $must)"; bad=1; }
    echo "| $name | $must | $([ $c = 0 ] && echo PASS || echo FAIL): $cs | $lmsg | outcome $([ $o = 0 ] && echo PASS || echo FAIL), traces $([ $p = 0 ] && echo PASS || echo FAIL) | $res |" >> "$MD"
    echo "$name: $res; bones $c; log $lmsg; outcome $o; traces $p"
}
for fx in bell-ganado shot-ganado; do
    d=$OUT/skent-$fx
    run "$d/odump" odump $fx RE4_SVC_EXERCISE=skent && run "$d/native" native $fx RE4_SVC_EXERCISE=skent \
        || { missing=1; echo "skent $fx: run failed"; continue; }
    row "skent $fx" PASS "$d/odump" "$d/native"
done
d=$OUT/skchain-bell-ganado
if run "$d/odump" odump bell-ganado RE4_SVC_EXERCISE=skchain && run "$d/native" native bell-ganado RE4_SVC_EXERCISE=skchain; then
    row "skchain bell-ganado" PASS "$d/odump" "$d/native"
    grep -q " CS 0 1" "$d/odump/skent.txt" && grep -q " CS 1 1" "$d/odump/skent.txt" \
        || { echo "skchain: the chains were not made in the reference (see $d/odump/skent.txt)"; bad=1; }
    if run "$d/ctl-chainmid" native bell-ganado RE4_SVC_EXERCISE=skchain RE4_SVC_CONTROL=chainmid; then
        row "control chainmid" FAIL "$d/odump" "$d/ctl-chainmid"
    else missing=1; echo "control chainmid: run failed"; fi
else
    missing=1; echo "skchain: run failed"
fi
d=$OUT/skent-bell-ganado
if run "$d/odump-plain" odump bell-ganado; then
    row "effect (exercise against none)" FAIL "$d/odump-plain" "$d/odump" nolog
else missing=1; echo "effect: run failed"; fi
for c in entflag entpost entpose enthist; do
    run "$d/ctl-$c" native bell-ganado RE4_SVC_EXERCISE=skent RE4_SVC_CONTROL=$c || { missing=1; echo "control $c: run failed"; continue; }
    row "control $c" FAIL "$d/odump" "$d/ctl-$c"
done
# the collision room release (eng-load1's R2): the reference without an exercise against native with colrel
relrow() {   # relrow <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4
    rows=$((rows + 1))
    python3 "$HERE/svc_compare.py" "$a" "$b" --json "$b/compare.json" > "$b/compare.txt" 2>&1
    local c=$?
    local r rm
    [ -s "$b/colrel.txt" ] || { missing=1; echo "| $name | $must | | no colrel.txt | | ERROR |" >> "$MD"; echo "$name: ERROR (no colrel.txt)"; return; }
    rm=$(python3 - "$b/colrel.txt" <<'PY'
import sys
v = {}
for line in open(sys.argv[1]):
    f = line.split()
    if len(f) >= 6: v[f[1]] = (int(f[3]), int(f[5]))
ok = set(v) == {"before", "released", "rebaked"} and v["released"] == (0, 0) and v["rebaked"] == v["before"] and v["before"][0] > 0
print(("ok " if ok else "BAD ") + " ".join("%s %d pieces %d B" % (k, *v[k]) for k in ("before", "released", "rebaked") if k in v))
sys.exit(0 if ok else 1)
PY
)
    r=$?
    [ $c -gt 1 ] && { missing=1; echo "| $name | $must | ERROR | | | ERROR |" >> "$MD"; echo "$name: ERROR"; return; }
    local got=PASS
    [ $c = 0 ] && [ $r = 0 ] || got=FAIL
    local res="$got (as it must)"
    [ "$got" != "$must" ] && { res="$got (MUST $must)"; bad=1; }
    echo "| $name | $must | queries and bones at svc_compare's bounds $([ $c = 0 ] && echo PASS || echo FAIL) | $rm | | $res |" >> "$MD"
    echo "$name: $res; compare $c; $rm"
}
d=$OUT/colrel-bell-ganado
if run "$d/odump" odump bell-ganado && run "$d/native" native bell-ganado RE4_SVC_EXERCISE=colrel     && run "$d/ctl-colkeep" native bell-ganado RE4_SVC_EXERCISE=colrel RE4_SVC_CONTROL=colkeep; then
    relrow "colrel bell-ganado" PASS "$d/odump" "$d/native"
    relrow "control colkeep" FAIL "$d/odump" "$d/ctl-colkeep"
else missing=1; echo "colrel: run failed"; fi
[ $rows = 11 ] || { echo "skent_check: $rows rows of 11"; missing=1; }
[ $missing = 1 ] && { echo "skent_check: a run or a report is missing ($MD)"; exit 2; }
[ $bad = 1 ] && { echo "skent_check: a row did not end as it must ($MD)"; exit 1; }
echo "skent_check: every row as it must ($MD)"
exit 0
