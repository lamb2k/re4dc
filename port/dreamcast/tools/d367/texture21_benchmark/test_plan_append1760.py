import copy,hashlib,json,struct,unittest,zlib
from pathlib import Path
import plan_append1760 as w
from plan_append1596 import layout,scoped,reader
ROOT=Path('/root/re4data/private/texture-rect21-final142-additions-packet-20261022-v2')
if w.os.name=='nt':ROOT=Path(r'\\wsl.localhost\Ubuntu-24.04\root\re4data\private\texture-rect21-final142-additions-packet-20261022-v2')
class CompositionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=json.loads((ROOT/'ADDITIONS142.json').read_text())['selected'];cls.known=reader(w.local('/root/probe/codex-texture-atlas21/port/dreamcast/tools/d367/texpack.py'))
 def test_all142_actual_canonical_descriptors_CRC_mips_namespace(self):
  for r in self.rows:
   with self.subTest(key=r['key']):w.alpha_candidate(w.local(r['absolute_path']).read_bytes(),r)
 def test_packet_member_mutations_refused(self):
  row=self.rows[0];blob=w.local(row['absolute_path']).read_bytes()
  for label,change in [('SHA',lambda r:r.update(sha256='0'*64)),('bytes',lambda r:r.update(bytes=r['bytes']+1)),('CRC',lambda r:r.update(body_crc32=0)),('descriptor',lambda r:r.update(descriptor_hex='00'*96)),('UV',lambda r:r.update(uv_scale=[.5,1.])),('levels',lambda r:r.update(mip_levels=0)),('namespace',lambda r:r.update(key='0'*8+'-'+'0'*8))]:
   r=copy.deepcopy(row);change(r)
   with self.subTest(label=label),self.assertRaises(ValueError):w.alpha_candidate(blob,r)
 def test_three_TWID_padding_texels_required(self):
  r=next(r for r in self.rows if r['payload_type']==1);blob=w.local(r['absolute_path']).read_bytes();side=r['physical'][0]
  self.assertEqual(r['payload_bytes'],6+sum(2*(1<<i)**2 for i in range(side.bit_length())))
  bad=bytearray(blob[:-6]);struct.pack_into('<I',bad,28,len(bad)-144);struct.pack_into('<I',bad,128,len(bad)-144);struct.pack_into('<I',bad,32,zlib.crc32(bad[48:]));q=copy.deepcopy(r);q.update(bytes=len(bad),package_bytes=len(bad),sha256=hashlib.sha256(bad).hexdigest(),candidate_sha256=hashlib.sha256(bad).hexdigest(),body_crc32=zlib.crc32(bad[48:]),candidate_crc32=zlib.crc32(bad[48:]),payload_bytes=len(bad)-144,descriptor_hex=bad[48:144].hex());q['key']=q['scoped_key']=scoped(q['original_key'],q['sha256'])
  with self.assertRaises(ValueError):w.alpha_candidate(bad,q)
 def test_full7293_layout_reindexes57_matches_knownbuilder(self):
  pkgs={(i,0):b'RE4DCTX\0'for i in range(7293)};rows={('%08x-%08x'%k):dict(bytes=len(b))for k,b in pkgs.items()};head,index,ordered,size=layout(rows);built,n=self.known.build(pkgs)
  self.assertEqual((len(index)//2048,len(head)+len(index),len(index)//16-len(rows)),(57,118784,3));self.assertEqual(built[:118784],head+index);self.assertEqual(len(built),size);self.assertEqual(self.known.verify(built)[0],7293)
  bad=bytearray(built);struct.pack_into('<I',bad,20,116736)
  with self.assertRaises(SystemExit):self.known.verify(bad)
 def test_actual_receipt_gate_and_missing_ownership_refusals(self):
  meta=w.local('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/append1618-materialization-v3-native-c-01');c=json.loads((meta/'controller.json').read_text());d=json.loads((meta/'child-result.json').read_text());w.receipt_gate(c,d)
  for field,value in [('qualified',False),('whole_job_empty',False),('exit_code',1),('handles_closed_after_empty',False)]:
   q=copy.deepcopy(c);q[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):w.receipt_gate(q,d)
  for field,value in [('status','FAILED'),('byte_exact_mirror',False),('native_C_sources_bound',614)]:
   q=copy.deepcopy(d);q[field]=value
   with self.subTest(field=field),self.assertRaises(ValueError):w.receipt_gate(c,q)
if __name__=='__main__':unittest.main(verbosity=2)
