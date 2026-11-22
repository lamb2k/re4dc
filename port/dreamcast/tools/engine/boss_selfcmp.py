#!/usr/bin/env python3
"""boss_selfcmp.py (lane eng-e2c): the BOSS scene of two engine builds compared on what the behaviour did (engine
against itself, Flycast serial logs of build_console_disc.sh discs).

    boss_selfcmp.py <serial A> <serial B> [--control]

Compared, line for line, with load-buffer addresses (0x8cXXXXXX / 8cXXXXXX) masked: the effect requests with their ticks
(E2 FXEV), the effect counts (E2 FX), every other E2 line (tasks, room set-up, hidden scroll pieces with their ticks),
the stub lines and the pool line. The selector's timing lines are printed, not compared (they are not claims). For each
group: identical, or the first differing pair and, for the effect requests, the first tick that differs.
--control plants one difference (B's first effect request moved one tick later): the comparison must report it.
Exit 0 every group identical, 1 a group differs, 2 a log missing or empty.
"""
import re
import sys

GROUPS = [('effect requests', r'^E2 FXEV'), ('effect counts', r'^E2 FX '), ('E2 lines', r'^E2 (?!FX)'),
          ('stubs', r'E1 STUB|stub'), ('pool', r'^E1 POOL')]


def lines(path, pat):
    out = []
    for ln in open(path, errors='replace'):
        if re.search(pat, ln):
            out.append(re.sub(r'0x8c[0-9a-f]{6}|\b8c[0-9a-f]{6}\b', 'ADDR', ln.rstrip()))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        sys.exit(__doc__)
    control = '--control' in sys.argv
    bad = False
    for name, pat in GROUPS:
        a, b = lines(args[0], pat), lines(args[1], pat)
        if name == 'effect requests' and (not a or not b):
            print('boss_selfcmp: no effect requests in a log')
            sys.exit(2)
        if control and name == 'effect requests':
            b = list(b)
            b[0] = re.sub(r't=(\d+)', lambda m: 't=%d' % (int(m.group(1)) + 1), b[0], count=1)
        if a == b:
            print('%-16s %d / %d lines identical' % (name, len(a), len(b)))
            continue
        bad = True
        i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        x = a[i] if i < len(a) else '(end)'
        y = b[i] if i < len(b) else '(end)'
        tick = ''
        if name == 'effect requests':
            ta = re.search(r't=(\d+)', x)
            tb = re.search(r't=(\d+)', y)
            tick = ' first differing tick %s / %s' % (ta.group(1) if ta else '-', tb.group(1) if tb else '-')
        print('%-16s %d / %d lines DIFFER at line %d%s\n    A: %s\n    B: %s' % (name, len(a), len(b), i + 1, tick, x[:160], y[:160]))
    for ln in lines(args[0], r'CDISC SUM BOSS (busy|svc|behav)'):
        print('A timing (not compared):', ln)
    for ln in lines(args[1], r'CDISC SUM BOSS (busy|svc|behav)'):
        print('B timing (not compared):', ln)
    print('boss_selfcmp: %s%s' % ('DIFFER' if bad else 'IDENTICAL', ' (control: one difference planted)' if control else ''))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
