#!/usr/bin/env bash
set -euo pipefail
ARM=${1:?off or on}; TYPE=${2:?g c t}
case "$ARM" in off|on);;*)exit 2;;esac
case "$TYPE" in g|c|t);;*)exit 2;;esac
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/d367
ROOT=/root/work/lanes/stat-bytes23-complete-scratch
REL=/root/work/lanes/stat-bytes23-takeover-scratch/release
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
L=sb23${ARM}2a14
if [ "$TYPE" = t ];then O=/root/probe/lanes/route/out-${L}rT; NEED=STAT_RELEASE_G_C_TRACE_COMPLETE
else O=/root/probe/lanes/route/out-fp${L}${TYPE}W;NEED="TWIN fp${L}${TYPE}W";fi
for N in $(seq 1 600);do
 if [ -f "$ROOT/$ARM/build.log" ] && grep -q "$NEED" "$ROOT/$ARM/build.log";then break;fi
 [ "$N" -lt 600 ] || { echo 'BUILD_NOT_READY';exit 4; }
 sleep 2
done
[ "$(head -1 "$O/stack.txt")" = 2a14662d4b025031cd93f64eed6a5d8159d473b7 ]
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
OUT="$EV/_discs/$ARM-$TYPE"
[ ! -e "$OUT" ]
mkdir -p "$EV/identities" "$EV/_discs"
cp "$O/stack.txt" "$EV/identities/$ARM-$TYPE-source.txt"
cp "$O/resolved-knobs.txt" "$EV/identities/$ARM-$TYPE-knobs.txt"
cp "$O/syms.txt" "$EV/identities/$ARM-$TYPE-syms.txt"
sha256sum "$O/re4dc-game.elf" "$O"/*.ovl > "$EV/identities/$ARM-$TYPE-programmes.sha256"
cp "$REL/manifest.json" "$EV/identities/release-data-manifest.json"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$REL/tree" "$REL/manifest.json" "$REL/IP.BIN" "$OUT" "$O" > "$EV/identities/$ARM-$TYPE-master.log" 2>&1
printf 'STAT_BASE_READY arm=%s type=%s path=%s\n' "$ARM" "$TYPE" "$OUT"
