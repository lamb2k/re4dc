#!/usr/bin/env python3
"""Bounded one-component semantic wall-plane proof, existing source material."""
import collections
import json
import math
from pathlib import Path
import sys

def build(d,w,dependencies,diagnostic):
    sys.path.insert(0,str(dependencies))
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    pi=160;mi=104;m=d['meshes'][mi];fc,cc=d['part_lods'][pi]
    pl=next(p for p in d['placements'] if p[0]==mi);A=np.asarray(pl[2:]).reshape(3,4)
    triangles=[];identities=[]
    for ci in range(fc,fc+cc):
        for ti,t in enumerate(w.level_triangles(d,d['levels'][d['clusters'][ci][6]])):
            triangles.append(t);identities.append((ci,ti))
    parents={}
    def find(x):
        parents.setdefault(x,x)
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    for t in triangles:
        root=find(t[0][:3])
        for v in t[1:]:parents[find(v[:3])]=root
    groups=collections.defaultdict(list)
    for i,t in enumerate(triangles):groups[find(t[0][:3])].append(i)
    candidate=[]
    for ix in groups.values():
        if len(ix)!=145:continue
        q=np.asarray([[v[:3] for v in triangles[i]] for i in ix],float)
        local=q*np.asarray(m[11:14])+np.asarray(m[8:11]);world=local@A[:,:3].T+A[:,3]
        lo=world.reshape(-1,3).min(0);hi=world.reshape(-1,3).max(0)
        if max(abs(lo-np.asarray([-1064,862,7826])))<3 and max(abs(hi-np.asarray([10666,5767,21110])))<3:candidate=ix
    assert len(candidate)==145,'Pinned near right-facade component mapping'
    q=np.asarray([[v[:3] for v in triangles[i]] for i in candidate],float)
    xyz=q*np.asarray(m[11:14]);nn=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);areas=np.linalg.norm(nn,axis=1)
    normals=nn/np.maximum(areas[:,None],1e-12);centers=xyz.mean(1)
    choices=[]
    for seed in range(len(candidate)):
        n=normals[seed]
        if abs(n[1])>.25:continue # Explicit vertical facade plane, roofs excluded.
        distances=np.abs((xyz-xyz[seed,0])@n).max(1)
        keep=(normals@n>.999)&(distances<20)
        ids=np.where(keep)[0];total=float(areas[ids].sum())
        choices.append((total,seed,ids))
    choices.sort(key=lambda v:v[0],reverse=True)
    total,seed,indices=choices[0];n=normals[seed]
    origin=xyz[seed,0];u=xyz[seed,1]-origin;u/=np.linalg.norm(u);v=np.cross(n,u)
    projected=(xyz-origin)@np.stack([u,v]).T
    polygons=[Polygon(projected[i]) for i in indices]
    union=shapely.unary_union(polygons)
    result=dict(component_triangles=145,component_source_ids=[identities[i] for i in candidate],selected_plane_triangles=len(indices),selected_ids=[identities[candidate[i]] for i in indices],normal=n.tolist(),origin=origin.tolist(),plane_u=u.tolist(),plane_v=v.tolist(),maximum_plane_relief_local=float(np.abs((xyz[indices]-origin)@n).max()),union_type=union.geom_type,union_area=union.area,source_polygon_area_sum=sum(p.area for p in polygons),polygons=[])
    polys=list(union.geoms) if union.geom_type=='MultiPolygon' else [union]
    for poly in polys:
        result['polygons'].append(dict(exterior=list(poly.exterior.coords),holes=[list(h.coords) for h in poly.interiors],area=poly.area))
    diagnostic.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('selected_plane_triangles','maximum_plane_relief_local','union_type','union_area','source_polygon_area_sum')},indent=2))
    print('Polygon contours',[(len(p.exterior.coords),[len(h.coords) for h in p.interiors]) for p in polys])
    return result

if __name__=='__main__':
    sys.path.insert(0,'/root/work/lanes/world-rebuild27/port/dreamcast/tools')
    import world_rebuild27 as w
    root=Path('/root/re4data/private/world-rebuild27-20261027');d,files,owners,policy=w.load(root/'baseline-A/dc/native/r101')
    build(d,w,root/'proxy27-python-deps',root/'B2-one-facade-plane-proof.json')
