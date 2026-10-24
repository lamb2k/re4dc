"""Public host controls only. Never calls main/authenticate or launches Flycast."""
from pathlib import Path
import copy,hashlib,json,sys,types,unittest,tempfile,os,fcntl,subprocess
HERE=Path(__file__).resolve().parent
def load(n):
 m=types.ModuleType(n);m.__file__=str(HERE/(n+'.py'));sys.modules[n]=m;exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__);return m
c=load('core');r=load('run');owner=load('owned_process')
class Controls(unittest.TestCase):
 def good(self):
  rr=dict(status='RUN_COMPLETE',emu='console',seconds=c.SECONDS,stop=c.STOP,stopped='goal',errors=[])
  b=dict(guest_exited=True,deadline_fired=False,guest_observed_elapsed_s=100)
  t='route movie terminal=1 id=10003 frames=1465/1465 uploaded=1465 presented=1465 heap_before=80000\nroute movie terminal=1 id=10020 frames=571/571 uploaded=571 presented=571 heap_before=70000\nMOVIEARENA borrow id=10030 token=1 gen=1\nMOVIEARENA return token=1 used=363360 restored=1\nroute movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340 heap_before=48768\n'
  return t,rr,b
 def test_complete_and_heap(self):
  t,rr,b=self.good();j=c.judge(t,rr,b);self.assertEqual(j['s30_heap_before'],48768);self.assertEqual(j['memory_acceptance'],'ROOT_DECISION_REQUIRED')
 def test_partial_s30(self):
  t,rr,b=self.good()
  for old,new in [('340/340','339/340'),('uploaded=340','uploaded=339'),('presented=340','presented=339')]:
   with self.assertRaises(RuntimeError):c.judge(t.replace(old,new),rr,b)
 def test_missing_or_duplicate_terminal(self):
  t,rr,b=self.good()
  for text in [t.rsplit('route movie terminal',1)[0],t+t.splitlines()[-1]]:
   with self.assertRaises(RuntimeError):c.judge(text,rr,b)
 def test_arena_restore_and_order(self):
  t,rr,b=self.good()
  for text in [t.replace('restored=1','restored=0'),t.replace('return token=1','return token=2'),t.replace('MOVIEARENA borrow id=10030 token=1 gen=1\n','')]:
   with self.assertRaises(RuntimeError):c.judge(text,rr,b)
 def test_stop_and_transport(self):
  t,rr,b=self.good()
  for k,v in [('stop','other'),('stopped','seconds'),('status','RUN_ERROR'),('emu','window'),('seconds',301),('errors',['fault'])]:
   bad=dict(rr,**{k:v})
   with self.assertRaises(RuntimeError):c.judge(t,bad,b)
 def test_hard_deadline_and_exit(self):
  t,rr,b=self.good()
  for k,v in [('deadline_fired',True),('guest_exited',False),('guest_observed_elapsed_s',300.001),('guest_observed_elapsed_s',0)]:
   with self.assertRaises(RuntimeError):c.judge(t,rr,dict(b,**{k:v}))
 def test_fatal_no_pass(self):
  t,rr,b=self.good()
  for token in ['OOM','HALT','FAULT','MISSING','Out of memory','no contiguous block']:
   with self.assertRaises(RuntimeError):c.judge(t+'\n'+token,rr,b)
 def test_heap_difference_not_hidden(self):
  t,rr,b=self.good();j=c.judge(t.replace('heap_before=48768','heap_before=4096'),rr,b);self.assertEqual(j['s30_heap_before'],4096);self.assertNotIn('memory_pass',j)
 def test_fixed_route(self):
  g=dict(arms={a:dict(base='/mnt/c/base-'+a,syms='0x1 0x2 0x3') for a in ['off','on']});a=c.route(g,'on')
  for key,value in [('--seconds','290'),('--grace','5'),('--stop',c.STOP),('--name','gc427-full-h2-on')]:self.assertEqual(a[a.index(key)+1],value)
  self.assertIn('h2-warp.txt',a[a.index('--warp')+1]);self.assertIn('h2-pad.txt',a[a.index('--pad')+1]);self.assertLessEqual(c.SECONDS+c.GRACE,c.TIMER);self.assertEqual(c.TIMER+3,c.LIMIT)
  with self.assertRaises(RuntimeError):c.route(g,'new')
 def test_instance_cleanup_identity(self):
  good=dict(pid=1,creation_FILETIME=22,path='owned',sha256='a'*64);owner.matches(good,dict(good))
  for k,v in [('pid',2),('creation_FILETIME',23),('path','other'),('sha256','b'*64)]:
   with self.assertRaises(AssertionError):owner.matches(dict(good,**{k:v}),good)
 def test_nonwaiting_kernel_slot(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'slot.lock';fd=r.acquire(52,[str(p)])
   try:
    self.assertEqual(fd,str(p));info=Path('/proc/self/fdinfo/52').read_text();self.assertIn('FLOCK',info)
    with self.assertRaises(RuntimeError):r.acquire(53,[str(p)])
   finally:os.close(52)
 def test_grant_wrong_pair_or_unapproved(self):
  g=dict(approved=True,authorization='ONE_DIAGNOSTIC_427_FULL_H2_PAIR',source=c.SOURCE,off_actual_producer_source=c.OFF_SOURCE,raw=c.RAW,arm_order=['off','on'],actual_child_seconds=300,harness_seconds=290,grace=5,user_allowance_question='call_893faf52f48b4286ba0eb3333782ea2c',KOS_first=True,final=str(c.FINAL),root_slots=3,global_slots=16,KOS_results=[{}],parent_kit={'path':'/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-retest-guest-exec-v4'},parent_independent_CLEAR={'status':'CLEAR_SOURCE_AND_BINDING','path':'review','identity':{}},poststage={'path':'proof','identity':{}},arms={a:dict(base=b,syms='',raw={'identity':{'sha256':c.RAW[a]}},elf={'identity':{'sha256':c.ELF[a]}}) for a,b in [('off','/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off'),('on','/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on')]})
  self.assertTrue(c.grant(g))
  for key,value in [('approved',False),('source','689092bc'),('off_actual_producer_source',c.SOURCE),('raw',{'off':c.RAW['off'],'on':'77dc'}),('KOS_first',False),('actual_child_seconds',301),('arm_order',['on','off'])]:
   with self.assertRaises(RuntimeError):c.grant(dict(g,**{key:value}))
 def test_four_KOS_complete_first(self):
  j=dict(complete_captures=True,all_allocated_bounded_KOS_pass=True,source=c.SOURCE,stage={'proof':'same'},cases={str(i):dict(index=i,complete_capture=True,actual_KOS_judge={'status':'PASS_BOUNDED_KOS48'},bounded={'deadline_fired':False}) for i in range(4)})
  self.assertTrue(c.kos_guard([j],j['stage']))
  for kind in ['missing','duplicate','failure','differentpair']:
   bad=copy.deepcopy(j)
   if kind=='missing':del bad['cases']['3']
   if kind=='duplicate':bad['cases']['3']['index']=0
   if kind=='failure':bad['cases']['3']['actual_KOS_judge']['status']='FAIL_BOUNDED_KOS48'
   if kind=='differentpair':bad['source']='689092bc'
   with self.assertRaises(RuntimeError):c.kos_guard([bad],j['stage'])
 def test_source_drift(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'source.py';p.write_text('raise AssertionError("executed")')
   with self.assertRaises(RuntimeError):c.module('must_not_execute',p,'0'*64)
 def test_missing_root_grant_refuses_before_work(self):
  p=subprocess.run(['/usr/bin/python3','-I','-S','-B',str(HERE/'run.py')],capture_output=True,text=True,timeout=3)
  self.assertNotEqual(p.returncode,0);self.assertIn('Separate root execution grant required',p.stderr);self.assertFalse(Path(c.FINAL).exists())
 def test_preserved_owner_exact_source(self):
  inp=c.read(HERE/'INPUTS.json');self.assertEqual(c.row(HERE/'owned_process.py'),inp['parent_owned_process'])
if __name__=='__main__':unittest.main(verbosity=2)