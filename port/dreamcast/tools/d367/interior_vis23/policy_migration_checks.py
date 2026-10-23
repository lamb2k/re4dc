#!/usr/bin/env python3
"""Fail-closed controls for the one pinned conversion-policy migration."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from policy_migration import verify

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('old','original','current','iso-receipt'):ap.add_argument('--'+name,type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 names={'old':('ps2-world.json','ps2-world.r4pw','ps2-world.ids','ps2-world.re4mesh'),
        'original':('ps2-world.r4pw','ps2-world.ids','ps2-world.re4mesh'),
        'current':('ps2-world.r4pw','ps2-world.ids','ps2-world.re4mesh')}
 result=verify(a.old,a.original,a.current,a.iso_receipt)
 assert result['proof_uses_exact_current_affines'] and not result['policy_equal'] and not result['runtime_admitted']
 runs=[]
 with tempfile.TemporaryDirectory(prefix='iv23-migration-checks-',dir='/dev/shm') as td:
  work=Path(td)
  for group,files in names.items():
   (work/group).mkdir()
   for name in files:shutil.copyfile(getattr(a,group)/name,work/group/name)
  iso=work/'iso.json';shutil.copyfile(a.iso_receipt,iso)
  def check():return verify(work/'old',work/'original',work/'current',iso)
  check()
  for group,files in names.items():
   for name in files:
    p=work/group/name;data=p.read_bytes();changed=bytearray(data);changed[min(17,len(changed)-1)]^=1;p.write_bytes(changed)
    try:check()
    except AssertionError:pass
    else:raise AssertionError('unreviewed bytes admitted: '+str(p))
    p.write_bytes(data);runs.append(group+'/'+name)
  data=iso.read_bytes();iso.write_bytes(data+b' ')
  try:check()
  except AssertionError:pass
  else:raise AssertionError('changed source ISO receipt admitted')
  runs.append('iso-receipt');iso.write_bytes(data);check()
 out=dict(host_only=True,baseline_verified=True,mutations_rejected=runs,
          verifier_sha256=hashlib.sha256(Path(__file__).with_name('policy_migration.py').read_bytes()).hexdigest(),
          tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n')
 print('PASS pinned migration baseline and',len(runs),'unreviewed-input negatives; no original input writes')

if __name__=='__main__':main()
