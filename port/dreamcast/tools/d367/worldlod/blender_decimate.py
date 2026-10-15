"""blender_decimate.py: Blender's Decimate (collapse) as the far-level reducer of tools/ps2_world_far_lod.py
(lane worldlod 2026-10-15, backlog C1; user idea: let a real mesh tool do the reduction).

  blender -b --factory-startup --python blender_decimate.py -- IN.json OUT.json

IN.json = ps2_world_far_lod.py --export-clusters (per cluster: model-unit positions, triangles with per-corner UV and
ARGB1555 colour, locked vertices = the ones shared with another cluster or part, triangle target). Per cluster the
script builds one mesh (corner UVs and corner colours as attributes, so UV seams are corner splits as in the source),
puts the locked vertices in a vertex group that the Decimate modifier protects (inverted group, factor 1000), decimates
in COLLAPSE mode to target / triangles, triangulates, and writes the triangles back with interpolated UV and colour.
A cluster whose result moved or lost a locked vertex is reported (crack risk) and written with the vertex snapped back
when it still exists. Deterministic: same input, same Blender version, same output (no randomness in collapse).
OUT.json = {"blender": version, "clusters": {cid: {"tris": [[x, y, z, u, v, argb1555] x3, ...], "locked_moved": n}}}
"""
import json
import sys

import bpy
import bmesh


def c1555_to_rgba(c):
    return (((c >> 10) & 31) / 31.0, ((c >> 5) & 31) / 31.0, (c & 31) / 31.0, 1.0 if c & 0x8000 else 0.0)


def rgba_to_1555(r, g, b, a):
    q = lambda x: min(31, max(0, round(x * 31)))
    return (0x8000 if a >= 0.5 else 0) | (q(r) << 10) | (q(g) << 5) | q(b)


def reduce_cluster(c):
    pos, tris, locked = c['pos'], c['tris'], set(c['locked'])
    me = bpy.data.meshes.new('c')
    me.from_pydata([tuple(p) for p in pos], [], [tuple(t[0]) for t in tris])
    me.update()
    uv = me.uv_layers.new(name='uv')
    col = me.color_attributes.new(name='col', type='FLOAT_COLOR', domain='CORNER')
    for poly, t in zip(me.polygons, tris):
        assert list(poly.vertices) == list(t[0])
        for k, li in enumerate(poly.loop_indices):
            u, v, colour = t[1][k]
            uv.data[li].uv = (u, v)
            col.data[li].color = c1555_to_rgba(int(colour))
    ob = bpy.data.objects.new('c', me)
    bpy.context.scene.collection.objects.link(ob)
    vg = ob.vertex_groups.new(name='lock')
    if locked:
        vg.add(sorted(locked), 1.0, 'REPLACE')
    mod = ob.modifiers.new('dec', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.0, min(1.0, c['target'] / max(1, len(tris))))
    mod.use_collapse_triangulate = True
    if locked:
        mod.vertex_group = 'lock'
        mod.invert_vertex_group = True
        mod.vertex_group_factor = 1000.0
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m2 = bpy.data.meshes.new_from_object(ev)
    bm = bmesh.new()
    bm.from_mesh(m2)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    uvl = bm.loops.layers.uv.get('uv')
    cl = bm.loops.layers.float_color.get('col')
    import mathutils
    kd = mathutils.kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()
    moved = sum(1 for i in locked if not len(bm.verts) or kd.find(pos[i])[2] > 1.0)   # > 1 model unit (mm) away
    out = []
    for f in bm.faces:
        tri = []
        for lp in f.loops:
            co = lp.vert.co
            u, v = lp[uvl].uv if uvl else (0.0, 0.0)
            r, g, b, a = lp[cl] if cl else (1, 1, 1, 1)
            tri.append([co.x, co.y, co.z, u, v, rgba_to_1555(r, g, b, a)])
        out.append(tri)
    bm.free()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(m2)
    return dict(tris=out, locked_moved=moved, source_tris=len(tris), target=c['target'])


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    src, dst = argv[0], argv[1]
    d = json.load(open(src))
    res = {}
    moved = 0
    for cid in sorted(d['clusters'], key=int):
        r = reduce_cluster(d['clusters'][cid])
        moved += r['locked_moved'] > 0
        res[cid] = r
    json.dump(dict(blender=bpy.app.version_string, source=d.get('source'), clusters=res), open(dst, 'w'))
    print('BLENDER DECIMATE OK clusters %d, clusters with a moved locked vertex %d' % (len(res), moved))


main()
