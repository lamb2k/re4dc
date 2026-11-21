#!/usr/bin/env python3
"""e2_exact.py: the line tests of two e2.txt logs (svc/e2_dump.cpp) against the same definitions evaluated in double
precision (lane eng-e2a). A second opinion beside e2_compare.py, never in its place: where the reference and the engine
differ by more than the bound, it says which of the two is nearer the definition both compute.

    e2_exact.py <ref dir> <test dir> [--json out.json]

Definitions (services/aim/em_hit.cpp, the game's): LC a capsule (an end sphere's entry beyond its end plane, the far end
first, else the side point h back along the segment from its nearest approach to the axis; an axis within 0.01 rad of
the vertical taken as the vertical; a start inside is a); LB a box in a frame (slabs; a mirrored frame takes the exit);
LQ a quad from its front; LA the capsule of the box chosen (its geometry from the G tokens, RE4_E2_BOXGEOM runs). Only
lines whose two answers both hit are measured. Exit 0 always (a report).
"""
import json
import math
import sys


def vec(t):
    return [float(x) for x in t[1:].split(',')]


def sub(a, b): return [a[i] - b[i] for i in range(3)]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def mul(a, s): return [a[i] * s for i in range(3)]
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def norm(a): return math.sqrt(dot(a, a))


def capsule(a, b, top, bot, r, snap=True, game_side=True):
    """the game's definition (snap: an axis within 0.01 rad of the vertical taken as the vertical; game_side: the side
    point h back along the segment from the nearest approach); snap=False / game_side=False give the true geometry"""
    rr = r * r
    ax = sub(top, bot)
    ln = norm(ax)
    u = [0.0, 1.0, 0.0] if ln == 0 else mul(ax, 1.0 / ln)
    if snap and (u[1] >= 0.99995 or u[1] <= -0.99995):
        u = [0.0, 1.0, 0.0]
    ra = sub(a, bot)
    sa = dot(ra, u)
    qa = sub(ra, mul(u, sa))
    if dot(sub(a, top), sub(a, top)) < rr or dot(ra, ra) < rr or (0 < sa < ln and dot(qa, qa) < rr):
        return a
    d = sub(b, a)
    if dot(d, d) <= 0.1:
        return None
    sd = dot(d, u)
    for c in (top, bot):
        m = sub(a, c)
        A, B, C = dot(d, d), dot(m, d), dot(m, m) - rr
        disc = B * B - A * C
        if A > 0 and disc > 0:
            t = (-B - math.sqrt(disc)) / A
            if 0 <= t <= 1:
                s = sa + t * sd
                if s < 0 or s > ln:
                    return add(a, mul(d, t))
    qd = sub(d, mul(u, sd))
    A = dot(qd, qd)
    if not A > 0.1:
        return None
    tn = -dot(qa, qd) / A
    q = add(qa, mul(qd, tn))
    q2 = dot(q, q)
    if not q2 < rr:
        return None
    back = math.sqrt(rr - q2) / (norm(d) if game_side else math.sqrt(A))
    t = tn - back if tn > 0 else tn + back
    s = sa + t * sd
    return add(a, mul(d, t)) if 0 <= t <= 1 and 0 <= s <= ln else None


def box(a, b, sx, sy, sz, ofs, cols):
    c = add(add(add(mul(cols[0], ofs[0]), mul(cols[1], ofs[1])), mul(cols[2], ofs[2])), cols[3])
    e0, e1, e2 = cols[0], cols[1], cols[2]
    det = dot(e0, cross(e1, e2))
    if det == 0:
        return None
    # rows of the inverse: (e1 x e2, e2 x e0, e0 x e1) / det
    inv = [mul(cross(e1, e2), 1 / det), mul(cross(e2, e0), 1 / det), mul(cross(e0, e1), 1 / det)]
    la = [dot(inv[i], sub(a, c)) for i in range(3)]
    lb = [dot(inv[i], sub(b, c)) for i in range(3)]
    lo, hi = [-sx, 0.0, -sz], [sx, sy, sz]
    tin, tout = -1e30, 1e30
    for i in range(3):
        dd = lb[i] - la[i]
        if dd == 0:
            if la[i] < lo[i] or la[i] > hi[i]:
                return None
            continue
        t0, t1 = (lo[i] - la[i]) / dd, (hi[i] - la[i]) / dd
        if t0 > t1:
            t0, t1 = t1, t0
        tin, tout = max(tin, t0), min(tout, t1)
    if tin > tout:
        return None
    t = tout if det < 0 else tin
    return add(a, mul(sub(b, a), t)) if 0 < t < 1 else None


def quad(a, b, q):
    n = cross(sub(q[2], q[1]), sub(q[0], q[1]))
    if n == [0, 0, 0]:
        return None
    da, db = dot(n, sub(a, q[0])), dot(n, sub(b, q[0]))
    if not (da > 0 and db < 0):
        return None
    x = add(a, mul(sub(b, a), da / (da - db)))
    for k in range(4):
        o = q[(k + 1) & 3]
        if dot(n, cross(sub(x, o), sub(q[k], o))) < 0:
            return None
    return x


def answer(tok, snap=True, game_side=True):
    """(definition's point or None, the log's point or None) for one line's tokens; snap / game_side as capsule()"""
    k = tok[1]
    arrow = tok.index('->')
    ins, outs = tok[2:arrow], tok[arrow + 1:]
    if k == 'LC':
        a, b, top, bot = (vec(x) for x in ins[:4])
        exact = capsule(a, b, top, bot, float(ins[4][1:]), snap, game_side)
        got = vec(outs[1]) if outs[0] == '1' else None
    elif k == 'LB':
        a, b = vec(ins[0]), vec(ins[1])
        sx, sy, sz = (float(x[1:]) for x in ins[2:5])
        ofs = vec(ins[5])
        cols = [vec(x) for x in ins[6:10]]
        exact = box(a, b, sx, sy, sz, ofs, cols)
        got = vec(outs[1]) if outs[0] == '1' else None
    elif k == 'LQ':
        a, b = vec(ins[0]), vec(ins[1])
        exact = quad(a, b, [vec(x) for x in ins[2:6]])
        got = vec(outs[1]) if outs[0] == '1' else None
    elif k == 'LA':
        g = [x for x in outs if x.startswith('G')]
        if len(g) != 3 or not outs[0].startswith('box') or int(outs[1], 16) & 8:
            return None
        a, b = vec(ins[1]), vec(ins[2])
        exact = capsule(a, b, vec(g[0]), vec(g[1]), float(g[2][1:]), snap, game_side)
        got = vec(outs[2])
    else:
        return None
    return exact, got


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    if js in args:
        args.remove(js)
    ra = open(args[0] + '/e2.txt').read().split('\n')
    rb = open(args[1] + '/e2.txt').read().split('\n')
    stats = {}
    rows = []
    rescue = []
    approx = {}   # the original's approximations: the largest gap between the game's answer and the true geometry
    for i, (x, y) in enumerate(zip(ra, rb)):
        tx, ty = x.split(), y.split()
        if len(tx) < 3 or tx[1] not in ('LC', 'LB', 'LQ', 'LA') or '->' not in tx or '->' not in ty:
            continue
        ar, at = answer(tx), answer(ty)
        if not ar or not at or ar[1] is None or at[1] is None or ar[0] is None:
            continue
        ex = ar[0]
        dr, dt = norm(sub(ar[1], ex)), norm(sub(at[1], ex))
        dd = max(abs(ar[1][j] - at[1][j]) for j in range(3))
        s = stats.setdefault(tx[1], {'lines': 0, 'ref_max': 0.0, 'test_max': 0.0, 'ref_over': 0, 'test_over': 0})
        s['lines'] += 1
        s['ref_max'] = max(s['ref_max'], dr)
        s['test_max'] = max(s['test_max'], dt)
        s['ref_over'] += dr > 0.01
        s['test_over'] += dt > 0.01
        # the integrator's rule (lane eng-e2a item 1): the engine within 0.01 of the definition, the reference farther
        if dt <= 0.01 and dr > dt:
            rescue.append(i + 1)
        if tx[1] in ('LC', 'LA'):
            for name, kw in (('vertical-snap', {'snap': False}), ('side-point', {'game_side': False})):
                tr = answer(tx, **kw)
                if tr and tr[0] is not None:
                    gap = norm(sub(ex, tr[0]))
                    if gap > approx.get(name, {'gap': 0.0})['gap']:
                        approx[name] = {'gap': gap, 'line': i + 1, 'text': x[:400]}
        if dd > 0.01:
            rows.append({'line': i + 1, 'kind': tx[1], 'ref_vs_test': dd, 'ref_from_exact': dr, 'test_from_exact': dt})
    for k, s in sorted(stats.items()):
        print('%s: %d hits; from the double-precision definition: reference max %.4g (%d over 0.01), engine max %.4g (%d over 0.01)'
              % (k, s['lines'], s['ref_max'], s['ref_over'], s['test_max'], s['test_over']))
    for r in rows:
        print('  line %(line)d %(kind)s: reference and engine %(ref_vs_test).4g apart; reference %(ref_from_exact).4g, engine '
              '%(test_from_exact).4g from the definition' % r)
    for name, a in sorted(approx.items()):
        print('approximation %s: largest gap from the true geometry %.4g unit at line %d' % (name, a['gap'], a['line']))
    if js:
        with open(js, 'w') as f:
            json.dump({'stats': stats, 'apart': rows, 'rescue': rescue, 'approximations': approx}, f, indent=1)


if __name__ == '__main__':
    main()
