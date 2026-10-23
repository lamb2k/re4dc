"""Miniature byte-copy/patch controls only: never opens a real ISO."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import recover as r

HERE=Path(__file__).resolve().parent

def digest(data):return hashlib.sha256(data).hexdigest()

class RecoveryControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='mini-');self.d=Path(self.tmp.name)
  self.payload=self.d/'old.bin';old=b'old-payload'*7;self.payload.write_bytes(old)
  room=b'room-identical'*3;size=8192;source=bytearray(b'X'*4096+b'N'*2048+b'\0'*2048);source[6144:6144+len(room)]=room
  before=b'B'*16;after=b'A'*16;source[64:80]=before;expected=bytearray(source);expected[4096:6144]=old+bytes(2048-len(old));expected[64:80]=after
  self.data=bytes(source);self.expected=bytes(expected)
  self.plan={'input':{'size':size,'sha256':digest(self.data)},'target':{'size':size,'sha256':digest(self.expected)},'original_size':4096,
   'appends':[dict(package_path='dc/a.ovl',offset=4096,size=len(old),new_size=120,padded_size=2048,old_sha256=digest(old)),dict(package_path='dc/native/r119/room.r4rc',offset=6144,size=len(room),new_size=len(room),padded_size=2048,old_sha256=digest(room))],
   'payloads':[dict(package_path='dc/a.ovl',path=str(self.payload),offset=4096,size=len(old),padded_size=2048,sha256=digest(old))],
   'point_patches':[dict(offset=64,before_hex=before.hex(),after_hex=after.hex())],'descriptor_checks':[dict(offset=8,hex=self.data[8:16].hex())]}
 def tearDown(self):self.tmp.cleanup()
 def replay(self,plan=None,data=None):
  p=self.d/'candidate';events=[]
  with p.open('x+b') as f:
   actual,self.verified=r.copy_patch(io.BytesIO(self.data if data is None else data),f,self.plan if plan is None else plan,event=events.append)
  return p,actual,events
 def test_exact_bytes_and_padding_full_readback(self):
  r.validate_shape(self.plan,production=False);p,h,events=self.replay();self.assertEqual(p.read_bytes(),self.expected);self.assertEqual(h,digest(self.expected));self.assertEqual(events,['SOURCE_FULL_HASH_VERIFIED','PATCHES_APPLIED','TARGET_FULL_HASH_VERIFIED'])
 def test_wrong_source_full_hash_refuses_before_patch(self):
  with self.assertRaisesRegex(ValueError,'source full SHA256'):self.replay(data=b'Q'+self.data[1:])
  self.assertFalse((self.d/'final').exists());self.assertEqual((self.d/'candidate').read_bytes()[64:80],b'B'*16)
 def test_truncated_or_long_source_refuses(self):
  for data in (self.data[:-1],self.data+b'X'):
   if (self.d/'candidate').exists():(self.d/'candidate').unlink()
   with self.assertRaises(ValueError):self.replay(data=data)
 def test_directory_preimage_refuses(self):
  plan=copy.deepcopy(self.plan);plan['point_patches'][0]['before_hex']=(b'Z'*16).hex()
  with self.assertRaisesRegex(ValueError,'preimage'):self.replay(plan)
 def test_descriptor_and_room_refuse(self):
  plan=copy.deepcopy(self.plan);plan['descriptor_checks'][0]['hex']='00'*8
  with self.assertRaisesRegex(ValueError,'descriptor'):self.replay(plan)
  (self.d/'candidate').unlink();plan=copy.deepcopy(self.plan);plan['appends'][1]['old_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'private room'):self.replay(plan)
 def test_old_payload_hash_refuses(self):
  self.payload.write_bytes(b'x'*self.payload.stat().st_size)
  with self.assertRaisesRegex(ValueError,'payload SHA256'):self.replay()
 def test_target_hash_mismatch_stays_unpublished(self):
  plan=copy.deepcopy(self.plan);plan['target']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'target SHA256'):self.replay(plan)
  self.assertTrue((self.d/'candidate').exists());self.assertFalse((self.d/'final').exists())
 def test_shape_overlap_gap_duplicate_and_padding_refuse(self):
  for kind in ('point_overlap','append_gap','payload_duplicate','padding'):
   plan=copy.deepcopy(self.plan)
   if kind=='point_overlap':plan['point_patches'].append(plan['point_patches'][0])
   if kind=='append_gap':plan['appends'][1]['offset']+=1
   if kind=='payload_duplicate':plan['payloads'].append(plan['payloads'][0])
   if kind=='padding':plan['appends'][0]['new_size']=3000
   with self.assertRaises(ValueError):r.validate_shape(plan,production=False)
 def test_atomic_exclusive_publish_one_inode_no_clobber(self):
  p,_,_=self.replay();target=self.d/'final';fd=os.open(self.d,os.O_RDONLY|os.O_DIRECTORY)
  try:
   with p.open('r+b') as f:
    inode=p.stat().st_ino;r.publish(p,target,f,fd,self.verified,len(self.expected))
   self.assertEqual(target.stat().st_ino,inode);self.assertEqual(target.read_bytes(),self.expected);self.assertFalse(p.exists())
   p.write_bytes(b'keep-candidate')
   with p.open('r+b') as f:
    with self.assertRaises(ValueError):r.publish(p,target,f,fd,self.verified,len(self.expected))
   self.assertEqual(target.read_bytes(),self.expected);self.assertEqual(p.read_bytes(),b'keep-candidate')
  finally:os.close(fd)
 def test_parent_renamed_replaced_during_link_refuses_preserves_all(self):
  # DrvFS may deny renaming a directory with an open child. Linux scratch
  # reproduces the reviewed namespace race rather than relying on that denial.
  previous=self.d
  with tempfile.TemporaryDirectory(prefix='ce034-parent-swap-') as tempdir:
   self.d=Path(tempdir)
   try:self.parent_swap_case()
   finally:self.d=previous
 def parent_swap_case(self):
  # Exact reviewer reproducer: replace literal parent inside os.link, while
  # the held directory still accepts the link. No old/temp/foreign name is removed.
  p,_,_=self.replay();live=self.d/'live';live.mkdir();temp=live/'candidate';p.rename(temp);target=live/'final';moved=self.d/'renamed'
  fd=os.open(live,os.O_RDONLY|os.O_DIRECTORY);real_link=os.link
  def swap(*args,**kw):
   live.rename(moved);live.mkdir();(live/'foreign').write_bytes(b'foreign-preserved')
   return real_link(*args,**kw)
  try:
   with temp.open('r+b') as f,patch.object(r.os,'link',side_effect=swap):
    with self.assertRaisesRegex(ValueError,'Literal parent'):r.publish(temp,target,f,fd,self.verified,len(self.expected))
   self.assertFalse(target.exists());self.assertEqual((live/'foreign').read_bytes(),b'foreign-preserved')
   self.assertEqual((moved/'candidate').read_bytes(),self.expected);self.assertEqual((moved/'final').read_bytes(),self.expected)
  finally:os.close(fd)
 def test_parent_replaced_before_link_never_links_or_unlinks(self):
  p,_,_=self.replay();live=self.d/'live';live.mkdir();temp=live/'candidate';p.rename(temp);target=live/'final';fd=os.open(live,os.O_RDONLY|os.O_DIRECTORY);moved=self.d/'renamed';live.rename(moved);live.mkdir();(live/'candidate').write_bytes(b'foreign')
  try:
   with (moved/'candidate').open('r+b') as f,patch.object(r.os,'link') as link:
    with self.assertRaisesRegex(ValueError,'Literal parent'):r.publish(temp,target,f,fd,self.verified,len(self.expected))
    link.assert_not_called()
   self.assertEqual((live/'candidate').read_bytes(),b'foreign');self.assertTrue((moved/'candidate').exists());self.assertFalse((moved/'final').exists())
  finally:os.close(fd)
 def test_foreign_temporary_replacement_never_unlinked(self):
  p,_,_=self.replay();target=self.d/'final';fd=os.open(self.d,os.O_RDONLY|os.O_DIRECTORY);saved=self.d/'verified-original';real_link=os.link
  def swap(*args,**kw):
   p.rename(saved);p.write_bytes(b'foreign-temp');return real_link(*args,**kw)
  try:
   with p.open('r+b') as f,patch.object(r.os,'link',side_effect=swap):
    with self.assertRaisesRegex(ValueError,'Literal target'):r.publish(p,target,f,fd,self.verified,len(self.expected))
   self.assertEqual(p.read_bytes(),b'foreign-temp');self.assertEqual(target.read_bytes(),b'foreign-temp');self.assertEqual(saved.read_bytes(),self.expected)
  finally:os.close(fd)
 def test_literal_target_replacement_and_wrong_size_refuse(self):
  p,_,_=self.replay();target=self.d/'final';fd=os.open(self.d,os.O_RDONLY|os.O_DIRECTORY)
  try:
   with p.open('r+b') as f:
    with self.assertRaisesRegex(ValueError,'size'):r.publish(p,target,f,fd,self.verified,len(self.expected)+1)
   self.assertTrue(p.exists());self.assertFalse(target.exists())
   target.write_bytes(b'foreign')
   with self.assertRaisesRegex(ValueError,'Literal target'):r.literal_target(target,fd,self.verified)
   self.assertEqual(target.read_bytes(),b'foreign')
  finally:os.close(fd)
 def test_standing_guest_package_reserve_actual_margin(self):
  self.assertEqual(2662713861+r.SIZE+r.META+r.GUEST,3754801669)
  self.assertEqual(r.PACKAGE_CAP-3754801669,3294715)
 def test_pinned_reader_rejects_symlink_or_mid_read_change(self):
  row=self.plan['payloads'][0];p=self.d/'link';p.symlink_to(self.payload)
  with self.assertRaises(ValueError):
   with r.pinned_reader({**row,'path':str(p)}):pass
  with self.assertRaises(ValueError):
   with r.pinned_reader(row):self.payload.write_bytes(b'y'*row['size'])
 def test_stale_or_insufficient_admission_refuses(self):
  now=r.datetime.datetime.now(r.datetime.timezone.utc)
  valid=dict(utc=now.isoformat(),admitted=True,errors=[],root_cap=r.ROOT_CAP,package_cap=r.PACKAGE_CAP,floor=r.FLOOR,guest_peak=r.GUEST,projected_peak=r.ROOT_CAP-r.SIZE-r.META,package_current_bytes=r.PACKAGE_CAP-r.SIZE-r.META-r.GUEST,c_free=r.FLOOR+r.GUEST+r.SIZE+r.META,roots=[{'path':str(r.CROOT)}]);r.admission(valid)
  for field,value in [('utc',(now-r.datetime.timedelta(seconds=61)).isoformat()),('projected_peak',valid['projected_peak']+1),('package_current_bytes',valid['package_current_bytes']+1),('c_free',valid['c_free']-1),('admitted',False)]:
   with self.assertRaises(ValueError):r.admission({**valid,field:value})
 def test_actual_plan_metadata_only_shape_and_exact_roster(self):
  plan=r.read_json(HERE/'PLAN.json',r.PLAN_SHA);r.validate_shape(plan)
  self.assertEqual(len(plan['payloads']),15);self.assertEqual(len(plan['point_patches']),32)
  changed=[x for x in plan['point_patches'] if x['before_hex']!=x['after_hex']]
  self.assertEqual(len(changed),2);self.assertTrue(all(x['package_path']=='1ST_READ.BIN' for x in changed))
  # Source-only check: no media path is opened by this control.
  self.assertEqual(sum(x['padded_size'] for x in plan['appends']),4257792)

if __name__=='__main__':
 import io
 log=io.StringIO();start=time.monotonic();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(RecoveryControls));elapsed=time.monotonic()-start
 print(log.getvalue());(HERE/'HOST-TEST.log').write_text(log.getvalue());record=dict(status='PASS' if result.wasSuccessful() else 'FAIL',methods=result.testsRun,errors=len(result.errors),failures=len(result.failures),seconds=elapsed,scope='Miniature copy/patch/publication plus actual JSON-plan shape only; no real ISO/payload read, no large hash, recovery, allocation or census.',source_files={n:digest((HERE/n).read_bytes()) for n in ('recover.py','test_recover.py','PLAN.json')});(HERE/'HOST-TEST-RESULTS.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
