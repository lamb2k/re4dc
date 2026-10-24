"""Replay old exact-protocol tests plus V2 guards, without pending media reads."""
from pathlib import Path
import ast,copy,hashlib,json,os,sys,tempfile,types,unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'kos-budget-retest-guest-prep-v1'
def load(name,path):
 raw=Path(path).read_bytes();m=types.ModuleType(name);m.__file__=str(path);sys.modules[name]=m;exec(compile(raw,str(path),'exec',dont_inherit=True),m.__dict__);return m
def row(p):return dict(size=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
def frozen_parent():
 assert row(OLD/'TOOLCHAIN-SEAL.json')['sha256']=='7b5120956b13f1d25f50280120686a8efe45ed70f09ca14042722cb4eaa9997e'
 pins=json.loads((OLD/'TOOLCHAIN-SEAL.json').read_bytes())['members']
 for n in ['host_controls.py','common.py','controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py']:assert row(OLD/n)==pins[n]
 return pins
pins=frozen_parent();c=load('guest_common',HERE/'common.py');r=load('recovery_context',HERE/'recovery_context.py')
# Keep the original protocol and benign cleanup assertions, executing their
# actual new source. Three old actual-resource/poststage tests cannot pass until
# a real OFF/current baseline exists; pending refusal is tested below instead.
raw=(OLD/'host_controls.py').read_text();oldline="c=load('common');k=c.context();judge=load('judge');win=load('windows_entry');owner=load('owned_process')"
assert raw.count(oldline)==1
raw=raw.replace(oldline,"c=load('common');k=HOST_BASE;judge=load('judge');win=load('windows_entry');owner=load('owned_process')")
base=load('test_stage_base',c.MEDIA/'core.py')
prior=types.ModuleType('prior_protocol_tests');prior.__file__=str(HERE/'prior_protocol_tests.py');prior.HOST_BASE=base
exec(compile(raw,str(OLD/'host_controls.py'),'exec',dont_inherit=True),prior.__dict__)
excluded={'test_actual_resources_union','test_actual_poststage','test_extra_roots_hardlink_counted_once'}
def member(size=7,ino=1):return dict(size=size,dev=1,ino=ino,nlink=1,sha256='a'*64)
class Recovery(unittest.TestCase):
 def snapshot(self):return dict(roots=['/RAM/base'],members={'a':member()},unique_bytes=7)
 def extra(self,rows=None):return dict(roots=['/RAM/new'],members=rows or {},absent_roots=[])
 def test_syntax(self):
  for p in HERE.glob('*.py'):ast.parse(p.read_bytes())
 def test_controller_six_exact(self):
  for n in ['controller.py','post_slot.py','launch.py','windows_entry.py','owned_process.py','judge.py']:self.assertEqual(row(HERE/n),pins[n])
 def test_pending_binding_refused(self):
  with self.assertRaisesRegex(RuntimeError,'UNKNOWN'):r.binding_guard(dict(status='PENDING_OFF'))
 def test_actual_binding_absent(self):self.assertFalse((HERE/'RECOVERY-BINDING.json').exists())
 def test_actual_baseline_absent(self):self.assertFalse((HERE/'CURRENT-BASELINE.json').exists())
 def test_full_current_baseline_membership_required(self):
  with self.assertRaisesRegex(RuntimeError,'membership'):r.compare_baseline(self.snapshot(),dict(members={},unique_bytes=0))
 def test_changed_baseline_inode(self):
  b=self.snapshot();v=copy.deepcopy(b);v['members']['a']['ino']=2
  with self.assertRaisesRegex(RuntimeError,'inode'):r.compare_baseline(b,v)
 def test_changed_baseline_sha(self):
  b=self.snapshot();v=copy.deepcopy(b);v['members']['a']['sha256']='b'*64
  with self.assertRaisesRegex(RuntimeError,'digest'):r.compare_baseline(b,v,True)
 def test_link_increase_only(self):
  b=self.snapshot();v=copy.deepcopy(b);v['members']['a']['nlink']=2;r.compare_baseline(b,v)
  with self.assertRaisesRegex(RuntimeError,'nlink'):r.compare_baseline(v,b)
 def test_shared_inode_once(self):self.assertEqual(r.total({'a':member(),'b':member()}),7)
 def test_equal_sha_distinct_inode_twice(self):self.assertEqual(r.total({'a':member(),'b':member(ino=2)}),14)
 def test_conflicting_shared_inode_size(self):
  with self.assertRaisesRegex(RuntimeError,'length'):r.total({'a':member(),'b':member(size=8)})
 def test_delta(self):
  b=self.snapshot()
  with self.assertRaisesRegex(RuntimeError,'capacity'):r.account(b,b,self.extra({'new':member(size=r.DELTA+1,ino=2)}),r.ADMIT,r.ADMIT)
 def test_aggregate(self):
  b=self.snapshot();b['members']['a']['size']=r.AGG;b['unique_bytes']=r.AGG
  with self.assertRaisesRegex(RuntimeError,'capacity'):r.account(b,b,self.extra({'new':member(size=1,ino=2)}),r.ADMIT,r.ADMIT)
 def test_C_start(self):
  b=self.snapshot()
  with self.assertRaisesRegex(RuntimeError,'C admission'):r.account(b,b,self.extra(),r.ADMIT-1,r.ADMIT)
 def test_C_floor(self):
  b=self.snapshot()
  with self.assertRaisesRegex(RuntimeError,'C admission'):r.account(b,b,self.extra(),r.FLOOR-1,r.FLOOR)
 def test_cap_exact_boundary(self):
  b=self.snapshot();v=r.account(b,b,self.extra({'new':member(size=r.DELTA,ino=2)}),r.ADMIT,r.ADMIT);self.assertEqual(v['new_unique_bytes'],r.DELTA)
 def test_actual_RAM_inodes_hash_and_symlink(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'a').write_bytes(b'ABC');os.link(p/'a',p/'b');v=r.inventory([d],True);self.assertEqual(v['unique_bytes'],3);self.assertEqual(len(v['members']),2)
   (p/'c').symlink_to(p/'a')
   with self.assertRaisesRegex(RuntimeError,'symlink'):r.inventory([d])
 def test_missing_baseline_root_refused(self):
  with self.assertRaisesRegex(RuntimeError,'disappeared'):r.inventory(['/dev/shm/not-a-current-baseline-root-GC427'])
 def test_future_absence_is_charged_when_created(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d)/'future';self.assertEqual(r.inventory([str(p)],allow_absent=True)['unique_bytes'],0);p.mkdir();(p/'meta').write_bytes(b'12345');self.assertEqual(r.inventory([str(p)],allow_absent=True)['unique_bytes'],5)
 def test_no_root_omission(self):self.assertEqual(len(r.BASELINE_ROOTS),17);self.assertIn(str(r.OFF),r.BASELINE_ROOTS);self.assertIn(str(HERE.parent/'kos-budget-retest-guest-exec-v2'),r.BASELINE_ROOTS)
 def test_recovery_context_required_in_grant(self):
  g=prior.Host().grant();g.pop('recovery_context')
  with self.assertRaises(KeyError):c.grant_guard(g,'test',base)
 def test_wrong_recovery_context(self):
  g=prior.Host().grant();g['recovery_context']='IGNORE_MISSING_OLD_TRACKS'
  with self.assertRaises(AssertionError):c.grant_guard(g,'test',base)
 def test_original_failure_readbacks_unchanged(self):prior.Host().test_actual_original_failures_preserved()
 def producer(self):return dict(media_producer=dict(tool_source=r.MEDIA_TOOL_SOURCE,seal=dict(path=str(r.MEDIA_TOOL_ROOT/'TOOLCHAIN-SEAL.json'),identity=dict(size=8896,sha256=r.MEDIA_TOOL_SEAL)),off_complete=dict(path=str(r.OFF/'COMPLETE.json'),identity=None)))
 def test_V5_producer_schema_only(self):r.producer_guard(self.producer(),read_files=False)
 def test_V4_producer_refused(self):
  p=self.producer();p['media_producer']['tool_source']='18f2ffa79a63f81a8379f220014f9def86ec36d1'
  with self.assertRaisesRegex(RuntimeError,'ext4V5'):r.producer_guard(p,read_files=False)
 def test_wrong_producer_seal(self):
  p=self.producer();p['media_producer']['seal']['identity']['sha256']='0'*64
  with self.assertRaisesRegex(RuntimeError,'ext4V5'):r.producer_guard(p,read_files=False)
 def test_wrong_OFF_complete_path(self):
  p=self.producer();p['media_producer']['off_complete']['path']=str(r.ON/'COMPLETE.json')
  with self.assertRaisesRegex(RuntimeError,'completion path'):r.producer_guard(p,read_files=False)
 def test_account_overlapping_path_inode_race(self):
  b=self.snapshot()
  with self.assertRaisesRegex(RuntimeError,'Overlapping'):r.account(b,b,self.extra({'a':member(ino=2)}),r.ADMIT,r.ADMIT)
 def meta(self):return dict(kind='public synthetic base',tree='/RAM/cdroot',elf='/RAM/actual-producer.elf',warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,gdi=r.GDI)
 def test_exact_base_metadata_layout(self):r.metadata_semantics(self.meta())
 def test_wrong_base_redirect_LBA(self):
  for key in ['warp_lba','pad_lba','w11_lba']:
   j=self.meta();j[key]+=1
   with self.assertRaisesRegex(RuntimeError,'fixture layout'):r.metadata_semantics(j)
 def test_bool_base_LBA_refused(self):
  j=self.meta();j['warp_lba']=True
  with self.assertRaisesRegex(RuntimeError,'fixture layout'):r.metadata_semantics(j)
 def test_wrong_fixture_extent(self):
  j=self.meta();j['fixture_bytes']=8191
  with self.assertRaisesRegex(RuntimeError,'fixture layout'):r.metadata_semantics(j)
 def test_GDI_outside_track_refused(self):
  j=self.meta();j['gdi']=r.GDI.replace('track03.iso','../unverified.iso')
  with self.assertRaisesRegex(RuntimeError,'GDI'):r.metadata_semantics(j)
 def test_duplicate_base_json_field_refused(self):
  with self.assertRaisesRegex(RuntimeError,'Duplicate'):r.unique_json_pairs([('warp_lba',400),('warp_lba',999)])
 def test_RAM_actual_host_metadata_and_wrong_hash(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'base.json').write_text(json.dumps(self.meta()));(p/'track03.sha256').write_text('a'*64+'\n');pins=r.host_metadata(p,'a'*64);self.assertEqual(set(pins),{'base.json','track03.sha256'})
   with self.assertRaisesRegex(RuntimeError,'hash sidecar'):r.host_metadata(p,'b'*64)
 def test_unknown_base_metadata_field(self):
  j=self.meta();j['alternate_disc']='evil'
  with self.assertRaisesRegex(RuntimeError,'fields'):r.metadata_semantics(j)
 def binder_serialization(self,path):
  # Execute the actual successful top-level metadata-binding statements,
  # including the drift guard, baseline serialization, binding validation and
  # outputs construction. Only filesystem facts/identities are RAM fixtures.
  import datetime
  tree=ast.parse(Path(path).read_bytes());main=tree.body[-1];self.assertIsInstance(main,ast.If)
  def target(node,name):return isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in node.targets)
  start=next(i for i,n in enumerate(main.body) if target(n,'drift'));end=next(i for i,n in enumerate(main.body) if target(n,'outputs'))
  definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['encoded','actual_drift']]
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   here=Path(d)/'source';here.mkdir();root=here.parent/'review-kos-budget-retest-media-poststage-v2';root.mkdir()
   drift_bytes=(json.dumps([],indent=1)+'\n').encode();baseline=dict(roots=[str(Path(d)/'retained')],members={},unique_bytes=0)
   def fake_row(p):return dict(size=1641,sha256='9409bd8b090ec545cf7e927fc68ac63266b558c4907493deabee91a0836aef85') if Path(p).name=='BASELINE-DRIFT.json' else dict(size=1,sha256='a'*64)
   def forbidden_fresh(*args):raise AssertionError('Unexpected drift/refusal write on successful statement path')
   ns=dict(Path=Path,json=json,hashlib=hashlib,datetime=datetime,HERE=here,HANDOFF=root/'ROOT-RECOVERY-HANDOFF.json',final=root/'FINAL-READBACK.json',r=r,row=fake_row,fresh=forbidden_fresh,old=dict(members={}),prior={},baseline=baseline,h=dict(approved_old_to_current_drift_identity=dict(size=len(drift_bytes),sha256=hashlib.sha256(drift_bytes).hexdigest())),actual={a:dict(tracks={'track03.iso':dict(size=10,sha256='e'*64)}) for a in ['off','on']})
   with patch.object(r,'HERE',here),patch.object(os,'statvfs',return_value=types.SimpleNamespace(f_bavail=40*1024**3,f_frsize=1)):
    exec(compile(ast.Module(body=definitions,type_ignores=[]),str(path),'exec',dont_inherit=True),ns)
    exec(compile(ast.Module(body=main.body[start:end+1],type_ignores=[]),str(path),'exec',dont_inherit=True),ns)
   return ns
 def test_actual_successful_binder_statement_serialization(self):
  ns=self.binder_serialization(HERE/'bind_recovery.py')
  self.assertTrue(callable(ns['encoded']));self.assertEqual(json.loads(ns['baseline_bytes'])['status'],'EXPLICIT_CURRENT_RETAINED_BASELINE_AFTER_VERIFIED_FRESH_OFF')
  self.assertEqual(ns['binding']['baseline_identity'],dict(size=len(ns['baseline_bytes']),sha256=hashlib.sha256(ns['baseline_bytes']).hexdigest()))
  self.assertIs(ns['outputs']['CURRENT-BASELINE.json'],ns['baseline']);self.assertIn('RECOVERY-BINDING.json',ns['outputs'])
 def test_preserved_V3_shadowing_fails_actual_statements(self):
  with self.assertRaises(TypeError):self.binder_serialization(HERE.parent/'kos-budget-retest-guest-exec-v3/bind_recovery.py')

if __name__=='__main__':
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 suite=unittest.TestSuite()
 for name in unittest.defaultTestLoader.getTestCaseNames(prior.Host):
  if name not in excluded:suite.addTest(prior.Host(name))
 suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Recovery))
 result=unittest.TextTestRunner(verbosity=1).run(suite)
 report=dict(status='SOURCE_HOST_PENDING_OFF_PASS' if result.wasSuccessful() else 'SOURCE_HOST_PENDING_OFF_FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),pending_actual_environment_tests=sorted(excluded),actual_baseline=False,actual_OFF_identity=False,SDK=0,stage=0,guest=0,production_locks=0,fake_release_processes=0)
 with (HERE/'HOST-CONTROLS.json').open('x') as f:json.dump(report,f,indent=1);f.write('\n')
 raise SystemExit(not result.wasSuccessful())
