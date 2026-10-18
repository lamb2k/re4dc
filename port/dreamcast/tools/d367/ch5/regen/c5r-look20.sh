#!/bin/bash
set -uo pipefail
G=/root/probe/lanes-20261018/ch5regen/game-249effe5
git -C "$G" ls-files | grep -iE "warps?/.*r3[0-3][0-9a-f]|ch5found.*warp|stagejump" | head -40
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5found-20261016
ls "$E/h-cx76mW/scenarios/cx-r325-walk-p77b/capture" | head -30
grep -a -m5 -i "warp" "$E/h-cx76mW/scenarios/cx-r325-walk-p77b/capture/run-output.txt" | head -5
