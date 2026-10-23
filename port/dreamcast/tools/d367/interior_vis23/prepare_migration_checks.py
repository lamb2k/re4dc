#!/usr/bin/env python3
"""Exercise the real optional prepare bridge with private copied-input negatives."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from policy_migration import EXPECTED

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for name in ('old','original','current','iso-receipt','scratch','out'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();tool=Path(__file__).with_name('prepare.py');cases=[]
 with tempfile.TemporaryDirectory(prefix='iv23-prepare-migration-',dir=a.scratch) as tmp:
  root=Path(tmp);old=root/'old';original=root/'original'
  old.mkdir();original.mkdir()
  for name in ('ps2-world.json','ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):shutil.copyfile(a.old/name,old/name)
  for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):shutil.copyfile(a.original/name,original/name)
  report=json.loads((old/'ps2-world.json').read_text());report['foreign_report_negative']=True
  (old/'foreign.json').write_text(json.dumps(report))
  b=bytearray((original/'ps2-world.r4pw').read_bytes());b[17]^=1;(original/'foreign.r4pw').write_bytes(b)
  log=root/'camera.txt';log.write_text('PCCULL frame=1 active=0 cell=-1 eye=-8800,1000,-8500\n')
  tests=[('baseline',None),('copied-report','unreviewed copied conversion report'),
   ('copied-original','unreviewed copied original policy'),('wrong-room','policy migration is r111 only'),
   ('stale-append','policy migration refuses stale append metadata'),('ordinary-no-migration','base report package mismatch')]
  for name,error in tests:
   out=root/name
   if name=='stale-append':
    (out/'inputs').mkdir(parents=True);(out/'inputs/append.json').write_text('{}')
   command=[sys.executable,str(tool),'--private',str(out),'--mesh',str(a.current/'ps2-world.re4mesh'),
    '--policy',str(a.current/'ps2-world.r4pw'),'--ids',str(a.current/'ps2-world.ids'),
    '--original-policy',str(original/('foreign.r4pw' if name=='copied-original' else 'ps2-world.r4pw')),
    '--base-report',str(old/('foreign.json' if name=='copied-report' else 'ps2-world.json')),
    '--log',str(log),'--room','112' if name=='wrong-room' else '111']
   if name!='ordinary-no-migration':command+=['--policy-migration-iso-receipt',str(a.iso_receipt)]
   result=subprocess.run(command,capture_output=True,text=True)
   if error:
    assert result.returncode and error in result.stderr,(name,result.stdout,result.stderr)
    assert not (out/'work/meta.json').exists(),'failed bridge generated qualified metadata'
   else:
    assert not result.returncode,(result.stdout,result.stderr)
    meta=json.loads((out/'work/meta.json').read_text());receipt=json.loads((out/'prepare-receipt.json').read_text())
    assert meta['static_provenance']['kind']=='exact-reviewed-policy-migration'
    assert sha(out/'inputs/base-report.json')==EXPECTED['report']
    assert sha(out/'inputs/original.r4pw')==EXPECTED['original_policy']
    assert meta['input_hashes']['ps2-world.r4pw']==EXPECTED['current_policy']
    assert meta['input_hashes']['policy-migration.json']==sha(out/'inputs/policy-migration.json')
    assert receipt['policy_migration']['old_report_unchanged'] and not receipt['policy_migration']['raw_iso_reread']
    assert receipt['pinned_tool_hashes']['pvs_prep.py']!=receipt['tool_hashes']['pvs_prep.py']
   cases.append(dict(name=name,expected='pass' if error is None else error,passed=True))
 report=dict(host_only=True,source_prepare_sha256=sha(tool),tool_sha256=sha(Path(__file__)),cases=cases)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n')
 print('PASS real prepare bridge baseline and five copied-input/default-path negatives')

if __name__=='__main__':main()
