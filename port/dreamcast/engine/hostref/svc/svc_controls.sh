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
#   mkrow    RE4_SVC_CONTROL=mkrow: the baked motion keys read one frame late (the next frame's row; lane eng-svc2)
#   mkroot   RE4_SVC_CONTROL=mkroot: the root motion's (and attach camera's) rows read one frame late (lane eng-svc3)
#   mkcoarse RE4_SVC_CONTROL=mkcoarse: with the 16-bit rows, every step cut to its top 8 bits (the tolerance must fail)
#   histnone RE4_SVC_CONTROL=histnone: no bone keeps its world_old / world_old2 (the check build serves NaN)
#   histfrozen RE4_SVC_CONTROL=histfrozen: updateOldPos never moves the kept history
#   clothshort RE4_SVC_CONTROL=clothshort: every cloth chain one link short (the native cloth; lane eng-svc2)
#   clothnograv RE4_SVC_CONTROL=clothnograv: cloth gravity off
#   clothwind RE4_SVC_CONTROL=clothwind: the cloth's wind twice as strong (the wind-on statistics must fail)
#   colgrid  RE4_SVC_CONTROL=colgrid: the line query's grid cells taken one cell to the side (polygons wrongly skipped)
# Lane eng-svc4 (round 4: the native versions of the remaining service units) adds the boundary log svc4.txt
# (svc4_dump.cpp: every call the behaviour makes to a round-4 entry point, compared line for line by svc4_compare.py,
# in every row) and the controls:
#   volpush  RE4_SVC_CONTROL=volpush: every push between two actor bodies 10% longer (hill-ashley: 41 pushes)
#   volline  RE4_SVC_CONTROL=volline: a line tests the cylinder bodies whatever its flag (square-follow: the camera's lines past Ashley)
#   colfloor RE4_SVC_CONTROL=colfloor: the per-model floor snap 0.5 unit high (col_model.cpp; e1-route)
#   colwall  RE4_SVC_CONTROL=colwall: the per-model wall slide's radius 10% larger (e1-route)
#   routenear RE4_SVC_CONTROL=routenear: the nearest reachable way point is the second one (hill-ashley: the partner)
#   followslow RE4_SVC_CONTROL=followslow: every root-motion follower blend step one tick longer (e1-route, exercise follow)
#   modelslot RE4_SVC_CONTROL=modelslot: a model's contiguous parts run starts at the second free run (hill-ashley)
#   camfov   RE4_SVC_CONTROL=camfov: the view frustum built for a field of view 1 degree wider (door103-walk)
#   camroll  RE4_SVC_CONTROL=camroll: the camera's roll orientation 0.01 rad further (door103-walk)
#   routehop RE4_SVC_CONTROL=routehop: the way points between skipped, every reachable destination its own next hop (bell-ganado: the Ganados' chase)
# The svc builds host the original cloth (game/pendulum.cpp) in the reference; the native build runs services/cloth.
# Random numbers are split (owner 2026-11-19): the cloth draws from a presentation generator in both builds, never from
# the behaviour's Rnd. So each fixture runs twice: with the cloth's wind on ("native": every bone but the cloth links
# compared as before, the links by cloth_stats.py, the traces in every field) and off (RE4_SVC_CLOTH_WIND=0: every
# bone, the links included, compared as before). The controls run with the wind off, the wind control with it on.
# and the native build against itself (a second run) must PASS bit for bit (determinism).
# The native runs sample the baked motion keys (RE4_SVC_MK=<pack>; without it the fixtures' archives are baked into
# <out dir>/motion.mkp, float32 rows, and <out dir>/motion-s16.mkp, 16-bit rows, first: bake/motion_keys.py). Each
# native row's detail ends with where the motion samples came from (rows; decoded from the clip's keys by the native
# decoder; the original decoder, always 0 since lane eng-svc3). Lane eng-svc3 adds, per fixture: the native build with
# no pack (RE4_SVC_MK=none: every sample, root motion included, decoded from the keys: must be bit-identical), and the
# 16-bit rows (an approximation, owner 2026-10-19: every bone but the cloth links within 1 unit / 0.1 degree, the links
# by cloth_stats.py, collision results exact and points within 1 unit, traces in every field).
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
rm -f "$OUT/.status"
ARCS="em/pl00.drs em/pl0e.drs em/pl0f.drs em/wep02.drs em/pl11.drs em/em15.drs em/em16.drs em/em12.drs"
if [ -z "${RE4_SVC_MK:-}" ]; then
    python3 "$ROOT/port/dreamcast/engine/bake/motion_keys.py" --tree "$TREE" --out "$OUT/motion.mkp" --report "$OUT/motion.tsv" \
        $ARCS > "$OUT/motion.txt" || { echo "motion key bake failed"; exit 2; }
    export RE4_SVC_MK="$OUT/motion.mkp"
fi
MK16=${RE4_SVC_MK16:-$OUT/motion-s16.mkp}
if [ ! -f "$MK16" ]; then
    python3 "$ROOT/port/dreamcast/engine/bake/motion_keys.py" --tree "$TREE" --out "$MK16" --report "$OUT/motion-s16.tsv" \
        --rows s16 $ARCS > "$OUT/motion-s16.txt" || { echo "motion key bake (s16) failed"; exit 2; }
fi
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
row() {   # row <name> <must> <ref dir> <test dir> <fixture> [cloth]: cloth = the wind is on (links by statistics)
    local name=$1 must=$2 a=$3 b=$4 fx=$5 mode=${6:-}
    local cs=""
    if [ "$mode" = cloth ] || [ "$mode" = approx ]; then
        local ct=""
        [ "$mode" = approx ] && ct="--col 1.0"
        python3 "$HERE/svc_compare.py" "$a" "$b" --skip-cloth $ct --json "$b/compare.json" > "$b/compare.txt"
        local sc=$?
        cs=$(python3 "$HERE/cloth_stats.py" "$a" "$b" --json "$b/cloth.json") || sc=1
        cs="; $(echo "$cs" | sed 's/^\(PASS\|FAIL\)  //')"
    else
        python3 "$HERE/svc_compare.py" "$a" "$b" --json "$b/compare.json" > "$b/compare.txt"
        local sc=$?
    fi
    # lane eng-svc4: the round-4 services' boundary log (svc4.txt), line for line
    local s4=""
    if [ -f "$a/svc4.txt" ] && [ -f "$b/svc4.txt" ]; then
        local t4=""
        [ "$mode" = approx ] && t4="--tol 1.0"
        s4=$(python3 "$HERE/svc4_compare.py" "$a" "$b" --json "$b/svc4.json" $t4) || sc=1
        s4="; $(echo "$s4" | sed 's/^\(PASS\|FAIL\)  //')"
    fi
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
print('bones %d/%d bit-identical (%d equal), max %.3g u %.3g deg; queries %d/%d identical, max %.3g u; first: %s' % (b['bit_identical_bones'], b['bones'], b['equal_bones'], max(b['max_pos'], b['max_pal_pos']), max(b['max_deg'], b['max_pal_deg']), c['identical'], c['compared'], c['max_point'], json.dumps(f) if f else '-'), end='')
h=j.get('history')
if h: print('; history %d/%d bone-ticks equal (%d not known yet), max %.3g u' % (h['equal'], h['compared'], h['unknown'], h['max']), end='')
print()" "$b/compare.json")
    local keys=""
    [ -f "$b/svc.txt" ] && keys=$(awk '/^motion keys:/ {printf "; motion samples: rows %s, decoded from keys %s, original decoder 0; root motion: rows %s, decoded %s", $11, $15, $23, $25}
        /^cloth:/ {printf "; cloth: %s chains native (fallback %s), %s steps", $3, $6+0, $8+0}
        /^col / {for (i = 2; i < NF; i += 2) v[$i] = $(i+1); printf "; line queries %s: polygons tested %s, skipped %s (check: hits among them %s, end-point only %s)", v["line_queries"], v["tris_line"], v["tris_skipped"], v["filter_miss"], v["filter_end"]}' "$b/svc.txt")
    [ "$got" = "$must" ] || echo 1 > "$OUT/.status"
    echo "| $fx | $name | $must | $ok | $([ $pr -eq 0 ] && echo PASS || echo FAIL) | $first$cs$keys$s4 |"
}
{
    echo "| Fixture | Check | Must | Bones and collision | Traces | Detail |"
    echo "|---|---|---|---|---|---|"
    for fx in $FIX; do
        run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native"
        row "native (cloth wind on: links by statistics)" PASS "$OUT/$fx/ref" "$OUT/$fx/native" "$fx" cloth
        run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref0" RE4_SVC_CLOTH_WIND=0
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native0" RE4_SVC_CLOTH_WIND=0
        row "native (cloth wind off: every bone)" PASS "$OUT/$fx/ref0" "$OUT/$fx/native0" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/native2"
        row determinism PASS "$OUT/$fx/native" "$OUT/$fx/native2" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/nopack" RE4_SVC_CLOTH_WIND=0 RE4_SVC_MK=none
        row "native, no pack (every sample decoded from the keys)" PASS "$OUT/$fx/ref0" "$OUT/$fx/nopack" "$fx"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/s16" RE4_SVC_CLOTH_WIND=0 RE4_SVC_MK="$MK16"
        row "native, 16-bit rows (tolerance; links by statistics)" PASS "$OUT/$fx/ref0" "$OUT/$fx/s16" "$fx" approx
    done
    for fx in door103-walk bell-ganado; do
        [ -d "$OUT/$fx/ref0" ] || run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref0" RE4_SVC_CLOTH_WIND=0
        ctl() {   # ctl <name> <control>: a wind-off run under the control, against the wind-off reference
            run "$B/native/re4ref" "$fx" "$OUT/$fx/c-$2" RE4_SVC_CLOTH_WIND=0 RE4_SVC_CONTROL=$2
            row "control: $1" FAIL "$OUT/$fx/ref0" "$OUT/$fx/c-$2" "$fx"
        }
        ctl "parent of bone 5 wrong by one" parent=5
        ctl "floors 1 unit higher" floor=1
        ctl "IK pass skipped" noik
        ctl "motion keys one frame late" mkrow
        ctl "root motion rows one frame late" mkroot
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-mkcoarse" RE4_SVC_CLOTH_WIND=0 RE4_SVC_CONTROL=mkcoarse RE4_SVC_MK="$MK16"
        row "control: 16-bit rows cut to 8 bits" FAIL "$OUT/$fx/ref0" "$OUT/$fx/c-mkcoarse" "$fx" approx
        ctl "no bone history kept (check build: NaN)" histnone
        ctl "bone history never moves" histfrozen
        ctl "cloth chains one link short" clothshort
        ctl "cloth gravity off" clothnograv
        ctl "line query cells one to the side" colgrid
    done
    # lane eng-svc4: the round-4 services' controls, each on a fixture that exercises it (svc4.txt counters)
    r4ctl() {   # r4ctl <fixture> <name> <control>
        local fx=$1
        [ -d "$OUT/$fx/ref0" ] || run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref0" RE4_SVC_CLOTH_WIND=0
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-$3" RE4_SVC_CLOTH_WIND=0 RE4_SVC_CONTROL=$3
        row "control: $2" FAIL "$OUT/$fx/ref0" "$OUT/$fx/c-$3" "$fx"
    }
    r4ctl hill-ashley "pushes between bodies 10% longer" volpush
    r4ctl square-follow "line tests cylinder bodies whatever the flag" volline
    r4ctl e1-route "floor snap 0.5 unit high" colfloor
    r4ctl e1-route "wall slide radius 10% larger" colwall
    r4ctl hill-ashley "nearest way point is the second reachable" routenear
    r4ctl bell-ganado "way points between skipped" routehop
    r4ctl hill-ashley "parts run at the second free run" modelslot
    r4ctl door103-walk "frustum 1 degree wider" camfov
    r4ctl door103-walk "roll orientation 0.01 rad further" camroll
    # service exercises (svc4_dump.cpp, RE4_SVC_EXERCISE): calls planted at fixed ticks for services the fixtures' play
    # does not reach; the reference and the native build get the same calls, so the comparison is still original
    # against native on the same inputs. Each exercise's controls must FAIL.
    exrow() {   # exrow <fixture> <exercise> <control>...
        local fx=$1 ex=$2 c
        shift 2
        run "$B/odump/re4ref" "$fx" "$OUT/$fx/x-$ex-ref" RE4_SVC_CLOTH_WIND=0 RE4_SVC_EXERCISE=$ex
        run "$B/native/re4ref" "$fx" "$OUT/$fx/x-$ex" RE4_SVC_CLOTH_WIND=0 RE4_SVC_EXERCISE=$ex
        row "exercise $ex: native" PASS "$OUT/$fx/x-$ex-ref" "$OUT/$fx/x-$ex" "$fx"
        for c in "$@"; do
            run "$B/native/re4ref" "$fx" "$OUT/$fx/x-$ex-c-$c" RE4_SVC_CLOTH_WIND=0 RE4_SVC_EXERCISE=$ex RE4_SVC_CONTROL=$c
            row "exercise $ex, control: $c" FAIL "$OUT/$fx/x-$ex-ref" "$OUT/$fx/x-$ex-c-$c" "$fx"
        done
    }
    exrow e1-route follow followslow
    exrow e1-route camtrack camfov camroll
    for fx in e1-route; do   # the wind pushes in proportion to the root speed: the moving fixture
        [ -d "$OUT/$fx/ref" ] || run "$B/odump/re4ref" "$fx" "$OUT/$fx/ref"
        run "$B/native/re4ref" "$fx" "$OUT/$fx/c-clothwind" RE4_SVC_CONTROL=clothwind
        row "control: cloth wind twice as strong" FAIL "$OUT/$fx/ref" "$OUT/$fx/c-clothwind" "$fx" cloth
    done
} | tee "$OUT/svc_controls.md"
[ -f "$OUT/.status" ] && status=1
rm -f "$OUT/.status"
exit $status
