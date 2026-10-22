#!/usr/bin/env python3
"""Verify pinned SDK + local patch, materialize an immutable owned overlay."""
import argparse,hashlib,json,subprocess,tarfile,io,tempfile,os
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--sdk',type=Path)
p.add_argument('--receipt',type=Path)
a=p.parse_args();here=Path(__file__).resolve().parent; dc=here.parents[2]
m=json.loads((here/'manifest.json').read_text());sdk=a.sdk or dc/'game/third_party/sh4zam'
assert subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip()==m['sdk_pin'],'SDK pin mismatch'
assert not subprocess.check_output(['git','-C',str(sdk),'status','--porcelain'],text=True).strip(),'dirty SDK base'
patch=here/'0001-strip-sq-api.patch';assert sha(patch)==m['patch_sha256'],'patch identity'
out=a.output.resolve();out.parent.mkdir(parents=True,exist_ok=True)
def verify(folder):
    for n,h in m['files'].items():assert sha(folder/n)==h,('overlay drift',n)
    assert json.loads((folder/'strip-patch-receipt.json').read_text())==m,'overlay receipt'
if out.exists():verify(out)
else:
    # The ceiling prevents Git treating the overlay as a subdirectory of the
    # RE4 worktree and silently ignoring patch paths.
    with tempfile.TemporaryDirectory(prefix='shz-strip-',dir=out.parent) as tmp:
        temp=Path(tmp)
        blob=subprocess.check_output(['git','-C',str(sdk),'archive',m['sdk_pin']])
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            assert all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in archive.getmembers())
            archive.extractall(temp,filter='data')
        subprocess.run(['git','apply','--check',str(patch)],cwd=temp,check=True,env={**os.environ,'GIT_CEILING_DIRECTORIES':str(out.parent)})
        subprocess.run(['git','apply',str(patch)],cwd=temp,check=True,env={**os.environ,'GIT_CEILING_DIRECTORIES':str(out.parent)})
        (temp/'strip-patch-receipt.json').write_text(json.dumps(m,indent=2)+'\n')
        verify(temp)
        os.rename(temp,out)
receipt=dict(overlay=str(out),sdk_pin=m['sdk_pin'],patch_sha256=m['patch_sha256'],files=m['files'])
if a.receipt:a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
