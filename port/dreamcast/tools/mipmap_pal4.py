"""Opt-in mips for existing compact twiddled PAL4 ARGB4444 packages.

Palette/base indices/UV dimensions stay exact. No 16-bit expansion on disc or
in VRAM. Runtime admission requires TEX_PAL4_MIPMAP=1, TEX_PAL4_ALPHA=1 and
CAST_MIPMAP=1. Rectangles and palette VQ need separate layout contracts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

import convert_tpl as tpl
from mipmap_vq import _feature, _halve, _nearest, rgba


def chain_bytes(side):
    return (side * side * 4 // 3 + 3) // 2


def level_offset(side):
    # KOS pvrtex MipMapOffset(PAL4, uncompressed, level), in bytes.
    return 1 if side == 1 else chain_bytes(side // 2)


@dataclass(frozen=True)
class NativePal4:
    header: tuple
    texture: tuple
    payload: bytes
    crc_rule: str

    @property
    def size(self):
        return self.texture[1]

    @property
    def mipmapped(self):
        return bool(self.texture[6] & tpl.FLAG_MIPMAP)

    @property
    def palette(self):
        return self.payload[-32:]

    @property
    def base_indices(self):
        offset = level_offset(self.size) if self.mipmapped else 0
        return self.payload[offset:offset + self.size * self.size // 2]


def read_native_pal4(blob):
    if len(blob) < 144:
        raise ValueError("short native palette package")
    h = tpl.HEADER.unpack_from(blob)
    if (h[:6] != (tpl.MAGIC, tpl.VERSION, 48, 96, 1, 48) or
            h[6] != 144 or h[6] + h[7] != len(blob)):
        raise ValueError("expected one canonical native palette descriptor")
    t = tpl.TEXTURE.unpack_from(blob, 48)
    _, w, height, fmt, offset, size, flags, layout, reserved = t
    if (not (8 <= w <= 1024 and w == height and w & (w - 1) == 0) or
            fmt != tpl.FORMAT_PAL4_ARGB4444 or layout != tpl.PAYLOAD_TWIDDLED or
            offset != 144 or reserved or flags & (1 << 30)):
        raise ValueError("palette mip generation needs square twiddled PAL4 ARGB4444")
    expected = (chain_bytes(w) if flags & tpl.FLAG_MIPMAP else w * w // 2) + 32
    if size != expected or h[7] != size:
        raise ValueError("native palette chain or palette tail length mismatch")
    if h[8] == zlib.crc32(blob[48:]) & 0xffffffff:
        rule = "header"
    elif h[8] == zlib.crc32(blob[144:]) & 0xffffffff:
        rule = "data"
    else:
        raise ValueError("unknown native palette CRC convention")
    return NativePal4(h, t, blob[144:], rule)


def palette_rgba(native):
    return [rgba(w, tpl.FORMAT_ARGB4444)
            for w in struct.unpack("<16H", native.palette)]


def decode_level(native, side):
    if side < 1 or side > native.size or side & (side - 1):
        raise ValueError("invalid palette mip level")
    if side != native.size and not native.mipmapped:
        raise ValueError("palette package has no smaller levels")
    palette = palette_rgba(native)
    offset = level_offset(side) if native.mipmapped else 0
    if side == 1:
        # Three leading padding nibbles: the fourth nibble is the 1x1 texel.
        return [palette[native.payload[1] >> 4]]
    packed = native.payload[offset:offset + side * side // 2]
    order = tpl.twiddle_16bpp(list(range(side * side)), side, side)
    out = [None] * (side * side)
    for at, linear in enumerate(order):
        index = (packed[at // 2] >> (4 * (at & 1))) & 15
        out[linear] = palette[index]
    return out


def _encode_level(pixels, side, palette, engine):
    order = tpl.twiddle_16bpp(list(range(side * side)), side, side) if side > 1 else [0]
    targets = [pixels[i] for i in order]
    unique = list(dict.fromkeys(targets))
    chosen, used = _nearest(unique, palette, engine)
    lookup = dict(zip(unique, chosen))
    indices = [lookup[t] for t in targets]
    if side == 1:
        # Replicate both nibbles: hardware's fourth nibble and old decoder
        # versions' low-nibble 1x1 preview agree.
        return bytes([indices[0] * 17]), used
    return bytes(indices[i] | indices[i + 1] << 4 for i in range(0, len(indices), 2)), used


def add_mipmaps(blob, *, enabled=False, engine="auto"):
    native = read_native_pal4(blob)
    evidence = dict(enabled=bool(enabled), changed=False, width=native.size,
        height=native.size, format=tpl.FORMAT_PAL4_ARGB4444, crc_rule=native.crc_rule,
        source_package_sha256=hashlib.sha256(blob).hexdigest(),
        palette_sha256=hashlib.sha256(native.palette).hexdigest(),
        base_indices_sha256=hashlib.sha256(native.base_indices).hexdigest(),
        before_payload_bytes=len(native.payload),
        required_build_knobs=["TEX_PAL4_MIPMAP=1", "TEX_PAL4_ALPHA=1", "CAST_MIPMAP=1"])
    if not enabled or native.mipmapped:
        evidence.update(reason="disabled" if not enabled else "already-mipmapped",
            after_payload_bytes=len(native.payload), extra_payload_bytes=0,
            package_sha256=evidence["source_package_sha256"],
            base_level_exact=True, palette_exact=True)
        result = tpl.canonical_native_crc(blob) if enabled else blob
        evidence.update(changed=result != blob,
                        package_sha256=hashlib.sha256(result).hexdigest(),
                        source_crc_rule=native.crc_rule,
                        output_crc_rule="header" if enabled else native.crc_rule,
                        crc_normalized=bool(enabled and result != blob))
        return result, evidence
    palette = [_feature(p) for p in palette_rgba(native)]
    pixels = [_feature(p) for p in decode_level(native, native.size)]
    side, engines = native.size, set()
    chain = bytearray(chain_bytes(side))
    chain[level_offset(side):] = native.base_indices
    while side > 1:
        pixels = _halve(pixels, side)
        side //= 2
        encoded, used = _encode_level(pixels, side, palette, engine)
        start = level_offset(side)
        chain[start:start + len(encoded)] = encoded
        engines.add(used)
    payload = bytes(chain) + native.palette
    h, t = list(native.header), list(native.texture)
    t[5], t[6], h[7] = len(payload), t[6] | tpl.FLAG_MIPMAP, len(payload)
    body = tpl.TEXTURE.pack(*t) + payload
    h[8] = zlib.crc32(body) & 0xffffffff
    result = tpl.HEADER.pack(*h) + body
    checked = read_native_pal4(result)
    if checked.base_indices != native.base_indices or checked.palette != native.palette:
        raise ValueError("palette mip generation changed original base or palette bytes")
    evidence.update(changed=True, after_payload_bytes=len(payload),
        extra_payload_bytes=len(payload) - len(native.payload),
        package_sha256=hashlib.sha256(result).hexdigest(), base_level_exact=True,
        palette_exact=True, engines=sorted(engines),
        levels=[dict(side=1 << i, offset=level_offset(1 << i))
                for i in range(native.size.bit_length())])
    return result, evidence
