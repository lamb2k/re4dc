#!/bin/bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/main-standard-memory-build-v3.sh'
if [ "${1:-}" = --after-slot ];then
 shift
 FREE=$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')
 [ "$FREE" -ge 22548578304 ] || { echo "DISK_HOLD after build-slot acquisition: free=$FREE reserve=21GiB";exit 3; }
 exec "$@"
fi
MODE=${1:?base off on twin-off twin-on}
ROOT=/root/work/lanes/dedup-offline23-standard
SOURCE=/root/work/lanes/dedup-offline23-next
SHA=54240115d1949243752c7052d22db2c4e0308826
BASE=831a2115e78e762f5a14886e3b1a4b17dbf9fab1
BASE_TREE=/root/work/lanes/dedup-offline23-recipe-base
[ "$(git -C "$SOURCE" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$SOURCE" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 22548578304 ] || { echo 'DISK_HOLD before setup: need21GiB';exit 3; }
mkdir -p "$ROOT"
case "$MODE" in
 base)
  if [ ! -e "$BASE_TREE" ];then git -C "$SOURCE" worktree add --detach "$BASE_TREE" "$BASE";fi
  TR=$BASE_TREE;EXPECT=$BASE;LP=dd23stdbase831;DD=0;;
 off) TR=$SOURCE;EXPECT=$SHA;LP=dd23stdoff542;DD=0;;
 on) TR=$SOURCE;EXPECT=$SHA;LP=dd23stdon542;DD=3;;
 twin-off) TR=/root/work/lanes/dedup-offline23-memory-off;EXPECT=$SHA;LP=dd23stdoff542;DD=0;;
 twin-on) TR=$SOURCE;EXPECT=$SHA;LP=dd23stdon542;DD=3;;
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
