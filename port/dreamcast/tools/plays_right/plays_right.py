#!/usr/bin/env python3
"""plays_right.py: compare two per-tick state traces of Leon (player and camera) with per-field tolerances.

    plays_right.py A.trace B.trace --tolerances tol.json [--offset N] [--window LO:HI] [--json out.json]
                                   [--fields p,a,mid,mf,ms,r,ps,rng,cam] [--quiet]

A and B are either re4ref traces (hostref, "# re4ref trace v1") or the old game's logic-trace log (the
run-output.txt of a LOGIC_TRACE=1 run: "LT t=..." lines). B's tick t is compared with A's tick t - N
(--offset N: B starts N ticks later in its own numbering). --window limits A's ticks.

Fields (present in both traces, or skipped with a note):
    p    position x, y, z         |dx|,|dy|,|dz| <= pos (units)             LT p=, re4ref p=
    a    yaw (and pitch, roll)    wrapped difference <= ang_deg (degrees)    LT a=, re4ref a=
    mid  motion id                exact                                      re4ref m= (archive slot)
    mf   motion frame             |d| <= frame (frames)                      LT m= frame, re4ref m=
    ms   motion state             exact                                      LT m= /state, re4ref m=
    r    routine (r_no_0..3)      exact                                      re4ref r=
    ps   discrete hash            exact (see "ps" below)                     LT ps=, re4ref ps= / psm=
    rng  generator state          exact                                      LT r=, re4ref rng=
    cam  camera eye and target    |d| <= cam (units), fovy <= cam_fovy_deg   re4ref cam=
A field a trace marks as not recorded ('~' in the logic trace, '-' in re4ref) is not compared at that tick.

ps: the logic trace's FNV of be_flag, stat (r_no_0..3), id, type and Mot_state. re4ref writes it for its own
be_flag (ps=) and with the draw pass's marker 0x08000000 set (psm=); against a logic trace either matches,
because the reference has no draw pass (tolerance "ps_draw_bits": the be_flag bits the draw pass owns).

Exit status: 0 when every compared tick is within tolerance, 1 on a divergence, 2 on a usage error.
The report names the first divergence (tick, field, both values, the difference) and a summary per field:
ticks compared, ticks over tolerance, the largest difference and where it is.
"""
import argparse
import json
import math
import struct
import sys


def f32(hexbits):
    return struct.unpack('<f', struct.pack('<I', int(hexbits, 16)))[0]


def fnv(words):
    h = 2166136261
    for w in words:
        h = ((h ^ (w & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h


def parse_kv(line):
    out = {}
    for tok in line.split()[1:]:
        if '=' in tok:
            k, v = tok.split('=', 1)
            out[k] = v
    return out


def floats(v, n):
    if v in ('-', None) or '~' in v:
        return None
    parts = v.split(',')
    if len(parts) < n:
        return None
    return [f32(x) for x in parts[:n]]


def load(path):
    """-> (kind, {tick: record}) with record keys p, a, mid, mf, ms, r, ps (list of acceptable), rng, cam."""
    recs = {}
    kind = None
    with open(path, errors='replace') as f:
        for line in f:
            if line.startswith('# re4ref trace'):
                kind = 're4ref'
                continue
            if line.startswith('T t=') and kind in (None, 're4ref'):
                kind = 're4ref'
                kv = parse_kv(line)
                t = int(kv['t'])
                r = {}
                r['in'] = kv.get('in')
                r['p'] = floats(kv.get('p'), 3)
                r['a'] = floats(kv.get('a'), 3)
                m = kv.get('m', '-')
                if m != '-':
                    mid, mf, ms = m.split(',')
                    r['mid'] = mid
                    r['mf'] = f32(mf)
                    r['ms'] = int(ms, 16)
                if kv.get('r', '-') != '-':
                    r['r'] = kv['r']
                if kv.get('ps', '-') != '-':
                    r['ps'] = [kv['ps'], kv.get('psm', kv['ps'])]
                if 'rng' in kv:
                    r['rng'] = kv['rng'].split('/')[0]
                cam = floats(kv.get('cam'), 7)
                if cam:
                    r['cam'] = cam
                r['stub'] = kv.get('stub')
                recs[t] = r
            elif line.startswith('LT t='):
                kind = 'logic'
                kv = parse_kv(line)
                t = int(kv['t'])
                r = {}
                r['p'] = floats(kv.get('p'), 3)
                r['a'] = floats(kv.get('a'), 3)
                m = kv.get('m', '~')
                if '~' not in m:
                    mf, ms = m.split('/')
                    r['mf'] = f32(mf)
                    r['ms'] = int(ms)
                if '~' not in kv.get('ps', '~'):
                    r['ps'] = [kv['ps']]
                if 'r' in kv and '~' not in kv['r']:
                    r['rng'] = kv['r']
                r['rm'] = kv.get('rm')
                recs.setdefault(t, r)   # a repeated tick keeps its first record
    if kind is None:
        sys.exit(f'plays_right: {path}: no trace records')
    return kind, recs


def ulps(x, y):
    """Distance between two floats in single-precision steps (sign-magnitude order)."""
    def key(f):
        i = struct.unpack('<i', struct.pack('<f', f))[0]
        return i if i >= 0 else -(i & 0x7FFFFFFF)
    return abs(key(x) - key(y))


def angdiff_deg(a, b):
    d = (a - b + math.pi) % (2 * math.pi) - math.pi
    return abs(math.degrees(d))


def compare(A, B, tol, offset, window, fields):
    """Per field: list of (tick, diff, over, aval, bval). Returns (results, first, notes)."""
    res = {f: [] for f in fields}
    first = None
    ticks = sorted(A)
    if window:
        ticks = [t for t in ticks if window[0] <= t <= window[1]]
    compared = 0
    for t in ticks:
        a = A[t]
        b = B.get(t + offset)
        if b is None:
            continue
        compared += 1
        for f in fields:
            av, bv = a.get(f), b.get(f)
            if av is None or bv is None:
                continue
            if f == 'p':
                d = max(abs(x - y) for x, y in zip(av, bv))
                over = d > tol['pos']
            elif f == 'a':
                d = max(angdiff_deg(x, y) for x, y in zip(av, bv))
                over = d > tol['ang_deg']
            elif f == 'mf':
                d = abs(av - bv)
                over = d > tol['frame']
            elif f == 'cam':
                d = max(abs(x - y) for x, y in zip(av[:6], bv[:6]))
                dfov = abs(av[6] - bv[6])
                over = d > tol['cam'] or dfov > tol['cam_fovy_deg']
            elif f == 'ps':
                d = 0 if set(av) & set(bv) else 1
                over = d != 0
            else:   # mid, ms, r, rng: exact
                d = 0 if av == bv else 1
                over = d != 0
            res[f].append((t, d, over, av, bv))
            if over and first is None:
                first = (t, f, av, bv, d)
    return res, first, compared


def fmt(v):
    if isinstance(v, list):
        return '(' + ', '.join(f'{x:.4f}' if isinstance(x, float) else str(x) for x in v) + ')'
    if isinstance(v, float):
        return f'{v:.4f}'
    return str(v)


DEFAULT_TOL = {'pos': 1.0, 'ang_deg': 1.0, 'frame': 0.0, 'cam': 1.0, 'cam_fovy_deg': 0.1}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--tolerances', help='JSON file: pos, ang_deg, frame, cam, cam_fovy_deg')
    ap.add_argument('--offset', type=int, default=0, help="B's tick = A's tick + offset")
    ap.add_argument('--window', help='LO:HI, A ticks')
    ap.add_argument('--fields', default='p,a,mid,mf,ms,r,ps,rng,cam')
    ap.add_argument('--json', help='write the report as JSON')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    tol = dict(DEFAULT_TOL)
    if args.tolerances:
        with open(args.tolerances) as f:
            tol.update({k: v for k, v in json.load(f).items() if not k.startswith('_')})
    window = tuple(int(x) for x in args.window.split(':')) if args.window else None
    fields = [f.strip() for f in args.fields.split(',') if f.strip()]
    ka, A = load(args.a)
    kb, B = load(args.b)
    res, first, compared = compare(A, B, tol, args.offset, window, fields)
    summary = {}
    for f in fields:
        rows = res[f]
        if not rows:
            summary[f] = {'compared': 0, 'note': 'not in both traces'}
            continue
        worst = max(rows, key=lambda r: r[1])
        over = [r for r in rows if r[2]]
        summary[f] = {'compared': len(rows), 'over': len(over), 'max': worst[1], 'max_at': worst[0],
                      'first_over': over[0][0] if over else None}
        if f in ('p', 'a', 'mf', 'cam'):
            # float exactness: ticks whose values are bit-identical, and the largest distance in float steps
            def as_list(v):
                return v if isinstance(v, list) else [v]
            us = [max(ulps(x, y) for x, y in zip(as_list(r[3]), as_list(r[4]))) for r in rows]
            summary[f]['bit_identical'] = sum(1 for u in us if u == 0)
            summary[f]['max_ulps'] = max(us)
    verdict = 'PASS' if first is None and compared else ('NO-OVERLAP' if not compared else 'DIVERGED')
    report = {'a': args.a, 'b': args.b, 'kinds': [ka, kb], 'offset': args.offset, 'window': window,
              'tolerances': tol, 'ticks_compared': compared, 'verdict': verdict, 'summary': summary}
    if first:
        t, f, av, bv, d = first
        report['first_divergence'] = {'tick': t, 'b_tick': t + args.offset, 'field': f, 'a': fmt(av),
                                      'b': fmt(bv), 'diff': d}
        # the agreement window: compared ticks before the first divergence
        report['agreement_ticks'] = sum(1 for tt in sorted(A) if tt < t and (tt + args.offset) in B
                                        and (not window or window[0] <= tt <= window[1]))
    if not args.quiet:
        print(f'{args.a} ({ka}) vs {args.b} ({kb}), offset {args.offset}: {compared} ticks compared, {verdict}')
        if first:
            fd = report['first_divergence']
            print(f"  first divergence: tick {fd['tick']} (B {fd['b_tick']}) field {fd['field']}: "
                  f"A {fd['a']} B {fd['b']} diff {fd['diff']}")
        for f in fields:
            s = summary[f]
            if s['compared'] == 0:
                print(f'  {f:4s} {s["note"]}')
            else:
                mx = s['max']
                mxs = f'{mx:.4f}' if isinstance(mx, float) else str(mx)
                bits = (f" bit-identical {s['bit_identical']} max {s['max_ulps']} ulps" if 'max_ulps' in s else '')
                print(f"  {f:4s} compared {s['compared']:5d} over {s['over']:5d} max {mxs} at {s['max_at']}"
                      + (f" first over {s['first_over']}" if s['first_over'] is not None else '') + bits)
    if args.json:
        with open(args.json, 'w') as f:
            json.dump(report, f, indent=1)
    sys.exit(0 if verdict == 'PASS' else 1)


if __name__ == '__main__':
    main()
