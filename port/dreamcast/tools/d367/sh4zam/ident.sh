#!/bin/bash
# ident.sh <label>: build the knob-off play arm <label>rP (test 13 recipe, GAME_SH4ZAM / SKIN_SH4ZAM / GAME_SH4ZAM_LOGIC /
# GAME_SHZ_MEMSET all off) from the lane tree and compare its image + overlays with test 13's t13mrP (c1ae83dd).
K=/root/probe/lanes-20261015/sh4zam
L=$1
cd $K && bash tree/port/dreamcast/tools/d367/sh4zam/zbuild.sh $L 0 rP 2>&1 | grep -E '^rc=' | cut -c1-100
OC=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
R=/root/probe/lanes/route
for l in t13mrP ${L}rP; do
  $OC -R .stack -O binary $R/out-$l/re4dc-game.elf /tmp/id-$l.bin
  echo "$l image $(sha256sum < /tmp/id-$l.bin | cut -c1-8) end $(cat $R/out-$l/end.txt)"
done
cmp /tmp/id-t13mrP.bin /tmp/id-${L}rP.bin && echo "IMAGE IDENTICAL"
for o in $R/out-t13mrP/*.ovl; do
  b=$(basename $o)
  cmp -s $o $R/out-${L}rP/$b && echo "$b identical" || echo "$b DIFFERS"
done
rm -f /tmp/id-t13mrP.bin /tmp/id-${L}rP.bin
