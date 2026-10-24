"""Real seed1 capture mutation controls; no guests."""
import copy,importlib.util,json,unittest
from pathlib import Path
p=Path(__file__).with_name('current-d5c-gdemu10.py')
sp=importlib.util.spec_from_file_location('gd',p);g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
class Controls(unittest.TestCase):
 def test_admission(self):
  g.admission(g.S,2,g.expected(2))
  for source,env in [(g.S,{k:v for k,v in g.expected(2).items() if k!='RE4DC_GD_SEED'}),(g.S,g.expected(1)),(g.S,{**g.expected(2),'RE4DC_GD_PROFILE':'plain'}),('0'*40,g.expected(2))]:
   with self.subTest(source=source,env=env),self.assertRaises(AssertionError):g.admission(source,2,env)
 def test_actual_capture_mutations(self):
  cap=g.E/'gdemu1-console-r1'
  r=json.loads((cap/'run-result.json').read_text());b=json.loads((cap/'bounded-launch.json').read_text());s=(cap/'run-output.txt').read_text();serial=(cap/'serial.txt').read_text()
  track=r['tracks']['track03_sha256'];fixture=r['fixtures']['warp']['sha256']
  self.assertGreater(g.check_record(1,r,b,s,serial,track,fixture)['early_stat_landing_rows'],0)
  cases=[]
  x=copy.deepcopy(r);del x['emu_env']['RE4DC_GD_SEED'];cases.append(('absent-env-seed',x,b,s,serial))
  x=copy.deepcopy(r);x['emu_env']['RE4DC_GD_SEED']='2';cases.append(('wrong-env-seed',x,b,s,serial))
  x=copy.deepcopy(r);x['emu_env']['RE4DC_GD_PROFILE']='other';cases.append(('wrong-env-profile',x,b,s,serial))
  cases.append(('serial-seed',r,b,s,serial.replace('seed=1','seed=2')))
  cases.append(('profile-only-no-read',r,b,s,serial.splitlines()[0]))
  cases.append(('no-landing',r,b,s,serial.replace('landedAfterStat=','missingLanding=')))
  cases.append(('no-endpoint',r,b,s.replace('phase=enter room=103','phase=enter room=102'),serial))
  cases.append(('bad-read',r,b,s+'\nDISC READ FAILED\n',serial))
  x=copy.deepcopy(b);x['deadline_fired']=True;cases.append(('deadline',r,x,s,serial))
  for name,rr,bb,ss,tt in cases:
   with self.subTest(name=name),self.assertRaises(AssertionError):g.check_record(1,rr,bb,ss,tt,track,fixture)
if __name__=='__main__':unittest.main()

