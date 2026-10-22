from pathlib import Path
import json,math
R=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018');d=json.loads((R/'r202-original-source-sat-20261019.json').read_text());points=[(22733.23046875,-22844.59765625),(22700,-23900),(23500,-24700)]
def y_at(t,x,z):
 a,b,c=t['points'];den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
 if abs(den)<.001:return None
 u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den;v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den;w=1-u-v
 return a[1]*u+b[1]*v+c[1]*w if min(u,v,w)>=-.001 else None
def sd(x,z,a,b):
 dx,dz=b[0]-a[0],b[1]-a[1];den=dx*dx+dz*dz;t=max(0,min(1,((x-a[0])*dx+(z-a[1])*dz)/den))if den else 0;return math.hypot(x-a[0]-t*dx,z-a[1]-t*dz)
rows=[]
for a,b in zip(points,points[1:]):
 count=math.ceil(math.dist(a,b)/50)
 for n in range(count+1):
  x=a[0]+(b[0]-a[0])*n/count;z=a[1]+(b[1]-a[1])*n/count;ys=[y for t in d['floors']if(y:=y_at(t,x,z))is not None and abs(y-10595.90918)<50];assert ys,('No matching source floor',x,z);y=ys[0];distance=1e20
  for wall in d['walls']:
   p=wall['points']
   for height in [y+500,y+1300]:
    if not min(v[1]for v in p)<=height<=max(v[1]for v in p):continue
    hits=[]
    for u,v in zip(p,p[1:]+p[:1]):
     if min(u[1],v[1])<=height<=max(u[1],v[1])and abs(u[1]-v[1])>.01:
      q=(height-u[1])/(v[1]-u[1]);hits.append((u[0]+q*(v[0]-u[0]),u[2]+q*(v[2]-u[2])))
    if len(hits)>=2:distance=min(distance,sd(x,z,hits[0],hits[1]))
  rows.append([x,y,z,distance])
proof=dict(scope='Read-only exact selected r202.arc original SAT route hypothesis. 50-unit samples, original floor height, body-height wall slices. Actual normal collision governs. No runtime mutation.',source_arc_sha256='79042994f58f719cd7b7af166fbf9922552851dd6aaed88bfd3502065574b216',points=points,samples=len(rows),minimum_wall_clearance=min(r[3]for r in rows),all_at_least300=all(r[3]>=300 for r in rows),rows=rows);out=R/'Test21/recovered-j-content-20261021/cannon-footpoint-source-polyline-check.json';assert not out.exists();out.write_text(json.dumps(proof,indent=2)+'\n');print({k:v for k,v in proof.items()if k!='rows'})