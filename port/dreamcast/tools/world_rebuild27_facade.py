#!/usr/bin/env python3
"""Bounded one-component semantic wall-plane proof, existing source material."""
import collections
import json
import math
import argparse
import copy
from pathlib import Path
import struct
import subprocess
import sys

def build(d,w,dependencies,diagnostic):
    sys.path.insert(0,str(dependencies))
    import numpy as np
    import shapely
    from shapely.geometry import Polygon
    pi=160;mi=104;m=d['meshes'][mi];fc,cc=d['part_lods'][pi]
    pl=next(p for p in d['placements'] if p[0]==mi);A=np.asarray(pl[2:]).reshape(3,4)
    triangles=[];identities=[]
    for ci in range(fc,fc+cc):
        for ti,t in enumerate(w.level_triangles(d,d['levels'][d['clusters'][ci][6]])):
            triangles.append(t);identities.append((ci,ti))
    parents={}
    def find(x):
        parents.setdefault(x,x)
        while parents[x]!=x:parents[x]=parents[parents[x]];x=parents[x]
        return x
    for t in triangles:
        root=find(t[0][:3])
        for v in t[1:]:parents[find(v[:3])]=root
    groups=collections.defaultdict(list)
    for i,t in enumerate(triangles):groups[find(t[0][:3])].append(i)
    candidate=[]
    for ix in groups.values():
        if len(ix)!=145:continue
        q=np.asarray([[v[:3] for v in triangles[i]] for i in ix],float)
        local=q*np.asarray(m[11:14])+np.asarray(m[8:11]);world=local@A[:,:3].T+A[:,3]
        lo=world.reshape(-1,3).min(0);hi=world.reshape(-1,3).max(0)
        if max(abs(lo-np.asarray([-1064,862,7826])))<3 and max(abs(hi-np.asarray([10666,5767,21110])))<3:candidate=ix
    assert len(candidate)==145,'Pinned near right-facade component mapping'
    q=np.asarray([[v[:3] for v in triangles[i]] for i in candidate],float)
    xyz=q*np.asarray(m[11:14]);nn=np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0]);areas=np.linalg.norm(nn,axis=1)
    normals=nn/np.maximum(areas[:,None],1e-12);centers=xyz.mean(1)
    choices=[]
    for seed in range(len(candidate)):
        n=normals[seed]
        if abs(n[1])>.25:continue # Explicit vertical facade plane, roofs excluded.
        distances=np.abs((xyz-xyz[seed,0])@n).max(1)
        keep=(normals@n>.999)&(distances<20)
        ids=np.where(keep)[0];total=float(areas[ids].sum())
        choices.append((total,seed,ids))
    choices.sort(key=lambda v:v[0],reverse=True)
    total,seed,indices=choices[0];n=normals[seed]
    origin=xyz[seed,0];u=xyz[seed,1]-origin;u/=np.linalg.norm(u);v=np.cross(n,u)
    projected=(xyz-origin)@np.stack([u,v]).T
    polygons=[Polygon(projected[i]) for i in indices]
    union=shapely.unary_union(polygons)
    result=dict(component_triangles=145,component_source_ids=[identities[i] for i in candidate],selected_plane_triangles=len(indices),selected_ids=[identities[candidate[i]] for i in indices],normal=n.tolist(),origin=origin.tolist(),plane_u=u.tolist(),plane_v=v.tolist(),maximum_plane_relief_local=float(np.abs((xyz[indices]-origin)@n).max()),union_type=union.geom_type,union_area=union.area,source_polygon_area_sum=sum(p.area for p in polygons),polygons=[])
    polys=list(union.geoms) if union.geom_type=='MultiPolygon' else [union]
    for poly in polys:
        result['polygons'].append(dict(exterior=list(poly.exterior.coords),holes=[list(h.coords) for h in poly.interiors],area=poly.area))
    # One bounded source-derived architectural plane. Simplify the broad outer
    # wall outline by at most 20 mm in world space; retain the measured window
    # aperture and conservatively expand it by 2 mm to cover quantization.
    assert union.geom_type=='Polygon' and len(union.interiors)==1
    scale=max(np.linalg.norm(A[:,:3],axis=0));outer=Polygon(union.exterior).simplify(2/scale,preserve_topology=True)
    holes=[Polygon(h).buffer(2/scale,join_style='mitre') for h in union.interiors]
    target=outer.difference(shapely.unary_union(holes))
    assert target.geom_type=='Polygon' and len(target.interiors)==1
    authored=list(shapely.constrained_delaunay_triangles(target).geoms)
    source_corners=list(dict.fromkeys(v for i in indices for v in triangles[candidate[i]]))
    local_corners=np.asarray([a[:3] for a in source_corners])*np.asarray(m[11:14])
    corner_map={};output=[]
    for t in authored:
        ring=list(t.exterior.coords)[:3];values=[]
        for point in ring:
            key=tuple(point)
            if key not in corner_map:
                local=origin+point[0]*u+point[1]*v
                grid=np.rint(local/np.asarray(m[11:14])).astype(int)
                assert (grid>=0).all() and (grid<=65535).all()
                nearest=int(np.argmin(((local_corners-local)**2).sum(1)))
                corner_map[key]=tuple(int(a) for a in grid)+tuple(source_corners[nearest][3:])
            values.append(corner_map[key])
        pp=np.asarray([a[:3] for a in values])*np.asarray(m[11:14])
        if np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),n)<0:values.reverse()
        output.append(tuple(values))
    # Independently project the serialized-grid triangles and prove coverage
    # and the source hole remain open before writing a package.
    emitted=[]
    for t in output:
        pp=np.asarray([a[:3] for a in t])*np.asarray(m[11:14]);xy=(pp-origin)@np.stack([u,v]).T
        assert np.dot(np.cross(pp[1]-pp[0],pp[2]-pp[0]),n)>0
        emitted.append(Polygon(xy))
    emitted_union=shapely.unary_union(emitted)
    hole=Polygon(union.interiors[0]);filled=hole.intersection(emitted_union).area
    assert filled<1e-6,'window aperture filled after quantization'
    assert emitted_union.geom_type=='Polygon' and len(emitted_union.interiors)==1
    result.update(operation='one source-derived vertical architectural plane with independently preserved window aperture',source_material_key='%08x-%08x'%tuple(d['materials'][pi][:2]),world_scale=float(scale),source_plane_relief_world_mm=float(np.abs((xyz[indices]-origin)@n).max()*scale),output_triangles=len(output),source_triangles_removed=len(indices),outer_boundary_maximum_simplification_world_mm=2,aperture_expansion_world_mm=2,source_window_aperture_area=hole.area,source_aperture_filled_area=filled,output_projected_union_area=emitted_union.area,outer_boundary_hausdorff_world_mm=union.exterior.hausdorff_distance(emitted_union.exterior)*scale,output_apertures=1,changing_owners_exact=True,ground_exact=True,all_other_source_components_exact=True,higher_lods_exact=True,appearance_accepted=False,timing_available=False,texture_approximation='nearest source UV/prelight per authored corner; existing resident PS2 key only',output_oriented_corners=output,source_corner_assignments=[dict(projected=list(k),output_corner=list(value)) for k,value in corner_map.items()])
    diagnostic.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('selected_plane_triangles','maximum_plane_relief_local','union_type','union_area','source_polygon_area_sum')},indent=2))
    print('Polygon contours',[(len(p.exterior.coords),[len(h.coords) for h in p.interiors]) for p in polys])
    selected_ids={tuple(x) for x in result['selected_ids']};target_ci=min(ci for ci,ti in selected_ids)
    replacements={}
    for ci in {ci for ci,ti in selected_ids}:
        source=w.level_triangles(d,d['levels'][d['clusters'][ci][6]])
        replacements[ci]=[t for ti,t in enumerate(source) if (ci,ti) not in selected_ids]
    replacements[target_ci].extend(output)
    return replacements,result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--helper-dir',type=Path,required=True);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--b1',type=Path,required=True);ap.add_argument('--dependencies',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();sys.path.insert(0,str(a.helper_dir));import world_rebuild27 as w
    assert not a.out.exists(),'immutable output exists'
    d,files,owners,policy=w.load(a.source)
    b1blob=(a.b1/'ps2-world.re4mesh').read_bytes();b1r=json.loads((a.b1/'RECEIPT.json').read_text())
    assert w.sha(b1blob)==b1r['candidate_sha256']
    for name,pin in b1r['source_sha256'].items():assert w.sha((a.source/name).read_bytes())==pin
    b=w.codec.decode(b1blob,files['ps2-world.r4pw']);a.out.mkdir(parents=True)
    replacements,proof=build(d,w,a.dependencies,a.out/'SOURCE-PLANE-PROOF.json')
    # The existing packer supports one replacement per cluster. This explicit
    # read provider supplies the authored L0 once and each original higher LOD
    # thereafter; no source helper or runtime changes are necessary.
    class LevelProvider(dict):
        def __init__(self):
            super().__init__(replacements);self.cursor=collections.Counter();self.expected={}
            for ci,ts in replacements.items():
                c=b['clusters'][ci];seq=[]
                for ordinal in range(c[7]):
                    lv=b['levels'][c[6]+ordinal]
                    value=ts if ordinal==0 else w.level_triangles(b,lv)
                    self.expected[c[6]+ordinal]=value
                    if lv[1]:seq.append(value)
                dict.__setitem__(self,ci,seq)
        def __getitem__(self,ci):
            ordinal=self.cursor[ci];self.cursor[ci]+=1
            return dict.__getitem__(self,ci)[ordinal]
    provider=LevelProvider();out=w.install_shells(b,provider)
    blob=w.codec.serialize_mesh(out);pol=w.codec.serialize_policy(out);assert pol==files['ps2-world.r4pw']
    (a.out/'ps2-world.raw.re4mesh').write_bytes(blob);(a.out/'ps2-world.r4pw').write_bytes(pol)
    cmd=[sys.executable,str(a.helper_dir/'ps2_strip_groups.py'),str(a.out/'ps2-world.raw.re4mesh'),str(a.out/'ps2-world.r4pw'),str(a.out/'ps2-world.re4mesh'),str(a.out/'ps2-world.r4sg'),'--groups','4','--report',str(a.out/'strip-groups.json')]
    run=subprocess.run(cmd,check=True,capture_output=True,text=True);(a.out/'strip-groups.log').write_text(run.stdout+run.stderr)
    sg=bytearray((a.out/'ps2-world.r4sg').read_bytes());struct.pack_into('<I',sg,24,policy);(a.out/'ps2-world.r4sg').write_bytes(sg)
    for name in ('ps2-world.ids','ps2-world.r4tc','room.r4rc'):(a.out/name).write_bytes((a.source/name).read_bytes())
    mesh=(a.out/'ps2-world.re4mesh').read_bytes();decoded=w.codec.decode(mesh,pol)
    checks=dict(changing_owner_meshes_exact_all_levels=0,owner_levels_checked=0,ground_exact_all_levels=True,all_higher_lods_exact=True,all_other_components_exact=True,source_aperture_filled_area=proof['source_aperture_filled_area'],authored_triangles_source_winding=True,source_identity_tables_unchanged=True,unchanged_companions=['ps2-world.r4pw','ps2-world.ids','ps2-world.r4tc','room.r4rc'])
    for key in ('meshes','placements','materials','part_lods'):assert decoded[key]==d[key]
    assert [c[6:] for c in decoded['clusters']]==[c[6:] for c in d['clusters']]
    for mi,m in enumerate(d['meshes']):
        if mi in owners:checks['changing_owner_meshes_exact_all_levels']+=1
        for pi in range(m[6],m[6]+m[7]):
            fc,cc=d['part_lods'][pi]
            for ci in range(fc,fc+cc):
                c=d['clusters'][ci]
                for ordinal in range(c[7]):
                    li=c[6]+ordinal;before=w.level_triangles(b,b['levels'][li]);after=w.level_triangles(decoded,decoded['levels'][li])
                    expected=provider.expected.get(li,before)
                    assert w.canonical(after)==w.canonical(expected),'serialized level differs from proof'
                    if ordinal>0:assert w.canonical(after)==w.canonical(before),'higher LOD changed'
                    if mi in owners:
                        assert after==w.level_triangles(d,d['levels'][li]);checks['owner_levels_checked']+=1
                    if mi in (163,188):assert after==w.level_triangles(d,d['levels'][li])
    h=struct.unpack_from('<4s19I',mesh);row=[0x101,len(pol),len(out['placements']),len(out['parts']),len(out['meshes']),struct.unpack_from('<I',pol,20)[0],w.fnv(pol),h[3],len(mesh),policy]
    (a.out/'world_rebuild27_certificates.inc').write_text('// PRIVATE B2 bounded facade proof; no visibility certification.\nstatic constexpr Certificate rebuild27_certificates[] = {\n{'+','.join('0x%08xU'%v for v in row)+'},\n};\n')
    receipt=copy.deepcopy(b1r);receipt.update(name=a.out.name,operation=proof['operation'],candidate_bytes=len(mesh),candidate_crc='%08x'%h[3],candidate_sha256=w.sha(mesh),certificate_row=row,l0_triangles_after=b1r['l0_triangles_after']-proof['source_triangles_removed']+proof['output_triangles'],tool_sha256=w.sha(Path(__file__).read_bytes()),helper_sha256=w.sha((a.helper_dir/'world_rebuild27.py').read_bytes()),b1_sha256=w.sha(b1blob),source_plane_proof='SOURCE-PLANE-PROOF.json',checks=checks,appearance_accepted=False,timing_available=False,source_l0_triangles_removed=proof['source_triangles_removed'],authored_l0_triangles=proof['output_triangles'])
    for r in receipt['feature_rows']:
        if r['part']==160:r['l0_triangles_after']-=proof['source_triangles_removed']-proof['output_triangles']
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (a.out/'INDEPENDENT-VERIFICATION.json').write_text(json.dumps(dict(checks=checks,projection_checks=proof,acceptance='Offline source/serialized geometry proof only; no native appearance or timing acceptance'),indent=2)+'\n')
    (a.out/'RECIPE.txt').write_text('PRIVATE DEFAULT-OFF B2 semantic facade proof. No production recipe or runtime changes.\nCommand: '+json.dumps(sys.argv)+'\nSource41-triangle near-house wall plane ->20triangles; one window aperture preserved with2mm conservative expansion.\nPart160/mesh104 only; every other source component, all higherLODs, owners, ground, all companions unchanged.\nPS2 source texture0c77c65b-a7d392ac unchanged. UV/prelight/depth approximation unaccepted.\nDependencies: Shapely2.1.2, NumPy2.2.6 for offline authoring only.\n')
    (a.out/'SHA256SUMS').write_text(''.join(w.sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(a.out.iterdir()) if p.is_file()))
    print(json.dumps({k:receipt[k] for k in ('name','l0_triangles_after','candidate_bytes','candidate_crc','candidate_sha256')},indent=2))

if __name__=='__main__':main()
