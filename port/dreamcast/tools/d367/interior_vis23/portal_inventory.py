#!/usr/bin/env python3
"""Price ownership cohorts before attempting an interior/portal proof.

This is an optimistic geometry ceiling, never visibility or liveness admission.
A repeated owner ID is not proof of static state or one physical house. Output
contains private asset bounds/ownership and belongs in private evidence only.
"""
import argparse, collections, importlib, json, struct, sys
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',required=True,type=Path)
    ap.add_argument('--inputs',required=True,type=Path)
    ap.add_argument('--room',required=True)
    ap.add_argument('--camera',required=True,type=Path)
    ap.add_argument('--lod-px',required=True,type=float)
    ap.add_argument('--profile-receipt',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    sys.path.insert(0,str(args.helper_dir))
    est=importlib.import_module('estimate')
    inp=importlib.import_module('inputs')
    helper_paths=[Path(est.__file__),Path(inp.__file__),Path(est.sg.__file__),Path(est.sg.Pkg.__module__ and sys.modules[est.sg.Pkg.__module__].__file__)]
    helpers=[inp.identity(p) for p in helper_paths]
    source=json.loads(args.inputs.read_text())[args.room]
    D,files=est.load(source);p=D['p'];ids=files['ids'].read_bytes()
    magic,version,n,crc=struct.unpack_from('<4sIII',ids)
    if magic!=b'R4ID' or version!=1 or n!=len(p.placements) or len(ids)<16+n:raise ValueError('Bad ownership IDs')
    raw_owners=list(ids[16:16+n]);owners=[raw_owners[pl['placement']] for pl in p.placements];multiplicity=collections.Counter(owners)
    meta={};parts={};placement_rows={}
    for pi,pl in enumerate(p.placements):
        mi=pl['mesh'];mesh=p.meshes[mi];M=D['WQ'][pi]
        placement_rows[pi]=dict(placement=pi,field=pl['placement'],owner=owners[pi],
                               owner_multiplicity=multiplicity[owners[pi]],mesh=mi,parts=[])
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            fc,cc=p.plod[part];points=[];meshlets=[]
            for ci in range(fc,fc+cc):
                cl=p.clusters[ci]
                for lv in range(cl['first_level'],cl['first_level']+cl['level_count']):
                    fm,mc,_=p.levels[lv]
                    for li in range(fm,fm+mc):
                        key=(pi,li)
                        if key in meta:raise ValueError('Meshlet appears in two instance clusters')
                        meta[key]=dict(part=part,cluster=ci,level=lv-cl['first_level'],owner=owners[pi],pass_=p.pmeta[part]['pass_'])
                        cg=D['CG'][D['c0'][li]:D['c0'][li+1]]
                        points.append(cg@M[:,:3].T+M[:,3]);meshlets.append(li)
            pts=np.concatenate(points) if points else np.empty((0,3))
            parts[(pi,part)]=dict(placement=pi,part=part,owner=owners[pi],pass_=p.pmeta[part]['pass_'],
                                  all_lod_meshlets=meshlets,all_lod_lo=pts.min(0).tolist() if len(pts) else None,
                                  all_lod_hi=pts.max(0).tolist() if len(pts) else None)
            placement_rows[pi]['parts'].append(part)
    cams=est.cameras(args.camera);rows=[];totals=collections.defaultdict(collections.Counter)
    for frame,cam in cams:
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19]
        pairs,mv,tv=est.selection(D,V,P,near,far,args.lod_px)
        ref=est.sg.view_counts(D,V,P,near,far,args.lod_px)
        nv=sum(x['nv'] for x in pairs.values())
        if nv!=ref['T1' if D['SG'] is not None else 'T0']:raise ValueError('Selector/reference disagreement')
        row=dict(frame=frame,selected_corners=nv,selected_meshlets=len(pairs),owners={},placements={})
        for (pi,li),x in pairs.items():
            m=meta[(pi,li)];part=m['part'];owner=m['owner'];pas=m['pass_']
            for typ,key in (('owner',owner),('placement',pi),('part',(pi,part)),('meshlet',(pi,li))):
                c=totals[(typ,key)];c['selected_corners']+=x['nv'];c['selected_meshlets']+=1
                c['opaque_corners']+=x['nv'] if pas==0 else 0
                c['opaque_meshlets']+=int(pas==0)
                c['walked_strips']+=int(x['walk'].sum())
            for typ,key in (('owners',owner),('placements',pi)):
                c=row[typ].setdefault(str(key),dict(corners=0,opaque_corners=0,meshlets=0))
                c['corners']+=x['nv'];c['opaque_corners']+=x['nv'] if pas==0 else 0;c['meshlets']+=1
        rows.append(row)
    def mean(typ,key):return {k:v/len(cams) for k,v in totals[(typ,key)].items()}
    for (pi,part),r in parts.items():r['mean']=mean('part',(pi,part))
    for pi,r in placement_rows.items():r['mean']=mean('placement',pi)
    owner_rows=[dict(owner=owner,placements=[i for i,v in enumerate(owners) if v==owner],
                     mean=mean('owner',owner)) for owner in sorted(multiplicity)]
    if helpers!=[inp.identity(p) for p in helper_paths]:raise ValueError('Helper changed during replay')
    out=dict(kind='OPTIMISTIC OWNERSHIP GEOMETRY CEILING; no culls, liveness proof or milliseconds',
             tool=inp.identity(Path(__file__)),helpers=helpers,inputs=source,camera=inp.identity(args.camera),
             selection_policy=inp.lod_policy(args.lod_px,args.profile_receipt),
             mean_selected_corners=float(np.mean([r['selected_corners'] for r in rows])),
             mean_selected_meshlets=float(np.mean([r['selected_meshlets'] for r in rows])),
             owners=owner_rows,placements=list(placement_rows.values()),parts=list(parts.values()),rows=rows,
             meshlet_instances=[dict(placement=pi,meshlet=li,**m,mean=mean('meshlet',(pi,li))) for (pi,li),m in meta.items()],
             assumptions=['exact baked physical affine only; dynamic state not reproduced',
                          'all target LOD corner bounds retained per source part',
                          'actual SG contiguous transform ranges and walked strips',
                          'every requested camera checked against independent SG count selector',
                          'owner IDs can span multiple houses and interior/exterior skins',
                          'no opening, hull closure, receiver, numeric receipt or source state admission'])
    with args.out.open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(dict(room=args.room,views=len(cams),mean_selected_corners=out['mean_selected_corners'],
                         owners=sorted(owner_rows,key=lambda r:r['mean'].get('opaque_corners',0),reverse=True)[:12])))

if __name__=='__main__':main()
