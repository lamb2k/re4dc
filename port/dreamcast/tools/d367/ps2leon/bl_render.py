"""ps2leon comparison renders (Blender 5.2 headless, EEVEE): Leon render meshes (mesh.json) posed in the captured game
pose (leon-source bones: capture x rest^-1, the root's room placement removed), textured with today's atlas and hair
pair images, three shadings:
  flat  the in-game shading model: texture x constant white, unlit (coarse owner path: SourceLighting off, MODULATE),
        hair alpha-blended (pair images: colour + the I4 mask), culling off (b.cull=0);
  clay  untextured grey under a key / fill / rim light (shape, silhouette and faceting the unlit draw hides);
  wire  clay + the triangle edges (where the triangles went; edge thickness per view).

blender -b --factory-startup --python bl_render.py -- <job.json>
job.json: {"models": [{"label", "mesh"}], "atlas": png, "hair": {"1": png, "2": png}, "tiles": asset-report tiles,
           "modes": [...], "views": [{"name", "cam": [right, back, up] (m, Leon frame), "aim": "head"|"body"|[x,y,z],
           "lens", "size": [w, h]}], "out": dir}
Leon frame: origin at the root on the ground, Leon faces -back; 'right' is Leon's right-hand side.
Writes <out>/<mode>-<view>-<label>.png.
"""
import json, math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector

job = json.loads(Path(sys.argv[sys.argv.index('--') + 1]).read_text())
out = Path(job['out']); out.mkdir(parents=True, exist_ok=True)
tiles = {k.replace('SourceTex_', ''): t for k, t in job['tiles'].items()}
HAIR_TILE = {'ac381b1a-3ade84b1': 1, '7a9de1fd-0e415f15': 2}
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
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
world = bpy.data.worlds.new('w'); scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes['Background']


def src_uv_from_atlas(u, v):
    x, y = u * 512, (1 - v) * 512
    for k, t in tiles.items():
        if t['x'] <= x < t['x'] + t['width'] and t['y'] <= y < t['y'] + t['height']:
            return ((x - t['x'] - 2) / t['inner_width'], 1 - (y - t['y'] - 2) / t['inner_height']), k
    raise ValueError((u, v))


def image(path):
    im = bpy.data.images.load(path, check_existing=True); im.colorspace_settings.name = 'sRGB'
    return im


def make_material(name, img, uvname, mode, alpha):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = uvname
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Linear'; tex.extension = 'REPEAT' if alpha else 'EXTEND'
    nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
    if mode == 'flat':
        sh = nt.nodes.new('ShaderNodeEmission'); nt.links.new(tex.outputs['Color'], sh.inputs['Color']); sh.inputs['Strength'].default_value = 1.0
    else:
        sh = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(tex.outputs['Color'], sh.inputs['Base Color'])
        sh.inputs['Roughness'].default_value = 0.85
        for k in ('Specular IOR Level', 'Specular'):
            if k in sh.inputs:
                sh.inputs[k].default_value = 0.0
    if alpha:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(tex.outputs['Alpha'], mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(sh.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], o.inputs['Surface'])
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            m.blend_method = 'BLEND'
    else:
        nt.links.new(sh.outputs[0], o.inputs['Surface'])
    m.use_backface_culling = False
    return m


def build(model, skip=()):
    mj = json.loads(Path(model['mesh']).read_text())
    P = np.asarray(mj['positions_mm'], float)
    rest = np.asarray([b['rest'] for b in mj['bones']], float); cap = np.asarray([b['capture'] for b in mj['bones']], float)
    root = rest[0] @ np.linalg.inv(cap[0])
    skin = np.einsum('ij,bjk,bkl->bil', root, cap, np.linalg.inv(rest))
    bone_world = np.einsum('ij,bjk->bik', root, cap)[:, :3, 3]
    nv = len(P)
    M = np.zeros((nv, 4, 4))
    for i, w in enumerate(mj['weights']):
        for b, x in w:
            M[i] += x * skin[b]
    PP = np.einsum('vij,vj->vi', M, np.c_[P, np.ones(nv)])[:, :3]
    to_bl = lambda a: np.c_[a[:, 0], -a[:, 2], a[:, 1]] * 0.001
    V = to_bl(PP)
    verts = [tuple(v) for v in V]
    faces, fmat, fuv, fsrc, fn = [], [], [], [], []
    seen = set()
    for t in mj['triangles']:
        if t['source_info'] in skip:
            continue
        ids = [c['vertex'] for c in t['corners']]
        key = frozenset(ids)
        if key in seen or len(key) < 3:
            # coincident copy (e.g. a double-sided or two-material hair card): its own vertices, drawn as well
            base = len(verts)
            for vi in ids:
                verts.append(tuple(V[vi]))
            ids2 = list(range(base, base + 3))
        else:
            ids2 = ids
        seen.add(frozenset(ids2))
        role = t['source_info']
        mat = 0
        su = [(0.0, 0.0)] * 3
        if role == 7:
            if 'material' in t:
                mat = t['material']; su = [tuple(c['src_uv']) for c in t['corners']]
            else:
                r = [src_uv_from_atlas(*c['uv']) for c in t['corners']]
                mat = HAIR_TILE[r[0][1]]; su = [x for x, _ in r]
        faces.append(ids2); fmat.append(mat)
        fuv.append([tuple(c['uv']) for c in t['corners']]); fsrc.append(su)
        nrm = []
        for c, vi in zip(t['corners'], ids):
            n = M[vi][:3, :3] @ np.asarray(c['normal'])
            n = n / max(np.linalg.norm(n), 1e-9)
            nrm.append((n[0], -n[2], n[1]))
        fn.append(nrm)
    me = bpy.data.meshes.new(model['label'] + ('-skip' if skip else ''))
    me.from_pydata(verts, [], faces); me.update(calc_edges=True)
    ua = me.uv_layers.new(name='atlas'); uh = me.uv_layers.new(name='hair')
    loops_n = []
    for p, uvs, sus, mat, nrm in zip(me.polygons, fuv, fsrc, fmat, fn):
        p.material_index = mat; p.use_smooth = True
        for li, uv, su, n in zip(p.loop_indices, uvs, sus, nrm):
            ua.data[li].uv = (uv[0], 1 - uv[1]); uh.data[li].uv = (su[0], 1 - su[1])
    for p, nrm in zip(me.polygons, fn):
        loops_n.extend(nrm)
    try:
        me.normals_split_custom_set(loops_n)
    except Exception as e:
        print('normals', e)
    ob = bpy.data.objects.new(me.name, me); scene.collection.objects.link(ob)
    bw = to_bl(bone_world)
    return ob, dict(head=Vector(bw[4]), body=Vector((float(bw[0][0]), float(bw[0][1]), 0.92)), right=float(np.sign(bone_world[10][0]) or 1.0))


CLAY = None


def clay():
    global CLAY
    if CLAY is None:
        m = bpy.data.materials.new('clay'); m.use_nodes = True
        bs = m.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Base Color'].default_value = (0.42, 0.42, 0.40, 1); bs.inputs['Roughness'].default_value = 0.75
        m.use_backface_culling = False
        CLAY = m
    return CLAY


def set_materials(ob, mode):
    me = ob.data; me.materials.clear()
    if mode == 'flat':
        me.materials.append(make_material('atlas-' + mode, image(job['atlas']), 'atlas', mode, False))
        me.materials.append(make_material('hair1-' + mode, image(job['hair']['1']), 'hair', mode, True))
        me.materials.append(make_material('hair2-' + mode, image(job['hair']['2']), 'hair', mode, True))
    else:
        for _ in range(3):
            me.materials.append(clay())


def wire_overlay(ob, thickness):
    w = ob.copy(); w.data = ob.data.copy(); w.name = ob.name + '-wire'; scene.collection.objects.link(w)
    mod = w.modifiers.new('wire', 'WIREFRAME'); mod.thickness = thickness; mod.use_replace = True; mod.use_even_offset = False
    m = bpy.data.materials.get('wire')
    if m is None:
        m = bpy.data.materials.new('wire'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (0.03, 0.03, 0.035, 1)
        nt.links.new(e.outputs[0], o.inputs['Surface'])
    w.data.materials.clear(); w.data.materials.append(m)
    for p in w.data.polygons:
        p.material_index = 0
    return w


cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data); scene.collection.objects.link(cam); scene.camera = cam
lights = []
for name, pos, energy in (('key', (2.5, -3.5, 4.5), 2.4), ('fill', (-3.0, -1.0, 2.0), 0.5), ('rim', (0.5, 4.0, 3.0), 0.9)):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = energy
    try:
        ld.use_shadow = False
    except Exception:
        pass
    lo = bpy.data.objects.new(name, ld); scene.collection.objects.link(lo); lo.location = pos
    lo.rotation_euler = (Vector((0, 0, 1)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    lights.append(lo)

built = []
for model in job['models']:
    ob, anchors = build(model)
    ob2, _ = build(model, skip={2})     # close-ups without role 2, the knife (pl00 0x00d on the hand bone 10) held across the face here
    ob.hide_render = ob2.hide_render = True
    built.append((model, ob, ob2, anchors))
for model, full, nohand, anchors in built:
    for mode in job['modes']:
        for o in (full, nohand):
            set_materials(o, mode)
        for lo in lights:
            lo.hide_render = mode == 'flat'
        bg.inputs[0].default_value = (0.16, 0.17, 0.19, 1) if mode == 'flat' else (0.36, 0.37, 0.40, 1)
        bg.inputs[1].default_value = 1.0
        for v in job['views']:
            ob = nohand if 2 in v.get('hide_roles', []) else full
            ob.hide_render = False
            wire = wire_overlay(ob, v.get('wire', 0.002)) if mode == 'wire' else None
            r = anchors['right']
            right, back, up = v['cam']
            loc = Vector((right * r, back, up))            # Leon frame -> Blender (Leon faces -y, up +z)
            aim = v.get('aim', 'body')
            if isinstance(aim, str):
                tgt = anchors[aim].copy()
            else:
                tgt = Vector((aim[0] * r, aim[1], aim[2]))
            off = Vector(v.get('aim_offset', (0, 0, 0)))
            off.x *= r
            tgt = tgt + off
            cam.location = tgt + loc if v.get('relative', True) else loc
            cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam_data.lens = v.get('lens', 50)
            scene.render.resolution_x, scene.render.resolution_y = v['size']
            scene.render.resolution_percentage = 100
            scene.render.filepath = str(out / ('%s-%s-%s.png' % (mode, v['name'], model['label'])))
            bpy.ops.render.render(write_still=True)
            if wire:
                bpy.data.objects.remove(wire, do_unlink=True)
            ob.hide_render = True
print('RENDERS_DONE', flush=True)
