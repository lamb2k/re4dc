#!/usr/bin/env python3
"""Opt-in source/data candidate for exact Test21 officer head material indices.

Only two r100 head BINs change. Body atlas layout remains a separate open case.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path
TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
import ps2_objects as po
import room_smd as rs

DAR_SHA = '4abfcc88bb61989fadc4759d885879da07b9e670d8c38206620d57912482c37d'
HEADS = [
    dict(slot=0x27, ps2_slot=0x25, mapping={0: 2}, triangles=1021,
         gc_sha='982b7e45f4cb019e9a565dbf7f0e5ea5a35b8993104b102b7167f9674f9d6ba9',
         ps2_sha='83ced77fbf122433f71bbb46ce19f9316b8c12caccea12432bb757013631b76d',
         active_sha='34c16b40088674b754783f83371033300a3fc7244a8850a169356adb7ce22ba8',
         counts=[0, 0, 0, 919, 51, 51, 0, 0, 0, 0]),
    dict(slot=0x29, ps2_slot=0x27, mapping={4: 6}, triangles=1276,
         gc_sha='d9515fa31d771cf819db9f4a593bcb3a1c776d8992c675d789cb365e4271f3be',
         ps2_sha='2b3283fe9de6a641c4da97acf92cd650f5af8179c79d9863bb0591221352f1db',
         active_sha='3f701c95090965c88916e2876c4185a6c438fafe417e9c76e510e9bb1e8b34c0',
         counts=[120, 132, 0, 0, 0, 846, 46, 46, 60, 26, 0, 0, 0]),
]


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def repair(dar, sources):
    if sha(dar) != DAR_SHA:
        raise ValueError('unreviewed r100 DAR identity')
    kind, size, dest, off = struct.unpack_from('<4I', dar, 0x20)
    if (kind, dest) != (0, 0) or off + size > len(dar):
        raise ValueError('unexpected native payload')
    pay = dar[off:off + size]
    entries = rs.tagged_entries(pay, '<')
    out = bytearray(dar)
    rows = []
    for case in HEADS:
        slot = case['slot']
        gc, ps2 = sources[slot]
        if sha(gc) != case['gc_sha'] or sha(ps2) != case['ps2_sha']:
            raise ValueError('unreviewed head source identity')
        tag, start, end = entries[slot - 4]
        if tag.rstrip(b'\0') != b'BIN' or sha(pay[start:end]) != case['active_sha']:
            raise ValueError('unreviewed selected head')
        new, stats = po.rebuild(gc, ps2, tex_map=case['mapping'])
        model = po.GcModel(new)
        counts = [len(p['tris']) for p in model.parts]
        if counts != case['counts'] or stats['out_tris'] != case['triangles'] or stats['no_tex_part']:
            raise ValueError('reviewed head cohorts changed')
        for a, b in zip(po.GcModel(gc).parts, model.parts):
            if a['hdr'][:24] != b['hdr'][:24]:
                raise ValueError('material contract changed')
        new = po.to_le(new, 'r100:%x' % slot)
        if len(new) > end - start:
            raise ValueError('candidate exceeds exact head extent')
        # Preserve payload/heap/ISO offsets and NTR rows; no archive repack.
        new += bytes(end - start - len(new))
        out[off + start:off + end] = new
        rows.append(dict(slot=slot, ps2_slot=case['ps2_slot'], texture_map=case['mapping'],
                         gc_sha256=sha(gc), ps2_sha256=sha(ps2), stats=stats,
                         part_triangles=counts, output_BIN_sha256=sha(new),
                         range=[off + start, off + end], padded_bytes=len(new)))
    allowed = [r['range'] for r in rows]
    changed = [i for i, (a, b) in enumerate(zip(dar, out)) if a != b]
    if any(not any(a <= i < b for a, b in allowed) for i in changed):
        raise ValueError('change outside reviewed head extents')
    report = dict(schema='issue52-officer-head-map-1', input_dar_sha256=sha(dar), heads=rows,
                  output_bytes=len(out), output_sha256=sha(out), changed_bytes=len(changed),
                  tool_sources={p.name: sha(p.read_bytes()) for p in [Path(__file__), Path(po.__file__), Path(rs.__file__)]},
                  limits=['Opt-in source/data candidate; no automatic staging.',
                          'Body atlas/UV layout remains open; this does not claim a complete officer fix.',
                          'No repaired Flycast look, timing, release check or physical Dreamcast acceptance.'])
    return bytes(out), report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ['dar', 'sources', 'out', 'report']:
        ap.add_argument('--' + name, required=True, type=Path)
    ap.add_argument('--enable-officer-head-map', action='store_true')
    args = ap.parse_args()
    if not args.enable_officer_head_map:
        raise ValueError('candidate disabled; explicit --enable-officer-head-map required')
    if args.out.exists() or args.report.exists():
        raise ValueError('refusing to overwrite output')
    sources = {c['slot']: ((args.sources / ('r100-gc-%02x.bin' % c['slot'])).read_bytes(),
                          (args.sources / ('r100-ps2-%02x.bin' % c['ps2_slot'])).read_bytes()) for c in HEADS}
    output, report = repair(args.dar.read_bytes(), sources)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(output)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()