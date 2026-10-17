#!/bin/bash
# b2.sh: gate arms on the rebased lane tree (test 17 recipe = ch2-build.sh): on (recipe, T15_PG default) / off (T15_PG="")
B="/mnt/c/Game Dev/Emulators/_scratch_farmprop17/build.sh"
TOOL=/opt/toolchains/dc/sh-elf/bin
T15_PG="" bash "$B" fp17o rP | tail -1 | cut -c1-90
T15_PG="" bash "$B" fp17o rW | tail -1 | cut -c1-90
T15_PG="" bash "$B" fp17o rT | tail -1 | cut -c1-90
bash "$B" fp17q rW | tail -1 | cut -c1-90
bash "$B" fp17q rT | tail -1 | cut -c1-90
grep -o "PROP_GATE=[0-9]" /root/probe/lanes/route/out-fp17qrW/candidate.txt /root/probe/lanes/route/out-fp17orW/candidate.txt
# identity: off image vs base 9965feae (fp17zrP); both built with ch2-build rP
for l in fp17zrP fp17orP; do O=/root/probe/lanes/route/out-$l; $TOOL/sh-elf-objcopy -R .stack -O binary $O/re4dc-game.elf /tmp/$l.bin; echo "$l image $(sha256sum < /tmp/$l.bin | cut -c1-16) ovl $(cd $O && sha256sum *.ovl | sha256sum | cut -c1-16) n=$(ls $O/*.ovl | wc -l)"; rm /tmp/$l.bin; done
