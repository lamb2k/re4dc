"""Exact c57 ABI synthetic RAM tests; no process/emulator or memory mutation API."""
import importlib.util,json,pathlib,struct,unittest
P=pathlib.Path(__file__).parent;O=P.parent/'qa21_nontrace_plan'
spec=importlib.util.spec_from_file_location('adapter',P/'observer-v2.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class InlineMotion(unittest.TestCase):
 def setUp(self):
  self.layout=json.loads((O/'reader-c57-on-layout.json').read_text());self.sy=json.loads((O/'reader-c57-on-binding.json').read_text())['symbols'];self.source=json.loads((P/'source-contract-v2.json').read_text());self.mem=bytearray(16*1024*1024);self.forbid=None
  self.r=a.Reader(self.raw,self.sy,self.layout,self.layout['elf_sha256'],source_contract=self.source,expected_source=self.source['source']);self.g=0x8c800000;self.pl=0x8c900000;self.motdata=0x8c700000
 def raw(self,p,n):
  if self.forbid and max(p,self.forbid[0])<min(p+n,self.forbid[1]):raise AssertionError('pMot DATA dereferenced as MotionWork')
  return bytes(self.mem[p-0x8c000000:p-0x8c000000+n])
 def put(self,p,fmt,*v):struct.pack_into('<'+fmt,self.mem,p-0x8c000000,*v)
 def field(self,p,t,n,f,*v):self.put(p+self.r.off(t,n),f,*v)
 def scene(self,pmot=None):
  self.put(self.sy['_pG'],'I',self.g);self.put(self.sy['_pPL'],'I',self.pl);self.field(self.g,'GlobalWork','Frame_cnt','I',1234);self.field(self.g,'GlobalWork','pl_life','H',1200);self.field(self.pl,'cPlayer','be_flag','I',1)
  motion=self.pl+self.r.off('cPlayer','Motion');self.field(motion,'MotionWork','pMot','I',self.motdata if pmot is None else pmot);self.field(motion,'MotionWork','Mot_frame','f',71.9);self.field(motion,'MotionWork','Seq_frame','f',17.9);return motion
 def test_inline_exact_offset_size_and_anon_provenance(self):
  m=a._contract.member(self.layout,'cPlayer','Motion');self.assertEqual((m['offset'],m['bytes'],m['type']),(472,220,'MotionWork'));self.assertTrue(any(v['name']=='@anonymous' for v in m['route']))
 def test_adversarial_const_pMot_data_not_work(self):
  self.scene();self.put(self.motdata+36,'f',999);self.put(self.motdata+184,'f',888);self.forbid=(self.motdata,self.motdata+220);row=self.r.snapshot();self.assertEqual(row['motion']['pMot'],self.motdata);self.assertAlmostEqual(row['motion']['Seq_frame'],17.9,4);self.assertAlmostEqual(row['motion']['Mot_frame'],71.9,4)
 def test_null_pMot_still_valid_inline_work(self):
  self.scene(0);row=self.r.snapshot();self.assertEqual(row['motion']['pMot'],0);self.assertAlmostEqual(row['motion']['Seq_frame'],17.9,4)
 def test_code_const_pointer_never_dereferenced(self):
  self.scene(0x8c010000);self.forbid=(0x8c010000,0x8c010000+220);self.assertEqual(self.r.snapshot()['motion']['pMot'],0x8c010000)
 def test_startup_missing_is_unavailable(self):
  row=self.r.snapshot();self.assertFalse(row['valid']);self.assertNotIn('global',row);self.assertIsNone(row['qa_flags'])
 def test_startup_junk_and_boundary_pointer_are_unavailable(self):
  for value in (1,0xffffffff,0x8cffffff):
   self.put(self.sy['_pG'],'I',value);self.put(self.sy['_pPL'],'I',self.pl);self.assertFalse(self.r.snapshot()['valid'])
 def test_changed_source_frame_rejects_coherence(self):
  self.scene();addr=self.g+self.r.off('GlobalWork','Frame_cnt');raw=self.r.raw;seen=[]
  def reads(p,n):
   if p==addr:
    seen.append(1)
    if len(seen)>1:self.put(addr,'I',1235)
   return raw(p,n)
  self.r.raw=reads;self.assertFalse(self.r.snapshot()['coherent'])
 def test_actor_inline_and_signed_HP(self):
  ptr=0x8cb00000;motion=ptr+self.r.off('cEm','Motion');self.field(motion,'MotionWork','pMot','I',self.motdata);self.field(motion,'MotionWork','Seq_frame','f',22);self.field(ptr,'cEm','hp','h',-2);self.forbid=(self.motdata,self.motdata+220);row=self.r.actor(ptr);self.assertEqual(row['hp'],-2);self.assertEqual(row['motion']['Seq_frame'],22);self.assertIsNone(row['em10'])
 def test_cycle_or_outside_pool_is_not_valid_lifecycle(self):
  mgr=self.sy['_EmMgr'];pool=0x8cb00000;stride=self.layout['found']['cEm']['bytes']
  for n,v in [('pArray',pool),('nArray',2),('size',stride),('pAlive',pool)]:self.field(mgr,'cEmMgr',n,'I',v)
  self.field(pool,'cEm','id','B',0x15);self.field(pool,'cEm','pNext','I',pool);self.assertFalse(self.r.actor_chain()['manager_valid'])
if __name__=='__main__':unittest.main(verbosity=2)
