import hashlib,json,os,tempfile,unittest
from pathlib import Path
from file_charge import ChargeSession,WinPin,conservative_charge,publish_no_replace,roundup,safe_path
from mipmap_pair_plan import sha
def identity(p):
 s=p.stat();return {'volume_serial':s.st_dev,'file_index':s.st_ino,'link_count':s.st_nlink,'logical_bytes':s.st_size,'creation_time':s.st_ctime_ns}
class FakePin:
 allocated_bytes=1000
 def __init__(self,path,expected):
  self.path=path;self.initial=identity(path);self.closed=False
  if sha(path)!=expected:raise ValueError('fullSHA mismatch')
 def allocated(self):
  if identity(self.path)!=self.initial or self.initial['link_count']!=1:raise ValueError('fileID/link race')
  return self.allocated_bytes
 def close(self):self.closed=True
class ChargeTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.image=self.root/'closed.iso';self.image.write_bytes(b'A'*10000);self.plan_sha='a'*64;h=sha(self.image);self.plan={'track_bytes':10000,'arms':{'M1':{'predicted':{'sha256':h}}}}
  self.rb=self.root/'readback.json';self.rb.write_text(json.dumps({'result':'PASS','arm':'M1','all1743_LBAs_sizes_hashes':True,'all15_programme_exact':True,'files':{str(i):None for i in range(1743)},'plan_sha256':self.plan_sha,'track':{'path':str(self.image),'sha256':h,'bytes':10000}}))
  self.r=self.root/'credit.json';self.body={'result':'PASS','same_uncompressed_image_identity':True,'image':str(self.image),'sha256':h,'logical_bytes':10000,'native_file_identity':identity(self.image),'readback_path':str(self.rb),'all1743_readback_receipt_sha256':sha(self.rb)};self.refresh()
 def refresh(self):self.r.write_text(json.dumps(self.body));self.credits=[{'receipt_path':str(self.r),'sha256':sha(self.r)}]
 def session(self):return ChargeSession(self.root,self.plan,self.plan_sha,self.credits,self.root/'next.iso',pin=FakePin)
 def tearDown(self):self.t.cleanup()
 def test_native_credit_and_fresh_query(self):
  ordinary=conservative_charge(self.root)
  with self.session()as s:
   self.assertEqual(s.charge(),ordinary-roundup(10000,s.cluster)+roundup(1000,s.cluster));FakePin.allocated_bytes=5000
   self.assertEqual(s.charge(),ordinary-roundup(10000,s.cluster)+roundup(5000,s.cluster))
  FakePin.allocated_bytes=1000
 def test_failed_unknown_files_remain_rounded_logical(self):
  (self.root/'failed.partial').write_bytes(b'X'*9001)
  with self.session()as s:self.assertGreaterEqual(s.charge(),roundup(9001,s.cluster)+roundup(1000,s.cluster))
 def test_receipt_hash_tamper(self):
  self.r.write_text('tampered');self.assertRaises(ValueError,self.session)
 def test_readback_hash_tamper(self):
  self.rb.write_text('tampered');self.assertRaises(ValueError,self.session)
 def test_plan_mismatch(self):
  self.plan_sha='b'*64;self.assertRaises(ValueError,self.session)
 def test_fileID_replacement_rejected(self):
  # Keep the old inode allocated: unlink/recreate can recycle inode+coarse
  # ctime in the POSIX mock, unlike the native NTFS file-reference contract.
  self.image.rename(self.root/'old-inode.iso');self.image.write_bytes(b'A'*10000);self.assertRaises(ValueError,self.session)
 def test_file_content_replacement_rejected(self):
  self.image.write_bytes(b'B'*10000);self.assertRaises(ValueError,self.session)
 def test_hardlink_and_symlink_rejected(self):
  link=self.root/'extra'
  os.link(self.image,link);self.assertRaises(ValueError,self.session);link.unlink()
  try:link.symlink_to(self.image)
  except OSError:self.skipTest('OS symlink privilege unavailable')
  self.assertRaises(ValueError,conservative_charge,self.root)
 def test_outside_path_and_active_output_rejected(self):
  self.assertRaises(ValueError,safe_path,self.root.parent/'outside',self.root)
  self.assertRaises(ValueError,ChargeSession,self.root,self.plan,self.plan_sha,self.credits,self.image,FakePin)
 def test_no_overwrite_publication_both_platforms(self):
  partial=self.root/'new.partial';final=self.root/'final';partial.write_bytes(b'new');final.write_bytes(b'old')
  self.assertRaises(OSError,publish_no_replace,partial,final);self.assertEqual(final.read_bytes(),b'old');self.assertEqual(partial.read_bytes(),b'new');final.unlink();publish_no_replace(partial,final);self.assertEqual(final.read_bytes(),b'new');self.assertFalse(partial.exists())
 @unittest.skipUnless(os.name=='nt','actual Windows API')
 def test_actual_native_pin_blocks_write_delete_and_closes(self):
  with WinPin(self.image,sha(self.image))as held:
   self.assertEqual(held.initial['logical_bytes'],10000);self.assertEqual(held.initial['link_count'],1);self.assertGreaterEqual(held.allocated(),0)
   self.assertRaises(OSError,self.image.write_bytes,b'overwrite');self.assertRaises(OSError,self.image.unlink)
  self.image.write_bytes(b'afterclose');self.assertEqual(self.image.read_bytes(),b'afterclose')
if __name__=='__main__':unittest.main()
