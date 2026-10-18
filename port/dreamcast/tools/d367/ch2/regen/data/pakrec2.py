"""pakrec2.py: tex.pak 13340bfa = texpack.build(base ae84c909 + the ch2 chain's keys taken from pak17 (51f1f7a4)).
Key sets: vq16-ch2 / vq16-c31 (stage 1, filtered to keys pak17 changed), vq16-r200t, vq16-r200k, ps2lib wep effect keys."""
import glob, hashlib, importlib.util, itertools, json, os, struct, sys
L = '/root/probe/lanes-20261017r/ch2regen'
S = '/mnt/c/Users/lambd/AppData/Local/Temp/claude/C--Game-Dev-Emulators/c357f0f1-ecb5-45e4-b858-3f1d8ec8cd20/scratchpad/ch2regen'
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
fp = load('fp', L + '/tree/port/dreamcast/tools/d367/fullplay/fp_iso.py'); sys.path.insert(0, L + '/t-2f4a731e/port/dreamcast/tools/d367'); import texpack
T = json.load(open(S + '/need-n3.json'))['need']['dc/tex.pak']
def read(b):
    _, n, io, _, _ = struct.unpack_from('<5I', b, 8)
    return {struct.unpack_from('<2I', b, io + 16 * i): b[struct.unpack_from('<I', b, io + 16 * i + 8)[0]:][:struct.unpack_from('<I', b, io + 16 * i + 12)[0]] for i in range(n)}
B = read(open(L + '/t163/dc/tex.pak', 'rb').read())
tr = fp.Track('/mnt/c/Flycast-Evidence/_disccache/23b02efeb438cd7cc097de7a1ce3924175e7d1aef10efafd9cd7a25715961bc1/track03.iso', 45000)
P = read(next(tr.read_bytes(e, s) for p, e, s in fp.files(tr) if p.lstrip('/').lower() == 'dc/tex.pak'))
def keys(f):
    out = set()
    for l in open(L + '/lists/' + f):
        if l.startswith('#') or not l.strip(): continue
        k = l.split()[0]; out.add((int(k[:8], 16), int(k[9:17], 16)))
    return out
wep = set()
for p in glob.glob('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/wep*/*.re4tex'):
    n = os.path.basename(p)[:-7]; wep.add((int(n[:8], 16), int(n[9:], 16)))
sets = {'ch2': keys(os.environ.get('CH2', 'vq16-ch2.txt')), 'c31': keys(os.environ.get('C31', 'vq16-c31.txt')), 'r200t': keys('vq16-r200t.txt'), 'r200k': keys('vq16-r200k.txt'), 'wep': wep, 'r101': keys('vq17-r101.txt')}
diff = {k for k, v in P.items() if B.get(k) != v}
for n, s in sets.items(): print(n, len(s), 'changed in pak17', len(s & diff))
print('target', T['size'], T['sha256'][:16])
for r in [len(sets) - 1]:
    for combo in itertools.combinations(sorted(sets), r):
        if 'r101' in combo: continue
        M = dict(B)
        for c in combo:
            for k in sets[c] & diff: M[k] = P[k]
        blob, n = texpack.build(M); h = hashlib.sha256(blob).hexdigest()
        tag = 'MATCH' if h == T['sha256'] else ('size-ok' if len(blob) == T['size'] else '')
        print('+'.join(combo), n, len(blob), h[:16], tag)
        if tag == 'MATCH':
            open(L + '/tex-13340bfa.pak', 'wb').write(blob); sys.exit(0)
