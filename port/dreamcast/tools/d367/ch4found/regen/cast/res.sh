#!/bin/bash
# ch4regen: replay of /c/tmp/ch4/cast/res6.sh (10-17 08:35Z) -> resident-ch4d.bin (target 9419a6b6).
set -euo pipefail
L=/root/probe/lanes-20261018/ch4regen
T=$L/tree/port/dreamcast/tools/d367; R=$T/vram/resident
mkdir -p $L/ch4found/vram
B="/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/datasets/ch2data-20261016/files/dc/resident.bin"
LISTS="$R/r206.tsv $R/r210.tsv $R/r211.tsv $R/r212.tsv $R/r213.tsv $R/r214.tsv $R/r215.tsv $R/r216.tsv $R/r217.tsv $R/r218.tsv $R/r219.tsv $R/r21b.tsv $R/r21d.tsv $R/r220.tsv $R/r222.tsv $R/r223.tsv $R/r224.tsv $R/r225.tsv $R/r226.tsv $R/r227.tsv $R/r229.tsv $R/r22b.tsv"
sha256sum "$B" | cut -c1-16
python3 $T/water/water_resident.py pack "$B" $L/ch4found/vram/resident-ch4d.bin $LISTS | tail -2
sha256sum $L/ch4found/vram/resident-ch4d.bin | cut -c1-16
