#!/bin/bash
set -euo pipefail
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
ROOT=/root/work/lanes/dedup-offline23-main
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
O=/root/probe/lanes/route/out-fpdd23diagW
R=$ROOT/stage-on
[ -s "$O/re4dc-game.elf" ] && [ ! -s "$O/missing.txt" ]
[ ! -e "$EV/base-diag" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 24696061952 ]
for k in SCENERY_DEDUP=3 TEX_CHECK=1 MCHECK_LEONGC=1 NATIVE_MODEL_REGISTRY_CENSUS=1 KOS_WATCH=1 KOS_SQUEEZE=1 W11_FIXTURE=1; do grep -qx "$k" "$O/resolved-knobs.txt"; done
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/pkgtree" "$R/manifest.json" "$R/gdemu/IP.BIN" "$EV/base-diag" "$O" > "$ROOT/diagnostic-master.log" 2>&1
tail -2 "$ROOT/diagnostic-master.log"
