from pathlib import Path
import json,os,sys,time,signal,subprocess,hashlib,types,fcntl,datetime
HERE=Path(__file__).resolve().parent
KIT=HERE.parent/'kos-census-media-prep-v1'
GRANT='195f59bdb3e94945e51bfcb47b0b759f1a1abb488631a6c63a06c45e3d91992b'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def row(p):return {'size':Path(p).stat().st_size,'sha256':sha(p)}
def fresh(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def verify(p,x):assert row(p)==x,str(p)
assert sha(HERE/'ROOT-CALLER-GUEST-GRANT-v1.json')==GRANT
g=read(HERE/'ROOT-CALLER-GUEST-GRANT-v1.json')
verify(KIT/'TOOLCHAIN-SEAL.json',g['kit_seal'])
for n,pin in read(KIT/'TOOLCHAIN-SEAL.json')['members'].items():verify(KIT/n,pin)
c=types.ModuleType('census_root_common');c.__file__=str(KIT/'common.py');exec(compile((KIT/'common.py').read_bytes(),c.__file__,'exec'),c.__dict__)
p=read(KIT/'OBSERVATION-PROPOSAL.json');verify(KIT/'OBSERVATION-PROPOSAL.json',g['proposal']);verify(KIT/'BINDING.json',g['binding'])
TEMPLATE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par')
for n,pin in g['template'].items():verify(TEMPLATE/n,pin)
for h in g['helpers'].values():verify(h['path'],h['identity'])
verify(KIT/'fixtures/kos-squeeze0.txt',g['fixture'])
assert read(HERE/'ROOT-STAGE-PAIR-RESULT.json')['complete'] is True
R=Path(sys.argv[1]);review=read(R);assert review['status']=='CLEAR_POSTSTAGE_ALL_FILES_NO_GUEST'
for arm in ['off','on']:
 a=review['arms'][arm];verify(a['readback_path'],a['readback_identity']);assert read(a['readback_path'])['status']=='STAGE_ALL_FILE_READBACK_PASS_GUEST_NOT_RUN'
 verify(c.FINAL/arm/'COMPLETE.json',a['complete_identity'])
 for name,pin in read(a['readback_path'])['tracks'].items():verify(c.FINAL/arm/name,pin)
result={'complete':False,'scope':g['scope'],'grant_sha256':GRANT,'poststage_review':row(R),'arms':{},'template':g['template'],'helpers':g['helpers']}
def release_active():
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:args=[x.decode(errors='replace') for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
  except (OSError,ProcessLookupError):continue
  if not args or Path(args[0]).name not in {'bash','python','python3','python3.12'}:continue
  for a in args[1:5]:
   if a in {'-c','-m'}:break
   if a.startswith('-'):continue
   if Path(a).name in {'rr-cycle.sh','rr-cycle.py','rr-qa.sh','rr-qa.py','rr-jobs.sh','rr-jobs.py'}:return True
   break
 return False
def lock_sample(pgid):
 out=[]
 for d in Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   if os.getpgid(int(d.name))!=pgid:continue
   for fd in ['6','9']:
    target=os.readlink(d/'fd'/fd)
    if not ('/guest-slots/slot-' in target or '/probe/.trace.lock' in target):continue
    info=(d/'fdinfo'/fd).read_text();assert 'lock:' in info,'descriptor without real held lock'
    out.append({'pid':int(d.name),'fd':int(fd),'target':target,'fdinfo':info})
  except (FileNotFoundError,ProcessLookupError,PermissionError):continue
 return out
for s in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(s,c.stop)
env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','RE4DC_','HWTRACE','GC_','FP_','TRACE_','LD_')) and k not in {'BASH_ENV','ENV','SHELLOPTS','BASHOPTS','CDPATH'}}
forward={'RE4DC_EMU':'console','FP_NOLIMIT':'1','RE4DC_MAX_FLYCASTS':'16','RE4DC_CONSOLE_EXE':r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe','TRACE_SLOTS':'16','GC_CENSUS_GUEST_ALLOCATED':GRANT,'PYTHONDONTWRITEBYTECODE':'1'}
env.update(forward);env['WSLENV']=':'.join(forward)
try:
 for arm in ['off','on']:
  c.bounds(c.ADMIT);assert not release_active(),'release priority'
  for n,pin in g['template'].items():verify(TEMPLATE/n,pin)
  for h in g['helpers'].values():verify(h['path'],h['identity'])
  argv=list(p['arms'][arm]['argv']);argv[argv.index('--period')+1]='25'
  cap=Path('/mnt/c'+argv[argv.index('--cap')+1][2:].replace('\\','/'))
  assert not cap.exists();assert not Path(str(cap)+'-pycache').exists()
  argv[5:5]=['-I','-S','-B','-X','pycache_prefix='+argv[argv.index('--cap')+1]+'-pycache']
  start=time.monotonic();samples=[];child=None
  rec={'argv':argv,'environment_explicit':forward,'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   with (HERE/('caller-'+arm+'-CONTROLLER.log')).open('xb') as log:
    child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
    while child.poll() is None:
     c.bounds();assert not release_active(),'release priority';assert time.monotonic()-start<95,'root parent deadline'
     if not samples:
      snap=lock_sample(child.pid)
      if {6,9}<={x['fd'] for x in snap}:samples=snap
     time.sleep(.5)
    rec['returncode']=child.returncode;assert child.returncode==0
   assert samples,'No actual inherited root/global kernel locks observed';rec['kernel_lock_sample']=samples
   bound=read(cap/'bounded-launch.json');run=read(cap/'run-result.json')
   assert bound['guest_exited'] is True and bound['deadline_fired'] is False and bound['guest_observed_elapsed_s']<=55
   assert bound['expected_executable_sha256']==g['helpers']['console']['identity']['sha256']
   assert bound['harness_sha256']==g['helpers']['harness']['identity']['sha256']
   assert run['status']=='RUN_COMPLETE' and run['emu']=='console' and run['seconds']==45 and run['stop'] is None
   assert row(cap/'flycast.exe')==g['helpers']['console']['identity']
   assert row(cap/'fixture-warp.txt')==g['fixture']
   cfg=(cap/'emu.cfg').read_text();assert 'aica.LimitFPS = no' in cfg and 'rend.vsync = no' in cfg
   rec.update(cap=str(cap),bounded=bound,run=run,capture_files={q.relative_to(cap).as_posix():row(q) for q in cap.rglob('*') if q.is_file()},complete=True)
  finally:
   if child:c.cleanup(child)
   rec['controller_elapsed_s']=time.monotonic()-start;fresh(HERE/('caller-'+arm+'-PROCESS.json'),rec)
  result['arms'][arm]=rec;print(arm+' CALLER CAPTURE COMPLETE',flush=True)
 result['complete']=True
except BaseException as e:result['failure']=repr(e);raise
finally:
 result.update(C_free=c.freeC(),owned_bytes=c.owned_bytes());fresh(HERE/'ROOT-CALLER-PAIR-RESULT.json',result)
