"""Serial root-granted held0 pair; no guest without separate exact seal grant."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
import common as c
import rain_record as rr

def floor():
 w=int(subprocess.check_output([str(c.native(PLAN['tools']['python']['path'])),'-I','-S','-B','-c',"import shutil;print(shutil.disk_usage('C:\\\\').free)"],text=True).strip());l=__import__('shutil').disk_usage('/mnt/c').free
 c.need(min(w,l)>=24*1024**3,'Lower Windows/WSL floor');return {'Windows_free':w,'WSL_free':l,'lower':min(w,l)}
def lock_sample(group):
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if os.getpgid(int(p.name))!=group:continue
   for fd in [6,9]:
    q=p/'fd'/str(fd)
    try:target=os.readlink(q);info=(p/'fdinfo'/str(fd)).read_text()
    except FileNotFoundError:continue
    if ('/guest-slots/slot-' in target or '/probe/.trace.lock' in target) and 'lock:' in info:rows.append({'pid':int(p.name),'fd':fd,'target':target,'fdinfo':info})
  except (OSError,ProcessLookupError):continue
 return rows

def kill_owned(child):
 for sig in [signal.SIGTERM,signal.SIGKILL]:
  try:os.killpg(child.pid,sig)
  except ProcessLookupError:pass
  if sig==signal.SIGTERM:
   try:child.wait(timeout=3)
   except subprocess.TimeoutExpired:pass
 child.wait()
def main():
 global PLAN
 PLAN=c.verify_kit('guest');grant=c.read(c.HERE/'ROOT-GUEST-GRANT.json')
 c.need(grant.get('toolchain_sha256')==c.sha(c.HERE/'TOOLCHAIN-SEAL.json') and grant.get('scope')=='held0-r10c-console45-child55','Separate root held0 grant')
 c.verify_inputs(PLAN)
 output=c.HERE/'PAIR-RESULT.json';c.need(not output.exists(),'No resume/overwrite');report={'complete':False,'capture_complete':False,'diagnostic_accepted':False,'scope':'held0 console host observation only','arms':{}}
 env={k:v for k,v in os.environ.items() if not k.startswith(('PYTHON','RE4DC_','FP_','TRACE_','LD_')) and k not in {'BASH_ENV','ENV','SHELLOPTS','BASHOPTS','CDPATH'}}
 forward={'RE4DC_EMU':'console','FP_NOLIMIT':'1','RE4DC_MAX_FLYCASTS':'16','TRACE_SLOTS':'16','RE4DC_CONSOLE_EXE':str(c.native(PLAN['tools']['console']['path'])),'RAIN_QA_GUEST_ALLOCATED':c.sha(c.HERE/'TOOLCHAIN-SEAL.json')}
 # c.native is Linux here: convert only arguments passed to the Windows interpreter.
 def win(p):
  p=str(p)
  return 'C:'+p[6:].replace('/','\\') if p.startswith('/mnt/c/') else '\\\\wsl.localhost\\Ubuntu-24.04'+p.replace('/','\\')
 forward['RE4DC_CONSOLE_EXE']=win(PLAN['tools']['console']['path']);env.update(forward);env['WSLENV']=':'.join(forward)
 def stop(sig,frame):raise RuntimeError('Owned signal '+str(sig))
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,stop)
 try:
  for arm in ['off','on']:
   c.need(not c.release_active(),'Release priority');floor();cap=c.native(PLAN['captures'][arm]);c.need(not cap.exists(),'Fresh capture')
   cache=PLAN['cache_prefixes'][arm];c.need(not c.native('/mnt/c/'+cache[3:].replace('\\','/')).exists(),'Fresh cache prefix before Python startup')
   argv=['/usr/bin/bash','-p',PLAN['tools']['stat3']['path'],'/usr/bin/bash','-p',PLAN['tools']['trace16']['path'],PLAN['tools']['python']['path'],'-I','-S','-B','-X','pycache_prefix='+cache,win(c.HERE/'launch.py'),'guest',arm]
   child=None;start=time.monotonic();samples=[];record={'argv':argv,'environment':forward,'complete':False,'capture_complete':False,'diagnostic_accepted':False}
   try:
    with (c.HERE/('guest-'+arm+'.log')).open('x') as log:
     child=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
     while child.poll() is None:
      c.need(time.monotonic()-start<80,'Parent80s envelope');c.need(not c.release_active(),'Release priority');floor()
      if not samples:
       snap=lock_sample(child.pid)
       if {6,9}<={x['fd'] for x in snap}:samples=snap
      time.sleep(.5)
     c.need(child.returncode==0,'Bounded harness failed');record['returncode']=child.returncode
    c.need(samples,'No actual inherited kernel lock receipts')
    bound=c.read(cap/'bounded-launch.json');run=c.read(cap/'run-result.json')
    c.need(bound.get('guest_exited') is True and bound.get('deadline_fired') is False and bound.get('guest_observed_elapsed_s',999)<=55,'Exact55 child qualification')
    c.need(run.get('status')=='RUN_COMPLETE' and run.get('seconds')==45 and run.get('emu')=='console' and run.get('stop') is None,'Actual fixed45 console request')
    c.need('aica.LimitFPS = no' in (cap/'emu.cfg').read_text() and 'rend.vsync = no' in (cap/'emu.cfg').read_text(),'Actual explicitFPS configuration')
    text=(cap/'run-output.txt').read_text(errors='replace')
    kos=[line for line in text.splitlines() if 'kos squeeze:' in line];record['kos_squeeze_lines']=kos
    record['held0_observed']=bool(kos and all('held=0 requested=0 frag=0' in line for line in kos))
    c.need(record['held0_observed'],'Actual held0 profile not observed')
    c.need('warp: room enter 10c (#1)' in text,'Authenticated route room endpoint absent')
    images=sorted((cap/'shots').rglob('*.png')) if (cap/'shots').exists() else []
    record['image_evidence']={'status':'FILES_PRESENT_UNREVIEWED' if images else 'NO_IMAGE_EVIDENCE','files':{str(p.relative_to(cap)):c.row(p) for p in images}}
    record['diagnostic_record_scope']='Double-read hostRAM raw/counters only; missing or invalid samples remain UNKNOWN, never physical cache/presentation proof'
    record.update(capture_complete=True,kernel_lock_sample=samples,bounded=bound,run=run)
    if arm=='on':
     pidfile=cap/'flycast.pid';expected_pid=int(pidfile.read_text()) if pidfile.exists() else None
     record['diagnostic']=rr.judge_file(cap.parent/(cap.name+'-rain-records.jsonl'),expected_pid)
     record['diagnostic_accepted']=record['diagnostic']['diagnostic_accepted']
    else:record['diagnostic']={'status':'NOT_COMPILED_IN_OFF','diagnostic_accepted':False}
    record['complete']=record['capture_complete'] and (arm=='off' or record['diagnostic_accepted'])
   finally:
    if child:
     # WSL process-group cleanup alone is not Windows-child containment.
     cleanup_argv=[PLAN['tools']['python']['path'],'-I','-S','-B',win(c.HERE/'cleanup_guest.py'),arm]
     cleanup_ok=False
     try:
      cleanup=subprocess.run(cleanup_argv,env=env,capture_output=True,text=True,timeout=5)
      cleanup_ok=cleanup.returncode==0
      record['exact_Windows_cleanup']={'returncode':cleanup.returncode,'stdout':cleanup.stdout,'stderr':cleanup.stderr}
     except BaseException as e:record['exact_Windows_cleanup']={'failure':repr(e)}
     finally:kill_owned(child)
     record['parent_elapsed_s']=time.monotonic()-start;report['arms'][arm]=record
     c.need(cleanup_ok,'Exact Windows cleanup not established')
    record['parent_elapsed_s']=time.monotonic()-start;report['arms'][arm]=record
  report['capture_complete']=all(r.get('capture_complete') is True for r in report['arms'].values()) and len(report['arms'])==2
  report['diagnostic_accepted']=report['arms']['on'].get('diagnostic_accepted') is True
  report['complete']=report['capture_complete'] and report['diagnostic_accepted']
  c.need(report['diagnostic_accepted'],'ON diagnostic evidence FAILED or UNKNOWN')
 except BaseException as e:report['failure']=repr(e);raise
 finally:c.fresh(output,report)
