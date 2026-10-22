import hashlib,json,os,struct,tempfile,unittest,zlib
from pathlib import Path
from plan_append1596 import layout,append,scoped,candidate,reader,seal

READER=os.environ.get('RE4_KNOWN_TEXPACK_READER')
def fixture():
 side=16;data=bytes(2134);tex=struct.pack('<64s8I',b'synthetic-source',16,16,0,144,len(data),4,2,0);body=tex+data;crc=zlib.crc32(body)&0xffffffff
 blob=struct.pack('<8s10I',b'RE4DCTX\0',2,48,96,1,48,144,len(data),crc,1,0)+body;h=hashlib.sha256(blob).hexdigest();key=scoped('01234567-89abcdef',h)
 return blob,dict(candidate_sha256=h,package_bytes=len(blob),physical=[16,16],format=0,flags=4,payload_type=2,uv_scale=[1.,1.],candidate_payload=len(data),candidate_crc32=crc,original_key='01234567-89abcdef',scoped_key=key)
class AppendTests(unittest.TestCase):
 def test_candidate_canonical_crc_and_deterministic_namespace(self):
  b,r=fixture();v=candidate(b,r);self.assertEqual(v['mip_levels'],5);self.assertEqual(v['payload'],2134);self.assertEqual(r['scoped_key'],scoped(r['original_key'],r['candidate_sha256']))
 def test_corrupt_payload_legacy_crc_missing_mips_wrong_namespace_rejected(self):
  original,r=fixture()
  for kind in ['payload','legacy','nomip','key']:
   b=bytearray(original);rr=dict(r)
   if kind=='payload':b[-1]^=1
   elif kind=='legacy':struct.pack_into('<I',b,36,zlib.crc32(b[144:])&0xffffffff)
   elif kind=='nomip':struct.pack_into('<I',b,132,0);struct.pack_into('<I',b,36,zlib.crc32(b[48:])&0xffffffff)
   else:rr['scoped_key']='ffffffff-ffffffff'
   if kind!='key':rr['candidate_sha256']=hashlib.sha256(b).hexdigest();rr['scoped_key']=scoped(rr['original_key'],rr['candidate_sha256'])
   with self.subTest(kind=kind),self.assertRaises(AssertionError):candidate(bytes(b),rr)
 def test_collision_never_replaces_current_member(self):
  base={'00000001-00000002':{'bytes':10,'sha256':'a'}};old=dict(base)
  with self.assertRaisesRegex(AssertionError,'collision'):append(base,{'00000001-00000002':{'bytes':99}})
  self.assertEqual(base,old)
 def test_layout_capacity_alignment_index_crc(self):
  b,r=fixture();rows={r['scoped_key']:dict(bytes=len(b),sha256=r['candidate_sha256'])};h,index,ordered,size=layout(rows)
  self.assertEqual(struct.unpack_from('<5I',h,8),(1,1,2048,4096,zlib.crc32(index)&0xffffffff));self.assertEqual(ordered[0]['offset'],4096);self.assertEqual(size%2048,0)
  with self.assertRaises(AssertionError):layout({})
 def test_layout_known_archive_writer_equivalence_in_memory(self):
  if not READER:self.skipTest('known texpack reader path required')
  known=reader(Path(READER));b,r=fixture();pkgs={(1,2):b,(4,5):b};expected,n=known.build(pkgs);head,index,rows,size=layout({'%08x-%08x'%k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())for k,v in pkgs.items()});actual=head+index+b+bytes((-len(b))%2048)+b+bytes((-len(b))%2048)
  self.assertEqual(expected,actual);self.assertEqual(known.verify(actual)[0],2);self.assertEqual(len(actual),size)
 def test_seal_rejects_input_mutation(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'member').write_bytes(b'original');text=hashlib.sha256(b'original').hexdigest()+'  member\n';(p/'SHA256SUMS.txt').write_text(text);h=hashlib.sha256((p/'SHA256SUMS.txt').read_bytes()).hexdigest();self.assertEqual(seal(p,h),1);(p/'member').write_bytes(b'changed')
   with self.assertRaises(AssertionError):seal(p,h)
if __name__=='__main__':unittest.main()
