"""Root-granted fixed serial pair only. No SDK, stage or admission retries."""
from pathlib import Path
import argparse,hashlib,json,os,sys,subprocess,time,signal,fcntl,types,secrets
HERE=Path(__file__).resolve().parent

def acquire(fd,paths):
 try:os.fstat(fd)
 except OSError:pass
 else:raise RuntimeError('Reserved lock descriptor already open')
 for path in paths:
  p=Path(path);assert p.parent.is_dir();handle=os.open(p,os.O_RDWR|os.O_CREAT,0o600)
  try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:os.close(handle);continue
  if handle!=fd:os.dup2(handle,fd);os.close(handle)
  return str(p)
 raise RuntimeError('No free owned slot; no wait/retry')

def retain_reservations(check,recover,observe,publish,pause=time.sleep):
 """Never return or raise while closure is UNKNOWN; same controller owns FDs."""
 held=False
 while True:
  try:
   if check():return held
   held=True
   recover() # Only an explicit fresh root recovery request can invoke a query.
   if check():return held
   snapshot=observe();publish(dict(state='RECOVERY_HOLD_OWNED_LEASES_RETAINED',resources=snapshot))
  except BaseException as exc:
   held=True
   try:publish(dict(state='RECOVERY_HOLD_OWNED_LEASES_RETAINED',observation_failure=repr(exc)))
   except BaseException:pass
  try:pause(1)
  except BaseException:pass
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--grant',type=Path);ap.add_argument('--grant-sha');ap.add_argument('--seal');v=ap.parse_args();assert v.execute and v.grant and v.grant_sha and v.seal,'Separate root execution grant required'
 sealraw=(HERE/'SOURCE-SEAL.json').read_bytes();assert hashlib.sha256(sealraw).hexdigest()==v.seal;pins=json.loads(sealraw)['members']
 raw=(HERE/'core.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==pins['core.py']['sha256'];c=types.ModuleType('h2_core');c.__file__=str(HERE/'core.py');sys.modules['h2_core']=c;exec(compile(raw,c.__file__,'exec',dont_inherit=True),c.__dict__)
 c.own_seal(v.seal);assert c.sha(v.grant)==v.grant_sha;g=c.read(v.grant);parent,k,baseline=c.authenticate(g)
 assert not any(os.environ.get(n) for n in ['BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH','PYTHONPATH','PYTHONHOME','PYTHONPYCACHEPREFIX'])
 assert not parent.release_active();k.capacity(k.ADMIT);root=Path(c.FINAL);assert not root.exists(),'No rerun/overwrite';root.mkdir();c.fresh(root/'ATTEMPT.json',dict(grant=c.row(v.grant),source_seal=v.seal,guest_allowance_consumed=False))
 active={'held':False,'interrupted':None}
 def stop(sig,frame):
  if active['held']:active['interrupted']=sig
  else:raise RuntimeError('Owned interruption '+str(sig))
 for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,stop)
 result=dict(source=c.SOURCE,off_actual_producer_source=c.OFF_SOURCE,raw=c.RAW,arms={},complete=False,scope='H2 playback+heap observation; root memory acceptance separate')
 try:
  for arm in ['off','on']:
   cap=root/('h2-'+arm);cache=root/('cache-'+arm);assert not cap.exists() and not cache.exists();c.own_seal(v.seal);parent.check_poststage(g,k,arm);assert not parent.release_active();k.capacity(k.ADMIT)
   locks={};child=None;spawn_attempted=False;rec={'nonce':secrets.token_hex(16)};result['arms'][arm]=rec
   def capacity():
    if active['interrupted'] is not None:raise RuntimeError('Owned interruption '+str(active['interrupted']))
    k.capacity();s=os.statvfs('/mnt/c');assert s.f_bavail*s.f_frsize>=24*1024**3;old={(v['dev'],v['ino']) for v in baseline['members'].values()};new={} 
    for p in root.rglob('*'):
     if p.is_file():
      s=p.stat();key=(s.st_dev,s.st_ino)
      if key not in old:new[key]=s.st_size
    assert sum(new.values())<=5*1024**3//4;assert not parent.release_active(),'Release priority'
   inp=c.read(HERE/'INPUTS.json');py=inp['helpers']['python']['path']
   def command(cleanup=False,cleanup_id=0):
    return [py,'-I','-S','-B','-X','pycache_prefix='+c.win(root/((('cleanup-cache-'+arm+'-'+str(cleanup_id)) if cleanup else ('cache-'+arm)))),'-c',c.BOOT,c.win(HERE/'windows_entry.py'),c.sha(HERE/'windows_entry.py'),'--grant',c.win(v.grant),'--grant-sha',v.grant_sha,'--seal',v.seal,'--arm',arm,'--nonce',rec['nonce'],'--cleanup-id',str(cleanup_id),*(['--cleanup'] if cleanup else [])]
   env={'PATH':'/usr/bin:/bin','HOME':'/root','LANG':'C','RE4DC_EMU':'console','FP_NOLIMIT':'1','RE4DC_MAX_FLYCASTS':'16','TRACE_SLOTS':'16','RE4DC_CONSOLE_EXE':inp['helpers']['console']['windows_path'],'WSLENV':'RE4DC_EMU:FP_NOLIMIT:RE4DC_MAX_FLYCASTS:TRACE_SLOTS:RE4DC_CONSOLE_EXE'}
   try:
    active['held']=True
    locks[6]=acquire(6,['/root/work/lanes/stat-bytes23-complete-scratch/guest-slots/slot-'+str(i)+'.lock' for i in range(3)])
    locks[9]=acquire(9,['/root/probe/.trace.lock'+('' if i==0 else '.'+str(i)) for i in range(16)])
    rec['kernel_locks']=parent.kernel_locks();capacity();start=time.monotonic()
    with (root/(arm+'-controller.log')).open('x') as log:
     spawn_attempted=True
     child=subprocess.Popen(command(),stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,pass_fds=(6,9))
     while child.poll() is None:
      capacity();assert time.monotonic()-start<380,'Preparation+actual child+cleanup envelope380s';time.sleep(.5)
     assert child.returncode==0,'Owned Windows wrapper failed'
    bound=c.read(cap/'bounded-launch.json');rr=c.read(cap/'run-result.json');assert bound['harness_sha256']==inp['helpers']['harness']['identity']['sha256'] and bound['expected_executable_sha256']==inp['helpers']['console']['identity']['sha256']
    assert rr['fixtures']=={n:dict(src=c.win(p['path']),bytes=p['identity']['size'],sha256=p['identity']['sha256']) for n,p in inp['fixtures'].items()}
    rec['judgement']=c.judge((cap/'run-output.txt').read_text(errors='replace'),rr,bound);rec.update(run=c.row(cap/'run-result.json'),log=c.row(cap/'run-output.txt'),bounded=c.row(cap/'bounded-launch.json'),wrapper_seconds=time.monotonic()-start)
   finally:
    # No implicit exit/release on UNKNOWN: callbacks never leave this same
    # controller until an authenticated retained-handle or query wait proves exit.
    cleanup_ids=[];requests=set();closure={'proven':not spawn_attempted and child is None and not cap.exists(),'kind':'UNKNOWN'}
    def cleanup_query(number):
     with (root/(arm+'-cleanup-'+str(number)+'.log')).open('x') as f:q=subprocess.run(command(True,number),env=env,stdout=f,stderr=subprocess.STDOUT,timeout=10)
     cleanup_ids.append(number)
     if q.returncode!=0:raise RuntimeError('Exact-instance cleanup UNKNOWN')
    try:
     if child:
      try:os.killpg(child.pid,signal.SIGTERM)
      except ProcessLookupError:pass
      try:child.wait(timeout=3)
      except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
      if (cap/'OWNED-GUEST.json').exists():cleanup_query(0)
    except BaseException as exc:rec['cleanup_failure']=repr(exc)
    def check_closed():
     if closure['proven']:return True
     try:
      c.own_seal(v.seal);owned=c.read(cap/'OWNED-GUEST.json') if (cap/'OWNED-GUEST.json').exists() else None
      if (cap/'RETAINED-HANDLE-EXIT.json').exists():
       c.handle_closure(c.read(cap/'RETAINED-HANDLE-EXIT.json'),arm,v.grant_sha,v.seal,rec['nonce'],owned);closure.update(proven=True,kind='ACTUAL_RETAINED_POPEN_HANDLE_EXIT',proof=c.row(cap/'RETAINED-HANDLE-EXIT.json'));return True
      if owned is not None:
       for number in cleanup_ids:
        path=cap/('OWNED-CLEANUP-'+str(number)+'.json')
        if path.exists():
         try:c.query_closure(c.read(path),owned,v.grant_sha,v.seal,rec['nonce'])
         except BaseException:continue
         closure.update(proven=True,kind='INDEPENDENT_AUTHENTICATED_WAIT_EXIT',proof=c.row(path));return True
     except BaseException as exc:rec['closure_observation_failure']=repr(exc)
     return False
    def recover():
     for path in sorted(root.glob(arm+'-RECOVERY-REQUEST-*.json')):
      key=str(path)
      if key in requests:continue
      requests.add(key);request=c.read(path)
      assert request==dict(approved=True,action='QUERY_SAME_OWNED_INSTANCE_ONLY',grant_sha256=v.grant_sha,source_seal=v.seal,nonce=rec['nonce'],arm=arm),'Wrong root recovery request'
      assert (cap/'OWNED-GUEST.json').exists(),'No authentic exact-instance identity available; retain hold'
      cleanup_query(len(requests))
    def observe_hold():
     # Resource/priority/signal problems are recorded while reservations remain.
     return dict(parent_resources=k.capacity(),interrupted_signal=active['interrupted'],release_active=parent.release_active(),locks=parent.kernel_locks())
    def publish_hold(record):
     first=root/(arm+'-RECOVERY-HOLD.json');latest=root/(arm+'-RECOVERY-LATEST.json');payload=dict(record,nonce=rec['nonce'],closure=closure)
     if not first.exists():c.fresh(first,payload)
     pending=root/(arm+'-RECOVERY-PENDING.json');pending.write_text(c.__dict__['json'].dumps(payload)+'\n');os.replace(pending,latest)
    held=retain_reservations(check_closed,recover,observe_hold,publish_hold)
    rec['closure']=closure;rec['recovery_hold_entered']=held
    for fd in reversed(list(locks)):os.close(fd)
    active['held']=False
    if held or rec.get('cleanup_failure'):raise RuntimeError('Containment resolved; original H2 attempt failed, no further guest')
   capacity()
  result['complete']=True;result['s30_heap_ON_minus_OFF']=result['arms']['on']['judgement']['s30_heap_before']-result['arms']['off']['judgement']['s30_heap_before']
 except BaseException as exc:result['failure']=repr(exc);raise
 finally:c.fresh(root/'RESULT.json',result)
if __name__=='__main__':main()