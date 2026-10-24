from pathlib import Path
import hashlib,json,re
r=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023')
rows=[]
for arm in ('off','on'):
 p=r/f'full-h2-{arm}-console-r1';t=(p/'run-output.txt').read_text(errors='replace');rr=json.loads((p/'run-result.json').read_text())
 movies=[]
 for m in re.finditer(r'route movie terminal=(\d+) id=(\d+) frames=(\d+)/(\d+) uploaded=(\d+) presented=(\d+)[^\n]*heap_before=(\d+)',t):
  a=[int(x) for x in m.groups()];movies.append(dict(terminal=a[0],id=a[1],frames=a[2],expected=a[3],uploaded=a[4],presented=a[5],heap_before=a[6]))
 assert len(movies)==3 and [m['id'] for m in movies]==[10003,10020,10030]
 assert all(m['terminal']==1 and m['frames']==m['expected']==m['uploaded']==m['presented'] for m in movies)
 assert rr['emu']=='console' and rr['status']=='RUN_COMPLETE' and rr['stopped']=='goal'
 bad=[l for l in t.splitlines() if re.search(r'Out of memory|\bHALT\b|\bFAULT\b|\bMISSING\b|no contiguous block',l)]
 assert not bad
 rows.append(dict(arm=arm,capture=str(p),seconds_limit=rr['seconds'],elapsed_s=rr['elapsed_s'],movies=movies,restored='restored=1' in t,source_fixture_pins=rr['fixtures'],dd3_admissions=re.findall(r'SCNDEDUP3 room=([0-9a-f]+)',t)))
assert rows[0]['movies']==rows[1]['movies']
res=dict(matched_no_added_heap=True,full_route_playback_pass=True,historical_94KB_floor='NOT_ESTABLISHED_BY_THIS_PAIR; investigate baseline identity',rows=rows)
(r/'full-h2-matched-r1.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='rows'}));print([(x['arm'],x['elapsed_s'],x['movies'][-1]['heap_before']) for x in rows])
