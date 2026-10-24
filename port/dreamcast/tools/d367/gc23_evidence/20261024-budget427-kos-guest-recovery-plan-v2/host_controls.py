"""RAM-only controls; no production locks, release processes, media or guests."""
from pathlib import Path
import copy,hashlib,json,os,sys,tempfile,types,unittest
HERE=Path(__file__).resolve().parent
p=HERE/'recovery.py';r=types.ModuleType('recovery');r.__file__=str(p)
exec(compile(p.read_bytes(),str(p),'exec',dont_inherit=True),r.__dict__)

def member(size=10,ino=1,sha='a'*64):return dict(size=size,dev=1,ino=ino,nlink=1,sha256=sha)

class Controls(unittest.TestCase):
 def valid(self):
  return dict(source=r.SOURCE,predecessor_guest_seal=r.PARENT,state='FRESH_OFF_AND_ON_INDEPENDENTLY_READ_BACK',old_baseline_disappearance_acknowledged=True,restored_old_image_identity=False,off_build_provenance='RAIN_PRODUCED_DISABLED_PAYLOAD_EQUIVALENT',off_program_sha256=r.OFF_PROGRAM,on_track_identity=dict(size=1024618496,sha256=r.ON_TRACK),all14_exact=True,assets1697_exact=True,IP_exact=True,redirects6_exact=True,off_root='/tmp/off',on_root='/tmp/on',off_readback_path='/tmp/off.json',on_readback_path='/tmp/on.json',off_track_identity=dict(size=100,sha256='b'*64),off_readback_identity=dict(size=100,sha256='c'*64),on_readback_identity=dict(size=100,sha256='d'*64))
 def bad_binding(self,key,value):
  j=self.valid();j[key]=value
  with self.assertRaises(ValueError):r.binding_guard(j)
 def test_valid_schema_only_not_actual_acceptance(self):r.binding_guard(self.valid())
 def test_pending_OFF(self):self.bad_binding('state','PENDING_ACTUAL_OFF')
 def test_unknown_OFF_identity(self):self.bad_binding('off_track_identity',None)
 def test_unknown_readback(self):self.bad_binding('off_readback_identity',{})
 def test_unacknowledged_disappearance(self):self.bad_binding('old_baseline_disappearance_acknowledged',False)
 def test_restoration_claim(self):self.bad_binding('restored_old_image_identity',True)
 def test_invented_OFF_provenance(self):self.bad_binding('off_build_provenance','GC427_FRESH_BUILD')
 def test_wrong_OFF_main(self):self.bad_binding('off_program_sha256','a'*64)
 def test_wrong_ON_track(self):self.bad_binding('on_track_identity',dict(size=1024618496,sha256='a'*64))
 def test_missing_overlay_proof(self):self.bad_binding('all14_exact',False)
 def test_missing_assets(self):self.bad_binding('assets1697_exact',False)
 def test_missing_IP(self):self.bad_binding('IP_exact',False)
 def test_missing_redirects(self):self.bad_binding('redirects6_exact',False)
 def test_wrong_source(self):self.bad_binding('source','a'*40)
 def test_wrong_lineage(self):self.bad_binding('predecessor_guest_seal','a'*64)
 def test_path_traversal(self):self.bad_binding('off_root','/tmp/../off')
 def test_unknown_path(self):self.bad_binding('off_root',None)
 def test_inode_alias_count_once(self):self.assertEqual(r.unique_bytes({'a':member(),'b':member()}),10)
 def test_same_digest_distinct_inode_count_twice(self):self.assertEqual(r.unique_bytes({'a':member(),'b':member(ino=2)}),20)
 def test_same_inode_different_digest_refuses(self):
  with self.assertRaises(ValueError):r.unique_bytes({'a':member(),'b':member(sha='b'*64)})
 def test_same_inode_different_length_refuses(self):
  with self.assertRaises(ValueError):r.unique_bytes({'a':member(),'b':member(size=11)})
 def test_invalid_digest(self):
  with self.assertRaises(ValueError):r.unique_bytes({'a':member(sha='UNKNOWN')})
 def base(self):return dict(members={'a':member()},unique_bytes=10)
 def test_baseline_membership_loss(self):
  with self.assertRaises(ValueError):r.unchanged(self.base(),dict(members={}))
 def test_changed_baseline_bytes(self):
  with self.assertRaises(ValueError):r.bounds(self.base(),{'a':member(sha='b'*64)},r.ADMIT)
 def test_changed_inode(self):
  with self.assertRaises(ValueError):r.bounds(self.base(),{'a':member(ino=2)},r.ADMIT)
 def test_increased_links_allowed(self):
  v=member();v['nlink']=2;self.assertEqual(r.bounds(self.base(),{'a':v},r.ADMIT)['new_unique_bytes'],0)
 def test_decreased_links_refuse(self):
  b=self.base();b['members']['a']['nlink']=2
  with self.assertRaises(ValueError):r.bounds(b,{'a':member()},r.ADMIT)
 def test_C_admission(self):
  with self.assertRaises(ValueError):r.bounds(self.base(),{'a':member()},r.ADMIT-1,True)
 def test_C_floor(self):
  with self.assertRaises(ValueError):r.bounds(self.base(),{'a':member()},r.FLOOR-1)
 def test_delta_cap(self):
  with self.assertRaises(ValueError):r.bounds(self.base(),{'a':member(),'b':member(r.DELTA+1,2)},r.ADMIT)
 def test_aggregate_cap(self):
  b=dict(members={'a':member(r.AGGREGATE)},unique_bytes=r.AGGREGATE)
  with self.assertRaises(ValueError):r.bounds(b,{**b['members'],'b':member(1,2)},r.ADMIT)
 def test_boundary_exact(self):
  self.assertEqual(r.bounds(self.base(),{'a':member(),'b':member(r.DELTA,2)},r.ADMIT,True)['new_unique_bytes'],r.DELTA)
 def test_actual_RAM_hardlink_scan(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'one').write_bytes(b'123');os.link(p/'one',p/'two');v=r.scan([d]);self.assertEqual(v['unique_bytes'],3);self.assertEqual(len(v['members']),2)
 def test_actual_RAM_symlink_refusal(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);(p/'one').write_bytes(b'123');(p/'alias').symlink_to(p/'one')
   with self.assertRaises(ValueError):r.scan([d])
 def test_missing_root_refusal(self):
  with self.assertRaises(ValueError):r.scan(['/dev/shm/definitely-not-a-recovery-root-23'])
 def test_actual_tracks_not_receipt_substitution(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   p=Path(d);j=self.valid()
   for arm in ['off','on']:
    (p/arm).mkdir();(p/(arm+'.json')).write_text('{}');j[arm+'_root']=str(p/arm);j[arm+'_readback_path']=str(p/(arm+'.json'));j[arm+'_readback_identity']=r.identity(p/(arm+'.json'))
   with self.assertRaises(FileNotFoundError):r.readback_media(j)
 def test_actual_pending_file_refuses(self):
  with self.assertRaises(ValueError):r.binding_guard(json.loads((HERE/'BINDING-PENDING.json').read_text()))
 def test_no_baseline_prematurely_frozen(self):self.assertFalse((HERE/'CURRENT-BASELINE.json').exists())
 def test_fixed_controller_limits(self):
  j=json.loads((HERE/'RECOVERY-PLAN.json').read_text());c=j['controller']
  self.assertEqual([c[k] for k in ['harness_seconds','exact_child_seconds','admission_seconds','runtime_seconds','overall_seconds','root_slots','global_slots']],[45,55,180,95,1300,3,16])
  self.assertEqual(c['four_cases'],[dict(arm=a,frag=f,held=49152) for a,f in [('off',0),('on',0),('off',1),('on',1)]])

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 report=dict(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),production_media_read=0,SDK=0,stage=0,guest=0,production_locks=0,scope='Synthetic source accounting/pending refusal only')
 out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True)
 with out.open('x') as f:json.dump(report,f,indent=1);f.write('\n')
 raise SystemExit(not result.wasSuccessful())
