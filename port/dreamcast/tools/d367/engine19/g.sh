#!/bin/bash
# g.sh <name> <arm label> <warp (WSL path)> [pad (WSL path)] [seconds] (Git Bash): fixture with the VIS room files, then one run.
set -euo pipefail
N=${1:?}; L=${2:?}; W=${3:?}; P=${4:-}; S=${5:-60}
D=$(cd "$(dirname "$0")" && pwd)
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root -- env RC19D=${RC19D:-/root/re4data/private/rc19v-20261019} \
  bash /root/probe/lanes-20261019/engine19/k/fix.sh "$L" "$N" "$W" $P | tail -1
bash "$D/run.sh" "$N" "$L" "/root/probe/lanes-20261019/engine19/k/fix/$N.json" "$S"
