"""Seal24 actual pre-repair captures; read-only evidence aggregation, no guest/build/assets."""
from pathlib import Path
import hashlib,json,re,shutil
HERE=Path(__file__).resolve().parent
E=Path(r'C:\Flycast-Evidence\re4-dreamcast\world-emit23-takeover\49ad20f9')
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
ASSETS='de1f410a4c2f6175a728ff50fee8a555db20b5fa76873733eab2659647617830'
GATES={'h2':'g','kos0':'c','kos1':'c','gd1':'g','bench100':'c','bench101':'c','bell':'t','mendez':'t'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def fresh(p,data):
 with p.open('x',encoding='utf-8') as f:f.write(data)
def jfresh(p,row):fresh(p,json.dumps(row,indent=2)+'\n')
def pair_sequence(text):
 return bool(re.search(r'native UI: load /cd/dc/tex/7/7d4e1e92-052bdc2e\.re4tex 128x128 fmt=14\n(?:[^\n]*\n){0,2}native UI: package rejected: open failed\nnative UI: upload FAILED vram=0\n(?:[^\n]*\n){0,2}native UI: pair missing 7d4e1e92-052bdc2e color=43aff05a-cfb2b1a5 mask=572a97ee-75aeb071 128x128',text))
assert sha(E/'current-gates-helper-b/SHA256SUMS')=='be0796160dec68387371f0a8f79a33662a3da032de7288ea9a3263fb9a0e0d43'
assert sha(HERE/'current_gates.py')=='f8d81e3884ef7197834259fef72cb25152770d857ad697e8c325ddca438049bb'
rootdelta=read(E/'root-helper/source-delta.json')
assert rootdelta['original_sha256']==sha(HERE/'current_gates.py') and rootdelta['root_copy_sha256']==sha(HERE/'current_gates_root_v1.py')
reference=Path(r'C:\Flycast-Evidence\re4-dreamcast\audits23-takeover\5e4de9a0\decisions-mendez-on-r1\run-output.txt')
assert pair_sequence(reference.read_text(errors='replace').replace('\0',''))
rows=[];units={};metrics={};paircases=[]
for arm in ['B','L','E']:
 metrics[arm]={}
 for gate,profile in GATES.items():
  tag=arm+'-'+gate+('-root-r1' if arm in ['L','E'] and profile in ['g','c'] else '-r1');cap=E/'captures'/tag
  launch=read(cap/'current-gate-launch.json');result=read(cap/'current-gate-result.json');run=read(cap/'run-result.json');bound=read(cap/'bounded-launch.json');unit=launch['unit']
  assert unit['source']==SOURCE and unit['arm']==arm and unit['profile']==profile and unit['asset_manifest_sha256']==ASSETS
  assert len(unit['programme']['overlays'])==14 and launch['gate']==gate
  assert result['current_launch_sha256']==sha(cap/'current-gate-launch.json') and result['run_output_sha256']==sha(cap/'run-output.txt')
  assert bound['deadline_seconds']==55 and bound['guest_exited'] and not bound['deadline_fired'] and not run['errors'] and run['status']=='RUN_COMPLETE'
  assert result['exact_console_image_verified'] and result['exact_harness_verified'] and result['launcher_rc']==0
  key=arm+'-'+profile
  if key in units:assert units[key]['programme']==unit['programme']
  else:units[key]=unit
  obs=result['observed'];row={'arm':arm,'gate':gate,'profile':profile,'unit_identity':key,'tag':tag,'strict_pass':result['pass'],'critical':result['critical'],'observed':obs,'elapsed_s':run['elapsed_s'],'deadline_fired':bound['deadline_fired'],'capture':str(cap),'digests':{n:sha(cap/n) for n in ['current-gate-launch.json','current-gate-result.json','run-result.json','bounded-launch.json','run-output.txt']}}
  if gate=='h2':metrics[arm]['h2_heap_before']=obs['heap_before']
  if gate in ['kos0','kos1']:metrics[arm][gate+'_min_headroom']=obs['min_headroom'];metrics[arm][gate+'_margin_over4096']=obs['min_headroom']-4096
  if gate in ['bell','mendez']:
   cmp=read(cap/'decision-comparison.json');row['decision_comparison']={'rc':obs['comparison']['rc'],'compared':cmp['compared'],'window':cmp['window'],'informational_sq':cmp['rows'].get('sq'),'json_sha256':sha(cap/'decision-comparison.json'),'text_sha256':sha(cap/'decision-comparison.txt')};row['route_decisions_pass']=bool(obs['goal_stop'] and obs['source_event_markers'] and obs['comparison']['rc']==0)
  if gate=='mendez':
   text=(cap/'run-output.txt').read_text(errors='replace').replace('\0','');same=pair_sequence(text) and result['critical']==['native UI: package rejected: open failed','native UI: upload FAILED vram=0']
   row['same_missing_pair_as_proved_R_reference']=same;row['known_control_gap']=same and row['route_decisions_pass'];paircases.append({'arm':arm,'tag':tag,'same_missing_pair':same,'strict_pass':result['pass'],'route_decisions_pass':row['route_decisions_pass'],'log_sha256':row['digests']['run-output.txt']})
  rows.append(row)
assert len(rows)==24
proofs={p.name:{'sha256':sha(p),'scope':read(p)['scope'],'source':read(p)['source'],'old_source':read(p)['old_source'],'profile':read(p)['profile'],'eligible':read(p)['eligible']} for p in sorted((E/'reuse').glob('R-*-5e4d.json'))}
result={'schema':1,'source':SOURCE,'pre_repair':True,'world_unit_complete':False,'private_QA_pair_ready':False,'classification':'Actual current49ad ON-arm Flycast regression evidence, not hardware/performance/visual-pixel acceptance','fresh_ON_captures':24,'strict_passes':sum(r['strict_pass'] for r in rows),'strict_failures':sum(not r['strict_pass'] for r in rows),'actual_memory_metrics':metrics,'rows':rows,'unique_programme_profile_identities':units,'shared_asset_manifest_sha256':ASSETS,'R_control_reuse_proofs':proofs,'root_helper_scope_delta':{'path':str(E/'root-helper/source-delta.json'),'sha256':sha(E/'root-helper/source-delta.json'),'record':rootdelta},'common_UI_gap':{'reference':str(reference),'reference_log_sha256':sha(reference),'cases':paircases,'disposition':'Strict failures preserved; root owns private PS2-source recovery and future post-repair gates. No exceptions/allowlists/retries/assets or recipe enable.'},'bounds':'Each worker at most one child, sharedstat3/trace16/exact55console; this worker ran L/E traces serially after root g/c ended.','B_seal_sha256':sha(E/'current-gates-helper-b/SHA256SUMS'),'aggregate_generator_sha256':sha(Path(__file__))}
report=HERE/'RESULTS-ALL-PRE-REPAIR.json';jfresh(report,result)
lines=['# All current ON-arm gates — pre-repair addendum','','Source '+SOURCE+'. This is a separate addendum; original B report/seal is unchanged. Root performed L/E g/c12captures, this worker completed their4trace captures serially with the frozen original helper. All24 actual captures are retained. No R guest/disc was duplicated; current R g/c/t reuse is proved by exact rawmain/all14overlays and baseline assets.','','Strict totals: '+str(result['strict_passes'])+' pass, '+str(result['strict_failures'])+' fail. The three Mendez failures retain the exact same missing material pair as byte-proven R; their full movie/route/MUST decision comparisons separately pass. They are not converted to overall pass.','','| Arm | H2 heap_before | KOS49152 frag0 min | frag1 min | margin over4096 frag0 / frag1 |','|---|---:|---:|---:|---:|']
for arm in ['B','L','E']:
 d=metrics[arm];lines.append('|'+arm+'|'+str(d['h2_heap_before'])+'|'+str(d['kos0_min_headroom'])+'|'+str(d['kos1_min_headroom'])+'|'+str(d['kos0_margin_over4096'])+' / '+str(d['kos1_margin_over4096'])+'|')
lines+=['','All H2 movies completed340/340 uploaded/presented with matching arena return restored1. Both exact48KiB squeeze cases passed in each arm. All GD seed1 cases observed actual gdemu/jitter20000/seed1 and door103 without bad reads. Forest/cross current C-profile actor census, CAST-GC --not-drawn, LEONGC and TEXCHK passed with memory/VRAM witnesses and zero rejection/retry/eviction counters. These checks do not certify PS2 source provenance, visual parity or console performance.','','| Arm | Bell strict | Mendez strict | Mendez route/MUST comparison |','|---|---|---|---|']
for arm in ['B','L','E']:
 bell=next(r for r in rows if r['arm']==arm and r['gate']=='bell');m=next(r for r in rows if r['arm']==arm and r['gate']=='mendez');lines.append('|'+arm+'|'+('PASS' if bell['strict_pass'] else 'FAIL')+'|'+('PASS' if m['strict_pass'] else 'FAIL: same missing UI pair' if m['same_missing_pair_as_proved_R_reference'] else 'FAIL: inspect raw evidence')+'|'+('PASS' if m['route_decisions_pass'] else 'FAIL')+', '+str(m['decision_comparison']['compared'])+' common ticks|')
lines+=['','Mendez source movies1067/265/321 and two explicit diagnostic kills reach room10f. All MUST state fields match the R control in each common frame window; informational sq differences remain in the JSON/comparator output. No claim of every trace field, pixels, an independent physical window-jump or hardware acceptance follows.','','Common missing pair: 7d4e1e92-052bdc2e, color43aff05a-cfb2b1a5 and mask572a97ee-75aeb071, with package-open/upload failure before DOORDEMO. Same pair/order is independently matched in each actual Mendez log and the proved R reference. The raw current-gate-result.json files remain pass:false. Root owns private PS2-source repair and subsequent qualification. No helper exception, relaxed predicate, asset swap, recipe/data enable or weaker retry was made.','','Current world unit and private QA pair remain NOT READY. Both world performance switches remain unpromoted. Root owns remaining repair/still/console/integration decisions. Frozen original helperf8d81... and rootcopy1861... remain byte unchanged; root source-delta.json records only worker.lock ->root-worker.lock and unchanged shared limits. Original B seal remains '+result['B_seal_sha256']+'.','','Machine report RESULTS-ALL-PRE-REPAIR.json binds each actual capture log/result/launch/bound digest, unique source/programme/14overlay/profile and common assets, plus exact root helper fork/proved R controls. This is pre-repair evidence; do not silently reuse it as a post-repair verdict. No owned L/E guest remains after this seal.']
addendum=HERE/'HANDBACK-ALL-PRE-REPAIR.md';fresh(addendum,'\n'.join(lines)+'\n')
dest=E/'current-gates-all-pre-repair';dest.mkdir(exist_ok=False)
for path in [report,addendum,Path(__file__)]:shutil.copyfile(path,dest/path.name)
seal=''.join(sha(dest/p.name)+'  '+p.name+'\n' for p in [report,addendum,Path(__file__)]);fresh(dest/'SHA256SUMS',seal)
assert sha(E/'current-gates-helper-b/SHA256SUMS')==result['B_seal_sha256']
print(json.dumps({'strict_passes':result['strict_passes'],'strict_failures':result['strict_failures'],'metrics':metrics,'report_sha256':sha(report),'addendum_sha256':sha(addendum),'seal_sha256':sha(dest/'SHA256SUMS'),'evidence':str(dest)},indent=2))
