#!/bin/bash
# speed_controls.sh: the controls of lane eng-svcspd1's speed fixes (docs/engine/SERVICES_COST_20261121.md). Each fix
# keeps every result of the service the same; its check is the service equivalence suite (hostref/svc/svc_controls.sh,
# every row as it must). Here each fix gets an input that breaks it, and the same comparison (svc_compare.py, wind off:
# every bone, the cloth links included, and every collision query, against the reference) must then FAIL. The plain
# native run must PASS on the same fixtures (the comparison is the suite's).
#
#   RE4_TREE=<converted data tree> speed_controls.sh <out dir>
#
# Controls (RE4_SVC_CONTROL, read by the services themselves), each on the fixtures that exercise its fix:
#   trigstale   skeleton: a bone's kept sin and cos reused whatever its angles (fix 1, the pose angles' sines kept)
#   clothbound  cloth: the parallel volume test's skip bound 40 units short (fix 2, the volume tests' early out; only
#               the skirt's tests come near enough to hit: hill-ashley)
#   ikclosure   skeleton: the world pass before the IK leaves out the IK chains' parents (fix 3, the pass limited to the
#               bones the IK reads)
#   worldfast   skeleton: the world pass's inline position product takes its second row from the parent's first (a
#               transcription slip; fix 4, the pass's steps inline)
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build, a run or a comparison is missing; the
# table goes to stdout and <out dir>/speed_controls.md.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
SV=$ROOT/port/dreamcast/engine/hostref/svc
PR=$ROOT/port/dreamcast/tools/plays_right
CONTROLS=${SPEED_CONTROLS:-"trigstale:door103-walk,hill-ashley,bell-ganado clothbound:hill-ashley"}
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "speed_controls: no $bin build at $B/$bin/re4ref"; exit 2; }
done
mkdir -p "$OUT"
echo 0 > "$OUT/.status"
MK=${RE4_SVC_MK:-$OUT/motion.mkp}
if [ ! -f "$MK" ]; then   # the archives svc_controls.sh bakes
    ARCS="em/pl00.drs em/pl0e.drs em/pl0f.drs em/wep02.drs em/pl11.drs em/em15.drs em/em16.drs em/em12.drs"
    python3 "$ROOT/port/dreamcast/engine/bake/motion_keys.py" --tree "$TREE" --out "$MK" --report "$OUT/motion.tsv" \
        $ARCS > "$OUT/motion.txt" 2>&1 || { echo "speed_controls: motion key bake failed"; exit 2; }
fi
run() {   # run <binary> <fixture> <dir> [env...]
    local bin=$1 fx=$2 d=$3
    shift 3
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_CLOTH_WIND=0 RE4_SVC_MK="$MK" "$@" "$bin" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" || { echo "speed_controls: re4ref failed: $d"; echo 2 > "$OUT/.status"; }
}
row() {   # row <fixture> <name> <must> <test dir>
    local fx=$1 name=$2 must=$3 d=$4 got=PASS
    python3 "$SV/svc_compare.py" "$OUT/$fx/ref0" "$d" --json "$d/compare.json" > "$d/compare.txt" || got=FAIL
    [ -s "$d/compare.json" ] || { got=ERROR; echo 2 > "$OUT/.status"; }
    local ok="$got (as it must)"
    [ "$got" = "$must" ] || { ok="$got (WRONG: must $must)"; [ "$(cat "$OUT/.status")" = 0 ] && echo 1 > "$OUT/.status"; }
    local first
    first=$(python3 -c "
import json,sys
j=json.load(open(sys.argv[1])); b=j['bones']; c=j['collision']
f=b.get('first') or c.get('first')
print('bones %d/%d bit-identical, max %.3g u %.3g deg; queries %d/%d identical; first: %s' % (b['bit_identical_bones'], b['bones'], max(b['max_pos'], b['max_pal_pos']), max(b['max_deg'], b['max_pal_deg']), c['identical'], c['compared'], json.dumps(f) if f else '-'))" "$d/compare.json" 2>/dev/null)
    echo "| $fx | $name | $must | $ok | $first |"
}
{
    echo "| Fixture | Row | Must | Result | Detail |"
    echo "|---|---|---|---|---|"
    for fx in door103-walk hill-ashley bell-ganado; do
        run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref0"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native0"
        row "$fx" "native (the fixes in)" PASS "$OUT/$fx/native0"
    done
    for cf in $CONTROLS; do
        c=${cf%%:*}
        for fx in $(echo "${cf#*:}" | tr ',' ' '); do
            run "$B/native/re4ref" "$fx" "$OUT/$fx/c-$c" RE4_SVC_CONTROL=$c
            row "$fx" "control: $c" FAIL "$OUT/$fx/c-$c"
        done
    done
} | tee "$OUT/speed_controls.md"
exit "$(cat "$OUT/.status")"
