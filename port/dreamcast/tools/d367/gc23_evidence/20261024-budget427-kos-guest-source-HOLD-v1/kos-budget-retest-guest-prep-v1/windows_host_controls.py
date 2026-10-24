"""Actual benign WindowsPython child/handle controls. No emulator or slots."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,types
HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and sys.pycache_prefix and not Path(sys.pycache_prefix).exists()
a=argparse.ArgumentParser();a.add_argument('--owned-sha256',required=True);a.add_argument('--entry-sha256',required=True);v=a.parse_args();p=HERE/'owned_process.py';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==v.owned_sha256
m=types.ModuleType('owned_process');m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__)
child=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(30)']);controls=[]
try:
 ident=m.identity(int(child._handle),child.pid);assert Path(ident['path']).resolve()==Path(sys.executable).resolve();controls.append('actual_owned_handle_identity')
 for key,value in [('creation_FILETIME',ident['creation_FILETIME']+1),('path','C:\\not-owned.exe'),('sha256','0'*64)]:
  wrong={**ident,key:value}
  try:m.terminate(wrong)
  except AssertionError:assert child.poll() is None;controls.append('wrong_'+key+'_refused_without_termination')
  else:raise AssertionError('Wrong instance accepted')
 result=m.terminate(ident);assert result['terminated_exact_instance'] and result['exit_observed'] and result['exit_code']==97;child.wait(timeout=3);assert child.returncode==97;controls.append('actual_exact_instance_terminated_and_exit_observed')
 again=m.terminate(ident);assert again['already_exited'];controls.append('already_exited_safe')
 p=HERE/'windows_entry.py';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==v.entry_sha256;entry=types.ModuleType('actual_entry');entry.__file__=str(p);exec(compile(raw,str(p),'exec'),entry.__dict__)
 def fault(*args):raise OSError('owned host synthetic witness fault')
 for kind in ['identity','write']:
  owned=subprocess.Popen([sys.executable,'-I','-S','-B','-c','import time;time.sleep(30)'])
  try:
   try:entry.record_owned(owned,sys.executable,dict(sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()),types.SimpleNamespace(identity=fault) if kind=='identity' else m,fault if kind=='write' else lambda _:None)
   except OSError:assert owned.poll() is not None;controls.append('actual_pre_timer_'+kind+'_fault_exact_object_terminated')
   else:raise AssertionError('Host fault was accepted')
  finally:
   if owned.poll() is None:owned.terminate();owned.wait(timeout=3)
 print(json.dumps(dict(status='WINDOWS_OWNED_BENIGN_CHILD_CONTROLS_PASS',controls=controls,guest=0,SDK=0,production_locks=0,child_identity=ident)))
finally:
 if child.poll() is None:child.terminate();child.wait(timeout=3)
