#!/bin/bash
# ch5regen: the two pair keys (38679b3b 32x256, 9c7695f7 64x128): pairs2 -> addss raw -> vqroom (vq2) [-> vq3].
# Tries single VQ and a second VQ pass over the first output; verifies against the targets.
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
T=$L/game-249effe5/port/dreamcast/tools
W=$L/vqpair
export PYTHONDONTWRITEBYTECODE=1
rm -rf "${W:?}"; mkdir -p "$W"
ls -la "$L/pairs-e1/38679b3b-1513dade.re4tex" "$L/pairs-e2/9c7695f7-b4764a7f.re4tex"
sha256sum "$L/pairs-e1/38679b3b-1513dade.re4tex" "$L/pairs-e2/9c7695f7-b4764a7f.re4tex" | cut -c1-16
cd /tmp
python3 "$S/c5r_vqkeys.py" "$T" "$W/v1" "$L/pairs-e1/38679b3b-1513dade.re4tex" "$L/pairs-e2/9c7695f7-b4764a7f.re4tex"
python3 "$S/c5r_vqkeys.py" "$T" "$W/v2" "$W"/v1/out/*.re4tex || true
sha256sum "$W"/v1/out/* "$W"/v2/out/* 2>/dev/null | cut -c1-16
grep -E "38679b3b|9c7695f7" "$S/missing-src.tsv" | cut -f2,3 | cut -c1-30
python3 "$S/c5r_verify.py" "$S/missing-src.tsv" "$L/found.tsv" "$W"
