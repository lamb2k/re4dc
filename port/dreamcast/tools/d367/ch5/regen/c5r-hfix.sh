#!/bin/bash
# ch5regen: add the stager's remaining ROOT input (gameplay/verify_cost_inputs.py) to the lane harness copy; clear the
# lane's own failed r305 staging leftovers.
set -euo pipefail
SH="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927"
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018
L=/root/probe/lanes-20261018/ch5regen
mkdir -p "$E/hroot/gameplay"
cp "$SH/gameplay/verify_cost_inputs.py" "$E/hroot/gameplay/"
ls "$L/stage/scen" 2>/dev/null || true
if [ -d "$L/stage/scen/c5r-r305" ]; then rm -rf "${L:?}/stage/scen/c5r-r305"; fi
if [ -d "$E/hroot/h/scenarios/c5r-r305" ]; then rm -rf "${E:?}/hroot/h/scenarios/c5r-r305"; fi
ls "$E/hroot/h/scenarios"
