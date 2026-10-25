# world-blender25: per map cell piece (meshlet instance) and vertex counts for an R4IM+R4PW world.
# usage: cells.py <bundle dir> <cell metres> [--doc]
import sys, struct, collections, json
sys.path.insert(0, '/root/work/lanes/world-blender25/port/dreamcast/tools/d367/world_blender_roundtrip')
import package as p

d, cell = sys.argv[1], float(sys.argv[2])
mesh = open(d + '/ps2-world.re4mesh', 'rb').read(); side = open(d + '/ps2-world.r4pw', 'rb').read()
doc = p.decode(mesh, side, preserve_index_layout=True)
if '--keys' in sys.argv:
    pass
own = p.owners(doc)
def centre(ji, pl):
    m = doc['meshlets'][ji]; mi = own[ji][0]; me = doc['meshes'][mi]
    lo, hi = me[14:17], me[17:20]
    q = [(m[5+a] + m[8+a]) / 2 / 65535.0 for a in range(3)]
    loc = [lo[a] + q[a] * (hi[a] - lo[a]) for a in range(3)]
    A = pl[2:]
    return [A[r*4]*loc[0] + A[r*4+1]*loc[1] + A[r*4+2]*loc[2] + A[r*4+3] for r in range(3)]
pieces = []  # (x, z, verts, mesh, placement index, ji)
for pidx, pl in enumerate(doc['placements']):
    mi = pl[0]; me = doc['meshes'][mi]
    for ji, o in own.items():
        if o[0] != mi or o[4] != 0:
            continue
        c = centre(ji, pl)
        pieces.append((c[0], c[2], doc['meshlets'][ji][3], mi, pidx, ji))
print('LOD0 pieces', len(pieces), 'verts', sum(x[2] for x in pieces))
xs = [x[0] for x in pieces]; zs = [x[1] for x in pieces]
x0, z0 = min(xs), min(zs)
print('extent mm x %.0f..%.0f z %.0f..%.0f' % (x0, max(xs), z0, max(zs)))
for cm in (cell,):
    c = collections.Counter(); v = collections.Counter()
    for x, z, n, *_ in pieces:
        k = (int((x - x0) // (cm*1000)), int((z - z0) // (cm*1000))); c[k] += 1; v[k] += n
    for k, n in c.most_common(6):
        print('cell %.0fm col %s row %d: pieces %d verts %d' % (cm, chr(65 + k[0]), k[1] + 1, n, v[k]))
json.dump(dict(x0=x0, z0=z0, cell=cell), open(d + '/grid.json', 'w'))
cx, cz = -7914.0, 2000.0
for h in (10, 12.5, 15, 20):
    sel = [x for x in pieces if abs(x[0]-cx) <= h*1000 and abs(x[1]-cz) <= h*1000]
    print('centre cross +-%.1fm: pieces %d verts %d meshes %d placements %d' % (h, len(sel), sum(x[2] for x in sel), len({x[3] for x in sel}), len({x[4] for x in sel})))
