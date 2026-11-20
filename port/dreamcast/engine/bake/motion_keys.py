"""motion_keys.py: offline motion keys for the native skeleton service (lane eng-svc2; docs/engine/SERVICES.md 10).

The game samples a motion clip ("FCV": per joint three axis key streams, Hermite keys at integer frames, in nine
encodings) with HermiteInterpolation: a search from a per-bone key history, then the Hermite blend of the bracketing
pair. The engine samples from this bake instead: per clip, a table of every pose value at every integer frame
(frame-major: one row of floats a frame, the joints in clip order), so a tick at an integer frame reads one row and
nothing else. No search, no history, no key decoding.

  python3 motion_keys.py --tree <converted data tree> --out motion.mkp em/pl00.drs em/wep02.drs ...

Inputs: the archives' FCV entries (the DVD container placed as the game places it, the tagged archive's "FCV"
entries) and, for the prepared enemy archives whose FCV entries are proxies, the full clips in dc/mot/*.fcv.

Exactness (PC, the reference's SSE single precision):
  - every value of a row is computed with the original's operations in its order in float32 (numpy float32 is IEEE
    single, no contraction): the key fields decoded as Fcc_get_data_* decodes them (s16 and s8 times 0.0001f), then
    hermite() (math_sub.cpp) at t = (frame - f0) / (f1 - f0); a frame on a key takes the key's value;
  - rotation channels are stored after VecRadLimit (idempotent on its own output), as MotionMoveCore applies it;
  - the last row (frame maxFrame) holds each axis's last key: the original's answer for a frame at or past the end
    of a clip that does not loop. A looping clip wraps the frame first, as the original does;
  - fractional frames (0.2% of samples on the fixtures) are served from the clip's own key blocks ("cold", copied
    into the bake as they are) by the original decoder with its history off: on these clips the result does not
    depend on the history (every axis's keys start at 0, end at maxFrame and rise strictly, checked here), so the
    search from key 0 finds the same bracket the history search finds.
A clip any pose joint of which fails those checks is not baked (the service then keeps the original decoder for it).

Pack layout (little-endian):
  header 32 B   "RE4MK1\\0\\0", u32 clips, u32 index offset, u32 bytes, u32 0 x3
  index         per clip: u32 identity, u32 offset (sorted by identity)
  clips         32-aligned, each:
    0   u32 identity   FNV-1a of the clip header (maxFrame, joint count, kinds, parts) and every pose joint's key
                       block in joint order: what the service computes from MotionSetCore's key table
    4   u16 maxFrame, u16 joints
    8   u16 rows (maxFrame + 1), u16 stride (floats a row, a multiple of 8: rows start on a 32-byte line)
    12  u16 const floats, u16 flags (0)
    16  u32 joint table, rows, const, cold table, cold blocks (offsets from the clip), u32 cold bytes,
        u32 the original clip's bytes, u32 0
    64  joint table: per joint u16 kind word (as the original), u8 parts, u8 source (0 rows, 1 const, 2 not a pose
        channel: the original path), u16 first column, u16 0
        cold table: per joint u32 offset of its key block in the cold section (0xFFFFFFFF none)
        const: floats; rows: rows x stride floats; cold: the key blocks as the original encodes them
"""
import argparse
import glob
import os
import struct
import sys

import numpy as np

F32 = np.float32
SCALE = F32(0.0001)
PI = F32(3.1415927)
PI2 = F32(6.2831855)
# Fcc key layouts: type -> (value field, tangent field, key bytes). In-tangent after the value, out-tangent after it.
KEY = {0: ('f', 'f', 12), 1: ('f', 'h', 8), 2: ('f', 'b', 6), 4: ('h', 'f', 10), 5: ('h', 'h', 6), 6: ('h', 'b', 4),
       8: ('b', 'f', 9), 9: ('b', 'h', 5), 10: ('b', 'b', 3)}
FSIZE = {'f': 4, 'h': 2, 'b': 1}
NONE = 0xFFFFFFFF


def place(d, base=0, depth=0, out=None):
    """The DVD container's main-RAM parts, placed as host_data.cpp (and dvd.cpp) places them."""
    if out is None:
        out = bytearray()
    h = base + 0x20
    while h + 0x20 <= len(d):
        e = struct.unpack_from('<8I', d, h)
        if e[0] == 0xFFFFFFFF:
            break
        if e[0] == 0 and e[2] == 0:
            o = base + e[3]
            out += d[o:o + e[1]]
            out += bytes((-len(out)) & 31)
        elif e[0] == 4 and depth == 0:
            place(d, base + e[3], 1, out)
        h += 0x20
    return bytes(out)


def fnv(data, h=2166136261):
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def target(info):
    """MotionMoveCore's channel test: 'rot' / 'pos' / 'scale', or None (root, camera, unknown: the original path)."""
    kind, ch = info & 0xFF, (info >> 8) & 0xF
    if ch in (6, 7):
        return None
    if kind & 2:
        return 'rot'
    if kind & 4:
        return 'pos'
    if kind & 8:
        return 'scale'
    if kind & 0x30:
        return 'rot'
    return None


def field(buf, at, fmt, m, ks):
    """m fields of format fmt at buf[at], stride ks, as Fcc_get_data_* converts them."""
    idx = at + np.arange(m) * ks
    if fmt == 'f':
        raw = np.frombuffer(bytes(b for i in idx for b in buf[i:i + 4]), dtype='<f4')
        return raw.astype(F32)
    if fmt == 'h':
        raw = np.frombuffer(bytes(b for i in idx for b in buf[i:i + 2]), dtype='<i2')
        return raw.astype(F32) * SCALE
    raw = np.array([buf[i] - 256 if buf[i] >= 128 else buf[i] for i in idx], dtype=np.int8)
    return raw.astype(F32) * SCALE


def hermite(p0, p1, v0, v1, t):
    """math_sub.cpp hermite(), float32, the original's order."""
    t2 = t * t
    t3 = t * t2
    h01 = -(t3 + t3) + F32(3.0) * t2
    h11 = t3 - t2
    h10 = h11 - t2 + t
    h00 = -h01 + F32(1.0)
    return p0 * h00 + p1 * h01 + v0 * h10 + v1 * h11


def rad_limit(x):
    x = x.copy()
    while True:
        hi = x >= PI
        if not hi.any():
            break
        x[hi] = x[hi] - PI2
    while True:
        lo = x < -PI
        if not lo.any():
            break
        x[lo] = x[lo] + PI2
    return x


class Reject(Exception):
    pass


def axis_rows(buf, p, ftype, max_frame):
    """One axis at buf[p]: (values at frames 0..maxFrame, next axis offset)."""
    vf, tf, ks = KEY[ftype]
    if p + 2 > len(buf):
        raise Reject('axis past the end')
    m, = struct.unpack_from('<H', buf, p)
    if m == 0 or p + 2 + m * (2 + ks) > len(buf):
        raise Reject(f'axis with {m} keys')
    fr = np.array(struct.unpack_from(f'<{m}H', buf, p + 2), dtype=np.int64)
    d = p + 2 + 2 * m
    if fr[0] != 0 or fr[-1] != max_frame or (m > 1 and np.any(np.diff(fr) <= 0)):
        raise Reject('keys do not run 0..maxFrame strictly rising')
    val = field(buf, d, vf, m, ks)
    tin = field(buf, d + FSIZE[vf], tf, m, ks)
    tout = field(buf, d + FSIZE[vf] + FSIZE[tf], tf, m, ks)
    rows = np.empty(max_frame + 1, dtype=F32)
    if max_frame > 0:
        k = np.arange(max_frame)
        i = np.searchsorted(fr, k, side='right') - 1
        on = fr[i] == k
        j = np.minimum(i + 1, m - 1)
        f0 = fr[i].astype(F32)
        f1 = fr[j].astype(F32)
        with np.errstate(divide='ignore', invalid='ignore'):
            t = (k.astype(F32) - f0) / (f1 - f0)
            h = hermite(val[i], val[j], tout[i], tin[j], t)
        rows[:max_frame] = np.where(on, val[i], h)
    rows[max_frame] = val[m - 1]
    return rows, d + m * ks


def bake_clip(buf, base, limit):
    """The clip at buf[base:limit] -> (identity, record bytes, stats), or raises Reject."""
    c = buf
    max_frame, n = struct.unpack_from('<HB', c, base)
    if n == 0:
        raise Reject('no joints')
    infos = struct.unpack_from(f'<{n}H', c, base + 3)
    parts = c[base + 3 + 2 * n:base + 3 + 3 * n]
    o = base + ((3 + 3 * n + 3) & ~3)
    ofs = struct.unpack_from(f'<{n}I', c, o + 4)
    ident = fnv(c[base:base + 3 + 3 * n])
    joints = []
    cold = bytearray()
    cold_tab = []
    for i in range(n):
        tg = target(infos[i])
        if tg is None:
            joints.append((infos[i], parts[i], 2, None))
            cold_tab.append(NONE)
            continue
        ftype = infos[i] >> 12
        if ftype not in KEY:
            raise Reject(f'joint {i}: key type {ftype}')
        p0 = base + ofs[i]
        if ofs[i] >= limit - base:
            raise Reject(f'joint {i}: key block outside the clip')
        p = p0
        axes = []
        for _ in range(3):
            r, p = axis_rows(c, p, ftype, max_frame)
            axes.append(rad_limit(r) if tg == 'rot' else r)
        if p > limit:
            raise Reject(f'joint {i}: key block runs past the clip')
        block = c[p0:p]
        ident = fnv(block, ident)
        cold_tab.append(len(cold))
        cold += block
        cold += bytes((-len(cold)) & 1)
        joints.append((infos[i], parts[i], 0, axes))
    # columns: a joint whose three axes are constant goes to the const table
    rows_cols, const_vals, jt = [], [], []
    for info, pno, src, axes in joints:
        if src == 2:
            jt.append(struct.pack('<HBBHH', info, pno, 2, 0, 0))
            continue
        if all(np.all(a.view(np.uint32) == a.view(np.uint32)[0]) for a in axes):
            jt.append(struct.pack('<HBBHH', info, pno, 1, len(const_vals), 0))
            const_vals += [a[0] for a in axes]
        else:
            jt.append(struct.pack('<HBBHH', info, pno, 0, len(rows_cols), 0))
            rows_cols += axes
    nrows = max_frame + 1
    stride = (len(rows_cols) + 7) & ~7
    table = np.zeros((nrows, max(stride, 0)), dtype=F32)
    for col, a in enumerate(rows_cols):
        table[:, col] = a
    def al(x):
        return (x + 31) & ~31
    off_joint = 64
    off_ctab = off_joint + 8 * n
    off_const = al(off_ctab + 4 * n)
    off_rows = al(off_const + 4 * len(const_vals))
    off_cold = al(off_rows + 4 * nrows * stride)
    total = al(off_cold + len(cold))
    rec = bytearray(total)
    struct.pack_into('<IHHHHHH8I', rec, 0, ident, max_frame, n, nrows, stride, len(const_vals), 0,
                     off_joint, off_rows, off_const, off_ctab, off_cold, len(cold), limit - base, 0)
    rec[off_joint:off_joint + 8 * n] = b''.join(jt)
    struct.pack_into(f'<{n}I', rec, off_ctab, *cold_tab)
    if const_vals:
        rec[off_const:off_const + 4 * len(const_vals)] = np.array(const_vals, dtype='<f4').tobytes()
    rec[off_rows:off_rows + 4 * nrows * stride] = table.astype('<f4').tobytes()
    rec[off_cold:off_cold + len(cold)] = cold
    stats = {'joints': n, 'pose_joints': sum(1 for j in joints if j[2] != 2), 'row_floats': len(rows_cols),
             'const_floats': len(const_vals), 'rows': nrows, 'hot_bytes': off_cold, 'cold_bytes': len(cold),
             'bytes': total, 'src_bytes': limit - base}
    return ident, bytes(rec), stats


def archive_clips(tree, name):
    """(label, buffer, start, end) of every FCV entry with its keys in the archive, and the dc/mot clips its MTC
    table lists (the prepared archives' proxies)."""
    d = place(open(os.path.join(tree, name), 'rb').read())
    n, = struct.unpack_from('<I', d, 0)
    offs = struct.unpack_from(f'<{n}I', d, 16)
    tags = [d[16 + 4 * n + 4 * i:16 + 4 * n + 4 * i + 4] for i in range(n)]
    ends = sorted(set(offs) | {len(d)})
    proxies = set()
    for i in range(n):
        if tags[i] != b'MTC\0':
            continue
        mtc = offs[i]
        if d[mtc:mtc + 8] != b'R4MOTBL\0':
            continue
        cnt, = struct.unpack_from('<I', d, mtc + 12)
        for k in range(cnt):
            at, size, crc, fv = struct.unpack_from('<4I', d, mtc + 32 + 20 * k)
            proxies.add(at)
            f = os.path.join(tree, 'dc/mot/%08x-%08x.fcv' % (crc, fv))
            c = open(f, 'rb').read()
            yield ('%s:%d (dc/mot/%08x-%08x)' % (name, k, crc, fv), c, 0, len(c))
    for i in range(n):
        if tags[i] != b'FCV\0' or offs[i] in proxies:
            continue
        end = next(e for e in ends if e > offs[i])
        yield ('%s:%d' % (name, i), d, offs[i], end)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tree', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--report')
    ap.add_argument('archives', nargs='+')
    a = ap.parse_args()
    clips = {}
    rejects = []
    tot = {'clips': 0, 'src_bytes': 0, 'bytes': 0, 'hot_bytes': 0, 'cold_bytes': 0, 'row_floats': 0, 'const_floats': 0,
           'pose_joints': 0, 'dups': 0}
    for arc in a.archives:
        for label, buf, s, e in archive_clips(a.tree, arc):
            try:
                ident, rec, st = bake_clip(buf, s, e)
            except Reject as r:
                rejects.append((label, str(r)))
                continue
            if ident in clips:
                # same header and pose key blocks (root-motion or camera blocks may differ: not served from here)
                if clips[ident][0][:40] + clips[ident][0][44:] != rec[:40] + rec[44:]:
                    sys.exit(f'identity collision {ident:08x}: {label} and {clips[ident][1]}')
                tot['dups'] += 1
                continue
            clips[ident] = (rec, label, st)
            tot['clips'] += 1
            for k in ('src_bytes', 'bytes', 'hot_bytes', 'cold_bytes', 'row_floats', 'const_floats', 'pose_joints'):
                tot[k] += st[k]
    order = sorted(clips)
    idx_off = 32
    at = (idx_off + 8 * len(order) + 31) & ~31
    index, body = [], bytearray()
    for ident in order:
        index.append(struct.pack('<II', ident, at + len(body)))
        body += clips[ident][0]
    total = at + len(body)
    out = bytearray(struct.pack('<8s6I', b'RE4MK1\0\0', len(order), idx_off, total, 0, 0, 0))
    out += b''.join(index)
    out += bytes(at - len(out))
    out += body
    open(a.out, 'wb').write(out)
    lines = [f'clips {tot["clips"]} (duplicates {tot["dups"]}), rejected {len(rejects)}',
             f'original clips {tot["src_bytes"]} B; bake {tot["bytes"]} B: hot (joint tables, const, rows) '
             f'{tot["hot_bytes"]} B, cold key blocks {tot["cold_bytes"]} B; pack {total} B',
             f'pose joints {tot["pose_joints"]}: row floats {tot["row_floats"]}, const floats {tot["const_floats"]}']
    lines += [f'rejected {lab}: {why}' for lab, why in rejects]
    if a.report:
        with open(a.report, 'w') as f:
            f.write('\n'.join(lines) + '\n')
            f.write('# identity\tlabel\tjoints\tpose\trows\trow_floats\tconst_floats\thot\tcold\tbytes\tsrc_bytes\n')
            for ident in order:
                rec, lab, st = clips[ident]
                f.write(f'{ident:08x}\t{lab}\t{st["joints"]}\t{st["pose_joints"]}\t{st["rows"]}\t{st["row_floats"]}\t'
                        f'{st["const_floats"]}\t{st["hot_bytes"]}\t{st["cold_bytes"]}\t{st["bytes"]}\t{st["src_bytes"]}\n')
    print('\n'.join(lines[:3]))
    print(f'rejected {len(rejects)}' + (': ' + '; '.join(f'{l} ({w})' for l, w in rejects[:8]) if rejects else ''))


if __name__ == '__main__':
    main()
