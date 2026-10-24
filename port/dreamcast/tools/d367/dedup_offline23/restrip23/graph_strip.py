"""Opaque graph stripification estimate; material/tie admission is caller-owned."""
from collections import Counter,defaultdict
from ordered_strip import triangles
def canonical(t):return min(tuple(t),tuple(t[1:]+t[:1]),tuple(t[2:]+t[:2]))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def segment_hits(p,q,t):
 a,b,c=t;d=sub(q,p);e1=sub(b,a);e2=sub(c,a);h=cross(d,e2);det=dot(e1,h)
 if not det:return False
 v=sub(p,a);u=dot(v,h);w=cross(v,e1);vv=dot(d,w);tt=dot(e2,w)
 if det<0:det,u,vv,tt=-det,-u,-vv,-tt
 return 0<=u<=det and 0<=vv and u+vv<=det and 0<tt<det
def overlap2(a,b,normal):
 k=max(range(3),key=lambda x:abs(normal[x]));axes=[j for j in range(3) if j!=k]
 aa=[tuple(p[j] for j in axes) for p in a];bb=[tuple(p[j] for j in axes) for p in b]
 for poly in (aa,bb):
  for p,q in zip(poly,poly[1:]+poly[:1]):
   axis=(q[1]-p[1],p[0]-q[0]);x=[dot(v,axis) for v in aa];y=[dot(v,axis) for v in bb]
   if max(x)<=min(y) or max(y)<=min(x):return False
 return True
def tie_risks(strips,corners):
 ts=triangles(strips);pts=[tuple(tuple(corners[q][:3]) for q in t) for t in ts]
 normals=[cross(sub(b,a),sub(c,a)) for a,b,c in pts];risks=Counter()
 if any(n==(0,0,0) for n in normals):risks['degenerate']=1
 keys=defaultdict(set)
 for s in strips:
  for q in s:keys[tuple(corners[q][:3])].add(tuple(corners[q]))
 if any(len(v)>1 for v in keys.values()):risks['attribute_seam']=1
 faces=Counter(tuple(sorted(t)) for t in pts)
 if any(n>1 for n in faces.values()):risks['duplicate_position_face']=1
 edges=Counter(tuple(sorted((a,b))) for t in pts for a,b in zip(t,t[1:]+t[:1]))
 if any(n>2 for n in edges.values()):risks['nonmanifold_position_edge']=1
 # Exact integer grid tests; no floating tolerance can silently declare safe.
 for i,a in enumerate(pts):
  if normals[i]==(0,0,0):continue
  for j in range(i+1,len(pts)):
   b=pts[j]
   if normals[j]==(0,0,0):continue
   if cross(normals[i],normals[j])==(0,0,0):
    if dot(normals[i],sub(b[0],a[0]))==0 and overlap2(a,b,normals[i]):risks['coplanar_positive_area_overlap']=1
   elif any(segment_hits(p,q,b) for p,q in zip(a,a[1:]+a[:1])) or any(segment_hits(p,q,a) for p,q in zip(b,b[1:]+b[:1])):
    risks['crossing_surface']=1
 return dict(risks)
def graph_partition(strips,corners,rotations=False):
 old=[list(s) for s in strips];before=triangles(old)
 ids=[];seen={}
 for i,c in enumerate(corners):ids.append(seen.setdefault(tuple(c),i))
 ts=[tuple(ids[q] for q in t) for t in before]
 edge=defaultdict(list)
 for i,t in enumerate(ts):
  for j in range(3 if rotations else 1):
   r=t[j:]+t[:j];edge[r[:2]].append((i,r[2],j))
 remain=set(range(len(ts)));result=[]
 def next_options(path,used):
  a,b=path[-2:];pair=(b,a) if (len(path)-2)&1 else (a,b)
  return [(i,c,j) for i,c,j in edge[pair] if i in remain and i not in used]
 def degree(i):
  t=ts[i];return sum(sum(v in remain and v!=i for v,_,_ in edge[(b,a)]) for a,b in zip(t,t[1:]+t[:1]))
 while remain:
  options=[]
  for root in sorted(remain,key=lambda i:(degree(i),i))[:16]:
   for rotation in range(3 if rotations else 1):
    start=ts[root][rotation:]+ts[root][:rotation]
    for reverse_score in (False,True):
     path=list(start);used={root};order=[root]
     while len(path)<255:
      cand=next_options(path,used)
      if not cand:break
      i,c,_=min(cand,key=lambda v:((-1 if reverse_score else 1)*len(next_options(path+[v[1]],used|{v[0]})),v[0],v[2]))
      path.append(c);used.add(i);order.append(i)
     options.append((path,used,order))
  path,used,_=min(options,key=lambda v:(-len(v[0]),tuple(v[2]),tuple(v[0])))
  remain-=used;result.append(path)
 decode=lambda ss:[tuple(tuple(corners[q]) for q in t) for t in triangles(ss)]
 a,b=decode(old),decode(result)
 if Counter(canonical(t) for t in a)!=Counter(canonical(t) for t in b):raise AssertionError('attribute/winding/multiplicity changed')
 if not rotations and Counter(a)!=Counter(b):raise AssertionError('provoking tuple changed')
 if sum(map(len,result))>=sum(map(len,old)):return old
 return result


def topology_bound(strips,corners):
 """Optimistic corner floor for ALL triangles in a group, allowing cyclic order.
 Any strip is a simple path in this full-attribute oriented adjacency graph.
 Each connected component needs a strip; each degree-one triangle an endpoint.
 It also needs ceil(triangles/253) strips. This relaxes parity/branch constraints,
 tie/provoking/degenerate/clip constraints, so is a lower floor, not a solution.
 """
 ts=triangles(strips);edge=defaultdict(list);adj=[set() for t in ts]
 for i,t in enumerate(ts):
  tt=[tuple(corners[q]) for q in t]
  for a,b in zip(tt,tt[1:]+tt[:1]):edge[a,b].append(i)
 for (a,b),ix in edge.items():
  for i in ix:
   for j in edge.get((b,a),[]):
    if i!=j:adj[i].add(j)
 remain=set(range(len(ts)));floor=0;components=0;leaves=0
 while remain:
  todo=[next(iter(remain))];found=set()
  while todo:
   i=todo.pop()
   if i in found:continue
   found.add(i);todo.extend(adj[i]-found)
  remain-=found;leaf=sum(len(adj[i])==1 for i in found);leaves+=leaf;components+=1
  floor+=max(1,(leaf+1)//2,(len(found)+252)//253)
 # Empty groups contribute zero. Nonmanifold/degenerate identities are retained.
 assert floor<=len(strips), (floor,len(strips))
 return dict(triangles=len(ts),components=components,degree_one_triangles=leaves,min_strips=floor,min_corners=len(ts)+2*floor)
