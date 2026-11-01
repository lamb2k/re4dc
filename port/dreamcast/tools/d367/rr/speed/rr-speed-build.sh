#!/bin/bash
# rr-speed-build.sh <sha> <label> <work dir>   (WSL; lane guards28, 2026-10-28)
# The speed gate's cost arm of one build: that commit's OWN release recipe (its rr/recipe.conf CH2 + its T15REC) as a
# warp arm (rW) with PACE_MODE=off PC_SAMPLER_BYTES=8192 (every tick draws, so hw ms per frame = CPU per drawn frame),
# the perf-24b method. Detached worktree <work>/tree-<label>; ELF in /root/probe/lanes/route/out-<label>rW.
# Writes <work>/<label>.data (its disc data line) and <work>/<label>.env (the private data dirs its recipe.conf exports).
set -euo pipefail
SHA=${1:?sha}; X=${2:?label}; W=${3:?work dir}
MAIN=${RR_MAIN:-/root/work/re4-dreamcast}
T=$W/tree-$X
mkdir -p "$W"
if [ ! -d "$T" ]; then git -C "$MAIN" worktree prune; git -C "$MAIN" worktree add -q --detach "$T" "$SHA"; fi
git -C "$T" checkout -q -f --detach "$SHA"
git -C "$T" submodule update -q --init --recursive
[ "$(git -C "$T" rev-parse HEAD)" = "$(git -C "$MAIN" rev-parse "$SHA")" ]
before=$(env | sort)
# shellcheck source=/dev/null
. "$T/port/dreamcast/tools/d367/rr/recipe.conf"
echo "$DATA" > "$W/$X.data"
comm -13 <(echo "$before") <(env | sort) | grep -E '^[A-Z0-9_]+=/' > "$W/$X.env" || true
export SOURCE_DATE_EPOCH=1760000000
K=$W/k-$X T=$T LP=$X CH2="$CH2" XON="PACE_MODE=off PC_SAMPLER_BYTES=8192" \
  bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" rW 2>&1 | tail -3
E=/root/probe/lanes/route/out-${X}rW/re4dc-game.elf
[ -s "$E" ] || { echo "rr-speed-build: no ELF for $X"; exit 1; }
[ ! -s "/root/probe/lanes/route/out-${X}rW/missing.txt" ] || { echo "rr-speed-build: missing.txt not empty for $X"; exit 1; }
echo "built $X $SHA elf $(sha256sum "$E" | cut -c1-16)"
