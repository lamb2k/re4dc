#!/bin/bash
# ch5regen: gate fixtures per island room from the recorded runs (cx76mW p77b; cx80mW r303/r320/r327/r31c; cx79mW r31b).
set -euo pipefail
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch5regen
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
OUT=/root/probe/lanes-20261018/ch5regen/gate/fix
A=()
for d in "$E"/h-cx76mW/scenarios/cx-r3*-walk-p77b; do
  r=$(basename "$d" | cut -d- -f2)
  case $r in r303|r320|r327|r31c|r31b) continue;; esac
  A+=("$r=$d")
done
A+=("r303=$E/h-cx80mW/scenarios/cx-r303-walk-p81" "r327=$E/h-cx80mW/scenarios/cx-r327-walk-p81" "r320=$E/h-cx80mW/scenarios/cx-r320-walk-g80" "r31c=$E/h-cx80mW/scenarios/cx-r31c-walk-k80f" "r31b=$E/h-cx79mW/scenarios/cx-r31b-walk-b79")
python3 "$S/c5r_gatefix.py" "/mnt/c/Game Dev/Emulators/re4dc-recovery/harvest.db" "$OUT" "${A[@]}"
