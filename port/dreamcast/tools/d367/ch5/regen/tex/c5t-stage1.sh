#!/bin/bash
# ch5regen: stage one gate scenario through the lane-private harness copy. usage: c5r-stage1.sh <room> <arm>
set -euo pipefail
ROOM=${1:?room}; ARM=${2:?arm}
L=/root/probe/lanes-20261018/ch5tex
E=/mnt/c/Flycast-Evidence/re4-dreamcast/ch5regen-20261018
H=$E/hroot/h
mkdir -p "$L/stage" "$E/disccache" "$L/gate/logs"
export RE4DC_HARNESS=$H RE4DC_STAGE_ROOT=$L/stage RE4DC_DISCCACHE=$E/disccache
python3 "$H/stage-ext4/stage_scenario.py" "c5t-$ROOM" --arm "$ARM" --programs "$H/programs-route.json" \
  --overlay /mnt/c/Flycast-Evidence/re4-dreamcast/r11-media-overlay-r1/payloads --fixture "$L/gate/fix/$ROOM.json" > "$L/gate/logs/stage-$ROOM.json" 2>&1 || true
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['status'],d['disc_sha256'],d['base_sha256'][:8])" "$L/gate/logs/stage-$ROOM.json" 2>/dev/null || tail -4 "$L/gate/logs/stage-$ROOM.json"
