#!/bin/bash
# build.sh <label prefix> <arm> [extra knobs...] (WSL): actorplan lane arm on the t15 recipe from the actorplan tree.
#   cost arm: XON="PACE_MODE=off PC_SAMPLER_BYTES=8192 ..." rW
set -u
LPX=$1; ARM=$2; shift 2
export T=/root/probe/lanes-20261015/actorplan
export K=/root/probe/lanes-20261015/actorplan-k
export LP=$LPX
export XON="${XON:-} $*"
mkdir -p $K
bash $T/port/dreamcast/tools/d367/test15/t15-build.sh $ARM
