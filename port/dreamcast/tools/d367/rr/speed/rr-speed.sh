#!/bin/bash
# rr-speed.sh <ref sha> <cand sha> <out file> [work dir]   (WSL; lane guards28, 2026-10-28)
# Release-to-release speed gate (OPT-TRACK "Release-to-release speed gate"; Test 24 shipped slower than Test 22 and
# nothing compared them). Builds each commit's own release recipe as a cost arm (rr-speed-build.sh), runs the five
# hwmodel benchmark scenes (cross, bell, farm, house, r11c; rr-speed-hw.sh, at most SPEED_PAR=2 Flycasts at once) and
# judges candidate vs reference with rr_speed.py (tolerance SPEED_TOL_MS=1.0 / SPEED_TOL_PCT=3). The reference
# (normally the live release, recipe.conf RR_SPEED_REF) is measured once and cached by sha in $SPEED_EV/ref-<sha8>.
# Writes the rr_speed.py table to <out file>; its last line is "SPEED PASS|FAIL ...". Exit 0 PASS, 1 FAIL, 2 error.
set -euo pipefail
REF=${1:?ref sha}; CAND=${2:?cand sha}; OUT=${3:?out file}
RR_HOME=${RR_HOME:-/root/rr}
W=${4:-/root/probe/rr-speed}
HERE=$(cd "$(dirname "$0")" && pwd)
MAIN=${RR_MAIN:-/root/work/re4-dreamcast}
SCENES=${SPEED_SCENES:-cross bell farm house r11c}
PAR=${SPEED_PAR:-2}
EVB=${SPEED_EV:-/mnt/c/Flycast-Evidence/re4-dreamcast/rr-speed}
R8=$(git -C "$MAIN" rev-parse "$REF" | cut -c1-8); C8=$(git -C "$MAIN" rev-parse "$CAND" | cut -c1-8)
mkdir -p "$W" "$RR_HOME/speed" "$EVB"
measure() { # <sha8> <label> <evidence dir>
  local s=$1 x=$2 ev=$3 sc pids=() n=0
  bash "$HERE/rr-speed-build.sh" "$s" "$x" "$W" || return 1
  mkdir -p "$ev"
  for sc in $SCENES; do
    [ -s "$ev/hwmodel-$x-$sc/proj/projection.txt" ] && continue
    rm -rf "${ev:?}/hwmodel-$x-$sc"
    bash "$HERE/rr-speed-hw.sh" "$x" "$sc" "$W" "$ev" > "$W/hw-$x-$sc.log" 2>&1 &
    pids+=($!); n=$((n + 1))
    if [ "$n" -ge "$PAR" ]; then wait "${pids[0]}" || true; pids=("${pids[@]:1}"); n=$((n - 1)); fi
  done
  for p in "${pids[@]}"; do wait "$p" || true; done
}
RD=$EVB/ref-$R8   # on C: (hwproject needs a Windows-visible evidence root); kept as the reference cache
if ! ls "$RD"/hwmodel-*-r11c/proj/projection.txt >/dev/null 2>&1; then measure "$R8" "sr$R8" "$RD" || { echo "SPEED FAIL: reference $R8 did not build" > "$OUT"; exit 2; }; fi
CD=$EVB/$C8
measure "$C8" "sc$C8" "$CD" || { echo "SPEED FAIL: candidate $C8 did not build" > "$OUT"; exit 2; }
rc=0
python3 "$HERE/rr_speed.py" "$RD" "$CD" --tol-ms "${SPEED_TOL_MS:-1.0}" --tol-pct "${SPEED_TOL_PCT:-3}" --scenes "${SCENES// /,}" > "$OUT" || rc=$?
cat "$OUT"
# the candidate's cost-arm objdir and tree are rebuildable: drop them (the reference cache keeps only its results)
rm -rf "/root/probe/lanes/route/out-sc${C8:?}rW" "${W:?}/k-sc$C8"
git -C "$MAIN" worktree remove -f "$W/tree-sc$C8" 2>/dev/null || true
exit $rc
