#!/bin/bash
# hw.sh <name> <arm label (e19kmW)> <warp WSL path> <A:B> (Git Bash): stage the fixture disc, then hwproject
# (count A:B, trace A:B:8, drop traces); the staged disc is deleted afterwards.
set -euo pipefail
N=${1:?}; L=${2:?}; W=${3:?}; WIN=${4:?}
D=$(cd "$(dirname "$0")" && pwd)
HW="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
K=/root/probe/lanes-20261019/engine19/k
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env RC19D=/root/re4data/private/rc19o2-20261019 bash $K/fix.sh "$L" "$N" "$W" | tail -1
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root --cd "$HW" -- python3 /root/work/lanes/engine19/port/dreamcast/tools/d367/stage_ext4/stage_scenario.py route-e19-$N --arm candidate-route$L --programs programs-route.json --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture $K/fix/$N.json > /dev/null 2>&1
DISC="$HW/scenarios/route-e19-$N/disc/disc.bin"
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- bash /root/work/lanes/engine19/port/dreamcast/tools/hwmodel/hwproject.sh --name e19-$N --disc "$DISC" --count $WIN --trace $WIN:8 --drop-traces /root/probe/lanes/route/out-$L 2>&1 | tail -40
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- rm -f "$DISC"
