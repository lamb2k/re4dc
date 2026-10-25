"""Real bpy mutations against a saved/reopened fixture; each must fail closed."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import blender_bridge as bridge
import package as p
import sidecars


def main():
    import bpy
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--blend',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:])
    doc,files=bridge.load_bundle(args.source)

    def ob(name='draw.000001.000000'):return bpy.data.objects[name]
    def mesh():return ob().data
    def mat():return bpy.data.materials['material.000000']
    def prop(obj,key,index,value):
        r=json.loads(obj[key]);r[index]=value;obj[key]=bridge.js(r)
    def source_change():
        source=json.loads(bpy.context.scene['r4_sources']);source['ps2-world.re4mesh']='0'*64
        bpy.context.scene['r4_sources']=bridge.js(source)
    def add_object():
        o=bpy.data.objects.new('foreign-object',None);bpy.context.scene.collection.objects.link(o)
    def modifier():ob().modifiers.new('forbidden','DECIMATE')
    def identity_change():prop(ob('mesh.000000'),'r4_record',0,999)
    def matrix_change():prop(ob('placement.000001'),'r4_record',3,9.0)
    def aux_change(key):
        a=json.loads(bpy.context.scene['r4_aux']);a[key][0]=0;bpy.context.scene['r4_aux']=bridge.js(a)
    controls=[
        ('position',lambda:setattr(mesh().vertices[0].co,'x',mesh().vertices[0].co.x+1.0)),
        ('coarse-LOD-position',lambda:setattr(ob('draw.000001.000001').data.vertices[0].co,'x',99.0)),
        ('shared-placement-copy',lambda:setattr(ob('draw.000002.000000').data.vertices[0].co,'z',99.0)),
        ('UV',lambda:setattr(mesh().uv_layers['uv'].data[0].uv,'x',9.0)),
        ('prelit-color',lambda:setattr(mesh().color_attributes['prelit'].data[0],'color',(0,0,0,1))),
        ('quantized-position',lambda:setattr(mesh().attributes['r4_qx'].data[0],'value',1)),
        ('quantized-UV',lambda:setattr(mesh().attributes['r4_qu'].data[0],'value',1)),
        ('quantized-color',lambda:setattr(mesh().attributes['r4_argb1555'].data[0],'value',0)),
        ('source-vertex-id',lambda:setattr(mesh().attributes['r4_vertex_id'].data[0],'value',1)),
        ('triangle-winding',lambda:setattr(mesh().loops[0],'vertex_index',2)),
        ('smooth-normal',lambda:setattr(mesh().polygons[0],'use_smooth',True)),
        ('extra-UV-layer',lambda:mesh().uv_layers.new(name='extra')),
        ('extra-point-attribute',lambda:mesh().attributes.new('foreign','INT','POINT')),
        ('shape-key',lambda:ob().shape_key_add(name='foreign')),
        ('modifier',modifier),
        ('object-transform',lambda:setattr(ob().location,'x',1.0)),
        ('object-parent',lambda:setattr(ob(),'parent',ob('mesh.000000'))),
        ('object-addition',add_object),
        ('object-deletion',lambda:bpy.data.objects.remove(ob(),do_unlink=True)),
        ('object-rename',lambda:setattr(ob(),'name','wrong-name')),
        ('mesh-source-id',identity_change),
        ('part-source-offset',lambda:prop(ob('part.000000'),'r4_record',0,999)),
        ('cluster-bounds',lambda:prop(ob('cluster.000000'),'r4_record',0,1)),
        ('LOD-error',lambda:prop(ob('level.000001'),'r4_record',2,999.)),
        ('strip-command',lambda:ob().__setitem__('r4_commands','{}')),
        ('placement-affine-metadata',matrix_change),
        ('placement-affine-basis',lambda:setattr(ob('placement.000001').data.vertices[1].co,'x',123.0)),
        ('placement-source-id',lambda:prop(ob('placement.000001'),'r4_record',1,99)),
        ('pass',lambda:prop(mat(),'r4_record',4,2)),
        ('cull',lambda:prop(mat(),'r4_record',5,2)),
        ('texture-key',lambda:prop(mat(),'r4_record',0,0)),
        ('material-node-strength',lambda:setattr(mat().node_tree.nodes['emission'].inputs['Strength'],'default_value',2.)),
        ('material-node-link',lambda:mat().node_tree.links.remove(mat().node_tree.links[0])),
        ('material-property',lambda:setattr(mat(),'use_backface_culling',True)),
        ('material-scalar-setting',lambda:setattr(mat(),'use_transparency_overlap',False)),
        ('material-assignment',lambda:mesh().materials.clear()),
        ('material-addition',lambda:bpy.data.materials.new('foreign-material')),
        ('animation',lambda:ob().keyframe_insert(data_path='location',frame=1)),
        ('LOD-visibility',lambda:setattr(ob('draw.000001.000001'),'hide_viewport',False)),
        ('palette',lambda:aux_change('palette')),
        ('class',lambda:aux_change('classes')),
        ('source-hash',source_change),
        ('scene-unit',lambda:setattr(bpy.context.scene.unit_settings,'scale_length',1000.)),
    ]
    results=[]
    for name,mutate in controls:
        bpy.ops.wm.open_mainfile(filepath=str(args.blend),load_ui=False,use_scripts=False)
        mutate()
        try:
            result=bridge.validate_scene(bpy,doc,files)
            sidecars.rebuild(files,result,p.serialize_mesh(result),p.serialize_policy(result))
        except ValueError as error:
            results.append(dict(control=name,rejected=True,reason=str(error)))
        else:
            raise AssertionError('mutation escaped identity validator: '+name)
    bpy.ops.wm.open_mainfile(filepath=str(args.blend),load_ui=False,use_scripts=False)
    result=bridge.validate_scene(bpy,doc,files)
    assert sidecars.rebuild(files,result,p.serialize_mesh(result),p.serialize_policy(result))==files
    report=dict(blender_version=list(bpy.app.version),build_hash=bpy.app.build_hash.decode(),
                negative_controls=results,controls=len(results),restored_identity=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print('BUILD11_MUTATIONS_OK '+str(len(results)))


if __name__=='__main__':main()
