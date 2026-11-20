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

Actors (trace v2, lane eng-host2): --actor SEL compares one hosted actor's block (the A lines) instead of
the T line. SEL is e=<list entry hex>, k=<alive-list index> or id=<enemy id hex>[#rank]. Against another re4ref
trace every actor field compares:
    p, a       as above (position, angles)
    mid, mf, ms  motion slot (Exxx: the actor's archive), frame, state; exact as above
    r          routine bytes, exact          hp   life, exact          be   be_flag, exact
    f          the actor's flags word (Ganado work flags; partner subFlags), exact
    aps        the actor's discrete hash (be_flag, stat, id, type, Mot_state, life), exact
    rc         the generator calls the actor made this tick, exact
    rng        the generator state at the end of the tick (the T line's), exact
Against an old logic trace only the position is recorded: the LP lines (decision-trace runs) give every alive
enemy's id and position every 4th tick, in alive-list order. The A actor is matched to the old record of the
same id at the same rank among that id's records (its rank in the reference's own alive list), so the two
lists must hold the same actors in the same order (the fixture creates them as the old run did).
An old trace recorded with LOGIC_TRACE_EM_FROM/TO (LE and LF lines, lane eng-e1b) gives every alive enemy every
tick: position, yaw (a: the yaw alone), motion frame and state, routine (r, from the stat word), life (hp),
be_flag (be), the discrete hash (aps, rebuilt from those fields) and the generator (rng, the LT line's); it has
no motion slot (mid), flags word (f) or per-actor generator calls (rc). The A actor is matched by id and rank.

Strict structure (lane eng-svc4, default; --lenient turns it off for sparse old-game logs): the comparison FAILS,
whatever the values, when
    a tick is missing          A's ticks must be one unbroken run (or the --expect-ticks LO:HI range) and B must have
                               every one of them (the selected actor on every tick A has it), no tick more;
    a field is missing         every compared field is on every compared tick of both traces; a field both traces mark
                               as not recorded ('-') at the same tick counts as compared and equal;
    a value is not finite      any NaN or infinity in a compared float field of either trace;
    a tick is repeated         two T lines with one tick (two A lines of one actor and tick, two LT lines);
    the counts are off         the compared ticks must equal --expect-count N when given, and every field's compared
                               count must equal the compared ticks.
The report lists every structure problem (kind, trace, tick, field) and the verdict is STRUCTURE (exit 1).

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


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


# which trace tokens carry which compared fields (strict structure)
T_TOKENS = {'p': 'p', 'a': 'a', 'mid': 'm', 'mf': 'm', 'ms': 'm', 'r': 'r', 'ps': 'ps', 'rng': 'rng', 'cam': 'cam'}
A_TOKENS = {'p': 'p', 'a': 'a', 'mid': 'm', 'mf': 'm', 'ms': 'm', 'r': 'r', 'hp': 'hp', 'be': 'be', 'f': 'f',
            'aps': 'ps', 'rc': 'rc'}
LT_TOKENS = {'p': 'p', 'a': 'a', 'mf': 'm', 'ms': 'm', 'ps': 'ps', 'rng': 'r'}


def token_state(kv, tokens):
    """-> (absent fields, not-recorded fields) of one trace line: a token missing from the line, or '-' / '~'."""
    absent, nr = set(), set()
    for f, tok in tokens.items():
        if tok not in kv:
            absent.add(f)
        elif kv[tok] in ('-', '') or '~' in kv[tok]:
            nr.add(f)
    return absent, nr


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


META = {}   # path -> {'dups': [...]}: what load() saw that the records cannot show (strict structure)


def load(path):
    """-> (kind, {tick: record}) with record keys p, a, mid, mf, ms, r, ps (list of acceptable), rng, cam.
    Strict structure: a record also carries '_absent' / '_nr' (fields missing / marked not recorded on its line);
    repeated lines go to META[path]['dups']."""
    recs = {}
    kind = None
    dups = []
    seen_a = set()
    META[path] = {'dups': dups}
    with open(path, errors='replace') as f:
        for line in f:
            if line.startswith('# re4ref trace'):
                kind = 're4ref'
                continue
            if line.startswith('T t=') and kind in (None, 're4ref'):
                kind = 're4ref'
                kv = parse_kv(line)
                t = int(kv['t'])
                if recs.get(t, {}).get('_T'):
                    dups.append(('T', t))
                    continue   # the first record stands; strict mode fails on the repeat
                r = {'_T': True}
                r['_absent'], r['_nr'] = token_state(kv, T_TOKENS)
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
                r.setdefault('actors', [])
                recs[t] = {**recs.get(t, {}), **r}
            elif line.startswith('A t=') and kind in (None, 're4ref'):
                kv = parse_kv(line)
                t = int(kv['t'])
                if (t, kv.get('e')) in seen_a:
                    dups.append(('A', t, kv.get('e')))
                    continue
                seen_a.add((t, kv.get('e')))
                ab, nr = token_state(kv, A_TOKENS)
                a = {'_absent': ab, '_nr': nr, 'k': int(kv['k']), 'id': kv['id'], 'e': kv['e'], 'p': floats(kv.get('p'), 3),
                     'a': floats(kv.get('a'), 3), 'r': kv.get('r'), 'hp': kv.get('hp'), 'be': kv.get('be'),
                     'f': kv.get('f'), 'aps': kv.get('ps'), 'rc': kv.get('rc')}
                m = kv.get('m', '-')
                if m != '-':
                    mid, mf, ms = m.split(',')
                    a['mid'], a['mf'], a['ms'] = mid, f32(mf), int(ms, 16)
                recs.setdefault(t, {}).setdefault('actors', []).append(a)
            elif line.startswith('R t=') and kind in (None, 're4ref'):
                kv = parse_kv(line)
                recs.setdefault(int(kv['t']), {})['rcalls'] = kv
            elif line.startswith('LP t='):
                # decision-trace runs: id:x,y,z of every alive enemy every 4th tick, alive-list order
                t = int(line.split()[1][2:])
                k = int(line.split()[2][2:]) if line.split()[2][2:].isdigit() else -1
                rec = recs.setdefault(t, {})
                if k < 0 or rec.get('lp_done'):
                    continue   # unowned, or a repeated tick: keep the first record
                if k == 0 and 'lp' in rec:
                    rec['lp_done'] = True
                    continue
                lst = rec.setdefault('lp', [])
                for tok in line.split()[3:]:
                    if ':' in tok:
                        i, xyz = tok.split(':', 1)
                        if i != 'ff':
                            lst.append({'id': i, 'p': floats(xyz, 3)})
            elif line.startswith('LE t='):
                # LOGIC_TRACE_EM_FROM/TO runs (lane eng-e1b): every alive enemy-list work every tick, alive-list
                # order: id, type, be_flag, stat (r_no_0..3 as a little-endian word), Mot_state, life (hex),
                # Mot_frame and position bits; the LF line after it carries the yaw
                kv = parse_kv(line)
                t, k = int(kv['t']), int(kv['k'])
                rec = recs.setdefault(t, {})
                if rec.get('le_done'):
                    continue
                lst = rec.setdefault('le', [])
                if k == 0 and lst:
                    rec['le_done'] = True   # a repeated tick: keep the first record
                    continue
                st = int(kv['stat'], 16)
                e = {'k': k, 'id': '%02x' % int(kv['id'], 16), 'p': floats(kv['pos'], 3), 'mf': f32(kv['mf']),
                     'ms': int(kv['ms'], 16), 'hp': str(s16(int(kv['hp'], 16))), 'be': '%08x' % int(kv['be'], 16),
                     'r': ''.join('%02x' % ((st >> (8 * i)) & 0xFF) for i in range(4))}
                e['aps'] = '%08x' % fnv([int(kv['be'], 16), st, int(kv['id'], 16), int(kv['type'], 16),
                                         int(kv['ms'], 16), int(kv['hp'], 16) & 0xFFFF])
                lst.append(e)
            elif line.startswith('LF t='):
                kv = parse_kv(line)
                rec = recs.get(int(kv['t']), {})
                lst = rec.get('le', [])
                if lst and lst[-1]['k'] == int(kv['k']) and 'a' not in lst[-1] and not rec.get('le_done'):
                    lst[-1]['a'] = [None, f32(kv['ay']), None]   # yaw only
            elif line.startswith('LT t='):
                kind = 'logic'
                kv = parse_kv(line)
                t = int(kv['t'])
                if recs.get(t, {}).get('_LT'):
                    dups.append(('LT', t))
                r = {'_LT': True}
                r['_absent'], r['_nr'] = token_state(kv, LT_TOKENS)
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
                if 'p' not in recs.get(t, {}):   # a repeated tick keeps its first record
                    recs[t] = {**r, **recs.get(t, {})}
                else:
                    recs[t]['_LT'] = True
    if kind is None:
        sys.exit(f'plays_right: {path}: no trace records')
    if kind == 're4ref':
        # strict structure (lane eng-svc5): a tick that has A or R lines but no T line lost its T line
        dups.extend(('noT', t) for t in sorted(recs) if not recs[t].get('_T'))
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
                d = max(angdiff_deg(x, y) for x, y in zip(av, bv) if x is not None and y is not None)
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


def finite(v):
    if isinstance(v, float):
        return math.isfinite(v)
    if isinstance(v, list):
        return all(finite(x) for x in v)
    return True


def structure(A, B, fields, offset, window, expect_range, expect_count, dups_a, dups_b):
    """Strict structure (see the module doc): -> list of problems, each {kind, trace, tick, field, detail}."""
    probs = []

    def add(kind, trace, tick=None, field=None, detail=''):
        probs.append({'kind': kind, 'trace': trace, 'tick': tick, 'field': field, 'detail': detail})
    for d in dups_a:
        add('missing tick' if d[0] == 'noT' else 'duplicate tick', 'A', d[1], None,
            'no T line' if d[0] == 'noT' else ' '.join(str(x) for x in d))
    for d in dups_b:
        add('missing tick' if d[0] == 'noT' else 'duplicate tick', 'B', d[1], None,
            'no T line' if d[0] == 'noT' else ' '.join(str(x) for x in d))
    ta = sorted(t for t in A if not window or window[0] <= t <= window[1])
    tb = sorted(t - offset for t in B if not window or window[0] <= t - offset <= window[1])
    if expect_range:
        want = list(range(expect_range[0], expect_range[1] + 1))
    else:
        want = list(range(ta[0], ta[-1] + 1)) if ta else []
    sa, sb, sw = set(ta), set(tb), set(want)
    for t in sorted(sw - sa):
        add('missing tick', 'A', t)
    for t in sorted(sw - sb):
        add('missing tick', 'B', t + offset)
    for t in sorted(sa - sw):
        add('extra tick', 'A', t)
    for t in sorted(sb - sw):
        add('extra tick', 'B', t + offset)
    both = sorted(sa & sb & sw)
    if not both:
        add('tick count', 'A/B', None, None, 'no tick in both traces')
    if expect_count is not None and len(both) != expect_count:
        add('tick count', 'A/B', None, None, 'compared %d, expected %d' % (len(both), expect_count))
    counts = {f: 0 for f in fields}
    for t in both:
        a, b = A[t], B[t + offset]
        for f in fields:
            na, nb = f in a.get('_nr', ()), f in b.get('_nr', ())
            ma = f in a.get('_absent', ()) or ('_absent' not in a and a.get(f) is None)
            mb = f in b.get('_absent', ()) or ('_absent' not in b and b.get(f) is None)
            if ma:
                add('missing field', 'A', t, f)
            if mb:
                add('missing field', 'B', t + offset, f)
            if ma or mb:
                continue
            if na != nb:
                add('missing field', 'A' if na else 'B', t if na else t + offset, f, 'not recorded on one side only')
                continue
            if not na and not (finite(a.get(f)) and finite(b.get(f))):
                add('non-finite value', 'A' if not finite(a.get(f)) else 'B', t, f,
                    '%s / %s' % (fmt(a.get(f)), fmt(b.get(f))))
                continue
            counts[f] += 1
    for f in fields:
        if counts[f] != len(both):
            add('field count', 'A/B', None, f, 'compared on %d of %d ticks' % (counts[f], len(both)))
    return probs


def fmt(v):
    if isinstance(v, list):
        return '(' + ', '.join(f'{x:.4f}' if isinstance(x, float) else str(x) for x in v) + ')'
    if isinstance(v, float):
        return f'{v:.4f}'
    return str(v)


DEFAULT_TOL = {'pos': 1.0, 'ang_deg': 1.0, 'frame': 0.0, 'cam': 1.0, 'cam_fovy_deg': 0.1}
ACTOR_FIELDS = 'p,a,mid,mf,ms,r,hp,be,f,aps,rc,rng'


def pick(actors, sel):
    """The actor of an A list that SEL names (e=, k=, id=[#rank]); -> (record, its rank among its id)."""
    key, _, val = sel.partition('=')
    rank_want = None
    if key == 'id' and '#' in val:
        val, r = val.split('#', 1)
        rank_want = int(r)
    seen = {}
    for a in actors:
        rank = seen.get(a['id'], 0)
        seen[a['id']] = rank + 1
        if key == 'e' and int(a['e'], 16) == int(val, 16):
            return a, rank
        if key == 'k' and a['k'] == int(val):
            return a, rank
        if key == 'id' and int(a['id'], 16) == int(val, 16) and (rank_want is None or rank == rank_want):
            return a, rank
    return None, None


def actor_views(A, B, kb, sel, offset):
    """{tick: fields} for the selected actor in A, and its counterpart in B (same SEL in a re4ref trace; the
    same id at the same rank in an old trace's LP list)."""
    va, vb = {}, {}
    for t, r in A.items():
        a, rank = pick(r.get('actors', []), sel)
        if a is None:
            continue
        va[t] = dict(a, rng=r.get('rng'))
        if r.get('rng') is None and '_absent' in a:
            va[t]['_absent'] = a['_absent'] | {'rng'}
        b = B.get(t + offset)
        if not b:
            continue
        if kb == 're4ref':
            x, _ = pick(b.get('actors', []), sel)
            if x is not None:
                vb[t + offset] = dict(x, rng=b.get('rng'))
                if b.get('rng') is None and '_absent' in x:
                    vb[t + offset]['_absent'] = x['_absent'] | {'rng'}
        elif 'le' in b:
            # LE runs: every field the logic trace records (no motion slot, flags or per-actor generator calls)
            same = [x for x in b['le'] if x['id'] == a['id']]
            if rank < len(same):
                vb[t + offset] = dict(same[rank], rng=b.get('rng'))
        elif 'lp' in b:
            same = [x for x in b['lp'] if x['id'] == a['id']]
            if rank < len(same):
                vb[t + offset] = {'p': same[rank]['p']}
    return va, vb


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--tolerances', help='JSON file: pos, ang_deg, frame, cam, cam_fovy_deg')
    ap.add_argument('--offset', type=int, default=0, help="B's tick = A's tick + offset")
    ap.add_argument('--window', help='LO:HI, A ticks')
    ap.add_argument('--fields', help='default p,a,mid,mf,ms,r,ps,rng,cam (T line) or ' + ACTOR_FIELDS + ' (--actor)')
    ap.add_argument('--actor', help='compare one actor block (A lines): e=<entry>, k=<index> or id=<id>[#rank]')
    ap.add_argument('--json', help='write the report as JSON')
    ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--lenient', action='store_true',
                    help='the old reader: skip missing ticks and fields (sparse old-game logs); no structure check')
    ap.add_argument('--expect-ticks', help='LO:HI, the tick set A and B must both hold (default: A first to last)')
    ap.add_argument('--expect-count', type=int, help='the number of compared ticks the comparison must reach')
    args = ap.parse_args()
    tol = dict(DEFAULT_TOL)
    if args.tolerances:
        with open(args.tolerances) as f:
            tol.update({k: v for k, v in json.load(f).items() if not k.startswith('_')})
    window = tuple(int(x) for x in args.window.split(':')) if args.window else None
    fields = [f.strip() for f in (args.fields or (ACTOR_FIELDS if args.actor else 'p,a,mid,mf,ms,r,ps,rng,cam'))
              .split(',') if f.strip()]
    ka, A = load(args.a)
    kb, B = load(args.b)
    dups_a, dups_b = META[args.a]['dups'], META[args.b]['dups']   # any repeated line is a fault of the trace
    if args.actor:
        if ka != 're4ref':
            sys.exit('plays_right: --actor needs a re4ref trace as A')
        A, B = actor_views(A, B, kb, args.actor, args.offset)
        if not A:
            sys.exit(f'plays_right: no actor {args.actor} in {args.a}')
    res, first, compared = compare(A, B, tol, args.offset, window, fields)
    probs = []
    if not args.lenient:
        er = tuple(int(x) for x in args.expect_ticks.split(':')) if args.expect_ticks else None
        probs = structure(A, B, fields, args.offset, window, er, args.expect_count, dups_a, dups_b)
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
            us = [max(ulps(x, y) for x, y in zip(as_list(r[3]), as_list(r[4])) if x is not None and y is not None)
                  for r in rows]
            summary[f]['bit_identical'] = sum(1 for u in us if u == 0)
            summary[f]['max_ulps'] = max(us)
    verdict = 'PASS' if first is None and compared else ('NO-OVERLAP' if not compared else 'DIVERGED')
    if probs and verdict == 'PASS':
        verdict = 'STRUCTURE'
    report = {'a': args.a, 'b': args.b, 'kinds': [ka, kb], 'offset': args.offset, 'window': window,
              'tolerances': tol, 'ticks_compared': compared, 'verdict': verdict, 'summary': summary,
              'strict': not args.lenient, 'structure_problems': len(probs), 'structure': probs[:200]}
    if first:
        t, f, av, bv, d = first
        report['first_divergence'] = {'tick': t, 'b_tick': t + args.offset, 'field': f, 'a': fmt(av),
                                      'b': fmt(bv), 'diff': d}
        # the agreement window: compared ticks before the first divergence
        report['agreement_ticks'] = sum(1 for tt in sorted(A) if tt < t and (tt + args.offset) in B
                                        and (not window or window[0] <= tt <= window[1]))
        # inside that window: ticks whose position is bit-identical, and the largest position difference
        rows = [r for r in res.get('p', []) if r[0] < t]
        if rows:
            report['agreement_p_bit_identical'] = sum(1 for r in rows if all(ulps(x, y) == 0 for x, y in zip(r[3], r[4])))
            report['agreement_p_max'] = max(r[1] for r in rows)
            report['agreement_last_tick'] = max(r[0] for r in rows)
    if not args.quiet:
        print(f'{args.a} ({ka}) vs {args.b} ({kb}), offset {args.offset}: {compared} ticks compared, {verdict}')
        if first:
            fd = report['first_divergence']
            print(f"  first divergence: tick {fd['tick']} (B {fd['b_tick']}) field {fd['field']}: "
                  f"A {fd['a']} B {fd['b']} diff {fd['diff']}")
        if probs:
            kinds = {}
            for pr in probs:
                kinds[pr['kind']] = kinds.get(pr['kind'], 0) + 1
            p0 = probs[0]
            print('  structure: %d problems (%s); first: %s' % (
                len(probs), ', '.join('%s %d' % kv for kv in sorted(kinds.items())),
                ' '.join(str(p0[k]) for k in ('kind', 'trace', 'tick', 'field', 'detail') if p0[k] not in (None, ''))))
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
    sys.exit(0 if verdict == 'PASS' and not probs else 1)


if __name__ == '__main__':
    main()
