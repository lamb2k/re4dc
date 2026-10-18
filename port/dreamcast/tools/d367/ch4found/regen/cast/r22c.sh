#!/bin/bash
# ch4regen: replay of the ch4found 13:31:35Z reg-22c build (regcast-ch4 copy + r22c rooms, model_registry).
set -euo pipefail
L=/root/probe/lanes-20261016/ch4found
mkdir -p "$L/cast"
rm -rf "${L:?}/cast/regcast-ch4"
cp -a /root/probe/lanes-20261016/cast16/conv4/regcast-ch4 "$L/cast/regcast-ch4"
cd "$L/cast/regcast-ch4"
python3 - <<'EOF'
import re
for f in ['merchant18-c0/ps2-v1/revision-manifest.json','merchant18-o0/ps2-v1/revision-manifest.json','ps2-overlay/integration-bundle/catalog.json']:
    s=open(f).read()
    s2,n=re.subn(r'("r229",\s*\n(\s*)"r22a")(\s*\n\s*\])', lambda m: m.group(1)+',\n'+m.group(2)+'"r22c"'+m.group(3), s)
    open(f,'w').write(s2); print(f,n)
EOF
cd "$L/tree"
M=port/dreamcast/tools/d367/model-registry
grep -o '"cast_dir": "[^"]*"' $M/ps2-ch4-r22c.json
o=$L/cast/reg-22c; rm -rf "${o:?}"
python3 port/dreamcast/tools/d367/model_registry.py $M/ps2-ch4-r22c.json $o --tree $L/tree --package-room 22c --pool --wide-identity --pack-bones 64 > $o.log 2>&1 && sha256sum $o/package/r22c/registry.re4nmr || tail -2 $o.log
