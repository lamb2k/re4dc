#!/bin/bash
# ch5regen: the same summary over the recorded ch5found16 runs (reference for the gate results). Read-only.
set -uo pipefail
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
G=/root/probe/lanes-20261018/ch5regen/game-249effe5/port/dreamcast/tools/d367
for d in "$E"/h-cx76mW/scenarios/cx-r3*-walk-p77b "$E"/h-cx80mW/scenarios/cx-r303-walk-p81 "$E"/h-cx80mW/scenarios/cx-r327-walk-p81 "$E"/h-cx80mW/scenarios/cx-r320-walk-g80 "$E"/h-cx80mW/scenarios/cx-r31c-walk-k80f "$E"/h-cx79mW/scenarios/cx-r31b-walk-b79; do
  O=$d/capture/run-output.txt; [ -f "$O" ] || continue
  CG=$(python3 "$G/cast_gc.py" "$O" --allow "$G/castgc/allow.tsv" 2>&1 | tail -1 | grep -oE '\((PASS|FAIL)\)|exit [0-9]|no census' | head -1)
  echo "$(basename "$d") halt=$(grep -ac HALT "$O") fault=$(grep -ac FAULT "$O") missing=$(grep -ac 'RE4DC MISSING' "$O") texfail=$(grep -ac 'texchk: FAIL' "$O") rooms=$(grep -aoE 'room enter [0-9a-f]+' "$O" | awk '{print $3}' | sort -u | tr '\n' ',') castgc=$CG"
done
