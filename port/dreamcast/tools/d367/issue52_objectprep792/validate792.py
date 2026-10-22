"""Read-only NEXT792 source-plan validation: no compiler or lease invocation."""
from pathlib import Path
import gzip,hashlib,json,os,subprocess
M=Path(__file__).resolve().parent
P=Path('/root/probe/codex-issue52-objects/port/dreamcast/tools/d367/issue52_objectprep650')
T=Path('/root/probe/codex-mipmap21-next792')
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def req(x,msg):
 if not x:raise RuntimeError(msg)
for line in (M/'SHA256SUMS').read_text().splitlines():
 h,name=line.split('  ',1);req(sha(M/name)==h,'packet checksum '+name)
r=load(M/'plan.json');req(subprocess.check_output(['git','rev-parse','HEAD'],cwd=T,text=True).strip()==r['source'],'root792 HEAD changed')
req(not subprocess.check_output(['git','status','--porcelain'],cwd=T,text=True).strip(),'root792 dirty')
count=0
for values in [load(M/'references.json'),load(M/'candidate-input-pins.json.gz'),load(M/'root-source-files.json'),load(P/'system-header-pins.json.gz'),load(P/'toolchain-pins.json')]:
 for v in values:
  p=Path(v['path']);req(p.is_file() and sha(p)==v['sha256'] and str(p.resolve())==v['resolved_path'],'input identity '+str(p));count+=1
for d in load(M/'selected-source-delta.json'):
 for k in ('candidate','prior650'):
  v=d[k];req(sha(Path(v['path']))==v['sha256'],'source delta reference drift '+v['path'])
env=load(P/'compiler-environment.json')
for p in env['absent_include_roots']+env.get('absent_tool_specs',[]):req(not Path(p).exists(),'absence invariant '+p)
for k,v in env['influencing_environment'].items():req(os.environ.get(k)==v,'compiler environment '+k)
old=load(P/'planned-tasks.json');new=load(M/'planned-tasks.json.gz');req(len(new)==6,'six tasks missing')
for name,t in new.items():
 req(t['cwd']==str(T/'port/dreamcast/game'),'wrong792 cwd')
 for field in ('command','macro_command','preprocess_command','full_dependency_command'):
  reverse=[s.replace(r['future_output'],'/root/probe/issue52-650-sh4-objects-20261022-01') for s in t[field]]
  req(reverse==old[name][field],'effective code flags differ '+name+' '+field)
req(not Path(r['future_output']).exists(),'future792 output exists; preserve it')
print(json.dumps(dict(state='SOURCE-ONLY PLAN REVALIDATED',source=r['source'],checked_input_records=count,planned_fresh_tasks=len(new),compiler_or_lease_invocations=0)))
