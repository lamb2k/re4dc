"""Existing RE4DCTX first-texture decoder used to verify generated textures."""
import struct
from pathlib import Path
import numpy as np
HEADER = struct.Struct('<8s10I')
TEXTURE = struct.Struct('<64s8I')

def untwiddle_index(w, h):
    """index map: linear (y*w+x) -> twiddled offset (square tiles of min(w,h))."""
    m = min(w, h)
    def spread(v):
        r = np.zeros_like(v)
        for b in range(10):
            r |= (v & (1 << b)) << b
        return r
    y, x = np.mgrid[0:h, 0:w]
    return (spread(y & (m - 1)) | (spread(x & (m - 1)) << 1)) + (x // m) * m * m + (y // m) * m * m

def px16(t, fmt):
    t = t.astype(np.uint32)
    if fmt == 0:  # RGB565
        r, g, b = (t >> 11) & 31, (t >> 5) & 63, t & 31
        return np.stack([r * 255 // 31, g * 255 // 63, b * 255 // 31, np.full_like(r, 255)], -1)
    if fmt == 1:  # ARGB1555
        a, r, g, b = (t >> 15) & 1, (t >> 10) & 31, (t >> 5) & 31, t & 31
        return np.stack([r * 255 // 31, g * 255 // 31, b * 255 // 31, a * 255], -1)
    a, r, g, b = (t >> 12) & 15, (t >> 8) & 15, (t >> 4) & 15, t & 15  # ARGB4444
    return np.stack([r * 17, g * 17, b * 17, a * 17], -1)

def decode(path):
    b = Path(path).read_bytes()
    magic, ver, hsize, tsize, count, toff, doff, dlen, crc, nimg, _ = HEADER.unpack_from(b, 0)
    name, w, h, fmt, off, size, flags, payload, _ = TEXTURE.unpack_from(b, toff)
    raw = b[off:off + size]
    if payload == 2:  # VQ: 2048-byte codebook (256 x 2x2 texels) + twiddled indices of 2x2 blocks
        cb = np.frombuffer(raw[:2048], dtype="<u2").reshape(256, 4)
        idx = np.frombuffer(raw[2048:2048 + (w // 2) * (h // 2)], dtype=np.uint8)
        tw = untwiddle_index(w // 2, h // 2)
        blocks = cb[idx[tw]]  # (h/2, w/2, 4) texels in twiddled order 0:(0,0) 1:(0,1)y 2:(1,0) 3:(1,1)
        t = np.zeros((h, w), dtype=np.uint16)
        t[0::2, 0::2] = blocks[..., 0]; t[1::2, 0::2] = blocks[..., 1]
        t[0::2, 1::2] = blocks[..., 2]; t[1::2, 1::2] = blocks[..., 3]
    else:
        t = np.frombuffer(raw, dtype="<u2")[:w * h]
        if payload == 1:
            t = t[untwiddle_index(w, h)]
        t = t.reshape(h, w)
    return px16(t, fmt).astype(np.uint8), dict(w=w, h=h, fmt=fmt, payload=payload, flags=flags)
