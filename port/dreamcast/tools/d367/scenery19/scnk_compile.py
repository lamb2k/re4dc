#!/usr/bin/env python3
"""SCNK v1: scenery chunk section for one room's PS2 world package (lane scenery19).

Input : <pkg>/ps2-world.re4mesh (R4IM v3) + ps2-world.r4pw. Output: the SCNK section body (an R4RC section,
engine19 room_file.c, tag 'SCNK') and a size/dedup report.

Per meshlet (a "chunk", Code: Veronica njCnk style) the section stores
  - its distinct grid positions (a meshlet corner = position + u,v,colour; seams repeat a position),
  - one u8 point index per corner (strip indices are unchanged and still address corners),
  - a bounding sphere (grid units) and a back-face cone (for parts drawn with PVR culling).
The runtime transforms each point once, then builds each corner from its point and the corner's own u,v,colour,
so every vertex word is unchanged (the same ftrv on the same input). Geometry, strips and their order are untouched.

Layout (little endian, 4-byte aligned):
  head  32 B : 'SCNK', u32 version=1, u32 r4im_crc, u32 r4im_bytes, u32 meshlet_count, u32 point_total,
               u32 rec_offset (=32), u32 data_offset
  rec   32 B : u32 data (offset from data_offset), u16 points, u16 corners,
               f32 sphere cx,cy,cz,r (grid units), i8 cone ax,ay,az (x127), i8 cone cos (x127, -128 = no cone), u32 0
  data       : points x 3 u16, pad to 4, corners x u8, pad to 4
"""
import argparse, json, struct, sys, zlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worldlean'))
from r4im_pkg import Pkg  # noqa: E402

VERSION = 1


def cone_of(pos, tris, cull):
    if cull not in (1, 2) or not tris:
        return None
    t = np.asarray(tris, dtype=np.int64)
    p = pos.astype(np.float64)
    n = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]]) * (1 if cull == 2 else -1)
    ln = np.linalg.norm(n, axis=1)
    ok = ln > 1e-9
    if not ok.any():
        return None
    nn = n[ok] / ln[ok, None]
    ax = nn.sum(0); la = np.linalg.norm(ax)
    if la < 1e-9:
        return None
    ax /= la
    c = float((nn @ ax).min())
    if c <= 0:
        return None
    # quantise conservatively: the stored cutoff must not exceed the true one after axis rounding
    q = np.clip(np.round(ax * 127), -127, 127).astype(int)
    qa = q / np.linalg.norm(q)
    c2 = float((nn @ qa).min())
    cq = int(np.floor(c2 * 127)) if c2 > 0 else -128
    return (int(q[0]), int(q[1]), int(q[2]), cq if cq > 0 else -128)


def compile_room(pkg_dir):
    p = Pkg(pkg_dir / 'ps2-world.re4mesh', pkg_dir / 'ps2-world.r4pw')
    part_of_let = {}
    for pi, part in enumerate(p.parts):
        for li in range(part['first_let'], part['first_let'] + part['let_count']):
            part_of_let[li] = pi
    recs, data = [], bytearray()
    st = dict(meshlets=p.nlet, corners=0, points=0, cones=0)
    for li in range(p.nlet):
        corners, tris = p.let_tris(li)
        pos = np.ascontiguousarray(corners[:, :3])
        uniq, inv = np.unique(pos, axis=0, return_inverse=True)
        # first-use order keeps the point list deterministic and cache friendly
        order = []; remap = {}
        for k in inv.ravel():
            if k not in remap:
                remap[k] = len(order); order.append(k)
        pts = uniq[order]; idx = np.array([remap[k] for k in inv.ravel()], dtype=np.uint8)
        assert len(pts) <= 256 and len(idx) == len(pos)
        assert np.array_equal(pts[idx], pos)
        lo, hi = pts.min(0).astype(np.float64), pts.max(0).astype(np.float64)
        c = (lo + hi) * 0.5
        r = float(np.sqrt(((pts - c) ** 2).sum(1)).max()) * (1 + 1e-6) + 1e-3
        cn = cone_of(pos, tris, p.pmeta[part_of_let[li]]['cull'] if li in part_of_let else 0)
        st['corners'] += len(pos); st['points'] += len(pts); st['cones'] += cn is not None
        off = len(data)
        data += pts.astype('<u2').tobytes()
        data += b'\0' * (-len(data) % 4)
        data += idx.tobytes()
        data += b'\0' * (-len(data) % 4)
        ax = cn if cn else (0, 0, 0, -128)
        recs.append(struct.pack('<IHH4f4bI', off, len(pts), len(pos), *c, r, *ax, 0))
    head = struct.pack('<4s7I', b'SCNK', VERSION, p.mesh_crc, p.mesh_bytes, p.nlet, st['points'], 32, 32 + 32 * p.nlet)
    body = head + b''.join(recs) + bytes(data)
    st['bytes'] = len(body); st['crc32'] = zlib.crc32(body) & 0xffffffff
    st['r4im_bytes'] = p.mesh_bytes
    return body, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('native', type=Path, help='dc/native directory holding r1xx/ps2-world.*')
    ap.add_argument('out', type=Path)
    ap.add_argument('rooms', nargs='*')
    a = ap.parse_args()
    rooms = a.rooms or sorted(d.name for d in a.native.iterdir() if (d / 'ps2-world.re4mesh').exists())
    a.out.mkdir(parents=True, exist_ok=True)
    report = {}
    for room in rooms:
        body, st = compile_room(a.native / room)
        (a.out / f'{room}.scnk').write_bytes(body)
        report[room] = st
        print('%s meshlets=%d corners=%d points=%d (%.1f%% fewer) cones=%d bytes=%d (r4im %d)' % (
            room, st['meshlets'], st['corners'], st['points'], 100 * (1 - st['points'] / max(st['corners'], 1)),
            st['cones'], st['bytes'], st['r4im_bytes']))
    (a.out / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
