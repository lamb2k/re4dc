#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
O=/root/probe/lanes-20261018/ch4regen/out-cast
rm -rf "${O:?}"; mkdir -p "$O"
python3 $S/c4r-c16stage.py $S/c4r-missing-src.tsv $O /root/probe/lanes-20261018/ch4regen/c16reg/b /root/probe/lanes-20261018/ch4regen/ch4found/cast
grep MISSING $O/MANIFEST.tsv | cut -f2,3 || true
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018/cast"
mkdir -p "$C"; cp -r "$O"/. "$C"/
cd "$C" && sha256sum -c --quiet SHA256SUMS && echo C-SHA-OK
