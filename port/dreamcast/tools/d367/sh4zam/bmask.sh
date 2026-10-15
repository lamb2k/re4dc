#!/bin/bash
# bmask.sh <tag> <boot mask> [extra knobs]: SKIN_SH4ZAM cost arm (test 13 recipe + GAME_SH4ZAM render-only + SKIN_SH4ZAM=1,
# boot mask = a .data word; PACE_MODE=off PC_SAMPLER_BYTES=8192), label sk<tag>rW.
K=/root/probe/lanes-20261015/sh4zam
TAG=$1; M=$2; shift 2
cd $K && XON="SKIN_SH4ZAM=${SKZ:-1} SKIN_SH4ZAM_BOOT=$M PACE_MODE=off PC_SAMPLER_BYTES=8192 $*" \
  bash tree/port/dreamcast/tools/d367/sh4zam/zbuild.sh sk$TAG 1 rW
O=/root/probe/lanes/route/out-sk${TAG}rW
/opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf | grep -E ' _re4dc_skin_sh4zam_mask$| _end$'
/opt/toolchains/dc/sh-elf/bin/sh-elf-size $O/re4dc-game.elf
cat $O/missing.txt 2>/dev/null | head
