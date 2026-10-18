#!/bin/bash
# ch5regen: cast16 conv5/conv6 member conversions, Windows python as recorded (c5reconv.sh / k10 commands).
# usage: c5r-c16conv.sh <t5|t6> <conv5|conv6> <preset>...
set -euo pipefail
R=//wsl.localhost/Ubuntu-24.04/root/probe/lanes-20261018/ch5regen/c16
T=$R/$1/port/dreamcast/tools; W=$R/$2; shift 2
export PS2CAST_INPUTS=$R/inputs
LOG=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen/c16logs
mkdir -p "$LOG"
cd /c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
for n in "$@"; do
  rm -rf "${W:?}/${n:?}"
  if timeout 1500 python "$T/ps2_cast.py" convert "$n" "$W/$n" --bone-tol 0.05 > "$LOG/conv-$n.log" 2>&1; then echo "conv ok $n"; else echo "conv FAIL $n: $(grep -E 'Error' "$LOG/conv-$n.log" | tail -1 | cut -c1-200)"; fi
done
