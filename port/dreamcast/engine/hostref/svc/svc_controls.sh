#!/bin/bash
# svc_controls.sh: the native services' equivalence check and its own proof (lane eng-svc; docs/engine/SERVICES.md).
#
#   RE4_TREE=<converted data tree> svc_controls.sh <out dir> [fixture ...]
#
# For each fixture (default: all six) the reference with the dump (odump) and the native build run the same inputs;
# svc_compare.py compares bones and collision queries tick by tick, plays_right.py the traces. Then the controls,
# each of which must make the comparison FAIL:
#   parent   RE4_SVC_CONTROL=parent=5: bone 5's parent one bone too low (a wrong parent index in the table)
#   floor    RE4_SVC_CONTROL=floor=1: every floor and slope triangle raised by 1 unit in the baked tables
#   noik     RE4_SVC_CONTROL=noik: the IK pass skipped
# and the native build against itself (a second run) must PASS bit for bit (determinism).
# Exit status 0 when every line ends as it must; the table goes to stdout and <out dir>/svc_controls.md.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
shift
FIX=${*:-door103-walk e1-route bell-ganado bell-ganado-hit hill-ashley square-follow}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=$ROOT/build/hostref
PR=$ROOT/port/dreamcast/tools/plays_right
mkdir -p "$OUT"
run() {   # run <binary> <fixture> <dir> [env...]
    local bin=$1 fx=$2 d=$3
    shift 3
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" "$@" "$bin" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" --out "$d/trace.txt" --log "$d/run.log" \
        2> "$d/err.txt" || { echo "re4ref failed: $d"; exit 2; }
}
actors() {   # the actors of a fixture's A lines, as plays_right --actor selectors
    case $1 in
        bell-ganado) echo "e=14 e=1c e=1e e=1f" ;;
        bell-ganado-hit) echo "e=14" ;;
        hill-ashley) echo "id=03 e=df e=e0 e=e1 e=e3" ;;
        square-follow) echo "id=03" ;;
    esac
}
status=0
row() {   # row <name> <must> <ref dir> <test dir> <fixture>
    local name=$1 must=$2 a=$3 b=$4 fx=$5
    python3 "$HERE/svc_compare.py" "$a" "$b" --json "$b/compare.json" > "$b/compare.txt"
    local sc=$?
    local pr=0 s
    python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --json "$b/pr.json" --quiet || pr=1
    for s in $(actors "$fx"); do
        python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --actor "$s" --quiet || pr=1
    done
    local got=PASS
    [ $sc -ne 0 ] && got=FAIL
    local ok="$got (as it must)"
    [ "$got" = "$must" ] || { ok="$got (WRONG: must $must)"; status=1; }
    local first
    first=$(python3 -c "
import json,sys
j=json.load(open(sys.argv[1])); b=j['bones']; c=j['collision']
f=b.get('first') or c.get('first')
print('bones %d/%d bit-identical (%d equal), max %.3g u %.3g deg; queries %d/%d identical, max %.3g u; first: %s' % (b['bit_identical_bones'], b['bones'], b['equal_bones'], max(b['max_pos'], b['max_pal_pos']), max(b['max_deg'], b['max_pal_deg']), c['identical'], c['compared'], c['max_point'], json.dumps(f) if f else '-'))" "$b/compare.json")
    echo "| $fx | $name | $must | $ok | $([ $pr -eq 0 ] && echo PASS || echo FAIL) | $first |"
}
{
    echo "| Fixture | Check | Must | Bones and collision | Traces | Detail |"
    echo "|---|---|---|---|---|---|"
    for fx in $FIX; do
        run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native"
        row native PASS "$OUT/$fx/ref" "$OUT/$fx/native" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native2"
        row determinism PASS "$OUT/$fx/native" "$OUT/$fx/native2" "$fx"
    done
    for fx in door103-walk bell-ganado; do
        [ -d "$OUT/$fx/ref" ] || run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-parent" RE4_SVC_CONTROL=parent=5
        row "control: parent of bone 5 wrong by one" FAIL "$OUT/$fx/ref" "$OUT/$fx/c-parent" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-floor" RE4_SVC_CONTROL=floor=1
        row "control: floors 1 unit higher" FAIL "$OUT/$fx/ref" "$OUT/$fx/c-floor" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-noik" RE4_SVC_CONTROL=noik
        row "control: IK pass skipped" FAIL "$OUT/$fx/ref" "$OUT/$fx/c-noik" "$fx"
    done
} | tee "$OUT/svc_controls.md"
exit $status
