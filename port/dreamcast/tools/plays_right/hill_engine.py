#!/usr/bin/env python3
"""hill_engine.py: the engine's hill scene (Leon and Ashley) judged against the PC reference (lane eng-e1o, H-017.9).

    RE4_TREE=<converted data tree> hill_engine.py <serial.txt> <out dir> [--scene HILLT] [--bin re4ref]

<serial.txt> is the serial log of a test disc with the traced hill scene (tools/engine/build_console_disc.sh --scenes
HILLT: the E1 image with the root file HILL and no NOTRACE, a function run). Its re4ref trace v2 lines (header, T, A, R)
are the engine's records. The reference is re4ref (the plain build: the fixed reference, routine bytes swapped, em10 and
the presentation callers split, BSpline through the host alias) on fixtures/hill-follow.txt, run here; nothing from its
run reaches the engine. What the engine is given: the fixture's set-up as the image's hill route has it (room r11d,
seed 0x0d37, Leon resumed as the fixture's resume line, Ashley created by SubCharInit and told to follow, 728 ticks, the
fixture's four pad lines), no generator feed (FEED.BIN absent) and no hidden resume of Ashley (RESUMEA absent): the
image's log must say neither "FEED" nor "RESUMEA", or the run is refused (exit 2).

Rows (plays_right.py, the fields and tolerances of the earlier 729-record comparison, lanes eng-e1b to eng-e1d:
tolerances.json; every tick 0..728 must be compared):
    Leon    p,a,mid,mf,ms,r,ps          must PASS
    Ashley  p,a,mid,mf,ms,r,hp,be,f,aps (--actor id=03)   must PASS
    control: the reference with the presentation split off (RE4_PRESENT_SPLIT=0) against the reference, Ashley: must
             FAIL (her face's draws shift her idle timer; lane eng-e1d: routine from tick 367)
Also reported: outcome.py on the same two runs (the gate's reader). Exit 0 when every row ends as it must, 1 when one
does not, 2 when an input is missing.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../../..'))
LEON_FIELDS = 'p,a,mid,mf,ms,r,ps'
ASHLEY_FIELDS = 'p,a,mid,mf,ms,r,hp,be,f,aps'


def scene_lines(serial, name):
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


def pr(a, b, fields, actor, out, ticks, env=None):
    js = out + '.json'
    cmd = [sys.executable, os.path.join(HERE, 'plays_right.py'), a, b, '--tolerances', os.path.join(HERE, 'tolerances.json'),
           '--fields', fields, '--expect-ticks', '0:%d' % ticks, '--json', js, '--quiet']
    if actor:
        cmd += ['--actor', actor]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    open(out + '.txt', 'w').write(r.stdout + r.stderr)
    try:
        j = json.load(open(js))
    except (OSError, ValueError):
        return 'ERROR', r.stdout.strip()[-200:] or r.stderr.strip()[-200:], None
    fd = j.get('first_divergence') or {}
    per = '; '.join('%s %d/%d' % (k, v['compared'] - v['over'], v['compared'])
                    for k, v in j.get('summary', {}).items() if v.get('compared'))
    detail = '%d ticks; first divergence %s; %s' % (j.get('ticks_compared', 0),
                                                   ('tick %s %s' % (fd.get('tick'), fd.get('field', ''))) if fd else 'none', per)
    return ('PASS' if r.returncode == 0 else 'FAIL' if r.returncode == 1 else 'ERROR'), detail, j


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('serial')
    ap.add_argument('out')
    ap.add_argument('--scene', default='HILLT')
    ap.add_argument('--bin', default=os.path.join(ROOT, 'build/hostref/plain/re4ref'))
    ap.add_argument('--fixture', default=os.path.join(HERE, 'fixtures/hill-follow.txt'))
    a = ap.parse_args()
    tree = os.environ.get('RE4_TREE')
    for p, what in ((a.serial, 'serial log'), (a.bin, 're4ref'), (a.fixture, 'fixture'), (tree or '', 'RE4_TREE')):
        if not p or not os.path.exists(p):
            print('hill_engine: no %s at %s' % (what, p))
            return 2
    os.makedirs(a.out, exist_ok=True)
    ticks = int(re.search(r'^ticks\s+(\d+)', open(a.fixture).read(), re.M).group(1))
    serial = open(a.serial, errors='replace').read().replace('\r', '').splitlines()
    seg, res = scene_lines(serial, a.scene)
    if seg is None:
        print('hill_engine: scene %s not in %s' % (a.scene, a.serial))
        return 2
    given = [s for s in seg if re.search(r'E1 (FEED|RESUMEA)', s)]
    if given or not any(s.startswith('E1 scene: hill path') for s in seg):
        print('hill_engine: the run is not the plain hill scene (%s)' % (given[:2] or 'no hill scene line'))
        return 2
    eng = os.path.join(a.out, 'engine.trace')
    n = 0
    with open(eng, 'w', newline='\n') as o:
        for s in seg:
            if s.startswith(('# re4ref trace', 'H fixture=', 'T t=', 'A t=', 'R t=')):
                o.write(s.rstrip() + '\n')
                n += 1
    if not n:
        print('hill_engine: no trace lines in scene %s (a NOTRACE run?)' % a.scene)
        return 2
    refs = {}
    for tag, env in (('ref', None), ('ref-nosplit', dict(os.environ, RE4_PRESENT_SPLIT='0'))):
        t = os.path.join(a.out, tag + '.trace')
        r = subprocess.run([a.bin, '--tree', tree, '--fixture', a.fixture, '--out', t, '--log', os.path.join(a.out, tag + '.log')],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=env)
        if r.returncode or not os.path.getsize(t):
            print('hill_engine: re4ref failed (%s): %s' % (tag, r.stderr.strip()[-300:]))
            return 2
        refs[tag] = t
    rows, status = [], 0
    for name, must, aa, bb, fields, actor in (
            ('Leon, engine (Flycast) against the reference', 'PASS', eng, refs['ref'], LEON_FIELDS, None),
            ('Ashley, engine (Flycast) against the reference', 'PASS', eng, refs['ref'], ASHLEY_FIELDS, 'id=03'),
            ('control: Ashley, the reference with the split off against the reference', 'FAIL', refs['ref-nosplit'], refs['ref'],
             ASHLEY_FIELDS, 'id=03')):
        got, detail, _ = pr(aa, bb, fields, actor, os.path.join(a.out, re.sub(r'\W+', '-', name.split(',')[0] + '-' + name.split(' ')[-1])), ticks)
        ok = got == must
        status = status or (0 if ok else (2 if got == 'ERROR' else 1))
        rows.append('| %s | %s | %s | %s |' % (name, must, got + (' (as it must)' if ok else ' (WRONG)'), detail))
    # the gate's reader on the same pair (reported)
    o = subprocess.run([sys.executable, os.path.join(HERE, 'outcome.py'), refs['ref'], eng, '--expect-ticks', '0:%d' % ticks,
                        '--tolerances', os.path.join(HERE, 'tolerances.json'), '--json', os.path.join(a.out, 'outcome.json')],
                       capture_output=True, text=True)
    open(os.path.join(a.out, 'outcome.txt'), 'w').write(o.stdout + o.stderr)
    first = (o.stdout.strip().splitlines() or ['-'])[0]
    rows.append('| outcome.py: the reference (A) against the engine (B) | reported | %s | %s |' % (
        'PASS' if o.returncode == 0 else 'FAIL' if o.returncode == 1 else 'ERROR', first.replace('|', '/')[:200]))
    table = ['Engine scene %s, %d trace lines; selector: %s' % (a.scene, n, (res or '').strip()[:120]), '',
             '| Check | Must | Got | Detail |', '|---|---|---|---|'] + rows
    open(os.path.join(a.out, 'hill_engine.md'), 'w').write('\n'.join(table) + '\n')
    print('\n'.join(table))
    print('hill_engine: %s' % ('every row as it must' if status == 0 else 'exit %d' % status))
    return status


if __name__ == '__main__':
    sys.exit(main())
