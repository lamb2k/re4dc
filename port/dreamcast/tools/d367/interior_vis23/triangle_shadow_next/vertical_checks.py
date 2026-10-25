#!/usr/bin/env python3
"""Small public nominal Y-halfspace controls and intended safety mutants."""
import argparse,hashlib,json,resource,subprocess,sys,tempfile
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior controls')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));here=Path(__file__).resolve().parent;original=(here/'vertical_domain.py').read_text();records=[]
 variants=[('baseline',None,None),('outer-halfspaces-mutant',('def add(label,fn):rows.append(affine_row(label,fn))',"def add(label,fn):\n  if label['kind']!='outer_edge':rows.append(affine_row(label,fn))"),'test_all_outer'),('strict-quantization-mutant',('(lo/100).denominator+1','(lo/100).denominator'),'test_signed_quantization'),('halfspace-direction-mutant',('elif a>0:','elif a<0:'),'test_exact_open')]
 with tempfile.TemporaryDirectory(prefix='iv23-vertical-controls-',dir='/dev/shm') as temp:
  temp=Path(temp)
  for name,mutation,select in variants:
   source=original
   if mutation:
    old,new=mutation
    if source.count(old)!=1:raise ValueError('Mutation anchor changed')
    source=source.replace(old,new)
   (temp/'vertical_domain.py').write_text(source)
   for n in ('exact_shadow.py','exact_union.py','test_vertical_domain.py'):(temp/n).write_bytes((here/n).read_bytes())
   run=subprocess.run([sys.executable,'-B',str(temp/'test_vertical_domain.py')]+(['-k',select] if select else []),text=True,capture_output=True)
   if (run.returncode==0)!=(mutation is None):raise ValueError('Unexpected outcome '+name+run.stdout+run.stderr)
   if mutation and ('AssertionError' not in run.stderr or 'ERROR:' in run.stderr):raise ValueError('Unexpected mutant failure '+name+run.stderr)
   records.append(dict(name=name,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr))
 out=dict(kind='Public exact nominal Y analysis controls only',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),sources={n:hashlib.sha256((here/n).read_bytes()).hexdigest() for n in ('vertical_domain.py','test_vertical_domain.py','exact_union.py','exact_shadow.py')},variants=records,runtime_admitted=False,limits=dict(address_space_bytes=268435456,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1))
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
