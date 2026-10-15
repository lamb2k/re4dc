#!/bin/bash
# b7.sh: GAME_SHZ_MEM with the main-RAM + overlap guards: zf7rW (cost, mask 7) and zf0rW (mask 0)
A=/root/probe/lanes-20261015/sh4zam/adopt
cd $A
for m in 7 0; do
  T=$A LP=zf$m XON="GAME_SHZ_MEM=1 SHZ_MEM_BOOT=$m PACE_MODE=off PC_SAMPLER_BYTES=8192" \
    bash port/dreamcast/tools/d367/test14/t14-build.sh rW 2>&1 | grep -E '^rc=' | cut -c1-90
done
