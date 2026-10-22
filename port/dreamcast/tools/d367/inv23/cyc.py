"""cyc.py <run-output.txt> [keysout]: per sub-screen phase: DISCRD KB, texture loads, evictions (inv23)."""
import sys, re, collections
ph = 'pre'; n = 0; order = ['pre']
kb = collections.Counter(); mus = collections.Counter(); reads = collections.Counter()
loads = collections.defaultdict(list); misc = collections.defaultdict(collections.Counter)
first_vram = {}
last_vram = ''
for raw in open(sys.argv[1], 'rb'):
    l = raw.decode('latin1').rstrip()
    if 'subscreen backing: open' in l:
        n += 1; ph = 'open%d' % n; order.append(ph); first_vram[ph] = last_vram
    elif 'subscreen backing: close' in l:
        ph = 'after%d' % n; order.append(ph)
    if l.startswith('vram room:'): last_vram = l
    m = re.match(r'DISCRD: window_ms=\d+ reads=(\d+) kb=(\d+).*music reads=(\d+) kb=(\d+)', l)
    if m:
        reads[ph] += int(m.group(1)); kb[ph] += int(m.group(2)); mus[ph] += int(m.group(4))
    m = re.match(r'native UI: load (\S+) (\d+)x(\d+) fmt=(\d+)', l)
    if m:
        loads[ph].append((m.group(1).rsplit('/', 1)[-1], m.group(2) + 'x' + m.group(3), m.group(4)))
    for k in ('evict', 'thrash', 'no contiguous', 'refus', 'motion miss', 'Read File'):
        if k in l: misc[ph][k] += 1
for p in order:
    print('%-7s disc kb=%6d reads=%5d music_kb=%5d tex_loads=%3d %s' % (p, kb[p], reads[p], mus[p], len(loads[p]), dict(misc[p])))
    if p in first_vram: print('        vram at open: ' + first_vram[p][:230])
if len(sys.argv) > 2:
    with open(sys.argv[2], 'w') as f:
        for p in order:
            for k in loads[p]: f.write('%s\t%s\t%s\t%s\n' % (p, k[0], k[1], k[2]))
