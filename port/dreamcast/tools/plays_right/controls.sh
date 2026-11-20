#!/bin/bash
# controls.sh: the plays-right check's own proof (docs/engine/PLAYS_RIGHT.md sections 6 and "Actors").
#
#   RE4_TREE=<converted data tree> controls.sh [out dir] [re4ref binary]
#
# Runs the reference (hostref re4ref) on each base fixture twice and once under each control, then compares
# with plays_right.py and the agreed tolerances. Leon (door103-walk, the T line):
#   determinism     the reference against itself (a second run): must PASS, bit for bit
#   walk-speed      the walk covers 2% more ground per tick: must FAIL (position)
#   drop-rng        one generator call dropped (the first after tick 1): must FAIL (generator state). On bell-ganado
#                   (lane eng-svc5): Leon's own door103 walk no longer draws from the behaviour generator (his eye wander
#                   is presentation since lane eng-e1d), so the control dropped nothing there and passed
#   shift-input     every pad change one tick later: must FAIL (routine, motion)
# Actors (lane eng-host2; the A block of one actor, every actor field):
#   determinism-ganado    bell-ganado twice, the walking Ganado (list entry 0x14): must PASS
#   drop-rng-ganado       that Ganado's first generator call from tick 1 dropped: must FAIL
#   determinism-hit       bell-ganado-hit twice (a handgun hit on 0x14 at tick 60): must PASS
#   late-hit              the same hit one tick later: must FAIL
#   determinism-ashley    square-follow twice, Ashley (id 03): must PASS
#   follow-dist           Ashley 10% further from Leon while she follows him: must FAIL
# Strict structure (lane eng-svc5; plays_right.py fails on a broken trace whatever its values; --lenient is the old
# reader, for sparse old-game logs), each on a copy of the bell-ganado trace against the original:
#   missing-tick    the T line of tick 100 removed                        must FAIL (missing tick)
#   missing-field   the p= of one T line removed                          must FAIL (missing field)
#   non-finite      one T position a NaN                                  must FAIL (non-finite value)
#   duplicate-tick  one T line twice                                      must FAIL (duplicate tick)
#   short-trace     the trace cut after tick 200 (of 300)                 must FAIL (missing tick)
#   count           --expect-count 999 on two identical traces            must FAIL (tick count)
#   actor-gap       the A line of 0x14 at tick 100 removed (--actor e=14)  must FAIL (missing tick)
#   lenient         the missing-tick copy with --lenient                  must PASS (the old reader skips it)
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
run bell-ganado.txt drop drop-rng=1
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
# strict structure: broken copies of the bell-ganado trace (lane eng-svc5)
python3 - "$OUT" <<'EOF' || { echo "mutation failed"; exit 2; }
import re, sys
o = sys.argv[1]
L = open(o + '/ganado.trace').read().splitlines()
def w(name, lines):
    open(o + '/' + name + '.trace', 'w').write('\n'.join(lines) + '\n')
w('s-gap', [s for s in L if not s.startswith('T t=100 ')])
w('s-field', [re.sub(r' p=\S+', '', s) if s.startswith('T t=100 ') else s for s in L])
w('s-nan', [re.sub(r' p=[0-9a-f]{8},', ' p=7fc00000,', s) if s.startswith('T t=100 ') else s for s in L])
w('s-dup', [x for s in L for x in ([s, s] if s.startswith('T t=100 ') else [s])])
w('s-cut', [s for s in L if not re.match(r'^[TAR] t=(\d+)', s) or int(re.match(r'^[TAR] t=(\d+)', s).group(1)) <= 200])
w('s-agap', [s for s in L if not (s.startswith('A t=100 ') and ' e=14 ' in s)])
EOF
status=0
{
    echo "| Check | Must | Result | First divergence |"
    echo "|---|---|---|---|"
    for row in "determinism:base:base2:PASS:" "walk-speed:base:walk:FAIL:" "drop-rng:ganado:drop:FAIL:" \
               "shift-input:base:shift:FAIL:" \
               "determinism-ganado:ganado:ganado2:PASS:e=14" "drop-rng-ganado:ganado:ganado-drop:FAIL:e=14" \
               "determinism-hit:hit:hit2:PASS:e=14" "late-hit:hit:hit-late:FAIL:e=14" \
               "determinism-ashley:ashley:ashley2:PASS:id=03" "follow-dist:ashley:ashley-far:FAIL:id=03" \
               "missing-tick:ganado:s-gap:FAIL:" "missing-field:ganado:s-field:FAIL:" "non-finite:ganado:s-nan:FAIL:" \
               "duplicate-tick:ganado:s-dup:FAIL:" "short-trace:ganado:s-cut:FAIL:" "count:ganado:ganado2:FAIL::--expect-count=999" \
               "actor-gap:ganado:s-agap:FAIL:e=14" "lenient:ganado:s-gap:PASS::--lenient"; do
        IFS=: read -r name a b must actor opt <<< "$row"
        sel=()
        [ -n "$actor" ] && sel=(--actor "$actor")
        [ -n "${opt:-}" ] && sel+=("$opt")
        python3 "$HERE/plays_right.py" "$OUT/$a.trace" "$OUT/$b.trace" --tolerances "$TOL" "${sel[@]}" \
            --json "$OUT/$name.json" --quiet
        rc=$?
        got=$([ $rc -eq 0 ] && echo PASS || echo FAIL)
        first=$(python3 -c "import json,sys; j=json.load(open(sys.argv[1])); d=j.get('first_divergence'); s=j.get('structure') or []; print(('structure: %d problems, first %s' % (j['structure_problems'], ' '.join(str(s[0][k]) for k in ('kind', 'trace', 'tick', 'field', 'detail') if s[0][k] not in (None, ''))) + ('; ' if d else '')) if s else '', end=''); print('-' if not d and not s else ('' if not d else 'tick %d %s: %s vs %s' % (d['tick'], d['field'], d['a'], d['b'])))" "$OUT/$name.json")
        ok=$([ "$got" = "$must" ] && echo "$got (as it must)" || echo "$got (WRONG: must $must)")
        [ "$got" = "$must" ] || status=1
        echo "| $name | $must | $ok | $first |"
    done
} | tee "$OUT/controls.md"
exit $status
