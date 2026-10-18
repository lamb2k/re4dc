#!/bin/bash
# ch5regen: run the remaining island room gates, two Flycasts at a time (two sequential queues).
set -uo pipefail
S=/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
Q1="r300 r301 r304 r306 r307 r308 r309 r30a r30b r30c r30d r30e r30f r310 r311 r312"
Q2="r315 r316 r317 r318 r31a r31d r321 r325 r326 r329 r330 r303:candidate-routecx80mW r327:candidate-routecx80mW r320:candidate-routecx80mW r31c:candidate-routecx80mW r31b:candidate-routecx79mW"
q() { for x in $1; do r=${x%%:*}; a=candidate-routecx76mW; [ "$x" != "$r" ] && a=${x#*:}; bash "$S/c5r-gate1.sh" "$r" "$a" 2>&1 | tail -1; done; }
q "$Q1" > "$S/c16logs/gates-q1.txt" &
sleep 20
q "$Q2" > "$S/c16logs/gates-q2.txt"
wait
cat "$S/c16logs/gates-q1.txt" "$S/c16logs/gates-q2.txt"
