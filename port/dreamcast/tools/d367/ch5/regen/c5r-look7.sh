set -uo pipefail
T=/root/probe/lanes-20261018/ch4regen/cxtree-b47/port/dreamcast/tools
grep -n "def host_tools" -A30 $T/build_ps2_assets.py
grep -n "PROFILE *=\|def build\b\|def build(" $T/build_ps2_assets.py
cat $T/ps2_assets/requirements.txt
wc -l $T/build_ps2_assets.py
ls $T/ps2_assets/ $T/ps2_assets/*.json 2>/dev/null
python3 -c "import json;p=json.load(open('$T/ps2_assets/worlds.json'));print({k:(v if not isinstance(v,(list,dict)) or len(str(v))<300 else str(v)[:300]) for k,v in p.items()})" 2>&1 | head -30
