#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-takeover/port/dreamcast/tools/d367
ROOT=/root/work/lanes/stat-bytes23-takeover-scratch
C='/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-933936ea/gdemu'
[ -s "$C/track03.bin" ]
[ "$(df --output=avail -B1 /mnt/c | tail -1 | tr -d ' ')" -ge 23622320128 ]
[ ! -e "$ROOT/release/tree" ]
mkdir -p "$ROOT/release"
sha256sum "$C/disc.gdi" "$C/track03.bin" > "$ROOT/release/origin-candidate.sha256"
python3 "$T/fullplay/fp_iso.py" extract "$C/track03.bin" "$ROOT/release/tree" --manifest "$ROOT/release/manifest.json" --ipbin "$ROOT/release/IP.BIN"
sha256sum "$ROOT/release/tree/1ST_READ.BIN" "$ROOT/release/manifest.json"
printf 'RR LOG\n'
tail -n 6 /root/rr/work/1023-1920-933936ea/cycle.log | cut -c1-200
