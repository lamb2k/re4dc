import hashlib,json,struct,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
import matched994_stream as s
from matched_pair_readback import both,name_of
from programme994_inspect import fnv
class Stream(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name);self.base=self.root/'base';self.base.write_bytes(bytes(8192));self.src=self.root/'payload';self.src.write_bytes(b'new exact payload');self.row={'path':'/dc/test','start':2048,'end':4096,'bytes':17,'source_path':str(self.src),'sha256':s.sha(self.src)}
  self.p={'base_path':str(self.base),'common_ranges':[],'arms':{'M1':{'ranges':[self.row],'patches':[{'start':16,'before':'00000000','after':'01020304'}]}}}
  self.track=patch.object(s,'TRACK',8192);self.old=patch.object(s,'OLD_C',s.sha(self.base));self.track.start();self.old.start()
 def tearDown(self):self.track.stop();self.old.stop();self.t.cleanup()
 def test_exact_payload_zero_padding_metadata_and_hash(self):
  b=b''.join(s.blocks(self.p,'M1'));expected=bytearray(8192);expected[16:20]=bytes.fromhex('01020304');expected[2048:2065]=b'new exact payload';self.assertEqual(b,expected);self.assertEqual(s.predicted(self.p,'M1')['sha256'],hashlib.sha256(expected).hexdigest())
 def test_source_changed_rejected(self):
  self.src.write_bytes(b'changed');self.assertRaises(ValueError,s.check_sources,[self.row])
 def test_wrong_metadata_rejected(self):
  self.p['arms']['M1']['patches'][0]['before']='01010101';self.assertRaises(ValueError,lambda:list(s.blocks(self.p,'M1')))
 def test_overlap_rejected(self):
  self.p['common_ranges']=[self.row];self.assertRaises(ValueError,lambda:list(s.blocks(self.p,'M1')))
 def test_wrong_base_even_if_valid_ranges_rejected(self):
  self.base.write_bytes(b'X'+bytes(8191));self.assertRaises(ValueError,lambda:list(s.blocks(self.p,'M1')))
 def test_guard_throttles_expensive_probes_and_prospective_limit(self):
  a=types.SimpleNamespace(allocation_cap=10000,peer_reserved=0)
  with patch.object(s,'guard',return_value=(s.FLOOR+100000000,0))as g,patch.object(s.time,'monotonic',side_effect=[0,0.01,0.02,0.3]):
   w=s.WriterGuard(a,{},100);w.advance(10);w.advance(20);w.advance(30);self.assertEqual(g.call_count,2);self.assertRaises(ValueError,w.advance,41)
 def test_missing_resource_admission_rejects_before_image(self):
  p=self.root/'plan.json';p.write_text(json.dumps(self.p));a=self.root/'admission.json';a.write_text(json.dumps({'plan_sha256':s.sha(p),'arm':'M1','stage_authorized':False,'candidate_contract_valid':False}));args=types.SimpleNamespace(plan=p,plan_sha256=s.sha(p),allocation_receipt=a,arm='M1');self.assertRaises(AssertionError,s.write,args);self.assertFalse((self.root/'track03.iso').exists())
 def writer_args(self):
  self.p['arms']['M1']['predicted']=s.predicted(self.p,'M1');p=self.root/'plan.json';p.write_text(json.dumps(self.p));a=self.root/'admission.json';a.write_text(json.dumps({'plan_sha256':s.sha(p),'arm':'M1','stage_authorized':True,'candidate_contract_valid':True}));out=self.root/'new';out.mkdir()
  for name in ['track01.bin','track02.raw','disc.gdi']:(self.root/name).write_bytes(('synthetic '+name).encode())
  return types.SimpleNamespace(plan=p,plan_sha256=s.sha(p),allocation_receipt=a,arm='M1',output=out/'track03.iso',allocation_root=self.root,allocation_cap=100000,peer_reserved=0,smalltracks=self.root)
 def test_bounded_synthetic_writer_copies_exact_smalltracks(self):
  a=self.writer_args()
  with patch.object(s,'guard',return_value=(s.FLOOR+100000000,0)):s.write(a)
  self.assertEqual(s.sha(a.output),self.p['arms']['M1']['predicted']['sha256']);self.assertFalse(a.output.with_name('track03.iso.partial').exists());self.assertEqual((a.output.parent/'disc.gdi').read_bytes(),(self.root/'disc.gdi').read_bytes())
 def test_failed_writer_preserves_partial_and_no_final(self):
  a=self.writer_args();self.base.write_bytes(b'X'+bytes(8191))
  with patch.object(s,'guard',return_value=(s.FLOOR+100000000,0)):self.assertRaises(ValueError,s.write,a)
  self.assertFalse(a.output.exists());self.assertTrue(a.output.with_name('track03.iso.partial').exists())
class Format(unittest.TestCase):
 def test_LEBE_requires_exact_agreement(self):
  self.assertEqual(both(struct.pack('<I',19)+struct.pack('>I',19),0),19);self.assertRaises(ValueError,both,struct.pack('<I',19)+struct.pack('>I',20),0)
 def test_RockRidge_name_overrides_ISO(self):
  b=bytearray(60);b[32]=3;b[33:36]=b'OLD';b[36:46]=b'NM\x0a\x01\0new.x';self.assertEqual(name_of(b),'new.x')
 def test_word_FNV_width_and_known_empty_identity(self):
  self.assertEqual(fnv(b''),2166136261);self.assertRaises(ValueError,fnv,b'bad')
if __name__=='__main__':unittest.main()
