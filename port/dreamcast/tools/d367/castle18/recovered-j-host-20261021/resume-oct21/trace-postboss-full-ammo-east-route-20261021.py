from pathlib import Path
import json,hashlib,math
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');base=L/'trace-r201-dungeon-floor-wall-navigation-20261019.py';ns={};exec(compile(base.read_text().split('nodes={};bycell=')[0],str(base),'exec'),ns)
points=[[16012.0664,2000,-37525],[16250,2000,-30750],[17750,2000,-25250],[20000,2000,-24000],[32250,2000,-25500],[32250,2000,-29250],[39250,2000,-30500],[41000,2000,-32000],[41500,2000,-33250]];segments=[]
for a,b in zip(points,points[1:]):
 n=max(1,math.ceil(math.dist(a,b)/75));bad=[]
 for i in range(n+1):
  x,y,z=[a[k]+(b[k]-a[k])*i/n for k in range(3)]
  if ns['blocked'](round(x/250),round(z/250),y) or not any((yy:=ns['plane'](t,x,z))is not None and abs(yy-y)<50 for t in ns['floors']):bad.append([x,y,z])
 segments.append(dict(start=a,end=b,samples=n+1,blocked_samples=bad))
out=D/'postboss-full-ammo-east-route-sourceSAT-20261021.json';assert not out.exists();out.write_text(json.dumps(dict(scope='Offline source floor/wall clearance only; actual normal collision and unchanged injury/resource guards remain authoritative. No guest or game writes.',source_sha256=hashlib.sha256((ns['R']/'r201-original-source-sat-navigation-20261019.json').read_bytes()).hexdigest(),historical_stairs193_position_reference_only=True,original_source_only_future_route=True,segments=segments),indent=2)+'\n');print(out);print([(x['end'],len(x['blocked_samples']))for x in segments])