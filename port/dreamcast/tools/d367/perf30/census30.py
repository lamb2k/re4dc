#!/usr/bin/env python3
"""census30.py <run-output.txt> <elf> <room hex> [--skip N] [--out file.md]   (WSL; lane perf30-census)
Sums the CENSUS30 windows (c30w / c30e / c30o / c30s / c30r lines, game/census30.cpp) of one Flycast run in one room,
skipping the first N full windows (settle; default 1), and prints per-tick tables: effects live vs drawn by id with the
draw-cut outcome, effect owners, skeleton passes per actor key split drawn / dropped ticks, and the callers of
partsWorldCalc / getPartsPtr resolved with sh-elf-addr2line. All numbers are Flycast counts (not timing)."""
import argparse, collections, re, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument('log'); ap.add_argument('elf'); ap.add_argument('room')
ap.add_argument('--skip', type=int, default=1)
ap.add_argument('--out')
a = ap.parse_args()
room = int(a.room, 16)
OUTS = ['drawn', 'tcap', 'haze', 'ess', 'trim', 'level', 'none', 'emit_np', 'strip_np', 'trans_ne', 'custom', 'notq']
SKS = ['calls', 'parts', 'rep', 'mot', 'ik', 'pen', 'penskip', 'cloth', 'models']

wins = []
cur = None
for line in open(a.log, errors='replace'):
    i = line.find('c30')
    if i < 0:
        continue
    s = line[i:].strip()
    if s.startswith('c30w:'):
        m = re.search(r'f=(\d+)\.\.(\d+) room=([0-9a-f]+) ticks=(\d+) drawn=(\d+) dropped=(\d+) leon=(\w+) ash=(\w+) nesp=(\d+) '
                      r'live/tick d=(\d+) x=(\d+) max=(\d+) queued/tick=(\d+) emit/tick=(\d+) drawn/tick=(\d+) skelmiss=(\d+)', s)
        if not m:
            cur = None
            continue
        g = m.groups()
        cur = dict(f0=int(g[0]), f1=int(g[1]), room=int(g[2], 16), ticks=int(g[3]), d=int(g[4]), x=int(g[5]), leon=g[6],
                   ash=g[7], nesp=int(g[8]), maxlive=int(g[11]), skelmiss=int(g[15]), e={}, o={}, s={}, r={})
        wins.append(cur)
    elif cur is None:
        continue
    elif s.startswith('c30e:'):
        m = re.match(r'c30e: id=(\w+) liveD=(\d+) liveX=(\d+) moved=(\d+)(.*)', s)
        if m:
            d = dict(liveD=int(m.group(2)), liveX=int(m.group(3)), moved=int(m.group(4)))
            for k, v in re.findall(r'(\w+)=(\d+)', m.group(5)):
                d[k] = int(v)
            cur['e'][m.group(1)] = d
    elif s.startswith('c30o:'):
        m = re.match(r'c30o: own=(\w+) live=(\d+) drawn=(\d+)', s)
        if m:
            cur['o'][m.group(1)] = (int(m.group(2)), int(m.group(3)))
    elif s.startswith('c30s:'):
        m = re.match(r'c30s: own=(\w+) self=(\d) ph=(\w) D (.*) X (.*)', s)
        if m:
            dd = dict(re.findall(r'(\w+)=(\d+)', m.group(4)))
            xx = dict(re.findall(r'(\w+)=(\d+)', m.group(5)))
            cur['s'][(m.group(1), m.group(2), m.group(3))] = ({k: int(v) for k, v in dd.items()}, {k: int(v) for k, v in xx.items()})
    elif s.startswith('c30r:'):
        m = re.match(r'c30r: k=(\w) ra=([0-9a-f]+) ph=(\w) d=(\d+) x=(\d+)', s)
        if m:
            cur['r'][(m.group(1), m.group(2), m.group(3))] = (int(m.group(4)), int(m.group(5)))

sel = [w for w in wins if w['room'] == room and w['ticks'] >= 250]
sel = sel[a.skip:]
if not sel:
    sys.exit('no full windows in room %03x (%d windows total)' % (room, len(wins)))
TD = sum(w['d'] for w in sel); TX = sum(w['x'] for w in sel); T = TD + TX
out = []
P = out.append
P('# CENSUS30 room %03x: %d windows, frames %d..%d, %d ticks (%d drawn, %d dropped = %.1f%% dropped) [Flycast counts]'
  % (room, len(sel), sel[0]['f0'], sel[-1]['f1'], T, TD, TX, 100.0 * TX / max(T, 1)))
P('leon id %s, ashley id %s, effect pool %d slots, max live %d, skelmiss %d' % (sel[0]['leon'], sel[-1]['ash'], sel[0]['nesp'],
  max(w['maxlive'] for w in sel), sum(w['skelmiss'] for w in sel)))
# effects
E = collections.defaultdict(lambda: collections.Counter())
for w in sel:
    for k, d in w['e'].items():
        E[k].update(d)
tot = collections.Counter()
for d in E.values():
    tot.update(d)
P('')
P('## Effects per tick (live on all ticks; outcomes on drawn ticks)')
P('live/tick all %.1f (drawn ticks %.1f, dropped ticks %.1f), moved/tick %.1f' % (
  (tot['liveD'] + tot['liveX']) / T, tot['liveD'] / max(TD, 1), tot['liveX'] / max(TX, 1), tot['moved'] / T))
P('outcomes per drawn tick: ' + ', '.join('%s %.1f' % (o, tot[o] / max(TD, 1)) for o in OUTS if tot[o]))
P('')
P('| id | live/tick | moved/tick | drawn | ' + ' | '.join(OUTS[1:]) + ' |')
P('|---|---:|---:|---:|' + '---:|' * (len(OUTS) - 1))
for k, d in sorted(E.items(), key=lambda kv: -(kv[1]['liveD'] + kv[1]['liveX'])):
    lv = (d['liveD'] + d['liveX']) / T
    if lv < 0.05:
        continue
    P('| %s | %.1f | %.1f | %.1f | ' % (k, lv, d['moved'] / T, d['drawn'] / max(TD, 1)) +
      ' | '.join('%.1f' % (d[o] / max(TD, 1)) for o in OUTS[1:]) + ' |')
O = collections.defaultdict(lambda: [0, 0])
for w in sel:
    for k, (lv, dr) in w['o'].items():
        O[k][0] += lv; O[k][1] += dr
P('')
P('## Effect owners (drawn ticks): live/tick, drawn/tick')
P(', '.join('%s %.1f/%.1f' % (k, v[0] / max(TD, 1), v[1] / max(TD, 1)) for k, v in sorted(O.items(), key=lambda kv: -kv[1][0])))
# skeleton
S = collections.defaultdict(lambda: [collections.Counter(), collections.Counter()])
for w in sel:
    for k, (dd, xx) in w['s'].items():
        S[k][0].update(dd); S[k][1].update(xx)
P('')
P('## Skeleton per tick (own = construct id of the enemy whose move runs, fe = outside EmMgr.move; self 1 = its own model;'
  ' ph T logic, R after the pacer decision (Trans), N next Render). D = drawn ticks, X = dropped ticks')
P('| own | self | ph | ' + ' | '.join('D ' + s for s in SKS) + ' | ' + ' | '.join('X ' + s for s in SKS) + ' |')
P('|---|---|---|' + '---:|' * (2 * len(SKS)))
for k, (dd, xx) in sorted(S.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
    P('| %s | %s | %s | ' % k + ' | '.join('%.2f' % (dd[s] / max(TD, 1)) for s in SKS) + ' | ' +
      ' | '.join('%.2f' % (xx[s] / max(TX, 1)) for s in SKS) + ' |')
# callers
R = collections.defaultdict(lambda: [0, 0])
for w in sel:
    for k, (d, x) in w['r'].items():
        R[k][0] += d; R[k][1] += x
addrs = sorted({int(k[1], 16) for k in R})
names = {}
if addrs:
    a2l = 'sh-elf-addr2line'
    for cand in ('/opt/toolchains/dc/sh-elf/bin/sh-elf-addr2line', 'sh-elf-addr2line'):
        try:
            res = subprocess.run([cand, '-f', '-C', '-e', a.elf] + ['%x' % (x - 2) for x in addrs], capture_output=True, text=True)
            ls = res.stdout.splitlines()
            for i, x in enumerate(addrs):
                names[x] = ls[2 * i] + ' (' + ls[2 * i + 1].split('/')[-1] + ')'
            break
        except Exception:
            continue
P('')
P('## Callers per tick (W = partsWorldCalc, P = getPartsPtr(no >= 0); D drawn ticks, X dropped ticks)')
P('| k | ph | D/tick | X/tick | caller |')
P('|---|---|---:|---:|---|')
for k, (d, x) in sorted(R.items(), key=lambda kv: -(kv[1][0] + kv[1][1])):
    if (d + x) / T < 0.2:
        continue
    P('| %s | %s | %.1f | %.1f | %s |' % (k[0], k[2], d / max(TD, 1), x / max(TX, 1), names.get(int(k[1], 16), k[1])))
txt = '\n'.join(out) + '\n'
if a.out:
    open(a.out, 'w').write(txt)
print(txt)
