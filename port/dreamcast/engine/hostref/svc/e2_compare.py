#!/usr/bin/env python3
"""e2_compare.py: compare the enemy hit geometry's boundary logs (e2.txt, svc/e2_dump.cpp) of two re4ref runs (lane
eng-e2a).

    e2_compare.py <ref dir> <test dir> [--json out.json]

The same calls in the same order: every token equal, except the typed numbers, each within its bound (stated in the
brief before the runs): "P" a position (x, y, z) within 0.01 unit in each axis; "R" a length within 0.01 unit; "D" a
squared distance whose root is within 0.01 unit; "A" an angle within 0.01 degree. Integers, flags, box names and the
counts compare exactly. Lines starting with '#' (exercise markers) are compared exactly too. Exit 0 when the logs agree,
1 on a difference (the first is named, with the largest deviation per type), 2 on a missing or empty log.
"""
import json
import math
import sys
from collections import Counter

POS = 0.01
DEG = 0.01


def load(d):
    try:
        with open(d + '/e2.txt', errors='replace') as f:
            return [ln.rstrip('\n') for ln in f]
    except OSError:
        return None


def nums(tok):
    return [float(x) for x in tok[1:].split(',')]


def token_dev(a, b):
    """(ok, kind, deviation) for one token pair"""
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
        dev = max(abs(u - v) for u, v in zip(x, y))
        return dev <= POS, k, dev
    if k == 'D':
        dev = max(abs(math.sqrt(max(u, 0.0)) - math.sqrt(max(v, 0.0))) for u, v in zip(x, y))
        return dev <= POS, k, dev
    d = abs(x[0] - y[0]) % (2 * math.pi)
    dev = math.degrees(min(d, 2 * math.pi - d))
    return dev <= DEG, k, dev


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    if js in args:
        args.remove(js)
    ra, rb = load(args[0]), load(args[1])
    if not ra or not rb:
        print('e2_compare: missing or empty e2.txt')
        sys.exit(2)
    kinds = Counter(l.split()[1] for l in ra if not l.startswith('#') and len(l.split()) > 1)
    worst = {}
    first = None
    same = exact = 0
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
        elif first is None:
            first = {'line': i + 1, 'ref': x[:300], 'test': y[:300]}
    if first is None and len(ra) != len(rb):
        first = {'line': min(len(ra), len(rb)) + 1, 'ref': 'lines %d' % len(ra), 'test': 'lines %d' % len(rb)}
    ok = first is None
    rep = {'lines_ref': len(ra), 'lines_test': len(rb), 'within': same, 'identical': exact, 'kinds': dict(kinds),
           'worst': {k: {'dev': v[0], 'line': v[1]} for k, v in worst.items()}, 'first': first,
           'verdict': 'PASS' if ok else 'FAIL', 'bounds': {'pos_unit': POS, 'angle_deg': DEG}}
    w = ' '.join('%s %.5g@%d' % (k, v[0], v[1]) for k, v in sorted(worst.items()))
    print('%s  e2 lines %d/%d within bounds (%d identical); worst %s; calls %s%s' % (
        rep['verdict'], same, len(ra), exact, w or '-', ' '.join('%s %d' % kv for kv in sorted(kinds.items())),
        '' if ok else '; first difference at line %d: ref "%s" test "%s"' % (first['line'], first['ref'][:200], first['test'][:200])))
    if js:
        with open(js, 'w') as f:
            json.dump(rep, f, indent=1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
