set -euo pipefail
L=/root/probe/lanes-20261018/ch5regen
cd $L/tools
git apply --exclude=port/dreamcast/tools/ps2_assets/worlds.json --exclude=port/dreamcast/tools/d367/cx_room_fixtures.py $L/st3-tools.diff
python3 - <<'P'
import json
p='port/dreamcast/tools/ps2_assets/worlds.json'
w=json.load(open(p))
w['gc_source_disc2']={"bytes": 1459978240, "sha256": "118640eb02953d5a8234d3f9e27ea535e75b0346b9cf22aa764b65c3d76f1b12"}
open(p,'w').write(json.dumps(w,indent=2)+'\n')
P
git add -A && git -c user.name=ch5regen -c user.email=noreply@anthropic.com commit -qm "st3 lane tool diff (minus worlds rooms list / cx_room_fixtures) + disc2 pin"
git log --oneline -3
ls -la "/mnt/c/Users/Public/ps2/DVD/Resident Evil 4 (USA).iso"
ls -la "/mnt/c/Game Dev/Emulators/re4-assets-private/world-agent-20260926/from-main/ps2-trees/tools/ps2_tpl_decode.py"
if [ ! -x $L/venv/bin/python ]; then python3 -m venv $L/venv; $L/venv/bin/pip -q install numpy==2.5.3 Pillow==12.3.0 2>&1 | tail -3; fi
$L/venv/bin/python -c "import numpy,PIL;print(numpy.__version__,PIL.__version__)"
