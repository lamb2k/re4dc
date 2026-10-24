#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-takeover
F=$T/port/dreamcast/tools/d367
printf 'CURRENT RR OUTPUTS\n'
for O in /root/probe/lanes/route/out-rr933936erP /root/probe/lanes/route/out-rr933936earP /root/probe/lanes/route/out-rr377569arP;do
 [ ! -d "$O" ] || { printf '%s\n' "$O"; cat "$O/stack.txt";ls -l "$O/re4dc-game.elf"; }
done
printf 'CURRENT RR WORK\n'
ls -t /root/rr/work | head -4
W=/root/rr/work/1023-1920-933936ea
find "$W" -maxdepth 2 -type f -printf '%P\n' | head -35
printf 'FULLPLAY MASTER\n'
sed -n '1,160p' "$F/fullplay/fp_master.sh"
printf 'CH2 ARMS\n'
grep -nE 'rT|rP|XON|CH2=|LOG_|TREE|buildslot' "$F/ch2/ch2-build.sh" | head -70
printf 'BELL MENDEZ REPRO TOOLS\n'
find "$F" -maxdepth 3 -type f | grep -E 'decision|mendez|bell|repro' | head -50
