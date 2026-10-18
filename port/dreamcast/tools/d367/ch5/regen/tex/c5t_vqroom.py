#!/usr/bin/env python3
"""vqroom.py <out.pak> <work dir> <base pak> --fixtures <armed.json>... --logs <run-output.txt>... [--min-bytes N] [--dry]
st3 lane (2026-10-15, CLAUDE.md VRAM rule "shrink before evicting"): every texture the island runs loaded that is a
single twiddled 16-bit package of at least --min-bytes is re-encoded offline as full-codebook VQ (vram12's
vq_native_ui.encode + vq_pak.restamp: same key, size, format, material name and CRC rule). The source package is the
one the runtime reads: the base pak's entry when the key is packed, else the fixture's loose file. Writes a new pak
(base entries + the VQ packages, loose keys added) and vq-report.json (PSNR per key). Images under --min-psnr keep
their 16-bit package. Offline data only."""
import argparse, json, pathlib, re, struct, sys, hashlib
T='/root/probe/lanes-20261018/ch5regen/game-249effe5/port/dreamcast/tools'
sys.path.insert(0, T); sys.path.insert(0, T + '/d367'); sys.path.insert(0, T + '/d367/vram')
import vq_native_ui as vq, texpack, vq_pak
LOAD = re.compile(r'native UI: load \S*/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex (\d+)x(\d+) fmt=(\d+)')
ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('work'); ap.add_argument('base')
ap.add_argument('--fixtures', nargs='+', default=[]); ap.add_argument('--logs', nargs='+', default=[])
ap.add_argument('--min-bytes', type=int, default=8192); ap.add_argument('--min-psnr', type=float, default=26.0)
ap.add_argument('--dry', action='store_true')
a = ap.parse_args()
pkgs = vq_pak.read_pak(open(a.base, 'rb').read())
loose = {}
for f in a.fixtures:
    for k, v in json.load(open(f))['replace'].items():
        if k.startswith('dc/tex/') and k.endswith('.re4tex'): loose.setdefault(k.rsplit('/', 1)[1][:-7], v)
loads = {}; gxfmt = {}; ui = set()
VQ_FMTS = {4, 5, 6, 14}   # GX RGB565 / RGB5A3 / RGBA8 / CMPR sources; C4/C8 and intensity sources stay (palette path)
for lg in a.logs:
    text = open(lg, errors='replace').read()
    bind = text.find('native room identities:')
    for m in LOAD.finditer(text):
        loads[m.group(1)] = loads.get(m.group(1), 0) + 1; gxfmt[m.group(1)] = int(m.group(4))
        if bind < 0 or m.start() < bind: ui.add(m.group(1))   # 2D UI / boot set: loaded before the room binds
work = pathlib.Path(a.work); src = work / 'src-packages'; outd = work / 'vq-packages'; prev = work / 'previews'
for d in (src, outd, prev): d.mkdir(parents=True, exist_ok=True)
cand = []
for key in sorted(loads):
    if key in ui or gxfmt[key] not in VQ_FMTS: continue
    k = tuple(int(x, 16) for x in key.split('-'))
    blob = pkgs.get(k)
    origin = 'pak'
    if blob is None:
        if key not in loose: continue
        blob = open(loose[key], 'rb').read(); origin = 'loose'
    try: w, h, fmt, flags, _ = vq.read_package(blob)
    except Exception: continue
    if w * h * 2 < a.min_bytes or w < 8 or h < 8: continue
    cand.append((key, k, blob, origin, w, h))
print('candidates', len(cand), 'bytes16', sum(c[4] * c[5] * 2 for c in cand))
if a.dry: sys.exit(0)
report = []; added = 0
for key, k, blob, origin, w, h in cand:
    (src / (key + '.re4tex')).write_bytes(blob)
    try:
        e = vq.encode(key, src, outd, vq.PVRTEX, (w, h), prev)
        new, rule = vq_pak.restamp(blob, (outd / (key + '.re4tex')).read_bytes())
    except Exception as ex:
        report.append(dict(key=key, status='encode-failed', error=str(ex))); continue
    e.update(origin=origin, loads=loads[key], crc_rule=rule)
    if e['psnr_db'] < a.min_psnr:
        e['status'] = 'kept-16bit (psnr)'; report.append(e); continue
    (outd / (key + '.re4tex')).write_bytes(new)
    e['status'] = 'vq'; e['package_sha256'] = hashlib.sha256(new).hexdigest()
    added += k not in pkgs
    pkgs[k] = new; report.append(e)
    print('%s %4dx%-4d %-6s %7d -> %6d psnr=%.1f' % (key, w, h, origin, e['before_vram'], e['after_vram'], e['psnr_db']), flush=True)
out, _ = texpack.build(pkgs); texpack.verify(out); open(a.out, 'wb').write(out)
vqd = [e for e in report if e.get('status') == 'vq']
tot = dict(candidates=len(cand), vq=len(vqd), added_keys=added, before_vram=sum(e['before_vram'] for e in vqd),
           after_vram=sum(e['after_vram'] for e in vqd), base=a.base, out=a.out, out_sha256=hashlib.sha256(out).hexdigest())
(work / 'vq-report.json').write_text(json.dumps(dict(summary=tot, images=report), indent=1) + '\n')
print('total', tot)
