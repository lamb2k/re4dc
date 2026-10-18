"""Export private R4IM cluster geometry and conservative protection metadata to Blender JSON.

Full six-u16 corner identities survive the round trip. Placement/material/lighting
sidecars are inputs, never rewritten. Only entire static clusters beyond the
12 m walkable-area band qualify; 3 m guard covers walk sampling and grid error.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct, sys
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'lostpart'))
from lostpart import Walk
from r4im_pkg import Pkg
from package_io import read, write, let_corners

def triangles(p, level):
    out=[]
    for li in range(level[0],level[0]+level[1]):
        corners,strips=let_corners(p,p['lets'][li])
        for s in strips:
            for k in range(len(s)-2):
                ix=(s[k],s[k+1],s[k+2]) if k%2==0 else (s[k+2],s[k+1],s[k])
                t=tuple(tuple(p['verts'][corners[j]]) for j in ix)
                if len({v[:3] for v in t})==3:out.append(t)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('data',type=Path);ap.add_argument('--walk',type=Path,required=True)
    a=ap.parse_args();d=a.data;blob=(d/'ps2-world.re4mesh').read_bytes();p=read(blob)
    assert write(p)==blob,'unmodified package roundtrip must be byte exact'
    pkg=Pkg(d/'ps2-world.re4mesh',d/'ps2-world.r4pw');walk=Walk(str(a.walk))
    ids=(d/'ps2-world.ids').read_bytes();values=ids[16:];dynamic={0,1,2}
    dynamic.update(i for i,x in enumerate(values) if x<250 and values.count(x)==1)
    placements=collections.defaultdict(list)
    for pl in pkg.placements:placements[pl['mesh']].append(pl)
    rows=[]
    for mi,m in enumerate(p['meshes']):
      for pi in range(m[6],m[6]+m[7]):
       for ci in range(*[p['plods'][pi][0],sum(p['plods'][pi])]):
        ts=triangles(p,p['levels'][p['clusters'][ci][6]])
        if not ts:continue
        keys=list(dict.fromkeys(v for t in ts for v in t));ix={v:i for i,v in enumerate(keys)}
        q=np.array([v[:3] for v in keys],float);positions=q*np.array(m[11:14])+np.array(m[8:11])
        far=True;distance=1e30
        for pl in placements[mi]:
            if pl['placement'] in dynamic:far=False
            M=pkg.wq(pl);world=q@M[:,:3].T+M[:,3]
            center=(world.min(0)+world.max(0))/2
            radius=np.linalg.norm((world.max(0)-world.min(0))[[0,2]])/2
            horizontal=walk.dist((center[0],0,center[2]))
            lower=horizontal/1.083-radius-2200
            distance=min(distance,lower)
            if lower<=12000:far=False
        # UVs must be affine across a planar patch, and lighting must be constant.
        uv=np.array([v[3:5] for v in keys],float)
        X=np.column_stack([positions-positions.mean(0),np.ones(len(keys))])
        coeff=np.linalg.lstsq(X,uv,rcond=None)[0]
        uverror=float(np.abs(X@coeff-uv).max())
        sv=np.linalg.svd(positions-positions.mean(0),compute_uv=False)
        planar=float(sv[-1]) if len(sv)==3 else 0
        constant=len({v[5] for v in keys})==1
        eligible=far and len(ts)>2 and planar<0.01 and uverror<0.05 and constant
        rows.append(dict(mesh=mi,part=pi,cluster=ci,bin=m[0],keys=keys,positions=positions.tolist(),
                         faces=[[ix[v] for v in t] for t in ts],far=far,eligible=eligible,
                         walk_lower_bound_mm=distance,uv_error=uverror,planarity=planar,
                         constant_lighting=constant,material=pkg.pmeta[pi]))
    out=dict(source_sha256=hashlib.sha256(blob).hexdigest(),roundtrip_byte_identical=True,
             protection='all static placements; 12m walk band plus conservative sampling guard; dynamic protected',clusters=rows)
    (d/'blender-input.json').write_text(json.dumps(out,separators=(',',':')))
    summary=dict(clusters=len(rows),far=sum(r['far'] for r in rows),eligible=sum(r['eligible'] for r in rows),
                 triangles=sum(len(r['faces']) for r in rows),eligible_triangles=sum(len(r['faces']) for r in rows if r['eligible']))
    (d/'export-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary)

if __name__=='__main__':main()
