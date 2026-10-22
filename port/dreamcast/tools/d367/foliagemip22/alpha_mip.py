#!/usr/bin/env python3
"""Coverage-preserving alpha mip chains for cut-out foliage / branch textures (lane foliagemip22, 2026-10-22).

Opt-in generator mode (default: nothing changes). For a base-only ARGB4444 / ARGB1555 twiddled or full-codebook
VQ package (the mipfix22 gate held its old chain for coverage), it rebuilds the lower levels so that each FINAL
encoded level (after 16-bit quantization and VQ encoding, i.e. what the PVR samples) keeps the base share of texels
at or above the render alpha test (mip_quality.ALPHA_REF):

* colour: premultiplied box filter of the base, un-premultiplied (no dark fringe);
* alpha: straight box filter of the base, then a per-level scale chosen by bisection on the ENCODED level so the
  number of passing texels equals round(base coverage * texels) (standard alpha-to-coverage-preserving mips);
* VQ: the base codebook and base indices stay byte-identical; unused codebook slots get k-means vectors of the
  lower levels (alpha-weighted), then every lower level is encoded against the whole book.

Silhouette check per level: IoU between the encoded alpha mask and a reference mask = the box-filtered base alpha
re-thresholded to the base coverage (top-N texels), plus the coverage error.
The base level is never changed; the caller requalifies the output with mip_quality.audit.
"""
from __future__ import annotations

import struct
import zlib

import convert_tpl as tpl
import mipmap_vq as vq
import mipmap_twiddled as tw

ALPHA_REF = 128


def _filtered_levels(base, side):
    """{side: [(r,g,b,a) floats straight]} for every lower level, box filtered from the base (premultiplied)."""
    cur = [(p[0] * p[3], p[1] * p[3], p[2] * p[3], float(p[3])) for p in base]
    out = {}
    s = side
    while s > 1:
        nxt = []
        for y in range(0, s, 2):
            for x in range(0, s, 2):
                q = (cur[y * s + x], cur[y * s + x + 1], cur[(y + 1) * s + x], cur[(y + 1) * s + x + 1])
                nxt.append(tuple(sum(p[c] for p in q) / 4 for c in range(4)))
        cur, s = nxt, s // 2
        lvl = []
        for r, g, b, a in cur:
            lvl.append((r / a, g / a, b / a, a) if a > 0 else (0.0, 0.0, 0.0, 0.0))
        out[s] = lvl
    return out


def _apply(level, n_pass):
    """Rank-forced alpha: the n_pass texels with the highest filtered alpha pass the alpha test (>= 136, the
    smallest ARGB4444 value >= ALPHA_REF), every other texel stays below it; soft alpha is otherwise kept."""
    keep = ref_mask(level, n_pass)
    out = []
    for (r, g, b, a), k in zip(level, keep):
        a = int(a + .5)
        a = max(a, 136) if k else min(a, ALPHA_REF - 1)
        out.append((min(255, int(r + .5)), min(255, int(g + .5)), min(255, int(b + .5)), a))
    return out


def ref_mask(level, n_pass):
    order = sorted(range(len(level)), key=lambda i: (-level[i][3], i))
    keep = set(order[:n_pass])
    return [i in keep for i in range(len(level))]


def iou(m1, m2):
    inter = sum(a and b for a, b in zip(m1, m2))
    union = sum(a or b for a, b in zip(m1, m2))
    return 1.0 if union == 0 else inter / union


def _target(cov0, n):  # noqa
    return int(cov0 * n + 0.5)


def _search(level, n_target, encode_count):
    """Forced pass count n in [0, len] whose ENCODED count is closest to the target (bisection; the encoded count
    is monotone in n up to VQ noise)."""
    lo, hi = 0, len(level)
    best = None
    n = n_target
    for _ in range(14):
        c, payload = encode_count(n)
        if best is None or abs(c - n_target) < abs(best[0] - n_target):
            best = (c, payload, n)
        if c == n_target or lo >= hi:
            break
        if c < n_target:
            lo = n + 1
        else:
            hi = n - 1
        if lo > hi:
            break
        n = (lo + hi) // 2
    return best


def _tiny_target(cov0, n, small):
    """mip_quality tiny-level rule: 2x2 / 1x1 follow the encoded 4x4 share (1x1 = majority)."""
    if n < 16 and small is not None:
        return int(small * n + 0.5)
    return _target(cov0, n)


# ---------------- twiddled 16-bit ----------------

def _pack_fn(fmt):
    return {tpl.FORMAT_ARGB1555: tpl._pack_1555, tpl.FORMAT_ARGB4444: tpl._pack_4444}[fmt]


def twiddled_chain(blob):
    native = tw.read_native_twiddled(blob)
    fmt = native.texture[3]
    pack = _pack_fn(fmt)
    side = native.size
    base = tw.decode_level(native, side)
    cov0 = sum(p[3] >= ALPHA_REF for p in base) / len(base)
    levels = _filtered_levels(base, side)
    chain = bytearray(tw.chain_bytes(side))
    chain[tw.level_offset(side):] = native.base_texels
    report, small = [], None
    for s in sorted(levels, reverse=True):
        lvl = levels[s]
        n = s * s
        want = _tiny_target(cov0, n, small)

        def enc(scale, lvl=lvl):  # scale = forced pass count
            words = [pack(p) for p in _apply(lvl, scale)]
            px = [vq.rgba(w, fmt) for w in words]
            return sum(p[3] >= ALPHA_REF for p in px), (words, px)
        c, (words, px), scale = _search(lvl, want, enc)
        tw_words = tpl.twiddle_16bpp(words, s, s) if s > 1 else words
        at = tw.level_offset(s)
        chain[at:at + 2 * n] = struct.pack("<%dH" % n, *tw_words)
        mask = [p[3] >= ALPHA_REF for p in px]
        report.append(dict(side=s, target=want, passing=c, coverage=round(c / n, 4),
                           coverage_err=round(c / n - cov0, 4), iou=round(iou(mask, ref_mask(lvl, want)), 4),
                           forced_pass=scale))
        if s == 4:
            small = c / n
    h, t = list(native.header), list(native.texture)
    t[5], t[6], h[7] = len(chain), t[6] | tpl.FLAG_MIPMAP, len(chain)
    body = tpl.TEXTURE.pack(*t) + bytes(chain)
    h[8] = zlib.crc32(body) & 0xffffffff
    out = tpl.HEADER.pack(*h) + body
    if tw.read_native_twiddled(out).base_texels != native.base_texels:
        raise ValueError("base changed")
    return out, dict(base_coverage=round(cov0, 4), levels=report,
                     before_payload_bytes=len(native.payload), after_payload_bytes=len(chain))


# ---------------- VQ ----------------

def _blocks(px, s):
    blocks = s // 2
    order = tpl.twiddle_16bpp(list(range(blocks * blocks)), blocks, blocks)
    out = []
    for linear in order:
        x, y = (linear % blocks) * 2, (linear // blocks) * 2
        out.append((px[y * s + x], px[(y + 1) * s + x], px[y * s + x + 1], px[(y + 1) * s + x + 1]))
    return out


AW = 3  # alpha weight in codeword matching (the mask is what thins / fills in)


def _feat(vec):
    f = []
    for r, g, b, a in vec:
        f += [r * a / 255, g * a / 255, b * a / 255, AW * a]
    return f


def _nearest(target, feats, cache):
    key = tuple(target)
    hit = cache.get(key)
    if hit is not None:
        return hit
    best, err = 0, None
    for i, f in enumerate(feats):
        e = 0.0
        for a, b in zip(key, f):
            e += (a - b) ** 2
            if err is not None and e >= err:
                break
        if err is None or e < err:
            best, err = i, e
    cache[key] = best
    return best


def _kmeans(points, k, iters=8):
    if not points or k <= 0:
        return []
    uniq = list(dict.fromkeys(tuple(p) for p in points))
    if len(uniq) <= k:
        return [list(p) for p in uniq]
    step = len(uniq) / k
    cent = [list(uniq[int(i * step)]) for i in range(k)]
    for _ in range(iters):
        sums = [[0.0] * len(cent[0]) for _ in cent]
        cnt = [0] * len(cent)
        for p in points:
            j = min(range(len(cent)), key=lambda j: sum((a - b) ** 2 for a, b in zip(p, cent[j])))
            cnt[j] += 1
            for d, v in enumerate(p):
                sums[j][d] += v
        cent = [[v / cnt[j] for v in sums[j]] if cnt[j] else cent[j] for j in range(len(cent))]
    return cent


def vq_chain(blob):
    native = vq.read_native_vq(blob)
    fmt = native.texture[3]
    pack = _pack_fn(fmt)
    side = native.size
    base = vq.decode_level(native, side)
    cov0 = sum(p[3] >= ALPHA_REF for p in base) / len(base)
    levels = _filtered_levels(base, side)
    used = sorted(set(native.base_indices))
    free = [i for i in range(256) if i not in set(used)]
    words = list(struct.unpack("<1024H", native.codebook))
    # Spare slots: k-means over the lower-level 2x2 blocks at their coverage-matching scale on plain 16-bit
    # quantization (a first estimate; final scale is searched on the VQ-encoded level below).
    pts = []
    if free:
        for s in sorted(levels, reverse=True):
            if s < 2:
                continue
            lvl = levels[s]
            want = _target(cov0, s * s)

            def q16(scale, lvl=lvl):  # scale = forced pass count
                px = [vq.rgba(pack(p), fmt) for p in _apply(lvl, scale)]
                return sum(p[3] >= ALPHA_REF for p in px), px
            _, px, _ = _search(lvl, want, q16)
            for blk in _blocks(px, s):
                pts.append(_feat(blk))
        cents = _kmeans(pts, len(free))
        for slot, cfeat in zip(free, cents):
            vec = []
            for t in range(4):
                pr, pg, pb, aw = cfeat[4 * t:4 * t + 4]
                a = max(0.0, min(255.0, aw / AW))
                if a > 0:
                    rgb = [max(0, min(255, int(c * 255 / a + .5))) for c in (pr, pg, pb)]
                else:
                    rgb = [0, 0, 0]
                vec.append(pack((rgb[0], rgb[1], rgb[2], int(a + .5))))
            words[4 * slot:4 * slot + 4] = vec
    codebook = struct.pack("<1024H", *words)
    book = [tuple(vq.rgba(w, fmt) for w in words[i:i + 4]) for i in range(0, 1024, 4)]
    feats = [_feat(v) for v in book]
    feats1 = [_feat([v[3]])for v in book]   # 1x1 samples the BR texel
    idx = {side: native.base_indices}
    report, small = [], None
    for s in sorted(levels, reverse=True):
        lvl = levels[s]
        n = s * s
        want = _tiny_target(cov0, n, small)
        cache = {}

        def enc(scale, lvl=lvl, s=s, cache=cache):  # scale = forced pass count
            px = _apply(lvl, scale)
            if s == 1:
                i = _nearest(_feat([px[0]]), feats1, cache)
                dec = [book[i][3]]
                return int(dec[0][3] >= ALPHA_REF), (bytes([i]), dec)
            ids = [_nearest(_feat(b), feats, cache) for b in _blocks(px, s)]
            dec = _decode_flat(book, ids, s)
            return sum(p[3] >= ALPHA_REF for p in dec), (bytes(ids), dec)
        c, (ib, dec), scale = _search(lvl, want, enc)
        idx[s] = ib
        mask = [p[3] >= ALPHA_REF for p in dec]
        report.append(dict(side=s, target=want, passing=c, coverage=round(c / n, 4),
                           coverage_err=round(c / n - cov0, 4), iou=round(iou(mask, ref_mask(lvl, want)), 4),
                           forced_pass=scale))
        if s == 4:
            small = c / n
    payload = codebook + b"".join(idx[1 << i] for i in range(side.bit_length()))
    assert len(payload) == 2048 + tpl.vq_mip_index_bytes(side)
    h, t = list(native.header), list(native.texture)
    t[5], t[6] = len(payload), t[6] | tpl.FLAG_MIPMAP
    h[7] = len(payload)
    body = tpl.TEXTURE.pack(*t) + payload
    h[8] = zlib.crc32(body) & 0xffffffff
    out = tpl.HEADER.pack(*h) + body
    chk = vq.read_native_vq(out)
    if chk.base_indices != native.base_indices or vq.decode_level(chk, side) != base:
        raise ValueError("base changed")
    return out, dict(base_coverage=round(cov0, 4), levels=report, codebook_used=len(used), spare_slots=len(free),
                     before_payload_bytes=len(native.payload), after_payload_bytes=len(payload))


def _decode_flat(book, ids, s):
    blocks = s // 2
    order = tpl.twiddle_16bpp(list(range(blocks * blocks)), blocks, blocks)
    px = [None] * (s * s)
    for at, linear in enumerate(order):
        x, y = (linear % blocks) * 2, (linear // blocks) * 2
        q = book[ids[at]]
        px[y * s + x], px[(y + 1) * s + x], px[y * s + x + 1], px[(y + 1) * s + x + 1] = q
    return px


def coverage_chain(blob, *, enabled=False):
    """(package, report). Disabled: the input bytes, unchanged."""
    if not enabled:
        return blob, dict(enabled=False)
    try:
        native = vq.read_native_vq(blob)
        kind = "vq"
    except ValueError:
        native = tw.read_native_twiddled(blob)
        kind = "twiddled"
    if native.mipmapped:
        raise ValueError("input already mipmapped")
    if native.texture[3] not in (tpl.FORMAT_ARGB1555, tpl.FORMAT_ARGB4444):
        raise ValueError("needs an alpha 16-bit format")
    out, rep = (vq_chain if kind == "vq" else twiddled_chain)(blob)
    rep.update(enabled=True, kind=kind)
    return out, rep
