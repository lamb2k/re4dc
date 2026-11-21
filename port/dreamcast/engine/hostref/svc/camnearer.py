#!/usr/bin/env python3
"""camnearer.py: where two arms of the engine's camera differ, which is nearer the PC reference (lane eng-e1l).

    camnearer.py <ref dir> <arm A dir> <arm B dir>

Each dir holds a cam.txt (camengine.py for the engine arms, svc4_dump.cpp for the reference). On every tick where A and
B differ (any eye, target, roll or fov bit), the distance of each to the reference is the largest eye or target
coordinate difference. PASS when B is at least as near as A on every such tick (B's change moves the camera toward the
reference wherever it moves it at all); FAIL otherwise, naming the first tick where B is farther. Used with A = the
lab arm ZCLIP0 (the game's distances zero, the camera every E1 image had) and B = the image as it is; the control
swaps them and must FAIL. Exit 0 PASS, 1 FAIL, 2 a missing log or no tick where the arms differ.
"""
import sys


def load(d):
    out = {}
    with open(d + '/cam.txt') as f:
        for ln in f:
            t = ln.split()
            if t and t[0] != 'R':
                out[int(t[0])] = [float(x) for x in t[1:9]]
    return out


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    try:
        r, a, b = (load(d) for d in sys.argv[1:4])
    except OSError as e:
        print('camnearer: ERROR %s' % e)
        return 2
    ticks = [t for t in sorted(r) if t in a and t in b and a[t] != b[t]]
    if not ticks:
        print('camnearer: ERROR the arms do not differ on any tick')
        return 2
    dist = lambda x, t: max(abs(x[t][i] - r[t][i]) for i in range(6))
    farther = [t for t in ticks if dist(b, t) > dist(a, t)]
    wa = max(ticks, key=lambda t: dist(a, t))
    wb = max(ticks, key=lambda t: dist(b, t))
    msg = ('%s  %d ticks differ (%d..%d); B nearer or equal on %d; worst A %.3g units (tick %d), worst B %.3g units (tick %d)' % (
        'FAIL' if farther else 'PASS', len(ticks), ticks[0], ticks[-1], len(ticks) - len(farther), dist(a, wa), wa,
        dist(b, wb), wb))
    if farther:
        t = farther[0]
        x = max(farther, key=lambda t: dist(b, t) - dist(a, t))
        msg += '; first farther: tick %d (A %.3g, B %.3g); most farther: tick %d by %.3g units' % (
            t, dist(a, t), dist(b, t), x, dist(b, x) - dist(a, x))
    print(msg)
    return 1 if farther else 0


if __name__ == '__main__':
    sys.exit(main())
