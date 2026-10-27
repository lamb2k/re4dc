#!/usr/bin/env python3
"""Private B2 coplanar-patch structural authoring; existing renderer and PS2 data.

The B1 selection is a mandatory pinned input. Changing owners and ground are
never modified. Architectural triangles are partitioned by source material,
edge adjacency, winding and source plane. Only simple polygons are retessellated;
holes, UV seams, nonmanifold edges and ambiguous boundaries keep source triangles.
"""
import argparse
import collections
import json
import math
from pathlib import Path
import struct
import subprocess
import sys


def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))
def pos(v,step):return tuple(v[i]*step[i] for i in range(3))
def edge(a,b):return tuple(sorted((a[:3],b[:3])))
def area2(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def partition(tris,step,tolerance,angle):
    points=[[pos(v,step) for v in t] for t in tris]
    normals=[]
    for p in points:
        n=cross(sub(p[1],p[0]),sub(p[2],p[0]));l=norm(n)
        normals.append(tuple(v/l for v in n) if l>1e-9 else (0,0,0))
    edges=collections.defaultdict(list)
    for i,t in enumerate(tris):
        for a,b in zip(t,t[1:]+t[:1]):edges[edge(a,b)].append(i)
    adjacent=collections.defaultdict(set)
    for ids in edges.values():
        if len(ids)==2:
            a,b=ids;adjacent[a].add(b);adjacent[b].add(a)
    todo=set(range(len(tris)));regions=[]
    threshold=math.cos(math.radians(angle))
    while todo:
        seed=min(todo);todo.remove(seed);region=[seed];queue=[seed]
        n=normals[seed];anchor=points[seed][0]
        while queue:
            i=queue.pop()
            for j in sorted(adjacent[i]&todo):
                if dot(n,normals[j])<threshold:continue
                if max(abs(dot(n,sub(p,anchor))) for p in points[j])>tolerance:continue
                todo.remove(j);region.append(j);queue.append(j)
        regions.append(region)
    return regions


def dissolve(tris,step,boundary_tolerance=1e-8,approximate_uv=False):
    """Ear clipping a simple source boundary, preserving all boundary corners."""
    edges=collections.defaultdict(list);corners=collections.defaultdict(set)
    for t in tris:
        for v in t:corners[v[:3]].add(v)
        for a,b in zip(t,t[1:]+t[:1]):edges[edge(a,b)].append((a,b))
    boundary={}
    for e,uses in edges.items():
        if len(uses)>2:return tris,'nonmanifold',None
        if len(uses)==2:
            a,b=uses[0];c,d=uses[1]
            if a[:3]!=d[:3] or b[:3]!=c[:3]:return tris,'mixed winding',None
            # UV discontinuities are real texture features, so retain them.
            if not approximate_uv and (a[:5]!=d[:5] or b[:5]!=c[:5]):return tris,'UV seam',None
        else:
            a,b=uses[0]
            if a[:3] in boundary:return tris,'ambiguous boundary',None
            boundary[a[:3]]=b[:3]
    if len(boundary)<3:return tris,'closed surface',None
    ring=[min(boundary)]
    while True:
        nxt=boundary.get(ring[-1])
        if nxt==ring[0]:break
        if nxt is None or nxt in ring:return tris,'broken boundary',None
        ring.append(nxt)
    if len(ring)!=len(boundary):return tris,'multiple loops or hole',None
    # Boundary UV/color vertices must each be unambiguous. Interior prelight is
    # deliberately resampled by the authored triangulation and remains unaccepted.
    if not approximate_uv and any(len(corners[p])!=1 for p in ring):return tris,'boundary corner seam',None
    outgoing={uses[0][0][:3]:uses[0][0] for uses in edges.values() if len(uses)==1}
    vs=[outgoing[p] for p in ring]
    original_boundary=list(vs)
    # Collapse only collinear subdivisions with linearly compatible source UVs.
    # Every emitted corner is still an exact source corner; the full original
    # boundary is retained in the receipt for an independent deviation check.
    removed=0
    while len(vs)>3:
        changed=False
        for i,b in enumerate(vs):
            a,c=vs[i-1],vs[(i+1)%len(vs)]
            pa,pb,pc=(pos(v,step) for v in (a,b,c));ac=sub(pc,pa);den=dot(ac,ac)
            if den<1e-12:continue
            fraction=dot(sub(pb,pa),ac)/den
            distance=norm(sub(sub(pb,pa),tuple(fraction*v for v in ac)))
            if not 0<fraction<1 or distance>boundary_tolerance:continue
            if not approximate_uv and any(abs(b[k]-(a[k]+fraction*(c[k]-a[k])))>2 for k in (3,4)):continue
            vs.pop(i);removed+=1;changed=True;break
        if not changed:break
    xyz=[pos(v,step) for v in vs]
    n=tuple(sum(cross(sub(pos(t[1],step),pos(t[0],step)),sub(pos(t[2],step),pos(t[0],step)))[i] for t in tris) for i in range(3))
    axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
    xy=[tuple(p[a] for a in axes) for p in xyz]
    signed=sum(xy[i][0]*xy[(i+1)%len(xy)][1]-xy[(i+1)%len(xy)][0]*xy[i][1] for i in range(len(xy)))
    if abs(signed)<1e-8:return tris,'degenerate boundary',None
    sign=1 if signed>0 else -1
    indices=list(range(len(vs)));out=[]
    while len(indices)>3:
        found=False
        for k,b in enumerate(indices):
            a=indices[k-1];c=indices[(k+1)%len(indices)]
            if sign*area2(xy[a],xy[b],xy[c])<1e-8:continue
            if any(sign*area2(xy[a],xy[b],xy[p])>=-1e-8 and sign*area2(xy[b],xy[c],xy[p])>=-1e-8 and sign*area2(xy[c],xy[a],xy[p])>=-1e-8 for p in indices if p not in (a,b,c)):continue
            out.append((vs[a],vs[b],vs[c]));indices.pop(k);found=True;break
        if not found:return tris,'non-simple or collinear boundary',None
    out.append(tuple(vs[i] for i in indices))
    if any(dot(cross(sub(pos(t[1],step),pos(t[0],step)),sub(pos(t[2],step),pos(t[0],step))),n)<=1e-8 for t in out):
        return tris,'degenerate or reversed output',None
    if len(out)>=len(tris):return tris,'no interior tessellation saving',None
    return out,'authored',{'boundary_vertices':len(vs),'boundary_vertices_before':len(original_boundary),'boundary_subdivisions_removed':removed,'boundary_tolerance_local':boundary_tolerance,'source_boundary':original_boundary,'output_boundary':vs,'boundary_loops':1,'source_triangles':len(tris),'output_triangles':len(out),'removed_interior_vertices':len(corners)-len(original_boundary),'emitted_positions_uv_color_exact_source_corners':True,'UV_appearance_approximation':approximate_uv,'source_interior_uv_seam_edges':sum(len(uses)==2 and (uses[0][0][:5]!=uses[1][1][:5] or uses[0][1][:5]!=uses[1][0][:5]) for uses in edges.values())}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',type=Path,required=True)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--b1',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--plane-mm',type=float,default=1.0)
    ap.add_argument('--angle-deg',type=float,default=1.0)
    ap.add_argument('--approximate-uv',action='store_true',help='Reuse source key/corners while allowing interior UV and prelight interpolation changes')
    args=ap.parse_args();sys.path.insert(0,str(args.helper_dir))
    import world_rebuild27 as w
    w.require(not args.out.exists(),'immutable output exists')
    d,files,owners,policy=w.load(args.source)
    b1r=json.loads((args.b1/'RECEIPT.json').read_text())
    b1mesh=(args.b1/'ps2-world.re4mesh').read_bytes()
    w.require(w.sha(b1mesh)==b1r['candidate_sha256'],'B1 receipt pin')
    for name,pin in b1r['source_sha256'].items():w.require(w.sha((args.source/name).read_bytes())==pin,'source pin '+name)
    b1=w.codec.decode(b1mesh,files['ps2-world.r4pw'])
    selected={r['part']:r['group'] for r in b1r['feature_rows'] if r['l0_triangles_after']}
    replacements={};records=[];reasons=collections.Counter()
    for mi,m in enumerate(d['meshes']):
        if mi in owners:continue
        for pi in range(m[6],m[6]+m[7]):
            if selected.get(pi) not in ('building_masses','major_openings'):continue
            w.require(d['materials'][pi][4]==0,'opaque architecture required')
            fc,cc=d['part_lods'][pi];triangles=[];identities=[]
            for ci in range(fc,fc+cc):
                for ti,t in enumerate(w.level_triangles(d,d['levels'][d['clusters'][ci][6]])):
                    triangles.append(t);identities.append((ci,ti))
            scale=max(norm(p[2+i:14:4]) for p in d['placements'] if p[0]==mi for i in range(3))
            regions=partition(triangles,m[11:14],args.plane_mm/max(scale,1e-9),args.angle_deg)
            pending=collections.defaultdict(list);changed=False
            for region_id,indices in enumerate(regions):
                source=[triangles[i] for i in indices]
                out,why,detail=dissolve(source,m[11:14],approximate_uv=args.approximate_uv);reasons[why]+=1
                if detail:
                    changed=True;target=min(identities[i][0] for i in indices)
                    pending[target].extend(out)
                    records.append(dict(mesh=mi,source_bin=m[0],part=pi,group=selected[pi],region=region_id,source_triangle_ids=[identities[i] for i in indices],assigned_cluster=target,source_sha256=w.sha(json.dumps(source).encode()),output_sha256=w.sha(json.dumps(out).encode()),**detail))
                else:
                    for i in indices:pending[identities[i][0]].append(triangles[i])
            if changed:
                for ci in range(fc,fc+cc):replacements[ci]=pending[ci]
    out=w.install_shells(b1,replacements)
    blob=w.codec.serialize_mesh(out);pol=w.codec.serialize_policy(out)
    w.require(pol==files['ps2-world.r4pw'],'R4PW changed')
    args.out.mkdir(parents=True)
    (args.out/'ps2-world.raw.re4mesh').write_bytes(blob)
    (args.out/'ps2-world.r4pw').write_bytes(pol)
    cmd=[sys.executable,str(args.helper_dir/'ps2_strip_groups.py'),str(args.out/'ps2-world.raw.re4mesh'),str(args.out/'ps2-world.r4pw'),str(args.out/'ps2-world.re4mesh'),str(args.out/'ps2-world.r4sg'),'--groups','4','--report',str(args.out/'strip-groups.json')]
    r=subprocess.run(cmd,check=True,capture_output=True,text=True);(args.out/'strip-groups.log').write_text(r.stdout+r.stderr)
    sg=bytearray((args.out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,policy);(args.out/'ps2-world.r4sg').write_bytes(sg)
    for name in ('ps2-world.ids','ps2-world.r4tc','room.r4rc'):(args.out/name).write_bytes((args.source/name).read_bytes())
    mesh=(args.out/'ps2-world.re4mesh').read_bytes();grouped=w.codec.decode(mesh,pol)
    for lv,glv in zip(out['levels'],grouped['levels']):w.require(w.canonical(w.level_triangles(out,lv))==w.canonical(w.level_triangles(grouped,glv)),'stripgroup changed geometry')
    receipt=w.report(d,grouped,owners,['ground','building_masses','major_openings'],selected,replacements)
    h=struct.unpack_from('<4s19I',mesh)
    row=[0x101,len(pol),len(out['placements']),len(out['parts']),len(out['meshes']),struct.unpack_from('<I',pol,20)[0],w.fnv(pol),h[3],len(mesh),policy]
    (args.out/'world_rebuild27_certificates.inc').write_text('// PRIVATE B2 candidate source-policy mapping; no visibility certification.\nstatic constexpr Certificate rebuild27_certificates[] = {\n{'+','.join('0x%08xU'%v for v in row)+'},\n};\n')
    receipt.update(name=args.out.name,operation='B1 architecture partitioned into near-coplanar source patches; simple exact boundary retessellation',authored_regions=records,refusal_counts=dict(reasons),source_sha256={n:w.sha(v) for n,v in files.items()},b1_sha256=w.sha(b1mesh),helper_sha256=w.sha((args.helper_dir/'world_rebuild27.py').read_bytes()),tool_sha256=w.sha(Path(__file__).read_bytes()),candidate_bytes=len(mesh),candidate_crc='%08x'%h[3],candidate_sha256=w.sha(mesh),certificate_row=row,plane_tolerance_mm=args.plane_mm,normal_tolerance_deg=args.angle_deg,ground_exact=True,texture_assets_unchanged=True,gameplay_assets_unchanged=True,all_actor_data_unchanged=True)
    (args.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (args.out/'RECIPE.txt').write_text('PRIVATE UNACCEPTED B2 structural proxy, existing renderer only.\nCommand: '+json.dumps(sys.argv)+'\nGround and changing-owner geometry exact all levels. B1 omissions unchanged.\nBoundary source corners retain positions, UV, prelight. Interior prelight and triangulation approximate.\nHoles/non-simple boundaries/seams/nonmanifold regions retain source. No look or timing acceptance.\n')
    (args.out/'SHA256SUMS').write_text(''.join(w.sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(args.out.iterdir()) if p.is_file()))
    print(json.dumps({k:receipt[k] for k in ('name','l0_triangles_after','candidate_bytes','candidate_crc','candidate_sha256','refusal_counts')},indent=2))


if __name__=='__main__':main()
