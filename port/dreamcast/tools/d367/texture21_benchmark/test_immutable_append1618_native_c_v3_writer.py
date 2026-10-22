import copy,ctypes,gzip,hashlib,json,os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import immutable_append1618_native_c_v3_writer as new
import native_c_source_binding21 as binding
import test_immutable_append1600_writer as original
import test_immutable_append1618_writer as v1tests
import test_immutable_append1618_buffered_v2_writer as v2tests

def record():
 p=Path(binding.MANIFEST_PATH)if os.name=='nt'else Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/append1618-native-c-source-plan-01/SOURCE-FILES-615.json.gz')
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==binding.MANIFEST_SHA;return json.loads(gzip.decompress(raw))
class V3CoreTests(v2tests.BufferedV2Tests):
 def setUp(self):
  original.WriterTests.setUp(self);self.patches=[patch.object(original,'w',new),patch.object(v1tests,'new',new),patch.object(v2tests,'new',new)];self.stream=new.source_stream
  fixture_binding=SimpleNamespace(open=lambda path:Path(path).open('rb'))
  self.patches.append(patch.object(new,'source_stream',side_effect=lambda h,i,r,g:self.stream(h,i,r,g,fixture_binding)))
  for p in self.patches:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  original.WriterTests.tearDown(self)
 def test_exact_child_allocation_refusals(self):
  plan=dict(controller_sha256='a'*64,metadata_root='synthetic-meta',payload_roots=['one','two'],prior_failed_controller_sha256='c'*64,c_source_manifest_path=binding.MANIFEST_PATH,c_source_manifest_sha256=binding.MANIFEST_SHA);pp=self.root/'plan.json';pp.write_text(json.dumps(plan));ps=new.sha(pp);ap=self.root/'allocation.json'
  a=dict(allocated=True,allocation_id='SYNTHETIC_NOT_EXECUTABLE',writer_plan_sha256=ps,writer_source_sha256=new.sha(new.__file__),controller_sha256=plan['controller_sha256'],aggregate_cap_bytes=new.CAP,runtime_floor_bytes=new.FLOOR,peer_reserved_bytes=new.PEER,inner_seconds=51,approved_output_root=plan['metadata_root'],approved_payload_roots=plan['payload_roots'],prior_failed_controller_sha256=plan['prior_failed_controller_sha256'],c_source_manifest_path=binding.MANIFEST_PATH,c_source_manifest_sha256=binding.MANIFEST_SHA)
  ap.write_text(json.dumps(a));self.assertEqual(new.allocation(pp,ps,ap,new.sha(ap),plan)['allocation_id'],a['allocation_id'])
  for field,value in[('allocated',False),('aggregate_cap_bytes',new.CAP+1),('runtime_floor_bytes',0),('peer_reserved_bytes',0),('controller_sha256','b'*64),('writer_source_sha256','0'*64),('approved_payload_roots',['elsewhere']),('compression_credits',[{}]),('prior_failed_controller_sha256','d'*64),('c_source_manifest_path','wrong'),('c_source_manifest_sha256','0'*64)]:
   ap.write_text(json.dumps({**a,field:value}))
   with self.subTest(field=field),self.assertRaises(ValueError):new.allocation(pp,ps,ap,new.sha(ap),plan)

class NativeBindingTests(unittest.TestCase):
 def test_real_frozen615_metadata_parses_and_manifest_pin_refusals(self):
  b=binding.NativeCBinding(record());self.assertEqual((len(b.by_old),len(b.by_c)),(615,615));self.assertEqual(ctypes.sizeof(binding.INFO),52)
  for p in[{},dict(c_source_manifest_path='wrong',c_source_manifest_sha256=binding.MANIFEST_SHA),dict(c_source_manifest_path=binding.MANIFEST_PATH,c_source_manifest_sha256='0'*64)]:
   with self.assertRaises(ValueError):binding.NativeCBinding.load(p)
 def test_manifest_path_nativeID_alias_singlelink_mtime_and_provenance_refused(self):
  for label,mutate in[
   ('filecount',lambda r:r['files'].pop()),
   ('unknownroot',lambda r:r['files'][0].update(c_source_root=r'C:\wrong')),
   ('UNCpath',lambda r:r['files'][0].update(c_source_path=r'\\server\share\file')),
   ('escape',lambda r:r['files'][0].update(relative_path='../escape')),
   ('alias',lambda r:r['files'][1].update(native_identity=copy.deepcopy(r['files'][0]['native_identity']))),
   ('hardlink',lambda r:r['files'][0]['native_identity'].update(link_count=2)),
   ('mtime',lambda r:r['files'][0].update(last_write_filetime=0)),
   ('producer',lambda r:r['producer_manifest_pins']['next415'].update(sha256='0'*64))]:
   r=record();mutate(r)
   with self.subTest(label=label),self.assertRaises(ValueError):binding.NativeCBinding(r)
 def test_map_exact7151_member_contract_and_unknown_source_refusal(self):
  b=binding.NativeCBinding(record());rows=[]
  for e in b.by_old.values():
   for i in range(e['member_refs']):rows.append(dict(path=e['old_source_path'],source=e['source_group'],sha256=e['sha256'],body_crc32=e['body_crc32'],bytes=1 if e['source_group']=='canonical1004'else e['native_identity']['logical_bytes'],source_offset=i if e['source_group']=='canonical1004'else 0))
  mapped=b.map_rows(rows);self.assertEqual(len(mapped),7151);self.assertTrue(all(binding.proof.canonical_c(r['path']).startswith('c:')for r in mapped))
  rows[-1]['path']='unknown'
  with self.assertRaises(ValueError):b.map_rows(rows)
 def test_context_closes_file_even_when_final_identity_check_raises(self):
  with tempfile.TemporaryDirectory(prefix='re4-c-binding-owned-')as temp:
   path=Path(temp)/'tiny';path.write_bytes(b'OWNED_FIXTURE');obj=object.__new__(binding.NativeCBinding);obj.by_c={'FIXTURE':{}}
   calls=[]
   def check(f,e):
    calls.append(f)
    if len(calls)==2:raise ValueError('SYNTHETIC_FINAL_IDENTITY_FAILURE')
   with patch.object(binding.proof,'canonical_c',return_value='FIXTURE'),patch.object(binding,'check_handle',side_effect=check),self.assertRaises(ValueError):
    with obj.open(path)as f:self.assertFalse(f.closed)
   self.assertTrue(f.closed);self.assertEqual(len(calls),2)
 @unittest.skipUnless(os.name=='nt','native Windows handle ABI fixture')
 def test_actual_opened_handle_fileID_mtime_and_finalpath_binding(self):
  with tempfile.TemporaryDirectory(prefix='re4-native-handle-owned-')as temp:
   root=Path(temp);path=root/'data';path.write_bytes(b'OWNED_NATIVE_BINDING');proof=binding.proof.verified_file(path,root,hashlib.sha256(path.read_bytes()).hexdigest());expected={**proof,'c_source_path':str(path)}
   with path.open('rb')as file:
    binding.check_handle(file,expected)
    for field in('file_index','link_count','logical_bytes'):
     bad=copy.deepcopy(expected);bad['native_identity'][field]+=1
     with self.subTest(field=field),self.assertRaises(ValueError):binding.check_handle(file,bad)
    bad=copy.deepcopy(expected);bad['last_write_filetime']+=1
    with self.assertRaises(ValueError):binding.check_handle(file,bad)
    bad=copy.deepcopy(expected);bad['c_source_path']=str(root/'other')
    with self.assertRaises(ValueError):binding.check_handle(file,bad)
if __name__=='__main__':unittest.main(verbosity=2)
