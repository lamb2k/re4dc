"""Opt-in mip chains for square native 16-bit twiddled packages.

Full-resolution texel words, dimensions, material and flags stay exact.
Only lower levels are filtered and quantized in the original native format.
Runtime requires CAST_MIPMAP=1 and TEX_TWIDDLED_MIPMAP=1.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib

import convert_tpl as tpl
from mipmap_vq import _feature, _halve, rgba


def chain_bytes(side):
    return (side * side * 4 // 3 + 3) * 2


def level_offset(side):
    return 6 if side == 1 else chain_bytes(side // 2)


@dataclass(frozen=True)
class NativeTwiddled:
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
    def base_texels(self):
        start = level_offset(self.size) if self.mipmapped else 0
        return self.payload[start:start + self.size * self.size * 2]


def read_native_twiddled(blob):
    if len(blob) < 144:
        raise ValueError("short native twiddled package")
    h = tpl.HEADER.unpack_from(blob)
    if (h[:6] != (tpl.MAGIC, tpl.VERSION, 48, 96, 1, 48) or
            h[6] != 144 or h[6] + h[7] != len(blob)):
        raise ValueError("expected one canonical native twiddled descriptor")
    t = tpl.TEXTURE.unpack_from(blob, 48)
    _, w, height, fmt, offset, size, flags, layout, reserved = t
    if (not (8 <= w <= 1024 and w == height and w & (w - 1) == 0) or
            fmt not in (tpl.FORMAT_RGB565, tpl.FORMAT_ARGB1555, tpl.FORMAT_ARGB4444) or
            layout != tpl.PAYLOAD_TWIDDLED or offset != 144 or reserved or flags & (1 << 30)):
        raise ValueError("native mip generation needs square 16-bit twiddled texels")
    expected = chain_bytes(w) if flags & tpl.FLAG_MIPMAP else w * w * 2
    if size != expected or h[7] != size:
        raise ValueError("native twiddled chain length mismatch")
    if h[8] == zlib.crc32(blob[48:]) & 0xffffffff:
        rule = "header"
    elif h[8] == zlib.crc32(blob[144:]) & 0xffffffff:
        rule = "data"
    else:
        raise ValueError("unknown native twiddled CRC convention")
    return NativeTwiddled(h, t, blob[144:], rule)


def decode_level(native, side):
    if side < 1 or side > native.size or side & (side - 1):
        raise ValueError("invalid native twiddled mip level")
    if side != native.size and not native.mipmapped:
        raise ValueError("native twiddled package has no smaller levels")
    start = level_offset(side) if native.mipmapped else 0
    words = struct.unpack_from("<%dH" % (side * side), native.payload, start)
    order = tpl.twiddle_16bpp(list(range(side * side)), side, side) if side > 1 else [0]
    out = [None] * (side * side)
    for at, linear in enumerate(order):
        out[linear] = rgba(words[at], native.texture[3])
    return out


def _straight(feature):
    alpha_feature = feature[3]
    if not alpha_feature:
        return 0, 0, 0, 0
    color = tuple(min(255, (c * 255 + alpha_feature // 2) // alpha_feature)
                  for c in feature[:3])
    return color + (min(255, (alpha_feature + 127) // 255),)


def _encode_level(pixels, side, fmt):
    pack = {tpl.FORMAT_RGB565: tpl._pack_565,
            tpl.FORMAT_ARGB1555: tpl._pack_1555,
            tpl.FORMAT_ARGB4444: tpl._pack_4444}[fmt]
    words = [pack(_straight(p)) for p in pixels]
    if side > 1:
        words = tpl.twiddle_16bpp(words, side, side)
    return struct.pack("<%dH" % len(words), *words)


def add_mipmaps(blob, *, enabled=False, engine="auto"):
    native = read_native_twiddled(blob)
    evidence = dict(enabled=bool(enabled), changed=False, width=native.size,
        height=native.size, format=native.texture[3], crc_rule=native.crc_rule,
        source_package_sha256=hashlib.sha256(blob).hexdigest(),
        base_texels_sha256=hashlib.sha256(native.base_texels).hexdigest(),
        before_payload_bytes=len(native.payload),
        required_build_knobs=["TEX_TWIDDLED_MIPMAP=1", "CAST_MIPMAP=1"])
    if not enabled or native.mipmapped:
        evidence.update(reason="disabled" if not enabled else "already-mipmapped",
            after_payload_bytes=len(native.payload), extra_payload_bytes=0,
            package_sha256=evidence["source_package_sha256"], base_level_exact=True)
        result = tpl.canonical_native_crc(blob) if enabled else blob
        evidence.update(changed=result != blob,
                        package_sha256=hashlib.sha256(result).hexdigest(),
                        source_crc_rule=native.crc_rule,
                        output_crc_rule="header" if enabled else native.crc_rule,
                        crc_normalized=bool(enabled and result != blob))
        return result, evidence
    pixels = [_feature(p) for p in decode_level(native, native.size)]
    side = native.size
    chain = bytearray(chain_bytes(side))
    chain[level_offset(side):] = native.base_texels
    while side > 1:
        pixels = _halve(pixels, side)
        side //= 2
        encoded = _encode_level(pixels, side, native.texture[3])
        at = level_offset(side)
        chain[at:at + len(encoded)] = encoded
    h, t = list(native.header), list(native.texture)
    t[5], t[6], h[7] = len(chain), t[6] | tpl.FLAG_MIPMAP, len(chain)
    body = tpl.TEXTURE.pack(*t) + chain
    h[8] = zlib.crc32(body) & 0xffffffff
    result = tpl.HEADER.pack(*h) + body
    checked = read_native_twiddled(result)
    if checked.base_texels != native.base_texels:
        raise ValueError("native twiddled mips changed original full-resolution words")
    evidence.update(changed=True, after_payload_bytes=len(chain),
        extra_payload_bytes=len(chain) - len(native.payload),
        package_sha256=hashlib.sha256(result).hexdigest(), base_level_exact=True,
        engines=["integer-native"],
        levels=[dict(side=1 << i, offset=level_offset(1 << i))
                for i in range(native.size.bit_length())])
    return result, evidence
