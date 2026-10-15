#!/bin/bash
# b4.sh <mask...>: GAME_SHZ_MEM cost arms on the t14/rc recipe (adopt tree), boot mask as .data; label m<mask>rW
A=/root/probe/lanes-20261015/sh4zam/adopt
cd $A
for m in "$@"; do
  T=$A LP=zm$m XON="GAME_SHZ_MEM=1 SHZ_MEM_BOOT=$m PACE_MODE=off PC_SAMPLER_BYTES=8192" \
    bash port/dreamcast/tools/d367/test14/t14-build.sh rW > /root/probe/lanes-20261015/sh4zam/scr/b4-$m.log 2>&1
  grep -E '^rc=' /root/probe/lanes-20261015/sh4zam/scr/b4-$m.log | cut -c1-90
  O=/root/probe/lanes/route/out-zm${m}rW
  /opt/toolchains/dc/sh-elf/bin/sh-elf-nm $O/re4dc-game.elf 2>/dev/null | grep -E ' _re4dc_shz_mem_mask$| _end$| ___wrap_memcpy$| _shz_memset8_sh4_$'
  cat $O/missing.txt 2>/dev/null | head -5
done
