"""Pure/public host controls and benign owned-child cleanup; no production slots."""
from pathlib import Path
import ast,copy,json,os,sys,tempfile,time,types,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
def load(name):
 p=HERE/(name+'.py');m=types.ModuleType(name);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
c=load('common');k=c.context();judge=load('judge');win=load('windows_entry');owner=load('owned_process')
class Host(unittest.TestCase):
 def test_syntax(self):
  for p in HERE.glob('*.py'):ast.parse(p.read_text())
 def grant(self):
  g=c.read(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json');g.update(approved=True,kit_sha256='test');return g
 def test_grant_exact(self):c.grant_guard(self.grant(),'test',k)
 def test_grant_unapproved(self):
  with self.assertRaises(AssertionError):c.grant_guard(c.read(HERE/'ROOT-GUEST-GRANT-TEMPLATE.json'),'test',k)
 def bad_grant(self,change):
  g=self.grant();change(g)
  with self.assertRaises(AssertionError):c.grant_guard(g,'test',k)
 def test_grant_H2(self):self.bad_grant(lambda g:g.update(H2=True))
 def test_grant_timer(self):self.bad_grant(lambda g:g.update(exact_child_seconds=56))
 def test_grant_admission(self):self.bad_grant(lambda g:g.update(admission_seconds=181))
 def test_grant_parent(self):self.bad_grant(lambda g:g.update(parent_seconds=96))
 def test_grant_overall(self):self.bad_grant(lambda g:g.update(overall_seconds=1301))
 def test_grant_wrong_source(self):self.bad_grant(lambda g:g.update(source='c2f9'))
 def test_grant_cap_raise(self):self.bad_grant(lambda g:g.update(new_delta_cap=k.DELTA+1))
 def test_grant_aggregate_raise(self):self.bad_grant(lambda g:g.update(aggregate_cap=k.AGG+1))
 def test_grant_case_expansion(self):self.bad_grant(lambda g:g.update(case_order=[0,1,2,3,4]))
 def test_grant_subsets(self):
  for cases in [[0,1],[2,3]]:g=self.grant();g['case_order']=cases;c.grant_guard(g,'test',k)
 def handshake(self):return dict(phase='AUTHENTICATED_BEFORE_WINDOWS_PYTHON',case=0,pid=43,pgid=42,nonce='a'*32,grant_sha256='grant',guest_kit_sha256='seal',prepared_monotonic=110,cap_absent=True,cache_absent=True,helpers_verified=True,locks=[dict(fd=6),dict(fd=9)],argv=['pinned'])
 def handshake_run(self,h=None,now=120):return c.handshake_guard(self.handshake() if h is None else h,0,'a'*32,'grant','seal',100,now,['pinned'],42)
 def test_handshake_exact(self):self.assertEqual(self.handshake_run(),205)
 def bad_handshake(self,change):
  h=self.handshake();change(h)
  with self.assertRaises(AssertionError):self.handshake_run(h)
 def test_handshake_wrongcase(self):self.bad_handshake(lambda h:h.update(case=1))
 def test_handshake_forgednonce(self):self.bad_handshake(lambda h:h.update(nonce='b'*32))
 def test_handshake_wronggrant(self):self.bad_handshake(lambda h:h.update(grant_sha256='other'))
 def test_handshake_wrongkit(self):self.bad_handshake(lambda h:h.update(guest_kit_sha256='other'))
 def test_handshake_wrongargv(self):self.bad_handshake(lambda h:h.update(argv=['unreviewed']))
 def test_handshake_missing(self):
  with self.assertRaises((KeyError,TypeError)):c.handshake_guard({},0,'a'*32,'grant','seal',100,120,['pinned'],42)
 def test_handshake_wrong_processgroup(self):self.bad_handshake(lambda h:h.update(pgid=99))
 def test_handshake_late(self):
  with self.assertRaises(AssertionError):self.handshake_run(now=280.001)
 def test_handshake_future(self):self.bad_handshake(lambda h:h.update(prepared_monotonic=121))
 def test_handshake_preexisting(self):self.bad_handshake(lambda h:h.update(prepared_monotonic=99))
 def test_handshake_missinglock(self):self.bad_handshake(lambda h:h.update(locks=[dict(fd=6)]))
 def test_handshake_existingcache(self):self.bad_handshake(lambda h:h.update(cache_absent=False))
 def test_actual_helpers(self):c.check_inputs(self.grant(),k)
 def test_actual_poststage(self):
  for a in ['off','on']:c.check_poststage(self.grant(),k,a,hash_tracks=False)
 def test_actual_resources_union(self):
  v=c.capacity(k);self.assertLess(v['new_unique_bytes'],k.DELTA);self.assertLess(v['aggregate_bytes'],k.AGG)
 def test_actual_kernel_locks_not_env(self):
  with self.assertRaises((AssertionError,OSError)):c.kernel_locks()
 def test_case_bounds(self):
  for x in [-1,4,True]:
   with self.assertRaises(AssertionError):c.case(x,k)
 def test_existing_cache(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   with self.assertRaises(AssertionError):c.check_fresh(dict(cap_WSL=d+'/absent',cache_WSL=d))
 def test_duplicateFPS(self):
  with self.assertRaises(AssertionError):win.config_guard('aica.LimitFPS = no\naica.LimitFPS = yes\nrend.vsync = no\n')
 def test_wrongFPS(self):
  with self.assertRaises(AssertionError):win.config_guard('aica.LimitFPS = yes\nrend.vsync = no\n')
 def test_missingFPS(self):
  with self.assertRaises(AssertionError):win.config_guard('rend.vsync = no\n')
 def test_exactFPS(self):win.config_guard('[config]\naica.LimitFPS = no\nrend.vsync = no\n')
 def test_owned_PID_reuse(self):
  a=dict(pid=1,creation_FILETIME=2,path='owned',sha256='hash')
  with self.assertRaises(AssertionError):owner.matches({**a,'creation_FILETIME':3},a)
 def test_release_is_mocked_no_process(self):
  with patch.object(c.Path,'iterdir',return_value=[Path('/proc/123456')]),patch.object(c.Path,'read_bytes',return_value=b'/bin/bash\0/root/rr/bin/rr-cycle.sh\0'):self.assertTrue(c.release_active())
  with patch.object(c.Path,'iterdir',return_value=[Path('/proc/123456')]),patch.object(c.Path,'read_bytes',return_value=b'/usr/bin/python3\0-c\0rr-cycle.sh\0'):self.assertFalse(c.release_active())
 def test_metadata_root_escape(self):
  g=self.grant();g['metadata_allowlists']['/outside']=[]
  with self.assertRaises(AssertionError):c.metadata_guard(g,k)
 def test_metadata_member_escape(self):
  g=self.grant();g['metadata_allowlists'][str(c.META_ROOTS[0])].append('../outside.json')
  with self.assertRaises(AssertionError):c.metadata_guard(g,k)
 def synthetic(self,head=4096,frag=0,goal=True,frame=960):return f'kos squeeze: held=49152 requested=49152 frag={frag} pieces={1 if frag==0 else 12}\n'+('warp: alert at room frame 30 (entry 1)\n' if goal else '')+f'kos watch: frame={frame} free={head} used=100 break=0 headroom={head} min={head} top=2000 holes={head-2000}\n'
 def run_log(self,text,frag=0):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:p=Path(d)/'synthetic';p.write_text(text);return judge.judge(p,frag)
 def test_KOS_exact4K(self):self.assertEqual(self.run_log(self.synthetic())['status'],'PASS_BOUNDED_KOS48')
 def test_KOS_under4K(self):self.assertEqual(self.run_log(self.synthetic(head=4000))['status'],'FAIL_BOUNDED_KOS48')
 def test_KOS_wrongfrag(self):self.assertEqual(self.run_log(self.synthetic(frag=1))['status'],'UNKNOWN_INCOMPLETE_KOS_OBSERVATION')
 def test_KOS_missinggoal(self):self.assertEqual(self.run_log(self.synthetic(goal=False))['status'],'UNKNOWN_INCOMPLETE_KOS_OBSERVATION')
 def test_KOS_incompleteframe(self):self.assertEqual(self.run_log(self.synthetic(frame=30))['status'],'UNKNOWN_INCOMPLETE_KOS_OBSERVATION')
 def test_KOS_malformed(self):self.assertEqual(self.run_log(self.synthetic().replace('break=0','break=8'))['status'],'UNKNOWN_INCOMPLETE_KOS_OBSERVATION')
 def test_KOS_HALT(self):self.assertEqual(self.run_log(self.synthetic()+'HALT\n')['status'],'FAIL_BOUNDED_KOS48')
 def test_actual_original_failures_preserved(self):
  base=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/qa-memory-media-aab-v1/captures')
  for frag,expected in [(0,4000),(1,4016)]:
   p=base/('kos-on-49152-'+str(frag))/'run-output.txt';v=judge.judge(p,frag);self.assertEqual(v['minimum_headroom'],expected);self.assertEqual(v['status'],'FAIL_BOUNDED_KOS48')
 def test_owned_deadline_cleanup(self):
  helper,pins=k.parent()
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'pid';code='import os,time,pathlib;pathlib.Path('+repr(str(p))+').write_text(str(os.getpid()));time.sleep(20)'
   with self.assertRaises(AssertionError):helper.run_child(['/usr/bin/python3','-I','-S','-B','-c',code],Path(d)/'log',time.monotonic()+.25,lambda:None)
   with self.assertRaises(ProcessLookupError):os.kill(int(p.read_text()),0)
 def test_sealed_unknownfile(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'tiny.py').write_text('x=1\n');(p/'TOOLCHAIN-SEAL.json').write_text(json.dumps({'members':{'tiny.py':c.row(p/'tiny.py')}}));seal=c.sha(p/'TOOLCHAIN-SEAL.json')
   with patch.object(c,'HERE',p):
    c.sealed(seal);(p/'unexpected.json').write_text('{}')
    with self.assertRaises(AssertionError):c.sealed(seal)
 def test_extra_roots_hardlink_counted_once(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'guest').mkdir();(p/'meta').mkdir();(p/'guest/a.json').write_bytes(b'123456789');os.link(p/'guest/a.json',p/'meta/b.json');base=k.capacity()['aggregate_bytes']
   with patch.object(c,'HERE',p/'guest'),patch.object(c,'META_ROOTS',[p/'meta']):self.assertEqual(c.capacity(k)['aggregate_bytes'],base+9)
 def test_atomic_handshake(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'test-ADMISSION.json';c.publish_admission(p,self.handshake());self.assertEqual(c.read(p),self.handshake());self.assertEqual(p.stat().st_ino,p.with_name('test-ADMISSION-PREPARED.json').stat().st_ino)
   with self.assertRaises(FileExistsError):c.publish_admission(p,self.handshake())
 def test_optimized_entry_refused(self):
  import subprocess
  v=subprocess.run(['/usr/bin/python3','-I','-S','-B','-O',str(HERE/'launch.py')],capture_output=True,text=True,timeout=3);self.assertNotEqual(v.returncode,0);self.assertIn('Optimized Python refused',v.stderr)
if __name__=='__main__':
 assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Host));c.fresh(HERE/'HOST-CONTROLS.json',dict(tests=r.testsRun,success=r.wasSuccessful(),failures=len(r.failures),errors=len(r.errors),production_locks=0,SDK=0,stage=0,guests=0,fake_release_processes=0));raise SystemExit(not r.wasSuccessful())
