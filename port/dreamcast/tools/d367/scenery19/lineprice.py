#!/usr/bin/env python3
"""lineprice.py <hwmodel evidence dir> <function regex> [n]: exclusive MODELLED ms per source line inside the matching
functions (proj/nominal.pcs.tsv, addr2line on the evidence ELF), with the line's max executions per frame."""
import bisect, collections, re, subprocess, sys

BIN = '/opt/toolchains/dc/sh-elf/bin/'
CC = ['base', 'dep_load', 'dep_fpu', 'dep_fdiv', 'dep_other', 'flock', 'branch', 'imiss', 'dmiss', 'pfwait', 'sq', 'uncached']
d, pat = sys.argv[1], re.compile(sys.argv[2]); top = int(sys.argv[3]) if len(sys.argv) > 3 else 40
elf = d + '/re4dc-game.elf'
syms = []
for l in subprocess.run([BIN + 'sh-elf-nm', '-C', '--defined-only', '-n', elf], capture_output=True, text=True).stdout.splitlines():
    f = l.split(' ', 2)
    if len(f) == 3 and f[1] in 'tTwW': syms.append((int(f[0], 16), f[2]))
syms.sort(); starts = [s[0] for s in syms]
frames = 1
for l in open(d + '/proj/nominal.sum.txt'):
    if l.startswith('frames '): frames = int(l.split()[1])
cols = None; rows = []
for l in open(d + '/proj/nominal.pcs.tsv'):
    f = l.rstrip('\n').split('\t')
    if cols is None: cols = {c: i for i, c in enumerate(f)}; continue
    pc = int(f[0], 16); i = bisect.bisect_right(starts, pc) - 1
    if i < 0 or not pat.search(syms[i][1]): continue
    rows.append((pc, sum(float(f[cols[k]]) for k in CC), int(f[cols['exec']])))
out = subprocess.run([BIN + 'sh-elf-addr2line', '-e', elf] + ['%x' % r[0] for r in rows], capture_output=True, text=True).stdout.split('\n')
by = collections.Counter(); ex = collections.Counter(); tot = 0.0
for r, ln in zip(rows, out):
    ln = ln.split('/')[-1]; by[ln] += r[1]; ex[ln] = max(ex[ln], r[2]); tot += r[1]
k = 1.0 / frames / 200000.0
print('total %.3f ms/frame' % (tot * k))
for ln, c in by.most_common(top):
    print('%7.3f ms  maxexec/fr %8.1f  %s' % (c * k, ex[ln] / frames, ln))
