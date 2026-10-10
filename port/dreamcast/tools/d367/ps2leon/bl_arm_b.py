"""ps2leon arm B (PS2_LEON=2), Blender 5.2 headless: the PS2 Leon's triangle budget (5,167) redistributed, every part
reduced from the GameCube sections (the cl lane's reduction pipeline: character-prototype build_blender.py reduce_obj
steps and rebuild_leon_hair.py's border protection, in leon-4k-comparison.blend's Leon_REFERENCE_LOCKED meshes).

blender -b --factory-startup --python bl_arm_b.py -- <comparison.blend> <job.json> <out dir>
job.json: {"targets": {role: {region: triangles}}, "regions": [region of bone 0..118], "tiles": asset-report tiles,
           "hair_materials": {key: runtime material}}
Writes <out>/mesh.json (re4dc-approved-render-mesh-1 + per-corner src_uv / per-triangle material for role 7),
<out>/report-b.json and <out>/leon-b.blend.

Per role: (1) drop repeated identical submissions (reduce_obj); role 7 also drops a same-material copy over the same
three corners with the same UVs and the opposite winding (the GC's double-sided card copy: the owner path draws Leon
with culling off, b.cull=0, so the copy only blends the same texels twice; the GC, culling, shows one of them);
(2) weld equal-position-and-weight vertices except in the hair (rebuild_leon_hair.py: welding overlapping locks
broke the nape); (3) give each face the region with the largest summed bone weight over its corners (head / torso /
arms / legs, leon_sources.bone_regions); (4) reduce each region piece to its target with Blender's collapse decimation,
the vertices shared with another region's faces held (vertex group weight 0, factor 1000, as the hair revision held
the leg border), so the pieces meet exactly; (5) join, limit to 3 influences, normalize; (6) map the source UVs into
today's 512 atlas tiles (build_leon_4k.py), keep the source UV for the hair runs.
"""
import json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
blend, job_path, out = args[0], args[1], Path(args[2])
out.mkdir(parents=True, exist_ok=True)
job = json.loads(Path(job_path).read_text())
REGIONS = ['head', 'torso', 'arms', 'legs']
bone_region = job['regions']
tiles = {k.replace('SourceTex_', ''): t for k, t in job['tiles'].items()}
hair_mat = job['hair_materials']
bpy.ops.wm.open_mainfile(filepath=blend)
assert not bpy.app.online_access
scene = bpy.data.scenes['Leon_4k_and_Ganado_874']
bpy.context.window.scene = scene
refcol = bpy.data.collections['Leon_REFERENCE_LOCKED']
refs = sorted([o for o in refcol.objects if o.type == 'MESH'], key=lambda o: o['source_info_index'])
oldrig = next(o for o in refcol.objects if o.type == 'ARMATURE')
col = bpy.data.collections.new('Leon_B_PS2BUDGET'); scene.collection.children.link(col)
rig = oldrig.copy(); rig.data = oldrig.data.copy(); rig.name = 'Leon_B_Rig'; col.objects.link(rig)
rig.animation_data_clear(); rig.location = (0, 0, 0)
for p in rig.pose.bones:
    p.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()


def ntris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def clone(o, name):
    n = o.copy(); n.data = o.data.copy(); n.name = name; col.objects.link(n)
    n.parent = rig
    for m in n.modifiers:
        if m.type == 'ARMATURE':
            m.object = rig
    n.hide_render = False; n.hide_viewport = False
    return n


def clean(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bad = [f for f in bm.faces if f.calc_area() < 1e-12]
    if bad:
        bmesh.ops.delete(bm, geom=bad, context='FACES_ONLY')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(o.data); bm.free(); o.data.update(); o.data.validate()


def prepare(o, role):
    """repeated submissions, double-sided copies (hair), welds; returns counts."""
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    seen, dup = set(), []
    for f in bm.faces:
        corners = tuple((l.vert.index, tuple(round(x, 7) for x in l[uv].uv)) for l in f.loops)
        key = (f.material_index, min(corners[k:] + corners[:k] for k in range(len(corners))))
        if key in seen:
            dup.append(f)
        else:
            seen.add(key)
    bmesh.ops.delete(bm, geom=dup, context='FACES_ONLY')
    twin = []
    if role == 7:
        seen = {}
        for f in bm.faces:
            corners = tuple((tuple(round(x, 6) for x in l.vert.co), tuple(round(x, 7) for x in l[uv].uv)) for l in f.loops)
            fwd = min(corners[k:] + corners[:k] for k in range(3))
            rc = corners[::-1]
            rev = min(rc[k:] + rc[:k] for k in range(3))
            if (f.material_index, rev) in seen:
                twin.append(f)
            else:
                seen[(f.material_index, fwd)] = f
        bmesh.ops.delete(bm, geom=twin, context='FACES_ONLY')
    weld = {}
    if role != 7:
        deform = bm.verts.layers.deform.active
        unique = {}
        for v in bm.verts:
            w = tuple(sorted((k, round(x, 7)) for k, x in v[deform].items())) if deform else ()
            key = (tuple(round(x, 7) for x in v.co), w)
            if key in unique:
                weld[v] = unique[key]
            else:
                unique[key] = v
        if weld:
            bmesh.ops.weld_verts(bm, targetmap=weld)
    bm.to_mesh(o.data); bm.free(); o.data.update()
    clean(o)
    return dict(repeated=len(dup), double_sided_copies=len(twin), welded=len(weld))


def face_regions(o):
    names = {g.index: int(g.name[4:]) for g in o.vertex_groups}
    vreg = []
    for v in o.data.vertices:
        acc = {}
        for g in v.groups:
            if g.weight > 1e-7:
                r = bone_region[names[g.group]]
                acc[r] = acc.get(r, 0) + g.weight
        vreg.append(acc)
    out = []
    for p in o.data.polygons:
        acc = {}
        for vi in p.vertices:
            for r, w in vreg[vi].items():
                acc[r] = acc.get(r, 0) + w
        out.append(max(acc.items(), key=lambda kv: (kv[1], -REGIONS.index(kv[0])))[0])
    return out


def key3(co):
    return (round(co.x, 6), round(co.y, 6), round(co.z, 6))


def decimate(piece, target, held):
    """collapse-decimate a copy of piece to ~target triangles, held vertices weighted 0; returns the object."""
    start = ntris(piece)
    if target >= start:
        return piece, dict(start=start, target=target, result=start, ratio=1.0, tries=0, held_missing=0)
    ratio = target / start
    best = None
    for attempt in range(6):
        o = piece.copy(); o.data = piece.data.copy(); col.objects.link(o)
        g = o.vertex_groups.new(name='PS2LEON_Hold')
        for v in o.data.vertices:
            g.add([v.index], 0.0 if key3(v.co) in held else 1.0, 'REPLACE')
        select([o])
        dec = o.modifiers.new('ps2leon region budget', 'DECIMATE')
        dec.decimate_type = 'COLLAPSE'; dec.ratio = min(1.0, ratio); dec.use_collapse_triangulate = True
        if held:
            dec.vertex_group = g.name; dec.vertex_group_factor = 1000
        bpy.ops.object.modifier_move_up(modifier=dec.name)
        bpy.ops.object.modifier_apply(modifier=dec.name)
        o.vertex_groups.remove(o.vertex_groups['PS2LEON_Hold'])
        clean(o)
        got = ntris(o)
        err = abs(got - target)
        if best is None or err < best[1]:
            if best:
                bpy.data.objects.remove(best[0], do_unlink=True)
            best = (o, err, got, ratio, attempt + 1)
        else:
            bpy.data.objects.remove(o, do_unlink=True)
        if err <= max(1, target // 400):
            break
        ratio *= target / max(got, 1)
    o, err, got, ratio, tries = best
    have = {key3(v.co) for v in o.data.vertices}
    want = {key3(v.co) for v in piece.data.vertices} & held
    bpy.data.objects.remove(piece, do_unlink=True)
    return o, dict(start=start, target=target, result=got, ratio=ratio, tries=tries, held=len(want), held_missing=len(want - have))


def split(o, regs, region):
    p = o.copy(); p.data = o.data.copy(); col.objects.link(p)
    bm = bmesh.new(); bm.from_mesh(p.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f, r in zip(bm.faces, regs) if r != region], context='FACES_ONLY')
    bm.to_mesh(p.data); bm.free(); p.data.update(); clean(p)
    return p


report = dict(roles=[])
role_objs = []
for role, src in enumerate(refs):
    assert src['source_info_index'] == role
    o = clone(src, 'Leon_B_info_%02d' % role)
    raw = ntris(o)
    prep = prepare(o, role)
    regs = face_regions(o)
    counts = {r: regs.count(r) for r in REGIONS if r in regs}
    # vertices of faces in more than one region: held so the region pieces meet exactly
    vr = {}
    for p, r in zip(o.data.polygons, regs):
        for vi in p.vertices:
            vr.setdefault(key3(o.data.vertices[vi].co), set()).add(r)
    held = {k for k, s in vr.items() if len(s) > 1}
    targets = {r: int(t) for r, t in job['targets'][str(role)].items()}
    pieces, rows = [], {}
    for region in REGIONS:
        if region not in counts:
            continue
        t = targets.get(region, counts[region])
        piece = split(o, regs, region)
        piece, row = decimate(piece, t, held)
        piece.name = 'Leon_B_info_%02d_%s' % (role, region)
        pieces.append(piece); rows[region] = row
    bpy.data.objects.remove(o, do_unlink=True)
    select(pieces); bpy.ops.object.join()
    ro = bpy.context.object; ro.name = 'Leon_B_info_%02d' % role; ro.data.name = ro.name
    ro['source_info_index'] = role
    select([ro])
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=3)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    clean(ro)
    # atlas UVs (build_leon_4k.py tile map), the source UV layer kept for the hair runs
    me = ro.data
    srcuv = me.uv_layers['SourceUV']
    atlas = me.uv_layers.new(name='AtlasUV', do_init=True)
    for p in me.polygons:
        t = tiles[me.materials[p.material_index].name.replace('SourceTex_', '')]
        for li in p.loop_indices:
            u, v = srcuv.data[li].uv
            atlas.data[li].uv = ((t['x'] + 2 + u * t['inner_width']) / 512, (t['y'] + 2 + v * t['inner_height']) / 512)
    role_objs.append(ro)
    row = dict(role=role, source_triangles=raw, after_prepare=sum(counts.values()), prepare=prep, regions_before=counts,
               targets=targets, pieces=rows, triangles=ntris(ro), vertices=len(me.vertices))
    report['roles'].append(row)
    print('ROLE', json.dumps(row), flush=True)

# export (export_coarse_actor.py's mapping and checks, one object per role, global vertex ids)
to_source = Matrix(((1000, 0, 0), (0, 0, 1000), (0, -1000, 0)))
source = json.loads(Path(job['source']).read_text())
bone_names = {f"src_{b['id']:03d}": b['id'] for b in source['bones']}
positions, weights, triangles = [], [], []
for ro in role_objs:
    assert ro.matrix_local == Matrix.Identity(4) and all(m.type == 'ARMATURE' for m in ro.modifiers)
    role = ro['source_info_index']
    base = len(positions)
    for v in ro.data.vertices:
        positions.append(list(to_source @ v.co))
        inf = sorted([bone_names[ro.vertex_groups[g.group].name], g.weight] for g in v.groups if g.weight > 1e-7)
        tot = sum(w for _, w in inf)
        assert 0 < len(inf) <= 3 and abs(tot - 1) < 1e-5, (role, inf)
        weights.append([[b, w / tot] for b, w in inf])
    me = ro.data
    atlas, srcuv = me.uv_layers['AtlasUV'], me.uv_layers['SourceUV']
    me.calc_loop_triangles()
    for lt in me.loop_triangles:
        corners = []
        for li in lt.loops:
            n = to_source @ me.corner_normals[li].vector; n.normalize()
            u, v = atlas.data[li].uv
            c = {'vertex': base + me.loops[li].vertex_index, 'normal': list(n), 'uv': [u, 1 - v]}
            if role == 7:
                su, sv = srcuv.data[li].uv
                c['src_uv'] = [su, 1 - sv]
            corners.append(c)
        t = {'source_info': role, 'corners': corners}
        if role == 7:
            t['material'] = hair_mat[me.materials[me.polygons[lt.polygon_index].material_index].name.replace('SourceTex_', '')]
        triangles.append(t)
mesh = {'schema': 're4dc-approved-render-mesh-1', 'blend_sha256': None, 'source_sha256': job['source_sha256'],
        'mesh': 'Leon_B_RenderMesh', 'positions_mm': positions, 'weights': weights, 'bones': source['bones'], 'triangles': triangles,
        'source_info_counts': {str(i): sum(t['source_info'] == i for t in triangles) for i in range(8)},
        'policy': 'ps2leon arm B: the PS2 budget redistributed, GC sections reduced; render only. Source info visibility remains separate.'}
(out / 'mesh.json').write_text(json.dumps(mesh, separators=(',', ':')))
report.update(triangles=len(triangles), vertices=len(positions))
(out / 'report-b.json').write_text(json.dumps(report, indent=1))
for c in scene.collection.children:
    if c.name != col.name:
        c.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=str(out / 'leon-b.blend'), compress=True)
print('ARM_B', len(triangles), 'triangles', len(positions), 'vertices', flush=True)
