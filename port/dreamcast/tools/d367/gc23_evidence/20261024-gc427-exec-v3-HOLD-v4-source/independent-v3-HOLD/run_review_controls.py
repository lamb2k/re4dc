from pathlib import Path
import hashlib,types,sys,unittest,json,io,tempfile,copy
D=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-retest-guest-exec-v3')
p=D/'host_controls.py';raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='54cf8ceec902a5c8f82c6e7631c31e0466175da2bb5274f0008605673fd312cd'
m=types.ModuleType('review_controls');m.__file__=str(p);sys.modules[m.__name__]=m
exec(compile(raw,str(p),'exec'),m.__dict__)
suite=unittest.TestSuite()
for name in unittest.defaultTestLoader.getTestCaseNames(m.prior.Host):
 if name not in m.excluded:suite.addTest(m.prior.Host(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(m.Recovery))
r=unittest.TextTestRunner(verbosity=2).run(suite)
assert r.wasSuccessful() and r.testsRun==87 and not r.skipped
C=m.r
class Extra(unittest.TestCase):
 def meta(self):return dict(kind='synthetic-only',tree='/public/tree',elf='/public/program.elf',warp_lba=400,pad_lba=420,w11_lba=440,fixture_bytes=8192,gdi=C.GDI)
 def files(self,root,meta=None,sidecar=None):
  (root/'base.json').write_text(json.dumps(meta or self.meta()))
  (root/'track03.sha256').write_text(sidecar if sidecar is not None else 'a'*64+'\n')
 def test_duplicate_raw_JSON_even_equal_value_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.files(root)
   text=(root/'base.json').read_text();(root/'base.json').write_text('{"warp_lba":400,'+text[1:])
   with self.assertRaisesRegex(RuntimeError,'Duplicate'):C.host_metadata(root,'a'*64)
 def test_valid_changed_provenance_is_a_different_pin(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.files(root);before=C.host_metadata(root,'a'*64)
   value=self.meta();value['elf']='/public/other-program.elf';self.files(root,value)
   self.assertNotEqual(C.host_metadata(root,'a'*64),before)
 def test_symlink_host_file_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.files(root);(root/'base.json').rename(root/'regular.json');(root/'base.json').symlink_to(root/'regular.json')
   with self.assertRaisesRegex(RuntimeError,'nonregular'):C.host_metadata(root,'a'*64)
 def test_sidecar_sha_substitution_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.files(root,sidecar='b'*64+'\n')
   with self.assertRaisesRegex(RuntimeError,'hash sidecar'):C.host_metadata(root,'a'*64)
 def test_outside_track_GDI_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);meta=self.meta();meta['gdi']=C.GDI.replace('track03.iso','unrelated.iso');self.files(root,meta)
   with self.assertRaisesRegex(RuntimeError,'GDI'):C.host_metadata(root,'a'*64)
 def test_numeric_layout_wrong_but_valid_JSON_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);meta=self.meta();meta['pad_lba']=400;self.files(root,meta)
   with self.assertRaisesRegex(RuntimeError,'fixture layout'):C.host_metadata(root,'a'*64)

r2=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Extra));assert r2.wasSuccessful()
base=C;mutants=[]
for name,old,new,test in [
 ('sidecar',"need(raw_files['track03.sha256'] in [track_sha256.encode(),(track_sha256+'\\n').encode(),(track_sha256+'\\r\\n').encode()]",'need(True','test_sidecar_sha_substitution_refuses'),
 ('symlink','p.is_file() and not p.is_symlink()','p.is_file()','test_symlink_host_file_refuses'),
 ('duplicate',"need(key not in result,'Duplicate host base JSON field')","need(True,'Duplicate host base JSON field')",'test_duplicate_raw_JSON_even_equal_value_refuses'),
 ('numeric','type(meta[name]) is int and meta[name]==value','type(meta[name]) is int','test_numeric_layout_wrong_but_valid_JSON_refuses')]:
 raw=Path(base.__file__).read_text();assert old in raw,(name,old);raw=raw.replace(old,new,1)
 mod=types.ModuleType('mutant_'+name);mod.__file__=base.__file__;sys.modules[mod.__name__]=mod;exec(compile(raw,mod.__file__,'exec'),mod.__dict__);C=mod
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([Extra(test)]));assert result.failures and not result.errors,(name,stream.getvalue())
 mutants.append(dict(name=name,caught=True,output=stream.getvalue()))
C=base
Path(sys.argv[1]).write_text(json.dumps(dict(author_public_controls=87,extra_controls=6,mutants=mutants,private_binding=False,SDK_stage_guest=False,pending_actual=sorted(m.excluded)),indent=2)+'\n')
print('PASS87+6 controls and4 semantic mutants; no actual binding')
