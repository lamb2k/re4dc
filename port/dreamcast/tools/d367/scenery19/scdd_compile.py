#!/usr/bin/env python3
"""SCDD v1: the scenery point-dedup section of a room's R4RC file (lane scenery19, SCENERY_DEDUP=2).

For each PS2 world meshlet (R4IM v3 dc/native/<room>/ps2-world.re4mesh) a corner whose grid position (x, y, z) already
appeared earlier in the meshlet is a "repeat" of that first corner. The runtime (native_static.cpp dedup) reorders the
meshlet's corners at room load, firsts first and repeats last (each group in corner order), transforms only the firsts
and builds every repeat from its first copy (same x, y, 1/w, outcode; its own u, v, colour): every vertex word is the
knob-off word. This section replaces the load-time position hashing of SCENERY_DEDUP=1 and lives in the room file's
heap-4 block (engine19 room_file.c), so no separate allocation.

Body (little endian):
  head 16 B : u32 r4im_crc, u32 r4im_bytes, u32 meshlet_count, u32 repeat_total
  lets      : u32[meshlet_count]  offset into src | repeats << 24 (0 = no repeats, or n < 2 / n > 256): the draw's word
  src       : u8[repeat_total]    per repeat (reordered position u0 + j): its first copy's reordered corner index
  mask      : for each meshlet with repeats, in meshlet order, ceil(n / 8) bytes: bit k (byte k >> 3, bit k & 7) set =
              stored corner k is a repeat. The load reorder (open and movie reload) derives the permutation from it.
  pad to 16

Usage: scdd_compile.py <native dir> <rc in dir> <rc out dir> [rooms...]
  Copies every <rc in>/<room>/room.r4rc to <rc out>, adding (or replacing) the SCDD section (optional, flags 0) for the
  rooms that have a PS2 world package. Deterministic. Writes MANIFEST-SCDD.tsv and SHA256SUMS in <rc out>.
"""
import hashlib, struct, sys, zlib
from pathlib import Path


class _Pkg:
    """The R4IM v3 fields this tool needs (layout as worldlean/r4im_pkg.py; no numpy)."""
    def __init__(self, path):
        m = Path(path).read_bytes()
        self.m = m
        self.mesh_bytes, self.mesh_crc = struct.unpack_from('<II', m, 8)
        h = struct.unpack_from('<4s15I', m, 0)
        self.nlet, self.o_let, self.o_vert, self.o_strip = h[6], h[12], h[13], h[14]

    def corners(self, li):
        fv, fs, _, vc, sc = struct.unpack_from('<IIIHH', self.m, self.o_let + 28 * li)
        s = self.o_strip + fs
        idx = struct.unpack_from('<%dH' % vc, self.m, s) if sc & 0x8000 else range(vc)
        return [struct.unpack_from('<3H', self.m, self.o_vert + 12 * (fv + k)) for k in idx]


def scdd(pkg_dir):
    p = _Pkg(pkg_dir / 'ps2-world.re4mesh')
    lets, src, mask = [], bytearray(), bytearray()
    corners_total = 0
    for li in range(p.nlet):
        corners = p.corners(li)
        n = len(corners)
        corners_total += n
        if n < 2 or n > 256:
            lets.append(0); continue
        seen, first = {}, []
        for k in range(n):
            key = tuple(int(v) for v in corners[k])
            first.append(seen.setdefault(key, k))
        rep = sum(1 for k in range(n) if first[k] != k)
        if not rep:
            lets.append(0); continue
        pos, u, d = [0] * n, 0, n - rep
        for k in range(n):
            if first[k] == k:
                pos[k] = u; u += 1
            else:
                pos[k] = d; d += 1
        lets.append(len(src) | (rep << 24))
        mb = bytearray((n + 7) // 8)
        for k in range(n):
            if first[k] != k:
                src.append(pos[first[k]]); mb[k >> 3] |= 1 << (k & 7)
        mask += mb
    body = struct.pack('<4I', p.mesh_crc, p.mesh_bytes, p.nlet, len(src)) + struct.pack('<%dI' % len(lets), *lets)
    body += bytes(src) + bytes(mask)
    body += bytes(-len(body) % 16)
    return body, dict(meshlets=p.nlet, corners=corners_total, repeats=len(src))


def read_rc(b):
    assert b[:4] == b'R4RC' and struct.unpack_from('<H', b, 4)[0] == 1
    n = struct.unpack_from('<I', b, 12)[0]
    secs = []
    for i in range(n):
        tag, ver, fl, off, ln, cnt, stride, al, _ = struct.unpack_from('<4sHHIIIIII', b, 64 + 32 * i)
        secs.append([tag, ver, fl, b[off:off + ln], cnt, stride, al])
    return secs


def write_rc(b, secs):
    n = len(secs)
    off = 64 + 32 * n
    body, dirs = b'', b''
    for tag, ver, fl, data, cnt, stride, al in secs:
        body += b'\0' * (-(off + len(body)) % 16)
        dirs += struct.pack('<4sHHIIIIII', tag, ver, fl, off + len(body), len(data), cnt, stride, 16, 0)
        body += data
    body += b'\0' * (-(off + len(body)) % 16)
    payload = dirs + body
    hdr = bytearray(b[:64])
    struct.pack_into('<I', hdr, 12, n)
    struct.pack_into('<I', hdr, 16, 64 + len(payload))
    struct.pack_into('<I', hdr, 48, zlib.crc32(payload) & 0xFFFFFFFF)
    return bytes(hdr) + payload


def main():
    native, rin, rout = (Path(x) for x in sys.argv[1:4])
    rooms = sys.argv[4:] or sorted(d.name for d in rin.iterdir() if (d / 'room.r4rc').is_file())
    rout.mkdir(parents=True, exist_ok=True)
    rows, sums = [], []
    for r in rooms:
        src = rin / r / 'room.r4rc'
        if not src.is_file():
            continue
        b = src.read_bytes()
        secs = [s for s in read_rc(b) if s[0] != b'SCDD']
        st = dict(meshlets=0, corners=0, repeats=0)
        if (native / r / 'ps2-world.re4mesh').is_file():
            body, st = scdd(native / r)
            secs.append([b'SCDD', 1, 0, body, st['meshlets'], 0, 16])
            st['bytes'] = len(body)
        out = write_rc(b, secs)
        (rout / r).mkdir(exist_ok=True)
        (rout / r / 'room.r4rc').write_bytes(out)
        rows.append((r, len(b), len(out), st.get('bytes', 0), st['meshlets'], st['corners'], st['repeats']))
        sums.append('%s  %s/room.r4rc' % (hashlib.sha256(out).hexdigest(), r))
    with open(rout / 'MANIFEST-SCDD.tsv', 'w') as m:
        m.write('room\tin_bytes\tout_bytes\tscdd_bytes\tmeshlets\tcorners\trepeats\n')
        for x in rows:
            m.write('\t'.join(str(v) for v in x) + '\n')
    (rout / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    for x in rows:
        if x[3]:
            print('%s scdd=%d B meshlets=%d corners=%d repeats=%d (%.1f%%)' % (x[0], x[3], x[4], x[5], x[6],
                                                                               100.0 * x[6] / max(x[5], 1)))


if __name__ == '__main__':
    main()
