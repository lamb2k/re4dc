#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
O=/root/probe/lanes-20261018/ch4regen/out-forch3
rm -rf "${O:?}"; mkdir -p "$O"
python3 $S/c4r-forch3.py "/mnt/c/Game Dev/Emulators/re4-assets-private/ch3regen-20261018/NEED-FROM-CH4-cast16.tsv" $O \
  /root/probe/lanes-20261018/ch4regen/c16reg /root/probe/lanes-20261018/ch4regen/c16old /root/probe/lanes-20261016/cast16/conv4 /root/probe/lanes-20261018/ch4regen/ch4found/cast
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018/for-ch3"
mkdir -p "$C"; cp -r "$O"/. "$C"/
cd "$C" && sha256sum -c --quiet SHA256SUMS && echo C-SHA-OK
