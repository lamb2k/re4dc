#!/usr/bin/env python3
"""Run exact-union synthetic controls and semantic safety mutants, RAM only."""
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior controls')
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
 here=Path(__file__).resolve().parent;original=(here/'exact_union.py').read_text();records=[]
 mutations=[('baseline',None),('outer-edge-mutant',("if lower<=0:return dict(proven=False,reason='edge_unknown')","if False:return dict(proven=False,reason='edge_unknown')")),('uncertainty-mutant',('r=Q(vertex_error)','r=Q(0)')),('one-plane-mutant',('for t in ts:\n        a,b,c=[v[i] for i in t]','for t in ts[:1]:\n        a,b,c=[v[i] for i in t]'))]
 with tempfile.TemporaryDirectory(prefix='iv23-union-math-',dir='/dev/shm') as tmp:
  tmp=Path(tmp)
  for name,mutation in mutations:
   source=original
   if mutation:
    old,new=mutation
    if source.count(old)!=1:raise ValueError('Mutation anchor changed')
    source=source.replace(old,new)
   (tmp/'exact_union.py').write_text(source)
   for file in ('exact_shadow.py','test_exact_union.py'):(tmp/file).write_bytes((here/file).read_bytes())
   run=subprocess.run([sys.executable,str(tmp/'test_exact_union.py')],capture_output=True,text=True)
   if (run.returncode==0)!=(mutation is None):raise ValueError('Unexpected '+name+' '+run.stdout+run.stderr)
   if mutation and ('AssertionError' not in run.stderr or 'ERROR:' in run.stderr):raise ValueError('Mutant did not fail the intended assertion '+name)
   records.append(dict(name=name,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected='pass' if mutation is None else 'assertion failure'))
 out=dict(kind='Exact IDEAL shared-index actual-triangle union synthetic controls only',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources={file:hashlib.sha256((here/file).read_bytes()).hexdigest() for file in ('exact_union.py','exact_shadow.py','test_exact_union.py')},variants=records,renderer_admission=False,limits=dict(address_space_bytes=256*1024*1024,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1))
 a.out.parent.mkdir(parents=True,exist_ok=True)
 with a.out.open('x') as f:json.dump(out,f,indent=1);f.write('\n')
 print(json.dumps(out))

if __name__=='__main__':main()
