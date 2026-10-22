"""Read-only revalidation of a prepared packet. Never invokes a compiler."""
from pathlib import Path
import gzip,hashlib,json,os,subprocess,sys
M=Path(__file__).resolve().parent
# This file can run from the source metadata namespace or its evidence mirror.
def load(name):
 p=M/name
 return json.loads(gzip.decompress(p.read_bytes()) if name.endswith('.gz') else p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def require(x,msg):
 if not x:raise RuntimeError(msg)
r=load('preparation.json');T=Path('/root/probe/codex-mipmap21-next650')
require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()==r['source'],'candidate HEAD changed')
require(not subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip(),'candidate dirty')
count=0
for name in ('canonical-references.json','candidate-input-pins.json.gz','system-header-pins.json.gz','toolchain-pins.json'):
 for v in load(name):
  p=Path(v['path']);require(p.is_file() and sha(p)==v['sha256'],'pin disagreement '+str(p));count+=1
  require(str(p.resolve())==v['resolved_path'],'resolved path changed '+str(p))
env=load('compiler-environment.json')
for p in env['absent_include_roots']:require(not Path(p).exists(),'absent include path appeared '+p)
for k,v in env['influencing_environment'].items():require(os.environ.get(k)==v,'compiler environment changed '+k)
require(not Path(r['future_output']).exists(),'future output exists; preserve and inspect it')
tasks=load('planned-tasks.json');require(len(tasks)==6,'task inventory')
for name,t in tasks.items():
 a=t['command'];d=[x for x in a if x.startswith('-DRE4DC_WORLD_RECT21=')]
 want=[] if name.endswith('-default') else ['-DRE4DC_WORLD_RECT21='+('1' if name.endswith('-on') else '0')]
 require(d==want,'guard argv mismatch '+name)
 require(a[a.index('-c')+1]=='platform/'+name.rsplit('-',1)[0]+'.cpp','wrong TU '+name)
 require(str(Path(a[a.index('-o')+1]).parent)==str(Path(r['future_output'])/'objects'),'output outside owned tree')
print(json.dumps(dict(status='PREPARATION REVALIDATED; no compiler/preprocessor/link/build run',source=r['source'],checked_file_pins=count,tasks=len(tasks))))
