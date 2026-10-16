"""lostpart.py: automatic lost-part check for a reduced PS2 world (worldtest16, coordinator 10-16).

    python lostpart.py OUTDIR --name NAME --orig MESH R4PW --red MESH R4PW --walk WALK.json [--room r101] [--cams]

Compares an original world package (level 0) with a reduced one (its level 0: e.g. a ps2-wv5.re4mesh) part by part,
offline. Works across batching / strip grouping (no part identity needed in the reduced file): every reduced triangle is
matched by texture key (R4PW crc, fnv, pass) and world position.

Pieces: every (placement, part) of the original (a part is one texture of one mesh, so fused meshes are already split
by texture) is further split into connected pieces (shared world vertex positions).

Checks per piece:
 1. Orthographic silhouettes along X, Y and Z (the +/- views of an unculled silhouette are the same, so 6 axes = 3),
    128 px on the piece's longest side. coverage = share of the piece's silhouette pixels still covered by reduced
    triangles of the same texture whose box meets the piece's box (1 px tolerance). Thin pixels = silhouette pixels a
    3x3 opening removes (rails, planks, posts, crossbars seen side-on); thin coverage = their covered share.
 2. Walk-path cameras (--cams): the room's sheet cameras plus door arrivals and enemy set positions x 8 yaws, 320x240,
    painter's order for the original; per piece, its visible pixels in the original vs those still covered by reduced
    triangles of the same texture drawn alone (no occlusion, so a changed occluder is not a lost part; 1 px tolerance).

Flag (FAIL) when, on the worst axis with a real silhouette, coverage < --cov (0.90) or thin coverage < --thin-cov (0.75),
and the loss is visible from the walk path: lost pixels scaled to the screen at the piece's walk-path distance
(640x480, focal 514.7, distance floor 1500 mm) reach --min-px (4 px^2), or a camera loses >= --cam-px (20) of the
piece's pixels with retained < 50%. Output: OUTDIR/NAME.json (all pieces' numbers), NAME.txt (PASS/FAIL list),
NAME-flags.png (thumbnails: original silhouette white, reduced red, kept overlap yellow).
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, r'C:\Game Dev\Emulators\room-budget-20261015\in')
from r4im_pkg import Pkg  # noqa: E402

FOCAL = 514.7


def wsl(p):
    return r'\\wsl.localhost\Ubuntu-24.04' + p.replace('/', '\\') if p.startswith('/root/') else p


def load(mesh, r4pw, pieces=False):
    """World triangles (N,3,3) float64, texture key per triangle, and (if pieces) piece ids + piece records."""
    p = Pkg(wsl(mesh), wsl(r4pw))
    keys = {}
    T, K, PC = [], [], []
    recs = []
    for pi, pl in enumerate(p.placements):
        mesh_ = p.meshes[pl['mesh']]
        M = p.wq(pl)
        for k in range(mesh_['part_count']):
            part = mesh_['first_part'] + k
            pm = p.pmeta[part]
            key = keys.setdefault((pm['crc'], pm['fnv'], pm['pass_']), len(keys))
            fc, cc = p.plod[part]
            tris = []
            for c in range(fc, fc + cc):
                cl = p.clusters[c]
                fm, mc, _ = p.levels[cl['first_level']]
                for li in range(fm, fm + mc):
                    corners, tt = p.let_tris(li)
                    if not tt:
                        continue
                    w = corners[:, :3].astype(np.float64) @ M[:, :3].T + M[:, 3]
                    tris.append(w[np.array(tt, dtype=np.int64)])
            if not tris:
                continue
            tris = np.concatenate(tris)
            if pieces:
                q = np.round(tris.reshape(-1, 3)).astype(np.int64)
                _, inv = np.unique(q, axis=0, return_inverse=True)
                inv = inv.reshape(-1, 3)
                par = list(range(inv.max() + 1))

                def find(x):
                    while par[x] != x:
                        par[x] = par[par[x]]
                        x = par[x]
                    return x
                for a, b, c in inv:
                    ra = find(a)
                    for x in (b, c):
                        rx = find(x)
                        if rx != ra:
                            par[rx] = ra
                roots = np.array([find(a) for a in inv[:, 0]])
                for r in np.unique(roots):
                    sel = roots == r
                    recs.append(dict(placement=pi, part=part, bin=mesh_['bin'], key=key, ntri=int(sel.sum())))
                    PC.append(np.full(int(sel.sum()), len(recs) - 1))
                    T.append(tris[sel]); K.append(np.full(int(sel.sum()), key))
            else:
                T.append(tris); K.append(np.full(len(tris), key))
    T = np.concatenate(T); K = np.concatenate(K)
    return p, keys, T, K, (np.concatenate(PC) if pieces else None), recs


def erode(m):
    o = m.copy()
    o[1:, :] &= m[:-1, :]; o[:-1, :] &= m[1:, :]; o[:, 1:] &= m[:, :-1]; o[:, :-1] &= m[:, 1:]
    o[1:, 1:] &= m[:-1, :-1]; o[:-1, :-1] &= m[1:, 1:]; o[1:, :-1] &= m[:-1, 1:]; o[:-1, 1:] &= m[1:, :-1]
    return o


def dilate(m):
    o = m.copy()
    o[1:, :] |= m[:-1, :]; o[:-1, :] |= m[1:, :]; o[:, 1:] |= m[:, :-1]; o[:, :-1] |= m[:, 1:]
    o[1:, 1:] |= m[:-1, :-1]; o[:-1, :-1] |= m[1:, 1:]; o[1:, :-1] |= m[:-1, 1:]; o[:-1, 1:] |= m[1:, :-1]
    return o


def raster(tris2d, w, h):
    im = Image.new('1', (w, h), 0)
    d = ImageDraw.Draw(im)
    for t in tris2d:
        d.polygon([(float(t[0, 0]), float(t[0, 1])), (float(t[1, 0]), float(t[1, 1])), (float(t[2, 0]), float(t[2, 1]))], fill=1, outline=1)
    return np.array(im, dtype=bool)


AXES = (('X', (2, 1)), ('Y', (0, 2)), ('Z', (0, 1)))


def ortho(piece_tris, red_tris, lo, hi, res=128):
    out = []
    for name, (u, v) in AXES:
        ext = max(hi[u] - lo[u], hi[v] - lo[v], 1.0)
        s = (res - 4) / ext
        w = int((hi[u] - lo[u]) * s) + 5; h = int((hi[v] - lo[v]) * s) + 5
        def P(t):
            q = np.empty(t.shape[:2] + (2,))
            q[..., 0] = (t[..., u] - lo[u]) * s + 2
            q[..., 1] = (hi[v] - t[..., v]) * s + 2
            return q
        mo = raster(P(piece_tris), w, h)
        mr = raster(P(red_tris), w, h) if len(red_tris) else np.zeros((h, w), bool)
        mrd = dilate(mr)
        n = int(mo.sum())
        cov = float((mo & mrd).sum()) / n if n else 1.0
        thin = mo & ~dilate(erode(mo))
        nt = int(thin.sum())
        tcov = float((thin & mrd).sum()) / nt if nt else 1.0
        area_mm2 = n / (s * s)
        out.append(dict(axis=name, px=n, cov=cov, thin_px=nt, thin_cov=tcov, area_mm2=area_mm2, mo=mo, mr=mr))
    return out


class Walk:
    def __init__(self, path):
        sys.path.insert(0, wsl('/root/probe/worldtest16-20261016/tree/port/dreamcast/tools'))
        import ps2_world_vert_ladder as L
        pts = json.load(open(wsl(path)))['points']
        self.f = L.WalkField(pts)

    def dist(self, p):
        return self.f.dist(*p)


def cameras(room):
    """price2.py's sheet cameras + roomproj door arrivals / enemy set positions, 8 yaws each (Leon's rig)."""
    import importlib.util
    sp = importlib.util.spec_from_file_location('rp', r'C:\Game Dev\Emulators\room-budget-20261015\roomproj.py')
    rp = importlib.util.module_from_spec(sp); sp.loader.exec_module(rp)
    import ast, re
    src = open(r'C:\Game Dev\Emulators\worldtest-20261016\scripts\price2.py').read()
    CAMS = ast.literal_eval(re.search(r'CAMS = (\{.*?\})\n', src, re.S).group(1))
    cams = []
    for x, y, z, yaw in CAMS.get(room, []):
        cams.append(('cam', np.array([x, y, z], float), yaw))
    pts = [('door', np.array(d['pos'], float)) for d in rp.doors().get(room, [])]
    pts += [('em%02x' % e['id'], np.array(e['pos'], float) * 10.0) for e in rp.esl_positions().get(room, [])]
    for n, P in pts:
        for k in range(8):
            cams.append((n, P, 2 * math.pi * k / 8))
    out = []
    for n, P, yaw in cams:
        fwd, right, up = rp.basis(P, yaw, rp.PITCH)
        eye = P + np.array([0, rp.EYE_UP, 0]) - fwd * rp.EYE_BACK + right * rp.EYE_RIGHT
        out.append((n, eye, fwd, right, up, yaw))
    return out


def render_ids(T, ids, eye, fwd, right, up, W=320, H=240, far=25000.0, near=300.0):
    """Painter's-order id buffer (value = id + 1). Triangles crossing the near plane are clipped (Sutherland-Hodgman),
    not dropped: reduced triangles are larger and would otherwise vanish near the camera."""
    f = FOCAL * H / 480.0
    d = T - eye
    z = d @ fwd; x = d @ right; y = d @ up
    inside = z > near
    keep = inside.any(1) & (z.min(1) < far)
    idx = np.nonzero(keep)[0]
    order = idx[np.argsort(-z[idx].mean(1))]
    im = Image.new('I', (W, H), 0)
    dr = ImageDraw.Draw(im)
    full = inside.all(1)
    for i in order:
        if full[i]:
            pts = [(W / 2 + f * x[i, k] / z[i, k], H / 2 - f * y[i, k] / z[i, k]) for k in range(3)]
        else:
            poly = []
            for k in range(3):
                k2 = (k + 1) % 3
                a_in, b_in = inside[i, k], inside[i, k2]
                if a_in:
                    poly.append((x[i, k], y[i, k], z[i, k]))
                if a_in != b_in:
                    t = (near - z[i, k]) / (z[i, k2] - z[i, k])
                    poly.append((x[i, k] + t * (x[i, k2] - x[i, k]), y[i, k] + t * (y[i, k2] - y[i, k]), near))
            pts = [(W / 2 + f * px / pz, H / 2 - f * py / pz) for px, py, pz in poly]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(xs) < 0 or min(xs) > W or max(ys) < 0 or min(ys) > H:
            continue
        if max(abs(v) for v in xs + ys) > 1e5:
            pts = [(min(max(px, -1e5), 1e5), min(max(py, -1e5), 1e5)) for px, py in pts]
        dr.polygon([(float(px), float(py)) for px, py in pts], fill=int(ids[i]) + 1)
    return np.array(im, dtype=np.int64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir'); ap.add_argument('--name', required=True)
    ap.add_argument('--orig', nargs=2, required=True); ap.add_argument('--red', nargs=2, required=True)
    ap.add_argument('--walk', required=True); ap.add_argument('--room')
    ap.add_argument('--cams', action='store_true')
    ap.add_argument('--cov', type=float, default=0.90); ap.add_argument('--thin-cov', type=float, default=0.75)
    ap.add_argument('--min-px', type=float, default=4.0); ap.add_argument('--cam-px', type=int, default=20)
    ap.add_argument('--thin-min', type=int, default=8, help='thin pixels needed before thin coverage counts')
    ap.add_argument('--box', help='x0,x1,y0,y1,z0,z1: also list every piece inside (validation)')
    a = ap.parse_args()
    t0 = time.time()
    od = Path(a.outdir); od.mkdir(parents=True, exist_ok=True)
    po, ko, TO, KO, PC, recs = load(*a.orig, pieces=True)
    pr, kr, TR, KR, _, _ = load(*a.red)
    # map reduced keys onto original key ids (unknown keys never match)
    kmap = {v: ko.get(k, -1) for k, v in kr.items()}
    KR = np.array([kmap[k] for k in KR])
    print('%s: original %d tris %d pieces, reduced %d tris (%.0f s)' % (a.name, len(TO), len(recs), len(TR), time.time() - t0), flush=True)
    walk = Walk(a.walk)
    rlo = TR.min(1); rhi = TR.max(1)
    order = np.argsort(PC, kind='stable')
    starts = np.searchsorted(PC[order], np.arange(len(recs) + 1))
    res = []
    for i, r in enumerate(recs):
        tt = TO[order[starts[i]:starts[i + 1]]]
        lo = tt.reshape(-1, 3).min(0); hi = tt.reshape(-1, 3).max(0)
        ext = float((hi - lo).max()); mg = max(20.0, 0.02 * ext)
        sel = (KR == r['key']) & (rlo <= hi + mg).all(1) & (rhi >= lo - mg).all(1)
        ax = ortho(tt, TR[sel], lo, hi)
        c = (lo + hi) / 2
        dist = max(walk.dist(c), 1500.0)
        sc = FOCAL / dist   # screen px per mm at the walk-path distance
        big = max(x['px'] for x in ax)
        worst = None
        for x in ax:
            if x['px'] < 0.05 * big or x['px'] < 16:
                continue   # edge-on view: no real silhouette
            lost_px = (1 - x['cov']) * x['area_mm2'] * sc * sc
            thin_lost = x['thin_px'] >= a.thin_min and x['thin_cov'] < a.thin_cov
            bad = (x['cov'] < a.cov and lost_px >= a.min_px) or (thin_lost and ext * sc >= 6)
            score = (1 - x['cov']) + (1 - x['thin_cov'])
            if worst is None or score > worst[0]:
                worst = (score, x, lost_px, bad)
        r2 = dict(r, lo=[round(float(v)) for v in lo], hi=[round(float(v)) for v in hi], ext=round(ext), walk_mm=round(dist),
                  axes=[dict(axis=x['axis'], px=x['px'], cov=round(x['cov'], 3), thin_px=x['thin_px'], thin_cov=round(x['thin_cov'], 3)) for x in ax])
        if worst:
            r2.update(cov=round(worst[1]['cov'], 3), thin_cov=round(worst[1]['thin_cov'], 3), lost_screen_px=round(worst[2], 1),
                      ortho_fail=bool(worst[3]), worst_axis=worst[1]['axis'])
            if worst[3]:
                r2['_thumb'] = (worst[1]['mo'], worst[1]['mr'])
        else:
            r2.update(cov=1.0, thin_cov=1.0, lost_screen_px=0.0, ortho_fail=False)
        res.append(r2)
        if i % 500 == 0:
            print('  piece %d/%d (%.0f s)' % (i, len(recs), time.time() - t0), flush=True)
    cam_fail = {}
    PKEY = np.array([r['key'] for r in recs])
    if a.cams and a.room:
        cams = cameras(a.room)
        for ci, (n, eye, fwd, right, up, yaw) in enumerate(cams):
            io = render_ids(TO, PC, eye, fwd, right, up)
            pid = io - 1
            vis = pid >= 0
            if not vis.any():
                continue
            pk = np.full(io.shape, -2, np.int64)
            pk[vis] = PKEY[pid[vis]]
            # the reduced triangles of each visible texture, drawn alone (no occlusion: a part counts as kept where
            # its own texture is still there, whatever now stands in front of it), 1 px tolerance
            match = np.zeros(io.shape, bool)
            for k in np.unique(pk[vis]):
                sel = KR == k
                if not sel.any():
                    continue
                m = render_ids(TR[sel], np.zeros(int(sel.sum()), np.int64), eye, fwd, right, up) > 0
                match |= dilate(m) & (pk == k)
            cnt = np.bincount(pid[vis], minlength=len(recs))
            kept = np.bincount(pid[vis & match], minlength=len(recs))
            for j in np.nonzero(cnt >= a.cam_px)[0]:
                lost = int(cnt[j] - kept[j])
                if lost >= a.cam_px and kept[j] < 0.5 * cnt[j]:
                    f = cam_fail.setdefault(int(j), [])
                    f.append(dict(cam=ci, name=n, yaw=round(yaw, 3), px=int(cnt[j]), kept=int(kept[j])))
            if ci % 10 == 0:
                print('  camera %d/%d (%.0f s)' % (ci, len(cams), time.time() - t0), flush=True)
    for j, f in cam_fail.items():
        res[j]['cam_fail'] = sorted(f, key=lambda x: x['kept'] - x['px'])[:3]
    flagged = [i for i, r in enumerate(res) if r['ortho_fail'] or r.get('cam_fail')]
    flagged.sort(key=lambda i: -(res[i]['lost_screen_px'] + sum(x['px'] - x['kept'] for x in res[i].get('cam_fail', []))))
    # thumbnails
    th = []
    for i in flagged[:60]:
        r = res[i]
        if '_thumb' in r:
            mo, mr = r['_thumb']
        else:
            tt = TO[order[starts[i]:starts[i + 1]]]
            lo = np.array(r['lo'], float); hi = np.array(r['hi'], float)
            ext = float((hi - lo).max()); mg = max(20.0, 0.02 * ext)
            sel = (KR == r['key']) & (rlo <= hi + mg).all(1) & (rhi >= lo - mg).all(1)
            ax = max(ortho(tt, TR[sel], lo, hi), key=lambda x: x['px'])
            mo, mr = ax['mo'], ax['mr']
        img = np.zeros(mo.shape + (3,), np.uint8)
        img[mo] = (255, 255, 255); img[mr] = (200, 40, 40); img[mo & mr] = (240, 220, 60)
        th.append((i, Image.fromarray(img)))
    if th:
        cw, ch = 150, 168
        cols = 6; rows = (len(th) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * cw, rows * ch + 20), (30, 30, 30))
        d = ImageDraw.Draw(sheet)
        d.text((4, 4), '%s: %d flagged pieces (white = original only, yellow = kept, red = reduced only)' % (a.name, len(flagged)), fill=(255, 255, 255))
        for n, (i, im) in enumerate(th):
            r = res[i]
            im.thumbnail((cw - 8, ch - 34))
            x0 = (n % cols) * cw + 4; y0 = (n // cols) * ch + 24
            sheet.paste(im, (x0, y0))
            d.text((x0, y0 + ch - 32), 'bin 0x%x pt %d pl %d' % (r['bin'], r['part'], r['placement']), fill=(255, 255, 255))
            cf = r.get('cam_fail')
            d.text((x0, y0 + ch - 20), 'cov %.2f thin %.2f%s' % (r['cov'], r['thin_cov'], ' cam %d/%d' % (cf[0]['kept'], cf[0]['px']) if cf else ''),
                   fill=(255, 200, 120))
        sheet.save(od / (a.name + '-flags.png'))
    for r in res:
        r.pop('_thumb', None)
    summ = dict(name=a.name, orig=a.orig, red=a.red, pieces=len(res), flagged=len(flagged), verdict='PASS' if not flagged else 'FAIL',
                params=dict(cov=a.cov, thin_cov=a.thin_cov, min_px=a.min_px, cam_px=a.cam_px, thin_min=a.thin_min, cams=a.cams),
                seconds=round(time.time() - t0))
    json.dump(dict(summary=summ, pieces=res), open(od / (a.name + '.json'), 'w'))
    with open(od / (a.name + '.txt'), 'w') as f:
        f.write('LOST-PART CHECK %s: %s (%d of %d pieces flagged)\n' % (a.name, summ['verdict'], len(flagged), len(res)))
        f.write('original %s\nreduced  %s\n' % (' '.join(a.orig), ' '.join(a.red)))
        for i in flagged:
            r = res[i]
            f.write('FAIL bin 0x%02x part %d placement %d tris %d box %s..%s walk %d mm: cov %.2f thin %.2f (%s) lost %.0f screen px%s\n' % (
                r['bin'], r['part'], r['placement'], r['ntri'], r['lo'], r['hi'], r['walk_mm'], r['cov'], r['thin_cov'], r.get('worst_axis', '-'),
                r['lost_screen_px'], ''.join(' | cam %s yaw %.2f %d/%d px' % (c['name'], c['yaw'], c['kept'], c['px']) for c in r.get('cam_fail', []))))
        if a.box:
            b = [float(v) for v in a.box.split(',')]
            f.write('\npieces inside box %s:\n' % a.box)
            for r in res:
                c = [(r['lo'][k] + r['hi'][k]) / 2 for k in range(3)]
                if b[0] <= c[0] <= b[1] and b[2] <= c[1] <= b[3] and b[4] <= c[2] <= b[5] and (r['cov'] < 0.98 or r['thin_cov'] < 0.98):
                    f.write('  bin 0x%02x part %d pl %d tris %d ext %d: cov %.2f thin %.2f %s\n' % (
                        r['bin'], r['part'], r['placement'], r['ntri'], r['ext'], r['cov'], r['thin_cov'], 'FLAG' if (r['ortho_fail'] or r.get('cam_fail')) else ''))
    print('%s: %s, %d of %d pieces flagged (%.0f s)' % (a.name, summ['verdict'], len(flagged), len(res), time.time() - t0))


if __name__ == '__main__':
    main()
