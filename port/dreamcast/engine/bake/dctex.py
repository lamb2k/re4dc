"""Decode Dreamcast texture packages (RE4DCTX: VQ or plain twiddled; ARGB1555 / RGB565 / ARGB4444; PAL4 with a
palette tail) to RGBA arrays, and encode RGBA back to a twiddled ARGB4444 package. Bake helper (eng-e0b)."""
import struct, zlib
import numpy as np
def untwiddle_index(w, h):
    """index[y, x] -> twiddled position, for a w x h (powers of two) image"""
    n = min(w, h); ys, xs = np.mgrid[0:h, 0:w]
    def inter(v, bits):
        r = np.zeros_like(v)
        for b in range(bits): r |= ((v >> b) & 1) << (2 * b)
        return r
    bits = n.bit_length() - 1
    # square blocks of n x n, blocks laid out linearly along the longer axis
    sub = (inter(ys % n, bits) | (inter(xs % n, bits) << 1))
    block = (ys // n) * (w // n) + (xs // n)
    return block * n * n + sub
def to_rgba(px, fmt):
    px = px.astype(np.uint32)
    if fmt == 1:   # RGB565 (package fmt 0)
        r = (px >> 11) & 31; g = (px >> 5) & 63; b = px & 31
        return np.stack([r * 255 // 31, g * 255 // 63, b * 255 // 31, np.full_like(r, 255)], -1).astype(np.uint8)
    if fmt == 0:   # ARGB1555
        a = (px >> 15) & 1; r = (px >> 10) & 31; g = (px >> 5) & 31; b = px & 31
        return np.stack([r * 255 // 31, g * 255 // 31, b * 255 // 31, a * 255], -1).astype(np.uint8)
    a = (px >> 12) & 15; r = (px >> 8) & 15; g = (px >> 4) & 15; b = px & 15   # ARGB4444
    return np.stack([r * 17, g * 17, b * 17, a * 17], -1).astype(np.uint8)
PVRFMT = (1, 0, 2, 5, 5, 6)
def decode(pkg):
    at = struct.unpack_from('<I', pkg, 24)[0]
    w, h, fmt, data_at, n, flags, payload, _ = struct.unpack_from('<8I', pkg, at + 64)
    data = pkg[data_at:data_at + n]; pf = PVRFMT[fmt]
    if payload == 2:   # VQ: 256-entry codebook of 2x2 texels, then one index per 2x2 block (twiddled)
        cb = np.frombuffer(data[:2048], dtype='<u2').reshape(256, 4)
        bw, bh = w // 2, h // 2; nidx = bw * bh
        idx = np.frombuffer(data[len(data) - nidx:], dtype=np.uint8)   # top level last (mip levels precede)
        tw = untwiddle_index(bw, bh)
        blocks = cb[idx[tw]]                       # bh x bw x 4 (twiddled 2x2: (0,0) (0,1) (1,0) (1,1) as y,x)
        img = np.zeros((h, w), np.uint16)
        img[0::2, 0::2] = blocks[..., 0]; img[1::2, 0::2] = blocks[..., 1]; img[0::2, 1::2] = blocks[..., 2]; img[1::2, 1::2] = blocks[..., 3]
        return to_rgba(img, pf)
    if pf == 5:   # PAL4: twiddled 4-bit indices (low nibble first), then a 16-colour palette (ARGB8888 when flags & 8)
        tail = 64 if flags & 8 else 32; pal = data[len(data) - tail:]; ix = np.frombuffer(data[:len(data) - tail], dtype=np.uint8)
        ix = ix[len(ix) - w * h // 2:]
        nib = np.empty(w * h, np.uint8); nib[0::2] = ix & 15; nib[1::2] = ix >> 4
        if tail == 64:
            c = np.frombuffer(pal, dtype='<u4'); lut = np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24], -1).astype(np.uint8)
        else:
            c = np.frombuffer(pal, dtype='<u2').astype(np.uint32)
            lut = np.stack([(c >> 8 & 15) * 17, (c >> 4 & 15) * 17, (c & 15) * 17, (c >> 12) * 17], -1).astype(np.uint8)
        return lut[nib[untwiddle_index(w, h)]]
    if pf in (0, 1, 2):
        px = np.frombuffer(data[len(data) - 2 * w * h:], dtype='<u2')
        return to_rgba(px[untwiddle_index(w, h)], pf)
    raise ValueError(f'format {fmt} payload {payload}')
def encode_4444(rgba, name=b'composite'):
    """Twiddled ARGB4444 package (no VQ, no mip maps), same header layout as the bake's packages."""
    h, w = rgba.shape[:2]
    q = (rgba.astype(np.uint32) + 8) // 17
    px = ((q[..., 3] << 12) | (q[..., 0] << 8) | (q[..., 1] << 4) | q[..., 2]).astype('<u2')
    tw = untwiddle_index(w, h); out = np.zeros(w * h, '<u2'); out[tw.ravel()] = px.ravel()
    data = out.tobytes(); n = len(data)
    desc = name.ljust(64, b'\0')[:64] + struct.pack('<8I', w, h, 2, 144, n, 0, 0, 0)
    return struct.pack('<8s10I', b'RE4DCTX', 2, 48, 96, 1, 48, 144, n, zlib.crc32(data), 1, 0) + desc + data
