#!/usr/bin/env python3
"""Default-off, report-only officer body picture transformer.

Computes the exact three-package/TPL correction in memory. This CLI writes only
small qualification metadata; asset emission/staging needs separate allocation.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys, zlib
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367/test12fx')]
import convert_tpl as ct
import ps2_objects as po
import ps2_tpl_decode as pt

INPUTS = {
    'r100-active-24.bin': 'd81cb3e345dbae7b39b26ce07e93b7ca6e08a259f4504ad81e06e0286a1f1df2',
    'r100-active-26.bin': '59e76709e9337775de95eea6c0bc7d72005f09802498323cdcc3101a426a4697',
    'r100-gc-24.bin': '7f171ccb945d92c325c0c9b428d449e1cfae8bb590b5b069fa5f8e96d7ab9a13',
    'r100-gc-26.bin': 'b3d2f8e1805a595e2a5a4a2eb81552ae076101bca9f3fb311afd57110a113798',
    'r100-ps2-22.bin': '02194f1344f183b71e3c50ef48e10f722faaa528f8d512254771d0cc95629ffb',
    'r100-ps2-24.bin': '78c553ed67420f367acbdfd7e00d5146ccd62314feabdf0a103647fe4c94f89a',
    'r100-active-25.tpl': '13b45adeaae5cfe975023eef2944fca2ef14240bc75ff52f54ac1e22e6568a14',
    'r100-gc-25.tpl': '6aec38379a01de8a43eaac8df8620c1b217328b4829b76f5f6e351e3c1462b86',
    'r100-ps2-23.tpl': '27cea0f1fea7168757028eebeed81c9498cdcfa2de1a83de6bdd5d2bf517f987',
}
PAIRS = [(0x24, 0x22, 1582), (0x26, 0x24, 1571)]
SHAPES = [(256, 128), (128, 64), (256, 256)]
BASE_DAR_SHA = '4abfcc88bb61989fadc4759d885879da07b9e670d8c38206620d57912482c37d'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key_for(payload):
    value = 2166136261
    for b in payload:
        value = ((value ^ b) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(payload) & 0xffffffff, value)


def records(tpl):
    count, desc = struct.unpack_from('<II', tpl, 4)
    if count != 3:
        raise ValueError('unreviewed body texture count')
    result = []
    for i in range(count):
        hdr = struct.unpack_from('<I', tpl, desc + 8 * i)[0]
        h, w, fmt, rec, ws, wt = struct.unpack_from('<2H4I', tpl, hdr)
        if tpl[rec:rec + 8] != b'R4NREF\0\0' or fmt != 14:
            raise ValueError('unreviewed native body reference')
        if struct.unpack_from('<3I', tpl, rec + 16) != (w, h, fmt):
            raise ValueError('native descriptor/record mismatch')
        result.append(dict(image=i, header=hdr, record=rec, shape=[w, h], source_format=fmt,
                           wrap=[ws, wt], key='%08x-%08x' % struct.unpack_from('<II', tpl, rec + 8)))
    return result


# Nearest representable expanded565 value, deterministic lower-code ties.
LEVEL5 = tuple((i << 3) | (i >> 2) for i in range(32))
LEVEL6 = tuple((i << 2) | (i >> 4) for i in range(64))
NEAREST5 = tuple(min(range(32), key=lambda i: (abs(v - LEVEL5[i]), i)) for v in range(256))
NEAREST6 = tuple(min(range(64), key=lambda i: (abs(v - LEVEL6[i]), i)) for v in range(256))


def quantize565(pixel):
    return (NEAREST5[pixel[0]] << 11) | (NEAREST6[pixel[1]] << 5) | NEAREST5[pixel[2]]


def expand565(word):
    return (LEVEL5[(word >> 11) & 31], LEVEL6[(word >> 5) & 63], LEVEL5[word & 31])


def opaque_package(pixels, w, h, label):
    if any(p[3] != 255 for p in pixels):
        raise ValueError('opaque body material cannot discard source alpha')
    image = ct.TplImage(w, h, ct.GX_TF_RGBA8, b'')
    encoded = [expand565(quantize565(p)) + (255,) for p in pixels]
    blob, _ = ct.build_package([image], [ct.MaterialBinding(label, 0, None)], twiddle=True, source_pixels={0: encoded})
    header = ct.HEADER.unpack_from(blob)
    desc = ct.TEXTURE.unpack_from(blob, header[5])
    if desc[3] != ct.FORMAT_RGB565 or desc[6] or desc[7] != ct.PAYLOAD_TWIDDLED:
        raise ValueError('body package changed alpha/layout contract')
    return blob, key_for(blob[desc[4]:desc[4] + desc[5]])


def transform(inputs):
    for name, digest in INPUTS.items():
        if sha(inputs[name]) != digest:
            raise ValueError('unreviewed body input identity: ' + name)
    # Recover material correspondence from the conversion that exactly produced
    # each selected body. Never infer it from same-number archive/image labels.
    mappings, models = {}, []
    for gc_slot, ps2_slot, triangles in PAIRS:
        gc = inputs['r100-gc-%02x.bin' % gc_slot]
        ps2 = inputs['r100-ps2-%02x.bin' % ps2_slot]
        selected = inputs['r100-active-%02x.bin' % gc_slot]
        rebuilt, stats = po.rebuild(gc, ps2)
        if po.to_le(rebuilt) != selected or stats['out_tris'] != triangles:
            raise ValueError('selected body does not reproduce from paired source')
        parts = po.GcModel(rebuilt).parts
        if any(part['hdr'][11] & 4 for part in parts):
            raise ValueError('unreviewed alpha-masked body part')
        for part, (gc_image, ps2_images) in stats['part_images'].items():
            mappings.setdefault(gc_image, set()).update(ps2_images)
        models.append(dict(gc_BIN=gc_slot, ps2_BIN=ps2_slot, gc_TPL=0x25, ps2_TPL=0x23,
                           selected_reproduced_exactly=True, triangles=triangles,
                           BIN_sha256=sha(selected), material_flags=[p['hdr'][11] for p in parts],
                           geometry_UV_animation='Unchanged selected BIN bytes; no model or motion transformation.'))
    if mappings != {0: {0}, 1: {1}, 2: {2}}:
        raise ValueError('unreviewed many-to-one/changed picture correspondence')
    template = inputs['r100-active-25.tpl']
    before = records(template)
    original = ct.parse_tpl(inputs['r100-gc-25.tpl'])
    decoded = pt.parse_tpl(inputs['r100-ps2-23.tpl'])['entries']
    if len(original) != 3 or len(decoded) != 3:
        raise ValueError('source TPL count changed')
    out, packages, rows, allowed = bytearray(template), {}, [], []
    for old in before:
        image = old['image']
        ps2_image = next(iter(mappings[image]))
        header = decoded[ps2_image]
        if header['interlace'] & 1:
            raise ValueError('unreviewed PS2 picture orientation')
        w, h, rgba, stats = pt.decode(inputs['r100-ps2-23.tpl'], header)
        if (w, h) != SHAPES[image] or old['shape'] != [original[image].width, original[image].height]:
            raise ValueError('unreviewed source picture dimensions')
        pixels = list(zip(*(iter(rgba),) * 4))
        blob, key = opaque_package(pixels, w, h, 'issue52 r100 body image%d' % image)
        packages[key] = blob
        hdr, rec = old['header'], old['record']
        struct.pack_into('<HH', out, hdr, h, w)
        struct.pack_into('<II', out, rec + 8, *(int(v, 16) for v in key.split('-')))
        struct.pack_into('<II', out, rec + 16, w, h)
        allowed.extend([[hdr, hdr + 4], [rec + 8, rec + 24]])
        words = [quantize565(p) for p in pixels]
        max_error = [0, 0, 0]
        for p, word in zip(pixels, words):
            expanded = expand565(word)
            max_error = [max(a, abs(v - q)) for a, v, q in zip(max_error, p, expanded)]
        rows.append(dict(gc_image=image, paired_PS2_image=ps2_image, old_key=old['key'], new_key=key,
                         old_shape=old['shape'], declared_shape=[w, h], wrap=old['wrap'],
                         source_RGBA_sha256=sha(rgba), source_alpha_levels=sorted(set(rgba[3::4])),
                         package_sha256=sha(blob), package_bytes=len(blob), payload_bytes=2 * w * h,
                         source_format_preserved=old['source_format'], package_format='RGB565 twiddled',
                         no_picture_resize=True, quantization='nearest expanded RGB565; no VQ', UV_normalization='Header and package dimensions equal; renderer u/v scales1.',
                         max_RGB_channel_quantization_error=max_error))
    after = records(out)
    for old, new, shape in zip(before, after, SHAPES):
        if old['wrap'] != new['wrap'] or old['source_format'] != new['source_format'] or new['shape'] != list(shape):
            raise ValueError('body repeat/format/shape contract changed')
    changed = [i for i, (a, b) in enumerate(zip(template, out)) if a != b]
    if len(out) != len(template) or any(not any(a <= i < b for a, b in allowed) for i in changed):
        raise ValueError('TPL change outside dimensions/native reference identities')
    if len(packages) != 3:
        raise ValueError('body package identity collision')
    report = dict(schema='issue52-officer-body-transform-plan-1', base_DAR_sha256=BASE_DAR_SHA,
                  inputs={n: sha(inputs[n]) for n in INPUTS}, models=models, pictures=rows,
                  TPL_slot=0x25, original_TPL_sha256=sha(template), transformed_TPL_sha256=sha(out),
                  TPL_bytes=len(out), changed_TPL_bytes=len(changed), allowed_TPL_ranges=allowed,
                  geometry_UV_pose_motion_head_bytes_changed=0,
                  source_payload_bytes=sum(r['payload_bytes'] for r in rows),
                  in_memory_package_bytes=sum(len(v) for v in packages.values()),
                  tool_sources={Path(m.__file__).name: sha(Path(m.__file__).read_bytes()) for m in [po, pt, ct]},
                  limits=['Report-only CLI: no asset, archive, mirror, stage or guest emitted.',
                          'In-memory diffuse-picture correction only; head candidate is separate.',
                          'Historical body weight conversion is preserved, not repaired or target-qualified.',
                          'No target appearance/capacity, release or physical Dreamcast acceptance; no performance claim.'])
    return bytes(out), packages, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources', required=True, type=Path)
    ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--enable-body-texture-transform', action='store_true')
    args = ap.parse_args()
    if not args.enable_body_texture_transform:
        raise ValueError('body transformer disabled; explicit enable flag required')
    if args.report.exists():
        raise ValueError('refusing to overwrite report')
    tpl, packages, report = transform({n: (args.sources / n).read_bytes() for n in INPUTS})
    report['tool_sources'][Path(__file__).name] = sha(Path(__file__).read_bytes())
    text = json.dumps(report, indent=2) + '\n'
    if len(text.encode()) > 128 * 1024:
        raise ValueError('report exceeds bounded metadata budget')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text)
    print(json.dumps({k: report[k] for k in ['transformed_TPL_sha256', 'TPL_bytes', 'changed_TPL_bytes',
                                             'geometry_UV_pose_motion_head_bytes_changed', 'source_payload_bytes']}, indent=2))


if __name__ == '__main__':
    main()