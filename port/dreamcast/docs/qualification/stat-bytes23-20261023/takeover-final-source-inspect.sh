#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
git -C /root/work/lanes/stat-bytes23-camera-control diff HEAD^..HEAD
rg -n -C12 'stat & STAT_BE\(0xFFFFFF00\)' "$T/src/game/player.cpp"
rg -n '^CH2=|STAT_ROUTINE|STAT_DIAG|KOS_CACHE_P2' "$T/port/dreamcast/tools/d367/rr/recipe.conf"
find /root/work/lanes -maxdepth 2 -name ROOT-LIVE.md -o -name ROOT-LIVE.txt