"""Opt-in, lossless native16-bit VQ when its complete payload is smaller.

The input is an existing square twiddled 16-bit or compact PAL4 package.
Dictionary coding succeeds only when every 2x2 vector fits the PVR's 256-entry codebook.
There is no quantization, resampling, new alpha decision or dimension change.
An existing mip chain is preserved rather than silently stripped/rebuilt.
"""
from __future__ import annotations

import hashlib
import struct
import zlib

import convert_tpl as tpl
import mipmap_pal4 as pal4
import mipmap_twiddled as twiddled
import mipmap_vq as vq


def rounded32(n):
    return (n + 31) // 32 * 32


def compact(blob, *, enabled=False):
    if len(blob) < 144:
        raise ValueError("short native package")
    texture = tpl.TEXTURE.unpack_from(blob, 48)
    if texture[7] == tpl.PAYLOAD_VQ:
        native = vq.read_native_vq(blob)
        reader, fmt = vq, native.texture[3]
    elif texture[3] == tpl.FORMAT_PAL4_ARGB4444:
        native = pal4.read_native_pal4(blob)
        reader, fmt = pal4, tpl.FORMAT_ARGB4444
    else:
        native = twiddled.read_native_twiddled(blob)
        reader, fmt = twiddled, native.texture[3]
    report = dict(enabled=bool(enabled), changed=False, width=native.size,
        height=native.size, source_format=native.texture[3], target_format=fmt,
        source_layout=native.texture[7], crc_rule=native.crc_rule,
        source_package_sha256=hashlib.sha256(blob).hexdigest(),
        before_payload_bytes=len(native.payload),
        before_alloc32_bytes=rounded32(len(native.payload)),
        exact_base_rgba=True, exact_alpha=True, exact_dimensions=True,
        exact_material=True, exact_header_flags=True, runtime_changes=False)

    def unchanged(reason):
        report.update(reason=reason, after_payload_bytes=len(native.payload),
            after_alloc32_bytes=rounded32(len(native.payload)), saved_payload_bytes=0,
            saved_alloc32_bytes=0, package_sha256=report["source_package_sha256"])
        return blob, report

    if native.texture[7] == tpl.PAYLOAD_VQ:
        return unchanged("already-vq")
    if native.mipmapped:
        return unchanged("existing-mip-chain-preserved")
    # In Morton texel order every four adjacent words form TL,BL,TR,BR;
    # the resulting vector indices are already in Morton block order.
    if reader is pal4:
        palette = struct.unpack("<16H", native.palette)
        words = [palette[(b >> shift) & 15]
                 for b in native.base_indices for shift in (0, 4)]
    else:
        words = struct.unpack("<%dH" % (native.size * native.size), native.base_texels)
    book, indices, seen = [], bytearray(), {}
    for at in range(0, len(words), 4):
        vector = tuple(words[at:at + 4])
        index = seen.get(vector)
        if index is None:
            index = len(book)
            if index == 256:
                report["distinct_vectors_lower_bound"] = 257
                return unchanged("requires-lossy-vector-quantization")
            seen[vector] = index
            book.append(vector)
        indices.append(index)
    report["distinct_vectors"] = len(book)
    payload = b"".join(struct.pack("<4H", *q) for q in book).ljust(2048, b"\0") + indices
    report["candidate_payload_bytes"] = len(payload)
    report["candidate_alloc32_bytes"] = rounded32(len(payload))
    if len(payload) >= len(native.payload) or rounded32(len(payload)) >= rounded32(len(native.payload)):
        return unchanged("vq-codebook-overhead-does-not-win")
    if not enabled:
        return unchanged("disabled")
    h, t = list(native.header), list(native.texture)
    t[3], t[5], t[7], h[7] = fmt, len(payload), tpl.PAYLOAD_VQ, len(payload)
    body = tpl.TEXTURE.pack(*t) + payload
    h[8] = zlib.crc32(body) & 0xffffffff
    result = tpl.HEADER.pack(*h) + body
    checked = vq.read_native_vq(result)
    if reader.decode_level(native, native.size) != vq.decode_level(checked, checked.size):
        raise ValueError("lossless vector coding changed decoded full-resolution RGBA")
    report.update(changed=True, reason="lossless-vq-smaller", after_payload_bytes=len(payload),
        after_alloc32_bytes=rounded32(len(payload)),
        saved_payload_bytes=len(native.payload) - len(payload),
        saved_alloc32_bytes=rounded32(len(native.payload)) - rounded32(len(payload)),
        package_sha256=hashlib.sha256(result).hexdigest())
    return result, report
