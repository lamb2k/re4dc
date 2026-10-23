#!/usr/bin/env python3
"""Repack owned SDK sources as a reviewable patch against the clean public pin."""
import argparse,difflib,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);a=p.parse_args();here=Path(__file__).resolve().parent;dc=here.parents[2];base=dc/'game/third_party/sh4zam'
m=json.loads((here/'manifest.json').read_text());assert subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()==m['sdk_pin']
assert not subprocess.check_output(['git','-C',str(base),'status','--porcelain'],text=True).strip()
subprocess.run(['python3',str(here/'check_area.py'),'--overlay',str(a.source)],check=True)
names=['include/sh4zam/shz_strip.h','source/shz_strip.cpp','source/shz_strip.S','source/shz_strip_area.inc','source/shz_strip_fused.inc','CMakeLists.txt']
patch='';files={}
for name in names:
    body=(a.source/name).read_text();files[name]=hashlib.sha256(body.encode()).hexdigest()
    patch+=f'diff --git a/{name} b/{name}\n'
    if (base/name).exists():
        old=(base/name).read_text();patch+=''.join(difflib.unified_diff(old.splitlines(True),body.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    else:
        lines=body.splitlines();patch+=f'new file mode 100644\n--- /dev/null\n+++ b/{name}\n@@ -0,0 +1,{len(lines)} @@\n'+''.join('+'+x+'\n' for x in lines)
(here/'0001-strip-sq-api.patch').write_text(patch)
m.update(files=files,patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),stage='Fused six-phase short scan, mask/lean emission and batch lease; performance acceptance open')
(here/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m))
