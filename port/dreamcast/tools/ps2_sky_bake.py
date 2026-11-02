#!/usr/bin/env python3
"""SKY_PLAY (lane sky27, 2026-11-02): each room's PS2 sky / backdrop rows -> one panorama for the PVR background plane.

In normal play look A culls the PS2 world at the view distance (18.75 / 25 m), so the room's sky dome, treeline and
backdrop cards (60-400 m out) are never drawn and the clear colour shows where the PS2 shows sky. SKY_PLAY=1
(native_sky.cpp) draws this panorama as the PVR background plane instead of the flat clear colour: the ISP fills it
behind everything for free, so normal play draws no extra geometry.

Rows, by data (no hand list): a row (OBJ group = SMD row = R4PW placement field) is a sky / backdrop row when
  - its median triangle area is >= 30 m^2 (the PS2 authors domes, treelines and backdrop cards as a few huge
    triangles; every play-space row of chapters 1-4 has a median under 30 m^2 except these),
  - it reaches >= 20 m from the room's route graph (RTP points; rooms without an RTP use their up-facing floor), and
  - it spans >= 5 m vertically (not a ground plane).
On r100 / r101 this gives exactly native_static.cpp ps2_sky_row's hand list (r100 2 3 33..37 75, r101 0 1 2).

Bake: the chosen rows only, from the PS2 source (JADERLINK OBJ export: authored vertex colours, GS modulate, TPL
textures), seen from the route graph's centroid, as 6 cube faces with fragments nearer than --near (20 m) left out
(the real world draws what is near; a near card baked in would ghost when Leon stands elsewhere). PS2 fog: the
room's PS2 LIT cut 0 (type, start, end, colour; GX curve) at each fragment's distance; empty directions get the
fog colour (the PS2 clear). Resampled to an equirectangular band (u = yaw = atan2(x, z) / 2 pi, v from --top to
--bottom degrees of elevation) and VQ-encoded RGB565 (1024 x 256: 66 KiB of VRAM).

Output per room: <out>/<room>/ps2-sky.r4sk  (48-byte header + VQ payload) and ps2-sky.png (the decoded panorama),
plus <out>/rows.json (the room / row table with each row's features).
R4SK header (48 bytes, little-endian): magic 'R4SK', u32 version 2, u16 width, u16 height, u32 payload bytes,
f32 top elevation (deg), f32 bottom elevation (deg), f32 eye x, y, z (mm, world), u16 row count, u16 payload offset;
then the sky rows (u16 each = R4PW placement field = OBJ group, zero-padded to 16 bytes), then the payload.
The runtime leaves those rows out of the world while it shows the plane.

usage: ps2_sky_bake.py <extract dir (inputs/ + aux/)> <out dir> [room ...] [--near 20000] [--face 512]
Windows Python (numpy, PIL), like ps2_room_r4im.py.
"""
import argparse, hashlib, json, math, re, struct, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ps2_room_r4im as R  # noqa: E402
import ps2_room_sheet as S  # noqa: E402

AREA_M2, DMAX_M, YSPAN_M = 30.0, 20.0, 5.0
W, H = 1024, 256
TOP, BOTTOM = 80.0, -35.0


def rtp(aux):
    f = next(iter(sorted(aux.glob('*.RTP'))), None)
    if f is None:
        return None
    d = f.read_bytes()
    if d[:4] != b'PTR2':
        return None
    n = struct.unpack_from('<H', d, 6)[0]
    return np.array([struct.unpack_from('<3f', d, 0x20 + 32 * i) for i in range(n)], np.float64) if n else None


def ps2_fog(aux):
    """PS2 LIT (little-endian, the GameCube LIT layout): cut 0 env fog type, start, end (mm), colour."""
    f = next(iter(sorted(aux.glob('*_002.LIT'))), None)
    if f is None:
        return None
    L = f.read_bytes()
    n = struct.unpack_from('<H', L, 0)[0]
    o = struct.unpack_from('<%dI' % n, L, 4)[0]
    rgba = L[o + 0x14:o + 0x18]
    return dict(type=struct.unpack_from('<i', L, o + 8)[0], start=struct.unpack_from('<f', L, o + 12)[0],
                end=struct.unpack_from('<f', L, o + 16)[0], rgb=[rgba[0], rgba[1], rgba[2]])


def gx_fog(fog, z):
    typ, start, end = fog['type'], fog['start'], fog['end']
    if not end > start:
        return (z >= end).astype(np.float64)
    t = np.clip((z - start) / (end - start), 0, 1)
    k = typ & 7
    return (1 - 2 ** (-8 * t) if k == 4 else 1 - 2 ** (-8 * t * t) if k == 5 else
            2 ** (-8 * (1 - t)) if k == 6 else 2 ** (-8 * (1 - t) ** 2) if k == 7 else t)


def rows_of(room, src, pts):
    obj = R.ps.read_obj(src / f'{room}_004.scenario.obj')
    V = np.asarray(obj['v'], np.float64)[:, :3] * 100
    if pts is None:
        # no route graph: up-facing floor triangles in the lowest 30 % of the room stand in for the play space
        T = np.concatenate([V[np.asarray([[c[0] for c in f] for f, _ in g['faces']], int).reshape(-1, 3)]
                            for g in obj['groups'] if g['faces']])
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
        up = n[:, 1] / np.maximum(np.linalg.norm(n, axis=1), 1e-9)
        c = T.mean(1)
        floor = c[(np.abs(up) > 0.9) & (c[:, 1] <= np.percentile(c[:, 1], 30))]
        pts = floor[::max(1, len(floor) // 200)] if len(floor) else c[::max(1, len(c) // 200)]
    rows = []
    for gi, g in enumerate(obj['groups']):
        faces = [[c[0] for c in f] for f, _ in g['faces']]
        if not faces:
            continue
        ix = np.asarray(faces, int).reshape(-1, 3)
        T = V[ix]
        area = np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1) / 2 / 1e6
        P = V[np.unique(ix)]
        d = np.hypot(P[:, None, 0] - pts[None, :, 0], P[:, None, 2] - pts[None, :, 2]).min(1) / 1000
        m = re.search(r'SMD_(\d+)#SMX_(\d+)#TYPE_([0-9A-F]+)#BIN_(\d+)', g['name'])
        r = dict(row=gi, smd=int(m.group(1)), bin=int(m.group(4)), type=m.group(3), tris=len(ix),
                 median_area_m2=round(float(np.median(area)), 1), dmin_m=round(float(d.min()), 1),
                 dmax_m=round(float(d.max()), 1), yspan_m=round(float(np.ptp(P[:, 1])) / 1000, 1),
                 ymax_m=round(float(P[:, 1].max()) / 1000, 1))
        r['sky'] = r['median_area_m2'] >= AREA_M2 and r['dmax_m'] >= DMAX_M and r['yspan_m'] >= YSPAN_M
        rows.append(r)
    return rows, pts


def batches_of(room, src, rows, tex_dir):
    """the sky rows as ps2_room_sheet batches: authored vertex colour (COLOR groups) x texel, the PS2 pass."""
    keep = {r['row'] for r in rows if r['sky']}
    obj = R.ps.read_obj(src / f'{room}_004.scenario.obj')
    mats = R.ps.read_idxmaterial(src / f'{room}_004.scenario.idxmaterial')
    V = np.asarray(obj['v'], np.float64) * 100
    VT = np.asarray(obj['vt'], np.float64) * (255 / 256)
    VC = np.asarray([c if c is not None else (1, 1, 1, 1) for c in obj['vc']], np.float64)
    used, raw = set(), []
    for gi, g in enumerate(obj['groups']):
        if gi not in keep:
            continue
        ix = np.asarray([[c for c in f] for f, _ in g['faces']], int)
        tex = np.array([int(mats[m]['diffuse_map']) for _, m in g['faces']])
        blend = np.array([bool(int(mats[m]['material_flag'], 16) & 4) for _, m in g['faces']])
        pos = V[ix[:, :, 0]][..., :3]
        col = np.concatenate([VC[ix[:, :, 0], :3], VC[ix[:, :, 0], 3:4]], -1)
        raw.append((pos, VT[ix[:, :, 1]], col, tex, blend))
        used |= set(int(t) for t in tex)
    dec = R.tpl.cmd_decode(src / f'{room}_004.TPL', tex_dir, used, False, False, 'gs')
    textures, mode = {}, {}
    for t in used:
        base = next(x for x in dec['textures'] if x['entry'] == t and x['level'] == 'base')
        img = Image.open(tex_dir / base['file'])
        textures[t] = S.Tex(img)
        a = np.unique(np.asarray(img.convert('RGBA'))[..., 3])
        mode[t] = 0 if a.min() == 255 else (1 if np.all(np.isin(a, [0, 255])) else 2)
    batches = []
    for pos, uv, col, tex, blend in raw:
        for t in np.unique(tex):
            for b in (False, True):
                m = (tex == t) & (blend == b)
                if m.any():
                    batches.append((pos[m], uv[m], col[m], int(t), mode[int(t)] if b else 0))
    return batches, textures


def render_face(view, batches, textures):
    """ps2_room_sheet.render with the depth buffer returned (inf = nothing drawn)."""
    rgb = np.zeros((view.h, view.w, 3))
    zb = np.full((view.h, view.w), np.inf, np.float32)
    trs = []
    for P, UV, C, tex, pas in batches:
        X = view.cam(P.reshape(-1, 3)).reshape(-1, 3, 3)
        for i in np.nonzero(X[..., 2].max(1) > view.znear)[0]:
            item = (X[i], UV[i], C[i], tex, pas)
            if pas == 2:
                trs.append(item)
            else:
                S.tri(view, rgb, zb, item, textures, S.ps2_colour, blend=False)
    trs.sort(key=lambda it: -it[0][:, 2].mean())
    for item in trs:
        # a graded layer over nothing would blend with black: it marks the depth where it is opaque enough
        S.tri(view, rgb, zb, item, textures, S.ps2_colour, blend=True)
    return rgb, zb


def bake(room, src, aux, out, near, face):
    pts = rtp(aux)
    rows, walk = rows_of(room, src, pts)
    sky = [r for r in rows if r['sky']]
    info = dict(room=room, route_points=None if pts is None else len(pts), rows=rows, sky_rows=[r['row'] for r in sky])
    if not sky:
        return info
    fog = ps2_fog(aux) or dict(type=0, start=0.0, end=0.0, rgb=[0, 0, 0])
    eye = walk.mean(0) + np.array([0, 1700.0, 0])          # eye height over the play space's centre
    with tempfile.TemporaryDirectory(prefix='skybake-') as td:
        batches, textures = batches_of(room, src, rows, Path(td))
    dirs = [(1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)]
    fogc = np.array(fog['rgb'], float)
    faces = []
    ss = 3                                                  # supersampled faces (the rasteriser samples nearest)
    for d in dirs:
        v = S.View(room, eye, eye + np.array(d, float), face * ss, face * ss, fov=90.0)
        v.znear = near
        rgb, zb = render_face(v, batches, textures)
        # PS2 fog at each fragment's distance from the eye, empty pixels = the fog colour (the PS2 clear)
        gy, gx = np.mgrid[0:v.h, 0:v.w]
        tx, ty = (gx + 0.5 - v.w / 2) / v.k, (v.h / 2 - gy - 0.5) / v.k
        hit = np.isfinite(zb)
        dist = np.where(hit, zb, 0.0) * np.sqrt(1 + tx * tx + ty * ty)
        f = np.clip(gx_fog(fog, dist), 0, 1)[..., None]
        col = np.where(hit[..., None], rgb * (1 - f) + fogc * f, fogc)
        col = col.reshape(face, ss, face, ss, 3).mean((1, 3))
        cov = hit.reshape(face, ss, face, ss).mean((1, 3))
        v = S.View(room, eye, eye + np.array(d, float), face, face, fov=90.0)
        faces.append((v, col, cov))
    # equirect band: texel centre -> direction -> the face it falls in
    u = (np.arange(W) + 0.5) / W * 2 * math.pi
    e = np.radians(TOP + (BOTTOM - TOP) * (np.arange(H) + 0.5) / H)
    yaw, el = np.meshgrid(u, e)
    D = np.stack([np.sin(yaw) * np.cos(el), np.sin(el), np.cos(yaw) * np.cos(el)], -1).reshape(-1, 3)
    pano = np.tile(fogc, (len(D), 1))
    best = np.full(len(D), -np.inf)
    pick = np.zeros(len(D), int)
    for k, (v, _, _) in enumerate(faces):
        f = v.R[2]
        dot = D @ f
        better = dot > best
        best[better] = dot[better]; pick[better] = k
    covered = np.zeros(len(D))
    for k, (v, col, cov) in enumerate(faces):
        m = pick == k
        if not m.any():
            continue
        X = D[m] @ v.R.T
        fx = np.clip(v.w / 2 + v.k * X[:, 0] / X[:, 2] - 0.5, 0, v.w - 1.001)
        fy = np.clip(v.h / 2 - v.k * X[:, 1] / X[:, 2] - 0.5, 0, v.h - 1.001)
        x0, y0 = fx.astype(int), fy.astype(int)
        ax, ay = (fx - x0)[:, None], (fy - y0)[:, None]
        x1, y1 = np.minimum(x0 + 1, v.w - 1), np.minimum(y0 + 1, v.h - 1)
        pano[m] = ((col[y0, x0] * (1 - ax) + col[y0, x1] * ax) * (1 - ay) +
                   (col[y1, x0] * (1 - ax) + col[y1, x1] * ax) * ay)
        covered[m] = cov[y0, x0]
    img = np.clip(np.rint(pano.reshape(H, W, 3)), 0, 255)
    rgba = np.concatenate([img, np.full((H, W, 1), 255.0)], -1)
    payload = R.vq_encode(rgba, 0)
    # the rows the plane stands in for: the runtime leaves them out of the world while the plane is shown (in normal
    # play look A draws them anyway when their bounds reach the view, fully fogged: that hid the plane and cost geometry)
    rl = sorted(r['row'] for r in sky)
    rows_blob = struct.pack('<%dH' % len(rl), *rl)
    rows_blob += b'\0' * (-len(rows_blob) % 16)
    head = struct.pack('<4sIHHI5fHH', b'R4SK', 2, W, H, len(payload), TOP, BOTTOM, *map(float, eye), len(rl),
                       48 + len(rows_blob))
    head += b'\0' * (48 - len(head))
    head += rows_blob
    od = out / room
    od.mkdir(parents=True, exist_ok=True)
    blob = head + payload
    (od / 'ps2-sky.r4sk').write_bytes(blob)
    # the decoded VQ (what the console samples) for the review sheet
    cb = R.codec.px16(np.frombuffer(payload[:2048], '<u2').astype(np.uint32), 0).reshape(256, 4, -1)
    idx = np.frombuffer(payload[2048:], np.uint8)
    tw = R.codec.untwiddle_index(W // 2, H // 2)
    lab = idx[tw.ravel()].reshape(H // 2, W // 2)
    blk = cb[lab][..., :3]                               # (h/2, w/2, 4 texels, 3): texel order (0,0) (1,0) (0,1) (1,1)
    dec = np.zeros((H, W, 3), np.uint8)
    dec[::2, ::2] = blk[:, :, 0]; dec[1::2, ::2] = blk[:, :, 1]; dec[::2, 1::2] = blk[:, :, 2]; dec[1::2, 1::2] = blk[:, :, 3]
    Image.fromarray(dec).save(od / 'ps2-sky.png')
    Image.fromarray(img.astype(np.uint8)).save(od / 'ps2-sky-source.png')
    info.update(file=str(od / 'ps2-sky.r4sk'), bytes=len(blob), vram_bytes=len(payload), eye=[round(float(x)) for x in eye],
                fog=fog, sha256=hashlib.sha256(blob).hexdigest(),
                coverage=round(float(covered.mean()), 3))
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('extract', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('rooms', nargs='*')
    ap.add_argument('--near', type=float, default=20000.0)
    ap.add_argument('--face', type=int, default=512)
    a = ap.parse_args()
    rooms = a.rooms or sorted(p.name for p in (a.extract / 'inputs').iterdir())
    a.out.mkdir(parents=True, exist_ok=True)
    table = {}
    tp = a.out / 'rows.json'
    if tp.exists():
        table = json.loads(tp.read_text())
    for room in rooms:
        info = bake(room, a.extract / 'inputs' / room, a.extract / 'aux' / room, a.out, a.near, a.face)
        table[room] = info
        print(room, 'sky rows', info['sky_rows'], 'bytes', info.get('bytes'), 'coverage', info.get('coverage'), flush=True)
        tp.write_text(json.dumps(table, indent=1) + '\n')


if __name__ == '__main__':
    main()
