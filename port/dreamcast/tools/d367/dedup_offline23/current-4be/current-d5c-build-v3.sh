#!/bin/bash
set -euo pipefail
if [ "${1:-}" = --after-slot ];then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ] || { echo DISK_FLOOR_AFTER_SLOT;exit 3; }
 exec "$@"
fi
MODE=${1:?off/on/twin-off/twin-on/diag/qa-off/qa-on}
OWN='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23'
. "$OWN/current-d5c-pins.sh"
case "$MODE" in qa-off|qa-on)TREE=/root/work/lanes/dedup-offline23-qa-4be08e01;;esac
T=$TREE/port/dreamcast/tools/d367
[ "$(git -C "$TREE" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TREE" status --porcelain --untracked-files=no)" ]
[ "$(git -C "$TREE" show "$BASE:port/dreamcast/tools/d367/rr/recipe.conf" | sha256sum | cut -c1-64)" = "$(sha256sum "$T/rr/recipe.conf" | cut -c1-64)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
if pgrep -af '^(bash|/bin/bash|python|python3) [^ ]*rr-(cycle|qa|jobs)\.(sh|py)( |$)' > /dev/shm/dedup-current-release-processes.txt;then
 echo 'RELEASE_PRIORITY_HOLD';cat /dev/shm/dedup-current-release-processes.txt;exit 3
fi
mkdir -p "$WORK/build/$MODE"
exec 7>"$TREE.build.lock";flock -n 7 || { echo TREE_LEASE_BUSY;exit 2; }
exec > >(tee "$WORK/build/$MODE/launch.log") 2>&1
export JOBS=1 SOURCE_DATE_EPOCH=1760000000 PYTHONDONTWRITEBYTECODE=1 PRUNE_AUTO=0
export ROUTE_PROGRAMS_DIR="$WORK/programs" ROUTE_PROGRAMS_JSON='' ROUTE_REGISTRY_LOCK="$WORK/programs.lock"
export RE4DC_HARNESS="$WORK"
. "$T/rr/recipe.conf"
git -C "$TREE" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$WORK/build/$MODE/kos-before.sha256"
case "$MODE" in
 trace-off|trace-on)
  ARM=${MODE#trace-};DD=0;[ "$ARM" = off ] || DD=3
  LP=dd23cur${S8}${ARM};LABEL=${LP}rT;O=/root/probe/lanes/route/out-$LABEL
  [ ! -e "$O" ]
  bash /root/probe/d367-buildslot.sh bash "$OWN/current-d5c-build.sh" --after-slot env K="$WORK/build/$MODE/k" T="$TREE" LP="$LP" CH2="$CH2 SCENERY_DEDUP=$DD" XON="PC_SAMPLER=0" bash "$T/ch2/ch2-build.sh" rT
  ;;
 off|on)
  DD=0;[ "$MODE" = off ] || DD=3
  LP=dd23cur${S8}${MODE};LABEL=${LP}rP;O=/root/probe/lanes/route/out-$LABEL
  [ ! -e "$O" ]
  bash /root/probe/d367-buildslot.sh bash "$OWN/current-d5c-build.sh" --after-slot env K="$WORK/build/$MODE/k" T="$TREE" LP="$LP" CH2="$CH2 SCENERY_DEDUP=$DD" XON='' bash "$T/ch2/ch2-build.sh" rP
  ;;
 twin-off|twin-on|diag)
  ARM=${MODE#twin-};[ "$MODE" != diag ] || ARM=on
  RELEASE=/root/probe/lanes/route/out-dd23cur${S8}${ARM}rP
  [ "$(cat "$RELEASE/stack.txt")" = "$SOURCE" ];[ ! -s "$RELEASE/missing.txt" ]
  LAB=dd23cur${S8}${ARM}g;EXTRA=()
  if [ "$MODE" = diag ];then LAB=dd23cur${S8}diag;EXTRA=(KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1 NATIVE_MODEL_REGISTRY_CENSUS=1 NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150);fi
  O=/root/probe/lanes/route/out-fp${LAB}W
  [ ! -e "$O" ];[ ! -e /root/probe/lanes/route/out-fp${LAB}P ]
  export FP_TREE=$TREE
  bash /root/probe/d367-buildslot.sh bash "$OWN/current-d5c-build.sh" --after-slot bash "$T/fullplay/fp_twin.sh" "$RELEASE" "$LAB" "${EXTRA[@]}"
  ;;
 qa-off|qa-on)
  ARM=${MODE#qa-};DD=0;[ "$ARM" = off ] || DD=3
  LP=dd23${S8}${ARM}q;O=/root/probe/lanes/route/out-${LP}rW
  [ ! -e "$O" ]
  export ROUTE_PROGRAMS_DIR="$WORK/qa/programs" RE4DC_HARNESS="$WORK/qa"
  bash /root/probe/d367-buildslot.sh bash "$OWN/current-d5c-build.sh" --after-slot env K="$WORK/build/$MODE/k" T="$TREE" LP="$LP" CH2="$CH2" XON="SCENERY_DEDUP=$DD PC_SAMPLER=0 QA_MENU=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23 QA_SRC=$S8" bash "$T/ch2/ch2-build.sh" rW
  ;;
 *)exit 2;;
esac
[ -s "$O/re4dc-game.elf" ];[ ! -s "$O/missing.txt" ]
[ "$(cat "$O/stack.txt")" = "$SOURCE" ]
for K in SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_SUBMIT_BATCH=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 EM_READ_RETRY=1 KOS_CACHE_P2_DIAG=0 STAT_ROUTINE_BYTES=1 STAT_DIAG=0 VRAM_ROOM_ARENA=0;do
 grep -qx "$K" "$O/resolved-knobs.txt"
done
[ "$(find "$O" -maxdepth 1 -name '*.ovl' | wc -l)" -eq 14 ]
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$WORK/build/$MODE/kos-after.sha256"
cmp "$WORK/build/$MODE/kos-before.sha256" "$WORK/build/$MODE/kos-after.sha256"
echo "OWNED_CURRENT_BUILD_COMPLETE mode=$MODE source=$SOURCE output=$O"
