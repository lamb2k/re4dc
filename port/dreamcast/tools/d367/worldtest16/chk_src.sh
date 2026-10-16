#!/bin/bash
# chk_src.sh (WSL): terrain B: are world16 rooms/<r>/src.* the shipping level-0 files?
R=/root/probe/world16-20261016/rooms; P="/mnt/c/Game Dev/Emulators/re4-assets-private/t11-20261014"
for r in r100 r102 r103 r104 r105 r106 r107 r108 r109 r10a; do
  d="$P/blackps2/$r"; [ $r = r100 ] && d="$P/r100-smx-tr4"
  for e in re4mesh r4pw ids; do
    a=$(sha256sum $R/$r/src.$e | cut -c1-12); b=$(sha256sum "$d/ps2-world.$e" | cut -c1-12)
    [ "$a" = "$b" ] && s=same || s=DIFF
    echo "$r $e $a $b $s"
  done
done
