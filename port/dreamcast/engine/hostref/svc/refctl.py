#!/usr/bin/env python3
"""refctl.py: the measurements of the reference controls (lane eng-e1o, H-017.8; svc/refctl.sh runs them).

    refctl.py draws <reference trace> <old trace> --tick T --extra N
        The generator calls of two re4ref traces of the same fixture (trace v2 R lines: other, player, camera, objects,
        creation and each actor's). PASS when they agree on every tick before T and the old trace makes N more calls
        than the reference at tick T (the stated finding); FAIL otherwise. The first differing tick and the calls of each
        side are printed. Exit 0 PASS, 1 FAIL, 2 a missing trace or no R line.
    refctl.py rail <cam dir>
        The camrail exercise's rail lines (cam.txt "R" lines): how many distinct eye/target pairs. Prints STUCK when every
        rail line holds the first line's eye and target (the rail evaluated at its first key whatever the search found),
        MOVES otherwise. Exit 0 STUCK, 1 MOVES, 2 no rail line.
"""
import re
import sys


def r_lines(path):
    out = {}
    try:
        with open(path) as f:
            for ln in f:
                if not ln.startswith('R t='):
                    continue
                m = re.match(r'R t=(\d+) (.*)$', ln.strip())
                if not m:
                    continue
                calls = [int(x) for x in re.findall(r'-?\d+', m.group(2))]
                out[int(m.group(1))] = (m.group(2), sum(calls))
    except OSError:
        return None
    return out


def draws(a, b, tick, extra):
    ra, rb = r_lines(a), r_lines(b)
    if not ra or not rb:
        print('ERROR no R lines (%s: %s, %s: %s)' % (a, bool(ra), b, bool(rb)))
        return 2
    first = None
    for t in sorted(set(ra) | set(rb)):
        if ra.get(t) != rb.get(t):
            first = t
            break
    if first is None:
        print('FAIL the two traces make the same generator calls on every tick (%d ticks): no difference at tick %d' % (len(ra), tick))
        return 1
    ca, cb = ra.get(first, ('-', 0)), rb.get(first, ('-', 0))
    msg = 'first tick %d: reference %d calls (%s), old %d calls (%s), %+d' % (first, ca[1], ca[0], cb[1], cb[0], cb[1] - ca[1])
    ok = first == tick and cb[1] - ca[1] == extra
    print(('PASS ' if ok else 'FAIL ') + msg + ('' if ok else ' (stated: tick %d, %+d)' % (tick, extra)))
    return 0 if ok else 1


def rail(d):
    rows = []
    try:
        with open(d + '/cam.txt') as f:
            for ln in f:
                t = ln.split()
                if t and t[0] == 'R' and len(t) >= 9:
                    rows.append((int(t[1]), tuple(t[2:8])))
    except OSError:
        pass
    if not rows:
        print('ERROR no rail lines in %s/cam.txt' % d)
        return 2
    distinct = len({r[1] for r in rows})
    stuck = all(r[1] == rows[0][1] for r in rows)
    print('%s %d rail lines (ticks %d..%d), %d distinct eye/target; first eye %s target %s' % (
        'STUCK' if stuck else 'MOVES', len(rows), rows[0][0], rows[-1][0], distinct, ','.join(rows[0][1][:3]),
        ','.join(rows[0][1][3:6])))
    return 0 if stuck else 1


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == 'draws':
        tick = int(sys.argv[sys.argv.index('--tick') + 1]) if '--tick' in sys.argv else -1
        extra = int(sys.argv[sys.argv.index('--extra') + 1]) if '--extra' in sys.argv else 0
        return draws(sys.argv[2], sys.argv[3], tick, extra)
    if len(sys.argv) == 3 and sys.argv[1] == 'rail':
        return rail(sys.argv[2])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
