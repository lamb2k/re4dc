#!/bin/bash
# castle-knob identity (shared modules.cpp / Makefile / em_set / game.cpp edits): the ch3found cxc3fmW knob set, from
# origin/t15/int (base worktree) and lane/ch5found16
L=/root/probe/lanes-20261016/ch5found
X="ROUTE_CH22=1 ROUTE_CH23=1 EM10_SHARED=1 ROUTE_CH31=1 ROUTE_CH32=1 ROUTE_MOVIES=1 ROUTE_MOVIES_CH3=1 LEON_OT_WATER=1 FOG_OFF_CLEAR=1 PS2_CH3_ENEMY=1 PS2_ENEMY_CH3_DIR=/root/probe/lanes-20261015/castle/private-include PS2_ENEMY_CH22_DIR=/root/probe/codex-ch23-20261013/private-include PS2_ENEMY_CH23_DIR=/root/probe/codex-ch23-20261013/private-include ALIVE_CAP_LOG=1 WARP_JUMP=1 NATIVE_MODEL_REGISTRY_CENSUS=1 VRAM_ROOM_LOG=1 HEAP4_WATER=1 AICA_STR_ENT_MAX=56 LOGIC_TRACE=0 GAME_DECISION_TRACE=0"
T=$L/base bash /mnt/c/tmp/ch5/build.sh cx5d mW $X
bash /mnt/c/tmp/ch5/build.sh cx5e mW $X
for a in cx5dmW cx5emW; do
  /opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -O binary -R .stack $L/build/out-$a/re4dc-game.elf /tmp/$a.bin 2>/dev/null
  echo "$a image $(sha256sum < /tmp/$a.bin | cut -c1-16) $(stat -c %s /tmp/$a.bin)"
  (cd $L/build/out-$a && sha256sum *.ovl | cut -c1-16,66- | tr '\n' ' '); echo
done
