"""New immutable-seal tests: parser, exact refs, final sampling; no guest/RAM/input."""
import copy,hashlib,importlib.util,json,os,pathlib,tempfile,types,unittest
from unittest import mock
P=pathlib.Path(__file__).parent
def load(name,n):
 spec=importlib.util.spec_from_file_location(name,P/n);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
o=load('seal_outer','outer-driver.py');c=load('seal_core','guest-supervisor-core.py');t=load('seal_telemetry_tests','test-failure-telemetry.py')
class ParserAndBounds(unittest.TestCase):
 def setUp(self):self.profile=json.loads((P/'guest-profile-v2.json').read_text())
 def argv(self):return ['--profile',str(P/'guest-profile-v2.json'),'--profile-sha256','profile','--tools-sha256','tools','--mode','cold-shoot01']
 def test_actual_parser_exact_argv_and_no_seed(self):
  a=o.parse_args(self.argv());self.assertEqual(a.mode,'cold-shoot01');self.assertIsNone(a.seed);self.assertEqual(a.profile,P/'guest-profile-v2.json');o.validate_seed(self.profile,a.mode,a.seed,'profile')
 def test_actual_parser_refuses_unknown_mode_and_limit_override(self):
  for argv in [self.argv()+['--seconds','50'],self.argv()[:-1]+['unowned']]:
   with self.assertRaises(SystemExit):o.parse_args(argv)
 def test_actual_cold_seed_refused(self):
  a=o.parse_args(self.argv()+['--seed','prior']);
  with self.assertRaisesRegex(RuntimeError,'cold forbids'):o.validate_seed(self.profile,a.mode,a.seed,'profile')
 def test_every_bound_is_exact_and_not_profile_overrideable(self):
  o.fixed_profile(self.profile)
  for key,val in self.profile['limits'].items():
   v=copy.deepcopy(self.profile);v['limits'][key]=val+1 if isinstance(val,(float,int)) else val+'changed'
   with self.subTest(key=key):
    with self.assertRaisesRegex(RuntimeError,'bounds changed'):o.fixed_profile(v)
 def test_wrong_new_evidence_root_refused(self):
  self.profile['evidence_root']='C:/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-guests-20261021'
  with self.assertRaisesRegex(RuntimeError,'unowned'):o.fixed_profile(self.profile)
class References(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.tmp.name);self.disc=self.p/'disc';self.disc.mkdir();self.old=self.p/'old';(self.old/'cold-shoot01').mkdir(parents=True);(self.old/'cold-shoot01-control').mkdir();self.profile=json.loads((P/'guest-profile-v2.json').read_text());self.profile['disc']['files']={};files={}
  for n in ['track01.bin','track02.raw','track03.iso']:
   source=self.disc/n;source.write_bytes(n.encode());ref=self.old/'cold-shoot01'/n;os.link(source,ref);s=source.stat();digest=hashlib.sha256(source.read_bytes()).hexdigest();self.profile['disc']['files'][n]={'bytes':s.st_size,'sha256':digest};files[n]={'path':str(ref),'bytes':s.st_size,'sha256':digest,'expected_source_links':2 if n=='track03.iso' else None,'source_mtime_ns':s.st_mtime_ns,'source_native_id':'0x21'}
  failed={'qualified':False,'source':o.SOURCE,'program_sha256':o.PROGRAM,'elf_sha256':o.ELF,'image_sha256':o.IMAGE};q=self.old/'cold-shoot01-control/qualification.json';q.write_text(json.dumps(failed));owner=self.old/'OWNED-BY.json';owner.write_text(json.dumps({'lane':'qa21-combined-regression','programme':o.PROGRAM,'image':o.IMAGE}));self.profile['retained_source_references']={'root':str(self.old),'files':files,'qualification':{'path':str(q),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()},'owner':{'path':str(owner),'sha256':hashlib.sha256(owner.read_bytes()).hexdigest()}}
  self.alias=o.no_alias
  def translate(path):
   if str(path)=='C:/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-guests-20261021':return self.old
   return self.alias(path)
  self.patch=mock.patch.object(o,'no_alias',translate);self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def validate(self,native=lambda _:0x21):o.validate_source_references(self.profile,self.disc,lambda:None,native)
 def test_exact_two_link_image_and_refs_accepted_without_cleanup(self):self.validate();self.assertEqual((self.disc/'track03.iso').stat().st_nlink,2)
 def test_common_tracks_can_remain_canonical_shared_without_image_gate_weakening(self):
  for i in range(11):os.link(self.disc/'track01.bin',self.p/('canonical'+str(i)))
  self.validate();self.assertEqual((self.disc/'track01.bin').stat().st_nlink,13)
 def test_third_image_link_refused(self):
  os.link(self.disc/'track03.iso',self.p/'foreign')
  with self.assertRaisesRegex(RuntimeError,'nativeID/linkcount'):self.validate()
 def test_replaced_samebytes_reference_refused(self):
  ref=self.old/'cold-shoot01/track03.iso';data=ref.read_bytes();ref.unlink();ref.write_bytes(data)
  with self.assertRaisesRegex(RuntimeError,'samefile'):self.validate()
 def test_native_image_replacement_refused(self):
  with self.assertRaisesRegex(RuntimeError,'nativeID/linkcount'):self.validate(lambda _:0x22)
 def test_unproved_failed_parent_and_changed_receipt_refused(self):
  q=self.old/'cold-shoot01-control/qualification.json';j=json.loads(q.read_text());j['qualified']=True;q.write_text(json.dumps(j));self.profile['retained_source_references']['qualification']['sha256']=hashlib.sha256(q.read_bytes()).hexdigest()
  with self.assertRaisesRegex(RuntimeError,'exact failed fixture'):self.validate()
class FinalResources(unittest.TestCase):
 def runfake(self,kind):
  helper=t.FailureCleanup();v=helper.fake();stopped=[False];stop=v.stop_private_job
  def stopped_job(job):stop(job);stopped[0]=True
  v.stop_private_job=stopped_job
  if kind=='floor':v.free=lambda:c.RUNTIME-1 if stopped[0] else c.ADMISSION+1
  if kind=='cap':v.evidence_bytes=lambda:c.CAP if stopped[0] else 0
  if kind=='global':v.global_count=lambda:17 if stopped[0] else 0
  if kind=='sampling':
   def free():
    if stopped[0]:raise OSError('injected final sample unavailable')
    return c.ADMISSION+1
   v.free=free
  result=c.monitor(v,[]);self.assertFalse(result['qualified']);self.assertIn('injected after guest',result['error']);self.assertEqual(helper.order[-1],'close');self.assertIn('empty',helper.order);return result
 def test_final_floor_cap_global_each_veto_and_cleanup(self):
  for kind in ['floor','cap','global']:
   with self.subTest(kind=kind):
    r=self.runfake(kind);self.assertTrue(r['final_resources']['available']);self.assertTrue(any('final resource sample' in x for x in r['cleanup_errors']))
 def test_final_sampler_failure_is_unavailable_not_zero_and_cleanup_runs(self):
  r=self.runfake('sampling');self.assertFalse(r['final_resources']['available']);self.assertNotIn('free_C_bytes',r['final_resources']);self.assertIn('unavailable',r['final_resources']['reason'])
 def test_final_valid_snapshot_preserves_original_failure(self):
  r=self.runfake('valid');self.assertTrue(r['final_resources']['available']);self.assertEqual(r['final_resources']['evidence_cap'],60000000);self.assertEqual(r['final_resources']['runtime_floor'],19394461696)
if __name__=='__main__':unittest.main(verbosity=2)
