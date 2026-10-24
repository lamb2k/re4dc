"""Four fixed serial owned console children, only after exact root grant."""
from pathlib import Path
import json,os,secrets,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 overall=time.monotonic();c=sys.modules['guest_common'];k=c.context();g,gpath,seal=c.authorize(k);c.metadata_guard(g,k);c.check_inputs(g,k);c.capacity(k,k.ADMIT)
 resultpath=HERE/('RESULT-'+c.sha(gpath)+'.json');assert not resultpath.exists(),'No grant restart/overwrite'
 helper,pins=k.parent();judge=c.module('bounded_kos_judge',HERE/'judge.py',c.read(HERE/'TOOLCHAIN-SEAL.json')['members']['judge.py']['sha256'])
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,helper.stop)
 env={key:value for key,value in os.environ.items() if not key.startswith(('PYTHON','RE4DC_','HWTRACE','GC_','FP_','TRACE_','LD_')) and key not in ['BASH_ENV','ENV','SHELLOPTS','BASHOPTS','CDPATH']}
 forward=dict(RE4DC_EMU='console',FP_NOLIMIT='1',RE4DC_MAX_FLYCASTS='16',TRACE_SLOTS='16',RE4DC_CONSOLE_EXE=c.read(HERE/'INPUT-PINS.json')['helpers']['console']['windows_path'],PYTHONDONTWRITEBYTECODE='1')
 env.update(forward);env.update(GC_BUDGET_RETEST_GUEST_TOOLS=seal,GC_BUDGET_RETEST_GUEST_GRANT=str(gpath),GC_BUDGET_RETEST_GUEST_GRANT_SHA256=c.sha(gpath));env['WSLENV']=':'.join(forward)
 result=dict(complete_captures=False,all_allocated_bounded_KOS_pass=False,allocated_case_order=g['case_order'],source=c.SOURCE,scope='Allocated fixed corrected427 KOS48 cases only; root acceptance separate',grant_identity=c.row(gpath),stage=g['poststage'],cases={},H2='NOT_RUN',admission_seconds_cap=180,runtime_envelope_cap=95,actual_guest_cap=55,overall_cap=1300)
 try:
  for index in g['case_order']:
   assert time.monotonic()-overall<1280,'Overall active1280s +reserved20s cleanup/receipt cap'
   case=c.case(index,k);cap=Path(case['cap_WSL']);c.check_fresh(case);c.check_inputs(g,k);c.check_poststage(g,k,case['arm']);c.metadata_guard(g,k);c.capacity(k,k.ADMIT);assert not c.release_active(),'Release priority'
   argv=[*case['argv'][:4],'/usr/bin/python3','-I','-S','-B',str(HERE/'launch.py'),'--post-slot','--case',str(index)]
   assert not (HERE/'attempts'/(case['name']+'-ADMISSION.json')).exists() and not (HERE/'attempts'/(case['name']+'-CONTROLLER.log')).exists()
   rec=dict(index=index,case=case['name'],argv=argv,complete_capture=False);result['cases'][case['name']]=rec;start=time.monotonic();child=None;samples=[];runtime_deadline=None;nonce=secrets.token_hex(16);env['GC_BUDGET_RETEST_ADMISSION_NONCE']=nonce
   try:
    with (HERE/'attempts'/(case['name']+'-CONTROLLER.log')).open('xb') if (HERE/'attempts').exists() else _first_log(HERE/'attempts',case['name']) as log:
     child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
     while child.poll() is None:
      c.metadata_guard(g,k);c.capacity(k);assert not c.release_active(),'Release priority';now=time.monotonic();assert now-overall<1280,'Overall active1280s +reserved20s cleanup/receipt cap'
      admission=HERE/'attempts'/(case['name']+'-ADMISSION.json')
      if runtime_deadline is None:
       if admission.exists():
        h=c.read(admission);runtime_deadline=c.handshake_guard(h,index,nonce,c.sha(gpath),seal,start,now,c.windows_command({**case,'index':index},gpath,seal),child.pid);assert h['poststage']==g['poststage'];rec['admission']=h;rec['admission_elapsed_s']=h['prepared_monotonic']-start
       else:assert now-start<180,'Admission180s deadline'
      else:assert now<runtime_deadline,'Owned runtime95s deadline'
      if not samples:
       snapshot=c.kernel_sample(child.pid)
       if {6,9}<={v['fd'] for v in snapshot}:samples=snapshot
      time.sleep(.5)
     rec['returncode']=child.returncode;assert child.returncode==0 and samples and runtime_deadline is not None,'Actual authenticated admission/root/global locks and clean child required'
    bound=c.read(cap/'bounded-launch.json');run=c.read(cap/'run-result.json');inp=c.read(HERE/'INPUT-PINS.json')
    assert bound['guest_exited'] is True and bound['deadline_fired'] is False and bound['guest_observed_elapsed_s']<=55
    assert bound['expected_executable_sha256']==inp['helpers']['console']['identity']['sha256'] and bound['harness_sha256']==inp['helpers']['harness']['identity']['sha256']
    assert run['status']=='RUN_COMPLETE' and run['emu']=='console' and run['seconds']==45 and run['stop'] is None and not run['errors']
    assert c.row(cap/'flycast.exe')==inp['helpers']['console']['identity'];c.verify(cap/'fixture-warp.txt',inp['fixtures'][str(case['fragment'])]['identity'])
    assert c.read(cap/'PRE-POPEN.json')['before_guest'] is True and c.read(cap/'PNG-READBACK.json')['status']=='ACTUAL_PNG_DECODE_READBACK_PASS'
    pictures=c.read(cap/'PNG-READBACK.json')['images'];assert pictures
    for pin in pictures:
     path=Path(pin['path']);assert not path.is_absolute() and '..' not in path.parts and path.parts[0]=='shots';c.verify(cap/path,pin['identity']);assert (cap/path).read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    memory=judge.judge(cap/'run-output.txt',case['fragment'])
    rec.update(complete_capture=True,kernel_lock_sample=samples,bounded=bound,run=run,PNG_readback=c.row(cap/'PNG-READBACK.json'),actual_KOS_judge=memory,log_identity=c.row(cap/'run-output.txt'),pre_Popen=c.read(cap/'PRE-POPEN.json'))
   except BaseException as exc:rec['failure']=repr(exc);raise
   finally:
    if child:helper.cleanup(child)
    # The original exact55s timer owns the guest object. This extra cleanup
    # authenticates PID + OS creation FILETIME + exact image/path on a handle.
    try:
     if (cap/'OWNED-GUEST.json').exists() and not (cap/'OWNED-CLEANUP.json').exists():
      cache=Path(case['cache_WSL']+'-cleanup');assert not cache.exists()
      py=c.read(HERE/'INPUT-PINS.json')['helpers']['python']['path']
      cleanup=[py,'-I','-S','-B','-X','pycache_prefix='+c.win(cache),'-c',c.BOOTSTRAP,c.win(HERE/'windows_entry.py'),c.sha(HERE/'windows_entry.py'),'--case',str(index),'--tools',seal,'--grant',c.win(gpath),'--grant-sha256',c.sha(gpath),'--cleanup']
      with (HERE/'attempts'/(case['name']+'-CLEANUP.log')).open('xb') as out:rec['cleanup_returncode']=subprocess.run(cleanup,stdout=out,stderr=subprocess.STDOUT,env=env,timeout=10).returncode
      assert rec['cleanup_returncode']==0,'Exact-instance cleanup unknown; stop'
    except BaseException as exc:rec['cleanup_failure']=repr(exc);raise
    finally:rec['controller_elapsed_s']=time.monotonic()-start;c.fresh(HERE/'attempts'/(case['name']+'-PROCESS.json'),rec)
   result['cases'][case['name']]=rec;c.capacity(k)
  result['complete_captures']=True;result['all_allocated_bounded_KOS_pass']=all(v['actual_KOS_judge']['status']=='PASS_BOUNDED_KOS48' for v in result['cases'].values())
 except BaseException as exc:result['failure']=repr(exc);raise
 finally:
  try:result['resources']=c.capacity(k)
  except BaseException as exc:result['resource_observation_failure']=repr(exc)
  result['overall_elapsed_s']=time.monotonic()-overall;c.fresh(resultpath,result)
def _first_log(directory,name):
 directory.mkdir();return (directory/(name+'-CONTROLLER.log')).open('xb')
if __name__=='__main__':main()
