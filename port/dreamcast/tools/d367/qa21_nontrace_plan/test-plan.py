"""Host-only regression tests for qualification gates/read-only metadata adapter."""
import copy,importlib.util,json,pathlib,struct,unittest
from policies import valid_sample,free_play,shooting_safe,qa_safe,discharge
P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('adapter',P/'observer-adapter.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Gates(unittest.TestCase):
 def setUp(self):
  self.row={'global':{'player_life':1200,'frame':10,'room':0x103,'rno':[3,0,0,0],'stop':0,'status':[0]*4},'player':{'ptr':0x8c100000,'pos':[0]*3,'rno':[0]*4,'alive':1},'event_start_cnt':0,'subscreen_type':0,'ssloop':0,'qa_frames':None,'qa_flags':None,'coherent':True}
 def test_initial_missing_is_not_death_or_freeplay(self):
  self.assertFalse(valid_sample({}));self.assertFalse(free_play({}));self.assertFalse(shooting_safe({}))
 def test_absent_qa_does_not_block_ordinary_shooting(self):
  self.assertTrue(shooting_safe(self.row));self.assertFalse(qa_safe(self.row))
 def test_event_and_source_masks_withhold_shooting(self):
  for field,value in [('stop',0x80400000),('player_life',0),('rno',[4,0,0,0])]:
   r=copy.deepcopy(self.row);r['global'][field]=value;self.assertFalse(shooting_safe(r))
  for index,mask in [(0,0x200000),(2,0x80000000)]:
   r=copy.deepcopy(self.row);r['global']['status'][index]=mask;self.assertFalse(shooting_safe(r))
  self.row['coherent']=False;self.assertFalse(shooting_safe(self.row))
 def fixture(self):
  return {'room':0x103,'frame':100,'weapon':{'slot':12,'id':1,'equipped_id':1,'weapon_no':2,'loaded_rounds':10},'debug_flags':[0]*4,'counters':{'g_shot_cnt':3,'c_shot_cnt':3,'g_hit_cnt':1,'g_kill_cnt':0}}
 def test_discharge_needs_ammo_and_both_counters(self):
  b=self.fixture();e=copy.deepcopy(b);e['frame']+=30;e['weapon']['loaded_rounds']-=1;e['counters']['g_shot_cnt']+=1;e['counters']['c_shot_cnt']+=1
  self.assertTrue(discharge(b,e)['accepted'])
  e['weapon']['loaded_rounds']+=1;self.assertFalse(discharge(b,e)['accepted'])
 def test_adapter_nested_global_discharge(self):
  b=self.fixture();e=copy.deepcopy(b);e['frame']+=30;e['weapon']['loaded_rounds']-=1
  for k in ('g_shot_cnt','c_shot_cnt'):e['counters'][k]+=1
  for row in (b,e):row['global']={k:row.pop(k) for k in ('room','frame')}
  self.assertTrue(discharge(b,e)['accepted'])
 def test_missing_weapon_cannot_claim_discharge(self):
  self.assertFalse(discharge({}, {})['accepted'])
  b=self.fixture();e=copy.deepcopy(b);e['weapon']['slot']=0;self.assertFalse(discharge(b,e)['accepted'])
 def test_weapon_switch_infinite_special_and_room_rejected(self):
  for change in ('switch','infinite','special','room'):
   b=self.fixture();e=copy.deepcopy(b);e['frame']+=30;e['weapon']['loaded_rounds']-=1
   for k in ('g_shot_cnt','c_shot_cnt'):e['counters'][k]+=1
   if change=='switch':e['weapon']['slot']=13
   if change=='infinite':b['debug_flags'][2]=0x400000
   if change=='special':b['weapon']['id']=e['weapon']['id']=0x6d
   if change=='room':e['room']=0x101
   self.assertFalse(discharge(b,e)['accepted'])
class Adapter(unittest.TestCase):
 def setUp(self):
  self.layout=json.loads((P/'historical-a18-on-layout.json').read_text());self.sy={n:0x8c010000+i*512 for i,n in enumerate(a.REQUIRED)};self.mem=bytearray(16*1024*1024)
  self.r=a.Reader(lambda p,n:bytes(self.mem[p-0x8c000000:p-0x8c000000+n]),self.sy,self.layout,self.layout['elf_sha256'])
 def put(self,p,fmt,v):struct.pack_into('<'+fmt,self.mem,p-0x8c000000,*v)
 def field(self,b,t,n,fmt,v):self.put(b+self.r.off(t,n),fmt,v)
 def test_absent_qa_optional_missing_generic_fails(self):
  self.assertIsNone(self.r.sy[a.OPTIONAL_QA[0]])
  sy=dict(self.sy);del sy['_Key']
  with self.assertRaises(ValueError):a.select_symbols(sy)
 def test_mismatched_elf_and_outside_ram_fail(self):
  with self.assertRaises(ValueError):a.Reader(None,self.sy,self.layout,'wrong')
  with self.assertRaises(ValueError):self.r.read(0,'I')
 def test_initial_pointer_sample_invalid(self):self.assertFalse(self.r.snapshot()['valid'])
 def test_generic_snapshot_without_qa_or_trace(self):
  g=0x8c100000;pl=0x8c200000;arm=0x8c300000
  self.put(self.sy['_pG'],'I',[g]);self.put(self.sy['_pPL'],'I',[pl]);self.field(g,'GlobalWork','Frame_cnt','I',[90]);self.field(g,'GlobalWork','pl_life','H',[1200]);self.field(g,'GlobalWork','Rno0','4B',[3,0,0,0]);self.field(pl,'cPlayer','be_flag','I',[1]);self.field(self.sy['_ItemMgr'],'cItemMgr','pArm','I',[arm]);self.field(arm,'ItemWork','bullet','H',[0xe00a]);self.field(self.sy['_Key'],'KeyWork','on','Q',[0x100000080])
  s=self.r.snapshot();self.assertTrue(s['coherent']);self.assertIsNone(s['qa_frames']);self.assertTrue(shooting_safe(s));self.assertEqual(s['weapon']['loaded_rounds'],10);self.assertEqual(s['keys']['on'],0x100000080)
 def test_actor_identity_and_no_automatic_em10_read(self):
  ptr=0x8c400000;self.field(ptr,'cEm','serial','I',[77]);self.field(ptr,'cEm','r_no_0','4B',[1,0x30,1,3]);self.field(ptr,'cEm','hp','H',[3000]);r=self.r.actor(ptr)
  self.assertEqual(r['serial'],77);self.assertEqual(r['rno'],[1,48,1,3]);self.assertNotIn('em10',r)
  wk=ptr+self.r.off('cEm','x3E0');self.field(wk,'Em10Work','Timer','i',[19]);self.field(wk,'Em10Work','Fire_timer','i',[-4]);r=self.r.actor(ptr,True);self.assertEqual(r['em10']['Timer'],19);self.assertEqual(r['em10']['Fire_timer'],-4)
if __name__=='__main__':unittest.main(verbosity=2)
