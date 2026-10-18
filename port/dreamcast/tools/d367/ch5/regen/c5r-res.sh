#!/bin/bash
# ch5regen: dc/resident.bin (gatlas17 res17g) = resident_keys.py pack + water_resident.py pack at 0cb61387.
set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
O=$L/res17g
rm -rf "${O:?}"; mkdir -p "$O/src"
git -C "$L/tree" archive 0cb61387 port/dreamcast/tools/d367/vram port/dreamcast/tools/d367/water | tar -x -C "$O/src"
cd "$O/src/port/dreamcast/tools/d367"
ls vram/resident | wc -l; ls water/resident | wc -l
python3 vram/resident_keys.py pack "$O/a.bin" vram/resident/*.tsv | tail -2
python3 water/water_resident.py pack "$O/a.bin" "$O/resident.bin" water/resident/*.tsv | tail -2
sha256sum "$O/resident.bin"
