"""Small mocked-identity files only. No game images, ELF copy, subprocess or emulator."""
import copy,hashlib,importlib.util,json,os,pathlib,tempfile,unittest
P=pathlib.Path(__file__).parent;s=importlib.util.spec_from_file_location('outer',P/'outer-driver.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
class Outer(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name);self.realP=m.P;self.hash=m.hash_file;m.P=self.p;self.profile=json.loads((P/'guest-profile-v2.json').read_text());self.disc=self.p/'stage'/'input'/'gdemu';self.disc.mkdir(parents=True);self.template=self.p/'template';(self.template/'data').mkdir(parents=True)
  self.image=self.disc/'track03.iso';self.image.write_bytes(b'iso');self.elf=self.p/'exact.elf';self.elf.write_bytes(b'elf');self.layout=self.p/'layout.json';self.layout.write_bytes(b'layout');self.dep=self.p/'dependency.py';self.dep.write_bytes(b'pass');self.tool=self.p/'tool.py';self.tool.write_bytes(b'tool');(self.disc.parents[1]/'KEEP.txt').write_bytes(b'keep')
  self.profile['disc']={'path':str(self.disc),'files':{'track03.iso':{'bytes':3,'sha256':m.IMAGE,'native_id':'0x21'}},'stage_receipts':{'KEEP.txt':sha(self.disc.parents[1]/'KEEP.txt')}};self.profile['elf_path']=str(self.elf);self.profile['observer']['layout']=str(self.layout);self.profile['observer']['layout_sha256']=sha(self.layout);self.profile['retained_dependencies']={'dependency.py':{'path':str(self.dep),'sha256':sha(self.dep)}}
  tmpl={}
  for n in ['flycast.exe','emu.cfg','data/a.bin','data/b.bin']:
   f=self.template/n;f.write_bytes(n.encode());tmpl[n]={'sha256':sha(f)}
  self.profile['template']={'path':str(self.template),'files':tmpl};(self.p/'source-manifest.json').write_text(json.dumps({'files':{'tool.py':{'sha256':sha(self.tool)}}}))
  def hashes(path,guard=lambda:None):
   guard()
   if pathlib.Path(path)==self.image:return m.IMAGE
   if pathlib.Path(path)==self.elf:return m.ELF
   return self.hash(path,guard)
  m.hash_file=hashes
 def tearDown(self):m.P=self.realP;m.hash_file=self.hash;self.tmp.cleanup()
 def preflight(self):return m.preflight(self.profile,lambda:None,lambda _:0x21)
 def test_tiny_fixture_identity_preflight(self):self.assertIn('track03.iso',self.preflight())
 def test_template_unexpected_oldstate_refused(self):
  (self.template/'data'/'disc.state').write_bytes(b'old')
  with self.assertRaisesRegex(RuntimeError,'unexpected template'):self.preflight()
 def test_template_and_tool_change_refused(self):
  self.tool.write_bytes(b'changed')
  with self.assertRaisesRegex(RuntimeError,'own reviewed'):self.preflight()
 def test_source_image_native_replacement_refused(self):
  with self.assertRaisesRegex(RuntimeError,'fileID/linkcount'):m.preflight(self.profile,lambda:None,lambda _:0x22)
 def test_source_image_linkcount_refused(self):
  os.link(self.image,self.p/'alias-image')
  with self.assertRaisesRegex(RuntimeError,'fileID/linkcount'):self.preflight()
 def test_changed_accepted_stage_receipt_refused(self):
  (self.disc.parents[1]/'KEEP.txt').write_bytes(b'changed')
  with self.assertRaisesRegex(RuntimeError,'stage receipt'):self.preflight()
 def test_floor_exception_during_hash_propagates_before_output(self):
  def floor():raise RuntimeError('injected floor')
  with self.assertRaisesRegex(RuntimeError,'floor'):m.preflight(self.profile,floor,lambda _:0x21)
  self.assertFalse((self.p/'guest').exists())
 def test_bounds_and_programme_not_overrideable(self):
  for key in ['disk_runtime','absolute_actual_seconds','evidence_bytes']:
   profile=copy.deepcopy(self.profile);profile['limits'][key]-=1
   with self.assertRaisesRegex(RuntimeError,'bounds changed'):m.fixed_profile(profile)
 def test_output_no_retry_and_foreign_marker_refused(self):
  profile={'evidence_root':str(self.p/'owned')};cap,control,marker=m.output_paths(profile,'cold-shoot01');self.assertTrue(control.exists());self.assertFalse(cap.exists())
  with self.assertRaisesRegex(RuntimeError,'existing output'):m.output_paths(profile,'cold-shoot01')
  marker.write_text('{}')
  with self.assertRaisesRegex(RuntimeError,'ownership'):m.output_paths(profile,'cinematic01')
 @unittest.skipIf(os.name=='nt','actual symlink test on Linux; no privilege requirement on host')
 def test_ancestor_alias_rejected_before_metadata(self):
  real=self.p/'real';real.mkdir();alias=self.p/'alias';alias.symlink_to(real,target_is_directory=True)
  with self.assertRaisesRegex(RuntimeError,'BEFORE metadata'):m.output_paths({'evidence_root':str(alias/'newroot')},'cold-shoot01')
  self.assertFalse((real/'newroot').exists())
 def test_only_owned_newprogram_qualified_parent(self):
  root=self.p/'guest';root.mkdir();self.profile['evidence_root']=str(root);parent=root/'cold-shoot01';parent.mkdir();control=root/'cold-shoot01-control';control.mkdir();receipt=control/'qualification.json';receipt.write_text(json.dumps({'qualified':True,'profile_sha256':'pinned','program_sha256':m.PROGRAM}));m.validate_seed(self.profile,'return-door01',parent,'pinned')
  with self.assertRaisesRegex(RuntimeError,'parent not qualified'):m.validate_seed(self.profile,'return-door01',parent,'changed')
  with self.assertRaisesRegex(RuntimeError,'only exact owned'):m.validate_seed(self.profile,'return-door01',root/'foreign','pinned')
if __name__=='__main__':unittest.main(verbosity=2)
