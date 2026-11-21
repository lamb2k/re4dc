#!/bin/bash
# camcheck.sh: the camera service against the original camera code (lane eng-e1j, ruling H-016.1; SERVICES.md 48).
#
#   RE4_TREE=<converted data tree> camcheck.sh <out dir>
#
# re4ref odump (the original camera units: camera, view, cam_sys, cam_ctrl, cam_qfps, cam_extra) and native (the
# engine's camera service: services/camera) run the same inputs, wind off; svc/camcheck.py compares the frame's camera
# of every tick (cam.txt: eye, target, roll, fov, and the controller's area, cut, routine and blend frames), within
# max(0.01 unit, 2^-20 of the coordinate) and 0.01 degree (stated before the run; CAM_POS, CAM_REL, CAM_DEG override). plays_right.py compares the
# traces. Rows that must PASS: five fixtures (the village route, the hill, the bell fight, the square follow, the
# door walk), determinism (bit for bit), the exercises camblend (cut blends) and camrail (rail fit, search and
# evaluation: no fixture has either). Controls that must FAIL: smoothing off, cut blend off, rail parameter 0.25 on.
# Each row states two musts, the camera's and the trace's (plays_right.py, lane eng-e1o): smoothing off and cut blend off
# change the play (trace FAIL); the rail control moves only the exercise's rail lines (trace PASS: the rail is not played).
# Lane eng-e1n: the exercise campush (the push-object camera, its door branch) must PASS / PASS; controls caminv (its
# inverse skipped) and camfollow (the shoulder follow's rate) must FAIL / FAIL (they move the camera, so the stick's
# world direction and the play); the exercise camexport: the engine's cut writer refuses an oversized cut with the
# buffer and its guards untouched (PASS), the original writer overruns it (FAIL; no trace compared).
# Lane eng-e1p: the exercise camrefuse (four cases, each PASS) and its control camlate (the stale case FAIL).
# Exit 0 when every row is as it must, 1 when one is not, 2 when a run or a build is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
PR=$ROOT/port/dreamcast/tools/plays_right
CC=$HERE/camcheck.py
for bin in odump native; do
    [ -x "$B/$bin/re4ref" ] || { echo "camcheck: no $bin build at $B/$bin/re4ref (make $bin)"; exit 2; }
done
mkdir -p "$OUT"
rm -f "$OUT/.wrong" "$OUT/.abort"
TOL="--pos ${CAM_POS:-0.01} --rel ${CAM_REL:-9.5367431640625e-07} --deg ${CAM_DEG:-0.01}"
run() {   # run <bin> <fixture> <dir> [env...]
    local bin=$1 fx=$2 d=$3
    shift 3
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_CLOTH_WIND=0 "$@" "$B/$bin/re4ref" --tree "$TREE" --fixture "$PR/fixtures/$fx.txt" \
        --out "$d/trace.txt" --log "$d/run.log" 2> "$d/err.txt" || { echo "camcheck: run failed $d" >&2; touch "$OUT/.abort"; }
}
row() {   # row <name> <camera must> <trace must> <ref dir> <test dir> [exact]
    # lane eng-e1o (H-017.8): the row is as it must only when the camera AND the trace (plays_right.py's exit) end as
    # they must; a missing or empty trace is an error, not a FAIL (plays_right.py exits 1 on an unreadable trace too)
    local name=$1 must=$2 tmust=$3 a=$4 b=$5 res got tgot
    if [ "${6:-}" = exact ]; then res=$(python3 "$CC" "$a" "$b" --pos 0 --rel 0 --deg 0); else res=$(python3 "$CC" "$a" "$b" $TOL --json "$b/cam.json"); fi
    case $? in 0) got=PASS ;; 1) got=FAIL ;; *) got=ERROR; touch "$OUT/.abort" ;; esac
    if [ -s "$a/trace.txt" ] && [ -s "$b/trace.txt" ]; then
        python3 "$PR/plays_right.py" "$a/trace.txt" "$b/trace.txt" --tolerances "$PR/tolerances.json" --quiet > /dev/null
        case $? in 0) tgot=PASS ;; 1) tgot=FAIL ;; *) tgot=ERROR; touch "$OUT/.abort" ;; esac
    else
        tgot=ERROR; touch "$OUT/.abort"
    fi
    local ok="$got (as it must)" tok="$tgot (as it must)"
    [ "$got" = "$must" ] || { ok="$got (WRONG: must $must)"; touch "$OUT/.wrong"; }
    [ "$tgot" = "$tmust" ] || { tok="$tgot (WRONG: must $tmust)"; touch "$OUT/.wrong"; }
    echo "| $name | $must / $tmust | $ok | $tok | ${res#* } |"
}
{
    echo "| Check | Must (camera / trace) | Camera | Trace (plays_right) | Detail |"
    echo "|---|---|---|---|---|"
    for fx in e1-route hill-ashley bell-ganado square-follow door103-walk; do
        run odump $fx "$OUT/$fx/ref"
        run native $fx "$OUT/$fx/nat"
        row "$fx: native camera against the original" PASS PASS "$OUT/$fx/ref" "$OUT/$fx/nat"
    done
    run native e1-route "$OUT/e1-route/nat2"
    row "e1-route: native against itself (determinism, exact)" PASS PASS "$OUT/e1-route/nat" "$OUT/e1-route/nat2" exact
    for ex in camblend camrail; do
        run odump e1-route "$OUT/x-$ex/ref" RE4_SVC_EXERCISE=$ex
        run native e1-route "$OUT/x-$ex/nat" RE4_SVC_EXERCISE=$ex
        row "e1-route, exercise $ex: native against the original" PASS PASS "$OUT/x-$ex/ref" "$OUT/x-$ex/nat"
    done
    run native e1-route "$OUT/c-camsmooth" RE4_SVC_CONTROL=camsmooth
    row "control: smoothing off (e1-route)" FAIL FAIL "$OUT/e1-route/ref" "$OUT/c-camsmooth"
    run native e1-route "$OUT/c-caminterp" RE4_SVC_CONTROL=caminterp RE4_SVC_EXERCISE=camblend
    row "control: cut blend off (e1-route, exercise camblend)" FAIL FAIL "$OUT/x-camblend/ref" "$OUT/c-caminterp"
    run native e1-route "$OUT/c-camrail" RE4_SVC_CONTROL=camrail RE4_SVC_EXERCISE=camrail
    # CAMCHECK_RAIL_TRACE_MUST=FAIL is the script's own control (lane eng-e1o): the trace column is counted, so the run
    # must then end exit 1 with this row WRONG (before, the trace's exit was shown and not counted)
    row "control: rail parameter 0.25 further (e1-route, exercise camrail)" FAIL "${CAMCHECK_RAIL_TRACE_MUST:-PASS}" "$OUT/x-camrail/ref" "$OUT/c-camrail"
    # lane eng-e1n (H-017.1, .3): the push-object camera (exercise campush on the door walk: svc4_dump.cpp), the shoulder
    # camera's follow and the push camera's inverse as controls, the cut writer's refusal (exercise camexport)
    run odump door103-walk "$OUT/x-campush/ref" RE4_SVC_EXERCISE=campush
    run native door103-walk "$OUT/x-campush/nat" RE4_SVC_EXERCISE=campush
    row "door103-walk, exercise campush: native against the original" PASS PASS "$OUT/x-campush/ref" "$OUT/x-campush/nat"
    run native door103-walk "$OUT/c-caminv" RE4_SVC_CONTROL=caminv RE4_SVC_EXERCISE=campush
    row "control: the push camera's player-frame inverse skipped (door103-walk, exercise campush)" FAIL FAIL "$OUT/x-campush/ref" "$OUT/c-caminv"
    run native e1-route "$OUT/c-camfollow" RE4_SVC_CONTROL=camfollow
    row "control: the shoulder camera's follow rate 0.5 instead of 0.6 (e1-route)" FAIL FAIL "$OUT/e1-route/ref" "$OUT/c-camfollow"
    run odump e1-route "$OUT/x-camexport/ref" RE4_SVC_EXERCISE=camexport
    run native e1-route "$OUT/x-camexport/nat" RE4_SVC_EXERCISE=camexport
    xrow() {   # xrow <name> <must> <dir>: the camexport line: refused (nothing written, guards intact, the motion ended)
        local got=FAIL line
        line=$(grep -h "^# camexport" "$3/svc4.txt" 2>/dev/null)
        [ -n "$line" ] || { touch "$OUT/.abort"; line="(no camexport line)"; }
        echo "$line" | grep -q "buffer_untouched 1 guards_intact 1 motion_ended 1" && got=PASS
        local ok="$got (as it must)"
        [ "$got" = "$2" ] || { ok="$got (WRONG: must $2)"; touch "$OUT/.wrong"; }
        echo "| $1 | $2 / - | $ok | - | ${line#\# } |"
    }
    xrow "exercise camexport: the engine's writer refuses a 7-key cut before writing" PASS "$OUT/x-camexport/nat"
    xrow "control: the original writer on the same cut (odump)" FAIL "$OUT/x-camexport/ref"
    # lane eng-e1p (H-018.2): a refused export honoured through the whole chain (exercise camrefuse, native only): the
    # guarded buffer unchanged after the export, after the CameraMotion is made and after a move, the motion ended, for
    # an oversize cut, counts 0 and 27, and a stale valid 5-key table; control camlate (the refusal checked after the
    # header is read and the table relocated, the order before) must FAIL the stale case
    run native e1-route "$OUT/x-camrefuse/nat" RE4_SVC_EXERCISE=camrefuse
    run native e1-route "$OUT/c-camlate" RE4_SVC_CONTROL=camlate RE4_SVC_EXERCISE=camrefuse
    rrow() {   # rrow <name> <must> <dir> <case>
        local got=FAIL line
        line=$(grep -h "^# camrefuse: case $4 " "$3/svc4.txt" 2>/dev/null)
        [ -n "$line" ] || { touch "$OUT/.abort"; line="(no camrefuse line for $4)"; }
        echo "$line" | grep -q "after_export 1 after_construct 1 after_move 1 guards_intact 1 motion_ended 1$" && got=PASS
        local ok="$got (as it must)"
        [ "$got" = "$2" ] || { ok="$got (WRONG: must $2)"; touch "$OUT/.wrong"; }
        echo "| $1 | $2 / - | $ok | - | ${line#\# } |"
    }
    for c in oversize count0 count27 stale; do
        rrow "exercise camrefuse ($c): the refused buffer untouched by export, construction and a move" PASS "$OUT/x-camrefuse/nat" $c
    done
    rrow "control camlate: the refusal checked after the reads (stale table)" FAIL "$OUT/c-camlate" stale
} | tee "$OUT/camcheck.md"
status=0
[ -f "$OUT/.wrong" ] && status=1
[ -f "$OUT/.abort" ] && status=2
rm -f "$OUT/.wrong" "$OUT/.abort"
echo "camcheck: $([ $status -eq 0 ] && echo 'every row as it must' || echo "exit $status")"
exit $status
