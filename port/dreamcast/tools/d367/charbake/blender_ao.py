"""charbake Blender step (headless): bake ambient occlusion for an approved render mesh in its bind pose.

blender -b --factory-startup --python blender_ao.py -- <job.json>

job.json: {"mesh": <mesh json>, "out": <dir>, "bake_infos": [0..6], "occluder_infos": [7], "res": 2048,
           "samples": 256, "distances": [0.08, 0.3], "threads": 6, "margin": 16}
Mesh JSON schema re4dc-approved-render-mesh-1 (positions_mm; triangles with corners {vertex, normal, uv}; source_info),
or a cast mesh converted to that schema by cb_cast.py. Source millimetres -> Blender metres: (x, y, z) -> (x, -z, y).

Writes into <out>: ao_<distance mm>.npy per distance (float32 [res, res], rows bottom to top, on the "unique" map
made of each corner's "cell" UV, laid out by the driver) and blender.json (versions, settings, timings).
The job is deterministic for one Blender build (fixed seed, CPU, fixed thread count); the driver caches the outputs
by input hash and treats them as inputs afterwards.
"""
import json
import sys
import time

import bpy


def main():
    job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
    out = job['out']
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    m = json.load(open(job['mesh']))
    P = m['positions_mm']
    verts = [(x * 0.001, -z * 0.001, y * 0.001) for x, y, z in P]
    bake_set = set(job['bake_infos'])
    occ_set = set(job.get('occluder_infos', []))
    bake_tris = [t for t in m['triangles'] if t['source_info'] in bake_set]
    occ_tris = [t for t in m['triangles'] if t['source_info'] in occ_set]

    def make(name, tris, with_uv):
        me = bpy.data.meshes.new(name)
        used = sorted({c['vertex'] for t in tris for c in t['corners']})
        remap = {v: i for i, v in enumerate(used)}
        me.from_pydata([verts[v] for v in used], [], [[remap[c['vertex']] for c in t['corners']] for t in tris])
        me.validate(clean_customdata=False)
        if len(me.polygons) != len(tris):
            raise SystemExit('%s: %d polygons for %d triangles (validate removed some)' % (name, len(me.polygons), len(tris)))
        if with_uv:
            uv = me.uv_layers.new(name='atlas')
            for poly, t in zip(me.polygons, tris):
                for li, c in zip(poly.loop_indices, t['corners']):
                    uv.data[li].uv = (c['uv'][0], 1.0 - c['uv'][1])
        normals = []
        for poly, t in zip(me.polygons, tris):
            for c in t['corners']:
                nx, ny, nz = c['normal']
                normals.append((nx, -nz, ny))
        me.normals_split_custom_set(normals)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    body = make('bake', bake_tris, True)
    occ = make('occluder', occ_tris, False) if occ_tris else None

    # The unique map: every baked triangle owns its texels. The driver lays the triangles out (corner "cell", one
    # grid cell per triangle, deterministic); Blender only bakes.
    uvu = body.data.uv_layers.new(name='unique')
    for poly, t in zip(body.data.polygons, bake_tris):
        for li, c in zip(poly.loop_indices, t['corners']):
            uvu.data[li].uv = (c['cell'][0], c['cell'][1])
    body.data.uv_layers.active = uvu
    uvu.active_render = True

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = int(job.get('samples', 256))
    scene.cycles.seed = 0
    scene.cycles.use_animated_seed = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = int(job.get('threads', 6))
    scene.render.bake.margin = int(job.get('margin', 16))
    scene.render.bake.margin_type = 'EXTEND'
    world = bpy.data.worlds.new('charbake')
    scene.world = world
    res = int(job.get('res', 2048))
    mat = bpy.data.materials.new('charbake')
    nodes = mat.node_tree.nodes
    body.data.materials.append(mat)
    timings = {}
    for dist in job['distances']:
        world.light_settings.distance = float(dist)
        name = 'ao_%03d' % round(dist * 1000)
        img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=True)
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = img
        nodes.active = tex
        for ob in bpy.context.scene.objects:
            ob.select_set(ob == body)
        bpy.context.view_layer.objects.active = body
        t1 = time.time()
        bpy.ops.object.bake(type='AO', use_clear=True, margin=int(job.get('margin', 16)), target='IMAGE_TEXTURES')
        timings[name] = round(time.time() - t1, 1)
        # Raw float pixels (Blender order: rows bottom to top, RGBA); channel 0 is the occlusion.
        import numpy as np
        px = np.empty(res * res * 4, np.float32)
        img.pixels.foreach_get(px)
        np.save('%s/%s.npy' % (out, name), px.reshape(res, res, 4)[:, :, 0].copy())
        nodes.remove(tex)
    json.dump(dict(blender=bpy.app.version_string, build_hash=bpy.app.build_hash.decode() if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
                   job=job, baked_triangles=len(bake_tris), occluder_triangles=len(occ_tris), timings=timings,
                   seconds=round(time.time() - t0, 1)), open(out + '/blender.json', 'w'), indent=1)


main()
