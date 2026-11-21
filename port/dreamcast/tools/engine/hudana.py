"""hudana.py <pack> <out folder> [picture]: the HUD widget records of a NAT3 pack (picture 1 by default) with their
textures (size, format, original-size flag, coordinates); writes each widget's texture and its cut as PNGs to <out
folder> (private: keep it out of git). Lane eng-e1i; also the pack reader hudcheck.py uses."""
import struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'engine' / 'bake'))   # dctex
import dctex

def block(b, at=0):
    n = struct.unpack_from('<I', b, at)[0]
    offs = struct.unpack_from(f'<{n+1}I', b, at + 4)
    base = at + 4 + 4 * (n + 1)
    return [b[base + offs[i]:base + offs[i + 1]] for i in range(n)]

def load(path):
    b = Path(path).read_bytes()
    magic, ver, room, n, crc = struct.unpack_from('<4s4I', b)
    assert magic == b'NAT3', magic
    secs = block(b, 20)
    return dict(textures=block(secs[0]), headers=block(secs[1]), frames=block(secs[3]),
                samples=[block(secs[4 + i]) for i in range(9)], room=room)

def stream(p, k, picture):
    """words of sample stream k at picture (1-based), applying the change rows from picture 1"""
    words = []
    for f in p['frames'][:picture]:
        idx = struct.unpack_from('<10I', f)[1 + k]
        row = p['samples'][k][idx]
        n = struct.unpack_from('<I', row)[0]
        if len(words) < n: words += [0] * (n - len(words))
        words = words[:n]
        at = 4
        while at < len(row):
            i, mask = struct.unpack_from('<2I', row, at); at += 8
            for j in range(32):
                if mask >> j & 1:
                    words[i + j] = struct.unpack_from('<I', row, at)[0]; at += 4
    return words

def widgets(p, picture=1):
    w = stream(p, 5, picture)
    raw = struct.pack(f'<{len(w)}I', *w)
    hud = w[:4]
    out = []
    for at in range(16, len(raw), 96):
        r = struct.unpack_from('<8I16f', raw, at)
        out.append(dict(identity=r[0], tree=r[1], shape=r[2], hidden=r[3], hdr=r[4], fnv=r[5], mask=r[6:8],
                        pos=r[8:11], rot=r[11:14], w=r[14], h=r[15], color=r[16:20], uv=r[20:24], at=at))
    return hud, out, raw

def texinfo(p, hdr):
    row = p['headers'][hdr]
    tid = struct.unpack_from('<I', row)[0]
    pkg = p['textures'][tid]
    at = struct.unpack_from('<I', pkg, 24)[0]
    w, h, fmt, _, _, flags, payload, _ = struct.unpack_from('<8I', pkg, at + 64)
    oflags = struct.unpack_from('<I', pkg, 44)[0]
    name = pkg[at:at + 64].split(b'\0')[0]
    return dict(tid=tid, w=w, h=h, fmt=fmt, payload=payload, flags=flags, hflag=oflags, name=name, pkg=pkg,
                hwords=struct.unpack_from('<9I', row))

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    pack = sys.argv[1]; pic = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    p = load(pack)
    hud, ws, _ = widgets(p, pic)
    tag = Path(pack).stem
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    print('room', hex(p['room']), 'frames', len(p['frames']), 'hud words', hud, 'widgets', len(ws))
    seen = {}
    for q in ws:
        idn = q['identity'] & 255; cls = q['identity'] >> 8 & 255; mark = q['identity'] >> 16
        par = q['tree'] & 255; lv = q['tree'] >> 8 & 255; typ = q['tree'] >> 16
        vis = (not q['hidden']) and (q['shape'] & 0x80000)
        s = f"id {idn:3} cls {cls:3} mark {mark:4} par {par:3} lv {lv} type {typ} shape {q['shape']:08x} vis {int(bool(vis))} " \
            f"pos ({q['pos'][0]:7.1f},{q['pos'][1]:7.1f}) rot {q['rot'][2]:6.3f} wh ({q['w']:6.1f},{q['h']:6.1f}) " \
            f"col ({','.join(f'{c:.0f}' for c in q['color'])}) uv ({','.join(f'{c:.4f}' for c in q['uv'])}) hdr {q['hdr']:x} masked {q['mask'][0]}"
        if q['hdr'] != 0xffffffff:
            t = texinfo(p, q['hdr'])
            s += f" tex {t['tid']} {t['w']}x{t['h']} fmt {t['fmt']} pay {t['payload']} hflag {t['hflag']:08x} {t['name']}"
            if t['tid'] not in seen:
                try:
                    img = dctex.decode(t['pkg']); seen[t['tid']] = img
                    Image.fromarray(img, 'RGBA').save(out / f"tex{t['tid']}.png")
                except Exception as e:
                    s += f' decode {e}'
            img = seen.get(t['tid'])
            if img is not None and vis:
                H, W = img.shape[:2]; u0, v0, u1, v1 = q['uv']
                c = Image.fromarray(img, 'RGBA').convert('RGB')
                d = ImageDraw.Draw(c); d.rectangle([u0 * W, v0 * H, u1 * W - 1, v1 * H - 1], outline=(255, 0, 0))
                c.resize((W * 4, H * 4), Image.NEAREST).save(out / f'cut-id{idn:03}.png')
        print(s)
