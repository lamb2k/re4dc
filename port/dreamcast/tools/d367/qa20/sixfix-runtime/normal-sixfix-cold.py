from pathlib import Path
import sys,time,json
from qa_owned_checkpoint import capture_checkpoint
cap=Path(sys.argv[1]);deadline=time.monotonic()+52;first=None
while time.monotonic()<deadline:
 try:
  if not (cap/'run-start.json').exists():time.sleep(.05);continue
  assert json.loads((cap/'run-start.json').read_text())['seed']is None,'Reset lineage only'
  rows=(cap/'readonly-combat-io.jsonl').read_text().splitlines();s=json.loads(rows[-1])
  if not s.get('world_safe')or 'player_pos'not in s:time.sleep(.05);continue
  assert s['room']==0x100 and s['health'][0]==1200
  x,y,z=s['player_pos'];assert -84000<x<-82000 and 800<y<1000 and -39000<z<-38000
  if first is None:first=s['frame']
  if s['frame']-first<30:time.sleep(.05);continue
  result=capture_checkpoint(cap,'cold-entry','Original QA menu R100 preset; no world input','Fresh program safe pre-s03 entry; original hidden first Ganado, not after-s20 combat')
  owner=json.loads((cap/'owned-process.json').read_text());(cap/'cold-entry-result.json').write_text(json.dumps(dict(sample=s,screenshot=result),indent=2)+'\n');request=dict(pid=owner['pid'],start_filetime=owner['start_filetime'],reason='SIXFIX_FRESH_COLD_ENTRY_SAVED');tmp=cap/'owned-stop-request.tmp';tmp.write_text(json.dumps(request)+'\n');tmp.replace(cap/'owned-stop-request.json');break
 except (FileNotFoundError,IndexError,json.JSONDecodeError):time.sleep(.05)
else:raise SystemExit('No safe fresh cold entry before bounded deadline')
