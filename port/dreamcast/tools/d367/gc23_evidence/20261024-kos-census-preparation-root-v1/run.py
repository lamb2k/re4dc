"""Future root-granted matched census links only; never stages or starts a guest."""
from pathlib import Path
import hashlib,json,os,re,signal,subprocess,time
import graph
import prepare as prep
HERE=Path(__file__).resolve().parent
INJECTION={'CC','CXX','CPP','AS','AR','LD','NM','OBJCOPY','OBJDUMP','RANLIB','STRIP','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS',
 'MAKEFLAGS','MFLAGS','GNUMAKEFLAGS','GCC_EXEC_PREFIX','COMPILER_PATH','LIBRARY_PATH','CPATH','C_INCLUDE_PATH','CPLUS_INCLUDE_PATH',
 'BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PYTHONHOME','PYTHONPYCACHEPREFIX','RE4DC_KOS_CC_BASE',
 'KOS_CFLAGS','KOS_CPPFLAGS','KOS_LDFLAGS','KOS_CC_BASE','KOS_CC','KOS_CXX'}

class OwnedStop(RuntimeError):pass
def signal_stop(signum,frame):raise OwnedStop('Owned interruption signal '+str(signum))
def assert_fd_lock(fd,path):
 path=Path(path);a=os.fstat(fd);b=path.stat()
 assert (a.st_dev,a.st_ino)==(b.st_dev,b.st_ino),('Wrong lock inode',fd,path)
 info=Path('/proc/self/fdinfo/'+str(fd)).read_text()
 assert any('FLOCK' in line and 'ADVISORY' in line and 'WRITE' in line for line in info.splitlines() if line.startswith('lock:')),('Descriptor is not actually flock-held',fd)
def actual_locks():
 canonical='/tmp/d367-build-'+hashlib.md5(str(prep.TREE).encode()).hexdigest()[:12]+'.lock'
 assert_fd_lock(7,canonical);shared=[]
 paths={8:'/root/probe/d367-build2.lock',9:'/root/probe/d367-build.lock'}
 for fd,path in paths.items():
  try:assert_fd_lock(fd,path)
  except (OSError,AssertionError):continue
  shared.append(fd)
 assert len(shared)==1,'Exactly one actual shared FD8/9 required'
 actual=[]
 for p in Path('/proc/self/fd').iterdir():
  try:target=os.readlink(p)
  except OSError:continue
  if target in paths.values():actual.append(int(p.name))
 assert actual==shared,('Unexpected inherited shared lock descriptor',actual,shared)
 return {'canonical_FD':7,'canonical_path':canonical,'shared_FD':shared[0],'shared_path':paths[shared[0]]}
def release_cmd(args):
 if not args or Path(args[0]).name not in {'bash','python','python3','python3.12'}:return False
 for argument in args[1:5]:
  if argument in {'-c','-m'}:return False
  if argument.startswith('-'):continue
  return Path(argument).name in {'rr-cycle.sh','rr-cycle.py','rr-qa.sh','rr-qa.py','rr-jobs.sh','rr-jobs.py'}
 return False
def release_active():
 for p in Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==os.getpid():continue
  try:args=(p/'cmdline').read_bytes().split(b'\0');args=[x.decode(errors='replace') for x in args if x]
  except (FileNotFoundError,PermissionError,ProcessLookupError):continue
  if release_cmd(args):return True
 return False
def owned_bytes(root):return prep.used(root)+prep.used(HERE)
def cleanup_child(child):
 old={s:signal.getsignal(s) for s in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]}
 for s in old:signal.signal(s,signal.SIG_IGN)
 try:
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  until=time.monotonic()+3
  while time.monotonic()<until:
   child.poll()
   try:os.killpg(child.pid,0)
   except ProcessLookupError:break
   time.sleep(0.05)
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait()
 finally:
  for s,handler in old.items():signal.signal(s,handler)
def owned_child(argv,stdout,deadline,monitor,cwd=None,env=None):
 """Every build and analysis child has one owned session and monitored cleanup."""
 monitor();assert time.monotonic()<deadline
 child=subprocess.Popen(argv,cwd=cwd,env=env,stdout=stdout,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  while child.poll() is None:
   monitor()
   if time.monotonic()>=deadline:raise OwnedStop('Whole owned arm deadline600s')
   time.sleep(0.25)
  if child.returncode:raise OwnedStop('Owned child failed rc='+str(child.returncode))
  monitor()
 finally:
  cleanup_child(child)

def check_capacity(budget,cbytes,rbytes,owned,admission=False):
 assert cbytes>=budget['C_admission_bytes' if admission else 'C_floor_bytes']
 assert rbytes>=budget['RAM_admission_bytes' if admission else 'RAM_floor_bytes']
 assert owned<=budget['owned_bytes_cap']

def integrity(plan):
 prep.semantic(plan)
 assert prep.git(prep.TREE,'rev-parse','HEAD').decode().strip()==prep.SOURCE
 assert not prep.git(prep.TREE,'status','--porcelain')
 for key in ['input_pins','preserved_artifacts','actual_existing_d_files']:prep.verify(plan[key])
 root=Path(plan['root'])
 for arm in plan['arm_order']:
  prep.verify({str(root/arm/'source'/n):r for n,r in plan['source_manifests'][arm].items()})
 check_capacity(plan['budget'],prep.free('/mnt/c'),prep.free('/dev/shm'),owned_bytes(root))

def tool_integrity():
 seal=prep.read(HERE/'TOOLCHAIN-SEAL.json')
 for n,pin in seal['members'].items():assert prep.row(HERE/n)==pin,('tool changed',n)
 assert os.environ.get('GC_KOS_CENSUS_TOOLS')==prep.sha(HERE/'TOOLCHAIN-SEAL.json')

def post_external_deps(root,arm,pins):
 cwd=root/arm/'source/port/dreamcast/game';seen={};missing=[]
 for dep in (root/arm/'out').rglob('*.d'):
  line=dep.read_text().replace('\\\n',' ').splitlines()[0]
  import shlex
  for token in shlex.split(line.split(':',1)[1]):
   p=Path(token);p=(p if p.is_absolute() else cwd/p).resolve()
   if p.is_relative_to(root/arm/'source') or p.is_relative_to(root/arm/'out'):continue
   if str(p) not in pins:missing.append(str(p));continue
   assert prep.row(p)==pins[str(p)];seen[str(p)]=pins[str(p)]
 assert not missing,('Unpinned new external .d dependencies',sorted(set(missing)))
 return {'external_paths':len(seen),'unpinned':[],'scope':'MMD non-system only; pinned SDK/sysroot scope remains separate.'}

def main():
 for signum in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(signum,signal_stop)
 assert not {k for k in INJECTION if os.environ.get(k)},'Inherited compiler/loader/Python injection refused'
 assert os.environ.get('GC_KOS_CENSUS_SOURCE')==prep.SOURCE and os.environ.get('GC_KOS_CENSUS_SLOT')=='1','Root allocation and canonical slot required'
 locks=actual_locks()
 assert os.environ.get('GC_KOS_CENSUS_PLAN')==prep.sha(HERE/'PREPARATION.json'),'Exact root plan allocation required'
 tool_integrity();plan=prep.read(HERE/'PREPARATION.json');root=Path(plan['root']);budget=plan['budget']
 assert not (root/'census-receipt.json').exists(),'Unique output; no restart or overwrite'
 assert not release_active(),'Release work has priority'
 check_capacity(budget,prep.free('/mnt/c'),prep.free('/dev/shm'),owned_bytes(root),admission=True)
 integrity(plan)
 report={'source':prep.SOURCE,'plan_sha256':prep.sha(HERE/'PREPARATION.json'),'tool_seal_sha256':prep.sha(HERE/'TOOLCHAIN-SEAL.json'),
  'scope':'Fresh mode1 attribution-only matched OFF/ON, no memory/performance/staging/guest qualification','locks':locks,
  'owned_roots':[str(root),str(HERE)],'arms':{},'complete':False}
 def save():(root/'census-receipt.json').write_text(json.dumps(report,indent=1)+'\n')
 save()
 try:
  for arm in plan['arm_order']:
   start=time.monotonic();deadline=start+budget['per_arm_seconds']
   def monitor():
    actual_locks()
    check_capacity(budget,prep.free('/mnt/c'),prep.free('/dev/shm'),owned_bytes(root))
    if release_active():raise OwnedStop('Release work became active; owned census yields')
    if time.monotonic()>=deadline:raise OwnedStop('Whole owned arm deadline600s')
   tool_integrity();integrity(plan)
   base=root/arm;out=base/'out';source=base/'source';scratch=source/'port/dreamcast/game/obj'
   assert not out.exists() and not scratch.exists() and not (base/'build.log').exists()
   assert prep.actual_preflight(source,plan['commands'][arm])['returncode']==0
   (base/'tmp').mkdir();prep.emit(base/'command.json',plan['commands'][arm])
   report['arms'][arm]={'started':True,'command_sha256':prep.sha(base/'command.json'),'complete':False};save()
   def remaining():
    value=deadline-time.monotonic();assert value>0,'Whole owned arm deadline600s';return value
   with (base/'build.log').open('x') as log:
    env=dict(plan['environment'][arm],D367_SLOT_HELD='1',PYTHONPYCACHEPREFIX=str(base/'python-cache-child'))
    report['arms'][arm]['fixed_environment_additions']={k:env[k] for k in ['D367_SLOT_HELD','PYTHONPYCACHEPREFIX']};save()
    owned_child(plan['commands'][arm],log,deadline,monitor,cwd=source,env=env)
   assert (scratch/'missing.txt').is_file() and (scratch/'missing.txt').stat().st_size==0
   alias=(scratch/'aliases.ld').read_text();missing=(scratch/'missing.cpp').read_text()
   assert not any(n in alias+missing for n in ['__wrap_malloc','__wrap_memalign','kos_census','motion_unknown','gcasset'])
   resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
   required=dict(prep.read(prep.AUDIT/'NEXT-DIAGNOSTIC-PAIR.json')['common_required_resolved'])
   required.update(prep.read(prep.AUDIT/'NEXT-DIAGNOSTIC-PAIR.json')['arm_required_resolved'][arm])
   wrong={k:[v,resolved.get(k)] for k,v in required.items() if resolved.get(k)!=v}
   assert not wrong,('Resolved required profile differs',wrong)
   elf=out/'re4dc-game.elf';raw=base/'program.bin'
   tools='/opt/toolchains/dc/sh-elf/bin/'
   with (base/'objcopy-analysis.log').open('x') as stream:
    owned_child([tools+'sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(raw)],stream,deadline,monitor,env=env)
   proof=graph.verify(elf,base/'build.log',arm,plan['baseline_wraps'][arm])
   for obj in proof['graph']['ordered_objects']:assert Path(obj).is_relative_to(out/'obj'),('Reused/nonowned game object',obj)
   overlays=sorted(out.glob('*.ovl'));assert {p.name for p in overlays}=={x.lower()+'.ovl' for x in plan['expected_overlays']}
   deps=post_external_deps(root,arm,plan['input_pins'])
   for option,name in [(['-S'],'symbols.txt'),([], 'size.txt'),(['-A'],'sections.txt')]:
    command=[tools+('sh-elf-nm' if name=='symbols.txt' else 'sh-elf-size'),*option,str(elf)]
    with (base/name).open('x') as f:owned_child(command,f,deadline,monitor,env=env)
   prep.emit(base/'MODE1-GRAPH.json',proof)
   report['arms'][arm].update({'complete':True,'seconds':time.monotonic()-start,'files':{p.name:prep.row(p) for p in [elf,raw,*overlays]},
    'mode1_graph_sha256':prep.sha(base/'MODE1-GRAPH.json'),'external_dependency_postcheck':deps,'build_log_sha256':prep.sha(base/'build.log'),
    'resolved_sha256':prep.sha(out/'resolved-knobs.txt'),'coverage':'UNKNOWN; no live census/mallinfo/overflow reconciliation yet'})
   integrity(plan);monitor();remaining();save();print(arm+' MODE1 FRESH LINK AND MANDATORY ROUTE GRAPH COMPLETE; attribution only',flush=True)
  report['complete']=True;save()
 except BaseException as exc:
  report['complete']=False;report['failure']=repr(exc);report['owned_bytes']=owned_bytes(root);save();raise
if __name__=='__main__':main()
