from pathlib import Path
import json,hashlib,re,subprocess
root=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01');p=json.loads((root/'current4be-preflight-r1.json').read_text())
def pin(path):
 path=Path(path);return {'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
plan={'source':p['source'],'arms':{}}
for arm,x in p['programs'].items():
 files=dict(x['files']);files['candidate.txt']=pin(Path(files['re4dc-game.elf']['path']).parent/'candidate.txt')
 plan['arms'][arm]={'program':{'status':'PINNED_FOR_ACTUAL_OWNED_H2','files':files},'stage_identity':str(root/('base-standard-current4be-'+arm+'-r1')/'owned-stage-identity.json')}
out=root/'current4be-programme-pins-r1.json';assert not out.exists();out.write_text(json.dumps(plan,indent=2)+'\n')
rows={}
for arm in ('off','on'):
 cap=root/('h2-'+arm+'-console-r1');run=json.loads((cap/'run-result.json').read_text());text=(cap/'run-output.txt').read_text(errors='replace')
 bounded=json.loads((cap/'bounded-launch.json').read_text());assert not bounded['deadline_fired'] and bounded['guest_observed_elapsed_s']<=55
 assert run['status']=='RUN_COMPLETE' and run['stopped']=='goal' and run['emu']=='console' and run['seconds']==50 and not run['errors']
 movies={}
 for movie,n in [('10003',1465),('10020',571),('10030',340)]:
  m=re.search(r'route movie terminal=1 id='+movie+r' frames=(\d+)/(\d+) uploaded=(\d+) presented=(\d+)[^\r\n]*?heap_before=(\d+)',text)
  assert m and all(int(m[i])==n for i in range(1,5)),(arm,movie)
  movies[movie]={'frames':n,'uploaded':n,'presented':n,'heap_before':int(m[5])}
 restored=re.findall(r'MOVIEARENA return[^\r\n]*restored=(\d+)',text);assert restored and all(x=='1' for x in restored)
 borrows=re.findall(r'MOVIEARENA borrow[^\r\n]*capacity=(\d+) budget=(\d+)',text)
 assert borrows
 if arm=='on':
  assert text.count('SCNDEDUP3 room=100')>=2
  assert all(int(c)==1512928 for c,b in borrows)
 else:
  assert not re.search(r'SCNDEDUP3',text)
  assert all(int(c)==1562656 for c,b in borrows)
 arena=re.search(r'arena fit (\d+) bytes \((\d+) left to KOS\)',text);assert arena
 rows[arm]={'source':p['source'],'run':pin(cap/'run-result.json'),'log':pin(cap/'run-output.txt'),'elapsed_s':run['elapsed_s'],'emulator_mode':run['emu'],'limit_s':run['seconds'],'bounded55':pin(cap/'bounded-launch.json'),'movies':movies,'restored':True,'world_borrows':[{'capacity':int(c),'budget':int(b)} for c,b in borrows],'dd3_admissions':re.findall(r'SCNDEDUP3 room=([0-9a-f]+)',text),'arena_bytes':int(arena[1]),'kos_left':int(arena[2]),'base':run['tracks']['base'],'track03_sha256':run['tracks']['track03_sha256']}
 print(arm,'s30',movies['10030']['frames'],'heap_before',movies['10030']['heap_before'],'restored1','elapsed',run['elapsed_s'],'arena',arena[1])
assert rows['on']['movies']['10030']['heap_before']>=rows['off']['movies']['10030']['heap_before']
for arm in ('off','on'):
 cap=root/('h2-'+arm+'-console-r1');run=json.loads((cap/'run-result.json').read_text());expected=Path(p['tools']['fullplay/segments/h2-pad.txt']['path']).read_bytes().replace(b'\r',b'')
 assert run['fixtures']['pad']['sha256']==hashlib.sha256(expected).hexdigest()
result={'source':p['source'],'status':'PASS_MATCHED_FULL_H2_PLAYBACK_AND_NO_LOSS_FLYCAST_PROXY','scope':'MODELLED: Flycast console mode with unthrottled JIT FP_NOLIMIT; actual captured heap/playback evidence, not physical console/performance or full release acceptance','arms':rows,'s30_heap_delta_on_minus_off':rows['on']['movies']['10030']['heap_before']-rows['off']['movies']['10030']['heap_before'],'data_identity_receipt':pin(root/'current4be-matched-data-r1.json'),'preflight_receipt':pin(root/'current4be-preflight-r1.json'),'limits':'Root owns final gating/QA/integration; diagnostic census/KOS/GDEMU/gameplay/look requirements not inferred from this fullH2 result. Prior failures preserved.'}
out=root/'current4be-matched-h2-r1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')