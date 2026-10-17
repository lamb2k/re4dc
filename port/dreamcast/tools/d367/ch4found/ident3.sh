set -u
L=/root/probe/lanes-20261016/ch4found
cd $L/tree
rm -rf /root/probe/lanes/route/out-c4idh3rP
T=$L/tree K=$L/k LP=c4idh3 bash port/dreamcast/tools/d367/test15/t15-build.sh rP > $L/k/ident3-build.log 2>&1; echo build rc=$?
OC=/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy
O=/root/probe/lanes/route/out-c4idh3rP; $OC -O binary -R .stack $O/re4dc-game.elf $L/k/img-c4idh3.bin; sha256sum $L/k/img-c4idh3.bin $L/k/img-c4idb2.bin
(cd $O && find . -name '*.ovl' -not -path './obj/*' | sort | xargs -r sha256sum) > $L/k/ovl-c4idh3.txt; wc -l < $L/k/ovl-c4idh3.txt
cmp $L/k/img-c4idb2.bin $L/k/img-c4idh3.bin && echo IMAGE IDENTICAL
diff $L/k/ovl-c4idb2.txt $L/k/ovl-c4idh3.txt && echo OVERLAYS IDENTICAL
echo IDENT3 DONE
