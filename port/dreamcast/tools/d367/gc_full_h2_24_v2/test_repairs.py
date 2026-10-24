"""Actual source-extracted V1 defect regressions; fake process/clock/OS only."""
from pathlib import Path
import ast,copy,json,types,unittest,tempfile,sys,re,os
HERE=Path(__file__).resolve().parent

def load(n):
 m=types.ModuleType('repair_'+n);m.__file__=str(HERE/(n+'.py'));exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__);return m
c=load('core');r=load('run')
class Repairs(unittest.TestCase):
 def popen_case(self,kind):
  clock={'value':0.};events=[];timers=[];processes=[]
  class Popen:
   def __init__(self,*a,**k):self.pid=101;self._handle=202;self.alive=True;self.returncode=None;processes.append(self);clock['value']+=298 if kind=='expired_create' else 0;events.append('Popen returned')
   def poll(self):return None if self.alive else self.returncode
   def terminate(self):self.alive=False;self.returncode=97;events.append('terminate')
   def wait(self,timeout=None):assert not self.alive;events.append('wait');return self.returncode
  class Timer:
   def __init__(self,delay,callback):self.delay=delay;self.callback=callback;self.started=False;timers.append(self)
   def start(self):
    if kind=='start_error':raise MemoryError('timer start failed')
    self.started=True;events.append('timer started')
  def delay():
   self.assertTrue(timers and timers[0].started);clock['value']=297;timers[0].callback();clock['value']=301
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   cap=Path(d)/'cap';cap.mkdir();(cap/'emu.cfg').write_text('aica.LimitFPS=no\nrend.vsync=no\n')
   def identity(handle,pid):
    events.append('identity begins')
    if kind=='blocked_identity':delay()
    return dict(sha256='a'*64,path=str(cap/'flycast.exe'))
   def fresh(path,j):
    if path.name=='OWNED-GUEST.json' and kind=='blocked_receipt':delay()
    events.append(path.name)
   tree=ast.parse((HERE/'windows_entry.py').read_bytes());node=next(x for x in ast.walk(tree) if isinstance(x,ast.ClassDef) and x.name=='OwnedPopen');w=next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name=='witness_exit')
   scaffold=ast.parse('def factory():\n guest=None\n timer=None\n PLACEHOLDER\n return OwnedPopen\n');scaffold.body[0].body[2]=copy.deepcopy(node);module=ast.Module(body=[copy.deepcopy(w),*scaffold.body],type_ignores=[]);ast.fix_missing_locations(module)
   env=dict(Path=Path,original=Popen,cap=cap,owner=types.SimpleNamespace(identity=identity),expected={'sha256':'a'*64},state={},c=types.SimpleNamespace(TIMER=297,LIMIT=300,verify=lambda *a:None,row=lambda p:{},fresh=fresh),time=types.SimpleNamespace(monotonic=lambda:clock['value']),threading=types.SimpleNamespace(Timer=Timer),re=re,v=types.SimpleNamespace(arm='off',nonce='b'*32,grant_sha='c'*64,seal='d'*64))
   exec(compile(module,'<exact Windows OwnedPopen and wait witness>','exec'),env)
   cls=env['factory']()
   if kind=='start_error':
    with self.assertRaises(MemoryError):cls([str(cap/'flycast.exe'),'disc.gdi'],cwd=cap)
   else:cls([str(cap/'flycast.exe'),'disc.gdi'],cwd=cap)
   self.assertFalse(processes[0].alive);self.assertIn('wait',events)
   if kind.startswith('blocked_'):self.assertLess(events.index('timer started'),events.index('identity begins'));self.assertIn('RETAINED-HANDLE-EXIT.json',events)
   if kind=='expired_create':self.assertLess(events.index('terminate'),events.index('identity begins'));self.assertFalse(timers[0].started)
 def test_blocked_identity_timer_prearmed(self):self.popen_case('blocked_identity')
 def test_blocked_receipt_timer_prearmed(self):self.popen_case('blocked_receipt')
 def test_expired_creation_return_kills_before_identity(self):self.popen_case('expired_create')
 def test_timer_start_failure_closes_actual_object(self):self.popen_case('start_error')
 def proof(self):
  return dict(kind='ACTUAL_RETAINED_POPEN_HANDLE_EXIT',native_handle=202,wait_observed=True,pid=101,command=[c.win(c.FINAL/'h2-off'/'flycast.exe'),'disc.gdi'],guest_path=c.win(c.FINAL/'h2-off'/'flycast.exe'),executable_sha256=c.read(HERE/'INPUTS.json')['helpers']['console']['identity']['sha256'],root_grant_sha256='a'*64,nonce='b'*32,source_seal='c'*64,exit_code=97,creation_started_monotonic=0.,exit_observed_monotonic=297.,observed_elapsed_s=297.)
 def test_native_proof_bound_to_attempt_and_clock(self):
  p=self.proof();self.assertTrue(c.handle_closure(p,'off','a'*64,'c'*64,'b'*32))
  for key,value in [('nonce','x'),('root_grant_sha256','x'),('source_seal','x'),('wait_observed',False),('native_handle',0),('exit_code',-1),('command',['other']),('observed_elapsed_s',298.),('exit_observed_monotonic',float('inf'))]:
   with self.assertRaises(RuntimeError):c.handle_closure(dict(p,**{key:value}),'off','a'*64,'c'*64,'b'*32)
 def test_bare_already_exited_not_exit_proof(self):
  owned=dict(pid=101,creation_FILETIME=22,path='owned',sha256='a'*64);p=dict(root_grant_sha256='a',source_seal='c',nonce='b',guest_identity=owned,query_result={'already_exited':True})
  with self.assertRaises(RuntimeError):c.query_closure(p,owned,'a','c','b')
 def test_unknown_cleanup_cannot_release_or_implicitly_return(self):
  # Execute the ACTUAL per-arm finally, with fake OS closes and UNKNOWN query.
  tree=ast.parse((HERE/'run.py').read_bytes());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');node=next(x for x in ast.walk(main) if isinstance(x,ast.Try) and x.finalbody and any(isinstance(y,ast.FunctionDef) and y.name=='check_closed' for y in x.finalbody))
  module=ast.Module(body=[ast.Try(body=[ast.Pass()],handlers=[],orelse=[],finalbody=copy.deepcopy(node.finalbody))],type_ignores=[]);ast.fix_missing_locations(module)
  closed=[];pauses=[];observations=[]
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);cap=root/'cap';cap.mkdir();proof=self.proof();owned=dict(pid=101,creation_FILETIME=22,path=proof['guest_path'],sha256=proof['executable_sha256']);(cap/'OWNED-GUEST.json').write_text(json.dumps(owned))
   class Child:
    pid=999
    def wait(self,timeout=None):return 0
   def killpg(*a):raise ProcessLookupError()
   def pause(seconds):
    self.assertEqual(closed,[]);pauses.append(seconds)
    if len(pauses)==1:raise KeyboardInterrupt('SIG-like interruption while UNKNOWN')
    (cap/'RETAINED-HANDLE-EXIT.json').write_text(json.dumps(proof))
   retainer=types.FunctionType(r.retain_reservations.__code__,r.retain_reservations.__globals__,argdefs=(pause,))
   fakec=types.ModuleType('fakecore');fakec.__dict__.update(c.__dict__);fakec.own_seal=lambda x:None
   env=dict(child=Child(),spawn_attempted=True,cap=cap,root=root,arm='off',locks={6:'root3',9:'global16'},rec={'nonce':'b'*32},active={'held':True,'interrupted':15},env={},command=lambda *a:['no-real-command'],subprocess=types.SimpleNamespace(STDOUT=-2,TimeoutExpired=TimeoutError,run=lambda *a,**k:types.SimpleNamespace(returncode=1)),os=types.SimpleNamespace(close=lambda fd:closed.append(fd),killpg=killpg,replace=os.replace),signal=types.SimpleNamespace(SIGTERM=15,SIGKILL=9),c=fakec,v=types.SimpleNamespace(grant_sha='a'*64,seal='c'*64),k=types.SimpleNamespace(capacity=lambda:(_ for _ in ()).throw(RuntimeError('floor/query UNKNOWN'))),parent=types.SimpleNamespace(release_active=lambda:True,kernel_locks=lambda:[]),retain_reservations=retainer)
   with self.assertRaisesRegex(RuntimeError,'Containment resolved; original H2 attempt failed'):exec(compile(module,'<actual per-arm finally>','exec'),env)
   self.assertGreaterEqual(len(pauses),2);self.assertEqual(closed,[9,6]);self.assertTrue(env['rec']['recovery_hold_entered']);self.assertTrue(env['rec']['closure']['proven']);self.assertFalse(env['active']['held'])
 def test_signal_handler_records_without_unwinding_held_controller(self):
  node=next(x for x in ast.walk(ast.parse((HERE/'run.py').read_bytes())) if isinstance(x,ast.FunctionDef) and x.name=='stop');m=ast.Module(body=[copy.deepcopy(node)],type_ignores=[]);ast.fix_missing_locations(m);e={'active':{'held':True,'interrupted':None}};exec(compile(m,'<actual signal handler>','exec'),e);e['stop'](15,None);self.assertEqual(e['active']['interrupted'],15)
  e['active']['held']=False
  with self.assertRaises(RuntimeError):e['stop'](15,None)
if __name__=='__main__':unittest.main(verbosity=2)