set -euo pipefail
# c3g-gh.sh: private harness h-c3g = copy of ch3found h-c3wmW + arm c3gmW + the shared playability stager (read-only copy).
P="/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/continuation-20260927/playability-r11-r1"
S=/mnt/c/Flycast-Evidence/re4-dreamcast/ch3found-20261016/h-c3wmW
H=/mnt/c/Flycast-Evidence/re4-dreamcast/ch3gate-20261018/h-c3g
[ -e "$H" ] && { echo exists; exit 1; }
mkdir -p "$H/programs" "$H/scenarios"
cp "$S/run-emulator-novsync.py" "$S/cx-harness-provenance.json" "$S/cx-resolved-knobs.txt" "$H/"
cp "$P/programs-route.json" "$H/"
cp -r "$S/source-snapshots" "$H/"
cp -r "$P/programs/candidate-routec3gmW" "$H/programs/"
cp "$P/stage-scenario.py" "$H/"; cp -r "$P/stage-ext4" "$H/"; rm -rf "${H:?}/stage-ext4/__pycache__"
python3 - "$H" <<'PY'
import json, sys
h = sys.argv[1]; p = h + '/cx-harness-provenance.json'
d = json.load(open(p)); old = d['arm']; d['arm'] = 'candidate-routec3gmW'
d['ch3gate'] = {'copied_from': 'ch3found-20261016/h-c3wmW', 'old_arm': old,
                'elf_sha256': open('/root/probe/lanes/route/out-c3gmW/elf.sha256').read().split()[0]}
json.dump(d, open(p, 'w'), indent=1)
r = json.load(open(h + '/programs-route.json'))
print('arm', old, '->', d['arm'], 'route entries with c3gmW:', sum('c3gmW' in json.dumps(x) for x in (r if isinstance(r, list) else r.values())))
PY
echo "ch3gate 2026-10-18: recovered-data gate, ch1-2 at current versions (ch2data-20261018 + cast16data-20261016), ch3regen + ch4regen data, arm c3gmW (CH4REC mW, PE2/PE3/PE4 regenerated), shared stager copy. Flycast only." > "$H/PURPOSE.txt"
sha256sum "$H/programs/candidate-routec3gmW/1ST_READ.BIN" | cut -c1-16
