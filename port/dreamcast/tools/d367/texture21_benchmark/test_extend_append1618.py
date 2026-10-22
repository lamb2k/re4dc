import copy,hashlib,struct,unittest,zlib
from extend_append1618 import twid_candidate
from plan_append1596 import scoped,layout
from extend_append1600 import shifts

def fixture():
 t=struct.pack('<64s8I',b'SYNTHETIC_NOT_GAME',16,16,0,144,688,4,1,0);body=t+bytes(688);b=struct.pack('<8s10I',b'RE4DCTX\0',2,48,96,1,48,144,688,zlib.crc32(body),1,0)+body
 r=dict(candidate_sha256=hashlib.sha256(b).hexdigest(),package_bytes=832,candidate_crc32=zlib.crc32(body),logical=[32,16],physical=[16,16],uv_scale=[1.,1.],format=0,flags=4,payload_type=1,candidate_payload=688,decoded_levels=[1,2,4,8,16],source_codebook_present=False,original_key='12345678-abcdef01');r['scoped_key']=scoped(r['original_key'],r['candidate_sha256']);return b,r
def rebind(b,r):
 b=bytearray(b);struct.pack_into('<I',b,36,zlib.crc32(b[48:]));b=bytes(b);r=copy.deepcopy(r);r.update(candidate_sha256=hashlib.sha256(b).hexdigest(),package_bytes=len(b),candidate_crc32=zlib.crc32(b[48:]));r['scoped_key']=scoped(r['original_key'],r['candidate_sha256']);return b,r
class TwidDeltaTests(unittest.TestCase):
 def test_exact_twiddled_contract_accepts_both_logical_widths(self):
  for width in(32,64):
   b,r=fixture();r['logical']=[width,16];c=twid_candidate(b,r);self.assertEqual((c['payload_type'],c['payload'],c['mip_levels']),(1,688,5))
 def test_reject_VQ_alpha_format_flags_dimensions_UV_and_missing_levels(self):
  b,r=fixture()
  for field,value in[('payload_type',2),('format',1),('flags',0),('physical',[32,32]),('logical',[16,64]),('uv_scale',[2.,1.]),('decoded_levels',[1,2,4,8]),('source_codebook_present',True)]:
   bad=copy.deepcopy(r);bad[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):twid_candidate(b,bad)
 def test_actual_descriptor_VQ_or_alpha_refused_after_valid_rehash(self):
  b,r=fixture()
  for off,value in[(48+64+3*4,1),(48+64+7*4,2),(48+64,32),(48+64+6*4,0)]:
   bad=bytearray(b);struct.pack_into('<I',bad,off,value);bad,meta=rebind(bad,r)
   with self.subTest(offset=off),self.assertRaises(ValueError):twid_candidate(bad,meta)
 def test_header_and_bodyCRC_and_namespace_independently_refused(self):
  b,r=fixture();bad=bytearray(b);bad[-1]^=1;r2=copy.deepcopy(r);r2['candidate_sha256']=hashlib.sha256(bad).hexdigest()
  with self.assertRaises(ValueError):twid_candidate(bytes(bad),r2)
  r2=copy.deepcopy(r);r2['scoped_key']='00000000-00000000'
  with self.assertRaises(ValueError):twid_candidate(b,r2)
  bad=bytearray(b);struct.pack_into('<I',bad,44,1);bad,meta=rebind(bad,r)
  with self.assertRaises(ValueError):twid_candidate(bad,meta)
 def test_18_insertions_preserve56_sector_index_capacity_and_extents(self):
  key=lambda n:'%08x-00000000'%n
  rows={key(n):dict(bytes=832,sha256='schema')for n in range(0,7133*2,2)};h,i,p,size=layout(rows);before={r['key']:r for r in p}
  for n in range(18):rows[key(n*2+1)]=dict(bytes=832,sha256='schema')
  h,i,f,finalsize=layout(rows);self.assertEqual((len(f),len(i),finalsize-size),(7151,56*2048,18*2048));self.assertEqual(sum(r['members']for r in shifts(before,{r['key']:r for r in f})),7133)
if __name__=='__main__':unittest.main(verbosity=2)
