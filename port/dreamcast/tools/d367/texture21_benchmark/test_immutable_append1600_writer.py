"""Small owned fixtures only. No production pack writes or controller invocation."""
import hashlib,importlib.util,json,os,struct,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
import immutable_append1600_writer as w
from file_charge import WinPin

class WriterTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='re4-append1600-owned-fixture-');self.root=Path(self.tmp.name);self.clock=[0.];self.free=[10**9]
 def tearDown(self):self.tmp.cleanup()
 def guard(self,**kw):return w.Budget([self.root],kw.pop('cap',65536),100,10,clock=lambda:self.clock[0],free=lambda:self.free[0],reserve=0,**kw)
 def package(self):
  b=bytearray(160);b[:8]=b'RE4DCTX\0';b[48:144]=bytes(range(96));b[144:]=b'SYNTHETIC_BYTES!X';struct.pack_into('<I',b,36,zlib.crc32(b[48:]));return bytes(b)
 def fixture(self):
  b=self.package();source=self.root/'source.ctx';source.write_bytes(b);index=struct.pack('<4I',1,2,4096,len(b))+bytes(2032);head=struct.pack('<8s5I',b'RE4PAK1\0',1,1,2048,4096,zlib.crc32(index))+bytes(2020)
  row=dict(key='00000001-00000002',bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),path=source,source_root=self.root,source_offset=0,offset=4096,descriptor_hex=b[48:144].hex(),body_crc32=zlib.crc32(b[48:]));blob=head+index+b+bytes((-len(b))%2048)
  known_path=w.local('/root/probe/codex-texture-atlas21/port/dreamcast/tools/d367/texpack.py');self.assertEqual(w.sha(known_path),w.READER_SHA);spec=importlib.util.spec_from_file_location('fixture_known_reader',known_path);known=importlib.util.module_from_spec(spec);spec.loader.exec_module(known)
  return head,index,[row],blob,known
 def test_small_primary_mirror_reader_and_member_sha(self):
  h,i,rows,b,k=self.fixture();g=self.guard();digest=hashlib.sha256(b).hexdigest();inspect=lambda p:w.inspect_pack(p,h,i,rows,len(b),digest,k,g)
  primary=self.root/'primary.pak';mirror=self.root/'mirror.pak';w.write_one(primary,w.source_stream(h,i,rows,g),len(b),digest,inspect,g);w.write_one(mirror,w.copy_blocks(primary,g),len(b),digest,inspect,g);self.assertEqual(primary.read_bytes(),b);self.assertEqual(primary.read_bytes(),mirror.read_bytes());self.assertFalse(primary.with_suffix('.pak.part').exists())
 def test_corrupt_source_preserves_partial_never_publishes(self):
  h,i,r,b,k=self.fixture();r[0]['path'].write_bytes(r[0]['path'].read_bytes()[:-1]+b'!');g=self.guard();out=self.root/'bad.pak'
  with self.assertRaises(ValueError):w.write_one(out,w.source_stream(h,i,r,g),len(b),hashlib.sha256(b).hexdigest(),lambda _:None,g)
  self.assertTrue((self.root/'bad.pak.part').exists());self.assertFalse(out.exists())
 def test_descriptor_crc_independently_rejected(self):
  h,i,r,b,k=self.fixture();r[0]['body_crc32']^=1
  with self.assertRaises(ValueError):list(w.source_stream(h,i,r,self.guard()))
 def test_wrong_expected_sha_preserves_partial(self):
  out=self.root/'wrong';g=self.guard()
  with self.assertRaises(ValueError):w.write_one(out,[b'abc'],3,'0'*64,lambda _:None,g)
  self.assertEqual((self.root/'wrong.part').read_bytes(),b'abc');self.assertFalse(out.exists())
 def test_existing_final_and_partial_no_clobber(self):
  for name in ('final','partial'):
   out=self.root/name;old=out if name=='final'else out.with_name(name+'.part');old.write_bytes(b'KEEP');g=self.guard()
   with self.assertRaises(FileExistsError):w.write_one(out,[b'new'],3,hashlib.sha256(b'new').hexdigest(),lambda _:None,g)
   self.assertEqual(old.read_bytes(),b'KEEP')
 def test_publication_race_refuses_new_final(self):
  out=self.root/'race';g=self.guard()
  def readback(p):out.write_bytes(b'KEEP');return {}
  with self.assertRaises(OSError):w.write_one(out,[b'abc'],3,hashlib.sha256(b'abc').hexdigest(),readback,g)
  self.assertEqual(out.read_bytes(),b'KEEP');self.assertEqual((self.root/'race.part').read_bytes(),b'abc')
 def test_readback_identity_size_mutation_rejected(self):
  out=self.root/'mutated';g=self.guard()
  def readback(p):p.write_bytes(b'different');return {}
  with self.assertRaises(ValueError):w.write_one(out,[b'abc'],3,hashlib.sha256(b'abc').hexdigest(),readback,g)
  self.assertFalse(out.exists())
 def test_known_reader_corrupt_index_and_member_rejected(self):
  h,i,r,b,k=self.fixture();p=self.root/'inspect';p.write_bytes(b);g=self.guard();wrong=[{**r[0],'sha256':'0'*64}]
  with self.assertRaises(ValueError):w.inspect_pack(p,h,i,wrong,len(b),hashlib.sha256(b).hexdigest(),k,g)
  bad=bytearray(b);bad[2048]^=1;p.write_bytes(bad)
  with self.assertRaises(SystemExit):w.inspect_pack(p,h,i,r,len(b),hashlib.sha256(bad).hexdigest(),k,g)
 def test_quota_floor_deadline_and_probe_throttling(self):
  g=self.guard(cap=4096);p=g.claim(self.root/'owned');g.check(p,4096);g.check(p,1);self.assertEqual(g.probes,1)
  with self.assertRaises(RuntimeError):g.check(p,4097)
  self.free[0]=99
  with self.assertRaises(RuntimeError):g.check(force=True)
  self.free[0]=10**9;self.clock[0]=11
  with self.assertRaises(RuntimeError):g.check()
 def test_probe_os_stall_rejected_after_return(self):
  def slow():self.clock[0]=11;return 10**9
  g=w.Budget([self.root],65536,100,10,clock=lambda:self.clock[0],free=slow,reserve=0)
  with self.assertRaisesRegex(RuntimeError,'during filesystem probe'):g.check()
 def test_native_larger_charge_never_compression_credit(self):
  p=self.root/'unknown';p.write_bytes(b'a');g=self.guard(charge=lambda p,n:max(w.roundup(n,4096),8192));self.assertEqual(g.check(),8192)
  self.assertGreaterEqual(w.file_charge(p,1),4096)
 def test_unowned_outside_symlink_and_overlap_refused(self):
  g=self.guard()
  with self.assertRaises(ValueError):g.check(self.root/'unknown',1)
  with self.assertRaises(ValueError):g.claim(self.root.parent/'outside')
  with self.assertRaises(ValueError):w.Budget([self.root,self.root/'child'],1,0,1)
  with self.assertRaises(ValueError):g.check(upcoming=-1)
  if os.name!='nt':
   p=self.root/'link';p.symlink_to('/tmp')
   with self.assertRaises(ValueError):g.claim(p/'file')
 def test_exact_child_allocation_refusals(self):
  plan={'controller_sha256':'a'*64,'metadata_root':'synthetic-meta','payload_roots':['one','two']};pp=self.root/'plan.json';pp.write_text(json.dumps(plan));ps=w.sha(pp);ap=self.root/'allocation.json'
  a=dict(allocated=True,allocation_id='SYNTHETIC_NOT_EXECUTABLE',writer_plan_sha256=ps,writer_source_sha256=w.sha(w.__file__),controller_sha256=plan['controller_sha256'],aggregate_cap_bytes=w.CAP,runtime_floor_bytes=w.FLOOR,peer_reserved_bytes=w.PEER,inner_seconds=51,approved_output_root=plan['metadata_root'],approved_payload_roots=plan['payload_roots'])
  ap.write_text(json.dumps(a));self.assertEqual(w.allocation(pp,ps,ap,w.sha(ap),plan)['allocation_id'],a['allocation_id'])
  for field,value in [('allocated',False),('aggregate_cap_bytes',w.CAP+1),('runtime_floor_bytes',0),('peer_reserved_bytes',0),('controller_sha256','b'*64),('writer_source_sha256','0'*64),('approved_payload_roots',['elsewhere']),('compression_credits',[{}])]:
   ap.write_text(json.dumps({**a,field:value}))
   with self.subTest(field=field),self.assertRaises(ValueError):w.allocation(pp,ps,ap,w.sha(ap),plan)
  ap.write_text(json.dumps(a))
  with self.assertRaises(ValueError):w.allocation(pp,ps,ap,'0'*64,plan)
 def test_missing_dependency_never_reaches_resolution(self):
  p=self.root/'missing-dependency.json';p.write_text(json.dumps({'source_sha256':{}}))
  with patch('sys.argv',['adapter','--plan',str(p),'--plan-sha256',w.sha(p)]),patch.object(w,'resolve')as resolver:
   with self.assertRaisesRegex(ValueError,'exact source dependency'):w.main()
   resolver.assert_not_called()
 def test_external_owned_partial_growth_refused(self):
  g=self.guard();p=g.claim(self.root/'foreign-growth');p.write_bytes(b'unowned-growth')
  with self.assertRaisesRegex(RuntimeError,'changed externally'):g.check(force=True)
 @unittest.skipUnless(os.name=='nt','Windows retained read-handle control')
 def test_native_retained_identity_sha_write_denial(self):
  p=self.root/'native-pin';p.write_bytes(b'OWNED_SYNTHETIC')
  with WinPin(p,w.sha(p))as held:
   self.assertEqual(held.initial['link_count'],1);self.assertGreaterEqual(held.allocated(),0)
   with self.assertRaises(OSError):p.write_bytes(b'overwrite')
  with self.assertRaises(ValueError):WinPin(p,'0'*64)

if __name__=='__main__':unittest.main(verbosity=2)
