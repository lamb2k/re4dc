#!/usr/bin/env python3
"""Verify actual serialized B2 facade geometry independently from authoring."""
import argparse
import collections
import json
from pathlib import Path
import sys

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('helper-dir','source','b1','dependencies','candidate'):ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args();sys.path.insert(0,str(a.helper_dir));sys.path.insert(0,str(a.dependencies))
    import world_rebuild27 as w
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    d,files,owners,policy=w.load(a.source);b=w.codec.decode((a.b1/'ps2-world.re4mesh').read_bytes(),files['ps2-world.r4pw'])
    p=w.codec.decode((a.candidate/'ps2-world.re4mesh').read_bytes(),(a.candidate/'ps2-world.r4pw').read_bytes())
    r=json.loads((a.candidate/'SOURCE-PLANE-PROOF.json').read_text());selected={tuple(v) for v in r['selected_ids']}
    source=[];authored=[];owner_levels=ground_levels=other_levels=0
    for mi,m in enumerate(d['meshes']):
        for pi in range(m[6],m[6]+m[7]):
            fc,cc=d['part_lods'][pi]
            for ci in range(fc,fc+cc):
                c=d['clusters'][ci]
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;before=w.level_triangles(b,b['levels'][li]);after=w.level_triangles(p,p['levels'][li])
                    if pi==160 and ordinal==0:
                        removed=[t for ti,t in enumerate(before) if (ci,ti) in selected]
                        source.extend(removed);remain=w.canonical(before);remain.subtract(w.canonical(removed))
                        extra=w.canonical(after);extra.subtract(remain);assert all(n>=0 for n in extra.values())
                        authored.extend(t for t,n in extra.items() for _ in range(n))
                    else:assert w.canonical(before)==w.canonical(after);other_levels+=1
                    if mi in owners:assert after==w.level_triangles(d,d['levels'][li]);owner_levels+=1
                    if mi in (163,188):assert after==w.level_triangles(d,d['levels'][li]);ground_levels+=1
    assert len(source)==41 and len(authored)==20
    # Derive a fresh projection from source area normals, independently of the
    # author's stored plane. This tests actual serialized geometry and holes.
    step=np.asarray(d['meshes'][104][11:14]);s=np.asarray([[v[:3] for v in t] for t in source])*step
    q=np.asarray([[v[:3] for v in t] for t in authored])*step
    n=np.cross(s[:,1]-s[:,0],s[:,2]-s[:,0]).sum(0);n/=np.linalg.norm(n)
    u=np.asarray([0.,1.,0.]);u-=n*np.dot(n,u);u/=np.linalg.norm(u);v=np.cross(n,u)
    sn=np.cross(s[:,1]-s[:,0],s[:,2]-s[:,0]);qn=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
    assert (qn@n>0).all(),'authored winding or degenerate triangle'
    sp=[Polygon(t@np.stack((u,v)).T) for t in s];qp=[Polygon(t@np.stack((u,v)).T) for t in q]
    su=shapely.unary_union(sp);qu=shapely.unary_union(qp)
    assert su.geom_type==qu.geom_type=='Polygon' and len(su.interiors)==len(qu.interiors)==1
    aperture=Polygon(su.interiors[0]);filled=aperture.intersection(qu).area;assert filled<1e-6
    assert abs(sum(t.area for t in qp)-qu.area)<1e-6,'overlapping authored triangles'
    for key in ('meshes','placements','materials','part_lods'):assert p[key]==d[key]
    for name in ('ps2-world.ids','ps2-world.r4pw','ps2-world.r4tc','room.r4rc'):assert (a.candidate/name).read_bytes()==(a.source/name).read_bytes()
    checks=dict(actual_source_triangles=41,actual_authored_triangles=20,owner_meshes_exact=len(owners),owner_levels_exact=owner_levels,ground_levels_exact=ground_levels,all_other_source_levels_exact=other_levels,source_apertures=1,serialized_output_apertures=1,source_aperture_filled_area=filled,all_output_triangles_correct_winding=True,all_output_triangles_nondegenerate=True,output_triangles_nonoverlapping=True,companions_and_source_identity_tables_unchanged=True,candidate_sha256=w.sha((a.candidate/'ps2-world.re4mesh').read_bytes()),appearance_accepted=False,timing_available=False)
    (a.candidate/'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
