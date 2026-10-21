"""Texture formulas (section 4.4) and a read-only .re4tex header reader."""
import math
import struct

HEADER = struct.Struct("<8s10I")      # room/texture_package.hpp Header (48 B)
TEXTURE = struct.Struct("<64s8I")     # Texture (96 B)
PAYLOADS = {0: "linear", 1: "twiddled", 2: "vq"}
FORMATS = {0: "RGB565", 1: "ARGB1555", 2: "ARGB4444", 4: "PAL4_ARGB4444", 5: "PAL8_ARGB4444"}


def read_re4tex(path):
    """Descriptor payload inventory, not live/rounded allocator residency.

    Mip payloads include all levels and any palette tail. Base-only formulas
    remain useful for proposed textures but undercount an existing chain.
    """
    with open(path, "rb") as stream:
        d = stream.read()
    h = HEADER.unpack_from(d, 0)
    if h[0] != b"RE4DCTX\0":
        raise ValueError("%s: not a re4tex" % path)
    count, toff, stride = h[4], h[5], h[3]
    out = []
    for i in range(count):
        t = TEXTURE.unpack_from(d, toff + i * stride)
        w, hh, fmt, doff, dsize, flags, payload = t[1:8]
        out.append(dict(width=w, height=hh, format=FORMATS.get(fmt, fmt), payload=PAYLOADS.get(payload, payload),
                        data_bytes=dsize, vram_bytes=(dsize if flags & 4 else
                            w * hh // 2 + 32 if fmt == 4 and payload == 1 else
                            w * hh + 512 if fmt == 5 and payload == 1 else
                            vram_bytes(PAYLOADS.get(payload, "linear"), w, hh))))
    return dict(file_bytes=len(d), textures=out, vram_bytes=sum(t["vram_bytes"] for t in out))


def decode_pal4_argb4444(data, width, height):
    """Independent pixel-coordinate decoder of native twiddled PAL4 + palette.

    Returns row-major 16-bit words and RGBA bytes for a full equality proof.
    Rectangular PVR textures are adjacent Morton-order squares.
    """
    if not all(8 <= n <= 1024 and not n & (n - 1) for n in (width, height)):
        raise ValueError('invalid PAL4 dimensions')
    if len(data) != width * height // 2 + 32:
        raise ValueError('invalid PAL4 payload length')
    colors = struct.unpack_from('<16H', data, len(data) - 32)
    side = min(width, height)
    words, rgba = [], bytearray()
    for y in range(height):
        for x in range(width):
            location = ((y // side) + (x // side)) * side * side
            bit = 1
            while bit < side:
                location += (bool(y & bit) + 2 * bool(x & bit)) * bit * bit
                bit <<= 1
            index = (data[location // 2] >> (4 * (location % 2))) & 15
            word = colors[index]
            words.append(word)
            rgba.extend(((word >> 8 & 15) * 17, (word >> 4 & 15) * 17,
                         (word & 15) * 17, (word >> 12) * 17))
    return words, bytes(rgba)


def pow2(n):
    return 1 << max(3, math.ceil(math.log2(max(1, n))))


def vram_bytes(kind, w, h):
    """Section 4.4: 16-bit 2wh; full-codebook VQ 2048 + wh/4; PAL4 wh/2; PAL8 wh."""
    w, h = pow2(w), pow2(h)
    if kind == "vq":
        return 2048 + w * h // 4
    if kind == "pal4":
        return w * h // 2
    if kind == "pal8":
        return w * h
    return 2 * w * h


def needed_scale(rho_texels_per_mm, z_min_mm, k=415.692):
    """Largest magnification m = K / (z_min * rho); recommended size factor
    2^floor(log2(min(1, 2m))) (1 = keep, 1/2 = half is invisible, ...)."""
    if rho_texels_per_mm <= 0 or z_min_mm <= 0:
        return 1.0, 0.0
    m = k / (z_min_mm * rho_texels_per_mm)
    f = min(1.0, 2.0 * m)
    return (2.0 ** math.floor(math.log2(f)) if f > 0 else 1.0), m


def vq_loss(psnr, coverage, ref=48.0):
    return coverage * max(0.0, (ref - psnr) / ref)


# ---- decoded images for the review renders (RGBA bytes, row 0 = image top)
class Image:
    __slots__ = ("w", "h", "rgba", "opaque")

    def __init__(self, w, h, rgba):
        self.w, self.h, self.rgba = w, h, bytes(rgba)
        self.opaque = all(a == 255 for a in self.rgba[3::4])


def png_read(path):
    """Minimal PNG decoder (8-bit grey/RGB/palette/grey-alpha/RGBA, non-interlaced) -> Image."""
    import zlib
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s: not a PNG" % path)
    o, idat, plte, trns = 8, bytearray(), b"", b""
    w = h = depth = ctype = inter = None
    while o < len(d):
        n, tag = struct.unpack_from(">I4s", d, o)
        body = d[o + 8:o + 8 + n]
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            plte = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        o += 12 + n
    if depth != 8 or inter:
        raise ValueError("%s: only 8-bit non-interlaced PNGs" % path)
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(bytes(idat))
    stride = w * ch
    out = bytearray(h * stride)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        if f == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + (((line[i - ch] if i >= ch else 0) + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out[y * stride:(y + 1) * stride] = line
        prev = line
    rgba = bytearray(4 * w * h)
    if ctype == 6:
        rgba[:] = out
    elif ctype == 2:
        rgba[0::4], rgba[1::4], rgba[2::4] = out[0::3], out[1::3], out[2::3]
        rgba[3::4] = b"\xff" * (w * h)
    elif ctype == 0:
        rgba[0::4] = rgba[1::4] = rgba[2::4] = out
        rgba[3::4] = b"\xff" * (w * h)
    elif ctype == 4:
        rgba[0::4] = rgba[1::4] = rgba[2::4] = out[0::2]
        rgba[3::4] = out[1::2]
    else:
        for i, k in enumerate(out):
            rgba[4 * i:4 * i + 3] = plte[3 * k:3 * k + 3]
            rgba[4 * i + 3] = trns[k] if k < len(trns) else 255
    return Image(w, h, rgba)


def tpl_images(path, tools_dir):
    """R100.TPL-style GC TPL -> [Image] (convert_tpl.decode_image; deterministic)."""
    import sys
    sys.path.insert(0, str(tools_dir))
    import convert_tpl
    out = []
    for im in convert_tpl.parse_tpl(open(path, "rb").read()):
        px = convert_tpl.decode_image(im)
        out.append(Image(im.width, im.height, bytes(c for p in px for c in p)))
    return out


def png_rgba_bytes(img):
    """Image -> RGBA PNG bytes (zlib level 9, filter 0: deterministic)."""
    import zlib
    raw = bytearray()
    stride = 4 * img.w
    for y in range(img.h):
        raw.append(0)
        raw.extend(img.rgba[y * stride:(y + 1) * stride])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", img.w, img.h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
