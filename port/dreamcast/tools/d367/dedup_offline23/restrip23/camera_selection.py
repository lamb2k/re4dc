"""Copied source-only world_merge23 camera/LOD/SG selector; LOD supplied explicitly.
Original source SHA256 9110e7fffbdfbc17e2a6d2948404d2fad42c94735db0b2f64098f9d9464313d6
Not runtime or pixel evidence.
"""
import re,struct
from pathlib import Path
import numpy as np
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
