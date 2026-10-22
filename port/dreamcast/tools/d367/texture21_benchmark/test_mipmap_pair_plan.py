import hashlib,io,json,tempfile,unittest
from pathlib import Path
from mipmap_pair_plan import raw_read,both32,record_patch,programme_rows
class PairPlanTests(unittest.TestCase):
 def test_raw_sector_payload_and_crossing_slice(self):
  data=b''.join(bytes([i])*2048 for i in range(6));raw=b''.join(b'H'*16+bytes([i])*2048+b'T'*288 for i in range(6));self.assertEqual(raw_read(io.BytesIO(raw),2047,4099),data[2047:2047+4099])
  with self.assertRaisesRegex(ValueError,'truncated'):raw_read(io.BytesIO(raw),len(data)-1,3)
 def test_all_size_records_are_both_endian(self):
  r={'after_bytes':100,'directory_records':[{'record_lba':45018,'record_offset':254,'tree':'primary'},{'record_lba':45020,'record_offset':400,'tree':'RockRidge'}]};p=record_patch(r,200);self.assertEqual(len(p),2);self.assertEqual(p[0]['after'],both32(200).hex());self.assertEqual(record_patch(r,100),[])
 def test_exact_programme_set_and_extent_cap(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'bytes.bin';source.write_bytes(b'x'*10);h=hashlib.sha256(source.read_bytes()).hexdigest();names=['/1ST_READ.BIN']+['/dc/x%d.ovl'%i for i in range(14)];selected={n:{'after_extent':45000+i*2,'after_bytes':8,'before':{'bytes':8}} for i,n in enumerate(names)};m={'source':'new-reviewed-source','elf_sha256':'newELF','resolved_flags_sha256':'flags','compile_inputs_sha256':'inputs','files':{n:{'bytes':10,'sha256':h,'source_path':str(source)} for n in names}};self.assertEqual(len(programme_rows(m,selected,100000)),15)
   old=m['files'].pop(names[-1])
   with self.assertRaisesRegex(ValueError,'all14'):programme_rows(m,selected,100000)
   m['files'][names[-1]]=old;m['files'][names[-1]]['bytes']=2049
   with self.assertRaisesRegex(ValueError,'exceeds'):programme_rows(m,selected,100000)
 def test_source_mutation_and_missing_identity_rejected(self):
  names=['/1ST_READ.BIN']+['/dc/x%d.ovl'%i for i in range(14)]
  with self.assertRaisesRegex(ValueError,'binding'):programme_rows({'files':{n:{} for n in names}},{n:{} for n in names},100)
if __name__=='__main__':unittest.main()
