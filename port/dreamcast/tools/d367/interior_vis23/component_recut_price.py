#!/usr/bin/env python3
"""Price source-edge component children without emitting or admitting a package.

Each child retains complete original strips and exact twelve-byte corner data.
Strips bridging multiple components remain in a fallback child. Original cluster
LOD selection/affine/material/ownership stay unchanged. No merging, world baking,
portal proof, source-state admission, target build or timing claim is performed.
"""
import argparse, collections, hashlib, importlib, json, sys
from pathlib import Path
import numpy as np


def strip_records(p,li):
    le=p.lets[li];corners,_=p.let_tris(li)
    pos=p.o_strip+le['first_strip']+(2*le['vc'] if le['sc']&0x8000 else 0)
    end=pos+le['strip_bytes'];out=[];ti=0
    while pos<end:
        n=p.m[pos];ix=list(p.m[pos+1:pos+1+n]);pos+=n+1
        out.append((ix,ti));ti+=max(0,n-2)
    if pos!=end:raise ValueError('Strip extent')
    return corners,out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',required=True,type=Path);ap.add_argument('--inputs',required=True,type=Path)
    ap.add_argument('--room',required=True);ap.add_argument('--camera',required=True,type=Path)
    ap.add_argument('--profile-receipt',required=True,type=Path);ap.add_argument('--lod-px',required=True,type=float)
    ap.add_argument('--topology',required=True,type=Path,action='append');ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();sys.path.insert(0,str(a.helper_dir));est=importlib.import_module('estimate');inp=importlib.import_module('inputs')
    source=json.loads(a.inputs.read_text())[a.room];D,files=est.load(source);p=D['p']
    topology=[json.loads(f.read_text()) for f in a.topology];models={};groups={};seen=set()
    for fi,top in enumerate(topology):
        if top['room']!=a.room:raise ValueError('Wrong topology room')
        for k,v in top['inputs'].items():
            if v['sha256']!=inp.identity(files[k])['sha256']:raise ValueError('Topology input mismatch')
        pi=top['placement'];tri_components={};component_lets=collections.defaultdict(set)
        for comp,c in enumerate(top['components']):
            name=f'{fi}:{comp}';groups[name]=dict(topology=fi,component=comp,triangles=c['triangles'],lo=c['lo'],hi=c['hi'])
            for t in c['source_triangles']:
                key=(t['meshlet'],t['triangle'])
                if key in tri_components:raise ValueError('Duplicate source triangle')
                tri_components[key]=(name,t['q']);component_lets[name].add(t['meshlet'])
        for li in sorted({k[0] for k in tri_components}):
            if (pi,li) in seen:raise ValueError('Overlapping topology inputs')
            seen.add((pi,li));corners,strips=strip_records(p,li);buckets=collections.defaultdict(list)
            canonical=[]
            for si,(ix,ti) in enumerate(strips):
                owners=set()
                for k in range(len(ix)-2):
                    winding=(ix[k],ix[k+1],ix[k+2]) if k%2==0 else (ix[k+2],ix[k+1],ix[k])
                    q=[tuple(int(x) for x in corners[j,:3]) for j in winding]
                    nonzero=len(set(q))==3 and np.any(np.cross(np.subtract(q[1],q[0]),np.subtract(q[2],q[0])))
                    if nonzero:
                        name,expected=tri_components[(li,ti+k)]
                        if q!=[tuple(v) for v in expected]:raise ValueError('Topology triangle differs from current source')
                        owners.add(name)
                    canonical.append(b''.join(corners[j].astype('<u2').tobytes() for j in winding))
                bucket=next(iter(owners)) if len(owners)==1 else 'fallback'
                buckets[bucket].append((si,ix))
            children=[];restored=[]
            for name,ss in buckets.items():
                used=sorted({j for _,ix in ss for j in ix});remap={j:i for i,j in enumerate(used)}
                child=corners[used]
                for si,ix in ss:
                    rr=[remap[j] for j in ix]
                    for k in range(len(rr)-2):
                        old=(ix[k],ix[k+1],ix[k+2]) if k%2==0 else (ix[k+2],ix[k+1],ix[k])
                        new=(rr[k],rr[k+1],rr[k+2]) if k%2==0 else (rr[k+2],rr[k+1],rr[k])
                        ob=b''.join(corners[j].astype('<u2').tobytes() for j in old)
                        nb=b''.join(child[j].astype('<u2').tobytes() for j in new)
                        if ob!=nb:raise ValueError('Recut changed ordered triangle/corner attributes')
                        restored.append((si,k,nb))
                children.append(dict(component=name,nv=len(used),strips=[si for si,_ in ss],corner_indices=used,
                                     strip_bytes=sum(1+len(ix) for _,ix in ss)))
            restored.sort();digest=lambda seq:hashlib.sha256(b''.join(seq)).hexdigest()
            if digest(canonical)!=digest([v for _,_,v in restored]):raise ValueError('Recut reordered or lost triangle')
            models[(pi,li)]=dict(children=children,original_nv=len(corners),ordered_triangle_sha256=digest(canonical),
                                 corner_duplication=sum(c['nv'] for c in children)-len(corners),original_strips=[ix for ix,_ in strips])
    cams=est.cameras(a.camera);stats={name:[] for name in groups};base_rows=[]
    for frame,cam in cams:
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19]
        pairs,_,_=est.selection(D,V,P,near,far,a.lod_px);base=sum(x['nv'] for x in pairs.values())
        ref=est.sg.view_counts(D,V,P,near,far,a.lod_px)
        if base!=ref['T1' if D['SG'] is not None else 'T0']:raise ValueError('SG reference mismatch')
        base_rows.append(dict(frame=frame,corners=base,meshlets=len(pairs)))
        for name in groups:
            saved=extra_calls=active=0;raw=0
            for key,m in models.items():
                if key not in pairs:continue
                x=pairs[key];hidden=[c for c in m['children'] if c['component']==name]
                if not hidden:continue
                raw+=x['nv']
                if not any(x['walk'][si] for c in hidden for si in c['strips']):continue
                kept=[c for c in m['children'] if c['component']!=name]
                # Conservative price: all retained child corners, no child SG/frustum credit.
                saved+=x['nv']-sum(c['nv'] for c in kept);extra_calls+=len(kept)-1;active+=1
            stats[name].append(dict(frame=frame,net_saved_corners=saved,extra_meshlet_draws=extra_calls,
                                    affected_original_meshlets=active,mixed_original_corner_upper=raw))
    for name,r in groups.items():
        r['mean']={k:float(np.mean([v[k] for v in stats[name]])) for k in stats[name][0] if k!='frame'}
        r['rows']=stats[name]
        variants=[]
        for (pi,li),m in models.items():
            hidden={si for c in m['children'] if c['component']==name for si in c['strips']}
            if not hidden:continue
            retained=[(si,ix) for si,ix in enumerate(m['original_strips']) if si not in hidden]
            used=sorted({j for _,ix in retained for j in ix})
            corners,_=p.let_tris(li);child=corners[used];remap={j:i for i,j in enumerate(used)}
            original_bytes=[];child_bytes=[]
            for si,ix in retained:
                rr=[remap[j] for j in ix]
                for k in range(len(ix)-2):
                    old=(ix[k],ix[k+1],ix[k+2]) if k%2==0 else (ix[k+2],ix[k+1],ix[k])
                    new=(rr[k],rr[k+1],rr[k+2]) if k%2==0 else (rr[k+2],rr[k+1],rr[k])
                    original_bytes.append(b''.join(corners[j].astype('<u2').tobytes() for j in old))
                    child_bytes.append(b''.join(child[j].astype('<u2').tobytes() for j in new))
            if original_bytes!=child_bytes:raise ValueError('Dedicated variant changed retained ordered triangle stream')
            retained_digest=hashlib.sha256(b''.join(original_bytes)).hexdigest()
            # One compact retained child stores remaining complete strips in original order.
            # It is used only after this one component is proven hidden; otherwise draw original.
            variants.append(dict(placement=pi,meshlet=li,retained_strips=[si for si,_ in retained],
                                 corner_count=len(used),strip_bytes=sum(1+len(ix) for _,ix in retained),
                                 source_strip_order_retained=True,ordered_retained_triangle_sha256=retained_digest))
        r['two_way_variant_geometry_bytes']=sum(v['corner_count']*12+v['strip_bytes']+28 for v in variants if v['retained_strips'])
        r['two_way_variant_SG_bytes']=sum(16*D['G'] for v in variants if v['retained_strips']) if D['SG'] is not None else 0
        r['two_way_variant_children']=variants
        r['two_way_variant_extra_draw_upper_bound']=0
        r['two_way_variant_note']='One dedicated hide-this-component variant emits remaining complete strips in source order with at most one retained child per original draw. Other LODs/mixed strips stay fallback; runtime, memory and pixels are unqualified.'
    children=[c for m in models.values() for c in m['children']]
    added=sum(c['nv']*12+c['strip_bytes']+28 for c in children)
    sg_added=sum(16*D['G'] for _ in children) if D['SG'] is not None else 0
    out=dict(kind='LOSSLESS COMPONENT RECUT PRICE ONLY; hypothetical component hidden in every view, no portal or runtime admission',
             inputs=source,camera=inp.identity(a.camera),topology=[inp.identity(f) for f in a.topology],
             tool=inp.identity(Path(__file__)),helpers=[inp.identity(Path(mod.__file__)) for mod in (est,inp,est.sg,sys.modules[est.sg.Pkg.__module__])],selection_policy=inp.lod_policy(a.lod_px,a.profile_receipt),
             groups=groups,base_rows=base_rows,models=[dict(placement=pi,meshlet=li,**m) for (pi,li),m in models.items()],
             added_original_retained_geometry_bytes=added,additional_SG_bytes=sg_added,
             additional_descriptor_count=len(children),corner_duplication=sum(m['corner_duplication'] for m in models.values()),
             assumptions=['no portal invisibility or all-LOD source closure has been proven',
                          'only supplied source LOD components priced; other levels unchanged fallback',
                          'complete original strips retained; cross-component strips remain fallback',
                          'source triangle order reconstructed and twelve-byte attributes/winding reverified; grouped child draw order NOT qualified',
                          'original draw path retained unless a proven hidden component activates its children',
                          'partial-child price pays all kept corners without new SG/frustum savings',
                          'room metadata, runtime cull work and target memory qualification remain unpriced'])
    with a.out.open('x') as f:json.dump(out,f,indent=2)
    print(json.dumps(dict(groups={k:{kk:vv for kk,vv in v.items() if kk!='rows'} for k,v in groups.items()},
                         added_geometry_bytes=added,SG_bytes=sg_added,corner_duplication=out['corner_duplication'])))

if __name__=='__main__':main()
