"""Strict QA pair contracts; import has no SDK or build side effects."""
from pathlib import Path
import hashlib,json,os,re,signal,subprocess,time
HERE=Path(__file__).resolve().parent
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
TREE=Path('/root/work/lanes/codex-composition-int24')
ROOT=Path('/dev/shm/rain8ce-qa-pair-v1-2ykw93ke')
PLAN_SHA='c81c41509284d959927ae50b3a6506f7fd16d69c1da4a155dbf563ae2010d54e'
HOST_ROOT=Path('/dev/shm/rain8ce-qa-kit-host-v1')
WINPY='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'
def require(v,s):
 if not v:raise RuntimeError(s)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def identity(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def verify(rows):
 for p,r in rows.items():require(identity(p)==r,'Pinned input changed '+str(p))
def exclusive_json(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,indent=1);f.write('\n')
def contained(root,path):
 require(not Path(root).is_symlink(),'Owned root symlink refused');root=Path(root).resolve();path=Path(path).resolve();require(path!=root and path.is_relative_to(root),'Owned path escape');return path
def used(root):
 require(Path(root).is_dir() and not Path(root).is_symlink(),'Owned root must be a real directory')
 total=0
 for p in Path(root).rglob('*'):
  require(not p.is_symlink(),'Symlink refused '+str(p))
  if p.is_file():total+=p.stat().st_size
 return total
def load():
 require(sha(HERE/'PREPARATION.json')==PLAN_SHA,'Exact preparation required')
 p=json.loads((HERE/'PREPARATION.json').read_text());require(p['source']==SOURCE and Path(p['root'])==ROOT and p['object_reuse'] is False,'Exact source/root/no reuse')
 require(p['reference']['compile_count']==568 and p['reference']['object_count']==449,'Actual QA graph')
 require(p['budget']==dict(per_arm_seconds=600,owned_bytes_cap=2*1024**3,C_admission_bytes=26*1024**3,C_floor_bytes=24*1024**3,RAM_admission_bytes=3*1024**3,RAM_floor_bytes=512*1024**2,jobs=1,poll_seconds=0.5,shared_slots=1),'Exact limits')
 return p
def check_inputs(plan):
 verify(plan['input_pins']);verify(plan['tool_pins']);verify(json.loads((HERE/'CONTRACT.json').read_text())['reference_dependency_pins']);verify(json.loads((HERE/'CONTRACT.json').read_text())['reference_provider_pins'])
 for arm in ['off','on']:verify({str(ROOT/arm/'source'/k):v for k,v in plan['source_manifest'].items()})
 def git(*args):return subprocess.check_output(['/usr/bin/git','--no-optional-locks','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*args],text=True,timeout=30).strip()
 require(git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'Canonical source changed')
def release_active():
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:a=(p/'cmdline').read_bytes().split(b'\0')
  except (OSError,PermissionError):continue
  if len(a)>1 and Path(os.fsdecode(a[0])).name in ['bash','python','python3'] and re.search(r'/rr-(cycle|qa|jobs)\.(sh|py)$',os.fsdecode(a[1])):return True
 return False
def ram_observation(tmpfs_available,meminfo):
 require(type(tmpfs_available) is int and tmpfs_available>=0,'Invalid tmpfs availability')
 rows=[line.split() for line in meminfo.splitlines() if line.split() and line.split()[0]=='MemAvailable:']
 require(len(rows)==1 and len(rows[0])==3 and rows[0][1].isdigit() and rows[0][2]=='kB','Missing/malformed MemAvailable')
 available=int(rows[0][1])*1024
 return dict(RAM_free=min(tmpfs_available,available),tmpfs_available_bytes=tmpfs_available,MemAvailable_bytes=available)
def resources(root):
 # Lower Windows/WSL figure is authoritative; failed observation is a refusal.
 windows=int(subprocess.check_output([WINPY,'-c',"import shutil;print(shutil.disk_usage('C:\\\\').free)"],text=True,timeout=3).strip());s=os.statvfs('/mnt/c');wsl=s.f_bavail*s.f_frsize;s=os.statvfs('/dev/shm')
 return dict(C_free=min(windows,wsl),windows_C_free=windows,wsl_C_free=wsl,**ram_observation(s.f_bavail*s.f_frsize,Path('/proc/meminfo').read_text()),owned_bytes=used(root)+used(HERE)+(used(HOST_ROOT) if HOST_ROOT.exists() else 0),release_active=release_active())
def boundaries(r,b,elapsed=0,admission=False):
 require(not r.get('release_active',False),'Release priority hold');require(r['C_free']>=b['C_admission_bytes' if admission else 'C_floor_bytes'],'C capacity');require(r['RAM_free']>=b['RAM_admission_bytes' if admission else 'RAM_floor_bytes'],'RAM capacity');require(r['owned_bytes']<=b['owned_bytes_cap'],'Total owned cap');require(elapsed<=b['per_arm_seconds'],'Arm deadline')
def terminate(child):
 # Always close the owned process group, even when its leader exited first.
 try:os.killpg(child.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 deadline=time.monotonic()+3
 while time.monotonic()<deadline:
  child.poll()
  try:os.killpg(child.pid,0)
  except ProcessLookupError:break
  time.sleep(.05)
 try:os.killpg(child.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 child.wait(timeout=3)
def run_owned(argv,cwd,env,log,root,budget,started,sample=resources):
 boundaries(sample(root),budget,time.monotonic()-started);child=None
 try:
  with Path(log).open('x') as f:
   child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
   while child.poll() is None:
    boundaries(sample(root),budget,time.monotonic()-started);time.sleep(budget['poll_seconds'])
   boundaries(sample(root),budget,time.monotonic()-started);require(child.returncode==0,'Owned child failed rc='+str(child.returncode))
 finally:
  if child is not None:terminate(child)
 return time.monotonic()-started
REFUSED_ENV=['MAKEFLAGS','MFLAGS','GNUMAKEFLAGS','CC','CXX','CPP','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','COMPILER_PATH','GCC_EXEC_PREFIX','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PYTHONHOME','BASH_ENV','ENV','RE4DC_KOS_CC_BASE','D367_SLOT_HELD']
def clean_environment(plan,arm,tmp):
 return dict(PATH='/usr/bin:/bin',HOME='/root',USER='root',LOGNAME='root',LANG='C.UTF-8',LC_ALL='C.UTF-8',SHELL='/bin/bash',**plan['environment'][arm],D367_SLOT_HELD='1',TMPDIR=str(tmp),TMP=str(tmp),TEMP=str(tmp),PYTHONPYCACHEPREFIX=str(tmp/'unused-bytecache'))
def finishable(arms):require(set(arms)=={'off','on'} and all(x.get('complete') is True for x in arms.values()),'Incomplete arms')

def fresh_arm(a):
 require(all(not p.exists() and not p.is_symlink() for p in [a/'out',a/'source/port/dreamcast/game/obj',a/'build.log',a/'program.bin',a/'command.json']),'Fresh arm outputs required; never reuse/restart')
