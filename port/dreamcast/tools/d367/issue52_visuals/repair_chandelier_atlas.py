#!/usr/bin/env python3
"""Opt-in exact Test21 chandelier PS2 material atlas/UV candidate; no staging.

Preserves the selected room/model extents, geometry, joints, weights and material
contract. Source repeat addressing is baked into eight-texel periodic collars.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, struct, sys, zlib
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367/test12fx')]
import convert_character as cc
import convert_tpl as ct
import ps2_bin as pb
import ps2_objects as po
import ps2_tpl_decode as pt
import room_smd as rs

SIZE, BORDER = 256, 8
DAR_SHA = 'cf667833fafcb87a332be5d343ad47b772c781ecff0f5db2a9df3fc6fcbf590f'
INPUTS = {
    'r117-gc-1f.bin': '0ab9483cadd1ec5638f3f54fe271e7de54a6df66573018520c2fbd14d95b3746',
    'r117-ps2-1f.bin': '7befa981c606cf3f595595e7c271790c1c77d4c9598dc03c2d684e56bda8cade',
    'r117-gc-20.tpl': 'b72fa619e9e654bf620ff2fef02f9db770ec9e5ee7da1c563d850864b63b1ff2',
    'r117-ps2-20.tpl': '55b8550f80e44219d6c125ba0c0b79c2e7f09fff0228ccd3d7a2a9c2da4be772',
}
# Original PS2 material order, source image/mask, exact unscaled tile rectangle.
TILES = [
    dict(material=0, image=0, mask=None, rect=(8, 8, 128, 128), triangles=1046),
    dict(material=1, image=3, mask=4, rect=(168, 8, 64, 64), triangles=40),
    dict(material=2, image=1, mask=2, rect=(8, 160, 128, 16), triangles=184),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fnv(data):
    value = 2166136261
    for b in data:
        value = ((value ^ b) * 16777619) & 0xffffffff
    return value


def payload_key(data):
    return '%08x-%08x' % (zlib.crc32(data) & 0xffffffff, fnv(data))


def pair_key(colour, mask):
    words = [int(v, 16) for k in [colour, mask] for v in k.split('-')]
    return payload_key(b'R4MPv001' + struct.pack('<4I', *words))


def mask_levels(pixels):
    if any(r != g or r != b or r % 16 for r, g, b, a in pixels):
        raise ValueError('unreviewed PS2 mask intensity')
    return [r // 16 * 17 for r, g, b, a in pixels]


def atlas_uv(rect, uv):
    x, y, w, h = rect
    return ((x + uv[0] * w) / SIZE, (y + uv[1] * h) / SIZE)


def paste_repeat(atlas, occupied, pixels, rect):
    x, y, w, h = rect
    for yy in range(y - BORDER, y + h + BORDER):
        for xx in range(x - BORDER, x + w + BORDER):
            if not (0 <= xx < SIZE and 0 <= yy < SIZE) or (xx, yy) in occupied:
                raise ValueError('atlas collar outside or overlapping')
            occupied.add((xx, yy))
            atlas[yy * SIZE + xx] = pixels[((yy - y) % h) * w + (xx - x) % w]


def bilinear(pixels, w, h, uv):
    x, y = uv[0] * w - .5, uv[1] * h - .5
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    out = [0.0] * 4
    for dx, wx in [(0, 1 - fx), (1, fx)]:
        for dy, wy in [(0, 1 - fy), (1, fy)]:
            p = pixels[((y0 + dy) % h) * w + (x0 + dx) % w]
            for c in range(4):
                out[c] += p[c] * wx * wy
    return out


def decode_tiles(data):
    headers = pt.parse_tpl(data)['entries']
    decoded = {}
    for i, header in enumerate(headers):
        w, h, rgba, stats = pt.decode(data, header)
        if header['interlace'] & 1:
            raise ValueError('unreviewed chandelier image orientation')
        decoded[i] = (w, h, list(zip(*(iter(rgba),) * 4)))
    result = {}
    for tile in TILES:
        x, y, w, h = tile['rect']
        iw, ih, pixels = decoded[tile['image']]
        if (iw, ih) != (w, h):
            raise ValueError('unreviewed PS2 image dimensions')
        if tile['mask'] is None:
            pixels = [(r, g, b, 255) for r, g, b, a in pixels]
        else:
            mw, mh, mask = decoded[tile['mask']]
            if (mw, mh) != (w, h):
                raise ValueError('source mask dimensions differ')
            pixels = [(r, g, b, a) for (r, g, b, _), a in zip(pixels, mask_levels(mask))]
        result[tile['material']] = pixels
    return result


def geometry(data):
    """Oriented LE model triangles, excluding the deliberately changed UVs."""
    h = rs.bin_layout(data, '<')
    stride = 8 if h['flags'] & 0x80000000 else 6
    ns = 4 if h['flags'] & 0x20000000 else 8
    triangles = []
    for rel, size in rs.part_headers(data, '<', h):
        at = h['ptr']['parts'] + rel
        cur, end = at + 32, at + 32 + size
        while cur < end:
            op = data[cur]
            cur += 1
            if not op:
                continue
            if op not in (0x80, 0x90, 0x98):
                raise ValueError('unexpected primitive')
            count = struct.unpack_from('>H', data, cur)[0]
            cur += 2
            recs = [struct.unpack_from('>4H' if stride == 8 else '>3H', data, cur + i * stride) for i in range(count)]
            cur += count * stride
            for tri in cc.triangulate(op, recs):
                corners = []
                for c in tri:
                    vi, ni = c[:2]
                    ci = c[2] if stride == 8 else 0
                    p = data[h['ptr']['vtx'] + vi * 8:h['ptr']['vtx'] + vi * 8 + 8]
                    n = data[h['ptr']['nrm'] + ni * ns:h['ptr']['nrm'] + ni * ns + ns]
                    colour = data[h['ptr']['clr'] + ci * 4:h['ptr']['clr'] + ci * 4 + 4]
                    wi = struct.unpack_from('<H', p, 6)[0]
                    weight = data[h['ptr']['weight'] + wi * 8:h['ptr']['weight'] + wi * 8 + 8]
                    corners.append((p, n, colour, weight))
                triangles.append(min(tuple(corners), tuple(corners[1:] + corners[:1]), tuple(corners[2:] + corners[:2])))
    return collections.Counter(triangles)


def package(pixels, label, alpha=False):
    image = ct.TplImage(SIZE, SIZE, ct.GX_TF_RGBA8, b'')
    blob, _ = ct.build_package([image], [ct.MaterialBinding(label, 0, None)], twiddle=True, source_pixels={0: pixels})
    head = ct.HEADER.unpack_from(blob)
    desc = ct.TEXTURE.unpack_from(blob, head[5])
    expected = ct.FORMAT_ARGB4444 if alpha else ct.FORMAT_RGB565
    if desc[3] != expected or desc[7] != ct.PAYLOAD_TWIDDLED or desc[1:3] != (SIZE, SIZE):
        raise ValueError('unexpected atlas package descriptor')
    return blob, payload_key(blob[desc[4]:desc[4] + desc[5]])


def repair(dar, inputs):
    if sha(dar) != DAR_SHA:
        raise ValueError('unreviewed r117 DAR identity')
    for name, expected in INPUTS.items():
        if sha(inputs[name]) != expected:
            raise ValueError('unreviewed input identity: ' + name)
    # The retained GC material repeats in both axes, for colour and mask.
    gc_tpl = inputs['r117-gc-20.tpl']
    for i in range(2):
        hdr = struct.unpack_from('>I', gc_tpl, 12 + i * 8)[0]
        if struct.unpack_from('>II', gc_tpl, hdr + 12) != (1, 1):
            raise ValueError('source repeat policy changed')
    kind, size, dest, off = struct.unpack_from('<4I', dar, 32)
    pay = dar[off:off + size]
    entries = rs.tagged_entries(pay, '<')
    _, bs, be = entries[0x1f - 4]
    _, ts, te = entries[0x20 - 4]
    active = pay[bs:be]
    if sha(active) != 'd6c9b168191c8f3d5551a7e7508930642a76d2d346774b50465d8c5f5d8b9259':
        raise ValueError('unreviewed selected chandelier')
    tiles = decode_tiles(inputs['r117-ps2-20.tpl'])
    atlas, occupied = [(0, 0, 0, 0)] * (SIZE * SIZE), set()
    for tile in TILES:
        paste_repeat(atlas, occupied, tiles[tile['material']], tile['rect'])
    model = pb.parse_bin(inputs['r117-ps2-1f.bin'])
    source = list(pb.triangles(model))
    counts = collections.Counter(i for i, cs in source)
    if [counts[i] for i in range(3)] != [t['triangles'] for t in TILES]:
        raise ValueError('source material triangle counts changed')
    for tile, material in zip(TILES, model.materials):
        if material['diffuse'] != tile['image'] or (material['opacity'] if material['flag'] & 4 else None) != tile['mask']:
            raise ValueError('source material semantics changed')
    converted, sample_count, ideal_error, quant_error = [], 0, 0.0, 0.0
    for material, corners in source:
        rect = TILES[material]['rect']
        transformed = [atlas_uv(rect, c['uv']) for c in corners]
        quantized = [(round(u * 256) / 256, round(v * 256) / 256) for u, v in transformed]
        x, y, w, h = rect
        for actual, quant in zip(transformed, quantized):
            px, py = actual[0] * SIZE, actual[1] * SIZE
            if not (x - BORDER + 1 <= px < x + w + BORDER - 1 and y - BORDER + 1 <= py < y + h + BORDER - 1):
                raise ValueError('UV/filter footprint leaves periodic collar')
            quant_error = max(quant_error, abs(actual[0] - quant[0]) * SIZE, abs(actual[1] - quant[1]) * SIZE)
        for weights in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (.5, .5, 0), (0, .5, .5), (.5, 0, .5), (1/3, 1/3, 1/3)]:
            uv = tuple(sum(weights[j] * corners[j]['uv'][a] for j in range(3)) for a in range(2))
            mapped = atlas_uv(rect, uv)
            a = bilinear(tiles[material], w, h, uv)
            b = bilinear(atlas, SIZE, SIZE, mapped)
            ideal_error = max(ideal_error, max(abs(v - q) for v, q in zip(a, b)))
            sample_count += 1
        converted.append((0, [(c['p'], c['n'], uv, tuple(c['w'])) for c, uv in zip(corners, transformed)]))
    if ideal_error > 1e-9 or quant_error > .5000000001:
        raise ValueError('atlas sampling/quantization bound failed')
    rebuilt, stats = po.rebuild(inputs['r117-gc-1f.bin'], None, gc_tris_from=lambda m: converted)
    new = po.to_le(rebuilt, 'chandelier-atlas')
    if len(new) > len(active):
        raise ValueError('candidate exceeds selected BIN extent')
    new += bytes(len(active) - len(new))
    if geometry(new) != geometry(active) or sum(geometry(new).values()) != 1270:
        raise ValueError('geometry/normal/colour/weight contract changed')
    a, b = rs.bin_layout(active, '<'), rs.bin_layout(new, '<')
    for field in ['version', 'nw', 'nj', 'nd', 'flags', 'ext', 'nv', 'nn']:
        if a[field] != b[field]:
            raise ValueError('model contract changed: ' + field)
    if active[a['ptr']['head']:a['ptr']['vtx']] != new[b['ptr']['head']:b['ptr']['vtx']]:
        raise ValueError('joint/animation header changed')
    pa, pb_ = a['ptr']['parts'], b['ptr']['parts']
    if active[pa:pa + 24] != new[pb_:pb_ + 24]:
        raise ValueError('source material contract changed')
    colour_pixels = [(r, g, b, 255) for r, g, b, a in atlas]
    mask_pixels = [(a, a, a, 255) for r, g, b, a in atlas]
    colour, colour_key = package(colour_pixels, 'issue52 r117 chandelier colour')
    mask, mask_key = package(mask_pixels, 'issue52 r117 chandelier mask')
    pair, _ = package(atlas, 'issue52 r117 chandelier pair', alpha=True)
    combined_key = pair_key(colour_key, mask_key)
    packages = {colour_key: colour, mask_key: mask, combined_key: pair}
    if len(packages) != 3:
        raise ValueError('candidate key collision')
    out = bytearray(dar)
    out[off + bs:off + be] = new
    tpl = bytearray(pay[ts:te])
    key_ranges = []
    for i, key in enumerate([colour_key, mask_key]):
        desc = struct.unpack_from('<I', tpl, 8)[0]
        hdr = struct.unpack_from('<I', tpl, desc + i * 8)[0]
        rec = struct.unpack_from('<I', tpl, hdr + 8)[0]
        if tpl[rec:rec + 8] != b'R4NREF\0\0' or struct.unpack_from('<II', tpl, rec + 16) != (SIZE, SIZE):
            raise ValueError('source native reference shape changed')
        struct.pack_into('<II', tpl, rec + 8, *(int(v, 16) for v in key.split('-')))
        key_ranges.append([off + ts + rec + 8, off + ts + rec + 16])
    out[off + ts:off + te] = tpl
    allowed = [[off + bs, off + be]] + key_ranges
    changed = [i for i, (x, y) in enumerate(zip(dar, out)) if x != y]
    if any(not any(x <= i < y for x, y in allowed) for i in changed):
        raise ValueError('change outside BIN and two reference keys')
    report = dict(schema='issue52-chandelier-atlas-1', input_dar_sha256=sha(dar),
        inputs={name: sha(inputs[name]) for name in INPUTS}, source_materials=TILES,
        output_dar_sha256=sha(out), output_bytes=len(out), changed_bytes=len(changed), allowed_ranges=allowed,
        colour_key=colour_key, mask_key=mask_key, pair_key=combined_key,
        packages={k: dict(bytes=len(v), sha256=sha(v)) for k, v in packages.items()}, stats=stats,
        checks=dict(geometry_normal_colour_weights_exact=True, joint_animation_header_exact=True,
                    source_material_contract_exact=True, model_extents_exact=True, other_room_bytes_exact=True,
                    ideal_bilinear_samples=sample_count, ideal_max_channel_error=ideal_error,
                    signed8_8_max_atlas_pixel_error=quant_error, repeat_collar_texels=BORDER,
                    mask_alpha_levels=list(range(0, 256, 17))),
        tool_sources={Path(m.__file__).name: sha(Path(m.__file__).read_bytes()) for m in [po, pt, ct, rs]},
        limits=['Default-off source/data candidate only; no automatic staging.',
                'Signed8.8 UV quantization is bounded to half an atlas texel; repaired target appearance remains open.',
                'No guest, frame-time/FPS, release check or physical Dreamcast acceptance.'])
    return bytes(out), packages, atlas, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['dar', 'sources', 'out']:
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--enable-chandelier-atlas', action='store_true')
    args = ap.parse_args()
    if not args.enable_chandelier_atlas:
        raise ValueError('candidate disabled; explicit --enable-chandelier-atlas required')
    if args.out.exists():
        raise ValueError('refusing to overwrite output directory')
    output, packages, atlas, report = repair(args.dar.read_bytes(), {n: (args.sources / n).read_bytes() for n in INPUTS})
    report['tool_sources'][Path(__file__).name] = sha(Path(__file__).read_bytes())
    args.out.mkdir(parents=True)
    (args.out / 'r117.dar').write_bytes(output)
    tex = args.out / 'tex'
    tex.mkdir()
    for key, blob in packages.items():
        (tex / (key + '.re4tex')).write_bytes(blob)
    pt.write_png(args.out / 'atlas-source.png', SIZE, SIZE, bytes(v for p in atlas for v in p))
    (args.out / 'repair.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['output_dar_sha256', 'output_bytes', 'changed_bytes', 'pair_key', 'checks']}, indent=2))


if __name__ == '__main__':
    main()