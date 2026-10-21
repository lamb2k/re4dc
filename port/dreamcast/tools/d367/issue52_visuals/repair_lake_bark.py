#!/usr/bin/env python3
"""Opt-in repair of the exact public Test21 r10b floating-island material map.

Source/data candidate only. No recipe/default/runtime changes or target acceptance.
The PS2 bark/stump images use indices2/3; retained GC materials use4/5.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
import ps2_objects as po
import room_smd as rs

DAR_SHA = '39bd07e125cc0830446ca70207e52c60d949699ed0e1dfc53186e805e4f87b49'
GC_SHA = '7cb06f6f9c9270d842a8da4391533d62275ba45936914537f7bd3ed6c155bd6b'
PS2_SHA = '143942ef2453e9b4b7ee45ceaeec4c0033221f235c594e056813b16ed3e10d2d'
TEX_MAP = {0: 0, 2: 4, 3: 5}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def verify_inputs(dar, gc, ps2):
    for name, blob, expected in [('DAR', dar, DAR_SHA), ('GC BIN', gc, GC_SHA), ('PS2 BIN', ps2, PS2_SHA)]:
        if sha(blob) != expected:
            raise ValueError('unreviewed %s identity' % name)


def repair(dar, gc, ps2):
    verify_inputs(dar, gc, ps2)
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if (kind, dest) != (0, 0) or off + size > len(dar):
        raise ValueError('unexpected native payload')
    pay = dar[off:off + size]
    old_entries = rs.tagged_entries(pay, '<')
    target = 0x1e - 4
    tag, start, end = old_entries[target]
    if tag.rstrip(b'\0') != b'BIN':
        raise ValueError('target is not a BIN')
    new_bin, stats = po.rebuild(gc, ps2, tex_map=TEX_MAP)
    model = po.GcModel(new_bin)
    counts = [len(p['tris']) for p in model.parts]
    if counts != [406, 39, 0, 84] or stats['no_tex_part'] or stats['out_tris'] != 529:
        raise ValueError('reviewed material cohorts changed')
    # Retain every material contract except the stream length/polygon count.
    original = po.GcModel(gc)
    for old, new in zip(original.parts, model.parts):
        if old['hdr'][:24] != new['hdr'][:24]:
            raise ValueError('material header changed')
    newpay = po.rebuild_tagged(pay, '<', {target: po.to_le(new_bin, 'r10b:1e')})
    newpay, tables = po.remap_native_tables(pay, newpay)
    new_entries = rs.tagged_entries(newpay, '<')
    retained = []
    for i, ((tag, a, b), (newtag, c, d)) in enumerate(zip(old_entries, new_entries)):
        if tag != newtag:
            raise ValueError('entry tag changed')
        if i == target or tag in po.NATIVE_TABLES:
            continue
        if pay[a:b] != newpay[c:d]:
            raise ValueError('unrelated payload entry changed')
        retained.append(i + 4)
    out = bytearray(dar[:off]) + newpay
    out += bytes(po.al(len(out), 2048) - len(out))
    struct.pack_into('<4I', out, 0x20, kind, len(newpay), dest, off)
    report = dict(schema='issue52-r10b-bark-map-1', input_dar_sha256=sha(dar), gc_bin_sha256=sha(gc), ps2_bin_sha256=sha(ps2),
                  texture_map=TEX_MAP, source_part_triangles=counts, stats=stats, native_tables=tables,
                  retained_payload_entries=retained, payload_before=len(pay), payload_after=len(newpay),
                  output_bytes=len(out), output_sha256=sha(out),
                  tool_sources={p.name: sha(p.read_bytes()) for p in [Path(__file__), Path(po.__file__), Path(rs.__file__)]},
                  limits=['Opt-in source/data candidate; no automatic staging.', 'Existing public texture records/packages retained.',
                          'No repaired Flycast look, timing, release check or physical Dreamcast acceptance.'])
    return bytes(out), report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['dar', 'gc-bin', 'ps2-bin', 'out', 'report']:
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--enable-r10b-bark-map', action='store_true')
    args = ap.parse_args()
    if not args.enable_r10b_bark_map:
        raise ValueError('candidate disabled; explicit --enable-r10b-bark-map required')
    if args.out.exists() or args.report.exists():
        raise ValueError('refusing to overwrite output')
    output, report = repair(args.dar.read_bytes(), args.gc_bin.read_bytes(), args.ps2_bin.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(output)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
