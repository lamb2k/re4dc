#!/usr/bin/env python3
"""Offline opaque selection replay from actual PS2CAM records.

Reuses current package bounds, every selectable LOD and actual view/projection.
Counts are baked-pose host replays, not target counters, pixel visibility or ms.
No strip-group sidecar is supported; absent r10d SG matches the staged package.
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

import numpy as np


PATTERN = r'PS2CAM f=(\d+) cf=([0-9a-fA-F]{8}) c=((?:[0-9a-fA-F]{8} ){11}[0-9a-fA-F]{8}) p=((?:[0-9a-fA-F]{8} ){6}[0-9a-fA-F]{8})'


def cameras(log,first,last,stride):
    by_frame={}
    for m in re.finditer(PATTERN,Path(log).read_text(errors='replace')):
        frame=int(m[1])
        if first<=frame<=last and (frame-first)%stride==0:
            values=[struct.unpack('<f',bytes.fromhex(x)[::-1])[0] for x in (m[3]+' '+m[4]+' '+m[2]).split()]
            by_frame[frame]=values
    return sorted(by_frame.items())


def visible(lo,hi,m,p,near,far):
    # native_static.cpp / render::group_visible support-radius equations.
    cen=(np.array(lo)+hi)*.5;ext=(np.array(hi)-lo)*.5
    v=m[:,:3]@cen+m[:,3];rad=np.abs(m[:,:3])@ext
    if -v[2]+rad[2]<near or -v[2]-rad[2]>far:return False
    for a,b,c in ((p[1],0,p[2]-1),(-p[1],0,-p[2]-1),
                  (0,-p[3],-p[4]-1),(0,p[3],p[4]-1)):
        plane=np.array([a,b,c])
        if plane@v+np.abs(plane)@rad<-.0001:return False
    return True


def replay(pkg,cam,lod_px,far_lod):
    v=np.array(cam[:12]).reshape(3,4);proj=cam[12:19]
    near=proj[6]/(proj[5]-1);far=cam[19]
    px=max(320*abs(proj[1]),240*abs(proj[3]));inst=0;out=[]
    for pi,pl in enumerate(pkg.placements):
        mesh=pkg.meshes[pl['mesh']];A=pl['affine']
        mv=np.zeros((3,4));mv[:,:3]=v[:,:3]@A[:,:3];mv[:,3]=v[:,:3]@A[:,3]+v[:,3]
        world=pkg.wq(pl);mq=np.zeros((3,4));mq[:,:3]=v[:,:3]@world[:,:3];mq[:,3]=v[:,:3]@world[:,3]+v[:,3]
        scale=np.sqrt((mv[:,:3]**2).sum(1).max())*px/(lod_px*far_lod)
        placement_on=visible(np.array(mesh['bmin']),np.array(mesh['bmax']),mv,proj,near,far)
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            fc,cc=pkg.plod[part]
            for ci in range(fc,fc+cc):
                cluster=pkg.clusters[ci];lo=np.array(cluster['bmin'],float);hi=np.array(cluster['bmax'],float)
                count=0;lets=0;level=-1
                if placement_on and pkg.pmeta[part]['pass_']==0 and visible(lo,hi,mq,proj,near,far):
                    center=(lo+hi)*.5;extent=(hi-lo)*.5
                    depth=max(near,-mq[2,:3]@center-mq[2,3]-np.abs(mq[2,:3])@extent)
                    level=cluster['level_count']-1
                    while level and pkg.levels[cluster['first_level']+level][2]*scale>depth:level-=1
                    # Current PS2_WORLD_NONEMPTY_LOD=1 chooses nearest nonempty
                    # finer level when an offline coarse level is empty.
                    while level and not pkg.levels[cluster['first_level']+level][1]:level-=1
                    first,n,_=pkg.levels[cluster['first_level']+level]
                    for li in range(first,first+n):
                        ml=pkg.lets[li]
                        if visible(np.array(ml['bmin'],float),np.array(ml['bmax'],float),mq,proj,near,far):
                            count+=ml['vc'];lets+=1
                out.append(dict(instance=inst,placement=pi,part=part,cluster=ci,level=level,corners=count,meshlets=lets));inst+=1
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('private',type=Path);ap.add_argument('--log',required=True,type=Path)
    ap.add_argument('--first',type=int,default=500);ap.add_argument('--last',type=int,default=794)
    ap.add_argument('--stride',type=int,default=7);ap.add_argument('--lod-px',type=float,default=5.)
    ap.add_argument('--far-lod',type=float,default=4.);ap.add_argument('--pre-strip-groups',action='store_true',help='conservative selected work ceiling before SG selection');ap.add_argument('--name',required=True)
    a=ap.parse_args();r=a.private
    sys.path.insert(0,str(r/'helpers'/'interior'));from r4im import Pkg
    pkg=Pkg(r/'inputs/ps2-world.re4mesh',r/'inputs/ps2-world.r4pw')
    sg=(r/'inputs/ps2-world.r4sg').exists()
    assert not sg or a.pre_strip_groups,'SG replay unsupported; explicit --pre-strip-groups required for upper-bound pricing'
    chosen=cameras(a.log,a.first,a.last,a.stride);assert chosen,'no selected exact cameras'
    summaries=[];rows=[]
    for frame,cam in chosen:
        counts=replay(pkg,cam,a.lod_px,a.far_lod)
        rows.append(dict(frame=frame,instances=counts))
        summaries.append(dict(frame=frame,corners=sum(c['corners'] for c in counts),
                              meshlets=sum(c['meshlets'] for c in counts),
                              clusters=sum(c['corners']>0 for c in counts)))
    report=dict(kind='offline baked-pose pre-strip-group work ceiling' if sg else 'offline baked-pose opaque selection replay',actual_runtime_counters=False,strip_group_sidecar_bound=sg,
                assumptions=['baked placement poses; no source hierarchy/hide/AREA change',
                             'strip-group selection omitted; selected work is an upper bound' if sg else 'bound inputs have no strip-group sidecar',
                             'host double arithmetic; boundary cases require target count comparison'],
                log=str(a.log),frames=[s['frame'] for s in summaries],lod_px=a.lod_px,far_lod=a.far_lod,
                selected_corners_mean=float(np.mean([s['corners'] for s in summaries])),
                selected_meshlets_mean=float(np.mean([s['meshlets'] for s in summaries])),summaries=summaries)
    (r/f'{a.name}-selection.json').write_text(json.dumps(report,indent=1)+'\n')
    (r/f'{a.name}-selected-instances.json').write_text(json.dumps(rows)+'\n')
    (r/f'{a.name}-cameras.txt').write_text(''.join(' '.join(format(x,'.9g') for x in c)+'\n' for _,c in chosen))
    print(json.dumps({k:report[k] for k in ('kind','actual_runtime_counters','selected_corners_mean','selected_meshlets_mean')}))


if __name__=='__main__':main()
