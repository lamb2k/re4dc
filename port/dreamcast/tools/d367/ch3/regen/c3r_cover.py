"""c3r_cover.py: coverage of the missing castle/ch3found targets.
Sources: my WSL lane outputs (hashed), other lanes' SHA256SUMS (ch2regen, ch4regen, cxfix-replay) on C:.
Writes cover.json {disc path: [source path, origin]}; prints per-folder table."""
import collections, hashlib, json, os, re, sys
S = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(os.path.join(S, 'srcmap.json')))
lanes = json.load(open(os.path.join(S, 'missing.json')))
want = collections.defaultdict(list)
for p, v in m.items(): want[v['sha256']].append(p)
found = {}
MINE = r'\\wsl.localhost\Ubuntu-24.04\root\probe\lanes-20261018\ch3regen'
for sub in ['tex1', 'rel', 'pkg', 'aica', 'prepem', 'compact', 'extra']:
    for root, _, fs in os.walk(os.path.join(MINE, sub)):
        for f in fs:
            p = os.path.join(root, f)
            if f.endswith(('.log', '.json', 'manifest')) or not os.path.isfile(p): continue
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            for k in want.get(h, []): found.setdefault(k, (p, 'ch3regen'))
AP = r'C:\Game Dev\Emulators\re4-assets-private'
for lane, sums in [('ch2regen', r'ch2regen-20261018\SHA256SUMS.txt'), ('ch2regen', r'ch2regen-20261018\datasets\SHA256SUMS.txt'),
                   ('ch4regen', r'ch4regen-20261018\SHA256SUMS'), ('cxfix', r'cxfix-replay-20261018\SHA256SUMS')]:
    fp = os.path.join(AP, sums)
    if not os.path.exists(fp):
        for c in (fp + '.txt',):
            if os.path.exists(c): fp = c
    if not os.path.exists(fp): print('no sums', fp); continue
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
    t = collections.Counter(fold(p) for p in ms); g = collections.Counter(fold(p) for p in ms if p in found)
    print(lane, 'missing', len(ms), 'found', sum(g.values()))
    for k in sorted(t): print('  %-12s %5d %5d' % (k, t[k], g[k]))
print('by origin', collections.Counter(v[1] for v in found.values()))
