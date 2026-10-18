"""c3r_split91.py TOOLS MISSING COVER CH2DIR PAK...: split ch3found's uncovered dc/tex keys: in a pak (shadowed),
key file in the ch2 data set (covered; same sha or not), or a real gap."""
import collections, hashlib, json, os, sys
T, mj, cj, ch2 = sys.argv[1:5]; paks = sys.argv[5:]
sys.path[:0] = [T + '/d367', T + '/d367/vram', T]
from vq_pak import read_pak
m = json.load(open(mj))['ch3found-20261016']; c = json.load(open(cj))
miss = {p: v['sha256'] for p, v in m.items() if p.startswith('dc/tex/') and 'ch3found-20261016|' + p not in c}
inpak = set()
for pk in paks: inpak |= set('%08x-%08x' % k for k in read_pak(open(pk, 'rb').read()))
c2 = {}
for r, _, fs in os.walk(ch2):
    for f in fs:
        if f.endswith('.re4tex'): c2.setdefault(f[:-7].lower(), os.path.join(r, f))
st = collections.defaultdict(list)
for p, s in sorted(miss.items()):
    k = p.split('/')[-1][:-7]
    if k in inpak: st['shadowed'].append(k)
    elif k in c2: st['ch2 same' if hashlib.sha256(open(c2[k], 'rb').read()).hexdigest() == s else 'ch2 other'].append(k)
    else: st['gap'].append(k)
for t, v in st.items(): print(t, len(v), ' '.join(v[:40]))
json.dump(st, open(os.path.join(os.path.dirname(mj), 'split91.json'), 'w'), indent=0)
