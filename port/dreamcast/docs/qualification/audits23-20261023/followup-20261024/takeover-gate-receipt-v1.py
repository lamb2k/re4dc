#!/usr/bin/env python3
"""Bind the actual audits23 local gates; do not promote physical/causal claims."""
import hashlib,json,pathlib,re
E=pathlib.Path('C:/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0')
A=pathlib.Path('C:/Game Dev/Emulators/codex-lanes/audits23')
SOURCE='5e4de9a0262d3629c9833c959557de198b2e9f0c'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def clean(cap):
 r,b=load(cap/'run-result.json'),load(cap/'bounded-launch.json')
 assert r['status']=='RUN_COMPLETE' and not r['errors'] and not b['deadline_fired'] and b['guest_exited'],str(cap)
 s=(cap/'run-output.txt').read_text(errors='replace').replace('\0','')
 assert not re.search(r'HALT|FAULT|RE4DC MISSING|Out of memory|\[LOG OVERRUN',s),str(cap)
 return s,{'path':str(cap),'log_sha256':sha(cap/'run-output.txt'),'run_sha256':sha(cap/'run-result.json'),'bounded_sha256':sha(cap/'bounded-launch.json'),'elapsed_s':r['elapsed_s']}
def h2(name):
 s,r=clean(E/name); rows=[]
 for ident,n in [('10003',1465),('10020',571),('10030',340)]:
  m=re.search(r'route movie terminal=1 id='+ident+r' frames=(\d+)/(\d+) uploaded=(\d+) presented=(\d+)[^\n]*heap_before=(\d+)',s)
  assert m and list(map(int,m.groups()[:4]))==[n]*4,(name,ident)
  rows.append({'id':ident,'frames':n,'uploaded':n,'presented':n,'heap_before':int(m[5])})
 borrows=re.findall(r'MOVIEARENA borrow id=10030 token=(\d+)',s); assert len(borrows)==1,(name,borrows)
 returns=re.findall(r'MOVIEARENA return token='+borrows[0]+r'[^\n]*restored=1',s); assert len(returns)==1,(name,len(returns))
 return dict(r,pass_local=True,movies=rows,restored_returns=len(returns))
result={'source':SOURCE,'evidence_kind':'Local host/target/Flycast console checks; timing MODELLED; no full release or physical acceptance','h2':h2('h2-on-r2'),'census_profile_h2':h2('h2-on-c-reference-r1'),'diagnostic_h2':h2('diag-h2-r1'),'kos':[],'gdemu':[],'decisions':{},'events':{},'diagnostics':{},'physical_acceptance':False,'historic_arena_crash_cause_proven':False,'production_recipe_four_knobs':0}
assert result['h2']['movies'][-1]['heap_before']==93920
assert result['diagnostic_h2']['movies'][-1]['heap_before']==result['census_profile_h2']['movies'][-1]['heap_before']==57056
for frag in (0,1):
 cap=E/f'kos-on-49152-{frag}';_,r=clean(cap);g=load(cap/'gate.json');assert g['pass']; result['kos'].append(dict(r,gate=g,gate_sha256=sha(cap/'gate.json')))
for seed in range(1,11):
 cap=E/f'gdemu-on-seed{seed}';_,r=clean(cap);g=load(cap/'gate.json');assert g['pass'] and g['emu_env']['RE4DC_GD_SEED']==str(seed) and g['profile']==['GDCONSOLE profile=gdemu'];result['gdemu'].append(dict(r,seed=seed,pass_local=True,gate_sha256=sha(cap/'gate.json')))
c=load(E/'census-on/results.json');assert c['pass_rooms']==c['total_rooms']==4
result['census']={'pass_rooms':4,'result_sha256':sha(E/'census-on/results.json'),'rooms':[x['room'] for x in c['rooms']]}
for scene in ('bell','mendez'):
 _,r=clean(E/f'decisions-{scene}-on-r1');p=E/f'decisions-{scene}-comparison.json';j=load(p);assert j['verdict']=='MUST-IDENTICAL' and j['drift']['player_max']==j['drift']['enemy_max']==0 and j['drift']['slot_id_mismatches']==0
 result['decisions'][scene]=dict(r,compared_ticks=j['compared'],verdict=j['verdict'],drift=j['drift'],comparison_sha256=sha(p))
for arm in ('off','on'):
 for mode in ('r117','dam'):
  cap=E/f'event-{mode}-{arm}-r3';_,r=clean(cap);p=cap/'aud23-event-observation.json';j=load(p);q=j['summary'];assert j['observer_version']==3 and all('unknown' in x for x in j['errors']) and not q['acceptance_pass']
  if mode=='r117':
   assert q['source_state_sequence_observed'] and q['baseline_unsolved_observed'] and q['started_in_event_observed'] and q['solved_disarmed_event_clear_endpose_observed']
   rows=[]
   for st in j['stills']:
    assert st['capture_status']=='completed' and st['source_phase_still_matches_after_capture']
    rows.append({'phase':st['phase'],'binding_sha256':sha(cap/st['path']/'capture-binding.json'),'pictures':[{'path':str(f.relative_to(E)),'sha256':sha(f)} for f in sorted((cap/st['path']/'frames').glob('fb*.png'))]})
   assert len(rows)==2 and all(len(x['pictures'])==2 for x in rows)
   obs={'sequence_observed':True,'stills':rows,'visual_review':'Root inspected ON/OFF fb0 and ON fb1: visible loaded church, normal prompt before, prompt absent after. Other gate angle not shown; idle/pose not tick matched, no pixel-identical claim.'}
  else:
   assert q['pool_event_sequence_observed'] and q['baseline_clear_without_list2_observed'] and q['guarded_list2_during_event_observed'] and q['normal_event_clear_source_exit_observed'] and not q['phase_witness_pass']
   actors=q['first_list2_witness']['pool']['actors'];a=[a for a in actors if a['id']==0x12 and a['kind']==0 and a['entry']==2 and a['alive']];assert len(a)==1
   pairs=q['guarded_motion_progress_pairs'];assert pairs and all(p['to_frame']>p['from_frame'] and bool(p['motion_header_sha256']) for p in pairs)
   assert any(p['motion_header_sha256']==a[0]['motion_header_sha256'] for p in pairs)
   obs={'sequence_observed':True,'motion_headers':sorted(set(p['motion_header_sha256'] for p in pairs)),'actor':a[0],'motion_progress_pairs':len(pairs),'final_position':q['final_witness']['player']['pos'],'overlay_phase_authenticated':False,'full_motion_provenance':False,'historical_failure_reproduced':False}
  result['events'][f'{mode}-{arm}']=dict(r,observation_sha256=sha(p),source=j['source'],program_elf_sha256=j['program_elf_sha256'],manifest_sha256=j['symbol_manifest_sha256'],sample_count=j['samples'],unknown_samples=j['unknown_samples'],**obs)
for room in ('r101','r10c','r117','r200'):
 p=E/f'diag-{room}-r1/cache-diag.json';j=load(p);assert j['status']=='VALID_RECORDED_INTERVALS';result['diagnostics'][room]={'receipt_sha256':sha(p),'totals':j['totals'],'limits':j['limits']}
result['arena']={'source':'53fcbc0ba8fac8fcf035143dbd8cdd0870dd2b77','profile':'private VRAM_ROOM_ARENA1 NO_TOP0 CACHE_LINEWISE0; differs from production arena0 and historical B/B3','qualified_local':'Own boot/menu warp/H2/48KiB fight frag0+1; see sealed QUALIFICATION.json','two_minute_physical_run':'PENDING; no deterministic <=55s equivalent','historical_layout_identical':False}
result['open']=['Physical arena two-minute observation and physical puzzle/dam/fight acceptance','Historical failure injection/repro and exact overlay phases are not demonstrated','Cache masked-window measurements exclude observer/restore tail; unattributed boot/transition/tails remain','Fresh full release check remains pending; local gates alone do not establish it']
result['receipt_script_sha256']=sha(pathlib.Path(__file__))
(E/'LOCAL-GATE-RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'h2_s30':result['h2']['movies'][-1],'census':result['census']['pass_rooms'],'gdemu_seeds':len(result['gdemu']),'event_controls':list(result['events']),'output':str(E/'LOCAL-GATE-RECEIPT.json')},indent=2))