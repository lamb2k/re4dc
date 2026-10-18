#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch4regen
L=/root/probe/lanes-20261018/ch4regen
C="/mnt/c/Game Dev/Emulators/re4-assets-private/ch4regen-20261018"
cp $L/ch4found/snd/aica-c4c/em/*.drs "$C/aica-c4c/em/"
(cd "$C/aica-c4c" && sha256sum em/*.drs > SHA256SUMS && cut -c1-16 SHA256SUMS)
T=$L/tree; D=$T/port/dreamcast/tools/d367/ch4found/regen/cast
for f in c4r-aica2.sh c4r-em11.sh c4r-pub3.sh; do cp $S/$f $D/${f#c4r-}; done
cd $T; git add port/dreamcast/tools/d367/ch4found/regen/cast
git commit -q -m "ch4regen: aica-c4c em1a/em11/em16/em1c by sha-only AICA search (castle layout): 8/8 byte-exact

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0161knP9yvavohe6o4n2fpoV"
git push -q origin HEAD:wip/ch4regen-20261018
git log --oneline -1
grep -c 7398aaaa "/mnt/c/Game Dev/Emulators/re4-assets-private/ch3regen-20261018/MANIFEST.tsv" || true
