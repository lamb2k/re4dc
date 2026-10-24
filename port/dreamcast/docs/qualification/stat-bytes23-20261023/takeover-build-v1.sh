#!/usr/bin/env bash
set -euo pipefail
SELF='/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23/takeover-build-v1.sh'
if [ "${1:-}" = --after-slot ]; then
 shift
 [ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ] || { echo 'DISK_HOLD need22GiB';exit 3; }
 exec "$@"
fi
ARM=${1:?off or on}
case "$ARM" in off) V=0;TR=/root/work/lanes/stat-bytes23-takeover-off;;on) V=1;TR=/root/work/lanes/stat-bytes23-takeover;;*)exit 2;;esac
SOURCE=66f098ed842d05cca196a1ef3facb9249ee88eed
ROOT=/root/work/lanes/stat-bytes23-takeover-scratch
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
if [ ! -e "$TR" ];then git -C /root/work/lanes/stat-bytes23-takeover worktree add --detach "$TR" "$SOURCE";fi
[ "$(git -C "$TR" rev-parse HEAD)" = "$SOURCE" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
mkdir -p "$ROOT/$ARM"
exec 7>"$ROOT/tree-$ARM.lock";flock -n 7 || exit 2
exec > >(tee "$ROOT/$ARM/build.log") 2>&1
git -C "$TR" submodule update --init --depth 1 port/dreamcast/game/third_party/sh4zam
T=$TR/port/dreamcast/tools/d367
export JOBS=1 SOURCE_DATE_EPOCH=1760000000
. "$T/rr/recipe.conf"
cp "$T/rr/recipe.conf" "$ROOT/$ARM/recipe.conf"
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/$ARM/kos-before.sha256"
LP=sb23${ARM}66f0
O=/root/probe/lanes/route/out-${LP}rP
[ ! -e "$O" ]
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot env K="$ROOT/$ARM/k" T="$TR" LP="$LP" CH2="$CH2 STAT_ROUTINE_BYTES=$V STAT_DIAG=0" XON="" bash "$T/ch2/ch2-build.sh" rP
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
for K in "STAT_ROUTINE_BYTES=$V" STAT_DIAG=0 CPU_BACKFACE=0 ACTOR_BACKFACE=0 FX_LEVEL=3 FX_TRIM=1 PC_SAMPLER=0 QA_MENU=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
export FP_TREE=$TR
bash /root/probe/d367-buildslot.sh bash "$SELF" --after-slot bash "$T/fullplay/fp_twin.sh" "$O" ${LP}g
sha256sum /root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a > "$ROOT/$ARM/kos-after.sha256"
cmp "$ROOT/$ARM/kos-before.sha256" "$ROOT/$ARM/kos-after.sha256"
printf 'STAT_RELEASE_AND_G_TWIN_COMPLETE arm=%s source=%s\n' "$ARM" "$SOURCE"
