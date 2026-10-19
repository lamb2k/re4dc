#!/usr/bin/env python3
"""ps2_mask_runs.py: an alpha-mask (hair) run for a PS2 cast section (lane ps2cast-3, 2026-10-11).

The PS2 TPLs are opaque, so a PS2 cast mesh draws its hair cards as solid geometry where the GC source draws them with
an alpha mask (GC BIN part material bit 2: colour image + I4 mask image, drawn as a second, blended pass). This tool
gives the PS2 section the GC look for those cards without changing its geometry:

1. classify: every triangle of the section's runtime chunk (FE/v3 blob in castmodel_runtime.h) whose rest-pose centroid
   lies within --max-mm of a GC triangle of a masked GC material (closest GC triangle of the GC section) is a hair
   triangle; every other triangle stays in the opaque run (same atlas, same UV words);
2. hair UVs: the hair triangles' atlas UVs are mapped affinely from their atlas bounding box onto a small texture
   (--size, default the GC hair image size) - new UV words for the hair run only;
3. bake: for every texel of that texture covered by a hair triangle (2x2 supersamples), the surface point is projected
   to the closest GC triangle of a masked material and the GC colour image and I4 mask are sampled there
   (ps2_gctex_bake.py's transfer), then dilated;
4. pair: an ARGB4444 package exactly as the runtime's masked materials (native_ui.cpp model_mask_key: key = CRC-32 /
   FNV-1a of "R4MPv001" + colour key + mask key; texel = colour >> 4 per channel | mask // 17 << 12, charbake's hair
   pairs). The colour and mask keys are content keys of the baked images; only the pair package is staged;
5. runs: the opaque and the hair triangle lists restripified by the cl lane's fastpath build_blob.py (as cb_hair.py),
   each checked to keep its exact oriented triangle multiset; the hair list keeps the PS2 chunk order (source order)
   for its translucent draw; coincident triangles (the same three positions) across the two runs are listed (real
   hardware breaks equal-depth ties by order: the opaque run draws first, so a coincident pair keeps a fixed order).

--atlas-rgba <png> (lane ps2cast 2026-10-14, Ashley): the PS2 texture's own alpha instead of the GC bake. The cast's atlas
with the PS2 alpha (ps2_ashley.py atlas-rgba.png: PS2 alpha 0x80 = 255) decides and paints the run: a triangle is a hair
triangle when the atlas alpha under it (corners, edge midpoints, centroid) falls below 128 anywhere, and the pair texture
samples the atlas colour + alpha at each texel's original UV. --atlas-alpha-threshold 255 also preserves
partially transparent PS2 surfaces (default 128 retains the existing hair-card classification). Used where the PS2 moved alpha cards into a section whose
GC source has several masked materials (Ashley's PS2 hair in GC extra 9). The GC arguments are still read for the record.

Output (<out>/): mask-runs.json (section, triangles per run, keys, coincidence report, inputs), opaque.blob, hair.blob,
hair.uv (u16 pairs / 32768), colour.png, mask.png, pair.png, <pair key>.re4tex.
Usage (Windows Python, numpy + PIL):
  python ps2_mask_runs.py <cast dir> <gc em.drs> <gc bin arc> <gc tpl arc> <section> <out> [--size 64x128] [--max-mm 8]
  --multi-mask (lane geodrop17, 2026-10-17): a GC section with several masked materials (the r320 helicopter em3d body:
  colours 1 / 3 / 20, masks 2 / 4 / 21) bakes them all into the one pair texture (needs --size); each texel samples the
  colour + mask images of the masked GC triangle it projects to. The runtime still sees one mask run per section.
"""
import argparse, hashlib, importlib.util, json, os, struct, sys, tempfile, zlib
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'd367'), str(HERE / 'd367' / 'charbake'), str(HERE.parents[2] / 'tools')]
import ps2_gctex_bake as bk  # noqa: E402
import model_registry as mr  # noqa: E402
import cb_tex as T  # noqa: E402
from cb_blob import Blob, canon  # noqa: E402
import convert_tpl, drs  # noqa: E402

STORE = Path(os.environ.get('RE4_PRIVATE', 'C:/Game Dev/Emulators/re4-assets-private'))
FASTPATH = STORE / 'character-prototype-20260925/tools/fastpath/build_blob.py'


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fnv1a32(b):
    h = 2166136261
    for x in b:
        h = ((h ^ x) * 16777619) & 0xffffffff
    return h


def content_key(tag, b):
    data = tag.encode() + b
    return zlib.crc32(data) & 0xffffffff, fnv1a32(data)


def pair_key(colour, mask):
    data = b'R4MPv001' + struct.pack('<4I', colour[0], colour[1], mask[0], mask[1])
    return zlib.crc32(data) & 0xffffffff, fnv1a32(data)


def build_run(bb, tris, pos, nrm, uv, flags, bounds):
    with tempfile.TemporaryDirectory(prefix='maskrun-') as d:
        d = Path(d)
        corners = [c for t in tris for c in t]
        (d / 'info0.gx').write_bytes(bytes([0x90]) + struct.pack('>H', len(corners)) + b''.join(struct.pack('>3H', *c) for c in corners))
        (d / 'info0.pos').write_bytes(pos); (d / 'info0.nrm').write_bytes(nrm); (d / 'info0.uv').write_bytes(uv)
        ch = bb.Chunk(bb.load_chunk(d, 0))
    best = None
    for mode in ('boundary', 'near', 'palette'):
        for wd in (0.0, 0.02, 0.1):
            metas = bb.build(ch, mode, wd, 8)
            cst, st = bb.cost(metas)
            if best is None or cst < best[0]:
                best = (cst, metas, mode, wd)
    blob = bytearray(bb.assemble(ch, best[1]))
    blob[2] = flags; blob[16:32] = bounds  # the chunk's flags and whole-chunk bounds (one fog / cull decision)
    blob = bytes(blob) + bytes((-len(blob)) % 32)
    nb = Blob(blob)
    got = sorted(canon(t) for t in nb.triangles() if t is not None)
    if got != sorted(canon(t) for t in tris) or any(t is None for t in nb.triangles()):
        raise SystemExit('run triangle set / winding changed')
    return blob, dict(seed=best[2], w_dist=best[3], **{k: v for k, v in nb.stats().items() if k not in ('triangles', 'bytes')})


def main():
    ap = argparse.ArgumentParser()
    for k in ('cast', 'drs', 'bin', 'tpl', 'section', 'out'):
        ap.add_argument(k)
    ap.add_argument('--size'); ap.add_argument('--max-mm', type=float, default=8.0); ap.add_argument('--ss', type=int, default=2)
    ap.add_argument('--atlas-rgba')
    ap.add_argument('--atlas-alpha-threshold', type=int, default=128,
                    help='classify atlas triangles below this alpha (default 128; 255 also preserves partial alpha)')
    ap.add_argument('--multi-mask', action='store_true', help='bake every masked GC material of the section into one pair')
    a = ap.parse_args()
    if not 1 <= a.atlas_alpha_threshold <= 255:
        ap.error('--atlas-alpha-threshold must be in 1..255')
    if a.atlas_alpha_threshold != 128 and not a.atlas_rgba:
        ap.error('--atlas-alpha-threshold needs --atlas-rgba')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cast = Path(a.cast); sec = int(a.section)
    man = json.loads((cast / 'manifest.json').read_text())
    hdr = cast / man['levels']['conservative']['runtime_header']
    chunks, bones = mr.parse_header(str(hdr))
    c = [x for x in chunks if x['source_info'] == sec][0]
    shift = int(json.loads((cast / 'validation.json').read_text()).get('position_shift', 4))
    blob = Blob(c['stream'])
    tris = [t for t in blob.triangles() if t is not None]
    P = np.asarray([struct.unpack_from('<3h', c['positions'], 8 * k) for k in range(c['position_count'])], float) / (1 << shift)
    UV = np.asarray([struct.unpack_from('<2H', c['uv'], 4 * k) for k in range(len(c['uv']) // 4)], float) / 32768.0
    db = Path(a.drs).read_bytes(); g = drs.Drs(db)
    tims = convert_tpl.parse_tpl(g.entries[int(a.tpl, 0) - 4][1])
    imgs = [np.asarray(convert_tpl.decode_image(t), float).reshape(t.height, t.width, 4) for t in tims]
    S = bk.gc_section(g.entries[int(a.bin, 0) - 4][1], tims)
    masked = S['alpha'] >= 0
    if not masked.any():
        raise SystemExit('the GC section has no masked material')
    colour_ids = sorted(set(S['mat'][masked].tolist())); mask_ids = sorted(set(S['alpha'][masked].tolist()))
    atlas = None
    if a.atlas_rgba:
        atlas = np.asarray(Image.open(a.atlas_rgba).convert('RGBA'), float)
        if not a.size:
            raise SystemExit('--atlas-rgba needs --size')
        ci = mi = -1
    elif len(colour_ids) != 1 or len(mask_ids) != 1:
        # several masked GC materials (lane geodrop17, the em3d helicopter: colours 1 / 3 / 20, masks 2 / 4 / 21): one hair
        # run and one pair texture for all of them; each texel samples the colour + mask images of the masked GC triangle
        # it projects to (its own material), so the runtime's single mask pair per section is unchanged
        if not a.multi_mask:
            raise SystemExit(f'one masked GC material expected: colour {colour_ids} mask {mask_ids} (--multi-mask bakes all)')
        if not a.size:
            raise SystemExit('--multi-mask needs --size')
        ci = mi = -1
    else:
        ci, mi = colour_ids[0], mask_ids[0]
    W, H = (map(int, a.size.split('x')) if a.size else (tims[ci].width, tims[ci].height))
    cen = S['v'].mean(1)

    def closest(p, sel=None):
        idx = np.arange(len(cen)) if sel is None else np.nonzero(sel)[0]
        d2 = ((p[:, None, :] - cen[None, idx, :]) ** 2).sum(2)
        kk = min(24, len(idx)); cand = idx[np.argpartition(d2, kk - 1, axis=1)[:, :kk]]
        best_d = np.full(len(p), np.inf); best_t = np.zeros(len(p), int); best_b = np.zeros((len(p), 3))
        for j in range(kk):
            ti = cand[:, j]
            q, b = bk.closest_point_tri(p, S['v'][ti, 0], S['v'][ti, 1], S['v'][ti, 2])
            d = np.linalg.norm(q - p, axis=1); better = d < best_d
            best_d[better] = d[better]; best_t[better] = ti[better]; best_b[better] = b[better]
        return best_d, best_t, best_b
    tc = np.asarray([P[[k[0] for k in t]].mean(0) for t in tris])
    if atlas is not None:
        # the PS2 alpha under the triangle: corners, edge midpoints and centroid of its atlas UVs
        wts = np.asarray([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0], [0, .5, .5], [.5, 0, .5], [1 / 3, 1 / 3, 1 / 3]])
        hair = np.asarray([bk.sample(atlas, wts @ UV[[k[2] for k in t]])[:, 3].min() < a.atlas_alpha_threshold for t in tris])
        d = np.zeros(len(tris))
    else:
        # The GC projection is unused by --atlas-rgba, whose source alpha
        # completely determines the run. Avoid its quadratic scratch there.
        d, ti, _ = closest(tc)
        hair = masked[ti] & (d <= a.max_mm)
    H_tris = [t for t, h in zip(tris, hair) if h]; O_tris = [t for t, h in zip(tris, hair) if not h]
    if not H_tris:
        raise SystemExit('no PS2 triangle lies on a masked GC material')
    # hair UVs: the hair triangles' UV islands (connected through shared UV words) keep their shape and are packed
    # (shelves, tallest first, 2-texel gutters) into the hair texture at the largest uniform scale that fits
    huv = np.asarray([UV[k[2]] for t in H_tris for k in t])
    lo, hi = huv.min(0), huv.max(0)
    parent = {}
    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for t in H_tris:
        for k in t[1:]:
            parent[find(k[2])] = find(t[0][2])
    islands = {}
    for t in H_tris:
        islands.setdefault(find(t[0][2]), set()).update(k[2] for k in t)
    isl = []
    for r_, s_ in islands.items():
        pts = np.asarray([UV[j] for j in s_]); isl.append((sorted(s_), pts.min(0), pts.max(0)))
    def pack(scale):
        x = y = rowh = 0.0; place = []
        for ids, mn, mx in sorted(isl, key=lambda e: -(e[2][1] - e[1][1])):
            w_ = (mx[0] - mn[0]) * scale + 2; h_ = (mx[1] - mn[1]) * scale + 2
            if w_ > W or h_ > H: return None
            if x + w_ > W: x, y, rowh = 0.0, y + rowh, 0.0
            if y + h_ > H: return None
            place.append((ids, mn, x + 1, y + 1)); x += w_; rowh = max(rowh, h_)
        return place
    s_lo, s_hi = 1.0, 65536.0
    for _ in range(40):
        mid = (s_lo + s_hi) / 2
        if pack(mid): s_lo = mid
        else: s_hi = mid
    scale = s_lo; place = pack(scale)
    newuv = {}
    for ids, mn, ox, oy in place:
        for j in ids:
            newuv[j] = ((UV[j][0] - mn[0]) * scale + ox) / W, ((UV[j][1] - mn[1]) * scale + oy) / H
    nuv, nmap = [], {}
    H_new = []
    for t in H_tris:
        nt = []
        for (vi, ni, tj) in t:
            if tj not in nmap:
                nmap[tj] = len(nuv); nuv.append(newuv[tj])
            nt.append((vi, ni, nmap[tj]))
        H_new.append(tuple(nt))
    nuv = np.asarray(nuv)
    t_old_uv = {id(nt): np.asarray([UV[k[2]] for k in ot]) for nt, ot in zip(H_new, H_tris)}
    uvb = b''.join(struct.pack('<2H', *(int(round(x * 32768)) for x in np.clip(u, 0, 1))) for u in nuv)
    # bake the GC colour + mask onto the hair texture
    acc = np.zeros((H, W, 3)); msk = np.zeros((H, W)); cnt = np.zeros((H, W))
    for t in H_new:
        v = P[[k[0] for k in t]]; uvp = nuv[[k[2] for k in t]] * [W * a.ss, H * a.ss]
        x0, y0 = np.floor(uvp.min(0)).astype(int) - 1; x1, y1 = np.ceil(uvp.max(0)).astype(int) + 1
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        q = np.stack([xs.ravel(), ys.ravel()], 1)
        Tm = np.array([[uvp[1, 0] - uvp[0, 0], uvp[2, 0] - uvp[0, 0]], [uvp[1, 1] - uvp[0, 1], uvp[2, 1] - uvp[0, 1]]])
        if abs(np.linalg.det(Tm)) < 1e-9:
            continue
        l = np.linalg.solve(Tm, (q - uvp[0]).T).T
        b = np.stack([1 - l[:, 0] - l[:, 1], l[:, 0], l[:, 1]], 1)
        ins = (b >= -1e-6).all(1) & (q[:, 0] >= 0) & (q[:, 1] >= 0) & (q[:, 0] < W * a.ss) & (q[:, 1] < H * a.ss)
        if not ins.any():
            continue
        b = np.clip(b[ins], 0, None); b /= b.sum(1, keepdims=True); q = q[ins]
        p = b @ v
        if atlas is not None:
            # the texel's original atlas UV (the island map is affine per triangle): colour + PS2 alpha
            ouv = b @ t_old_uv[id(t)]
            px = bk.sample(atlas, ouv); col = px[:, :3]; alv = px[:, 3]
        else:
            dd, tt, bb_ = closest(p, masked)
            guv = (bb_[:, :, None] * S['uv'][tt]).sum(1)
            if ci >= 0:
                col = bk.sample(imgs[ci], guv); al = bk.sample(imgs[mi], guv)
                alv = al[:, 3] if (imgs[mi][..., 3] < 255).any() else al[:, :3].mean(1)
            else:
                col = np.zeros((len(p), 4)); alv = np.zeros(len(p))
                for c_, m_ in sorted(set(zip(S['mat'][tt].tolist(), S['alpha'][tt].tolist()))):
                    sel = (S['mat'][tt] == c_) & (S['alpha'][tt] == m_)
                    col[sel] = bk.sample(imgs[c_], guv[sel]); al = bk.sample(imgs[m_], guv[sel])
                    alv[sel] = al[:, 3] if (imgs[m_][..., 3] < 255).any() else al[:, :3].mean(1)
        tx = (q[:, 0] // a.ss).astype(int); ty = (q[:, 1] // a.ss).astype(int)
        np.add.at(acc, (ty, tx), col[:, :3]); np.add.at(msk, (ty, tx), alv); np.add.at(cnt, (ty, tx), 1)
    cov = cnt > 0
    rgb = np.zeros((H, W, 3)); am = np.zeros((H, W))
    rgb[cov] = acc[cov] / cnt[cov, None]; am[cov] = msk[cov] / cnt[cov]
    filled = cov.copy()
    for _ in range(6):
        nb = np.zeros((H, W, 3)); nm = np.zeros((H, W)); nc = np.zeros((H, W))
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sf = np.roll(filled, (dy, dx), (0, 1)); nb += np.roll(rgb, (dy, dx), (0, 1)) * sf[..., None]
            nm += np.roll(am, (dy, dx), (0, 1)) * sf; nc += sf
        grow = (~filled) & (nc > 0)
        rgb[grow] = nb[grow] / nc[grow, None]; am[grow] = nm[grow] / nc[grow]; filled |= grow
    rgb8 = np.clip(rgb + 0.5, 0, 255).astype(np.uint8); a8 = np.clip(am + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(rgb8, 'RGB').save(out / 'colour.png'); Image.fromarray(a8, 'L').save(out / 'mask.png')
    ck = content_key('ps2mask/colour/', rgb8.tobytes()); mk = content_key('ps2mask/mask/', a8.tobytes()); pk = pair_key(ck, mk)
    tex16 = ((a8.astype(np.uint16) // 17) << 12) | ((rgb8[..., 0].astype(np.uint16) >> 4) << 8) | \
            ((rgb8[..., 1].astype(np.uint16) >> 4) << 4) | (rgb8[..., 2].astype(np.uint16) >> 4)
    pkg = T.package_twiddled16('ps2mask_' + cast.name.replace('-', '_')[:50], tex16, T.ARGB4444)
    pname = '%08x-%08x.re4tex' % pk
    (out / pname).write_bytes(pkg)
    Image.fromarray(np.dstack([rgb8, a8]), 'RGBA').save(out / 'pair.png')
    # runs
    spec = importlib.util.spec_from_file_location('build_blob', FASTPATH); bb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bb)
    flags, bounds = c['stream'][2], c['stream'][16:32]
    # a section whose every PS2 triangle lies on a masked GC material (the zealot accessories 0x20F / 0x217) has no
    # opaque run: mask_only (NATIVE_MODEL_REGISTRY_POOL packages; the pinned Luis hair is ps2_luis_mask.py's)
    oblob, ost = build_run(bb, O_tris, c['positions'], c['normals'], c['uv'], flags, bounds) if O_tris else (b'', {})
    hblob, hst = build_run(bb, H_new, c['positions'], c['normals'], uvb, flags, bounds)
    (out / 'opaque.blob').write_bytes(oblob); (out / 'hair.blob').write_bytes(hblob); (out / 'hair.uv').write_bytes(uvb)
    # coincidence: triangles over the same three positions (rounded to 1/16 mm) across and within the runs
    def pkey(t):
        return tuple(sorted(tuple(P[k[0]]) for k in t))
    groups = {}
    for tag, lst in (('opaque', O_tris), ('hair', H_tris)):
        for k, t in enumerate(lst):
            groups.setdefault(pkey(t), []).append((tag, k))
    co = [gr for gr in groups.values() if len(gr) > 1]
    cross = [gr for gr in co if len({x[0] for x in gr}) > 1]
    rep = dict(tool='tools/ps2_mask_runs.py', cast=str(cast), header_sha256=sha(hdr.read_bytes()), section=sec,
               **({'mask_only': True} if not O_tris else {}),
               source='atlas-rgba ' + sha(Path(a.atlas_rgba).read_bytes()) if atlas is not None else 'gc-bake',
               gc=dict(drs_sha256=sha(db), bin=a.bin, tpl=a.tpl, colour_image=ci, mask_image=mi,
                       **({'masked_materials': [list(x) for x in sorted(set(zip(S['mat'][masked].tolist(), S['alpha'][masked].tolist())))]}
                          if ci < 0 and atlas is None else {}),
                       masked_triangles=int(masked.sum()), triangles=len(S['v'])),
               triangles=dict(chunk=len(tris), opaque=len(O_tris), hair=len(H_tris)), max_mm=a.max_mm,
               hair_distance_mm=dict(median=float(np.median(d[hair])), max=float(d[hair].max())),
               hair_atlas_bbox=[float(x) for x in (*lo, *hi)], uv_islands=len(isl), uv_scale_texels_per_uv=round(scale, 3), texture=dict(width=W, height=H, covered=int(cov.sum()),
               punched=int(((a8 < 128) & cov).sum())),
               keys=dict(colour='%08x-%08x' % ck, mask='%08x-%08x' % mk, pair='%08x-%08x' % pk),
               pair_package=dict(file=pname, sha256=sha(pkg), bytes=len(pkg), vram_bytes=W * H * 2, format='ARGB4444 twiddled'),
               runs=dict(opaque=dict(triangles=len(O_tris), bytes=len(oblob), sha256=sha(oblob), **ost),
                         hair=dict(triangles=len(H_tris), bytes=len(hblob), sha256=sha(hblob), uv_bytes=len(uvb), **hst)),
               coincident=dict(groups=len(co), cross_material=len(cross), cross_examples=cross[:8]),
               fastpath_sha256=sha(FASTPATH.read_bytes()))
    if atlas is not None and a.atlas_alpha_threshold != 128:
        rep['atlas_alpha_threshold'] = a.atlas_alpha_threshold
    (out / 'mask-runs.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('triangles', 'hair_distance_mm', 'texture', 'keys', 'coincident')}, indent=1))


if __name__ == '__main__':
    main()
