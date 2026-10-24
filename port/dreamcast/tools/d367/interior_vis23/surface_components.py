#!/usr/bin/env python3
"""Inspect exact grid-edge connectivity, never weld a source crack or certify a hull.

Components are per physical placement/LOD. Equal grid coordinates connect even
when UV/normal corners were split. Different coordinates never connect. Output
is private source geometry and must not be committed. This is topology research,
not conservative cell construction or runtime admission.
"""
import argparse, collections, importlib, json, sys
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',required=True,type=Path)
    ap.add_argument('--inputs',required=True,type=Path)
    ap.add_argument('--room',required=True)
    ap.add_argument('--placement',required=True,type=int)
    ap.add_argument('--parts',required=True,help='Comma-separated part indices owned by this placement')
    ap.add_argument('--level',required=True,type=int)
    ap.add_argument('--seed-meshlet',type=int)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args();sys.path.insert(0,str(args.helper_dir))
    est=importlib.import_module('estimate');inp=importlib.import_module('inputs')
    D,files=est.load(json.loads(args.inputs.read_text())[args.room]);p=D['p']
    if not 0<=args.placement<len(p.placements) or args.level<0:raise ValueError('Invalid placement/level')
    pl=p.placements[args.placement];mesh=p.meshes[pl['mesh']];M=D['WQ'][args.placement]
    parts=[int(x) for x in args.parts.split(',')]
    if len(set(parts))!=len(parts):raise ValueError('Repeated part')
    valid=set(range(mesh['first_part'],mesh['first_part']+mesh['part_count']))
    if not set(parts)<=valid:raise ValueError('Part not owned by placement')
    tris=[];edges=collections.defaultdict(list);degenerate=0
    for part in parts:
        fc,cc=p.plod[part]
        for ci in range(fc,fc+cc):
            cl=p.clusters[ci]
            if args.level>=cl['level_count']:raise ValueError('Requested LOD absent from a cluster')
            fm,mc,_=p.levels[cl['first_level']+args.level]
            for li in range(fm,fm+mc):
                corners,indices=p.let_tris(li)
                for ti,ix in enumerate(indices):
                    q=[tuple(int(v) for v in corners[i,:3]) for i in ix]
                    if len(set(q))<3 or not np.any(np.cross(np.subtract(q[1],q[0]),np.subtract(q[2],q[0]))):
                        degenerate+=1;continue
                    index=len(tris);tris.append(dict(part=part,cluster=ci,meshlet=li,triangle=ti,q=q))
                    for k in range(3):
                        a,b=q[k],q[(k+1)%3];edges[tuple(sorted((a,b)))].append((index,int(a<b)))
    parent=list(range(len(tris)))
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for uses in edges.values():
        root=find(uses[0][0])
        for i,_ in uses[1:]:parent[find(i)]=root
    groups=collections.defaultdict(list)
    for i in range(len(tris)):groups[find(i)].append(i)
    output=[]
    for members in groups.values():
        member_set=set(members);ts=[tris[i] for i in members];qs=sorted({v for t in ts for v in t['q']})
        xyz=np.array(qs)@M[:,:3].T+M[:,3]
        ee=[(edge,uses) for edge,uses in edges.items() if uses[0][0] in member_set]
        boundary=[edge for edge,uses in ee if len(uses)==1]
        output.append(dict(triangles=len(members),meshlets=sorted({t['meshlet'] for t in ts}),
                           clusters=sorted({t['cluster'] for t in ts}),parts=sorted({t['part'] for t in ts}),
                           lo=xyz.min(0).tolist(),hi=xyz.max(0).tolist(),
                           boundary_edges=len(boundary),nonmanifold_edges=sum(len(u)>2 for _,u in ee),
                           same_direction_edges=sum(len(u)==2 and u[0][1]==u[1][1] for _,u in ee),
                           seed_meshlet_present=args.seed_meshlet in {t['meshlet'] for t in ts},
                           boundary_grid_edges=boundary,source_triangles=ts))
    output.sort(key=lambda r:r['triangles'],reverse=True)
    out=dict(kind='EXACT GRID-EDGE TOPOLOGY DIAGNOSTIC; no hull or visibility admission',
             tool=inp.identity(Path(__file__)),helpers=[inp.identity(Path(mod.__file__)) for mod in (est,inp,est.sg,sys.modules[est.sg.Pkg.__module__])],inputs={k:inp.identity(v) for k,v in files.items()},
             room=args.room,placement=args.placement,parts=parts,level=args.level,
             degenerate_triangles_ignored=degenerate,components=output,
             warnings=['all nonzero-area faces retained regardless of material, cull or receiver eligibility',
                       'no approximate seam welding; source cracks remain boundary edges',
                       'different placements are never welded by this diagnostic',
                       'meshlet can mix components; component bounds do not prove all-LOD membership',
                       'closed edge graph alone does not prove an oriented non-self-intersecting hull'])
    with args.out.open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(dict(room=args.room,placement=args.placement,parts=parts,level=args.level,
                         components=[{k:v for k,v in r.items() if k not in ('boundary_grid_edges','source_triangles')} for r in output])))

if __name__=='__main__':main()
