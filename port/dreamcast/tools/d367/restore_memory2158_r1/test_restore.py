"""Tiny host-only controls for exact retained replay and literal DFD publication."""
from pathlib import Path
import contextlib,datetime,hashlib,io,json,os,sys,tempfile,unittest
from unittest.mock import patch
import restore as r
class RestoreTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.core=r.load_core();cls.recovery=cls.core.load_recovery()
 def fixture(self,p):
  base=p/'source/base.iso';base.parent.mkdir();base.write_bytes(b'A'*65536+b'B'*65536+b'TAIL'*16384);blob=p/'delta/changes.bin';blob.parent.mkdir();blob.write_bytes(b'C'*65536);target=b'A'*65536+b'C'*65536
  m=dict(base_size=base.stat().st_size,base_sha256=r.sha(base),target_size=len(target),target_sha256=hashlib.sha256(target).hexdigest(),block_bytes=65536,blob=dict(size=65536,sha256=r.sha(blob)),rows=[dict(offset=65536,size=65536,blob_offset=0)])
  return base,blob,target,m
 def test_original_iterstream_full_base_tail_and_full_written_readback(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);base,blob,target,m=self.fixture(p);calls=[]
   with r.Input(base,base.stat().st_size)as b,r.Input(blob,65536)as d,(p/'candidate').open('w+b')as w:
    def guard():b.check();d.check();calls.append(1)
    self.assertEqual(r.stream_to_writer(self.core,self.recovery,b.anchored,d.anchored,m,w,guard),m['target_sha256']);w.seek(0);self.assertEqual(w.read(),target)
   self.assertGreaterEqual(len(calls),3)
 def test_bad_base_blob_target_and_overlap_fail_unpublished(self):
  for mode in ('base','blob','target','overlap'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory()as t:
    p=Path(t);base,blob,target,m=self.fixture(p)
    if mode=='base':base.write_bytes(b'Z'*base.stat().st_size)
    if mode=='blob':blob.write_bytes(b'Z'*65536)
    if mode=='target':m['target_sha256']='0'*64
    if mode=='overlap':m['rows'].append(m['rows'][0])
    with (p/'candidate').open('w+b')as w,self.assertRaises(ValueError):r.stream_to_writer(self.core,self.recovery,base,blob,m,w)
    self.assertFalse((p/'published').exists());self.assertTrue((p/'candidate').exists())
 def test_short_write_and_written_readback_corruption_reject(self):
  class Writer(io.BytesIO):
   bad=False
   def fileno(self):return 1
   def write(self,b):return super().write(b)-int(self.bad)
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);base,blob,target,m=self.fixture(p);w=Writer();w.bad=True
   with self.assertRaises(ValueError):r.stream_to_writer(self.core,self.recovery,base,blob,m,w)
   class BadRead(Writer):
    def read(self,n=-1):return super().read(n).replace(b'A',b'Z')
   with patch.object(r.os,'fsync'),self.assertRaisesRegex(ValueError,'written target'):r.stream_to_writer(self.core,self.recovery,base,blob,m,BadRead())
 def test_successful_publication_is_same_inode_one_allocation(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);tmp=p/'owned.tmp';target=p/'track03.iso'
   with r.Directory(p)as d,tmp.open('w+b')as w:
    w.write(b'EXACT');w.flush();before=os.fstat(w.fileno());out=r.publish(d,tmp.name,target.name,w)
    self.assertEqual(out,r.object_id(before));self.assertEqual(os.stat(target).st_ino,before.st_ino);self.assertEqual(os.stat(target).st_nlink,1);self.assertFalse(tmp.exists());self.assertEqual(target.read_bytes(),b'EXACT')
 def test_existing_target_and_dangling_target_preserved(self):
  for symlink in (False,True):
   with tempfile.TemporaryDirectory()as t:
    p=Path(t);tmp=p/'owned.tmp';target=p/'track03.iso'
    target.symlink_to(p/'absent')if symlink else target.write_bytes(b'OLD')
    with r.Directory(p)as d,tmp.open('w+b')as w,self.assertRaises(FileExistsError):r.publish(d,tmp.name,target.name,w)
    self.assertTrue(os.path.lexists(target));self.assertTrue(tmp.exists())
 def test_parent_rename_before_link_fails_and_keeps_candidate(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);p=root/'literal';p.mkdir();tmp=p/'owned.tmp';moved=root/'moved'
   with r.Directory(p)as d,tmp.open('w+b')as w:
    w.write(b'EXACT');w.flush()
    def event(name):
     if name=='BEFORE_EXCLUSIVE_LINK':p.rename(moved);p.mkdir()
    with self.assertRaises(ValueError):r.publish(d,tmp.name,'track03.iso',w,event)
   self.assertFalse((p/'track03.iso').exists());self.assertFalse((moved/'track03.iso').exists());self.assertTrue((moved/tmp.name).exists())
 def test_parent_rename_after_link_fails_no_cleanup_no_acceptance(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);p=root/'literal';p.mkdir();tmp=p/'owned.tmp';moved=root/'moved'
   with r.Directory(p)as d,tmp.open('w+b')as w:
    w.write(b'EXACT');w.flush()
    def event(name):
     if name=='LINK_VERIFIED_LITERAL_SAME_INODE':p.rename(moved);p.mkdir()
    with self.assertRaises(ValueError):r.publish(d,tmp.name,'track03.iso',w,event)
   self.assertFalse((p/'track03.iso').exists());self.assertTrue((moved/'track03.iso').exists());self.assertTrue((moved/tmp.name).exists());self.assertEqual((moved/tmp.name).stat().st_ino,(moved/'track03.iso').stat().st_ino)
 def test_ancestor_rename_rejects_even_with_held_child_DFD(self):
  with tempfile.TemporaryDirectory()as t:
   root=Path(t);ancestor=root/'a';p=ancestor/'child';p.mkdir(parents=True)
   with r.Directory(p)as d:
    ancestor.rename(root/'renamed');p.mkdir(parents=True)
    with self.assertRaises(ValueError):d.check()
 def test_input_named_inode_replacement_and_source_parent_rename(self):
  for mode in ('replace','rename'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory()as t:
    p=Path(t);parent=p/'source';parent.mkdir();base=parent/'base';base.write_bytes(b'ORIGINAL')
    with r.Input(base,8)as b:
     anchored=b.anchored
     if mode=='replace':base.rename(parent/'old');base.write_bytes(b'ORIGINAL')
     else:parent.rename(p/'moved');parent.mkdir();base.write_bytes(b'OTHER___');self.assertEqual(anchored.read_bytes(),b'ORIGINAL')
     with self.assertRaises(ValueError):b.check()
 def test_symlink_directory_and_input_fail_closed(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t);real=p/'real';real.mkdir();(real/'file').write_bytes(b'X');alias=p/'alias';alias.symlink_to(real,target_is_directory=True)
   with self.assertRaises(ValueError):r.Directory(alias)
   link=p/'file';link.symlink_to(real/'file')
   with self.assertRaises(ValueError):r.Input(link,1)
 def test_existing_lease_nonblocking_and_named_identity(self):
  with tempfile.TemporaryDirectory()as t:
   p=Path(t)/'lease';p.write_bytes(b'')
   with r.Input(p,0)as first,r.Input(p,0)as second:
    r.fcntl.flock(first.fd,r.fcntl.LOCK_EX|r.fcntl.LOCK_NB)
    with self.assertRaises(BlockingIOError):r.fcntl.flock(second.fd,r.fcntl.LOCK_EX|r.fcntl.LOCK_NB)
    p.rename(p.with_name('old'));p.write_bytes(b'')
    with self.assertRaises(ValueError):first.check()
 def admission(self):return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),admitted=True,package_one_guest_admitted=True,errors=[],root_cap=r.ROOT_CAP,package_cap=r.PACKAGE_CAP,floor=r.FLOOR,guest_peak=r.GUEST,projected_peak=0,package_current_bytes=0,c_free=r.FLOOR+r.SIZE+r.META+r.GUEST,roots=[dict(path=str(r.CROOT))])
 def test_fresh_one_ISO_metadata_and_future_guest_reservation(self):
  good=self.admission();r.admission(good)
  for key,value in (('package_one_guest_admitted',False),('guest_peak',0),('floor',0),('root_cap',r.ROOT_CAP+1),('projected_peak',r.ROOT_CAP-r.SIZE-r.META+1),('package_current_bytes',r.PACKAGE_CAP-r.SIZE-r.META-r.GUEST+1),('c_free',good['c_free']-1)):
   with self.subTest(key=key),self.assertRaises(ValueError):r.admission(dict(good,**{key:value}))
  with self.assertRaises(ValueError):r.admission(good,datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=61))
 def test_default_never_loads_metadata_or_opens_images(self):
  with patch.object(sys,'argv',['restore.py']),patch.object(r,'metadata',side_effect=AssertionError('no metadata')),patch.object(r,'Input',side_effect=AssertionError('no image')),patch('sys.stdout',new_callable=io.StringIO)as out:r.main()
  self.assertEqual(json.loads(out.getvalue())['status'],'SOURCE_ONLY_NOT_EXECUTED')
 def test_exact_small_metadata_and_immutable_core_source(self):
  m=r.metadata();self.assertEqual(m['target_sha256'],r.TARGET_SHA);self.assertEqual(m['base_sha256'],r.BASE_SHA);self.assertEqual(self.recovery.BLOCK,65536)
if __name__=='__main__':unittest.main()
