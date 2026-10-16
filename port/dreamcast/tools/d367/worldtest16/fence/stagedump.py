#!/usr/bin/env python3
"""stagedump.py <room dir> X0,Y0,Z0,X1,Y1,Z1 [stage=file ...]: per-stage, per-part triangle / vertex counts inside a
world box (worldtest16: which step of room_c.sh drops the r101 house-fence rails). Every stage file is read with the
same sidecar (src.r4pw: placements + part passes). For each part the drawn level is the one each cluster names
(cluster[6]), as diffverts.py / the loader read it."""
import sys, os, collections, importlib.util
T = '/root/probe/codex-cpu-t15-20261016/tree/port/dreamcast/tools'
sys.path.insert(0, T)
spec = importlib.util.spec_from_file_location('F', T + '/ps2_world_far_lod.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
import ps2_world_far_lod as _  # noqa: crb import path
crb = F.crb
D = sys.argv[1]
B = [float(v) for v in sys.argv[2].split(',')]
STAGES = [a.split('=', 1) for a in sys.argv[3:]] or [
    ('src', 'src.re4mesh'), ('L2', 'L2.re4mesh'), ('flat', 'flat.re4mesh'), ('flatg', 'flatg.re4mesh'),
    ('sp-pre', 'sp/before-groups.re4mesh'), ('sp-wv5', 'sp/ps2-wv5.re4mesh'), ('sp-L0', 'sp/ps2-world.re4mesh')]


def inside(w):
    return B[0] <= w[0] <= B[3] and B[1] <= w[1] <= B[4] and B[2] <= w[2] <= B[5]


def dump(path):
    p = F.read(open(path, 'rb').read())
    sc = os.path.join(os.path.dirname(path), 'ps2-world.r4pw') if '/sp/' in path else os.path.join(D, 'src.r4pw')
    passes, pls = F.read_sidecar(sc, len(p['parts']))
    bymesh = collections.defaultdict(list)
    for mi, aff in pls:
        bymesh[mi].append(aff)
    res = {}
    for mi, mesh in enumerate(p['meshes']):
        step, origin = mesh[11:14], mesh[8:11]
        for pi in range(mesh[6], mesh[6] + mesh[7]):
            c0, cn = p['plods'][pi][0], p['plods'][pi][1]
            ntri, verts = 0, set()
            for ci in range(c0, c0 + cn):
                lv = p['levels'][p['clusters'][ci][6]]
                for li in range(lv[0], lv[0] + lv[1]):
                    corners, strips = F.let_corners(p, p['lets'][li])
                    for s in strips:
                        for t in crb.strip_triangles(s):
                            for aff in bymesh.get(mi, []):
                                ws = []
                                for k in t:
                                    v = p['verts'][corners[k]]
                                    m = [origin[a] + step[a] * v[a] for a in range(3)]
                                    ws.append(tuple(aff[r][0] * m[0] + aff[r][1] * m[1] + aff[r][2] * m[2] + aff[r][3] for r in range(3)))
                                c = [sum(w[a] for w in ws) / 3 for a in range(3)]
                                if inside(c):
                                    ntri += 1
                                    verts.update(tuple(round(x) for x in w) for w in ws)
            if ntri:
                part = p['parts'][pi]
                res[pi] = dict(mesh=mi, bin=mesh[0], pass_=passes[pi], tris=ntri, verts=len(verts), part=part[:6])
    return p, res


out = {}
for name, f in STAGES:
    fp = os.path.join(D, f)
    if not os.path.exists(fp):
        continue
    try:
        p, r = dump(fp)
    except AssertionError as e:
        print(name, 'unreadable with src.r4pw:', e); continue
    out[name] = r
    tot = sum(x['tris'] for x in r.values())
    print('== %-7s parts %4d meshes %3d | in box: %d parts, %d triangles' % (name, len(p['parts']), len(p['meshes']), len(r), tot))
for n, r in out.items():
    agg = collections.Counter()
    for k, x in r.items():
        agg[(x['bin'], x['pass_'])] += x['tris']
    print('%-7s by (bin, pass): %s' % (n, ' '.join('0x%02x/%d:%d' % (b, ps, c) for (b, ps), c in sorted(agg.items()))))
keys = sorted(set(k for r in out.values() for k in r))
print('part  bin  pass  ' + '  '.join('%7s' % n for n in out))
for k in keys:
    any_ = next(r[k] for r in out.values() if k in r)
    print('%4d  0x%02x  %d    ' % (k, any_['bin'], any_['pass_']) + '  '.join('%7s' % (out[n][k]['tris'] if k in out[n] else '-') for n in out))
