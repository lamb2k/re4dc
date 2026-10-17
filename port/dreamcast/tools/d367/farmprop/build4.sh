#!/bin/bash
# build4.sh <label prefix> <arm> [extra knobs...] (WSL): castle recipe arm (ch4found/ch4-build.sh = T15REC + CH4REC)
set -uo pipefail
LPX=$1; ARM=$2; shift 2
export T=/root/probe/lanes-20261016/farmprop17
export K=/root/probe/lanes-20261016/fp17/k
export LP=$LPX
export XON="${XON:-} $*"
bash "$T/port/dreamcast/tools/d367/ch4found/ch4-build.sh" "$ARM"
