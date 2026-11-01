# world-blender25: Blender built-ins on converter-input parts. Run by wb_filter.py:
#   blender --background --factory-startup --python wb_reduce.py -- job.json res.json
# Per part (one texture/pass/cull): Merge by Distance (bmesh remove_doubles; corners keep their own UV/colour, so
# seams survive), Limited Dissolve (dissolve_limit, delimit UV+material) + triangulate, then Decimate (collapse
# modifier, triangulate) at a ratio. Parts under 8 triangles are left alone. Positions in model mm.
import sys, json, math
import bpy, bmesh

a = sys.argv[sys.argv.index('--') + 1:]
job = json.load(open(a[0])); op = job['op']
st = dict(tri_in=0, tri_out=0, v_in=0, v_out=0, parts=0)
out = []
for m in job['meshes']:
    rparts = []
    for tris in m['parts']:
        if len(tris) < 8:
            rparts.append([[c[:9] for c in t] for t in tris]); continue
        if not any(c[9] for t in tris for c in t):
            rparts.append([[c[:9] for c in t] for t in tris]); continue
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new('uv'); coll = bm.loops.layers.float_color.new('col')
        vm = {}; mask = set()
        for t in tris:
            vs = []
            for c in t:
                k = tuple(c[0:3])
                if k not in vm:
                    vm[k] = bm.verts.new(k)
                if len(c) > 9 and c[9]:
                    mask.add(vm[k])
                vs.append(vm[k])
            if len(set(vs)) < 3:
                continue
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            for l, c in zip(f.loops, t):
                l[uvl].uv = (c[3], c[4]); l[coll] = [c[5], c[6], c[7], c[8]]
        v0, t0 = len(bm.verts), len(bm.faces)
        if op['merge'] > 0:
            bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if v in mask], dist=op['merge'])
        if op['angle'] > 0:
            mv = [v for v in bm.verts if v.is_valid and v in mask]
            bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(op['angle']), verts=mv,
                                     edges=[e for e in bm.edges if all(v in mask for v in e.verts)],
                                     delimit={'UV'})
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
        if op['ratio'] < 1:
            bm.verts.index_update(); wi = [v.index for v in bm.verts if v.is_valid and v in mask]
            me = bpy.data.meshes.new('p'); bm.to_mesh(me); bm.free()
            ob = bpy.data.objects.new('p', me); bpy.context.scene.collection.objects.link(ob)
            vg = ob.vertex_groups.new(name='box'); vg.add(wi, 1.0, 'REPLACE')
            md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = op['ratio']; md.use_collapse_triangulate = True
            md.vertex_group = 'box'; md.vertex_group_factor = 1000.0
            dg = bpy.context.evaluated_depsgraph_get()
            me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            bm = bmesh.new(); bm.from_mesh(me2)
            uvl = bm.loops.layers.uv.get('uv'); coll = bm.loops.layers.float_color.get('col')
            bpy.data.objects.remove(ob); bpy.data.meshes.remove(me2)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        rt = []
        for f in bm.faces:
            rt.append([[*l.vert.co, l[uvl].uv.x, l[uvl].uv.y, *l[coll]] for l in f.loops])
        st['tri_in'] += t0; st['tri_out'] += len(rt); st['v_in'] += v0; st['v_out'] += len(bm.verts); st['parts'] += 1
        bm.free()
        if not rt:  # never empty a part (the converter would drop it and renumber parts)
            rt = [[c[:9] for c in t] for t in tris]
        rparts.append(rt)
    out.append(dict(mesh=m['mesh'], parts=rparts))
json.dump(dict(meshes=out), open(a[1], 'w'))
print('WB_REDUCE', json.dumps(op), json.dumps(st))
