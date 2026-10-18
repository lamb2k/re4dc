"""Private far-only r101 study using native Blender Dissolve/Collapse and Data Transfer.

Preserves L0 except clusters proved permanently far from walkable space;
otherwise replaces an existing coarsest level only. Sampled bidirectional
surface distance is a rejection filter, not a Hausdorff proof. The package and
runtime acceptance gates remain independent. All thin/small connected pieces,
open boundaries, UV seams and sharp edges receive protected vertex weights.
"""
import bpy,bmesh,json,sys,math,time,collections
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def colour(c):return (((c>>10)&31)/31,((c>>5)&31)/31,(c&31)/31,float((c>>15)&1))
def rgba(c):return (round(c[3])<<15)|(round(max(0,min(1,c[0]))*31)<<10)|(round(max(0,min(1,c[1]))*31)<<5)|round(max(0,min(1,c[2]))*31)
def make(row,triangles,name):
    # PS2 per-corner colour/UV records are Blender loop data, not mesh splits.
    keys=list(dict.fromkeys(tuple(k[:3]) for t in triangles for k in t));index={k:i for i,k in enumerate(keys)}
    pos=[tuple(row['step'][a]*k[a] for a in range(3)) for k in keys]
    faces=[[index[tuple(k[:3])] for k in t] for t in triangles]
    me=bpy.data.meshes.new(name);me.from_pydata(pos,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    ob.location=row['origin']
    ca=me.color_attributes.new(name='BakedLighting',type='FLOAT_COLOR',domain='CORNER');uv=me.uv_layers.new(name='SourceUV')
    for face,tri in zip(me.polygons,triangles):
      for li,k in zip(face.loop_indices,tri):
        ca.data[li].color=colour(k[5]);uv.data[li].uv=(k[3]/65535,k[4]/65535)
    decoded=[]
    for face in me.polygons:
      tri=[]
      for li in face.loop_indices:
        p=me.vertices[me.loops[li].vertex_index].co
        tri.append(tuple(round(p[a]/row['step'][a]) for a in range(3))+tuple(round(u*65535) for u in uv.data[li].uv)+(rgba(ca.data[li].color),))
      decoded.append(tuple(tri))
    def canonical(ts):return collections.Counter(min(t,t[1:]+t[:1],t[2:]+t[:2]) for t in ts)
    assert canonical(decoded)==canonical([tuple(tuple(k) for k in t) for t in triangles]),'Blender loop/corner roundtrip changed source'
    return ob,keys

def protect(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    fixed=set();seen=set();reasons=dict(boundary=set(),sharp=set(),seam=set(),small=set())
    for edge in bm.edges:
        seam=False
        if len(edge.link_faces)==2:
            uv=bm.loops.layers.uv.active
            for v in edge.verts:
                loops=[l for f in edge.link_faces for l in f.loops if l.vert==v]
                if uv and len(loops)==2 and (loops[0][uv].uv-loops[1][uv].uv).length>1e-6:seam=True
        if len(edge.link_faces)!=2 or edge.calc_face_angle(0)>0.35 or seam:
            fixed.update(v.index for v in edge.verts)
            reason='boundary' if len(edge.link_faces)!=2 else 'sharp' if edge.calc_face_angle(0)>0.35 else 'seam'
            reasons[reason].update(v.index for v in edge.verts)
    for v in bm.verts:
        if v.index in seen:continue
        component={v.index};todo=[v];seen.add(v.index)
        while todo:
            u=todo.pop()
            for edge in u.link_edges:
                w=edge.other_vert(u)
                if w.index not in seen:seen.add(w.index);component.add(w.index);todo.append(w)
        coords=[bm.verts[i].co for i in component]
        extent=sorted(max(p[a] for p in coords)-min(p[a] for p in coords) for a in range(3))
        if len(component)<24 or extent[1]<500:fixed.update(component);reasons['small'].update(component)
    bm.free()
    movable=[v.index for v in ob.data.vertices if v.index not in fixed]
    vg=ob.vertex_groups.new(name='MayReduce')
    if movable:vg.add(movable,1,'REPLACE')
    return fixed,movable,{k:len(v) for k,v in reasons.items()}

def surface_samples(me):
    pts=[v.co.copy() for v in me.vertices]
    for p in me.polygons:
        vs=[me.vertices[i].co for i in p.vertices]
        pts.append(sum(vs,Vector())/len(vs))
        for i,v in enumerate(vs):pts.append((v+vs[(i+1)%len(vs)])/2)
    return pts

def distance(a,b):
    bvh=BVHTree.FromPolygons([v.co for v in b.vertices],[p.vertices[:] for p in b.polygons],all_triangles=True)
    return max((bvh.find_nearest(p)[3] or 0) for p in surface_samples(a))

def main():
    assert not bpy.app.online_access
    path=Path(sys.argv[sys.argv.index('--')+1]);data=json.loads((path/'blender-input.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    reports=[];changes={};start=time.time()
    for row in data['clusters']:
        if len(row['levels'])<2 and not row['far']:continue
        original,okeys=make(row,row['levels'][0]['triangles'],'original-%04d'%row['cluster'])
        low,lkeys=make(row,row['levels'][-1]['triangles'],'far-%04d'%row['cluster'])
        fixed,movable,reasons=protect(low);before=len(low.data.polygons)
        fixed_coordinates=[low.data.vertices[i].co.copy() for i in fixed]
        bpy.context.view_layer.objects.active=low
        technique='collapse'
        if movable:
            mod=low.modifiers.new('Native protected collapse','DECIMATE');mod.decimate_type='COLLAPSE';mod.ratio=.70
            mod.vertex_group='MayReduce';mod.vertex_group_factor=1000;mod.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        after=len(low.data.polygons)
        # Pin check: every protected original coordinate remains a vertex.
        preserved=all(any((p-v.co).length<1e-5 for v in low.data.vertices) for p in fixed_coordinates)
        err=max(distance(original.data,low.data),distance(low.data,original.data)) if after<before and preserved else None
        accepted=err is not None and err<=23.0 and after<before
        reason='candidate' if accepted else ('protected_vertices_changed' if not preserved else 'no_saving' if after>=before else 'surface_error')
        if accepted:
            mod=low.modifiers.new('Transfer original UV and baked lighting','DATA_TRANSFER');mod.object=original
            mod.use_loop_data=True;mod.data_types_loops={'COLOR_CORNER','UV'};mod.loop_mapping='POLYINTERP_NEAREST'
            bpy.ops.object.modifier_apply(modifier=mod.name)
            me=low.data;uv=me.uv_layers['SourceUV'];ca=me.color_attributes['BakedLighting'];ts=[]
            for face in me.polygons:
                assert len(face.loop_indices)==3
                out=[]
                for li in face.loop_indices:
                    v=me.vertices[me.loops[li].vertex_index].co
                    q=[min(65535,max(0,round(v[a]/row['step'][a]))) for a in range(3)]
                    tex=[min(65535,max(0,round(u*65535))) for u in uv.data[li].uv]
                    out.append(q+tex+[rgba(ca.data[li].color)])
                if len({tuple(x[:3]) for x in out})==3:ts.append(out)
            changes[str(row['cluster'])]=dict(triangles=ts,error_mm=err,level=len(row['levels'])-1)
        original.hide_render=True;original.hide_viewport=True
        reports.append(dict(cluster=row['cluster'],part=row['part'],technique=technique,before=before,after=after,
                            protected_vertices=len(fixed),movable_vertices=len(movable),pins_preserved=preserved,
                            sampled_error_mm=err,accepted=accepted,reason=reason,protection_reasons=reasons))
    bpy.ops.wm.save_as_mainfile(filepath=str(path/'r101-far-pilot.blend'))
    summary=dict(technique='Blender Collapse, protected boundaries and small/thin pieces; Data Transfer UV and lighting',
                 source_sha256=data['source_sha256'],blender_version=bpy.app.version_string,changed_clusters=len(changes),
                 triangles_removed=sum(r['before']-r['after'] for r in reports if r['accepted']),elapsed_s=time.time()-start,
                 limits='23 model-unit sampled surface distance; source L0 protected unless permanently far; placement scale must qualify any screen-space claim; no runtime acceptance yet')
    (path/'blender-far-output.json').write_text(json.dumps(dict(summary=summary,changes=changes,clusters=reports),separators=(',',':')))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
