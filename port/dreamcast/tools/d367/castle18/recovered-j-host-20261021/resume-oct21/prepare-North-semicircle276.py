from pathlib import Path
import json,math
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');h={};exec((L/'trace-r201-dungeon-floor-wall-navigation-20261019.py').read_text().split('nodes={};bycell=')[0],h);pts=[(19050.837890625,-44980.29296875),(19000,-42500),(23500,-41500),(27500,-42500),(28500,-45000)];legs=[]
for a,b in zip(pts,pts[1:]):
 bad=[];steps=math.ceil(math.dist(a,b)/75);mind=1e9
 for i in range(steps+1):
  x=a[0]+(b[0]-a[0])*i/steps;z=a[1]+(b[1]-a[1])*i/steps;mind=min(mind,math.hypot(x-23717.7265625,z+45587.56640625));ys=[h['plane'](t,x,z)for t in h['floors']];ys=[y for y in ys if y is not None and abs(y+2000)<550]
  if not ys or all(h['blocked'](round(x/250),round(z/250),y)for y in ys):bad.append([x,z])
 legs.append(dict(start=a,end=b,blocked=bad,initial_actor_min_distance= mind))
p=D/'resume275-full-North-semicircle-sourceSAT-20261021.json';assert not p.exists();p.write_text(json.dumps(dict(scope='Offline source SAT route/static initial enemy separation hypothesis only. Actual actor moves; no silence claim or guest.',legs=legs),indent=2)+'\n');print([(len(x['blocked']),round(x['initial_actor_min_distance']))for x in legs]);assert not any(x['blocked']for x in legs)
