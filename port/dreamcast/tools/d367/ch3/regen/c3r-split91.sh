set -euo pipefail
L=/root/probe/lanes-20261018/ch3regen
S=/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch3regen
A="/mnt/c/Game Dev/Emulators/re4-assets-private"
P="$A/ch3regen-20261018/paks"
cd /tmp
python3 "$S/c3r_split91.py" "$L/trees/origin/lane/castle-1015/port/dreamcast/tools" "$S/missing.json" "$S/cover.json" \
  "$A/ch2data-20261018" "$P/tex-c33b-15975911.pak" "$P/tex-c34b-7398aaaa.pak" "$P/tex-t12d-43be4b59.pak"
sha256sum "$A/ch4regen-20261018/aica-c4c/em/em1c.drs" | cut -c1-8 || true
python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['ch3found-20261016']['em/em1c.drs']['sha256'][:8])" "$S/missing.json"
