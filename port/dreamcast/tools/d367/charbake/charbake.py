#!/usr/bin/env python3
"""charbake (D367, 2026-10-10): offline processing of the Dreamcast character textures.

Windows Python (numpy + PIL) + Blender 5.2 (headless) + the pinned KOS pvrtex in WSL (VQ only).

  charbake.py bake  [char ...]          Blender: ambient occlusion of each character mesh in its bind pose (cached)
  charbake.py build [char ...]          transfer the occlusion onto the runtime atlas, compose every variant, encode
                                        the native packages and previews (deterministic, from the cached bake)
  charbake.py verify [char ...]         rebuild from the cached bake into a temporary dir and compare every byte
  charbake.py pak <base tex.pak> <out tex.pak> <char:variant> ... [--add <char:variant> ...]
                                        a copy of a staged tex.pak with those packages under their ORIGINAL keys
                                        (the staged-asset switch: the ELF and every other package unchanged); after
                                        --add, packages under their own variant keys (CHARBAKE_TOGGLE discs)
  charbake.py table <out charbake_variants.h>
                                        the CHARBAKE_TOGGLE variant table (keys and labels) from charbake.json

Inputs are pinned in charbake.json (paths relative to the private store, sha256 each). The store defaults to
C:/Game Dev/Emulators/re4-assets-private (env CHARBAKE_STORE). Outputs: <store>/charbake-20261010/{cache,out}.
Nothing here reads or writes the game's geometry: the runtime meshes, skeletons, weights, palettes, bounds and
collision are untouched; the only products are texture packages for keys the play recipe already draws.
Private outputs: never commit them; the repo holds this code only.

Shading model (variants in charbake.json): out_linear = albedo_linear * shade, with
  shade = max(prod(1 - k_d * (1 - ao_d)), floor) * (ground + (sky - ground) * (n_y + 1) / 2) * gain
where ao_d is the bind-pose occlusion at distance d (Cycles AO bake on a per-triangle unique layout, averaged over
every surface point that maps to the atlas texel: the source atlases reuse texels for mirrored / repeated parts) and
n_y the up component of the interpolated source normal (the same on mirrored parts, so the term stays consistent).
The runtime draws these characters with constant white vertex colour (SourceLighting enable 0, MODULATE): the
texture is the only shading, so nothing is lit twice.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cb_tex as T  # noqa: E402

STORE = Path(os.environ.get('CHARBAKE_STORE', 'C:/Game Dev/Emulators/re4-assets-private'))
BLENDER = Path(os.environ.get('CHARBAKE_BLENDER', 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
PVRTEX = os.environ.get('CHARBAKE_PVRTEX', '/root/work/kos-re4dc-d336/utils/pvrtex/pvrtex')
LAYOUT_VERSION = 1
GAMMA = 2.2


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def cfg():
    return json.loads((HERE / 'charbake.json').read_text())


def store_file(rel, want=None) -> bytes:
    b = (STORE / rel).read_bytes()
    if want and sha(b) != want:
        raise SystemExit('input changed: %s (sha256 %s, pinned %s)' % (rel, sha(b), want))
    return b


def wsl_path(p: Path) -> str:
    s = str(Path(p).resolve()).replace('\\', '/')
    if s[1] == ':':
        return '/mnt/' + s[0].lower() + s[2:]
    raise SystemExit('not a drive path: %s' % s)


# ------------------------------------------------------------------ layout and bake
def cells(n: int, res: int):
    """Per-triangle unique layout: triangle i owns grid cell i (row-major from the bottom-left), mapped onto the
    cell's lower-left half with a 2-texel border. Returns [n, 3, 2] UVs in Blender convention (v up)."""
    g = 1
    while g * g < n:
        g += 1
    cp = res // g
    m = 2.0
    out = np.zeros((n, 3, 2))
    for i in range(n):
        cx, cy = (i % g) * cp, (i // g) * cp
        out[i] = [[cx + m, cy + m], [cx + cp - m - 1, cy + m], [cx + m, cy + cp - m - 1]]
    return out / res


def bake_dir(c, char, mesh):
    """The bake's cache dir, keyed by its inputs: mesh, infos, job settings, layout and the Blender script (its LF
    form, so a Windows checkout with CRLF line ends finds the same bakes)."""
    job = c['blender_job']
    script = (HERE / 'blender_ao.py').read_bytes().replace(b'\r\n', b'\n')
    key = sha(json.dumps(dict(mesh=mesh['sha256'], bake=mesh['bake_infos'], occ=mesh['occluder_infos'], job=job,
                              layout=LAYOUT_VERSION, script=sha(script)), sort_keys=True).encode())[:16]
    return STORE / c['out'] / 'cache' / char / mesh['name'] / key


def two_sided(positions, tris, eps_mm=0.5):
    """Blender's mesh validation drops a face that repeats another face's vertex set. Cast meshes can carry two-sided
    pairs (em15-0b: 10 cloth triangles, same vertices, reversed winding, own UVs, each with normals along its own
    winding). Each repeat gets its own vertex copies pushed eps_mm along its own face normal, so the pair neither
    merges nor occludes itself (each face's AO hemisphere then points away from its partner). Meshes without repeats
    are unchanged. Returns the (possibly extended) positions; rewrites the repeats' corner vertex indices."""
    pos = [list(p) for p in positions]
    seen = set()
    for t in tris:
        vs = frozenset(c['vertex'] for c in t['corners'])
        if vs not in seen:
            seen.add(vs)
            continue
        a, b, cc = (np.array(pos[c['vertex']], np.float64) for c in t['corners'])
        n = np.cross(b - a, cc - a)
        n /= np.linalg.norm(n)
        for corner in t['corners']:
            pos.append([round(float(x), 4) for x in np.array(pos[corner['vertex']]) + eps_mm * n])
            corner['vertex'] = len(pos) - 1
    return pos


def bake(c, char):
    job = c['blender_job']
    for mesh in c['characters'][char]['meshes']:
        d = bake_dir(c, char, mesh)
        names = ['ao_%03d.npy' % round(x * 1000) for x in job['distances']]
        if all((d / n).exists() for n in names) and (d / 'blender.json').exists():
            print('bake %s/%s: cached %s' % (char, mesh['name'], d.name))
            continue
        d.mkdir(parents=True, exist_ok=True)
        m = json.loads(store_file(mesh['path'], mesh['sha256']))
        bake_tris = [t for t in m['triangles'] if t['source_info'] in mesh['bake_infos']]
        cl = cells(len(bake_tris), job['res'])
        for t, uv in zip(bake_tris, cl):
            for corner, u in zip(t['corners'], uv):
                corner['cell'] = [round(float(u[0]), 7), round(float(u[1]), 7)]
        tris = bake_tris + [t for t in m['triangles'] if t['source_info'] in mesh['occluder_infos']]
        sub = dict(schema=m['schema'], positions_mm=two_sided(m['positions_mm'], tris), triangles=tris)
        (d / 'bakemesh.json').write_text(json.dumps(sub))
        j = dict(job, mesh=str(d / 'bakemesh.json').replace('\\', '/'), out=str(d).replace('\\', '/'),
                 bake_infos=mesh['bake_infos'], occluder_infos=mesh['occluder_infos'])
        (d / 'job.json').write_text(json.dumps(j, indent=1))
        print('bake %s/%s: Blender -> %s' % (char, mesh['name'], d))
        r = subprocess.run([str(BLENDER), '-b', '--factory-startup', '--python', str(HERE / 'blender_ao.py'), '--',
                            str(d / 'job.json')], capture_output=True, text=True)
        (d / 'blender.log').write_text(r.stdout + r.stderr)
        if r.returncode or not all((d / n).exists() for n in names):
            raise SystemExit('Blender bake failed, see %s' % (d / 'blender.log'))


# ------------------------------------------------------------------ transfer onto the atlas
def raster(px, w, h):
    """Sample centres inside a triangle given in pixel coords (top-left origin): ys, xs, barycentrics [n, 3]."""
    x0, y0 = np.floor(px.min(0)).astype(int)
    x1, y1 = np.ceil(px.max(0)).astype(int)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w - 1), min(y1, h - 1)
    if x1 < x0 or y1 < y0:
        return None
    ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    cx, cy = xs + 0.5, ys + 0.5
    (ax, ay), (bx, by), (qx, qy) = px
    den = (by - qy) * (ax - qx) + (qx - bx) * (ay - qy)
    if abs(den) < 1e-12:
        return None
    l0 = ((by - qy) * (cx - qx) + (qx - bx) * (cy - qy)) / den
    l1 = ((qy - ay) * (cx - qx) + (ax - qx) * (cy - qy)) / den
    l2 = 1.0 - l0 - l1
    ok = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
    if not ok.any():
        return None
    return ys[ok], xs[ok], np.stack([l0[ok], l1[ok], l2[ok]], -1)


def bilinear(img, u, v):
    """img [R, R] rows bottom to top; u, v in [0, 1] (v up)."""
    r = img.shape[0]
    x = np.clip(u * r - 0.5, 0, r - 1.001)
    y = np.clip(v * r - 0.5, 0, r - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def transfer(c, char, ss=4):
    """-> dict of float arrays over the atlas: ao_<d> (exposure-weighted mean over the surface samples mapping to the
    texel), ao_<d>_sd (spread between them), ny, cover (sample count)."""
    ch = c['characters'][char]
    at = ch['atlas']
    w, h = at['width'], at['height']
    W, H = w * ss, h * ss
    job = c['blender_job']
    dn = ['ao_%03d' % round(x * 1000) for x in job['distances']]
    acc = {n: np.zeros(h * w) for n in dn}
    acc2 = {n: np.zeros(h * w) for n in dn}
    ny = np.zeros(h * w)
    cnt = np.zeros(h * w)
    uses = np.zeros(h * w)
    for mesh in ch['meshes']:
        d = bake_dir(c, char, mesh)
        maps = {n: np.load(d / (n + '.npy')) for n in dn}
        m = json.loads(store_file(mesh['path'], mesh['sha256']))
        bake_tris = [t for t in m['triangles'] if t['source_info'] in mesh['bake_infos']]
        cl = cells(len(bake_tris), job['res'])
        for t, cuv in zip(bake_tris, cl):
            px = np.array([[cr['uv'][0] * W, cr['uv'][1] * H] for cr in t['corners']])
            r = raster(px, W, H)
            if r is None:
                continue
            ys, xs, bc = r
            tex = (ys // ss) * w + (xs // ss)
            uu = bc @ cuv[:, 0]
            vv = bc @ cuv[:, 1]
            nrm = bc @ np.array([cr['normal'] for cr in t['corners']])
            nl = np.linalg.norm(nrm, axis=1)
            nl[nl == 0] = 1
            # Each use of a texel weighs by its broad exposure: a hidden surface sharing texels with a visible one
            # (a source atlas reuses texels) must not darken the visible one.
            wt = bilinear(maps[dn[-1]], uu, vv) + 0.02
            np.add.at(ny, tex, wt * nrm[:, 1] / nl)
            np.add.at(cnt, tex, wt)
            np.add.at(uses, tex, 1)
            for n in dn:
                val = bilinear(maps[n], uu, vv)
                np.add.at(acc[n], tex, wt * val)
                np.add.at(acc2[n], tex, wt * val * val)
    out = {}
    has = uses > 0
    for n in dn:
        mean = np.where(has, acc[n] / np.maximum(cnt, 1e-9), 1.0)
        var = np.where(has, acc2[n] / np.maximum(cnt, 1e-9) - mean * mean, 0.0)
        out[n] = mean.reshape(h, w)
        out[n + '_sd'] = np.sqrt(np.maximum(var, 0)).reshape(h, w)
    out['ny'] = np.where(has, ny / np.maximum(cnt, 1e-9), 0.0).reshape(h, w)
    out['cover'] = uses.reshape(h, w)
    return out


def dilate(field, mask, steps=6):
    """Fill texels outside mask from covered neighbours (mean of the covered 8-neighbourhood), steps times, so the
    bilinear filter never reads unshaded gutter texels at island borders. Deterministic."""
    f = field.copy()
    m = mask.copy()
    for _ in range(steps):
        s = np.zeros_like(f)
        k = np.zeros_like(f)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                sf = np.roll(np.roll(np.where(m, f, 0.0), dy, 0), dx, 1)
                sm = np.roll(np.roll(m.astype(float), dy, 0), dx, 1)
                s += sf
                k += sm
        grow = (~m) & (k > 0)
        f[grow] = s[grow] / k[grow]
        m = m | grow
    return f, m


def shade_field(tr, spec):
    """The shading factor over the atlas for one variant (1.0 where no surface maps)."""
    covered = tr['cover'] > 0
    s = np.ones_like(tr['ny'])
    for n, k in spec.get('ao', {}).items():
        s = s * (1.0 - float(k) * (1.0 - np.clip(tr[n], 0.0, 1.0)))
    s = np.maximum(s, spec.get('floor', 0.0))
    t = (tr['ny'] + 1.0) * 0.5
    s = s * (spec.get('ground', 1.0) + (spec.get('sky', 1.0) - spec.get('ground', 1.0)) * t) * spec.get('gain', 1.0)
    s = np.where(covered, s, 1.0)
    s, grown = dilate(s, covered)
    return np.where(grown, s, 1.0)


def compose(albedo_rgb, shade):
    lin = np.power(albedo_rgb / 255.0, GAMMA) * shade[..., None]
    return np.clip(np.power(np.clip(lin, 0, 1), 1.0 / GAMMA) * 255.0, 0, 255)


def grade(rgbf, spec):
    """Texel-space gain and tint (spec {"gain": g, "tint": [r, g, b]}), applied to the 0..255 texel values the way the
    GameCube's TEV multiplies a texel by its light colour (the GameCube / Dreamcast ratios are measured on framebuffer
    values, see charbake.json "gcb"). None: unchanged."""
    if not spec:
        return rgbf
    k = float(spec.get('gain', 1.0)) * np.array(spec.get('tint', [1.0, 1.0, 1.0]), np.float64)
    return np.clip(rgbf * k, 0, 255)


# ------------------------------------------------------------------ encoding
def encode_rgb565(base_pkg: bytes, rgbf, quant):
    q = T.quant565(rgbf, quant)
    return T.replace_texels16(base_pkg, q), T.expand16(q, T.RGB565)


def encode_vq(rgbf, name, work: Path, dither=None):
    """pvrtex full-codebook VQ (RGB565) of an 8-bit rendering of rgbf; -> (package, decoded RGBA)."""
    work.mkdir(parents=True, exist_ok=True)
    png = work / 'vq-in.png'
    dt = work / 'vq-out.dt'
    from PIL import Image
    Image.fromarray(np.floor(rgbf + 0.5).astype(np.uint8)).save(png)
    cmd = [PVRTEX, '-i', wsl_path(png), '-o', wsl_path(dt), '-f', 'RGB565', '-c']
    if dither is not None:
        cmd += ['-d', str(dither)]
    r = subprocess.run(['wsl', '-d', 'Ubuntu-24.04', '--'] + cmd, capture_output=True, text=True)
    if r.returncode or not dt.exists():
        raise SystemExit('pvrtex failed: %s %s' % (r.stdout, r.stderr))
    enc = dt.read_bytes()
    pkg = vq_package_from_dt(enc, name)
    _, rgba = T.decode(pkg)
    return pkg, rgba


def vq_package_from_dt(encoded: bytes, material: str) -> bytes:
    """tools/convert_tpl.py package_existing_vq (same checks, same bytes), restated here so this Windows tool runs
    without the repo on its path; verified byte-identical against the cast atlas package (cb_selftest)."""
    import struct
    import zlib
    if len(encoded) < 32 or encoded[:4] != b'DcTx':
        raise ValueError('expected pvrtex DcTx header')
    size, = struct.unpack_from('<I', encoded, 4)
    version, units, book, colors = encoded[8:12]
    width, height, mode = struct.unpack_from('<HHI', encoded, 12)
    fmt = (mode >> 27) & 7
    dims = all(8 <= n <= 1024 and n & (n - 1) == 0 for n in (width, height))
    if (size != len(encoded) or size % 32 or version != 0 or units != 0 or book != 255 or not dims or fmt > 2 or
            not mode & (1 << 30) or mode & ((1 << 31) | (1 << 26) | (1 << 25) | (1 << 11)) or any(encoded[20:32])):
        raise ValueError('unsupported DcTx version, layout, size or codebook')
    expected = 2048 + width * height // 4
    native = {0: T.ARGB1555, 1: T.RGB565, 2: T.ARGB4444}[fmt]
    flags = 0 if fmt == 1 else 1 | (2 if fmt == 0 else 0)
    payload = encoded[32:32 + expected]
    start = T.HEADER.size + T.TEXTURE.size
    desc = T.TEXTURE.pack(material.encode().ljust(64, b'\0'), width, height, native, start, len(payload), flags, T.VQ, 0)
    body = desc + payload
    head = T.HEADER.pack(T.MAGIC, 2, T.HEADER.size, T.TEXTURE.size, 1, T.HEADER.size, start, len(payload),
                         zlib.crc32(body) & 0xffffffff, 1, 0)
    return head + body


# ------------------------------------------------------------------ build
def build(c, char, out_root: Path, quiet=False):
    ch = c['characters'][char]
    at = ch['atlas']
    key = at['key']
    w, h = at['width'], at['height']
    src = store_file(at['source_png'], at['source_png_sha256'])
    from io import BytesIO
    from PIL import Image
    albedo = np.asarray(Image.open(BytesIO(src)).convert('RGB')).astype(np.float64)
    if albedo.shape[:2] != (h, w):
        raise SystemExit('%s: source png %s, atlas %dx%d' % (char, albedo.shape, w, h))
    base_pkg = (STORE / c['out'] / 'src' / (key + '.re4tex')).read_bytes()
    if sha(base_pkg) != at['current_package_sha256']:
        raise SystemExit('%s: current package changed' % char)
    tr = transfer(c, char)
    od = out_root / char
    od.mkdir(parents=True, exist_ok=True)
    rows = {}
    covered = tr['cover'] > 0
    stats = dict(texels=int(w * h), covered=int(covered.sum()))
    for n in tr:
        if n.startswith('ao_') and not n.endswith('_sd'):
            stats[n] = dict(mean=round(float(tr[n][covered].mean()), 4), p05=round(float(np.percentile(tr[n][covered], 5)), 4),
                            spread_between_uses_p95=round(float(np.percentile(tr[n + '_sd'][covered], 95)), 4))
    T.save_png(od / 'cover.png', np.dstack([np.clip(tr['cover'] * 40, 0, 255).astype(np.uint8)] * 3 +
                                           [np.full((h, w), 255, np.uint8)]))
    for vn, v in c['variants'].items():
        spec = v['shade']
        sh = shade_field(tr, spec) if spec else np.ones((h, w))
        rgbf = grade(compose(albedo, sh), v.get('grade'))
        vd = od / vn
        vd.mkdir(exist_ok=True)
        if v.get('payload', at['payload']) == 'rgb565':   # a variant's "payload": "vq" re-encodes a 16-bit atlas
            pkg, rgba = encode_rgb565(base_pkg, rgbf, v.get('quant', 'none'))
        else:
            pkg, rgba = encode_vq(rgbf, T.read_package(base_pkg)['name'], vd / 'work', v.get('vq_dither'))
        (vd / (key + '.re4tex')).write_bytes(pkg)
        T.save_png(vd / 'preview.png', rgba)
        T.save_png(vd / 'shade.png', np.dstack([np.clip(sh * 200, 0, 255).astype(np.uint8)] * 3 +
                                               [np.full((h, w), 255, np.uint8)]))
        rows[vn] = dict(key=key, package_sha256=sha(pkg), bytes=len(pkg), shade_mean=round(float(sh[covered].mean()), 4),
                        shade_p05=round(float(np.percentile(sh[covered], 5)), 4),
                        shade_p95=round(float(np.percentile(sh[covered], 95)), 4))
        if not quiet:
            print('%s/%s: %s %s' % (char, vn, rows[vn]['package_sha256'][:16], rows[vn]))
    man = dict(tool='tools/d367/charbake/charbake.py', character=char, atlas=at, stats=stats, variants=rows,
               bakes={m['name']: str(bake_dir(c, char, m).relative_to(STORE)).replace('\\', '/') for m in ch['meshes']},
               config_sha256=sha((HERE / 'charbake.json').read_bytes()))
    (od / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


def build_hair(c, out_root: Path, quiet=False):
    """Leon's hair colour pairs (ARGB4444 64x128: the RGB565 source colour truncated to 4 bits + the I4 mask as
    alpha, as the bundle made them; checked below). A variant with a "hair" grade re-quantises the graded colour
    (nearest 4-bit level) and keeps every alpha nibble. -> manifest."""
    hc = c['hair']
    od = out_root / 'hairtex'
    od.mkdir(parents=True, exist_ok=True)
    src = STORE / c['out'] / 'src'
    rows = {}
    for t in hc['textures']:
        pair = (src / (t['pair'] + '.re4tex')).read_bytes()
        colour = (src / (t['colour'] + '.re4tex')).read_bytes()
        mask = (src / (t['mask'] + '.re4tex')).read_bytes()
        for b, k in ((pair, 'pair_sha256'), (colour, 'colour_sha256'), (mask, 'mask_sha256')):
            if sha(b) != t[k]:
                raise SystemExit('hair %s: %s changed' % (t['pair'], k))
        col8 = T.decode(colour)[1][..., :3].astype(np.float64)
        a4 = (T.decode(mask)[1][..., 3].astype(np.uint16) // 17)

        def pack4444(r4):
            return (a4 << 12) | (r4[..., 0].astype(np.uint16) << 8) | (r4[..., 1].astype(np.uint16) << 4) | r4[..., 2].astype(np.uint16)

        same = T.replace_texels16(pair, pack4444(col8.astype(np.uint16) >> 4))
        if same != pair:
            raise SystemExit('hair %s: the truncated colour + mask does not rebuild the play pair' % t['pair'])
        for vn, v in c['variants'].items():
            if not v.get('hair'):
                continue
            g = grade(col8, v['hair'])
            r4 = np.clip(np.floor(g * 15.0 / 255.0 + 0.5), 0, 15)
            vd = od / vn
            vd.mkdir(exist_ok=True)
            # The pair (what the owner path draws) and the RGB565 colour source (what a source-path hair draw would
            # load through re4dc_actor_hair_texture_key), graded alike.
            for key, pkg in ((t['pair'], T.replace_texels16(pair, pack4444(r4))),
                             (t['colour'], T.replace_texels16(colour, T.quant565(g, 'none')))):
                (vd / (key + '.re4tex')).write_bytes(pkg)
                T.save_png(vd / (key + '.png'), T.decode(pkg)[1])
                rows.setdefault(vn, {})[key] = dict(package_sha256=sha(pkg), bytes=len(pkg))
                if not quiet:
                    print('hair/%s %s: %s' % (vn, key, sha(pkg)[:16]))
    man = dict(tool='tools/d367/charbake/charbake.py', character='hair', textures=hc['textures'], variants=rows,
               config_sha256=sha((HERE / 'charbake.json').read_bytes()))
    (od / 'manifest.json').write_text(json.dumps(man, indent=1))
    return man


def fnv1a32(b: bytes) -> int:
    h = 0x811c9dc5
    for x in b:
        h = ((h ^ x) * 0x01000193) & 0xffffffff
    return h


def variant_key(char, vn):
    """The key a variant's package has on a CHARBAKE_TOGGLE disc (charbake_variants.h): crc32 / fnv1a32 of
    "charbake/<char>/<variant>" (the hair pairs: char "hair0" / "hair1"); never a source texture's key (the pak tool
    refuses a collision)."""
    name = ('charbake/%s/%s' % (char, vn)).encode()
    import zlib
    return zlib.crc32(name) & 0xffffffff, fnv1a32(name)


def pair_key(colour, mask):
    """The key the runtime derives for a colour + mask material pair (native_ui.cpp model_mask_key: CRC-32 / FNV-1a of
    "R4MPv001" + colour crc, fnv, mask crc, fnv as little-endian words); the play hair pairs are exactly this."""
    import struct
    import zlib
    data = b'R4MPv001' + struct.pack('<4I', colour[0], colour[1], mask[0], mask[1])
    return zlib.crc32(data) & 0xffffffff, fnv1a32(data)


def hair_keys(c, vn):
    """[(colour key, pair key)] of the two hair textures for a toggle variant (None: the play keys). A variant's colour
    image gets its own key ("charbake/hair<i>c/<variant>"); its pair key is then the one the runtime derives."""
    out = []
    for i, t in enumerate(c['hair']['textures']):
        if vn is None:
            out.append((T.parse_key(t['colour']), T.parse_key(t['pair'])))
        else:
            ck = variant_key('hair%dc' % i, vn)
            out.append((ck, pair_key(ck, T.parse_key(t['mask']))))
    return out


def cmd_table(c, out):
    """Write game/charbake_variants.h (keys and labels only) from charbake.json "toggle"."""
    lk = T.parse_key(c['characters']['leon']['atlas']['key'])
    gk = T.parse_key(c['characters']['ganado']['atlas']['key'])
    for (ck, pk), t in zip(hair_keys(c, None), c['hair']['textures']):   # the derivation reproduces the play pairs
        if pair_key(ck, T.parse_key(t['mask'])) != pk:
            raise SystemExit('pair key derivation does not reproduce %s' % t['pair'])
    rows = []
    for e in c['toggle']:
        lv, gv, hv = e.get('leon'), e.get('ganado'), e.get('hair')
        l = variant_key('leon', lv) if lv else lk
        g = variant_key('ganado', gv) if gv else gk
        h = hair_keys(c, hv)
        rows.append('    {"%s",0x%08xU,0x%08xU,0x%08xU,0x%08xU,{0x%08xU,0x%08xU},{0x%08xU,0x%08xU},{0x%08xU,0x%08xU},{0x%08xU,0x%08xU}},'
                    '  // leon %s, ganado %s, hair %s' % (
                        e['label'], l[0], l[1], g[0], g[1], h[0][0][0], h[1][0][0], h[0][0][1], h[1][0][1],
                        h[0][1][0], h[1][1][0], h[0][1][1], h[1][1][1], lv or 'play', gv or 'play', hv or 'play'))
    lines = [
        '#pragma once',
        '// charbake (tools/d367/charbake/charbake.py table; charbake.mk CHARBAKE_TOGGLE test builds): the character',
        '// texture variants the look toggle can select. Keys and labels only: the packages are private and a',
        '// CHARBAKE_TOGGLE disc carries them in its tex.pak (charbake.py pak --add). Variant 0 is the play build.',
        '// hair_colour: the keys of the hair colour images; hair_pair: the colour + mask pair keys the runtime derives from',
        '// them (native_ui.cpp model_mask_key), which the hair materials draw.',
        'namespace re4dc_charbake {',
        'struct Variant { char label[4]; unsigned leon_crc, leon_fnv, ganado_crc, ganado_fnv, hair_colour_crc[2], hair_colour_fnv[2],',
        '                 hair_pair_crc[2], hair_pair_fnv[2]; };',
        'constexpr unsigned kLeonCrc=0x%08xU, kLeonFnv=0x%08xU, kGanadoCrc=0x%08xU, kGanadoFnv=0x%08xU;' % (
            lk[0], lk[1], gk[0], gk[1]),
        'constexpr Variant variants[] = {',
    ] + rows + [
        '};',
        'constexpr unsigned kCount = sizeof(variants) / sizeof(variants[0]);',
        '}',
    ]
    text = chr(10).join(lines) + chr(10)
    Path(out).write_bytes(text.encode())
    print('table %s: %d variants' % (out, len(rows)))


def variant_packages(c, char, vn):
    """[(key under which the play build draws it, package path, variant key)] of one char:variant."""
    if char == 'hair':
        d = STORE / c['out'] / 'out' / 'hairtex' / vn
        out = []
        for t, (ck, pk) in zip(c['hair']['textures'], hair_keys(c, vn)):
            out.append((T.parse_key(t['pair']), d / (t['pair'] + '.re4tex'), pk))
            out.append((T.parse_key(t['colour']), d / (t['colour'] + '.re4tex'), ck))
        return out
    at = c['characters'][char]['atlas']
    return [(T.parse_key(at['key']), STORE / c['out'] / 'out' / char / vn / (at['key'] + '.re4tex'), variant_key(char, vn))]


def cmd_pak(c, base, out, specs):
    """specs: <char>:<variant> replaces the package(s) under the play key (a staged-asset switch; char leon, ganado or
    hair); --add then <char>:<variant> ... adds packages under their variant keys (CHARBAKE_TOGGLE discs), keeping the
    originals."""
    changes = {}
    idx = T.pak_index(base)
    add = False
    for s in specs:
        if s == '--add':
            add = True
            continue
        char, vn = s.split(':')
        for play, p, vk in variant_packages(c, char, vn):
            if add:
                k = vk
                if k in idx:
                    raise SystemExit('variant key %s collides with a package of %s' % (T.key_str(k), base))
            else:
                k = play
                if k not in idx:
                    raise SystemExit('%s is not in %s' % (T.key_str(k), base))
            changes[k] = p.read_bytes()
    blob = T.pak_with(base, changes)
    Path(out).write_bytes(blob)
    print('pak %s: %d packages, %d bytes, sha256 %s (%s)' % (out, len(idx) + sum(1 for k in changes if k not in idx),
                                                             len(blob), sha(blob), ' '.join(specs)))


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    c = cfg()
    chars = [x for x in a[1:] if x in c['characters']] if a[1:] else list(c['characters'])
    if a[0] == 'bake':
        for ch in chars:
            bake(c, ch)
    elif a[0] == 'build':
        for ch in chars:
            build(c, ch, STORE / c['out'] / 'out')
        if 'hair' in a[1:] or len(a) == 1:
            build_hair(c, STORE / c['out'] / 'out')
    elif a[0] == 'verify':
        bad = 0
        for ch in chars:
            ref = json.loads((STORE / c['out'] / 'out' / ch / 'manifest.json').read_text())
            tmp = Path(tempfile.mkdtemp(prefix='charbake-verify-'))
            try:
                man = build(c, ch, tmp, quiet=True)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            for vn, r in ref['variants'].items():
                ok = man['variants'].get(vn, {}).get('package_sha256') == r['package_sha256']
                bad += not ok
                print('verify %s/%s: %s' % (ch, vn, 'SAME' if ok else 'DIFFERENT'))
        if 'hair' in a[1:] or len(a) == 1:
            ref = json.loads((STORE / c['out'] / 'out' / 'hairtex' / 'manifest.json').read_text())
            tmp = Path(tempfile.mkdtemp(prefix='charbake-verify-'))
            try:
                man = build_hair(c, tmp, quiet=True)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            for vn, r in ref['variants'].items():
                ok = man['variants'].get(vn) == r
                bad += not ok
                print('verify hair/%s: %s' % (vn, 'SAME' if ok else 'DIFFERENT'))
        if bad:
            raise SystemExit(1)
    elif a[0] == 'pak':
        cmd_pak(c, a[1], a[2], a[3:])
    elif a[0] == 'table':
        cmd_table(c, a[1])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
