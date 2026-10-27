"""Render actual independently decoded native VQ textures on saved C9 geometry."""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1]);assert not bpy.app.online_access
bpy.ops.preferences.addon_enable(module='cycles');bpy.ops.wm.open_mainfile(filepath=str(root/'house-bake.blend'))
scene=bpy.context.scene;scene.render.threads_mode='FIXED';scene.render.threads=4
exchange=json.loads((root/'HOUSE-EXCHANGE.json').read_text())
native=json.loads((root/'NATIVE-CORE-EXCHANGE.json').read_text()) if (root/'NATIVE-CORE-EXCHANGE.json').exists() else None
atlas=json.loads((root/'ATLAS-EXCHANGE.json').read_text())
for role in ('wall','roof'):
    obj=bpy.data.objects[role+'_BAKED_TARGET'];image=bpy.data.images.load(str(root/(role+'-native-decoded.png')));image.colorspace_settings.name='Non-Color'
    if native:
        # Recreate from actual final R4IM strips, not the producer's float UVs.
        vertices=[];faces=[]
        for t in native[role]:
            start=len(vertices);vertices.extend((p[0]/1000,-p[2]/1000,p[1]/1000) for p in t['world_mm']);faces.append((start,start+1,start+2))
        me=bpy.data.meshes.new(role+'_ACTUAL_NATIVE_CORE');me.from_pydata(vertices,[],faces);me.update();uv=me.uv_layers.new(name='BAKE_UV')
        for p,t in zip(me.polygons,native[role]):
            assert all(v==65535 for v in t['prelight_word'])
            for loop,(u,v) in zip(p.loop_indices,t['uv_top_left']):uv.data[loop].uv=(u,1-v)
        me.materials.append(obj.active_material);obj.data=me
    else:
        basis=atlas[role]['source_uv_origin_step']
        for p,t in zip(obj.data.polygons,atlas[role]['target_triangles']):
            for loop,c in zip(p.loop_indices,t['baked_corners_existing_part_basis']):obj.data.uv_layers['BAKE_UV'].data[loop].uv=(basis[0]+c[3]*basis[2],1-(basis[1]+c[4]*basis[3]))
    for node in obj.active_material.node_tree.nodes:
        if node.type=='TEX_IMAGE':node.image=image
points=[Vector((p[0]/1000,-p[2]/1000,p[1]/1000)) for role in ('wall','roof') for t in exchange[role]['source'] for p in t['world_mm']]
center=(Vector(tuple(min(p[i] for p in points) for i in range(3)))+Vector(tuple(max(p[i] for p in points) for i in range(3))))*.5
radius=max((p-center).length for p in points)*2.7;camera=scene.camera
for frame in range(12):
    angle=math.radians(30+frame*30);eye=center+Vector((radius*math.cos(angle),radius*math.sin(angle),radius*.32));camera.location=eye;camera.rotation_euler=(center-eye).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(root/('VQ_BAKED_C9-%02d.png'%frame));bpy.ops.render.render(write_still=True)
for image in bpy.data.images:
    if image.source=='FILE':image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(root/'house-bake-vq.blend'),check_existing=False)
(root/'ENCODED-RENDER-RECEIPT.json').write_text(json.dumps(dict(actual_native_geometry_and_uv=native is not None,candidate_sha256=native['candidate_sha256'] if native else None,native_exchange_sha256=hashlib.sha256((root/'NATIVE-CORE-EXCHANGE.json').read_bytes()).hexdigest() if native else None,producer_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),decoded_vq_maps=True,uv_runtime_top_left_to_blender_v='1-v',frames=12,appearance_accepted=False,timing_available=False),indent=2)+'\n')
