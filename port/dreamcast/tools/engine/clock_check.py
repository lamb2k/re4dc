#!/usr/bin/env python3
"""clock_check.py <serial log> [--judge kos]: the engine clock's check (lane eng-clock1; core/e1_clock.h).

Reads the boot file GAPPROBE's lines (core/e1_clock.cpp) from a Flycast or console serial log and judges:
  reload   E1 CLOCK: TMU2's reload is 12,468,720 counts at Pck/4 (the rate the engine converts at)
  on       the engine clock with interrupts on: no gap over 0.2 ms but the probe's own spin (3,000-4,999 us, the
           probe's control), across at least one whole second
  off      the same with interrupts off (no spin), across at least one whole second
  span     600 display fields (CLOCKSPAN): the span agrees with 600 NTSC fields (1001/60 ms each) within one field, and
           no field reads more than 500 us longer than the shortest
  control  KOS's own conversion (timer_ns_gettime64) on the same probe MUST show the jump: a 2,300-2,700 us gap with
           interrupts on and off, and a field 2,000 us or more over the shortest
--judge kos: judge KOS's lines by the engine's rules (the checker's own control: it must FAIL).
Exit 0 when every row is as it must."""
import re
import sys

FIELD_US = 1001000 / 60.0  # 16,683.3 us: one NTSC field (59.94 Hz)


def main():
    args = sys.argv[1:]
    judge = 'engine'
    if '--judge' in args:
        i = args.index('--judge')
        judge = args[i + 1]
        del args[i:i + 2]
    text = open(args[0], errors='replace').read()
    rows = []

    def row(name, ok, what):
        rows.append((name, ok))
        print('%-8s %s  %s' % (name, 'PASS' if ok else 'FAIL', what))

    m = re.search(r'E1 CLOCK TMU2 reload (\d+) counts, prescaler (\d+).*: (OK|MISMATCH)', text)
    row('reload', bool(m) and m.group(3) == 'OK', m.group(0) if m else 'no E1 CLOCK line')

    def arm(name, tag):
        h = re.search(r'E1 GAPPROBE %s %s: (\d+) ms, (\d+) reads, (\d+) gaps over 0\.2 ms, crosses (\d+) whole seconds'
                      % (name, tag), text)
        gaps = [int(g) for g in re.findall(r'E1 GAPPROBE %s %s gap (\d+) us at' % (name, tag), text)]
        return h, gaps

    def judge_clean(name, tag, spin):
        h, gaps = arm(name, tag)
        if not h:
            return False, 'no probe line for %s %s' % (name, tag)
        crosses = int(h.group(4))
        spins = [g for g in gaps if 3000 <= g <= 4999]
        other = [g for g in gaps if not (3000 <= g <= 4999)]
        ok = crosses >= 1 and not other and (len(spins) == 1 if spin else not spins)
        return ok, '%s %s: crosses %d s, gaps %s' % (name, tag, crosses, gaps)

    def judge_jump(name, tag):
        h, gaps = arm(name, tag)
        if not h:
            return False, 'no probe line for %s %s' % (name, tag)
        jumps = [g for g in gaps if 2300 <= g <= 2700]
        return int(h.group(4)) >= 1 and len(jumps) >= 1, '%s %s: crosses %s s, gaps %s' % (name, tag, h.group(4), gaps)

    for tag, spin in (('irq-on', True), ('irq-off', False)):
        ok, what = judge_clean(judge, tag, spin)
        row('on' if spin else 'off', ok, what)
    s = re.search(r'E1 CLOCKSPAN (\d+) fields: engine span (\d+) us, field min (\d+) max (\d+) \(field (\d+)\); '
                  r'kos span (\d+) us, field min (\d+) max (\d+) \(field (\d+)\)', text)
    if s:
        n = int(s.group(1))
        e = [int(s.group(i)) for i in (2, 3, 4)]
        k = [int(s.group(i)) for i in (6, 7, 8)]
        span, mn, mx = e if judge == 'engine' else k
        ok = abs(span - n * FIELD_US) <= FIELD_US and mx - mn <= 500
        row('span', ok, '%s: %d fields span %d us (expected %.0f), field min %d max %d' % (judge, n, span, n * FIELD_US, mn, mx))
        row('control', k[2] - k[1] >= 2000 and all(judge_jump('kos', t)[0] for t in ('irq-on', 'irq-off')),
            'kos: field max - min %d us; %s; %s' % (k[2] - k[1], judge_jump('kos', 'irq-on')[1], judge_jump('kos', 'irq-off')[1]))
    else:
        row('span', False, 'no E1 CLOCKSPAN line')
        row('control', False, 'no E1 CLOCKSPAN line')
    bad = [r for r, ok in rows if not ok]
    print('clock_check (%s): %s' % (judge, 'every row PASS' if not bad else 'FAIL: ' + ', '.join(bad)))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
