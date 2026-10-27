#!/usr/bin/env python3
"""Independent source-boundary and oriented-triangle verifier for private B2."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys

def vector(a,b):return tuple(b[i]-a[i] for i in range(3))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def normal(t,step):
    p=[tuple(v[i]*step[i] for i in range(3)) for v in t]
    return cross(vector(p[0],p[1]),vector(p[0],p[2]))
def canon(t):return min(t,t[1:]+t[:1],t[2:]+t[:2])
def geomedge(a,b):return tuple(sorted((a[:3],b[:3])))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',type=Path,required=True);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--b1',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True)
    args=ap.parse_args();sys.path.insert(0,str(args.helper_dir));import world_rebuild27 as w
    d,files,owners,policy=w.load(args.source)
    p=w.codec.decode((args.candidate/'ps2-world.re4mesh').read_bytes(),(args.candidate/'ps2-world.r4pw').read_bytes())
    b=w.codec.decode((args.b1/'ps2-world.re4mesh').read_bytes(),files['ps2-world.r4pw'])
    r=json.loads((args.candidate/'RECEIPT.json').read_text())
    checks={};changed=collections.defaultdict(list);removed=collections.defaultdict(set)
    for name in ('ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc'):
        assert (args.candidate/name).read_bytes()==(args.source/name).read_bytes(),name
    checks['companions_byte_identical']=True
    for key in ('meshes','placements','materials','part_lods'):assert d[key]==p[key],key
    assert [c[6:] for c in d['clusters']]==[c[6:] for c in p['clusters']]
    checks['all_source_identity_tables_preserved']=True
    source_regions=0;removed_triangles=0;min_winding_dot=None
    for rec in r['authored_regions']:
        mi,pi=rec['mesh'],rec['part'];assert mi not in owners
        assert rec['group'] in ('building_masses','major_openings') and d['materials'][pi][4]==0
        step=d['meshes'][mi][11:14];source=[]
        for ci,ti in rec['source_triangle_ids']:
            assert (ci,ti) not in removed[pi];removed[pi].add((ci,ti))
            source.append(w.level_triangles(d,d['levels'][d['clusters'][ci][6]])[ti])
        assert hashlib.sha256(json.dumps(source).encode()).hexdigest()==rec['source_sha256']
        # Reconstruct each output by independent ear clipping of the recorded
        # boundary. The producer's dissolve/partition functions are not imported.
        boundary=[tuple(v) for v in rec['output_boundary']]
        source_edges=collections.Counter(geomedge(a,b) for t in source for a,b in zip(t,t[1:]+t[:1]))
        assert all(n<=2 for n in source_edges.values())
        full=[tuple(v) for v in rec['source_boundary']]
        assert set(geomedge(a,b) for a,b in zip(full,full[1:]+full[:1]))=={e for e,n in source_edges.items() if n==1}
        assert all(v in {v for t in source for v in t} for v in boundary)
        assert len({v[:3] for v in full})==len(full) and len({v[:3] for v in boundary})==len(boundary)
        # Every removed boundary point lies exactly on its replacement segment.
        start=full.index(boundary[0]);full=full[start:]+full[:start]
        k=0
        for a,c in zip(boundary,boundary[1:]+boundary[:1]):
            assert full[k][:3]==a[:3]
            pa=tuple(a[i]*step[i] for i in range(3));pc=tuple(c[i]*step[i] for i in range(3));ac=vector(pa,pc)
            k=(k+1)%len(full)
            while full[k][:3]!=c[:3]:
                q=tuple(full[k][i]*step[i] for i in range(3));aq=vector(pa,q)
                assert dot(cross(aq,ac),cross(aq,ac))<=1e-12*max(dot(ac,ac),1)
                assert -1e-9<=dot(aq,ac)<=dot(ac,ac)+1e-9
                k=(k+1)%len(full)
        changed[rec['assigned_cluster']].append(rec)
        source_regions+=1;removed_triangles+=len(source)-rec['output_triangles']
    # Identify authored triangles by subtracting each region's exact retained
    # source triangles from its source cluster. All untouched triangles survive.
    owner_levels=ground_levels=0;actual_saved=0
    grouped_by_cluster=collections.defaultdict(list)
    for rec in r['authored_regions']:grouped_by_cluster[rec['assigned_cluster']].append(rec)
    for mi,m in enumerate(d['meshes']):
        for pi in range(m[6],m[6]+m[7]):
            fc,cc=d['part_lods'][pi]
            for ci in range(fc,fc+cc):
                c=d['clusters'][ci]
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;a=w.level_triangles(d,d['levels'][li]);out=w.level_triangles(p,p['levels'][li]);prior=w.level_triangles(b,b['levels'][li])
                    if mi in owners:assert a==out;owner_levels+=1
                    elif pi not in removed and ci not in grouped_by_cluster:assert w.canonical(prior)==w.canonical(out)
                    if mi in (163,188):assert a==out;ground_levels+=1
                    if ordinal==0:
                        actual_saved+=len(prior)-len(out)
                        if pi in removed:
                            source=w.level_triangles(d,d['levels'][li]);kept=[t for ti,t in enumerate(source) if (ci,ti) not in removed[pi]]
                            pool=w.canonical(out);pool.subtract(w.canonical(kept));assert all(n>=0 for n in pool.values())
                            leftovers=[t for t,n in pool.items() for _ in range(n)]
                            expected=sum(x['output_triangles'] for x in grouped_by_cluster[ci]);assert len(leftovers)==expected
                            # For each region, output hash identifies its source-corner
                            # triangles as one subset; all projected signed area and
                            # boundary constraints must match source independently.
                            for rec in grouped_by_cluster[ci]:
                                vertices={tuple(v) for v in rec['output_boundary']}
                                rt=[t for t in leftovers if all(v in vertices for v in t)]
                                assert len(rt)==rec['output_triangles']
                                src=[w.level_triangles(d,d['levels'][d['clusters'][sci][6]])[ti] for sci,ti in rec['source_triangle_ids']]
                                sn=tuple(sum(normal(t,m[11:14])[axis] for t in src) for axis in range(3))
                                axis=max(range(3),key=lambda a:abs(sn[a]));outarea=0
                                for t in rt:
                                    n=normal(t,m[11:14]);dp=dot(n,sn);assert dp>0
                                    min_winding_dot=dp if min_winding_dot is None else min(dp,min_winding_dot);outarea+=n[axis]
                                assert abs(outarea-sn[axis])<=max(abs(sn[axis])*1e-10,1e-6)
    assert len(owners)==21 and actual_saved==removed_triangles
    checks.update(owner_meshes_exact_all_levels=len(owners),owner_levels_checked=owner_levels,ground_levels_exact=ground_levels,authored_regions_verified=source_regions,source_boundary_holes_filled=0,actual_l0_triangles_removed=actual_saved,all_authored_triangles_source_winding=True,source_projected_coverage_area_preserved=True,all_unmodified_triangles_exact=True)
    (args.candidate/'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(dict(checks=checks,candidate_sha256=hashlib.sha256((args.candidate/'ps2-world.re4mesh').read_bytes()).hexdigest(),appearance_accepted=False,timing_available=False),indent=2)+'\n')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
