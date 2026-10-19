#!/bin/bash
# scenario19/build.sh  (WSL; lane scenario19, 2026-10-19): the programs for scenario discs.
#   <LP>rP  the Test 19 release recipe (T15REC from test15/t15-build.sh + CH2REC from ch2/ch2-build.sh + the Test 18
#           release knobs + ROUTE_SOON_KEY), i.e. what the Test 19 candidate would be at this tree's HEAD.
#   <LP>sP  the scenario disc program: <LP>rP + DBG_WARP=1 (the warp rig reads /cd/dc/warp.txt and starts the scenario;
#           nothing else changes: no PC sampler, no traces, controller and VMU as in play).
#   <LP>sC  the check twin: <LP>sP + the CAST-GC census, TEX_CHECK=2, MCHECK_LEONGC and KOS_WATCH/KOS_SQUEEZE (never shipped).
# Env: T tree (default this checkout), LP label prefix (default s19), K logs dir. Outputs /root/probe/lanes/route/out-<label>.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export T=${T:-$(cd "$HERE/../../../../.." && pwd)}
export K=${K:-/root/work/lanes/scenario19-scratch/k}
LP=${LP:-s19}
mkdir -p "$K" "$K/programs"
# Never touch the shared harness program registry from this lane.
export ROUTE_PROGRAMS_DIR=$K/programs ROUTE_PROGRAMS_JSON=
PE=/root/re4data/private/ps2enemy-ch2-20261016
eval "$(grep '^CH2REC=' "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh")"
T18="ROUTE_SOON_RETURN=1 MOVIE_AUDIO_PRIME=1 ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1 LEON_SKIN_SLOTS=2 LEON_HEADLESS=1 LEON_HEADLESS_DIR=/root/re4data/private/garr18-head-20261019 LEON_CLOTH_DRAWN=1 HAZE_SPRITE_CUT=1 FX_MIST_PS2=1 PS2_HDR_SETS=128 ROUTE_SOON_KEY=1"
if [ "${SKIP_RP:-0}" != 1 ]; then
  LP=$LP CH2="$CH2REC $T18" XON="" bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" rP | cut -c1-160
fi
O=/root/probe/lanes/route/out-${LP}rP
[ -s "$O/re4dc-game.elf" ] || { echo "no $O" >&2; exit 1; }
RP=$(sed 's/^.*PC_SAMPLER=1 //' "$O/candidate.txt")
TOOL=/opt/toolchains/dc/sh-elf/bin
b() { local lab=$1; shift
  (cd "$T" && TREE=$T bash /root/probe/d367-buildslot.sh bash port/dreamcast/tools/d367/route/route-build.sh "$lab" "$@") >> "$K/logs-build.txt" 2>&1
  local o=/root/probe/lanes/route/out-$lab
  rm -rf "${K:?}/programs/candidate-route$lab"
  $TOOL/sh-elf-objcopy -R .stack -O binary "$o/re4dc-game.elf" "$K/img-$lab.bin"
  echo "$lab elf=$(cut -c1-16 "$o/elf.sha256") image=$(sha256sum < "$K/img-$lab.bin" | cut -c1-8) missing=$(wc -c < "$o/missing.txt")"
  rm -f "$K/img-$lab.bin"; }
$TOOL/sh-elf-objcopy -R .stack -O binary "$O/re4dc-game.elf" "$K/img-rP.bin"
echo "${LP}rP image=$(sha256sum < "$K/img-rP.bin" | cut -c1-8)"; rm -f "$K/img-rP.bin"
b ${LP}sP $RP DBG_WARP=1
b ${LP}sC $RP DBG_WARP=1 MCHECK_LEONGC=1 TEX_CHECK=2 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 KOS_WATCH=1 KOS_SQUEEZE=1
echo SCENARIO BUILDS DONE
