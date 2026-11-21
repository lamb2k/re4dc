#!/usr/bin/env python3
"""shot_engine.py: the engine's shot judged against the PC reference (lane eng-e1k, HANDOVERS.md H-016.3).

    RE4_TREE=<converted data tree> shot_engine.py <serial.txt> <out dir> [--bin re4ref] [--fixture shot-ganado.txt]

<serial.txt> is the serial log of a test disc with the SHOT scenes (tools/engine/build_console_disc.sh --scenes
SHOT,SHOTNP,SHOTDMG,SHOTLATE): the FIGHT=1 image playing the fixture file SHOT.TXT, traced (LT, LE, LL lines). The
reference is re4ref (the plain build) on the same fixture file, run here; nothing from its run reaches the engine.
outcome.py judges each engine scene's records against the reference's trace (--log b, ticks 0..the fixture's length):

    SHOT      the fixture as it is                          must PASS
    SHOTNP    the fixture without the press at tick 160     must FAIL [damage]: no hit
    SHOTDMG   the engine takes 100 more life at each hit    must FAIL [damage]: the amounts differ
    SHOTLATE  the engine holds each hit 30 ticks            must FAIL [damage]: the same amounts, a tick 30 apart

Then the outcome table of SHOT against the reference: every life drop of every actor (tick, before, after) in both,
kills, the room clear, route, position and yaw maxima. Exit 0 when every row ends as it must; 1 when one does not; 2
when an input is missing (a scene not in the log, no reference binary, no tree).
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../../..'))
sys.path.insert(0, HERE)
import outcome  # noqa: E402  (the reader itself: the same parse for the table)

SCENES = [('SHOT', 'PASS', None), ('SHOTNP', 'FAIL', 'amounts'), ('SHOTDMG', 'FAIL', 'amounts'), ('SHOTLATE', 'FAIL', 'time')]


def scene_lines(serial, name):
    """The serial lines of one scene's run: from its CDISC RUN line to its CDISC RESULT line."""
    out, on = [], False
    for s in serial:
        if re.match(r'^CDISC RUN \d+ %s ' % re.escape(name), s):
            on, out = True, []
            continue
        if on and re.match(r'^CDISC RESULT \d+ %s ' % re.escape(name), s):
            return out, s
        if on:
            out.append(s)
    return None, None


def drops(run):
    """{actor: [(tick, before, after)]} and Leon's, from a run outcome.read() returned."""
    d = {k: outcome.life_events(r)[0] for k, r in sorted(run.actors.items())}
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('serial')
    ap.add_argument('out')
    ap.add_argument('--bin', default=os.path.join(ROOT, 'build/hostref/plain/re4ref'))
    ap.add_argument('--fixture', default=os.path.join(HERE, 'fixtures/shot-ganado.txt'))
    a = ap.parse_args()
    tree = os.environ.get('RE4_TREE')
    for p, what in ((a.serial, 'serial log'), (a.bin, 're4ref'), (a.fixture, 'fixture'), (tree or '', 'RE4_TREE')):
        if not p or not os.path.exists(p):
            print('shot_engine: no %s at %s' % (what, p))
            sys.exit(2)
    os.makedirs(a.out, exist_ok=True)
    ticks = int(re.search(r'^ticks\s+(\d+)', open(a.fixture).read(), re.M).group(1))
    ref = os.path.join(a.out, 'ref-trace.txt')
    r = subprocess.run([a.bin, '--tree', tree, '--fixture', a.fixture, '--out', ref, '--log', os.path.join(a.out, 'ref.log')],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode or not os.path.getsize(ref):
        print('shot_engine: re4ref failed: %s' % r.stderr.strip())
        sys.exit(2)
    serial = open(a.serial, errors='replace').read().replace('\r', '').splitlines()
    rows, status, results = [], 0, {}
    for name, must, why in SCENES:
        seg, res = scene_lines(serial, name)
        if seg is None:
            print('shot_engine: scene %s not in %s' % (name, a.serial))
            sys.exit(2)
        eng = os.path.join(a.out, '%s.log' % name)
        open(eng, 'w').write('\n'.join(seg) + '\n')
        jp = os.path.join(a.out, '%s-outcome.json' % name)
        o = subprocess.run([sys.executable, os.path.join(HERE, 'outcome.py'), ref, eng, '--log', 'b', '--expect-ticks',
                            '0:%d' % ticks, '--tolerances', os.path.join(HERE, 'tolerances.json'), '--json', jp],
                           capture_output=True, text=True)
        open(os.path.join(a.out, '%s-outcome.txt' % name), 'w').write(o.stdout + o.stderr)
        j = json.load(open(jp))
        got = j['verdict']
        dmg = [p for p in j['problems'] if p['kind'] == 'damage']
        ok = got == must and o.returncode in (0, 1)
        if ok and must == 'FAIL':
            # the control must fail on damage, for its own reason: different amounts, or the same amounts at another tick
            ok = bool(dmg) and (dmg[0]['detail'].startswith('A amounts') if why == 'amounts' else dmg[0]['detail'].startswith('A at'))
        if not ok:
            status = 1
        first = (j['problems'][0] if j['problems'] else None)
        rows.append('| %s | %s%s | %s | %s | %s | %s |' % (
            name, must, ' [damage: %s]' % why if why else '', got + (' (as it must)' if ok else ' (WRONG)'),
            ', '.join('%s %d' % kv for kv in sorted(j.get('problem_kinds', {}).items())) or '-',
            ('[%s] tick %s %s %s' % (dmg[0]['kind'], dmg[0]['tick'], dmg[0]['what'], dmg[0]['detail'])) if dmg else
            ('[%s] tick %s %s %s' % (first['kind'], first['tick'], first['what'], first['detail']) if first else
             '%d ticks, %d actors, position max %.4f, yaw max %.4f deg' % (j.get('ticks_compared', 0), len(j.get('actors', [])),
                                                                       j['position']['max'], j['yaw']['max_deg'])),
            (res or '').replace('|', '/')[:90]))
        results[name] = (eng, j)
    table = ['| Scene | Must | Got | Problem kinds | First damage problem, else first problem, else result | Selector |',
             '|---|---|---|---|---|---|'] + rows
    # the outcome table: SHOT against the reference
    probs = outcome.Problems()
    A = outcome.read(ref, 'A', False, probs)
    B = outcome.read(results['SHOT'][0], 'B', True, probs)
    j = results['SHOT'][1]
    ot = ['', '## SHOT (engine, Flycast) against the PC reference (re4ref plain), %d ticks' % ticks, '',
          '| Actor | Reference: life drops (tick before->after) | Engine: life drops | Spawn tick A / B | Same |', '|---|---|---|---|---|']
    da, db = drops(A), drops(B)
    for k in sorted(set(da) | set(db)):
        fa, fb = da.get(k, []), db.get(k, [])
        sa = min(A.actors[k]) if k in A.actors else None
        sb = min(B.actors[k]) if k in B.actors else None
        fmt = lambda L: ', '.join('%d %d->%d' % x for x in L) or 'none'
        same = [x[1] - x[2] for x in fa] == [x[1] - x[2] for x in fb] and all(abs(x[0] - y[0]) <= 3 for x, y in zip(fa, fb))
        ot.append('| %s | %s | %s | %s / %s | %s |' % (k, fmt(fa), fmt(fb), sa, sb, 'yes' if same else 'NO'))
    ot += ['', 'kills: %s; room clear: %s; route (Leon at the last tick) %.4f units; position max %.4f units (tick %s, %s), '
           'over 1 unit %d; yaw max %.4f degrees (tick %s, %s), over 1 degree %d; tolerances %s' % (
               j.get('kills'), j.get('clear'), j['route']['diff'], j['position']['max'], j['position']['max_at'],
               j['position']['max_actor'], j['position']['over'], j['yaw']['max_deg'], j['yaw']['max_at'],
               j['yaw']['max_actor'], j['yaw']['over'], j['tolerances'])]
    text = '\n'.join(table + ot) + '\n'
    open(os.path.join(a.out, 'shot_engine.md'), 'w').write(text)
    print(text)
    print('%d scenes, %s' % (len(rows), 'all as they must' if status == 0 else 'SOME WRONG'))
    sys.exit(status)


if __name__ == '__main__':
    main()
