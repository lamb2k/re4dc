#!/bin/bash
# build.sh [arm]  (WSL; lane gprof17, 2026-10-17): the gameplay profiler arm = ch2-build.sh rW (the recipe the render
# sweep used, cap 4) + PC_SAMPLER=1 PC_SAMPLER_PHASE=1 with a 64 KiB ring. Label gparW (out dir
# /root/probe/lanes/route/out-gparW). The knob-off identity arm is plain `ch2-build.sh rW` from this tree vs t15/int.
# Design and run plan: C:\Game Dev\Emulators\GAMEPLAY-PROFILE-20261017.md.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ARM=${1:-rW}
export LP=${LP:-gpa}
export K=${K:-/root/probe/lanes-20261017r/gprof17-k}
export XON="${XON:-} PC_SAMPLER=1 PC_SAMPLER_PHASE=1 PC_SAMPLER_BYTES=65536"
exec bash "$HERE/../ch2/ch2-build.sh" "$ARM"
