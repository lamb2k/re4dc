#!/bin/bash
# blogic.sh: GAME_SH4ZAM_LOGIC arms.
#   lgrW  cost arm  = skm0rW + GAME_SH4ZAM=1 (global) + GAME_SH4ZAM_LOGIC=1 (PACE_MODE=off PC_SAMPLER_BYTES=8192)
#   zcrW  equivalence control = test 13 recipe + GAME_SH4ZAM render-only (accepted) + cap logs
#   zlrW  equivalence logic arm = zcrW + GAME_SH4ZAM_LOGIC=1
K=/root/probe/lanes-20261015/sh4zam
cd $K
for a in "$@"; do case $a in
  lg) XON="SKIN_SH4ZAM=1 SKIN_SH4ZAM_BOOT=0 GAME_SH4ZAM_LOGIC=1 PACE_MODE=off PC_SAMPLER_BYTES=8192" \
        bash tree/port/dreamcast/tools/d367/sh4zam/zbuild.sh lg 2 rW ;;
  zc) XON="ALIVE_CAP_LOG=1 R101_CAP_LOG=1" bash tree/port/dreamcast/tools/d367/sh4zam/zbuild.sh zc 1 rW ;;
  zl) XON="ALIVE_CAP_LOG=1 R101_CAP_LOG=1 GAME_SH4ZAM_LOGIC=1" bash tree/port/dreamcast/tools/d367/sh4zam/zbuild.sh zl 2 rW ;;
esac; done
