"""Four fixed corrected427 cases only. No work is performed at import."""
from pathlib import Path
import hashlib,json,os,sys,types
if not __debug__:raise RuntimeError('Optimized Python refused')
HERE=Path(__file__).resolve().parent
MEDIA=HERE.parent/'kos-budget-retest-media-prep-v2'
MEDIA_SEAL='2301e39cfb166ee25bab261f0323d1df27331155148b67453bc527ce7330bee1'
SOURCE='427784b1f48aa30742850bb5025925ab619b740e'
META_ROOTS=[HERE.parent/n for n in ['kos-budget-retest-stage-root-v1','review-kos-budget-retest-media-poststage-v1','kos-budget-retest-guest-root-review-v1']]
BOOTSTRAP="""import hashlib,pathlib,sys,types
path=pathlib.Path(sys.argv.pop(1));expected=sys.argv.pop(1);raw=path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=expected:raise SystemExit('Entry source changed')
mod=types.ModuleType('__main__');mod.__file__=str(path);sys.modules['__main__']=mod;sys.argv[0]=str(path)
exec(compile(raw,str(path),'exec',dont_inherit=True),mod.__dict__)
"""
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def fresh(p,j):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('x') as f:json.dump(j,f,indent=1);f.write('\n')
def publish_admission(path,j):
 path=Path(path);pending=path.with_name(path.name.replace('-ADMISSION.json','-ADMISSION-PREPARED.json'));fresh(pending,j);os.link(pending,path)
def verify(p,v):assert row(p)=={'size':v.get('size',v.get('bytes')),'sha256':v['sha256']},str(p)
def module(name,path,expected):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
 m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__);return m
def context():
 assert sha(MEDIA/'TOOLCHAIN-SEAL.json')==MEDIA_SEAL
 pins=read(MEDIA/'TOOLCHAIN-SEAL.json')['members']
 for n,p in pins.items():verify(MEDIA/n,p)
 return module('retest_stage_core',MEDIA/'core.py',pins['core.py']['sha256'])
def sealed(expected):
 assert sha(HERE/'TOOLCHAIN-SEAL.json')==expected
 for n,v in read(HERE/'TOOLCHAIN-SEAL.json')['members'].items():verify(HERE/n,v)
 allowed=set(read(HERE/'TOOLCHAIN-SEAL.json')['members'])|{'TOOLCHAIN-SEAL.json','READBACK.json'}
 for p in HERE.rglob('*'):
  assert not p.is_symlink()
  if not p.is_file():continue
  rel=p.relative_to(HERE)
  if len(rel.parts)==1:
   assert p.name in allowed or (p.name.startswith('RESULT-') and p.name.endswith('.json') and len(p.name)==76 and all(x in '0123456789abcdef' for x in p.name[7:-5])),'Unexpected guest-kit output'
  else:
   assert len(rel.parts)==2 and rel.parts[0]=='attempts'
   assert rel.parts[1] in {c['name']+suffix for c in read(MEDIA/'GUEST-PROPOSAL.json')['cases'] for suffix in ['-CONTROLLER.log','-ADMISSION.json','-ADMISSION-PREPARED.json','-PROCESS.json','-CLEANUP.log']},'Unexpected case output'
def capacity(k,required=None):
 v=k.capacity(k.FLOOR if required is None else required)
 roots=[*k.read(MEDIA/'BASELINE.json')['roots'],k.HERE,k.WORK,k.FINAL,HERE,*META_ROOTS]
 aggregate,_,_=k.scan(roots);v['aggregate_bytes']=aggregate;v['new_unique_bytes']=aggregate-v['prior_unique_bytes'];v['guest_and_root_metadata_roots']=[str(HERE),*map(str,META_ROOTS)]
 assert v['new_unique_bytes']<=k.DELTA and v['aggregate_bytes']<=k.AGG
 return v
def metadata_guard(g,k):
 allowed=g['metadata_allowlists'];assert set(allowed)==set(map(str,META_ROOTS))
 for root in META_ROOTS:
  names=allowed[str(root)];assert isinstance(names,list) and len(names)<=64 and len(set(names))==len(names)
  for n in names:
   p=Path(n);assert n and not p.is_absolute() and '..' not in p.parts and '\\' not in n and str(p)==n and p.suffix in ['.json','.py','.log','.md','.txt','.sha256']
  _,files,_=k.scan([root]);assert {str(Path(p).relative_to(root)) for p in files}<=set(names),'Unexpected observer metadata file'
def win(p):
 s=str(p)
 return 'C:\\'+s[7:].replace('/','\\') if s.startswith('/mnt/c/') else '\\\\wsl.localhost\\Ubuntu-24.04'+s.replace('/','\\')
def case(index,k):
 assert type(index) is int and 0<=index<4,'Only the four fixed cases'
 c=read(MEDIA/'GUEST-PROPOSAL.json')['cases'][index]
 assert (c['arm'],c['fragment'])==[('off',0),('on',0),('off',1),('on',1)][index]
 assert (c['held'],c['harness_seconds'],c['exact_child_seconds'])==(49152,45,55)
 cap=Path(c['cap_WSL']);cache=Path(c['cache_WSL'])
 assert cap==k.FINAL/'captures'/c['name'] and cache==k.FINAL/'cache'/c['name']
 assert cap.is_absolute() and cache.is_absolute() and cap==cap.resolve() and cache==cache.resolve()
 return c
def check_fresh(c):
 for key in ['cap_WSL','cache_WSL']:assert not Path(c[key]).exists(),('Fresh cap/absent-X required',key)
def windows_command(c,gpath,seal):
 argv=list(c['argv'][4:]);assert argv[1:5]==['-I','-S','-B','-X'] and argv[5]=='pycache_prefix='+win(c['cache_WSL'])
 argv[6:]=['-c',BOOTSTRAP,win(HERE/'windows_entry.py'),sha(HERE/'windows_entry.py'),'--case',str(c['index']),'--tools',seal,'--grant',win(gpath),'--grant-sha256',sha(gpath),'--',*argv[6:]]
 return argv
def grant_guard(g,seal,k):
 assert g.get('approved') is True and g['source']==SOURCE and g['authorization']=='FOUR_KOS48_CORRECTED427_CONSOLE_ONLY'
 assert g['kit_sha256']==seal and g['media_kit_sha256']==MEDIA_SEAL
 assert g['case_order'] in [[0,1],[2,3],[0,1,2,3]] and g['seconds']==45 and g['exact_child_seconds']==55 and g['parent_seconds']==95 and g['admission_seconds']==180 and g['overall_seconds']==1300
 assert all(type(i) is int for i in g['case_order'])
 assert g['new_delta_cap']==k.DELTA and g['aggregate_cap']==k.AGG and g['root_slots']==3 and g['global_slots']==16
 assert g['H2'] is False and g['scope']=='CAPTURES_AND_BOUNDED_KOS_JUDGEMENT_ONLY'
def handshake_guard(h,index,nonce,grant_sha,seal,started,now,argv,pgid):
 assert h['phase']=='AUTHENTICATED_BEFORE_WINDOWS_PYTHON' and type(h['case']) is int and h['case']==index and h['nonce']==nonce
 assert h['pgid']==pgid and type(h['pid']) is int and h['pid']>0,'Wrong admission process group'
 assert h['grant_sha256']==grant_sha and h['guest_kit_sha256']==seal and h['cap_absent'] is True and h['cache_absent'] is True and h['helpers_verified'] is True
 assert started<=h['prepared_monotonic']<=now and now-started<=180,'Missing/late/future admission handshake'
 assert {6,9}=={v['fd'] for v in h['locks']}
 assert h['argv']==argv,'Forged/changed Windows command handshake'
 return h['prepared_monotonic']+95
def authorize(k):
 seal=os.environ.get('GC_BUDGET_RETEST_GUEST_TOOLS');assert seal
 sealed(seal);path=Path(os.environ.get('GC_BUDGET_RETEST_GUEST_GRANT','/nonexistent'));assert path.is_file() and sha(path)==os.environ.get('GC_BUDGET_RETEST_GUEST_GRANT_SHA256')
 g=read(path);grant_guard(g,seal,k)
 assert path.is_absolute() and path==path.resolve() and path.parent==META_ROOTS[2],'Grant must be in the fixed root guest review directory'
 assert not any(os.environ.get(n) for n in ['BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PYTHONHOME','PYTHONPYCACHEPREFIX'])
 return g,path,seal
def check_poststage(g,k,arm,hash_tracks=True):
 pin=g['poststage'];verify(pin['path'],pin['identity']);s=read(pin['path'])
 root=META_ROOTS[1];assert Path(pin['path'])==root/'FINAL-READBACK.json' and pin['identity']['sha256']=='4dd7b532825d198b4f35f7f2cea576638e37339fc9e5e04cb5a4b4dd5fd7bb49'
 assert sha(root/'REVIEW-SEAL.json')=='1715b3b8f5514c3c2eeb7a5c1c3a0e8adde0174c7738589add3e5328642cf3c1'
 for n,v in read(root/'REVIEW-SEAL.json')['files'].items():verify(root/n,v)
 assert s['decision']=='CLEAR_COMPLETED_GC_STAGE_STATIC_MEDIA_READBACK_ONLY_NO_GUEST_PERMISSION' and s['source']==SOURCE and s['toolchain']['sha256']==MEDIA_SEAL
 verify(k.FINAL/'PAIR-STAGE-COMPLETE.json',s['pair_stage']);assert read(k.FINAL/'PAIR-STAGE-COMPLETE.json')['status']=='STAGE_ALL_FILES_COMPLETE_NO_GUEST'
 r=read(root/(arm.upper()+'-INDEPENDENT.json'))
 assert r['status']=='STAGE_ALL_FILE_READBACK_PASS_GUEST_NOT_RUN' and r['source']==SOURCE and r['arm']==arm
 assert r['binding_sha256']==sha(MEDIA/'BINDING.json') and r['manifest']==read(MEDIA/(arm.upper()+'-EXPECTED-MANIFEST.json')) and len(r['redirect_records'])==6
 base=k.OFF if arm=='off' else k.FINAL/'on'
 complete=k.FINAL/'REUSED-OFF.json' if arm=='off' else base/'COMPLETE.json';verify(complete,s['OFF_reuse' if arm=='off' else 'ON_complete'])
 if hash_tracks:
  for n,v in r['tracks'].items():assert n in ['track03.iso','track01-template.iso','track02.raw'];verify(base/n,v)
 return r
def check_inputs(g,k):
 for pin in read(HERE/'INPUT-PINS.json')['helpers'].values():verify(pin['path'],pin['identity'])
 for pin in read(HERE/'INPUT-PINS.json')['template'].values():verify(pin['path'],pin['identity'])
 for name in ['pillow_launcher','pillow_manifest','pillow_seal']:
  p=read(HERE/'INPUT-PINS.json')[name];verify(p['path'],p['identity'])
 pins=read(read(HERE/'INPUT-PINS.json')['pillow_manifest']['path'])
 for group,base in [('package_files','package_root'),('distribution','distribution_root')]:
  text=pins[base];assert text[1:3]==':\\';root=Path('/mnt/'+text[0].lower()+text[2:].replace('\\','/'));assert root==root.resolve() and not root.is_symlink()
  if group=='package_files':assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.relative_to(root).parts}==set(pins[group])
  for name,v in pins[group].items():assert not (root/name).is_symlink();verify(root/name,v)
 k.validate_binding(k.read(MEDIA/'BINDING.json'))
def kernel_locks():
 out=[]
 for fd,kind in [(6,'root3'),(9,'global16')]:
  target=os.readlink('/proc/self/fd/'+str(fd));p=Path(target)
  if fd==6:assert p.parent==Path('/root/work/lanes/stat-bytes23-complete-scratch/guest-slots') and p.name in ['slot-'+str(i)+'.lock' for i in range(3)]
  else:assert target in ['/root/probe/.trace.lock']+['/root/probe/.trace.lock.'+str(i) for i in range(1,16)]
  a=os.fstat(fd);b=p.stat();assert (a.st_dev,a.st_ino)==(b.st_dev,b.st_ino)
  info=Path('/proc/self/fdinfo/'+str(fd)).read_text();assert any('FLOCK' in x and 'ADVISORY' in x and 'WRITE' in x for x in info.splitlines() if x.startswith('lock:'))
  out.append(dict(fd=fd,path=target,kind=kind,fdinfo=info))
 return out
def kernel_sample(pgid):
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if os.getpgid(int(p.name))!=pgid:continue
   for fd in [6,9]:
    target=os.readlink(p/'fd'/str(fd));info=(p/'fdinfo'/str(fd)).read_text()
    if ('/guest-slots/slot-' in target or '/probe/.trace.lock' in target) and any('FLOCK' in x and 'ADVISORY' in x and 'WRITE' in x for x in info.splitlines() if x.startswith('lock:')):out.append(dict(pid=int(p.name),fd=fd,path=target,fdinfo=info))
  except (OSError,ProcessLookupError):continue
 return out
def release_active():
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  except (OSError,ProcessLookupError):continue
  if not args or Path(args[0]).name not in {'bash','python','python3','python3.12'}:continue
  for arg in args[1:5]:
   if arg in ['-c','-m']:break
   if arg.startswith('-'):continue
   if Path(arg).name in ['rr-cycle.sh','rr-cycle.py','rr-qa.sh','rr-qa.py','rr-jobs.sh','rr-jobs.py']:return True
   break
 return False
