"""Opt-in mip chains for native square 16-bit full-codebook VQ packages.

The existing codebook and largest-level index plane remain byte-identical.
Only lower levels are generated. Native format/UVs, material/source identity,
alpha flags are preserved. Legacy CRC inputs are accepted; enabled output uses
the runtime CRC over descriptors and payload. No runtime changes.

PVR layout authority: pinned KOS utils/pvrtex pvr_texture.c MipMapOffset and
pvr_texture_decoder.c. Indices are Morton ordered; a codebook vector is
TL, BL, TR, BR. The 1x1 level samples BR, at byte 6 of its expanded vector.
"""
from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass

import convert_tpl as tpl


@dataclass(frozen=True)
class NativeVq:
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
    def codebook(self):
        return self.payload[:2048]

    @property
    def base_indices(self):
        return self.payload[-self.size * self.size // 4:]


def read_native_vq(blob: bytes) -> NativeVq:
    if len(blob) < tpl.HEADER.size + tpl.TEXTURE.size:
        raise ValueError("native package is shorter than its descriptors")
    h = tpl.HEADER.unpack_from(blob)
    if (h[0] != tpl.MAGIC or h[1] != tpl.VERSION or
            h[2:6] != (tpl.HEADER.size, tpl.TEXTURE.size, 1, tpl.HEADER.size)):
        raise ValueError("expected one standard native texture descriptor")
    t = tpl.TEXTURE.unpack_from(blob, h[5])
    _, w, height, fmt, off, size, flags, payload, reserved = t
    dimensions = 8 <= w <= 1024 and w == height and w & (w - 1) == 0
    if (not dimensions or fmt not in (tpl.FORMAT_RGB565,
            tpl.FORMAT_ARGB1555, tpl.FORMAT_ARGB4444) or
            payload != tpl.PAYLOAD_VQ or reserved or flags & (1 << 30)):
        raise ValueError("mip generation needs square 16-bit full-codebook VQ")
    if off != tpl.HEADER.size + tpl.TEXTURE.size or h[6] != off:
        raise ValueError("unsupported native descriptor or payload offset")
    indices = tpl.vq_mip_index_bytes(w) if flags & tpl.FLAG_MIPMAP else w * w // 4
    if size != 2048 + indices or h[7] != size or len(blob) != off + size:
        raise ValueError("native VQ payload length or full codebook mismatch")
    if h[8] == zlib.crc32(blob[h[2]:]) & 0xffffffff:
        rule = "header"
    elif h[8] == zlib.crc32(blob[off:]) & 0xffffffff:
        # Existing vram/vq_pak.restamp preserves this legacy convention too.
        rule = "data"
    else:
        raise ValueError("unknown source package CRC convention")
    return NativeVq(h, t, blob[off:], rule)


def rgba(word, fmt):
    if fmt == tpl.FORMAT_RGB565:
        return (*tpl._expand_565(word), 255)
    if fmt == tpl.FORMAT_ARGB1555:
        r, g, b = (word >> 10) & 31, (word >> 5) & 31, word & 31
        return ((r << 3) | (r >> 2), (g << 3) | (g >> 2),
                (b << 3) | (b >> 2), 255 if word & 0x8000 else 0)
    if fmt == tpl.FORMAT_ARGB4444:
        return (((word >> 8) & 15) * 17, ((word >> 4) & 15) * 17,
                (word & 15) * 17, ((word >> 12) & 15) * 17)
    raise ValueError("not a supported 16-bit pixel format")


def codebook_rgba(native: NativeVq):
    words = struct.unpack("<1024H", native.codebook)
    fmt = native.texture[3]
    return [tuple(rgba(w, fmt) for w in words[i:i + 4])
            for i in range(0, 1024, 4)]


def decode_level(native: NativeVq, side: int):
    if side < 1 or side > native.size or side & (side - 1):
        raise ValueError("invalid requested mip level")
    if side != native.size and not native.mipmapped:
        raise ValueError("package has no lower levels")
    book = codebook_rgba(native)
    if side == 1:
        return [book[native.payload[2048]][3]]
    offset = tpl.vq_mip_index_bytes(side // 2) if native.mipmapped else 0
    indices = native.payload[2048 + offset:2048 + offset + side * side // 4]
    blocks = side // 2
    order = tpl.twiddle_16bpp(list(range(blocks * blocks)), blocks, blocks)
    pixels = [None] * (side * side)
    for at, linear in enumerate(order):
        x, y = (linear % blocks) * 2, (linear // blocks) * 2
        q = book[indices[at]]
        pixels[y * side + x], pixels[(y + 1) * side + x] = q[0], q[1]
        pixels[y * side + x + 1], pixels[(y + 1) * side + x + 1] = q[2], q[3]
    return pixels


def _feature(pixel):
    r, g, b, a = pixel
    # Integer premultiplied colour prevents hidden transparent RGB bleeding.
    return r * a, g * a, b * a, a * 255


def _halve(pixels, side):
    out = []
    for y in range(0, side, 2):
        for x in range(0, side, 2):
            q = [pixels[y * side + x], pixels[y * side + x + 1],
                 pixels[(y + 1) * side + x], pixels[(y + 1) * side + x + 1]]
            out.append(tuple((sum(p[c] for p in q) + 2) // 4 for c in range(4)))
    return out


def _nearest_python(targets, book):
    result = []
    for target in targets:
        best, error = 0, None
        for at, vector in enumerate(book):
            total = 0
            for a, b in zip(target, vector):
                total += (a - b) ** 2
                if error is not None and total >= error:
                    break
            if error is None or total < error:
                best, error = at, total
        result.append(best)
    return result


def _nearest(targets, book, engine):
    if engine not in ("auto", "python", "numpy"):
        raise ValueError("engine must be auto, python or numpy")
    if engine != "python":
        try:
            import numpy as np
        except ImportError:
            if engine == "numpy":
                raise ValueError("numpy engine requested, but numpy is unavailable") from None
        else:
            # Exact int64 arithmetic; auto/python have the same lowest-index tie rule.
            # 16 * 65025^2 is safely below the int64 range.
            b = np.asarray(book, dtype=np.int64)
            out = []
            for first in range(0, len(targets), 128):
                t = np.asarray(targets[first:first + 128], dtype=np.int64)
                delta = t[:, None, :] - b[None, :, :]
                errors = (delta * delta).sum(axis=2)
                out.extend(errors.argmin(axis=1).tolist())
            return out, "numpy"
    return _nearest_python(targets, book), "python"


def _encode_level(pixels, side, book, engine):
    if side == 1:
        # The hardware's first expanded vector has six pad bytes before 1x1.
        targets = [pixels[0]]
        vectors = [b[12:16] for b in book]
    else:
        targets = []
        blocks = side // 2
        order = tpl.twiddle_16bpp(list(range(blocks * blocks)), blocks, blocks)
        for linear in order:
            x, y = (linear % blocks) * 2, (linear // blocks) * 2
            targets.append(pixels[y * side + x] + pixels[(y + 1) * side + x] +
                           pixels[y * side + x + 1] + pixels[(y + 1) * side + x + 1])
        vectors = book
    # A texture often repeats blocks. Search each distinct block only once.
    unique = list(dict.fromkeys(targets))
    indices, chosen_engine = _nearest(unique, vectors, engine)
    lookup = dict(zip(unique, indices))
    return bytes(lookup[t] for t in targets), chosen_engine


def add_mipmaps(blob: bytes, *, enabled=False, engine="auto"):
    """Return (package, evidence). Disabled mode always returns the original bytes."""
    native = read_native_vq(blob)
    evidence = dict(enabled=bool(enabled), changed=False, width=native.size,
                    height=native.size, format=native.texture[3],
                    crc_rule=native.crc_rule, before_payload_bytes=len(native.payload),
                    source_package_sha256=hashlib.sha256(blob).hexdigest(),
                    codebook_sha256=hashlib.sha256(native.codebook).hexdigest(),
                    base_indices_sha256=hashlib.sha256(native.base_indices).hexdigest())
    if not enabled or native.mipmapped:
        evidence.update(reason="disabled" if not enabled else "already-mipmapped",
                        after_payload_bytes=len(native.payload), extra_payload_bytes=0,
                        package_sha256=evidence["source_package_sha256"],
                        base_level_exact=True, codebook_exact=True)
        result = tpl.canonical_native_crc(blob) if enabled else blob
        evidence.update(changed=result != blob,
                        package_sha256=hashlib.sha256(result).hexdigest(),
                        source_crc_rule=native.crc_rule,
                        output_crc_rule="header" if enabled else native.crc_rule,
                        crc_normalized=bool(enabled and result != blob))
        return result, evidence
    book = [tuple(c for pixel in vector for c in _feature(pixel))
            for vector in codebook_rgba(native)]
    pixels = [_feature(p) for p in decode_level(native, native.size)]
    side = native.size
    levels = {side: native.base_indices}
    engines = set()
    while side > 1:
        pixels = _halve(pixels, side)
        side //= 2
        levels[side], used = _encode_level(pixels, side, book, engine)
        engines.add(used)
    payload = native.codebook + b"".join(levels[1 << i]
                for i in range(native.size.bit_length()))
    assert len(payload) == 2048 + tpl.vq_mip_index_bytes(native.size)
    h, t = list(native.header), list(native.texture)
    t[5], t[6] = len(payload), t[6] | tpl.FLAG_MIPMAP
    h[7] = len(payload)
    body = tpl.TEXTURE.pack(*t) + payload
    h[8] = zlib.crc32(body) & 0xffffffff
    result = tpl.HEADER.pack(*h) + body
    checked = read_native_vq(result)
    if checked.codebook != native.codebook or checked.base_indices != native.base_indices:
        raise ValueError("mip generation changed the original full-resolution bytes")
    evidence.update(changed=True, after_payload_bytes=len(payload),
                    extra_payload_bytes=len(payload) - len(native.payload),
                    package_sha256=hashlib.sha256(result).hexdigest(),
                    base_level_exact=True, codebook_exact=True,
                    engines=sorted(engines), smallest_level_samples_codebook_texel=3,
                    levels=[dict(side=s, index_bytes=len(levels[s])) for s in sorted(levels)])
    return result, evidence
