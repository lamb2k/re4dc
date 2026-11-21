#!/usr/bin/env python3
"""sndreq_check.py: the engine's sound requests against the PC reference's, tick by tick (lane eng-snd1, H-025.1).

    sndreq_check.py <engine serial log> <scene> <reference run log> [--out report.md] [--control drop|move|extra]

The hosted behaviour asks for sounds through SndCall and SndStop. On the engine every request is written to the trace
as an SR line by the sound service (services/sound/snd_svc.cpp: "SR t=<tick> f=<Frame_cnt> k=<C|S> b=<block> n=<no>
v=<flags hex> i=<id> p=<x,y,z float bits | ->"); the PC reference (hostref re4ref, hostref/host_stubs.cpp) writes the
same fields to its run log ("SR f=... k=..."). The scene's SR lines are taken from the serial log between the
selector's "CDISC RUN <n> <scene>" line and its "CDISC RESULT <n> <scene>" line.

The rule (stated before any run): over the ticks both runs cover (the reference fixture's length), the two request
lists are equal, in order, tick by tick:
  - every SndCall: same tick (Frame_cnt), block, number, flags and id; position within the plays-right tolerance
    (tools/plays_right/tolerances.json "pos", per axis), or no position on both sides;
  - every SndStop: same tick and fade time (its id is the sound the driver returned, which the reference, playing no
    sound, answers 0: not compared);
  - no request missing, none extra. A dropped call fails at its tick.
Fails closed: a missing file, a scene with no SR lines while the reference has some, or an engine Frame_cnt that does
not advance with its tick, exits 2.
Controls (each must FAIL; the self-check of this script, run on the same inputs):
  --control drop   the engine's first request from tick 100 on removed
  --control move   the engine's first request with a position moved 2 units on x
  --control extra  one request added to the engine's list (a copy of its first, one tick later)
Exit: 0 PASS, 1 FAIL, 2 not judged."""
import argparse
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOL = os.path.join(HERE, '..', '..', '..', '..', 'tools', 'plays_right', 'tolerances.json')
SR = re.compile(r'^SR (?:t=(\d+) )?f=(\d+) k=([CS]) b=(\d+) n=(\d+) v=([0-9a-f]{8}) i=(-?\d+) p=(-|[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8})\s*$')


def fl(h):
    return struct.unpack('<f', struct.pack('<I', int(h, 16)))[0]


def parse(lines):
    out = []
    for ln in lines:
        m = SR.match(ln.strip())
        if not m:
            if ln.startswith('SR '):
                raise ValueError('malformed SR line: ' + ln.strip()[:80])
            continue
        t, f, k, b, n, v, i, p = m.groups()
        out.append({'t': int(t) if t else None, 'f': int(f), 'k': k, 'b': int(b), 'n': int(n), 'v': v, 'i': int(i),
                    'p': None if p == '-' else tuple(fl(x) for x in p.split(','))})
    return out


def scene_lines(serial, scene):
    """The scene's lines: from "CDISC RUN <n> <scene> " to its "CDISC RESULT <n> <scene> " (the selector's)."""
    lines = open(serial, errors='replace').read().splitlines()
    start = end = None
    for k, ln in enumerate(lines):
        if start is None and re.match(r'^CDISC RUN \d+ %s ' % re.escape(scene), ln):
            start = k
        elif start is not None and re.match(r'^CDISC RESULT \d+ %s ' % re.escape(scene), ln):
            end = k
            break
    if start is None:
        return None
    return lines[start:end if end is not None else len(lines)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('serial')
    ap.add_argument('scene')
    ap.add_argument('reflog')
    ap.add_argument('--out')
    ap.add_argument('--control', choices=['drop', 'move', 'extra'])
    a = ap.parse_args()
    for p in (a.serial, a.reflog, TOL):
        if not os.path.exists(p):
            print(f'sndreq_check: missing {p}')
            return 2
    tol = json.load(open(TOL))['pos']
    sl = scene_lines(a.serial, a.scene)
    if sl is None:
        print(f'sndreq_check: no scene {a.scene} in {a.serial}')
        return 2
    eng = parse(sl)
    ref = parse(open(a.reflog, errors='replace').read().splitlines())
    if not ref:
        print('sndreq_check: the reference log has no SR line (not judged)')
        return 2
    if not eng:
        print(f'sndreq_check: scene {a.scene} has no SR line (a timing run, or the requests are not traced): not judged')
        return 2
    offs = {e['f'] - e['t'] for e in eng if e['t'] is not None}
    if len(offs) != 1:
        print(f'sndreq_check: engine Frame_cnt does not advance with its tick (offsets {sorted(offs)[:5]}): not judged')
        return 2
    if a.control == 'drop':
        k = next((j for j, e in enumerate(eng) if e['t'] is not None and e['t'] >= 100), None)
        if k is not None:
            del eng[k]
    elif a.control == 'move':
        k = next((j for j, e in enumerate(eng) if e['p']), None)
        if k is not None:
            p = eng[k]['p']
            eng[k] = dict(eng[k], p=(p[0] + 2.0, p[1], p[2]))
    elif a.control == 'extra':
        eng.insert(1, dict(eng[0], f=eng[0]['f'] + 1))
        eng.sort(key=lambda e: e['f'])
    # the ticks both cover: the reference's fixture length (its last tick is the end of its trace, not of its requests:
    # the engine's later requests beyond the reference's last tick are not judged)
    ref_last = max(e['f'] for e in ref)
    lo = 1
    hi = ref_last
    eng_w = [e for e in eng if lo <= e['f'] <= hi]
    ref_w = [e for e in ref if lo <= e['f'] <= hi]
    rows = []
    first_bad = None
    n = max(len(eng_w), len(ref_w))
    for j in range(n):
        e = eng_w[j] if j < len(eng_w) else None
        r = ref_w[j] if j < len(ref_w) else None
        why = ''
        if e is None:
            why = 'missing on the engine'
        elif r is None:
            why = 'extra on the engine'
        elif e['f'] != r['f']:
            why = f"tick {e['f']} on the engine, {r['f']} on the reference"
        elif e['k'] != r['k']:
            why = 'kind'
        elif e['k'] == 'C':
            if (e['b'], e['n'], e['v'], e['i']) != (r['b'], r['n'], r['v'], r['i']):
                why = 'block/number/flags/id'
            elif (e['p'] is None) != (r['p'] is None):
                why = 'position present on one side only'
            elif e['p'] and max(abs(x - y) for x, y in zip(e['p'], r['p'])) > tol:
                why = 'position off by %.3f units' % max(abs(x - y) for x, y in zip(e['p'], r['p']))
        else:
            if e['v'] != r['v']:
                why = 'stop fade time'
        if why and first_bad is None:
            first_bad = (j, why, e, r)
        rows.append((j, e, r, why))
    verdict = 'FAIL' if first_bad else 'PASS'
    head = (f'sndreq_check {a.scene}{" control " + a.control if a.control else ""}: engine {len(eng_w)} requests, '
            f'reference {len(ref_w)}, ticks 1-{hi}: {verdict}')
    if first_bad:
        j, why, e, r = first_bad
        at = (e or r)['f']
        head += f' (request {j + 1}, tick {at}: {why})'
    print(head)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(head + '\n\n| # | tick | engine | reference | |\n|---|---|---|---|---|\n')
            fmt = lambda x: '-' if x is None else f"{x['k']} b{x['b']} n{x['n']} v{x['v']} i{x['i']}"
            for j, e, r, why in rows:
                f.write(f"| {j + 1} | {(e or r)['f']} | {fmt(e)} | {fmt(r)} | {why} |\n")
    return 1 if first_bad else 0


if __name__ == '__main__':
    sys.exit(main())
