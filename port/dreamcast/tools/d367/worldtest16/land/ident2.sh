#!/bin/bash
# ident2.sh (WSL): loadable-image identity (objcopy -O binary, as fp_twin's IDENTITY check), w16mrP vs w16brP.
OC=$(ls /opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy 2>/dev/null || command -v sh-elf-objcopy)
T=$(mktemp -d)
for l in w16mrP w16brP; do
  $OC -O binary /root/probe/lanes/route/out-$l/re4dc-game.elf $T/$l.bin
  echo "$l image $(sha256sum $T/$l.bin | cut -c1-16) bytes $(stat -c %s $T/$l.bin)"
done
cmp -s $T/w16mrP.bin $T/w16brP.bin && echo "IMAGE IDENTICAL" || echo "IMAGE DIFFERS"
rm -rf $T
