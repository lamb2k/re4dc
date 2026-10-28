#!/bin/bash
# scn-disc.sh <program label> <out dir>  (WSL; lane lake20 2026-10-20, after scenario19/disc.sh): the lake QA scenario disc.
# The current release data (rr/recipe.conf DATA on the payload base) with this program and its own overlays, plus under /dc/:
#   warp.txt, bench2.txt .. bench5.txt   the start points (scenario/scene<k>-warp.txt; no `bench` lines: free play)
#   quality.txt                          speed=screen (the speed display on from boot)
# Standard GD-ROM layout (mkgdi.sh LAYOUT=standard). Output <out dir>/gdemu + gdemu-sha256.txt, on ext4.
set -euo pipefail
LAB=${1:?program label}; D=${2:?out dir}
HERE=$(cd "$(dirname "$0")" && pwd)
T=$HERE/..
O=/root/probe/lanes/route/out-$LAB
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
export RE4DC_PROGRAMS_DIR=$HW/programs RC19D=${RC19D:-/root/re4data/private/rc19s-20261019}
eval "$(grep '^DATA=' "$T/rr/recipe.conf")"
[ -s "$O/re4dc-game.elf" ] || { echo "no build $O" >&2; exit 1; }
[ ! -s "$O/missing.txt" ] || { echo "$LAB has missing symbols" >&2; exit 1; }
grep -q 'BENCH_SCENARIO=1' "$O/candidate.txt" || { echo "$LAB is not a BENCH_SCENARIO=1 program" >&2; exit 1; }
case "$D" in /root/work/lanes/*) ;; *) echo "out dir must be under /root/work/lanes" >&2; exit 1;; esac
rm -rf "${D:?}"; mkdir -p "$D/fix" "$D/harness/programs/candidate-route$LAB"
for o in "$O"/*.ovl; do ln "$o" "$D/harness/programs/candidate-route$LAB/"; done
RE4DC_HARNESS=$D/harness python3 "$T/test11/t11-fix.py" "$LAB" "$D/pkg.json" --base payload --data "$DATA" > "$D/fix.log"
PKG_K=$D python3 "$T/test8/t8-pkgtree.py" "$LAB" "$D/pkg.json" > "$D/pkgtree.txt"
tail -1 "$D/pkgtree.txt" | grep -q PKGTREE_OK || { echo "pkgtree check failed"; tail -20 "$D/pkgtree.txt"; exit 1; }
for o in "$O"/*.ovl; do cmp -s "$o" "$D/pkgtree/dc/$(basename "$o")" || { echo "overlay mismatch $(basename "$o")" >&2; exit 1; }; done
n=0
for k in 1 2 3 4 5; do
  f=$HERE/scenario/scene$k-warp.txt; [ -s "$f" ] || break
  dst=$D/fix/bench$k.txt; [ $k = 1 ] && dst=$D/fix/warp.txt
  tr -d '\r' < "$f" | grep -v '^#' > "$dst"
  [ "$(stat -c %s "$dst")" -lt 2048 ] || { echo "$f too long" >&2; exit 1; }
  n=$k
done
printf 'speed=screen\n' > "$D/fix/quality.txt"
# QA_LINK=1 programs (lane link28 10-28): the remote link dials on its own (game/qa_link_bench.cpp); inert otherwise
echo 'auto 1' > "$D/fix/link.txt"
echo "scenes $n"
(cd "$T" && LAYOUT=standard TITLE="RE4DC LAKE SCENARIO (NOT THE GAME)" PRODUCT=T0020 bash mkgdi.sh "$O/re4dc-game.elf" "$D/pkgtree" "$D/gdemu" "$D/fix" | tail -2)
rm -f "$D/gdemu/IP.BIN"
(cd "$D/gdemu" && sha256sum disc.gdi track01.bin track02.raw track03.bin) > "$D/gdemu-sha256.txt"
rm -rf "${D:?}/pkgtree" "${D:?}/harness"
cat "$D/gdemu-sha256.txt"
echo "DISC $D/gdemu"
