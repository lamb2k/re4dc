from pathlib import Path
import json,hashlib,sys,unittest,copy,io
P=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23/native-normalize-f240r1');sys.path.insert(0,str(P))
from proof_objects import verify_objects,SHARED
from normalize import validate_config
from policy import FINAL_SOURCE,EVIDENCE_ROOT
class BindingControls(unittest.TestCase):
 def setUp(self):
  self.root=EVIDENCE_ROOT+'/on2';self.manifest=dict(path=self.root+'/OBJECTS.json',sha256='m');self.rows=[dict(path=self.root+'/obj/a.o',sha256='s',bytes=1),dict(path=SHARED+'/a.ld',sha256='a',bytes=2),dict(path=SHARED+'/ovlh/b.o',sha256='b',bytes=3)]
  self.mapping=dict(source=FINAL_SOURCE,arm='on',original_manifest=self.manifest,original_link_receipt_sha256='l',live_standard_object_root=self.root+'/obj',entries=[])
  for r,kind,folder in zip(self.rows[1:],['ACTUAL_COPIED_FILE','ACTUAL_RETAINED_OWNED_LINK_SCRATCH'],['link-inputs','link-scratch']):
   self.mapping['entries'].append(dict(original_path=r['path'],original_sha256=r['sha256'],original_bytes=r['bytes'],status='RETAINED_REHASHABLE',retention_kind=kind,retained_path=self.root+'/'+folder+'/'+r['path'][len(SHARED)+1:],retained_sha256=r['sha256'],retained_bytes=r['bytes']))
 def runmap(self):return verify_objects(self.rows,self.mapping,self.manifest,FINAL_SOURCE,'on','l',lambda r:b'')
 def test_both_actual_retention_kinds(self):self.assertEqual(self.runmap()['retained_mapped_rehashed'],2)
 def test_arbitrary_retained_path_refused(self):
  self.mapping['entries'][0]['retained_path']='/tmp/arbitrary';self.assertRaises(ValueError,self.runmap)
 def test_invented_retention_kind_refused(self):
  self.mapping['entries'][0]['retention_kind']='COPY_ASSUMED';self.assertRaises(ValueError,self.runmap)
 def test_missing_alias_refused(self):
  self.mapping['entries'].pop();self.assertRaises(ValueError,self.runmap)
 def test_wrong_programme_refused(self):
  self.mapping['source']='old';self.assertRaises(ValueError,self.runmap)
 def test_off_config_refused(self):self.assertRaises(ValueError,validate_config,dict(source=FINAL_SOURCE,root=EVIDENCE_ROOT,arms={'off':{}}),'off')
 def test_exact_on_scope(self):validate_config(dict(source=FINAL_SOURCE,root=EVIDENCE_ROOT,arms={'on':{}}),'on')
stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BindingControls));assert r.wasSuccessful(),stream.getvalue()
(P/'HOST-CONTROLS.json').write_text(json.dumps(dict(status='PASS',tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),output=stream.getvalue(),build=False,stage=False,guest=False),indent=2)+'\n');print(stream.getvalue())
