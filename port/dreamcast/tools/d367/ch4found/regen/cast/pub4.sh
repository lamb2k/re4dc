#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261018/ch4regen
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018/texpak/dc"
mkdir -p "$C"; cp $L/texpak/tex-z9.pak "$C/tex.pak"
(cd "$C/.." && sha256sum dc/tex.pak > SHA256SUMS && sha256sum -c --quiet SHA256SUMS && echo C-SHA-OK)
T=$L/tree; D=$T/port/dreamcast/tools/d367/ch4found/regen/cast
cp $S/c4r-texpak.sh $D/texpak.sh; cp $S/c4r-pub4.sh $D/pub4.sh
cd $T; git add port/dreamcast/tools/d367/ch4found/regen/cast
git commit -q -m "ch4regen: dc/tex.pak (tex-z9 5ed4ba5a) byte-exact on ch3regen tex-c34b 7398aaaa

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0161knP9yvavohe6o4n2fpoV"
git push -q origin HEAD:wip/ch4regen-20261018
git log --oneline -1
