#!/usr/bin/env python3
"""sched_compare.py REF_TRACE REF_PROGRAM RUN_TRACE RUN_PROGRAM (lane eng-sched1): the PC check's comparison.

Same order of task steps: every T line (tick, slot, status and sleep count before and after the step, the task's
function by name: each program's symbol table maps its own addresses) equal, in order.
Same outcome: every S line (the script's calls into the rest of the game, by tick, in order) and every F line (the
final task table, the room flags and save record, the run's hash) equal. A run that did not finish (no "F hash"
line: halted, stuck or crashed) fails. E lines (engine diagnostics, e.g. the engine list's counters) are printed,
not compared. Exit 0 PASS, 1 FAIL."""
import subprocess
import sys


def names(prog):
    out = subprocess.run(['nm', '-C', prog], capture_output=True, text=True).stdout
    m = {}
    for line in out.split('\n'):
        p = line.split(' ', 2)
        if len(p) == 3 and p[0] and p[1] in 'tTwW':
            m[int(p[0], 16)] = p[2]
    return m


def load(trace, prog):
    sym = names(prog)
    t, s, f, e, other = [], [], [], [], []
    for line in open(trace, errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('T '):
            p = line.split(' ')
            p[-1] = sym.get(int(p[-1], 16), p[-1])
            t.append(' '.join(p))
        elif line.startswith('S '):
            s.append(line)
        elif line.startswith('F '):
            f.append(line)
        elif line.startswith('E '):
            e.append(line)
        elif not line.startswith('#'):
            other.append(line)
    return t, s, f, e, other


def first_diff(a, b):
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else '<end>'
        y = b[i] if i < len(b) else '<end>'
        if x != y:
            return i, x, y
    return None


def main():
    r = load(sys.argv[1], sys.argv[2])
    n = load(sys.argv[3], sys.argv[4])
    ok = True
    for k, what in ((0, 'task steps'), (1, 'stub calls'), (2, 'final state')):
        d = first_diff(r[k], n[k])
        print('%-12s ref %6d run %6d  %s' % (what, len(r[k]), len(n[k]), 'same' if d is None else
              'DIFFER at %d: ref "%s" run "%s"' % d))
        ok &= d is None
    for k, side in ((r, 'ref'), (n, 'run')):
        if not any(x.startswith('F hash') for x in k[2]):
            print('%s: the run did not finish%s' % (side, (': ' + k[4][-1]) if k[4] else ''))
            ok = False
        if k[4]:
            print('%s: %s' % (side, k[4][-1]))
    tasks = sorted(set(x.split(' ')[-1] for x in r[0]))
    print('tasks %d: %s' % (len(tasks), ', '.join(tasks)))
    eng = sorted(set(' '.join(x.split(' ')[2:]) for x in n[3]))
    if eng:
        print('engine diagnostics (run, not compared): %s' % '; '.join(eng))
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
