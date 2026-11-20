#!/bin/bash
# Fixture-capable split reference disc (as eng-e1b's refdisc.sh): the pristine LE tree (hard links, read only)
# + the refsplit program and overlays; dc/warp.txt and dc/padscript.txt redirected to fixed LBAs so a run patches them.
# The ISO is written straight to E: (C: is short of space).
set -euo pipefail
L=/root/work/lanes/eng-ref
work=$L/.ref
dest=/mnt/e/RE4DC-Lanes/eng-ref/refsplit
src=/root/work/lanes/eng-bench/.m1/pristine
test -s /root/work/lanes/eng-bench/.m1/pristine.json
stage=$work/ref-stage
rm -rf "$stage"; mkdir -p "$stage"
cp -al "$src/." "$stage/"
for f in warp.txt padscript.txt w11.txt qa-menu.txt; do rm -f "$stage/dc/$f"; done
rm -f "$stage/1ST_READ.BIN"
/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy -R .stack -O binary "$work/route/out-refsplit/re4dc-game.elf" "$stage/1ST_READ.BIN"
for f in "$work/route/out-refsplit"/*.ovl; do rm -f "$stage/dc/${f##*/}"; cp "$f" "$stage/dc/"; done
mkdir -p "$dest" "$work/t1"
touch "$work/t1/README.TXT"
for name in warp.txt padscript.txt; do head -c 8192 /dev/zero > "$stage/dc/$name"; done
cp /root/work/lanes/eng-bench/.m1/pristine-ip.bin "$work/pristine-ip.bin"
rm -f "$dest/track03.iso"
genisoimage -quiet -C 0,45000 -G "$work/pristine-ip.bin" -r -J -l -input-charset iso8859-1 -V RE4DCROOM -o "$dest/track03.iso" "$stage"
fp=$work/tree/port/dreamcast/tools/d367/fullplay/fp_iso.py
python3 "$fp" redirect "$dest/track03.iso" /dc/warp.txt 400 8192
python3 "$fp" redirect "$dest/track03.iso" /dc/padscript.txt 420 8192
genisoimage -quiet -G "$work/pristine-ip.bin" -V RE4DCLD -o "$dest/track01-template.iso" "$work/t1"
truncate -s 1241088 "$dest/track01-template.iso"
head -c 710304 /dev/zero > "$dest/track02.raw"
sha256sum "$dest/track03.iso" | cut -d' ' -f1 > "$dest/track03.sha256"
echo '{"warp_lba":400,"pad_lba":420,"kind":"refsplit","fixture_bytes":8192,"gdi":"3\n1 0 4 2048 track01.iso 0\n2 756 0 2352 track02.raw 0\n3 45000 4 2048 track03.iso 0\n"}' > "$dest/base.json"
cp "$work/route/out-refsplit/syms.txt" "$dest/syms.txt"
cp "$work/route/out-refsplit/elf.sha256" "$dest/elf.sha256"
cat "$dest/syms.txt"; ls -la "$dest"
rm -rf "$stage"
