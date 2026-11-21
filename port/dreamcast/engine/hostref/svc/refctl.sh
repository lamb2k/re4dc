#!/bin/bash
# refctl.sh: the PC reference's three changes of 2026-11-21, each against its old behaviour kept as a build of its own
# (lane eng-e1o, HANDOVERS.md H-017.8: "each reference change keeps its old behaviour as a switchable build and a row
# that is run").
#
#   RE4_TREE=<converted data tree> refctl.sh <out dir>
#
# The fixed reference is the hostref build in RE4_HOSTREF_BUILD (default $ROOT/build/hostref: plain and odump, made
# here when missing). Each old reference is built by this script in a folder of its own (REFCTL_BUILD, default
# $ROOT/build/hostref-ctl-<name>), run, judged, then deleted (REFCTL_KEEP=1 keeps them), one at a time:
#   em10      EM10_SPLIT=0: em10's 13 presentation callers on the behaviour generator (before lane eng-e1k). On
#             shot-ganado (plain build): the generator calls agree up to tick 135, where the old reference makes two more
#             (the Ganado's voice timer; stated by lane eng-e1k) [refctl.py draws]; and the outcome differs: outcome.py
#             with the fixed reference as A must FAIL.
#   bspline   BSPLINE_ALIAS=i386: cam_ctrl's BSpline through the floats-first alias as it is (before lane eng-e1j). On
#             e1-route with the camrail exercise (odump build): the old rail stays at its first key [refctl.py rail:
#             STUCK], the fixed one moves [MOVES], and camcheck.py fixed against old must FAIL.
#   stat      STAT_BYTES=0: the routine bytes read unswapped (before lane eng-e1m). On e1-route (seed 0), hill-follow and
#             shot-ganado (odump build): camcheck.py fixed against old must FAIL on each (from tick 2, 2 and 3: Leon's
#             idle creep the old reference's shoulder camera followed).
# Positive rows: the fixed reference against itself on each fixture (exact) must PASS, so a FAIL above is the change.
# A row that cannot be run (a build or a run that fails, a trace missing) is ERROR, never skipped. Exit 0 when every row
# is as it must, 1 when one is not, 2 when one could not be run.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
HREF=$(cd "$HERE/.." && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)
OUT=${1:?out dir}
TREE=${RE4_TREE:?set RE4_TREE to the converted data tree (private game data)}
B=${RE4_HOSTREF_BUILD:-$ROOT/build/hostref}
CTLB=${REFCTL_BUILD:-$ROOT/build/hostref-ctl}
J=${REFCTL_J:-3}
PR=$ROOT/port/dreamcast/tools/plays_right
CC=$HERE/camcheck.py
RC=$HERE/refctl.py
mkdir -p "$OUT"
rm -f "$OUT/.wrong" "$OUT/.abort"
TOL="--pos ${CAM_POS:-0.01} --rel ${CAM_REL:-9.5367431640625e-07} --deg ${CAM_DEG:-0.01}"
build() {   # build <dir> <target> [switches]: make the hostref target into <dir>; 0 when the binary is there
    local d=$1 t=$2
    shift 2
    [ -x "$d/$t/re4ref" ] && return 0
    make -C "$HREF" -j"$J" BUILD="$d" "$@" "$([ "$t" = plain ] && echo all || echo "$t")" > "$OUT/make-$(basename "$d")-$t.log" 2>&1
    [ -x "$d/$t/re4ref" ] || { echo "refctl: build failed: $d $t $* (see $OUT/make-$(basename "$d")-$t.log)" >&2; return 1; }
}
run() {   # run <binary> <fixture file> <dir> [env...]
    local bin=$1 fx=$2 d=$3
    shift 3
    mkdir -p "$d"
    env RE4_SVC_OUT="$d" RE4_SVC_CLOTH_WIND=0 "$@" "$bin" --tree "$TREE" --fixture "$fx" --out "$d/trace.txt" \
        --log "$d/run.log" 2> "$d/err.txt" && [ -s "$d/trace.txt" ] || { echo "refctl: run failed $d" >&2; return 1; }
}
row() {   # row <name> <must> <got> <detail>
    local ok="$3 (as it must)"
    case $3 in PASS|FAIL|STUCK|MOVES) [ "$3" = "$2" ] || { ok="$3 (WRONG: must $2)"; touch "$OUT/.wrong"; } ;;
               *) ok="ERROR (could not be run)"; touch "$OUT/.abort" ;; esac
    echo "| $1 | $2 | $ok | $4 |"
}
verdict() { case $1 in 0) echo "$2" ;; 1) echo "$3" ;; *) echo ERROR ;; esac; }
camrow() {   # camrow <name> <must> <ref dir> <test dir> [exact]
    local res rc
    if [ "${5:-}" = exact ]; then res=$(python3 "$CC" "$3" "$4" --pos 0 --rel 0 --deg 0); else res=$(python3 "$CC" "$3" "$4" $TOL); fi
    rc=$?
    row "$1" "$2" "$(verdict $rc PASS FAIL)" "${res#* }"
}
gone() { [ "${REFCTL_KEEP:-0}" = 1 ] || rm -rf -- "$1"; }
sed 's/^seed .*/seed 0x0000/' "$PR/fixtures/e1-route.txt" > "$OUT/e1-route-s0.txt"
SHOTFX=$PR/fixtures/shot-ganado.txt
SHOTTICKS=$(awk '$1 == "ticks" {print $2; exit}' "$SHOTFX")
{
    echo "| Check | Must | Got | Detail |"
    echo "|---|---|---|---|"
    if ! build "$B" plain || ! build "$B" odump; then
        row "the fixed reference (plain, odump) at $B" PASS ERROR "build failed"
    else
        # ---- em10: the presentation callers unsplit
        D=$OUT/em10
        okr=1
        run "$B/plain/re4ref" "$SHOTFX" "$D/ref" || okr=0
        run "$B/plain/re4ref" "$SHOTFX" "$D/ref2" || okr=0
        if [ $okr = 1 ]; then
            python3 "$PR/outcome.py" "$D/ref/trace.txt" "$D/ref2/trace.txt" --expect-ticks 0:"$SHOTTICKS" \
                --tolerances "$PR/tolerances.json" > "$D/self-outcome.txt" 2>&1; rc=$?
            res=$(grep -E '^(PASS|FAIL)' "$D/self-outcome.txt" | head -1)
            row "shot-ganado: the fixed reference against itself (outcome)" PASS "$(verdict $rc PASS FAIL)" "$(echo "$res" | head -1)"
        else
            row "shot-ganado: the fixed reference against itself (outcome)" PASS ERROR "run failed"
        fi
        if build "$CTLB-em10" plain EM10_SPLIT=0 && run "$CTLB-em10/plain/re4ref" "$SHOTFX" "$D/old" && [ $okr = 1 ]; then
            res=$(python3 "$RC" draws "$D/ref/trace.txt" "$D/old/trace.txt" --tick 135 --extra 2); rc=$?
            row "em10 unsplit (EM10_SPLIT=0), shot-ganado: two more behaviour draws at tick 135" PASS "$(verdict $rc PASS FAIL)" "${res#* }"
            python3 "$PR/outcome.py" "$D/ref/trace.txt" "$D/old/trace.txt" --expect-ticks 0:"$SHOTTICKS" \
                --tolerances "$PR/tolerances.json" --json "$D/outcome.json" > "$D/outcome.txt" 2>&1; rc=$?
            row "em10 unsplit, shot-ganado: outcome against the fixed reference" FAIL "$(verdict $rc PASS FAIL)" \
                "$(python3 -c "import json,sys;j=json.load(open(sys.argv[1]));p=j['problems'];print('kinds %s; first [%s] tick %s %s %s'%(j.get('problem_kinds'),p[0]['kind'],p[0]['tick'],p[0]['what'],p[0]['detail']) if p else 'no problem')" "$D/outcome.json" 2>/dev/null || echo 'no outcome report')"
        else
            row "em10 unsplit (EM10_SPLIT=0), shot-ganado: two more behaviour draws at tick 135" PASS ERROR "build or run failed"
            row "em10 unsplit, shot-ganado: outcome against the fixed reference" FAIL ERROR "build or run failed"
        fi
        gone "$CTLB-em10"
        # ---- bspline: the i386 floats-first alias
        D=$OUT/bspline
        if run "$B/odump/re4ref" "$OUT/e1-route-s0.txt" "$D/ref" RE4_SVC_EXERCISE=camrail; then
            res=$(python3 "$RC" rail "$D/ref"); rc=$?
            row "the fixed reference, e1-route exercise camrail: the rail moves" MOVES "$(case $rc in 0) echo STUCK;; 1) echo MOVES;; *) echo ERROR;; esac)" "${res#* }"
        else
            row "the fixed reference, e1-route exercise camrail: the rail moves" MOVES ERROR "run failed"
        fi
        if build "$CTLB-bspline" odump BSPLINE_ALIAS=i386 && run "$CTLB-bspline/odump/re4ref" "$OUT/e1-route-s0.txt" "$D/old" RE4_SVC_EXERCISE=camrail; then
            res=$(python3 "$RC" rail "$D/old"); rc=$?
            row "BSpline i386 alias (BSPLINE_ALIAS=i386), camrail: the rail stuck at its first key" STUCK "$(case $rc in 0) echo STUCK;; 1) echo MOVES;; *) echo ERROR;; esac)" "${res#* }"
            camrow "BSpline i386 alias, camrail: camera against the fixed reference" FAIL "$D/ref" "$D/old"
        else
            row "BSpline i386 alias (BSPLINE_ALIAS=i386), camrail: the rail stuck at its first key" STUCK ERROR "build or run failed"
            row "BSpline i386 alias, camrail: camera against the fixed reference" FAIL ERROR "build or run failed"
        fi
        gone "$CTLB-bspline"
        # ---- stat: the routine bytes unswapped
        D=$OUT/stat
        if build "$CTLB-stat" odump STAT_BYTES=0; then
            for fx in e1-route-s0 hill-follow shot-ganado; do
                f=$PR/fixtures/$fx.txt; [ $fx = e1-route-s0 ] && f=$OUT/e1-route-s0.txt
                if run "$B/odump/re4ref" "$f" "$D/$fx/ref" && run "$B/odump/re4ref" "$f" "$D/$fx/ref2" &&
                   run "$CTLB-stat/odump/re4ref" "$f" "$D/$fx/old"; then
                    camrow "$fx: the fixed reference against itself (camera, exact)" PASS "$D/$fx/ref" "$D/$fx/ref2" exact
                    camrow "routine bytes unswapped (STAT_BYTES=0), $fx: camera against the fixed reference" FAIL "$D/$fx/ref" "$D/$fx/old"
                else
                    row "routine bytes unswapped (STAT_BYTES=0), $fx" FAIL ERROR "run failed"
                fi
            done
        else
            row "routine bytes unswapped (STAT_BYTES=0)" FAIL ERROR "build failed"
        fi
        gone "$CTLB-stat"
    fi
} | tee "$OUT/refctl.md"
status=0
[ -f "$OUT/.wrong" ] && status=1
[ -f "$OUT/.abort" ] && status=2
rm -f "$OUT/.wrong" "$OUT/.abort"
echo "refctl: $([ $status -eq 0 ] && echo 'every row as it must' || echo "exit $status")"
exit $status
