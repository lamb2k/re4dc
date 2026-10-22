import copy,hashlib,json,mmap,struct,unittest,zlib
from pathlib import Path
import plan_fresh1760_disc as w
class FreshLayoutTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.known=w.reader(w.local('/root/probe/codex-texture-atlas21/port/dreamcast/tools/d367/texpack.py'))
 def fixture(self,kind,mip,legacy=False):
  payload=b'P'*(688 if mip and kind==1 else 3414 if mip else 512);desc=struct.pack('<64s8I',b'fixture',16,16,0,144,len(payload),4 if mip else 0,kind,0);body=desc+payload;h=struct.pack('<8s10I',b'RE4DCTX\0',2,48,96,1,48,144,len(payload),zlib.crc32(payload if legacy else body),1,0);return h+body
 def test_actual_native_flags_counts_and_legacy_route_not_zero_mip_label(self):
  pkgs={(i,0):self.fixture(kind,mip,legacy)for i,(kind,mip,legacy)in enumerate([(2,True,False),(1,True,True),(2,False,False),(1,False,True)])};pack,n=self.known.build(pkgs);r,binary=w.package_inventory(pack,self.known,w.digest(pack));self.assertEqual(r['counts']['mip_packages'],2);self.assertEqual(r['counts']['payload_1'],2);self.assertEqual(r['counts']['payload_2'],2);self.assertEqual(r['CRC_categories'],{'canonical_descriptor_payload':2,'legacy_payload_only':2});self.assertEqual(len(binary),4*32)
  with self.assertRaises(ValueError):w.package_inventory(pack,self.known,'0'*64)
 def world_fixture(self):
  places=bytes(52);part=struct.pack('<IIHH4B',1,2,16,16,0,0,0,0);newpart=struct.pack('<IIHH4B',3,4,16,16,0,0,0,0)
  def world(p):
   body=p+places;return struct.pack('<4s7I',b'R4PW',1,1,1,1,zlib.crc32(body),0,0)+body
  a,b=world(part),world(newpart);meshbody=b'GEOM';mesh=struct.pack('<4s19I',b'R4IM',3,84,zlib.crc32(meshbody),1,1,*([0]*14))+meshbody;crc=struct.unpack_from('<I',a,20)[0];ids=struct.pack('<4s3I',b'R4ID',1,1,crc)+bytes(16);cl=b'\1';tc=struct.pack('<4s5I',b'R4TC',1,1,1,crc,zlib.crc32(cl))+cl+bytes(3);spec=dict(original_sha256=w.digest(a),candidate_sha256=w.digest(b),bytes=len(b),canonical_source_crc=crc,physical_body_crc=struct.unpack_from('<I',b,20)[0],physical_file_fnv=w.fnv(b),mesh_crc=zlib.crc32(meshbody),mesh_sha256=w.digest(mesh),mesh_bytes=len(mesh));return a,b,spec,ids,tc,mesh
 def test_original_metadata_sourceCRC_keyonly_world_parity_and_absent_TC(self):
  a,b,s,ids,tc,mesh=self.world_fixture();r=w.world_parity(a,b,s,ids,tc,mesh);self.assertTrue(r['geometry_exact']);self.assertTrue(r['classes_present']);self.assertEqual(r['M0_actual_header_crc'],r['M1_cert_expected_source_crc']);self.assertFalse(w.world_parity(a,b,s,ids,None,mesh)['classes_present'])
 def test_nonkey_material_metadata_and_geometry_mutations_refused(self):
  a,b,s,ids,tc,mesh=self.world_fixture()
  for label,mutate in [('ids',lambda:(a,b,s,ids[:12]+bytes(4)+ids[16:],tc,mesh)),('classes',lambda:(a,b,s,ids,tc[:24]+b'X'+tc[25:],mesh)),('mesh',lambda:(a,b,s,ids,tc,mesh[:-1]+b'X'))]:
   with self.subTest(label=label),self.assertRaises(ValueError):w.world_parity(*mutate())
  bad=bytearray(b);bad[40]^=1;struct.pack_into('<I',bad,20,zlib.crc32(bad[32:]));q={**s,'candidate_sha256':w.digest(bad),'physical_body_crc':struct.unpack_from('<I',bad,20)[0],'physical_file_fnv':w.fnv(bad)}
  with self.assertRaises(ValueError):w.world_parity(a,bad,q,ids,tc,mesh)
 def test_concrete_layout_start_and_all27_worlds_original_identity(self):
  base=w.local('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/canonical1004-pair-01/M0/full-readback.json');selected=w.local('/mnt/c/Flycast-Evidence/re4-dreamcast/mipmap21-next792-integration-20261022/ROOT-selected792-20261022.json');f=json.loads(base.read_text())['files'];s=json.loads(selected.read_text())['selected'];rows,end=w.append_layout(f,s);self.assertEqual((len(rows),rows[0]['new_extent'],end,w.LBA0+end//2048),(28,549150,1195433984,628708));self.assertNotIn('r11f',[r.get('room')for r in rows]);self.assertNotIn('r200',[r.get('room')for r in rows])
  bad=copy.deepcopy(f);bad['/dc/tex.pak']['sha256']='0'*64
  with self.assertRaises(ValueError):w.append_layout(bad,s)
 def iso_fixture(self,cycle=False):
  b=bytearray(21*2048);b[16*2048:16*2048+7]=b'\1CD001\1';b[17*2048]=255
  def rec(name,extent,size):
   n=33+len(name)+(0 if len(name)%2 else 1);r=bytearray(n);r[0]=n;struct.pack_into('<I',r,2,extent);struct.pack_into('>I',r,6,extent);struct.pack_into('<I',r,10,size);struct.pack_into('>I',r,14,size);r[25]=2;r[32]=len(name);r[33:33+len(name)]=name;return r
  root=rec(b'\0',45020,2048);b[16*2048+156:16*2048+156+len(root)]=root
  if cycle:r=rec(b'CYCLE',45020,2048);b[20*2048:20*2048+len(r)]=r
  return b
 def test_directory_cycle_LEBE_and_nonprimary_refusal(self):
  self.assertEqual(len(w.directory(self.iso_fixture())[0]),0)
  with self.assertRaises(ValueError):w.directory(self.iso_fixture(True))
  bad=self.iso_fixture();bad[17*2048]=2
  with self.assertRaises(ValueError):w.directory(bad)
  bad=self.iso_fixture();bad[16*2048+156+6]^=1
  with self.assertRaises(ValueError):w.directory(bad)
if __name__=='__main__':unittest.main(verbosity=2)
