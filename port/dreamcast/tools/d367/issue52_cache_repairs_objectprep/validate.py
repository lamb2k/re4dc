"""Revalidate source-only plan without invoking compiler/preprocessor/make."""
from pathlib import Path
import gzip,hashlib,json,os,subprocess
M=Path(__file__).resolve().parent
def load(n):
 b=(M/n).read_bytes();return json.loads(gzip.decompress(b) if n.endswith('.gz') else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(c,s):
 if not c:raise RuntimeError(s)
def verify(r):
 p=Path(r['path']);req(p.is_file() and sha(p)==r['sha256'] and str(p.resolve())==r['resolved_path'],'pin disagreement '+str(p))
for line in (M/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);req(sha(M/n)==h,'packet disagreement '+n)
p=load('plan.json');T=Path(p['tree'])
req(subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()==p['source'],'source HEAD drift')
req(not subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip(),'source dirty; no qualification admission')
req(not Path(p['future_output']).exists(),'future output exists; preserve and inspect')
n=0
for f in ['references.json','input-pins.json.gz','tool-extra-pins.json']:
 for r in load(f):verify(r);n+=1
R={r['path']:r for r in load('references.json')}
for path in R:
 if path.endswith('/system-header-pins.json.gz') or path.endswith('/toolchain-pins.json'):
  raw=Path(path).read_bytes();rows=json.loads(gzip.decompress(raw) if path.endswith('.gz') else raw)
  for r in rows:verify(r);n+=1
E=load('environment.json')
for path in E['absent']:req(not Path(path).exists(),'absence invariant changed '+path)
for k,v in E['influencing_environment'].items():req(os.environ.get(k)==v,'influencing environment drift '+k)
fixed=Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include-fixed')
req({str(q) for q in fixed.rglob('*') if q.is_file()}=={r['path'] for r in load('tool-extra-pins.json')},'include-fixed inventory drift')
B=load('baseline-projections.json');C=load('compile-contracts.json.gz');tasks=load('planned-tasks.json.gz')
req(len(tasks)==8 and set(tasks)==set(p['task_order']),'eight-task inventory')
for c in C:
 name=c['unit'];old=gzip.decompress((M/B[name]['compressed_source']).read_bytes())
 req(hashlib.sha256(old).hexdigest()==B[name]['sha256'],'previous TU payload drift')
 req(old==subprocess.check_output(['git','show',B[name]['commit']+':'+c['source']],cwd=T),'previous TU Git disagreement')
 sourcearg=c['recorded_canonical_argv'][c['recorded_canonical_argv'].index('-c')+1]
 for mode in ['previous','default','off','on']:
  t=tasks[name+'-'+mode];a=t['command'];guard=c['guard']
  expected=[] if mode in ['previous','default'] else ['-D'+guard+'='+('1' if mode=='on' else '0')]
  req([v for v in a if v.startswith('-D'+guard+'=')]==expected,'guard definition drift')
  req(a[a.index('-c')+1]==sourcearg,'source spelling changed')
  req(a[:len(c['mapped_unchanged_prefix'])]==c['mapped_unchanged_prefix'],'effective flag prefix changed')
  req([v for v in a if v.startswith('-O')]==c['optimization_order'],'optimization order changed')
  req(str(Path(a[a.index('-o')+1]).parent)==str(Path(p['future_output'])/'objects'),'output ownership drift')
req(p['actual_compiler_runs']==0 and not p['actual_lease'],'not source-only')
print(json.dumps(dict(state='SOURCE_ONLY_PREPARATION_REVALIDATED',source=p['source'],checked_pins=n,planned_tasks=len(tasks),compiler_runs=0,lease=False)))