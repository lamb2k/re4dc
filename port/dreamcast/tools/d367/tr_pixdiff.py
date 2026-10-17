#!/usr/bin/env python3
"""tr_pixdiff.py: Tier 2 look gate for transparency changes (lane trans17, 2026-10-17).

TRANSPARENCY-PLAN-20261017.md section 5. Compares two framebuffer stills of the same frame and frozen camera
(A = today, B = the policy arm) and decides Tier 2 versus Tier 3 with the coordinator's thresholds (10-17):

  pass (Tier 2) when  changed pixels <= --max-pct (1.0 % of the frame)
                 and  no changed pixel outside the silhouette mask dilated by --dilate (2 px)
                 and  max per-channel delta inside the mask <= --max-delta (24 / 255).

The mask is the converted geometry's silhouette: --mask IMG (any non-black pixel), or --mask-diff HL (pixels where
HL, the TRANS_POLICY_DEBUG still with the class highlighted, differs from A). Without a mask the outside test cannot
be made and the verdict is "tier3 (no mask)". A pixel "changed" when any channel differs by more than --tol (0).

Inputs: PNG (8-bit gray/RGB/RGBA, non-interlaced) or binary PPM (P6). No third-party modules.
Output: one JSON object on stdout (or --json FILE); --heat FILE writes a PNG of |A-B| (x4, red outside the mask).
Exit: 0 tier2 pass, 1 tier3, 2 input error.
"""
import argparse
import json
import struct
import sys
import zlib


def read_png(blob):
    if blob[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not PNG')
    at, idat, w = 8, b'', None
    while at < len(blob):
        n, t = struct.unpack_from('>I4s', blob, at)
        d = blob[at + 8:at + 8 + n]
        at += 12 + n
        if t == b'IHDR':
            w, h, depth, ctype, comp, filt, inter = struct.unpack('>IIBBBBB', d)
            if depth != 8 or inter or ctype not in (0, 2, 6):
                raise ValueError('PNG: 8-bit gray/RGB/RGBA, non-interlaced only')
        elif t == b'IDAT':
            idat += d
        elif t == b'IEND':
            break
    bpp = {0: 1, 2: 3, 6: 4}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    out = bytearray(w * h * 3)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        o = y * w * 3
        if bpp == 1:
            for x in range(w):
                out[o + 3 * x:o + 3 * x + 3] = bytes((line[x],)) * 3
        else:
            for x in range(w):
                out[o + 3 * x:o + 3 * x + 3] = line[x * bpp:x * bpp + 3]
    return w, h, out


def read_ppm(blob):
    tok, at = [], 2
    while len(tok) < 3:
        while blob[at:at + 1].isspace():
            at += 1
        if blob[at:at + 1] == b'#':
            at = blob.index(b'\n', at) + 1
            continue
        s = at
        while not blob[at:at + 1].isspace():
            at += 1
        tok.append(int(blob[s:at]))
    w, h, mx = tok
    if mx != 255:
        raise ValueError('PPM: maxval 255 only')
    at += 1
    return w, h, bytearray(blob[at:at + w * h * 3])


def read_img(path):
    with open(path, 'rb') as fh:
        blob = fh.read()
    if blob[:2] == b'P6':
        return read_ppm(blob)
    return read_png(blob)


def write_png(path, w, h, rgb):
    raw = b''.join(b'\0' + bytes(rgb[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as fh:
        fh.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                 chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def dilate(mask, w, h, r):
    if r <= 0:
        return mask
    # separable Chebyshev dilation (square of side 2r+1)
    tmp = bytearray(w * h)
    for y in range(h):
        row = y * w
        for x in range(w):
            if mask[row + x]:
                for xx in range(max(0, x - r), min(w, x + r + 1)):
                    tmp[row + xx] = 1
    out = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            if tmp[y * w + x]:
                for yy in range(max(0, y - r), min(h, y + r + 1)):
                    out[yy * w + x] = 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('a', help='A still (today)')
    ap.add_argument('b', help='B still (policy arm)')
    m = ap.add_mutually_exclusive_group()
    m.add_argument('--mask', help='silhouette mask image (non-black = converted geometry)')
    m.add_argument('--mask-diff', help='highlight still: mask = pixels where it differs from A')
    ap.add_argument('--dilate', type=int, default=2)
    ap.add_argument('--max-pct', type=float, default=1.0)
    ap.add_argument('--max-delta', type=int, default=24)
    ap.add_argument('--tol', type=int, default=0)
    ap.add_argument('--label', default='')
    ap.add_argument('--json')
    ap.add_argument('--heat')
    a = ap.parse_args()
    try:
        wa, ha, A = read_img(a.a)
        wb, hb, B = read_img(a.b)
        if (wa, ha) != (wb, hb):
            raise ValueError('size %dx%d vs %dx%d' % (wa, ha, wb, hb))
        w, h = wa, ha
        mask = None
        if a.mask or a.mask_diff:
            wm, hm, M = read_img(a.mask or a.mask_diff)
            if (wm, hm) != (w, h):
                raise ValueError('mask size')
            if a.mask:
                mask = bytearray(1 if (M[3 * i] | M[3 * i + 1] | M[3 * i + 2]) else 0 for i in range(w * h))
            else:
                mask = bytearray(1 if M[3 * i:3 * i + 3] != A[3 * i:3 * i + 3] else 0 for i in range(w * h))
            mask = dilate(mask, w, h, a.dilate)
    except (OSError, ValueError, zlib.error, struct.error) as e:
        print(json.dumps(dict(error=str(e))))
        return 2
    n = w * h
    changed = outside = 0
    max_in = max_out = 0
    sum_d = [0, 0, 0]
    heat = bytearray(n * 3) if a.heat else None
    for i in range(n):
        d0 = abs(A[3 * i] - B[3 * i])
        d1 = abs(A[3 * i + 1] - B[3 * i + 1])
        d2 = abs(A[3 * i + 2] - B[3 * i + 2])
        md = max(d0, d1, d2)
        if md <= a.tol:
            continue
        changed += 1
        sum_d[0] += d0
        sum_d[1] += d1
        sum_d[2] += d2
        ins = mask is not None and mask[i]
        if ins:
            max_in = max(max_in, md)
        else:
            outside += 1
            max_out = max(max_out, md)
        if heat is not None:
            v = min(255, md * 4)
            heat[3 * i:3 * i + 3] = bytes((v, v, v)) if ins else bytes((255, 0, 0))
    pct = 100.0 * changed / n
    reasons = []
    if pct > a.max_pct:
        reasons.append('changed %.3f%% > %.3f%%' % (pct, a.max_pct))
    if mask is None and changed:
        reasons.append('no mask')
    elif outside:
        reasons.append('%d px changed outside the %d-px mask' % (outside, a.dilate))
    if max_in > a.max_delta:
        reasons.append('max delta inside %d > %d' % (max_in, a.max_delta))
    res = dict(label=a.label, a=a.a, b=a.b, width=w, height=h, changed=changed, changed_pct=round(pct, 4),
               mean_delta=[round(s / changed, 2) if changed else 0 for s in sum_d],
               max_delta_inside=max_in, changed_outside=outside if mask is not None else None,
               max_delta_outside=max_out, mask=bool(mask is not None), dilate=a.dilate,
               thresholds=dict(max_pct=a.max_pct, max_delta=a.max_delta, tol=a.tol),
               verdict='tier2' if not reasons else 'tier3', reasons=reasons)
    js = json.dumps(res, indent=1)
    if a.json:
        with open(a.json, 'w') as fh:
            fh.write(js + '\n')
    print(js)
    if heat is not None:
        write_png(a.heat, w, h, heat)
    return 0 if not reasons else 1


if __name__ == '__main__':
    sys.exit(main())
