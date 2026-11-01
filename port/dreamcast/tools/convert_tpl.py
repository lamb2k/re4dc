#!/usr/bin/env python3
"""Convert an RE4 GameCube TPL plus MTL bindings to a Dreamcast texture pack.

The input and output contain private game assets. This tracked tool only
contains format conversion code and emits RGB565 or one-bit ARGB1555 pixels in
linear row order. The runtime twiddles those pixels while uploading to PVR RAM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import struct
import sys
import zlib
from dataclasses import dataclass


TPL_MAGIC = 0x0020AF30
GX_TF_I4 = 0
GX_TF_I8 = 1
GX_TF_IA4 = 2
GX_TF_IA8 = 3
GX_TF_RGB565 = 4
GX_TF_RGBA8 = 6
GX_TF_C4 = 8
GX_TF_C8 = 9
GX_TF_CMPR = 14

GX_TL_IA8 = 0
GX_TL_RGB565 = 1
GX_TL_RGB5A3 = 2

MAGIC = b"RE4DCTX\0"
VERSION = 2
FORMAT_RGB565 = 0
FORMAT_ARGB1555 = 1
FORMAT_ARGB4444 = 2
FORMAT_PAL4_ARGB4444 = 4
FORMAT_PAL8_ARGB4444 = 5
FLAG_ALPHA = 1
FLAG_BINARY_ALPHA = 2
# CAST_MIPMAP (Phase 2 A2): the VQ payload carries the PVR mip chain (codebook, then the index bytes of every level
# from 1x1 up, the PVR's own layout); the runtime samples it with the TCW mipmap bit. Only builds with CAST_MIPMAP=1
# accept such a package (room/texture_package.cpp).
FLAG_MIPMAP = 4
# R4b: how the payload is laid out, so the runtime can upload it without
# interpreting it. Version 1 had no such field and was always LINEAR.
PAYLOAD_LINEAR = 0
PAYLOAD_TWIDDLED = 1
PAYLOAD_VQ = 2
HEADER = struct.Struct("<8s10I")
TEXTURE = struct.Struct("<64s8I")
IMAGE_NUMBER = re.compile(r"-(\d+)\.png$", re.IGNORECASE)


def canonical_native_crc(blob: bytes) -> bytes:
    """Accept a verified legacy CRC domain, emit the runtime's full body CRC.

    Texture Package::adopt covers everything after header_size, including all
    descriptors. The CRC word is Header field8 at byte36; data_size at32 is
    untouched. This changes no descriptor, palette, codebook or texel byte.
    """
    if len(blob) < HEADER.size:
        raise ValueError("short native texture header")
    h = list(HEADER.unpack_from(blob))
    if (h[:4] != [MAGIC, VERSION, HEADER.size, TEXTURE.size] or
            not h[4] or h[5] != HEADER.size or
            h[5] + h[4] * h[3] > h[6] or h[6] + h[7] != len(blob)):
        raise ValueError("unsupported native texture CRC bounds")
    canonical = zlib.crc32(blob[h[2]:]) & 0xffffffff
    if h[8] == canonical:
        return blob
    if h[8] != zlib.crc32(blob[h[6]:]) & 0xffffffff:
        raise ValueError("unknown native texture CRC convention")
    h[8] = canonical
    return HEADER.pack(*h) + blob[HEADER.size:]


@dataclass(frozen=True)
class TplImage:
    width: int
    height: int
    format: int
    data: bytes
    palette_format: int | None = None
    palette_data: bytes | None = None


@dataclass(frozen=True)
class MaterialBinding:
    name: str
    color_image: int
    alpha_image: int | None


def _u32be(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"read outside TPL at 0x{offset:x}")
    return struct.unpack_from(">I", data, offset)[0]


def _expected_image_size(width: int, height: int, image_format: int) -> int:
    if image_format in (GX_TF_I4, GX_TF_C4, GX_TF_CMPR):
        return ((width + 7) // 8) * ((height + 7) // 8) * 32
    if image_format in (GX_TF_I8, GX_TF_IA4, GX_TF_C8):
        return ((width + 7) // 8) * ((height + 3) // 4) * 32
    if image_format in (GX_TF_IA8, GX_TF_RGB565):
        return ((width + 3) // 4) * ((height + 3) // 4) * 32
    if image_format == GX_TF_RGBA8:
        return ((width + 3) // 4) * ((height + 3) // 4) * 64
    raise ValueError(f"unsupported TPL image format 0x{image_format:x}")


def parse_tpl(data: bytes) -> list[TplImage]:
    if len(data) < 12:
        raise ValueError("TPL is smaller than its header")
    magic, image_count, descriptor_offset = struct.unpack_from(">III", data)
    if magic != TPL_MAGIC:
        raise ValueError(f"unexpected TPL magic 0x{magic:08x}")
    if image_count == 0 or descriptor_offset + image_count * 8 > len(data):
        raise ValueError("TPL descriptor table is outside the file")

    images: list[TplImage] = []
    for image_index in range(image_count):
        descriptor = descriptor_offset + image_index * 8
        texture_header = _u32be(data, descriptor)
        palette_header = _u32be(data, descriptor + 4)
        if texture_header == 0 or texture_header + 12 > len(data):
            raise ValueError(f"image {image_index} has an invalid texture header")
        height, width, image_format, data_offset = struct.unpack_from(
            ">HHII", data, texture_header
        )
        if width == 0 or height == 0:
            raise ValueError(f"image {image_index} has zero dimensions")
        size = _expected_image_size(width, height, image_format)
        if data_offset + size > len(data):
            raise ValueError(f"image {image_index} data is outside the file")
        palette_format = None
        palette_data = None
        if image_format in (GX_TF_C4, GX_TF_C8):
            if palette_header == 0 or palette_header + 12 > len(data):
                raise ValueError(f"image {image_index} has no palette header")
            palette_entries, _, _, palette_format, palette_offset = struct.unpack_from(
                ">HBBII", data, palette_header
            )
            palette_size = palette_entries * 2
            if palette_entries == 0 or palette_offset + palette_size > len(data):
                raise ValueError(f"image {image_index} palette is outside the file")
            palette_data = data[palette_offset:palette_offset + palette_size]
        images.append(TplImage(
            width, height, image_format, data[data_offset:data_offset + size],
            palette_format, palette_data,
        ))
    return images


def _expand_565(value: int) -> tuple[int, int, int]:
    red = (value >> 11) & 31
    green = (value >> 5) & 63
    blue = value & 31
    return (
        (red << 3) | (red >> 2),
        (green << 2) | (green >> 4),
        (blue << 3) | (blue >> 2),
    )


def _mix(first: tuple[int, int, int], second: tuple[int, int, int],
         first_weight: int, denominator: int) -> tuple[int, int, int]:
    second_weight = denominator - first_weight
    return tuple(
        (first[channel] * first_weight + second[channel] * second_weight) // denominator
        for channel in range(3)
    )


def decode_cmpr(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (image.width * image.height)
    source = memoryview(image.data)
    offset = 0
    for tile_y in range(0, image.height, 8):
        for tile_x in range(0, image.width, 8):
            for sub_y in (0, 4):
                for sub_x in (0, 4):
                    color0, color1 = struct.unpack_from(">HH", source, offset)
                    selectors = source[offset + 4:offset + 8]
                    offset += 8
                    rgb0 = _expand_565(color0)
                    rgb1 = _expand_565(color1)
                    if color0 > color1:
                        palette = (
                            (*rgb0, 255),
                            (*rgb1, 255),
                            (*_mix(rgb0, rgb1, 2, 3), 255),
                            (*_mix(rgb0, rgb1, 1, 3), 255),
                        )
                    else:
                        palette = (
                            (*rgb0, 255),
                            (*rgb1, 255),
                            (*_mix(rgb0, rgb1, 1, 2), 255),
                            (0, 0, 0, 0),
                        )
                    for row in range(4):
                        bits = selectors[row]
                        y = tile_y + sub_y + row
                        if y >= image.height:
                            continue
                        for column in range(4):
                            x = tile_x + sub_x + column
                            if x < image.width:
                                selector = (bits >> (6 - column * 2)) & 3
                                pixels[y * image.width + x] = palette[selector]
    return pixels


def decode_i4(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 255)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 8):
        for tile_x in range(0, image.width, 8):
            for row in range(8):
                y = tile_y + row
                for pair in range(4):
                    value = image.data[offset]
                    offset += 1
                    for within, nibble in enumerate((value >> 4, value & 15)):
                        x = tile_x + pair * 2 + within
                        if x < image.width and y < image.height:
                            intensity = nibble * 17
                            pixels[y * image.width + x] = (
                                intensity, intensity, intensity, 255
                            )
    return pixels


def decode_i8(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 255)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 4):
        for tile_x in range(0, image.width, 8):
            for row in range(4):
                y = tile_y + row
                for column in range(8):
                    intensity = image.data[offset]
                    offset += 1
                    x = tile_x + column
                    if x < image.width and y < image.height:
                        pixels[y * image.width + x] = (
                            intensity, intensity, intensity, 255
                        )
    return pixels


def decode_ia4(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 4):
        for tile_x in range(0, image.width, 8):
            for row in range(4):
                y = tile_y + row
                for column in range(8):
                    value = image.data[offset]
                    offset += 1
                    x = tile_x + column
                    if x < image.width and y < image.height:
                        alpha = (value >> 4) * 17
                        intensity = (value & 15) * 17
                        pixels[y * image.width + x] = (
                            intensity, intensity, intensity, alpha
                        )
    return pixels


def decode_ia8(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 4):
        for tile_x in range(0, image.width, 4):
            for row in range(4):
                y = tile_y + row
                for column in range(4):
                    alpha = image.data[offset]
                    intensity = image.data[offset + 1]
                    offset += 2
                    x = tile_x + column
                    if x < image.width and y < image.height:
                        pixels[y * image.width + x] = (
                            intensity, intensity, intensity, alpha
                        )
    return pixels


def decode_rgba8(image: TplImage) -> list[tuple[int, int, int, int]]:
    pixels = [(0, 0, 0, 0)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 4):
        for tile_x in range(0, image.width, 4):
            ar_offset = offset
            gb_offset = offset + 32
            for row in range(4):
                y = tile_y + row
                for column in range(4):
                    pixel = row * 4 + column
                    alpha = image.data[ar_offset + pixel * 2]
                    red = image.data[ar_offset + pixel * 2 + 1]
                    green = image.data[gb_offset + pixel * 2]
                    blue = image.data[gb_offset + pixel * 2 + 1]
                    x = tile_x + column
                    if x < image.width and y < image.height:
                        pixels[y * image.width + x] = (red, green, blue, alpha)
            offset += 64
    return pixels


def _decode_palette_entry(
    value: int, palette_format: int
) -> tuple[int, int, int, int]:
    if palette_format == GX_TL_IA8:
        alpha = value >> 8
        intensity = value & 0xFF
        return (intensity, intensity, intensity, alpha)
    if palette_format == GX_TL_RGB565:
        return (*_expand_565(value), 255)
    if palette_format == GX_TL_RGB5A3:
        if value & 0x8000:
            red = (value >> 10) & 31
            green = (value >> 5) & 31
            blue = value & 31
            return (
                (red << 3) | (red >> 2),
                (green << 3) | (green >> 2),
                (blue << 3) | (blue >> 2),
                255,
            )
        alpha = (value >> 12) & 7
        red = (value >> 8) & 15
        green = (value >> 4) & 15
        blue = value & 15
        return (red * 17, green * 17, blue * 17,
                (alpha << 5) | (alpha << 2) | (alpha >> 1))
    raise ValueError(f"unsupported TPL palette format 0x{palette_format:x}")


def decode_indexed(image: TplImage) -> list[tuple[int, int, int, int]]:
    if image.palette_format is None or image.palette_data is None:
        raise ValueError("indexed TPL image has no palette")
    palette = [
        _decode_palette_entry(value, image.palette_format)
        for value, in struct.iter_unpack(">H", image.palette_data)
    ]
    pixels = [(0, 0, 0, 0)] * (image.width * image.height)
    offset = 0
    tile_width = 8
    tile_height = 8 if image.format == GX_TF_C4 else 4
    for tile_y in range(0, image.height, tile_height):
        for tile_x in range(0, image.width, tile_width):
            for row in range(tile_height):
                y = tile_y + row
                if image.format == GX_TF_C4:
                    for pair in range(4):
                        value = image.data[offset]
                        offset += 1
                        for within, index in enumerate((value >> 4, value & 15)):
                            x = tile_x + pair * 2 + within
                            if x < image.width and y < image.height:
                                pixels[y * image.width + x] = palette[index]
                else:
                    for column in range(8):
                        index = image.data[offset]
                        offset += 1
                        x = tile_x + column
                        if x < image.width and y < image.height:
                            pixels[y * image.width + x] = palette[index]
    return pixels


def decode_rgb565(image: TplImage) -> list[tuple[int, int, int, int]]:
    # Same source layout used by extract_ui_images.decode_16: big-endian
    # RGB565 in 4x4 tiles. Reuse the existing channel expansion; no tint/boost.
    pixels = [(0, 0, 0, 255)] * (image.width * image.height)
    offset = 0
    for tile_y in range(0, image.height, 4):
        for tile_x in range(0, image.width, 4):
            for row in range(4):
                for column in range(4):
                    value = struct.unpack_from(">H", image.data, offset)[0]
                    offset += 2
                    x, y = tile_x + column, tile_y + row
                    if x < image.width and y < image.height:
                        pixels[y * image.width + x] = (*_expand_565(value), 255)
    return pixels


def decode_image(image: TplImage) -> list[tuple[int, int, int, int]]:
    if image.format == GX_TF_CMPR:
        return decode_cmpr(image)
    if image.format == GX_TF_I4:
        return decode_i4(image)
    if image.format == GX_TF_I8:
        return decode_i8(image)
    if image.format == GX_TF_IA4:
        return decode_ia4(image)
    if image.format == GX_TF_IA8:
        return decode_ia8(image)
    if image.format == GX_TF_RGB565:
        return decode_rgb565(image)
    if image.format == GX_TF_RGBA8:
        return decode_rgba8(image)
    if image.format in (GX_TF_C4, GX_TF_C8):
        return decode_indexed(image)
    raise ValueError(f"unsupported TPL image format 0x{image.format:x}")


def _image_number(value: str, line_no: int) -> int:
    match = IMAGE_NUMBER.search(value.replace("\\", "/"))
    if match is None:
        raise ValueError(f"MTL line {line_no}: cannot identify image in {value!r}")
    return int(match.group(1))


def parse_mtl(text: str) -> list[MaterialBinding]:
    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line_no, raw_line in enumerate(text.splitlines(), 1):
        fields = raw_line.strip().split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "newmtl":
            if len(fields) < 2:
                raise ValueError(f"MTL line {line_no}: material needs a name")
            current = {"name": " ".join(fields[1:]), "color": None, "alpha": None}
            records.append(current)
        elif fields[0] in {"map_Kd", "map_d"}:
            if current is None or len(fields) < 2:
                raise ValueError(f"MTL line {line_no}: map precedes material")
            key = "color" if fields[0] == "map_Kd" else "alpha"
            current[key] = _image_number(fields[-1], line_no)

    bindings: list[MaterialBinding] = []
    names: set[str] = set()
    for record in records:
        name = str(record["name"])
        if name in names:
            raise ValueError(f"duplicate material {name!r}")
        names.add(name)
        if record["color"] is None:
            raise ValueError(f"material {name!r} has no map_Kd")
        bindings.append(MaterialBinding(name, int(record["color"]), record["alpha"]))
    if not bindings:
        raise ValueError("MTL has no textured materials")
    return bindings


def _name_bytes(name: str) -> bytes:
    encoded = name.encode("utf-8")
    if len(encoded) >= 64:
        raise ValueError(f"material name is too long: {name!r}")
    return encoded.ljust(64, b"\0")


# RE4DC_PACK_ROUND=1 (colour27, 2026-10-27; offline, default 0 = the historical truncating packers, byte-identical
# packages): round each 8-bit channel to the nearest 5/6/4-bit level instead of dropping its low bits. Truncation
# darkens every value by half a step on average and sends 8-bit values below 16 (4444) / 8 (565, 1555) to 0, so faint
# effect alpha vanishes (colour27 audit: 11 % of the visible texels of PS2 effects ship fully transparent).
PACK_ROUND = os.environ.get("RE4DC_PACK_ROUND", "0") == "1"


def _q(value: int, levels: int) -> int:
    """8-bit channel -> 0..levels: nearest level (PACK_ROUND) or the historical truncation."""
    if PACK_ROUND:
        return (value * levels + 127) // 255
    return value >> {31: 3, 63: 2, 15: 4}[levels]


def _pack_565(pixel: tuple[int, int, int, int]) -> int:
    red, green, blue, _ = pixel
    return (_q(red, 31) << 11) | (_q(green, 63) << 5) | _q(blue, 31)


def _pack_1555(pixel: tuple[int, int, int, int]) -> int:
    red, green, blue, alpha = pixel
    return ((1 if alpha >= 128 else 0) << 15) | (_q(red, 31) << 10) | (_q(green, 31) << 5) | _q(blue, 31)


def _pack_4444(pixel: tuple[int, int, int, int]) -> int:
    red, green, blue, alpha = pixel
    return (_q(alpha, 15) << 12) | (_q(red, 15) << 8) | (_q(green, 15) << 4) | _q(blue, 15)


def downsample_box(
    pixels: list[tuple[int, int, int, int]], width: int, height: int
) -> tuple[list[tuple[int, int, int, int]], int, int]:
    new_width = max(1, width // 2)
    new_height = max(1, height // 2)
    result: list[tuple[int, int, int, int]] = []
    for y in range(new_height):
        for x in range(new_width):
            samples = [
                pixels[min(y * 2 + dy, height - 1) * width +
                       min(x * 2 + dx, width - 1)]
                for dy in range(2)
                for dx in range(2)
            ]
            result.append(tuple(
                sum(pixel[channel] for pixel in samples) // len(samples)
                for channel in range(4)
            ))
    return result, new_width, new_height


def vq_mip_index_bytes(size: int) -> int:
    """PVR mipmapped VQ index bytes of a square size x size texture: one byte for the 1x1 level, then one byte per
    2x2 block of every level 2x2 .. size x size."""
    total, s = 1, 2
    while s <= size:
        total += (s // 2) * (s // 2)
        s *= 2
    return total


def package_existing_vq(encoded: bytes, material: str = "source", allow_mipmaps: bool = False) -> tuple[bytes, dict]:
    """Wrap a pinned pvrtex DcTx candidate without decoding or re-encoding.

    Bounded support: 16-bit RGB565/ARGB1555/ARGB4444, full 256-entry VQ,
    power-of-two dimensions, no strides or partial/small codebooks; mipmaps only
    with allow_mipmaps (square, FLAG_MIPMAP; CAST_MIPMAP runtime builds).
    DcTx layout authority: pinned KOS utils/pvrtex/file_dctex.h/.c.
    """
    if len(encoded)<32 or encoded[:4]!=b'DcTx':
        raise ValueError('expected pvrtex DcTx header')
    size,=struct.unpack_from('<I',encoded,4)
    version,units,book,colors=encoded[8:12]
    width,height,mode=struct.unpack_from('<HHI',encoded,12)
    fmt=(mode>>27)&7
    dimensions=all(8<=n<=1024 and n&(n-1)==0 for n in (width,height))
    if (size!=len(encoded) or size%32 or version!=0 or units!=0 or book!=255 or
        not dimensions or fmt>2 or not mode&(1<<30) or mode&((0 if allow_mipmaps else 1<<31)|(1<<26)|(1<<25)|(1<<11)) or
        any(encoded[20:32])):
        raise ValueError('unsupported DcTx version, layout, size or codebook')
    if (8<<((mode>>3)&7),8<<(mode&7))!=(width,height):
        raise ValueError('DcTx dimensions disagree with PVR size flags')
    mip=bool(mode&(1<<31))
    if mip and width!=height:
        raise ValueError('a mipmapped PVR texture must be square')
    expected=2048+(vq_mip_index_bytes(width) if mip else width*height//4)
    if len(encoded)!=((32+expected+31)&~31):
        raise ValueError('VQ payload must be the full codebook plus compact block indices')
    native_format={0:FORMAT_ARGB1555,1:FORMAT_RGB565,2:FORMAT_ARGB4444}[fmt]
    flags=0 if fmt==1 else FLAG_ALPHA | (FLAG_BINARY_ALPHA if fmt==0 else 0)
    if mip:
        flags|=FLAG_MIPMAP
    payload=encoded[32:32+expected] # DcTx transport padding is not texture data.
    start=HEADER.size+TEXTURE.size
    descriptor=TEXTURE.pack(_name_bytes(material),width,height,native_format,start,len(payload),flags,PAYLOAD_VQ,0)
    body=descriptor+payload
    header=HEADER.pack(MAGIC,VERSION,HEADER.size,TEXTURE.size,1,HEADER.size,start,len(payload),zlib.crc32(body)&0xffffffff,1,0)
    return header+body,{'width':width,'height':height,'payload':'vq','format':native_format,
                        'encoded_file_bytes':len(encoded),'vram_bytes':len(payload),
                        'uncompressed_16bit_bytes':width*height*2,
                        'candidate_only':True,'reencoded':False,**({'mipmap':True} if mip else {})}


def package_exact_pal4_argb4444(native: bytes) -> tuple[bytes, dict]:
    """Losslessly replace one native twiddled ARGB4444 descriptor with PAL4.

    TEX_PAL4_ALPHA=1 is required. All 16-bit words must fit a 16-color exact
    dictionary. No resampling or quantization; source label/flags/header identity
    metadata stay unchanged. The two adjacent Morton-order indices occupy the
    low then high nibble, matching the native glyph atlas/PVR PAL4 layout.
    """
    if len(native) < HEADER.size + TEXTURE.size:
        raise ValueError('short native package')
    h = list(HEADER.unpack_from(native))
    if (h[0:4] != [MAGIC, VERSION, HEADER.size, TEXTURE.size] or
            h[4] != 1 or h[5] != HEADER.size or
            h[6] != HEADER.size + TEXTURE.size or h[6] + h[7] != len(native)):
        raise ValueError('expected one canonical native descriptor')
    if h[8] == zlib.crc32(native[HEADER.size:]) & 0xffffffff:
        crc_rule = 'header'
    elif h[8] == zlib.crc32(native[h[6]:]) & 0xffffffff:
        # The older PS2 writer used the texel-only CRC. Its canonical shape
        # below is still checked; the result always emits the full-body CRC.
        crc_rule = 'data'
    else:
        raise ValueError('native payload CRC mismatch')
    t = list(TEXTURE.unpack_from(native, h[5]))
    _, w, hh, fmt, off, size, flags, layout, reserved = t
    if (not all(8 <= n <= 1024 and not n & (n - 1) for n in (w, hh)) or
            fmt != FORMAT_ARGB4444 or layout != PAYLOAD_TWIDDLED or reserved or
            flags & FLAG_MIPMAP or off != h[6] or size != w * hh * 2 or size != h[7]):
        raise ValueError('expected base-level native twiddled ARGB4444')
    words = struct.unpack_from('<%dH' % (w * hh), native, off)
    palette = sorted(set(words))
    if len(palette) > 16:
        raise ValueError('exact PAL4 needs at most 16 distinct ARGB4444 words')
    dictionary = {word: i for i, word in enumerate(palette)}
    indices = bytes(dictionary[words[i]] | dictionary[words[i + 1]] << 4
                    for i in range(0, len(words), 2))
    payload = indices + struct.pack('<16H', *(palette + [0] * (16 - len(palette))))
    t[3], t[5] = FORMAT_PAL4_ARGB4444, len(payload)
    body = TEXTURE.pack(*t) + payload
    h[7], h[8] = len(payload), zlib.crc32(body) & 0xffffffff
    return HEADER.pack(*h) + body, dict(width=w, height=hh, unique_words=len(palette),
        format=FORMAT_PAL4_ARGB4444, payload='twiddled', vram_bytes=len(payload),
        saved_bytes=size-len(payload), palette_ram_bytes=64, lossless=True, source_crc_rule=crc_rule,
        required_build_knob='TEX_PAL4_ALPHA=1')


def build_package(
    images: list[TplImage], bindings: list[MaterialBinding],
    max_dimension: int | None = None, twiddle: bool = False,
    pad_to_power_of_two: bool = False, source_intensity_alpha: bool = False,
    source_mask_alpha: bool = False,
    source_pixels: dict[int, list[tuple[int, int, int, int]]] | None = None,
) -> tuple[bytes, dict[str, object]]:
    # source_pixels: optional RGBA replacements (e.g. ui_overrides.py) for the decoded
    # texels of an image index, same width*height; encoded exactly as a decoded image.
    decoded: dict[int, list[tuple[int, int, int, int]]] = {}
    packed: dict[tuple[int, int | None], tuple[int, int, int, int, int, int]] = {}

    def get_image(index: int) -> tuple[TplImage, list[tuple[int, int, int, int]]]:
        if index < 0 or index >= len(images):
            raise ValueError(f"MTL references missing TPL image {index}")
        if index not in decoded and source_pixels and index in source_pixels:
            pixels = list(source_pixels[index])
            if len(pixels) != images[index].width * images[index].height:
                raise ValueError(f"replacement pixels for image {index} do not match its dimensions")
            decoded[index] = pixels
        if index not in decoded:
            decoded[index] = decode_image(images[index])
            if source_intensity_alpha and images[index].format in (GX_TF_I4, GX_TF_I8):
                # GX intensity formats replicate intensity into alpha as well.
                # Opt in for recovered consumers; legacy viewer candidates are
                # not silently regenerated with changed alpha classification.
                decoded[index] = [(r, g, b, r) for r, g, b, _ in decoded[index]]
        return images[index], decoded[index]

    texture_offset = HEADER.size
    data_offset = texture_offset + len(bindings) * TEXTURE.size
    texture_blob = bytearray()
    data_blob = bytearray()
    manifest_materials: list[dict[str, object]] = []

    for binding in bindings:
        key = (binding.color_image, binding.alpha_image)
        if key not in packed:
            source, pixels = get_image(binding.color_image)
            pixels = list(pixels)
            has_alpha = any(pixel[3] < 255 for pixel in pixels)
            if binding.alpha_image is not None:
                alpha_source, alpha_pixels = get_image(binding.alpha_image)
                if (alpha_source.width, alpha_source.height) != (source.width, source.height):
                    raise ValueError(f"material {binding.name!r} alpha dimensions differ")
                pixels = [
                    (color[0], color[1], color[2], alpha[3] if source_mask_alpha else alpha[0])
                    for color, alpha in zip(pixels, alpha_pixels)
                ]
                has_alpha = True
            width = source.width
            height = source.height
            while max_dimension is not None and max(width, height) > max_dimension:
                pixels, width, height = downsample_box(pixels, width, height)
            if pad_to_power_of_two:
                # Keep every source texel; replicate the border into padding.
                # The source adapter scales UVs by source/native dimensions.
                padded_w = max(8, 1 << (width - 1).bit_length())
                padded_h = max(8, 1 << (height - 1).bit_length())
                if padded_w > 1024 or padded_h > 1024:
                    raise ValueError("texture exceeds native PVR dimensions")
                pixels = [pixels[min(y, height-1)*width + min(x, width-1)]
                          for y in range(padded_h) for x in range(padded_w)]
                width, height = padded_w, padded_h
            # The source's default room/model blend mode is SRCALPHA /
            # INVSRCALPHA. Preserve mask gradients in the Dreamcast's bounded
            # 16-bit format instead of turning them into opaque punch-through
            # silhouettes.
            image_format = FORMAT_ARGB4444 if has_alpha else FORMAT_RGB565
            pack_pixel = _pack_4444 if has_alpha else _pack_565
            texels = [pack_pixel(pixel) for pixel in pixels]
            payload_format = PAYLOAD_LINEAR
            if twiddle:
                texels = twiddle_16bpp(texels, width, height)
                payload_format = PAYLOAD_TWIDDLED
            raw = b"".join(struct.pack("<H", texel) for texel in texels)
            relative_offset = len(data_blob)
            data_blob.extend(raw)
            binary_alpha = (
                has_alpha and all(pixel[3] in (0, 255) for pixel in pixels)
            )
            flags = FLAG_ALPHA if has_alpha else 0
            if binary_alpha:
                flags |= FLAG_BINARY_ALPHA
            packed[key] = (
                relative_offset, len(raw), image_format, flags,
                width, height, payload_format,
            )
        (relative_offset, raw_size, image_format, flags, width, height,
         payload_format) = packed[key]
        texture_blob.extend(
            TEXTURE.pack(
                _name_bytes(binding.name), width, height,
                image_format, data_offset + relative_offset, raw_size, flags,
                payload_format, 0
            )
        )
        manifest_materials.append({
            "name": binding.name,
            "color_image": binding.color_image,
            "alpha_image": binding.alpha_image,
            "width": width,
            "height": height,
            "format": "argb4444" if flags & FLAG_ALPHA else "rgb565",
            "binary_alpha": bool(flags & FLAG_BINARY_ALPHA),
            "bytes": raw_size,
            "payload": ("twiddled" if payload_format == PAYLOAD_TWIDDLED
                        else "vq" if payload_format == PAYLOAD_VQ else "linear"),
        })

    payload = bytes(texture_blob + data_blob)
    payload_crc32 = zlib.crc32(payload) & 0xFFFFFFFF
    header = HEADER.pack(
        MAGIC, VERSION, HEADER.size, TEXTURE.size, len(bindings), texture_offset,
        data_offset, len(data_blob), payload_crc32, len(images), 0
    )
    metadata = {
        "format": "re4dc-textures",
        "version": VERSION,
        "tpl_images": len(images),
        "materials": manifest_materials,
        "texture_bytes": len(data_blob),
        "payload_crc32": f"{payload_crc32:08x}",
        "max_dimension": max_dimension,
        "twiddled": twiddle,
    }
    return header + payload, metadata


def _twiddle_table(value: int) -> int:
    """Spread the low bits of `value` into even bit positions."""
    result = 0
    for bit in range(10):
        result |= (value & (1 << bit)) << bit
    return result


def twiddle_16bpp(pixels: list[int], width: int, height: int) -> list[int]:
    """Reorder 16-bit texels into the PVR's twiddled layout.

    This is the same mapping `pvr_txr_load_ex()` applies while uploading, moved
    to build time so the runtime can copy the payload straight into texture
    memory. Doing it here and uploading raw must produce byte-identical VRAM.
    """
    minimum = min(width, height)
    mask = minimum - 1
    out = [0] * (width * height)
    for y in range(height):
        row = y * width
        twiddled_y = _twiddle_table(y & mask)
        block = (y // minimum) * minimum * minimum
        for x in range(width):
            index = (twiddled_y | (_twiddle_table(x & mask) << 1)) + \
                (x // minimum) * minimum * minimum + block
            out[index] = pixels[row + x]
    return out


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tpl", type=pathlib.Path, help="private GameCube TPL")
    parser.add_argument("mtl", type=pathlib.Path, help="private exported MTL")
    parser.add_argument("output", type=pathlib.Path, help="private Dreamcast texture pack")
    parser.add_argument("--manifest", type=pathlib.Path, help="JSON manifest path")
    parser.add_argument(
        "--max-dimension", type=int,
        help="halve oversized textures until both dimensions fit this limit",
    )
    parser.add_argument(
        "--twiddle", action="store_true",
        help="write payloads in the PVR's twiddled order so the runtime can "
             "copy them straight into texture memory",
    )
    args = parser.parse_args(argv)

    tpl_data = args.tpl.read_bytes()
    mtl_data = args.mtl.read_bytes()
    images = parse_tpl(tpl_data)
    bindings = parse_mtl(mtl_data.decode("utf-8-sig"))
    if args.max_dimension is not None and args.max_dimension < 8:
        raise ValueError("max dimension must be at least 8")
    package, metadata = build_package(
        images, bindings, args.max_dimension, args.twiddle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(package)
    metadata.update({
        "tpl_source": args.tpl.name,
        "tpl_sha256": sha256_bytes(tpl_data),
        "mtl_source": args.mtl.name,
        "mtl_sha256": sha256_bytes(mtl_data),
        "package": args.output.name,
        "package_bytes": len(package),
        "package_sha256": sha256_bytes(package),
    })
    manifest_path = args.manifest or args.output.with_suffix(args.output.suffix + ".json")
    manifest_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, ValueError) as error:
        print(f"texture conversion failed: {error}", file=sys.stderr)
        raise SystemExit(1)
