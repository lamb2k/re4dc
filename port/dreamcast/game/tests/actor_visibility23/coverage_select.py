"""Exact offline dependencies for already authored opaque panels; no runtime permission."""
from collections import Counter
from fractions import Fraction as F
from itertools import product

def area(poly):
 return abs(sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(poly,poly[1:]+poly[:1])))

def clip(poly,a,b,inside):
 result=[]
 def d(p):return(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
 for s,e in zip(poly,poly[1:]+poly[:1]):
  ds,de=d(s),d(e);si=ds>=0 if inside else ds<=0;ei=de>=0 if inside else de<=0
  if si:result.append(s)
  if si!=ei:
   t=ds/(ds-de);result.append((s[0]+t*(e[0]-s[0]),s[1]+t*(e[1]-s[1])))
 return result if len(result)>=3 and area(result)>0 else []

def subtract(poly,triangle):
 remain=poly;outside=[]
 for a,b in zip(triangle,triangle[1:]+triangle[:1]):
  q=clip(remain,a,b,False)
  if q:outside.append(q)
  remain=clip(remain,a,b,True)
  if not remain:break
 return outside

def exact_sources(triangles):
 result=[]
 for source in triangles:
  if len(source)!=3 or any(len(v)!=3 for v in source):raise ValueError('exact xyz triangles required')
  result.append(tuple(tuple(F(x)for x in v)for v in source))
 if not result or len(result)>32:raise ValueError('one to32 stable source IDs required')
 return result

def protected_rect(panel,margin):
 c=[tuple(F(x)for x in v)for v in panel['corners']]
 if len(c)!=4 or any(len(v)!=3 for v in c)or len({v[2]for v in c})!=1:raise ValueError('existing axis-aligned planar rectangle required')
 l,b,z=c[0];rr,t,_=c[2]
 if not l<rr or not b<t or c!=[(l,b,z),(rr,b,z),(rr,t,z),(l,t,z)]:raise ValueError('existing rectangle orientation/extent differs')
 m=F(margin)
 if m<0:raise ValueError('nonnegative protection margin required')
 return[(l-m,b-m),(rr+m,b-m),(rr+m,t+m),(l-m,t+m)]

def projected(source):
 tri=[(v[0],v[1])for v in source]
 signed=sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(tri,tri[1:]+tri[:1]))
 if signed<0:tri.reverse()
 return tri if signed else []

def boundary_edges(sources,ids):
 edges=Counter()
 for index in ids:
  a,b,c=sources[index]
  for u,v in((a,b),(b,c),(c,a)):
   if edges[v,u]:edges[v,u]-=1
   else:edges[u,v]+=1
 return[edge for edge,n in edges.items()for _ in range(n)]

def certify(sources,ids,panels,margin=100):
 if not panels:raise ValueError('at least one existing panel required')
 edges=boundary_edges(sources,ids);checks=[]
 for panel in panels:
  rect=protected_rect(panel,margin);remain=[rect]
  for index in ids:
   tri=projected(sources[index])
   if tri:remain=[p for poly in remain for p in subtract(poly,tri)]
   if not remain:break
  l,b=rect[0];rr,t=rect[2]
  touches=sum(max(a[0],c[0])>=l and min(a[0],c[0])<=rr and max(a[1],c[1])>=b and min(a[1],c[1])<=t for a,c in edges)
  checks.append(dict(exact_remaining_polygons=len(remain),exact_remaining_double_area=str(sum(area(p)for p in remain)),unmatched_edges_touching_expanded_panel=touches))
 return dict(valid=all(not c['exact_remaining_polygons']and not c['unmatched_edges_touching_expanded_panel']for c in checks),panels=checks,unmatched_edges=len(edges))

def select_dependencies(triangles,panels,margin=100):
 """Stable original-ID deletion, deletion-irredundant under coverage AND seam validation."""
 sources=exact_sources(triangles);selected=list(range(len(sources)));removed=[]
 if not certify(sources,selected,panels,margin)['valid']:raise ValueError('original roster does not certify every protected panel/seam')
 for index in range(len(sources)):
  trial=[i for i in selected if i!=index]
  if certify(sources,trial,panels,margin)['valid']:selected=trial;removed.append(index)
 proof=certify(sources,selected,panels,margin)
 if not proof['valid']or any(certify(sources,[j for j in selected if j!=i],panels,margin)['valid']for i in selected):raise ValueError('dependency selection not certified/irredundant')
 return dict(selected_dependency_ids=selected,removed_dependency_ids=removed,required_coverage_mask=sum(1<<i for i in selected),protection_margin_mm=margin,selection='ascending stable original-ID deletion; exact expanded-panel union and reversed-edge boundary exclusion',deletion_irredundant_under_validator=True,**proof)

def check_frontside_and_slab(triangles,selected,panels,min_front=100):
 sources=exact_sources(triangles);distance2=F(min_front)**2;checks=0
 for panel in panels:
  z=F(panel['corners'][0][2]);half=F(panel['half']);eye=list(map(F,panel['frontside_eye_box']))
  if len(eye)!=6 or any(eye[i]>eye[i+1]for i in(0,2,4)):raise ValueError('existing frontside eye box required')
  for index in selected:
   a,b,c=sources[index];u=[b[i]-a[i]for i in range(3)];v=[c[i]-a[i]for i in range(3)]
   n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];norm2=sum(x*x for x in n)
   if not norm2 or any(abs(p[2]-z)>half for p in(a,b,c)):raise ValueError('selected source escapes unchanged normal slab')
   for e in product(eye[:2],eye[2:4],eye[4:]):
    d=sum(n[i]*(e[i]-a[i])for i in range(3))
    if d<=0 or d*d<=distance2*norm2:raise ValueError('selected source fails exact frontside distance')
    checks+=1
 return dict(all_eye_box_corners_exact_distance_gt_mm=min_front,exact_frontside_checks=checks,unchanged_normal_slab=True)

def bind_quantized_identity(bindings,point,identity):
 if point in bindings and bindings[point]!=identity:raise ValueError('shared world point has mismatched mesh/grid/quantized identity')
 bindings[point]=identity

def validate_lod_coverage(records,required_mask):
 if not 0<required_mask<=0xffffffff:raise ValueError('nonempty32-bit dependency mask required')
 covered=[0,0,0]
 for record in records:
  level,bit=record['level'],record['coverage_bit']
  if type(level)is not int or level not in(0,1,2)or type(bit)is not int or not 0<=bit<32 or not(required_mask&(1<<bit)):raise ValueError('unknown LOD or unselected dependency bit')
  covered[level]|=1<<bit
 if covered!=[required_mask]*3:raise ValueError('every selected package LOD must cover the complete dependency mask')
 return covered
