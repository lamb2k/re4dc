from pathlib import Path
import json,math,hashlib,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
p=L/'STATUS.md';s=p.read_text(encoding='utf-8');a=s.index('Done:');b=s.index('Next:',a);s=s[:a]+'''Done: Latest closed261 source29014 state17e2c51442d37a02809716447cb8682238a03680734366969d002518891d9c73; Leon1200/1200, Ashley90/600 Wait46, Garrador4000, HG10+25. Full South-offset/East escape completed; existing6500 frontal guard stopped before patrol/West return. Original127 and all authentic death/Continue lineage preserved. Run260 prealignment hunting stopped safely before RT/fire; host yaw-release decay correction in progress.
Doing now: No guest active. Preparing a complete South/West reposition, original patrol observation and return; source-only body prealignment release-latch correction. Current Garrador and chapter remain unfinished.
'''+s[b:];a=s.index('Updated:');b=s.index('\n',a);s=s[:a]+'Updated: '+datetime.datetime.now().astimezone().isoformat(timespec='seconds')+'. Exact closed261 audited; no current resource hold.'+s[b:];p.write_text(s,encoding='utf-8')
h={};src=(L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text();exec(src.split('nodes={};bycell=')[0],h)
pts=[(27774.599609375,-44822.61328125),(23500,-47500),(16000,-45500),(23500,-47500),(19000,-45000)];legs=[]
for a,b in zip(pts,pts[1:]):
 bad=[];steps=math.ceil(math.dist(a,b)/75)
 for i in range(steps+1):
  x=a[0]+(b[0]-a[0])*i/steps;z=a[1]+(b[1]-a[1])*i/steps;ys=[h['plane'](t,x,z)for t in h['floors']];ys=[y for y in ys if y is not None and abs(y+2000)<550]
  if not ys or all(h['blocked'](round(x/250),round(z/250),y)for y in ys):bad.append([x,z])
 legs.append(dict(start=a,end=b,blocked_samples=bad))
o=D/'resume261-full-South-West-patrol-South-return-sourceSAT-v3-20261021.json';assert not o.exists();o.write_text(json.dumps(dict(scope='OFFLINE source SAT conservative route hypothesis only, no guest or state writes. Four full legs: South flank, far West original patrol wait, South flank again, West firing point. Actual collision remains authoritative.',legs=legs),indent=2)+'\n');print([(x['end'],len(x['blocked_samples']))for x in legs]);assert not any(x['blocked_samples']for x in legs)
p=L/'owned-window-recovered-j-r201-combined-South-West-patrol-four-leg-still.py';assert not p.exists();s=(L/'owned-window-recovered-j-r201-combined-full-patrol-quickturn18-still.py').read_text();s=s.replace('assert len(targets)==3;target_i=2','assert len(targets)==4;target_i=2');s=s.replace('Require3targets','Require4targets with source-SAT screened complete South-West-patrol-South-return cycle');compile(s,str(p),'exec');p.write_text(s);print(p.name,hashlib.sha256(p.read_bytes()).hexdigest())
