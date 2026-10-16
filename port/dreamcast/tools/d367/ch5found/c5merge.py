"""ch5found16 island fixture = test 15 mW data (T15_DATA, ch3found's t15-mW.json) + the st3 lane's island room fixture(s).
Rules (mirrors ch3found16's c3merge.py):
  test 15 wins on every shared disc path, except
  dc/tex.pak       -> test 15's; island keys of the st3 VQ pak (tex-st3vq4.pak) it lacks are staged loose (VQ bytes as packed)
  dc/resident.bin  -> r000 core + the island lists (resident_keys.py pack)
  etc/emleon06/07.esl, em/em1d|em1e|em1f.drs, st3/*, rel/st3_*, evd/r3*, dc/movie/r3*, dc/native/r3* -> st3 lane
  st3/<room>.arc|.dar -> the rel33 released archives when they exist (setpak.py's rule)
  dc/warp.txt / padscript / codec_ready -> the FIRST island fixture's (or --warp <file>)
Program files (1ST_READ.BIN, dc/*.ovl) are dropped and re-added from the label's candidate dir.
usage: c5merge.py <t15.json> <st3 armed.json>[,<more>...] <out.json> <candidate dir> <resident.bin> [--warp <warp.txt>]"""
import json, struct, sys, hashlib, re, os, glob
from pathlib import Path
args = sys.argv[1:]
warp = None
if '--warp' in args:
    i = args.index('--warp'); warp = args[i + 1]; del args[i:i + 2]
t15, st3s, out, cand, res = args[:5]
L = Path('/root/probe/lanes-20261016/ch5found')
REL33 = Path('/root/probe/lanes-20261014/st3/rel33')
t = json.load(open(t15)); tr = t['replace']
prog = lambda k: re.match(r'dc/[^/]+\.ovl$', k) or k == '1ST_READ.BIN'
for k in list(tr):
    if prog(k): del tr[k]
ISL = ('etc/emleon06.esl', 'etc/emleon07.esl', 'em/em1d.drs', 'em/em1e.drs', 'em/em1f.drs')
added = 0; removes = set(t.get('remove', [])); first = None; srcs = []
for st3 in st3s.split(','):
    s = json.load(open(st3)); sr = s['replace']; srcs.append(st3)
    if first is None: first = sr
    removes |= set(s.get('remove', []))
    for k, v in sr.items():
        if prog(k) or k in ('dc/tex.pak', 'dc/resident.bin', 'dc/warp.txt', 'dc/padscript.txt', 'dc/codec_ready.txt'):
            continue
        if k not in tr or k in ISL or k.startswith(('st3/', 'rel/st3_', 'evd/r3', 'dc/movie/r3', 'dc/native/r3')):
            if k not in tr: added += 1
            tr[k] = v
for k in ('dc/warp.txt', 'dc/padscript.txt', 'dc/codec_ready.txt'):
    if k in first: tr[k] = first[k]
    else: tr.pop(k, None)
if warp: tr['dc/warp.txt'] = warp
rel = 0
for k in list(tr):
    m = re.match(r'st3/(r3[0-9a-f]{2})\.(arc|dar)$', k)
    if m and (REL33 / ('rel-' + m.group(1)) / 'st3' / ('%s.%s' % m.groups())).exists():
        tr[k] = str(REL33 / ('rel-' + m.group(1)) / 'st3' / ('%s.%s' % m.groups())); rel += 1
tr['dc/resident.bin'] = res
# PAK=<union pak> (tools/pakunion.py: every key of the st3 VQ pak and test 15's, smaller payload on a shared key):
# the island disc's tex.pak; then no st3 key is staged loose.
if os.environ.get('PAK'): tr['dc/tex.pak'] = os.environ['PAK']
def idx(p):
    b = Path(p).read_bytes(); magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0); d = {}
    for i in range(count):
        cc, f, o, n = struct.unpack_from('<4I', b, ioff + 16 * i); d['%08x-%08x' % (cc, f)] = (o, n)
    return b, d
_, ti = idx(tr['dc/tex.pak'])
sb, si = idx('/root/probe/lanes-20261014/st3/vq33/tex-st3vq4.pak')
ld = L / 'fix/st3-pak-loose'; ld.mkdir(parents=True, exist_ok=True)
loose = 0
for k, (o, n) in si.items():
    if k in ti:
        continue
    dest = 'dc/tex/%s/%s.re4tex' % (k[0], k)
    if dest in tr:
        continue  # a loose file already staged (pairs, cast) wins
    f = ld / (k + '.re4tex')
    if not f.exists(): f.write_bytes(sb[o:o + n])
    tr[dest] = str(f); loose += 1
for f in sorted(glob.glob(cand + '/*.ovl')):
    tr['dc/' + os.path.basename(f)] = f
if os.path.exists(cand + '/1ST_READ.BIN'): tr['1ST_READ.BIN'] = cand + '/1ST_READ.BIN'
t['remove'] = sorted(removes - set(tr))
missing = [k for k, v in tr.items() if not Path(v).exists()]
t.setdefault('provenance', {})['ch5found16'] = dict(t15=t15, st3=srcs, st3_added=added, st3_pak_loose=loose, rel33=rel,
    resident=res, warp=warp)
Path(out).write_text(json.dumps(t, indent=1, sort_keys=True) + '\n')
print(out, 'added', added, 'loose', loose, 'rel33', rel, 'missing', missing[:20], len(missing))
