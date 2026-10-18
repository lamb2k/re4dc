"""Run inside official Blender: exact planar dissolve, keeping UV/colour slopes and boundaries.

This first pilot permits only topology changes whose position, UV and ARGB1555
interpolants are identical. No Collapse, Merge-by-Distance or Un-Subdivide is
accepted on this pass: they can move a boundary or change a lighting slope.
"""
import bpy,bmesh,json,sys,math,time
from pathlib import Path
from mathutils import Vector

def colour(c):return ((c>>10)&31,(c>>5)&31,c&31,(c>>15)&1)
def compatible(edge,row):
    if len(edge.link_faces)!=2:return False
    f,g=edge.link_faces
    if len(f.verts)!=3 or len(g.verts)!=3:return False
    vs=list(f.verts);other=[v for v in g.verts if v not in vs]
    if len(other)!=1:return False
    d=other[0]
    a,b,c=[v.co for v in vs];p=d.co
    u=b-a;v=c-a;n=u.cross(v)
    if n.length_squared<1e-20 or abs(n.dot(p-a))/n.length>1e-5:return False
    uu=u.dot(u);uv=u.dot(v);vv=v.dot(v);w=p-a;den=uu*vv-uv*uv
    if den<=1e-20:return False
    x=(w.dot(u)*vv-w.dot(v)*uv)/den;y=(w.dot(v)*uu-w.dot(u)*uv)/den
    ks=[row['keys'][z.index] for z in vs]+[row['keys'][d.index]]
    attrs=[(*k[3:5],*colour(k[5])) for k in ks]
    return all(abs(attrs[0][i]+x*(attrs[1][i]-attrs[0][i])+y*(attrs[2][i]-attrs[0][i])-attrs[3][i])<1e-4 for i in range(6))

def main():
    assert not bpy.app.online_access
    path=Path(sys.argv[sys.argv.index('--')+1]);data=json.loads((path/'blender-input.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    report=[];changes={};start=time.time()
    for row in data['clusters']:
        me=bpy.data.meshes.new('source-%04d'%row['cluster']);me.from_pydata(row['positions'],[],row['faces']);me.update()
        src=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(src)
        src['part']=row['part'];src['cluster']=row['cluster'];src['bin']=row['bin'];src['protected_surface']=True
        ca=me.color_attributes.new(name='BakedLighting',type='FLOAT_COLOR',domain='CORNER')
        uv=me.uv_layers.new(name='SourceUV')
        for loop in me.loops:
            k=row['keys'][loop.vertex_index];cc=colour(k[5]);ca.data[loop.index].color=(*[v/31 for v in cc[:3]],float(cc[3]));uv.data[loop.index].uv=(k[3]/65535,k[4]/65535)
        bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();bm.verts.index_update()
        layer=bm.verts.layers.int.new('source_corner')
        for vert in bm.verts:vert[layer]=vert.index
        good=[]
        for edge in bm.edges:
            if compatible(edge,row):good.append(edge)
            else:edge.seam=True
        if good:
            goodset=set(good)
            interior=[v for v in bm.verts if v.link_edges and all(e in goodset for e in v.link_edges)]
            bmesh.ops.dissolve_limit(bm,angle_limit=1e-7,verts=interior,edges=good,use_dissolve_boundaries=False,delimit={'SEAM','SHARP','UV','MATERIAL'})
            bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
        out=[]
        for face in bm.faces:
            assert len(face.verts)==3
            out.append([row['keys'][v[layer]] for v in face.verts])
        before=len(row['faces']);after=len(out)
        accepted=after<before
        if accepted:
            # Store evaluated native Blender output plus the original corner IDs.
            target_mesh=bpy.data.meshes.new('dissolve-%04d'%row['cluster']);bm.to_mesh(target_mesh);target_mesh.update()
            target=bpy.data.objects.new(target_mesh.name,target_mesh);bpy.context.collection.objects.link(target)
            mod=target.modifiers.new('Restore baked lighting','DATA_TRANSFER');mod.object=src
            mod.use_loop_data=True;mod.data_types_loops={'COLOR_CORNER'};mod.loop_mapping='POLYINTERP_NEAREST'
            bpy.context.view_layer.objects.active=target;target.select_set(True)
            bpy.ops.object.modifier_apply(modifier=mod.name);target.select_set(False)
            src.hide_render=True;src.hide_viewport=True
            changes[str(row['cluster'])]=out
        report.append(dict(cluster=row['cluster'],part=row['part'],before=before,after=after,compatible_edges=len(good),accepted=accepted))
        bm.free()
    bpy.ops.wm.save_as_mainfile(filepath=str(path/'r101-planar-pilot.blend'))
    summary=dict(technique='Blender native Limited Dissolve; exact position/UV/colour-slope guard',
                 blender_version=bpy.app.version_string,source_sha256=data['source_sha256'],
                 changed_clusters=len(changes),triangles_before=sum(r['before'] for r in report),
                 triangles_after=sum(r['after'] if r['accepted'] else r['before'] for r in report),elapsed_s=time.time()-start)
    (path/'blender-output.json').write_text(json.dumps(dict(summary=summary,changes=changes,clusters=report),separators=(',',':')))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
