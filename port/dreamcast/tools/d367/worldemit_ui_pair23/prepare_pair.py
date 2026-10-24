#!/usr/bin/env python3
"""Audit one exact PS2 Mendez pair; emit only with --prepare-private OUTPUT.
No GC pixels, image resampling, VQ, runtime/recipe changes or production acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

TOOLS = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TOOLS), str(TOOLS / 'd367/test12fx')]
import ps2_bin as pb
import ps2_tpl_decode as td
import convert_tpl as ct
from prepare_native_ui import material_pair_identity

COLOR = '43aff05a-cfb2b1a5'
MASK = '572a97ee-75aeb071'
KEY = '7d4e1e92-052bdc2e'
DAT_SHA = '97535f18b388066dc9bb876f421d64c83d18710592617f7fa70a7d40456370d3'
TPL_SHA = '25a93ea79a3cb55d0b0ccca208e63d829750d5e4d6e521a44fe93d46c4f18640'
DAT_SIZE = 3727616

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_materials(materials):
    masked = [m for m in materials if m['flag'] & 4]
    if len(masked) != 1 or (masked[0]['flag'], masked[0]['diffuse'], masked[0]['opacity']) != (4, 0, 1):
        raise ValueError('expected sole explicit PS2 colour0 opacity1 material')
    return masked[0]['raw']

def compose(colour, mask, width, height):
    if width != 128 or height != 128 or len(colour) != width*height*4 or len(mask) != len(colour):
        raise ValueError('exact 128x128 RGBA pair required')
    pixels = []
    for off in range(0, len(colour), 4):
        r, g, b = mask[off:off+3]
        if r != g or r != b or r % 16:
            raise ValueError('PS2 opacity image must use authored grey 4-bit levels')
        # Existing ps2_objects_tex mask recipe: n*16 -> n*17, then ARGB4444.
        pixels.append(tuple(colour[off:off+3]) + (r//16*17,))
    return pixels

def encode(pixels):
    if len(pixels) != 128*128:
        raise ValueError('wrong composed pixel count')
    placeholder = ct.TplImage(128, 128, ct.GX_TF_RGBA8, b'')
    # Every source pixel is provided by the PS2 decoder; GX decode is never called.
    return ct.build_package([placeholder], [ct.MaterialBinding('PS2-em35-TPL5-0-opacity1', 0, None)],
                            twiddle=True, source_pixels={0: pixels})

def audit(raw):
    if len(raw) != DAT_SIZE or sha(raw) != DAT_SHA:
        raise ValueError('PS2 em35.dat exact member identity mismatch')
    entries = {i+4: (tag, data) for i, tag, data in pb.dat_entries(raw)}
    tag, tpl = entries[5]
    if tag != 'TPL' or sha(tpl) != TPL_SHA:
        raise ValueError('PS2 TPL5 identity mismatch')
    tp = td.parse_tpl(tpl)
    if tp['count'] != 9:
        raise ValueError('PS2 TPL5 entry count mismatch')
    materials = {}
    for arc in (4, 7):
        tag, data = entries[arc]
        if tag != 'BIN':
            raise ValueError('PS2 masked owner is not BIN')
        model = pb.parse_bin(data)
        materials[str(arc)] = dict(bin_sha256=sha(data), raw=check_materials(model.materials))
    for arc in (6, 8):
        tag, data = entries[arc]
        if tag != 'BIN' or any(m['flag'] & 4 for m in pb.parse_bin(data).materials):
            raise ValueError('unexpected PS2 mask on extra/legs owner')
    decoded, image_records = [], []
    for i in (0, 1):
        h = tp['entries'][i]
        if (h['width'], h['height'], h['bitdepth'], h['interlace']) != (128, 128, 9 if i == 0 else 8, 2):
            raise ValueError('PS2 image descriptor mismatch')
        w, ht, rgba, _ = td.decode(tpl, h, swizzle='gs')
        jw, jh, jrgba, _ = td.decode(tpl, h, swizzle='jl')
        if (w, ht, rgba) != (jw, jh, jrgba):
            raise ValueError('independent PS2 unswizzle disagreement')
        decoded.append(rgba)
        image_records.append(dict(index=i, rgba_sha256=sha(rgba), header=h))
    if material_pair_identity(COLOR, MASK) != KEY:
        raise ValueError('runtime pair key mismatch')
    pixels = compose(*decoded, 128, 128)
    blob, meta = encode(pixels)
    # The full-body CRC domain is the one required by the native package loader.
    if ct.canonical_native_crc(blob) != blob:
        raise ValueError('noncanonical native package')
    report = dict(schema='PS2_MENDEZ_PAIR_PRIVATE_CANDIDATE_V1', key=KEY,
        requested_source_tokens=dict(colour=COLOR, mask=MASK),
        member=dict(name='em35.dat', bytes=len(raw), sha256=sha(raw)),
        tpl=dict(arc=5, bytes=len(tpl), sha256=sha(tpl)), materials=materials,
        images=image_records, recipe='PS2 RGB image0 + grayscale opacity image1; n*16 to n*17; twiddled ARGB4444',
        native=meta, package=dict(bytes=len(blob), sha256=sha(blob)),
        production_enabled=False, runtime_qualified=False, look_approved=False,
        limitations=['Source tokens name the requesting GC TPL identities; emitted pixels are exclusively PS2.',
                      'Source material correspondence does not certify reference-mesh UV parity or visible result.',
                      'No SDK/guest/upload/VRAM/gameplay gate performed; original Mendez failure remains.'])
    return report, blob, decoded, pixels

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ps2-iso', type=Path, required=True)
    ap.add_argument('--prepare-private', type=Path)
    args = ap.parse_args(argv)
    index = pb.afs_index(args.ps2_iso)
    offset, size = index['em35.dat']
    if size != DAT_SIZE:
        raise ValueError('PS2 AFS em35 member size mismatch')
    report, blob, decoded, pixels = audit(pb.afs_read(args.ps2_iso, 'em35.dat', index))
    report['input_location'] = dict(iso=str(args.ps2_iso.resolve()), member_byte_offset=offset)
    report['tools'] = {str(p.relative_to(TOOLS)): sha(p.read_bytes()) for p in
                       [Path(__file__), Path(pb.__file__), Path(td.__file__), Path(ct.__file__)]}
    if args.prepare_private:
        out = args.prepare_private
        out.mkdir(parents=True, exist_ok=False)
        target = out / 'files/dc/tex/7' / (KEY + '.re4tex')
        target.parent.mkdir(parents=True)
        target.write_bytes(blob)
        td.write_png(out/'ps2-colour.png', 128, 128, decoded[0])
        td.write_png(out/'ps2-opacity.png', 128, 128, decoded[1])
        td.write_png(out/'ps2-pair.png', 128, 128, bytes(v for p in pixels for v in p))
        (out/'candidate.json').write_text(json.dumps(report, indent=2)+'\n')
        # Explicit local-only manifest, never auto-enrolled in DATA or a recipe.
        (out/'local-pack.json').write_text(json.dumps(dict(replace={str(target.relative_to(out/'files')): str(target.resolve())},
              option='MENDEZ_PS2_PAIR23_PRIVATE', default=0, production_enabled=False,
              candidate_sha256=report['package']['sha256']), indent=2)+'\n')
    print(json.dumps(dict(key=KEY, package=report['package'], private_written=bool(args.prepare_private),
                          production_enabled=False, runtime_qualified=False), indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
