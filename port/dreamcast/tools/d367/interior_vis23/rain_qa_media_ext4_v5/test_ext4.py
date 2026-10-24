"""Focused ext4 publication/cache-boundary controls; tiny owned fixtures only."""
from pathlib import Path
import sys,types,tempfile,unittest,json,ast,os
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
for name in ['common','process_group','future_master']:
 m=types.ModuleType(name);m.__file__=str(HERE/(name+'.py'));sys.modules[name]=m;exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec',dont_inherit=True),m.__dict__)
f=sys.modules['future_master']
class Ext4(unittest.TestCase):
 def test_kernel_mount_selection_and_bridge_refusal(self):
  mi='1 0 8:0 / / rw - ext4 /dev/sdc rw\n2 1 0:2 / /mnt/c rw - 9p C: rw\n'
  self.assertEqual(f.require_ext4('/root/probe/new',mi)['filesystem'],'ext4')
  with self.assertRaises(ValueError):f.require_ext4('/mnt/c/new',mi)
  self.assertEqual(f.require_ext4('/root/probe')['filesystem'],'ext4')
 def fixture(self,root):
  work=root/'work';images=work/'off'/'iso-out';base=root/'final';images.mkdir(parents=True);base.mkdir()
  for i,n in enumerate(f.TRACKS):(images/n).write_bytes(bytes([i])*128)
  return work,images,base,{n:f.row(images/n) for n in f.TRACKS}
 def test_bulk_publish_exact_and_nonfresh_refusal(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d));calls=[];f.publish_tracks(i,b,p,lambda:calls.append(1));self.assertEqual(len(calls),3)
   self.assertEqual({n:f.row(b/n) for n in f.TRACKS},p)
   with self.assertRaises(ValueError):f.publish_tracks(i,b,p,lambda:None)
 def test_source_drift_refuses_before_publication(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d));(i/f.TRACKS[0]).write_bytes(b'changed')
   with self.assertRaises(ValueError):f.publish_tracks(i,b,p,lambda:None)
   self.assertEqual(list(b.iterdir()),[])
 def test_symlink_source_and_destination_refused(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d));dest=b/f.TRACKS[0];dest.symlink_to(i/f.TRACKS[0])
   with self.assertRaises(ValueError):f.publish_tracks(i,b,p,lambda:None)
   dest.unlink();original=i/f.TRACKS[0];other=i/'other';original.rename(other);original.symlink_to(other)
   with self.assertRaises(ValueError):f.publish_tracks(i,b,p,lambda:None)
 def test_only_verified_exact_cache_tracks_retired(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d));keep=i/'KEEP.json';keep.write_bytes(b'keep');f.publish_tracks(i,b,p,lambda:None);f.fresh(b/'FINAL-VERIFIED-BEFORE-CACHE-RETIREMENT.json',{'tracks':p,'all1715_files_exact':True,'sourceIP_exact':True,'new_media_identity':True});f.retire_verified_tracks(i,b,p,w)
   self.assertEqual(keep.read_bytes(),b'keep');self.assertTrue(all(not(i/n).exists() for n in f.TRACKS));self.assertTrue(all((b/n).exists() for n in f.TRACKS));self.assertTrue((b/'EXT4-CACHE-RETIREMENT-DONE.json').exists())
 def test_retirement_wrong_owner_drift_or_hardlink_refused(self):
  for kind in ['owner','finaldrift','hardlink']:
   with self.subTest(kind=kind),tempfile.TemporaryDirectory(dir='/dev/shm') as d:
    w,i,b,p=self.fixture(Path(d));f.publish_tracks(i,b,p,lambda:None);f.fresh(b/'FINAL-VERIFIED-BEFORE-CACHE-RETIREMENT.json',{'tracks':p,'all1715_files_exact':True,'sourceIP_exact':True,'new_media_identity':True})
    if kind=='finaldrift':(b/f.TRACKS[0]).write_bytes(b'drift')
    if kind=='hardlink':__import__('os').link(i/f.TRACKS[0],i/'alias')
    with self.assertRaises(ValueError):f.retire_verified_tracks(i,b,p,w/'wrong' if kind=='owner' else w)
    self.assertTrue(all((i/n).exists() for n in f.TRACKS));self.assertFalse((b/'EXT4-CACHE-RETIREMENT-BEFORE.json').exists())
 def test_actual_path_plan_budget_and_order(self):
  p=json.loads((HERE/'PLAN.json').read_bytes());s=(HERE/'future_master.py').read_text();m=p['media_assembly'];self.assertEqual(m['RE4DC_STAGE_EXT4'],1);self.assertLess(m['peak_model_bytes'],p['capacity']['owned_cap_bytes']);self.assertEqual(m['serial_arms'],['off','on']);self.assertEqual(m['peak_track_copies'],3)
  for name in f.TRACKS:self.assertNotIn("'-o',base/'"+name+"'",s)
  self.assertIn("'RE4DC_STAGE_EXT4':'1'",s);self.assertLess(s.index('post=verify_images(base'),s.index('retire_verified_tracks(images,base,pins)'));self.assertIn('Prospective bulk publication exceeds owned cap',s)
  serial=(HERE/'serial_stage.py').read_text();self.assertIn("for arm in selected",serial);self.assertIn("os.environ.get('RAIN_QA_STAGE_ARMS')!=selection",serial);self.assertIn("if set(pair)=={'off','on'}",serial);self.assertIn('signal.setitimer(signal.ITIMER_REAL,600)',serial)
 def test_missing_final_verification_never_retires(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d));f.publish_tracks(i,b,p,lambda:None)
   with self.assertRaises(FileNotFoundError):f.retire_verified_tracks(i,b,p,w)
   self.assertTrue(all((i/n).exists() for n in f.TRACKS))
 def test_partial_copy_failure_preserves_source_and_no_retirement(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   w,i,b,p=self.fixture(Path(d))
   def stop():raise RuntimeError('controlled interruption')
   with self.assertRaises(RuntimeError):f.publish_tracks(i,b,p,stop)
   self.assertTrue(all((i/n).exists() for n in f.TRACKS));self.assertFalse((b/'EXT4-CACHE-RETIREMENT-BEFORE.json').exists())
 def test_actual_serial_scope_stops_after_off_and_invalid_scope_writes_nothing(self):
  m=types.ModuleType('serial_stage');m.__file__=str(HERE/'serial_stage.py');exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec',dont_inherit=True),m.__dict__)
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);plan={'source':'synthetic','capacity':{},'base_paths':{a:str(root/'final'/a) for a in ['off','on']},'work_paths':{a:str(root/'work'/a) for a in ['off','on']},'programmes':{a:{'program.bin':{'sha256':a}} for a in ['off','on']}};calls=[]
   def completed(a):
    calls.append(a);b=Path(plan['base_paths'][a]);b.mkdir(parents=True)
    for n in f.TRACKS:(b/n).write_bytes(b'x')
    f.fresh(b/'COMPLETE.json',{'status':'STAGED_READBACK_PASS_GUEST_PENDING','source':'synthetic','programme':a,'all14_exact':True,'assets_exact':True,'tool_seal_sha256':'pin','plan_sha256':'pin','tracks':{n:f.row(b/n) for n in f.TRACKS}})
   with patch.dict(os.environ,{'RAIN_QA_STAGE_ARMS':'off'}),patch.object(m.c,'verify_kit',return_value=plan),patch.object(m.c,'verify_inputs'),patch.object(m.c,'sha',side_effect=lambda path:'pin' if Path(path).name in ['TOOLCHAIN-SEAL.json','PLAN.json'] else f.sha(path)),patch.object(m,'resources',return_value={}),patch.object(m.fm,'main',side_effect=completed),patch.object(m.c,'release_active',return_value=False):
    with self.assertRaises(ValueError):m.main('on')
    self.assertFalse((root/'final').exists())
    # resources() normally returns this observed field.
    with patch.object(m,'resources',return_value={'release_active':False}):m.main('off')
   self.assertEqual(calls,['off']);self.assertTrue((root/'final'/'ROOT-STAGE-OFF-RESULT.json').exists());self.assertFalse((root/'final'/'on').exists());self.assertFalse((root/'final'/'ROOT-STAGED-PAIR-RESULT.json').exists())
 def test_prior_safety_cores_unchanged(self):
  parent=HERE.parent/'qa-media-observer-recovery-v4'
  for name in ['common.py','process_group.py','cleanup_guest.py','rain_record.py','observe_pair.py','post_slot.py','official_fp_iso.py','official_fp_master.sh','SOURCE-IP.BIN']:
   self.assertEqual((HERE/name).read_bytes(),(parent/name).read_bytes(),name)
  def nested_run(path):return next(n for n in ast.walk(ast.parse(path.read_bytes())) if isinstance(n,ast.FunctionDef) and n.name=='run')
  self.assertEqual(ast.dump(nested_run(HERE/'future_master.py')),ast.dump(nested_run(parent/'future_master.py')))
if __name__=='__main__':unittest.main(verbosity=2)
