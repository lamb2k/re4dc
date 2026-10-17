#!/bin/bash
# build.sh <label prefix> <arm> [extra knobs...] (WSL): farmprop17 arm on the test 17 recipe (ch2-build.sh = T15REC + CH2REC)
# from the farmprop17 tree. Arms rP / rW / mW / rT (recipe) and the x* knob-off twins of ch2-build.sh.
set -uo pipefail
LPX=$1; ARM=$2; shift 2
export T=${T:-/root/probe/lanes-20261016/farmprop17}
export K=/root/probe/lanes-20261016/fp17/k
export LP=$LPX
export XON="${XON:-} $*"
mkdir -p "$K"
bash "$T/port/dreamcast/tools/d367/ch2/ch2-build.sh" "$ARM"
