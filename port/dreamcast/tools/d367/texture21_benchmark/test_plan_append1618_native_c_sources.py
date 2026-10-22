import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import plan_append1618_native_c_sources as p

def rows_fixture():
 rows=[];manifests={g:{}for g in p.SEALS}
 for i in range(6537):rows.append(dict(key='%08x-00000000'%i,source='canonical1004',path=Path('/synthetic/base/tex.pak'),source_root=Path('/synthetic/base'),source_offset=i,sha256='member-sha',body_crc32=None))
 key=7000
 for group,count in p.EXPECTED_FILES.items():
  if group=='canonical1004':continue
  for i in range(count):
   name='%08x-00000000'%key;key+=1;rel='textures/'+name+'.re4tex';digest='%064x'%key;root=Path('/synthetic')/group;rows.append(dict(key=name,source=group,path=root/rel,source_root=root,source_offset=0,sha256=digest,body_crc32=i));manifests[group][rel]=digest
 return rows,manifests

class NativeSourcePlanTests(unittest.TestCase):
 def test_canonical_C_only_and_native_alias_refusal(self):
  p.require_same_path(r'C:\Exact\File',r'\\?\C:\exact\file')
  for bad in[r'\\server\share\file',r'\\?\UNC\server\share\file',r'D:\file',r'C:relative','relative',r'\\?\Volume{abc}\file']:
   with self.subTest(path=bad),self.assertRaises(ValueError):p.canonical_c(bad)
  with self.assertRaises(ValueError):p.require_same_path(r'C:\Exact\File',r'\\?\C:\Other\File')
 def test_all7151_members_map_to615_explicit_files_offsets_and_hashes_retained(self):
  rows,manifests=rows_fixture();mapped,files=p.map_rows(rows,manifests);self.assertEqual((len(mapped),len(files)),(7151,615));self.assertEqual(sum(f['member_refs']for f in files.values()),7151)
  for a,b in zip(rows,mapped):
   self.assertEqual((a['key'],a['source_offset'],a['sha256'],a['body_crc32']),(b['key'],b['source_offset'],b['sha256'],b['body_crc32']));self.assertTrue(str(b['path']).startswith(p.ROOTS[a['source']]))
 def test_missing_or_changed_manifest_no_fallback_and_unknown_group_refused(self):
  rows,m=rows_fixture();first=rows[6537];m[first['source']].clear()
  with self.assertRaises(ValueError):p.map_rows(rows,m)
  rows,m=rows_fixture();rows[-1]['source']='not_explicit'
  with self.assertRaises(ValueError):p.map_rows(rows,m)
  rows,m=rows_fixture();rows[-1]['path']=rows[-1]['source_root']/'outside-name'
  with self.assertRaises(ValueError):p.map_rows(rows,m)
 def test_shared_native_identity_rejected(self):
  f={'one':dict(c_source_path='one',c_source_root='root',expected_file_sha256='a'),'two':dict(c_source_path='two',c_source_root='root',expected_file_sha256='b')};same=dict(sha256='synthetic',native_identity=dict(volume_serial=1,file_index=2,link_count=1))
  with patch.object(p,'verified_file',return_value=same),self.assertRaises(ValueError):p.bind_identities(f)
 @unittest.skipUnless(os.name=='nt','native Windows C fixture')
 def test_native_C_file_fullsha_singlelink_finalpath_and_wrongsha_refusal(self):
  with tempfile.TemporaryDirectory(prefix='re4-c-source-plan-owned-')as temp:
   root=Path(temp);file=root/'source';file.write_bytes(b'SMALL_OWNED_SOURCE_FIXTURE');digest=hashlib.sha256(file.read_bytes()).hexdigest();r=p.verified_file(file,root,digest);self.assertEqual(r['sha256'],digest);self.assertEqual(r['native_identity']['link_count'],1);p.require_same_path(file,r['native_final_path'])
   with self.assertRaises(ValueError):p.verified_file(file,root,'0'*64)
   alias=root/'hardlink';os.link(file,alias)
   with self.assertRaises(ValueError):p.verified_file(file,root,digest)
if __name__=='__main__':unittest.main(verbosity=2)
