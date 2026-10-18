"""c3r_vq34.py TREE BASEPAK LOOSEMAP.json OUTDIR: ch3found vqsel34.py + c115/c116 replay (tex-c34.pak).
LOOSEMAP: {key: path of the verified (target-sha) loose 16-bit file of the ch3found fixture}."""
import json, re, sys, collections, pathlib, glob, subprocess
T = sys.argv[1] + '/port/dreamcast/tools'
sys.path[:0] = [T, T + '/d367', T + '/d367/vram']
import vq_native_ui as vq, texpack
import convert_tpl as tpl
from vq_pak import read_pak
pak = read_pak(open(sys.argv[2], 'rb').read())
loose = json.load(open(sys.argv[3]))
W = pathlib.Path(sys.argv[4]); W.mkdir(parents=True, exist_ok=True)
LOAD = re.compile(r'native UI: load /cd/dc/tex/./([0-9a-f]{8}-[0-9a-f]{8})\.re4tex')
keys = collections.defaultdict(set)
for log in glob.glob('/mnt/c/Flycast-Evidence/re4-dreamcast/ch3found-20261016/h-cxc3fmW/scenarios/cx-r2*/capture/run-output.txt'):
    room = log.split('/cx-')[1][:4]
    for l in open(log, errors='replace'):
        m = LOAD.search(l)
        if m: keys[m.group(1)].add(room)
fx = set(l.split('\t')[0] for l in open('/mnt/c/Game Dev/Emulators/re4-assets-private/ps2lib/effects-tex/KEYS.tsv'))
done = set()
for f in glob.glob(T + '/d367/vram/vq16-*.txt'):
    if f.endswith('vq16-c34.txt'): continue
    done |= set(l.split()[0] for l in open(f) if l.strip() and not l.startswith('#'))
st = collections.Counter(); cand = []; src = dict(pak)
for k, rooms in sorted(keys.items()):
    kk = tuple(int(x, 16) for x in k.split('-'))
    if kk in pak: st['in_t15_pak'] += 1; continue
    p = loose.get(k)
    if not p: st['nofile'] += 1; continue
    blob = open(p, 'rb').read()
    try: w, h, fmt, flags, _ = vq.read_package(blob)
    except Exception: st['not16'] += 1; continue
    if k in done: st['already_vq_list'] += 1; continue
    if k in fx: st['fx'] += 1; continue
    if fmt != tpl.FORMAT_RGB565: st['alpha_fmt'] += 1; continue
    if w < 64 or h < 64: st['small'] += 1; continue
    cand.append((k, w, h, sorted(rooms))); src[kk] = blob
print(dict(st), 'selected', len(cand), 'VRAM 16-bit', sum(w * h * 2 for _, w, h, _ in cand), [c[0] for c in cand])
out, _ = texpack.build(src); texpack.verify(out); (W / 'src.pak').write_bytes(out)
subprocess.check_call([sys.executable, T + '/d367/vram/vq_pak.py', str(W / 'src.pak'), str(W / 'vq.pak'), str(W / 'work')] + [c[0] for c in cand],
                      stdout=open(W / 'vq.log', 'w'), stderr=subprocess.STDOUT)
s = read_pak((W / 'src.pak').read_bytes()); vqp = read_pak((W / 'vq.pak').read_bytes())
r = json.load(open(W / 'work/vq-report.json'))
nm = lambda e: e.get('key') or e.get('name')
for e in r['images']:
    if e['psnr_db'] < 29.0:
        kk = tuple(int(x, 16) for x in nm(e).split('-')); vqp[kk] = s[kk]
out, _ = texpack.build(vqp); texpack.verify(out); (W / 'tex-c34.pak').write_bytes(out)
import hashlib; print('tex-c34', len(out), hashlib.sha256(out).hexdigest()[:16], [(nm(e), round(e['psnr_db'], 1)) for e in r['images']])
