"""Small host temp files/fake children only; never invokes real stage main()."""
import hashlib,importlib.util,io,json,os,pathlib,signal,subprocess,sys,tempfile,time,types,unittest
P=pathlib.Path(__file__).parent

def load(n,path):
 s=importlib.util.spec_from_file_location(n,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=load('budget',P/'stage-budget.py');w=load('writer',P/'stage-writer.py');s=load('supervisor',P/'stage-supervisor.py')
class Writer(unittest.TestCase):
 def test_small_fake_stream_chunks_and_pre_post_guards(self):
  events=[];data=b'abcdefghij';dst=io.BytesIO();n,digest=w.copy_stream(io.BytesIO(data),dst,lambda **kw:events.append((dst.tell(),kw)),chunk=3)
  self.assertEqual(dst.getvalue(),data);self.assertEqual(n,10);self.assertEqual(digest,hashlib.sha256(data).hexdigest());self.assertEqual(len(events),9)
  self.assertEqual(events[0],(0,{'extra':3}));self.assertEqual(events[-1],(10,{}))
 def test_fault_retains_partial_output_charged(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);p=root/'failed-partial.bin';calls=[]
   def guard(**kw):
    if len(calls)==4:raise RuntimeError('injected after two chunks')
    calls.append(kw)
   with p.open('xb') as dst:
    with self.assertRaises(RuntimeError):w.copy_stream(io.BytesIO(b'0123456789'),dst,guard,chunk=3)
   self.assertEqual(p.read_bytes(),b'012345');self.assertGreaterEqual(b.measure(root)['bytes'],6)
 def test_same_bytes_replacement_refused_by_reviewed_identity(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'source';p.write_bytes(b'bytes');st=p.stat();plan={'source_device':st.st_dev,'source_inode':st.st_ino,'track_bytes':st.st_size,'source_mtime_ns':st.st_mtime_ns}
   self.assertEqual(w.require_source_identity(p,plan)['inode'],st.st_ino)
   replacement=pathlib.Path(d)/'replacement';replacement.write_bytes(b'bytes');os.utime(replacement,ns=(st.st_atime_ns,st.st_mtime_ns));os.replace(replacement,p)
   with self.assertRaises(ValueError):w.require_source_identity(p,plan)
 def test_prewrite_guard_refuses_before_any_write(self):
  dst=io.BytesIO()
  def fail(**kw):raise RuntimeError('space')
  with self.assertRaises(RuntimeError):w.copy_stream(io.BytesIO(b'abc'),dst,fail)
  self.assertEqual(dst.getvalue(),b'')
 def test_declared_metadata_only_and_payload_digest(self):
  data=(3348196).to_bytes(4,'little')+(3348196).to_bytes(4,'big');spec={'kind':'directory-size-both-endian','offset':37128,'old_file_bytes':3349284,'new_file_bytes':3348196,'bytes':8,'new_sha256':hashlib.sha256(data).hexdigest()}
  self.assertEqual(w.materialize(spec,None),data);spec['offset']=37129
  with self.assertRaises(ValueError):w.materialize(spec,None)
class Accounting(unittest.TestCase):
 def test_per_file_max_not_max_of_totals(self):
  a=types.SimpleNamespace(st_size=1,st_blocks=2);c=types.SimpleNamespace(st_size=2048,st_blocks=1)
  self.assertEqual(b.charge(a)+b.charge(c),3072)
 def test_sparse_failed_outputs_and_disappearing_temp(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'attempt-failed').mkdir();p=root/'attempt-failed/partial';p.write_bytes(b'x'*10)
   sparse=root/'sparse';f=sparse.open('wb');f.seek(200000);f.write(b'x');f.close();gone=root/'atomic-temp';gone.write_bytes(b'x')
   before=b.measure(root);self.assertGreaterEqual(before['bytes'],200011)
   def stat(path):
    if pathlib.Path(path)==gone:raise FileNotFoundError()
    return os.lstat(path)
   after=b.measure(root,lstat=stat);self.assertFalse(any(e['path']==str(gone) for e in after['entries']))
   guard=b.Guard(root,free=lambda:b.ADMISSION+1,cap=before['bytes']+100)
   with self.assertRaises(RuntimeError):guard.check(extra=101)
 def test_runtime_and_admission_floor_refuse(self):
  with tempfile.TemporaryDirectory() as d:
   guard=b.Guard(d,free=lambda:b.RUNTIME-1)
   with self.assertRaises(RuntimeError):guard.check()
   guard=b.Guard(d,free=lambda:b.ADMISSION-1)
   with self.assertRaises(RuntimeError):guard.check(admission=True)
 def test_next_write_reserves_runtime_floor(self):
  with tempfile.TemporaryDirectory() as d:
   guard=b.Guard(d,free=lambda:b.RUNTIME+10)
   with self.assertRaises(RuntimeError):guard.check(extra=11)
 def test_hardlinks_and_symlinks_not_exempted(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);p=root/'data';p.write_bytes(b'a');os.link(p,root/'link')
   with self.assertRaises(ValueError):b.measure(root)
   (root/'link').unlink();(root/'alias').symlink_to(p)
   with self.assertRaises(ValueError):b.measure(root)
class Supervisor(unittest.TestCase):
 def run_child(self,hook=None,sample=lambda:None,code='import time;time.sleep(20)',timeout=5):
  with tempfile.TemporaryFile() as stream:return s.supervise([sys.executable,'-c',code],stream,sample,after_spawn=hook,timeout=timeout,release='test-token')
 def assert_gone(self,r):
  self.assertTrue(r['child_exited']);self.assertFalse(pathlib.Path('/proc/'+str(r['owned']['pid'])).exists())
 def test_ancestor_alias_rejected_before_metadata(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'real').mkdir();(root/'alias').symlink_to(root/'real',target_is_directory=True)
   with self.assertRaises(ValueError):s.validate_root(root/'alias/newstage')
   self.assertFalse((root/'real/newstage').exists())
 def test_actual_closed_stdin_release_and_close_failure_still_cleans(self):
  with tempfile.TemporaryDirectory() as d:
   marker=pathlib.Path(d)/'ready'
   code='import os,time,pathlib;os.close(0);pathlib.Path('+repr(str(marker))+').write_text("ready");time.sleep(20)'
   def ready(info):
    end=time.monotonic()+2
    while not marker.exists():
     if time.monotonic()>end:raise RuntimeError('no child fd0-close handshake')
     time.sleep(.005)
   r=self.run_child(hook=ready,code=code);self.assertFalse(r['qualified']);self.assertIn('BrokenPipe',r['error']);self.assertIn('BrokenPipe',r['pipe_close_error']);self.assert_gone(r)
 def test_fault_after_spawn_cleanup_no_orphan(self):
  def fault(info):raise RuntimeError('injected after spawn before release')
  r=self.run_child(hook=fault);self.assertFalse(r['qualified']);self.assert_gone(r)
 def test_sampler_exception_cleanup_no_orphan(self):
  def fault():raise FileNotFoundError('injected sampler temp race')
  r=self.run_child(sample=fault);self.assertFalse(r['qualified']);self.assert_gone(r)
 def test_initial_identity_exception_finally_recovers(self):
  real=s.identity;calls=[]
  def first_fail(pid):
   if not calls:calls.append(pid);raise RuntimeError('injected first identity failure')
   return real(pid)
  s.identity=first_fail
  try:r=self.run_child()
  finally:s.identity=real
  self.assertFalse(r['qualified']);self.assert_gone(r)
 def test_timeout_and_success(self):
  r=self.run_child(timeout=.2);self.assertFalse(r['qualified']);self.assert_gone(r)
  r=self.run_child(code='import sys;assert sys.stdin.readline().strip()=="test-token"');self.assertTrue(r['qualified']);self.assert_gone(r)
 def test_foreign_identity_refuses_and_owned_cleanup_still_possible(self):
  child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(20)'],start_new_session=True)
  real=s.identity(child.pid);wrong=dict(real,proc_start='foreign')
  try:
   with self.assertRaises(RuntimeError):s.stop_owned(child,wrong)
   self.assertIsNone(child.poll())
  finally:s.stop_owned(child,real)
  self.assertIsNotNone(child.poll())
 def test_ignored_TERM_escalates_only_owned_group(self):
  child=subprocess.Popen([sys.executable,'-u','-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(20)'],stdout=subprocess.PIPE,start_new_session=True)
  try:
   self.assertEqual(child.stdout.readline().strip(),b'ready');owned=s.identity(child.pid);s.stop_owned(child,owned);self.assertEqual(child.returncode,-signal.SIGKILL)
  finally:
   if child.poll() is None:s.stop_owned(child,s.identity(child.pid))
   child.stdout.close()
 def test_final_sampler_failure_disqualifies_zero_exit(self):
  calls=[]
  def sample():
   calls.append(1)
   if len(calls)>1:raise RuntimeError('final sample failure')
  r=self.run_child(code='import time;time.sleep(.05)',sample=sample);self.assertFalse(r['qualified']);self.assert_gone(r)
if __name__=='__main__':unittest.main(verbosity=2)
