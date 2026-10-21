#!/usr/bin/env python3
"""Independent on-disk TPL/RE4DCTX readback for the frozen605 body bundle.

Native parser/Morton/RGB565 decoder does not import the transformer or encoder.
The retained PS2 decoder is used only to read the original expected pictures.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys, zlib
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
PLAN_SHA = '630dd8ea65cef68de30102cd7a109017848a4cf4035fefa2fe60650c0d2215ce'
HEAD = struct.Struct('<8s10I')
DESC = struct.Struct('<64s8I')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def payload_key(data):
    fnv = 2166136261
    for value in data:
        fnv = ((fnv ^ value) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(data) & 0xffffffff, fnv)


def decode_native(blob):
    if len(blob) < 144:
        raise ValueError('short native package')
    magic, version, hsize, stride, count, toff, doff, size, crc, r0, r1 = HEAD.unpack_from(blob)
    if (magic, version, hsize, stride, count, toff, doff) != (b'RE4DCTX\0', 2, 48, 96, 1, 48, 144):
        raise ValueError('unqualified native header')
    if doff + size != len(blob) or zlib.crc32(blob[toff:]) & 0xffffffff != crc:
        raise ValueError('native CRC/extent failed')
    name, w, h, fmt, off, nbytes, flags, layout, extra = DESC.unpack_from(blob, toff)
    if fmt != 0 or layout != 1 or flags or extra or off != doff or nbytes != size or size != 2 * w * h:
        raise ValueError('native RGB565 layout contract failed')
    if min(w, h) < 8 or max(w, h) > 1024 or w & (w - 1) or h & (h - 1):
        raise ValueError('native dimensions failed')
    raw = blob[off:off + nbytes]
    words = struct.unpack('<%dH' % (w * h), raw)
    decoded = bytearray()
    side = min(w, h)
    for y in range(h):
        for x in range(w):
            sx, sy = x % side, y % side
            morton = 0
            for bit in range(side.bit_length() - 1):
                morton |= ((sy >> bit) & 1) << (2 * bit)
                morton |= ((sx >> bit) & 1) << (2 * bit + 1)
            index = morton + (x // side + y // side) * side * side
            value = words[index]
            r, g, b = (value >> 11) & 31, (value >> 5) & 63, value & 31
            decoded.extend(((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255))
    return w, h, bytes(decoded), payload_key(raw)


def parse_tpl(blob):
    if len(blob) != 256:
        raise ValueError('TPL extent changed')
    magic, count, table = struct.unpack_from('<3I', blob)
    if magic != 0x20af30 or count != 3 or table != 12:
        raise ValueError('TPL header changed')
    result = []
    for i in range(count):
        hdr, palette = struct.unpack_from('<2I', blob, table + i * 8)
        height, width, fmt, record, ws, wt = struct.unpack_from('<2H4I', blob, hdr)
        if palette or hdr + 36 > len(blob) or record + 32 > len(blob):
            raise ValueError('TPL pointer outside fragment')
        if blob[record:record + 8] != b'R4NREF\0\0':
            raise ValueError('TPL native record missing')
        if struct.unpack_from('<3I', blob, record + 16) != (width, height, fmt):
            raise ValueError('TPL native descriptor does not match header')
        if fmt != 14 or (ws, wt) != (1, 1):
            raise ValueError('TPL source CMPR/repeat contract changed')
        key = '%08x-%08x' % struct.unpack_from('<2I', blob, record + 8)
        result.append(dict(image=i, header=hdr, record=record, width=width, height=height, key=key))
    return result


def nearest_reference(pixels):
    # Separate reference quantizer, defined against representable channel values.
    levels5 = [(i << 3) | (i >> 2) for i in range(32)]
    levels6 = [(i << 2) | (i >> 4) for i in range(64)]
    r5 = [min(levels5, key=lambda q: (abs(v - q), q)) for v in range(256)]
    r6 = [min(levels6, key=lambda q: (abs(v - q), q)) for v in range(256)]
    result = bytearray()
    for i in range(0, len(pixels), 4):
        if pixels[i + 3] != 255:
            raise ValueError('source body alpha is not opaque')
        result.extend((r5[pixels[i]], r6[pixels[i + 1]], r5[pixels[i + 2]], 255))
    return bytes(result)


def verify(candidate, sources, plan_path):
    raw_plan = plan_path.read_bytes()
    if sha(raw_plan) != PLAN_SHA:
        raise ValueError('frozen605 plan identity failed')
    plan = json.loads(raw_plan)
    for name, expected in plan['inputs'].items():
        if sha((sources / name).read_bytes()) != expected:
            raise ValueError('source identity failed: ' + name)
    tpl_path = candidate / 'r100-body-25.tpl'
    tpl = tpl_path.read_bytes()
    if sha(tpl) != plan['transformed_TPL_sha256']:
        raise ValueError('actual emitted TPL identity failed')
    before = (sources / 'r100-active-25.tpl').read_bytes()
    old, current = parse_tpl(before), parse_tpl(tpl)
    allowed = set()
    for row in old:
        allowed.update(range(row['header'], row['header'] + 4))
        allowed.update(range(row['record'] + 8, row['record'] + 24))
    changed = [i for i, (a, b) in enumerate(zip(before, tpl)) if a != b]
    if len(changed) != 32 or any(i not in allowed for i in changed):
        raise ValueError('TPL scope is not the reviewed32byte change')
    sys.path.insert(0, str(TOOLS / 'd367/test12fx'))
    import ps2_tpl_decode as source_tpl
    if sha(Path(source_tpl.__file__).read_bytes()) != plan['tool_sources']['ps2_tpl_decode.py']:
        raise ValueError('frozen source picture decoder changed')
    source_bytes = (sources / 'r100-ps2-23.tpl').read_bytes()
    source_headers = source_tpl.parse_tpl(source_bytes)['entries']
    files, decoded_rows, texels = [], [], 0
    for row, expected in zip(current, plan['pictures']):
        key = expected['new_key']
        if row['key'] != key or [row['width'], row['height']] != expected['declared_shape']:
            raise ValueError('emitted TPL sampler binding changed')
        path = candidate / 'tex' / (key + '.re4tex')
        blob = path.read_bytes()
        if sha(blob) != expected['package_sha256']:
            raise ValueError('emitted texture identity failed')
        w, h, pixels, actual_key = decode_native(blob)
        if actual_key != key or (w, h) != (row['width'], row['height']):
            raise ValueError('package/TPL dimensions or payload key disagree')
        header = source_headers[expected['paired_PS2_image']]
        sw, sh, source, stats = source_tpl.decode(source_bytes, header)
        if (sw, sh) != (w, h) or header['interlace'] & 1:
            raise ValueError('source image dimensions/orientation changed')
        reference = nearest_reference(source)
        if pixels != reference:
            raise ValueError('independently decoded texture differs from all-pixel source reference')
        texels += w * h
        files.append(dict(path=str(path.relative_to(candidate)), bytes=len(blob), sha256=sha(blob)))
        decoded_rows.append(dict(key=key, width=w, height=h, decoded_RGBA_sha256=sha(pixels),
                                 all_texels_match_reference=True, alpha255=True))
    files.append(dict(path='r100-body-25.tpl', bytes=len(tpl), sha256=sha(tpl)))
    expected_assets = {r['path'] for r in files}
    actual_assets = {str(p.relative_to(candidate)) for p in candidate.rglob('*') if p.is_file() and p.suffix in ('.tpl', '.re4tex', '.bin', '.dar', '.gdi', '.iso')}
    if actual_assets != expected_assets:
        raise ValueError('unreviewed extra/missing binary assets')
    return dict(schema='issue52-officer-body-independent-readback-1', frozen_source_commit='605d76beddff0a1e132b8be362937e143f325730',
        frozen_plan_sha256=PLAN_SHA, independent_verifier_sha256=sha(Path(__file__).read_bytes()), files=files,
        decoded=decoded_rows, decoded_texels=texels, TPL_changed_bytes=len(changed),
        TPL_extent_unchanged=True, other_TPL_bytes_exact=True, all_source_inputs_unchanged=True,
        source_payload_delta_bytes=139264,
        limits=['Actual privately emitted assets independently parsed/decoded; no archive/image/stage/guest.',
                'No model/UV/material/animation/head assets emitted or altered.',
                'No target appearance/capacity/performance/release/physical acceptance.'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['candidate', 'sources', 'plan', 'report']:
        ap.add_argument('--' + name, type=Path, required=True)
    args = ap.parse_args()
    if args.report.exists():
        raise ValueError('refusing to overwrite readback report')
    report = verify(args.candidate, args.sources, args.plan)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(decoded_texels=report['decoded_texels'], TPL_changed_bytes=report['TPL_changed_bytes'], passed=True)))


if __name__ == '__main__':
    main()