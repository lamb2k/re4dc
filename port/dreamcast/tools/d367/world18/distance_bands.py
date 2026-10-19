#!/usr/bin/env python3
"""Host distance-band accounting for the existing world traversal; no runtime edits.

Counts transformed local corner ranges (including unused corners between kept
groups), not submitted triangles or visible pixels. Source-owned dynamic records
are separated because the retained camera log does not record their activation.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path
import numpy as np
import cone_ceiling as cc

sg=cc.sg
LABELS=('<15m','15-30m','30-45m','45-60m','>60m')
EDGES=np.array((15000.,30000.,45000.,60000.))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def load_package(path):
    mesh=path/'ps2-world.re4mesh';side=path/'ps2-world.r4pw';groups=path/'ps2-world.r4sg'
    d=sg.load(mesh,side,groups if groups.exists() else None)
    d['real_groups']=groups.exists()
    if not d['real_groups']:
        d['G']=1;d['SG']=np.zeros((d['p'].nlet,1,8),dtype=np.int64)
        for li,l in enumerate(d['p'].lets):
            d['SG'][li,0]=(*l['bmin'],*l['bmax'],l['strip_bytes'],(l['vc']-1)<<8)
    return d

def part_policy(package,source):
    """Current Test18 FOLIAGE_TRIM=1, TRANS_POLICY=3, look A sky0.

    TRANS_POLICY3 changes pass membership but not the far plane. Every surviving
    part is counted once; this does not apply source-owned dynamic activation.
    """
    side=(package/'ps2-world.r4pw').read_bytes()
    n=struct.unpack_from('<I',side,12)[0]
    text=(source/'port/dreamcast/game/platform/include/foliage_keys.inc').read_text()
    keys={(int(a,16),int(b,16)):int(c) for a,b,c in re.findall(r'\{\s*0x([0-9a-fA-F]+)[uU]?,\s*0x([0-9a-fA-F]+)[uU]?,\s*(\d+)[uU]?\s*\}',text)}
    assert keys,'Foliage table parser found no keys'
    caps=np.full(n,np.inf);dropped=np.zeros(n,dtype=bool)
    for i in range(n):
        crc,fnv,width,height,ps,cull,flags,reserved=struct.unpack_from('<IIHHBBBB',side,32+16*i)
        if ps==2 and not(reserved&1):
            cls=keys.get((crc,fnv),0)
            if cls==1:dropped[i]=True
            elif cls==2:caps[i]=12000.
    return caps,dropped

def selected(d,V,P,near,far,lodpx,caps,dropped):
    a,c=sg.side_coefs(P);WQ,AF=d['WQ'],d['AF']
    Mv=np.einsum('ij,njk->nik',V[:,:3],WQ[:,:,:3])
    tv=np.einsum('ij,nj->ni',V[:,:3],WQ[:,:,3])+V[:,3]
    ma=np.einsum('ij,njk->nik',V[:,:3],AF[:,:,:3])
    ls=np.sqrt((ma**2).sum(2).max(1))*max(320*abs(P[1]),240*abs(P[3]))/lodpx
    pl=d['ci_pl'];parts=d['ci_part'];cf=np.minimum(far,caps[parts])
    v,r=sg.boxes_view(Mv[pl],tv[pl],d['cbox'])
    outside,_,inside=sg.classify(v,r,a,c,near,cf,True)
    vis=np.nonzero(~outside & ~dropped[parts])[0]
    depth=np.maximum(-v[vis,2]-r[vis,2],near)
    level=d['nlv'][vis]-1
    for _ in range(int(d['nlv'].max())):
        idx=d['flv'][vis]+level
        level-=(level>0)&(d['LV'][idx,2]*ls[pl[vis]]>depth)
    for ci,lvi in zip(vis,d['flv'][vis]+level):
        pi=int(pl[ci]);part=int(parts[ci]);fm,mc=d['LV'][lvi,:2].astype(int)
        for li in range(fm,fm+mc):
            if inside[ci]:mask=0
            else:
                vb,rb=sg.boxes_view(Mv[pi:pi+1],tv[pi:pi+1],d['lbox'][li:li+1])
                out,masks,_=sg.classify(vb,rb,a,c,near,cf[ci],False)
                if out[0]:continue
                mask=int(masks[0])
            rec=d['SG'][li];on=rec[:,6]!=np.r_[0,rec[:-1,6]]
            if mask and d['real_groups']:
                lo,hi=rec[:,:3],rec[:,3:6]
                for k in range(5):
                    if not(mask&(1<<k)):continue
                    if k<4:
                        row=0 if k<2 else 1
                        nn=a[k]*Mv[pi,row]+c[k]*Mv[pi,2]
                        dd=a[k]*tv[pi,row]+c[k]*tv[pi,2]
                    else:nn,dd=-Mv[pi,2],-tv[pi,2]-near
                    on &= np.maximum(nn*lo,nn*hi).sum(1)+dd>=-1.
            yield pi,part,li,on

def run(a):
    d=load_package(a.package);p=d['p']
    caps,dropped=part_policy(a.package,a.source)
    dyn=cc.dynamic_fields(a.package,p,int(a.room[1:],16))
    cameras=cc.cameras(a.log,a.first,a.last,a.stride);rows=[]
    for frame,cam in cameras:
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19]
        near,far=P[6]/(P[5]-1),cam[19]
        eye=-np.linalg.solve(V[:,:3],V[:,3])
        # Retain a cross-check against the previously qualified raw geometry replay.
        raw=sum(cc.corner_count(on,d['SG'][li],int(d['vc'][li]),True) for _,_,li,on in cc.selected_meshlets(d,V,P,near,far,a.lodpx))
        reference=sg.view_counts(d,V,P,near,far,a.lodpx)
        assert raw==reference['T1' if d['real_groups'] else 'T0'],(frame,raw,reference)
        hist={name:np.zeros(5,dtype=np.int64) for name in ('all','static','source_owned','sky')}
        depth_hist=np.zeros(5,dtype=np.int64);lets=0
        for pi,part,li,on in selected(d,V,P,near,far,a.lodpx,caps,dropped):
            rec=d['SG'][li];vc=int(d['vc'][li]);n=cc.corner_count(on,rec,vc,True)
            if not n:continue
            nonempty=rec[:,6]!=np.r_[0,rec[:-1,6]]
            lo,hi=(0,vc-1) if np.array_equal(on,nonempty) else (int((rec[on,7]&255).min()),int((rec[on,7]>>8).max()))
            assert hi-lo+1==n
            grid=d['CG'][d['c0'][li]+lo:d['c0'][li]+hi+1]
            world=grid@d['WQ'][pi,:,:3].T+d['WQ'][pi,:,3]
            distances=np.linalg.norm(world-eye,axis=1)
            bins=np.bincount(np.searchsorted(EDGES,distances,side='right'),minlength=5)
            view=world@V[:,:3].T+V[:,3]
            depth_hist+=np.bincount(np.searchsorted(EDGES,-view[:,2],side='right'),minlength=5)
            hist['all']+=bins
            rowid=p.placements[pi]['placement']
            sky=a.room=='r101' and rowid<=2
            hist['sky' if sky else 'source_owned' if rowid in dyn else 'static']+=bins
            lets+=1
        assert np.array_equal(hist['all'],hist['static']+hist['source_owned']+hist['sky'])
        rows.append(dict(frame=frame,eye_mm=eye.tolist(),cull_far_mm=far,raw_replay_corners=raw,meshlets=lets,
                         bands={k:v.tolist() for k,v in hist.items()},depth_bands=depth_hist.tolist()))
    mean={k:np.mean([r['bands'][k] for r in rows],axis=0).tolist() for k in rows[0]['bands']}
    total=sum(mean['all']);shares=[x/total for x in mean['all']]
    report=dict(room=a.room,kind='HOST GEOMETRY REPLAY; no timing measured by this tool',bands=LABELS,
                distance='Euclidean distance from logged camera eye to each transformed corner, in source millimetres; edges are lower-inclusive',
                mean_corners=mean,mean_total_corners=total,all_corner_shares=shares,
                mean_depth_corners=np.mean([r['depth_bands'] for r in rows],axis=0).tolist(),
                first=rows[0]['frame'],last=rows[-1]['frame'],samples=len(rows),lod_px=a.lodpx,
                camera_log=str(a.log),camera_log_sha256=sha(a.log),
                files={f.name:sha(f) for f in a.package.glob('ps2-world.*')},
                policies=dict(foliage=1,foliage_near_mm=12000,trans_policy=3,sky=0,near_capped_parts=int(np.isfinite(caps).sum()),dropped_parts=int(dropped.sum())),
                rows=rows,limitations=[
                    'Retained camera replay on byte-verified current room inputs; not a fresh runtime corner counter.',
                    'Source-owned dynamic activation/transforms and placement gates are absent; their authored counts are separated.',
                    'Classification uses the existing float64 host model; runtime floating-point edge decisions can differ.',
                    'Bands account for transformed corner ranges, not final visibility or GPU pixel cost.',
                    'FOLIAGE_NEAR and dropped parts are applied; TRANS_POLICY3 changes pass but not the far plane.',
                    'Per-band milliseconds require a separately identified exclusive-cost allocation and are not direct band timing.'
                ])
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('room','mean_corners','mean_total_corners','all_corner_shares','policies','samples')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('log',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--room',required=True,choices=('r101','r103'));p.add_argument('--source',type=Path,required=True)
    p.add_argument('--first',type=int,default=500);p.add_argument('--last',type=int,default=794);p.add_argument('--stride',type=int,default=7);p.add_argument('--lodpx',type=float,default=5)
    run(p.parse_args())
