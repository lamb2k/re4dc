#!/usr/bin/env python3
"""Pin cardinal/optional sight-line intersections to actual L0 mesh triangles.

Diagnoses a proposed camera fixture only. It cannot certify an enclosed volume,
portals, material admission, current source pose/LOD, or continuous visibility.
Private coordinates and mesh receipts must stay outside Git.
"""
from pathlib import Path
import struct, json, hashlib, math, sys
import argparse
ap=argparse.ArgumentParser(description='L0 source-geometry fixture probes only; rays are never continuous visibility proof.')
ap.add_argument('package',type=Path);ap.add_argument('--eye',type=float,nargs=3,required=True)
ap.add_argument('--target',type=float,nargs=3);ap.add_argument('--opaque-only',action='store_true')
ap.add_argument('--out',type=Path,required=True)
args=ap.parse_args();d=args.package
m=(d/'ps2-world.re4mesh').read_bytes();p=(d/'ps2-world.r4pw').read_bytes()
h=struct.unpack_from('<4s15I4I',m); hp=struct.unpack_from('<4s7I',p)
nc,nl,oplod,oc,olv=struct.unpack_from('<5I',m,80)
base=32+hp[3]*16
assert m[:4]==b'R4IM' and p[:4]==b'R4PW'
eye=tuple(args.eye)
dirs=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
target=args.target;distance=None
if target:
 delta=tuple(target[i]-eye[i] for i in range(3));distance=math.sqrt(sum(x*x for x in delta));assert distance>0
 dirs.append(tuple(x/distance for x in delta))
nearest=[(float('inf'),None)]*len(dirs)
def sub(a,b):return tuple(a[i]-b[i] for i in range(3))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
for pi in range(hp[2]):
    r=struct.unpack_from('<HH12f',p,base+52*pi); mi=r[0];a=r[2:14]
    mesh=struct.unpack_from('<HBBHHIII12f',m,h[10]+68*mi)
    for part in range(mesh[6],mesh[6]+mesh[7]):
        pas,cull=p[32+16*part+12:32+16*part+14]
        if args.opaque_only and pas!=0:continue
        fc,cc=struct.unpack_from('<2I',m,oplod+8*part)
        for ci in range(fc,fc+cc):
            cl=struct.unpack_from('<6HII',m,oc+20*ci)
            fm,nlet,_=struct.unpack_from('<IIf',m,olv+12*cl[6])
            for li in range(fm,fm+nlet):
                le=struct.unpack_from('<IIIHH6H',m,h[12]+28*li)
                fv,fs,sbytes,vc,sc=le[:5];sp=h[14]+fs
                if sc&0x8000:
                    offsets=struct.unpack_from('<%dH'%vc,m,sp);sp+=vc*2
                else:offsets=range(vc)
                v=[]
                for vi in offsets:
                    q=struct.unpack_from('<3H',m,h[13]+12*(fv+vi))
                    local=tuple(mesh[8+k]+q[k]*mesh[11+k] for k in range(3))
                    v.append(tuple(dot(a[k*4:k*4+3],local)+a[k*4+3] for k in range(3)))
                end=sp+sbytes
                while sp<end:
                    n=m[sp];sp+=1;ids=m[sp:sp+n];sp+=n
                    for ti in range(n-2):
                        va,vb,vcv=(v[ids[ti]],v[ids[ti+1]],v[ids[ti+2]])
                        e1,e2=sub(vb,va),sub(vcv,va);tv=sub(eye,va)
                        for axis,direction in enumerate(dirs):
                            pv=cross(direction,e2);det=dot(e1,pv)
                            if abs(det)<1e-8:continue
                            u=dot(tv,pv)/det
                            if u<0 or u>1:continue
                            qv=cross(tv,e1);w=dot(direction,qv)/det
                            if w<0 or u+w>1:continue
                            dist=dot(e2,qv)/det
                            if 1e-5<dist<nearest[axis][0]:
                                nearest[axis]=(dist,dict(placement=pi,mesh=mi,bin=mesh[0],part=part,cluster=ci,meshlet=li,pass_=pas,cull=cull,triangle=[va,vb,vcv]))
nearest=[(t,row) if math.isfinite(t) else (None,None) for t,row in nearest]
out=dict(kind='sampled L0 fixture diagnostic only; not cull proof',opaque_only=args.opaque_only,tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),eye=eye,dirs=dirs,nearest=nearest,target=target,target_distance=distance,mesh_sha256=hashlib.sha256(m).hexdigest(),policy_sha256=hashlib.sha256(p).hexdigest())
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(eye=eye,target_distance=distance,nearest=[(None if t is None else round(t,2),None if row is None else (row['placement'],row['mesh'],row['part'])) for t,row in nearest]),indent=2))
