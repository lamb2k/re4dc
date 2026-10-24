"""Shared strict contracts. Import has no build/SDK side effects."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time,re
HERE=Path(__file__).resolve().parent
PREP=HERE.parent/'full-normal-rain8ce-prep'
EXTRA_OWNED=[HERE,PREP,Path('/dev/shm/rain8ce-controller-host-owned-v1'),Path('/dev/shm/rain8ce-controller-host-rijajt1z')]
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
TREE=Path('/root/work/lanes/codex-composition-int24')
PLAN_SHA='b823d007d436625e245abc9e4d7aa6f36df45cbe5d146f1c1fc967bae74e707e'
PREP_SEAL='96400c0e65ea61f7a7505aef8f154cfe4b8cf869cfa06698e765ea9fcfe611c3'

def require(ok,reason):
 if not ok:raise RuntimeError(reason)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def identity(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def verify(rows):
 for name,row in rows.items():require(identity(name)==row,'Pinned file changed '+str(name))
def contained(root,path):
 root=Path(root).resolve();path=Path(path).resolve();require(path.is_relative_to(root) and path!=root,'Path escaped owned root');return path
def used(root):
 total=0
 for p in Path(root).rglob('*'):
  require(not p.is_symlink(),'Owned symlink refused '+str(p))
  if p.is_file():total+=p.stat().st_size
 return total
def free(path):s=os.statvfs(path);return s.f_bavail*s.f_frsize
def release_active():
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:av=(proc/'cmdline').read_bytes().split(b'\0')
  except (FileNotFoundError,PermissionError,ProcessLookupError):continue
  if len(av)>1 and Path(os.fsdecode(av[0])).name in ['bash','python','python3'] and re.search(r'/rr-(cycle|qa|jobs)\.(sh|py)$',os.fsdecode(av[1])):return True
 return False

def resources(root):return dict(C_free=free('/mnt/c'),RAM_free=free('/dev/shm'),owned_bytes=used(root)+sum(used(p) for p in EXTRA_OWNED),release_active=release_active())
def boundaries(values,budget,elapsed=0,admission=False):
 require(not values.get('release_active',False),'Release priority')
 require(values['C_free']>=budget['C_admission_bytes' if admission else 'C_floor_bytes'],'C capacity')
 require(values['RAM_free']>=budget['RAM_admission_bytes' if admission else 'RAM_floor_bytes'],'RAM capacity')
 require(values['owned_bytes']<=budget['owned_bytes_cap'],'Owned cap')
 require(elapsed<=budget['per_arm_seconds'],'Arm deadline')
def load():
 require(sha(PREP/'SHA256-MANIFEST.json')==PREP_SEAL,'Original preparation seal')
 seal=json.loads((PREP/'SHA256-MANIFEST.json').read_text());verify({str(PREP/n):r for n,r in seal['files'].items()})
 require(sha(PREP/'PREPARATION.json')==PLAN_SHA,'Preparation pin')
 p=json.loads((PREP/'PREPARATION.json').read_text());require(p['source']==SOURCE,'Source pin')
 require(Path(p['root'])==Path('/dev/shm/rain8ce-full-normal-179r4a5c'),'Exact exports required')
 require(p['budget']['per_arm_seconds']==600 and p['budget']['owned_bytes_cap']==2*1024**3,'Budget contract')
 return p
def check_inputs(plan):
 verify(plan['input_pins'])
 for arm in ['off','on']:verify({str(Path(plan['root'])/arm/'source'/n):v for n,v in plan['source_manifest'].items()})
 def git(*a):return subprocess.check_output(['git','--no-optional-locks','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*a],text=True).strip()
 require(git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'Canonical source changed')
def exclusive_json(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2);f.write('\n')
def terminate(child):
 if child.poll() is not None:return
 try:os.killpg(child.pid,signal.SIGTERM)
 except ProcessLookupError:return
 try:child.wait(timeout=3)
 except subprocess.TimeoutExpired:
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait()
def run_owned(argv,cwd,env,log,root,budget,started,sample=resources):
 """One owned child process group only; 0.5s floor/cap/deadline checks incl bootstrap."""
 boundaries(sample(root),budget,time.monotonic()-started)
 child=None
 try:
  with Path(log).open('x') as f:
   child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   while child.poll() is None:
    boundaries(sample(root),budget,time.monotonic()-started);time.sleep(0.5)
   boundaries(sample(root),budget,time.monotonic()-started)
   require(child.returncode==0,'Owned child failed rc='+str(child.returncode))
 finally:
  if child is not None:terminate(child)
 return time.monotonic()-started

def finishable(arms):require(set(arms)=={'off','on'} and all(x.get('complete') is True for x in arms.values()),'Incomplete arms')
