"""Only bounded Door candidate/seed contracts; no process, live RAM, input or guest."""
import copy,hashlib,importlib.util,json,math,pathlib,unittest
P=pathlib.Path(__file__).parent;V=P.parent.parent/'qa21_nontrace_guest_telemetry_v1'
def load(n,f):
 s=importlib.util.spec_from_file_location(n,f);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
candidate=load('door_candidate',P/'controller-candidate.py');original=load('door_original',V/'controller-core.py');outer=load('door_plan_outer',V/'outer-driver.py');inner=load('door_plan_inner',V/'inner-adapter.py');d=load('door_plan_deadlines',V/'input-deadlines.py')
class Timer:
 def __init__(self,delay,fn):self.delay=delay
 def start(self):pass
 def cancel(self):pass
 def join(self,timeout=None):pass
 def is_alive(self):return False
class DoorPlan(unittest.TestCase):
 def setUp(self):self.seed=json.loads((P/'seed-contract.json').read_text());self.row=self.seed['rich_snapshot'];self.profile=json.loads((V/'guest-profile-v2.json').read_text())
 def contact(self):
  row=copy.deepcopy(self.row);row['player']['pos']=[-49000.,0.,7670.];row['player']['ang']=[0.,-math.pi/2,0.];return row
 def test_exact_candidate_is_only_point2_to_point15_contact_hold(self):
  source=(V/'controller-core.py').read_bytes();self.assertEqual((P/'controller-candidate.py').read_bytes(),source.replace(b"key='a';hold=.2;self.attempts+=1",b"key='a';hold=.15;self.attempts+=1"));self.assertEqual((P/'policies.py').read_bytes(),(V/'policies.py').read_bytes())
 def test_reproduces_original_role_bound_gap_without_executing_input(self):
  e=original.Door();self.assertEqual(e.step(self.contact(),0,0)[0]['down'],'a');self.assertEqual(e.pending_hold,.2);self.assertGreater(e.pending_hold,.15)
 def test_candidate_contact_bound_feeds_existing_inputlease_and_releases(self):
  e=candidate.Door();self.assertEqual(e.step(self.contact(),0,0)[0]['down'],'a');self.assertEqual(e.pending_hold,.15);now=[0.];posts=[];fail=[];inputs=d.Inputs(lambda k,u:posts.append((k,u,now[0])),lambda:now[0],fail.append,clock=lambda:now[0],timer=Timer)
  try:
   inputs.down('a',e.pending_hold);now[0]=.13;inputs.expire('a',inputs.held['a']);self.assertFalse(inputs.keys());self.assertEqual(posts[-1],('a',True,.13));self.assertFalse(fail)
  finally:inputs.close()
 def test_actual_seed_offline_freeplay_and_firstaction_match(self):
  self.assertTrue(candidate.policy.free_play(self.row));self.assertEqual(self.row['global']['frame'],533);self.assertEqual(self.row['global']['room'],0x103);self.assertEqual(self.row['global']['player_life'],1200);self.assertEqual(self.row['qa_flags'],0);self.assertIsNone(self.row['transport_coherent']);old=original.Door();new=candidate.Door();self.assertEqual(old.step(self.row,0,0),new.step(self.row,0,0));self.assertEqual(new.pending_hold,.65)
 def test_existing_parser_and_exact_profile_qualified_parent_contract(self):
  profile=V/'guest-profile-v2.json';self.assertEqual(hashlib.sha256(profile.read_bytes()).hexdigest(),'4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b');seed=pathlib.Path(self.seed['seed']);a=outer.parse_args(['--profile',str(profile),'--profile-sha256','4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b','--tools-sha256','not-a-launch-seal','--mode','return-door01','--seed',str(seed)]);inner.validate_role(self.profile,a.mode,a.seed)
  # Source-only Windows path semantics are tested live by the plan driver; no main is called.
  self.assertEqual(a.mode,'return-door01');self.assertEqual(a.seed,seed)
 def test_stale_qa_ui_event_death_all_withhold_or_release(self):
  rows=[]
  for key,val in [('qa_flags',1),('subscreen_type',64),('event_start_cnt',1)]:
   row=copy.deepcopy(self.row);row[key]=val;rows.append((row,0))
  dead=copy.deepcopy(self.row);dead['global']['player_life']=0;rows.append((dead,0));rows.append((copy.deepcopy(self.row),.201))
  for row,age in rows:
   e=candidate.Door();e.held={'turnleft'};out=e.step(row,age,0);self.assertFalse(any('down' in x for x in out));self.assertFalse(e.held)
 def test_roomtransition_to_original_manual_stops_all_navigation(self):
  row=copy.deepcopy(self.row);row['global']['room']=0x101;row['subscreen_type']=64;row['ssloop']=1;e=candidate.Door();e.held={'fwd'};out=e.step(row,0,1);self.assertTrue(e.done);self.assertFalse(e.held);self.assertFalse(any('down' in x for x in out));self.assertEqual(e.step(row,0,2),[])
 def test_four_contact_attempts_max_then_stop(self):
  row=self.contact();e=candidate.Door();downs=0
  for n in range(6):
   out=e.step(row,0,n);downs+=sum(a.get('down')=='a' for a in out)
   e.step(row,0,n+.2)
  self.assertEqual(downs,4);self.assertTrue(e.done)
 def test_cutoff_prevents_further_navigation(self):
  e=candidate.Door();e.held={'a'};out=e.step(self.row,0,40.75);self.assertTrue(e.done);self.assertFalse(e.held);self.assertFalse(any('down' in x for x in out))
 def test_geometry_inputs_stay_within_original_bounds(self):
  for px,pz in [(-47630,7032),(-49000,7670),(-49731,7670),(-48301,6000),(-48301,9600)]:
   for yaw in [-3.,-1.5,0.,1.5,3.]:
    row=copy.deepcopy(self.row);row['player']['pos']=[float(px),0.,float(pz)];row['player']['ang']=[0.,yaw,0.];e=candidate.Door();out=e.step(row,0,0);key=out[0]['down'];self.assertGreater(e.pending_hold,0);self.assertLessEqual(e.pending_hold,.15 if key=='a' else .65)
if __name__=='__main__':unittest.main(verbosity=2)
