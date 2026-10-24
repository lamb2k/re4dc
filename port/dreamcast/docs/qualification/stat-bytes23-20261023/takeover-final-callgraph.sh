#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
rg -n -- '->moved|\bmoved\b' "$T/src/game/camera.cpp" "$T/src/game/player.cpp" "$T/src/game"/cam*.cpp "$T/include/cPlayer.h" 2>/dev/null | head -100
find '/mnt/c/Game Dev/Emulators/codex-lanes' -maxdepth 2 -iname '*root*live*'