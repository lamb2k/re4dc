#!/usr/bin/env python3
"""charbake texture I/O (D367 charbake, 2026-10-10). numpy + PIL (Windows Python).

Native packages (RE4DCTX v2, tools/convert_tpl.py layout), single texture:
  HEADER  <8s10I : magic, version, header_size, stride, count, texture_offset, data_offset, data_size, crc32(body),
                   1, 0   (convert_tpl.package_existing_vq writes these fields)
  TEXTURE <64s8I : name, width, height, format (0 RGB565, 1 ARGB1555, 2 ARGB4444), data_offset, data_size, flags,
                   payload (0 linear, 1 twiddled, 2 VQ), extra
Twiddle: convert_tpl.twiddle_16bpp (y bits even, x bits odd, square min-side blocks along the long side).
VQ: 2048-byte codebook (256 x 4 texels, each 2x2 block in twiddled order (0,0) (0,1) (1,0) (1,1) as (x, y)) then one
index byte per 2x2 block, the blocks twiddled over (w/2) x (h/2).
tex.pak: tools/d367/texpack.py layout (read here; written by texpack.build for a deterministic pack).

Private inputs and outputs: decoded / encoded textures are game assets; never commit them.
"""
from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

import numpy as np

MAGIC = b'RE4DCTX\0'
HEADER = struct.Struct('<8s10I')
TEXTURE = struct.Struct('<64s8I')
RGB565, ARGB1555, ARGB4444 = 0, 1, 2
LINEAR, TWIDDLED, VQ = 0, 1, 2


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- tex.pak
def pak_index(pak) -> dict:
    with open(pak, 'rb') as f:
        head = f.read(2048)
        if head[:8] != b'RE4PAK1\0':
            raise SystemExit('not a tex.pak: %s' % pak)
        _ver, count, index_off, _data_off, _crc = struct.unpack_from('<5I', head, 8)
        f.seek(index_off)
        index = f.read(count * 16)
    out = {}
    for i in range(count):
        c, n, off, size = struct.unpack_from('<4I', index, i * 16)
        out[(c, n)] = (off, size)
    return out


def pak_get(pak, key) -> bytes:
    idx = pak_index(pak)
    off, size = idx[key]
    with open(pak, 'rb') as f:
        f.seek(off)
        return f.read(size)


def parse_key(s: str):
    a, b = s.lower().split('-')
    return int(a, 16), int(b, 16)


def key_str(k) -> str:
    return '%08x-%08x' % k


# ---------------------------------------------------------------- twiddle
def _spread(v):
    v = v.astype(np.int64)
    r = np.zeros_like(v)
    for bit in range(11):
        r |= ((v >> bit) & 1) << (2 * bit)
    return r


def twiddle_index(width: int, height: int) -> np.ndarray:
    """twiddled[i] position of linear texel (y, x): array [h, w] of twiddled offsets (convert_tpl.twiddle_16bpp)."""
    m = min(width, height)
    y = np.arange(height)[:, None]
    x = np.arange(width)[None, :]
    return (_spread(y & (m - 1)) | (_spread(x & (m - 1)) << 1)) + (x // m) * m * m + (y // m) * m * m


# ---------------------------------------------------------------- 16-bit texels
def expand16(v: np.ndarray, fmt: int) -> np.ndarray:
    v = v.astype(np.uint32)
    if fmt == RGB565:
        r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
        rgba = np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), np.full_like(v, 255)], -1)
    elif fmt == ARGB1555:
        r, g, b = (v >> 10) & 31, (v >> 5) & 31, v & 31
        rgba = np.stack([(r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2), np.where(v & 0x8000, 255, 0)], -1)
    else:
        rgba = np.stack([((v >> 8) & 15) * 17, ((v >> 4) & 15) * 17, (v & 15) * 17, (v >> 12) * 17], -1)
    return rgba.astype(np.uint8)


def pack565(rgb: np.ndarray) -> np.ndarray:
    """uint8 [..., 3] -> uint16 RGB565 by truncation (convert_tpl._pack_565)."""
    r, g, b = (rgb[..., 0].astype(np.uint16) >> 3), (rgb[..., 1].astype(np.uint16) >> 2), (rgb[..., 2].astype(np.uint16) >> 3)
    return (r << 11) | (g << 5) | b


def quant565(rgbf: np.ndarray, dither: str = 'none') -> np.ndarray:
    """float RGB 0..255 [h, w, 3] -> uint16 RGB565. dither: 'none' (round to nearest 565 level), 'trunc' (convert_tpl's
    truncation), 'bayer' (4x4 ordered, +-half a step), 'fs' (Floyd-Steinberg, serpentine, deterministic)."""
    h, w, _ = rgbf.shape
    levels = np.array([31.0, 63.0, 31.0])
    if dither == 'trunc':
        return pack565(np.clip(rgbf, 0, 255).astype(np.uint8))
    x = np.clip(rgbf, 0, 255) / 255.0 * levels
    if dither == 'none':
        q = np.floor(x + 0.5)
    elif dither == 'bayer':
        b4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float64) / 16.0 - 15.0 / 32.0
        t = np.tile(b4, (h // 4 + 1, w // 4 + 1))[:h, :w]
        q = np.floor(x + 0.5 + t[..., None])
    elif dither == 'fs':
        x = x.copy()
        q = np.zeros_like(x)
        for yy in range(h):
            rng = range(w) if yy % 2 == 0 else range(w - 1, -1, -1)
            s = 1 if yy % 2 == 0 else -1
            for xx in rng:
                old = x[yy, xx]
                new = np.clip(np.floor(old + 0.5), 0, levels)
                q[yy, xx] = new
                e = old - new
                if 0 <= xx + s < w:
                    x[yy, xx + s] += e * (7 / 16)
                if yy + 1 < h:
                    if 0 <= xx - s < w:
                        x[yy + 1, xx - s] += e * (3 / 16)
                    x[yy + 1, xx] += e * (5 / 16)
                    if 0 <= xx + s < w:
                        x[yy + 1, xx + s] += e * (1 / 16)
    else:
        raise ValueError(dither)
    q = np.clip(q, 0, levels).astype(np.uint16)
    return (q[..., 0] << 11) | (q[..., 1] << 5) | q[..., 2]


# ---------------------------------------------------------------- packages
def read_package(blob: bytes) -> dict:
    h = HEADER.unpack_from(blob)
    if h[0] != MAGIC or h[1] != 2 or h[4] != 1 or h[3] != TEXTURE.size:
        raise ValueError('expected a single-texture RE4DCTX v2 package')
    name, width, height, fmt, doff, dsize, flags, payload, extra = TEXTURE.unpack_from(blob, h[5])
    return dict(header=h, name=name.rstrip(b'\0').decode(errors='replace'), width=width, height=height, format=fmt,
                data_offset=doff, data_size=dsize, flags=flags, payload=payload, extra=extra, texture_offset=h[5])


def decode(blob: bytes) -> tuple[dict, np.ndarray]:
    """-> (info, RGBA uint8 [h, w, 4]) for twiddled 16-bit or VQ payloads."""
    p = read_package(blob)
    w, h, fmt = p['width'], p['height'], p['format']
    data = blob[p['data_offset']:p['data_offset'] + p['data_size']]
    if p['payload'] == TWIDDLED:
        tex = np.frombuffer(data, '<u2', w * h)
        lin = tex[twiddle_index(w, h)]
        return p, expand16(lin, fmt)
    if p['payload'] == VQ:
        book = np.frombuffer(data, '<u2', 1024).reshape(256, 4)
        idx = np.frombuffer(data, np.uint8, (w // 2) * (h // 2), 2048)
        bi = idx[twiddle_index(w // 2, h // 2)]          # [h/2, w/2] codebook entries
        texels = book[bi]                                  # [h/2, w/2, 4]; order (0,0) (0,1) (1,0) (1,1) as (x, y)
        out = np.zeros((h, w), np.uint16)
        out[0::2, 0::2] = texels[..., 0]
        out[1::2, 0::2] = texels[..., 1]
        out[0::2, 1::2] = texels[..., 2]
        out[1::2, 1::2] = texels[..., 3]
        return p, expand16(out, fmt)
    raise ValueError('payload %d not handled' % p['payload'])


def _finish(blob: bytearray, p: dict) -> bytes:
    """Recompute the header crc32 over the body (descriptor + payload) as convert_tpl writes it."""
    h = list(HEADER.unpack_from(blob))
    body = bytes(blob[h[5]:])
    h[8] = zlib.crc32(body) & 0xffffffff
    HEADER.pack_into(blob, 0, *h)
    return bytes(blob)


def replace_texels16(blob: bytes, tex16: np.ndarray) -> bytes:
    """The same twiddled 16-bit package (name, size, format, flags) with new texels (uint16 [h, w], row-major)."""
    p = read_package(blob)
    if p['payload'] != TWIDDLED:
        raise ValueError('replace_texels16 needs a twiddled package')
    w, h = p['width'], p['height']
    if tex16.shape != (h, w):
        raise ValueError('size mismatch')
    tw = np.zeros(w * h, '<u2')
    tw[twiddle_index(w, h).ravel()] = tex16.ravel()
    out = bytearray(blob)
    out[p['data_offset']:p['data_offset'] + w * h * 2] = tw.tobytes()
    return _finish(out, p)


def package_twiddled16(name: str, tex16: np.ndarray, fmt: int = RGB565, flags: int = 0) -> bytes:
    """A new single-texture twiddled 16-bit package (convert_tpl.build_package layout for one material)."""
    h, w = tex16.shape
    tw = np.zeros(w * h, '<u2')
    tw[twiddle_index(w, h).ravel()] = tex16.ravel()
    payload = tw.tobytes()
    start = HEADER.size + TEXTURE.size
    desc = TEXTURE.pack(name.encode().ljust(64, b'\0'), w, h, fmt, start, len(payload), flags, TWIDDLED, 0)
    body = desc + payload
    head = HEADER.pack(MAGIC, 2, HEADER.size, TEXTURE.size, 1, HEADER.size, start, len(payload),
                       zlib.crc32(body) & 0xffffffff, 1, 0)
    return head + body


def package_vq(name: str, book: np.ndarray, blocks: np.ndarray, fmt: int = RGB565, flags: int = 0) -> bytes:
    """A VQ package from a codebook uint16 [256, 4] (texel order (0,0) (0,1) (1,0) (1,1) as (x, y)) and block indices
    uint8 [h/2, w/2] (row-major); the indices are twiddled here."""
    hh, ww = blocks.shape
    tw = np.zeros(hh * ww, np.uint8)
    tw[twiddle_index(ww, hh).ravel()] = blocks.ravel()
    payload = book.astype('<u2').tobytes() + tw.tobytes()
    start = HEADER.size + TEXTURE.size
    desc = TEXTURE.pack(name.encode().ljust(64, b'\0'), ww * 2, hh * 2, fmt, start, len(payload), flags, VQ, 0)
    body = desc + payload
    head = HEADER.pack(MAGIC, 2, HEADER.size, TEXTURE.size, 1, HEADER.size, start, len(payload),
                       zlib.crc32(body) & 0xffffffff, 1, 0)
    return head + body


def vq_blocks_from_texels(tex16: np.ndarray) -> np.ndarray:
    """uint16 [h, w] -> [h/2, w/2, 4] block texels in codebook order."""
    return np.stack([tex16[0::2, 0::2], tex16[1::2, 0::2], tex16[0::2, 1::2], tex16[1::2, 1::2]], -1)


# ---------------------------------------------------------------- texpack (deterministic, texpack.py layout)
def build_pak(pkgs: dict) -> bytes:
    keys = sorted(pkgs)
    count = len(keys)
    index_bytes = (count * 16 + 2047) // 2048 * 2048
    data_offset = 2048 + index_bytes
    index, data, off = bytearray(), bytearray(), data_offset
    for k in keys:
        b = pkgs[k]
        if b[:8] != MAGIC:
            raise SystemExit('not a texture package: %08x-%08x' % k)
        index += struct.pack('<4I', k[0], k[1], off, len(b))
        pad = (-len(b)) % 2048
        data += b + bytes(pad)
        off += len(b) + pad
    index += bytes(index_bytes - len(index))
    head = b'RE4PAK1\0' + struct.pack('<5I', 1, count, 2048, data_offset, zlib.crc32(bytes(index)))
    head += bytes(2048 - len(head))
    return bytes(head) + bytes(index) + bytes(data)


def pak_with(pak, changes: dict) -> bytes:
    """A copy of a tex.pak with packages replaced or added ({key: package bytes or None to remove})."""
    idx = pak_index(pak)
    pkgs = {}
    with open(pak, 'rb') as f:
        for k, (off, size) in idx.items():
            f.seek(off)
            pkgs[k] = f.read(size)
    for k, v in changes.items():
        if v is None:
            pkgs.pop(k, None)
        else:
            pkgs[k] = v
    return build_pak(pkgs)


def save_png(path, rgba: np.ndarray):
    from PIL import Image
    Image.fromarray(rgba).save(path)


def load_rgba(path) -> np.ndarray:
    from PIL import Image
    return np.asarray(Image.open(path).convert('RGBA'))
