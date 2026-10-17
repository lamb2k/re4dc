#!/usr/bin/env python3
"""disc_pack.py --fixture F.json --pkg-src DIR --out DIR [--psnr 29] [--min-bytes 16384] [--core r000.tsv] [--dry]
(lane pak17, 2026-10-16; offline data, private outputs: nothing produced here belongs in Git)

One disc's loose textures into its tex.pak (the VRAM rule: textures in the pack, VQ by default). The disc is the
package fixture F (t11-fix.py) over the package base tree DIR (t16-package.sh PKG_SRC): its loose dc/tex/<c>/<key>.re4tex
are the base tree's files minus F's removals plus F's staged ones; its pack is F's dc/tex.pak (else the base's).
Per loose key:
  - in the pack already: the loose copy is dropped (native_ui.cpp looks the pack up first, texpack::find before the
    loose path, so the loose copy is never read; same bytes or not, the pack's package is the one in use);
  - not in the pack, a single-texture twiddled 16-bit package of at least --min-bytes, opaque (RGB565, or ARGB1555 /
    ARGB4444 with every texel at full alpha) and not a UI picture (the core HUD set --core, sub screen / item / font
    sources): re-encoded as full-codebook VQ (vq_native_ui.encode, the vq_pak.py method: same key, size, format and
    material name); kept 16-bit when the PSNR is below --psnr;
  - every other package goes into the pack as it is.
Output (DIR): tex.pak (texpack.py build + verify), base.json (the input pack's and every loose source's sha256),
loose-keys.txt (every loose disc path the pack now holds: t11-fix.py
drops them from the disc), vq-keys.txt, report.json (per key: class, bytes, PSNR), SUMMARY.txt. --dry classifies only."""
import argparse, hashlib, json, re, struct, sys, tempfile
from pathlib import Path
T = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(T)); sys.path.insert(0, str(T / 'd367')); sys.path.insert(0, str(T / 'd367' / 'vram'))
import vq_native_ui as vq   # noqa: E402
import texpack             # noqa: E402
from vq_pak import restamp, read_pak  # noqa: E402
tpl = vq.tpl
NAME = re.compile(r'^dc/tex/[0-9a-f]/([0-9a-f]{8}-[0-9a-f]{8})\.re4tex$')
UI_SRC = re.compile(r'(items|/ss/|subscreen|sub-screen|font|hud|menu|manual|/ui[-/_])', re.I)
sec = lambda n: (n + 2047) // 2048 * 2048


def disc_files(fix, src):
    rm = set(fix.get('remove', []))
    loose = {}
    for p in sorted((src / 'dc' / 'tex').rglob('*.re4tex')):
        d = 'dc/tex/' + p.relative_to(src / 'dc' / 'tex').as_posix()
        if NAME.match(d) and d not in rm:
            loose[d] = str(p)
    for d, s in fix['replace'].items():
        if isinstance(s, str) and NAME.match(d):
            loose[d] = s
    pak = fix['replace'].get('dc/tex.pak', str(src / 'dc' / 'tex.pak'))
    return loose, pak


def opaque(fmt, texels):
    if fmt == tpl.FORMAT_RGB565:
        return True
    if fmt == tpl.FORMAT_ARGB1555:
        return all(v & 0x8000 for v in texels)
    if fmt == tpl.FORMAT_ARGB4444:
        return all((v & 0xF000) == 0xF000 for v in texels)
    return False


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    a.add_argument('--fixture', required=True); a.add_argument('--pkg-src', required=True, type=Path)
    a.add_argument('--out', required=True, type=Path); a.add_argument('--psnr', type=float, default=29.0)
    a.add_argument('--min-bytes', type=int, default=16384); a.add_argument('--core', action='append', default=[])
    a.add_argument('--pvrtex', default=vq.PVRTEX); a.add_argument('--dry', action='store_true')
    o = a.parse_args(argv)
    fix = json.load(open(o.fixture))
    loose, pakp = disc_files(fix, o.pkg_src)
    blob = Path(pakp).read_bytes(); texpack.verify(blob)
    pkgs = read_pak(blob)
    core = {l.split()[0] for f in o.core for l in open(f) if l.strip() and not l.startswith(('#', 'key'))}
    rows, add, vqk = [], {}, []
    work = Path(tempfile.mkdtemp(prefix='disc_pack-'))
    (work / 'src').mkdir(); (work / 'vq').mkdir(); (work / 'prev').mkdir()
    for d, s in sorted(loose.items()):
        name = NAME.match(d).group(1); k = tuple(int(x, 16) for x in name.split('-'))
        b = Path(s).read_bytes()
        row = dict(key=name, disc=d, src=s, bytes=len(b), disc_bytes=sec(len(b)))
        if k in pkgs:
            row['cls'] = 'in-pak-same' if pkgs[k] == b else 'in-pak-other'
            rows.append(row); continue
        try:
            w, h, fmt, flags, texels = vq.read_package(b)
        except ValueError as e:
            row.update(cls='as-is', why=str(e)); add[k] = b; rows.append(row); continue
        row.update(w=w, h=h, fmt=vq.FORMAT_NAMES.get(fmt, fmt))
        why = None
        if w * h * 2 < o.min_bytes:
            why = 'small'
        elif name in core or UI_SRC.search(s):
            why = 'ui'
        elif not opaque(fmt, texels):
            why = 'alpha'
        if why or o.dry:
            row.update(cls='as-is-16' if why else 'vq-candidate', why=why); add[k] = b; rows.append(row); continue
        (work / 'src' / (name + '.re4tex')).write_bytes(b)
        e = vq.encode(name, work / 'src', work / 'vq', o.pvrtex, (w, h), work / 'prev')
        row['psnr'] = e['psnr_db']
        if e['psnr_db'] < o.psnr:
            row.update(cls='as-is-16', why='psnr'); add[k] = b; rows.append(row); continue
        new, rule = restamp(b, (work / 'vq' / (name + '.re4tex')).read_bytes())
        row.update(cls='vq', vq_bytes=len(new), crc_rule=rule, vram_before=w * h * 2, vram_after=e['after_vram'])
        add[k] = new; vqk.append(name); rows.append(row)
    o.out.mkdir(parents=True, exist_ok=True)
    cls = {}
    for r in rows:
        c = cls.setdefault(r['cls'], [0, 0, 0]); c[0] += 1; c[1] += r['disc_bytes']
        c[2] += sec(r.get('vq_bytes', r['bytes'])) if r['cls'] not in ('in-pak-same', 'in-pak-other') else 0
    lines = ['disc_pack: fixture %s, base %s, pack %s (%d keys, %d B)' % (o.fixture, o.pkg_src, pakp, len(pkgs), len(blob)),
             'loose keys %d, %d B on disc (2 KiB sectors)' % (len(rows), sum(r['disc_bytes'] for r in rows))]
    for c, (n, b, p) in sorted(cls.items()):
        lines.append('  %-14s %5d keys  loose %11d B  -> pack %11d B' % (c, n, b, p))
    why = {}
    for r in rows:
        if r.get('why'):
            why[r['why']] = why.get(r['why'], 0) + 1
    lines.append('  kept 16-bit / as-is reasons: %s' % why)
    if not o.dry:
        allp = dict(pkgs); allp.update(add)
        out, _ = texpack.build(allp); texpack.verify(out)
        (o.out / 'tex.pak').write_bytes(out)
        (o.out / 'loose-keys.txt').write_text(''.join(r['disc'] + '\n' for r in rows))
        (o.out / 'vq-keys.txt').write_text(''.join(k + '\n' for k in sorted(vqk)))
        # what the pack was built from: t11-fix.py drop_loose refuses a fixture whose other sets now stage another
        # pack or other loose bytes (rebuild with this tool then)
        (o.out / 'base.json').write_text(json.dumps(dict(
            pak=hashlib.sha256(blob).hexdigest(), out=hashlib.sha256(out).hexdigest(),
            loose={r['disc']: hashlib.sha256(Path(r['src']).read_bytes()).hexdigest() for r in rows}), indent=1) + '\n')
        lines.append('tex.pak %d keys, %d B, sha256 %s (was %d keys, %d B)' % (len(allp), len(out),
                     hashlib.sha256(out).hexdigest(), len(pkgs), len(blob)))
        ps = [r['psnr'] for r in rows if r['cls'] == 'vq']
        if ps:
            lines.append('VQ %d keys, PSNR %.1f..%.1f dB, VRAM %d -> %d B' % (len(ps), min(ps), max(ps),
                         sum(r['vram_before'] for r in rows if r['cls'] == 'vq'), sum(r['vram_after'] for r in rows if r['cls'] == 'vq')))
    (o.out / 'report.json').write_text(json.dumps(dict(summary=lines, rows=rows), indent=1) + '\n')
    (o.out / 'SUMMARY.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
