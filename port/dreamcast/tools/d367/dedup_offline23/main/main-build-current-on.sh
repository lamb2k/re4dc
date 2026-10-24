#!/bin/bash
set -euo pipefail
TR=/root/work/lanes/dedup-offline23-next
SCR=/root/work/lanes/dedup-offline23-next-main
SHA=daabb0dba96e55a047fda9135e5fb9aad91d1c4f
T=$TR/port/dreamcast/tools/d367
O=/root/probe/lanes/route/out-dd23daabnowrW
[ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
[ ! -e "$O" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 26843545600 ]
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
mkdir -p "$SCR/on-k"
exec 9>"$SCR/tree.lock";flock -n 9
exec > >(tee "$SCR/on-build.log") 2>&1
export JOBS=1 SOURCE_DATE_EPOCH=1760000000
. "$T/rr/recipe.conf"
K="$SCR/on-k" T="$TR" LP=dd23daabnow CH2="$CH2" \
 XON='SCENERY_DEDUP=3 SCENERY_REPLAY_LEAN=0 QA_MENU=1 WARP_AFTER_RESET=1 WORLD_METER=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23-DD3 QA_SRC=daabb0db' \
 bash "$T/ch2/ch2-build.sh" rW
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
printf 'CURRENT_TARGET_LINK_COMPLETE source=%s\n' "$SHA"
