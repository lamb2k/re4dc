#!/usr/bin/env python3
"""PS2_PVS step 3 (lane t2exact, 2026-10-15): conservative per-cell sets from the caster's raw sets, the disc file, stats.

usage (Windows Python with numpy):
  pvs_emit.py emit <work dir> <out .pvs> [--dilate 1] [--near 3000]
  pvs_emit.py stats <work dir> x,z [x,z ...]          raw / emitted set sizes at points (world mm), vs everything near
  pvs_emit.py verify <work dir> <out .pvs>            checks <work>/verify.bin (pvs_cast verify) against the file

Set of a cell (conservative):
  - the union of the caster's raw sets of the cell and its neighbours within --dilate cells (a camera near a cell edge
    sees what the next cell's eyes see; it also covers rays that slipped between triangles),
  - every instance whose world box comes within --near mm of the cell's camera volume,
  - every instance of a dynamic placement (pvs_prep.py: the runtime may move it) and every non-opaque one whose box
    meets the cell's 60 m reach (only opaque triangles occlude, and a ray can miss a thin translucent card),
  - a cell with no ground point has no set (the runtime draws everything there), as does a camera outside the cell's
    Y range (local ground + the eye heights, +-1 m).

File (little endian): header 64 bytes
  char magic[4] "R4PV"; u32 version 1, mesh_crc, mesh_bytes, sidecar_crc, ninst, nx, nz; f32 x0, z0, cell;
  u32 nsets, set_bytes, ncells_with_set, pad[2]
  then nx*nz cells x 8 bytes {u16 set (0xffff: none); i16 ylo, yhi (decimetres); u16 pad}, then nsets x set_bytes
  (bit i of a set = instance i, pvs_prep.py's numbering).
"""
import json, struct, sys
from pathlib import Path
import numpy as np


def load_cells(work):
    b = (Path(work) / 'cells.bin').read_bytes()
    nx, nz, ninst = struct.unpack_from('<3I', b, 0); x0, z0, cell = struct.unpack_from('<3f', b, 12)
    nb = (ninst + 7) // 8; rec = 12 + nb; at = 24
    ylo = np.zeros(nx * nz, np.float32); yhi = np.zeros(nx * nz, np.float32); has = np.zeros(nx * nz, bool)
    bits = np.zeros((nx * nz, nb), np.uint8)
    for c in range(nx * nz):
        ylo[c], yhi[c] = struct.unpack_from('<2f', b, at); has[c] = b[at + 8] != 0
        bits[c] = np.frombuffer(b, np.uint8, nb, at + 12); at += rec
    return dict(nx=nx, nz=nz, ninst=ninst, x0=x0, z0=z0, cell=cell, nb=nb, ylo=ylo, yhi=yhi, has=has,
                vis=np.unpackbits(bits, axis=1, bitorder='little')[:, :ninst].astype(bool))


def load_inst(work):
    rows = [l.rstrip('\n').split('\t') for l in open(Path(work) / 'inst.tsv')][1:]
    a = np.array([[float(x) for x in r] for r in rows])
    return dict(n=len(a), placement=a[:, 1].astype(int), pas=a[:, 5].astype(int), dyn=a[:, 7].astype(bool),
                lo=a[:, 8:11], hi=a[:, 11:14], verts=a[:, 14].astype(int))


def box_dist(lo, hi, blo, bhi):
    """distance between box arrays lo/hi (n x 3) and one box blo/bhi"""
    d = np.maximum(0, np.maximum(lo - bhi, blo - hi))
    return np.sqrt((d * d).sum(1))


def conservative(C, I, dilate, near):
    nx, nz = C['nx'], C['nz']
    out = np.zeros_like(C['vis'])
    for c in range(nx * nz):
        if not C['has'][c]:
            continue
        ix, iz = c % nx, c // nx
        s = np.zeros(I['n'], bool)
        for dz in range(-dilate, dilate + 1):
            for dx in range(-dilate, dilate + 1):
                jx, jz = ix + dx, iz + dz
                if 0 <= jx < nx and 0 <= jz < nz:
                    s |= C['vis'][jz * nx + jx]
        blo = np.array([C['x0'] + ix * C['cell'], C['ylo'][c] - 1000, C['z0'] + iz * C['cell']])
        bhi = np.array([C['x0'] + (ix + 1) * C['cell'], C['yhi'][c] + 1000, C['z0'] + (iz + 1) * C['cell']])
        d = box_dist(I['lo'], I['hi'], blo, bhi)
        s |= d <= near
        s |= I['dyn']
        s |= (I['pas'] != 0) & (d <= 60000)
        out[c] = s
    return out


def emit(work, out_path, dilate, near):
    meta = json.loads((Path(work) / 'meta.json').read_text())
    C, I = load_cells(work), load_inst(work)
    S = conservative(C, I, dilate, near)
    nb = C['nb']
    sets, index = {}, []
    for c in range(C['nx'] * C['nz']):
        if not C['has'][c]:
            index.append((0xffff, 0, 0)); continue
        key = np.packbits(S[c].astype(np.uint8), bitorder='little').tobytes().ljust(nb, b'\0')
        k = sets.setdefault(key, len(sets))
        lo = int(np.floor((C['ylo'][c] - 1000) / 100)); hi = int(np.ceil((C['yhi'][c] + 1000) / 100))
        index.append((k, max(-32768, lo), min(32767, hi)))
    assert len(sets) < 0xffff
    head = struct.pack('<4s7I3f5I', b'R4PV', 1, meta['mesh_crc'], meta['mesh_bytes'], meta['sidecar_crc'], C['ninst'],
                       C['nx'], C['nz'], C['x0'], C['z0'], C['cell'], len(sets), nb, int(C['has'].sum()), 0, 0)
    assert len(head) == 64
    body = b''.join(struct.pack('<Hhhh', k, lo, hi, 0) for k, lo, hi in index)
    blob = head + body + b''.join(sorted(sets, key=sets.get))
    blob += b'\0' * (-len(blob) % 32)
    Path(out_path).write_bytes(blob)
    used = C['has']
    frac = S[used].sum(1) / C['ninst']
    vfrac = (S[used] * I['verts']).sum(1) / I['verts'].sum()
    print('emit %s: %d bytes, %d cells with a set of %d, %d distinct sets, %d instances; set size mean %.1f%% '
          '(vertices %.1f%%), max %.1f%%' % (out_path, len(blob), used.sum(), C['nx'] * C['nz'], len(sets), C['ninst'],
                                              100 * frac.mean(), 100 * vfrac.mean(), 100 * frac.max()))


def stats(work, pts, dilate, near):
    C, I = load_cells(work), load_inst(work)
    S = conservative(C, I, dilate, near)
    for p in pts:
        x, z = (float(v) for v in p.split(','))
        ix, iz = int((x - C['x0']) // C['cell']), int((z - C['z0']) // C['cell'])
        c = iz * C['nx'] + ix
        if not C['has'][c]:
            print('%s: cell %d,%d has no set' % (p, ix, iz)); continue
        cen = np.array([x, (C['ylo'][c] + C['yhi'][c]) / 2, z])
        for R in (25000, 40000):
            near_r = box_dist(I['lo'], I['hi'], cen, cen) <= R
            for name, s in (('raw', C['vis'][c]), ('pvs', S[c])):
                k = near_r & s
                print('%s cell %d,%d y %d..%d  within %2d m: %3d inst %6d verts | %s %3d inst %6d verts (%.0f%% of verts)' % (
                    p, ix, iz, C['ylo'][c], C['yhi'][c], R // 1000, near_r.sum(), I['verts'][near_r].sum(), name, k.sum(),
                    I['verts'][k].sum(), 100.0 * I['verts'][k].sum() / max(1, I['verts'][near_r].sum())))


def verify(work, pvs_path):
    C, I = load_cells(work), load_inst(work)
    b = Path(pvs_path).read_bytes()
    nsets, nb = struct.unpack_from('<2I', b, 44)
    nx, nz = C['nx'], C['nz']
    idx = [struct.unpack_from('<Hhh', b, 64 + 8 * c) for c in range(nx * nz)]
    base = 64 + 8 * nx * nz
    sets = [np.unpackbits(np.frombuffer(b, np.uint8, nb, base + nb * k), bitorder='little')[:C['ninst']].astype(bool)
            for k in range(nsets)]
    v = (Path(work) / 'verify.bin').read_bytes()
    m = struct.unpack_from('<I', v, 0)[0]; at = 4; bad = 0; badv = 0; eyes = 0; out = 0
    for _ in range(m):
        c = struct.unpack_from('<I', v, at)[0]; e = struct.unpack_from('<3f', v, at + 4)
        vis = np.unpackbits(np.frombuffer(v, np.uint8, nb, at + 16), bitorder='little')[:C['ninst']].astype(bool)
        at += 16 + nb
        k, lo, hi = idx[c]
        if k == 0xffff or not (lo * 100 <= e[1] <= hi * 100):
            out += 1; continue
        eyes += 1
        miss = vis & ~sets[k]
        if miss.any():
            bad += 1; badv += int(I['verts'][miss].sum())
            if bad <= 10:
                print('MISS cell %d eye %d,%d,%d: instances %s (%d verts)' % (c, e[0], e[1], e[2], list(np.nonzero(miss)[0]),
                                                                          I['verts'][miss].sum()))
    print('verify: %d eyes in a cell volume (%d outside), %d with an instance outside the set (%d level-0 vertices)' % (
        eyes, out, bad, badv))


def main():
    a = sys.argv[1:]
    def opt(name, dflt):
        return float(a[a.index(name) + 1]) if name in a else dflt
    dilate, near = int(opt('--dilate', 1)), opt('--near', 3000)
    if a[0] == 'emit':
        emit(a[1], a[2], dilate, near)
    elif a[0] == 'stats':
        stats(a[1], [x for x in a[2:] if ',' in x], dilate, near)
    elif a[0] == 'verify':
        verify(a[1], a[2])


if __name__ == '__main__':
    main()
