#!/usr/bin/env python3
"""sched_engine.py (lane eng-sched2): the engine's task steps on a Flycast serial log against the PC check's trace.

  sched_engine.py steps SERIAL SCENE E1_ELF PC_TRACE PC_PROGRAM [--nm sh-elf-nm] [--min-ticks 600]
      The scene's E1 SCHEDT lines (host/sched_host.cpp: every TaskSchedulerMain call, after play) against the T lines
      of the PC check's trace (hostref/svc/sched_check.sh: sched_ref, the reference OS rules): tick, slot, status and
      sleep count before and after each step, and the task's function by name (each program's own symbol table), in
      order, over the ticks both runs cover. FAIL when a step differs, when the scene printed no record or dropped
      steps (recorded < steps), or when fewer than --min-ticks ticks are compared.
      The control: the same scene against the PC's reverse control trace (sched_check.sh row ref-reverse: the tasks
      run reversed) must FAIL with "steps DIFFER".
  sched_engine.py delay SERIAL SCENE [--us 200] [--tick 200]
      The timing control of the cost lines: the scene's "E1 SCHED cost all" worst must read at least --us at tick
      --tick (TSCHED: SCHEDD adds a known 200 us there). On the clean SCHED scene it must FAIL.
Exit 0 PASS, 1 FAIL, 2 input missing. The serial holds several scenes: a scene's part runs from the previous
"CDISC RESULT" line (or the start) to its own first "CDISC RESULT <n> <SCENE> " line (the summary at the end repeats
them). Run the PC check for the scene's tick count (sched_check.sh <out> 640 for the village route) so every engine
tick is compared."""
import argparse
import re
import subprocess
import sys


def scene_part(serial, scene):
    part, cur = None, []
    for line in open(serial, errors='replace'):
        m = re.match(r'CDISC RESULT \d+ (\S+) ', line)
        if m:
            if m.group(1) == scene and part is None:   # the first: the summary repeats the result lines at the end
                part = cur
            cur = []
            continue
        cur.append(line.rstrip('\n'))
    return part


def names(prog, nm):
    out = subprocess.run([nm, '-C', prog], capture_output=True, text=True).stdout
    m = {}
    for line in out.split('\n'):
        p = line.split(' ', 2)
        if len(p) == 3 and p[0] and p[1] in 'tTwW':
            m[int(p[0], 16)] = p[2]
    return m


def engine_steps(part, sym):
    steps, end = [], None
    for line in part:
        if line.startswith('E1 SCHEDT END'):
            m = re.search(r'steps (\d+) recorded (\d+)', line)
            end = (int(m.group(1)), int(m.group(2)))
        elif line.startswith('E1 SCHEDT '):
            for item in line.split()[2:]:
                # item form tick:slot:st0/sl0>st/sl:func, hex
                t, slot, ab, f = item.split(':')
                a0, b0 = ab.split('>')
                st0, sl0 = (int(x, 16) for x in a0.split('/'))
                st, sl = (int(x, 16) for x in b0.split('/'))
                steps.append((int(t, 16), int(slot, 16), st0, sl0, st, sl, sym.get(int(f, 16), f)))
    return steps, end


def pc_steps(trace, sym):
    steps = []
    for line in open(trace, errors='replace'):
        if not line.startswith('T '):
            continue
        p = line.split()
        a, b = p[3].split('/'), p[4].split('/')
        steps.append((int(p[1]), int(p[2]), int(a[0], 16), int(a[1]), int(b[0], 16), int(b[1]),
                      sym.get(int(p[5], 16), p[5])))
    return steps


def fmt(s):
    return 'tick %d slot %d %02x/%d>%02x/%d %s' % s if s else '<end>'


def cmd_steps(a):
    part = scene_part(a.serial, a.scene)
    if part is None:
        print('scene %s: no CDISC RESULT line in %s' % (a.scene, a.serial))
        print('FAIL')
        return 2
    eng, end = engine_steps(part, names(a.elf, a.nm))
    ref = pc_steps(a.trace, names(a.prog, 'nm'))
    ok = True
    if end is None:
        print('engine: no "E1 SCHEDT END" line (the record was not printed)')
        ok = False
    elif end[1] < end[0]:
        print('engine: %d steps, only %d recorded' % end)
        ok = False
    last = min(eng[-1][0] if eng else -1, ref[-1][0] if ref else -1)
    e = [s for s in eng if s[0] <= last]
    r = [s for s in ref if s[0] <= last]
    print('ticks compared 0..%d; steps engine %d PC %d (engine total %d, PC total %d)' % (last, len(e), len(r), len(eng),
                                                                                         len(ref)))
    if last < a.min_ticks:
        print('fewer than %d ticks compared' % a.min_ticks)
        ok = False
    if eng and ref and ref[-1][0] < eng[-1][0]:
        print('the PC trace ends at tick %d, the engine ran to tick %d: run the PC check for the scene\'s ticks'
              % (ref[-1][0], eng[-1][0]))
        ok = False
    diff = None
    for i in range(max(len(e), len(r))):
        x = e[i] if i < len(e) else None
        y = r[i] if i < len(r) else None
        if x != y:
            diff = (i, x, y)
            break
    if diff:
        print('steps DIFFER at %d: engine "%s" PC "%s"' % (diff[0], fmt(diff[1]), fmt(diff[2])))
        ok = False
    else:
        print('steps same')
    tasks = sorted(set(s[6] for s in e))
    print('tasks %d: %s' % (len(tasks), ', '.join(tasks)))
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


def cmd_delay(a):
    part = scene_part(a.serial, a.scene)
    if part is None:
        print('scene %s: no CDISC RESULT line in %s' % (a.scene, a.serial))
        print('FAIL')
        return 2
    line = next((l for l in part if l.startswith('E1 SCHED cost all:')), None)
    if not line:
        print('no "E1 SCHED cost all" line')
        print('FAIL')
        return 1
    m = re.search(r'worst (\d+) us \(tick (\d+)\)', line)
    worst, tick = int(m.group(1)), int(m.group(2))
    ok = worst >= a.us and tick == a.tick
    print('%s; worst %d us at tick %d, must be at least %d at tick %d' % (line, worst, tick, a.us, a.tick))
    print('PASS' if ok else 'FAIL')
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('steps')
    s.add_argument('serial'); s.add_argument('scene'); s.add_argument('elf'); s.add_argument('trace'); s.add_argument('prog')
    s.add_argument('--nm', default='sh-elf-nm'); s.add_argument('--min-ticks', type=int, default=600)
    d = sub.add_parser('delay')
    d.add_argument('serial'); d.add_argument('scene')
    d.add_argument('--us', type=int, default=200); d.add_argument('--tick', type=int, default=200)
    a = ap.parse_args()
    return cmd_steps(a) if a.cmd == 'steps' else cmd_delay(a)


if __name__ == '__main__':
    sys.exit(main())
