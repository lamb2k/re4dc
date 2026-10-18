#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261018/ch4regen
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018"
mkdir -p "$C/aica-c4c/em" "$C/vram/dc"
for e in em14 em19 em1b em2d; do cp $L/ch4found/snd/aica-c4c/em/$e.drs "$C/aica-c4c/em/"; done
cp $L/ch4found/vram/resident-ch4d.bin "$C/vram/dc/resident.bin"
(cd "$C/aica-c4c" && sha256sum em/*.drs > SHA256SUMS && cat SHA256SUMS | cut -c1-16)
(cd "$C/vram" && sha256sum dc/resident.bin > SHA256SUMS && cut -c1-16 SHA256SUMS)
T=$L/tree; D=$T/port/dreamcast/tools/d367/ch4found/regen/cast
for f in c4r-c3conv.sh c4r-c3drs.sh c4r-c3reg.sh c4r-compall.py c4r-aica1.sh c4r-res.sh c4r-srcsha.py c4r-pub2.sh; do cp $S/$f $D/${f#c4r-}; done
cd $T; git add port/dreamcast/tools/d367/ch4found/regen/cast
git commit -q -m "ch4regen: conv3 castle regs for ch3 (4/4), aica-c4c em14/em19/em1b/em2d, resident-ch4d.bin: byte-exact

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0161knP9yvavohe6o4n2fpoV"
git push -q origin HEAD:wip/ch4regen-20261018
git log --oneline -1
