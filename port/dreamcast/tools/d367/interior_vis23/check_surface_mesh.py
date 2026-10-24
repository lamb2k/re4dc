"""Compare complete decoded source data to pinned numpy reference, read-only."""
import argparse,hashlib,importlib.util,json,struct,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--decoder',required=True,type=Path);p.add_argument('--reference',required=True,type=Path);p.add_argument('--mesh',required=True,type=Path);p.add_argument('--policy',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
x=load('new_surface',a.decoder).Pkg(a.mesh,a.policy);y=load('reference_surface',a.reference).Pkg(a.mesh,a.policy)
for k in ['magic','version','mesh_bytes','mesh_crc','sidecar_crc','pmeta','meshes','parts','plod','clusters','levels','lets']:
 assert getattr(x,k)==getattr(y,k),k
assert x.verts==[tuple(map(int,r)) for r in y.verts]
for i,(u,v) in enumerate(zip(x.placements,y.placements)):
 assert u['mesh']==v['mesh'] and u['placement']==v['placement'] and u['affine']==v['affine'].tolist(),i
assert len(x.placements)==len(y.placements)
triangles=0;corners=0
for li in range(x.nlet):
 u,ut=x.let_tris(li);v,vt=y.let_tris(li);assert u==[tuple(map(int,r)) for r in v] and ut==vt,li
 triangles+=len(ut);corners+=len(u)
r=dict(kind='Complete read-only decoder equality against pinned reference; not renderer/pixel equivalence',meshlets=x.nlet,placements=len(x.placements),corner_records=corners,ordered_triangles=triangles,all_headers_policy_affines_vertices_strips_equal=True,inputs={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [a.decoder,a.reference,a.mesh,a.policy]})
with a.out.open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))


