#!/usr/bin/env python3
"""e2_compare.py: compare the boundary logs (e2.txt, svc/e2_dump.cpp) of two re4ref runs (lane eng-e2a).

    e2_compare.py <ref dir> <test dir> [--rescue exact.json] [--json out.json]

The same calls in the same order: every token equal, except the typed numbers, each within its bound. Positions
("P" x, y, z: each axis), lengths ("R") and the roots of squared distances ("D") within max(0.01 unit, 2^-20 of the
value), the bound lane eng-e1j set for the camera (integrator ruling on lane eng-e2a's item 1: the plain 0.01 bound
cannot hold where a float's own step is near it); angles ("A") within 0.01 degree. Integers, flags, box names and counts
compare exactly; lines starting with '#' (exercise markers) too.

--rescue exact.json (e2_exact.py, the same two runs): a line-test line (LA, LC, LB, LQ) outside the bound still agrees
when e2_exact.py lists it as rescued: both answers hit, every text token is equal, the engine's hit point is within 0.01
unit of the double-precision answer of the same definition, and the reference is farther from it than the engine is.
Both counts are reported (lines within the bound; lines agreeing only by that rule).

Exit 0 when the logs agree, 1 on a difference (the first is named, with the largest deviation per type), 2 on a missing
or empty log or rescue file.
"""
import json
import math
import sys
from collections import Counter

POS = 0.01
REL = 2.0 ** -20
DEG = 0.01


def load(d):
    try:
        with open(d + '/e2.txt', errors='replace') as f:
            return [ln.rstrip('\n') for ln in f]
    except OSError:
        return None


def nums(tok):
    return [float(x) for x in tok[1:].split(',')]


def bound(v):
    return max(POS, abs(v) * REL)


def token_dev(a, b):
    """(ok, kind, deviation) for one token pair; deviation in units (degrees for A)"""
    if a == b:
        return True, None, 0.0
    if a[:1] != b[:1] or a[:1] not in 'PRDA' or len(a) < 2 or len(b) < 2:
        return False, 'text', None
    k = a[0]
    try:
        x, y = nums(a), nums(b)
    except ValueError:
        return False, 'text', None
    if len(x) != len(y):
        return False, 'text', None
    if k in 'PR':
        devs = [(abs(u - v), bound(u)) for u, v in zip(x, y)]
    elif k == 'D':
        devs = [(abs(math.sqrt(max(u, 0.0)) - math.sqrt(max(v, 0.0))), bound(math.sqrt(max(u, 0.0)))) for u, v in zip(x, y)]
    else:
        d = abs(x[0] - y[0]) % (2 * math.pi)
        devs = [(math.degrees(min(d, 2 * math.pi - d)), DEG)]
    return all(dv <= bd for dv, bd in devs), k, max(dv for dv, bd in devs)


def text_equal(tx, ty):
    return len(tx) == len(ty) and all(a == b or (a[:1] == b[:1] and a[:1] in 'PRDAG') for a, b in zip(tx, ty))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = {}
    for o in ('--json', '--rescue'):
        if o in sys.argv:
            opt[o] = sys.argv[sys.argv.index(o) + 1]
            args.remove(opt[o])
    ra, rb = load(args[0]), load(args[1])
    if not ra or not rb:
        print('e2_compare: missing or empty e2.txt')
        sys.exit(2)
    rescue = set()
    if '--rescue' in opt:
        try:
            rescue = set(json.load(open(opt['--rescue']))['rescue'])
        except (OSError, KeyError, ValueError):
            print('e2_compare: unreadable rescue file %s' % opt['--rescue'])
            sys.exit(2)
    kinds = Counter(l.split()[1] for l in ra if not l.startswith('#') and len(l.split()) > 1)
    worst = {}
    first = None
    same = exact = rescued = 0
    for i, (x, y) in enumerate(zip(ra, rb)):
        tx, ty = x.split(), y.split()
        ok = len(tx) == len(ty)
        if ok:
            for a, b in zip(tx, ty):
                good, k, dev = token_dev(a, b)
                if k and dev is not None and dev > worst.get(k, (0.0, 0))[0]:
                    worst[k] = (dev, i + 1)
                ok = ok and good
        if ok:
            same += 1
            exact += x == y
        elif i + 1 in rescue and len(tx) > 1 and tx[1] in ('LA', 'LC', 'LB', 'LQ') and text_equal(tx, ty):
            rescued += 1
        elif first is None:
            first = {'line': i + 1, 'ref': x[:300], 'test': y[:300]}
    if first is None and len(ra) != len(rb):
        first = {'line': min(len(ra), len(rb)) + 1, 'ref': 'lines %d' % len(ra), 'test': 'lines %d' % len(rb)}
    ok = first is None
    rep = {'lines_ref': len(ra), 'lines_test': len(rb), 'within': same, 'identical': exact, 'rescued_by_exact': rescued,
           'kinds': dict(kinds), 'worst': {k: {'dev': v[0], 'line': v[1]} for k, v in worst.items()}, 'first': first,
           'verdict': 'PASS' if ok else 'FAIL',
           'bounds': {'pos_unit': POS, 'pos_rel': REL, 'angle_deg': DEG, 'rescue_file': opt.get('--rescue')}}
    w = ' '.join('%s %.5g@%d' % (k, v[0], v[1]) for k, v in sorted(worst.items()))
    print('%s  e2 lines %d/%d within bounds (%d identical), %d more by the double-precision answer rule; worst %s; calls %s%s' % (
        rep['verdict'], same, len(ra), exact, rescued, w or '-', ' '.join('%s %d' % kv for kv in sorted(kinds.items())),
        '' if ok else '; first difference at line %d: ref "%s" test "%s"' % (first['line'], first['ref'][:200], first['test'][:200])))
    if '--json' in opt:
        with open(opt['--json'], 'w') as f:
            json.dump(rep, f, indent=1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
