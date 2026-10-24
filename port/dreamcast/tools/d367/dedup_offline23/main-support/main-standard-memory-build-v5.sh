#!/bin/bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/main-standard-memory-build-v5.sh'
if [ "${1:-}" = --after-slot ];then
 shift
 FREE=$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')
 [ "$FREE" -ge 22548578304 ] || { echo "DISK_HOLD after build-slot acquisition: free=$FREE reserve=21GiB";exit 3; }
 exec "$@"
fi
MODE=${1:?base off on twin-off twin-on}
ROOT=/root/work/lanes/dedup-offline23-standard-repair5be3
SOURCE=/root/work/lanes/dedup-offline23-next
SHA=5be38f009f9ae4d42daff69dacc537e8230bcfca
BASE=ea969bb241f77291d2ca43d706c9dc2d1226ee76
BASE_TREE=/root/work/lanes/dedup-offline23-recipe-current-ea
[ "$(git -C "$SOURCE" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$SOURCE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 22548578304 ] || { echo 'DISK_HOLD before setup: need21GiB';exit 3; }
mkdir -p "$ROOT"
case "$MODE" in
 base)
  if [ ! -e "$BASE_TREE" ];then git -C "$SOURCE" worktree add --detach "$BASE_TREE" "$BASE";fi
  TR=$BASE_TREE;EXPECT=$BASE;LP=dd23stdbaseea;DD=0;;
 off)
  TR=/root/work/lanes/dedup-offline23-current-off5be3
  if [ ! -e "$TR" ];then git -C "$SOURCE" worktree add --detach "$TR" "$SHA";fi
  EXPECT=$SHA;LP=dd23stdoff5be3;DD=0;;
 on) TR=$SOURCE;EXPECT=$SHA;LP=dd23stdon5be3;DD=3;;
 twin-off)
  TR=/root/work/lanes/dedup-offline23-current-off5be3
  if [ ! -e "$TR" ];then git -C "$SOURCE" worktree add --detach "$TR" "$SHA";fi
  EXPECT=$SHA;LP=dd23stdoff5be3;DD=0;;
 twin-on) TR=$SOURCE;EXPECT=$SHA;LP=dd23stdon5be3;DD=3;;
 *)exit 2;;
esac
[ "$(git -C "$TR" rev-parse HEAD)" = "$EXPECT" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
T=$TR/port/dreamcast/tools/d367
export JOBS=1 SOURCE_DATE_EPOCH=1760000000
mkdir -p "$ROOT/$MODE"
exec 7>"$ROOT/$(basename "$TR").lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/$MODE/launch.log") 2>&1
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
printf 'source=%s mode=%s tree=%s\n' "$EXPECT" "$MODE" "$TR"
find /root/work/kos-re4dc-d367/lib -maxdepth 3 -name libkallisti.a -exec sha256sum {} \; > "$ROOT/$MODE/kos-before.sha256"
sha256sum "$T/rr/recipe.conf" > "$ROOT/$MODE/recipe.sha256"
if [[ "$MODE" = twin-* ]];then
 O=/root/probe/lanes/route/out-${LP}rP
 [ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
 LAB=${LP}g
 [ ! -e /root/probe/lanes/route/out-fp${LAB}W ] && [ ! -e /root/probe/lanes/route/out-fp${LAB}P ]
 export FP_TREE=$TR
 # The unmodified twin tool includes release reproduction; no FP_SKIP_IDENTITY.
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$T/fullplay/fp_twin.sh" "$O" "$LAB"
 O=/root/probe/lanes/route/out-fp${LAB}W
 for K in DBG_WARP=1 WARP_JUMP=1 PC_SAMPLER=0 TEX_CHECK=1 MCHECK_LEONGC=1;do grep -qx "$K" "$O/resolved-knobs.txt";done
else
 O=/root/probe/lanes/route/out-${LP}rP
 [ ! -e "$O" ]
 . "$T/rr/recipe.conf"
 bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/$MODE/k" T="$TR" LP="$LP" CH2="$CH2 SCENERY_DEDUP=$DD" XON="" bash "$T/ch2/ch2-build.sh" rP
fi
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
for K in "SCENERY_DEDUP=$DD" QA_MENU=0 WORLD_METER=0 PC_SAMPLER=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
find /root/work/kos-re4dc-d367/lib -maxdepth 3 -name libkallisti.a -exec sha256sum {} \; > "$ROOT/$MODE/kos-after.sha256"
[ -s "$ROOT/$MODE/kos-before.sha256" ]
cmp "$ROOT/$MODE/kos-before.sha256" "$ROOT/$MODE/kos-after.sha256"
printf 'STANDARD_PROFILE_LINK_COMPLETE mode=%s source=%s output=%s\n' "$MODE" "$EXPECT" "$O"
