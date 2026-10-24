#!/usr/bin/env bash
set -euo pipefail
BASE=d5c1ceab9e06461462669b3ce1d28a379747a74a
SOURCE=4be08e0110592510e3630c01fa9f49b3ac2fed3d
FIX=${1:?reviewed prefetch decoder fix commit required}
REPO=/root/work/lanes/dedup-offline23-current-d5c
LAND=/root/work/lanes/dedup-offline23-land
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01/root-landing'
[ "$(git -C "$REPO" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$REPO" status --porcelain)" ]
[ "$(git -C "$REPO" remote get-url origin)" = 'https://github.com/lamb2k/re4dc.git' ]
git -C "$REPO" fetch origin t15/int
[ "$(git -C "$REPO" rev-parse origin/t15/int)" = "$BASE" ]
git -C "$REPO" cat-file -e "$FIX^{commit}"
git -C "$REPO" merge-base --is-ancestor "$SOURCE" "$FIX"
[ ! -e "$LAND" ]
mkdir -p "$E"
git -C "$REPO" worktree add -b wip/dedup-offline23-land-20261023 "$LAND" "$BASE"
git -C "$LAND" merge --no-ff --no-edit "$FIX"
[ "$(git -C "$LAND" rev-parse HEAD^1)" = "$BASE" ]
[ "$(git -C "$LAND" rev-parse HEAD^2)" = "$FIX" ]
git -C "$LAND" diff --exit-code "$BASE" HEAD -- port/dreamcast/tools/d367/rr/recipe.conf
git -C "$LAND" diff --check
[ -z "$(git -C "$LAND" status --porcelain)" ]
git -C "$LAND" rev-parse HEAD > "$E/merge-source.txt"
git -C "$LAND" show --stat --oneline HEAD > "$E/merge-stat.txt"
printf 'LOCAL_DEFAULT_OFF_MERGE_PREPARED; NOT PUSHED; source=%s\n' "$(git -C "$LAND" rev-parse HEAD)"
