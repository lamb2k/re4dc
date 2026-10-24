#!/usr/bin/env bash
set -euo pipefail
ARM=${1:?R/L/E/B};TYPE=${2:?g/c/t/m/n}
case "$ARM" in R)S=0;P=0;;L)S=1;P=0;;E)S=0;P=1;;B)S=1;P=1;;*)exit 2;;esac
LP=we23${ARM}7a3a;CV=0;MV=0
case "$TYPE" in g|c|m|n)O=/root/probe/lanes/route/out-fp${LP}${TYPE}W;;t)O=/root/probe/lanes/route/out-${LP}rT;;*)exit 2;;esac
[ "$TYPE" != n ] || CV=1200
[ "$TYPE" != m ] || MV=1
T=/root/work/lanes/world-emit23-target-$ARM/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/7a3af776'
R=/root/work/lanes/stat-bytes23-takeover-scratch/release
B=$E/_discs/$ARM-$TYPE
[ ! -e "$B" ];[ -s "$O/re4dc-game.elf" ];[ ! -s "$O/missing.txt" ]
[ "$(head -1 "$O/stack.txt")" = 7a3af776ff8c14070f96272cd48074e5895d0490 ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
for K in "SCENERY_SELECT_LEAN2=$S" "SCENERY_EMIT_PREFETCH=$P" "SCENERY_EMIT_CENSUS=$CV" "WORLD_METER=$MV" SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_SUBMIT_BATCH=1 SCENERY_DEDUP=0 PS2_PVS=0 STAT_ROUTINE_BYTES=1 CPU_BACKFACE=0 ACTOR_BACKFACE=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
mkdir -p "$E/identities"
cp "$O/syms.txt" "$E/identities/$ARM-$TYPE-syms.txt"
cp "$O/resolved-knobs.txt" "$E/identities/$ARM-$TYPE-resolved-knobs.txt"
cp "$O/stack.txt" "$E/identities/$ARM-$TYPE-stack.txt"
sha256sum "$O/re4dc-game.elf" "$O"/*.ovl > "$E/identities/$ARM-$TYPE-programmes.sha256"
cp "$R/manifest.json" "$E/identities/baseline-source-release-manifest.json"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/tree" "$R/manifest.json" "$R/IP.BIN" "$B" "$O" > "$E/identities/$ARM-$TYPE-master.log" 2>&1
printf 'WORLD_STAGE_READY arm=%s type=%s\n' "$ARM" "$TYPE"