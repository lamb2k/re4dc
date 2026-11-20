"""motion_keys.py: offline motion keys for the native skeleton service (lanes eng-svc2, eng-svc3; SERVICES.md 10, 16).

The game samples a motion clip ("FCV": per joint three axis key streams, Hermite keys at integer frames, in nine
encodings) with HermiteInterpolation: a search from a per-bone key history, then the Hermite blend of the bracketing
pair. The engine samples from this bake instead: per clip, a table of every value at every integer frame
(frame-major: one row a frame), so a tick at an integer frame reads one row and nothing else. No search, no history,
no key decoding.

  python3 motion_keys.py --tree <converted data tree> --out motion.mkp [--rows f32|s16] [--qscale column|clip]
                         [--set <file>] [--report <tsv>] em/pl00.drs em/wep02.drs ...

Inputs: the archives' FCV entries (the DVD container placed as the game places it, the tagged archive's "FCV"
entries) and, for the prepared enemy archives whose FCV entries are proxies, the full clips in dc/mot/*.fcv.

Channels (round 3, lane eng-svc3):
  - pose channels (bone rotation, position, scale: what MotionMoveCore writes) go to the pose rows, or to the const
    table when a joint's three axes never change. --rows f32 stores the values (exact); --rows s16 stores each value
    as a 16-bit step between a column's minimum and maximum (--qscale column: a scale and an offset per column;
    --qscale clip: one pair for the whole clip). An approximation (owner 2026-10-19): the report gives each clip's
    largest error;
  - root channels (Null_pos, kind 1; Null_rot, kind 0x40: MotionGetSpeed's root motion and MotionSetCore's start
    values) and camera channels (the attach camera's, channel 6 / 7) go to the aux rows, always float32: root motion
    moves the actor, so it stays exact.
  - nothing is copied for fractional frames (0.2% of samples on the fixtures): the service decodes those from the
    clip's own key blocks, which stay resident with the archive, by a key search from key 0 (no history). On these
    clips that gives the original's values: every axis's keys start at 0, end at maxFrame and rise strictly (checked
    here), so the search from key 0 finds the same bracket the history search finds.
A clip any served joint of which fails those checks is not baked (the service then decodes every frame of it from
its keys). --set keeps only the clips listed (archive:entry labels or identities, one a line): the per-room clip
set; a clip outside it is decoded from its keys too (counted, exact, slower).

Exactness (PC, the reference's SSE single precision): every value is computed with the original's operations in
its order in float32 (numpy float32 is IEEE single, no contraction): the key fields decoded as Fcc_get_data_*
decodes them (s16 and s8 times 0.0001f), then hermite() (math_sub.cpp) at t = (frame - f0) / (f1 - f0); a frame on a
key takes the key's value; pose rotations are stored after VecRadLimit (idempotent on its own output), as
MotionMoveCore applies it; the last row (frame maxFrame) holds each axis's last key: the original's answer for a
frame at or past the end of a clip that does not loop.

Pack layout (little-endian), "RE4MK2":
  header 32 B   "RE4MK2\\0\\0", u32 clips, u32 index offset, u32 bytes, u32 flags (1: s16 rows), u32 0 x2
  index         per clip: u32 identity, u32 offset (sorted by identity)
  clips         32-aligned, each:
    0   u32 identity   FNV-1a of the clip header (maxFrame, joint count, kinds, parts) and every served joint's key
                       block in joint order: what the service computes from MotionSetCore's key table
    4   u16 maxFrame, u16 joints
    8   u16 rows (maxFrame + 1), u16 stride (values a pose row: rows start on a 32-byte line)
    12  u16 const floats, u16 flags (1: pose rows are s16 steps)
    16  u16 aux columns, u16 aux stride (floats an aux row: the aux columns, unpadded)
    20  u32 joint table, pose rows, const, aux rows, quant table (offsets from the clip), u32 the original clip's bytes,
        u32 0 x5
    64  joint table: per joint u16 kind word (as the original), u8 parts, u8 source (0 pose rows, 1 const, 2 aux rows,
        3 not served: the original skips it), u16 first column, u16 0
        const: floats; quant (s16 only): per pose column f32 scale, f32 offset (value = offset + step x scale);
        pose rows: rows x stride (f32 or u16); aux rows: rows x aux stride f32
"""
import argparse
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
SRC_ROWS, SRC_CONST, SRC_AUX, SRC_NONE = 0, 1, 2, 3


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


def channel(info):
    """What a joint is to the service: 'rot' / 'pos' / 'scale' (pose: MotionMoveCore's channel test), 'aux' (root
    motion: kind 1 / 0x40; the attach camera: channel 6 / 7), or None (the original skips it)."""
    kind, ch = info & 0xFF, (info >> 8) & 0xF
    if ch in (6, 7) or kind in (1, 0x40):
        return 'aux'
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
    frac = None
    if FRAC and max_frame > 0:
        # the exact values a quarter, a half and three quarters past each integer frame (--frac-check)
        k = np.repeat(np.arange(max_frame), 3).astype(F32) + np.tile(np.array([0.25, 0.5, 0.75], dtype=F32), max_frame)
        i = np.searchsorted(fr, k, side='right') - 1
        j = np.minimum(i + 1, m - 1)
        f0 = fr[i].astype(F32)
        f1 = fr[j].astype(F32)
        t = (k - f0) / (f1 - f0)
        frac = hermite(val[i], val[j], tout[i], tin[j], t).reshape(max_frame, 3)
    return rows, d + m * ks, frac


FRAC = False
FRAC_ERR = {'lerp_rot': 0.0, 'lerp_pos': 0.0, 'lerp_aux': 0.0, 'cr_rot': 0.0, 'cr_pos': 0.0, 'cr_aux': 0.0}


def frac_check(rows, frac, rot):
    """the largest error of a fractional frame served from the rows (linear; Catmull-Rom over four rows) against the keys"""
    r = rows.astype(np.float64)
    if rot:   # unwrap the rows (they are VecRadLimit's output) so neighbours are continuous
        r = np.unwrap(r)
    ex = frac.astype(np.float64)
    pm = np.concatenate([[r[0]], r[:-2]])             # row k-1 (clamped)
    p0, p1 = r[:-1], r[1:]
    p2 = np.concatenate([r[2:], [r[-1]]])              # row k+2 (clamped)
    worst = {}
    for name, fn in (('lerp', lambda u: p0 + (p1 - p0) * u),
                     ('cr', lambda u: 0.5 * (2 * p0 + (-pm + p1) * u + (2 * pm - 5 * p0 + 4 * p1 - p2) * u * u
                                            + (-pm + 3 * p0 - 3 * p1 + p2) * u ** 3))):
        e = 0.0
        for c, u in enumerate((0.25, 0.5, 0.75)):
            d = fn(u) - ex[:, c]
            if rot:
                d = (d + np.pi) % (2 * np.pi) - np.pi
            e = max(e, float(np.max(np.abs(d))) if len(d) else 0.0)
        worst[name] = e
    return worst


def quantise(cols, mode):
    """cols: list of float32 arrays (one per pose column). -> (u16 steps per column, scale, offset per column, largest
    error per column) with value = offset + step * scale in float32, as the service computes it."""
    if not cols:
        return [], [], [], []
    if mode == 'clip':
        lo_all = min(F32(c.min()) for c in cols)
        hi_all = max(F32(c.max()) for c in cols)
    q, sc, of, er = [], [], [], []
    for c in cols:
        lo, hi = (lo_all, hi_all) if mode == 'clip' else (F32(c.min()), F32(c.max()))
        s = F32((np.float64(hi) - np.float64(lo)) / 65535.0)
        if s == 0:
            k = np.zeros(len(c), dtype=np.uint16)
        else:
            k = np.clip(np.rint((c.astype(np.float64) - np.float64(lo)) / np.float64(s)), 0, 65535).astype(np.uint16)
            # the nearest step in float32 as the service forms it (offset + step x scale)
            for d in (-1, 1):
                k2 = np.clip(k.astype(np.int64) + d, 0, 65535).astype(np.uint16)
                e1 = np.abs((lo + k.astype(F32) * s) - c)
                e2 = np.abs((lo + k2.astype(F32) * s) - c)
                k = np.where(e2 < e1, k2, k)
        v = lo + k.astype(F32) * s
        q.append(k)
        sc.append(s)
        of.append(lo)
        er.append(float(np.max(np.abs(v - c))) if len(c) else 0.0)
    return q, sc, of, er


def bake_clip(buf, base, limit, rows_fmt='f32', qmode='column'):
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
    for i in range(n):
        tg = channel(infos[i])
        if tg is None:
            joints.append((infos[i], parts[i], SRC_NONE, None, None))
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
            r, p, fr_ = axis_rows(c, p, ftype, max_frame)
            if fr_ is not None:
                w = frac_check(r, fr_, tg == 'rot')
                kk = tg if tg in ('rot', 'aux') else 'pos'
                for nm in ('lerp', 'cr'):
                    FRAC_ERR[nm + '_' + kk] = max(FRAC_ERR[nm + '_' + kk], w[nm])
            axes.append(rad_limit(r) if tg == 'rot' else r)
        if p > limit:
            raise Reject(f'joint {i}: key block runs past the clip')
        ident = fnv(c[p0:p], ident)
        joints.append((infos[i], parts[i], SRC_AUX if tg == 'aux' else SRC_ROWS, axes, tg))
    # columns: a pose joint whose three axes are constant goes to the const table; aux joints to the aux rows
    pose_cols, aux_cols, const_vals, jt, kinds = [], [], [], [], []
    for info, pno, src, axes, tg in joints:
        if src == SRC_NONE:
            jt.append(struct.pack('<HBBHH', info, pno, SRC_NONE, 0, 0))
        elif src == SRC_AUX:
            jt.append(struct.pack('<HBBHH', info, pno, SRC_AUX, len(aux_cols), 0))
            aux_cols += axes
        elif all(np.all(a.view(np.uint32) == a.view(np.uint32)[0]) for a in axes):
            jt.append(struct.pack('<HBBHH', info, pno, SRC_CONST, len(const_vals), 0))
            const_vals += [a[0] for a in axes]
        else:
            jt.append(struct.pack('<HBBHH', info, pno, SRC_ROWS, len(pose_cols), 0))
            pose_cols += axes
            kinds += [tg] * 3
    nrows = max_frame + 1
    s16 = rows_fmt == 's16'
    esz = 2 if s16 else 4
    stride = (len(pose_cols) + (15 if s16 else 7)) & ~(15 if s16 else 7)
    astride = len(aux_cols)   # aux rows unpadded: a tick reads two joints' values (root position and rotation)
    err = {'rot': 0.0, 'pos': 0.0, 'scale': 0.0}
    if s16:
        q, sc, of, er = quantise(pose_cols, qmode)
        table = np.zeros((nrows, stride), dtype='<u2')
        for col, a in enumerate(q):
            table[:, col] = a
            err[kinds[col]] = max(err[kinds[col]], er[col])
        quant = np.array([x for pair in zip(sc, of) for x in pair], dtype='<f4')
    else:
        table = np.zeros((nrows, stride), dtype='<f4')
        for col, a in enumerate(pose_cols):
            table[:, col] = a
        quant = np.zeros(0, dtype='<f4')
    aux = np.zeros((nrows, astride), dtype='<f4')
    for col, a in enumerate(aux_cols):
        aux[:, col] = a

    def al(x):
        return (x + 31) & ~31
    off_joint = 64
    off_const = al(off_joint + 8 * n)
    off_quant = al(off_const + 4 * len(const_vals))
    off_rows = al(off_quant + 4 * len(quant))
    off_aux = al(off_rows + esz * nrows * stride)
    total = al(off_aux + 4 * nrows * astride)
    rec = bytearray(total)
    struct.pack_into('<I8H6I5I', rec, 0, ident, max_frame, n, nrows, stride, len(const_vals), 1 if s16 else 0,
                     len(aux_cols), astride, off_joint, off_rows, off_const, off_aux, off_quant, limit - base, 0, 0, 0, 0, 0)
    rec[off_joint:off_joint + 8 * n] = b''.join(jt)
    if const_vals:
        rec[off_const:off_const + 4 * len(const_vals)] = np.array(const_vals, dtype='<f4').tobytes()
    if len(quant):
        rec[off_quant:off_quant + 4 * len(quant)] = quant.tobytes()
    rec[off_rows:off_rows + esz * nrows * stride] = table.tobytes()
    rec[off_aux:off_aux + 4 * nrows * astride] = aux.astype('<f4').tobytes()
    stats = {'joints': n, 'pose_joints': sum(1 for j in joints if j[2] in (SRC_ROWS, SRC_CONST)),
             'aux_joints': sum(1 for j in joints if j[2] == SRC_AUX), 'row_cols': len(pose_cols),
             'aux_cols': len(aux_cols), 'const_floats': len(const_vals), 'rows': nrows,
             'pose_bytes': esz * nrows * stride, 'aux_bytes': 4 * nrows * astride, 'bytes': total,
             'src_bytes': limit - base, 'err_rot': err['rot'], 'err_pos': err['pos'], 'err_scale': err['scale']}
    return ident, bytes(rec), stats


def archive_clips(tree, name):
    """(label, buffer, start, end) of every FCV entry of the archive, label = archive:entry. A prepared archive's FCV
    entries are proxies: the full clip is the dc/mot file its MTC table names."""
    d = place(open(os.path.join(tree, name), 'rb').read())
    n, = struct.unpack_from('<I', d, 0)
    offs = struct.unpack_from(f'<{n}I', d, 16)
    tags = [d[16 + 4 * n + 4 * i:16 + 4 * n + 4 * i + 4] for i in range(n)]
    ends = sorted(set(offs) | {len(d)})
    proxies = {}
    for i in range(n):
        if tags[i] != b'MTC\0':
            continue
        mtc = offs[i]
        if d[mtc:mtc + 8] != b'R4MOTBL\0':
            continue
        cnt, = struct.unpack_from('<I', d, mtc + 12)
        for k in range(cnt):
            at, size, crc, fv = struct.unpack_from('<4I', d, mtc + 32 + 20 * k)
            proxies[at] = 'dc/mot/%08x-%08x.fcv' % (crc, fv)
    for i in range(n):
        if tags[i] != b'FCV\0':
            continue
        if offs[i] in proxies:
            c = open(os.path.join(tree, proxies[offs[i]]), 'rb').read()
            yield ('%s:%d' % (name, i), c, 0, len(c))
        else:
            end = next(e for e in ends if e > offs[i])
            yield ('%s:%d' % (name, i), d, offs[i], end)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tree', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--rows', choices=('f32', 's16'), default='f32')
    ap.add_argument('--qscale', choices=('column', 'clip'), default='column')
    ap.add_argument('--set', help='keep only these clips (archive:entry labels or 8-digit identities, one a line)')
    ap.add_argument('--report')
    ap.add_argument('--frac-check', action='store_true', help='the error of fractional frames served from the rows')
    ap.add_argument('archives', nargs='+')
    a = ap.parse_args()
    global FRAC
    FRAC = a.frac_check
    keep = None
    if a.set:
        keep = set(l.split('#')[0].strip() for l in open(a.set)) - {''}
    clips, rejects, labels, allst = {}, [], {}, {}
    tot = {'clips': 0, 'src_bytes': 0, 'bytes': 0, 'pose_bytes': 0, 'aux_bytes': 0, 'row_cols': 0, 'aux_cols': 0,
           'const_floats': 0, 'pose_joints': 0, 'dups': 0, 'left_out': 0}
    errs = {'err_rot': 0.0, 'err_pos': 0.0, 'err_scale': 0.0}
    for arc in a.archives:
        for label, buf, s, e in archive_clips(a.tree, arc):
            try:
                ident, rec, st = bake_clip(buf, s, e, a.rows, a.qscale)
            except Reject as r:
                rejects.append((label, str(r)))
                continue
            labels.setdefault(ident, []).append(label)
            allst[ident] = st
            if keep is not None and label not in keep and '%08x' % ident not in keep:
                continue
            if ident in clips:
                if clips[ident][0] != rec:
                    sys.exit(f'identity collision {ident:08x}: {label} and {clips[ident][1]}')
                tot['dups'] += 1
                continue
            clips[ident] = (rec, label, st)
            tot['clips'] += 1
            for k in ('src_bytes', 'bytes', 'pose_bytes', 'aux_bytes', 'row_cols', 'aux_cols', 'const_floats',
                      'pose_joints'):
                tot[k] += st[k]
            for k in errs:
                errs[k] = max(errs[k], st[k])
    if keep is not None:
        tot['left_out'] = sum(1 for i in labels if i not in clips)
    order = sorted(clips)
    idx_off = 32
    at = (idx_off + 8 * len(order) + 31) & ~31
    index, body = [], bytearray()
    for ident in order:
        index.append(struct.pack('<II', ident, at + len(body)))
        body += clips[ident][0]
    total = at + len(body)
    out = bytearray(struct.pack('<8s5I', b'RE4MK2\0\0', len(order), idx_off, total, 1 if a.rows == 's16' else 0, 0))
    out += bytes(32 - len(out))
    out += b''.join(index)
    out += bytes(at - len(out))
    out += body
    open(a.out, 'wb').write(out)
    lines = [f'rows {a.rows}' + (f' (scale per {a.qscale})' if a.rows == 's16' else '') +
             f'; clips {tot["clips"]} (duplicates {tot["dups"]}, outside the set {tot["left_out"]}), rejected {len(rejects)}',
             f'original clips {tot["src_bytes"]} B; bake {tot["bytes"]} B (pose rows {tot["pose_bytes"]}, aux rows '
             f'{tot["aux_bytes"]}, tables and const the rest); pack {total} B',
             f'pose joints {tot["pose_joints"]}: row columns {tot["row_cols"]}, const floats {tot["const_floats"]}; '
             f'aux columns {tot["aux_cols"]}',
             'largest step error: rotation %.3g rad (%.4g deg), position %.3g u, scale %.3g' %
             (errs['err_rot'], np.degrees(errs['err_rot']), errs['err_pos'], errs['err_scale'])]
    lines += [f'rejected {lab}: {why}' for lab, why in rejects]
    if a.report:
        with open(a.report, 'w') as f:
            f.write('\n'.join(lines) + '\n')
            f.write('# identity\tlabels\tjoints\tpose\taux\trows\trow_cols\taux_cols\tconst\tpose_bytes\taux_bytes\tbytes\t'
                    'src_bytes\terr_rot\terr_pos\tbaked\n')
            for ident in sorted(labels):
                st = allst[ident]
                f.write(f'{ident:08x}\t{",".join(labels[ident])}\t{st["joints"]}\t{st["pose_joints"]}\t{st["aux_joints"]}\t'
                        f'{st["rows"]}\t{st["row_cols"]}\t{st["aux_cols"]}\t{st["const_floats"]}\t{st["pose_bytes"]}\t'
                        f'{st["aux_bytes"]}\t{st["bytes"]}\t{st["src_bytes"]}\t{st["err_rot"]:.3g}\t{st["err_pos"]:.3g}\t'
                        f'{int(ident in clips)}\n')
    if FRAC:
        lines.insert(4, 'fractional frames from the rows (against the keys): linear: pose rotation %.4g deg, position %.4g u, '
                        'root / camera %.4g; Catmull-Rom: %.4g deg, %.4g u, %.4g' % (
                            np.degrees(FRAC_ERR['lerp_rot']), FRAC_ERR['lerp_pos'], FRAC_ERR['lerp_aux'],
                            np.degrees(FRAC_ERR['cr_rot']), FRAC_ERR['cr_pos'], FRAC_ERR['cr_aux']))
    print('\n'.join(lines[:5 if FRAC else 4]))
    print(f'rejected {len(rejects)}' + (': ' + '; '.join(f'{l} ({w})' for l, w in rejects[:8]) if rejects else ''))


if __name__ == '__main__':
    main()
