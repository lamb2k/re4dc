from pathlib import Path
import json,math
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');h={};exec((L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text().split('nodes={};bycell=')[0],h);pts=[(28758.67578125,-47519.9453125),(27500,-45000),(25000,-44000)];legs=[]
for a,b in zip(pts,pts[1:]):
 bad=[];steps=math.ceil(math.dist(a,b)/75)
 for i in range(steps+1):
  x=a[0]+(b[0]-a[0])*i/steps;z=a[1]+(b[1]-a[1])*i/steps;ys=[h['plane'](t,x,z)for t in h['floors']];ys=[y for y in ys if y is not None and abs(y+2000)<550]
  if not ys or all(h['blocked'](round(x/250),round(z/250),y)for y in ys):bad.append([x,z])
 legs.append(dict(start=a,end=b,blocked=bad))
p=D/'resume268-full-East-to-North-center-sourceSAT-20261021.json';assert not p.exists();p.write_text(json.dumps(dict(scope='Offline source SAT route hypothesis only; no guest or state writes.',legs=legs),indent=2)+'\n');print([len(x['blocked'])for x in legs]);assert not any(x['blocked']for x in legs)
