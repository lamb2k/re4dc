#!/bin/bash
# controls.sh: the plays-right check's own proof (docs/engine/PLAYS_RIGHT.md sections 6 and "Actors").
#
#   RE4_TREE=<converted data tree> controls.sh [out dir] [re4ref binary]
#
# Runs the reference (hostref re4ref) on each base fixture twice and once under each control, then compares
# with plays_right.py and the agreed tolerances. Leon (door103-walk, the T line):
#   determinism     the reference against itself (a second run): must PASS, bit for bit
#   walk-speed      the walk covers 2% more ground per tick: must FAIL (position)
#   drop-rng        one generator call dropped (the first after tick 1): must FAIL (generator state)
#   shift-input     every pad change one tick later: must FAIL (routine, motion)
# Actors (lane eng-host2; the A block of one actor, every actor field):
#   determinism-ganado    bell-ganado twice, the walking Ganado (list entry 0x14): must PASS
#   drop-rng-ganado       that Ganado's first generator call from tick 1 dropped: must FAIL
#   determinism-hit       bell-ganado-hit twice (a handgun hit on 0x14 at tick 60): must PASS
#   late-hit              the same hit one tick later: must FAIL
#   determinism-ashley    square-follow twice, Ashley (id 03): must PASS
#   follow-dist           Ashley 10% further from Leon while she follows him: must FAIL
# Exit status 0 when every line ends as it must; the table goes to stdout and <out dir>/controls.md.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../.." && pwd)
OUT=${1:-$ROOT/build/hostref/controls}
BIN=${2:-$ROOT/build/hostref/plain/re4ref}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
TOL=$HERE/tolerances.json
mkdir -p "$OUT"
run() {   # run <fixture> <name> [control]
    local c=()
    [ -n "${3:-}" ] && c=(--control "$3")
    "$BIN" --tree "$TREE" --fixture "$HERE/fixtures/$1" --out "$OUT/$2.trace" --log "$OUT/$2.log" "${c[@]}" \
        || { echo "re4ref failed: $2"; exit 2; }
}
run door103-walk.txt base
run door103-walk.txt base2
run door103-walk.txt walk walk-speed=1.02
run door103-walk.txt drop drop-rng=1
run door103-walk.txt shift shift-input=1
run bell-ganado.txt ganado
run bell-ganado.txt ganado2
run bell-ganado.txt ganado-drop drop-rng-actor=1,3     # A k=3 is list entry 0x14
run bell-ganado-hit.txt hit
run bell-ganado-hit.txt hit2
run bell-ganado-hit.txt hit-late late-hit=1
run square-follow.txt ashley
run square-follow.txt ashley2
run square-follow.txt ashley-far follow-dist=1.1
status=0
{
    echo "| Check | Must | Result | First divergence |"
    echo "|---|---|---|---|"
    for row in "determinism:base:base2:PASS:" "walk-speed:base:walk:FAIL:" "drop-rng:base:drop:FAIL:" \
               "shift-input:base:shift:FAIL:" \
               "determinism-ganado:ganado:ganado2:PASS:e=14" "drop-rng-ganado:ganado:ganado-drop:FAIL:e=14" \
               "determinism-hit:hit:hit2:PASS:e=14" "late-hit:hit:hit-late:FAIL:e=14" \
               "determinism-ashley:ashley:ashley2:PASS:id=03" "follow-dist:ashley:ashley-far:FAIL:id=03"; do
        IFS=: read -r name a b must actor <<< "$row"
        sel=()
        [ -n "$actor" ] && sel=(--actor "$actor")
        python3 "$HERE/plays_right.py" "$OUT/$a.trace" "$OUT/$b.trace" --tolerances "$TOL" "${sel[@]}" \
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
