#!/bin/bash
# b5.sh: STRICT trace arms of GAME_SHZ_MEM on t14/rc: zt0rT (mask 0, same layout) and zt7rT (mask 7)
A=/root/probe/lanes-20261015/sh4zam/adopt
cd $A
for m in 0 7; do
  T=$A LP=zt$m XON="GAME_SHZ_MEM=1 SHZ_MEM_BOOT=$m" bash port/dreamcast/tools/d367/test14/t14-build.sh rT 2>&1 | grep -E '^rc=' | cut -c1-90
done
