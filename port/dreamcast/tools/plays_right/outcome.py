#!/usr/bin/env python3
"""outcome.py <reference run-output> <engine serial> [--offset 184] [--to 900] [--clear-tol 0.15] [--json out]

The outcome check (lane eng-ref): a second line of evidence where fixed pad scripts drift. Both sides run the same
closed-loop player (autoplay/autoplay.inc: aim at the nearest Ganado, fire when on target) from the same start; this
compares what came out of the fight, not tick-by-tick positions:

  kills       how many, and their order (actors named by spawn order: the order of first appearance, then rank)
  damage      the damage of every hit (life before - after), as a sorted list, and the per-actor sum
  spawns      the spawn sequence (type, starting life)
  waves       the room script's wave reports, in order; room events (the game held: Stop_flg 0x80400100) in order
  stuck       a living Ganado whose position and motion frame do not change for STUCK ticks outside an event, or
              Leon with an unchanged motion frame for STUCK ticks; it fails when only one side has it (some village
              Ganados wait without animating, in both) or when Leon is frozen
  clear time  the tick of the last kill both sides reach, within --clear-tol (fraction) or --clear-abs ticks

Reference: the old game's logic trace (LE lines, Frame_cnt ticks; tick k of the engine = reference tick offset + k).
Engine: the fight image's serial (LE lines with e=<entry>, its wave reports). Either side may be an old-game trace
(--ref-as-engine / --as-old) for the checker's own controls. PASS needs every row equal and the clear time within.
"""
import argparse, json, re, struct, sys

STUCK = 300


def f(h):
    return struct.unpack('<f', struct.pack('<I', int(h, 16)))[0]


def kv(line):
    return dict(x.split('=', 1) for x in line.split()[1:] if '=' in x)


def read(path, off, to, old):
    """per tick: Ganado list (key, type, hp, pos, mf); Leon (pos, mf); held flag; waves."""
    le, lt, waves, last_t = {}, {}, [], None
    pend = None
    for l in open(path, encoding='latin-1'):
        if l.startswith('LE t='):
            d = kv(l); t = int(d['t']) - (off if old else 0)
            if t < 0 or t > to or d.get('id') not in ('15', '10'): continue
            key = d.get('a') if old else 'e%s' % d.get('e', d.get('k'))
            le.setdefault(t, []).append(dict(key=key, k=int(d['k']), type=d['type'], hp=int(d['hp'], 16),
                                             p=tuple(f(x) for x in d['pos'].split(',')), mf=d['mf']))
        elif l.startswith('LT t='):
            d = kv(l); t = int(d['t']) - (off if old else 0); last_t = int(d['t'])
            if t < 0 or t > to: continue
            r = lt.setdefault(t, {})
            r['p'] = d['p']; r['m'] = d.get('m', '')
            if 'sp' in d: r['sp'] = int(d['sp'], 16)
        elif l.startswith('LL t='):
            d = kv(l); t = int(d['t']) - (off if old else 0)
            if 0 <= t <= to and 'sp' in d: lt.setdefault(t, {})['sp'] = int(d['sp'], 16)
        elif 'ps2en: r101 wave' in l:
            n = re.search(r'wave (\d+)', l).group(1)
            if old:
                if last_t is not None and 0 <= last_t + 1 - off <= to: waves.append((last_t + 1 - off, n))
            else:
                pend = n
        elif pend and '(tick' in l:
            t = int(re.search(r'tick (\d+)', l).group(1))
            if t <= to: waves.append((t, pend))
            pend = None
    return le, lt, waves


def outcome(le, lt, waves, to):
    ident, prev, spawns, hits, kills, stuck = {}, {}, [], [], [], []
    still = {}
    held_prev, events = False, []
    leon_m, leon_since = None, 0
    for t in range(0, to + 1):
        sp = lt.get(t, {}).get('sp')
        held = sp is not None and (sp & 0x80400100) == 0x80400100
        if sp is not None and held != held_prev:
            events.append(('start' if held else 'end', t)); held_prev = held
        cur = {}
        for a in sorted(le.get(t, []), key=lambda a: a['k']):
            if a['key'] not in ident:
                ident[a['key']] = len(ident); spawns.append((t, a['type'], a['hp']))
            i = ident[a['key']]; cur[i] = a
            if i in prev and a['hp'] < prev[i]['hp']:
                hits.append((t, i, prev[i]['hp'] - a['hp']))
                if a['hp'] <= 0 < prev[i]['hp']: kills.append((t, i))
            if a['hp'] > 0 and not held:
                s = (a['p'], a['mf'])
                if i in still and still[i][0] == s:
                    if t - still[i][1] == STUCK: stuck.append(('ganado', i, still[i][1]))
                else:
                    still[i] = (s, t)
        prev = cur
        m = lt.get(t, {}).get('m')
        if m is not None and not held:
            if m != leon_m: leon_m, leon_since = m, t
            elif t - leon_since == STUCK: stuck.append(('leon', -1, leon_since))
    return dict(spawns=spawns, hits=hits, kills=kills, waves=waves, events=events, stuck=stuck)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref'); ap.add_argument('eng')
    ap.add_argument('--offset', type=int, default=184)
    ap.add_argument('--to', type=int, default=900)
    ap.add_argument('--clear-tol', type=float, default=0.15)
    ap.add_argument('--clear-abs', type=int, default=60)
    ap.add_argument('--as-old', action='store_true', help='the second trace is an old-game trace too')
    ap.add_argument('--json')
    a = ap.parse_args()
    R = outcome(*read(a.ref, a.offset, a.to, True), a.to)
    E = outcome(*read(a.eng, a.offset, a.to, a.as_old), a.to)
    rows = []
    def row(name, r, e, ok):
        rows.append(dict(check=name, reference=r, engine=e, verdict='PASS' if ok else 'FAIL'))
    rk, ek = [i for _, i in R['kills']], [i for _, i in E['kills']]
    row('kills (spawn index, in order)', rk, ek, rk == ek)
    rd, ed = sorted(d for _, _, d in R['hits']), sorted(d for _, _, d in E['hits'])
    row('damage per hit (sorted)', rd, ed, rd == ed)
    rs, es = [(ty, hp) for _, ty, hp in R['spawns']], [(ty, hp) for _, ty, hp in E['spawns']]
    row('spawns (type, life)', rs, es, rs == es)
    rw, ew = [n for _, n in R['waves']], [n for _, n in E['waves']]
    row('waves', rw, ew, rw == ew)
    rv, ev = [k for k, _ in R['events']], [k for k, _ in E['events']]
    row('room events (held / released)', rv, ev, rv == ev)
    # a Ganado that waits without animating (the village has some) is in both runs; a stuck state is one only one side
    # has, or Leon frozen
    rsk, esk = sorted((k, i) for k, i, _ in R['stuck']), sorted((k, i) for k, i, _ in E['stuck'])
    row('stuck states (one side only, or Leon)', R['stuck'], E['stuck'],
        rsk == esk and not any(k == 'leon' for k, _ in rsk + esk))
    n = min(len(R['kills']), len(E['kills']))
    if n:
        rt, et = R['kills'][n - 1][0], E['kills'][n - 1][0]
        tol = max(a.clear_abs, int(a.clear_tol * rt))
        row('time to kill %d (ticks, tolerance %d)' % (n, tol), rt, et, abs(rt - et) <= tol)
    else:
        row('time to clear', None, None, len(R['kills']) == len(E['kills']) == 0)
    verdict = 'PASS' if all(r['verdict'] == 'PASS' for r in rows) else 'FAIL'
    for r in rows:
        print('%-40s %-5s ref %s | engine %s' % (r['check'], r['verdict'], str(r['reference'])[:90], str(r['engine'])[:90]))
    print('hits ref   ', ' '.join('%d:%d:-%d' % h for h in R['hits']))
    print('hits engine', ' '.join('%d:%d:-%d' % h for h in E['hits']))
    print('OUTCOME', verdict)
    if a.json:
        json.dump(dict(rows=rows, verdict=verdict, ref=R, engine=E), open(a.json, 'w'), indent=1)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
