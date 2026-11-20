#!/usr/bin/env python3
"""svc4_compare.py: compare the round-4 boundary logs (svc4.txt, svc4_dump.cpp) of two re4ref runs (lane eng-svc4).

    svc4_compare.py <ref dir> <test dir> [--json out.json] [--tol U]

Every call the behaviour made to a round-4 service entry point, in call order, with its tick, inputs and outputs as
float bits: the two logs must hold the same calls with the same results, line for line (bit-identical). Lines that
start with '#' are counters and are reported, not compared. Exit 0 when identical, 1 on a difference (the first one
is named), 2 on a missing or empty log.

--tol U (the approximate rows, e.g. 16-bit motion keys): the same calls in the same order with the same integer
results; every float within U (absolute, or relative to the value's size for values over 1000); folded hashes of float
state ('h' tokens) are not compared.
"""
import math
import re
import struct

FLT = re.compile(r'^[0-9a-f]{8}(,[0-9a-f]{8}){0,2}$')


def fl(h):
    return struct.unpack('<f', struct.pack('<I', int(h, 16)))[0]


def near(x, y, tol):
    """two log lines equal within tol: integers and kinds exact, float groups within tol, hashes skipped"""
    tx, ty = x.split(), y.split()
    if len(tx) != len(ty):
        return False
    for a, b in zip(tx, ty):
        if a == b:
            continue
        if a.startswith('h') and b.startswith('h'):
            continue
        if FLT.match(a) and FLT.match(b):
            for u, v in zip(a.split(','), b.split(',')):
                fu, fv = fl(u), fl(v)
                if math.isnan(fu) and math.isnan(fv):
                    continue
                if not abs(fu - fv) <= tol * max(1.0, abs(fu) / 1000.0):
                    return False
            continue
        return False
    return True
import json
import sys
from collections import Counter


def load(d):
    calls, notes = [], []
    try:
        with open(d + '/svc4.txt', errors='replace') as f:
            for ln in f:
                ln = ln.rstrip('\n')
                (notes if ln.startswith('#') else calls).append(ln)
    except OSError:
        return None, None
    return calls, notes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    js = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
    tol = float(sys.argv[sys.argv.index('--tol') + 1]) if '--tol' in sys.argv else None
    for v in (js, sys.argv[sys.argv.index('--tol') + 1] if tol is not None else None):
        if v in args:
            args.remove(v)
    a, b = args[0], args[1]
    ca, na = load(a)
    cb, nb = load(b)
    if ca is None or cb is None:
        print('svc4_compare: missing svc4.txt')
        sys.exit(2)
    kinds = Counter(l.split()[1] for l in ca if len(l.split()) > 1)
    first = None
    same = 0
    for i, (x, y) in enumerate(zip(ca, cb)):
        if x == y or (tol is not None and near(x, y, tol)):
            same += 1
        elif first is None:
            first = {'line': i + 1, 'ref': x[:300], 'test': y[:300]}
    ok = first is None and len(ca) == len(cb) and len(ca) > 0
    if first is None and len(ca) != len(cb):
        first = {'line': min(len(ca), len(cb)) + 1, 'ref': 'calls %d' % len(ca), 'test': 'calls %d' % len(cb)}
    rep = {'calls_ref': len(ca), 'calls_test': len(cb), 'identical': same, 'kinds': dict(kinds), 'first': first,
           'verdict': 'PASS' if ok else 'FAIL', 'counters': nb, 'tol': tol}
    print('%s  svc4 calls %d/%d identical (%s)%s' % (rep['verdict'], same, len(ca),
          ' '.join('%s %d' % kv for kv in sorted(kinds.items())),
          '' if ok else '; first difference at call %d: ref "%s" test "%s"' % (first['line'], first['ref'][:160], first['test'][:160])))
    if js:
        with open(js, 'w') as f:
            json.dump(rep, f, indent=1)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
