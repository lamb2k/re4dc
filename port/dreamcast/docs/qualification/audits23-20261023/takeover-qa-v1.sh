#!/usr/bin/env bash
set -euo pipefail
TR=/root/work/lanes/audits23-target-on
SHA=5e4de9a0262d3629c9833c959557de198b2e9f0c
T=$TR/port/dreamcast/tools/d367
ROOT=/root/work/lanes/audits23-console-scratch
W=$ROOT/qa23-5e4de9a0
[ "$(git -C "$TR" rev-parse HEAD)" = "$SHA" ]
[ -z "$(git -C "$TR" status --porcelain)" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
[ ! -e "$W" ]
mkdir -p "$W"
exec 7>"$ROOT/tree-lease.lock";flock -n 7 || exit 2
exec > >(tee "$W/launch.log") 2>&1
. "$T/rr/recipe.conf"
cp "$T/rr/recipe.conf" "$W/recipe.conf"
printf '\nCH2="%s STAT_ROUTINE_BYTES=1 STAT_DIAG=0 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 KOS_CACHE_P2_DIAG=0"\n' "$CH2" >> "$W/recipe.conf"
export JOBS=4 SOURCE_DATE_EPOCH=1760000000
L=rr${SHA:0:7}q
O=/root/probe/lanes/route/out-${L}rW
[ ! -e "$O" ]
bash /root/probe/d367-buildslot.sh env K="$W/kq" T="$TR" LP="$L" CH2="$CH2 STAT_ROUTINE_BYTES=1 STAT_DIAG=0 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 KOS_CACHE_P2_DIAG=0" XON="QA_MENU=1 WARP_AFTER_RESET=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 QA_TEST=23 QA_SRC=${SHA:0:8} PC_SAMPLER=0 STAT_DIAG=0" bash "$T/ch2/ch2-build.sh" rW
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
for K in STAT_ROUTINE_BYTES=1 STAT_DIAG=0 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 KOS_CACHE_P2_DIAG=0 QA_MENU=1 PC_SAMPLER=0 QA_TEST=23;do grep -qx "$K" "$O/resolved-knobs.txt";done
bash "$T/rr/rr-qa.sh" "$W" "$TR" "$SHA" 23 "$ROOT/zip" '/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0/qa'
printf 'PRIVATE_QA_BUILD_AND_PACKAGE_READY source=%s\n' "$SHA"
