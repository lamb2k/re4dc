#!/bin/bash
# sched_check.sh (lane eng-sched1): the game's script scheduler on the engine's lifted OS layer against the reference
# OS rules, on the PC. Plan 3.3 section 8 B2; docs/engine/lanes/eng-sched1.md.
#
#   sched_check.sh <out dir> [ticks]
#
# Builds (svc/sched/build.sh) two programs from the original units unchanged, src/game/scheduler.cpp,
# src/game/sce_sys.cpp and the village room script src/st1/r101.cpp: sched_ref over the GameCube OS rules
# (svc/sched/gc_os.cpp) with libgpu.cpp's list, sched_nat over the engine's lifted layer (engine/core/os_threads.cpp)
# on KOS's thread rules (svc/sched/kos_pc.cpp) with the engine's list (engine/services/scene/at_list.cpp). Each runs
# the room's start and <ticks> ticks (600) in the original's order and writes its task steps, the script's calls
# into the rest of the game and the final state; svc/sched/sched_compare.py compares each row with the reference.
#   rows (must PASS)   nat          the engine's layer, main thread at the engine's priority (KOS default 10)
#                      nat-prio16   main thread at 16, as the old port set it (tasks outrank the main thread)
#                      nat-jit7     KOS's timer pre-emption modelled (seed 7): the running thread now and then sent
#                                   to the back of its priority at interrupt restores and stub calls
#                      nat-jit91    the same, seed 91
#   controls (must FAIL) nowait     TaskSleep returns at once (a task polling on it never hands back)
#                      reverse      each new task linked at the tail of its ordering bucket (the tasks run reversed)
#                      ref-reverse  the same control on the reference layer
#   self (named, the reference against itself, must PASS: the comparison is deterministic)
# Exit 0 when every row ends as it must, 1 when one does not, 2 when a build or a run is missing.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:?out dir}
TICKS=${2:-600}
mkdir -p "$OUT"
B=$OUT/build
bash "$HERE/sched/build.sh" "$B" > "$OUT/build.log" 2>&1 || { echo "sched_check: build failed ($OUT/build.log)"; tail -5 "$OUT/build.log"; exit 2; }
CMP="python3 $HERE/sched/sched_compare.py"
MD=$OUT/sched_check.md
echo "| row | must | task steps / stub calls / final state | result |" > "$MD"
echo "|---|---|---|---|" >> "$MD"
timeout 120 env -u SCHED_CTL "$B/sched_ref" "$TICKS" "$OUT/ref.txt" 2> "$OUT/ref.err" || { echo "sched_check: reference run failed"; exit 2; }
bad=0
row() {   # row <name> <must> <reason a FAIL must show (grep -E on the comparison), or -> <program> [env...]
    local name=$1 must=$2 reason=$3 prog=$4
    shift 4
    timeout 120 env "$@" "$B/$prog" "$TICKS" "$OUT/$name.txt" 2> "$OUT/$name.err"
    local rc=$?
    $CMP "$OUT/ref.txt" "$B/sched_ref" "$OUT/$name.txt" "$B/$prog" > "$OUT/$name.cmp" 2>&1
    local res
    res=$(tail -1 "$OUT/$name.cmp")
    [ "$res" = PASS ] || res=FAIL
    local ok=WRONG
    [ "$res" = "$must" ] && ok=ok
    # a comparison that ended in an error is never a result; a control must fail for its own reason
    grep -q "^Traceback" "$OUT/$name.cmp" && ok=WRONG
    [ "$must" = FAIL ] && [ "$reason" != - ] && ! grep -qE "$reason" "$OUT/$name.cmp" && ok=WRONG
    [ $ok = ok ] || bad=1
    local why
    why=$(grep -E "^(task steps|stub calls|final state)" "$OUT/$name.cmp" | sed 's/  */ /g' | paste -sd ';' | cut -c1-300)
    grep -q "did not finish" "$OUT/$name.cmp" && why="$why; $(grep 'did not finish' "$OUT/$name.cmp" | head -1 | cut -c1-160)"
    why="$why; $(grep -h '^# os' "$OUT/$name.txt" | cut -c3-)"
    echo "| $name (rc $rc) | $must | $why | $res $ok |" >> "$MD"
    echo "sched_check: $name must $must: $res ($ok)"
}
row self PASS - sched_ref
row nat PASS - sched_nat
row nat-prio16 PASS - sched_nat SCHED_MAIN_PRIO=16
row nat-jit7 PASS - sched_nat SCHED_KOS_JITTER=7
row nat-jit91 PASS - sched_nat SCHED_KOS_JITTER=91
row nowait FAIL 'did not finish: STUCK' sched_nat SCHED_CTL=nowait
row reverse FAIL '^task steps.*DIFFER' sched_nat SCHED_CTL=reverse
row ref-reverse FAIL '^task steps.*DIFFER' sched_ref SCHED_CTL=reverse
grep -h "^tasks" "$OUT/nat.cmp" | head -1 >> "$MD"
grep -h "^engine diagnostics" "$OUT/nat.cmp" | head -1 >> "$MD"
echo "stubs: $(wc -l < "$B/undef.txt") generated ($(grep -c . "$B/stubs_int.txt") int-returning: $B/stubs_int.txt)" >> "$MD"
cat "$MD"
exit $bad
