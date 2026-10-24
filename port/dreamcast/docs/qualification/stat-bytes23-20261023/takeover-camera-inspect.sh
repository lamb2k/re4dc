#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete
sed -n '395,455p' "$T/src/game/player.cpp"
rg -n 'camMove|SetMove|setMove|moveCheck|cam.*move' "$T/src/game/player.cpp"