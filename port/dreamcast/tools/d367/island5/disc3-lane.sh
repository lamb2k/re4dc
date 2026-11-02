#!/bin/bash
# disc3-lane.sh <rr work dir of a packaged candidate> <lane home> [tree]  (WSL; lane world-ch5, 2026-11-02)
# Builds the Disc 3 arm outside an rr cycle, read-only against the rr candidate: a private work dir under <lane home>
# gets this tree's recipe.conf, the candidate's cycle.env and a private candidate dir whose gdemu/track03.bin is a
# symlink to the rr candidate's Disc 1 track (never written). rr-disc3.sh then writes <lane home>/cand/disc3/gdemu.
# D3_NO_TWINS=1 (default here): the disc only, no Flycast twins / bases.
set -euo pipefail
RW=${1:?rr work dir}; LH=${2:?lane home}
T=${3:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
S8=$(sed -n 's/^sha=//p' "$RW/cycle.env" | cut -c1-8); S7=${S8:0:7}
RC=$(cat "$RW/cand.txt"); [ -s "$RC/gdemu/track03.bin" ] || { echo "disc3-lane: no Disc 1 track in $RC"; exit 1; }
W=$LH/work/d3-$S7; C=$LH/cand-$S7
rm -rf "${W:?}" "${C:?}"; mkdir -p "$W" "$C/gdemu"
ln -s "$RC/gdemu/track03.bin" "$C/gdemu/track03.bin"
cp "$RW/cycle.env" "$W/cycle.env"; echo "$C" > "$W/cand.txt"
cp "$T/port/dreamcast/tools/d367/rr/recipe.conf" "$W/recipe.conf"
export RR_PFX=${RR_PFX:-wc5}
D3_NO_TWINS=${D3_NO_TWINS:-1} bash "$T/port/dreamcast/tools/d367/rr/rr-disc3.sh" "$W" "$T" "$T" "$S7" "${EVU:-/mnt/c/Flycast-Evidence/re4-dreamcast/world-ch5}"
cat "$W/disc3.env"
