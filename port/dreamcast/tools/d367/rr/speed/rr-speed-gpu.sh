#!/bin/bash
# rr-speed-gpu.sh <ref sha> <cand sha> <out file> [work dir]   (WSL; lane guards28, 2026-10-28)
# GPU row of the release-to-release speed gate (coordinator decision 10-28, after Test 24: n256 + strip groups cut the
# CPU MODELLED but sent ~10% more SQ->TA bytes, and the console ran slower). For each commit: its QA disc (rr-qa.sh with
# that commit's own recipe.conf, gdemu kept), then gpu-scene.sh on the five scenes (cross, bell, farm, house, r11c) on
# the cache-model Flycast, at most SPEED_PAR=2 scenes at once (one Flycast each), every run <= 60 s from load states.
# Judged by rr_speed_gpu.py (SPEED_GPU_TOL_PCT, default 5). The reference is measured once and cached by sha under
# $RR_HOME/speed/<sha8>/gpu (Windows-visible copy in SPEED_EV). Exit 0 PASS, 1 FAIL, 2 error.
set -euo pipefail
REF=${1:?ref sha}; CAND=${2:?cand sha}; OUT=${3:?out file}
RR_HOME=${RR_HOME:-/root/rr}
W=${4:-/root/probe/rr-speed}
HERE=$(cd "$(dirname "$0")" && pwd)
MAIN=${RR_MAIN:-/root/work/re4-dreamcast}
SCENES=${SPEED_SCENES:-cross bell farm house r11c}
PAR=${SPEED_PAR:-2}
EVB=${SPEED_EV:-/mnt/c/Flycast-Evidence/re4-dreamcast/rr-speed}
GITBASH=${GITBASH:-/mnt/c/Program Files/Git/bin/bash.exe}
R8=$(git -C "$MAIN" rev-parse "$REF" | cut -c1-8); C8=$(git -C "$MAIN" rev-parse "$CAND" | cut -c1-8)
EV=$EVB/gpu; mkdir -p "$W" "$EV"
qa() { # <sha8> <label>: QA disc -> $EV/disc-<label>/gdemu + syms
  local s=$1 x=$2 t=$W/tree-$2 qw=$W/qa-$2
  [ -s "$EV/disc-$x/gdemu/disc.gdi" ] && [ -s "$EV/disc-$x/syms.txt" ] && return 0
  if [ ! -d "$t" ]; then git -C "$MAIN" worktree prune; git -C "$MAIN" worktree add -q --detach "$t" "$s"; fi
  git -C "$t" submodule update -q --init --recursive
  mkdir -p "$qw"; git -C "$t" show HEAD:port/dreamcast/tools/d367/rr/recipe.conf | tr -d '\r' > "$qw/recipe.conf"
  RR_QA_KEEP_GDEMU=1 bash "$HERE/../rr-qa.sh" "$qw" "$t" "$(git -C "$t" rev-parse HEAD)" "speed$x" - > "$W/qa-$x.log" 2>&1 \
    || { tail -5 "$W/qa-$x.log"; return 1; }
  local s7; s7=$(git -C "$t" rev-parse HEAD | cut -c1-7)
  rm -rf "${EV:?}/disc-$x"; mkdir -p "$EV/disc-$x"
  cp -r "$qw/qa/gdemu" "$EV/disc-$x/gdemu"; rm -rf "${qw:?}/qa/gdemu"
  cp "/root/probe/lanes/route/out-rr${s7}qrW/syms.txt" "$EV/disc-$x/syms.txt"
  rm -rf "/root/probe/lanes/route/out-rr${s7:?}qrW"
  git -C "$MAIN" worktree remove -f "$t" || true
}
scenes() { # <label>
  local x=$1 sc pids=() n=0 gw
  gw=$(wslpath -w "$EV/disc-$x/gdemu")
  for sc in $SCENES; do
    [ -s "$EV/stats/$x-$sc-cstat.txt" ] && continue
    "$GITBASH" "//wsl.localhost/Ubuntu-24.04$HERE/gpu-scene.sh" "$gw" "/c/${EV#/mnt/c/}/disc-$x/syms.txt" "/c/${EV#/mnt/c/}" "$x" "$sc" \
      > "$W/gpu-$x-$sc.log" 2>&1 < /dev/null &
    pids+=($!); n=$((n + 1))
    if [ "$n" -ge "$PAR" ]; then wait "${pids[0]}" || true; pids=("${pids[@]:1}"); n=$((n - 1)); fi
  done
  for p in "${pids[@]}"; do wait "$p" || true; done
}
for pair in "$R8 g$R8" "$C8 g$C8"; do
  set -- $pair
  qa "$1" "$2" || { echo "SPEED-GPU FAIL: QA disc of $1 did not build" > "$OUT"; exit 2; }
  scenes "$2"
done
rc=0
python3 "$HERE/rr_speed_gpu.py" "$EV" "g$R8" "g$C8" --tol-pct "${SPEED_GPU_TOL_PCT:-5}" --scenes "${SCENES// /,}" > "$OUT" || rc=$?
cat "$OUT"
# the candidate's disc is rebuildable (the reference's is kept for the next cycle)
[ "${SPEED_GPU_KEEP_CAND:-0}" = 1 ] || rm -rf "${EV:?}/disc-g${C8:?}"
exit $rc
