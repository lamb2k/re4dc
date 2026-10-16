"""world16 look sheet: each room's worst projected view (roomproj p90 view, Leon rig), current vs rebuilt package.
Offline numpy raster (tools/ps2_room_sheet.py), textures from the packed PNGs by key, 25 m cull, no fog, no actors.
usage: sheet.py <ch1|ch2> <out.png> room,room,..."""
import sys, os, json, math, glob
from pathlib import Path
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw
TOOLS = r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-cpu-t15-20261016\tree\port\dreamcast\tools'
sys.path.insert(0, TOOLS)
import ps2_room_sheet as S
PRIV = r'C:\Game Dev\Emulators\re4-assets-private'
PRICE = r'C:\Game Dev\Emulators\world16-20261016\price'
W, H = 400, 300


def wpath(p):
    if p.startswith('/root/'):
        return r'\\wsl.localhost\Ubuntu-24.04' + p.replace('/', '\\')
    if p.startswith('/mnt/c/'):
        return 'C:' + p[6:]
    return p


def tex_index():
    idx = {}
    for j in glob.glob(PRIV + r'\**\ps2-world.json', recursive=True):
        d = Path(j).parent
        if not (d / 'textures-packed').is_dir():
            continue
        try:
            rows = json.loads(Path(j).read_text())['texture_rows']
        except Exception:
            continue
        for k, v in rows.items():
            png = d / 'textures-packed' / ('%04d.png' % int(k))
            if png.exists():
                idx.setdefault((v['key'][0], v['key'][1]), str(png))
    for d in (os.path.join(PRIV, 't11-20261014', 'blackps2', 'newtex'),):
        for f in glob.glob(d + r'\*.re4tex'):
            a, b = os.path.basename(f)[:-7].split('-')
            idx.setdefault((int(a, 16), int(b, 16)), f)
    return idx


def load_tex(p):
    if p.endswith('.re4tex'):
        import ps2_cast_sheet as CS
        try:
            x = CS.decode_re4tex(p)
        except Exception:
            return None
        return S.Tex(x if isinstance(x, Image.Image) else Image.fromarray(np.asarray(x, np.uint8)))
    return S.Tex(Image.open(p))


def tris(mesh, side):
    """package_tris without the json: texture = R4PW part key."""
    import struct
    pk = S.r4im.load(Path(mesh))
    sb = Path(side).read_bytes()
    magic, ver, npl, npa, nme = struct.unpack_from('<4s4I', sb)
    meta = [struct.unpack_from('<IIHHBBBB', sb, 32 + 16 * i) for i in range(npa)]
    off = 32 + 16 * npa
    places = [struct.unpack_from('<HH12f', sb, off + 52 * i) for i in range(npl)]
    per = {}
    for k in range(len(pk.meshes)):
        out = []
        for p in pk.mesh_parts(k):
            part = pk.parts[p]
            ulo, vlo, us, vs = part[8:12]
            crc, h2, w, h, pas, cull, _, _ = meta[p]
            P, UV, C = [], [], []
            for cl in pk.part_levels(p):
                for let in cl['levels'][0][1]:
                    for s in pk.meshlet_strips(let):
                        vv = [pk.vertex(v) for v in s]
                        for j in range(len(s) - 2):
                            a, b, c = (vv[j + 1], vv[j], vv[j + 2]) if j & 1 else (vv[j], vv[j + 1], vv[j + 2])
                            pa, pb, pc = (pk.world(k, *x[:3]) for x in (a, b, c))
                            if pa == pb or pb == pc or pa == pc:
                                continue
                            P.append((pa, pb, pc))
                            UV.append([(ulo + x[3] * us, vlo + x[4] * vs) for x in (a, b, c)])
                            C.append([((x[5] >> 10 & 31) / 31, (x[5] >> 5 & 31) / 31, (x[5] & 31) / 31,
                                       1.0 if x[5] & 0x8000 else 0.0) for x in (a, b, c)])
            if P:
                out.append((np.array(P), np.array(UV), np.array(C), (crc, h2), pas))
        per[k] = out
    batches = []
    for mi, gi, *aff in places:
        M = np.array(aff, np.float64).reshape(3, 4)
        for P, UV, C, key, pas in per.get(mi, []):
            batches.append((P @ M[:, :3].T + M[:, 3], UV, C, key, pas))
    return batches


def job(args):
    room, label, mesh, side, eye, tgt, idx = args
    b = tris(mesh, side)
    keys = {x[3] for x in b}
    tex = {}
    grey = S.Tex(Image.new('RGBA', (8, 8), (160, 160, 160, 255)))
    for k in keys:
        tex[k] = (load_tex(idx[k]) if k in idx else None) or grey
    v = S.View(label, eye, tgt, W, H, fov=math.degrees(2 * math.atan(4 / 3 * math.tan(math.radians(25)))))
    e = np.array(eye)
    b2 = []
    for P, UV, C, key, pas in b:
        m = np.linalg.norm(P - e, axis=2).min(1) < 25000
        if m.any():
            b2.append((P[m], UV[m], C[m], key, pas))
    img, st = S.render(v, b2, tex, S.dc_colour)
    return room, label, img, st, sum(1 for k in keys if k not in idx)


def main():
    which, out, rooms = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    P = PRIV + ('\\world16-ch1-20261016' if which == 'ch1' else '\\world16-ch2-20261016')
    src = json.load(open(P + '\\sources.json'))['rooms']
    cur = json.load(open(PRICE + ('\\cur.json' if which == 'ch1' else '\\cur2.json')))
    new = json.load(open(PRICE + ('\\new.json' if which == 'ch1' else '\\new2.json')))
    idx = tex_index()
    jobs, meta = [], {}
    for r in rooms:
        rows = cur[r]['rows']
        p90 = cur[r]['ta_p90']
        row = min(rows, key=lambda x: abs(x['ta'] - p90))
        pos = np.array(row['pos'], float); yaw = row['yaw']
        fwd = np.array([math.sin(yaw), 0, math.cos(yaw)]); right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
        eye = pos + np.array([0, 1650, 0]) - fwd * 1900 + right * 450
        pf = np.array([math.sin(yaw) * math.cos(math.radians(-6)), math.sin(math.radians(-6)), math.cos(yaw) * math.cos(math.radians(-6))])
        tgt = eye + pf * 10000
        nrow = [x for x in new[r]['rows'] if x['src'] == row['src'] and x['yaw'] == row['yaw']]
        meta[r] = (row['src'], row['ta'], nrow[0]['ta'] if nrow else None)
        d = os.path.join(P, r)
        nm = os.path.join(d, 'ps2-wv5.re4mesh')
        if not os.path.exists(nm):
            nm = os.path.join(d, 'ps2-world.re4mesh')
        eye2 = pos + np.array([0, 6000, 0]) - fwd * 8000
        tgt2 = eye2 + np.array([math.sin(yaw) * math.cos(math.radians(-25)), math.sin(math.radians(-25)), math.cos(yaw) * math.cos(math.radians(-25))]) * 10000
        for lab, mm, sd in (('current', wpath(src[r]['ps2-world.re4mesh']['path']), wpath(src[r]['ps2-world.r4pw']['path'])),
                            ('rebuilt', nm, os.path.join(d, 'ps2-world.r4pw'))):
            jobs.append((r, lab, mm, sd, eye, tgt, idx))
            jobs.append((r, lab + ' wide', mm, sd, eye2, tgt2, idx))
    with Pool(4) as pool:
        res = pool.map(job, jobs)
    got = {(r, l): (img, st, miss) for r, l, img, st, miss in res}
    pad, th = 6, 18
    sheet = Image.new('RGB', (4 * W + 5 * pad, len(rooms) * (H + th + pad) + pad + 24), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 4), 'world16 %s: worst projected view per room (MODELLED p90 view, offline raster, no fog/actors). Columns: rig view current | rebuilt | 8 m back 6 m up current | rebuilt.' % which, fill=(255, 255, 255))
    for i, r in enumerate(rooms):
        y = 24 + pad + i * (H + th + pad)
        s, tc, tn = meta[r]
        for j, l in enumerate(('current', 'rebuilt', 'current wide', 'rebuilt wide')):
            img, st, miss = got[(r, l)]
            x = pad + j * (W + pad)
            sheet.paste(Image.fromarray(img), (x, y + th))
            ta = (tc if l == 'current' else tn) if 'wide' not in l else '-'
            note = ' LAKE ROOM' if r in ('r10b', 'r11b') else ''
            dr.text((x, y + 2), '%s %s  view %s  TA verts %s  tris %d%s%s' % (r, l, s, ta, st['tris'], note,
                    ('  (%d keys untextured)' % miss) if miss else ''), fill=(255, 255, 160))
    sheet.save(out)
    print('wrote', out, meta)


if __name__ == '__main__':
    main()
