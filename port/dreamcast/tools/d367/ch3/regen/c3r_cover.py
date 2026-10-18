"""c3r_cover.py [EXTRA_DIR...]: coverage of the missing castle/ch3found targets, per lane (missing.json shas).
Sources: my WSL lane outputs (hashed), other lanes' SHA256SUMS (ch2regen, ch4regen, cxfix-replay) on C:.
Writes cover.json {"lane|disc path": [source path, origin]}; prints per-folder table."""
import collections, hashlib, json, os, re, sys
S = os.path.dirname(os.path.abspath(__file__))
lanes = json.load(open(os.path.join(S, 'missing.json')))
want = collections.defaultdict(list)
for lane, ms in lanes.items():
    for p, v in ms.items(): want[v['sha256']].append(lane + '|' + p)
found = {}
MINE = r'\\wsl.localhost\Ubuntu-24.04\root\probe\lanes-20261018\ch3regen'
dirs = [os.path.join(MINE, s) for s in ['tex1', 'rel', 'pkg', 'aica', 'prepem', 'compact', 'extra']] + sys.argv[1:]
for d in dirs:
    for root, _, fs in os.walk(d):
        for f in fs:
            p = os.path.join(root, f)
            if f.endswith(('.log', '.json', 'manifest')) or not os.path.isfile(p): continue
            if os.path.getsize(p) > 200 * 1024 * 1024: continue
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            for k in want.get(h, []): found.setdefault(k, (p, 'ch3regen'))
AP = r'C:\Game Dev\Emulators\re4-assets-private'
for lane, sums in [('ch2regen', r'ch2regen-20261018\SHA256SUMS.txt'), ('ch2regen', r'ch2regen-20261018\datasets\SHA256SUMS.txt'),
                   ('ch4regen', r'ch4regen-20261018\SHA256SUMS'), ('ch4regen', r'ch4regen-20261018\SHA256SUMS.txt'),
                   ('cxfix', r'cxfix-replay-20261018\SHA256SUMS')]:
    fp = os.path.join(AP, sums)
    if not os.path.exists(fp): continue
    base = os.path.dirname(fp)
    for line in open(fp, encoding='utf-8', errors='replace'):
        mm = re.match(r'([0-9a-f]{64})\s+\*?(.+)', line.strip())
        if not mm: continue
        for k in want.get(mm.group(1), []): found.setdefault(k, (os.path.join(base, mm.group(2)), lane))
json.dump(found, open(os.path.join(S, 'cover.json'), 'w'), indent=0)
def fold(p):
    parts = p.split('/')
    return parts[0] + '/' + parts[1] if p.startswith('dc/') and len(parts) > 2 else parts[0]
for lane, ms in lanes.items():
    t = collections.Counter(fold(p) for p in ms); g = collections.Counter(fold(p) for p in ms if lane + '|' + p in found)
    print(lane, 'missing', len(ms), 'found', sum(g.values()))
    for k in sorted(t): print('  %-12s %5d %5d' % (k, t[k], g[k]))
print('by origin', collections.Counter(v[1] for v in found.values()))
