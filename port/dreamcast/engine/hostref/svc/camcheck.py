#!/usr/bin/env python3
"""camcheck.py: the camera service against the original camera code on the same inputs (lane eng-e1j, H-016.1).

    camcheck.py <ref dir> <test dir> [--pos U] [--deg D] [--json out.json] [--quiet]

Each dir holds cam.txt (svc4_dump.cpp, re4ref odump = the original camera units, native = the engine's camera
service): one line a CameraMove, "tick eye.x eye.y eye.z target.x target.y target.z roll fov area cut routine blend"
(roll in radians, fov in degrees), and the exercise's rail lines "R tick ..." when one ran. The two runs must hold the
same lines (ticks in the same order); on each the controller's decisions (area, cut, routine, blend frames left) must be
equal and eye and target within U units on every axis (default 0.01), roll and fov within D degrees (default 0.01).
Exit 0 PASS, 1 FAIL (the first failing tick is named), 2 a missing or empty log, or the two logs of different length.
"""
import argparse
import json
import math
import sys


def load(d):
    rows = []
    try:
        with open(d + '/cam.txt') as f:
            for ln in f:
                t = ln.split()
                if not t:
                    continue
                kind = 'R' if t[0] == 'R' else 'C'
                if kind == 'R':
                    t = t[1:]
                if len(t) < 9:
                    continue
                rows.append((kind, int(t[0]), [float(x) for x in t[1:9]], [int(x) for x in t[9:13]]))
    except OSError:
        return None
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref')
    ap.add_argument('test')
    ap.add_argument('--pos', type=float, default=0.01)
    ap.add_argument('--deg', type=float, default=0.01)
    ap.add_argument('--json')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    r, t = load(a.ref), load(a.test)
    if not r or not t:
        print('camcheck: ERROR no cam.txt or an empty one (%s, %s)' % (a.ref, a.test))
        return 2
    out = {'ref': a.ref, 'test': a.test, 'tol_pos': a.pos, 'tol_deg': a.deg, 'lines': [len(r), len(t)]}
    if len(r) != len(t):
        print('camcheck: ERROR %d lines against %d' % (len(r), len(t)))
        return 2
    worst = {'eye': 0.0, 'target': 0.0, 'roll_deg': 0.0, 'fov_deg': 0.0}
    worst_at = {}
    first = None
    decisions_diff = 0
    rails = 0
    for (ka, ta, va, da), (kb, tb, vb, db) in zip(r, t):
        if ka != kb or ta != tb:
            first = first or {'tick': ta, 'why': 'line order (%s %d against %s %d)' % (ka, ta, kb, tb)}
            break
        rails += ka == 'R'
        if ka == 'C' and da != db:
            decisions_diff += 1
            first = first or {'tick': ta, 'why': 'decisions %s against %s (area, cut, routine, blend)' % (da, db)}
        de = max(abs(va[i] - vb[i]) for i in range(3))
        dt = max(abs(va[i] - vb[i]) for i in range(3, 6))
        dr = abs(va[6] - vb[6]) * 180.0 / math.pi
        df = abs(va[7] - vb[7])
        for k, v in (('eye', de), ('target', dt), ('roll_deg', dr), ('fov_deg', df)):
            if not v <= worst[k]:
                worst[k] = v
                worst_at[k] = ta
        bad = []
        if not de <= a.pos:
            bad.append('eye %.4g' % de)
        if not dt <= a.pos:
            bad.append('target %.4g' % dt)
        if not dr <= a.deg:
            bad.append('roll %.4g deg' % dr)
        if not df <= a.deg:
            bad.append('fov %.4g deg' % df)
        if bad and not first:
            first = {'tick': ta, 'why': ('rail ' if ka == 'R' else '') + ', '.join(bad)}
    out.update({'worst': worst, 'worst_tick': worst_at, 'first': first, 'decision_lines_different': decisions_diff,
                'rail_lines': rails, 'pass': first is None})
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(out, f, indent=1)
    msg = '%s  %d lines (%d rail); worst eye %.3g target %.3g units, roll %.3g fov %.3g deg; tolerance %g units %g deg' % (
        'PASS' if first is None else 'FAIL', len(r), rails, worst['eye'], worst['target'], worst['roll_deg'], worst['fov_deg'],
        a.pos, a.deg)
    if first:
        msg += '; first: tick %d %s' % (first['tick'], first['why'])
    print(msg)
    return 0 if first is None else 1


if __name__ == '__main__':
    sys.exit(main())
