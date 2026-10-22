from pathlib import Path
import json,math
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');h={};exec((L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text().split('nodes={};bycell=')[0],h);routes=[[(19000,-45000),(19000,-42000),(23500,-42000),(27500,-42500),(28500,-45000)],[(19000,-45000),(19000,-42500),(21300,-42000),(27000,-42000),(28500,-45000)]];rr=[]
for pts in routes:
 legs=[]
 for a,b in zip(pts,pts[1:]):
  bad=[];steps=math.ceil(math.dist(a,b)/75)
  for i in range(steps+1):
   x=a[0]+(b[0]-a[0])*i/steps;z=a[1]+(b[1]-a[1])*i/steps;ys=[h['plane'](t,x,z)for t in h['floors']];ys=[y for y in ys if y is not None and abs(y+2000)<550]
   if not ys or all(h['blocked'](round(x/250),round(z/250),y)for y in ys):bad.append([x,z])
  legs.append(dict(start=a,end=b,blocked=bad))
 rr.append(dict(points=pts,clear=not any(x['blocked']for x in legs),legs=legs))
p=D/'lower-floor-North-quiet-flank-sourceSAT-20261021.json';assert not p.exists();p.write_text(json.dumps(dict(scope='OFFLINE lower-floor alternatives through established259Northcorridor; no guest or silence/AI promise. Unlike rejected oldNorth-41500 route, this staysat-42000 opening. Originalcurrent enemy is asleep after285Continue; actual future dynamicseparation/health/PID controls required. Do not useUpperWeststairs afterbosswake.',routes=rr),indent=2)+'\n');print([(r['clear'],[len(x['blocked'])for x in r['legs']])for r in rr])
