"""3-2..3-4 VQ candidates (same rule as vq-c31: 16-bit, >= 64x64, not a PS2 effect key, PSNR >= 29 dB later),
from the castle-c32d runs' loads, against castle-c32d's tex.pak (tex-c31vq.pak) + loose files."""
import json, re, sys, collections, pathlib
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools')
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367')
sys.path.insert(0, '/root/probe/lanes-20261015/castle/tree/port/dreamcast/tools/d367/vram')
import vq_native_ui as vq
from vq_pak import read_pak
L = pathlib.Path('/root/probe/lanes-20261015/castle')
FIX = json.load(open(L / 'fix/castle-c32d.json'))['replace']
pak = read_pak(open(FIX['dc/tex.pak'], 'rb').read())
runs = [l.split() for l in open(sys.argv[1]).read().split('\n') if l.strip()]  # room logpath
LOAD = re.compile(r'native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
keys = collections.defaultdict(set)
for room, log in runs:
    for l in open(log, errors='replace'):
        m = LOAD.search(l)
        if m: keys[m.group(1)].add(room)
fx = set(l.split('\t')[0] for l in open('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/KEYS.tsv'))
done = set((L / 'tree/port/dreamcast/tools/d367/vram/vq16-c31.txt').read_text().split())
stats = collections.Counter(); cand = []
for k, rooms in sorted(keys.items()):
    kk = tuple(int(x, 16) for x in k.split('-'))
    if kk in pak: blob = pak[kk]; src = 'pak'
    else:
        p = FIX.get('dc/tex/%s/%s.re4tex' % (k[0], k))
        if not p: stats['nofile'] += 1; continue
        blob = open(p, 'rb').read(); src = 'loose'
    try: w, h, fmt, flags, extra = vq.read_package(blob)
    except Exception as e: stats['unreadable'] += 1; continue
    if k in done: stats['already_c31'] += 1; continue
    if k in fx: stats['fx'] += 1; continue
    if w < 64 or h < 64: stats['small'] += 1; continue
    cand.append((k, src, w, h, fmt, flags, len(blob), sorted(rooms)))
before = sum(c[2] * c[3] * 2 for c in cand); after = sum(2048 + c[2] * c[3] // 4 for c in cand)
print(stats, 'selected', len(cand), 'VRAM before %d after %d' % (before, after))
print(collections.Counter((c[1], c[4], c[5]) for c in cand))
json.dump(cand, open(L / 'vq-c32-cands.json', 'w'))
(L / 'vq-c32-keys.txt').write_text('\n'.join(c[0] for c in cand) + '\n')
