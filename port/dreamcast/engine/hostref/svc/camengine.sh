#!/bin/bash
# camengine.sh: the engine image's camera against the PC reference, tick by tick (lane eng-e1l; SERVICES.md 48).
#
#   RE4_TREE=<converted data tree> camengine.sh <out dir> <after serial.txt> [<before serial.txt>]
#
# The serial logs are Flycast (or console) runs of a test disc whose LEON, HILL and SHOT scenes ran traced (no NOTRACE
# file): each tick the image prints the camera service's record as a CAMLOG line (camengine.py). The reference is re4ref
# odump (the original camera units: camera, view, cam_sys, cam_ctrl, cam_qfps, cam_extra) on the scene's fixture:
#   LEON  tools/plays_right/fixtures/e1-route.txt with seed 0x0000 (the image's village route starts the generator at
#         0, as lane eng-e1g's village comparison did; written to <out>)
#   HILL  fixtures/hill-follow.txt (the image's hill scene: the same resume, 728 ticks; hill-ashley is another play)
#   SHOT  fixtures/shot-ganado.txt (the FIGHT image plays this file itself)
# camcheck.py compares every tick of the fixture: eye and target within max(0.01 unit, 2^-20 of the coordinate), roll and
# fov within 0.01 degree, the controller's decisions (area, cut, routine, blend frames left) equal (camcheck.sh's bound,
# stated before the run; CAM_POS, CAM_REL, CAM_DEG override).
# Rows:
#   PC: re4ref with ZNEAR / ZFAR zero (RE4_SVC_CONTROL=zclip0) against the reference as it is: where the game's near and
#       far distances reach the reference's camera (the shoulder camera's wall probe). Must (from the PC runs made
#       first, E:\RE4DC-Lanes\eng-e1l\ev\pc1): e1-route PASS (no effect), hill-follow FAIL (the probe meets the hill
#       from tick 1), shot-ganado PASS.
#   after: the image with the game's distances set, under camcheck's bound: must PASS (the goal).
#   before (when given: the lab arm ZCLIP0, the distances zero as every E1 image had them; its camera is the base
#       image's bit for bit): must FAIL on HILL (the control), PASS on LEON and SHOT if the image matched elsewhere.
#   nearer (when before is given): on every tick where before and after differ, after is at least as near the
#       reference (camnearer.py): must PASS on LEON and HILL; control: the arms swapped must FAIL.
# Lane eng-e1m: the reference swaps the routine bytes (hostref Makefile STAT_BYTES=1, as the image does). When the old
# reference is built (STAT_BYTES=0 in RE4_HOSTREF_GC_BUILD, default $ROOT/build/hostref-gc):
#   PC: the old reference against the reference: must FAIL on every scene (from tick 2: Leon's idle creep, which the
#       game's shoulder camera does not follow and the old reference did).
#   control: after against the old reference: must FAIL on every scene (the engine is not the old reference).
# When a control serial is given (4th argument: a run with the lab arm CAMEVERY, the shoulder camera handed Leon's
# matrix every tick as the old reference did), each of its scenes: engine against the reference must FAIL; engine
# against the old reference is reported (no must: the old reference also differs at the other routine-byte tests).
# The before arm's LEON row (ZCLIP0) must FAIL since this lane: with the game's distances zero the image's shoulder
# camera leaves the PC's at the village houses (tick 222; ev\z0 in the lane's evidence), where with them set it agrees.
# Exit 0 when every row is as it must, 1 when one is not, 2 when a run, a build or a scene is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
AFTER=${2:?after serial.txt}
BEFORE=${3:-}
CTRL=${4:-}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
GC=${RE4_HOSTREF_GC_BUILD:-$ROOT/build/hostref-gc}
PR=$ROOT/port/dreamcast/tools/plays_right
CC=$HERE/camcheck.py
CE=$HERE/camengine.py
[ -x "$B/odump/re4ref" ] || { echo "camengine: no odump build at $B/odump/re4ref (make odump)"; exit 2; }
for f in "$AFTER" ${BEFORE:+"$BEFORE"} ${CTRL:+"$CTRL"}; do [ -s "$f" ] || { echo "camengine: no serial log $f"; exit 2; }; done
mkdir -p "$OUT"
rm -f "$OUT/.wrong" "$OUT/.abort"
TOL="--pos ${CAM_POS:-0.01} --rel ${CAM_REL:-9.5367431640625e-07} --deg ${CAM_DEG:-0.01}"
sed 's/^seed .*/seed 0x0000/' "$PR/fixtures/e1-route.txt" > "$OUT/e1-route-s0.txt"
fixture() { case $1 in LEON) echo "$OUT/e1-route-s0.txt" ;; HILL) echo "$PR/fixtures/hill-follow.txt" ;; SHOT) echo "$PR/fixtures/shot-ganado.txt" ;; esac; }
run() {   # run <fixture file> <dir> [env...]   (RUN_BIN: another odump build)
    local fx=$1 d=$2
    shift 2
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_CLOTH_WIND=0 "$@" "${RUN_BIN:-$B/odump/re4ref}" --tree "$TREE" --fixture "$fx" --out "$d/trace.txt" \
        --log "$d/run.log" 2> "$d/err.txt" || { echo "camengine: run failed $d" >&2; touch "$OUT/.abort"; }
}
info() {   # info <name> <ref dir> <test dir>: a reported row, no must
    local res
    res=$(python3 "$CC" "$2" "$3" $TOL)
    echo "| $1 | - | ${res%% *} (reported) | ${res#* } |"
}
row() {   # row <name> <must> <ref dir> <test dir>
    local name=$1 must=$2 a=$3 b=$4 res got
    res=$(python3 "$CC" "$a" "$b" $TOL --json "$b/cam.json")
    case $? in 0) got=PASS ;; 1) got=FAIL ;; *) got=ERROR; touch "$OUT/.abort" ;; esac
    local ok="$got (as it must)"
    [ "$got" = "$must" ] || { ok="$got (WRONG: must $must)"; touch "$OUT/.wrong"; }
    echo "| $name | $must | $ok | ${res#* } |"
}
nearer() {   # nearer <name> <must> <ref dir> <A dir> <B dir>
    local name=$1 must=$2 res got
    res=$(python3 "$HERE/camnearer.py" "$3" "$4" "$5")
    case $? in 0) got=PASS ;; 1) got=FAIL ;; *) got=ERROR; touch "$OUT/.abort" ;; esac
    local ok="$got (as it must)"
    [ "$got" = "$must" ] || { ok="$got (WRONG: must $must)"; touch "$OUT/.wrong"; }
    echo "| $name | $must | $ok | ${res#* } |"
}
engine() {   # engine <arm> <serial> <scene> <must>
    local arm=$1 serial=$2 sc=$3 must=$4 d="$OUT/$1/$3"
    if ! python3 "$CE" "$serial" "$sc" "$OUT/ref/$sc" "$d" > "$OUT/$arm-$sc.camengine.txt" 2>&1; then
        touch "$OUT/.abort"
        echo "| $arm $sc: engine against the reference | $must | ERROR | $(tail -1 "$OUT/$arm-$sc.camengine.txt") |"
        return
    fi
    row "$arm $sc: engine (Flycast) against the reference" "$must" "$OUT/ref/$sc" "$d"
}
{
    echo "| Check | Must | Camera | Detail |"
    echo "|---|---|---|---|"
    for sc in LEON HILL SHOT; do
        run "$(fixture $sc)" "$OUT/ref/$sc"
        run "$(fixture $sc)" "$OUT/pc-zclip0/$sc" RE4_SVC_CONTROL=zclip0
    done
    row "PC: e1-route (seed 0), ZNEAR / ZFAR zero against the reference" PASS "$OUT/ref/LEON" "$OUT/pc-zclip0/LEON"
    row "PC: hill-follow, ZNEAR / ZFAR zero against the reference" FAIL "$OUT/ref/HILL" "$OUT/pc-zclip0/HILL"
    row "PC: shot-ganado, ZNEAR / ZFAR zero against the reference" PASS "$OUT/ref/SHOT" "$OUT/pc-zclip0/SHOT"
    for sc in LEON HILL SHOT; do engine after "$AFTER" $sc PASS; done
    if [ -x "$GC/odump/re4ref" ]; then
        for sc in LEON HILL SHOT; do
            RUN_BIN="$GC/odump/re4ref" run "$(fixture $sc)" "$OUT/oldref/$sc"
            row "PC: $sc the old reference (routine bytes unswapped) against the reference" FAIL "$OUT/ref/$sc" "$OUT/oldref/$sc"
            row "control: after $sc against the old reference" FAIL "$OUT/oldref/$sc" "$OUT/after/$sc"
        done
    else
        echo "| (no old reference build at $GC: its rows not run) | - | - | - |"
    fi
    if [ -n "$CTRL" ]; then
        for sc in LEON HILL SHOT; do
            # only the control serial's scenes that ran the arm (their log says "E1 CAMEVERY")
            awk -v s="$sc" '$0 ~ "^CDISC RUN [0-9]+ " s " " {on = 1; next} $0 ~ "^CDISC RESULT [0-9]+ " s " " {on = 0}
                on && /E1 CAMEVERY/ {f = 1} END {exit !f}' "$CTRL" || continue
            python3 "$CE" "$CTRL" "$sc" "$OUT/ref/$sc" "$OUT/ctrl/$sc" > "$OUT/ctrl-$sc.camengine.txt" 2>&1 || continue
            row "control CAMEVERY $sc: engine (Flycast) against the reference" FAIL "$OUT/ref/$sc" "$OUT/ctrl/$sc"
            [ -d "$OUT/oldref/$sc" ] && info "control CAMEVERY $sc: engine against the old reference" "$OUT/oldref/$sc" "$OUT/ctrl/$sc"
        done
    fi
    if [ -n "$BEFORE" ]; then
        engine before "$BEFORE" LEON FAIL
        engine before "$BEFORE" HILL FAIL
        engine before "$BEFORE" SHOT PASS
        for sc in LEON HILL; do
            nearer "$sc: after nearer the reference than before wherever they differ" PASS "$OUT/ref/$sc" "$OUT/before/$sc" "$OUT/after/$sc"
            nearer "control: $sc arms swapped (before nearer than after)" FAIL "$OUT/ref/$sc" "$OUT/after/$sc" "$OUT/before/$sc"
        done
    fi
} | tee "$OUT/camengine.md"
status=0
[ -f "$OUT/.wrong" ] && status=1
[ -f "$OUT/.abort" ] && status=2
rm -f "$OUT/.wrong" "$OUT/.abort"
echo "camengine: $([ $status -eq 0 ] && echo 'every row as it must' || echo "exit $status")"
exit $status
