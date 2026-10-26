"""efminv.py: pose-invariant geometry match of the EFM_PS2_CUT models against every PS2 efm model (lane fxproof26).

Triangle shape key = its three edge lengths, sorted, rounded to 1 unit (and to 2% for a scale-normalised pass, where
lengths are divided by the model's longest bbox side): invariant to translation and rotation (a model re-posed or
re-centred under a new id still matches). score = share of the GC triangles whose key occurs in the PS2 model.
"""
import sys, math, collections
sys.path.insert(0, '/root/work/lanes/fxproof26')
import efmmatch as M
PI = M.PI


def keys(tris, norm=False):
    pts = [v for t in tris for v in t]
    s = 1.0
    if norm and pts:
        s = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)) or 1.0
    c = collections.Counter()
    for t in tris:
        e = sorted(math.dist(t[i], t[(i + 1) % 3]) / s for i in range(3))
        c[tuple(round(x * (50 if norm else 1)) for x in e)] += 1
    return c


def score(a, b):
    return sum(min(n, b.get(k, 0)) for k, n in a.items()) / max(1, sum(a.values()))


def main():
    src = PI.Sources()
    gcm = {}
    for room, idv, kind in M.CUT:
        al = PI.core_assets(src) if room == 'core' else PI.room_assets(src, room)
        for cls, name, loc, gb, gt, pb_, pt_ in al:
            if cls == 'breakables' and loc['id'] == idv and ((kind == 0 and loc['kind'] == 'CORE') or
                                                            (kind == 1 and loc['kind'] == 'EFF') or
                                                            (kind == 2 and loc['kind'] == 'ETM')):
                gcm[(room, idv, name)] = M.gc_tris(gb)
    pm = [(n, i, t, keys(t), keys(t, True)) for n, i, t in M.ps2_models(src)]
    for k, tris in sorted(gcm.items()):
        a, an = keys(tris), keys(tris, True)
        res = sorted(((score(a, pk), score(an, pkn), n, len(t)) for n, i, t, pk, pkn in pm), reverse=True)
        resn = sorted(((score(an, pkn), score(a, pk), n, len(t)) for n, i, t, pk, pkn in pm), reverse=True)
        print('GC %s %s tris=%d' % (k[0], k[2], len(tris)))
        for r in res[:3]:
            print('   abs %.3f norm %.3f  %s tris=%d' % r)
        for r in resn[:2]:
            print('   norm %.3f abs %.3f  %s tris=%d' % r)


if __name__ == '__main__':
    main()
