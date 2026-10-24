#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/dedup-offline23-land/port/dreamcast/tools/d367
R=/root/work/lanes/stat-bytes23-takeover-scratch/release
O=/root/probe/lanes/route/out-rs24fb254camrW
E='/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/restrip23-fb254/root-forest-camera'
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 28991029248 ]
[ -f "$E/PROGRAMME-PINS.json" ]
[ -d "$R/tree" ];[ -f "$R/IP.BIN" ]
[ "$(sha256sum "$R/manifest.json" | cut -d' ' -f1)" = a424cdc4f68460b0d5ea8f591c44c62eefeab85b67941410bc996680dce41547 ]
[ ! -e "$E/base" ]
PRUNE_AUTO=0 bash "$T/fullplay/fp_master.sh" "$R/tree" "$R/manifest.json" "$R/IP.BIN" "$E/base" "$O" > "$E/master.log" 2>&1
tail -n 2 "$E/master.log"
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 25769803776 ]
echo FOREST_CAMERA_MASTER_COMPLETE
