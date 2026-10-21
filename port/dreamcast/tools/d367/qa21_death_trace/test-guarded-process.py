#!/usr/bin/env python3
"""Fault injection proves cleanup after sampling and receipt exceptions."""
import json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
import guarded_process as g
rows=[]
real=g.subprocess.Popen
for mode in ('sampler','receipt','first-identity'):
 captured=[]
 def spawn(*args,**kwargs):
  child=real(*args,**kwargs);captured.append(child);return child
 def sample():raise RuntimeError('injected sampler failure')
 calls=[0];real_identity=g.identity
 def flaky_identity(pid):
  calls[0]+=1
  if calls[0]==1:raise RuntimeError('injected identity read failure')
  return real_identity(pid)
 with tempfile.TemporaryDirectory(prefix='qa21-supervisor-test-') as tmp:
  tmp=Path(tmp);owner=tmp if mode=='receipt' else tmp/'owner.json'
  with (tmp/'log').open('wb') as stream,patch.object(g.subprocess,'Popen',spawn),patch.object(g,'identity',flaky_identity if mode=='first-identity' else real_identity):
   try:g.run_guarded(['sleep','60'],tmp,os.environ.copy(),stream,sample,owner,tick=.01)
   except (RuntimeError,IsADirectoryError):pass
   else:raise AssertionError('Fault did not propagate')
  child=captured[0];assert child.poll() is not None
  members=[]
  for entry in Path('/proc').iterdir():
   if entry.name.isdigit():
    try:
     identity=real_identity(int(entry.name))
     if identity['pgid']==child.pid:members.append(identity)
    except (FileNotFoundError,ProcessLookupError):pass
  assert not members,members
  rows.append({'injected_exception':mode,'pid':child.pid,'returncode':child.returncode,'remaining_group_members':members,'pass':True})
print(json.dumps({'status':'PASS','cases':rows},indent=2))
