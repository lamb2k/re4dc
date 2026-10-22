"""Focused receipt identity regression; tiny synthetic stand-ins, no real assets."""
import copy,json,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import fresh1760_stage_v2 as w
class ConsumerJoinTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name);boot=root/'boot';boot.write_bytes(b'B');overlay=root/'overlay';h=[0]*16;h[14:]=[1,2];overlay.write_bytes(struct.pack('<16I',*h));elf=root/'elf';elf.write_bytes(b'SYNTHETIC_ELF_NOT_PROGRAMME');self.bh=w.sha(boot);self.eh=w.sha(elf)
  self.ind=dict(canonical_runtime_source=w.SOURCE,fullprogram_source_gate=True,source_or_external_inputs_changed_during_unit=False,ELF_sha256=self.eh,programme_sha256=self.bh,all14_header_payload_relocation_CRC_and_newprogramme_binding_pass=True)
  self.q=dict(runtime_source=w.SOURCE,full_source_programme_gate=True,source_inputs_immutable=True,ELF_sha256=self.eh,programme_sha256=self.bh,all14_new_ELF_bound=True,independent_qualification_sha256='i',mip_PAL_flags_ON={k:True for k in ['CAST_MIPMAP','TEX_TWIDDLED_MIPMAP','TEX_PAL4_ALPHA','TEX_PAL4_MIPMAP','TEX_PAL8_ALPHA','TEX_PAL8_MIPMAP']})
  self.consumer=dict(source=w.SOURCE,new_programme_qualified=True,all_consumer_gates_qualified=True,ELF_sha256=self.eh,programme_sha256=self.bh);self.tool=dict(source=w.SOURCE,qualified=True,complete_actual_exec_plugin_tool_closure=True,new_unit_pre_post=True)
  rows=[]
  for path in w.PROGRAMME_PATHS:
   p=boot if path=='/1ST_READ.BIN'else overlay;rows.append(dict(name='program.bin'if path=='/1ST_READ.BIN'else path.removeprefix('/dc/'),Windows_path=str(p),bytes=p.stat().st_size,sha256=w.sha(p),header=h))
  self.manifest=dict(runtime_source=w.SOURCE,qualification_sha256='q',ELF=dict(Windows_path=str(elf),bytes=elf.stat().st_size,sha256=self.eh),programme_sha256=self.bh,image_id=[1,2],files15=rows)
  self.a=dict(schema='qualified792-programme-stage-admission-v1',qualified=True,source=w.SOURCE,qualification=dict(sha256='q'),independent=dict(sha256='i'),consumer={},tool_closure={},manifest={},actual_texture_crc_policy=dict(resident=1,payload_crc=0))
 def tearDown(self):self.temp.cleanup()
 def check(self,c):
  with patch.object(w,'hash_spec',side_effect=[self.q,self.ind,c,self.tool,self.manifest]),patch.object(w.proof,'canonical_c',lambda p:str(p)):return w.qualified_programme(self.a)
 def test_valid_exact_consumer_join_returns15_synthetic_rows(self):
  m,rows=self.check(self.consumer);self.assertEqual(len(rows),15);self.assertEqual(m['ELF']['sha256'],self.eh);self.assertEqual(m['programme_sha256'],self.bh)
 def test_each_missing_or_null_identity_refused(self):
  for field in ('ELF_sha256','programme_sha256'):
   for mode in ('missing','null'):
    c=copy.deepcopy(self.consumer)
    if mode=='missing':del c[field]
    else:c[field]=None
    with self.subTest(field=field,mode=mode),self.assertRaisesRegex(ValueError,'linked-consumer proof join'):self.check(c)
 def test_each_or_both_mismatched_identities_refused(self):
  for fields in [('ELF_sha256',),('programme_sha256',),('ELF_sha256','programme_sha256')]:
   c={**self.consumer,**{f:'0'*64 for f in fields}}
   with self.subTest(fields=fields),self.assertRaisesRegex(ValueError,'linked-consumer proof join'):self.check(c)
if __name__=='__main__':unittest.main(verbosity=2)
