#!/usr/bin/env python3
"""Private r101 named house-wall/roof replacement, using reviewed R4IM helpers.

This is one explicitly pinned source component pair in an existing candidate.
It is not a global surface simplifier, production converter or staging command.
"""
import argparse
import collections
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import world_rebuild27 as w


def triangles(d, part):
    result = {}
    fc, cc = d['part_lods'][part]
    for ci in range(fc, fc+cc):
        for ti, t in enumerate(w.level_triangles(d, d['levels'][d['clusters'][ci][6]])):
            result[(ci, ti)] = t
    return result


def positions(d, mesh, ts):
    import numpy as np
    m = d['meshes'][mesh]
    return np.asarray([[v[:3] for v in t] for t in ts], float)*m[11:14]+m[8:11]


def source_component(d, spec):
    """Require a connected source component, not just an approximate region."""
    import numpy as np
    all_tris = triangles(d, spec['part'])
    ids = [tuple(i) for i in spec['source_ids']]
    w.require(len(ids) == spec['source_triangles'] and len(set(ids)) == len(ids), 'component IDs/count')
    ts = [all_tris[i] for i in ids]
    parent = {}
    def find(v):
        parent.setdefault(v, v)
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v
    for t in all_tris.values():
        root = find(t[0][:3])
        for v in t[1:]:
            parent[find(v[:3])] = root
    root = find(ts[0][0][:3])
    actual = {i for i, t in all_tris.items() if find(t[0][:3]) == root}
    w.require(actual == set(ids), 'plan must name one entire source connected component')
    pl = d['placements'][spec['placement']]
    w.require(pl[0] == spec['mesh'], 'component placement/mesh')
    A = np.asarray(pl[2:]).reshape(3, 4)
    xyz = positions(d, spec['mesh'], ts)
    world = xyz @ A[:, :3].T + A[:, 3]
    w.require(max(abs(world.min((0, 1))-spec['world_lo'])) < 3 and
              max(abs(world.max((0, 1))-spec['world_hi'])) < 3, 'pinned component bounds')
    return dict(zip(ids, ts)), xyz, A


def author_walls(d, spec):
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    source, _, A = source_component(d, spec)
    mesh = spec['mesh']; m = d['meshes'][mesh]
    scale = max(np.linalg.norm(A[:, :3], axis=0))
    covered = set(); output = []; proofs = []
    for face in spec['faces']:
        ids = [tuple(i) for i in face['source_ids']]
        w.require(not covered.intersection(ids) and set(ids) <= source.keys(), 'wall face source partition')
        covered.update(ids)
        ts = [source[i] for i in ids]
        if len(ts) <= 2:
            output.extend(ts)
            proofs.append(dict(name=face['name'],source_ids=ids,source_triangles=len(ts),
                               output_triangles=len(ts),operation='source exact boundary/reveal'))
            continue
        xyz = positions(d, mesh, ts)
        area_normals = np.cross(xyz[:, 1]-xyz[:, 0], xyz[:, 2]-xyz[:, 0])
        normal = area_normals.sum(0); normal /= np.linalg.norm(normal)
        origin = xyz[0, 0]
        u = np.asarray([0., 1., 0.]); u -= normal*np.dot(normal, u); u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        uv = (xyz-origin) @ np.stack([u, v]).T
        union = shapely.unary_union([Polygon(t) for t in uv])
        parts = list(union.geoms) if union.geom_type == 'MultiPolygon' else [union]
        w.require(all(p.geom_type == 'Polygon' for p in parts), 'wall projected polygons')
        authored = []; face_proofs = []
        for poly in parts:
            # Named facade only: 20 mm outer contour edit. Retain every source
            # hole and concave negative space with a 3 mm quantization margin.
            outer = Polygon(poly.exterior).simplify(20/scale, preserve_topology=True)
            holes = [Polygon(h) for h in poly.interiors]
            negative = poly.convex_hull.difference(poly)
            target = outer.difference(negative.buffer(3/scale, join_style='mitre'))
            target = target.difference(shapely.unary_union([h.buffer(3/scale,join_style='mitre') for h in holes]))
            w.require(not target.is_empty, 'wall negative space removed entire plane')
            target_polys = list(target.geoms) if target.geom_type == 'MultiPolygon' else [target]
            for target_poly in target_polys:
                w.require(target_poly.geom_type == 'Polygon', 'wall target geometry')
                for tri in shapely.constrained_delaunay_triangles(target_poly).geoms:
                    verts = []
                    for point in list(tri.exterior.coords)[:3]:
                        projected = origin+point[0]*u+point[1]*v
                        # Interpolate position depth, UV and prelight from the
                        # nearest original projected triangle, preserving wall
                        # thickness between separately named facade planes.
                        best = None
                        for index, tri_uv in enumerate(uv):
                            P = Polygon(tri_uv)
                            dist = P.distance(shapely.Point(point))
                            if best is None or dist < best[0]: best = (dist, index)
                        index = best[1]; a, b, c = uv[index]
                        bary = np.linalg.lstsq(np.column_stack([b-a,c-a]),np.asarray(point)-a,rcond=None)[0]
                        weights = np.clip([1-bary.sum(),*bary],0,1);weights/=weights.sum()
                        depth = float(((xyz[index]-origin)@normal)@weights)
                        local = projected+normal*depth
                        grid = np.rint((local-m[8:11])/m[11:14]).astype(int)
                        w.require((grid >= 0).all() and (grid <= 65535).all(), 'wall position grid')
                        src = ts[index]
                        tex = np.rint(np.asarray([a[3:5] for a in src]).T@weights).astype(int)
                        rgb = np.asarray([[(a[5]>>s)&31 for s in (10,5,0)] for a in src])
                        rgb = np.rint(rgb.T@weights).astype(int)
                        color = (int(src[int(np.argmax(weights))][5])&0x8000)|int(rgb[0]<<10|rgb[1]<<5|rgb[2])
                        verts.append(tuple(int(a) for a in grid)+tuple(int(a) for a in tex)+(color,))
                    pp = positions(d,mesh,[verts])[0]
                    if np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),normal)<0:verts.reverse()
                    pp = positions(d,mesh,[verts])[0]
                    w.require(np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),normal)>1e-9,'wall degenerate/winding')
                    authored.append(tuple(verts))
            emitted = [Polygon((positions(d,mesh,[t])[0]-origin)@np.stack([u,v]).T) for t in authored]
            emitted_union = shapely.unary_union(emitted)
            # All source negative space, including notches open to the facade
            # perimeter, must remain empty after integer-grid serialization.
            filled = float(negative.intersection(emitted_union).area)
            w.require(filled < 1e-5, 'authored wall filled a source window/door/negative region')
            face_proofs.append(dict(source_holes=len(holes),negative_space_filled_area=filled,
                  negative_space_area=float(negative.area),output_holes=sum(len(p.interiors) for p in
                  (list(emitted_union.geoms) if emitted_union.geom_type=='MultiPolygon' else [emitted_union])),
                  boundary_hausdorff_world_mm=float(poly.boundary.hausdorff_distance(emitted_union.boundary)*scale)))
        output.extend(authored)
        proofs.append(dict(name=face['name'],source_ids=ids,source_triangles=len(ts),output_triangles=len(authored),
             operation='named facade contour with explicit source aperture and notch subtraction',
             normal=normal.tolist(),maximum_source_relief_world_mm=float(abs((xyz-origin)@normal).max()*scale),
             opening_proofs=face_proofs))
    w.require(covered == source.keys(),'wall face partition must cover the complete named component')
    w.require(len(output)<=spec['triangle_cap'],'named wall budget exceeded: '+str(
        [(p['name'],p['source_triangles'],p['output_triangles']) for p in proofs]))
    return source, output, proofs


def author_roof(d, spec):
    import numpy as np
    source, _, A = source_component(d, spec)
    corners = {v for t in source.values() for v in t}
    profiles = [[tuple(v) for v in row] for row in spec['profiles']]
    w.require(len(profiles)==5 and all(len(row)==6 for row in profiles), 'explicit five-station roof profile')
    w.require(all(v in corners for row in profiles for v in row), 'roof profile must use exact source corners')
    names = ('near_slope','near_ridge_skirt','ridge_cap','far_ridge_skirt','far_slope')
    output=[];proofs=[]
    for strip,name in enumerate(names):
        tris=[]
        for row in range(len(profiles)-1):
            a,b=profiles[row][strip:strip+2];c,e=profiles[row+1][strip:strip+2]
            for tri in ((a,c,e),(a,e,b)):
                pp=positions(d,spec['mesh'],[tri])[0]
                n=np.cross(pp[1]-pp[0],pp[2]-pp[0])
                world=pp@A[:,:3].T+A[:,3]
                wn=np.cross(world[1]-world[0],world[2]-world[0])
                direction=spec['world_outward_directions'][strip]
                if np.dot(wn,direction)<0:tri=(tri[0],tri[2],tri[1]);wn=-wn
                w.require(np.dot(wn,direction)>1e-9,'roof degenerate/winding')
                tris.append(tri)
        output.extend(tris);proofs.append(dict(name=name,output_triangles=len(tris),source_profile_corners=profiles))
    for end,row in enumerate((profiles[0],profiles[-1])):
        cap=[row[i] for i in (1,2,3,4)]
        tris=[(cap[0],cap[1],cap[2]),(cap[0],cap[2],cap[3])]
        local=positions(d,spec['mesh'],tris);expected=np.asarray(spec['local_length_axis'])*(-1 if end==0 else 1)
        if np.dot(np.cross(local[0,1]-local[0,0],local[0,2]-local[0,0]),expected)<0:
            tris=[(t[0],t[2],t[1]) for t in tris]
        for tri in tris:
            pp=positions(d,spec['mesh'],[tri])[0]
            w.require(np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),expected)>1e-9,'roof end winding')
        output.extend(tris);proofs.append(dict(name='ridge_end_'+str(end),output_triangles=len(tris)))
    w.require(len(output)<=spec['triangle_cap'],'named roof budget exceeded')
    return source,output,proofs


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--context',type=Path,required=True)
    ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--dependencies',type=Path,required=True,help='existing private NumPy/Shapely directory')
    a=ap.parse_args();w.require(not a.out.exists(),'immutable output exists')
    sys.path.insert(0,str(a.dependencies))
    plan_bytes=a.plan.read_bytes();plan=json.loads(plan_bytes)
    w.require(plan['room']=='r101' and plan['operation']=='one named house wall/roof replacement','bounded house plan')
    w.require(w.sha((HERE/'world_rebuild27.py').read_bytes())==plan['helper_sha256'],'reviewed helper pin')
    d,files,owners,policy=w.load(a.source)
    for n in w.SOURCE_INPUTS:
        w.require(w.sha(files[n])==plan['source_sha256'][n],'source pin '+n)
        w.require(w.sha((a.context/n).read_bytes())==plan['context_sha256'][n],'context pin '+n)
    for n in w.UNCHANGED_COMPANIONS:w.require((a.context/n).read_bytes()==files[n],'context source companion '+n)
    context_blob=(a.context/'ps2-world.re4mesh').read_bytes();context=w.codec.decode(context_blob,files['ps2-world.r4pw'])
    wall_source,wall,wall_proof=author_walls(d,plan['walls'])
    roof_source,roof,roof_proof=author_roof(d,plan['roof'])
    replacements={};expected={};changed_parts=set();source_count=0
    for spec,source,authored in ((plan['walls'],wall_source,wall),(plan['roof'],roof_source,roof)):
        w.require(spec['mesh'] not in owners,'changing owner cannot be authored')
        changed_parts.add(spec['part']);by_cluster=collections.defaultdict(list)
        for (ci,_),t in source.items():by_cluster[ci].append(t)
        for ci,removed in by_cluster.items():
            before=w.level_triangles(context,context['levels'][context['clusters'][ci][6]])
            counts=w.canonical(before);target=w.canonical(removed)
            w.require(not (target-counts),'named source component must be exact in context')
            # Match oriented triangles, allowing only cyclic corner rotations.
            remaining=target.copy();kept=[]
            for t in before:
                key=min(t,t[1:]+t[:1],t[2:]+t[:2])
                if remaining[key]:remaining[key]-=1
                else:kept.append(t)
            w.require(not +remaining,'source removal incomplete')
            replacements[ci]=kept
        replacements[min(by_cluster)].extend(authored);source_count+=len(source)
    class Levels(dict):
        def __init__(self):
            super().__init__();self.cursor=collections.Counter()
            for ci,ts in replacements.items():
                c=context['clusters'][ci];seq=[]
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;lv=context['levels'][li]
                    value=ts if ordinal==0 else w.level_triangles(context,lv)
                    expected[li]=value
                    if lv[1]:seq.append(value)
                dict.__setitem__(self,ci,seq)
        def __getitem__(self,ci):
            index=self.cursor[ci];self.cursor[ci]+=1
            return dict.__getitem__(self,ci)[index]
    provider=Levels();out=w.install_shells(context,provider)
    raw=w.codec.serialize_mesh(out);pol=w.codec.serialize_policy(out)
    w.require(pol==files['ps2-world.r4pw'],'unchanged policy')
    a.out.mkdir(parents=True)
    (a.out/'ps2-world.raw.re4mesh').write_bytes(raw);(a.out/'ps2-world.r4pw').write_bytes(pol)
    run=subprocess.run([sys.executable,str(HERE/'ps2_strip_groups.py'),str(a.out/'ps2-world.raw.re4mesh'),
      str(a.out/'ps2-world.r4pw'),str(a.out/'ps2-world.re4mesh'),str(a.out/'ps2-world.r4sg'),
      '--groups','4','--report',str(a.out/'strip-groups.json')],capture_output=True,text=True,check=True)
    (a.out/'strip-groups.log').write_text(run.stdout+run.stderr)
    sg=bytearray((a.out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,policy);(a.out/'ps2-world.r4sg').write_bytes(sg)
    companion_hashes={}
    for n in w.UNCHANGED_COMPANIONS:
        (a.out/n).write_bytes(files[n]);readback=(a.out/n).read_bytes()
        w.require(readback==files[n],'copied companion '+n);companion_hashes[n]=w.sha(readback)
    mesh=(a.out/'ps2-world.re4mesh').read_bytes();decoded=w.codec.decode(mesh,pol)
    for key in ('meshes','placements','materials','part_lods'):w.require(decoded[key]==context[key],'identity '+key)
    w.require([c[6:] for c in decoded['clusters']]==[c[6:] for c in context['clusters']],'cluster identity')
    owner_levels=0;untouched_levels=0
    for mi,m in enumerate(context['meshes']):
        for pi in range(m[6],m[6]+m[7]):
            fc,cc=context['part_lods'][pi]
            for c in context['clusters'][fc:fc+cc]:
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;before=w.level_triangles(context,context['levels'][li]);after=w.level_triangles(decoded,decoded['levels'][li])
                    w.require(w.canonical(after)==w.canonical(expected.get(li,before)),'serialized level proof')
                    if li not in expected:w.require(after==before,'untouched strip sequence');untouched_levels+=1
                    if ordinal>0:w.require(w.canonical(after)==w.canonical(before),'higher LOD changed')
                    if mi in owners:
                        w.require(after==w.level_triangles(d,d['levels'][li]),'changing owner exact');owner_levels+=1
    h=struct.unpack_from('<4s19I',mesh)
    row=[0x101,len(pol),len(out['placements']),len(out['parts']),len(out['meshes']),struct.unpack_from('<I',pol,20)[0],w.fnv(pol),h[3],len(mesh),policy]
    (a.out/'world_rebuild27_certificates.inc').write_text('// PRIVATE named house replacement, no visibility certificate.\nstatic constexpr Certificate rebuild27_certificates[] = {\n{'+','.join('0x%08xU'%v for v in row)+'},\n};\n')
    context_receipt=json.loads((a.context/'RECEIPT.json').read_text())
    receipt=dict(name=a.out.name,operation=plan['operation'],source_sha256={n:w.sha(v) for n,v in files.items()},
      context_sha256=plan['context_sha256'],plan_sha256=w.sha(plan_bytes),tool_sha256=w.sha(Path(__file__).read_bytes()),
      helper_sha256=plan['helper_sha256'],candidate_sha256=w.sha(mesh),candidate_bytes=len(mesh),candidate_crc='%08x'%h[3],
      certificate_row=row,unchanged_companion_sha256=companion_hashes,unchanged_companions_readback_verified=True,
      core_triangles_before=source_count,core_triangles_after=len(wall)+len(roof),walls_triangles=len(wall),roof_triangles=len(roof),
      l0_triangles_before=context_receipt['l0_triangles_after'],l0_triangles_after=context_receipt['l0_triangles_after']-source_count+len(wall)+len(roof),
      unique_owner_meshes=len(owners),owner_levels_exact=owner_levels,untouched_levels_sequence_exact=untouched_levels,
      all_higher_lods_unchanged=True,all_other_world_geometry_exact_to_context=True,
      appearance_accepted=False,timing_available=False,lostpart_verdict='NOT RUN; no source-feature or native appearance PASS inferred',
      wall_groups=wall_proof,roof_groups=roof_proof,remaining_differences=plan['remaining_differences'])
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');(a.out/'house-plan.json').write_bytes(plan_bytes)
    (a.out/'RECIPE.txt').write_text('Private named right-house wall/roof replacement, default off.\nCommand: '+json.dumps(sys.argv)+'\nNo runtime/staging/texture changes. No timing/appearance acceptance.\n')
    (a.out/'SHA256SUMS').write_text(''.join(w.sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(a.out.iterdir()) if p.is_file()))
    print(json.dumps({k:receipt[k] for k in ('name','candidate_sha256','candidate_bytes','core_triangles_before','core_triangles_after','walls_triangles','roof_triangles','l0_triangles_after')},indent=2))


if __name__=='__main__':main()
