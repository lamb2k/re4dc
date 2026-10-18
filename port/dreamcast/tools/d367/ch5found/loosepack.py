"""loosepack.py (lane ch5found16 round 3, MEASURE + MODELLED): disc 1 (test 15 RC) loose dc/tex keys vs its tex.pak.
For every loose key: in the pak or not; same bytes or not; for keys not in the pak, the package's format and the
modelled full-codebook VQ size (vq_pak.py rule: 2048 + w*h/4 texel bytes, same header). Disc bytes count 2 KiB sectors
(ISO 9660 files and RE4PAK1 entries are both 2 KiB aligned). Output: a summary + loosepack.json (per key)."""
import collections, glob, hashlib, json, struct, sys
sys.path.insert(0, '/root/probe/lanes-20261016/ch5found/tree/port/dreamcast/tools')
import vq_native_ui as vq
tpl = vq.tpl
MAN = json.load(open('/mnt/c/tmp/ch5/t15rc.manifest.json'))
PAK = '/root/probe/lanes-20261015/t15k/data/vq16cs/tex-vq16c.pak'
blob = open(PAK, 'rb').read()
assert hashlib.sha256(blob).hexdigest() == MAN['dc/tex.pak']['sha256']
magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', blob, 0)
pak = {}
for i in range(count):
    c, f, o, n = struct.unpack_from('<4I', blob, ioff + 16 * i)
    pak['%08x-%08x' % (c, f)] = blob[o:o + n]
# loose package bytes: the RC runs' fixtures (matched by the manifest's sha256)
src = {}
for st in glob.glob('/mnt/c/Flycast-Evidence/re4-dreamcast/t15rc-20261016/*/stage.json'):
    for k, v in json.load(open(st)).get('fixture', {}).get('replace', {}).items():
        if k.startswith('dc/tex/'): src.setdefault(k, v)
sec = lambda n: (n + 2047) // 2048 * 2048
rows = []; S = collections.Counter(); N = collections.Counter(); fmts = collections.Counter()
FMT = {getattr(tpl, a): a[7:] for a in dir(tpl) if a.startswith('FORMAT_')}
for k, m in sorted(MAN.items()):
    if not k.startswith('dc/tex/'): continue
    key = k.rsplit('/', 1)[1][:-7]
    disc = sec(m['size'])
    if key in pak:
        same = hashlib.sha256(pak[key]).hexdigest() == m['sha256']
        cat = 'in pak, same bytes' if same else 'in pak, different bytes (pak wins)'
        rows.append(dict(key=key, cat=cat, size=m['size'], pak_size=len(pak[key])))
        S[cat] += disc; N[cat] += 1; continue
    p = src.get(k)
    try:
        b = open(p, 'rb').read() if p else None
    except OSError:
        b = None
    if b is None or hashlib.sha256(b).hexdigest() != m['sha256']:
        S['not in pak, source not found'] += disc; N['not in pak, source not found'] += 1
        rows.append(dict(key=key, cat='not in pak, source not found', size=m['size'])); continue
    try:
        w, h, fmt, flags, _ = vq.read_package(b)
        vqs = len(b) - w * h * 2 + 2048 + w * h // 4
        cat = 'not in pak, 16-bit twiddled (VQ candidate)'
        fmts['%s %dx%d' % (FMT.get(fmt, fmt), w, h)] += 1
        S['vq: pak entry bytes after VQ'] += sec(vqs)
        rows.append(dict(key=key, cat=cat, size=m['size'], w=w, h=h, fmt=FMT.get(fmt, fmt), vq_size=vqs))
    except ValueError as e:
        cat = 'not in pak, other format (pack as is)'
        S['as-is: pak entry bytes'] += sec(len(b))
        rows.append(dict(key=key, cat=cat, size=m['size'], why=str(e)))
    S[cat] += disc; N[cat] += 1
tot = sum(sec(m['size']) for k, m in MAN.items() if k.startswith('dc/tex/'))
print('loose keys %d, %.2f MB on disc (2 KiB sectors); pak %d keys %.2f MB' % (sum(N.values()), tot / 1e6, count, len(blob) / 1e6))
for c in N: print('  %-48s %5d keys %8.2f MB' % (c, N[c], S[c] / 1e6))
for c in ('vq: pak entry bytes after VQ', 'as-is: pak entry bytes'): print('  %-48s %8.2f MB' % (c, S[c] / 1e6))
print('  top VQ candidate shapes:', fmts.most_common(8))
json.dump(dict(summary={c: [N[c], S[c]] for c in N}, rows=rows), open('/mnt/c/tmp/ch5/loosepack.json', 'w'), indent=1)
