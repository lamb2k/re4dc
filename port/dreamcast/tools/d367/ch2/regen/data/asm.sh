set -euo pipefail
L=/root/probe/lanes-20261017r/ch2regen; W=$L/resrc
rm -rf "${W:?}/x" "${W:?}/final"; mkdir -p $W/x $W/final
git -C $L/tree archive 7711ec04 port/dreamcast/tools/d367/vram port/dreamcast/tools/d367/water | tar -x -C $W/x
D=$W/x/port/dreamcast/tools/d367
python3 $D/vram/resident_keys.py pack $W/b.bin $D/vram/resident/*.tsv | tail -1
python3 $D/water/water_resident.py pack $W/b.bin $W/final/resident.bin $D/water/resident/*.tsv | tail -1
sha256sum $W/final/resident.bin | cut -c1-16
cp $W/final/resident.bin "/mnt/c/Game Dev/Emulators/re4-assets-private/ch2regen-20261018/resident-cfcc77d6.bin"
python3 /mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen/assemble.py
