#!/usr/bin/env python3
"""outcome_controls.py: the strict outcome reader's own proof (lane eng-svc5; docs/engine/PLAYS_RIGHT.md "Outcome reader").

    RE4_TREE=<converted data tree> outcome_controls.py <out dir> [--bin re4ref] [--engine-log serial.txt:LO:HI]

Runs the reference (hostref re4ref, plain build) on its fixtures and judges pairs with outcome.py. Every row says what it
must give (PASS or FAIL) and, for a FAIL, the problem kind it must report (other kinds a broken input causes as well
are listed beside it); a row ends as it must only when both hold. One control per failure kind:

  fail-closed (the input is broken, whatever the play):
    missing-file    B does not exist
    no-records      B is empty
    unknown-line    B carries a record tag the reader does not know; and, separately, a line that is not a record
    malformed       one A line of B without its life (hp=)
    non-finite      one actor position of B is a NaN
    duplicate       one T line of B twice
    short-run       B cut after tick 300 (of 520); and, separately, B without the T line of tick 100
    extra-tick      B with one tick after the last
    missing-actor   B without the Ganado 0x1e; and a required actor (--actors e=55) neither run has
  outcome (the input is well formed, the play differs):
    route           door103-walk with the walk 2% longer (re4ref --control walk-speed=1.02), --pos final
    position        the same run, every tick
    kill            bell-ganado-kill with the third hit removed (0x14 lives)
    damage          bell-ganado-kill with the second hit by weapon 0x14 (another amount; still a kill)
    damage-time     bell-ganado-kill with every hit 30 ticks later (--control late-hit=30), --pos final
    trigger-spawn   bell-ganado-kill with 0x1f created at tick 20, not 1
    trigger-gone    B with 0x1f's records removed from tick 400 on (it leaves the alive list early)
    trigger-event   the logic form (below) with the event word changed in B from tick 200 on
    clear           bell-ganado-clear with both hits on 0x1c removed (it lives: no room clear)
  as they must PASS:
    determinism     each fixture's reference run twice
    logic form      bell-ganado-clear written as logic-trace records (LT, LL, LE) against itself, both as serial logs
                    with other lines between the records (--log ab)
With --engine-log, an engine serial log (Flycast, the fight image's LT/LL/LE records) is read against itself (PASS) and
with one LL life drop added on Leon (damage: FAIL): the reader's logic path on a real engine log.
Exit status 0 when every row ends as it must. The table goes to stdout and <out dir>/outcome_controls.md.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../../..'))
OUTCOME = os.path.join(HERE, 'outcome.py')
TOL = os.path.join(HERE, 'tolerances.json')
FIX = os.path.join(HERE, 'fixtures')


def re4ref(binary, tree, fixture, out, control=None):
    os.makedirs(out, exist_ok=True)
    cmd = [binary, '--tree', tree, '--fixture', fixture, '--out', os.path.join(out, 'trace.txt'),
           '--log', os.path.join(out, 'run.log')]
    if control:
        cmd += ['--control', control]
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        sys.exit('re4ref failed (%s): %s' % (out, r.stderr.strip()))
    return os.path.join(out, 'trace.txt')


def derive_fixture(src, dst, subst):
    s = open(src).read()
    for old, new in subst:
        if old not in s:
            sys.exit('fixture %s: "%s" not found' % (src, old))
        s = s.replace(old, new, 1)
    open(dst, 'w').write(s)
    return dst


def mutate(src, dst, fn):
    lines = open(src).read().splitlines()
    open(dst, 'w').write('\n'.join(fn(lines)) + '\n')
    return dst


def judge(a, b, extra, jpath):
    r = subprocess.run([sys.executable, OUTCOME, a, b, '--tolerances', TOL, '--json', jpath, '--quiet'] + extra,
                       capture_output=True, text=True)
    try:
        j = json.load(open(jpath))
    except (OSError, ValueError):
        return r.returncode, None, 'no report: ' + r.stderr.strip()[-200:]
    p = j['problems'][0] if j['problems'] else None
    first = '[%s] %s tick %s %s %s' % (p['kind'], p['trace'], p['tick'], p['what'], p['detail']) if p else (
        '%d ticks, %d actors, kills %s, clear %s' % (j.get('ticks_compared', 0), len(j.get('actors', [])),
                                                     [(k['actor'], k['A']) for k in j.get('kills', [])],
                                                     (j.get('clear') or {}).get('A')))
    return r.returncode, j, first


def to_logic(lines, sp_from=None):
    """A re4ref v2 trace as logic-trace records (LT p/a, LL life and event word, LE per actor), with serial lines between
    them, as an engine log carries them. sp_from: the event word changes from that tick on (the trigger control)."""
    out = ['E1 boot: serial log (lane eng-svc5 control)']
    for s in lines:
        m = re.match(r'^(T|A) t=(\d+)', s)
        if not m:
            continue
        kv = dict(tok.split('=', 1) for tok in s.split()[1:] if '=' in tok)
        t = int(m.group(2))
        if m.group(1) == 'T':
            out.append('LT t=%d r=%s p=%s a=%s m=-/0' % (t, kv['rng'].split('/')[0], kv['p'], kv['a']))
            sp = '00000000' if sp_from is None or t < sp_from else '80400100'
            out.append('LL t=%d hp=4b0 st=00000000 ms=0 sp=%s fx=0' % (t, sp))
            out.append('ROW %d in 1 tick 2' % t)
        else:
            e = kv['e']
            out.append('LE t=%d k=%s id=%s type=4 be=%s stat=00000000 ms=0 hp=%x mf=00000000 pos=%s ay=%s e=%s' % (
                t, kv['k'], kv['id'], kv['be'], int(kv['hp']) & 0xFFFF, kv['p'], kv['a'].split(',')[1], e))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('--bin', default=os.path.join(ROOT, 'build/hostref/plain/re4ref'))
    ap.add_argument('--engine-log', help='serial.txt:LO:HI, an engine serial log with LT/LL/LE records')
    args = ap.parse_args()
    tree = os.environ.get('RE4_TREE')
    if not tree:
        sys.exit('set RE4_TREE to the converted data tree (private game data)')
    if not os.path.isfile(args.bin):
        sys.exit('no re4ref at %s' % args.bin)
    O = args.out
    os.makedirs(O, exist_ok=True)
    rows = []
    status = 0

    def row(name, must, kind, a, b, extra=()):
        nonlocal status
        rc, j, first = judge(a, b, list(extra), os.path.join(O, 'j-%s.json' % re.sub(r'\W+', '_', name)))
        got = 'PASS' if rc == 0 else 'FAIL'
        kinds = sorted((j or {}).get('problem_kinds', {}))
        ok = got == must and (must == 'PASS' or kind in kinds) and rc in (0, 1)
        if not ok:
            status = 1
        rows.append('| %s | %s%s | %s | %s | %s |' % (name, must, (' [%s]' % kind) if kind else '',
                                                      got + (' (as it must)' if ok else ' (WRONG)'),
                                                      ', '.join(kinds) or '-', first.replace('|', '/')))
    fx = lambda n: os.path.join(FIX, n + '.txt')
    # base runs and determinism
    base = {}
    for f in ('door103-walk', 'bell-ganado-kill', 'bell-ganado-clear', 'hill-ashley'):
        base[f] = re4ref(args.bin, tree, fx(f), os.path.join(O, f, 'ref'))
        again = re4ref(args.bin, tree, fx(f), os.path.join(O, f, 'ref2'))
        row('determinism ' + f, 'PASS', '', base[f], again)
    K = base['bell-ganado-kill']
    C = base['bell-ganado-clear']
    D = os.path.join(O, 'mut')
    os.makedirs(D, exist_ok=True)
    # fail-closed
    row('missing-file', 'FAIL', 'missing-file', K, os.path.join(D, 'no-such-trace.txt'))
    row('no-records', 'FAIL', 'no-records', K, mutate(K, os.path.join(D, 'empty.txt'), lambda L: []))
    row('unknown-line (record)', 'FAIL', 'unknown-line', K,
        mutate(K, os.path.join(D, 'unk.txt'), lambda L: L[:50] + ['Q t=20 x=1'] + L[50:]))
    row('unknown-line (text)', 'FAIL', 'unknown-line', K,
        mutate(K, os.path.join(D, 'unk2.txt'), lambda L: L[:50] + ['hello from the serial port'] + L[50:]))

    def drop_hp(L):
        out, done = [], False
        for s in L:
            if not done and s.startswith('A t=50 ') and ' e=14 ' in s:
                s = re.sub(r' hp=\S+', '', s)
                done = True
            out.append(s)
        return out
    row('malformed', 'FAIL', 'malformed', K, mutate(K, os.path.join(D, 'mal.txt'), drop_hp))

    def nan_pos(L):
        out, done = [], False
        for s in L:
            if not done and s.startswith('A t=80 ') and ' e=14 ' in s:
                s = re.sub(r' p=[0-9a-f]{8},', ' p=7fc00000,', s)
                done = True
            out.append(s)
        return out
    row('non-finite', 'FAIL', 'non-finite', K, mutate(K, os.path.join(D, 'nan.txt'), nan_pos))

    def dup_t(L):
        out = []
        for s in L:
            out.append(s)
            if s.startswith('T t=120 '):
                out.append(s)
        return out
    row('duplicate', 'FAIL', 'duplicate', K, mutate(K, os.path.join(D, 'dup.txt'), dup_t))

    def cut(L):
        out = []
        for s in L:
            m = re.match(r'^[TAR] t=(\d+)', s)
            if m and int(m.group(1)) > 300:
                break
            out.append(s)
        return out
    row('short-run (cut at 300)', 'FAIL', 'short-run', C, mutate(C, os.path.join(D, 'cut.txt'), cut))
    row('short-run (tick 100 missing)', 'FAIL', 'short-run', K,
        mutate(K, os.path.join(D, 'gap.txt'), lambda L: [s for s in L if not s.startswith('T t=100 ')]))

    def extra(L):
        last = [s for s in L if s.startswith('T t=')][-1]
        t = int(re.match(r'T t=(\d+)', last).group(1))
        return L + [last.replace('T t=%d ' % t, 'T t=%d ' % (t + 1)), 'R t=%d other=0 pl=0 cam=0 obj=0 spawn=0 em=-' % (t + 1)]
    row('extra-tick', 'FAIL', 'extra-tick', K, mutate(K, os.path.join(D, 'extra.txt'), extra))
    row('missing-actor (0x1e gone from B)', 'FAIL', 'missing-actor', K,
        mutate(K, os.path.join(D, 'noact.txt'), lambda L: [s for s in L if not (s.startswith('A ') and ' e=1e ' in s)]))
    row('missing-actor (required e=55)', 'FAIL', 'missing-actor', K, K, ['--actors', 'e=55'])
    # outcome
    W = re4ref(args.bin, tree, fx('door103-walk'), os.path.join(O, 'door103-walk', 'walk'), 'walk-speed=1.02')
    row('route (walk 2% longer)', 'FAIL', 'route', base['door103-walk'], W, ['--pos', 'final'])
    row('position (walk 2% longer)', 'FAIL', 'position', base['door103-walk'], W)
    kf = fx('bell-ganado-kill')
    nk = derive_fixture(kf, os.path.join(D, 'nokill.txt'), [('hit 140 0x14 2\n', '')])
    row('kill (third hit removed)', 'FAIL', 'kill', K, re4ref(args.bin, tree, nk, os.path.join(O, 'k-nokill')))
    dw = derive_fixture(kf, os.path.join(D, 'dmgwep.txt'), [('hit 100 0x14 2\n', 'hit 100 0x14 0x14\n')])
    row('damage (second hit by weapon 0x14)', 'FAIL', 'damage', K, re4ref(args.bin, tree, dw, os.path.join(O, 'k-dmgwep')))
    row('damage-time (hits 30 ticks later)', 'FAIL', 'damage', K,
        re4ref(args.bin, tree, kf, os.path.join(O, 'k-late30'), 'late-hit=30'), ['--pos', 'final'])
    sp = derive_fixture(kf, os.path.join(D, 'spawn20.txt'), [('actor 0x1f 1 post', 'actor 0x1f 20 post')])
    row('trigger-spawn (0x1f at tick 20)', 'FAIL', 'trigger', K, re4ref(args.bin, tree, sp, os.path.join(O, 'k-spawn20')))

    def gone(L):
        return [s for s in L if not (s.startswith('A ') and ' e=1f ' in s and int(re.match(r'A t=(\d+)', s).group(1)) >= 400)]
    row('trigger-gone (0x1f removed at 400)', 'FAIL', 'trigger', C, mutate(C, os.path.join(D, 'gone.txt'), gone))
    cf = fx('bell-ganado-clear')
    nc = derive_fixture(cf, os.path.join(D, 'noclear.txt'), [('hit 90 0x1c 0x13\n', ''), ('hit 130 0x1c 0x13\n', '')])
    row('clear (0x1c lives)', 'FAIL', 'clear', C, re4ref(args.bin, tree, nc, os.path.join(O, 'c-noclear')))
    # the logic form
    la = mutate(C, os.path.join(D, 'logic-a.txt'), lambda L: to_logic(L))
    lb = mutate(C, os.path.join(D, 'logic-b.txt'), lambda L: to_logic(L))
    le = mutate(C, os.path.join(D, 'logic-ev.txt'), lambda L: to_logic(L, sp_from=200))
    row('logic form (serial logs)', 'PASS', '', la, lb, ['--log', 'ab', '--expect-ticks', '0:520'])
    row('logic form without --log', 'FAIL', 'unknown-line', la, lb, ['--expect-ticks', '0:520'])
    row('logic form without --expect-ticks', 'FAIL', 'short-run', la, lb, ['--log', 'ab'])
    row('trigger-event (event word from 200)', 'FAIL', 'trigger', la, le, ['--log', 'ab', '--expect-ticks', '0:520'])
    if args.engine_log:
        path, lo, hi = args.engine_log.rsplit(':', 2)
        row('engine log against itself', 'PASS', '', path, path, ['--log', 'ab', '--expect-ticks', '%s:%s' % (lo, hi)])

        def leon_hit(L):
            out, done = [], False
            for s in L:
                m = re.match(r'^LL t=(\d+) hp=([0-9a-f]+)(.*)$', s)
                if m and int(m.group(1)) >= (int(lo) + int(hi)) // 2:
                    s = 'LL t=%s hp=%x%s' % (m.group(1), max(int(m.group(2), 16) - 100, 0), m.group(3))
                out.append(s)
            return out
        row('engine log, Leon hit once more', 'FAIL', 'damage', path, mutate(path, os.path.join(D, 'eng-hit.txt'), leon_hit),
            ['--log', 'ab', '--expect-ticks', '%s:%s' % (lo, hi)])
    table = ['| Row | Must [kind] | Got | Problem kinds reported | First problem / result |', '|---|---|---|---|---|'] + rows
    open(os.path.join(O, 'outcome_controls.md'), 'w').write('\n'.join(table) + '\n')
    print('\n'.join(table))
    print('%d rows, %s' % (len(rows), 'all as they must' if status == 0 else 'SOME WRONG'))
    sys.exit(status)


if __name__ == '__main__':
    main()
