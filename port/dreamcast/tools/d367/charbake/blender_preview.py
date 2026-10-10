"""charbake Blender preview (headless): render a character mesh with one or more atlas images, unlit (Workbench, flat
lighting, texture colour): the Dreamcast draws these characters with constant white vertex colour times the texture,
so a flat textured render is the in-game shading model without the PVR filtering.

blender -b --factory-startup --python blender_preview.py -- <job.json>
job.json: {"mesh": <mesh json>, "infos": [...], "images": {"<label>": <png>}, "out": <dir>, "size": [w, h],
           "views": [[name, yaw degrees, pitch degrees, distance m, target height m], ...], "lens": 50}
Writes <out>/<label>-<view>.png.
"""
import json
import math
import sys

import bpy


def main():
    job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    m = json.load(open(job['mesh']))
    P = m['positions_mm']
    infos = set(job['infos'])
    tris = [t for t in m['triangles'] if t['source_info'] in infos]
    used = sorted({c['vertex'] for t in tris for c in t['corners']})
    remap = {v: i for i, v in enumerate(used)}
    me = bpy.data.meshes.new('char')
    me.from_pydata([(P[v][0] * 0.001, -P[v][2] * 0.001, P[v][1] * 0.001) for v in used], [],
                   [[remap[c['vertex']] for c in t['corners']] for t in tris])
    uv = me.uv_layers.new(name='atlas')
    for poly, t in zip(me.polygons, tris):
        for li, c in zip(poly.loop_indices, t['corners']):
            uv.data[li].uv = (c['uv'][0], 1.0 - c['uv'][1])
    ob = bpy.data.objects.new('char', me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new('atlas')
    nt = mat.node_tree
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.interpolation = 'Linear'
    emit = nt.nodes.new('ShaderNodeEmission')
    out = nt.nodes.get('Material Output') or nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tex.outputs['Color'], emit.inputs['Color'])
    nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])
    me.materials.append(mat)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.color_type = 'TEXTURE'
    scene.display.shading.show_backface_culling = False
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x, scene.render.resolution_y = job.get('size', [512, 768])
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('w')
    scene.world = world
    world.color = (0.18, 0.18, 0.2)
    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = job.get('lens', 50)
    cam = bpy.data.objects.new('cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for label, png in job['images'].items():
        img = bpy.data.images.load(png)
        img.colorspace_settings.name = 'sRGB'
        tex.image = img
        for name, yaw, pitch, dist, th in job['views']:
            y, p = math.radians(yaw), math.radians(pitch)
            # yaw 0 = in front of the character (source +z is Leon's front: Blender -y)
            cx = dist * math.sin(y) * math.cos(p)
            cy = -dist * math.cos(y) * math.cos(p)
            cz = th + dist * math.sin(p)
            cam.location = (cx, cy, cz)
            d = (0 - cx, 0 - cy, th - cz)
            # aim the camera at (0, 0, th)
            import mathutils
            cam.rotation_euler = mathutils.Vector(d).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = '%s/%s-%s.png' % (job['out'], label, name)
            bpy.ops.render.render(write_still=True)


main()
