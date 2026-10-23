#!/bin/bash
set -euo pipefail
# One owned target build using the existing recipe and shared build-slot wrapper.
TR=/root/work/lanes/dedup-offline23-integration
SCR=/root/work/lanes/dedup-offline23-main
SHA=af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34
LP=dd23af09on
O=/root/probe/lanes/route/out-dd23af09onrW
P='/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1/programs/candidate-routedd23af09onrW'
T=$TR/port/dreamcast/tools/d367
[ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
[ "$(realpath -m "$O")" = /root/probe/lanes/route/out-dd23af09onrW ]
[ ! -e "$O" ] && [ ! -e "$P" ]
FREE=$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')
[ "$FREE" -ge 24696061952 ] || { echo 'C: floor plus build reserve unavailable'; exit 2; }
mkdir -p "$SCR/on-k"
exec 9>"$SCR/tree.lock"
flock -n 9 || { echo 'Owned source tree is busy'; exit 2; }
exec > >(tee "$SCR/on-build-launch.log") 2>&1
date -Is
printf 'source=%s tree=%s output=%s\n' "$SHA" "$TR" "$O"
export JOBS=1 SOURCE_DATE_EPOCH=1760000000
# Source the committed recipe only; do not edit production configuration.
. "$T/rr/recipe.conf"
K="$SCR/on-k" T="$TR" LP="$LP" CH2="$CH2" \
 XON='SCENERY_DEDUP=3 QA_MENU=1 WARP_AFTER_RESET=1 WORLD_METER=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23-DD3 QA_SRC=af09f0a2' \
 bash "$T/ch2/ch2-build.sh" rW
[ -s "$O/re4dc-game.elf" ]
[ ! -s "$O/missing.txt" ]
grep -q 'SCENERY_DEDUP=3' "$O/resolved-knobs.txt"
printf 'TARGET_LINK_COMPLETE source=%s\n' "$SHA"
