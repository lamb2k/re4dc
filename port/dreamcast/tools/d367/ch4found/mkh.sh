#!/bin/bash
# mkh.sh <ARM>: private harness for arm (copied from ch3found h-cxc3umW, as c3boss.sh does)
set -euo pipefail
ARM=$1
P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
CAND="$P/programs/candidate-route${ARM}"
S="/mnt/c/Flycast-Evidence/re4-dreamcast/ch3found-20261016/h-cxc3umW"
H="/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-${ARM}"
[ -d "$H" ] && { echo "exists $H"; exit 0; }
mkdir -p "$H/programs" "$H/scenarios"
for f in run-emulator-novsync.py stage-scenario-copy.py stage-scenario-ext4.py stage-scenario-v2.provenance.json stage-scenario-v2.py stage-scenario.py cx-harness-provenance.json; do cp "$S/$f" "$H/"; done
cp -r "$S/stage-ext4" "$S/source-snapshots" "$H/"
cp -r "$CAND" "$H/programs/"
ARM=$ARM python3 - "$P/programs-route.json" "$H/programs-route.json" <<'PY'
import json,sys,os
a='candidate-route'+os.environ['ARM']; d=json.load(open(sys.argv[1])); json.dump({a:d[a]},open(sys.argv[2],'w'),indent=2)
PY
sed -i "s/cxc3umW/${ARM}/g" "$H/cx-harness-provenance.json"
cp /root/probe/lanes/route/out-${ARM}/resolved-knobs.txt "$H/cx-resolved-knobs.txt"
echo "ch4found16 2026-10-16: chapter 4 (castle 4-1..4-4) room first-pass runs on STAGE_OVL=1 SS_POOL_TOP=1 ROUTE_CH41=1, arm ${ARM}. Flycast only." > "$H/PURPOSE.txt"
grep -n "cxc3" "$H"/*.py "$H"/*.json 2>/dev/null | head
echo "HARNESS $H"
