#!/bin/bash
# ch5tex: the four rooms, two Flycasts at a time.
set -euo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5tex
q() { for x in $1; do r=${x%%:*}; a=${x#*:}; bash "$S/c5t-gate1.sh" "$r" "$a" 2>&1 | tail -1 || true; done; }
q "r307:candidate-routecx76mW r310:candidate-routecx76mW" > "$S/gates-q1.txt" &
sleep 20
q "r31c:candidate-routecx80mW r31b:candidate-routecx79mW" > "$S/gates-q2.txt"
wait
cat "$S/gates-q1.txt" "$S/gates-q2.txt"
