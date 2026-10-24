#!/usr/bin/env bash
set -euo pipefail
T=/root/work/lanes/stat-bytes23-complete/port/dreamcast/tools/game30
E='/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d'
cmp_rc=0
python3 "$T/decision_cmp.py" "$E/mendez-bounded-off-r3/run-output.txt" "$E/mendez-bounded-on-r3/run-output.txt" --align frame --json "$E/mendez-bounded-r3-comparison.json" > "$E/mendez-bounded-r3-comparison.txt" 2>&1 || cmp_rc=$?
test "$cmp_rc" -eq 1 # Keep the real MUST-DIFFER result; verify its cause below.
cat "$E/mendez-bounded-r3-comparison.txt"
python3 - <<'PY'
import pathlib,json,re
r=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d');out={}
d=json.loads((r/'mendez-bounded-r3-comparison.json').read_text())
c0=json.loads((r/'camera-off-control.json').read_text())
c1=json.loads((r/'camera-on-control.json').read_text())
assert d['verdict']=='MUST-DIFFER' and d['compared']==2643
must='r sy sp st rf sc rm ms ps e es o os ec sa dm lq ep eg af'.split()
assert {k:d['rows'][k]['differ'] for k in must if d['rows'][k]['differ']}=={'lq':19}
assert c0['verdict']=='MUST-IDENTICAL' and c0['compared']==2643
assert c1['verdict']=='MUST-DIFFER'
assert {k:c1['rows'][k]['differ'] for k in must if c1['rows'][k]['differ']}=={'lq':19}
for x in [d,c0,c1]:
 assert x['drift']['player_max']==0 and x['drift']['enemy_max']==0 and x['drift']['slot_id_mismatches']==0
for a in ['off','on']:
 p=r/('mendez-bounded-'+a+'-r3');s=(p/'run-output.txt').read_text(errors='replace').replace('\0','');run=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text());w=json.loads((p/'window-observation.json').read_text())
 assert run.get('stopped')=='goal' and not run['errors'] and not b['deadline_fired']
 assert not re.search(r'HALT|FAULT|MISSING|Out of memory',s)
 assert 'phase=enter room=10f' in s
 for id,n in [('11f02',1067),('11f10',265),('11f11',321)]:assert re.search(f'route movie terminal=1 id={id} frames={n}/{n}',s),id
 assert len(re.findall('warp: kill 0x35 hp<=0',s))==2
 assert w['summary']['normal_event_state_sequence_observed'] and w['first_door_marker_reached'] and not w['errors']
 assert all(not x.get('error') and not x.get('door_marker_observed_during_capture') for x in w['shots'])
 out[a]={'source':w['source'],'elapsed_s':run['elapsed_s'],'room10f':True,'deaths':2,'full_movies':{'s02':1067,'s10':265,'s11':321},'observed_normal_event_sequence_before_door':True,'automatic_named_fcv_certification':False,'window_samples':w['samples'],'human_still_review':'Root inspected both arms: JUMP OUT approach, actual window jump motion, and event-clear standing framebuffer.','decisions':'MUST-DIFFER: 19 line-query counts only; legacy camera-predicate control restores MUST-IDENTICAL across 2643 ticks. No gameplay drift. Static causal review required separately.'}
(r/'mendez-bounded-r3-route-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
PY
