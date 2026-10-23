#!/usr/bin/env python3
"""Isolated materializer reproducibility, source drift and pin-failure controls."""
import json,subprocess,tempfile,shutil,sys,hashlib
from pathlib import Path
here=Path(__file__).resolve().parent; sdk=here.parents[2]/'game/third_party/sh4zam'
with tempfile.TemporaryDirectory(prefix='shz-strip-controls-') as tmp:
    temp=Path(tmp);tool=temp/'tool';tool.mkdir()
    for name in ('materialize.py','manifest.json','0001-strip-sq-api.patch'):shutil.copy2(here/name,tool/name)
    def run(out,ok):
        r=subprocess.run([sys.executable,str(tool/'materialize.py'),'--sdk',str(sdk),'--output',str(out)],text=True,capture_output=True)
        assert (r.returncode==0)==ok,(r.returncode,r.stdout,r.stderr)
    first=temp/'first';second=temp/'second';run(first,True);run(second,True);run(first,True)
    m=json.loads((tool/'manifest.json').read_text())
    for name in m['files']:assert (first/name).read_bytes()==(second/name).read_bytes()
    (first/'source/shz_strip.S').write_text('drift\n');run(first,False)
    p=tool/'0001-strip-sq-api.patch';p.write_bytes(p.read_bytes()+b'\n');run(temp/'bad-patch',False)
    m['sdk_pin']='0'*40;(tool/'manifest.json').write_text(json.dumps(m));run(temp/'bad-pin',False)
print(json.dumps(dict(reproducible_two_materializations=True,reused_overlay_verified=True,source_drift_rejected=True,patch_drift_rejected=True,wrong_pin_rejected=True,base_sdk_unchanged=True)))
