import copy,gzip,json,os,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import immutable_append1760_native_c_writer as new
import native1760_source_binding21 as binding
import test_immutable_append1600_writer as original
import test_immutable_append1618_writer as v1tests
import test_immutable_append1618_buffered_v2_writer as v2tests

def local_c(s):return Path(s)if os.name=='nt'else Path('/mnt/c/'+s[3:].replace('\\','/'))
def record():return json.loads(gzip.decompress(local_c(binding.MANIFEST_PATH).read_bytes()))
class Writer1760Tests(v2tests.BufferedV2Tests):
 def setUp(self):
  original.WriterTests.setUp(self);self.patches=[patch.object(original,'w',new),patch.object(v1tests,'new',new),patch.object(v2tests,'new',new)];self.stream=new.source_stream;fb=SimpleNamespace(open=lambda p:Path(p).open('rb'));self.patches.append(patch.object(new,'source_stream',side_effect=lambda h,i,r,g:self.stream(h,i,r,g,fb)))
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  original.WriterTests.tearDown(self)
 def test_exact_child_allocation_refusals(self):
  p=dict(controller_sha256='a'*64,metadata_root='synthetic',payload_roots=['one','two'],prior_failed_controller_sha256='c'*64,native_source_manifest_path=binding.MANIFEST_PATH,native_source_manifest_sha256=binding.MANIFEST_SHA);pp=self.root/'p.json';pp.write_text(json.dumps(p));ps=new.sha(pp);ap=self.root/'a.json';a=dict(allocated=True,allocation_id='SYNTHETIC_NOT_EXECUTABLE',writer_plan_sha256=ps,writer_source_sha256=new.sha(new.__file__),controller_sha256=p['controller_sha256'],aggregate_cap_bytes=new.CAP,runtime_floor_bytes=new.FLOOR,peer_reserved_bytes=new.PEER,inner_seconds=51,approved_output_root=p['metadata_root'],approved_payload_roots=p['payload_roots'],prior_failed_controller_sha256=p['prior_failed_controller_sha256'],native_source_manifest_path=binding.MANIFEST_PATH,native_source_manifest_sha256=binding.MANIFEST_SHA);ap.write_text(json.dumps(a));self.assertTrue(new.allocation(pp,ps,ap,new.sha(ap),p)['allocated'])
  for field,value in [('allocated',False),('aggregate_cap_bytes',new.CAP+1),('runtime_floor_bytes',0),('peer_reserved_bytes',0),('writer_source_sha256','0'*64),('controller_sha256','0'*64),('approved_payload_roots',['x']),('compression_credits',[{}]),('prior_failed_controller_sha256','0'*64),('native_source_manifest_path','elsewhere'),('native_source_manifest_sha256','0'*64)]:
   ap.write_text(json.dumps({**a,field:value}))
   with self.subTest(field=field),self.assertRaises(ValueError):new.allocation(pp,ps,ap,new.sha(ap),p)
class Binding1760Tests(unittest.TestCase):
 def test_actual143_metadata_and_binary_map(self):
  b=binding.Native1760Binding(record());self.assertEqual((len(b.by_c),len(b.by_key)),(143,142));raw=local_c(binding.MEMBER_PATH).read_bytes();self.assertEqual((len(raw),new.hashlib.sha256(raw).hexdigest()),(7151*32,binding.MEMBER_SHA))
 def test_native143_namespace_identity_alias_refusals(self):
  for label,change in [('count',lambda r:r['files'].pop()),('root',lambda r:r['roots'].update(actual1618='wrong')),('UNC',lambda r:r['files'][0].update(c_source_path=r'\\server\share\file')),('alias',lambda r:r['files'][1].update(native_identity=copy.deepcopy(r['files'][0]['native_identity']))),('link2',lambda r:r['files'][0]['native_identity'].update(link_count=2)),('mtime',lambda r:r['files'][0].update(last_write_filetime=0)),('parent',lambda r:r.update(parent_input_seal_sha256='0'*64)),('membermap',lambda r:r['parent_member_sha256_binary'].update(sha256='0'*64)),('target56',lambda r:r['expected'].update(index_sectors=56))]:
   r=record();change(r)
   with self.subTest(label=label),self.assertRaises(ValueError):binding.Native1760Binding(r)
 def test_manifest_plan_pin_refusals(self):
  for p in [{},dict(native_source_manifest_path='wrong',native_source_manifest_sha256=binding.MANIFEST_SHA),dict(native_source_manifest_path=binding.MANIFEST_PATH,native_source_manifest_sha256='0'*64)]:
   with self.assertRaises(ValueError):binding.Native1760Binding.load(p)
 @unittest.skipUnless(os.name=='nt','native retained source143 resolver')
 def test_actual7293_resolver_and_57sector_negative(self):
  p=json.loads(local_c(r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\append1760-writer-native-c-01\writer-plan.json').read_text());head,index,rows=new.resolve(p);self.assertEqual(len(rows),7293);self.assertEqual(len({str(r['path'])for r in rows}),143);b=binding.Native1760Binding.load(p)
  bad=bytearray(head);new.struct.pack_into('<I',bad,20,116736)
  with self.assertRaises(ValueError):b.resolve(bad,index)
  with self.assertRaises(ValueError):b.map_rows(rows[:-1])
  for field,value in [('parent_input_seal_path','wrong'),('parent_input_seal_sha256','0'*64)]:
   with self.assertRaises(ValueError):new.resolve({**p,field:value})
if __name__=='__main__':unittest.main(verbosity=2)
