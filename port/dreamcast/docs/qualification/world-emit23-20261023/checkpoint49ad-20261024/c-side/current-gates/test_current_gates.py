"""Pure host controls only: imports never stage/build/open a guest."""
import copy,importlib.util,json,pathlib,unittest
spec=importlib.util.spec_from_file_location('current_gates',pathlib.Path(__file__).with_name('current_gates.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
RUN={'status':'RUN_COMPLETE','errors':[],'stopped':'goal'}
BOUND={'guest_exited':True,'deadline_fired':False,'deadline_seconds':55}
def identity(x):return {'size':len(x),'sha256':m.hashlib.sha256(x.encode()).hexdigest()}
def sample_manifest():
 return {'1ST_READ.BIN':identity('old'),'dc/st1_0.ovl':identity('oldovl'),'dc/native/r101/world.pak':identity('private-test'),'snd/aica.dat':identity('synth')}
class Controls(unittest.TestCase):
 def test_all_four_exact_arm_profiles(self):
  for arm in m.ARMS:
   for profile in ['p','g','c','t','m']:
    m.validate_knobs(m.expected(arm,profile),arm,profile)
  m.validate_knobs(m.expected('R','n'),'R','n')
 def test_each_current_recipe_required_knob_missing_or_changed_rejected(self):
  for key in m.expected('B','c'):
   for value in [None,'wrong']:
    actual=m.expected('B','c')
    if value is None:actual.pop(key)
    else:actual[key]=value
    with self.assertRaises(m.Refused):m.validate_knobs(actual,'B','c')
 def test_old_audit_off_profile_cannot_pass(self):
  actual=m.expected('B','g')
  for key in ['ESP_POOL_RECYCLE','R117_EFFECT_FAILURE_SAFE','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD']:actual[key]='0'
  with self.assertRaises(m.Refused):m.validate_knobs(actual,'B','g')
 def test_diagnostic_profiles_not_substitutable(self):
  for wrong in ['g','t','m','n']:
   with self.assertRaises(m.Refused):m.validate_knobs(m.expected('R',wrong),'R','c')
 def test_duplicate_knobs_rejected(self):
  with self.assertRaises(m.Refused):m.knobs('KOS_WATCH=0\nKOS_WATCH=1\n')
 def test_programme_paths_exact_no_past_prefix(self):
  self.assertEqual(m.output('B','t').as_posix(),'/root/probe/lanes/route/out-we23B49adrT');self.assertEqual(m.output('L','g').as_posix(),'/root/probe/lanes/route/out-fpwe23L49adgW')
  with self.assertRaises(m.Refused):m.output('L','n')
 def test_manifest_asset_hash_ignores_only_programmes_and_fixtures(self):
  old=sample_manifest();new=copy.deepcopy(old);new['1ST_READ.BIN']=identity('new');new['dc/st1_0.ovl']=identity('newovl');new['dc/warp.txt']=identity('fixture');self.assertEqual(m.asset_hash(old),m.asset_hash(new));new['snd/aica.dat']=identity('changed');self.assertNotEqual(m.asset_hash(old),m.asset_hash(new))
 def test_manifest_escape_invalid_hash_and_duplicate_forms_rejected(self):
  for key in ['../secret','dc/../secret','/root/secret']:
   with self.assertRaises(m.Refused):m.assets({key:identity('x')})
  with self.assertRaises(m.Refused):m.assets({'a':{'size':1,'sha256':'bad'}})
 def test_staged_programmes_exact_and_assets_equal(self):
  baseline=sample_manifest();stage=copy.deepcopy(baseline);stage['1ST_READ.BIN']=identity('new');stage['dc/st1_0.ovl']=identity('newovl');prg={'main':identity('new'),'overlays':{'st1_0.ovl':identity('newovl')}};m.validate_stage_manifest(stage,baseline,prg)
  for key in ['1ST_READ.BIN','dc/st1_0.ovl','snd/aica.dat']:
   bad=copy.deepcopy(stage);bad[key]=identity('wrong')
   with self.assertRaises(m.Refused):m.validate_stage_manifest(bad,baseline,prg)
  stage['dc/extra.ovl']=identity('extra')
  with self.assertRaises(m.Refused):m.validate_stage_manifest(stage,baseline,prg)
 def test_h2_full_bound_movie_arena_and_heap(self):
  text='MOVIEARENA borrow id=10030 token=3 gen=1\nMOVIEARENA return token=3 used=1 restored=1\nroute movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340 heap_before=93920\n'
  self.assertTrue(m.gate_evidence('h2',text,RUN,BOUND)['pass'])
  for bad in [text.replace('340/340','339/340'),text.replace('heap_before=93920','heap_before=0'),text.replace('return token=3','return token=4'),text.replace('restored=1','restored=0'),text.replace('presented=340','presented=339')]:self.assertFalse(m.gate_evidence('h2',bad,RUN,BOUND)['pass'])
 def test_bounded_failure_or_missing_is_not_pass(self):
  text='route movie terminal=1 id=10130'
  self.assertTrue(m.gate_evidence('bell',text,RUN,BOUND)['pass'])
  for bad in [dict(BOUND,deadline_fired=True),dict(BOUND,guest_exited=False),dict(BOUND,deadline_seconds=70),{}]:self.assertFalse(m.gate_evidence('bell',text,RUN,bad)['pass'])
  for bad in [dict(RUN,errors=['x']),dict(RUN,status='FAIL'),dict(RUN,stopped='time')]:self.assertFalse(m.gate_evidence('bell',text,bad,BOUND)['pass'])
 def test_kos_both_exact48k_arms_and_headroom(self):
  for frag in ['0','1']:
   text='kos squeeze: held=49152 requested=49152 frag='+frag+' pieces=1\nkos watch: headroom=4096\nwarp: alert at room frame 30\n';self.assertTrue(m.gate_evidence('kos'+frag,text,RUN,BOUND)['pass'])
   for bad in [text.replace('headroom=4096','headroom=4095'),text.replace('held=49152','held=32768'),text.replace('warp: alert','warp: pending'),text.replace('frag='+frag,'frag='+str(1-int(frag)))]:self.assertFalse(m.gate_evidence('kos'+frag,bad,RUN,BOUND)['pass'])
 def test_gdemu_requires_actual_profile_and_door_and_zero_bad_reads(self):
  good='phase=enter room=103';self.assertTrue(m.gate_evidence('gd1',good,RUN,BOUND,{'gdemu_profile_observed':True})['pass'])
  for text,extra in [(good,{}),('',{'gdemu_profile_observed':True}),(good+'\nBAD-READ',{'gdemu_profile_observed':True})]:self.assertFalse(m.gate_evidence('gd1',text,RUN,BOUND,extra)['pass'])
 def test_bench_requires_live_census_texture_cast_leon_memory_and_room(self):
  checks={k:{'rc':0} for k in ['castgc','leongc','texchk']};text='warp: room enter 101\nNMRS f=150 room=101 id=12 native=1 crowd=0\nwarp: alivelist room 101 frame 150 ids 12*4@100/v4\nroom lifecycle: phase=enter room=101\nnative UI VRAM: free=100000 rejects=0 retries=0 evicted=0\n'
  self.assertTrue(m.gate_evidence('bench101',text,RUN,BOUND,{'checks':checks})['pass'])
  for item in ['warp: room enter','NMRS','warp: alivelist','room lifecycle:','native UI VRAM:']:
   bad='\n'.join(line for line in text.splitlines() if not line.startswith(item));self.assertFalse(m.gate_evidence('bench101',bad,RUN,BOUND,{'checks':checks})['pass'])
  for key in checks:
   bad=copy.deepcopy(checks);bad[key]['rc']=2;self.assertFalse(m.gate_evidence('bench101',text,RUN,BOUND,{'checks':bad})['pass'])
 def test_critical_lines_fail_even_with_event_goal(self):
  for line in ['HALT','FAULT','RE4DC MISSING','Out of memory','[LOG OVERRUN','no contiguous','native UI: upload FAILED','native UI: package rejected']:
   self.assertFalse(m.gate_evidence('bell','route movie terminal=1 id=10130\n'+line,RUN,BOUND)['pass'])
 def test_mendez_full_movies_two_explicit_diagnostic_kills_and_room(self):
  text='\n'.join('route movie terminal=1 id='+id+' frames='+str(n)+'/'+str(n) for id,n in [('11f02',1067),('11f10',265),('11f11',321)])+'\nwarp: kill 0x35 hp<=0\nwarp: kill 0x35 hp<=0\nphase=enter room=10f';self.assertTrue(m.gate_evidence('mendez',text,RUN,BOUND)['pass'])
  for bad in [text.replace('321/321','320/321'),text.replace('phase=enter room=10f','phase=enter room=11f'),text.replace('warp: kill 0x35 hp<=0','',1)]:self.assertFalse(m.gate_evidence('mendez',bad,RUN,BOUND)['pass'])
  self.assertFalse(m.gate_evidence('mendez',text,RUN,BOUND,{'decision_comparison':{'rc':1}})['pass'])
 def test_vram_refusal_retry_eviction_and_heap_corruption_are_not_pass(self):
  checks={k:{'rc':0} for k in ['castgc','leongc','texchk']};text='warp: room enter 100\nNMRS f=150 room=100 id=12 native=1 crowd=0\nwarp: alivelist room 100 frame 150 ids 12*1@100/v1\nroom lifecycle: phase=enter room=100\nnative UI VRAM: rejects=0 retries=0 evicted=0\n'
  self.assertTrue(m.gate_evidence('bench100',text,RUN,BOUND,{'checks':checks})['pass'])
  for bad in [text.replace('rejects=0','rejects=1'),text.replace('retries=0','retries=1'),text.replace('evicted=0','evicted=1'),text+'heap_check=bad']:
   self.assertFalse(m.gate_evidence('bench100',bad,RUN,BOUND,{'checks':checks})['pass'])
 def test_pruned_old_capture_requires_recorded_actual_base_and_track_sha(self):
  base='C:/owned/old-base';h='a'*64;run={'disc':base,'tracks':{'base':base,'track03_sha256':h}}
  self.assertTrue(m.recorded_track_matches(run,base,h))
  for bad in [dict(run,disc='C:/other'),dict(run,tracks={}),dict(run,tracks={'base':base,'track03_sha256':'b'*64}),dict(run,tracks={'base':'C:/other','track03_sha256':h})]:self.assertFalse(m.recorded_track_matches(bad,base,h))
if __name__=='__main__':unittest.main(verbosity=2)
