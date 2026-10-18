set -euo pipefail
P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
S=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4found-20261016/h-c4hmW
H=/mnt/c/Flycast-Evidence/re4-dreamcast/ch4regen-20261018/h-rg4
[ -e "$H" ] && { echo exists; exit 1; }
mkdir -p "$H/programs" "$H/scenarios"
cp "$S/run-emulator-novsync.py" "$S/cx-harness-provenance.json" "$S/cx-resolved-knobs.txt" "$S/programs-route.json" "$H/"
cp -r "$S/source-snapshots" "$H/"
cp -r "$S/programs/candidate-routec4hmW" "$H/programs/"
cp "$P/stage-scenario.py" "$H/"; cp -r "$P/stage-ext4" "$H/"; rm -rf "${H:?}/stage-ext4/__pycache__"
echo "ch4regen 2026-10-18: recovered-data gate, ch1-2 at current versions (ch2data-20261018 + cast16data-20261016), ch4 byte-exact regen set, arm c4hmW, shared stager copy (base = disc.sha256 beside the kite7 path, a61dfc16). Flycast only." > "$H/PURPOSE.txt"
grep -n "HERE\b\|HERE =" "$H/stage-ext4/stage_scenario.py" | head; cat "$P/stage-ext4/INSTALLED-FROM.txt" | head -3
cat /root/probe/d367-resume-20260927/integration-01/disc-ig27rc1-kite7/disc.sha256
python3 -c "import json;print(json.load(open('$H/cx-harness-provenance.json'))['arm'])"
