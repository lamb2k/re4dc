"""Source-state engine tests only; fake actions, no native input/process."""
import copy,importlib.util,pathlib,unittest
p=pathlib.Path(__file__).parent
s=importlib.util.spec_from_file_location('controller',p/'controller-core.py');c=importlib.util.module_from_spec(s);s.loader.exec_module(c)
s=importlib.util.spec_from_file_location('transport',p/'observe.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
def row(frame=10,rounds=10,shots=0):return {'valid':True,'coherent':True,'qa_flags':0,'global':{'frame':frame,'room':0x103,'player_life':1200,'rno':[3,0,0,0],'stop':0,'status':[0,0,0,0]},'player':{'ptr':0x8c900000,'rno':[0,0,1,1],'alive':1,'pos':[-47609,57,7084],'ang':[0,1.889,0],'dmgType_bits':0},'event_start_cnt':0,'subscreen_type':0,'ssloop':0,'debug_flags':[0,0,0],'weapon':{'valid_inventory_slot':True,'item_class':1,'weapon_source_match':True,'id':1,'equipped_id':1,'slot':0x8cb00000,'weapon_no':1,'loaded_rounds':rounds},'counters':{'g_shot_cnt':shots,'c_shot_cnt':shots,'g_hit_cnt':0,'g_kill_cnt':0},'manager_valid':True,'actors':[]}
class Controller(unittest.TestCase):
 def aim(self,engine):
  actions=[]
  for i in range(4):actions+=engine.step(row(10+i),0,i*.05)
  return actions
 def test_ordinary_two_actual_discharge_windows(self):
  e=c.Shooting();actions=self.aim(e);self.assertEqual(actions[0]['down'],'rtrig')
  self.assertEqual(e.step(row(15),0,.56)[0]['down'],'a');self.assertEqual(e.step(row(16),0,.72)[0]['up'],'a')
  a=e.step(row(20,9,1),0,1.38);self.assertTrue(next(x['proof'] for x in a if 'proof'in x)['accepted'])
  for i in range(4):a=e.step(row(21+i,9,1),0,1.4+i*.05)
  e.step(row(26,9,1),0,1.96);e.step(row(27,8,2),0,2.12);e.step(row(30,8,2),0,2.8)
  self.assertTrue(e.done);self.assertEqual([x['rounds'] for x in e.shots],[1,1]);self.assertEqual(e.stage,'complete')
 def test_no_ammo_or_counter_proof_from_pulse(self):
  a=c.policy.discharge(row(),row(12));self.assertFalse(a['accepted']);self.assertEqual(a['rounds'],0)
 def test_missing_coherence_never_accepted_zero(self):
  for key in ['valid','coherent']:
   r=row();del r[key];self.assertFalse(c.policy.valid_sample(r));self.assertFalse(c.policy.discharge(r,row(12,9,1))['accepted'])
 def test_stale_after_aim_releases_and_never_restarts(self):
  e=c.Shooting();self.aim(e);a=e.step(row(15),.201,.2);self.assertTrue(e.done);self.assertEqual(a[0]['up'],'rtrig');self.assertEqual(e.step(row(16),0,.3),[])
 def test_event_or_room_after_aim_ends_attempt(self):
  for change in ['event','room','qa']:
   e=c.Shooting();self.aim(e);r=row(15)
   if change=='event':r['event_start_cnt']=1
   elif change=='room':r['global']['room']=0x101
   else:r['qa_flags']=None
   a=e.step(r,0,.2);self.assertTrue(e.done);self.assertTrue(a)
 def test_infinite_special_bad_slot_unavailable_ammo_withheld(self):
  for field,value in [('loaded_rounds',None),('id',0x52),('valid_inventory_slot',False),('weapon_source_match',None)]:
   r=row();r['weapon'][field]=value;self.assertFalse(c.policy.ordinary_weapon_ready(r))
  r=row();r['debug_flags'][2]=0x400000;self.assertFalse(c.policy.ordinary_weapon_ready(r))
 def test_nonfinite_position_or_angle_withholds_input(self):
  for name in ['pos','ang']:
   r=row();r['player'][name][0]=float('nan');self.assertFalse(c.policy.valid_sample(r))
 def test_input_cutoff_releases_all(self):
  e=c.Shooting();self.aim(e);self.assertEqual(e.step(row(15),0,40.75)[0]['up'],'rtrig');self.assertTrue(e.done)
 def test_manual_B_only_two_no_gameplay_mash(self):
  e=c.Cinematic();r=row();r['global']['room']=0x101;r['subscreen_type']=64;r['ssloop']=1
  self.assertEqual(e.step(r,0,1),[]);self.assertEqual(e.step(r,0,1,True)[0]['down'],'b');self.assertEqual(e.step(r,0,1.16,True)[0]['up'],'b')
  self.assertEqual(e.step(r,0,2.2,True)[0]['down'],'b');e.step(r,0,2.36,True);self.assertEqual(e.step(r,0,4,True),[])
 def test_manual_context_end_releases_immediately(self):
  e=c.Cinematic();r=row();r['global']['room']=0x101;r['subscreen_type']=64;r['ssloop']=1;e.step(r,0,1,True);r['subscreen_type']=0;self.assertEqual(e.step(r,0,1.01,True)[0]['up'],'b')
 def test_catch_needs_reciprocal_exact_actor_identity(self):
  e=c.Cinematic();r=row();r['player']['dmgType_bits']=0x8cb00000;r['actors']=[{'ptr':0x8cb00000,'serial':2,'id':0x15,'type':4,'rno':[1,0x30,0,0],'dmgType_bits':r['player']['ptr']}]
  a=e.step(r,0,1);self.assertEqual(a[0]['actor_identity']['serial'],2);self.assertNotIn('down',a[0]);self.assertEqual(e.step(r,0,1.1),[])
 def test_bad_manager_disallows_actor_witness(self):
  e=c.Cinematic();r=row();r['manager_valid']=False;r['actors']=[{}];self.assertEqual(e.step(r,0,1),[])
 def test_death_demo_requires_sourcebit_and_native_log_not_Rno4(self):
  e=c.Cinematic();r=row();r['global']['rno'][0]=4;self.assertEqual(e.step(r,0,1),[]);r['global']['rno'][0]=3;r['global']['status'][0]=0x100000;self.assertEqual(e.step(r,0,1),[]);r['death_demo_log_observed']=True;self.assertEqual(e.step(r,0,1)[0]['capture'],'death-demo-start')
 def test_door_ordinary_transition_ends_navigation(self):
  e=c.Door();a=e.step(row(),0,1);self.assertIn(a[0]['down'],['turnleft','turnright','fwd','a']);r=row();r['global']['room']=0x101;a=e.step(r,0,1.01);self.assertTrue(e.done);self.assertIn('up',a[0])
 def test_bulk_source_frame_pointer_coherence(self):
  self.assertTrue(o.coherent_frames(10,10,10,True));self.assertFalse(o.coherent_frames(10,11,11,True));self.assertFalse(o.coherent_frames(10,10,10,False))
if __name__=='__main__':unittest.main(verbosity=2)
