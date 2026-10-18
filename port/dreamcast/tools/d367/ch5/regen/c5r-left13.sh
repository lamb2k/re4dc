#!/bin/bash
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
L=/root/probe/lanes-20261018/ch5regen
grep st3-pak-loose "$S/missing-src.tsv" | cut -f1,2 | tr -d '\r' > "$L/st3loose.tsv"
python3 "$S/c5r_leftkeys.py" "$S/missing-src.tsv" "$L/fixtures" "$L/pairs-st3" "$L/pairs-r3" "$L/pairs-em1f" "$L/pairs-e1" "$L/pairs-e2" "$L/pairs-evq" "$L/vqloose" "$L/emprep-game-249effe5" "$L/prepem-game-249effe5" "$L/pakdisc" 2>&1 | grep -v "^dc/" | head -20
ls "$L/pakdisc" | head; ls "$L/vqloose" | head
