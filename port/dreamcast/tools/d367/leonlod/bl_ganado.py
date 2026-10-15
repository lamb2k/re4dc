"""leonlod GANADO_LOD look renders (Blender 5.2 headless, EEVEE): PS2 cast Ganado render meshes (mesh.json, bind pose,
millimetres, GC axes: +Y up, +Z forward) textured with the appearance atlas, unlit (the in-game cast shading model:
texture x constant colour), culling off; plus a wire view (the textured mesh under its triangle edges).

blender -b --factory-startup --python bl_ganado.py -- <job.json>
job.json: {"models": [{"label", "mesh", "atlas"}], "views": [{"name", "region": "body"|"head", "size": [w, h]}],
           "modes": ["flat", "wire"], "out": dir}
Writes <out>/<mode>-<view>-<label>.png. Every model of a view uses the same camera (framed on the first model).
"""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

job = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
out = Path(job['out']); out.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        pass
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'None'
scene.render.image_settings.file_format = 'PNG'
world = bpy.data.worlds.new('w'); scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.82, 0.82, 0.80, 1)


def to_b(p):
    return Vector((p[0] / 1000.0, -p[2] / 1000.0, p[1] / 1000.0))


def build(model):
    m = json.loads(Path(model['mesh']).read_text())
    P = [to_b(p) for p in m['positions_mm']]
    faces, uvs = [], []
    for t in m['triangles']:
        faces.append([c['vertex'] for c in t['corners']])
        uvs.append([c['uv'] for c in t['corners']])
    me = bpy.data.meshes.new(model['label'])
    me.from_pydata(P, [], faces)
    uvl = me.uv_layers.new(name='uv')
    k = 0
    for poly, tuv in zip(me.polygons, uvs):
        for li, uv in zip(poly.loop_indices, tuv):
            uvl.data[li].uv = (uv[0], 1.0 - uv[1])
    me.update()
    ob = bpy.data.objects.new(model['label'], me)
    scene.collection.objects.link(ob)
    mat = bpy.data.materials.new(model['label'] + '-m'); mat.use_nodes = True
    nt = mat.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(model['atlas']); tx.interpolation = 'Linear'
    nt.links.new(tx.outputs['Color'], e.inputs['Color']); nt.links.new(e.outputs['Emission'], o.inputs['Surface'])
    mat.use_backface_culling = False
    me.materials.append(mat)
    # the wire overlay: a copy with a Wireframe modifier and a dark unlit material
    wo = bpy.data.objects.new(model['label'] + '-w', me.copy())
    scene.collection.objects.link(wo)
    wm = wo.modifiers.new('wf', 'WIREFRAME'); wm.thickness = 0.0035; wm.use_replace = True
    wmat = bpy.data.materials.new('wire'); wmat.use_nodes = True
    wn = wmat.node_tree; wn.nodes.clear()
    o2 = wn.nodes.new('ShaderNodeOutputMaterial'); e2 = wn.nodes.new('ShaderNodeEmission')
    e2.inputs['Color'].default_value = (0.05, 0.05, 0.08, 1)
    wn.links.new(e2.outputs['Emission'], o2.inputs['Surface'])
    wo.data.materials.clear(); wo.data.materials.append(wmat)
    return ob, wo, P


objs = [build(m) for m in job['models']]
P0 = objs[0][2]
zs = [p.z for p in P0]; zmin, zmax = min(zs), max(zs)
xs = [p.x for p in P0]; cx = (min(xs) + max(xs)) / 2
cam_d = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cam_d); scene.collection.objects.link(cam)
scene.camera = cam
cam_d.type = 'ORTHO'
for v in job['views']:
    w, h = v['size']
    scene.render.resolution_x, scene.render.resolution_y = w, h
    if v['region'] == 'head':
        top = zmax; z0 = zmax - 0.36
    else:
        top = zmax + 0.03; z0 = zmin - 0.03
    span = top - z0
    cam_d.ortho_scale = span * max(1.0, w / h)
    cam.location = Vector((cx, -5.0, (top + z0) / 2))
    cam.rotation_euler = (math.radians(90), 0, 0)
    for mode in job['modes']:
        for i, (ob, wo, _) in enumerate(objs):
            for j, (o2, w2, _) in enumerate(objs):
                o2.hide_render = j != i
                w2.hide_render = j != i or mode != 'wire'
            scene.render.filepath = str(out / ('%s-%s-%s.png' % (mode, v['name'], job['models'][i]['label'])))
            bpy.ops.render.render(write_still=True)
print('RENDERS_DONE')
