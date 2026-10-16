#!/bin/bash
# knob-off identity: t15-build rP from origin/t15/int 82af1cf3 (pristine worktree) vs lane/ch5found16 HEAD
L=/root/probe/lanes-20261016/ch5found
cd /root/probe/lanes-20261016/ch5found/tree
if [ ! -d $L/base ]; then git worktree add --detach $L/base 82af1cf3 >/dev/null 2>&1; (cd $L/base && git submodule update --init --recursive >/dev/null 2>&1); fi
T=$L/base bash /mnt/c/tmp/ch5/build.sh cx5b rP
bash /mnt/c/tmp/ch5/build.sh cx5k rP
for a in cx5brP cx5krP; do
  /opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -O binary -R .stack $L/build/out-$a/re4dc-game.elf /tmp/$a.bin 2>/dev/null
  echo "$a image $(sha256sum < /tmp/$a.bin | cut -c1-16) $(stat -c %s /tmp/$a.bin)"
  (cd $L/build/out-$a && sha256sum *.ovl | cut -c1-16,66-)
done
