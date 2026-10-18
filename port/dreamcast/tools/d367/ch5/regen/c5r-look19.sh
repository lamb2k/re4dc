#!/bin/bash
set -uo pipefail
E="/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016"
for r in $(awk -F'\t' '{print $4}' /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen/missing-src.tsv | tr -d '\r' | sort -u | tr '\\' '/'); do
  s="$E/$r/stage.json"; [ -f "$s" ] || s="$E/$r"
  echo "$r $(date -r "$s" -Iseconds 2>/dev/null)"
done | sort -u | head -40
cd /root/work/re4-dreamcast
git log --format="%h %cI %s" -12 origin/lane/ch5found16 | cut -c1-120
