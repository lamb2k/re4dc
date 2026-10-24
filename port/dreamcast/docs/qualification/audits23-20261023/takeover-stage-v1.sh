#!/usr/bin/env bash
set -euo pipefail
TYPE=${1:?g/c/t/d};DV=0;case "$TYPE" in g)O=/root/probe/lanes/route/out-fpau23on5e4dgW;;c)O=/root/probe/lanes/route/out-fpau23on5e4dcW;;t)O=/root/probe/lanes/route/out-au23on5e4drT;;d)O=/root/probe/lanes/route/out-fpau23diag5e4dcW;DV=1;;*)exit 2;;esac
T=/root/work/lanes/audits23-target-on/port/dreamcast/tools/d367
E='/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0'
R=/root/work/lanes/stat-bytes23-takeover-scratch/release
B=$E/_discs/on-$TYPE
[ ! -e "$B" ];[ -s "$O/re4dc-game.elf" ];[ ! -s "$O/missing.txt" ]
[ "$(head -1 "$O/stack.txt")" = 5e4de9a0262d3629c9833c959557de198b2e9f0c ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
for K in STAT_ROUTINE_BYTES=1 STAT_DIAG=0 EM_READ_RETRY=1 ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 KOS_CACHE_P2_DIAG=$DV VRAM_ROOM_ARENA=0;do grep -qx "$K" "$O/resolved-knobs.txt";done
mkdir -p "$E/identities"
cp "$O/syms.txt" "$E/identities/on-$TYPE-syms.txt"
cp "$O/resolved-knobs.txt" "$E/identities/on-$TYPE-resolved-knobs.txt"
cp "$O/stack.txt" "$E/identities/on-$TYPE-stack.txt"
sha256sum "$O/re4dc-game.elf" "$O"/*.ovl > "$E/identities/on-$TYPE-programmes.sha256"
cp "$R/manifest.json" "$E/identities/baseline-source-release-manifest.json"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/tree" "$R/manifest.json" "$R/IP.BIN" "$B" "$O" > "$E/identities/on-$TYPE-master.log" 2>&1
printf 'AUDIT_STAGE_COMPLETE type=%s\n' "$TYPE"