#!/bin/bash
# knob-off identity of this round's shared changes (Makefile st3 object flags + st3 hooks; aica_banks.py is a tool):
# the test 15 rP arm from the lane tree vs the round-1 result dad92dad411cc45b (origin/t15/int, same knob set)
L=/root/probe/lanes-20261016/ch5found
bash /mnt/c/tmp/ch5/build.sh cx5w rP
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -O binary -R .stack $L/build/out-cx5wrP/re4dc-game.elf /tmp/cx5wrP.bin 2>/dev/null
echo "cx5wrP image $(sha256sum < /tmp/cx5wrP.bin | cut -c1-16) $(stat -c %s /tmp/cx5wrP.bin) (round 1 base: dad92dad411cc45b 3376304)"
(cd $L/build/out-cx5wrP && sha256sum *.ovl | cut -c1-16,66- | tr '\n' ' '); echo
rm -f /tmp/cx5wrP.bin
