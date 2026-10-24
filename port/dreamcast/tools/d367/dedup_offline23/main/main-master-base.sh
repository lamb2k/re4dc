#!/bin/bash
set -euo pipefail
ARM=${1:?on or off}
TR=/root/work/lanes/dedup-offline23-integration
T=$TR/port/dreamcast/tools/d367
ROOT=/root/work/lanes/dedup-offline23-main
EV='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023'
case "$ARM" in on) LABEL=dd23af09on2rW;;off) LABEL=dd23af09offrW;;*) exit 2;;esac
R=$ROOT/stage-$ARM;O=/root/probe/lanes/route/out-$LABEL
DEST=$EV/base-$ARM
[ -s "$R/gdemu/track03.bin" ] && [ -s "$O/re4dc-game.elf" ]
[ ! -e "$DEST" ] && [ ! -e "$R/manifest.json" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
python3 "$T/fullplay/fp_iso.py" manifest "$R/gdemu/track03.bin" -o "$R/manifest.json"
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/pkgtree" "$R/manifest.json" "$R/gdemu/IP.BIN" "$DEST" "$O" > "$R/logs/fp-master.txt" 2>&1
tail -2 "$R/logs/fp-master.txt"
printf 'OWNED_CONSOLE_BASE_READY arm=%s programme=%s\n' "$ARM" "$LABEL"
