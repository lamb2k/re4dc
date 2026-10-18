set -uo pipefail
T=/root/probe/lanes-20261018/ch4regen/cxtree-b47/port/dreamcast/tools
python3 -c "
import json;p=json.load(open('$T/ps2_assets/worlds.json'))
for k,v in p['tools'].items(): print(k, v.get('url'), v.get('archive_sha256'))
"
for n in mono powerpc-linux-gnu-gcc qemu-ppc g++; do printf '%s: ' $n; command -v $n || echo none; done
python3 -c "import numpy,PIL;print(numpy.__version__,PIL.__version__)"
ls -d /root/probe/*/.venv /root/probe/*/*/.venv /root/probe/lanes-2026101*/*/tools/.assets 2>/dev/null
grep -n "tools\b\|a.tools\|def fetch\|def tool" $T/build_ps2_assets.py | head -30
