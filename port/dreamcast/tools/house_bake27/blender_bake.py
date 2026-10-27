"""Run only inside a separate offline Blender factory session; private data only."""
import bpy
import hashlib
import json
import math
from pathlib import Path
import sys
from mathutils import Vector

out=Path(sys.argv[sys.argv.index('--')+1]);exchange=json.loads((out/'HOUSE-EXCHANGE.json').read_text())
assert not bpy.app.online_access and not (out/'house-bake.blend').exists()
for addon in list(bpy.context.preferences.addons.keys()):
    bpy.ops.preferences.addon_disable(module=addon)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.render.image_settings.file_format='PNG';scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
scene.world.color=(.03,.03,.03);scene.render.film_transparent=False
collections={}
for name in ('REFERENCE_LOCKED','CANDIDATE_CONSERVATIVE','CANDIDATE_LEAN','REVIEW_CAMERAS'):
    col=bpy.data.collections.new(name);scene.collection.children.link(col);collections[name]=col

def coords(p):return (p[0]/1000,-p[2]/1000,p[1]/1000)
def material(role):
    image=bpy.data.images.load(str(out/(role+'-ps2-source.png')),check_existing=True);image.colorspace_settings.name='sRGB'
    m=bpy.data.materials.new(role+'_PS2_ALBEDO_TIMES_PS2_PRELIGHT');m.use_nodes=True;n=m.node_tree.nodes;n.clear();links=m.node_tree.links
    tex=n.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT';tex.interpolation='Linear'
    uv=n.new('ShaderNodeUVMap');uv.uv_map='SOURCE_UV';links.new(uv.outputs['UV'],tex.inputs['Vector'])
    col=n.new('ShaderNodeVertexColor');col.layer_name='PS2_PRELIGHT'
    multiply=n.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
    links.new(tex.outputs['Color'],multiply.inputs[1]);links.new(col.outputs['Color'],multiply.inputs[2])
    emit=n.new('ShaderNodeEmission');links.new(multiply.outputs['Color'],emit.inputs['Color']);emit.inputs['Strength'].default_value=1
    output=n.new('ShaderNodeOutputMaterial');links.new(emit.outputs[0],output.inputs['Surface']);return m

def mesh(role,kind,collection,mat):
    ts=exchange[role][kind];vs=[];faces=[]
    for t in ts:
        base=len(vs);vs.extend(coords(p) for p in t['world_mm']);faces.append((base,base+1,base+2))
    me=bpy.data.meshes.new(role+'_'+kind);me.from_pydata(vs,[],faces);me.update();obj=bpy.data.objects.new(role+'_'+kind,me);collection.objects.link(obj);me.materials.append(mat)
    uv=me.uv_layers.new(name='SOURCE_UV');col=me.color_attributes.new(name='PS2_PRELIGHT',type='FLOAT_COLOR',domain='CORNER')
    for poly,t in zip(me.polygons,ts):
        for loop,st,sc in zip(poly.loop_indices,t['uv'],t['prelight_rgba']):uv.data[loop].uv=(st[0],1-st[1]);col.data[loop].color=sc
    obj['source_part']=exchange[role]['part'];obj['source_mesh']=exchange[role]['mesh'];obj['source_material_key']=exchange[role]['source_material_key'];return obj

objects={};bake_receipt={'blender_version':bpy.app.version_string,'offline':not bpy.app.online_access,'bake_type':'EMIT selected-to-active','new_lighting':False,'maps':[],'reference_triangles':407,'target_triangles':107,'appearance_accepted':False,'timing_available':False}
for role in ('wall','roof'):
    mat=material(role)
    src=mesh(role,'source',collections['REFERENCE_LOCKED'],mat)
    plain=mesh(role,'target',collections['CANDIDATE_CONSERVATIVE'],mat)
    target=mesh(role,'target',collections['CANDIDATE_LEAN'],mat.copy());target.name=role+'_BAKED_TARGET'
    bpy.ops.object.select_all(action='DESELECT');target.select_set(True);bpy.context.view_layer.objects.active=target
    target.data.uv_layers.new(name='BAKE_UV');target.data.uv_layers.active_index=1
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.04,area_weight=1,correct_aspect=True,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
    target.data.uv_layers['BAKE_UV'].active_render=True
    image=bpy.data.images.new(role+'_BAKED_PS2_STATIC_DETAIL',width=512,height=512,alpha=False,float_buffer=False)
    image.generated_color=(.01,.01,.01,1);image.colorspace_settings.name='sRGB'
    n=target.active_material.node_tree.nodes;node=n.new('ShaderNodeTexImage');node.image=image;n.active=node
    src.hide_render=False;target.hide_render=False;plain.hide_render=True
    for other in objects.values():
        for obj in other:obj.hide_render=True
    bpy.ops.object.select_all(action='DESELECT');src.select_set(True);target.select_set(True);bpy.context.view_layer.objects.active=target
    scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.25;scene.render.bake.max_ray_distance=1.;scene.render.bake.margin=8
    bpy.ops.object.bake(type='EMIT')
    image.filepath_raw=str(out/(role+'-baked.png'));image.file_format='PNG';image.save()
    # Candidate display samples only the baked result; prelight is already in it.
    nodes=target.active_material.node_tree.nodes;nodes.clear();links=target.active_material.node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='EXTEND';tex.interpolation='Linear'
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='BAKE_UV';links.new(uv.outputs['UV'],tex.inputs['Vector'])
    emit=nodes.new('ShaderNodeEmission');links.new(tex.outputs['Color'],emit.inputs['Color']);output=nodes.new('ShaderNodeOutputMaterial');links.new(emit.outputs[0],output.inputs['Surface'])
    uvs=[[[float(v) for v in target.data.uv_layers['BAKE_UV'].data[i].uv] for i in p.loop_indices] for p in target.data.polygons]
    bake_receipt['maps'].append(dict(role=role,width=512,height=512,uv_layer='BAKE_UV',target_triangles=len(target.data.polygons),geometry_unchanged=True,atlas_uv_per_triangle=uvs))
    objects[role]=(src,plain,target)

# Validate that bake only adds UV/image data. Positions, triangle order, holes,
# winding and source component mapping stay exactly the reviewed C9 exchange.
for role,triple in objects.items():
    target=triple[2]
    for poly,t in zip(target.data.polygons,exchange[role]['target']):
        actual=[target.data.vertices[target.data.loops[i].vertex_index].co for i in poly.loop_indices]
        for p,expected in zip(actual,t['world_mm']):assert (p-Vector(coords(expected))).length<1e-5

cam_data=bpy.data.cameras.new('REVIEW_CAMERA');cam=bpy.data.objects.new('REVIEW_CAMERA',cam_data);collections['REVIEW_CAMERAS'].objects.link(cam);scene.camera=cam;cam_data.lens=44;cam_data.clip_end=200
allpoints=[Vector(coords(p)) for role in ('wall','roof') for t in exchange[role]['source'] for p in t['world_mm']]
center=(Vector(tuple(min(p[i] for p in allpoints) for i in range(3)))+Vector(tuple(max(p[i] for p in allpoints) for i in range(3))))*.5
radius=max((p-center).length for p in allpoints)*2.7
for frame in range(12):
    angle=math.radians(30+frame*30);eye=center+Vector((radius*math.cos(angle),radius*math.sin(angle),radius*.32))
    cam.location=eye;cam.rotation_euler=(center-eye).to_track_quat('-Z','Y').to_euler()
    for index,label in enumerate(('A_PS2_SOURCE','PLAIN_C9','BAKED_C9')):
        for triple in objects.values():
            for i,obj in enumerate(triple):obj.hide_render=i!=index
        scene.render.filepath=str(out/(label+'-%02d.png'%frame));bpy.ops.render.render(write_still=True)
for triple in objects.values():
    for i,obj in enumerate(triple):obj.hide_render=i!=2
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'house-bake.blend'),check_existing=False)
(out/'BLENDER-BAKE-RECEIPT.json').write_text(json.dumps(bake_receipt,indent=2)+'\n')
print('HOUSE_BAKE_COMPLETE',out)
