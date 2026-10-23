#!/usr/bin/env python3
"""Fixed offline static batches, priced on real cameras. Geometry counts, not timing.

Never merge moving/uniquely owned, sky, repeated BIN, nonopaque or multi-LOD
sources. Keep original strips; concatenate small meshlets with identical material
and UV contracts, grouped by fixed world-space area cells. This intentionally
does not perform facing/occlusion rejection or redesign gameplay.
"""
import argparse, collections, hashlib, json, re, struct, sys
from pathlib import Path
import numpy as np
from inputs import hostpath, identity, validate_ownership, lod_policy
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'worldlean'))
import sgprice as sg


def cameras(path,first=500,last=794,stride=7):
    pattern=r'PS2CAM f=(\d+) cf=([0-9a-f]{8}) c=([0-9a-f ]+) p=([0-9a-f ]+) vp='
    found={}
    for match in re.finditer(pattern,Path(path).read_text(errors='replace')):
        frame=int(match[1]);words=match[3].split()+match[4].split()+[match[2]]
        if first<=frame<=last and len(words)==20:
            values=struct.unpack('<20f',struct.pack('<20I',*(int(x,16) for x in words)))
            if np.isfinite(values).all():found[frame]=values
    frames=list(range(first,last+1,stride))
    if any(f not in found for f in frames):raise ValueError('Missing an exact requested camera frame')
    return [(f,found[f]) for f in frames]


def load(row):
    files={k:hostpath(v['path']) for k,v in row['files'].items()}
    for key,p in files.items():
        if identity(p)['sha256']!=row['files'][key]['sha256']:raise ValueError('Input changed: '+str(p))
    validate_ownership(files,row['provenance'])
    return sg.load(files['re4mesh'],files['r4pw'],files.get('r4sg')),files


def excluded_placements(D,files,room):
    p=D['p'];dynamic=set();ids=files.get('ids')
    if ids:
        b=ids.read_bytes();magic,version,n,crc=struct.unpack_from('<4sIII',b)
        if magic!=b'R4ID' or version!=1 or n>len(b)-16:raise ValueError('Bad placement IDs')
        values=list(b[16:16+n]);counts=collections.Counter(values)
        dynamic.update(i for i,v in enumerate(values) if v<250 and counts[v]==1)
    else:
        raise ValueError('Placement ownership IDs required before proposing merges')
    # Exact production SKY_FAR rows and known gate-owned rows; r100 is never changed.
    if room=='r101':dynamic.update((0,1,2))
    return dynamic


def records(D,files,room):
    p=D['p'];dynamic=excluded_placements(D,files,room)
    # Appended sources can restart BIN/common/owner together. The actual shared
    # mesh record, not its source-number tuple, is the instancing identity.
    def model_identity(placement):
        return placement['mesh']
    bin_count=collections.Counter(model_identity(x) for x in p.placements)
    result={};reasons=collections.Counter()
    for ci,(pi,part,cl) in enumerate(zip(D['ci_pl'],D['ci_part'],D['ci_cl'])):
        pi,part,cl=int(pi),int(part),int(cl)
        placement=p.placements[pi];mesh=p.meshes[placement['mesh']]
        reason=None
        if placement['placement'] in dynamic:reason='live_owned_or_sky'
        elif bin_count[model_identity(placement)]!=1:reason='repeated_source_model'
        elif p.pmeta[part]['pass_']!=0:reason='nonopaque'
        elif p.clusters[cl]['level_count']!=1:reason='multiple_LOD_levels'
        # Full sidecar material (including marked alpha byte), alpha/flags and UV mapping.
        policy=files['r4pw'].read_bytes()[32+16*part:48+16*part]
        pr=p.m[p.o_part+36*part:p.o_part+36*(part+1)]
        if reason is None and (policy[15] or pr[9]!=255):reason='vertex_alpha_or_marked'
        fm,mc,_=p.levels[p.clusters[cl]['first_level']]
        if reason:
            reasons[reason]+=mc;continue
        # Source offsets/texture-slot number are not state; final texture key and UV mapping are.
        material=((policy[:14]+policy[15:]).hex(),pr[9:12].hex(),pr[20:36].hex())
        M=D['WQ'][pi]
        for li in range(fm,fm+mc):
            nv=int(D['vc'][li])
            if nv>128:reasons['large_meshlet']+=1;continue
            cg=D['CG'][D['c0'][li]:D['c0'][li+1]]
            points=cg@M[:,:3].T+M[:,3]
            sa,sz=D['let_s0'][li:li+2]
            result[(pi,li)]=dict(pi=pi,part=part,ci=ci,li=li,nv=nv,lo=points.min(0),hi=points.max(0),
                                 center=(points.min(0)+points.max(0))*.5,material=material,
                                 triangles=int(np.maximum(0,D['s_n'][sa:sz]-2).sum()))
    return result,dict(reasons)


def batches(rec,cell,max_vertices):
    buckets=collections.defaultdict(list)
    for key,r in rec.items():
        xyz=tuple(np.floor(r['center']/cell).astype(int))
        buckets[(xyz,r['material'])].append(key)
    output=[]
    for bucket,keys in sorted(buckets.items()):
        current=[];nv=0
        for key in sorted(keys):
            if nv+rec[key]['nv']>max_vertices:
                if len(current)>1:output.append((bucket,current))
                current=[];nv=0
            current.append(key);nv+=rec[key]['nv']
        if len(current)>1:output.append((bucket,current))
    return [dict(part_key=bucket,members=keys,lo=np.min([rec[k]['lo'] for k in keys],0),
                 hi=np.max([rec[k]['hi'] for k in keys],0),nv=sum(rec[k]['nv'] for k in keys)) for bucket,keys in output]


def selection(D,V,P,near,far,lod_px):
    if not np.isfinite(lod_px) or lod_px<=0:raise ValueError("LOD divisor must be finite and positive")
    a,c=sg.side_coefs(P);pl=D['ci_pl']
    mv=np.einsum('ij,njk->nik',V[:,:3],D['WQ'][:,:,:3])
    tv=np.einsum('ij,nj->ni',V[:,:3],D['WQ'][:,:,3])+V[:,3]
    ma=np.einsum('ij,njk->nik',V[:,:3],D['AF'][:,:,:3])
    scale=np.sqrt((ma**2).sum(2).max(1))*max(320*abs(P[1]),240*abs(P[3]))/lod_px
    v,r=sg.boxes_view(mv[pl],tv[pl],D['cbox'])
    outside,_,inside=sg.classify(v,r,a,c,near,far,True)
    vis=np.flatnonzero(~outside);depth=np.maximum(-v[vis,2]-r[vis,2],near)
    level=D['nlv'][vis]-1
    for _ in range(int(D['nlv'].max())):
        ix=D['flv'][vis]+level
        level-=((level>0)&(D['LV'][ix,2]*scale[pl[vis]]>depth))
    pairs={}
    for i,lv in zip(vis,D['flv'][vis]+level):
        pi=int(pl[i]);fm,mc=D['LV'][lv,:2].astype(int)
        for li in range(fm,fm+mc):
            if inside[i]:mask=0
            else:
                vv,rr=sg.boxes_view(mv[pi:pi+1],tv[pi:pi+1],D['lbox'][li:li+1])
                out,masks,_=sg.classify(vv,rr,a,c,near,far,False)
                if out[0]:continue
                mask=int(masks[0])
            nv=int(D['vc'][li]);sa,sz=D['let_s0'][li:li+2]
            walk=np.ones(sz-sa,bool);xform=nv;lo=0;hi=nv-1
            if D['SG'] is not None and mask:
                rec=D['SG'][li];end=rec[:,6]
                nonempty=end!=np.r_[0,end[:-1]];cut=np.zeros(D['G'],bool)
                for k in range(5):
                    if not(mask&(1<<k)):continue
                    if k<4:
                        row=0 if k<2 else 1;n=a[k]*mv[pi,row]+c[k]*mv[pi,2];d=a[k]*tv[pi,row]+c[k]*tv[pi,2]
                    else:n=-mv[pi,2];d=-tv[pi,2]-near
                    cut|=np.maximum(n*rec[:,:3],n*rec[:,3:6]).sum(1)+d < -1.0
                cut&=nonempty
                if cut.any():
                    on=nonempty&~cut
                    lo=int((rec[on,7]&255).min()) if on.any() else 0
                    hi=int((rec[on,7]>>8).max()) if on.any() else -1
                    xform=hi-lo+1
                    walk=~cut[D['s_grp'][sa:sz]]
            pairs[(pi,li)]=dict(nv=xform,lo=lo,hi=hi,walk=walk)
    return pairs,mv,tv


def strips_emitted(D,pi,li,mv,tv,V,P,near,walk=None):
    a,c=sg.side_coefs(P);cg=D['CG'][D['c0'][li]:D['c0'][li+1]]
    cv=cg@mv[pi].T+tv[pi];oc=np.zeros(len(cv),np.uint8)
    for k in range(4):
        vv=cv[:,0] if k<2 else cv[:,1]
        oc|=np.where(a[k]*vv+c[k]*cv[:,2]<0,1<<k,0).astype(np.uint8)
    oc|=np.where(-cv[:,2]<near,16,0).astype(np.uint8)
    oc|=np.where(-cv[:,2]>sg.PROJ_FAR,32,0).astype(np.uint8)
    sa,sz=D['let_s0'][li:li+2];tri=0
    for local,si in enumerate(range(sa,sz)):
        if walk is not None and not walk[local]:continue
        idx=D['e_idx'][D['e0'][si]:D['e0'][si+1]]
        if not(np.bitwise_and.reduce(oc[idx])&63):tri+=max(0,len(idx)-2)
    return tri


def price(D,rec,bs,cams,lod_px):
    merged={k for b in bs for k in b['members']};rows=[]
    source_parts={}
    for pi,part in zip(D['ci_pl'],D['ci_part']):
        fc,cc=D['p'].plod[int(part)]
        for ci in range(fc,fc+cc):
            cl=D['p'].clusters[ci]
            for lv in range(cl['first_level'],cl['first_level']+cl['level_count']):
                fm,mc,_=D['p'].levels[lv]
                for li in range(fm,fm+mc):source_parts[(int(pi),li)]=(int(pi),int(part))
    for frame,cam in cams:
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19]
        pairs,mv,tv=selection(D,V,P,near,far,lod_px)
        ref=sg.view_counts(D,V,P,near,far,lod_px)
        vertices=sum(x['nv'] for x in pairs.values())
        assert vertices==ref['T1' if D['SG'] is not None else 'T0'],(frame,vertices,ref)
        base_tri=sum(strips_emitted(D,pi,li,mv,tv,V,P,near,x['walk']) for (pi,li),x in pairs.items())
        candidate_v=sum(x['nv'] for k,x in pairs.items() if k not in merged)
        candidate_parts=sum(k not in merged for k in pairs)
        candidate_tri=sum(strips_emitted(D,pi,li,mv,tv,V,P,near,x['walk']) for (pi,li),x in pairs.items() if (pi,li) not in merged)
        drawn=set();admitted=0;new_parts=set()
        for batch in bs:
            center=(batch['lo']+batch['hi'])*.5;ext=(batch['hi']-batch['lo'])*.5
            cv=(V[:,:3]@center+V[:,3])[None];radius=(np.abs(V[:,:3])@ext)[None]
            a,c=sg.side_coefs(P);out,_,_=sg.classify(cv,radius,a,c,near,far,False)
            if out[0]:
                # A conservative union box must never remove a selected member.
                assert not any(k in pairs for k in batch['members'])
                continue
            admitted+=1;candidate_parts+=1;candidate_v+=batch['nv'];new_parts.add(batch['part_key'])
            for pi,li in batch['members']:
                drawn.add((pi,li));candidate_tri+=strips_emitted(D,pi,li,mv,tv,V,P,near)
        assert all(k in drawn for k in pairs if k in merged)
        before_contexts={source_parts[k] for k in pairs}
        remaining_contexts={source_parts[k] for k in pairs if k not in merged}
        rows.append(dict(frame=frame,before_meshlets=len(pairs),after_meshlets=candidate_parts,
                         before_part_contexts=len(before_contexts),after_part_contexts=len(remaining_contexts)+len(new_parts),
                         before_placements=len({pi for pi,_ in before_contexts}),
                         after_placements=len({pi for pi,_ in remaining_contexts})+len({k[0] for k in new_parts}),
                         before_vertices=vertices,after_vertices=candidate_v,before_triangles=base_tri,
                         after_triangles=candidate_tri,batches_drawn=admitted))
    means={k:float(np.mean([r[k] for r in rows])) for k in rows[0] if k!='frame'}
    means['meshlet_drop_percent']=100*(1-means['after_meshlets']/means['before_meshlets'])
    means['part_context_drop_percent']=100*(1-means['after_part_contexts']/means['before_part_contexts'])
    means['vertex_growth_percent']=100*(means['after_vertices']/means['before_vertices']-1)
    return means,rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',required=True,type=Path);ap.add_argument('--room',choices=('r101','r103'),required=True)
    ap.add_argument('--camera',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--cells',default='2000,4000,8000,16000');ap.add_argument('--max-vertices',type=int,default=256)
    ap.add_argument('--lod-px',required=True,type=float,help='Effective runtime LOD divisor: quality lod_px times SCENERY_FAR_LOD when enabled')
    ap.add_argument('--profile-receipt',required=True,type=Path,help='Resolved runtime knobs or an explicit scenario receipt to hash into this report')
    args=ap.parse_args();source=json.loads(args.inputs.read_text())[args.room]
    policy=lod_policy(args.lod_px,args.profile_receipt)
    D,files=load(source);rec,reasons=records(D,files,args.room);cams=cameras(args.camera)
    results=[]
    for cell in [int(x) for x in args.cells.split(',')]:
        bs=batches(rec,cell,args.max_vertices);mean,rows=price(D,rec,bs,cams,args.lod_px)
        keys={k for b in bs for k in b['members']};corners=sum(rec[k]['nv'] for k in keys)
        # Conservative storage bound: retained originals PLUS copied float world xyz,
        # original u16 UV/color, copied strip bytes and 32-byte batch descriptors.
        copied_strip=sum(D['p'].lets[k[1]]['strip_bytes'] for k in keys)
        added=corners*18+copied_strip+32*len(bs)
        results.append(dict(cell_mm=cell,max_vertices=args.max_vertices,batches=len(bs),
                            member_meshlets=len(keys),copied_corners=corners,
                            conservative_added_room_bytes=added,
                            r100_data_delta_bytes=0,mean=mean,rows=rows,
                            geometry_gate=mean['part_context_drop_percent']>=40 and mean['vertex_growth_percent']<=10,
                            memory_gate='PENDING: replacement-pool layout and room free heap required'))
        print(json.dumps({k:v for k,v in results[-1].items() if k!='rows'}),flush=True)
    report=dict(kind='OFFLINE GEOMETRY ESTIMATE; not measured milliseconds or runtime acceptance',room=args.room,
                inputs=source,camera=identity(args.camera),frames=[f for f,_ in cams],selection_policy=policy,
                eligible_meshlets=len(rec),excluded_meshlets=reasons,results=results,
                assumptions=['fixed camera-independent batches','same material and UV contract',
                             'single-level static one-off source BIN only','repeated instances untouched',
                             'part contexts, placements and meshlet draws reported separately',
                             'source strips unchanged; no dedup or facing/occlusion credit',
                             'original selected geometry retained in every simulated frame',
                             'world float baking storage bound; target rounding/look not qualified',
                             'r100 dataset unchanged; target code and shared memory costs not yet built'])
    with args.output.open('x') as f:json.dump(report,f,indent=2)

if __name__=='__main__':main()
