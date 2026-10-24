"""Three-finding regressions: mocked capture, real benign groups, pure Win errors."""
from pathlib import Path
import ast,copy,json,os,signal,struct,subprocess,sys,tempfile,time,types,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
for name in ['common','rain_record','process_group','future_master','observe_pair']:
 p=HERE/(name+'.py');m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
c=sys.modules['common'];rr=sys.modules['rain_record'];pg=sys.modules['process_group'];fm=sys.modules['future_master'];obs=sys.modules['observe_pair']

def valid_rows(pid):
 v=[0]*44;v[0]=2;v[1]=1;v[2]=v[3]=7;v[9]=v[10]=v[11]=11;v[12]=0x10c010c;v[13]=8;v[14]=1|2|4|8192|16384;v[17]=v[18]=320
 for n in ['SET','BOUND','CALLBACK','QUEUE','CONSUMED','RETURN_POSITIVE']:v[20+rr.COUNTERS.index(n)]=1
 b=struct.pack('<20I24H',*v)
 return [{'status':'HOST_RAM_BASE','pid':pid,'RAM':'0x10000000','offset':'0x36c740','host_alias_only':True},{'host_elapsed_s':1.0,'pid':pid,'record':rr.stable(b,b)}]

class Repairs(unittest.TestCase):
 def transport(self,mode):
  with tempfile.TemporaryDirectory(prefix='rain-v2-judge-',dir='/dev/shm') as t:
   root=Path(t);local=root/'kit';local.mkdir();(local/'TOOLCHAIN-SEAL.json').write_text('public fixture');seal=c.sha(local/'TOOLCHAIN-SEAL.json');c.fresh(local/'ROOT-GUEST-GRANT.json',{'toolchain_sha256':seal,'scope':'held0-r10c-console45-child55'})
   plan={'input_pins':{},'tools':{'console':{'path':'/mnt/c/public-console.exe'},'python':{'path':'/mnt/c/public-python.exe'},'stat3':{'path':'/public-stat3.sh'},'trace16':{'path':'/public-trace16.sh'}},'captures':{a:str(root/a) for a in ['off','on']},'cache_prefixes':{a:'C:/public-fresh-cache-'+a for a in ['off','on']}}
   class Child:
    pid=9999999;returncode=0
    def __init__(self):self.calls=0
    def poll(self):self.calls+=1;return None if self.calls==1 else 0
   def spawn(argv,**kw):
    arm=argv[-1];cap=root/arm;cap.mkdir();(cap/'flycast.pid').write_text('9999999')
    c.fresh(cap/'bounded-launch.json',{'guest_exited':True,'deadline_fired':False,'guest_observed_elapsed_s':45});c.fresh(cap/'run-result.json',{'status':'RUN_COMPLETE','seconds':45,'emu':'console','stop':None});(cap/'emu.cfg').write_text('aica.LimitFPS = no\nrend.vsync = no\n');(cap/'run-output.txt').write_text('kos squeeze: held=0 requested=0 frag=0\nwarp: room enter 10c (#1)\n')
    if arm=='on':
     path=root/'on-rain-records.jsonl';rows=valid_rows(9999999)
     if mode=='failed':rows=[{'status':'OBSERVER_FAILED','error':'public read failure'}]
     elif mode=='empty':rows=[]
     elif mode=='malformed':path.write_text('{bad');return Child()
     elif mode=='nojoin':rows[1]['record']['raw']='00'*128;rows[1]['record']=rr.stable(bytes(128),bytes(128))
     elif mode=='unstable':rows.append({'pid':9999999,'record':rr.stable(bytes(128),bytes([1])+bytes(127))})
     elif mode=='badpid':rows=valid_rows(123)
     if mode!='missing':path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
    return Child()
   def native(p):
    if str(p).startswith('/mnt/c/public-fresh-cache-'):return root/'absent-cache'
    return Path(p)
   signals={s:signal.getsignal(s) for s in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]}
   failed=None
   try:
    with patch.object(c,'HERE',local),patch.object(c,'verify_kit',return_value=plan),patch.object(c,'verify_inputs',return_value={}),patch.object(c,'native',side_effect=native),patch.object(c,'release_active',return_value=False),patch.object(obs,'floor',return_value={}),patch.object(obs,'lock_sample',return_value=[{'fd':6},{'fd':9}]),patch.object(obs,'kill_owned',return_value=None),patch.object(obs.subprocess,'Popen',side_effect=spawn),patch.object(obs.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='mock cleanup',stderr='')),patch.object(obs.time,'sleep',return_value=None):
     try:obs.main()
     except RuntimeError as e:failed=e
   finally:
    for s,h in signals.items():signal.signal(s,h)
   report=c.read(local/'PAIR-RESULT.json');self.assertTrue(report['capture_complete']);self.assertTrue(report['arms']['on']['capture_complete'])
   self.assertEqual(report['complete'],mode=='valid');self.assertEqual(report['diagnostic_accepted'],mode=='valid')
   if mode!='valid':self.assertIsNotNone(failed);self.assertIn(report['arms']['on']['diagnostic']['status'],['UNKNOWN','FAILED'])
 def test_failed_observer(self):self.transport('failed')
 def test_empty_observer(self):self.transport('empty')
 def test_missing_observer(self):self.transport('missing')
 def test_malformed_observer(self):self.transport('malformed')
 def test_no_valid_source_join(self):self.transport('nojoin')
 def test_invalid_among_valid_unknown(self):self.transport('unstable')
 def test_wrong_PID(self):self.transport('badpid')
 def test_valid_source_counters(self):self.transport('valid')
 def stage_group(self,rc=0,release=False):
  source=(HERE/'future_master.py').read_text();tree=ast.parse(source);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');node=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='run');run_source=ast.get_source_segment(source,node)
  with tempfile.TemporaryDirectory(prefix='rain-v2-groups-',dir='/dev/shm') as t:
   root=Path(t);holders=[];original=subprocess.Popen
   def start(*a,**kw):p=original(*a,**kw);holders.append(p);return p
   ns=dict(commands=[],host_argv=fm.host_argv,fresh=fm.fresh,base=root,env={'PATH':'/usr/bin:/bin'},work=root,subprocess=subprocess,time=time,c=types.SimpleNamespace(release_active=lambda:release),owned_bytes=lambda roots:0,finalroot=root,workroot=root,cap={'owned_cap_bytes':2**30,'C_floor_bytes':0},floor=lambda n:{},os=os,signal=signal,pg=pg)
   exec(compile(run_source,'actual_nested_run.py','exec'),ns)
   marker=root/'background.pid';code='import os,time,pathlib,sys;p=os.fork();pathlib.Path('+repr(str(marker))+').write_text(str(p)) if p else time.sleep(20);sys.exit('+str(rc)+')'
   caught=None
   try:
    with patch.object(subprocess,'Popen',side_effect=start):
     try:ns['run'](['/usr/bin/python3.12','-I','-S','-B','-c',code],'owned-control')
     except ValueError as e:caught=e
    self.assertEqual(caught is not None,bool(rc or release));self.assertTrue(marker.exists());pid=int(marker.read_text());self.assertFalse(Path('/proc/'+str(pid)).exists(),'descendant not reaped');self.assertEqual(pg.members(holders[0].pid),[])
    proof=c.read(root/'owned-control-CONTAINMENT.json');self.assertTrue(proof['contained']);self.assertTrue(proof['reaped_descendants'])
   finally:
    if holders:
     try:os.killpg(holders[0].pid,signal.SIGKILL)
     except ProcessLookupError:pass
     holders[0].wait()
     pg.cleanup(holders[0],0)
 def test_success_leader0_descendant(self):self.stage_group()
 def test_failure_descendant(self):self.stage_group(3)
 def test_release_descendant(self):self.stage_group(0,True)
 def test_containment_failure_is_failure(self):
  source=(HERE/'future_master.py').read_text();main=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='main');node=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='run')
  with tempfile.TemporaryDirectory(prefix='rain-v2-contained-failure-',dir='/dev/shm') as t:
   root=Path(t)
   fake=types.SimpleNamespace(pid=9999999,returncode=0,poll=lambda:0)
   ns=dict(commands=[],host_argv=fm.host_argv,fresh=fm.fresh,base=root,env={},work=root,subprocess=subprocess,time=time,c=types.SimpleNamespace(release_active=lambda:False),owned_bytes=lambda roots:0,finalroot=root,workroot=root,cap={'owned_cap_bytes':2**30,'C_floor_bytes':0},floor=lambda n:{},os=os,signal=signal,pg=pg)
   exec(compile(ast.get_source_segment(source,node),'actual_run_failure.py','exec'),ns)
   with patch.object(subprocess,'Popen',return_value=fake),patch.object(pg,'enable_subreaper',return_value=1),patch.object(pg,'cleanup',side_effect=RuntimeError('public containment failure')):
    with self.assertRaisesRegex(RuntimeError,'containment failure'):ns['run'](['/usr/bin/python3.12','--version'],'control')
   self.assertFalse(c.read(root/'control-CONTAINMENT-FAILED.json')['contained'])
 def test_OpenProcess_errors(self):
  source=(HERE/'cleanup_guest.py').read_text();node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='null_handle_status');scope={};exec(compile(ast.get_source_segment(source,node),'actual_error_classifier.py','exec'),scope);f=scope['null_handle_status']
  self.assertTrue(f(87)['contained'])
  for error in [0,5,6,1168,9999]:
   with self.assertRaises(RuntimeError):f(error)
if __name__=='__main__':unittest.main(verbosity=2)
