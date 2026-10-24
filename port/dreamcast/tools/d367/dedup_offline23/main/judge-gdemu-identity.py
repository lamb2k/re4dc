from pathlib import Path
import json,re,hashlib
r=Path(r'C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023')
c=r/'gate-gdemu-r1';t=(c/'run-output.txt').read_text(errors='replace');rr=json.loads((c/'run-result.json').read_text())
bad=re.compile(r'MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))|HALT|FAULT|Out of memory')
rows=[l for l in t.splitlines() if bad.search(l)]
console=(c/'flycast.log').read_text(errors='replace')+(c/'serial.txt').read_text(errors='replace')
prof=re.findall(r'GDCONSOLE profile=[^\n]+',console)
res=dict(emu=rr['emu'],emu_env=rr['emu_env'],r103='phase=enter room=103' in t,bad_reads_or_stops=rows,profile=prof,loaded_dd3_rooms=re.findall(r'SCNDEDUP3 room=([0-9a-f]+)',t))
res['pass']=rr['emu']=='console' and rr['status']=='RUN_COMPLETE' and res['r103'] and not rows and any('profile=gdemu' in l and 'seed=1' in l for l in prof)
(r/'gdemu-seed1-gate-r1.json').write_text(json.dumps(res,indent=2)+'\n'); print(json.dumps(res))
# Every capture pins the executable bytes actually used, independent of the claimed mode.
pins=[]
for p in sorted(r.iterdir()):
 if p.is_dir() and (p/'run-result.json').is_file():
  rr=json.loads((p/'run-result.json').read_text()); ex=p/'flycast.exe'
  pins.append(dict(capture=str(p),emu=rr.get('emu'),exe_sha256=hashlib.sha256(ex.read_bytes()).hexdigest(),result_sha256=hashlib.sha256((p/'run-result.json').read_bytes()).hexdigest(),fixture=rr['fixtures']))
(r/'capture-identity-pins.json').write_text(json.dumps(pins,indent=2)+'\n'); print('Pinned captures',len(pins))
