"""Independent exact-real theorem controls; no scene data, renderer, or ray queries."""
from fractions import Fraction as F
from itertools import product
import json,resource
from pathlib import Path

def V(v): return tuple(F(x) for x in v)
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum((x*y for x,y in zip(a,b)),F(0))
def H(a,b,e,t): return dot(cross(sub(e,a),sub(b,a)),sub(t,a))
def plane(tri,p):
 a,b,c=tri;return dot(cross(sub(b,a),sub(c,a)),sub(p,a))
def proves(tri,eyes,targets,sigma=None):
 tri=tuple(map(V,tri));eyes=tuple(map(V,eyes));targets=tuple(map(V,targets))
 if len(tri)!=3 or not eyes or not targets or any(len(v)!=3 for v in (*tri,*eyes,*targets)): raise ValueError('arity')
 if not any(cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))):return False
 for s in ((1,-1) if sigma is None else (sigma,)):
  if s not in (-1,1):raise ValueError('orientation')
  if any(s*plane(tri,e)<=0 for e in eyes) or any(s*plane(tri,t)>=0 for t in targets):continue
  if all(s*H(tri[i],tri[(i+1)%3],e,t)>0 for i,e,t in product(range(3),eyes,targets)):return True
 return False

def bary_intersection(tri,e,t):
 tri=tuple(map(V,tri));e,t=V(e),V(t);de,dt=plane(tri,e),plane(tri,t);delta=de-dt
 assert delta
 weights=tuple(H(tri[i],tri[(i+1)%3],e,t)/delta for i in (1,2,0))
 assert sum(weights)==1
 x=tuple(e[k]+de/delta*(t[k]-e[k]) for k in range(3))
 assert x==tuple(sum(weights[i]*tri[i][k] for i in range(3)) for k in range(3))
 return weights,de/delta

def blend(points,weights):return tuple(sum(F(w)*p[k] for p,w in zip(points,weights)) for k in range(3))
def main(out):
 resource.setrlimit(resource.RLIMIT_AS,(268435456,)*2);records=[]
 def check(name,condition):
  assert condition,name
  records.append(name)
 tri=tuple(map(V,((-1,-1,0),(1,-1,0),(0,1,0))))
 eye=(V((0,0,1)),)
 target=tuple(map(V,((F(-8,5),F(-8,5),-1),(F(8,5),F(-8,5),-1),(0,F(8,5),-1))))
 check('whole actual target triangle positive',proves(tri,eye,target,1))
 box=tuple(product((F(-8,5),F(8,5)),(F(-8,5),F(8,5)),(-1,)))
 check('same target AABB refused',not proves(tri,eye,box,1))
 eyes=tuple(product((F(-1,16),F(1,16)),(F(-1,16),F(1,16)),(1,2)))
 large=tuple(map(V,((-4,-4,0),(4,-4,0),(0,4,0))))
 check('nonzero full eye volume positive',proves(large,eyes,target,1))
 for ei in range(len(eyes)):
  for ti in range(3):
   e=blend(eyes,[F(1,8)]*8);t=blend(target,[F(1,3)]*3)
   # Independent endpoint weighting identity, using nontrivial rational weights.
   ew=[F(1,8)]*8;tw=[F(1,3)]*3
   for i in range(3):
    assert H(large[i],large[(i+1)%3],e,t)==sum(ew[a]*tw[b]*H(large[i],large[(i+1)%3],ee,tt) for a,ee in enumerate(eyes) for b,tt in enumerate(target))
   weights,depth=bary_intersection(large,eyes[ei],target[ti]);assert min(weights)>0 and 0<depth<1
 check('tensor interpolation and exact barycentric identities',True)
 reverse=(tri[0],tri[2],tri[1])
 check('reversed geometric orientation requires matching uniform sign',proves(reverse,eye,target,-1) and not proves(reverse,eye,target,1))
 check('target before source refused',not proves(tri,eye,[(0,0,F(1,2))]))
 check('target touching plane refused',not proves(tri,eye,[(0,0,0)]))
 check('eye touching or straddling plane refused',not proves(tri,[(0,0,0)],target) and not proves(tri,[(0,0,1),(0,0,-1)],target))
 check('edge boundary strict refusal',not proves(tri,eye,[(-2,-2,-1)]))
 check('source degeneracy refused',not proves([(0,0,0),(1,0,0),(2,0,0)],eye,target))
 check('target degeneracy still satisfies convex hull theorem',proves(tri,eye,[(0,0,-1)]*3))
 check('one outside target vertex refuses whole face',not proves(tri,eye,[target[0],target[1],(0,3,-1)]))
 # Small source triangles individually cover only the three target vertices.
 patches=[]
 for t in target:
  x,y=t[0]/2,t[1]/2;r=F(1,20)
  patches.append(((x-r,y-r,0),(x+r,y-r,0),(x,y+r,0)))
 check('per vertex mixed-source hits do not imply any whole-face cover',all(proves(p,eye,[t]) for p,t in zip(patches,target)) and all(not proves(p,eye,target) for p in patches))
 center=blend(target,[F(1,3)]*3)
 check('mixed-source example has an uncovered interior point',all(not proves(p,eye,[center]) for p in patches))
 # Separate source per tested eye also cannot certify an entire eye cell.
 moving_eyes=(V((-1,0,1)),V((1,0,1)));point=(V((0,0,-1)),);eye_patches=[]
 for e in moving_eyes:
  x=e[0]/2;r=F(1,20);eye_patches.append(((x-r,-r,0),(x+r,-r,0),(x,r,0)))
 check('per eye mixed-source assignment leaves midpoint uncovered',all(proves(p,[e],point) for p,e in zip(eye_patches,moving_eyes)) and all(not proves(p,[(0,0,1)],point) for p in eye_patches))
 # Full Cartesian products are essential; matching endpoint labels is unsafe.
 a,b=V((0,0,0)),V((1,0,0));es=(V((0,-2,1)),V((0,2,1)));ts=(V((0,3,-1)),V((0,-1,-1)))
 check('matched E/T endpoint pairs can miss opposite edge sign',all(H(a,b,e,t)>0 for e,t in zip(es,ts)) and H(a,b,es[0],ts[1])<0)
 shifted=tuple((v[0]+3,v[1],v[2]) for v in tri)
 check('nominal source proof does not cover unbounded source perturbation',not proves(shifted,eye,target))
 result={'classification':'EXACT_REAL_SYNTHETIC_ONLY','groups':len(records),'controls':records,'scene_queries':0,'runtime_admitted':False,'proof_basis':'algebraic identities and convex tensor weights, not tested samples','limits':{'address_bytes':268435456,'jobs':1,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}}
 Path(out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 import sys
 main(sys.argv[1])
