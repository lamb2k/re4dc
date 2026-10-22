"""Synthetic host RAM under exact c57 ELF ABI, never an emulator capture/state."""
import copy,hashlib,importlib.util,json,pathlib,struct,unittest
from policies import shooting_safe,ordinary_weapon_ready,qa_safe,discharge
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('adapter',P/'observer-adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ExactFixture(unittest.TestCase):
 def setUp(self):
  self.layout=json.loads((P/'reader-c57-on-layout.json').read_text());self.binding=json.loads((P/'reader-c57-on-binding.json').read_text());self.source=json.loads((P/'reader-c57-source-contract.json').read_text());self.expected=json.loads((P/'reader-c57-on-expected.json').read_text())
  self.symbols=self.binding['symbols'];self.mem=bytearray(16*1024*1024)
  self.r=a.Reader(self.raw,self.symbols,self.layout,self.expected['elf_sha256'],source_contract=self.source,expected_source=self.expected['source'])
  self.g=0x8c800000;self.pl=0x8c900000;self.arm=0x8ca00000;self.actor=0x8cb00000;self.motion=0x8cc00000;self.body=0x8cc01000;self.system=0x8cc02000
 def raw(self,ptr,size):return bytes(self.mem[ptr-0x8c000000:ptr-0x8c000000+size])
 def put(self,ptr,fmt,*values):struct.pack_into('<'+fmt,self.mem,ptr-0x8c000000,*values)
 def field(self,ptr,typ,name,fmt,*values):self.put(ptr+self.r.off(typ,name),fmt,*values)
 def scene(self):
  for sym,value in [('_pG',self.g),('_pPL',self.pl),('_pSys',self.system)]:self.put(self.symbols[sym],'I',value)
  for n,f,v in [('Frame_cnt','I',[2000]),('pl_life','H',[1200]),('room_id','H',[0x103]),('Rno0','4B',[3,0,0,0]),('weapon_no','B',[2]),('g_shot_cnt','I',[5]),('c_shot_cnt','I',[5])]:self.field(self.g,'GlobalWork',n,f,*v)
  for n,f,v in [('be_flag','I',[1]),('serial','I',[123]),('pos','3f',[1.5,2.5,3.5]),('pMotion','I',[self.motion]),('Body','I',[self.body])]:self.field(self.pl,'cPlayer',n,f,*v)
  for n,f,v in [('pArm','I',[self.arm]),('pItems','I',[self.arm]),('nItems','i',[2]),('m_wep_id','H',[0x23])]:self.field(self.symbols['_ItemMgr'],'cItemMgr',n,f,*v)
  for n,f,v in [('id','H',[0x23]),('bullet','H',[10]),('flags','B',[1])]:self.field(self.arm,'ItemWork',n,f,*v)
  self.field(self.symbols['_Key'],'KeyWork','on','Q',0x100000080)
  self.field(self.motion,'MotionWork','Seq_frame','f',17.9);self.field(self.motion,'MotionWork','Mot_frame','f',71.9)
  self.field(self.system,'SystemWork','region','B',1)
 def test_exact_members_and_anonymous_routes(self):
  self.assertEqual(self.r.abi['field_count'],65)
  r=[v for v in self.r.abi['fields'] if v['structure']=='cPlayer' and v['requested']=='r_no_0'][0]
  self.assertEqual(r['path'],'cEm.cModel.r_no_0');self.assertGreater(len(r['route']),2)
 def test_scene_ammo_and_discharge(self):
  self.scene();before=self.r.snapshot();self.assertTrue(ordinary_weapon_ready(before));self.assertEqual(before['keys']['on'],0x100000080)
  self.assertAlmostEqual(before['motion']['Seq_frame'],17.9,places=4);self.assertAlmostEqual(before['motion']['Mot_frame'],71.9,places=4)
  self.field(self.arm,'ItemWork','bullet','H',9);self.field(self.g,'GlobalWork','Frame_cnt','I',2020)
  for n in ('g_shot_cnt','c_shot_cnt'):self.field(self.g,'GlobalWork',n,'I',6)
  result=discharge(before,self.r.snapshot());self.assertTrue(result['accepted']);self.assertEqual(result['rounds'],1)
 def test_missing_trace_and_qa_unavailable(self):
  self.scene();sy={n:v for n,v in self.symbols.items() if n not in a.OPTIONAL_QA};self.r=a.Reader(self.raw,sy,self.layout,self.expected['elf_sha256'],source_contract=self.source,expected_source=self.expected['source']);row=self.r.snapshot()
  self.assertIsNone(row['qa_frames']);self.assertIsNone(row['qa_flags']);self.assertFalse(qa_safe(row));self.assertTrue(ordinary_weapon_ready(row));self.assertTrue(all(v is None for v in row['diagnostics'].values()))
 def test_signed_hp_and_pointer_bits_and_integer_timers(self):
  self.field(self.actor,'cEm','hp','h',-3);self.field(self.actor,'cEm','dmgType','i',self.pl-0x100000000);self.field(self.actor,'cEm','serial','I',91)
  wk=self.actor+self.r.off('cEm','x3E0')
  self.field(wk,'Em10Work','Timer','i',19);self.field(wk,'Em10Work','Timer2','i',41);self.field(wk,'Em10Work','Fire_timer','i',-4)
  row=self.r.actor(self.actor,True);self.assertEqual(row['hp'],-3);self.assertEqual(row['dmgType_bits'],self.pl);self.assertEqual(row['em10']['Timer'],19);self.assertEqual(row['em10']['Fire_timer'],-4)
 def test_unsafe_scene_slot_and_class_cannot_discharge(self):
  self.scene();self.field(self.g,'GlobalWork','Stop_flg','I',0x80400000);self.assertFalse(ordinary_weapon_ready(self.r.snapshot()))
  self.field(self.g,'GlobalWork','Stop_flg','I',0);self.field(self.arm,'ItemWork','flags','B',0);row=self.r.snapshot();self.assertFalse(ordinary_weapon_ready(row));self.assertFalse(discharge(row,row)['accepted'])
  self.field(self.arm,'ItemWork','flags','B',1);self.field(self.arm,'ItemWork','id','H',1);row=self.r.snapshot();self.assertIsNone(row['weapon']['item_class']);self.assertFalse(ordinary_weapon_ready(row))
 def test_exact_classification_attribute_and_no_source_guess(self):
  self.scene();self.field(self.arm,'ItemWork','bullet','H',0xe00a);row=self.r.snapshot();self.assertFalse(row['weapon']['weapon_source_match']);self.assertFalse(ordinary_weapon_ready(row))
  with self.assertRaises(ValueError):a.Reader(self.raw,self.symbols,self.layout,self.expected['elf_sha256'])
 def test_tampered_type_size_anonymous_component_rejected(self):
  for change in ('size','encoding','vector'):
   layout=copy.deepcopy(self.layout)
   m=a._contract.member(layout,'cEm','hp')
   if change=='size':m['bytes']=4
   elif change=='encoding':m['encoding']=7
   else:a._contract.member(layout,'cPlayer','pos')['aggregate_members'][0]['offset']=4
   with self.assertRaises(ValueError):a._contract.validate_layout(layout)
 def test_duplicate_symbols_ambiguous_optional_unavailable(self):
  groups={n:[dict(address=v,bytes=4,type='STT_OBJECT')] for n,v in self.symbols.items() if v is not None}
  groups['_Key'].append(dict(groups['_Key'][0]));self.assertIn('_Key',a.resolve_symbol_groups(groups))
  groups['_Key'][1]['address']+=4
  with self.assertRaises(ValueError):a.select_symbols(a.resolve_symbol_groups(groups))
  groups['_Key'].pop();n=a.OPTIONAL_QA[0];groups[n].append(dict(address=0x8c123456,bytes=4,type='STT_OBJECT'));self.assertIsNone(a.select_symbols(a.resolve_symbol_groups(groups))[n])
 def test_nonatomic_event_unknown_initial_withholds(self):
  self.assertFalse(self.r.snapshot()['valid']);self.scene();frameaddr=self.g+self.r.off('GlobalWork','Frame_cnt');oldraw=self.r.raw;seen=[0]
  def changing(ptr,size):
   if ptr==frameaddr:
    seen[0]+=1
    if seen[0]>1:self.put(frameaddr,'I',2001)
   return oldraw(ptr,size)
  self.r.raw=changing;row=self.r.snapshot();self.assertFalse(row['coherent']);self.assertFalse(shooting_safe(row))
if __name__=='__main__':unittest.main(verbosity=2)
