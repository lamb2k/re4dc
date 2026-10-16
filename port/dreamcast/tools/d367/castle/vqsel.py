import json, re, sys, struct, collections, pathlib
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools')
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367')
import vq_native_ui as vq
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram')
from vq_pak import read_pak
FIX = json.load(open('/root/probe/lanes-20261015/castle/fix/castle-t12b.json'))['replace']
pak = read_pak(open(FIX['dc/tex.pak'], 'rb').read())
E = '/mnt/c/Flycast-Evidence/re4-dreamcast/castle-20261015/h-cxt12c/scenarios/'
runs = ['cx-r202-t12-01', 'cx-r207-t12-01', 'cx-r203-t12-01', 'cx-r201-t12b-01', 'cx-r208-t12b-01', 'cx-r204-t12b-01', 'cx-r200-c31t12-01']
LOAD = re.compile(r'native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
keys = collections.defaultdict(set)
for r in runs:
    for l in open(E + r + '/capture/run-output.txt', errors='replace'):
        m = LOAD.search(l)
        if m: keys[m.group(1)].add(r.split('-')[1])
r101 = set(open('/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram/vq16-r101.txt').read().split())
res101 = set(l.split('\t')[0] for l in open('/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram/resident/r101.tsv').read().splitlines()[1:])
stats = collections.Counter(); cand = []; byf = collections.Counter()
for k, rooms in sorted(keys.items()):
    kk = tuple(int(x, 16) for x in k.split('-'))
    src = 'pak' if kk in pak else 'loose'
    if src == 'pak': blob = pak[kk]
    else:
        p = FIX.get('dc/tex/%s/%s.re4tex' % (k[0], k))
        if not p: stats['nofile'] += 1; continue
        blob = open(p, 'rb').read()
    try: w, h, fmt, flags, extra = vq.read_package(blob)
    except Exception as e: stats['unreadable:' + str(e)[:40]] += 1; continue
    byf[(src, fmt)] += 1
    stats[src] += 1
    if k in res101: stats['in_r101_resident'] += 1
    cand.append((k, src, w, h, fmt, flags, len(blob), sorted(rooms), k in res101))
print(stats); print(byf)
json.dump(cand, open('/root/probe/lanes-20261015/castle/vq-c31-cands.json', 'w'))
big = sorted(cand, key=lambda c: -c[6])[:25]
for c in big: print(c)
