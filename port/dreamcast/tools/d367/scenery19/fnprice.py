#!/usr/bin/env python3
"""fnprice.py <hwmodel evidence dir> [regex] [other dir]: exclusive MODELLED ms per frame by function (proj/nominal),
main-image symbols from the ELF (sh-elf-nm). With a second dir: both columns and the difference."""
import bisect, collections, re, subprocess, sys

CC = ['base', 'dep_load', 'dep_fpu', 'dep_fdiv', 'dep_other', 'flock', 'branch', 'imiss', 'dmiss', 'pfwait', 'sq', 'uncached']


def load(d):
    out = subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-nm', '-C', '--defined-only', '-n', d + '/re4dc-game.elf'],
                         capture_output=True, text=True).stdout
    syms = []
    for l in out.splitlines():
        f = l.split(' ', 2)
        if len(f) == 3 and f[1] in 'tTwW':
            syms.append((int(f[0], 16), f[2]))
    syms.sort(); starts = [s[0] for s in syms]
    frames = 1
    for l in open(d + '/proj/nominal.sum.txt'):
        if l.startswith('frames '): frames = int(l.split()[1])
    cols = None; tot = collections.Counter(); calls = collections.Counter(); allc = 0.0
    for l in open(d + '/proj/nominal.pcs.tsv'):
        f = l.rstrip('\n').split('\t')
        if cols is None: cols = {c: i for i, c in enumerate(f)}; continue
        pc = int(f[0], 16); c = sum(float(f[cols[k]]) for k in CC); allc += c
        i = bisect.bisect_right(starts, pc) - 1
        n = syms[i][1] if i >= 0 else '?'
        tot[n] += c
        if i >= 0 and pc == syms[i][0]: calls[n] += int(f[cols['exec']])
    k = 1.0 / frames / 200000.0
    return {n: c * k for n, c in tot.items()}, {n: v / frames for n, v in calls.items()}, allc * k


a = load(sys.argv[1]); pat = re.compile(sys.argv[2] if len(sys.argv) > 2 else '.')
b = load(sys.argv[3]) if len(sys.argv) > 3 else None
print('total %.3f%s' % (a[2], '' if not b else '  ->  %.3f  (%+.3f)' % (b[2], b[2] - a[2])))
names = set(a[0]) | (set(b[0]) if b else set())
rows = sorted(names, key=lambda n: -max(a[0].get(n, 0), b[0].get(n, 0) if b else 0))
sa = sb = 0.0
for n in rows:
    if not pat.search(n): continue
    x = a[0].get(n, 0); sa += x
    if b:
        y = b[0].get(n, 0); sb += y
        if max(x, y) >= 0.005: print('%7.3f %7.3f %+7.3f  calls %7.1f  %s' % (x, y, y - x, a[1].get(n, 0), n[:150]))
    elif x >= 0.005: print('%7.3f  calls %7.1f  %s' % (x, a[1].get(n, 0), n[:150]))
print('selected %.3f%s' % (sa, '' if not b else ' -> %.3f (%+.3f)' % (sb, sb - sa)))
