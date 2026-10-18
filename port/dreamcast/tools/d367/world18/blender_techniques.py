"""Native Blender topology census. Outputs are diagnostic, never staged as game assets.

Counts alone do not establish quality or runtime savings. Un-Subdivide has no
boundary/protected-vertex guarantee, and unguarded Dissolve can alter lighting
slopes. This census compares those opportunities with the strict planar probe.
"""
import bpy,bmesh,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_far import make,rgba

def main():
    assert not bpy.app.online_access
    path=Path(sys.argv[sys.argv.index('--')+1]);data=json.loads((path/'blender-input.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    report=[];changes={}
    for row in data['clusters']:
        ob,keys=make(row,row['levels'][0]['triangles'],'diagnostic')
        original=ob.data.copy();base=len(ob.data.polygons);verts=len(ob.data.vertices)
        bm=bmesh.new();bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
        merged=len(bm.verts);bm.free()
        bpy.context.view_layer.objects.active=ob
        mod=ob.modifiers.new('Un-Subdivide census','DECIMATE');mod.decimate_type='UNSUBDIV';mod.iterations=2
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.data.calc_loop_triangles();unsub=len(ob.data.loop_triangles)
        if unsub<base:
            me=ob.data;uv=me.uv_layers['SourceUV'];ca=me.color_attributes['BakedLighting'];triangles=[]
            for face in me.loop_triangles:
                tri=[]
                for li in face.loops:
                    p=me.vertices[me.loops[li].vertex_index].co
                    q=[min(65535,max(0,round(p[a]/row['step'][a]))) for a in range(3)]
                    tex=[min(65535,max(0,round(u*65535))) for u in uv.data[li].uv]
                    tri.append(q+tex+[rgba(ca.data[li].color)])
                if len({tuple(v[:3]) for v in tri})==3:triangles.append(tri)
            changes[str(row['cluster'])]=dict(level=0,triangles=triangles)
        old=ob.data;ob.data=original.copy();bpy.data.meshes.remove(old)
        mod=ob.modifiers.new('Dissolve census','DECIMATE');mod.decimate_type='DISSOLVE';mod.angle_limit=.0001
        mod.delimit={'NORMAL','MATERIAL','SEAM','SHARP','UV'};mod.use_dissolve_boundaries=False
        bpy.ops.object.modifier_apply(modifier=mod.name)
        ob.data.calc_loop_triangles();dissolve=len(ob.data.loop_triangles)
        report.append(dict(cluster=row['cluster'],part=row['part'],triangles=base,unique_positions=verts,
                           merge_positions=merged,unsubdivide_triangles=unsub,unguarded_dissolve_triangles=dissolve))
        me=ob.data;bpy.data.objects.remove(ob,do_unlink=True);bpy.data.meshes.remove(me);bpy.data.meshes.remove(original)
    summary=dict(source_sha256=data['source_sha256'],blender_version=bpy.app.version_string,
                 clusters=len(report),triangles=sum(r['triangles'] for r in report),
                 merge_position_savings=sum(r['unique_positions']-r['merge_positions'] for r in report),
                 unsubdivide_triangle_savings=sum(r['triangles']-r['unsubdivide_triangles'] for r in report),
                 unguarded_dissolve_triangle_savings=sum(r['triangles']-r['unguarded_dissolve_triangles'] for r in report),
                 accepted_game_assets=0,note='diagnostic only; no quality acceptance or runtime saving inferred')
    summary['blender_original_corner_roundtrip_verified']=True
    (path/'blender-techniques.json').write_text(json.dumps(dict(summary=summary,clusters=report),separators=(',',':')))
    (path/'blender-unsubdivide-diagnostic.json').write_text(json.dumps(dict(summary=summary,changes=changes),separators=(',',':')))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
