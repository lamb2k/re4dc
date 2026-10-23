#!/usr/bin/env python3
"""Price every unresolved boundary loop as a whole opening; never admit a cell.

Exact grid-edge loops come from surface_components.py. Caps are enclosed by
padded world AABBs, so unknown bottom/top/seam boundaries stay openings. This
camera diagnostic cannot prove a manifold/non-self-intersecting closed hull,
inside/outside membership, all-LOD coverage, material opacity or live pose.
"""
import argparse, collections, importlib, json, sys
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',required=True,type=Path);ap.add_argument('--inputs',required=True,type=Path)
    ap.add_argument('--room',required=True);ap.add_argument('--topology',required=True,type=Path)
    ap.add_argument('--component',required=True,type=int);ap.add_argument('--camera',required=True,type=Path)
    ap.add_argument('--pad-mm',required=True,type=float);ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();sys.path.insert(0,str(a.helper_dir));est=importlib.import_module('estimate');inp=importlib.import_module('inputs')
    if not np.isfinite(a.pad_mm) or a.pad_mm<0:raise ValueError('Invalid pad')
    top=json.loads(a.topology.read_text());D,files=est.load(json.loads(a.inputs.read_text())[a.room])
    if top['room']!=a.room:raise ValueError('Wrong topology room')
    for key,value in top['inputs'].items():
        if value['sha256']!=inp.identity(files[key])['sha256']:raise ValueError('Topology source mismatch')
    c=top['components'][a.component];adj=collections.defaultdict(list);pending=set()
    for e in c['boundary_grid_edges']:
        v,w=map(tuple,e);adj[v].append(w);adj[w].append(v);pending.add(tuple(sorted((v,w))))
    failure=None;loops=[]
    if any(len(v)!=2 for v in adj.values()):failure='Boundary vertex degree is not two; unresolved surface stays visible'
    if c['nonmanifold_edges'] or c['same_direction_edges']:failure='Nonmanifold or inconsistent edge winding; unresolved surface stays visible'
    if not failure:
        while pending:
            start,cur=min(pending);previous=start;loop=[start]
            pending.remove(tuple(sorted((start,cur))))
            while cur!=start:
                loop.append(cur);choices=[v for v in adj[cur] if v!=previous]
                if len(choices)!=1:raise ValueError('Bad boundary cycle')
                nex=choices[0];edge=tuple(sorted((cur,nex)))
                if edge not in pending:raise ValueError('Boundary cycle repeated an edge')
                pending.remove(edge);previous,cur=cur,nex
            loops.append(loop)
    M=D['WQ'][top['placement']];portals=[]
    for loop in loops:
        xyz=np.array(loop)@M[:,:3].T+M[:,3];lo=xyz.min(0)-a.pad_mm;hi=xyz.max(0)+a.pad_mm
        portals.append(dict(edge_count=len(loop),grid_loop=loop,lo=lo.tolist(),hi=hi.tolist()))
    rows=[]
    for frame,cam in est.cameras(a.camera):
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19];visible=[]
        for i,portal in enumerate(portals):
            lo=np.array(portal['lo']);hi=np.array(portal['hi']);center=(lo+hi)*.5;extent=(hi-lo)*.5
            v=(V[:,:3]@center+V[:,3])[None];r=(np.abs(V[:,:3])@extent)[None]
            ac,bc=est.sg.side_coefs(P);outside,_,_=est.sg.classify(v,r,ac,bc,near,far,False)
            if not outside[0]:visible.append(i)
        rows.append(dict(frame=frame,visible_unresolved_openings=visible,all_openings_out=not failure and bool(portals) and not visible))
    out=dict(kind='UNRESOLVED BOUNDARY OPENING CAMERA PRICE; no cell, target membership or runtime admission',
             tool=inp.identity(Path(__file__)),helpers=[inp.identity(Path(mod.__file__)) for mod in (est,inp,est.sg,sys.modules[est.sg.Pkg.__module__])],topology=inp.identity(a.topology),component=a.component,
             camera=inp.identity(a.camera),pad_mm=a.pad_mm,fail_open_reason=failure,portals=portals,rows=rows,
             all_openings_out_views=sum(r['all_openings_out'] for r in rows),
             notes=['unknown bottom/top/seam loops are whole openings, never filled by assumption',
                    'every candidate cap lies in its loop convex hull and padded world AABB',
                    'all-openings-out is only a camera prerequisite, never a visibility proof',
                    'closed hull orientation/self-intersection and all-LOD membership remain unproved',
                    'source material, actual selected pose/LOD and numeric receipts remain required'])
    with a.out.open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(dict(component=a.component,loops=len(portals),failure=failure,all_openings_out_views=out['all_openings_out_views'],views=len(rows))))

if __name__=='__main__':main()
