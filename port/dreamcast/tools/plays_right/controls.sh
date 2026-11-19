#!/bin/bash
# controls.sh: the plays-right check's own proof (docs/engine/PLAYS_RIGHT.md section 6).
#
#   RE4_TREE=<converted data tree> controls.sh [out dir] [re4ref binary]
#
# Runs the reference (hostref re4ref) on the door103-walk fixture twice and once under each control, then
# compares with plays_right.py and the agreed tolerances:
#   determinism   the reference against itself (a second run): must PASS, bit for bit
#   walk-speed    the walk covers 2% more ground per tick: must FAIL (position)
#   drop-rng      one generator call dropped (the first after tick 1): must FAIL (generator state)
#   shift-input   every pad change one tick later: must FAIL (routine, motion)
# Exit status 0 when every line ends as it must; the table goes to stdout and <out dir>/controls.md.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
OUT=${1:-$ROOT/build/hostref/controls}
BIN=${2:-$ROOT/build/hostref/plain/re4ref}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
FX=$HERE/fixtures/door103-walk.txt
TOL=$HERE/tolerances.json
mkdir -p "$OUT"
run() {   # run <name> [control]
    local c=()
    [ -n "${2:-}" ] && c=(--control "$2")
    "$BIN" --tree "$TREE" --fixture "$FX" --out "$OUT/$1.trace" --log "$OUT/$1.log" "${c[@]}" || { echo "re4ref failed: $1"; exit 2; }
}
run base
run base2
run walk walk-speed=1.02
run drop drop-rng=1
run shift shift-input=1
status=0
{
    echo "| Check | Must | Result | First divergence |"
    echo "|---|---|---|---|"
    for pair in "determinism:base2:PASS" "walk-speed:walk:FAIL" "drop-rng:drop:FAIL" "shift-input:shift:FAIL"; do
        IFS=: read -r name trace must <<< "$pair"
        python3 "$HERE/plays_right.py" "$OUT/base.trace" "$OUT/$trace.trace" --tolerances "$TOL" \
            --json "$OUT/$name.json" --quiet
        rc=$?
        got=$([ $rc -eq 0 ] && echo PASS || echo FAIL)
        first=$(python3 -c "import json,sys; j=json.load(open(sys.argv[1])); d=j.get('first_divergence'); print('-' if not d else 'tick %d %s: %s vs %s' % (d['tick'], d['field'], d['a'], d['b']))" "$OUT/$name.json")
        ok=$([ "$got" = "$must" ] && echo "$got (as it must)" || echo "$got (WRONG: must $must)")
        [ "$got" = "$must" ] || status=1
        echo "| $name | $must | $ok | $first |"
    done
} | tee "$OUT/controls.md"
exit $status
