# world-blender25: apply ONE Blender built-in mesh operation to every group of a JADERLINK PS2 scenario OBJ and write
# the OBJ back in the same format (group names, usemtl runs, v x y z r g b a, vt, f v/vt). Untouched data passes through.
# Run: blender --background --factory-startup --python wb_ops.py -- <in.obj> <out.obj> <op> [param]
# ops: none | merge <dist OBJ units> | dissolve <deg> | sort | interior | decimate <ratio> <far_m>
import sys, math, collections
import bpy, bmesh

a = sys.argv[sys.argv.index('--') + 1:]
src, dst, op = a[0], a[1], a[2]
par = [float(x) for x in a[3:]]

# ---- parse (keep header lines, per group: name, verts, vts, faces with material runs)
head, groups = [], []
cur = None
vbase = tbase = 0  # global 1-based indices
V, T = [], []
VL, TL = [], []
for line in open(src, encoding='latin-1'):
    if line.startswith('g '):
        cur = dict(name=line.rstrip('\n'), v0=len(V), t0=len(T), faces=[], mats=[], pre=[])
        groups.append(cur); continue
    if cur is None:
        head.append(line); continue
    if line.startswith('v '):
        V.append(line.split()[1:]); VL.append(line); continue
    if line.startswith('vt '):
        T.append(line.split()[1:]); TL.append(line); continue
    if line.startswith('usemtl '):
        cur['mat'] = line.split(None, 1)[1].strip(); continue
    if line.startswith('f '):
        idx = [tuple(int(x) for x in c.split('/')) for c in line.split()[1:]]
        cur['faces'].append((cur.get('mat'), idx)); continue
    if line.strip():
        cur['pre'].append(line)
print('parsed groups', len(groups), 'v', len(V), 'vt', len(T), 'f', sum(len(g['faces']) for g in groups))

stats = collections.Counter()


def process(g):
    faces = g['faces']
    if not faces:
        return [], [], []
    bm = bmesh.new()
    col = bm.verts.layers.float_color.new('col') if hasattr(bm.verts.layers, 'float_color') else None
    uvl = bm.loops.layers.uv.new('uv')
    ov = bm.verts.layers.int.new('ov')
    ot = bm.loops.layers.int.new('ot')
    vmap = {}
    nxt = len(V) if groups.index(g) == len(groups) - 1 else groups[groups.index(g) + 1]['v0']
    for vi in range(g['v0'] + 1, nxt + 1):
        p = V[vi - 1]
        bv = bm.verts.new((float(p[0]), float(p[1]), float(p[2])))
        bv[col] = [float(x) for x in p[3:7]]
        bv[ov] = vi
        vmap[vi] = bv
    mats = []
    for m, _ in faces:
        if m not in mats:
            mats.append(m)
    for m, idx in faces:
        vs = []
        for vi, ti in idx:
            if vi not in vmap:
                p = V[vi - 1]
                bv = bm.verts.new((float(p[0]), float(p[1]), float(p[2])))
                bv[col] = [float(x) for x in p[3:7]]
                vmap[vi] = bv
            vs.append(vmap[vi])
        if len(set(vs)) < 3:
            stats['degenerate_in'] += 1
            continue
        try:
            f = bm.faces.new(vs)
        except ValueError:
            stats['dup_face_in'] += 1
            continue
        f.material_index = mats.index(m)
        for l, (vi, ti) in zip(f.loops, idx):
            t = T[ti - 1]
            l[uvl].uv = (float(t[0]), float(t[1]))
            l[ot] = ti
    bm.verts.ensure_lookup_table()
    if op == 'merge':
        # Merge by Distance per identical vertex colour (keeps colour seams); UV is per loop so UV seams survive.
        by = collections.defaultdict(list)
        for v in bm.verts:
            by[tuple(round(c, 6) for c in v[col])].append(v)
        n0 = len(bm.verts)
        for vs in by.values():
            if len(vs) > 1:
                bmesh.ops.remove_doubles(bm, verts=vs, dist=par[0])
        stats['merge_removed'] += n0 - len(bm.verts)
    elif op == 'dissolve':
        n0 = len(bm.faces)
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(par[0]), verts=bm.verts[:], edges=bm.edges[:],
                                 delimit={'MATERIAL', 'SEAM', 'SHARP', 'UV'})
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        stats['dissolve_dfaces'] += len(bm.faces) - n0
    elif op == 'interior':
        bm.edges.ensure_lookup_table()
        inner = [f for f in bm.faces if all(len(e.link_faces) > 2 for e in f.edges)]
        stats['interior_faces'] += len(inner)
        bmesh.ops.delete(bm, geom=inner, context='FACES')
    elif op == 'sort':
        pass  # handled below (Blender Sort Mesh Elements needs an object; done through bpy)
    elif op == 'decimate':
        ratio, far = par[0], par[1] * 10.0  # metres -> OBJ units (1 unit = 100 mm)
        c = sum((v.co for v in bm.verts), bm.verts[0].co.copy() * 0) / len(bm.verts)
        if c.length >= far:
            n0 = len(bm.faces)
            me = bpy.data.meshes.new('d'); bm.to_mesh(me); bm.free()
            ob = bpy.data.objects.new('d', me); bpy.context.scene.collection.objects.link(ob)
            md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = ratio; md.use_collapse_triangulate = True
            dg = bpy.context.evaluated_depsgraph_get(); me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            bm = bmesh.new(); bm.from_mesh(me2)
            col = bm.verts.layers.float_color.get('col'); uvl = bm.loops.layers.uv.get('uv'); ov = bm.verts.layers.int.get('ov'); ot = bm.loops.layers.int.get('ot')
            bpy.data.objects.remove(ob); stats['decimate_groups'] += 1; stats['decimate_dfaces'] += len(bm.faces) - n0
    if op == 'sort':
        me = bpy.data.meshes.new('s'); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new('s', me); bpy.context.scene.collection.objects.link(ob)
        bpy.context.view_layer.objects.active = ob; ob.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT', 'FACE'})
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new(); bm.from_mesh(me); col = bm.verts.layers.float_color.get('col'); uvl = bm.loops.layers.uv.get('uv'); ov = bm.verts.layers.int.get('ov'); ot = bm.loops.layers.int.get('ot')
        bpy.data.objects.remove(ob)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    vl = []
    for v in bm.verts:
        o = v[ov]
        if o and same(V[o - 1][:3], list(v.co)):
            vl.append(VL[o - 1])
        else:
            c = V[o - 1][3:7] if o else [repr_f(x) for x in v[col]]
            vl.append('v %s %s %s %s\n' % (repr_f(v.co.x), repr_f(v.co.y), repr_f(v.co.z), ' '.join(c)))
    tl, fl = [], []
    tkey = {}
    lastm = None
    for f in bm.faces:
        m = mats[f.material_index] if f.material_index < len(mats) else mats[0]
        if m != lastm:
            fl.append(('usemtl', m)); lastm = m
        cs = []
        for l in f.loops:
            uv = (repr_f(l[uvl].uv.x), repr_f(l[uvl].uv.y))
            o = l[ot]
            tl.append(TL[o - 1] if o and same(T[o - 1][:2], list(l[uvl].uv)) else 'vt %s %s\n' % uv)
            cs.append((l.vert.index, len(tl) - 1))
        fl.append(('f', cs))
    bm.free()
    return vl, tl, fl


import struct as _st
def f32(x):
    return _st.unpack('<f', _st.pack('<f', float(x)))[0]
def same(txt, vals):
    return len(txt) >= len(vals) and all(f32(a) == f32(b) for a, b in zip(txt, vals))


def repr_f(x):
    s = '%.7g' % x
    return s


out = open(dst, 'w', encoding='latin-1', newline='\n')
out.writelines(head)
gv = gt = 0
for g in groups:
    vl, tl, fl = process(g)
    out.write(g['name'] + '\n')
    out.writelines(vl); out.writelines(tl)
    for k, x in fl:
        if k == 'usemtl':
            out.write('usemtl %s\n' % x)
        else:
            out.write('f ' + ' '.join('%d/%d' % (gv + vi + 1, gt + ti + 1) for vi, ti in x) + '\n')
    gv += len(vl); gt += len(tl)
out.close()
print('WB_OPS', op, par, 'groups', len(groups), 'v_out', gv, 'vt_out', gt, dict(stats))
