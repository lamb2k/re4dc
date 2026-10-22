from pathlib import Path
import math,json
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');h={};exec((L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text().split('nodes={};bycell=')[0],h);pts=[(18679.85546875,-44815.25390625),(23500,-47500),(25000,-49000)];legs=[]
for a,b in zip(pts,pts[1:]):
 bad=[];n=math.ceil(math.dist(a,b)/75)
 for i in range(n+1):
  x=a[0]+(b[0]-a[0])*i/n;z=a[1]+(b[1]-a[1])*i/n;ys=[h['plane'](t,x,z)for t in h['floors']];ys=[y for y in ys if y is not None and -2300<y<-1500]
  if not ys or all(h['blocked'](round(x/250),round(z/250),y)for y in ys):bad.append([x,z])
 legs.append(dict(start=a,end=b,blocked=bad))
p=D/'current293-Northbell-Southquiet-combat-sourceSAT-20261021.json';assert not p.exists();p.write_text(json.dumps(dict(scope='OFFLINE sourceSAT quietSouthflank afterprospectiveNorthbellfromactual293Westposition; no guest/belllineofsight/dynamicAI/safety guarantee.',legs=legs),indent=2)+'\n');print([len(x['blocked'])for x in legs]);assert not any(x['blocked']for x in legs)
